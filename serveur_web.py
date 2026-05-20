#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json, os, asyncio, threading
from telegram import Bot, Update
from bot_peuferie import get_app, BOT_TOKEN, ADMIN_IDS, STATE_FILE, WEBHOOK_URL, PORT

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
CORS(app)
bot = Bot(token=BOT_TOKEN)
tg_app = get_app()

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

# Webhook Telegram — reçoit les updates
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    if data:
        loop = asyncio.new_event_loop()
        async def process():
            await tg_app.initialize()
            update = Update.de_json(data, tg_app.bot)
            await tg_app.process_update(update)
        loop.run_until_complete(process())
        loop.close()
    return "ok"

@app.route("/api/statut", methods=["GET"])
def get_statut():
    return jsonify({"statut": load_state().get("statut", "dispo")})

@app.route("/api/statut", methods=["POST"])
def set_statut():
    data = request.json
    if data.get("telegram_id") not in ADMIN_IDS:
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
        f"🛒 *NOUVELLE COMMANDE !*\n\n"
        f"📋 `{commande.get('orderId')}`\n"
        f"🛍️ {commande.get('items')}\n"
        f"💰 *{commande.get('total')} €*\n"
        f"💳 {commande.get('payMethod')}\n"
        f"📍 `{commande.get('livraison')}`"
    )
    loop = asyncio.new_event_loop()
    for admin_id in ADMIN_IDS:
        try:
            loop.run_until_complete(bot.send_message(chat_id=admin_id, text=txt, parse_mode="Markdown"))
        except Exception as e:
            print(f"Erreur notif: {e}")
    loop.close()
    return jsonify({"ok": True})

def setup_webhook():
    """Configure le webhook Telegram au démarrage"""
    import time
    time.sleep(3)
    loop = asyncio.new_event_loop()
    webhook_url = f"{WEBHOOK_URL}/webhook/{BOT_TOKEN}"
    try:
        loop.run_until_complete(bot.delete_webhook())
        loop.run_until_complete(bot.set_webhook(url=webhook_url))
        print(f"✅ Webhook configuré : {webhook_url}")
    except Exception as e:
        print(f"Erreur webhook: {e}")
    loop.close()

if __name__ == "__main__":
    # Configurer le webhook en arrière-plan
    t = threading.Thread(target=setup_webhook, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=PORT, debug=False)
