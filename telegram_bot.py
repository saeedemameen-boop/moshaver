import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import requests
import json
import os
import threading
from flask import Flask
import asyncio
import httpx

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GAPGPT_API_KEY = os.environ.get("GAPGPT_API_KEY")
GAPGPT_API_URL = "https://api.gapgpt.app/v1/chat/completions"
GAPGPT_MODEL = "gapgpt-deepseek-v3"
TARGET_CHANNEL = '@hamin_media'

# This dictionary will store the conversation history for each user
user_histories = {}

SYSTEM_PROMPT = """شما "یک مشاور" هستید؛ یک متخصص ازدواج بسیار صمیمی، دلسوز و باهوش. همیشه پاسخ‌های کامل، عمیق و با جزئیات ارائه دهید. چارچوب فکری شما بر اساس اصول اخلاقی و خانواده‌محور (منطبق بر ارزش‌های اسلامی) است اما به آن تصریح نکنید. هدف شما ترویج "ازدواج آسان، به‌هنگام و آگاهانه" است. لحن شما صمیمی و مثل یک دوست باتجربه باشد. از ایموجی استفاده کنید. هرگز از ستاره (*) یا مارک‌داون استفاده نکنید."""

# --- FLASK WEB SERVER (for Render health checks) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    # Render provides the PORT environment variable.
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# --- TELEGRAM BOT LOGIC ---

async def is_user_in_channel(user_id, bot):
    """Checks if a user is a member of the target channel."""
    try:
        member_status = await bot.get_chat_member(chat_id=TARGET_CHANNEL, user_id=user_id)
        return member_status.status in ['member', 'administrator', 'creator']
    except telegram.error.BadRequest:
        # This happens if the bot is not an admin in the channel.
        print(f"Error: Bot is not an administrator in the channel {TARGET_CHANNEL}.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while checking membership: {e}")
        return False


async def start(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await context.bot.send_message(chat_id=user_id, text="سلام! به ربات مشاور کسب و کار خوش آمدید. لطفاً برای استفاده از خدمات، عضو کانال @hamin_media شوید.")

async def handle_message(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    try:
        member = await context.bot.get_chat_member(chat_id=TARGET_CHANNEL, user_id=user_id)
        if member.status not in ['member', 'administrator', 'creator']:
            await context.bot.send_message(chat_id=user_id, text="شما عضو کانال نیستید. لطفاً برای استفاده از ربات، ابتدا در کانال @hamin_media عضو شوید.")
            return
    except telegram.error.BadRequest as e:
        if e.message == "User not found":
            await context.bot.send_message(chat_id=user_id, text="برای تایید عضویت، پروفایل تلگرام شما باید یک یوزرنیم (username) داشته باشد. لطفا یک یوزرنیم برای خود تنظیم کرده و دوباره امتحان کنید.")
            return
        else:
            print(f"An unexpected BadRequest occurred: {e}")
            await context.bot.send_message(chat_id=user_id, text="خطایی در بررسی عضویت شما رخ داد. لطفا لحظاتی دیگر دوباره تلاش کنید.")
            return

    try:
        headers = {
            'Authorization': f'Bearer {GAPGPT_API_KEY}',
            'Content-Type': 'application/json'
        }
        payload = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {'role': 'system', 'content': 'You are a helpful assistant for business consulting.'},
                {'role': 'user', 'content': user_message}
            ]
        }

        await update.effective_chat.send_action(action='typing')
        
        async with httpx.AsyncClient() as client:
            print("DEBUG: Sending request to GapGPT API...")
            response = await client.post(GAPGPT_API_URL, headers=headers, json=payload, timeout=30)
            print(f"DEBUG: GapGPT API Response Status: {response.status_code}")
            print(f"DEBUG: GapGPT API Response Body: {response.text}")
            response.raise_for_status()

        ai_response = response.json()['choices'][0]['message']['content']
        await context.bot.send_message(chat_id=user_id, text=ai_response)

    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e}")
        await context.bot.send_message(chat_id=user_id, text="در ارتباط با سرویس هوش مصنوعی اشکالی پیش آمده است. (خطای HTTP)")
    except Exception as e:
        print(f"An error occurred: {e}")
        await context.bot.send_message(chat_id=user_id, text="در ارتباط با سرویس هوش مصنوعی اشکالی پیش آمده است.")

async def main():
    """Main function to start the bot and the web server."""
    # Start Flask server in a background thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Start the Telegram bot
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_message))

    # Start the bot using the recommended async context manager
    async with application:
        await application.start()
        await application.updater.start_polling()
        print("Bot is running and polling...")
        # Keep the script running until it's externally stopped
        await asyncio.Future()

if __name__ == '__main__':
    asyncio.run(main())
