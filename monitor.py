import os
import json
import requests
import asyncio
from playwright.async_api import async_playwright

# --- CONFIG ---
# We get these from GitHub "Secrets" (Setup in Step 5)
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

STREAMERS = [
    {"platform": "Twitch", "user": "shroud", "url": "https://twitch.tv/shroud"},
    {"platform": "Kick",   "user": "xqc",    "url": "https://kick.com/xqc"}
]

STATE_FILE = "stream_state.json"

def send_alert(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        print(f"--> Sent: {text}")
    except Exception as e:
        print(f"Error sending message: {e}")

async def check_twitch(page, user):
    try:
        await page.goto(f"https://www.twitch.tv/{user}", wait_until="domcontentloaded")
        content = await page.content()
        if '"isLiveBroadcast":true' in content:
            return True
    except:
        pass
    return False

async def check_kick(page, user):
    try:
        # Kick API via browser
        await page.goto(f"https://kick.com/api/v1/channels/{user}", wait_until="networkidle")
        text = await page.evaluate("document.body.innerText")
        data = json.loads(text)
        if data.get("livestream"):
            return True
    except:
        pass
    return False

async def main():
    # 1. Load previous state
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            try: state = json.load(f)
            except: pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 2. Check each streamer
        for s in STREAMERS:
            is_live = False
            key = f"{s['platform']}_{s['user']}"
            
            if s['platform'] == "Twitch":
                is_live = await check_twitch(page, s['user'])
            elif s['platform'] == "Kick":
                is_live = await check_kick(page, s['user'])
            
            # 3. Logic: Only notify if they went from Offline -> Online
            was_live = state.get(key, False)
            
            if is_live and not was_live:
                send_alert(f"🚨 <b>{s['user']}</b> is LIVE on {s['platform']}!\n{s['url']}")
                state[key] = True
            elif not is_live:
                state[key] = False
            
            print(f"Checked {s['user']}: {is_live}")

        await browser.close()

    # 4. Save new state
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

if __name__ == "__main__":
    asyncio.run(main())
