# YouTube Downloader

Download one or many YouTube videos using `yt-dlp`. The downloader prefers a combined audio/video stream when available; otherwise it merges separate streams with FFmpeg supplied by `imageio-ffmpeg`.

## Requirements

Python 3.10 or later. Set up a virtual environment in this directory:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Activate `.venv` in each new terminal before running the downloader.

## Download

Run commands from this directory.

Download one video:

```powershell
python main.py "<youtube url>"
```

Choose the output filename:

```powershell
python main.py "<youtube url>" "video.mp4"
```

Batch-download URLs from a text file, one per line:

```powershell
python main.py -f urls.txt -o downloads
```

Existing files are skipped in batch mode. The script retries failed downloads and continues through the list, reporting failed URLs at the end. YouTube changes its extraction logic regularly, so keep `yt-dlp` updated:

```powershell
python -m pip install --upgrade yt-dlp
```
