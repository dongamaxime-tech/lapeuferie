#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json, os, asyncio, requests as req
from telegram import Bot

BOT_TOKEN = "8968952235:AAFvHPoQ1rTXmDdJQvWt-BYhmvXu4RYXyCs"
ADMIN_IDS = {1090117356, 8371219330}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SB_URL = "https://veqzfrsuiibgrruzjrgc.supabase.co"
SB_KEY = os.environ.get("SUPABASE_KEY", "")

app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
CORS(app)
bot = Bot(token=BOT_TOKEN)

def sb_get(key):
    try:
        r = req.get(
            f"{SB_URL}/rest/v1/pufferie_state?key=eq.{key}&select=value",
            headers={"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"},
            timeout=5
        )
        data = r.json()
        if data: return data[0]['value']
    except Exception as e:
        print(f"sb_get error: {e}")
    return None

def sb_set(key, value):
    try:
        r = req.patch(
            f"{SB_URL}/rest/v1/pufferie_state?key=eq.{key}",
            headers={
                "apikey": SB_KEY,
                "Authorization": f"Bearer {SB_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            },
            json={"value": value},
            timeout=5
        )
        print(f"sb_set {key}: {r.status_code}")
        return r.status_code < 300
    except Exception as e:
        print(f"sb_set error: {e}")
        return False

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
    sb_set("statut", data.get("statut", "dispo"))
    return jsonify({"ok": True})

@app.route("/api/produits", methods=["GET"])
def get_produits():
    val = sb_get("produits")
    return jsonify(val or [])

@app.route("/api/produits", methods=["POST"])
def save_produits():
    data = request.json or {}
    prods = data.get("produits", [])
    ok = sb_set("produits", prods)
    print(f"Save produits: {len(prods)} produits ok={ok}")
    return jsonify({"ok": ok})

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
    sb_set("livreurs", data.get("livreurs", []))
    sb_set("zone", data.get("zone", ""))
    return jsonify({"ok": True})

@app.route("/api/whatsapp", methods=["GET"])
def get_whatsapp():
    val = sb_get("whatsapp")
    return jsonify({"number": val or ""})

@app.route("/api/whatsapp", methods=["POST"])
def save_whatsapp():
    data = request.json or {}
    sb_set("whatsapp", data.get("number", ""))
    return jsonify({"ok": True})

@app.route("/api/loyalty", methods=["GET"])
def get_loyalty():
    val = sb_get("loyalty")
    return jsonify(val or [])

@app.route("/api/loyalty", methods=["POST"])
def save_loyalty():
    data = request.json or {}
    sb_set("loyalty", data.get("tiers", []))
    return jsonify({"ok": True})

@app.route("/api/commande", methods=["POST"])
def nouvelle_commande():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    commande = request.json or {}
    order_id = commande.get("orderId", "?")
    existing = sb_get("commandes") or []
    existing.append(commande)
    sb_set("commandes", existing)

    if commande.get('type') == 'preorder':
        txt_admin = (
            f"⭐ PRÉCOMMANDE !\n\n"
            f"👤 {commande.get('telegram_name','?')} ({commande.get('telegram_id','?')})\n"
            f"📦 {commande.get('brand')} — {commande.get('flavor')}\n"
            f"📏 Format : {commande.get('format','?')} × {commande.get('qty','1')}\n"
            f"📝 {commande.get('msg','') or 'Aucun message'}"
        )
        txt_livreur = txt_admin
    else:
        txt_admin = f"🛒 NOUVELLE COMMANDE !\n\n📋 {order_id}\n🛍 {commande.get('items')}\n💰 {commande.get('total')} €\n💳 {commande.get('payMethod')}\n📍 {commande.get('livraison')}"
        txt_livreur = f"🚨 COMMANDE À LIVRER\n\n📋 {order_id}\n🛍 {commande.get('items')}\n💰 {commande.get('total')} €\n💳 {commande.get('payMethod')}\n📍 {commande.get('livraison')}\n\n👇 Confirme ci-dessous"
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Confirmer", callback_data=f"confirm_{order_id}"),
        InlineKeyboardButton("⏰ Horaire", callback_data=f"horaire_{order_id}")
    ]])

    loop = asyncio.new_event_loop()
    for admin_id in ADMIN_IDS:
        try:
            loop.run_until_complete(bot.send_message(chat_id=admin_id, text=txt_admin))
            loop.run_until_complete(bot.send_message(chat_id=admin_id, text=txt_livreur, reply_markup=kb))
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
    def setup_webhook():
        time.sleep(5)
        loop = asyncio.new_event_loop()
        url = f"https://lapeuferie.onrender.com/webhook/{BOT_TOKEN}"
        try:
            loop.run_until_complete(bot.delete_webhook())
            loop.run_until_complete(bot.set_webhook(url=url))
            print(f"Webhook OK: {url}")
        except Exception as e:
            print(f"Webhook error: {e}")
        loop.close()
    threading.Thread(target=setup_webhook, daemon=True).start()
    app.run(host="0.0.0.0", port=port, debug=False)
