import os
import re
import csv
import io
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from github import Github, GithubException, Auth  # <--- CHANGED: Added Auth import
import config

# --- CONFIGURATION ---
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "").strip()
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "").strip()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()

GITHUB_REPO_NAME = "satvik-adeptmind/launch-tracker" 
CSV_FILENAME = "launches.csv"

app = App(token=SLACK_BOT_TOKEN)

# --- 1. HEALTH CHECK SERVER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
    
    # <--- CHANGED: Added do_HEAD to fix the 501 errors in logs
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def start_health_check():
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

def update_github_csv(new_row_list):
    # <--- CHANGED: Updated Authentication method to fix DeprecationWarning
    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    
    repo = g.get_repo(GITHUB_REPO_NAME)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            try:
                file_content = repo.get_contents(CSV_FILENAME)
                csv_data = file_content.decoded_content.decode("utf-8")
                sha = file_content.sha
                file_exists = True
            except:
                csv_data = "Date,Retailer,Tranche,Page_Count,Approver,Slack_Link\n"
                sha = None
                file_exists = False

            output = io.StringIO()
            # Write existing data first
            if file_exists:
                output.write(csv_data)
                if not csv_data.endswith("\n"):
                    output.write("\n")
            
            # Append new row
            writer = csv.writer(output)
            writer.writerow(new_row_list)
            updated_content = output.getvalue()

            commit_message = f"Log: {new_row_list[1]} by {new_row_list[4]}"
            
            if file_exists:
                repo.update_file(CSV_FILENAME, commit_message, updated_content, sha)
            else:
                repo.create_file(CSV_FILENAME, commit_message, updated_content)
            
            print(f"✅ Successfully logged to GitHub: {new_row_list}")
            return True

        except GithubException as e:
            if e.status == 409:
                print(f"⚠️ Concurrency conflict (Attempt {attempt+1}). Retrying...")
                time.sleep(1)
                continue
            else:
                print(f"❌ GitHub Error: {e}")
                return False
    return False

# --- SLACK LOGIC ---
@app.message(re.compile(r"\d+\s*pages?.*pushed\s+to\s+prod", re.IGNORECASE | re.DOTALL))
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
    # <--- CHANGED: Added text argument to fix UserWarning
    say(blocks=blocks, text=f"Prod Launch Detected: {retailer}", thread_ts=message['ts'])

@app.action("confirm_launch")
def handle_confirmation(ack, body, client):
    ack()
    
    data = body['actions'][0]['value'].split('|')
    retailer, tranche, count, original_user_id = data
    approver_id = body['user']['id']
    
    user_info = client.users_info(user=approver_id)
    approver_name = user_info['user']['real_name']
    
    try:
        permalink_res = client.chat_getPermalink(channel=body['channel']['id'], message_ts=body['message']['thread_ts'])
        slack_link = permalink_res['permalink']
    except:
        slack_link = "Link not found"

    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    row = [date_str, retailer, tranche, count, approver_name, slack_link]
    
    def background_update():
        success = update_github_csv(row)
        
        if success:
            client.chat_update(
                channel=body['channel']['id'],
                ts=body['message']['ts'],
                text="Logged!",
                blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": f"✅ *Logged* by <@{approver_id}> for {retailer}"}}]
            )
        else:
            client.chat_postMessage(
                channel=body['channel']['id'],
                thread_ts=body['message']['thread_ts'],
                text=f"❌ Failed to log to GitHub. Please check bot logs."
            )

    threading.Thread(target=background_update).start()

@app.action("ignore_launch")
def handle_ignore(ack, body, client):
    ack()
    client.chat_delete(channel=body['channel']['id'], ts=body['message']['ts'])

if __name__ == "__main__":
    threading.Thread(target=start_health_check, daemon=True).start()
    print("⚡️ Bot is running...")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
