# Phimfly Tools

Download subtitles from Phimfly episode pages and list all episode links in a season.

## Requirements

Python 3.10 or later. Use the shared `.venv` and follow the setup instructions in the repository [README](../README.md). To install only Phimfly dependencies into that environment, run this from the repository root:

```powershell
python -m pip install -r phimfly/requirements.txt
```

Activate the root `.venv` in each new terminal, then change into this directory before running a command. Export browser cookies for `phimfly.com` in Netscape format to `cookies/cookies.txt`. Cookie files are private and are not included in the repository.

## Download Subtitles

Run commands from this directory. Download all available subtitle tracks from one episode:

```powershell
python main.py "https://phimfly.com/watch/AkBu"
```

Process the URLs in `urls.txt`:

```powershell
python main.py --url-file urls.txt
```

Select a language (language code; repeat `--lang` for more than one), or specify another cookie file or output directory:

```powershell
python main.py "<episode URL>" --lang vi
python main.py --url-file urls.txt --cookies "<cookie file>" --output Downloads
```

Tracks are decrypted and saved beneath `Downloads/Phimfly/<episode title>/`. Existing files are skipped. A failed URL is reported and does not stop the remaining batch.

## Get Season Episode Links

```powershell
python episode_links.py "https://phimfly.com/watch/AkBu"
python episode_links.py "https://phimfly.com/watch/AkBu" --out episode_urls.txt
```

The link tool uses the same cookies. It refuses to overwrite an existing output file unless `--force` is provided. Feed the generated links to the subtitle downloader with `--url-file`.
