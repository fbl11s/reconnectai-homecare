import json

def handler(request, context):
    """Vercel serverless function entry point"""
    
    # Handle GET requests
    if request.method == 'GET':
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'status': 'running',
                'app': 'ReconnectAI Homecare',
                'message': 'Telegram webhook is ready'
            })
        }
    
    # Handle POST requests
    if request.method == 'POST':
        try:
            data = request.get_json()
            print(f"Received: {data}")
            
            if data and 'message' in data:
                msg = data['message']
                chat_id = msg['chat']['id']
                text = msg.get('text', '')
                
                import requests
                import os
                
                BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8716258798:AAH6fuR83RrVhxJJ_SVNIzHjYUW4ehH7iaM')
                
                if text == '/checkin':
                    send_message(chat_id, "✅ Check-in successful!", BOT_TOKEN)
                elif text == '/checkout':
                    send_message(chat_id, "✅ Check-out successful!", BOT_TOKEN)
                elif text == '/status':
                    send_message(chat_id, "Status: Not checked in", BOT_TOKEN)
                elif text == '/start':
                    send_message(chat_id, "🏥 Welcome to ReconnectAI Homecare!\n\nCommands:\n/checkin - Start shift\n/checkout - End shift\n/status - Check status", BOT_TOKEN)
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'status': 'ok'})
            }
            
        except Exception as e:
            print(f"Error: {e}")
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': str(e)})
            }
    
    return {
        'statusCode': 405,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'error': 'Method not allowed'})
    }

def send_message(chat_id, text, token):
    import requests
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        response = requests.post(url, json={"chat_id": chat_id, "text": text})
        print(f"Message sent: {response.status_code}")
    except Exception as e:
        print(f"Failed to send: {e}")
