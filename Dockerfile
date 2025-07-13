# Use Playwright’s official image (includes browsers + Python 3)
FROM mcr.microsoft.com/playwright:focal

WORKDIR /app

# Copy and install Python dependencies using python3 -m pip
COPY requirements.txt ./
RUN python3 -m pip install --upgrade pip \
 && python3 -m pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app
COPY . .

# Expose the port Railway will bind
ENV PORT=5000

# Start your Flask app
CMD ["python3", "app.py"]