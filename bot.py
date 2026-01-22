import os
import re
import csv
import subprocess # Needed for Git commands
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv # Needed to read .env file
import config

# --- LOAD SECRETS ---
load_dotenv() # This loads the variables from .env

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")

CSV_FILE = "launches.csv"

# Initialize App
app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)

# --- INITIALIZE CSV ---
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Retailer", "Tranche", "Page_Count", "Approver", "Slack_Link"])

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
        if retailer != "Unknown":
            break
            
    return retailer, tranche, page_count

# --- SLACK LISTENER ---
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

# --- ACTION HANDLER WITH GIT PUSH ---
@app.action("confirm_launch")
def handle_confirmation(ack, body, client):
    ack()
    data = body['actions'][0]['value'].split('|')
    retailer, tranche, count, user_id = data
    
    user_info = client.users_info(user=user_id)
    user_name = user_info['user']['real_name']
    
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    channel_id = body['channel']['id']
    msg_ts = body['message']['ts']
    slack_link = f"https://adeptmind.slack.com/archives/{channel_id}/p{msg_ts.replace('.','')}"

    # 1. Write to CSV
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([date_str, retailer, tranche, count, user_name, slack_link])
    
    # 2. AUTO-PUSH TO GITHUB
    try:
        print("🔄 Pushing to GitHub...")
        subprocess.run(["git", "add", CSV_FILE], check=True)
        subprocess.run(["git", "commit", "-m", f"Log launch: {retailer} {tranche}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ Successfully pushed to GitHub")
    except Exception as e:
        print(f"❌ Git Push Failed: {e}")

    # 3. Update Slack
    client.chat_update(
        channel=channel_id,
        ts=msg_ts,
        text="Logged!",
        blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": f"✅ *Logged & Pushed to Dashboard* by <@{body['user']['id']}>"}}]
    )

@app.action("ignore_launch")
def handle_ignore(ack, body, client):
    ack()
    client.chat_delete(channel=body['channel']['id'], ts=body['message']['ts'])

if __name__ == "__main__":
    print("⚡️ Bot is running...")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()