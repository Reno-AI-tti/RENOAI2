import os
import json
import requests
import re
import logging
import sqlite3
from datetime import datetime
import nest_asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Enable nest_asyncio
nest_asyncio.apply()

# Telegram Bot Token
TELEGRAM_TOKEN = '7904967711:AAEQ6vOYMYGVXfpOT99ZeBFUirTWWNNQAoA'
# Hugging Face API Token
HUGGINGFACE_TOKEN = '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'
# Hugging Face API URL
HUGGINGFACE_URL = 'https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-3.5-large-turbo'
# Private Channel ID for Plan Approval
PRIVATE_CHANNEL_ID = -1002627331515
# Required Channel ID
REQUIRED_CHANNEL_ID = -1002614804675
# Required Channel Link
CHANNEL_LINK = 'https://t.me/+QL1kF-t4LoVhODlk'
# Admin ID
ADMIN_ID = 1693155135

# Database file
DB_FILE = 'reno.db'

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    language TEXT,
                    plan TEXT,
                    photo_count INTEGER,
                    last_reset TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS pending (
                    user_id INTEGER PRIMARY KEY,
                    plan TEXT,
                    message_id INTEGER)''')
    conn.commit()
    conn.close()

if not os.path.exists(DB_FILE):
    init_db()

# Language-specific messages
MESSAGES = {
    'en': {
        'welcome': "🌟 Welcome! Please choose your language:\n\n",
        'menu': "📋 Main Menu:",
        'generate_image': "🎨 Generate Image",
        'generate_another': "🎨 Generate Another Image",
        'change_plan': "📦 Change Plan",
        'change_language': "🌐 Change Language",
        'help': "📖 Help",
        'help_text': "📖 Help:\n\n✅ Use '🎨 Generate Image' or commands like `photo (prompt)`, `img (prompt)` to create images. You can use English or Persian prompts!",
        'waiting_prompt': "✍️ Please enter the prompt for your image (English or Persian):",
        'processing': "⏳ Generating image...",
        'error_image': "❌ Error generating image. Please try again.",
        'error_translation': "❌ Error translating text. Please try again.",
        'choose_plan': "📦 Choose a subscription plan:",
        'free_plan': "🆓 Free Plan",
        'standard_plan': "📈 Standard Plan",
        'pro_plan': "🌟 Pro Plan",
        'free_plan_desc': "🆓 Free Plan:\n- 5 images per day\n\n[Buy] to activate | [Cancel]",
        'standard_plan_desc': "📈 Standard Plan:\n- 30 images per day\n- Requires a selfie\n\n[Buy] to proceed | [Cancel]",
        'pro_plan_desc': "🌟 Pro Plan:\n- Unlimited images per day\n- Requires a video message saying 'Please activate my Pro Plan'\n\n[Buy] to proceed | [Cancel]",
        'current_plan': "📋 Your current plan: {plan}\nImages remaining today: {remaining}",
        'limit_reached': "🚫 You've reached your daily limit ({limit}). Upgrade your plan!",
        'send_selfie': "📸 Please send a selfie to activate the Standard Plan.\n[Cancel]",
        'send_video': "🎥 Please send a video message saying 'Please activate my Pro Plan'.\n[Cancel]",
        'pending': "⏳ Your request is pending approval.",
        'approved': "✅ Your {plan} plan has been activated!",
        'rejected': "❌ Your {plan} request was rejected.",
        'join_channel': "🔒 To use the bot, please join our channel:\n[RENO AI]({link})\n\nThen press 'Check Membership'",
        'check_membership': "✅ Check Membership",
        'not_member': "❌ You are not a member of the channel. Please join first!",
        'plan_active': "⚠️ You already have an active plan ({plan}). Upgrade to a higher plan if needed!"
    },
    'fa': {
        'welcome': "🌟 خوش آمدید! لطفاً زبان خود را انتخاب کنید:\n\n",
        'menu': "📋 منوی اصلی:",
        'generate_image': "🎨 تولید تصویر",
        'generate_another': "🎨 تولید تصویر دیگر",
        'change_plan': "📦 تغییر پلن",
        'change_language': "🌐 تغییر زبان",
        'help': "📖 راهنما",
        'help_text': "📖 راهنما:\n\n✅ از '🎨 تولید تصویر' یا دستوراتی مثل `عکس (پرامپت)`، `تصویر (پرامپت)` استفاده کنید. می‌توانید از پرامپت فارسی یا انگلیسی استفاده کنید!",
        'waiting_prompt': "✍️ لطفاً متن پرامپت خود را برای تصویر وارد کنید (فارسی یا انگلیسی):",
        'processing': "⏳ در حال تولید تصویر...",
        'error_image': "❌ خطا در تولید تصویر. لطفاً دوباره امتحان کنید.",
        'error_translation': "❌ خطا در ترجمه متن. لطفاً دوباره امتحان کنید.",
        'choose_plan': "📦 یک پلن اشتراک انتخاب کنید:",
        'free_plan': "🆓 پلن رایگان",
        'standard_plan': "📈 پلن استاندارد",
        'pro_plan': "🌟 پلن حرفه‌ای",
        'free_plan_desc': "🆓 پلن رایگان:\n- ۵ تصویر در روز\n\n[خرید] برای فعال‌سازی | [لغو]",
        'standard_plan_desc': "📈 پلن استاندارد:\n- ۳۰ تصویر در روز\n- نیاز به ارسال سلفی\n\n[خرید] برای ادامه | [لغو]",
        'pro_plan_desc': "🌟 پلن حرفه‌ای:\n- بدون محدودیت روزانه\n- نیاز به پیام ویدیویی با گفتن 'لطفاً پلن حرفه‌ای من را فعال کنید'\n\n[خرید] برای ادامه | [لغو]",
        'current_plan': "📋 پلن فعلی شما: {plan}\nتعداد تصاویر باقی‌مانده امروز: {remaining}",
        'limit_reached': "🚫 شما به محدودیت روزانه خود ({limit}) رسیده‌اید. پلن خود را ارتقا دهید!",
        'send_selfie': "📸 لطفاً یک سلفی برای فعال‌سازی پلن استاندارد ارسال کنید.\n[لغو]",
        'send_video': "🎥 لطفاً یک پیام ویدیویی با گفتن 'لطفاً پلن حرفه‌ای من را فعال کنید' ارسال کنید.\n[لغو]",
        'pending': "⏳ درخواست شما در انتظار تأیید است.",
        'approved': "✅ پلن {plan} شما فعال شد!",
        'rejected': "❌ درخواست {plan} شما رد شد。",
        'join_channel': "🔒 برای استفاده از ربات، لطفاً در کانال ما عضو شوید:\n[RENO AI]({link})\n\nسپس دکمه 'بررسی عضویت' را فشار دهید",
        'check_membership': "✅ بررسی عضویت",
        'not_member': "❌ شما عضو کانال نیستید. لطفاً ابتدا عضو شوید!",
        'plan_active': "⚠️ شما در حال حاضر پلن فعالی ({plan}) دارید. در صورت نیاز به پلن بالاتر ارتقا دهید!"
    }
}

# Check if text is English
def is_english(text):
    return bool(re.match(r'^[A-Za-z0-9\s.,!?]+$', text))

# Translate text using MyMemory API
def translate_text(text, source_lang, target_lang):
    url = f"https://api.mymemory.translated.net/get?q={text}&langpair={source_lang}|{target_lang}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get('responseData', {}).get('translatedText', '')
    return ''

# Generate image using Hugging Face API
def generate_image(prompt):
    headers = {'Authorization': f'Bearer {HUGGINGFACE_TOKEN}', 'Content-Type': 'application/json'}
    data = json.dumps({'inputs': prompt})
    response = requests.post(HUGGINGFACE_URL, headers=headers, data=data)
    if response.status_code == 200:
        image_path = 'temp_image.png'
        with open(image_path, 'wb') as f:
            f.write(response.content)
        return image_path
    return None

# Database functions
def get_user_data(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT language, plan, photo_count, last_reset FROM users WHERE user_id = ?", (user_id,))
    data = c.fetchone()
    conn.close()
    if data:
        lang, plan, count, last_reset = data
        today = datetime.now().strftime('%Y-%m-%d')
        if last_reset != today:
            return lang, plan, 0, today
        return lang, plan, count, last_reset
    if user_id == ADMIN_ID:
        return 'en', 'pro', 0, datetime.now().strftime('%Y-%m-%d')
    return None, 'free', 0, datetime.now().strftime('%Y-%m-%d')

def update_user_data(user_id, lang=None, plan=None, count=None, reset=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, language, plan, photo_count, last_reset) VALUES (?, ?, ?, ?, ?)",
              (user_id, lang or get_user_data(user_id)[0], plan or get_user_data(user_id)[1],
               count if count is not None else get_user_data(user_id)[2], reset or get_user_data(user_id)[3]))
    conn.commit()
    conn.close()

def add_pending(user_id, plan, message_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO pending (user_id, plan, message_id) VALUES (?, ?, ?)", (user_id, plan, message_id))
    conn.commit()
    conn.close()

def get_pending_by_message_id(message_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id, plan FROM pending WHERE message_id = ?", (message_id,))
    data = c.fetchone()
    conn.close()
    return data

def remove_pending(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM pending WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# Check daily limit
def check_limit(user_id, lang):
    _, plan, count, _ = get_user_data(user_id)
    limits = {'free': 5, 'standard': 30, 'pro': float('inf')}
    limit = limits[plan]
    remaining = limit - count if limit != float('inf') else '∞'
    if count >= limit:
        return False, MESSAGES[lang]['limit_reached'].format(limit=limit), remaining
    return True, "", remaining

# Check channel membership
async def is_member(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=REQUIRED_CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# Send main menu
async def send_menu(chat_id, user_id, context):
    lang, plan, count, _ = get_user_data(user_id)
    limits = {'free': 5, 'standard': 30, 'pro': float('inf')}
    remaining = limits[plan] - count if limits[plan] != float('inf') else '∞'
    keyboard = [
        [InlineKeyboardButton(MESSAGES[lang]['generate_image'], callback_data='generate_image'),
         InlineKeyboardButton(MESSAGES[lang]['change_plan'], callback_data='change_plan')],
        [InlineKeyboardButton(MESSAGES[lang]['change_language'], callback_data='change_language'),
         InlineKeyboardButton(MESSAGES[lang]['help'], callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id,
                                   text=MESSAGES[lang]['current_plan'].format(plan=plan, remaining=remaining),
                                   reply_markup=reply_markup)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    lang, plan, _, _ = get_user_data(user_id)

    if not await is_member(user_id, context):
        keyboard = [[InlineKeyboardButton(MESSAGES['fa']['check_membership'], callback_data='check_membership')]]
        await context.bot.send_message(chat_id=chat_id, text=MESSAGES['fa']['join_channel'].format(link=CHANNEL_LINK),
                                       reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    if not lang:
        keyboard = [
            [InlineKeyboardButton("🇺🇸 English", callback_data='lang_en')],
            [InlineKeyboardButton("🇮🇷 فارسی", callback_data='lang_fa')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=chat_id, text=MESSAGES['en']['welcome'], reply_markup=reply_markup)
    else:
        await send_menu(chat_id, user_id, context)

# Handle group commands
async def group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    text = update.message.text.lower()
    commands = ['عکس ', 'photo ', 'img ', 'تصویر ']

    if not await is_member(user_id, context):
        keyboard = [[InlineKeyboardButton(MESSAGES['fa']['check_membership'], callback_data='check_membership')]]
        await context.bot.send_message(chat_id=chat_id, text=MESSAGES['fa']['join_channel'].format(link=CHANNEL_LINK),
                                       reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    for cmd in commands:
        if text.startswith(cmd):
            prompt = text[len(cmd):].strip()
            if not prompt:
                lang = get_user_data(user_id)[0] or 'en'
                await context.bot.send_message(chat_id=chat_id, text=MESSAGES[lang]['waiting_prompt'])
                return
            await process_prompt(prompt, user_id, chat_id, context, update.message.message_id)
            return

# Process image generation
async def process_prompt(prompt, user_id, chat_id, context, message_id=None):
    lang = get_user_data(user_id)[0] or 'en'
    can_generate, limit_message, remaining = check_limit(user_id, lang)
    if not can_generate:
        await context.bot.send_message(chat_id=chat_id, text=limit_message, reply_to_message_id=message_id)
        return

    # If the user's language is English and the prompt isn't English, translate to English
    if lang == 'en' and not is_english(prompt):
        prompt = translate_text(prompt, 'fa', 'en')
    # If the user's language is Farsi, keep the prompt as is unless the API requires English
    # Assuming the API needs English, translate Farsi prompts for consistency
    elif lang == 'fa' and not is_english(prompt):
        prompt = translate_text(prompt, 'fa', 'en')  # Comment this line if the API supports Farsi

    wait_message = await context.bot.send_message(chat_id=chat_id, text=MESSAGES[lang]['processing'], reply_to_message_id=message_id)
    image_path = generate_image(prompt)

    if image_path:
        await context.bot.delete_message(chat_id=chat_id, message_id=wait_message.message_id)
        with open(image_path, 'rb') as photo:
            await context.bot.send_photo(chat_id=chat_id, photo=photo, reply_to_message_id=message_id)
        _, _, count, reset = get_user_data(user_id)
        update_user_data(user_id, count=count + 1)
        limits = {'free': 5, 'standard': 30, 'pro': float('inf')}
        plan = get_user_data(user_id)[1]
        remaining = limits[plan] - (count + 1) if limits[plan] != float('inf') else '∞'
        keyboard = [[InlineKeyboardButton(MESSAGES[lang]['generate_another'], callback_data='generate_image')]]
        await context.bot.send_message(chat_id=chat_id,
                                       text=MESSAGES[lang]['current_plan'].format(plan=plan, remaining=remaining),
                                       reply_markup=InlineKeyboardMarkup(keyboard),
                                       reply_to_message_id=message_id)
        os.remove(image_path)
    else:
        await context.bot.send_message(chat_id=chat_id, text=MESSAGES[lang]['error_image'], reply_to_message_id=message_id)

# Callback handler
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    lang = get_user_data(user_id)[0] or 'en'

    if query.data == 'check_membership':
        if await is_member(user_id, context):
            lang, _, _, _ = get_user_data(user_id)
            if not lang:
                keyboard = [
                    [InlineKeyboardButton("🇺🇸 English", callback_data='lang_en')],
                    [InlineKeyboardButton("🇮🇷 فارسی", callback_data='lang_fa')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(chat_id=chat_id, text=MESSAGES['en']['welcome'], reply_markup=reply_markup)
            else:
                await send_menu(chat_id, user_id, context)
        else:
            keyboard = [[InlineKeyboardButton(MESSAGES['fa']['check_membership'], callback_data='check_membership')]]
            await context.bot.send_message(chat_id=chat_id, text=MESSAGES['fa']['join_channel'].format(link=CHANNEL_LINK),
                                           reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif query.data.startswith('lang_'):
        lang = query.data.split('_')[1]
        update_user_data(user_id, lang=lang)
        await send_menu(chat_id, user_id, context)
    elif query.data == 'generate_image':
        await context.bot.send_message(chat_id=chat_id, text=MESSAGES[lang]['waiting_prompt'])
        context.user_data['state'] = 'waiting_for_prompt'
    elif query.data == 'change_plan':
        keyboard = [
            [InlineKeyboardButton(MESSAGES[lang]['free_plan'], callback_data='plan_free')],
            [InlineKeyboardButton(MESSAGES[lang]['standard_plan'], callback_data='plan_standard')],
            [InlineKeyboardButton(MESSAGES[lang]['pro_plan'], callback_data='plan_pro')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=chat_id, text=MESSAGES[lang]['choose_plan'], reply_markup=reply_markup)
    elif query.data == 'change_language':
        keyboard = [
            [InlineKeyboardButton("🇺🇸 English", callback_data='lang_en')],
            [InlineKeyboardButton("🇮🇷 فارسی", callback_data='lang_fa')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=chat_id, text=MESSAGES[lang]['welcome'], reply_markup=reply_markup)
    elif query.data.startswith('plan_'):
        plan = query.data.split('_')[1]
        keyboard = [
            [InlineKeyboardButton("Buy" if lang == 'en' else "خرید", callback_data=f'buy_{plan}'),
             InlineKeyboardButton("Cancel" if lang == 'en' else "لغو", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=chat_id, text=MESSAGES[lang][f'{plan}_plan_desc'], reply_markup=reply_markup)
    elif query.data.startswith('buy_'):
        plan = query.data.split('_')[1]
        current_plan = get_user_data(user_id)[1]
        if plan == 'free':
            if current_plan != 'free' or get_user_data(user_id)[2] == 0:
                update_user_data(user_id, plan='free', count=0)
                await context.bot.send_message(chat_id=chat_id, text=MESSAGES[lang]['approved'].format(plan=plan))
                await send_menu(chat_id, user_id, context)
            else:
                await context.bot.send_message(chat_id=chat_id, text=MESSAGES[lang]['plan_active'].format(plan=current_plan))
        elif plan == 'standard':
            keyboard = [[InlineKeyboardButton("Cancel" if lang == 'en' else "لغو", callback_data='cancel')]]
            await context.bot.send_message(chat_id=chat_id, text=MESSAGES[lang]['send_selfie'], reply_markup=InlineKeyboardMarkup(keyboard))
            context.user_data['state'] = 'waiting_for_selfie'
        elif plan == 'pro':
            keyboard = [[InlineKeyboardButton("Cancel" if lang == 'en' else "لغو", callback_data='cancel')]]
            await context.bot.send_message(chat_id=chat_id, text=MESSAGES[lang]['send_video'], reply_markup=InlineKeyboardMarkup(keyboard))
            context.user_data['state'] = 'waiting_for_video_note'
    elif query.data == 'cancel':
        context.user_data['state'] = ''
        await send_menu(chat_id, user_id, context)
    elif query.data == 'help':
        await context.bot.send_message(chat_id=chat_id, text=MESSAGES[lang]['help_text'])
    elif query.data in ['approve', 'reject']:
        if query.from_user.id == ADMIN_ID:
            message_id = query.message.message_id
            pending_data = get_pending_by_message_id(message_id)
            if pending_data:
                user_id, plan = pending_data
                if query.data == 'approve':
                    update_user_data(user_id, plan=plan, count=0)
                    await context.bot.send_message(chat_id=user_id, text=MESSAGES[get_user_data(user_id)[0]]['approved'].format(plan=plan))
                else:
                    await context.bot.send_message(chat_id=user_id, text=MESSAGES[get_user_data(user_id)[0]]['rejected'].format(plan=plan))
                remove_pending(user_id)
                await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)
                await context.bot.send_message(chat_id=chat_id, text=f"{'✅ Approved' if query.data == 'approve' else '❌ Rejected'}", reply_to_message_id=message_id)
            else:
                await context.bot.send_message(chat_id=chat_id, text="❌ No pending request found for this message.")

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    lang = get_user_data(user_id)[0] or 'en'

    if not await is_member(user_id, context):
        keyboard = [[InlineKeyboardButton(MESSAGES['fa']['check_membership'], callback_data='check_membership')]]
        await context.bot.send_message(chat_id=chat_id, text=MESSAGES['fa']['join_channel'].format(link=CHANNEL_LINK),
                                       reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    if 'state' in context.user_data:
        if context.user_data['state'] == 'waiting_for_prompt':
            await process_prompt(update.message.text, user_id, chat_id, context)
            context.user_data['state'] = ''
        elif context.user_data['state'] == 'waiting_for_selfie' and update.message.photo:
            photo = update.message.photo[-1].file_id
            username = update.message.from_user.username or "N/A"
            name = update.message.from_user.first_name
            caption = f"User ID: {user_id}\nUsername: @{username}\nName: {name}\nPlan: standard\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            keyboard = [
                [InlineKeyboardButton("✅ Approve", callback_data='approve'),
                 InlineKeyboardButton("❌ Reject", callback_data='reject')]
            ]
            message = await context.bot.send_photo(chat_id=PRIVATE_CHANNEL_ID, photo=photo, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))
            add_pending(user_id, 'standard', message.message_id)
            await context.bot.send_message(chat_id=chat_id, text=MESSAGES[lang]['pending'])
            context.user_data['state'] = ''
        elif context.user_data['state'] == 'waiting_for_video_note' and update.message.video_note:
            video_note = update.message.video_note.file_id
            username = update.message.from_user.username or "N/A"
            name = update.message.from_user.first_name
            caption = f"User ID: {user_id}\nUsername: @{username}\nName: {name}\nPlan: pro\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            keyboard = [
                [InlineKeyboardButton("✅ Approve", callback_data='approve'),
                 InlineKeyboardButton("❌ Reject", callback_data='reject')]
            ]
            try:
                message = await context.bot.send_video_note(
                    chat_id=PRIVATE_CHANNEL_ID,
                    video_note=video_note,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                await context.bot.send_message(
                    chat_id=PRIVATE_CHANNEL_ID,
                    text=caption,
                    reply_to_message_id=message.message_id
                )
                add_pending(user_id, 'pro', message.message_id)
                await context.bot.send_message(chat_id=chat_id, text=MESSAGES[lang]['pending'])
                context.user_data['state'] = ''
            except Exception as e:
                logger.error(f"Error sending video note: {e}")
                await context.bot.send_message(chat_id=chat_id, text="❌ Error sending video note. Please try again.")

# Main function
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex(r'^(عکس |photo |img |تصویر )'), group_command))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND | filters.PHOTO | filters.VIDEO_NOTE, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()