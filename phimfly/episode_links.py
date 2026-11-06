import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

import requests

from main import load_session


def episode_metadata(html):
    match = re.search(r'type:"data",data:\{title:\{(.*?)\},uses:\{params:', html, re.DOTALL)
    if not match:
        raise ValueError("Episode data not found; check the URL, login and cookie file.")
    data = match.group(1)

    def field(name):
        value = re.search(r'(?:^|[,{}])' + re.escape(name) + r':("(?:[^"\\]|\\.)*"|void 0|null|\d+)', data)
        if not value:
            raise ValueError(f"Episode data is missing {name}.")
        return None if value.group(1) == "void 0" else json.loads(value.group(1))

    metadata = {name: field(name) for name in ("fid", "type", "number", "seasonFid", "prevTitleFid", "nextTitleFid")}
    if metadata["type"] != "episode" or not metadata["seasonFid"] or not isinstance(metadata["number"], int):
        raise ValueError("The page is not a season episode.")
    return metadata


def get_episode_links(session, url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ("phimfly.com", "www.phimfly.com"):
        raise ValueError("URL must be an HTTPS Phimfly watch page.")
    match = re.fullmatch(r"/watch/([A-Za-z0-9_-]+)/?", parsed.path)
    if not match:
        raise ValueError("URL must be an HTTPS Phimfly watch page.")

    def fetch(fid):
        if not isinstance(fid, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", fid):
            raise ValueError("Invalid episode ID in page data.")
        response = session.get(f"https://phimfly.com/watch/{fid}", timeout=30)
        response.raise_for_status()
        response.encoding = "utf-8"
        metadata = episode_metadata(response.text)
        if metadata["fid"] != fid:
            raise ValueError(f"Unexpected episode returned for {fid}.")
        return metadata

    initial = fetch(match.group(1))
    episodes = {initial["fid"]: initial}
    for direction in ("prevTitleFid", "nextTitleFid"):
        current = initial
        while current[direction]:
            fid = current[direction]
            if fid in episodes:
                raise ValueError(f"Episode navigation contains a cycle at {fid}.")
            current = fetch(fid)
            if current["seasonFid"] != initial["seasonFid"]:
                break
            episodes[fid] = current

    ordered = sorted(episodes.values(), key=lambda episode: episode["number"])
    return [f"https://phimfly.com/watch/{episode['fid']}" for episode in ordered]


def main():
    parser = argparse.ArgumentParser(description="Get Phimfly episode links for the current season.")
    parser.add_argument("url", help="Phimfly episode URL")
    parser.add_argument("--cookies", default="cookies/cookies.txt", help="Netscape-format cookies file")
    parser.add_argument("--out", help="Write links to a file")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output file")
    args = parser.parse_args()

    try:
        output = Path(args.out) if args.out else None
        if output and output.exists() and not args.force:
            raise FileExistsError(f"Output file already exists: {output}; use --force to overwrite it.")
        links = get_episode_links(load_session(args.cookies), args.url)
        if output:
            with output.open("w" if args.force else "x", encoding="utf-8") as file:
                file.write("\n".join(links) + "\n")
            print(f"Saved {len(links)} episode link(s) to {output}", file=sys.stderr)
        else:
            print("\n".join(links))
    except (OSError, ValueError, requests.RequestException) as exc:
        print(f"Could not retrieve episode links: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())