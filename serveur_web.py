#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json, os, asyncio, threading
import requests as req
from telegram import Bot

BOT_TOKEN = "8814685417:AAGlewLBJVhmq8FSl3XMC1oejUQx0U_PP3w"
ADMIN_IDS = {1090117356, 8371219330}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SB_URL = "https://veqzfrsuiibgrruzjrgc.supabase.co"
SB_KEY = os.environ.get("SUPABASE_KEY", "")

app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
CORS(app)
bot = Bot(token=BOT_TOKEN)

# Cache mémoire pour éviter les allers-retours Supabase
_cache = {}

def sb_get(key):
    if key in _cache:
        return _cache[key]
    try:
        r = req.get(
            f"{SB_URL}/rest/v1/pufferie_state?key=eq.{key}&select=value",
            headers={"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"},
            timeout=15
        )
        data = r.json()
        if data:
            _cache[key] = data[0]['value']
            return _cache[key]
    except Exception as e:
        print(f"sb_get error: {e}")
    return None

def sb_set(key, value):
    _cache[key] = value  # Mettre en cache immédiatement
    try:
        r = req.post(
            f"{SB_URL}/rest/v1/pufferie_state",
            headers={
                "apikey": SB_KEY,
                "Authorization": f"Bearer {SB_KEY}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal"
            },
            json={"key": key, "value": value},
            timeout=30
        )
        print(f"sb_set {key}: {r.status_code} len={len(str(value))}")
        if r.status_code >= 300:
            print(f"sb_set error: {r.text}")
        return r.status_code < 300
    except Exception as e:
        print(f"sb_set exception: {e}")
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
    return jsonify({"statut": sb_get("statut") or "dispo"})

@app.route("/api/statut", methods=["POST"])
def set_statut():
    data = request.json or {}
    sb_set("statut", data.get("statut", "dispo"))
    return jsonify({"ok": True})

@app.route("/api/produits", methods=["GET"])
def get_produits():
    return jsonify(sb_get("produits") or [])

@app.route("/api/produits", methods=["POST"])
def save_produits():
    data = request.json or {}
    prods = data.get("produits", [])
    ok = sb_set("produits", prods)
    print(f"Save produits: {len(prods)} produits, supabase_ok={ok}")
    if ok:
        return jsonify({"ok": True, "count": len(prods)})
    else:
        return jsonify({"ok": False, "error": "Supabase save failed"}), 500

@app.route("/api/livreurs", methods=["GET"])
def get_livreurs():
    return jsonify({
        "livreurs": sb_get("livreurs") or [],
        "zone": sb_get("zone") or "Nancy centre · Maxéville · Laxou · Vandœuvre · Essey-lès-Nancy"
    })

@app.route("/api/livreurs", methods=["POST"])
def save_livreurs():
    data = request.json or {}
    sb_set("livreurs", data.get("livreurs", []))
    sb_set("zone", data.get("zone", ""))
    return jsonify({"ok": True})

@app.route("/api/loyalty", methods=["GET"])
def get_loyalty():
    return jsonify(sb_get("loyalty") or [])

@app.route("/api/loyalty", methods=["POST"])
def save_loyalty():
    data = request.json or {}
    sb_set("loyalty", data.get("tiers", []))
    return jsonify({"ok": True})

@app.route("/api/loader_msgs", methods=["GET"])
def get_loader_msgs():
    val = sb_get("loader_msgs")
    return jsonify(val or [])

@app.route("/api/loader_msgs", methods=["POST"])
def save_loader_msgs():
    data = request.json or {}
    sb_set("loader_msgs", data.get("msgs", []))
    return jsonify({"ok": True})

@app.route("/api/whatsapp", methods=["GET"])
def get_whatsapp():
    return jsonify({"number": sb_get("whatsapp") or ""})

@app.route("/api/whatsapp", methods=["POST"])
def save_whatsapp():
    data = request.json or {}
    sb_set("whatsapp", data.get("number", ""))
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
        txt = (f"⭐ PRÉCOMMANDE !\n\n"
               f"👤 {commande.get('telegram_name','?')}\n"
               f"📦 {commande.get('brand')} — {commande.get('flavor')}\n"
               f"📏 {commande.get('format','?')} × {commande.get('qty','1')}\n"
               f"📝 {commande.get('msg','') or 'Aucun message'}")
        def send():
            loop = asyncio.new_event_loop()
            for uid in ADMIN_IDS:
                try: loop.run_until_complete(bot.send_message(chat_id=uid, text=txt))
                except: pass
            loop.close()
        threading.Thread(target=send, daemon=True).start()
    else:
        txt_admin = (f"🛒 NOUVELLE COMMANDE !\n\n📋 {order_id}\n"
                     f"🛍 {commande.get('items')}\n💰 {commande.get('total')} €\n"
                     f"💳 {commande.get('payMethod')}\n📍 {commande.get('livraison')}")
        txt_liv = txt_admin + "\n\n👇 Confirme ci-dessous"
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Confirmer", callback_data=f"confirm_{order_id}"),
            InlineKeyboardButton("⏰ Horaire", callback_data=f"horaire_{order_id}")
        ]])
        def send():
            loop = asyncio.new_event_loop()
            for uid in ADMIN_IDS:
                try:
                    loop.run_until_complete(bot.send_message(chat_id=uid, text=txt_admin))
                    loop.run_until_complete(bot.send_message(chat_id=uid, text=txt_liv, reply_markup=kb))
                except: pass
            loop.close()
        threading.Thread(target=send, daemon=True).start()

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
    import time
    def setup_webhook():
        time.sleep(3)
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
