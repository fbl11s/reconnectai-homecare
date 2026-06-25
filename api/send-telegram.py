from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

@app.route('/api/send-telegram', methods=['POST'])
def send_telegram():
    """Send a message to a Telegram user (for notifications)"""
    try:
        data = request.get_json()
        chat_id = data.get('chat_id')
        message = data.get('message')
        
        if not chat_id or not message:
            return jsonify({"error": "Missing chat_id or message"}), 400
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=payload)
        return jsonify(response.json()), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
