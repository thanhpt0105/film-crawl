"""
Download an Odysee video given its page URL.

This reuses the resolution logic from extract_video_url.py to find the
direct CDN URL, then streams the video to a local file with a progress
indicator.

Usage:
    python download_video.py "<odysee page url>" [output_path]

If output_path is omitted, the file is saved in the current directory
using the video's title as the filename.
"""
import os
import re
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


def download_file(url: str, dest_path: str) -> None:
    req = urllib.request.Request(url, headers=CDN_HEADERS, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        total = resp.length or 0
        downloaded = 0

        tmp_path = dest_path + ".part"
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
                    print(f"\r{format_size(downloaded)} downloaded", end="", flush=True)

    os.replace(tmp_path, dest_path)
    print()


def main() -> None:
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python download_video.py <odysee page url> [output_path]")
        sys.exit(1)

    page_url = sys.argv[1]
    output_arg = sys.argv[2] if len(sys.argv) == 3 else None

    lbry_url = parse_odysee_url(page_url)
    print(f"Resolving: {lbry_url}")

    claim = resolve_claim(lbry_url)
    title = claim.get("value", {}).get("title") or claim["claim_id"]
    stream_url = build_stream_url(claim)
    final_url = resolve_final_url(stream_url)
    print(f"Title: {title}")
    print(f"Direct video URL: {final_url}")

    if output_arg:
        dest_path = output_arg
    else:
        dest_path = sanitize_filename(title) + guess_extension(final_url)

    print(f"Downloading to: {dest_path}")
    try:
        download_file(final_url, dest_path)
    except urllib.error.HTTPError as e:
        print(f"\nDownload failed: HTTP {e.code} {e.reason}")
        sys.exit(1)

    print("Done.")


if __name__ == "__main__":
    main()
