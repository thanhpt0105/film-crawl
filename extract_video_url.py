"""
Extract the direct streaming (CDN) URL for a single Odysee video page.

This uses Odysee's own public resolve API (the same one the web player uses)
to look up a claim's metadata, then builds the direct media URL in the same
format Odysee's own "Download" button produces. It does not bypass any
access control - it only works for content Odysee already serves publicly.

Usage:
    python extract_video_url.py "<odysee page url>"
"""
import sys
import json
import urllib.parse
import urllib.request

RESOLVE_API = "https://api.na-backend.odysee.com/api/v1/proxy"

# Odysee's CDN requires a browser-like User-Agent and a Referer/Origin
# matching the site, otherwise it responds with 401 Unauthorized.
CDN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://odysee.com/",
    "Origin": "https://odysee.com",
}


def parse_odysee_url(page_url: str) -> str:
    """Convert an odysee.com page URL into an lbry:// claim URL.

    Example:
      https://odysee.com/@LeoTV:8/Some-Title:f
      -> @LeoTV#8/Some-Title#f
    """
    parsed = urllib.parse.urlparse(page_url)
    path = urllib.parse.unquote(parsed.path.lstrip("/"))
    parts = path.split("/")
    if len(parts) < 2:
        raise ValueError(f"Unrecognized Odysee URL format: {page_url}")

    def to_claim(part: str) -> str:
        # "@LeoTV:8" -> "@LeoTV#8", "Some-Title:f" -> "Some-Title#f"
        if ":" in part:
            name, claim_id = part.rsplit(":", 1)
            return f"{name}#{claim_id}"
        return part

    return "/".join(to_claim(p) for p in parts)


def resolve_claim(lbry_url: str) -> dict:
    payload = json.dumps(
        {"method": "resolve", "params": {"urls": [lbry_url]}}
    ).encode("utf-8")
    req = urllib.request.Request(
        RESOLVE_API,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.load(resp)

    result = data.get("result", {}).get(lbry_url)
    if not result or "error" in result:
        raise RuntimeError(f"Could not resolve claim: {result}")
    return result


def build_stream_url(claim: dict) -> str:
    name = claim["name"]
    claim_id = claim["claim_id"]
    source = claim.get("value", {}).get("source", {})
    sd_hash = source.get("sd_hash", "")
    sd_prefix = sd_hash[:6]
    return (
        f"https://player.odycdn.com/api/v3/streams/free/"
        f"{urllib.parse.quote(name)}/{claim_id}/{sd_prefix}"
    )


def resolve_final_url(stream_url: str) -> str:
    """Follow redirects (with the required headers) to get the final CDN URL."""
    req = urllib.request.Request(stream_url, headers=CDN_HEADERS, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.geturl()
    except urllib.error.HTTPError as e:
        return e.geturl() if hasattr(e, "geturl") else stream_url


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python extract_video_url.py <odysee page url>")
        sys.exit(1)

    page_url = sys.argv[1]
    lbry_url = parse_odysee_url(page_url)
    print(f"Resolving: {lbry_url}")

    claim = resolve_claim(lbry_url)
    title = claim.get("value", {}).get("title", "(unknown title)")
    stream_url = build_stream_url(claim)
    final_url = resolve_final_url(stream_url)

    print(f"Title: {title}")
    print(f"Claim ID: {claim['claim_id']}")
    print(f"Direct video URL: {final_url}")
    print("\nNote: this URL requires a Referer/Origin of https://odysee.com and a")
    print("browser-like User-Agent header to be accepted by the CDN (401 otherwise).")


if __name__ == "__main__":
    main()
