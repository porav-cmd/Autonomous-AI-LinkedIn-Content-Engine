from django.shortcuts import render

# Create your views here.

import requests
import time

import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

url = f"https://api.telegram.org/bot{token}/getUpdates"


offset = None

while True:
    params = {}
    if offset :
        params["offset"] = offset
    response = requests.get(url=url,params=params)   
    data = response.json()
    update = data["result"]
    if not update:
        print("No New MESSAGE")
        time.sleep(2)
        continue
    for items in update:
        message = items["message"]
        text = message["text"]
        sender = message["from"]["first_name"]
        print(sender,":",text)
        offset = items["update_id"]+1
        time.sleep(2)