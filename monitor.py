import os
import json
import requests
import asyncio
from playwright.async_api import async_playwright

# --- CONFIG ---
# These load the secrets you saved in GitHub Settings
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# --- YOUR STREAMER LIST ---
STREAMERS = [
    # --- KICK ---
    {"platform": "Kick", "user": "nahoule82k",    "url": "https://kick.com/nahoule82k"},
    {"platform": "Kick", "user": "naimiforever",  "url": "https://kick.com/naimiforever"},
    {"platform": "Kick", "user": "therealpatty",  "url": "https://kick.com/therealpatty"},
    {"platform": "Kick", "user": "marouane53",    "url": "https://kick.com/marouane53"},
    {"platform": "Kick", "user": "ilyaselmaliki", "url": "https://kick.com/ilyaselmaliki"},

    # --- TWITCH ---
    {"platform": "Twitch", "user": "naimiforever", "url": "https://twitch.tv/naimiforever"},
    {"platform": "Twitch", "user": "naimi",        "url": "https://twitch.tv/naimi"},
    {"platform": "Twitch", "user": "shake_make",   "url": "https://twitch.tv/shake_make"},
    {"platform": "Twitch", "user": "dreamerzlel",  "url": "https://twitch.tv/dreamerzlel"}
]

STATE_FILE = "stream_state.json"

def send_alert(text):
    """Sends the notification to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        print(f"--> Sent: {text}")
    except Exception as e:
        print(f"Error sending message: {e}")

async def check_twitch(page, user):
    """Checks Twitch source code for live status"""
    try:
        await page.goto(f"https://www.twitch.tv/{user}", wait_until="domcontentloaded")
        content = await page.content()
        # Twitch adds this hidden text when live
        if '"isLiveBroadcast":true' in content:
            return True
    except:
        pass
    return False

async def check_kick(page, user):
    """Checks Kick API via browser to bypass bot protection"""
    try:
        await page.goto(f"https://kick.com/api/v1/channels/{user}", wait_until="networkidle")
        text = await page.evaluate("document.body.innerText")
        data = json.loads(text)
        if data.get("livestream"):
            return True
    except:
        pass
    return False

async def main():
    print("--- Starting Check ---")
    
    # 1. Load previous state (who was live last time?)
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
            
            # Run the check based on platform
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
            
            print(f"Checked {s['user']} ({s['platform']}): {is_live}")

        await browser.close()

    # 4. Save new state
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)
    
    print("--- Check Complete ---")

if __name__ == "__main__":
    asyncio.run(main())
