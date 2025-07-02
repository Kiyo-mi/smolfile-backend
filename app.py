from flask import Flask, request, send_file
from flask_cors import CORS
import yt_dlp
import ffmpeg
import os
import uuid

# This starts your web app
app = Flask(__name__)
CORS(app)


# Where we’ll save the downloaded + compressed videos
OUTPUT_DIR = "compressed_videos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Set our file size goal: 10MB
TARGET_SIZE_MB = 10
TARGET_SIZE_BYTES = TARGET_SIZE_MB * 1024 * 1024
import requests
# STEP 1: Download the video from the given URL
def download_video(url, output_path):
    with requests.get(url, stream=True) as r:
        with open(output_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    ydl_opts = {
        
        'format': 'best[ext=mp4]',
'nocheckcertificate': True,
'geo_bypass': True,
'quiet': True,
'restrictfilenames': True,
'noplaylist': True,
'force_generic_extractor': True  # Helps with non-YouTube URLs
,  # Choose best quality MP4
        'outtmpl': output_path,     # Save to this path
        'quiet': True               # Don’t print too much info
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])         # Download the video

# STEP 2: Compress the video using FFmpeg
def compress_video(input_path, output_path):
    probe = ffmpeg.probe(input_path)
    duration = float(probe['format']['duration'])  # Get video length in seconds

    # Calculate bitrate needed to fit under 10MB
    bitrate = (TARGET_SIZE_BYTES * 8) / duration
    bitrate_k = int(bitrate / 1000)  # Convert to kilobits per second

    # Compress with target bitrate
    (
        ffmpeg
        .input(input_path)
        .output(output_path, video_bitrate=f'{bitrate_k}k', format='mp4', vcodec='libx264', acodec='aac')
        .run(overwrite_output=True)
    )

# STEP 3: Main route to handle video compression
@app.route('/compress', methods=['POST'])
def compress():
    video_url = request.form.get('url')
    if not video_url:
        return {'error': 'No URL provided'}, 400

    # BLOCK YouTube until later
    if "youtube.com" in video_url or "youtu.be" in video_url:
        return {'error': 'YouTube is unsupported for now'}, 400

    try:
        # Step 1: Get real mp4 URL
        direct_url = get_direct_video_url(video_url)
        if not direct_url:
            return {'error': 'Unable to extract video'}, 400

        # Step 2: Download & compress the video
        uid = str(uuid.uuid4())
        raw_path = f"{uid}_raw.mp4"
        raw_full = os.path.join(OUTPUT_DIR, raw_path)
        compressed_path = f"{uid}_smol.mp4"
        compressed_full = os.path.join(OUTPUT_DIR, compressed_path)

        # Download the actual file
        download_video(direct_url, raw_full)
        compress_video(raw_full, compressed_full)
        os.remove(raw_full)

        return send_file(compressed_full, as_attachment=True)
    except Exception as e:
        return {'error': str(e)}, 500

from playwright.sync_api import sync_playwright

def get_direct_video_url(page_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(page_url, timeout=60000)

        # Wait for video to load (adjust as needed)
        page.wait_for_timeout(3000)

        # Try grabbing video tag src
        video_src = page.eval_on_selector("video", "el => el.src")

        browser.close()
        return video_src

# Run the app locally
if __name__ == '__main__':
   import os
port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)

