# Odysee Downloader

Download public Odysee videos or resolve their direct CDN URLs. These tools use Odysee's public resolve API and do not bypass access controls.

## Requirements

Python 3.10 or later. No third-party packages are required.

## Download

Run commands from this directory.

Download a video using its Odysee page URL:

```powershell
python main.py "<odysee page url>"
```

Choose a destination filename:

```powershell
python main.py "<odysee page url>" "video.mp4"
```

Batch-download URLs from a text file, one URL per line:

```powershell
python main.py -f urls.txt -o downloads
```

Existing files are skipped. The batch continues after an individual URL fails and reports failures at the end.

## Resolve a Direct URL

```powershell
python extract_url.py "<odysee page url>"
python extract_url.py -f urls.txt
```

Blank lines and lines beginning with `#` are ignored in URL files.
