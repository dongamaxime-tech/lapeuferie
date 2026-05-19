#!/usr/bin/env python3
"""
Lance le serveur Flask + le bot Telegram en parallèle
"""
import threading
import asyncio
import logging
from serveur_web import app
from bot_peuferie import main as bot_main

logging.basicConfig(level=logging.INFO)

def run_flask():
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)

def run_bot():
    asyncio.run(bot_main())

if __name__ == "__main__":
    # Flask dans un thread
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    # Bot dans le thread principal
    run_bot()
