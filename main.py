import telegram
print(telegram.__version__)

import nest_asyncio
nest_asyncio.apply()

import requests
import asyncio
import logging
import ccxt.async_support as async_ccxt
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = "7131056450:AAEgN6hEGsRvOb1KZ4MzaGJHON2ynqYO4II"

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
USER_DATA = {}
IS_MONITORING = True  # To control the monitoring loop
crypto_data = {}

bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message with initial options and a note about stopping the bot."""
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
        "- /stop to halt monitoring and stop all alerts.\n\n"
        "Select an option from the menu to proceed."
    )
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stops the bot and monitoring tasks."""
    global IS_MONITORING
    IS_MONITORING = False
    await update.message.reply_text('Monitoring and alerts have been stopped. Use /start to resume.')

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

        elif user_state == AWAITING_TICKER_FOR_PRICE_ALERT:
            USER_DATA[chat_id] = {'ticker': user_input, 'type': 'price'}
            keyboard = [
                [InlineKeyboardButton("Percentage Change", callback_data='price_alert_percentage')],
                [InlineKeyboardButton("Absolute Value", callback_data='price_alert_absolute')]
            ]
            await update.message.reply_text("Select the type of price alert:", reply_markup=InlineKeyboardMarkup(keyboard))
            USER_STATES[chat_id] = CHOOSING_PRICE_ALERT_TYPE

        elif user_state == AWAITING_TICKER_FOR_VOLUME_ALERT:
            USER_DATA[chat_id] = {'ticker': user_input, 'type': 'volume'}
            keyboard = [
                [InlineKeyboardButton("Percentage Change", callback_data='volume_alert_percentage')],
                [InlineKeyboardButton("Absolute Value", callback_data='volume_alert_absolute')]
            ]
            await update.message.reply_text("Select the type of volume alert:", reply_markup=InlineKeyboardMarkup(keyboard))
            USER_STATES[chat_id] = CHOOSING_VOLUME_ALERT_TYPE

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
        # Split the input on a comma if present, or create a single item list
        values = [float(val.strip()) for val in user_input.split(',') if val.strip()]

        # Fetch current data for the ticker
        ticker = USER_DATA[chat_id]['ticker']
        ticker_data = crypto_data.get(ticker)
        if not ticker_data:
            await update.message.reply_text(f"Data for {ticker} not found.")
            return

        current_price = float(ticker_data['last'])
        # Ensure you're using the correct key for current change and volume in your data
        current_change = float(ticker_data['fluctuation'])
        current_volume = float(ticker_data['volume_24h'])

        # Initialize an empty list to hold alert info
        alert_infos = []

        # Construct the alert info based on the input values
        for value in values:
            direction = "increase" if value > 0 else "decrease"
            alert_infos.append({
                'type': alert_subtype,
                'value': value,
                'direction': direction,
                'ticker': ticker
            })

        # Construct a response message for the alert setup
        response_messages = []
        for alert_info in alert_infos:
            response_messages.append(f"✅ Alert set for a {alert_info['value']}% {alert_info['direction']} for {alert_info['ticker']}.")

        final_response_message = " ".join(response_messages)
        final_response_message += f"\nCurrent Price: ${current_price:.2f}\n24H Change: {current_change:.2f}%\n24H Volume: {current_volume}"

        # Send the alert setup confirmation message
        await update.message.reply_text(final_response_message)

        # Here you should store or update the alert in your system
        # This is just an example placeholder
        for alert_info in alert_infos:
            finalize_alert_setup(chat_id, alert_info)

    except ValueError:
        await update.message.reply_text("Please enter a valid number or a comma-separated pair of numbers for the alert.")
    except Exception as e:
        logger.error(f"Error processing alert setup for chat {chat_id}: {e}")
        await update.message.reply_text("There was an error processing your alert setup. Please try again.")
    finally:
        # Reset the user state after processing
        USER_STATES[chat_id] = 0

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

