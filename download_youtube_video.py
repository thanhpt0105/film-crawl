"""
Download a YouTube video given its page URL.

YouTube requires deciphering per-video signature/cipher logic to build
working stream URLs, and this logic changes frequently. Reimplementing it
from scratch is impractical, so this script uses the well-maintained
yt-dlp library (https://github.com/yt-dlp/yt-dlp) to do the extraction
and download, while keeping the same command-line interface as the other
scripts in this repo (single URL, or batch via -f/-o).

Requirements:
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install yt-dlp

Usage:
    # Single video
    python download_youtube_video.py "<youtube url>" [output_path]

    # Multiple videos listed in a text file (one URL per line, blank
    # lines and lines starting with # are ignored)
    python download_youtube_video.py -f urls.txt [-o output_dir]

If output_path/output_dir is omitted, files are saved in the current
directory using the video's title as the filename.

To reduce the chance of YouTube throttling/blocking requests as automated
traffic, batch mode waits between downloads and retries with backoff on
failure.
"""
import argparse
import os
import re
import sys
import time

try:
    import yt_dlp
except ImportError:
    print("This script requires yt-dlp. Install it with:")
    print("    python -m pip install yt-dlp")
    sys.exit(1)

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 15
BATCH_DELAY_SECONDS = 10


def sanitize_filename(name: str) -> str:
    """Strip characters that are invalid in filenames on Windows/Unix."""
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = name.strip().strip(".")
    return name or "video"


def read_urls_from_file(path: str) -> list[str]:
    urls = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def format_size(num_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f}{unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f}TB"


def make_progress_hook():
    def hook(status: dict) -> None:
        if status["status"] == "downloading":
            downloaded = status.get("downloaded_bytes") or 0
            total = status.get("total_bytes") or status.get("total_bytes_estimate")
            if total:
                percent = downloaded * 100 / total
                print(
                    f"\r{format_size(downloaded)} / {format_size(total)} "
                    f"({percent:5.1f}%)",
                    end="",
                    flush=True,
                )
            else:
                print(f"\r{format_size(downloaded)} downloaded", end="", flush=True)
        elif status["status"] == "finished":
            print()

    return hook


def fetch_title(url: str) -> str:
    """Look up the video title without downloading, so it can be checked
    before committing to the download.
    """
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info.get("title") or url


def download_video(url: str, dest_path: str | None = None) -> str:
    """Resolve and download a single YouTube video.

    Returns the path the video was saved to (or already existed at).
    """
    title = fetch_title(url)
    print(f"Title: {title}")

    if dest_path:
        out_template = dest_path
        final_guess = dest_path
    else:
        out_template = sanitize_filename(title) + ".%(ext)s"
        final_guess = sanitize_filename(title) + ".mp4"

    if os.path.exists(final_guess):
        print(f"Skipping (already exists): {final_guess}")
        return final_guess

    opts = {
        "outtmpl": out_template,
        "format": (
            "best[acodec!=none][vcodec!=none][ext=mp4]/"
            "best[acodec!=none][vcodec!=none]"
        ),
        "progress_hooks": [make_progress_hook()],
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
    }

    print(f"Downloading to: {final_guess}")
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            break
        except yt_dlp.utils.DownloadError as e:
            if attempt == MAX_RETRIES:
                raise
            wait = RETRY_BACKOFF_SECONDS * attempt
            print(
                f"\nDownload error ({e}), waiting {wait}s before retrying "
                f"({attempt}/{MAX_RETRIES})..."
            )
            time.sleep(wait)
    print("Done.")
    return final_guess


def download_batch(urls: list[str], output_dir: str | None) -> int:
    out_dir = output_dir or "."
    os.makedirs(out_dir, exist_ok=True)

    failures = []
    downloaded_count = 0
    for i, url in enumerate(urls, start=1):
        print(f"\n[{i}/{len(urls)}] {url}")

        try:
            title = fetch_title(url)
            print(f"Title: {title}")

            dest_path = os.path.join(out_dir, sanitize_filename(title) + ".mp4")
            if os.path.exists(dest_path):
                print(f"Skipping (already exists): {dest_path}")
                continue

            if downloaded_count > 0:
                print(f"Waiting {BATCH_DELAY_SECONDS}s before next download...")
                time.sleep(BATCH_DELAY_SECONDS)

            out_template = os.path.join(out_dir, sanitize_filename(title) + ".%(ext)s")
            opts = {
                "outtmpl": out_template,
                "format": (
                    "best[acodec!=none][vcodec!=none][ext=mp4]/"
                    "best[acodec!=none][vcodec!=none]"
                ),
                "progress_hooks": [make_progress_hook()],
                "quiet": True,
                "no_warnings": True,
                "noprogress": True,
            }

            print(f"Downloading to: {dest_path}")
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        ydl.download([url])
                    break
                except yt_dlp.utils.DownloadError as e:
                    if attempt == MAX_RETRIES:
                        raise
                    wait = RETRY_BACKOFF_SECONDS * attempt
                    print(
                        f"\nDownload error ({e}), waiting {wait}s before "
                        f"retrying ({attempt}/{MAX_RETRIES})..."
                    )
                    time.sleep(wait)
            print("Done.")
            downloaded_count += 1
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
    parser = argparse.ArgumentParser(description="Download one or more YouTube videos.")
    parser.add_argument("url", nargs="?", help="YouTube video URL")
    parser.add_argument(
        "output", nargs="?", help="Output file path (single URL mode only)"
    )
    parser.add_argument(
        "-f", "--file", help="Text file with one YouTube URL per line"
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
    except Exception as e:
        print(f"\nDownload failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
