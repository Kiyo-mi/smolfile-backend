# Use Playwright's official image (includes Python and dependencies)
FROM mcr.microsoft.com/playwright:focal

# Set working directory
WORKDIR /app

# Install system FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Copy application code
COPY . .

# Install Python dependencies
RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install --no-cache-dir -r requirements.txt

# (Browsers are pre-installed in this Playwright base image)

# Expose Flask port
EXPOSE 5000

# Start the Flask app
CMD ["python3", "app.py"]