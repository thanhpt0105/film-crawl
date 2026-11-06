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


def normalize_show_key(name: str) -> str:
    folded = strip_accents(name).lower()
    return re.sub(r"[^a-z0-9]+", " ", folded).strip()


def infer_episode_number(text: str) -> int | None:
    patterns = [
        r"\b[Ss](\d{1,2})[Ee](\d{1,3})\b",
        r"[Tt][aăâ]p[\s._-]*(\d{1,4})",
        r"\b(?:[Ee]pisode|[Ee]p)[\s._-]*(\d{1,4})\b",
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


def infer_season_number(text: str) -> int | None:
    match = re.search(r"\b[Ss](\d{1,2})[Ee]\d{1,3}\b", text)
    return int(match.group(1)) if match else None


def extract_lang_token(stem: str) -> str | None:
    folded = strip_accents(stem).lower()

    code_map = {
        "ar": "ar", "bg": "bg", "bn": "bn", "cs": "cs", "da": "da",
        "de": "de", "el": "el", "en": "en", "en-uk": "en", "en-us": "en",
        "es": "es", "es-419": "es", "es-es": "es", "et": "et", "fi": "fi",
        "fr": "fr", "fr-ca": "fr", "fr-fr": "fr", "he": "he", "hi": "hi",
        "hr": "hr", "hu": "hu", "id": "id", "is": "is", "it": "it",
        "ja": "ja", "ko": "ko", "ms": "ms", "nl": "nl", "no": "no",
        "pl": "pl", "pt": "pt", "pt-br": "pt", "ro": "ro", "ru": "ru",
        "sk": "sk", "sl": "sl", "sr": "sr", "sv": "sv", "ta": "ta",
        "te": "te", "th": "th", "tr": "tr", "uk": "uk", "vi": "vi",
        "vi-vn": "vi", "zh": "zh", "cmn-hans": "zh-Hans",
        "cmn-hant": "zh-Hant", "yue-hant": "zh-Hant",
    }
    tokens = re.split(r"[.\s_]+", folded)
    for token in (tokens[0], tokens[-1]):
        if token in code_map:
            return code_map[token]

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


def plan_renames(
    downloads_dir: Path,
    show: str,
    season: int | None,
    resolution: str,
    ignore_dirs=("archive",),
    source_show: str | None = None,
):
    plans = []
    skipped = []
    processed_subs = set()
    source_show = source_show or show
    source_key = normalize_show_key(source_show)
    show_dir = downloads_dir / show

    def is_ignored(path: Path) -> bool:
        return any(part.lower() in ignore_dirs for part in path.relative_to(downloads_dir).parts[:-1])

    def matches_source_show(path: Path) -> bool:
        parts = (downloads_dir.name, *path.relative_to(downloads_dir).parts)
        for part in parts:
            key = normalize_show_key(part)
            if key == source_key or key.startswith(source_key + " "):
                return True
        return False

    all_files = [
        p for p in downloads_dir.rglob("*")
        if p.is_file() and not is_ignored(p) and matches_source_show(p)
    ]
    if not all_files:
        raise ValueError(
            f"No files matched source show '{source_show}' under '{downloads_dir}'. "
            "Use --source-show to specify the source folder/name."
        )
    all_subs = sorted(p for p in all_files if p.suffix.lower() in SUB_EXTS)
    all_videos = sorted(p for p in all_files if p.suffix.lower() in VIDEO_EXTS)
    languages = {lang for sub in all_subs if (lang := extract_lang_token(sub.stem))}
    separate_language_dirs = len(languages) > 1
    videos_per_dir = {}
    for v in all_videos:
        videos_per_dir[v.parent] = videos_per_dir.get(v.parent, 0) + 1

    def belongs_to(sub: Path, video: Path) -> bool:
        # In a shared folder, only claim subtitles named after this video ("Episode.1." must not match "Episode.10.").
        if videos_per_dir[video.parent] == 1:
            return True
        return sub.stem == video.stem or sub.stem.startswith(video.stem + ".")

    def subtitle_target(sub: Path, new_base: str, video_stem: str | None = None) -> Path:
        lang = extract_lang_token(sub.stem)
        if sub.stem == video_stem:
            filename = f"{new_base}{sub.suffix.lower()}"
        elif lang:
            filename = f"{new_base}.{lang}{sub.suffix.lower()}"
        else:
            tail = sub.stem
            if video_stem:
                tail = tail.replace(video_stem, "")
            tail = tail.strip("._- ")
            tail = re.sub(r"\s+", ".", tail)
            tail = re.sub(r"[^A-Za-z0-9.\-]+", "", tail)
            filename = f"{new_base}.{tail}{sub.suffix.lower()}" if tail else f"{new_base}{sub.suffix.lower()}"

        destination = show_dir / lang if separate_language_dirs and lang else show_dir
        return destination / filename

    for video in all_videos:
        source_text = f"{video.parent.name}.{video.stem}"
        episode = infer_episode_number(source_text)
        if episode is None:
            skipped.append((video, "Could not infer episode number"))
            continue

        season_number = season if season is not None else infer_season_number(source_text) or 1
        new_base = build_new_basename(show, season_number, episode, resolution)
        new_video = show_dir / f"{new_base}{video.suffix.lower()}"
        plans.append((video, new_video))

        for sub in sorted(p for p in video.parent.iterdir() if p.suffix.lower() in SUB_EXTS and belongs_to(p, video)):
            processed_subs.add(sub)
            plans.append((sub, subtitle_target(sub, new_base, video.stem)))

    # Handle subtitle-only folders/files (episodes with no downloaded video).
    for sub in all_subs:
        if sub in processed_subs:
            continue

        source_text = f"{sub.parent.name}.{sub.stem}"
        episode = infer_episode_number(source_text)
        if episode is None:
            skipped.append((sub, "Could not infer episode number"))
            continue

        season_number = season if season is not None else infer_season_number(source_text) or 1
        new_base = build_new_basename(show, season_number, episode, resolution)
        plans.append((sub, subtitle_target(sub, new_base)))

    return plans, skipped


def find_plan_conflicts(plans):
    sources_by_target = {}
    planned_sources = {old for old, new in plans if old != new}
    for old, new in plans:
        sources_by_target.setdefault(new, []).append(old)

    conflicts = []
    for target, sources in sources_by_target.items():
        if len(sources) > 1:
            conflicts.append(f"Multiple source files target {target}: " + ", ".join(str(p) for p in sources))
        if target.exists() and target not in sources:
            conflicts.append(f"Target already exists: {target}")
        if target in planned_sources and target not in sources:
            conflicts.append(f"Target is also a source file in this plan: {target}")
    return conflicts


def apply_plans(plans, dry_run: bool):
    conflicts = find_plan_conflicts(plans)
    if conflicts:
        print("[ERROR] Rename plan has conflicts; no files were changed.")
        for conflict in conflicts:
            print(f"[CONFLICT] {conflict}")
        return -1

    renamed = 0
    for old, new in plans:
        if old == new:
            continue
        if new.exists() and new != old:
            print(f"[SKIP] Target exists: {new}")
            continue
        if dry_run:
            print(f"[DRY] {old} -> {new}")
        else:
            new.parent.mkdir(parents=True, exist_ok=True)
            old.rename(new)
            print(f"[OK ] {old} -> {new}")
            renamed += 1
    return renamed


def main():
    parser = argparse.ArgumentParser(description="Rename downloaded files from any service to Sonarr-style naming.")
    parser.add_argument("--show", required=True, help="Show name, e.g. The.Lament.of.Autumn")
    parser.add_argument(
        "--season",
        type=int,
        help="Season number override (default: infer SxxEyy from names, otherwise 1)",
    )
    parser.add_argument("--resolution", default="1080p", help="Quality tag (default: 1080p)")
    parser.add_argument("--downloads", default="Downloads", help="Downloads folder path")
    parser.add_argument(
        "--source-show",
        help="Source show name/alias used to select files (default: --show)",
    )
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
    try:
        plans, skipped = plan_renames(
            downloads_dir,
            show,
            args.season,
            args.resolution,
            tuple(n.lower() for n in args.ignore),
            args.source_show,
        )
    except ValueError as exc:
        parser.error(str(exc))

    if not plans:
        print("No media files found to rename.")
    else:
        mode = "APPLY" if args.apply else "DRY-RUN"
        print(f"Mode: {mode}")
        renamed = apply_plans(plans, dry_run=not args.apply)
        if renamed < 0:
            return 1
        if args.apply:
            print(f"Renamed {renamed} file(s).")

    if skipped:
        print("\nSkipped files:")
        for file_path, reason in skipped:
            print(f"- {file_path}: {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
