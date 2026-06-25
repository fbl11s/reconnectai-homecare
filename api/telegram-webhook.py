from flask import Flask, request, jsonify
import os
import json
import logging
from datetime import datetime
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Your bot token
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8716258798:AAH6fuR83RrVhxJJ_SVNIzHjYUW4ehH7iaM')

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
    """Handle incoming Telegram messages"""
    try:
        # Get the incoming data
        update = request.get_json()
        logger.info(f"Received update: {update}")

        if not update:
            return jsonify({"error": "No data"}), 400

        # Process the message
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            # Handle commands
            if text == '/checkin':
                response = "✅ Check-in successful!\n📍 Location not verified"
                send_message(chat_id, response)
            elif text == '/checkout':
                response = "✅ Check-out successful!"
                send_message(chat_id, response)
            elif text == '/status':
                response = "Current status: Not checked in"
                send_message(chat_id, response)
            elif text == '/start':
                response = "🏥 Welcome to ReconnectAI Homecare Time Tracker!\n\n"
                response += "Available commands:\n"
                response += "/checkin - Start your shift\n"
                response += "/checkout - End your shift\n"
                response += "/status - Check your current status"
                send_message(chat_id, response)

        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def send_message(chat_id, text):
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
