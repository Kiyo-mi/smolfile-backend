from flask import Flask, request, send_file
from flask_cors import CORS
import yt_dlp
import ffmpeg
import os
import uuid
import requests
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

# Initialize Flask
app = Flask(__name__)
CORS(app)

# Directory to store videos
OUTPUT_DIR = "compressed_videos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Target size: 10MB
TARGET_SIZE_MB = 10
TARGET_SIZE_BYTES = TARGET_SIZE_MB * 1024 * 1024


def extract_video_src_with_playwright(page_url):
    """
    Use Playwright to navigate to the page and extract the <video> tag's src.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(page_url, timeout=60000)
        page.wait_for_selector('video', timeout=15000)
        src = page.eval_on_selector('video', 'el => el.src')
        browser.close()
        return src


def download_video(url, output_path):
    """
    Download a video to output_path. Uses Playwright for YouTube; yt_dlp for others.
    """
    domain = urlparse(url).netloc.lower()
    # For YouTube (and domains that block non-browser clients), use Playwright
    if 'youtube.com' in domain or 'youtu.be' in domain:
        video_src = extract_video_src_with_playwright(url)
        # Stream download via requests
        with requests.get(video_src, stream=True) as r:
            r.raise_for_status()
            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
    else:
        # Use yt_dlp for other platforms (Instagram, Twitter, Reddit, etc.)
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'nocheckcertificate': True,
            'geo_bypass': True,
            'quiet': True,
            'restrictfilenames': True,
            'noplaylist': True,
            'outtmpl': output_path
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])


def compress_video(input_path, output_path):
    """
    Compress input_path to output_path targeting under 10MB.
    """
    probe = ffmpeg.probe(input_path)
    duration = float(probe['format']['duration'])
    bitrate = (TARGET_SIZE_BYTES * 8) / duration
    bitrate_k = int(bitrate / 1000)
    (
        ffmpeg
        .input(input_path)
        .output(output_path,
                video_bitrate=f'{bitrate_k}k',
                format='mp4',
                vcodec='libx264',
                acodec='aac')
        .run(overwrite_output=True)
    )

@app.route('/compress', methods=['POST'])
def compress():
    url = request.form.get('url')
    if not url:
        return {'error': 'No URL provided'}, 400

    try:
        uid = str(uuid.uuid4())
        raw = os.path.join(OUTPUT_DIR, f"{uid}_raw.mp4")
        small = os.path.join(OUTPUT_DIR, f"{uid}_smol.mp4")

        download_video(url, raw)
        compress_video(raw, small)
        os.remove(raw)

        return send_file(small, as_attachment=True)
    except Exception as e:
        # Log error for debugging
        print(f"Error during compression: {e}")
        return {'error': str(e)}, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
