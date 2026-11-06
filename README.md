# Film Crawl

Film Crawl is a collection of command-line download tools, organized by service. Each service folder has its own `main.py`, usage guide, and dependencies where needed.

## Downloader Types

- **Odysee**: Resolve public Odysee page URLs and download videos. Uses the public resolve API and does not bypass access controls. See [odysee/README.md](odysee/README.md).
- **Dailymotion**: Download videos by fetching and joining HLS transport-stream segments; FFmpeg is not required. See [dailymotion/README.md](dailymotion/README.md).
- **YouTube**: Download videos with `yt-dlp`; uses `imageio-ffmpeg` to merge separate audio and video streams when required. See [youtube/README.md](youtube/README.md).
- **iQIYI**: Interactive and batch video downloads, subtitles-only mode, episode-link extraction, and Sonarr naming. Windows video downloads bootstrap `N_m3u8DL-RE` and FFmpeg in the service folder. See [iqiyi/README.md](iqiyi/README.md).
- **Phimfly**: Batch subtitle downloading and current-season episode-link extraction. Requires private Phimfly cookies in Netscape format. See [phimfly/README.md](phimfly/README.md).

## Setup

Use Python 3.10 or later. Create one virtual environment at the repository root and install the combined requirements:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Activate this environment once in each new terminal. Then change into a service directory before running its `main.py`; this keeps each downloader's relative input, cookie, and output paths separate. The service-specific `requirements.txt` files can also be installed into the same environment when you only need selected services. Odysee and Dailymotion use only the Python standard library.

## Shared Sonarr Renamer

The root-level `rename_sonarr.py` works with output from any downloader. It previews changes by default, recognizes language names and codes in subtitle filenames, and infers seasons from `SxxEyy` names unless `--season` is supplied.

```powershell
python rename_sonarr.py --show The.Lament.of.Autumn --downloads iqiyi/Downloads
python rename_sonarr.py --show The.Lament.of.Autumn --downloads iqiyi/Downloads --apply
python rename_sonarr.py --show A.Shop.For.Killers --downloads phimfly/Downloads/Phimfly
```

See `python rename_sonarr.py --help` for resolution and ignored-folder options.

## Privacy and generated files

Do not commit browser cookies or other authentication data. Each service README explains where its local cookie file belongs. Virtual environments, logs, downloaded media, temporary files, and bootstrapped executables are excluded by [.gitignore](.gitignore).
