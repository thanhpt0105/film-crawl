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

Episode tracks are decrypted and saved automatically in Sonarr format, for example `Downloads/Phimfly/Reply.1994/Reply.1994.S01E02.1080p.vi.srt`. When an episode has multiple recognized languages, tracks are placed in language subfolders. Existing files are skipped, including on repeat downloads. A failed URL is reported and does not stop the remaining batch.

The show name and season are inferred from the page title. Override them or the quality tag when needed:

```powershell
python main.py --url-file urls.txt --show Seoul.Busters --season 1 --resolution 1080p
```

If the episode number or language cannot be inferred, or multiple tracks share a language, affected tracks retain their original names in the episode-title folder so no subtitles are overwritten.

## Get Season Episode Links

```powershell
python episode_links.py "https://phimfly.com/watch/AkBu"
python episode_links.py "https://phimfly.com/watch/AkBu" --out episode_urls.txt
```

The link tool uses the same cookies. It refuses to overwrite an existing output file unless `--force` is provided. Feed the generated links to the subtitle downloader with `--url-file`.

## Sonarr Naming

New episode downloads are named automatically. To rename older downloads, run the shared renamer from this directory to process only the selected show's subtitle folders. `--source-show` selects matching input folders while `--show` sets the Sonarr name. Matching ignores case, punctuation and Vietnamese accents. It detects Phimfly's language prefixes, infers the season from the episode title when available, and refuses to apply if any destination collides or already exists:

```powershell
python ..\rename_sonarr.py --show Reply.1994 --source-show "Reply 1994" --downloads Downloads\Phimfly
python ..\rename_sonarr.py --show Reply.1994 --source-show "Reply 1994" --downloads Downloads\Phimfly --apply
```
