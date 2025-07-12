# Use Playwright's official image (includes Python and dependencies)
FROM mcr.microsoft.com/playwright:focal

# Set working directory
WORKDIR /app

# Install system FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Copy application code
COPY . .

# Install Python dependencies and Playwright browsers
RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install --no-cache-dir -r requirements.txt \
    && python3 -m playwright install --with-deps

# Expose Flask port
EXPOSE 5000

# Start the Flask app
CMD ["python3", "app.py"]
