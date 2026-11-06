import argparse
import re
from pathlib import Path


VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".ts"}
SUB_EXTS = {".srt", ".ass", ".vtt", ".sub"}

LANG_MAP = {
    "tieng anh": "en",
    "english": "en",
    "tieng viet": "vi",
    "vietnamese": "vi",
    "tieng indonesia": "id",
    "bahasa indonesia": "id",
    "indonesian": "id",
    "tieng malaysia": "ms",
    "bahasa malaysia": "ms",
    "malay": "ms",
    "tieng trung gian the": "zh-Hans",
    "chinese simplified": "zh-Hans",
    "simplified chinese": "zh-Hans",
    "tieng trung phon the": "zh-Hant",
    "chinese traditional": "zh-Hant",
    "traditional chinese": "zh-Hant",
    "arabic": "ar",
    "french": "fr",
    "japanese": "ja",
    "korean": "ko",
    "portuguese": "pt",
    "spanish": "es",
    "thai": "th",
}


def sanitize_show_name(name: str) -> str:
    name = name.strip().replace(" ", ".")
    name = re.sub(r"[^A-Za-z0-9.\-]+", ".", name)
    name = re.sub(r"\.+", ".", name)
    return name.strip(".")


def strip_accents(text: str) -> str:
    replacements = {
        "a": "a", "A": "A", "e": "e", "E": "E", "i": "i", "I": "I",
        "o": "o", "O": "O", "u": "u", "U": "U", "y": "y", "Y": "Y",
        "d": "d", "D": "D",
    }
    # Small Vietnamese folding for language token parsing only.
    fold_table = str.maketrans({
        "a": "a", "A": "A", "e": "e", "E": "E", "i": "i", "I": "I",
        "o": "o", "O": "O", "u": "u", "U": "U", "y": "y", "Y": "Y",
        "d": "d", "D": "D",
        "à": "a", "á": "a", "ả": "a", "ã": "a", "ạ": "a", "ă": "a", "ằ": "a", "ắ": "a", "ẳ": "a", "ẵ": "a", "ặ": "a", "â": "a", "ầ": "a", "ấ": "a", "ẩ": "a", "ẫ": "a", "ậ": "a",
        "À": "A", "Á": "A", "Ả": "A", "Ã": "A", "Ạ": "A", "Ă": "A", "Ằ": "A", "Ắ": "A", "Ẳ": "A", "Ẵ": "A", "Ặ": "A", "Â": "A", "Ầ": "A", "Ấ": "A", "Ẩ": "A", "Ẫ": "A", "Ậ": "A",
        "è": "e", "é": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e", "ê": "e", "ề": "e", "ế": "e", "ể": "e", "ễ": "e", "ệ": "e",
        "È": "E", "É": "E", "Ẻ": "E", "Ẽ": "E", "Ẹ": "E", "Ê": "E", "Ề": "E", "Ế": "E", "Ể": "E", "Ễ": "E", "Ệ": "E",
        "ì": "i", "í": "i", "ỉ": "i", "ĩ": "i", "ị": "i",
        "Ì": "I", "Í": "I", "Ỉ": "I", "Ĩ": "I", "Ị": "I",
        "ò": "o", "ó": "o", "ỏ": "o", "õ": "o", "ọ": "o", "ô": "o", "ồ": "o", "ố": "o", "ổ": "o", "ỗ": "o", "ộ": "o", "ơ": "o", "ờ": "o", "ớ": "o", "ở": "o", "ỡ": "o", "ợ": "o",
        "Ò": "O", "Ó": "O", "Ỏ": "O", "Õ": "O", "Ọ": "O", "Ô": "O", "Ồ": "O", "Ố": "O", "Ổ": "O", "Ỗ": "O", "Ộ": "O", "Ơ": "O", "Ờ": "O", "Ớ": "O", "Ở": "O", "Ỡ": "O", "Ợ": "O",
        "ù": "u", "ú": "u", "ủ": "u", "ũ": "u", "ụ": "u", "ư": "u", "ừ": "u", "ứ": "u", "ử": "u", "ữ": "u", "ự": "u",
        "Ù": "U", "Ú": "U", "Ủ": "U", "Ũ": "U", "Ụ": "U", "Ư": "U", "Ừ": "U", "Ứ": "U", "Ử": "U", "Ữ": "U", "Ự": "U",
        "ỳ": "y", "ý": "y", "ỷ": "y", "ỹ": "y", "ỵ": "y",
        "Ỳ": "Y", "Ý": "Y", "Ỷ": "Y", "Ỹ": "Y", "Ỵ": "Y",
        "đ": "d", "Đ": "D",
    })
    return text.translate(fold_table)


def infer_episode_number(text: str) -> int | None:
    patterns = [
        r"[Tt][aăâ]p[\s._-]*(\d{1,4})",
        r"[Ee]pisode[\s._-]*(\d{1,4})",
        r"\b[Ss](\d{1,2})[Ee](\d{1,3})\b",
        r"\b[Ee](\d{1,3})\b",
        r"\b(\d{1,3})\b",
    ]

    for pattern in patterns:
        m = re.search(pattern, text)
        if not m:
            continue
        if len(m.groups()) == 2:
            return int(m.group(2))
        return int(m.group(1))
    return None


def extract_lang_token(stem: str) -> str | None:
    folded = strip_accents(stem).lower()

    # Fast path for files already using language codes (e.g. .en.srt, .zh-Hans.srt).
    code_map = {
        "en": "en",
        "vi": "vi",
        "id": "id",
        "ms": "ms",
        "zh-hans": "zh-Hans",
        "zh-hant": "zh-Hant",
    }
    tokens = re.split(r"[.\s_]+", folded)
    if tokens:
        last = tokens[-1]
        if last in code_map:
            return code_map[last]

    # Assume language is often at the end after last dot.
    tail = folded.split(".")[-2:]
    candidates = [" ".join(tail), tail[-1], folded]
    for c in candidates:
        for key, code in LANG_MAP.items():
            if key in c:
                return code
    return None


