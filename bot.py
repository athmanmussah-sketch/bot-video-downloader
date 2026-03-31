from flask import Flask
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, ConversationHandler, MessageHandler, filters
)
import subprocess
import os

# 🔐 TOKEN (Inapendekezwa kutumia Environment Variables kwa usalama zaidi)
BOT_TOKEN = "8798827383:AAGUC1EY5Yx4us1t2CkPNayZ0HfKI6gItoc"

# 📁 Cloud safe folder
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# 🔁 Share system (Kumbuka: Data hizi hupotea Render ikijizima/ikirestart)
user_shares = {}
verified_users = set()

SEARCH_QUERY, SELECT_VIDEO, SELECT_QUALITY = range(3)

# ================= FLASK SERVER (Kwa ajili ya Render) =================
app = Flask(__name__)

@app.route('/')
def health_check():
    return "DarkX Bot is running!", 200

def run_flask():
    # Render hutoa PORT yenyewe, tuseme 10000 kama haipo
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ================= BOT FUNCTIONS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 *DarkX Bot iko live!*\n\n"
        "/search <jina> - Tafuta video\n"
        "/download <url> - Download direct\n"
        "/status - Angalia hali ya bot",
        parse_mode="Markdown"
    )

def check_share(user_id):
    return user_id in verified_users or user_shares.get(user_id, 0) >= 4

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_share(user_id):
        await update.message.reply_text("⚠️ Lazima ushare mara 4 kwanza.")
        return
    if not context.args:
        await update.message.reply_text("Tumia: /download <url>")
        return

    url = context.args[0]
    await update.message.reply_text("⏳ Inadownload...")

    try:
        before = set(os.listdir(DOWNLOAD_FOLDER))
        subprocess.run([
            "yt-dlp", "-f", "best",
            "-o", f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s", url
        ], check=True)
        
        after = set(os.listdir(DOWNLOAD_FOLDER))
        new_files = list(after - before)

        if not new_files:
            await update.message.reply_text("❌ Hakuna file limepatikana.")
            return

        file_path = os.path.join(DOWNLOAD_FOLDER, new_files[0])
        await update.message.reply_text("📤 Inatuma file...")
        
        with open(file_path, "rb") as f:
            await update.message.reply_document(document=f)
        os.remove(file_path)
        await update.message.reply_text("✅ Imemaliza!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Tumia: /search <jina>")
        return
    query = " ".join(context.args)
    await update.message.reply_text("🔍 Inatafuta...")
    try:
        result = subprocess.run(
            ["yt-dlp", f"ytsearch5:{query}", "--get-title", "--get-id"],
            capture_output=True, text=True, check=True
        )
        lines = result.stdout.strip().split("\n")
        videos = []
        for i in range(0, len(lines), 2):
            if i + 1 < len(lines):
                videos.append((lines[i], lines[i+1]))

        if not videos:
            await update.message.reply_text("❌ Hakuna matokeo.")
            return

        keyboard = [[InlineKeyboardButton(v[0][:40], callback_data=f"vid_{v[1]}")] for v in videos]
        await update.message.reply_text("📋 Chagua video:", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def video_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    video_id = query.data.replace("vid_", "")
    url = f"https://youtu.be/{video_id}"
    keyboard = [
        [InlineKeyboardButton("Best", callback_data=f"q_best_{url}")],
        [InlineKeyboardButton("720p", callback_data=f"q_720_{url}")],
        [InlineKeyboardButton("480p", callback_data=f"q_480_{url}")]
    ]
    await query.edit_message_text("Chagua quality:", reply_markup=InlineKeyboardMarkup(keyboard))

async def quality_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_", 2)
    quality, url = data[1], data[2]
    await query.edit_message_text("⏳ Inadownload...")
    try:
        before = set(os.listdir(DOWNLOAD_FOLDER))
        quality_map = {"best": "best", "720": "best[height<=720]", "480": "best[height<=480]"}
        fmt = quality_map.get(quality, "best")
        subprocess.run(["yt-dlp", "-f", fmt, "-o", f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s", url], check=True)
        after = set(os.listdir(DOWNLOAD_FOLDER))
        new_files = list(after - before)
        file_path = os.path.join(DOWNLOAD_FOLDER, new_files[0])
        await query.message.reply_text("📤 Inatuma file...")
        with open(file_path, "rb") as f:
            await query.message.reply_document(document=f)
        os.remove(file_path)
        await query.message.reply_text("✅ Imemaliza!")
    except Exception as e:
        await query.message.reply_text(f"❌ Error: {e}")

# ================= MAIN =================
def main():
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("download", download))
    bot_app.add_handler(CommandHandler("search", search))
    bot_app.add_handler(CallbackQueryHandler(video_select, pattern="^vid_"))
    bot_app.add_handler(CallbackQueryHandler(quality_select, pattern="^q_"))
    
    print("Bot is starting...")
    bot_app.run_polling()

if __name__ == "__main__":
    # 1. Washa Flask kwenye thread ya pembeni (Background)
    threading.Thread(target=run_flask, daemon=True).start()
    
    # 2. Washa Telegram Bot
    main()
