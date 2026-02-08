from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Command handler for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am online and will send you trading signals.")

# Echo handler for any text message
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = str(update.message.chat_id)
    
    # Add new chat ID to env file if not already present
    current_chat_ids = os.getenv('CHAT_IDS', '').split(',')
    if chat_id not in current_chat_ids:
        current_chat_ids.append(chat_id)
        new_chat_ids = ','.join([id.strip() for id in current_chat_ids if id.strip()])
        
        # Update .env file
        with open('.env', 'r') as f:
            lines = f.readlines()
        
        with open('.env', 'w') as f:
            for line in lines:
                if line.startswith('CHAT_IDS='):
                    f.write(f'CHAT_IDS={new_chat_ids}\n')
                else:
                    f.write(line)
        
        # Send new user details to existing users
        user = update.message.from_user
        user_details = f"New user added:\nID: {user.id}\nFirst Name: {user.first_name or 'N/A'}\nLast Name: {user.last_name or 'N/A'}\nUsername: @{user.username or 'N/A'}\nChat ID: {chat_id}"
        await send_to_me(user_details)
    
    await update.message.reply_text("This is a private trading bot developed by Bhargav Ram Manukonda for personal use. It is designed exclusively to send trading signals and is not available for public use.")

# Function to send message to specific chat
async def send_message(chat_id, message):
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    bot = Bot(token=TOKEN)
    await bot.send_message(chat_id=chat_id, text=message)

# Send message to your chats
async def send_to_me(message):
    chat_ids = os.getenv('CHAT_IDS').split(',')
    for chat_id in chat_ids:
        await send_message(int(chat_id.strip()), message)

# Function to start the bot
def start_telegram_bot():
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Create the application
    application = Application.builder().token(TOKEN).build()
    
    # Add command and message handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Example usage: Send startup message
    asyncio.run(send_to_me("Trading bot is now online and ready!"))
    
    # Start the bot
    application.run_polling()

# Main function
def main():
    start_telegram_bot()

if __name__ == "__main__":
    main()