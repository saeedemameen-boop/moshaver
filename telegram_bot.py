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
    # Reset user history on /start to allow for fresh conversations
    if user_id in user_histories:
        del user_histories[user_id]

    welcome_message = (
        "سلام! به ربات «یک مشاور» خوش آمدید. 😊\n\n"
        "من یک متخصص ازدواج هستم که برای کمک به شما در مسیر \"ازدواج آسان، به‌هنگام و آگاهانه\" اینجا هستم.\n\n"
        "می‌توانید هر سوال یا دغدغه‌ای در مورد ازدواج دارید از من بپرسید. من با دقت و دلسوزی به شما پاسخ خواهم داد.\n\n"
        f"برای استفاده از خدمات، عضویت در کانال {TARGET_CHANNEL} الزامی است."
    )
    await context.bot.send_message(chat_id=user_id, text=welcome_message)

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
        # Get or create conversation history for the user
        if user_id not in user_histories:
            user_histories[user_id] = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        
        # Add user's message to their history
        user_histories[user_id].append({'role': 'user', 'content': user_message})

        headers = {
            'Authorization': f'Bearer {GAPGPT_API_KEY}',
            'Content-Type': 'application/json'
        }
        payload = {
            'model': GAPGPT_MODEL,
            'messages': user_histories[user_id]
        }

        await update.effective_chat.send_action(action='typing')
        
        async with httpx.AsyncClient() as client:
            print("DEBUG: Sending request to GapGPT API...")
            # Increased timeout for potentially longer AI responses
            response = await client.post(GAPGPT_API_URL, headers=headers, json=payload, timeout=60)
            print(f"DEBUG: GapGPT API Response Status: {response.status_code}")
            # Log the body for debugging, but be mindful of length/content
            print(f"DEBUG: GapGPT API Response Body: {response.text[:500]}")
            response.raise_for_status()

        response_data = response.json()
        ai_response = response_data['choices'][0]['message']['content']
        
        # Add AI's response to the history for context in next turn
        user_histories[user_id].append({'role': 'assistant', 'content': ai_response})

        await context.bot.send_message(chat_id=user_id, text=ai_response)

    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e}")
        print(f"Response body: {e.response.text}") # Log the actual error from the API
        await context.bot.send_message(chat_id=user_id, text="متاسفانه در ارتباط با سرویس هوش مصنوعی مشکلی پیش آمده است. لطفا کمی بعد دوباره تلاش کنید. 🙏 (خطای HTTP)")
    except Exception as e:
        print(f"An error occurred: {e}")
        await context.bot.send_message(chat_id=user_id, text="یک خطای غیرمنتظره رخ داد. تیم فنی در حال بررسی است. لطفا صبور باشید.")

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
