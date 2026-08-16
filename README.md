# film-crawl

Small command-line tools to extract and download the direct CDN video URL
for Odysee (odysee.com) video pages, using Odysee's own public resolve API
(the same one the web player uses). This does not bypass any access
control — it only works for content Odysee already serves publicly.

## Files

- [extract_video_url.py](extract_video_url.py) — resolve one or more Odysee page URLs to their direct CDN video URL.
- [download_video.py](download_video.py) — resolve and download one or more Odysee videos to disk.
- [urls.txt](urls.txt) — example list of Odysee page URLs (one per line) for batch mode.

## Requirements

- Python 3.10+ (no third-party dependencies).

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

## Notes

- The Odysee CDN requires a browser-like `User-Agent` and a `Referer`/`Origin`
  of `https://odysee.com`, otherwise it responds with `401 Unauthorized`.
  Both scripts send these headers automatically.
- Downloaded video files and `__pycache__/` are excluded via [.gitignore](.gitignore).
