# film-crawl

Small command-line tools to extract and download videos from Odysee,
Dailymotion, and YouTube.

## Files

- [extract_video_url.py](extract_video_url.py) — resolve one or more Odysee page URLs to their direct CDN video URL, using Odysee's own public resolve API (the same one the web player uses). This does not bypass any access control — it only works for content Odysee already serves publicly.
- [download_video.py](download_video.py) — resolve and download one or more Odysee videos to disk.
- [download_dailymotion_video.py](download_dailymotion_video.py) — resolve and download one or more Dailymotion videos to disk (no ffmpeg required; downloads and concatenates HLS `.ts` segments).
- [download_youtube_video.py](download_youtube_video.py) — resolve and download one or more YouTube videos to disk, using [yt-dlp](https://github.com/yt-dlp/yt-dlp).
- [urls.txt](urls.txt) — example list of Odysee page URLs (one per line) for batch mode.

## Requirements

- Python 3.10+.
- `extract_video_url.py` and `download_video.py` (Odysee) and `download_dailymotion_video.py` (Dailymotion) have no third-party dependencies.
- `download_youtube_video.py` requires `yt-dlp`, installed in a project-local virtual environment (do not install packages globally):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install yt-dlp
```

Activate the venv (`.venv\Scripts\Activate.ps1`) in each new terminal session before running `download_youtube_video.py`.

## Usage

### Extract a direct video URL

Single URL:

```powershell
python extract_video_url.py "<odysee page url>"
```

Batch, from a text file (one URL per line; blank lines and lines starting
with `#` are ignored):

```powershell
python extract_video_url.py -f urls.txt
```

### Download a video

Single URL, saved to the current directory using the video's title as the
filename:

```powershell
python download_video.py "<odysee page url>"
```

Single URL with a custom output path:

```powershell
python download_video.py "<odysee page url>" "myvideo.mp4"
```

Batch download from a file, optionally into a specific output directory:

```powershell
python download_video.py -f urls.txt -o downloads
```

Batch mode skips URLs whose destination file already exists, continues past
individual failures, and prints a summary of failed URLs at the end.

### Download a Dailymotion video

Same interface as the Odysee downloader:

```powershell
python download_dailymotion_video.py "<dailymotion url>"
python download_dailymotion_video.py -f urls.txt -o downloads
```

Saves a `.ts` (MPEG transport stream) file, playable directly in VLC, MPC-HC,
or PotPlayer without conversion.

### Download a YouTube video

Requires the venv with `yt-dlp` set up (see Requirements) and activated:

```powershell
python download_youtube_video.py "<youtube url>"
python download_youtube_video.py -f urls.txt -o downloads
```

## Notes

- The Odysee CDN requires a browser-like `User-Agent` and a `Referer`/`Origin`
  of `https://odysee.com`, otherwise it responds with `401 Unauthorized`.
  Both Odysee scripts send these headers automatically.
- The YouTube downloader restricts format selection to pre-muxed
  (audio+video combined) streams, since this environment has no `ffmpeg` (for
  merging separate streams) or JS runtime (needed to decipher some DASH-only
  formats).
- Downloaded video files, `.venv/`, and `__pycache__/` are excluded via [.gitignore](.gitignore).
