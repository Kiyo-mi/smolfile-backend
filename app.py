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

# STEP 1: Download the video from the given URL
def download_video(url, output_path):
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
 # 🚫 Block YouTube links for now
    if "youtube.com" in video_url or "youtu.be" in video_url:
        return {
            'error': 'YouTube is currently unsupported. Try Instagram, Twitter, or Reddit instead.'
        }, 400
    # Generate unique filename
    uid = str(uuid.uuid4())
    raw_path = f"{uid}_raw.mp4"
    raw_full = os.path.join(OUTPUT_DIR, raw_path)
    compressed_path = f"{uid}_smol.mp4"
    compressed_full = os.path.join(OUTPUT_DIR, compressed_path)

    try:
        # Download and compress
        download_video(video_url, raw_full)
        compress_video(raw_full, compressed_full)
        os.remove(raw_full)  # Clean up original file

        # Send compressed video back to user
        return send_file(compressed_full, as_attachment=True)
    except Exception as e:
        return {'error': str(e)}, 500

# Run the app locally
if __name__ == '__main__':
   import os
port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)

