import telegram
print(telegram.__version__)

import nest_asyncio
nest_asyncio.apply()


import asyncio
import logging
import ccxt.async_support as async_ccxt
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = "7131056450:AAEgN6hEGsRvOb1KZ4MzaGJHON2ynqYO4II"
    
exchange = async_ccxt.bitmart({'enableRateLimit': True})

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
AWAITING_TICKER_FOR_CONTINUOUS_PRICE_ALERT = 10
SETTING_CONTINUOUS_ALERT_PERCENTAGE = 11

# Global state management
USER_STATES = {}
USER_DATA = {}
IS_MONITORING = True  # To control the monitoring loop

bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message with initial options and a note about stopping the bot."""
    keyboard = [
        [InlineKeyboardButton("Check Coin Info", callback_data='check_info')],
        [InlineKeyboardButton("Set Price Alert", callback_data='set_price_alert')],
        [InlineKeyboardButton("Set Volume Alert", callback_data='set_volume_alert')],
        [InlineKeyboardButton("Continuous Percentage Alert", callback_data='continuous_alert')]
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

from telegram import Update
from telegram.ext import CallbackContext

async def button_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id

    logger.info(f"Button pressed: {query.data}, transitioning state for chat {chat_id}")

    if query.data == 'check_info':
        USER_STATES[chat_id] = AWAITING_TICKER_FOR_INFO
        await context.bot.send_message(chat_id, "Enter the cryptocurrency ticker (e.g., BTC/USDT):")

    elif query.data == 'set_price_alert':
        USER_STATES[chat_id] = AWAITING_TICKER_FOR_PRICE_ALERT
        await context.bot.send_message(chat_id, "Enter the cryptocurrency ticker for which you want to set a price alert (e.g., BTC/USDT):")

    elif query.data == 'set_volume_alert':
        USER_STATES[chat_id] = AWAITING_TICKER_FOR_VOLUME_ALERT
        await context.bot.send_message(chat_id, "Enter the cryptocurrency ticker for which you want to set a volume alert (e.g., BTC/USDT):")

    elif query.data == 'continuous_alert':
        USER_STATES[chat_id] = AWAITING_TICKER_FOR_CONTINUOUS_PRICE_ALERT
        await context.bot.send_message(chat_id, "Enter the cryptocurrency ticker for which you want to set a continuous price alert (e.g., BTC/USDT):")

    elif query.data == 'price_alert_percentage':
        USER_STATES[chat_id] = SETTING_PRICE_ALERT_PERCENTAGE
        await context.bot.send_message(chat_id, "Enter the percentage change for the price alert (e.g., 5 for a 5% increase; -5 for 5% decrease):")

    elif query.data == 'price_alert_absolute':
        USER_STATES[chat_id] = SETTING_PRICE_ALERT_ABSOLUTE
        await context.bot.send_message(chat_id, "Enter the absolute price value for the alert (e.g., 20000 for $20000 price):")

    elif query.data == 'volume_alert_percentage':
        USER_STATES[chat_id] = SETTING_VOLUME_ALERT_PERCENTAGE
        await context.bot.send_message(chat_id, "Enter the percentage change for the volume alert (e.g., 5 for a 5% increase; -5 for 5% decrease):")

    elif query.data == 'volume_alert_absolute':
        USER_STATES[chat_id] = SETTING_VOLUME_ALERT_ABSOLUTE
        await context.bot.send_message(chat_id, "Enter the absolute volume value for the alert (e.g., 50000 for 50000 units):")

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext

# Assuming USER_STATES, USER_DATA, and other necessary setups are already defined

logger = logging.getLogger(__name__)  # Set up logging

async def text_handler(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text.upper()  # Convert user input to uppercase for consistency
    chat_id = update.effective_chat.id
    user_state = USER_STATES.get(chat_id, 0)  # Default to AWAITING_COMMAND if no state is found
    logger.info(f"Handling text for chat {chat_id} in state {user_state}: {user_input}")

    try:
        if user_state == AWAITING_TICKER_FOR_INFO:
            try:
                # Asynchronously fetch the ticker information
                info_data = await exchange.fetch_ticker(user_input)
                # Construct the response message
                response_message = (
                    f"📢 {user_input}\n"
                    f"Price: ${info_data['last']:.6f}\n"
                    f"24H Change: {info_data['percentage']:.2f}%\n"
                    f"24H High: ${info_data['high']:.6f}\n"
                    f"24H Low: ${info_data['low']:.6f}\n"
                    f"24H Volume: ${info_data['quoteVolume']:.2f}"
                )
                await update.message.reply_text(response_message)
            except Exception as e:
                logger.error(f"Error fetching info for {user_input} in chat {chat_id}: {e}")
                await update.message.reply_text(f"Failed to fetch info for {user_input}. Error: {str(e)}")
            finally:
                USER_STATES[chat_id] = 0  # Reset the user state

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

        elif user_state == AWAITING_TICKER_FOR_CONTINUOUS_PRICE_ALERT:
            USER_DATA[chat_id] = {'ticker': user_input, 'type': 'continuous_percentage'}
            await update.message.reply_text("Enter the percentage change for the alert (e.g., 5 for a 5% increase, -5 for a 5% decrease):")
            USER_STATES[chat_id] = SETTING_CONTINUOUS_ALERT_PERCENTAGE

        elif user_state == SETTING_PRICE_ALERT_PERCENTAGE:
            await process_alert_setup(update, chat_id, user_state, user_input, 'percentage')

        elif user_state == SETTING_PRICE_ALERT_ABSOLUTE:
            await process_alert_setup(update, chat_id, user_state, user_input, 'absolute')

        elif user_state == SETTING_VOLUME_ALERT_PERCENTAGE:
            await process_alert_setup(update, chat_id, user_state, user_input, 'volume_percentage')

        elif user_state == SETTING_VOLUME_ALERT_ABSOLUTE:
            await process_alert_setup(update, chat_id, user_state, user_input, 'volume_absolute')

        elif user_state == SETTING_CONTINUOUS_ALERT_PERCENTAGE:
            await process_alert_setup(update, chat_id, user_state, user_input, 'continuous_percentage')

        else:
            # Handle unexpected states
            await default_state_response(update, chat_id)

    except Exception as e:
        logger.error(f"Error handling user input for chat {chat_id}: {e}")
        await update.message.reply_text("There was an error processing your request. Please try again.")
        USER_STATES[chat_id] = 0  # Reset to default state


async def process_alert_setup(update, chat_id, user_state, user_input, alert_subtype):
    try:
        # Handling for capturing both positive and negative percentage values.
        value = float(user_input)  # Direct float conversion to include negative values for decrease.
        # Fetch current data for the ticker
        current_data = await exchange.fetch_ticker(USER_DATA[chat_id]['ticker'])
        current_price = current_data['last']
        current_change = current_data['percentage']
        current_volume = current_data['quoteVolume']
        
        # Prepare alert data based on type
        alert_info = {
            'type': alert_subtype, 
            'value': value, 
            'ticker': USER_DATA[chat_id]['ticker']
        }
        
        # Customize the message based on alert subtype
        if alert_subtype == 'percentage' or alert_subtype == 'continuous_percentage':
            alert_direction = "increase" if value > 0 else "decrease"
            response_message = (
                f"✅ Alert set successfully for a {value}% {alert_direction} for {USER_DATA[chat_id]['ticker']}.\n"
                f"Current Price: ${current_price:.2f}\n"
                f"24H Change: {current_change:.2f}%"
            )
        elif alert_subtype == 'absolute':
            response_message = (
                f"✅ Price alert set successfully to notify when price reaches ${value:.2f} for {USER_DATA[chat_id]['ticker']}.\n"
                f"Current Price: ${current_price:.2f}\n"
                f"24H Change: {current_change:.2f}%"
            )
        elif alert_subtype == 'volume_percentage':
            response_message = (
                f"✅ Volume alert set successfully for a {value}% change for {USER_DATA[chat_id]['ticker']}.\n"
                f"Current Volume: {current_volume:.2f}"
            )
        elif alert_subtype == 'volume_absolute':
            response_message = (
                f"✅ Volume alert set successfully to notify when volume reaches {value} for {USER_DATA[chat_id]['ticker']}.\n"
                f"Current Volume: {current_volume:.2f}"
            )
        
        # Update user data and send the alert setup confirmation message
        finalize_alert_setup(chat_id, alert_info)
        await update.message.reply_text(response_message)
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
    finally:
        USER_STATES[chat_id] = 0  # Reset the user state after processing.

def finalize_alert_setup(chat_id, alert_info):
    # Add the new alert into the user's alerts list
    USER_DATA[chat_id]['alerts'] = USER_DATA[chat_id].get('alerts', []) + [alert_info]

import asyncio
import datetime
import logging

logger = logging.getLogger(__name__)

async def monitor_prices_and_volumes():
    while True:
        logger.info("Starting the monitoring loop.")
        for chat_id, user_info in USER_DATA.items():
            if 'alerts' in user_info:
                for alert in user_info['alerts']:
                    ticker = alert.get('ticker')
                    try:
                        current_data = await exchange.fetch_ticker(ticker)
                        current_price = current_data['last']
                        twenty_four_hour_change = current_data['percentage']
                        current_volume = current_data['quoteVolume']

                        # Save the price from the previous minute for comparison
                        previous_price = alert.get('previous_price', current_price)

                        # Update the 'previous_price' for the next iteration (one minute later)
                        alert['previous_price'] = current_price

                        logger.info(f"Retrieved current data for {ticker}: price={current_price}, 24h change={twenty_four_hour_change}%, volume={current_volume}")
                        logger.info(f"Previous data for {ticker}: price={previous_price}")

                        # Calculate the percentage change from one minute ago to now
                        price_change_percentage = ((current_price - previous_price) / previous_price) * 100 if previous_price else 0
                        logger.info(f"[{ticker}] Price change from one minute ago: {price_change_percentage}%")

                        # for one-time percentage alerts for price:
                        if alert.get('type') == 'percentage' and not alert.get('triggered', False):
                            if (alert['value'] > 0 and price_change_percentage >= alert['value']) or (alert['value'] < 0 and price_change_percentage <= alert['value']):
                                message = (f"🔔 Price Alert: {ticker} has met the target change of {alert['value']}%. "
                                           f"The current price is ${current_price:.2f}. The price change from one minute ago is {price_change_percentage:.2f}%.")
                                await bot.send_message(chat_id, message)
                                logger.info(f"Sent price alert for {ticker} to chat {chat_id}: {message}")
                                alert['triggered'] = True
                                
                        # One-time Absolute Alerts for Price
                        
                        if alert.get('type') == 'absolute' and not alert.get('triggered', False):
                            # Check if the current price has reached the alert's target value
                            if (current_price >= alert['value'] and previous_price < alert['value']) or (current_price <= alert['value'] and previous_price > alert['value']):
                                message = (f"🔔 Price Alert: {ticker} has reached the target price of ${alert['value']:.2f}. "
                                           f"Previous price was ${previous_price:.2f}. Current price is ${current_price:.2f}.")
                                await bot.send_message(chat_id, message)
                                logger.info(f"Sent price alert for {ticker} to chat {chat_id}: {message}")
                                alert['triggered'] = True  # Mark the alert as triggered

                        # Add similar logic for Continuous Percentage Alerts for Price
                        
                        if alert.get('type') == 'continuous_percentage':
                            last_notified_price = alert.get('last_notified_price', previous_price)
                            percentage_change_since_last_notification = ((current_price - last_notified_price) / last_notified_price) * 100 if last_notified_price else 0
                            logger.info(f"[{ticker}] Last notified price: {last_notified_price}, Current price: {current_price}, Change: {percentage_change_since_last_notification}%")
                            
                            user_alert_value = alert['value']  # This is the user-defined threshold for sending an alert
                            
                            if user_alert_value > 0 and percentage_change_since_last_notification >= user_alert_value:
                                message = (f"🔔 Continuous Price Alert: {ticker} has increased by {percentage_change_since_last_notification:.2f}% (threshold: {user_alert_value}%) since the last notification. "
                                           f"The current price is ${current_price:.2f}.")
                                
                                await bot.send_message(chat_id, message)
                                logger.info(f"Sent continuous price alert for {ticker} to chat {chat_id}: {message}")
                                alert['last_notified_price'] = current_price  # Update last notified price
                                
                                
                            elif user_alert_value < 0 and percentage_change_since_last_notification <= user_alert_value:
                                message = (f"🔔 Continuous Price Alert: {ticker} has decreased by {percentage_change_since_last_notification:.2f}% (threshold: {user_alert_value}%) since the last notification. "
                                           f"The current price is ${current_price:.2f}.")
                                await bot.send_message(chat_id, message)
                                logger.info(f"Sent continuous price alert for {ticker} to chat {chat_id}: {message}")
                                alert['last_notified_price'] = current_price  # Update last notified price

                        # Add similar logic for One-time Percentage Alerts for Volume
                        if alert.get('type') == 'volume_percentage' and not alert.get('triggered', False):
                            previous_volume = alert.get('previous_volume', current_volume)  # Use the current volume as previous if not set
                            volume_change_percentage = ((current_volume - previous_volume) / previous_volume) * 100 if previous_volume else 0
                            logger.info(f"[{ticker}] Volume change from one minute ago: {volume_change_percentage}%")
                            
                            if (alert['value'] > 0 and volume_change_percentage >= alert['value']) or (alert['value'] < 0 and volume_change_percentage <= alert['value']):
                                message = (f"🔔 Volume Alert: {ticker} has met the target volume change of {alert['value']}%. "
                                           f"The current volume is {current_volume:.2f}.")
                                await bot.send_message(chat_id, message)
                                logger.info(f"Sent volume alert for {ticker} to chat {chat_id}: {message}")
                                alert['triggered'] = True
                                alert['previous_volume'] = current_volume
                                
                        # Add similar logic for One-time Absolute Alerts for Volume
                        if alert.get('type') == 'volume_absolute' and not alert.get('triggered', False):
                            if current_volume >= alert['value']:
                                message = (f"🔔 Volume Alert: {ticker} has reached the target volume of {alert['value']}. "
                                           f"The current volume is {current_volume:.2f}.")
                                await bot.send_message(chat_id, message)
                                logger.info(f"Sent volume alert for {ticker} to chat {chat_id}: {message}")
                                alert['triggered'] = True  # Mark the alert as triggered to prevent repeated notifications

                        

                    except Exception as e:
                        logger.error(f"Failed to fetch data for {ticker}. Error: {e}")

        logger.info("Completed monitoring cycle, waiting for the next cycle.")
        await asyncio.sleep(60)  # Adjust sleep time as needed

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
