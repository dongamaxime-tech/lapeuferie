#!/usr/bin/env python3
"""
Serveur Web Flask — La Peuferie Nancy
Reçoit les commandes de la mini app et notifie le bot Telegram admin.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json, os, asyncio
from telegram import Bot

BOT_TOKEN = "8968952235:AAFvHPoQ1rTXmDdJQvWt-BYhmvXu4RYXyCs"
ADMIN_IDS = [1090117356]
STATE_FILE = "peuferie_state.json"

app = Flask(__name__, static_folder=".")
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

# ── Sert la mini app HTML ──────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(".", "la_peuferie_nancy.html")

# ── API : récupère le statut (appelé par la mini app au démarrage) ─────────────
@app.route("/api/statut", methods=["GET"])
def get_statut():
    state = load_state()
    return jsonify({"statut": state.get("statut", "dispo")})

# ── API : change le statut (appelé depuis la mini app admin) ──────────────────
@app.route("/api/statut", methods=["POST"])
def set_statut():
    data = request.json
    tg_id = data.get("telegram_id")
    if tg_id not in ADMIN_IDS:
        return jsonify({"error": "Non autorisé"}), 403
    state = load_state()
    state["statut"] = data.get("statut", "dispo")
    save_state(state)
    return jsonify({"ok": True})

# ── API : reçoit une commande depuis la mini app ───────────────────────────────
@app.route("/api/commande", methods=["POST"])
def nouvelle_commande():
    commande = request.json
    state = load_state()
    state.setdefault("commandes", []).append(commande)
    save_state(state)

    # Notif Telegram aux admins
    txt = (
        "🛒 *NOUVELLE COMMANDE !*\n\n"
        f"📋 Numéro : `{commande.get('orderId')}`\n"
        f"🛍️ Articles : {commande.get('items')}\n"
        f"💰 Total : *{commande.get('total')} €*\n"
        f"💳 Paiement : {commande.get('payMethod')}\n"
        f"📍 Livraison :\n`{commande.get('livraison')}`"
    )
    loop = asyncio.new_event_loop()
    for admin_id in ADMIN_IDS:
        loop.run_until_complete(
            bot.send_message(chat_id=admin_id, text=txt, parse_mode="Markdown")
        )
    loop.close()
    return jsonify({"ok": True})

# ── API : liste commandes (admin only) ────────────────────────────────────────
@app.route("/api/commandes", methods=["GET"])
def get_commandes():
    tg_id = int(request.args.get("telegram_id", 0))
    if tg_id not in ADMIN_IDS:
        return jsonify({"error": "Non autorisé"}), 403
    state = load_state()
    return jsonify(state.get("commandes", []))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
