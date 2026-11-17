import argparse
import base64
import hashlib
import http.cookiejar
import re
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit

import json5
import requests
from bs4 import BeautifulSoup
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rename_sonarr import build_new_basename, extract_lang_token, sanitize_show_name


def load_session(cookie_file):
    cookies = http.cookiejar.MozillaCookieJar(str(cookie_file))
    cookies.load(ignore_discard=True, ignore_expires=False)
    session = requests.Session()
    session.cookies = cookies
    return session


def get_subtitles(html):
    match = re.search(r'["\'][^"\']*/getSubtitles/[^"\']*["\']\s*:\s*\{\s*v\s*:\s*(?=\[)', html)
    if not match:
        raise ValueError("Subtitle data not found; check the URL, login and cookie file.")
    subtitles = json5.loads(html[match.end():], consume_trailing=False)
    if not isinstance(subtitles, list):
        raise ValueError("Unexpected subtitle data format.")
    return subtitles


def decrypt_subtitle(filename, content):
    rotated = filename.translate(str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "TUVWXYZABCDEFGHIJKLMNOPQRStuvwxyzabcdefghijklmnopqrs",
    ))
    key = hashlib.sha256(f"/watch/{rotated}".encode("utf-8")).digest()
    encrypted = base64.b64decode(content, validate=True)
    try:
        return AESGCM(key).decrypt(encrypted[:12], encrypted[12:], None)
    except InvalidTag as exc:
        raise ValueError(f"Could not decrypt subtitle: {filename}") from exc


def safe_name(value):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
    return name[:160] or "subtitle"


def download_page(session, url, output_dir, languages, show=None, season=None, resolution="1080p"):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ("phimfly.com", "www.phimfly.com") or not parsed.path.startswith("/watch/"):
        raise ValueError("URL must be an HTTPS Phimfly watch page.")

    response = session.get(url, timeout=30)
    response.raise_for_status()
    response.encoding = "utf-8"
    subtitles = get_subtitles(response.text)
    selected = [sub for sub in subtitles if not languages or str(sub.get("language", "")).lower() in languages]
    if not selected:
        raise ValueError("No subtitles found for the requested language(s).")

    soup = BeautifulSoup(response.text, "html.parser")
    title = safe_name(soup.title.get_text(strip=True) if soup.title else parsed.path.rsplit("/", 1)[-1])
    match = re.fullmatch(r"(.+?)\s+-\s+[Ss](\d{1,2})[Ee](\d{1,3})", title)
    show_name = sanitize_show_name(show or (match.group(1).split(" - ", 1)[0] if match else ""))
    base = None
    if match and show_name:
        base = build_new_basename(show_name, season if season is not None else int(match.group(2)), int(match.group(3)), resolution)
    else:
        print(f"Could not infer Sonarr episode name from '{title}'; keeping original filenames.", file=sys.stderr)

    track_languages = [extract_lang_token(str(sub.get("language", "und"))) for sub in selected]
    separate_language_dirs = len({lang for lang in track_languages if lang}) > 1
    for subtitle in selected:
        filename = subtitle["fileName"]
        subtitle_id = str(subtitle["subsceneId"])
        if subtitle.get("rand"):
            subtitle_id += "~" + str(subtitle["rand"])
        endpoint = f"https://phimfly.com/api/subtitle/{quote(subtitle_id, safe='')}/{quote(filename, safe='')}"
        language = extract_lang_token(str(subtitle.get("language", "und")))
        if base and language and track_languages.count(language) == 1:
            output = Path(output_dir) / show_name
            target = output / language / f"{base}.{language}{Path(filename).suffix.lower()}" if separate_language_dirs else output / f"{base}.{language}{Path(filename).suffix.lower()}"
            alternate = output / f"{base}.{language}{Path(filename).suffix.lower()}" if separate_language_dirs else output / language / f"{base}.{language}{Path(filename).suffix.lower()}"
            if alternate.exists():
                target = alternate
        else:
            output = Path(output_dir) / title
            target = output / f"{safe_name(str(subtitle.get('language', 'und')))}.{subtitle['id']}.{safe_name(filename)}"
            if base:
                print(f"Could not safely name subtitle '{filename}'; keeping original filename.", file=sys.stderr)
        if target.exists():
            print(f"Skipping existing file: {target}")
            continue
        result = session.get(endpoint, timeout=30)
        result.raise_for_status()
        content = decrypt_subtitle(filename, result.text.strip())
        content.decode("utf-8")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        print(f"Downloaded: {target}")


def main():
    parser = argparse.ArgumentParser(description="Download subtitles from Phimfly episode pages.")
    parser.add_argument("urls", nargs="*", help="Phimfly episode URLs")
    parser.add_argument("--url-file", help="Text file with one episode URL per line")
    parser.add_argument("--cookies", default="cookies/cookies.txt", help="Netscape-format cookies file")
    parser.add_argument("--output", default="Downloads/Phimfly", help="Output directory")
    parser.add_argument("--lang", action="append", help="Language code to download; repeat for multiple languages")
    parser.add_argument("--show", help="Override the Sonarr show name")
    parser.add_argument("--season", type=int, help="Override the season number")
    parser.add_argument("--resolution", default="1080p", help="Sonarr quality tag (default: 1080p)")
    args = parser.parse_args()

    try:
        urls = list(args.urls)
        if args.url_file:
            lines = Path(args.url_file).read_text(encoding="utf-8-sig").splitlines()
            urls.extend(line.strip() for line in lines if line.strip() and not line.strip().startswith("#"))
        if not urls:
            parser.error("Provide at least one URL or a non-empty --url-file.")
        session = load_session(args.cookies)
    except (OSError, ValueError, KeyError, requests.RequestException) as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        return 1

    languages = {language.lower() for language in args.lang or []}
    failed = []
    for index, url in enumerate(urls, start=1):
        print(f"[{index}/{len(urls)}] {url}")
        try:
            download_page(session, url, args.output, languages, args.show, args.season, args.resolution)
        except (OSError, ValueError, KeyError, requests.RequestException) as exc:
            print(f"Subtitle download failed for {url}: {exc}", file=sys.stderr)
            failed.append(url)
    if failed:
        print(f"Failed: {len(failed)} of {len(urls)} URL(s).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())