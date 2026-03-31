from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, ConversationHandler, MessageHandler, filters
)
import subprocess
import os
import re
from urllib.parse import quote

# 🔴 BOT TOKEN
BOT_TOKEN = "8798827383:AAGUC1EY5Yx4us1t2CkPNayZ0HfKI6gItoc"

DOWNLOAD_FOLDER = "/storage/emulated/0/Download/music_videos"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Store user share counts
user_shares = {}          # user_id -> count (0-4)
verified_users = set()    # user_id -> True after 4 shares

# Conversation states
SEARCH_QUERY, SELECT_VIDEO, SELECT_QUALITY = range(3)

# Temporary storage for search results
user_search_results = {}

def get_share_keyboard(user_id):
    """Create inline keyboard for sharing"""
    count = user_shares.get(user_id, 0)
    button = InlineKeyboardButton(f"✅ Share with a friend ({count}/4)", callback_data="share")
    keyboard = [[button]]
    if count >= 4:
        keyboard.append([InlineKeyboardButton("✅ I have shared 4 times", callback_data="share_done")])
    return InlineKeyboardMarkup(keyboard)

def get_quality_keyboard(video_url):
    """Create inline keyboard for quality selection"""
    qualities = [
        ("Best", "best"),
        ("720p", "720"),
        ("480p", "480"),
        ("360p", "360")
    ]
    keyboard = [
        [InlineKeyboardButton(q, callback_data=f"quality_{code}_{video_url}")]
        for q, code in qualities
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(
        "🔥 *DarkX Bot* iko live!\n\n"
        "📌 *Commands:*\n"
        "/start - Ona ujumbe huu\n"
        "/share - Kamilisha share ili upate ruhusa ya kudownload\n"
        "/download <url> - Download video moja kwa moja (baada ya share)\n"
        "/search <jina> - Tafuta video\n"
        "/status - Angalia hali ya share zako\n\n"
        "⚠️ *Kabla ya kutumia, lazima ushiriki bot hii kwa marafiki 4.*",
        parse_mode="Markdown",
        reply_markup=get_share_keyboard(user_id)
    )

async def share_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show share progress and buttons"""
    user_id = update.effective_user.id
    await update.message.reply_text(
        "🔁 *Share Requirement*\n\n"
        "Ili upate ruhusa ya kudownload, wasiliana na marafiki wako na uwape bot hii.\n"
        "Bonyeza kitufe cha 'Share with a friend' baada ya kushiriki kwa kila mmoja.\n"
        "Ukimaliza mara 4, utapata uwezo wa kudownload.",
        parse_mode="Markdown",
        reply_markup=get_share_keyboard(user_id)
    )

async def share_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    data = query.data

    if data == "share":
        count = user_shares.get(user_id, 0) + 1
        if count > 4:
            count = 4
        user_shares[user_id] = count
        if count == 4:
            verified_users.add(user_id)
            await query.edit_message_text(
                "✅ Hongera! Umeisha share mara 4. Sasa una ruhusa ya kudownload.\n"
                "Tumia /download au /search kuanza.",
                reply_markup=None
            )
        else:
            await query.edit_message_text(
                f"✅ Umeshare mara {count}/4. Endelea kushiriki na marafiki zako.\n"
                f"Baada ya kushare, bonyeza tena kitufe.",
                reply_markup=get_share_keyboard(user_id)
            )
    elif data == "share_done":
        if user_shares.get(user_id, 0) >= 4:
            verified_users.add(user_id)
            await query.edit_message_text(
                "✅ Sasa una ruhusa ya kudownload! Tumia /download au /search.",
                reply_markup=None
            )
        else:
            await query.edit_message_text(
                "❌ Bado hujakamilisha share zote 4. Bonyeza kitufe cha 'Share with a friend' mara 4.",
                reply_markup=get_share_keyboard(user_id)
            )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    count = user_shares.get(user_id, 0)
    if count >= 4:
        await update.message.reply_text("✅ Umekamilisha share zote 4! Unaweza kudownload.")
    else:
        await update.message.reply_text(
            f"📊 Hali ya share: {count}/4.\n"
            "Bonyeza /share ili uone kitufe cha kushare.",
            reply_markup=get_share_keyboard(user_id)
        )

def check_share(user_id):
    return user_id in verified_users or user_shares.get(user_id, 0) >= 4

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_share(user_id):
        await update.message.reply_text(
            "⚠️ Kabla ya kudownload, lazima ushiriki bot hii kwa marafiki 4.\n"
            "Tumia /share kuanza.",
            reply_markup=get_share_keyboard(user_id)
        )
        return

    if not context.args:
        await update.message.reply_text("❌ Tumia:\n/download <url>\n\nMfano: /download https://youtu.be/...")
        return

    url = context.args[0]
    # Check if user wants specific quality
    quality = "best"
    if len(context.args) > 1:
        qual = context.args[1].lower()
        if qual in ["best", "720", "480", "360"]:
            quality = qual

    await update.message.reply_text(f"⏳ Inadownload... ({quality})")

    try:
        # Download with yt-dlp
        before_files = set(os.listdir(DOWNLOAD_FOLDER))
        cmd = [
            "yt-dlp",
            "-f", f"best[height<={quality}]" if quality != "best" else "best",
            "-o", f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s",
            url
        ]
        subprocess.run(cmd, check=True)

        after_files = set(os.listdir(DOWNLOAD_FOLDER))
        new_files = list(after_files - before_files)

        if not new_files:
            await update.message.reply_text("❌ Imeshindwa kupata file.")
            return

        file_path = os.path.join(DOWNLOAD_FOLDER, new_files[0])

        await update.message.reply_text("📤 Inatuma file...")

        with open(file_path, "rb") as f:
            await update.message.reply_document(document=f, filename=os.path.basename(file_path))

        # After success, send thank you with WhatsApp channel
        await update.message.reply_text(
            "✅ Imemaliza!\n\n"
            "Asante kwa kutumia *DarkX Bot*! ❤️\n"
            "Jiunge na WhatsApp Channel yetu kwa maboresho na mafunzo zaidi:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📱 Jiunge WhatsApp Channel", url="https://whatsapp.com/channel/0029VbCdURHH5JM4JJHYAo2X")]
            ])
        )

        # Cleanup: delete file after sending
        os.remove(file_path)

    except Exception as e:
        await update.message.reply_text(f"❌ Hitilafu: {e}")

# Search functionality
async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_share(user_id):
        await update.message.reply_text(
            "⚠️ Kabla ya kutafuta, lazima ushiriki bot hii kwa marafiki 4.\n"
            "Tumia /share kuanza.",
            reply_markup=get_share_keyboard(user_id)
        )
        return ConversationHandler.END

    if not context.args:
        await update.message.reply_text("❌ Tumia:\n/search <jina la video>")
        return ConversationHandler.END

    query = " ".join(context.args)
    await update.message.reply_text("🔍 Inatafuta...")
    try:
        # Use yt-dlp to search
        result = subprocess.run(
            ["yt-dlp", f"ytsearch5:{query}", "--get-id", "--get-title"],
            capture_output=True, text=True, check=True
        )
        lines = result.stdout.strip().split("\n")
        if not lines or len(lines) < 2:
            await update.message.reply_text("❌ Hakuna matokeo.")
            return ConversationHandler.END

        # Parse titles and ids
        videos = []
        for i in range(0, len(lines), 2):
            if i+1 < len(lines):
                title = lines[i].strip()
                vid = lines[i+1].strip()
                videos.append((title, vid))

        if not videos:
            await update.message.reply_text("❌ Hakuna matokeo.")
            return ConversationHandler.END

        # Store results in user context
        context.user_data["search_results"] = videos
        # Build inline keyboard
        keyboard = []
        for idx, (title, vid) in enumerate(videos):
            keyboard.append([InlineKeyboardButton(f"{idx+1}. {title[:40]}", callback_data=f"select_{idx}")])
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_search")])
        await update.message.reply_text(
            "📋 Chagua video unayotaka:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECT_VIDEO

    except Exception as e:
        await update.message.reply_text(f"❌ Hitilafu wakati wa kutafuta: {e}")
        return ConversationHandler.END

async def select_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "cancel_search":
        await query.edit_message_text("❌ Umesitisha utafutaji.")
        return ConversationHandler.END

    if data.startswith("select_"):
        idx = int(data.split("_")[1])
        videos = context.user_data.get("search_results", [])
        if idx >= len(videos):
            await query.edit_message_text("❌ Video haipo.")
            return ConversationHandler.END

        title, video_id = videos[idx]
        video_url = f"https://youtu.be/{video_id}"
        context.user_data["selected_video"] = video_url
        # Ask for quality
        await query.edit_message_text(
            f"🎬 *{title}*\n\nSasa chagua ubora unaotaka:",
            parse_mode="Markdown",
            reply_markup=get_quality_keyboard(video_url)
        )
        return SELECT_QUALITY

async def select_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("quality_"):
        parts = data.split("_", 2)
        quality_code = parts[1]
        video_url = parts[2]

        # Perform download
        await query.edit_message_text(f"⏳ Inadownload... ({quality_code})")

        try:
            before_files = set(os.listdir(DOWNLOAD_FOLDER))
            quality_map = {
                "best": "best",
                "720": "best[height<=720]",
                "480": "best[height<=480]",
                "360": "best[height<=360]"
            }
            fmt = quality_map.get(quality_code, "best")

            cmd = [
                "yt-dlp",
                "-f", fmt,
                "-o", f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s",
                video_url
            ]
            subprocess.run(cmd, check=True)

            after_files = set(os.listdir(DOWNLOAD_FOLDER))
            new_files = list(after_files - before_files)

            if not new_files:
                await query.edit_message_text("❌ Imeshindwa kupata file.")
                return ConversationHandler.END

            file_path = os.path.join(DOWNLOAD_FOLDER, new_files[0])

            # Send file
            await query.message.reply_text("📤 Inatuma file...")
            with open(file_path, "rb") as f:
                await query.message.reply_document(document=f, filename=os.path.basename(file_path))

            # Thank you message with WhatsApp channel
            await query.message.reply_text(
                "✅ Imemaliza!\n\n"
                "Asante kwa kutumia *DarkX Bot*! ❤️\n"
                "Jiunge na WhatsApp Channel yetu kwa maboresho na mafunzo zaidi:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📱 Jiunge WhatsApp Channel", url="https://whatsapp.com/channel/0029VbCdURHH5JM4JJHYAo2X")]
                ])
            )

            # Cleanup
            os.remove(file_path)
            await query.edit_message_reply_markup(reply_markup=None)  # remove keyboard
            return ConversationHandler.END

        except Exception as e:
            await query.edit_message_text(f"❌ Hitilafu: {e}")
            return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Umesitisha.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("share", share_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("download", download))

    # Conversation handler for search
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("search", search_start)],
        states={
            SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_start)],  # not used directly
            SELECT_VIDEO: [CallbackQueryHandler(select_video, pattern="^(select_|cancel_search)")],
            SELECT_QUALITY: [CallbackQueryHandler(select_quality, pattern="^quality_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)

    # Share callback handler
    app.add_handler(CallbackQueryHandler(share_callback, pattern="^(share|share_done)$"))

    app.run_polling()

if __name__ == "__main__":
    main()
