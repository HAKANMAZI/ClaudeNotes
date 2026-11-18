@echo off
pip install -U yt-dlp
winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
python video_indirici.py
