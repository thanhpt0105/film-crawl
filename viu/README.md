# Viu Subtitle Downloader

Download the subtitle tracks listed on a Viu episode page, or get all episode links for a series and batch-download their subtitles.

## Requirements

Use the shared root `.venv` and follow the setup instructions in the repository [README](../README.md). To install only Viu dependencies into that environment, run from the repository root:

```powershell
python -m pip install -r viu/requirements.txt
```

The tested Singapore episode page exposes subtitle URLs directly in its page data; no Viu cookie file is needed for that public content.

## Get Episode Links

Run from this directory:

```powershell
python episode_links.py "https://www.viu.com/ott/sg/en/vod/2428843/In-Between"
python episode_links.py "<episode URL>" --out episode_urls.txt
```

The output file is not overwritten unless `--force` is provided.

## Download Subtitles

Download every available track from one episode:

```powershell
python main.py "https://www.viu.com/ott/sg/en/vod/2428843/In-Between"
```

Download all tracks for every link in a text file:

```powershell
python main.py --url-file episode_urls.txt
```

Select a language code, repeat `--lang` for more than one, or choose another output directory:

```powershell
python main.py --url-file episode_urls.txt --lang en --lang zh-Hant
python main.py --url-file episode_urls.txt --output Downloads
```

Subtitles are saved under `Downloads/<series>/` as `<series>.E01.<language>.srt`. Existing files are skipped, and failures for one episode do not stop the rest of the batch.
