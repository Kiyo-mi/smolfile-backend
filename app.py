from flask import Flask, request, send_file
from flask_cors import CORS
import yt_dlp
import ffmpeg
import os
import uuid
import requests
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from yt_dlp import YoutubeDL
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Initialize Flask
app = Flask(__name__)
CORS(app, resources={ r"/compress": {"origins": "*"} })

# Directory to store videos
OUTPUT_DIR = "compressed_videos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Target size: 10MB
TARGET_SIZE_MB = 10
TARGET_SIZE_BYTES = TARGET_SIZE_MB * 1024 * 1024

# Domains that need headless browser extraction
BROWSER_DOMAINS = (
    'youtube.com', 'youtu.be',
    'twitter.com', 'x.com'
)


def download_video(url, output_path):
    """
    Download the video at `url` directly via yt-dlp into output_path.
    """
    print(f"[yt-dlp] downloading {url} to {output_path}")
    ydl_opts = {
        "format": "best[ext=mp4]",
        "outtmpl": output_path,
        "quiet": True,
        "nocheckcertificate": True,
        "geo_bypass": True,
        "restrictfilenames": True,
        "noplaylist": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    print(f"[yt-dlp] saved to {output_path}")

    # 2) Fallback: yt-dlp
    print(f"[yt-dlp] downloading via yt-dlp for {url}")
    ydl_opts = {
        "format": "best[ext=mp4]",
        "outtmpl": output_path,
        "quiet": True,
        "nocheckcertificate": True,
        "geo_bypass": True,
        "restrictfilenames": True,
        "noplaylist": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    print(f"[yt-dlp] saved to {output_path}")


def compress_video(input_path, output_path):
    """
    Compress input_path to output_path targeting under 10MB.
    """
    print(f"[compress_video] probing {input_path}")
    probe = ffmpeg.probe(input_path)
    duration = float(probe['format']['duration'])
    bitrate = (TARGET_SIZE_BYTES * 8) / duration
    bitrate_k = int(bitrate / 1000)
    print(f"[compress_video] target bitrate: {bitrate_k}k")
    (
        ffmpeg
        .input(input_path)
        .output(
            output_path,
            video_bitrate=f'{bitrate_k}k',
            format='mp4',
            vcodec='libx264',
            acodec='aac'
        )
        .run(overwrite_output=True)
    )
    print(f"[compress_video] output saved to {output_path}")

@app.route('/compress', methods=['POST'])
def compress():
    url = request.form.get('url')
    if not url:
        return {'error': 'No URL provided'}, 400

    uid = str(uuid.uuid4())
    raw = os.path.join(OUTPUT_DIR, f"{uid}_raw.mp4")
    small = os.path.join(OUTPUT_DIR, f"{uid}_smol.mp4")

    try:
        # If download_video can’t find a src, it raises ValueError
        download_video(url, raw)
        compress_video(raw, small)
        os.remove(raw)
        return send_file(small, as_attachment=True)

    except ValueError as ve:
        # Handle our “no video found” case gracefully
        return {'error': str(ve)}, 400

    except Exception as e:
        # Everything else stays a 500
        return {'error': 'Internal server error'}, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)