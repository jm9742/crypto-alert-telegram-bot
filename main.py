import telegram
print(telegram.__version__)

import nest_asyncio
nest_asyncio.apply()

import json
import requests
import asyncio
import logging
import ccxt.async_support as async_ccxt
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = "7131056450:AAEgN6hEGsRvOb1KZ4MzaGJHON2ynqYO4II"

def save_user_data():
    with open('user_data.json', 'w') as file:
        json.dump(USER_DATA, file, ensure_ascii=False, indent=4)

def load_user_data():
    try:
        with open('user_data.json', 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.info("No existing user data found, starting with an empty dictionary.")
        return {}  # Return an empty dict if the file doesn't exist or is empty
    
# Load user data from file or initialize if not present
USER_DATA = load_user_data()

# Assuming states are defined as constants
AWAITING_COMMAND = 0
AWAITING_TICKER_FOR_INFO = 1
AWAITING_TICKER_FOR_PRICE_ALERT = 2
CHOOSING_PRICE_ALERT_TYPE = 3
SETTING_PRICE_ALERT_PERCENTAGE = 4
SETTING_PRICE_ALERT_ABSOLUTE = 5
AWAITING_TICKER_FOR_VOLUME_ALERT = 6
CHOOSING_VOLUME_ALERT_TYPE = 7
SETTING_VOLUME_ALERT_PERCENTAGE = 8
SETTING_VOLUME_ALERT_ABSOLUTE = 9

# Global state management
USER_STATES = {}
crypto_data = {}

bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    # Initialize user data if not already present
    USER_DATA[chat_id] = USER_DATA.get(chat_id, {'alerts': [], 'is_monitoring': True})
    USER_DATA[chat_id]['is_monitoring'] = True  # Start monitoring for this user
    
    # Load user data from file or initialize if not present
    save_user_data()
    
    keyboard = [
        [InlineKeyboardButton("Check Coin Info", callback_data='check_info')],
        [InlineKeyboardButton("Set Price Alert", callback_data='set_price_alert')],
        [InlineKeyboardButton("Set Volume Alert", callback_data='set_volume_alert')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_message = (
        "Welcome! Choose an option to get started:\n\n"
        "You can use the commands below at any time:\n"
        "- /start to display this message again.\n"
        "- /stop to halt monitoring and stop all alerts for you.\n\n"
        "Select an option from the menu to proceed."
    )
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    # Set user monitoring to False to stop monitoring for this user
    if chat_id in USER_DATA:
        USER_DATA[chat_id]['is_monitoring'] = False
        
        # Save the updated USER_DATA to the file
        save_user_data()
        await update.message.reply_text('Monitoring and alerts have been stopped for you. Use /start to resume.')
        
    else:
        await update.message.reply_text('You have no active monitoring to stop.')


import asyncio
import requests
import json

# This is your global dictionary to store cryptocurrency data

async def update_crypto_data():
    global crypto_data
    while True:
        try:
            # Perform an HTTP request to your data source endpoint
            response = requests.get("https://api-cloud.bitmart.com/spot/quotation/v3/tickers")
            data = response.json()

            # Process and update the crypto_data dictionary
            for item in data['data']:
                symbol, last, volume_24h, quote_volume_24h, open_24h, \
                high_24h, low_24h, fluctuation, bid_price, bid_size, \
                ask_price, ask_size, timestamp = item
                
                # Update the crypto_data dictionary
                crypto_data[symbol] = {
                    'last': last,
                    'volume_24h': volume_24h,
                    'quote_volume_24h': quote_volume_24h,
                    'open_24h': open_24h,
                    'high_24h': high_24h,
                    'low_24h': low_24h,
                    'fluctuation': fluctuation,
                    'bid_price': bid_price,
                    'bid_size': bid_size,
                    'ask_price': ask_price,
                    'ask_size': ask_size,
                    'timestamp': timestamp
                }
        except Exception as e:
            print(f"An error occurred: {e}")

        # Wait before updating the data again to avoid hitting rate limits
        await asyncio.sleep(1)  # Adjust the sleep time as needed for your data source's update frequency


from telegram import Update
from telegram.ext import CallbackContext

async def button_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id

    logger.info(f"Button pressed: {query.data}, transitioning state for chat {chat_id}")

    if query.data == 'check_info':
        USER_STATES[chat_id] = AWAITING_TICKER_FOR_INFO
        await context.bot.send_message(chat_id, "Enter the cryptocurrency ticker. Please enter a capitalized trading pair (e.g., BTC/USDT)")

    elif query.data == 'set_price_alert':
        USER_STATES[chat_id] = AWAITING_TICKER_FOR_PRICE_ALERT
        await context.bot.send_message(chat_id, "Enter the cryptocurrency ticker for which you want to set a price alert. Please enter a capitalized trading pair (e.g., BTC/USDT)")

    elif query.data == 'set_volume_alert':
        USER_STATES[chat_id] = AWAITING_TICKER_FOR_VOLUME_ALERT
        await context.bot.send_message(chat_id, "Enter the cryptocurrency ticker for which you want to set a volume alert. Please enter a capitalized trading pair (e.g., BTC/USDT):")

    elif query.data == 'price_alert_percentage':
        USER_STATES[chat_id] = SETTING_PRICE_ALERT_PERCENTAGE
        await context.bot.send_message(chat_id, "Enter the percentage change for the price alert (e.g., 5 for a 5% increase; -5 for 5% decrease; 5, -5 for both):")

    elif query.data == 'price_alert_absolute':
        USER_STATES[chat_id] = SETTING_PRICE_ALERT_ABSOLUTE
        await context.bot.send_message(chat_id, "Enter the absolute price value for the alert (e.g., 20000 for $20000 price):")

    elif query.data == 'volume_alert_percentage':
        USER_STATES[chat_id] = SETTING_VOLUME_ALERT_PERCENTAGE
        await context.bot.send_message(chat_id, "Enter the percentage change for the volume alert (e.g., 5 for a 5% increase; -5 for 5% decrease; 5, -5 for both):")

    elif query.data == 'volume_alert_absolute':
        USER_STATES[chat_id] = SETTING_VOLUME_ALERT_ABSOLUTE
        await context.bot.send_message(chat_id, "Enter the absolute volume value for the alert (e.g., 50000 for 50000 units):")


import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext

# Assuming USER_STATES, USER_DATA, and other necessary setups are already defined

logger = logging.getLogger(__name__)  # Set up logging

async def text_handler(update: Update, context: CallbackContext) -> None:
    original_user_input = update.message.text.strip()
    user_input = original_user_input.replace("/", "_").upper() 
    chat_id = update.effective_chat.id
    user_state = USER_STATES.get(chat_id, AWAITING_COMMAND)
    
    logger.info(f"Received text for chat {chat_id} in state {user_state}: '{original_user_input}'")
    logger.info(f"Formatted input for lookup: '{user_input}'")
    logger.info(f"Attempting to retrieve data for: {user_input}")
    
    try:
        if user_state == AWAITING_TICKER_FOR_INFO:
            info_data = crypto_data.get(user_input)
            logger.info(f"Lookup result for '{user_input}': {info_data}")
            
            if info_data: 
                response_message = (
                        f"📢 {user_input}\n"
                        f"Price: ${info_data['last']}\n"
                        f"24H Change: {info_data['fluctuation']}%\n"  # Assuming 'fluctuation' is the 24H Change
                        f"24H High: ${info_data['high_24h']}\n"
                        f"24H Low: ${info_data['low_24h']}\n"
                        f"24H Volume: {info_data['volume_24h']}"
                    )
            else:
                response_message = f"Data for {user_input} not found."
                logger.warning(f"Data for {user_input} not found in crypto_data.")
            
            await update.message.reply_text(response_message)

        elif user_state == AWAITING_TICKER_FOR_PRICE_ALERT or user_state == AWAITING_TICKER_FOR_VOLUME_ALERT:
            alert_type = 'price' if user_state == AWAITING_TICKER_FOR_PRICE_ALERT else 'volume'
            
            if 'alerts' not in USER_DATA[chat_id]:
                USER_DATA[chat_id]['alerts'] = []
                
            USER_DATA[chat_id]['alerts'].append({
                'ticker': user_input,
                'type': alert_type,
            })
            
            keyboard_buttons = [
                [InlineKeyboardButton("Percentage Change", callback_data=f'{alert_type}_alert_percentage')],
                [InlineKeyboardButton("Absolute Value", callback_data=f'{alert_type}_alert_absolute')]
            ]
            message_text = "Select the type of price alert:" if alert_type == 'price' else "Select the type of volume alert:"

            await update.message.reply_text(message_text, reply_markup=InlineKeyboardMarkup(keyboard_buttons))
            USER_STATES[chat_id] = CHOOSING_PRICE_ALERT_TYPE if alert_type == 'price' else CHOOSING_VOLUME_ALERT_TYPE

        elif user_state == SETTING_PRICE_ALERT_PERCENTAGE:
            await process_alert_setup(update, chat_id, user_state, user_input, 'percentage')

        elif user_state == SETTING_PRICE_ALERT_ABSOLUTE:
            await process_alert_setup(update, chat_id, user_state, user_input, 'absolute')

        elif user_state == SETTING_VOLUME_ALERT_PERCENTAGE:
            await process_alert_setup(update, chat_id, user_state, user_input, 'volume_percentage')

        elif user_state == SETTING_VOLUME_ALERT_ABSOLUTE:
            await process_alert_setup(update, chat_id, user_state, user_input, 'volume_absolute')

        else:
            # Handle unexpected states
            await default_state_response(update, chat_id)

    except Exception as e:
        logger.error(f"Error handling user input for chat {chat_id}: {e}")
        await update.message.reply_text("There was an error processing your request. Please try again.")
        USER_STATES[chat_id] = 0  # Reset to default state
        
async def process_alert_setup(update, chat_id, user_state, user_input, alert_subtype):
    try:
        values = [float(val.strip()) for val in user_input.split(',') if val.strip()]

        if not USER_DATA[chat_id].get('alerts'):
            await update.message.reply_text("No ticker selected for alert setup. Please start again.")
            return

        # Assumption: The last alert in 'alerts' list is the one we're currently setting up.
        ticker = USER_DATA[chat_id]['alerts'][-1]['ticker']

        ticker_data = crypto_data.get(ticker)
        if not ticker_data:
            await update.message.reply_text(f"Data for {ticker} not found.")
            return

        response_messages = []

        for value in values:
            new_alert_info = {
                'type': alert_subtype,
                'value': value,
                'ticker': ticker
            }

            if new_alert_info not in USER_DATA[chat_id]['alerts']:
                USER_DATA[chat_id]['alerts'].append(new_alert_info)

                if new_alert_info['type'] == 'absolute':
                    response_messages.append(f"✅ Alert set to notify when the price reaches ${value:.2f} for {ticker}.")
                elif new_alert_info['type'] in ['percentage', 'volume_percentage']:
                    direction = "increase" if value > 0 else "decrease"
                    response_messages.append(f"✅ Alert set for a {value}% {direction} for {ticker}.")
                elif new_alert_info['type'] == 'volume_absolute':
                    response_messages.append(f"✅ Volume alert set to notify when the volume reaches {value} for {ticker}.")

        if response_messages:
            final_response_message = " ".join(response_messages)
            await update.message.reply_text(final_response_message)

    except ValueError:
        await update.message.reply_text("Please enter a valid number or a comma-separated pair of numbers for the alert.")
    except Exception as e:
        logger.error(f"Error processing alert setup for chat {chat_id}: {e}")
        await update.message.reply_text("There was an error processing your alert setup. Please try again.")
    finally:
        USER_STATES[chat_id] = 0  # Reset the state to default after processing

def finalize_alert_setup(chat_id: int, alert_info: dict):
    """
    Adds the new alert information to the user's list of alerts in USER_DATA.
    
    Args:
        chat_id (int): The Telegram chat ID of the user.
        alert_info (dict): A dictionary containing the alert's type, value, and associated ticker.
    """
    # If there is no 'alerts' key in the USER_DATA for this user, add one
    if 'alerts' not in USER_DATA[chat_id]:
        USER_DATA[chat_id]['alerts'] = []

    # Add the new alert info to the user's list of alerts
    USER_DATA[chat_id]['alerts'].append(alert_info)
    logger.info(f"New alert added for chat {chat_id}: {alert_info}")

import asyncio

async def send_alert_message(bot, chat_id, message):
    try:
        await bot.send_message(chat_id=chat_id, text=message)
        logger.info(f"Alert sent to chat {chat_id}: {message}")
    except Exception as e:
        logger.error(f"Failed to send message to chat {chat_id}: {e}")

async def monitor_prices_and_volumes(bot):
    global USER_DATA, crypto_data
    while True:
        logger.info("Starting the monitoring loop.")
        for chat_id, user_info in USER_DATA.items():
            logger.info(f"Checking alerts for user_ID {chat_id}, monitoring status: {user_info.get('is_monitoring')}")
            if user_info.get('is_monitoring'):
                alerts = user_info.get('alerts', [])
                for alert in alerts:
                    ticker = alert.get('ticker')
                    try:
                        current_data = crypto_data.get(ticker, {})
                        if not current_data:
                            logger.info(f"No data for ticker {ticker}. Skipping.")
                            continue

                        current_price = float(current_data.get('last', 0))
                        current_volume = float(current_data.get('volume_24h', 0))
                        previous_price = alert.get('previous_price', current_price)
                        previous_volume = alert.get('previous_volume', current_volume)

                        # Price change alerts
                        if alert.get('type') == 'percentage':
                            price_change_percentage = ((current_price - previous_price) / previous_price) * 100 if previous_price else 0
                            if abs(price_change_percentage) >= abs(alert['value']):
                                direction = "increased" if price_change_percentage > 0 else "decreased"
                                message = f"🔔 Price Alert: {ticker} has {direction} by {abs(price_change_percentage):.4f}% (threshold: {alert['value']}%). Current price is ${current_price:.2f}."
                                await send_alert_message(bot, chat_id, message)

                        # Volume change alerts
                        if alert.get('type') == 'volume_percentage':
                            volume_change_percentage = ((current_volume - previous_volume) / previous_volume) * 100 if previous_volume else 0
                            if abs(volume_change_percentage) >= abs(alert['value']):
                                direction = "increased" if volume_change_percentage > 0 else "decreased"
                                message = f"🔔 Volume Alert: {ticker} has {direction} by {abs(volume_change_percentage):.4f}% (threshold: {alert['value']}%). Current volume is {current_volume:.2f}."
                                await send_alert_message(bot, chat_id, message)

                        # Absolute price alerts
                        if alert.get('type') == 'absolute':
                            price_crossed = (previous_price < alert['value'] <= current_price) or (previous_price > alert['value'] >= current_price)
                            if price_crossed and not alert.get('triggered', False):
                                message = f"🔔 Price Alert: {ticker} has reached the target price of ${alert['value']:.2f}. Current price is ${current_price:.2f}."
                                await send_alert_message(bot, chat_id, message)
                                alert['triggered'] = True

                        # Absolute volume alerts
                        if alert.get('type') == 'volume_absolute':
                            volume_crossed = (previous_volume < alert['value'] <= current_volume) or (previous_volume > alert['value'] >= current_volume)
                            if volume_crossed and not alert.get('triggered', False):
                                message = f"🔔 Volume Alert: {ticker} has reached the target volume of {alert['value']}. Current volume is {current_volume:.2f}."
                                await send_alert_message(bot, chat_id, message)
                                alert['triggered'] = True

                        # Update the previous values for the next check
                        alert['previous_price'] = current_price
                        alert['previous_volume'] = current_volume

                    except Exception as e:
                        logger.error(f"Error processing alert for {ticker}: {e}")

        logger.info("Completed monitoring cycle, waiting for the next cycle.")
        await asyncio.sleep(3)  # Adjust the sleep duration as necessary

# Setup logging as per your requirement
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Or DEBUG for more info

import asyncio

async def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register your handlers with the application
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), text_handler))

    # Create background tasks and keep references to them
    prices_and_volumes_task = asyncio.create_task(monitor_prices_and_volumes(application.bot))
    update_crypto_data_task = asyncio.create_task(update_crypto_data())

    try:
        # Start polling updates from Telegram
        await application.run_polling()
    finally:
        # If we reach this point, it's because run_polling has stopped for some reason
        # Now we need to cancel and await the background tasks
        prices_and_volumes_task.cancel()
        update_crypto_data_task.cancel()
        await asyncio.gather(prices_and_volumes_task, update_crypto_data_task, return_exceptions=True)
        await application.shutdown()

if __name__ == '__main__':
    # Use asyncio.run() to manage the event loop
    asyncio.run(main())








