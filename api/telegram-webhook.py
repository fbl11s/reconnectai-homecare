from flask import Flask, request, jsonify
import os
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8716258798:AAH6fuR83RrVhxJJ_SVNIzHjYUW4ehH7iaM')

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "running",
        "app": "ReconnectAI Homecare",
        "message": "Telegram webhook is ready"
    })

@app.route('/api/telegram-webhook', methods=['POST'])
def webhook():
    try:
        # Get the incoming data
        data = request.get_json()
        logger.info(f"Received: {data}")

        if not data:
            return jsonify({"error": "No data"}), 400

        # Process the message
        if 'message' in data:
            msg = data['message']
            chat_id = msg['chat']['id']
            text = msg.get('text', '')
            
            # Handle commands
            if text == '/checkin':
                send_message(chat_id, "✅ Check-in successful!")
            elif text == '/checkout':
                send_message(chat_id, "✅ Check-out successful!")
            elif text == '/status':
                send_message(chat_id, "Status: Not checked in")
            elif text == '/start':
                send_message(chat_id, "🏥 Welcome to ReconnectAI Homecare!\n\nCommands:\n/checkin - Start shift\n/checkout - End shift\n/status - Check status")

        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

def send_message(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={"chat_id": chat_id, "text": text})
        logger.info(f"Message sent: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send: {e}")

if __name__ == '__main__':
    app.run(debug=True)
