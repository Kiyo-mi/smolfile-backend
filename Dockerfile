# Use Playwright's official image which includes Node, Python, and necessary libs
FROM mcr.microsoft.com/playwright:focal

# Create and activate a Python virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install system FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Install Python dependencies and Playwright browsers
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && python3 -m playwright install --with-deps

# Expose Flask port
EXPOSE 5000

# Start the Flask app
CMD ["python3", "app.py"]
