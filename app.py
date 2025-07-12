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

# Domains that need headless browser extraction
BROWSER_DOMAINS = (
    'youtube.com', 'youtu.be',
    'instagram.com', 'www.instagram.com',
    'twitter.com', 'x.com'
)


def extract_video_src_with_playwright(page_url):
    """
    Use Playwright to navigate to a page and extract the <video> tag's src attribute.
    """
    print(f"[playwright] launching browser for: {page_url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(page_url, timeout=60000)
        page.wait_for_selector('video', timeout=15000)
        src = page.eval_on_selector('video', 'el => el.src')
        browser.close()
        print(f"[playwright] extracted src: {src}")
        return src


def download_video(url, output_path):
    """
    Download a video to output_path. Uses Playwright for certain domains; yt_dlp for others.
    """
    domain = urlparse(url).netloc.lower()
    print(f"[download_video] domain detected: {domain}")

    # If URL matches a domain that blocks generic extractors, use headless browser
    if any(d in domain for d in BROWSER_DOMAINS):
        print(f"[browser] extracting video src for {url}")
        video_src = extract_video_src_with_playwright(url)
        try:
            with requests.get(video_src, stream=True) as r:
                r.raise_for_status()
                print(f"[browser download] streaming from: {video_src}")
                with open(output_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            print(f"[browser download] saved to {output_path}")
            return
        except Exception as e:
            print(f"[browser download] failed for {url}: {e}")
            raise

    # Fallback to yt-dlp for other platforms (Reddit, generic links)
    print(f"[yt-dlp] downloading via yt-dlp for {url}")
    ydl_opts = {
        'format': 'best[ext=mp4]',
        'force_generic_extractor': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'quiet': True,
        'restrictfilenames': True,
        'noplaylist': True,
        'outtmpl': output_path
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"[yt-dlp] saved to {output_path}")
    except Exception as e:
        print(f"[yt-dlp] failed for {url}: {e}")
        raise


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
    print(f"[compress] request received for URL: {url}")
    if not url:
        return {'error': 'No URL provided'}, 400

    try:
        uid = str(uuid.uuid4())
        raw = os.path.join(OUTPUT_DIR, f"{uid}_raw.mp4")
        small = os.path.join(OUTPUT_DIR, f"{uid}_smol.mp4")

        download_video(url, raw)
        compress_video(raw, small)
        os.remove(raw)

        print(f"[compress] sending file: {small}")
        return send_file(small, as_attachment=True)
    except Exception as e:
        import traceback; traceback.print_exc()
        return {'error': str(e)}, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)