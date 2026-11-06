import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

import requests

from client import PAGE_HEADERS, get_page_metadata


def safe_name(value):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value)).strip(" .")
    return name[:160] or "subtitle"


def download_page(session, url, output_dir, languages):
    metadata = get_page_metadata(session, url)
    subtitles = metadata["subtitles"]
    selected = [
        track for track in subtitles
        if not languages or str(track.get("code", "")).lower() in languages
    ]
    if not selected:
        raise ValueError("No subtitles found for the requested language(s).")

    show = safe_name(metadata["series_name"])
    number = metadata["episode_number"]
    episode = f"E{number:02d}" if number is not None else f"{metadata['product_id']}"
    output = Path(output_dir) / show
    output.mkdir(parents=True, exist_ok=True)

    for track in selected:
        language = safe_name(track.get("code") or track.get("name") or "und")
        variants = [(track.get("url"), ""), (track.get("second_subtitle_url"), ".secondary")]
        for track_url, suffix in variants:
            if not track_url:
                continue
            parsed_track = urlsplit(track_url)
            if parsed_track.scheme != "https" or parsed_track.hostname != "ott-resources.viu.com":
                raise ValueError("Viu returned an unexpected subtitle host.")

            target = output / f"{show}.{episode}.{language}{suffix}.srt"
            if target.exists():
                print(f"Skipping existing file: {target}")
                continue

            response = session.get(
                track_url,
                headers={**PAGE_HEADERS, "Referer": url},
                timeout=30,
            )
            response.raise_for_status()
            content = response.content.decode("utf-8-sig")
            if not re.search(r"\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->", content):
                raise ValueError(f"Subtitle response is not valid SRT: {track_url}")
            target.write_text(content, encoding="utf-8")
            print(f"Downloaded: {target}")


def read_urls(args):
    urls = list(args.urls)
    if args.url_file:
        lines = Path(args.url_file).read_text(encoding="utf-8-sig").splitlines()
        urls.extend(line.strip() for line in lines if line.strip() and not line.strip().startswith("#"))
    return list(dict.fromkeys(urls))


def main():
    parser = argparse.ArgumentParser(description="Download subtitles from Viu episode pages.")
    parser.add_argument("urls", nargs="*", help="Viu episode URLs")
    parser.add_argument("--url-file", help="Text file with one Viu episode URL per line")
    parser.add_argument("--output", default="Downloads", help="Output directory")
    parser.add_argument("--lang", action="append", help="Subtitle code to download; repeat for multiple languages")
    args = parser.parse_args()

    try:
        urls = read_urls(args)
        if not urls:
            parser.error("Provide at least one URL or a non-empty --url-file.")
    except OSError as exc:
        print(f"Could not read URL file: {exc}", file=sys.stderr)
        return 1

    session = requests.Session()
    languages = {language.lower() for language in args.lang or []}
    failed = []
    for index, url in enumerate(urls, start=1):
        print(f"[{index}/{len(urls)}] {url}")
        try:
            download_page(session, url, args.output, languages)
        except (OSError, ValueError, KeyError, requests.RequestException) as exc:
            print(f"Subtitle download failed for {url}: {exc}", file=sys.stderr)
            failed.append(url)

    if failed:
        print(f"Failed: {len(failed)} of {len(urls)} URL(s).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
