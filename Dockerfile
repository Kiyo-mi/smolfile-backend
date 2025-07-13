# Use Playwright’s official image which bundles all browser dependencies
FROM mcr.microsoft.com/playwright:focal

# Set working directory
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY . .

# Expose the PORT (Railway sets this env var automatically)
ENV PORT=5000

# Launch your Flask app
CMD ["python3", "app.py"]