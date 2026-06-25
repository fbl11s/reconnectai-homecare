from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.parse
import psycopg2
from datetime import datetime, timezone

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8716258798:AAH6fuR83RrVhxJJ_SVNIzHjYUW4ehH7iaM')
DB_URL = os.getenv('SUPABASE_DB_URL')

def get_conn():
    return psycopg2.connect(DB_URL, sslmode='require')

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req)

def request_location(chat_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "📍 Please share your location to complete check-in:",
        "reply_markup": {
            "keyboard": [[{"text": "📍 Share Location", "request_location": True}]],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req)

def handle_checkin(chat_id, username, client=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM homecare_sessions WHERE chat_id=%s AND status='in'", (chat_id,))
    if cur.fetchone():
        conn.close()
        return "⚠️ You are already checked in. Use /checkout to end your shift.", False
    cur.execute(
        "INSERT INTO homecare_sessions (chat_id, username, checkin_time, status, client_name) VALUES (%s, %s, %s, 'in', %s)",
        (chat_id, username, datetime.now(timezone.utc), client)
    )
    conn.commit()
    conn.close()
    now = datetime.now(timezone.utc).strftime('%H:%M UTC')
    client_str = f" for <b>{client}</b>" if client else ""
    return f"✅ Checked in{client_str} at {now}\n\nPlease share your location 👇", True

def handle_location(chat_id, latitude, longitude):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE homecare_sessions SET latitude=%s, longitude=%s WHERE chat_id=%s AND status='in'",
        (latitude, longitude, chat_id)
    )
    conn.commit()
    conn.close()
    maps_url = f"https://maps.google.com/?q={latitude},{longitude}"
    return f"📍 Location recorded!\n<a href='{maps_url}'>View on map</a>\n\nUse /checkout when your shift ends."

def handle_checkout(chat_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, checkin_time, client_name, latitude, longitude FROM homecare_sessions WHERE chat_id=%s AND status='in'", (chat_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return "⚠️ You are not currently checked in. Use /checkin to start a shift."
    session_id, checkin_time, client_name, lat, lng = row
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
    client_str = f"\n👤 Client: <b>{client_name}</b>" if client_name else ""
    location_str = f"\n📍 Check-in location recorded" if lat else "\n📍 No location recorded"
    return f"✅ Checked out at {checkout_time.strftime('%H:%M UTC')}{client_str}\n⏱ Shift duration: {hours}h {minutes}m{location_str}"

def handle_status(chat_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT checkin_time, client_name, latitude FROM homecare_sessions WHERE chat_id=%s AND status='in'", (chat_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return "📋 Status: Not currently checked in."
    checkin_time, client_name, lat = row
    duration = datetime.now(timezone.utc) - checkin_time
    hours, remainder = divmod(int(duration.total_seconds()), 3600)
    minutes = remainder // 60
    client_str = f"\n👤 Client: <b>{client_name}</b>" if client_name else ""
    location_str = "✅ Recorded" if lat else "❌ Not recorded"
    return f"📋 Status: Checked in{client_str}\n⏱ Duration: {hours}h {minutes}m\n🕐 Since: {checkin_time.strftime('%H:%M UTC')}\n📍 Location: {location_str}"

def handle_report(chat_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT username, client_name, checkin_time, checkout_time,
               EXTRACT(EPOCH FROM (COALESCE(checkout_time, NOW()) - checkin_time))/3600 AS hours
        FROM homecare_sessions
        WHERE DATE(checkin_time) = CURRENT_DATE
        ORDER BY checkin_time DESC
        LIMIT 20
    """)
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return "📊 No sessions recorded today."
    lines = ["📊 <b>Today's Sessions</b>\n"]
    for username, client, cin, cout, hrs in rows:
        status = "✅ Complete" if cout else "🟢 Active"
        client_str = f" → {client}" if client else ""
        lines.append(f"👤 {username}{client_str}\n🕐 {cin.strftime('%H:%M')} - {'--:--' if not cout else cout.strftime('%H:%M')} ({hrs:.1f}h) {status}\n")
    return "\n".join(lines)

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

                # Handle location message
                if 'location' in msg:
                    lat = msg['location']['latitude']
                    lng = msg['location']['longitude']
                    reply = handle_location(chat_id, lat, lng)
                    send_message(chat_id, reply)
                else:
                    text = msg.get('text', '')
                    parts = text.split(' ', 1)
                    command = parts[0]
                    arg = parts[1].strip() if len(parts) > 1 else None

                    if command == '/start':
                        reply = "🏥 <b>Welcome to ReconnectAI Homecare!</b>\n\nCommands:\n/checkin [client name] - Start shift\n/checkout - End shift\n/status - Current status\n/report - Today's sessions"
                        send_message(chat_id, reply)
                    elif command == '/checkin':
                        reply, needs_location = handle_checkin(chat_id, username, arg)
                        send_message(chat_id, reply)
                        if needs_location:
                            request_location(chat_id)
                    elif command == '/checkout':
                        reply = handle_checkout(chat_id)
                        send_message(chat_id, reply)
                    elif command == '/status':
                        reply = handle_status(chat_id)
                        send_message(chat_id, reply)
                    elif command == '/report':
                        reply = handle_report(chat_id)
                        send_message(chat_id, reply)
                    else:
                        send_message(chat_id, "Unknown command. Use /checkin, /checkout, /status, or /report.")

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
