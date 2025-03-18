import json
import os
import random
import requests
import sqlite3
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuration
TOKEN = "7627074947:AAEvryLAvAKkrVrI2UFY3EfTj1trkg5adeQ"
ADMIN = "1693155135"
DEV = "velovpn"
FORCED_CHANNEL = "DIGI_X"  # without @
BOT_USERNAME = "mahsoljmk_bot"

# Set timezone
os.environ['TZ'] = 'Asia/Tehran'

# Database setup
DB_FILE = "data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS files (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        file_id TEXT,
        content TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        files TEXT NOT NULL
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS folders (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        files TEXT NOT NULL
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    # Initialize step and caption if not exist
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('step', 'none')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('caption', '')")
    
    conn.commit()
    conn.close()

# Check if database exists, if not create it
if not os.path.exists(DB_FILE):
    init_db()

# Keyboards
MAIN_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton("☁️ آپلود رسانه ☁️"), KeyboardButton("📁 ایجاد پوشه 📁")],
    [KeyboardButton("🗂 مدیریت پوشه‌ها 🗂"), KeyboardButton("📞 ارتباط با ادمین 📞")],
], resize_keyboard=True)

UPLOAD_MENU = ReplyKeyboardMarkup([
    [KeyboardButton("اتمام")],
], resize_keyboard=True)

FOLDER_MENU = ReplyKeyboardMarkup([
    [KeyboardButton("➕ افزودن به پوشه"), KeyboardButton("➖ حذف از پوشه")],
    [KeyboardButton("🗑 حذف پوشه"), KeyboardButton("منوی اصلی")],
], resize_keyboard=True)

CONTACT_ADMIN_MENU = ReplyKeyboardMarkup([
    [KeyboardButton("منوی اصلی")],
], resize_keyboard=True)

async def check_channel_membership(user_id: str) -> str:
    url = f"https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id=@{FORCED_CHANNEL}&user_id={user_id}"
    response = requests.get(url)
    data = response.json()
    return data['result']['status'] if response.ok and data.get('ok') else 'left'

async def send_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, keyboard=None):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode='HTML',
        disable_web_page_preview=True,
        reply_markup=keyboard
    )

