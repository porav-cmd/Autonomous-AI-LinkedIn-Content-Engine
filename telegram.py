import requests
import time
import os
from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(text):
    url = f"{BASE_URL}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": text
    }

    response = requests.post(url, data=data)

    return response.json()


def send_photo(photo_path, caption=None):
    url = f"{BASE_URL}/sendPhoto"
    data = {"chat_id": CHAT_ID}

    if caption and len(caption) > 1024:
        data["caption"] = caption[:1020] + "..."
    elif caption:
        data["caption"] = caption

    with open(photo_path, "rb") as photo_file:
        files = {"photo": photo_file}
        response = requests.post(url, data=data, files=files)

    res_json = response.json()
    print("[Telegram API Response]:", res_json)

    # If text exceeds 1024 chars, send the full post text in a follow-up message
    if caption and len(caption) > 1024:
        send_message(f"📢 Full Post Draft:\n\n{caption}")

    return res_json


def get_latest_update_id():

    url = f"{BASE_URL}/getUpdates"

    response = requests.get(url)

    data = response.json()

    updates = data["result"]

    if not updates:
        return None

    latest_update_id = updates[-1]["update_id"]

    return latest_update_id

def wait_for_reply(offset=None, max_wait_seconds=60):
    if offset is None:
        latest_update_id = get_latest_update_id()
        offset = 0 if latest_update_id is None else latest_update_id + 1

    url = f"{BASE_URL}/getUpdates"
    start_time = time.time()

    while time.time() - start_time < max_wait_seconds:
        try:
            params = {
                "offset": offset,
                "timeout": 5
            }
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            updates = data.get("result", [])

            if not updates:
                print(f"Waiting for Telegram reply ({int(max_wait_seconds - (time.time() - start_time))}s remaining)...")
                time.sleep(2)
                continue

            for item in updates:
                update_id = item["update_id"]
                print("Received update:", update_id)
                if "message" in item and "text" in item["message"]:
                    user_text = item["message"]["text"].strip()
                    print(f"User replied: {user_text}")
                    return user_text
        except Exception as e:
            print(f"Telegram polling warning ({e}). Retrying...")
            time.sleep(2)

    print(f"\n[Telegram] No reply received within {max_wait_seconds}s. Auto-selecting 'yes' for image generation...")
    return "yes"


def main():
    latest_update_id = get_latest_update_id()

    if latest_update_id is None:

        starting_offset = 0

    else:

        starting_offset = latest_update_id + 1

    print("Starting offset:", starting_offset)


    question = (
        "Do you want a screenshot, "
        "an AI image, or no image today?"
    )

    send_message(question)

    print("Question sent.")

    reply = wait_for_reply(starting_offset)

    print("Final reply:", reply)

if __name__ == "__main__":
    main()