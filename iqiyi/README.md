# iQIYI Downloader

Download iQIYI videos and subtitles interactively or in batch. Subtitles can also be downloaded without video.

## Requirements

Python 3.10 or later. Use the shared `.venv` and follow the setup instructions in the repository [README](../README.md). To install only iQIYI dependencies into that environment, run this from the repository root:

```powershell
python -m pip install -r iqiyi/requirements.txt
```

Activate the root `.venv` in each new terminal, then change into this directory before running a command. Export your iQIYI browser cookies in Netscape format to `cookies/cookies.txt`. Cookie files are private and are not included in the repository. On Windows, `N_m3u8DL-RE` and FFmpeg are downloaded into `tools/` automatically for video downloads.

## Interactive Download

Run commands from this directory:

```powershell
python main.py
```

Follow the prompts to choose language, resolution and video-plus-subtitles or subtitles-only mode.

## Batch Download

Put one iQIYI play URL per line in `urls.txt`, then run:

```powershell
python batch_download.py
```

Subtitles only:

```powershell
python batch_download.py --subtitles-only --download-delay 0
```

Download every episode when a URL belongs to a series:

```powershell
python batch_download.py --download-series
```

Use `--help` to see all batch options, including language, resolution, cookies, retry count and delay. Downloads are saved under `Downloads/`. Existing non-empty video and subtitle files are skipped.

## Episode Links

List all episodes in an iQIYI series from one episode URL:

```powershell
python episode_links.py "<iQIYI episode URL>"
python episode_links.py "<iQIYI episode URL>" --out episode_urls.txt
```

The `--out` option overwrites the specified file. Use the resulting list with `batch_download.py --url-file episode_urls.txt`.

## Sonarr Naming

Preview renames before applying them:

```powershell
python rename_sonarr.py --show The.Lament.of.Autumn --season 1
python rename_sonarr.py --show The.Lament.of.Autumn --season 1 --apply
```

The rename tool skips `Archive` folders by default. See `python rename_sonarr.py --help` for all options.
