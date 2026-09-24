# Music Downloader

A small dark-themed desktop app for downloading Spotify tracks, albums, and playlists with `spotdl`.

Downloaded files are saved to:

```text
%USERPROFILE%\Downloads\Spotify
```

## Features

- Dark PyQt6 interface
- Spotify track, album, and playlist links
- Progress log and progress bar
- Output folder button
- Downloads outside the project folder
- Uses a local `ffmpeg.exe` automatically when it is placed next to `main.py`

## Requirements

- Python 3.10+
- FFmpeg

Install Python packages:

```bash
pip install -r requirements.txt
```

Install FFmpeg in one of these ways:

```bash
spotdl --download-ffmpeg
```

Or place `ffmpeg.exe` next to `main.py`.

## Run

```bash
python main.py
```

## Notes

`spotdl` searches external audio providers. Some rare Spotify tracks may not be found by those providers, even when the Spotify link is valid.
