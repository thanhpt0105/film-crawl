"""
Download one or more Odysee videos given their page URL(s).

This reuses the resolution logic from extract_video_url.py to find the
direct CDN URL for each video, then streams it to a local file with a
progress indicator.

Usage:
    # Single video
    python download_video.py "<odysee page url>" [output_path]

    # Multiple videos listed in a text file (one URL per line, blank
    # lines and lines starting with # are ignored)
    python download_video.py -f urls.txt [-o output_dir]

If output_path/output_dir is omitted, files are saved in the current
directory using each video's title as the filename.
"""
import argparse
import http.client
import os
import re
import socket
import sys
import urllib.error
import urllib.request

from extract_video_url import (
    CDN_HEADERS,
    build_stream_url,
    parse_odysee_url,
    resolve_claim,
    resolve_final_url,
)

CHUNK_SIZE = 1024 * 256  # 256 KB
MAX_RETRIES = 3


def sanitize_filename(name: str) -> str:
    """Strip characters that are invalid in filenames on Windows/Unix."""
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = name.strip().strip(".")
    return name or "video"


def guess_extension(url: str) -> str:
    path = url.split("?", 1)[0]
    ext = os.path.splitext(path)[1]
    return ext if ext else ".mp4"


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


def download_file(url: str, dest_path: str) -> None:
    tmp_path = dest_path + ".part"

    for attempt in range(1, MAX_RETRIES + 1):
        req = urllib.request.Request(url, headers=CDN_HEADERS, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                total = resp.length or 0
                downloaded = 0

                with open(tmp_path, "wb") as f:
                    while True:
                        chunk = resp.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total:
                            percent = downloaded * 100 / total
                            print(
                                f"\r{format_size(downloaded)} / {format_size(total)} "
                                f"({percent:5.1f}%)",
                                end="",
                                flush=True,
                            )
                        else:
                            print(
                                f"\r{format_size(downloaded)} downloaded",
                                end="",
                                flush=True,
                            )

            print()
            if total and downloaded != total:
                raise IOError(
                    f"Incomplete download: got {downloaded} of {total} bytes"
                )

            os.replace(tmp_path, dest_path)
            return
        except (
            IOError,
            http.client.IncompleteRead,
            http.client.HTTPException,
            socket.timeout,
            urllib.error.URLError,
        ) as e:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if attempt == MAX_RETRIES:
                raise
            print(f"\nDownload error ({e}), retrying ({attempt}/{MAX_RETRIES})...")


def resolve_video_info(page_url: str) -> tuple[str, str]:
    """Resolve a page URL to (title, direct CDN url), retrying on transient
    network errors (e.g. DNS hiccups).
    """
    lbry_url = parse_odysee_url(page_url)
    print(f"Resolving: {lbry_url}")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            claim = resolve_claim(lbry_url)
            title = claim.get("value", {}).get("title") or claim["claim_id"]
            stream_url = build_stream_url(claim)
            final_url = resolve_final_url(stream_url)
            return title, final_url
        except (
            OSError,
            http.client.HTTPException,
            urllib.error.URLError,
        ) as e:
            if attempt == MAX_RETRIES:
                raise
            print(f"Resolve error ({e}), retrying ({attempt}/{MAX_RETRIES})...")


def download_video(page_url: str, dest_path: str | None = None) -> str:
    """Resolve and download a single Odysee video page URL.

    Returns the path the video was saved to (or already existed at).
    """
    title, final_url = resolve_video_info(page_url)
    print(f"Title: {title}")
    print(f"Direct video URL: {final_url}")

    if not dest_path:
        dest_path = sanitize_filename(title) + guess_extension(final_url)

    if os.path.exists(dest_path):
        print(f"Skipping (already exists): {dest_path}")
        return dest_path

    print(f"Downloading to: {dest_path}")
    download_file(final_url, dest_path)
    print("Done.")
    return dest_path


def download_batch(urls: list[str], output_dir: str | None) -> int:
    """Download every URL in the list, continuing past individual failures.

    Returns the number of failures.
    """
    out_dir = output_dir or "."
    os.makedirs(out_dir, exist_ok=True)

    failures = []
    for i, url in enumerate(urls, start=1):
        print(f"\n[{i}/{len(urls)}] {url}")
        try:
            title, final_url = resolve_video_info(url)
            print(f"Title: {title}")

            dest_path = os.path.join(
                out_dir, sanitize_filename(title) + guess_extension(final_url)
            )
            if os.path.exists(dest_path):
                print(f"Skipping (already exists): {dest_path}")
                continue

            print(f"Downloading to: {dest_path}")
            download_file(final_url, dest_path)
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
    parser = argparse.ArgumentParser(description="Download one or more Odysee videos.")
    parser.add_argument("url", nargs="?", help="Odysee page URL")
    parser.add_argument(
        "output", nargs="?", help="Output file path (single URL mode only)"
    )
    parser.add_argument(
        "-f", "--file", help="Text file with one Odysee page URL per line"
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
