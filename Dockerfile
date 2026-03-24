FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV BOT_TOKEN=${BOT_TOKEN}

EXPOSE 10000

CMD ["python", "bot.py"]
