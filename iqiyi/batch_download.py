import argparse
from pathlib import Path
import time

from colorama import Fore, Style, init

from modules.banners import banners, clear_screen
from modules.cookies import load_cookies
from modules.iq import (
    download_media,
    download_subtitles,
    fetch_html,
    get_episodes,
    get_series_title,
    get_title,
    get_video_m3u8,
    media_exists,
)
from modules.logging import setup_logging


# Initialize Colorama
init(autoreset=True)
logger = setup_logging("MAIN_BATCH")


LANGUAGE_MAP = {
    "en": "en_us",
    "english": "en_us",
    "zh-cn": "zh_cn",
    "zh-tw": "zh_tw",
    "id": "id_id",
    "ms": "ms_my",
    "th": "th_th",
    "vi": "vi_vn",
    "ja": "ja",
    "pt": "pt_br",
    "es": "es_mx",
}

RESOLUTION_MAP = {
    "1080p": 600,
    "720p": 400,
    "480p": 300,
    "360p": 200,
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Batch downloader for media URLs listed in a text file."
    )
    parser.add_argument(
        "--url-file",
        default="urls.txt",
        help="Path to a text file containing one URL per line (default: urls.txt).",
    )
    parser.add_argument(
        "--lang",
        default="en",
        help=(
            "Subtitle language (default: en). "
            "Supported: en, zh-cn, zh-tw, id, ms, th, vi, ja, pt, es."
        ),
    )
    parser.add_argument(
        "--resolution",
        default="1080p",
        choices=list(RESOLUTION_MAP.keys()),
        help="Video resolution (default: 1080p).",
    )
    parser.add_argument(
        "--subtitles-only",
        action="store_true",
        help="Download subtitles only (skip video download).",
    )
    parser.add_argument(
        "--download-series",
        action="store_true",
        help="If URL belongs to a series, download all episodes.",
    )
    parser.add_argument(
        "--cookies",
        default="cookies/cookies.txt",
        help="Path to cookies file (default: cookies/cookies.txt).",
    )
    parser.add_argument(
        "--download-delay",
        type=float,
        default=3.0,
        help="Delay in seconds before each download starts (default: 3).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Retries per URL/episode after a failure (default: 3).",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=5.0,
        help="Base delay in seconds between retries, doubled each attempt (default: 5).",
    )
    return parser.parse_args()


def normalize_lang(lang: str) -> str:
    key = lang.strip().lower()
    normalized = LANGUAGE_MAP.get(key)
    if normalized:
        return normalized

    # Allow direct internal values such as en_us, zh_cn, etc.
    if "_" in key:
        return key

    raise ValueError(
        "Unsupported language value. Use one of: "
        "en, zh-cn, zh-tw, id, ms, th, vi, ja, pt, es "
        "or internal values like en_us."
    )


def read_urls(url_file: str):
    path = Path(url_file)
    if not path.exists():
        raise FileNotFoundError(f"URL file not found: {url_file}")

    urls = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        urls.append(entry.replace("album", "play"))

    if not urls:
        raise ValueError("No valid URLs found in URL file.")
    return urls


def with_retries(action, label: str, retries: int, retry_delay: float):
    """Run action(); on failure retry with exponential backoff, then re-raise."""
    for attempt in range(retries + 1):
        try:
            return action()
        except Exception as exc:
            if attempt == retries:
                raise
            wait = retry_delay * (2 ** attempt)
            logger.warning(f"{label} failed ({exc}); retry {attempt + 1}/{retries} in {wait:.0f}s")
            time.sleep(wait)


def download_one_page(page_html: str, folder_title: str, subtitles_only: bool, download_delay: float):
    title = get_title(page_html)
    need_video = not subtitles_only and not media_exists(folder_title, title)
    if not subtitles_only and not need_video:
        logger.info(f"Skipping video, file already exists: {title}")

    if need_video and download_delay > 0:
        print(
            f"{Fore.YELLOW}Waiting {download_delay:.1f}s before download...{Style.RESET_ALL}"
        )
        time.sleep(download_delay)

    if need_video:
        get_video_m3u8(page_html)
        download_media(folder_title, title)
    download_subtitles(page_html, folder_title, title)


def process_url(
    url: str,
    cookies,
    lang: str,
    res: int,
    subtitles_only: bool,
    download_series: bool,
    download_delay: float,
    retries: int,
    retry_delay: float,
):
    logger.info(f"Processing URL: {url}")
    page_html = with_retries(lambda: fetch_html(url, res, lang, cookies), "Fetch page", retries, retry_delay)
    episodes = get_episodes(page_html, lang)

    if episodes and download_series:
        series_title = get_series_title(page_html)
        print(f"{Fore.YELLOW}Series Title: {Fore.WHITE}{series_title}{Style.RESET_ALL}")
        failed = []
        for idx, episode_url in enumerate(episodes, start=1):
            print(
                f"{Fore.CYAN}[{idx}/{len(episodes)}] Downloading episode page: "
                f"{Fore.WHITE}{episode_url}{Style.RESET_ALL}"
            )

            def run(episode_url=episode_url):
                episode_html = fetch_html(episode_url, res, lang, cookies)
                download_one_page(episode_html, series_title, subtitles_only, download_delay)

            try:
                with_retries(run, f"Episode {idx}", retries, retry_delay)
            except Exception as exc:
                logger.error(f"Episode {idx} failed after {retries} retries: {exc}")
                failed.append(episode_url)
        if failed:
            raise RuntimeError(f"{len(failed)} episode(s) failed: " + ", ".join(failed))
    else:
        title = get_title(page_html)
        folder_title = get_series_title(page_html) if episodes else title
        with_retries(
            lambda: download_one_page(page_html, folder_title, subtitles_only, download_delay),
            "Download",
            retries,
            retry_delay,
        )


def main():
    clear_screen()
    banners()

    args = parse_args()

    try:
        lang = normalize_lang(args.lang)
        res = RESOLUTION_MAP[args.resolution]
        urls = read_urls(args.url_file)

        print(f"\n{Fore.GREEN}Language:{Style.RESET_ALL} {lang}")
        print(f"{Fore.GREEN}Resolution:{Style.RESET_ALL} {args.resolution}")
        print(f"{Fore.GREEN}Mode:{Style.RESET_ALL} {'Subtitles only' if args.subtitles_only else 'Video + Subtitles'}")
        print(f"{Fore.GREEN}Pre-download delay:{Style.RESET_ALL} {args.download_delay:.1f}s")
        print(f"{Fore.GREEN}URLs loaded:{Style.RESET_ALL} {len(urls)}")

        cookies = load_cookies(args.cookies)
        failed_urls = []
        for idx, url in enumerate(urls, start=1):
            print(f"\n{Fore.MAGENTA}=== [{idx}/{len(urls)}] {url} ==={Style.RESET_ALL}")
            try:
                process_url(
                    url,
                    cookies,
                    lang,
                    res,
                    args.subtitles_only,
                    args.download_series,
                    args.download_delay,
                    args.retries,
                    args.retry_delay,
                )
            except Exception as exc:
                logger.error(f"Failed: {url}: {exc}")
                failed_urls.append(url)

        if failed_urls:
            print(f"\n{Fore.RED}{len(failed_urls)} URL(s) failed:{Style.RESET_ALL}")
            for url in failed_urls:
                print(f"- {url}")
        else:
            print(f"\n{Fore.GREEN}All downloads completed.{Style.RESET_ALL}")
    except Exception as exc:
        logger.error(f"Batch download failed: {exc}")
        print(f"\n{Fore.RED}Batch download failed: {exc}{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
