#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json, os, asyncio
from telegram import Bot

BOT_TOKEN = "8968952235:AAFvHPoQ1rTXmDdJQvWt-BYhmvXu4RYXyCs"
ADMIN_IDS = {1090117356, 8371219330}
STATE_FILE = "peuferie_state.json"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
CORS(app)
bot = Bot(token=BOT_TOKEN)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"statut": "dispo", "commandes": []}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "la_peuferie_nancy.html")

@app.route("/<path:filename>")
def static_files(filename):
    try:
        return send_from_directory(BASE_DIR, filename)
    except:
        return "Not found", 404

# Endpoint pour identifier l utilisateur depuis la boutique
@app.route("/api/whoami", methods=["POST"])
def whoami():
    data = request.json or {}
    uid = int(data.get("uid", 0))
    is_admin = uid in ADMIN_IDS
    return jsonify({"uid": uid, "is_admin": is_admin})

@app.route("/api/statut", methods=["GET"])
def get_statut():
    return jsonify({"statut": load_state().get("statut", "dispo")})

@app.route("/api/statut", methods=["POST"])
def set_statut():
    data = request.json
    if int(data.get("telegram_id", 0)) not in ADMIN_IDS:
        return jsonify({"error": "Non autorisé"}), 403
    state = load_state()
    state["statut"] = data.get("statut", "dispo")
    save_state(state)
    return jsonify({"ok": True})

@app.route("/api/commande", methods=["POST"])
def nouvelle_commande():
    commande = request.json
    state = load_state()
    state.setdefault("commandes", []).append(commande)
    save_state(state)
    txt = (
        f"🛒 NOUVELLE COMMANDE\n\n"
        f"📋 {commande.get('orderId')}\n"
        f"🛍 {commande.get('items')}\n"
        f"💰 {commande.get('total')} EUR\n"
        f"💳 {commande.get('payMethod')}\n"
        f"📍 {commande.get('livraison')}"
    )
    loop = asyncio.new_event_loop()
    for admin_id in ADMIN_IDS:
        try:
            loop.run_until_complete(bot.send_message(chat_id=admin_id, text=txt))
        except Exception as e:
            print(f"Erreur: {e}")
    loop.close()
    return jsonify({"ok": True})

# Webhook Telegram
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    from telegram import Update
    from bot_peuferie import get_app
    data = request.get_json()
    if data:
        tg_app = get_app()
        loop = asyncio.new_event_loop()
        async def process():
            await tg_app.initialize()
            update = Update.de_json(data, tg_app.bot)
            await tg_app.process_update(update)
        loop.run_until_complete(process())
        loop.close()
    return "ok"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    # Setup webhook
    import threading, time
    def setup():
        time.sleep(5)
        loop = asyncio.new_event_loop()
        url = f"https://lapeuferie.onrender.com/webhook/{BOT_TOKEN}"
        try:
            loop.run_until_complete(bot.delete_webhook())
            loop.run_until_complete(bot.set_webhook(url=url))
            print(f"Webhook: {url}")
        except Exception as e:
            print(f"Webhook error: {e}")
        loop.close()
    threading.Thread(target=setup, daemon=True).start()
    app.run(host="0.0.0.0", port=port, debug=False)
