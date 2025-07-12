# Use an official Python runtime with Playwright support
FROM mcr.microsoft.com/playwright:focal

# Create working directory
WORKDIR /app

# Install system FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Copy your backend code
COPY . .

# Install Python dependencies and Playwright browsers
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install

# Expose the port Flask listens on
EXPOSE 5000

# Tell Docker to run your app
CMD ["python", "app.py"]