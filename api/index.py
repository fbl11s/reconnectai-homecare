from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import psycopg2
from datetime import datetime, timezone

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8716258798:AAH6fuR83RrVhxJJ_SVNIzHjYUW4ehH7iaM')
DB_URL = os.getenv('SUPABASE_DB_URL')

def get_conn():
    return psycopg2.connect(DB_URL, sslmode='require')

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req)

def handle_checkin(chat_id, username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM homecare_sessions WHERE chat_id=%s AND status='in'", (chat_id,))
    if cur.fetchone():
        conn.close()
        return "⚠️ You are already checked in. Use /checkout to end your shift."
    cur.execute(
        "INSERT INTO homecare_sessions (chat_id, username, checkin_time, status) VALUES (%s, %s, %s, 'in')",
        (chat_id, username, datetime.now(timezone.utc))
    )
    conn.commit()
    conn.close()
    now = datetime.now(timezone.utc).strftime('%H:%M UTC')
    return f"✅ Checked in at {now}\n\nUse /checkout when your shift ends."

def handle_checkout(chat_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, checkin_time FROM homecare_sessions WHERE chat_id=%s AND status='in'", (chat_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return "⚠️ You are not currently checked in. Use /checkin to start a shift."
    session_id, checkin_time = row
    checkout_time = datetime.now(timezone.utc)
    duration = checkout_time - checkin_time
    hours, remainder = divmod(int(duration.total_seconds()), 3600)
    minutes = remainder // 60
    cur.execute(
        "UPDATE homecare_sessions SET checkout_time=%s, status='out' WHERE id=%s",
        (checkout_time, session_id)
    )
    conn.commit()
    conn.close()
    return f"✅ Checked out at {checkout_time.strftime('%H:%M UTC')}\n⏱ Shift duration: {hours}h {minutes}m"

def handle_status(chat_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT checkin_time FROM homecare_sessions WHERE chat_id=%s AND status='in'", (chat_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return "📋 Status: Not currently checked in."
    checkin_time = row[0]
    duration = datetime.now(timezone.utc) - checkin_time
    hours, remainder = divmod(int(duration.total_seconds()), 3600)
    minutes = remainder // 60
    return f"📋 Status: Checked in\n⏱ Duration: {hours}h {minutes}m\nSince: {checkin_time.strftime('%H:%M UTC')}"

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
                username = msg['chat'].get('username') or msg['chat'].get('first_name', 'unknown')
                text = msg.get('text', '')

                if text == '/start':
                    reply = "🏥 Welcome to ReconnectAI Homecare!\n\n/checkin - Start shift\n/checkout - End shift\n/status - Check current status"
                elif text == '/checkin':
                    reply = handle_checkin(chat_id, username)
                elif text == '/checkout':
                    reply = handle_checkout(chat_id)
                elif text == '/status':
                    reply = handle_status(chat_id)
                else:
                    reply = "Unknown command. Use /checkin, /checkout, or /status."

                send_message(chat_id, reply)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
