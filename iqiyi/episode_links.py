import argparse
import sys
from pathlib import Path

from modules.cookies import load_cookies
from modules.iq import create_scraper, extract_data, fetch_html, get_album_id

PLAY_BASE = "https://www.iq.com/play/"
API_URL = "https://pcw-api.iq.com/api/v2/episodeListSource/{album_id}"


def is_episode(entry):
    # Trailers/clips come back in the same list with episodeType 6 / contentType 31.
    return "playLocSuffix" in entry and entry.get("contentType", 1) == 1 and entry.get("episodeType") != 6


def episodes_from_api(album_id, lang):
    params = {
        "platformId": "3",
        "modeCode": "my",
        "langCode": lang,
        "startOrder": "0",
        "endOrder": "10000",
    }
    headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = create_scraper().get(API_URL.format(album_id=album_id), headers=headers, params=params)
    response.raise_for_status()
    return response.json().get("data", {}).get("epg", [])


def episodes_from_page(html):
    # The page only embeds the first page (up to 30) of episodes.
    pages = extract_data(html, ["props", "initialState", "play", "cachePlayList"]) or {}
    return [entry for page in pages.values() for entry in page]


def get_episode_links(url, lang, cookies):
    html = fetch_html(url, 600, lang, cookies)
    entries = []
    try:
        album_id = get_album_id(html)
        if album_id:
            entries = episodes_from_api(album_id, lang)
    except Exception as e:
        print(f"API lookup failed ({e}); falling back to page data.", file=sys.stderr)

    if not any(is_episode(e) for e in entries):
        entries = episodes_from_page(html)

    episodes = {}
    for entry in entries:
        if is_episode(entry):
            episodes[entry.get("order", len(episodes) + 1)] = PLAY_BASE + entry["playLocSuffix"]
    return [episodes[order] for order in sorted(episodes)]


def main():
    parser = argparse.ArgumentParser(description="List all episode links of an iQIYI series from one episode URL.")
    parser.add_argument("url", help="Any episode URL of the series.")
    parser.add_argument("--lang", default="en_us", help="Language code (default: en_us).")
    parser.add_argument("--cookies", default="cookies/cookies.txt", help="Cookies file (default: cookies/cookies.txt).")
    parser.add_argument("--out", help="Write links to this file (e.g. urls.txt) instead of only printing.")
    args = parser.parse_args()

    links = get_episode_links(args.url.replace("album", "play"), args.lang, load_cookies(args.cookies))
    if not links:
        raise SystemExit("No episodes found.")

    print("\n".join(links))
    if args.out:
        Path(args.out).write_text("\n".join(links) + "\n", encoding="utf-8")
        print(f"\nSaved {len(links)} link(s) to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
