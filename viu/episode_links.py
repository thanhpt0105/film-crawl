import argparse
import sys
from pathlib import Path

import requests

from client import get_episode_products, get_page_metadata, episode_url


def get_episode_links(session, url):
    metadata = get_page_metadata(session, url)
    products = get_episode_products(session, metadata["series_id"], referer=url)
    if not products:
        raise ValueError("Viu returned no episodes for this series.")
    return [episode_url(url, product["product_id"]) for product in products]


def main():
    parser = argparse.ArgumentParser(description="List all episode URLs for a Viu series.")
    parser.add_argument("url", help="Any Viu episode URL in the series")
    parser.add_argument("--out", help="Write links to a file instead of printing")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output file")
    args = parser.parse_args()

    try:
        output = Path(args.out) if args.out else None
        if output and output.exists() and not args.force:
            raise FileExistsError(f"Output file already exists: {output}; use --force to overwrite it.")
        links = get_episode_links(requests.Session(), args.url)
        if output:
            with output.open("w" if args.force else "x", encoding="utf-8") as file:
                file.write("\n".join(links) + "\n")
            print(f"Saved {len(links)} episode link(s) to {output}", file=sys.stderr)
        else:
            print("\n".join(links))
    except (OSError, ValueError, KeyError, requests.RequestException) as exc:
        print(f"Could not retrieve Viu episode links: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
