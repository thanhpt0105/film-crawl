# Dailymotion Downloader

Download Dailymotion videos as MPEG transport stream (`.ts`) files. The downloader fetches HLS segments directly and does not require FFmpeg.

## Requirements

Python 3.10 or later. No third-party packages are required.

## Download

Run commands from this directory.

Download one page URL or video ID:

```powershell
python main.py "<dailymotion url or video id>"
```

Choose the output filename:

```powershell
python main.py "<dailymotion url>" "video.ts"
```

Batch-download URLs from a text file, one per line:

```powershell
python main.py -f urls.txt -o downloads
```

The downloader retries transient segment failures and writes output in segment order. The resulting `.ts` file can be played in common media players such as VLC.
