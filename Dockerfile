# ১. সাইজ কমানোর জন্য 'slim' ভার্সন ব্যবহার করা হলো (ডিপ্লয় দ্রুত হবে)
FROM python:3.9-slim

# ২. FFmpeg ইনস্টল এবং সাথে অপ্রয়োজনীয় ক্যাশ ডিলিট করা (স্টোরেজ বাঁচবে)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ৩. ডিরেক্টরি সেটআপ
WORKDIR /app

# ৪. লাইব্রেরি ইনস্টল
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ৫. সব কোড কপি করা
COPY . .

# ৬. রেন্ডারের ওয়েব সার্ভিসের জন্য পোর্ট এক্সপোজ করা (Render পোর্ট দিয়ে চেক করে সার্ভিস লাইভ কিনা)
EXPOSE 10000

# ৭. বট রান করা (তোমার ফাইল অনুযায়ী bot.py রাখা হলো)
CMD ["python", "bot.py"]
