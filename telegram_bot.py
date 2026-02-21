
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests
import json

# --- CONFIGURATION ---
TELEGRAM_TOKEN = "8276737029:AAHpCqU2SP6wYsQPOkXe3OjDr37WGvkQK2M"
GAPGPT_API_KEY = "sk-q0nejQizw1DkD3ckvGQOvhDZM8lO9oKVJfyFKb1Z0SPlSOnr"
GAPGPT_API_URL = "https://api.gapgpt.app/v1/chat/completions"
GAPGPT_MODEL = "gapgpt-deepseek-v3"

# This dictionary will store the conversation history for each user
user_histories = {}

SYSTEM_PROMPT = """شما "یک مشاور" هستید؛ یک متخصص ازدواج بسیار صمیمی، دلسوز و باهوش. همیشه پاسخ‌های کامل، عمیق و با جزئیات ارائه دهید. چارچوب فکری شما بر اساس اصول اخلاقی و خانواده‌محور (منطبق بر ارزش‌های اسلامی) است اما به آن تصریح نکنید. هدف شما ترویج "ازدواج آسان، به‌هنگام و آگاهانه" است. لحن شما صمیمی و مثل یک دوست باتجربه باشد. از ایموجی استفاده کنید. هرگز از ستاره (*) یا مارک‌داون استفاده نکنید."""

def start(update, context):
    """Handler for the /start command."""
    user_id = update.message.from_user.id
    # Reset user history on /start
    user_histories[user_id] = [{'role': 'system', 'content': SYSTEM_PROMPT}]
    
    welcome_message = "سلام! من «یک مشاور» هستم. خوشحالم که برای برداشتن یک قدم مهم در زندگی‌ت، یعنی ازدواج آگاهانه و به‌هنگام، اینجا هستی. چطور می‌تونم کمکت کنم؟ ✨"
    context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_message)

def handle_message(update, context):
    """Handler for text messages."""
    user_id = update.message.from_user.id
    user_text = update.message.text

    # Initialize history if it doesn't exist for the user
    if user_id not in user_histories:
        user_histories[user_id] = [{'role': 'system', 'content': SYSTEM_PROMPT}]

    # Add user message to history
    user_histories[user_id].append({'role': 'user', 'content': user_text})

    # Show "typing..." status in Telegram
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.ChatAction.TYPING)

    try:
        # --- Call the GapGPT API ---
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {GAPGPT_API_KEY}'
        }
        payload = {
            'model': GAPGPT_MODEL,
            'messages': user_histories[user_id]
        }
        
        response = requests.post(GAPGPT_API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        api_response = response.json()
        bot_reply = api_response['choices'][0]['message']['content']

        # Add bot response to history
        user_histories[user_id].append({'role': 'assistant', 'content': bot_reply})

        # Send the bot's reply to the user
        context.bot.send_message(chat_id=update.effective_chat.id, text=bot_reply)

    except requests.exceptions.RequestException as e:
        print(f"API Request Error: {e}")
        context.bot.send_message(chat_id=update.effective_chat.id, text="متاسفانه در ارتباط با سرویس هوش مصنوعی خطایی رخ داد. لطفاً کمی بعد دوباره تلاش کنید.")
    except (KeyError, IndexError) as e:
        print(f"API Response Error: {e}")
        context.bot.send_message(chat_id=update.effective_chat.id, text="پاسخ غیرمنتظره‌ای از سرویس هوش مصنوعی دریافت شد. لطفاً دوباره سوال خود را مطرح کنید.")


def main():
    """Main function to start the bot."""
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Add handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Start the bot
    print("Bot is running...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