async def monitor_prices_and_volumes():
    global IS_MONITORING, crypto_data
    while IS_MONITORING:
        logger.info("Starting the monitoring loop.")
        for chat_id, user_info in USER_DATA.items():
            if 'alerts' in user_info:
                for alert in user_info['alerts']:
                    ticker = alert.get('ticker')
                    try:
                        # Directly use the updated crypto_data dictionary
                        current_data = crypto_data.get(ticker, {})
                        if not current_data:  # Skip if no data available for the ticker
                            continue

                        current_price = float(current_data['last'])
                        previous_price = alert.get('previous_price', current_price)  # Use current price as previous if not set
                        alert['previous_price'] = current_price  # Update for the next iteration

                        # Calculating the percentage change if type is 'percentage'
                        if alert.get('type') == 'percentage':
                            percentage_change = ((current_price - previous_price) / previous_price) * 100 if previous_price else 0
                            if abs(percentage_change) >= abs(alert['value']):
                                direction = "increased" if percentage_change > 0 else "decreased"
                                message = f"🔔 Continuous Price Alert: {ticker} has {direction} by {abs(percentage_change):.2f}% (threshold {alert['value']}%) since the last notification. The current price is ${current_price:.2f}."
                                await bot.send_message(chat_id, message)
                                logger.info(f"Sent continuous price alert for {ticker} to chat {chat_id}: {message}")
                                
                        if alert.get('type') == 'volume_percentage':
                            previous_volume = alert.get('previous_volume', current_volume)
                            alert['previous_volume'] = current_volume  # Update for next iteration
                            volume_change_percentage = ((current_volume - previous_volume) / previous_volume) * 100 if previous_volume else 0

                        if abs(volume_change_percentage) >= abs(alert['value']):
                            direction = "increased" if volume_change_percentage > 0 else "decreased"
                            message = f"🔔 Continuous Volume Alert: {ticker} has {direction} by {abs(volume_change_percentage):.2f}% (threshold {alert['value']}%) since the last notification. The current volume is {current_volume:.2f}."
                            await bot.send_message(chat_id, message)
                            logger.info(f"Sent continuous volume alert for {ticker} to chat {chat_id}. {message}")
                            
                            
                        if alert.get('type') == 'absolute' and not alert.get('triggered', False):
                            # Check if the current price has reached the alert's target value
                            if (current_price >= alert['value'] and previous_price < alert['value']) or (current_price <= alert['value'] and previous_price > alert['value']):
                                message = (f"🔔 Price Alert: {ticker} has reached the target price of ${alert['value']:.2f}. "
                                           f"Previous price was ${previous_price:.2f}. Current price is ${current_price:.2f}.")
                                await bot.send_message(chat_id, message)
                                logger.info(f"Sent price alert for {ticker} to chat {chat_id}: {message}")
                                alert['triggered'] = True  # Mark the alert as triggered
                                
                        if alert.get('type') == 'volume_absolute' and not alert.get('triggered', False):
                            if current_volume >= alert['value']:
                                message = (f"🔔 Volume Alert: {ticker} has reached the target volume of {alert['value']}. "
                                           f"The current volume is {current_volume:.2f}.")
                                await bot.send_message(chat_id, message)
                                logger.info(f"Sent volume alert for {ticker} to chat {chat_id}: {message}")
                                alert['triggered'] = True  # Mark the alert as triggered to prevent repeated notifications
                        
                    except Exception as e:
                        logger.error(f"Error processing alert for {ticker}: {e}")

        logger.info("Completed monitoring cycle, waiting for the next cycle.")
        await asyncio.sleep(10)  # Sleep time can be adjusted based on your needs

async def main():
    # Create the Application using your bot's token
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register your handlers with the application
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), text_handler))

    # Start the price and volume monitoring function in a background task
    asyncio.create_task(monitor_prices_and_volumes())

    # Start the cryptocurrency data updating function in a background task
    asyncio.create_task(update_crypto_data())

    # Start polling updates from Telegram
    await application.run_polling()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        # Perform any cleanup here
        print('Bot stopped by user')
        
    finally:
        loop.close()







