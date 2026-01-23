import os
import re
import csv
import subprocess
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import config

# --- CONFIGURATION ---
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") 
REPO_URL = "github.com/satvik-adeptmind/launch-tracker.git" 

CSV_FILE = "launches.csv"

app = App(token=SLACK_BOT_TOKEN)

# --- 1. THE FAKE WEB SERVER  ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def start_health_check():
    # Render assigns a port automatically via the PORT env var
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"🌍 Fake web server running on port {port}")
    server.serve_forever()

# --- HELPER FUNCTIONS ---
def parse_message(text):
    count_match = re.search(r"(\d+)\s*pages?", text, re.IGNORECASE)
    page_count = count_match.group(1) if count_match else "0"
    tranche_match = re.search(r"(Tranche|T)[\s-]?(\d+)", text, re.IGNORECASE)
    tranche = f"T{tranche_match.group(2)}" if tranche_match else "Unknown"
    
    text_lower = text.lower()
    retailer = "Unknown"
    for official_name, keywords in config.RETAILERS.items():
        for keyword in keywords:
            if re.search(r"\b" + re.escape(keyword) + r"\b", text_lower):
                retailer = official_name
                break
        if retailer != "Unknown": break
    return retailer, tranche, page_count

# --- SLACK LOGIC  ---
@app.message(re.compile("prod", re.IGNORECASE))
def handle_prod_message(message, say):
    text = message.get('text', '')
    user_id = message['user']
    retailer, tranche, page_count = parse_message(text)
    
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"🚀 *Prod Launch Detected!*"}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*Retailer:*\n{retailer}"},
            {"type": "mrkdwn", "text": f"*Tranche:*\n{tranche}"},
            {"type": "mrkdwn", "text": f"*Page Count:*\n{page_count}"}
        ]},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "✅ Confirm & Log"}, "style": "primary", "action_id": "confirm_launch", "value": f"{retailer}|{tranche}|{page_count}|{user_id}"},
            {"type": "button", "text": {"type": "plain_text", "text": "❌ Ignore"}, "style": "danger", "action_id": "ignore_launch"}
        ]}
    ]
    say(blocks=blocks, thread_ts=message['ts'])

@app.action("confirm_launch")
def handle_confirmation(ack, body, client):
    ack()
    data = body['actions'][0]['value'].split('|')
    retailer, tranche, count, user_id = data
    
    user_info = client.users_info(user=user_id)
    user_name = user_info['user']['real_name']
    
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Write CSV
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='') as f:
            csv.writer(f).writerow(["Date", "Retailer", "Tranche", "Page_Count", "Approver", "Slack_Link"])

    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([date_str, retailer, tranche, count, user_name, "Link"])
    
    # --- GIT PUSH LOGIC (Cloud Compatible) ---
    try:
        # Configure Git User (Required in cloud)
        subprocess.run(["git", "config", "--global", "user.email", "bot@adeptmind.ai"], check=True)
        subprocess.run(["git", "config", "--global", "user.name", "LaunchBot"], check=True)
        
        subprocess.run(["git", "add", CSV_FILE], check=True)
        subprocess.run(["git", "commit", "-m", f"Log: {retailer}"], check=True)
        
        # PUSH USING THE TOKEN
        # Format: https://TOKEN@github.com/user/repo.git
        remote_url = f"https://{GITHUB_TOKEN}@{REPO_URL}"
        subprocess.run(["git", "push", remote_url, "main"], check=True)
        print("✅ Pushed to GitHub")
        
    except Exception as e:
        print(f"❌ Git Error: {e}")

    client.chat_update(
        channel=body['channel']['id'],
        ts=body['message']['ts'],
        text="Logged!",
        blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": f"✅ *Logged* by <@{body['user']['id']}>"}}]
    )

@app.action("ignore_launch")
def handle_ignore(ack, body, client):
    ack()
    client.chat_delete(channel=body['channel']['id'], ts=body['message']['ts'])

if __name__ == "__main__":
    threading.Thread(target=start_health_check, daemon=True).start()
    
    print("⚡️ Bot is running...")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()