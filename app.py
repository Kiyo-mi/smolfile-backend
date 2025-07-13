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
    'instagram.com', 'www.instagram.com',
    'twitter.com', 'x.com'
)


def extract_video_src_with_playwright(page_url):
    """
    Use a mobile UA so Instagram/Twitter/Reels render a simple <video> tag.
    Returns the video src URL or None if not found.
    """
    mobile_ua = (
      "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 "
      "Mobile/15A372 Safari/604.1"
    )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=mobile_ua)
        page.goto(page_url, timeout=60000)
        try:
            # wait for any <video src> element
            page.wait_for_selector("video[src]", timeout=15000)
            src = page.eval_on_selector("video", "el => el.src")
            print(f"[browser] extracted src via playwright: {src}")
            browser.close()
            return src or None
        except PlaywrightTimeoutError:
            print("[browser] timeout waiting for video[src]")
        except Exception as e:
            print(f"[browser] error extracting video[src]: {e}")
        finally:
            browser.close()
        return None


def download_video(url, output_path):
    """
    First try Playwright/Mobile-UA extraction; if that fails, fallback to yt-dlp.
    """
    domain = urlparse(url).netloc.lower()
    print(f"[download_video] domain: {domain}")

    # 1) Playwright path for “hard” domains
    if any(d in domain for d in BROWSER_DOMAINS):
        print(f"[browser] playwright extracting for {url}")
        video_src = extract_video_src_with_playwright(url)
        if video_src:
            print(f"[browser] got src: {video_src}")
            # stream into file
            with requests.get(video_src, stream=True) as r:
                r.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
            print(f"[browser] saved to {output_path}")
            return
        print(f"[browser] no src, falling back to yt-dlp")

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