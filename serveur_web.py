#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json, os, asyncio, requests
from telegram import Bot

BOT_TOKEN = "8968952235:AAFvHPoQ1rTXmDdJQvWt-BYhmvXu4RYXyCs"
ADMIN_IDS = {1090117356, 8371219330}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Supabase
SUPABASE_URL = "https://veqzfrsuiibgrruzjrgc.supabase.co"
SUPABASE_KEY = "sb_publishable_lVEgsAXANGn5kSCXIhNYBA_cnuA4N2z"
SUPABASE_SECRET = "sb_secret_OpiXMxA7R0tU_3xhPmva6Q_MtIormd-"

def sb_get(key):
    """Lire une valeur depuis Supabase"""
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/pufferie_state?key=eq.{key}&select=value",
        headers={
            "apikey": SUPABASE_SECRET,
            "Authorization": f"Bearer {SUPABASE_SECRET}"
        }
    )
    if r.status_code == 200:
        data = r.json()
        if data:
            return data[0]['value']
    return None

def sb_set(key, value):
    """Écrire une valeur dans Supabase"""
    requests.patch(
        f"{SUPABASE_URL}/rest/v1/pufferie_state?key=eq.{key}",
        headers={
            "apikey": SUPABASE_SECRET,
            "Authorization": f"Bearer {SUPABASE_SECRET}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        },
        json={"value": value, "updated_at": "now()"}
    )

app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
CORS(app)
bot = Bot(token=BOT_TOKEN)

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "la_peuferie_nancy.html")

@app.route("/<path:filename>")
def static_files(filename):
    try:
        return send_from_directory(BASE_DIR, filename)
    except:
        return "Not found", 404

@app.route("/api/whoami", methods=["POST"])
def whoami():
    data = request.json or {}
    uid = int(data.get("uid", 0))
    return jsonify({"uid": uid, "is_admin": uid in ADMIN_IDS})

@app.route("/api/statut", methods=["GET"])
def get_statut():
    val = sb_get("statut")
    return jsonify({"statut": val or "dispo"})

@app.route("/api/statut", methods=["POST"])
def set_statut():
    data = request.json or {}
    if int(data.get("telegram_id", 0)) not in ADMIN_IDS:
        return jsonify({"error": "Non autorisé"}), 403
    sb_set("statut", data.get("statut", "dispo"))
    return jsonify({"ok": True})

@app.route("/api/produits", methods=["GET"])
def get_produits():
    val = sb_get("produits")
    return jsonify(val or [])

@app.route("/api/produits", methods=["POST"])
def save_produits():
    data = request.json or {}
    if int(data.get("telegram_id", 0)) not in ADMIN_IDS:
        return jsonify({"error": "Non autorisé"}), 403
    sb_set("produits", data.get("produits", []))
    return jsonify({"ok": True})

@app.route("/api/livreurs", methods=["GET"])
def get_livreurs():
    liv = sb_get("livreurs")
    zone = sb_get("zone")
    return jsonify({
        "livreurs": liv or [],
        "zone": zone or "Nancy centre · Maxéville · Laxou · Vandœuvre · Essey-lès-Nancy"
    })

@app.route("/api/livreurs", methods=["POST"])
def save_livreurs():
    data = request.json or {}
    if int(data.get("telegram_id", 0)) not in ADMIN_IDS:
        return jsonify({"error": "Non autorisé"}), 403
    sb_set("livreurs", data.get("livreurs", []))
    sb_set("zone", data.get("zone", ""))
    return jsonify({"ok": True})

@app.route("/api/commande", methods=["POST"])
def nouvelle_commande():
    commande = request.json or {}
    # Sauvegarder dans Supabase
    existing = sb_get("commandes") or []
    existing.append(commande)
    sb_set("commandes", existing)
    # Notifier admin Telegram
    txt = (
        f"🛒 NOUVELLE COMMANDE !\n\n"
        f"📋 {commande.get('orderId')}\n"
        f"🛍 {commande.get('items')}\n"
        f"💰 {commande.get('total')} €\n"
        f"💳 {commande.get('payMethod')}\n"
        f"📍 {commande.get('livraison')}"
    )
    loop = asyncio.new_event_loop()
    for admin_id in ADMIN_IDS:
        try:
            loop.run_until_complete(bot.send_message(chat_id=admin_id, text=txt))
        except Exception as e:
            print(f"Erreur notif: {e}")
    loop.close()
    return jsonify({"ok": True})

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
