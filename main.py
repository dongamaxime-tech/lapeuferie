#!/usr/bin/env python3
import threading
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)

def run_flask():
    from serveur_web import app
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)

def run_bot():
    from bot_peuferie import main as bot_main
    asyncio.run(bot_main())

if __name__ == "__main__":
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    run_bot()
