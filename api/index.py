from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8716258798:AAH6fuR83RrVhxJJ_SVNIzHjYUW4ehH7iaM')

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "running",
            "app": "ReconnectAI Homecare",
            "message": "Telegram webhook is ready"
        }).encode())

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
            if 'message' in data:
                msg = data['message']
                chat_id = msg['chat']['id']
                text = msg.get('text', '')
                replies = {
                    '/start':    "🏥 Welcome to ReconnectAI Homecare!\n\n/checkin - Start shift\n/checkout - End shift\n/status - Check status",
                    '/checkin':  "✅ Check-in recorded!",
                    '/checkout': "✅ Check-out recorded!",
                    '/status':   "📋 Status: Not currently checked in",
                }
                if text in replies:
                    send_message(chat_id, replies[text])
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
