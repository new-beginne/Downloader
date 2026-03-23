import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import threading
from flask import Flask # Render এর জন্য নতুন যুক্ত করা হলো

# আপনার BotFather থেকে পাওয়া টোকেন (এখন এটি Render এর Environment Variable থেকে নেবে)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# ইউজারদের লিংক সাময়িকভাবে সেভ রাখার জন্য ডিকশনারি
user_data = {}

# ==============================
# Start & Message Handler
# ==============================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # স্বাগতম মেসেজ (ইংরেজিতে)
    bot.reply_to(message, "👋 Welcome! I am Ultimate Downloader Bot.\n\n🔗 Please send me any video or playlist link to start.")

@bot.message_handler(func=lambda message: message.text.startswith('http'))
def handle_link(message):
    chat_id = message.chat.id
    url = message.text
    
    # লিংক মেমোরিতে সেভ করা
    user_data[chat_id] = {'url': url}
    
    # মেইন মেনু কীবোর্ড (সব বাটন ইংরেজিতে)
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("⚡ Auto Best Quality (No Sub)", callback_data="opt1"),
        InlineKeyboardButton("🇧🇩 Auto Best + Bangla Subtitle", callback_data="opt2"),
        InlineKeyboardButton("🎬 Choose Quality Manually", callback_data="opt3"),
        InlineKeyboardButton("🎵 Audio Only (MP3)", callback_data="opt4"),
        InlineKeyboardButton("📂 Playlist Download", callback_data="opt5"),
        InlineKeyboardButton("🔗 Direct Link (For 10GB+ / Large Files)", callback_data="opt6")
    )
    
    bot.reply_to(message, "📌 How do you want to download?", reply_markup=markup)

# ==============================
# Callback Queries (Menu Logic)
# ==============================
@bot.callback_query_handler(func=lambda call: True)
def process_callback(call):
    chat_id = call.message.chat.id
    action = call.data
    
    # লিংক খুঁজে না পেলে এরর মেসেজ
    if chat_id not in user_data or 'url' not in user_data[chat_id]:
        bot.answer_callback_query(call.id, "❌ Session expired! Please send the link again.", show_alert=True)
        return

    url = user_data[chat_id]['url']

    # ম্যানুয়াল কোয়ালিটি মেনু
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

    # প্রসেসিং মেসেজ
    bot.edit_message_text("⏳ Processing your request... Please wait.", chat_id=chat_id, message_id=call.message.message_id)
    threading.Thread(target=download_and_send, args=(chat_id, action, url, call.message.message_id)).start()

# ==============================
# Core Downloading & Link Fetching Logic
# ==============================
def download_and_send(chat_id, action, url, message_id):
    try:
        # ৬. ডাইরেক্ট ডাউনলোড লিংক লজিক
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
                           f"<i>⚠️ Note: Copy this link to ADM (Mobile), IDM (PC), or any browser to download at full speed!</i>")
                    bot.send_message(chat_id, msg, parse_mode='HTML')
                else:
                    bot.send_message(chat_id, "❌ Could not fetch direct link for this video.")
            bot.delete_message(chat_id, message_id)
            return

        # ডাউনলোডের সেটিংস
        ydl_opts = {
            'outtmpl': f'temp_{chat_id}_%(title)s.%(ext)s',
            'noplaylist': True,
            'quiet': True,
            'max_filesize': 50 * 1024 * 1024, # টেলিগ্রামের ৫০ এমবি লিমিট
        }
        
        if action == "opt1":
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        
        elif action == "opt2":
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitleslangs'] =['bn', 'bn.*', 'bn-BD']
            ydl_opts['postprocessors'] =[
                {'key': 'FFmpegSubtitlesConvertor', 'format': 'srt'},
                {'key': 'FFmpegEmbedSubtitle'}
            ]
        
        elif action.startswith("res_"):
            res = action.split("_")[1]
            ydl_opts['format'] = f'bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/best[height<={res}][ext=mp4]/best'
        
        elif action == "opt4":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] =[
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
                {'key': 'EmbedThumbnail'}
            ]
            ydl_opts['writethumbnail'] = True
            ydl_opts['outtmpl'] = f'temp_{chat_id}_%(title)s.mp3'
        
        elif action == "opt5":
            bot.edit_message_text("📂 Scanning playlist... This may take a while.", chat_id=chat_id, message_id=message_id)
            ydl_opts['noplaylist'] = False
            ydl_opts['format'] = 'best[ext=mp4]/best'
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                bot.send_message(chat_id, f"✅ Playlist download finished! Uploading files...")
                for entry in info['entries']:
                    if not entry: continue
                    filename = ydl.prepare_filename(entry)
                    send_file_to_telegram(chat_id, filename, is_audio=False)
            bot.delete_message(chat_id, message_id)
            return

        # ডাউনলোড শুরু করার মেসেজ
        bot.edit_message_text("📥 Downloading file to server...", chat_id=chat_id, message_id=message_id)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if action == "opt4":
                filename = filename.rsplit('.', 1)[0] + '.mp3'
            elif action == "opt2":
                filename = filename.rsplit('.', 1)[0] + '.mp4'

        # আপলোড শুরু করার মেসেজ
        bot.edit_message_text("📤 Uploading file to Telegram...", chat_id=chat_id, message_id=message_id)
        
        is_audio = (action == "opt4")
        success = send_file_to_telegram(chat_id, filename, is_audio)
        
        if success:
            bot.delete_message(chat_id, message_id)
        else:
            bot.edit_message_text("❌ File is larger than 50MB. Please use 'Direct Link' option.", chat_id=chat_id, message_id=message_id)

    except yt_dlp.utils.DownloadError as e:
        if 'File is larger than max-filesize' in str(e):
            bot.edit_message_text("❌ File size is over 50MB! Please use option 6 'Direct Link'.", chat_id=chat_id, message_id=message_id)
        else:
            bot.send_message(chat_id, f"❌ An error occurred:\n{str(e)[:100]}...")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Something went wrong:\n{str(e)[:100]}...")

# ==============================
# Telegram File Sender
# ==============================
def send_file_to_telegram(chat_id, filename, is_audio=False):
    try:
        # ফাইল সাইজ ৫০ এমবি এর বেশি কি না চেক
        if os.path.getsize(filename) > 50 * 1024 * 1024:
            os.remove(filename)
            return False
            
        with open(filename, 'rb') as file:
            if is_audio:
                bot.send_audio(chat_id, file, caption="🎵 Downloaded by Ultimate Downloader")
            else:
                bot.send_video(chat_id, file, caption="🎬 Downloaded by Ultimate Downloader")
        
        # আপলোড শেষে ফাইল ডিলেট করা
        os.remove(filename)
        return True
    except:
        if os.path.exists(filename): os.remove(filename)
        return False

# ==============================
# Render Dummy Web Server & App Start
# ==============================
app = Flask(__name__)

@app.route('/')
def home():
    return "Ultimate Downloader Bot is running perfectly on Render!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # ওয়েব সার্ভার ব্যাকগ্রাউন্ডে রান করা (Render কে খুশি রাখতে)
    threading.Thread(target=run_web).start()
    
    # আপনার টেলিগ্রাম বট রান করা
    print("🤖 Ultimate Downloader Bot is running...")
    bot.infinity_polling()
