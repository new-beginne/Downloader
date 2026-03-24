import os
import threading
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()  # Local testing / fallback
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise Exception("🚨 BOT_TOKEN environment variable not set!")

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

# ==============================
# Start & Message Handler
# ==============================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Welcome! I am Ultimate Downloader Bot.\n\n🔗 Send me a video/playlist link to start.")

@bot.message_handler(func=lambda message: message.text.startswith('http'))
def handle_link(message):
    chat_id = message.chat.id
    url = message.text
    user_data[chat_id] = {'url': url}

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("⚡ Auto Best Quality (No Sub)", callback_data="opt1"),
        InlineKeyboardButton("🇧🇩 Auto Best + Bangla Subtitle", callback_data="opt2"),
        InlineKeyboardButton("🎬 Choose Quality Manually", callback_data="opt3"),
        InlineKeyboardButton("🎵 Audio Only (MP3)", callback_data="opt4"),
        InlineKeyboardButton("📂 Playlist Download", callback_data="opt5"),
        InlineKeyboardButton("🔗 Direct Link (Large Files)", callback_data="opt6")
    )
    bot.reply_to(message, "📌 How do you want to download?", reply_markup=markup)

# ==============================
# Callback Queries (Menu Logic)
# ==============================
@bot.callback_query_handler(func=lambda call: True)
def process_callback(call):
    chat_id = call.message.chat.id
    action = call.data

    if chat_id not in user_data or 'url' not in user_data[chat_id]:
        bot.answer_callback_query(call.id, "❌ Session expired! Please send the link again.", show_alert=True)
        return

    url = user_data[chat_id]['url']

    if action == "opt3":
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("1080p", callback_data="res_1080"),
            InlineKeyboardButton("720p", callback_data="res_720"),
            InlineKeyboardButton("480p", callback_data="res_480"),
            InlineKeyboardButton("360p", callback_data="res_360")
        )
        bot.edit_message_text("🎬 Select video resolution:", chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
        return

    bot.edit_message_text("⏳ Processing your request... Please wait.", chat_id=chat_id, message_id=call.message.message_id)
    threading.Thread(target=download_and_send, args=(chat_id, action, url, call.message.message_id)).start()

# ==============================
# Core Downloading & Upload Logic
# ==============================
def download_and_send(chat_id, action, url, message_id):
    try:
        if action == "opt6":
            bot.edit_message_text("🔗 Generating direct link... Please wait.", chat_id=chat_id, message_id=message_id)
            ydl_opts_direct = {'format': 'best', 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts_direct) as ydl:
                info = ydl.extract_info(url, download=False)
                direct_url = info.get('url')
                title = info.get('title', 'Unknown Video')
                if direct_url:
                    msg = (f"🎬 <b>{title}</b>\n\n"
                           f"🔗 <b>Direct Download Link:</b>\n"
                           f"<a href='{direct_url}'>📥 Click here to Download</a>\n\n"
                           f"<i>⚠️ Use browser/ADM/IDM for full speed!</i>")
                    bot.send_message(chat_id, msg, parse_mode='HTML')
                else:
                    bot.send_message(chat_id, "❌ Could not fetch direct link.")
            bot.delete_message(chat_id, message_id)
            return

        ydl_opts = {
            'outtmpl': f'temp_{chat_id}_%(title)s.%(ext)s',
            'noplaylist': True,
            'quiet': True,
            'max_filesize': 50*1024*1024,
        }

        if action == "opt1":
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        elif action == "opt2":
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitleslangs'] = ['bn', 'bn.*', 'bn-BD']
            ydl_opts['postprocessors'] = [
                {'key':'FFmpegSubtitlesConvertor','format':'srt'},
                {'key':'FFmpegEmbedSubtitle'}
            ]
        elif action.startswith("res_"):
            res = action.split("_")[1]
            ydl_opts['format'] = f'bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/best[height<={res}][ext=mp4]/best'
        elif action == "opt4":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [
                {'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'},
                {'key':'EmbedThumbnail'}
            ]
            ydl_opts['writethumbnail'] = True
            ydl_opts['outtmpl'] = f'temp_{chat_id}_%(title)s.mp3'
        elif action == "opt5":
            bot.edit_message_text("📂 Scanning playlist... This may take a while.", chat_id=chat_id, message_id=message_id)
            ydl_opts['noplaylist'] = False
            ydl_opts['format'] = 'best[ext=mp4]/best'
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                bot.send_message(chat_id, "✅ Playlist download finished!")
                for entry in info['entries']:
                    if not entry: continue
                    filename = ydl.prepare_filename(entry)
                    send_file_to_telegram(chat_id, filename, is_audio=False)
            bot.delete_message(chat_id, message_id)
            return

        bot.edit_message_text("📥 Downloading file to server...", chat_id=chat_id, message_id=message_id)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if action == "opt4": filename = filename.rsplit('.',1)[0]+'.mp3'
            elif action == "opt2": filename = filename.rsplit('.',1)[0]+'.mp4'

        bot.edit_message_text("📤 Uploading file to Telegram...", chat_id=chat_id, message_id=message_id)
        is_audio = (action=="opt4")
        success = send_file_to_telegram(chat_id, filename, is_audio)
        if success:
            bot.delete_message(chat_id, message_id)
        else:
            bot.edit_message_text("❌ File >50MB! Use 'Direct Link' option.", chat_id=chat_id, message_id=message_id)

    except yt_dlp.utils.DownloadError as e:
        bot.send_message(chat_id, f"❌ Download error:\n{str(e)[:100]}")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Unexpected error:\n{str(e)[:100]}")

# ==============================
# Telegram File Sender
# ==============================
def send_file_to_telegram(chat_id, filename, is_audio=False):
    try:
        if os.path.getsize(filename) > 50*1024*1024:
            os.remove(filename)
            return False
        with open(filename,'rb') as file:
            if is_audio:
                bot.send_audio(chat_id, file, caption="🎵 Downloaded by Ultimate Downloader")
            else:
                bot.send_video(chat_id, file, caption="🎬 Downloaded by Ultimate Downloader")
        os.remove(filename)
        return True
    except:
        if os.path.exists(filename): os.remove(filename)
        return False

print("🤖 Ultimate Downloader Bot started successfully...")
bot.infinity_polling()
