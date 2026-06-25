from flask import Flask, request, jsonify
import os
import json
import logging
from datetime import datetime
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Your bot token from environment variables
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8716258798:AAH6fuR83RrVhxJJ_SVNIzHjYUW4ehH7iaM')
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'your-secret-here')

@app.route('/', methods=['GET'])
def home():
    """Root endpoint to verify the app is running"""
    return jsonify({
        "status": "running",
        "app": "ReconnectAI Homecare",
        "version": "1.0",
        "message": "Telegram webhook is ready"
    }), 200

@app.route('/api/telegram-webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram messages (check-in/out with location)"""
    try:
        # Verify webhook secret for security
        secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
        if secret != WEBHOOK_SECRET:
            logger.warning(f"Invalid secret: {secret}")
            return jsonify({"error": "Unauthorized"}), 403

        update = request.get_json()
        logger.info(f"Received update: {update}")

        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            user_id = message['from']['id']
            username = message['from'].get('username', 'Unknown')
            text = message.get('text', '')
            location = message.get('location', None)
            
            # Handle commands
            if text == '/checkin':
                response = handle_checkin(user_id, username, location, chat_id)
                send_telegram_message(chat_id, response)
                
            elif text == '/checkout':
                response = handle_checkout(user_id, username, location, chat_id)
                send_telegram_message(chat_id, response)
                
            elif text == '/status':
                response = get_status(user_id)
                send_telegram_message(chat_id, response)
                
            elif text == '/start':
                response = "🏥 Welcome to ReconnectAI Homecare Time Tracker!\n\n"
                response += "Available commands:\n"
                response += "/checkin - Start your shift (share location)\n"
                response += "/checkout - End your shift (share location)\n"
                response += "/status - Check your current status"
                send_telegram_message(chat_id, response)

        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def handle_checkin(user_id, username, location, chat_id):
    """Process check-in with location"""
    timestamp = datetime.now().isoformat()
    
    checkin_data = {
        "user_id": user_id,
        "username": username,
        "action": "checkin",
        "timestamp": timestamp,
        "location": location,
        "app": "ReconnectAI Homecare"
    }
    
    logger.info(f"Check-in: {checkin_data}")
    
    response = f"✅ Check-in successful!\n"
    response += f"👤 User: @{username}\n"
    response += f"⏰ Time: {timestamp}\n"
    if location:
        response += f"📍 Location confirmed (lat: {location.get('latitude')}, lon: {location.get('longitude')})"
    else:
        response += f"⚠️ No location shared. Please share your location."
    
    return response

def handle_checkout(user_id, username, location, chat_id):
    """Process check-out with location"""
    timestamp = datetime.now().isoformat()
    
    checkout_data = {
        "user_id": user_id,
        "username": username,
        "action": "checkout",
        "timestamp": timestamp,
        "location": location,
        "app": "ReconnectAI Homecare"
    }
    
    logger.info(f"Check-out: {checkout_data}")
    
    response = f"✅ Check-out successful!\n"
    response += f"👤 User: @{username}\n"
    response += f"⏰ Time: {timestamp}\n"
    if location:
        response += f"📍 Location confirmed"
    
    return response

def get_status(user_id):
    """Get current status for a user"""
    return "Current status: Not checked in"

def send_telegram_message(chat_id, text):
    """Send a message back to the user via Telegram API"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return None

if __name__ == '__main__':
    app.run(debug=True, port=5000)
