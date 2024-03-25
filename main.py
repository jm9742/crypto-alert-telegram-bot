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
    
exchange = async_ccxt.bitmart({'enableRateLimit': False})

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
        # Check if user input contains two values (e.g., "5, -5") and split them if so
        values = []
        if ',' in user_input:
            values = [float(val.strip()) for val in user_input.split(',')]
            alert_direction = f"an increase of {values[0]}% or a decrease of {-values[1]}%" if 'percentage' in alert_subtype else ""
        else:
            values = [float(user_input)]  # Single value for traditional alerts
            alert_direction = "increase" if values[0] > 0 else "decrease" if 'percentage' in alert_subtype else ""

        # Fetch current data for the ticker
        current_data = await exchange.fetch_ticker(USER_DATA[chat_id]['ticker'])
        current_price = current_data['last']
        current_change = current_data['percentage']
        current_volume = current_data['quoteVolume']
        
        # Prepare alert data and message based on subtype
        for value in values:
            alert_info = {
                'type': alert_subtype, 
                'value': value, 
                'ticker': USER_DATA[chat_id]['ticker']
            }

            # Customize message based on alert subtype and values
            if alert_subtype == 'percentage' or alert_subtype == 'volume_percentage':
                if len(values) == 2:  # Dual values
                    response_message = f"✅ Alert set successfully for {alert_direction} for {USER_DATA[chat_id]['ticker']}.\n Current Price: ${current_price:.2f}\n 24H Change: {current_change:.2f}%"
                    
                else:  # Single value
                    response_message = f"✅ Alert set successfully for a {value}% {alert_direction} for {USER_DATA[chat_id]['ticker']}.\n Current Price: ${current_price:.2f}\n 24H Change: {current_change:.2f}%"
           
            elif alert_subtype == 'absolute':
                response_message = f"✅ Price alert set successfully to notify when price reaches ${value:.2f} for {USER_DATA[chat_id]['ticker']}.\n Current Price: ${current_price:.2f}\n 24H Change: {current_change:.2f}%"
            
            elif alert_subtype == 'volume_absolute':
                response_message = f"✅ Volume alert set successfully to notify when volume reaches {value} for {USER_DATA[chat_id]['ticker']}.\n Current Volume: {current_volume:.2f}"

            # Update user data and send the alert setup confirmation message
            finalize_alert_setup(chat_id, alert_info)
            await update.message.reply_text(response_message)

    except ValueError:
        await update.message.reply_text("Please enter a valid number or a valid number range in the format x, -y.")
    finally:
        USER_STATES[chat_id] = 0  # Reset the user state after processing.

import asyncio
import logging

logger = logging.getLogger(__name__)

async def monitor_prices_and_volumes():
    while True:
        logger.info("Starting the monitoring loop.")
        for chat_id, user_info in USER_DATA.items():
            alerts = user_info.get('alerts', [])
            for alert in alerts:
                ticker = alert.get('ticker')
                try:
                    current_data = await exchange.fetch_ticker(ticker)
                    current_price = current_data['last']
                    twenty_four_hour_change = current_data['percentage']
                    current_volume = current_data['quoteVolume']

                    # Handle Continuous Percentage Alerts for Price
                    if alert.get('type') == 'absolute' and not alert.get('triggered', False):
                            # Check if the current price has reached the alert's target value
                            if (current_price >= alert['value'] and previous_price < alert['value']) or (current_price <= alert['value'] and previous_price > alert['value']):
                                message = (f"🔔 Price Alert: {ticker} has reached the target price of ${alert['value']:.2f}. "
                                           f"Previous price was ${previous_price:.2f}. Current price is ${current_price:.2f}.")
                                await bot.send_message(chat_id, message)
                                logger.info(f"Sent price alert for {ticker} to chat {chat_id}: {message}")
                                alert['triggered'] = True  # Mark the alert as triggered
                    
                    if alert.get('type') == 'percentage':
                        previous_price = alert.get('previous_price', current_price)
                        alert['previous_price'] = current_price  # Update for next iteration
                        price_change_percentage = ((current_price - previous_price) / previous_price) * 100 if previous_price else 0

                        if abs(price_change_percentage) >= abs(alert['value']):
                            direction = "increased" if price_change_percentage > 0 else "decreased"
                            message = f"🔔 Continuous Price Alert: {ticker} has {direction} by {abs(price_change_percentage):.2f}% since the last notification. The current price is ${current_price:.2f}."
                            await bot.send_message(chat_id, message)
                            logger.info(f"Sent continuous price alert for {ticker} to chat {chat_id}. {message}")

                    # Handle Continuous Percentage Alerts for Volume
                    if alert.get('type') == 'volume_percentage':
                        previous_volume = alert.get('previous_volume', current_volume)
                        alert['previous_volume'] = current_volume  # Update for next iteration
                        volume_change_percentage = ((current_volume - previous_volume) / previous_volume) * 100 if previous_volume else 0

                        if abs(volume_change_percentage) >= abs(alert['value']):
                            direction = "increased" if volume_change_percentage > 0 else "decreased"
                            message = f"🔔 Continuous Volume Alert: {ticker} has {direction} by {abs(volume_change_percentage):.2f}% since the last notification. The current volume is {current_volume:.2f}."
                            await bot.send_message(chat_id, message)
                            logger.info(f"Sent continuous volume alert for {ticker} to chat {chat_id}. {message}")
                    
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
        await asyncio.sleep(5)  # Adjust sleep time as needed

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