def get_setting(key):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def set_setting(key, value):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user_id = str(update.effective_user.id)
    text = update.message.text
    
    # Channel membership check
    status = await check_channel_membership(user_id)
    if status not in ['member', 'creator', 'administrator'] and user_id != ADMIN:
        await context.bot.send_message(
            chat_id=chat_id,
            text="لطفاً برای استفاده از ربات ابتدا در کانال @DIGI_X عضو شوید و سپس /start را بزنید",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("@DIGI_X", url=f"https://t.me/{FORCED_CHANNEL}")]
            ])
        )
        return
    
    # Handle session retrieval
    if text.startswith('/start session_'):
        session_id = text.replace('/start session_', '')
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT files FROM sessions WHERE id = ?", (session_id,))
        session_data = c.fetchone()
        if session_data:
            session_files = json.loads(session_data[0])
            c.execute("SELECT * FROM files")
            files_data = {row[0]: {'type': row[1], 'file_id': row[2], 'content': row[3]} for row in c.fetchall()}
            caption = get_setting('caption')
            
            for file in session_files:
                file_data = files_data.get(file['id'])
                if not file_data:
                    continue
                if file['type'] == 'photo' and file_data['file_id']:
                    await context.bot.send_photo(chat_id=chat_id, photo=file_data['file_id'], caption=caption)
                elif file['type'] == 'video' and file_data['file_id']:
                    await context.bot.send_video(chat_id=chat_id, video=file_data['file_id'], caption=caption)
                elif file['type'] == 'audio' and file_data['file_id']:
                    await context.bot.send_audio(chat_id=chat_id, audio=file_data['file_id'], caption=caption)
                elif file['type'] == 'document' and file_data['file_id']:
                    await context.bot.send_document(chat_id=chat_id, document=file_data['file_id'], caption=caption)
                elif file['type'] == 'animation' and file_data['file_id']:
                    await context.bot.send_animation(chat_id=chat_id, animation=file_data['file_id'], caption=caption)
                elif file['type'] == 'sticker' and file_data['file_id']:
                    await context.bot.send_sticker(chat_id=chat_id, sticker=file_data['file_id'])
                elif file['type'] == 'text' and file_data['content']:
                    await context.bot.send_message(chat_id=chat_id, text=file_data['content'])
        conn.close()
        return
    
    # Handle folder retrieval
    if text.startswith('/start folder_'):
        folder_id = text.replace('/start folder_', '')
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT files FROM folders WHERE id = ?", (folder_id,))
        folder_data = c.fetchone()
        if folder_data:
            folder_files = json.loads(folder_data[0])
            c.execute("SELECT * FROM files")
            files_data = {row[0]: {'type': row[1], 'file_id': row[2], 'content': row[3]} for row in c.fetchall()}
            caption = get_setting('caption')
            
            for file in folder_files:
                file_data = files_data.get(file['id'])
                if not file_data:
                    continue
                if file['type'] == 'photo' and file_data['file_id']:
                    await context.bot.send_photo(chat_id=chat_id, photo=file_data['file_id'], caption=caption)
                elif file['type'] == 'video' and file_data['file_id']:
                    await context.bot.send_video(chat_id=chat_id, video=file_data['file_id'], caption=caption)
                elif file['type'] == 'audio' and file_data['file_id']:
                    await context.bot.send_audio(chat_id=chat_id, audio=file_data['file_id'], caption=caption)
                elif file['type'] == 'document' and file_data['file_id']:
                    await context.bot.send_document(chat_id=chat_id, document=file_data['file_id'], caption=caption)
                elif file['type'] == 'animation' and file_data['file_id']:
                    await context.bot.send_animation(chat_id=chat_id, animation=file_data['file_id'], caption=caption)
                elif file['type'] == 'sticker' and file_data['file_id']:
                    await context.bot.send_sticker(chat_id=chat_id, sticker=file_data['file_id'])
                elif file['type'] == 'text' and file_data['content']:
                    await context.bot.send_message(chat_id=chat_id, text=file_data['content'])
        conn.close()
        return
    
    # Main menu
    if text in ["/start", "منوی اصلی"]:
        await send_message(update, context, "به ربات خوش آمدید!", MAIN_KEYBOARD)
        set_setting("step", "none")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user_id = str(update.effective_user.id)
    text = update.message.text if update.message.text else ""
    
    # Load step
    step = get_setting("step")

    # Upload media
    if text == "☁️ آپلود رسانه ☁️":
        if user_id != ADMIN:
            await send_message(update, context, "فقط ادمین می‌تواند فایل آپلود کند!")
            return
        session_id = str(random.randint(1000000, 9999999))
        set_setting("step", f"upload_{session_id}")
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO sessions (id, files) VALUES (?, ?)", (session_id, json.dumps([])))
        conn.commit()
        conn.close()
        await send_message(update, context, "فایل‌های خود را (عکس، ویدیو، موسیقی، سند، گیف، استیکر یا متن) ارسال کنید\nوقتی کارتان تمام شد دکمه 'اتمام' را بزنید", UPLOAD_MENU)

    elif step.startswith('upload_') and user_id == ADMIN:
        session_id = step.replace('upload_', '')
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT files FROM sessions WHERE id = ?", (session_id,))
        session_data = c.fetchone()
        if not session_data:
            conn.close()
            return
        session_files = json.loads(session_data[0])
        
        if text == "اتمام":
            link = f"https://t.me/{BOT_USERNAME}?start=session_{session_id}"
            await send_message(update, context, f"آپلود گروهی کامل شد!\nلینک دسترسی: {link}", MAIN_KEYBOARD)
            set_setting("step", "none")
        
        elif update.message.photo or update.message.video or update.message.audio or update.message.document or update.message.animation or update.message.sticker or update.message.text:
            rand = str(random.randint(1111111, 9999999))
            if update.message.photo:
                file_id = update.message.photo[-1].file_id
                c.execute("INSERT INTO files (id, type, file_id) VALUES (?, ?, ?)", (rand, 'photo', file_id))
                session_files.append({'type': 'photo', 'id': rand})
                await send_message(update, context, "عکس اضافه شد!", UPLOAD_MENU)
            elif update.message.video:
                file_id = update.message.video.file_id
                c.execute("INSERT INTO files (id, type, file_id) VALUES (?, ?, ?)", (rand, 'video', file_id))
                session_files.append({'type': 'video', 'id': rand})
                await send_message(update, context, "ویدیو اضافه شد!", UPLOAD_MENU)
            elif update.message.audio:
                file_id = update.message.audio.file_id
                c.execute("INSERT INTO files (id, type, file_id) VALUES (?, ?, ?)", (rand, 'audio', file_id))
                session_files.append({'type': 'audio', 'id': rand})
                await send_message(update, context, "موسیقی اضافه شد!", UPLOAD_MENU)
            elif update.message.document:
                file_id = update.message.document.file_id
                c.execute("INSERT INTO files (id, type, file_id) VALUES (?, ?, ?)", (rand, 'document', file_id))
                session_files.append({'type': 'document', 'id': rand})
                await send_message(update, context, "سند اضافه شد!", UPLOAD_MENU)
            elif update.message.animation:
                file_id = update.message.animation.file_id
                c.execute("INSERT INTO files (id, type, file_id) VALUES (?, ?, ?)", (rand, 'animation', file_id))
                session_files.append({'type': 'animation', 'id': rand})
                await send_message(update, context, "گیف اضافه شد!", UPLOAD_MENU)
            elif update.message.sticker:
                file_id = update.message.sticker.file_id
                c.execute("INSERT INTO files (id, type, file_id) VALUES (?, ?, ?)", (rand, 'sticker', file_id))
                session_files.append({'type': 'sticker', 'id': rand})
                await send_message(update, context, "استیکر اضافه شد!", UPLOAD_MENU)
            elif update.message.text:
                c.execute("INSERT INTO files (id, type, content) VALUES (?, ?, ?)", (rand, 'text', update.message.text))
                session_files.append({'type': 'text', 'id': rand})
                await send_message(update, context, "متن اضافه شد!", UPLOAD_MENU)
            c.execute("UPDATE sessions SET files = ? WHERE id = ?", (json.dumps(session_files), session_id))
            conn.commit()
        conn.close()

    # Create folder
    elif text == "📁 ایجاد پوشه 📁" and user_id == ADMIN:
        await send_message(update, context, "نام پوشه را وارد کنید:", UPLOAD_MENU)
        set_setting("step", "create_folder")

    elif step == "create_folder" and user_id == ADMIN and text != "اتمام":
        folder_id = str(random.randint(1000000, 9999999))
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO folders (id, name, files) VALUES (?, ?, ?)", (folder_id, text, json.dumps([])))
        conn.commit()
        conn.close()
        link = f"https://t.me/{BOT_USERNAME}?start=folder_{folder_id}"
        await send_message(update, context, f"پوشه '{text}' ایجاد شد!\nلینک: {link}", FOLDER_MENU)
        set_setting("step", f"folder_{folder_id}")

    # Manage folders
    elif text == "🗂 مدیریت پوشه‌ها 🗂" and user_id == ADMIN:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, name FROM folders")
        folders = c.fetchall()
        conn.close()
        if not folders:
            await send_message(update, context, "هیچ پوشه‌ای وجود ندارد!", MAIN_KEYBOARD)
            return
        
        folder_list = "لیست پوشه‌ها:\n"
        buttons = []
        for folder_id, folder_name in folders:
            folder_list += f"نام: {folder_name} | آیدی: {folder_id}\n"
            buttons.append([KeyboardButton(f"انتخاب پوشه {folder_name} ({folder_id})")])
        buttons.append([KeyboardButton("منوی اصلی")])
        
        await send_message(update, context, folder_list + "\nیک پوشه را برای مدیریت انتخاب کنید:", ReplyKeyboardMarkup(buttons, resize_keyboard=True))
        set_setting("step", "manage_folders")

    elif step == "manage_folders" and user_id == ADMIN:
        if text == "منوی اصلی":
            await send_message(update, context, "به منوی اصلی بازگشتید!", MAIN_KEYBOARD)
            set_setting("step", "none")
            return
        
        if text.startswith("انتخاب پوشه "):
            folder_info = text.replace("انتخاب پوشه ", "")
            folder_name = folder_info.split(" (")[0]
            folder_id = folder_info.split("(")[1].replace(")", "")
            
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT name FROM folders WHERE id = ?", (folder_id,))
            folder_data = c.fetchone()
            conn.close()
            if folder_data:
                await send_message(update, context, f"پوشه '{folder_data[0]}' انتخاب شد!", FOLDER_MENU)
                set_setting("step", f"folder_{folder_id}")
            else:
                await send_message(update, context, "پوشه یافت نشد!", MAIN_KEYBOARD)
                set_setting("step", "none")

    # Folder management
    elif step.startswith('folder_') and user_id == ADMIN:
        folder_id = step.replace('folder_', '')
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT name, files FROM folders WHERE id = ?", (folder_id,))
        folder_data = c.fetchone()
        if not folder_data:
            conn.close()
            await send_message(update, context, "پوشه یافت نشد! ممکن است پوشه ایجاد نشده باشد.", MAIN_KEYBOARD)
            set_setting("step", "none")
            return
        folder_name, folder_files = folder_data[0], json.loads(folder_data[1])
        conn.close()
        
        if text == "➕ افزودن به پوشه":
            await send_message(update, context, f"فایل‌ها را برای افزودن به پوشه '{folder_name}' بفرستید", UPLOAD_MENU)
            set_setting("step", f"add_to_folder_{folder_id}")
        
        elif text == "➖ حذف از پوشه":
            file_list = "فایل‌های موجود در پوشه:\n"
            if not folder_files:
                file_list += "هیچ فایلی در این پوشه وجود ندارد!"
            else:
                for file in folder_files:
                    file_type = "عکس" if file['type'] == 'photo' else "ویدیو" if file['type'] == 'video' else "موسیقی" if file['type'] == 'audio' else "سند" if file['type'] == 'document' else "گیف" if file['type'] == 'animation' else "استیکر" if file['type'] == 'sticker' else "متن"
                    file_list += f"- {file_type} | آیدی: {file['id']}\n"
            await send_message(update, context, file_list + "\nآیدی فایلی که می‌خواهید حذف کنید را وارد کنید:", UPLOAD_MENU)
            set_setting("step", f"remove_from_folder_{folder_id}")
        
        elif text == "🗑 حذف پوشه":
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
            conn.commit()
            conn.close()
            await send_message(update, context, f"پوشه '{folder_name}' با موفقیت حذف شد!", MAIN_KEYBOARD)
            set_setting("step", "none")
        
        elif text == "منوی اصلی":
            await send_message(update, context, "به منوی اصلی بازگشتید!", MAIN_KEYBOARD)
            set_setting("step", "none")

    elif step.startswith('add_to_folder_') and user_id == ADMIN:
        folder_id = step.replace('add_to_folder_', '')
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT name, files FROM folders WHERE id = ?", (folder_id,))
        folder_data = c.fetchone()
        if not folder_data:
            conn.close()
            await send_message(update, context, "پوشه یافت نشد! ممکن است پوشه حذف شده باشد.", MAIN_KEYBOARD)
            set_setting("step", "none")
            return
        folder_name, folder_files = folder_data[0], json.loads(folder_data[1])
        
        if text == "اتمام":
            link = f"https://t.me/{BOT_USERNAME}?start=folder_{folder_id}"
            await send_message(update, context, f"فایل‌ها به پوشه '{folder_name}' اضافه شدند!\nلینک: {link}", FOLDER_MENU)
            set_setting("step", f"folder_{folder_id}")
        
        elif update.message.photo or update.message.video or update.message.audio or update.message.document or update.message.animation or update.message.sticker or update.message.text:
            rand = str(random.randint(1111111, 9999999))
            if update.message.photo:
                file_id = update.message.photo[-1].file_id
                c.execute("INSERT INTO files (id, type, file_id) VALUES (?, ?, ?)", (rand, 'photo', file_id))
                folder_files.append({'type': 'photo', 'id': rand})
                await send_message(update, context, "عکس به پوشه اضافه شد!", UPLOAD_MENU)
            elif update.message.video:
                file_id = update.message.video.file_id
                c.execute("INSERT INTO files (id, type, file_id) VALUES (?, ?, ?)", (rand, 'video', file_id))
                folder_files.append({'type': 'video', 'id': rand})
                await send_message(update, context, "ویدیو به پوشه اضافه شد!", UPLOAD_MENU)
            elif update.message.audio:
                file_id = update.message.audio.file_id
                c.execute("INSERT INTO files (id, type, file_id) VALUES (?, ?, ?)", (rand, 'audio', file_id))
                folder_files.append({'type': 'audio', 'id': rand})
                await send_message(update, context, "موسیقی به پوشه اضافه شد!", UPLOAD_MENU)
            elif update.message.document:
                file_id = update.message.document.file_id
                c.execute("INSERT INTO files (id, type, file_id) VALUES (?, ?, ?)", (rand, 'document', file_id))
                folder_files.append({'type': 'document', 'id': rand})
                await send_message(update, context, "سند به پوشه اضافه شد!", UPLOAD_MENU)
            elif update.message.animation:
                file_id = update.message.animation.file_id
                c.execute("INSERT INTO files (id, type, file_id) VALUES (?, ?, ?)", (rand, 'animation', file_id))
                folder_files.append({'type': 'animation', 'id': rand})
                await send_message(update, context, "گیف به پوشه اضافه شد!", UPLOAD_MENU)
            elif update.message.sticker:
                file_id = update.message.sticker.file_id
                c.execute("INSERT INTO files (id, type, file_id) VALUES (?, ?, ?)", (rand, 'sticker', file_id))
                folder_files.append({'type': 'sticker', 'id': rand})
                await send_message(update, context, "استیکر به پوشه اضافه شد!", UPLOAD_MENU)
            elif update.message.text:
                c.execute("INSERT INTO files (id, type, content) VALUES (?, ?, ?)", (rand, 'text', update.message.text))
                folder_files.append({'type': 'text', 'id': rand})
                await send_message(update, context, "متن به پوشه اضافه شد!", UPLOAD_MENU)
            c.execute("UPDATE folders SET files = ? WHERE id = ?", (json.dumps(folder_files), folder_id))
            conn.commit()
        conn.close()

    elif step.startswith('remove_from_folder_') and user_id == ADMIN:
        folder_id = step.replace('remove_from_folder_', '')
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT name, files FROM folders WHERE id = ?", (folder_id,))
        folder_data = c.fetchone()
        if not folder_data:
            conn.close()
            await send_message(update, context, "پوشه یافت نشد!", MAIN_KEYBOARD)
            set_setting("step", "none")
            return
        folder_name, folder_files = folder_data[0], json.loads(folder_data[1])
        
        if text == "اتمام":
            await send_message(update, context, f"ویرایش پوشه '{folder_name}' کامل شد!", FOLDER_MENU)
            set_setting("step", f"folder_{folder_id}")
        
        elif text.isdigit():
            found = False
            for i, file in enumerate(folder_files):
                if file['id'] == text:
                    folder_files.pop(i)
                    found = True
                    break
            if found:
                c.execute("UPDATE folders SET files = ? WHERE id = ?", (json.dumps(folder_files), folder_id))
                conn.commit()
                await send_message(update, context, f"فایل با آیدی {text} از پوشه حذف شد!", UPLOAD_MENU)
            else:
                await send_message(update, context, f"فایل با آیدی {text} در این پوشه یافت نشد!", UPLOAD_MENU)
        conn.close()

    # Contact admin
    elif text == "📞 ارتباط با ادمین 📞":
        await send_message(update, context, "پیام خود را برای ادمین ارسال کنید:", CONTACT_ADMIN_MENU)
        set_setting("step", f"contact_admin_{user_id}")
    
    elif step.startswith('contact_admin_') and text != "منوی اصلی":
        sender_id = step.replace('contact_admin_', '')
        await context.bot.send_message(
            chat_id=ADMIN,
            text=f"پیام از کاربر {sender_id}:\n{text}"
        )
        await send_message(update, context, "پیام شما به ادمین ارسال شد!", MAIN_KEYBOARD)
        set_setting("step", "none")
    
    elif step.startswith('contact_admin_') and text == "منوی اصلی":
        await send_message(update, context, "به منوی اصلی بازگشتید!", MAIN_KEYBOARD)
        set_setting("step", "none")

def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.Document.ALL | filters.ANIMATION | filters.Sticker.ALL, handle_message))
    
    application.run_polling()

if __name__ == '__main__':
    main()

