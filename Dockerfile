FROM python:3.9

# সিস্টেমের জন্য FFmpeg ইনস্টল করা
RUN apt-get update && apt-get install -y ffmpeg

# ডিরেক্টরি সেটআপ
WORKDIR /app

# লাইব্রেরি ইনস্টল
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# সব কোড কপি করা
COPY . .

# বট রান করা
CMD ["python", "bot.py"]
