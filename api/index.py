from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import psycopg2
import csv
import io
from datetime import datetime, timezone

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8716258798:AAH6fuR83RrVhxJJ_SVNIzHjYUW4ehH7iaM')
DB_URL = os.getenv('SUPABASE_DB_URL')
RESEND_API_KEY = os.getenv('RESEND_API_KEY', 're_8jwZ6n1C_KfS46ACtTfGgTC8Vj3x6QpCy')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'reconnectaistudios@gmail.com')

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

def handle_export(chat_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT username, client_name, checkin_time, checkout_time,
               ROUND(EXTRACT(EPOCH FROM (COALESCE(checkout_time, NOW()) - checkin_time))/3600, 2) AS hours,
               latitude, longitude, status
        FROM homecare_sessions
        WHERE checkin_time >= DATE_TRUNC('week', NOW())
        ORDER BY checkin_time DESC
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "📊 No sessions this week to export."

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Carer', 'Client', 'Check-in', 'Check-out', 'Hours', 'Latitude', 'Longitude', 'Status'])
    for row in rows:
        username, client, cin, cout, hours, lat, lng, status = row
        writer.writerow([
            username,
            client or '',
            cin.strftime('%Y-%m-%d %H:%M UTC') if cin else '',
            cout.strftime('%Y-%m-%d %H:%M UTC') if cout else 'Active',
            hours,
            lat or '',
            lng or '',
            status
        ])
    csv_content = output.getvalue()

    # Send via Resend
    week_label = datetime.now(timezone.utc).strftime('Week of %b %d, %Y')
    email_payload = {
        "from": "ReconnectAI Homecare <onboarding@resend.dev>",
        "to": ["fbl11s@gmail.com"],
        "subject": f"Homecare Timesheet Export — {week_label}",
        "html": f"<p>Please find attached the weekly timesheet export for <b>{week_label}</b>.</p><p>Total sessions: <b>{len(rows)}</b></p>",
        "attachments": [
            {
                "filename": f"timesheet_{datetime.now(timezone.utc).strftime('%Y_%m_%d')}.csv",
                "content": csv_content,
                "content_type": "text/csv"
            }
        ]
    }

    try:
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps(email_payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {RESEND_API_KEY}"
            }
        )
        urllib.request.urlopen(req)
        return f"📧 Weekly timesheet ({len(rows)} sessions) sent to <b>{ADMIN_EMAIL}</b>"
    except Exception as e:
        return f"❌ Export failed: {str(e)}"

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
                        reply = "🏥 <b>Welcome to ReconnectAI Homecare!</b>\n\nCommands:\n/checkin [client name] - Start shift\n/checkout - End shift\n/status - Current status\n/report - Today's sessions\n/export - Email weekly timesheet"
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
                    elif command == '/export':
                        reply = handle_export(chat_id)
                        send_message(chat_id, reply)
                    else:
                        send_message(chat_id, "Unknown command. Use /checkin, /checkout, /status, /report, or /export.")

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
