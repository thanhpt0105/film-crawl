# Film Crawl

Film Crawl is a collection of command-line download tools, organized by service. Each service folder has its own `main.py`, usage guide, and dependencies where needed.

## Downloader Types

- **Odysee**: Resolve public Odysee page URLs and download videos. Uses the public resolve API and does not bypass access controls. See [odysee/README.md](odysee/README.md).
- **Dailymotion**: Download videos by fetching and joining HLS transport-stream segments; FFmpeg is not required. See [dailymotion/README.md](dailymotion/README.md).
- **YouTube**: Download videos with `yt-dlp`; uses `imageio-ffmpeg` to merge separate audio and video streams when required. See [youtube/README.md](youtube/README.md).
- **iQIYI**: Interactive and batch video downloads, subtitles-only mode, episode-link extraction, and Sonarr naming. Windows video downloads bootstrap `N_m3u8DL-RE` and FFmpeg in the service folder. See [iqiyi/README.md](iqiyi/README.md).
- **Phimfly**: Batch subtitle downloading and current-season episode-link extraction. Requires private Phimfly cookies in Netscape format. See [phimfly/README.md](phimfly/README.md).

## Setup

Use Python 3.10 or later. Each service manages its own dependencies; follow that service's README and run its commands from inside its directory. This keeps optional packages and runtime files separate.

## Privacy and generated files

Do not commit browser cookies or other authentication data. Each service README explains where its local cookie file belongs. Virtual environments, logs, downloaded media, temporary files, and bootstrapped executables are excluded by [.gitignore](.gitignore).
