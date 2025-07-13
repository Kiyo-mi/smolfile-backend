FROM mcr.microsoft.com/playwright:focal
WORKDIR /app

COPY requirements.txt ./

# Upgrade pip
RUN python3 -m pip install --upgrade pip

# Install requirements (this will show you which package is failing)
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PORT=5000
CMD ["python3", "app.py"]