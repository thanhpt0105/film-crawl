"""
Download a Dailymotion video given its page URL.

Dailymotion serves video as an HLS stream (m3u8 playlist of small .ts
segments), so this script:
  1. Fetches the public player metadata API to get the title and the
     master playlist URL.
  2. Picks the highest-bandwidth variant from the master playlist.
  3. Downloads every .ts segment from that variant and concatenates them
     into a single .ts file (playable directly in VLC/mpv/etc. - MPEG-TS
     segments can be concatenated as-is without re-encoding).

No third-party dependencies (no ffmpeg required).

Usage:
    # Single video
    python download_dailymotion_video.py "<dailymotion url or video id>" [output_path]

    # Multiple videos listed in a text file (one URL per line, blank
    # lines and lines starting with # are ignored)
    python download_dailymotion_video.py -f urls.txt [-o output_dir]
"""
import argparse
import http.client
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from concurrent.futures import ThreadPoolExecutor

METADATA_API = "https://www.dailymotion.com/player/metadata/video/{}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://www.dailymotion.com/",
    # Cloudflare in front of the HLS manifest returns 403 without these.
    "Origin": "https://www.dailymotion.com",
    "Accept": "*/*",
    "Accept-Encoding": "identity",
}

MAX_RETRIES = 8
DOWNLOAD_WORKERS = 16
RETRY_BACKOFF_SECONDS = 3
RATE_LIMIT_BACKOFF_SECONDS = 15


def parse_video_id(url_or_id: str) -> str:
    """Extract the Dailymotion video id from a page URL, short url, or a
    bare id.

    Examples:
      https://www.dailymotion.com/video/x9nz2mg -> x9nz2mg
      https://dai.ly/x9nz2mg                     -> x9nz2mg
      x9nz2mg                                    -> x9nz2mg
    """
    parsed = urllib.parse.urlparse(url_or_id)
    path = parsed.path.strip("/")
    if not path:
        return url_or_id.strip()
    return path.split("/")[-1]


