import json
from urllib.parse import urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

API_URL = "https://api-gateway-global.viu.com/api/mobile"
PAGE_HEADERS = {"User-Agent": "Mozilla/5.0"}


def parse_vod_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ("viu.com", "www.viu.com"):
        raise ValueError("URL must be an HTTPS Viu page.")

    parts = parsed.path.strip("/").split("/")
    if len(parts) != 6 or parts[0] != "ott" or parts[3] != "vod" or not parts[4].isdigit():
        raise ValueError("Expected a Viu URL like /ott/sg/en/vod/2428843/Title.")
    return parsed, parts


def get_page_metadata(session, url):
    parsed, parts = parse_vod_url(url)
    response = session.get(url, headers=PAGE_HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    next_data = soup.find("script", id="__NEXT_DATA__")
    if not next_data or not next_data.string:
        raise ValueError("Viu page data not found.")

    page = json.loads(next_data.string).get("props", {}).get("pageProps", {})
    fallback = page.get("fallback", {})
    detail = next(
        (
            value.get("data")
            for value in fallback.values()
            if isinstance(value, dict)
            and isinstance(value.get("data"), dict)
            and isinstance(value["data"].get("current_product"), dict)
            and isinstance(value["data"].get("series"), dict)
        ),
        None,
    )
    if not detail:
        raise ValueError("Viu product details were not present in the page.")

    product = detail["current_product"]
    series = detail["series"]
    try:
        episode_number = int(product.get("number"))
    except (TypeError, ValueError):
        episode_number = None

    return {
        "product_id": str(product.get("product_id") or parts[4]),
        "series_id": str(series.get("series_id") or ""),
        "series_name": str(series.get("name") or product.get("seo_title") or parts[5]),
        "episode_number": episode_number,
        "subtitles": product.get("subtitle") or [],
    }


def get_episode_products(session, series_id, referer=None):
    if not str(series_id).isdigit():
        raise ValueError("Viu series ID is missing or invalid.")

    response = session.get(
        API_URL,
        params={
            "r": "/vod/product-list",
            "os_flag_id": 1,
            "series_id": str(series_id),
            "size": -1,
            "sort": "desc",
        },
        headers={**PAGE_HEADERS, **({"Referer": referer} if referer else {})},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("status", {}).get("code") != 0:
        raise ValueError(f"Viu episode-list API returned: {payload.get('status')}")

    items = payload.get("data", {}).get("product_list", [])
    unique = {str(item["product_id"]): item for item in items if item.get("product_id")}
    return sorted(unique.values(), key=lambda item: int(item.get("number") or 0))


def episode_url(url, product_id):
    parsed, parts = parse_vod_url(url)
    parts[4] = str(product_id)
    path = "/" + "/".join(parts)
    return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, ""))
