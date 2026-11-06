import http.cookiejar
import re
import os
import json
import signal
import shutil
import requests
import cloudscraper
import sys
import zipfile
import tempfile
import subprocess
from modules.logging import setup_logging
from bs4 import BeautifulSoup

logger = setup_logging("IQ")

# ===================================================================================================================================================== #

def create_scraper():
    """Create a cloudscraper instance."""
    return cloudscraper.create_scraper()

# ===================================================================================================================================================== #

def parse_json_from_html(html, element_id):
    """Parse JSON data embedded in a script tag from HTML."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        script_content = soup.find("script", {"id": element_id}).text
        return json.loads(script_content)
    except Exception as e:
        logger.error(f"Error parsing JSON from HTML: {e}")
        return None

# ===================================================================================================================================================== #

def extract_data(html, key_path):
    """Extract nested data from parsed JSON using a key path."""
    data = parse_json_from_html(html, "__NEXT_DATA__")
    try:
        for key in key_path:
            data = data[key]
        return data
    except KeyError as e:
        logger.error(f"Key not found in JSON: {e} skipping...")
        return None

# ===================================================================================================================================================== #

def get_video_m3u8(html):
    """Extract and save the m3u8 link from HTML."""
    videos = extract_data(html, ["props", "initialProps", "pageProps", "prePlayerData", "dash", "data", "program", "video"])
    if videos:
        for video in videos:
            if "m3u8" in video:
                with open("temp.m3u8", "w") as file:
                    file.write(video["m3u8"])
                logger.info("Saved m3u8 file to temp.m3u8")
                return video["m3u8"]
    logger.warning("No m3u8 link found.")
    return None

# ===================================================================================================================================================== #

def fetch_html(url, res, lang, cookies):
    """Fetch HTML content from the URL with updated cookies."""
    cookies = dict(cookies or {})
    cookies.update({'lang': lang, 'QiyiPlayerBID': str(res)})
    scraper = create_scraper()
    try:
        response = scraper.get(url, cookies=cookies)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.error(f"Error fetching URL: {e}")
        raise
        
# ===================================================================================================================================================== #

def get_album_id(base_html):
    next_data = json.loads(BeautifulSoup(base_html, features="html.parser").find("script", {"id": "__NEXT_DATA__"}).text)
    return str(next_data['props']['initialState']['album']['videoAlbumInfo']['albumId'])

# ===================================================================================================================================================== #

def get_episodes(html, lang):
    album_id = get_album_id(html)
    if not album_id:
        return []
    
    url = f"https://pcw-api.iq.com/api/v2/episodeListSource/{album_id}"
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "x-forwarded-for": "82.102.19.66"
    }
    params = {
        "platformId": "3",
        "modeCode": "my",
        "langCode": lang,
        "startOrder": "0",
        "endOrder": "10000"
    }
    scraper = create_scraper()
    try:
        response = scraper.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return [f"https://www.iq.com/play/{e['playLocSuffix']}" for e in data.get("data", {}).get("epg", []) if "playLocSuffix" in e]
    except Exception as e:
        response_text = ""
        status_code = "unknown"
        content_type = "unknown"
        if 'response' in locals():
            status_code = response.status_code
            content_type = response.headers.get("Content-Type", "unknown")
            response_text = response.text[:200].replace("\n", " ")
        logger.error(
            f"Failed to retrieve episodes: {e}. status={status_code}, content_type={content_type}, body_preview={response_text}"
        )
        return []

# ===================================================================================================================================================== #

def get_series_title(base_html):
    try:
        return BeautifulSoup(base_html, features="html.parser").find("span", {"class": "intl-album-title-word-wrap"}).find('span').text
    except Exception as e:
        logger.error(f'Failed to get series title {e}')

# ===================================================================================================================================================== #

def get_album_id(html):
    """Extract album ID from HTML."""
    return extract_data(html, ["props", "initialState", "album", "videoAlbumInfo", "albumId"])

# ===================================================================================================================================================== #

def get_title(html):
    """Extract title from HTML."""
    try:
        return BeautifulSoup(html, "html.parser").find("p", {"class": "intl-play-title"}).text
    except Exception:
        raise ValueError("Failed to get title (wrong URL?)")


# ===================================================================================================================================================== #

def slugify(value):
    """Slugify a string for safe file naming."""
    value = str(value)
    value = re.sub(r"[^\w\s-]", "", value)
    return re.sub(r"[-\s]+", ".", value).strip("-_")

# ===================================================================================================================================================== #

TOOLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")


def _fetch_release_binary(repo, asset_match, exe_name):
    """Download a GitHub release zip and extract exe_name into TOOLS_DIR."""
    release = requests.get(f"https://api.github.com/repos/{repo}/releases/latest", timeout=30)
    release.raise_for_status()
    asset = next((a for a in release.json()["assets"] if asset_match(a["name"])), None)
    if not asset:
        raise FileNotFoundError(f"No matching release asset found in {repo}.")

    logger.info(f"Downloading {asset['name']} from {repo}...")
    os.makedirs(TOOLS_DIR, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = os.path.join(tmp, asset["name"])
        with requests.get(asset["browser_download_url"], stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    f.write(chunk)
        with zipfile.ZipFile(zip_path) as z:
            member = next((m for m in z.namelist() if os.path.basename(m).lower() == exe_name.lower()), None)
            if not member:
                raise FileNotFoundError(f"{exe_name} not found inside {asset['name']}.")
            with z.open(member) as src, open(os.path.join(TOOLS_DIR, exe_name), "wb") as dst:
                shutil.copyfileobj(src, dst)


def ensure_tools():
    """Return the N_m3u8DL-RE path, downloading it and ffmpeg into tools/ if missing."""
    os.environ["PATH"] = TOOLS_DIR + os.pathsep + os.environ.get("PATH", "")

    downloader = shutil.which("N_m3u8DL-RE") or shutil.which("re")
    if not shutil.which("ffmpeg") or not downloader:
        if sys.platform != "win32":
            raise FileNotFoundError("N_m3u8DL-RE and ffmpeg must be installed and on PATH.")

    if not downloader:
        _fetch_release_binary(
            "nilaoda/N_m3u8DL-RE",
            lambda n: "win-x64" in n and n.endswith(".zip"),
            "N_m3u8DL-RE.exe",
        )
        downloader = shutil.which("N_m3u8DL-RE")
    if not shutil.which("ffmpeg"):
        _fetch_release_binary(
            "BtbN/FFmpeg-Builds",
            lambda n: n == "ffmpeg-master-latest-win64-gpl.zip",
            "ffmpeg.exe",
        )
    return downloader


def media_exists(foldername, filename):
    """True if a non-empty video for this title is already in Downloads/."""
    base = os.path.join("Downloads", slugify(foldername), slugify(filename))
    return any(os.path.exists(base + ext) and os.path.getsize(base + ext) > 0 for ext in (".mp4", ".mkv"))


def download_media(foldername, filename):
    if media_exists(foldername, filename):
        logger.info(f"Skipping, file already exists: {filename}")
        return

    foldername, filename = slugify(foldername), slugify(filename)
    os.makedirs(f"Downloads/{foldername}", exist_ok=True)

    downloader = ensure_tools()
    if not downloader:
        raise FileNotFoundError("N_m3u8DL-RE could not be located or downloaded.")

    if not os.path.exists("./temp.m3u8"):
        raise FileNotFoundError("temp.m3u8 was not created. No downloadable m3u8 source was found.")

    command = [
        downloader,
        "--save-dir", f"Downloads/{foldername}",
        "--tmp-dir", "Temp/",
        "--save-name", filename,
        "--download-retry-count", "5",
        "./temp.m3u8",
        "-M", "mp4"
    ]
    logger.info(f"Downloading {filename}...")
    subprocess.run(command, check=True)
    os.remove("./temp.m3u8")

# ===================================================================================================================================================== #

def download_subtitles(html, foldername, filename):
    """Download subtitles from HTML."""
    subtitles = extract_data(html, ["props", "initialProps", "pageProps", "prePlayerData", "dash", "data", "program", "stl"])
    if not subtitles:
        logger.warning("No subtitles found.")
        return

    foldername, filename = slugify(foldername), slugify(filename)
    os.makedirs(f"Downloads/{foldername}", exist_ok=True)
    for subtitle in subtitles:
        lang = subtitle["_name"]
        sub_url = f"https://meta.video.iqiyi.com{subtitle['srt']}"
        sub_path = f"./Downloads/{foldername}/{filename}.{lang}.srt"

        if os.path.exists(sub_path) and os.path.getsize(sub_path) > 0:
            logger.info(f"Skipping, subtitle already exists: {sub_path}")
            continue

        response = create_scraper().get(sub_url)
        response.raise_for_status()
        with open(sub_path, "w", encoding="utf-8") as file:
            file.write(response.text)
        logger.info(f"Downloaded subtitle: {sub_path}")