def build_new_basename(show: str, season: int, episode: int, resolution: str) -> str:
    return f"{show}.S{season:02d}E{episode:02d}.{resolution}"


def plan_renames(downloads_dir: Path, show: str, season: int, resolution: str, ignore_dirs=("archive",)):
    plans = []
    skipped = []
    processed_subs = set()

    def is_ignored(path: Path) -> bool:
        return any(part.lower() in ignore_dirs for part in path.relative_to(downloads_dir).parts[:-1])

    all_files = [p for p in downloads_dir.rglob("*") if p.is_file() and not is_ignored(p)]
    all_subs = sorted(p for p in all_files if p.suffix.lower() in SUB_EXTS)
    all_videos = sorted(p for p in all_files if p.suffix.lower() in VIDEO_EXTS)
    videos_per_dir = {}
    for v in all_videos:
        videos_per_dir[v.parent] = videos_per_dir.get(v.parent, 0) + 1

    def belongs_to(sub: Path, video: Path) -> bool:
        # In a shared folder, only claim subtitles named after this video ("Episode.1." must not match "Episode.10.").
        if videos_per_dir[video.parent] == 1:
            return True
        return sub.stem == video.stem or sub.stem.startswith(video.stem + ".")

    for video in all_videos:
        source_text = f"{video.parent.name}.{video.stem}"
        episode = infer_episode_number(source_text)
        if episode is None:
            skipped.append((video, "Could not infer episode number"))
            continue

        new_base = build_new_basename(show, season, episode, resolution)
        new_video = video.with_name(f"{new_base}{video.suffix.lower()}")
        plans.append((video, new_video))

        for sub in sorted(p for p in video.parent.iterdir() if p.suffix.lower() in SUB_EXTS and belongs_to(p, video)):
            processed_subs.add(sub)
            if sub.stem == video.stem:
                new_sub = sub.with_name(f"{new_base}{sub.suffix.lower()}")
            else:
                lang = extract_lang_token(sub.stem)
                if lang:
                    new_sub = sub.with_name(f"{new_base}.{lang}{sub.suffix.lower()}")
                else:
                    tail = sub.stem.replace(video.stem, "").strip("._- ")
                    tail = re.sub(r"\s+", ".", tail)
                    tail = re.sub(r"[^A-Za-z0-9.\-]+", "", tail)
                    new_sub = sub.with_name(f"{new_base}.{tail}{sub.suffix.lower()}") if tail else sub.with_name(f"{new_base}{sub.suffix.lower()}")
            plans.append((sub, new_sub))

    # Handle subtitle-only folders/files (episodes with no downloaded video).
    for sub in all_subs:
        if sub in processed_subs:
            continue

        source_text = f"{sub.parent.name}.{sub.stem}"
        episode = infer_episode_number(source_text)
        if episode is None:
            skipped.append((sub, "Could not infer episode number"))
            continue

        new_base = build_new_basename(show, season, episode, resolution)
        lang = extract_lang_token(sub.stem)
        if not lang:
            # Unknown language name: keep the trailing token so different languages don't collide.
            tail = re.sub(r"[^A-Za-z0-9\-]+", "", sub.stem.rsplit(".", 1)[-1])
            lang = tail if "." in sub.stem and not tail.isdigit() else None
        if lang:
            new_sub = sub.with_name(f"{new_base}.{lang}{sub.suffix.lower()}")
        else:
            new_sub = sub.with_name(f"{new_base}{sub.suffix.lower()}")
        plans.append((sub, new_sub))

    return plans, skipped


def apply_plans(plans, dry_run: bool):
    renamed = 0
    for old, new in plans:
        if old == new:
            continue
        if new.exists() and new != old:
            print(f"[SKIP] Target exists: {new}")
            continue
        if dry_run:
            print(f"[DRY] {old.name} -> {new.name}")
        else:
            old.rename(new)
            print(f"[OK ] {old.name} -> {new.name}")
            renamed += 1
    return renamed


def main():
    parser = argparse.ArgumentParser(
        description="Rename downloaded files to Sonarr-style naming."
    )
    parser.add_argument("--show", required=True, help="Show name, e.g. The.Lament.of.Autumn")
    parser.add_argument("--season", type=int, default=1, help="Season number (default: 1)")
    parser.add_argument("--resolution", default="1080p", help="Quality tag (default: 1080p)")
    parser.add_argument("--downloads", default="Downloads", help="Downloads folder path")
    parser.add_argument(
        "--ignore",
        nargs="*",
        default=["Archive"],
        help="Folder names to skip, case-insensitive (default: Archive)",
    )
    parser.add_argument("--apply", action="store_true", help="Apply renames (default is dry-run)")
    args = parser.parse_args()

    downloads_dir = Path(args.downloads)
    if not downloads_dir.exists():
        raise SystemExit(f"Downloads folder not found: {downloads_dir}")

    show = sanitize_show_name(args.show)
    plans, skipped = plan_renames(
        downloads_dir, show, args.season, args.resolution, tuple(n.lower() for n in args.ignore)
    )

    if not plans:
        print("No media files found to rename.")
    else:
        mode = "APPLY" if args.apply else "DRY-RUN"
        print(f"Mode: {mode}")
        renamed = apply_plans(plans, dry_run=not args.apply)
        if args.apply:
            print(f"Renamed {renamed} file(s).")

    if skipped:
        print("\nSkipped files:")
        for file_path, reason in skipped:
            print(f"- {file_path}: {reason}")


if __name__ == "__main__":
    main()
