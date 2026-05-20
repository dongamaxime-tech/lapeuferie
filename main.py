#!/usr/bin/env python3
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from serveur_web import app, setup_webhook
import threading

if __name__ == "__main__":
    t = threading.Thread(target=setup_webhook, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
