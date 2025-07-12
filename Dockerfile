# Use Playwright’s Ubuntu+Python3 image (includes playwright CLI)
FROM mcr.microsoft.com/playwright:focal

WORKDIR /app

# Install FFmpeg system binary
RUN apt-get update && apt-get install -y ffmpeg

# Copy your application code
COPY . .

# Install Python dependencies and Playwright browsers
RUN python3 -m venv /opt/venv \
    && . /opt/venv/bin/activate \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && python3 -m playwright install

# Make sure the venv’s pip/python are used
ENV PATH="/opt/venv/bin:$PATH"

# Expose the port your Flask app runs on
EXPOSE 5000

# Start your app
CMD ["python3", "app.py"]