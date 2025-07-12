# Use the official Playwright image (includes Python 3 & Node)
FROM mcr.microsoft.com/playwright:focal

WORKDIR /app

# Install system FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Copy your backend code
COPY . .

# Upgrade pip and install Python deps
RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN python3 -m playwright install --with-deps

# Expose the Flask port
EXPOSE 5000

# Start the Flask app
CMD ["python3", "app.py"]