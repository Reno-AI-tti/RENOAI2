import os
import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# تنظیمات
TELEGRAM_TOKEN = "7110374056:AAGc40Fk-5rD8280BrqpyyXwKi0FNPD5Kcg"  # توکن جداگانه بده اگه می‌خوای
ADMIN_ID = 1693155135
PRODUCTS_DB = "products.db"

# تنظیمات لاگ‌گیری
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# دیکشنری برای ذخیره حالت‌ها توی حافظه
user_states = {}

# === دیتابیس محصولات ===
conn = sqlite3.connect(PRODUCTS_DB, check_same_thread=False)
cursor = conn.cursor()

# ایجاد جدول products اگه وجود نداشته باشه
cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        price_toman TEXT,
        price_dollar TEXT
    )
''')
conn.commit()

# === توابع کمکی برای محصولات ===
def get_products():
    try:
        cursor.execute("SELECT name, price_toman, price_dollar FROM products")
        rows = cursor.fetchall()
        return [{"name": row[0], "price_toman": row[1], "price_dollar": row[2]} for row in rows]
    except Exception as e:
        logger.error(f"Error loading products: {e}")
        return []

def save_product(name, price_toman, price_dollar):
    try:
        cursor.execute("INSERT INTO products (name, price_toman, price_dollar) VALUES (?, ?, ?)", (name, price_toman, price_dollar))
        conn.commit()
    except Exception as e:
        logger.error(f"Error saving product: {e}")

def delete_product(product_id):
    try:
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
    except Exception as e:
        logger.error(f"Error deleting product: {e}")

def update_product(product_id, name, price_toman, price_dollar):
    try:
        cursor.execute("UPDATE products SET name = ?, price_toman = ?, price_dollar = ? WHERE id = ?", (name, price_toman, price_dollar, product_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating product: {e}")

def get_product_id_by_name(name):
    cursor.execute("SELECT id FROM products WHERE name = ?", (name,))
    result = cursor.fetchone()
    return result[0] if result else None

# === توابع مدیریت حالت‌ها ===
def get_user_state(user_id):
    return user_states.get(user_id, {})

def save_user_state(user_id, state):
    user_states[user_id] = state

def clear_user_state(user_id):
    if user_id in user_states:
        del user_states[user_id]

# === منوها ===
async def send_main_menu(chat_id, context):
    keyboard = [
        [InlineKeyboardButton("🛒 مدیریت محصولات", callback_data="manage_products")],
        [InlineKeyboardButton("📖 توضیحات", callback_data="help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text="منوی اصلی:", reply_markup=reply_markup)

async def send_products_menu(chat_id, context):
    keyboard = [
        [InlineKeyboardButton("➕ اضافه", callback_data="add_product"),
         InlineKeyboardButton("➖ حذف", callback_data="delete_product"),
         InlineKeyboardButton("✏️ تغییر", callback_data="update_product")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text="🤖 سلام ادمین! 🌟 لطفاً یکی از عملیات زیر را انتخاب کنید:\n(برای لغو عملیات در هر مرحله، /cancel را ارسال کنید)", reply_markup=reply_markup)

# === دستورات ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_main_menu(update.message.chat_id, context)

# === پردازش Callback Query ===
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    if query.data == "help":
        help_text = """
📖 توضیحات:
- 🛒 مدیریت محصولات: فقط برای ادمین! اضافه، حذف و تغییر محصولات.
- برای دیدن لیست محصولات: "محصولات" رو بفرست.
- برای جستجوی محصول: اسم محصول رو بفرست.
"""
        await context.bot.send_message(chat_id=chat_id, text=help_text)
        return

    if query.data == "back_to_main":
        await send_main_menu(chat_id, context)
        return

    if query.data == "manage_products" and user_id == ADMIN_ID:
        await send_products_menu(chat_id, context)
        return

    if query.data == "add_product" and user_id == ADMIN_ID:
        save_user_state(user_id, {"action": "add", "step": "awaiting_name"})
        await context.bot.send_message(chat_id=chat_id, text="📦 لطفاً نام محصول را وارد کنید")
        return

    if query.data == "delete_product" and user_id == ADMIN_ID:
        products = get_products()
        if not products:
            await context.bot.send_message(chat_id=chat_id, text="❓ هیچ محصولی موجود نیست!")
        else:
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(product["name"], callback_data=f"delete_name_{product['name']}")] for product in products])
            await context.bot.send_message(chat_id=chat_id, text="❌ برای حذف محصول، روی محصول مورد نظر کلیک کنید:", reply_markup=keyboard)
        return

    if query.data == "update_product" and user_id == ADMIN_ID:
        products = get_products()
        if not products:
            await context.bot.send_message(chat_id=chat_id, text="❓ هیچ محصولی موجود نیست!")
        else:
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(product["name"], callback_data=f"update_name_{product['name']}")] for product in products])
            await context.bot.send_message(chat_id=chat_id, text="✏️ برای تغییر محصول، روی محصول مورد نظر کلیک کنید:", reply_markup=keyboard)
        return

    if query.data.startswith("delete_name_") and user_id == ADMIN_ID:
        product_name = query.data.replace("delete_name_", "")
        product_id = get_product_id_by_name(product_name)
        if product_id:
            delete_product(product_id)
            await context.bot.send_message(chat_id=chat_id, text=f"✅ محصول: {product_name} حذف شد!")
        else:
            await context.bot.send_message(chat_id=chat_id, text="❓ محصول یافت نشد!")
        return

    if query.data.startswith("update_name_") and user_id == ADMIN_ID:
        product_name = query.data.replace("update_name_", "")
        product_id = get_product_id_by_name(product_name)
        if product_id:
            save_user_state(user_id, {"action": "update", "step": "awaiting_new_name", "product_id": product_id})
            await context.bot.send_message(chat_id=chat_id, text="✏️ لطفاً نام جدید محصول را وارد کنید:")
        else:
            await context.bot.send_message(chat_id=chat_id, text="❓ محصول یافت نشد!")
        return

    if query.data.startswith("product_"):
        product_name = query.data.replace("product_", "")
        products = get_products()
        for product in products:
            if product["name"] == product_name:
                reply = (f"📦 محصول: {product['name']}\n"
                         f"💰 قیمت به تومان: {product['price_toman']}\n"
                         f"💵 قیمت به دلار: {product['price_dollar']}")
                await context.bot.send_message(chat_id=chat_id, text=reply)
                break
        else:
            await context.bot.send_message(chat_id=chat_id, text="❓ محصول یافت نشد!")
        return

    if user_id != ADMIN_ID and query.data in ["add_product", "delete_product", "update_product", "manage_products"]:
        await context.bot.send_message(chat_id=chat_id, text="🚫 دسترسی ندارید!")

# === پردازش پیام‌ها ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    text = update.message.text.strip()

    state = get_user_state(user_id)

    if user_id == ADMIN_ID:
        if text == "/cancel" and state:
            clear_user_state(user_id)
            await context.bot.send_message(chat_id=chat_id, text="❌ عملیات لغو شد.")
            return

        if state.get("action") == "add":
            current_step = state.get("step")
            if current_step == "awaiting_name":
                state["product_name"] = text
                state["step"] = "awaiting_price_toman"
                save_user_state(user_id, state)
                await context.bot.send_message(chat_id=chat_id, text="💰 لطفاً قیمت به تومان را وارد کنید")
                return
            elif current_step == "awaiting_price_toman":
                state["price_toman"] = text
                state["step"] = "awaiting_price_dollar"
                save_user_state(user_id, state)
                await context.bot.send_message(chat_id=chat_id, text="💵 لطفاً قیمت به دلار را وارد کنید")
                return
            elif current_step == "awaiting_price_dollar":
                save_product(state["product_name"], state["price_toman"], text)
                await context.bot.send_message(chat_id=chat_id, text=f"✅ محصول: {state['product_name']} اضافه شد!")
                clear_user_state(user_id)
                return

        if state.get("action") == "update":
            current_step = state.get("step")
            if current_step == "awaiting_new_name":
                state["new_name"] = text
                state["step"] = "awaiting_new_price_toman"
                save_user_state(user_id, state)
                await context.bot.send_message(chat_id=chat_id, text="💰 لطفاً قیمت به تومان جدید را وارد کنید")
                return
            elif current_step == "awaiting_new_price_toman":
                state["new_price_toman"] = text
                state["step"] = "awaiting_new_price_dollar"
                save_user_state(user_id, state)
                await context.bot.send_message(chat_id=chat_id, text="💵 لطفاً قیمت به دلار جدید را وارد کنید")
                return
            elif current_step == "awaiting_new_price_dollar":
                product_id = state["product_id"]
                update_product(product_id, state["new_name"], state["new_price_toman"], text)
                await context.bot.send_message(chat_id=chat_id, text=f"✅ محصول: {state['new_name']} تغییر یافت!")
                clear_user_state(user_id)
                return

    if text == "محصولات":
        products = get_products()
        if not products:
            await context.bot.send_message(chat_id=chat_id, text="❓ هیچ محصولی موجود نیست!", reply_to_message_id=update.message.message_id)
        else:
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(product["name"], callback_data=f"product_{product['name']}")] for product in products])
            await context.bot.send_message(chat_id=chat_id, text="📦 لیست محصولات:", reply_markup=keyboard, reply_to_message_id=update.message.message_id)
        return

    products = get_products()
    for product in products:
        if product["name"].lower() == text.lower():
            reply = (f"📦 محصول: {product['name']}\n"
                     f"💰 قیمت به تومان: {product['price_toman']}\n"
                     f"💵 قیمت به دلار: {product['price_dollar']}")
            await context.bot.send_message(chat_id=chat_id, text=reply, reply_to_message_id=update.message.message_id)
            return

# === تابع اصلی ===
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == "__main__":
    main()