def fetch_url(url: str, headers: dict | None = None, timeout: int = 15) -> bytes:
    req = urllib.request.Request(url, headers=headers or HEADERS, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_metadata(video_id: str) -> dict:
    data = fetch_url(METADATA_API.format(video_id))
    metadata = json.loads(data)
    if "error" in metadata:
        raise RuntimeError(f"Dailymotion returned an error: {metadata['error']}")
    return metadata


def parse_master_playlist(playlist_text: str, base_url: str) -> list[dict]:
    """Parse a master m3u8 playlist into a list of variants, each with
    'bandwidth' and 'url' (resolved to an absolute URL).
    """
    variants = []
    lines = playlist_text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("#EXT-X-STREAM-INF:"):
            attrs = line[len("#EXT-X-STREAM-INF:") :]
            bandwidth_match = re.search(r"BANDWIDTH=(\d+)", attrs)
            bandwidth = int(bandwidth_match.group(1)) if bandwidth_match else 0
            if i + 1 < len(lines):
                uri = lines[i + 1].strip().split("#", 1)[0]
                variants.append(
                    {"bandwidth": bandwidth, "url": urllib.parse.urljoin(base_url, uri)}
                )
    return variants


def parse_media_playlist(playlist_text: str, base_url: str) -> list[str]:
    """Parse a variant m3u8 playlist into a list of absolute segment URLs."""
    if "#EXT-X-KEY" in playlist_text:
        raise RuntimeError(
            "This stream is encrypted (EXT-X-KEY); this script cannot decrypt "
            "segments without ffmpeg."
        )

    segments = []
    for line in playlist_text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            segments.append(urllib.parse.urljoin(base_url, line))
    return segments


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = name.strip().strip(".")
    return name or "video"


def format_size(num_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f}{unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f}TB"


def read_urls_from_file(path: str) -> list[str]:
    urls = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def resolve_video_info(url_or_id: str) -> tuple[str, list[str]]:
    """Resolve a Dailymotion URL/id to (title, list of segment urls),
    retrying on transient network errors.
    """
    video_id = parse_video_id(url_or_id)
    print(f"Resolving: {video_id}")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            metadata = fetch_metadata(video_id)
            title = metadata.get("title") or video_id

            qualities = metadata.get("qualities", {})
            auto = qualities.get("auto") or []
            if not auto:
                raise RuntimeError("No playable stream found for this video.")
            master_url = auto[0]["url"]

            master_playlist = fetch_url(master_url).decode("utf-8")
            variants = parse_master_playlist(master_playlist, master_url)
            if not variants:
                raise RuntimeError("No quality variants found in master playlist.")
            best = max(variants, key=lambda v: v["bandwidth"])

            media_playlist = fetch_url(best["url"]).decode("utf-8")
            segments = parse_media_playlist(media_playlist, best["url"])
            if not segments:
                raise RuntimeError("No segments found in media playlist.")

            return title, segments
        except (
            OSError,
            http.client.HTTPException,
            urllib.error.URLError,
        ) as e:
            if attempt == MAX_RETRIES:
                raise
            print(f"Resolve error ({e}), retrying ({attempt}/{MAX_RETRIES})...")


def download_segment(url: str) -> bytes:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fetch_url(url, timeout=30)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                if attempt == MAX_RETRIES:
                    raise
                wait = RATE_LIMIT_BACKOFF_SECONDS * attempt
                print(f"\nRate limited (429), waiting {wait}s...")
                time.sleep(wait)
                continue
            raise
        except (
            IOError,
            http.client.IncompleteRead,
            http.client.HTTPException,
            socket.timeout,
            urllib.error.URLError,
        ) as e:
            if attempt == MAX_RETRIES:
                raise
            wait = RETRY_BACKOFF_SECONDS * attempt
            print(f"\nSegment error ({e}), retrying ({attempt}/{MAX_RETRIES})...")
            time.sleep(wait)


def download_segments(segments: list[str], dest_path: str) -> None:
    tmp_path = dest_path + ".part"
    total = len(segments)

    # Resume: if a .part file exists with fewer bytes than expected, we
    # can't know how many whole segments it holds reliably, so restart
    # cleanly rather than risk corrupting the stream.
    # Bounded window of in-flight futures keeps memory low while writing in order.
    with open(tmp_path, "wb") as f, ThreadPoolExecutor(DOWNLOAD_WORKERS) as pool:
        pending: deque = deque()
        next_idx = 0
        for i in range(1, total + 1):
            while next_idx < total and len(pending) < DOWNLOAD_WORKERS * 2:
                pending.append(pool.submit(download_segment, segments[next_idx]))
                next_idx += 1
            f.write(pending.popleft().result())
            percent = i * 100 / total
            print(f"\rSegment {i}/{total} ({percent:5.1f}%)", end="", flush=True)

    print()
    os.replace(tmp_path, dest_path)


def download_video(url_or_id: str, dest_path: str | None = None) -> str:
    """Resolve and download a single Dailymotion video.

    Returns the path the video was saved to (or already existed at).
    """
    title, segments = resolve_video_info(url_or_id)
    print(f"Title: {title}")
    print(f"Segments: {len(segments)}")

    if not dest_path:
        dest_path = sanitize_filename(title) + ".ts"

    if os.path.exists(dest_path):
        print(f"Skipping (already exists): {dest_path}")
        return dest_path

    print(f"Downloading to: {dest_path}")
    download_segments(segments, dest_path)
    print("Done.")
    return dest_path


def download_batch(urls: list[str], output_dir: str | None) -> int:
    out_dir = output_dir or "."
    os.makedirs(out_dir, exist_ok=True)

    failures = []
    for i, url in enumerate(urls, start=1):
        print(f"\n[{i}/{len(urls)}] {url}")
        try:
            title, segments = resolve_video_info(url)
            print(f"Title: {title}")
            print(f"Segments: {len(segments)}")

            dest_path = os.path.join(out_dir, sanitize_filename(title) + ".ts")
            if os.path.exists(dest_path):
                print(f"Skipping (already exists): {dest_path}")
                continue

            print(f"Downloading to: {dest_path}")
            download_segments(segments, dest_path)
            print("Done.")
        except Exception as e:
            print(f"Failed: {e}")
            failures.append(url)

    print(f"\nCompleted {len(urls) - len(failures)}/{len(urls)} downloads.")
    if failures:
        print("Failed URLs:")
        for url in failures:
            print(f"  {url}")
    return len(failures)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download one or more Dailymotion videos."
    )
    parser.add_argument("url", nargs="?", help="Dailymotion page URL or video id")
    parser.add_argument(
        "output", nargs="?", help="Output file path (single URL mode only)"
    )
    parser.add_argument(
        "-f", "--file", help="Text file with one Dailymotion URL per line"
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        help="Directory to save downloaded videos into (batch mode)",
    )
    args = parser.parse_args()

    if not args.url and not args.file:
        parser.print_usage()
        sys.exit(1)

    if args.file:
        urls = read_urls_from_file(args.file)
        if not urls:
            print(f"No URLs found in {args.file}")
            sys.exit(1)
        failures = download_batch(urls, args.output_dir)
        sys.exit(1 if failures else 0)

    try:
        download_video(args.url, args.output)
    except urllib.error.HTTPError as e:
        print(f"\nDownload failed: HTTP {e.code} {e.reason}")
        sys.exit(1)


if __name__ == "__main__":
    main()
