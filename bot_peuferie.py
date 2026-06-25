#!/usr/bin/env python3
import json, os, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "8814685417:AAGlewLBJVhmq8FSl3XMC1oejUQx0U_PP3w"
ADMIN_IDS = {1090117356, 8371219330}
LIVREUR_IDS = {1090117356, 8371219330}  # Recoit les commandes avec boutons livreur
BOT_USERNAME = "Lapeuferie_nancy_bot"
APP_SHORTNAME = "Pufferie"
WEBAPP_URL = "https://lapeuferie.onrender.com"
STATE_FILE = "peuferie_state.json"

logging.basicConfig(level=logging.INFO)

import requests as req_lib

SB_URL = "https://veqzfrsuiibgrruzjrgc.supabase.co"
SB_KEY = os.environ.get("SUPABASE_KEY", "")

async def get_client_id(order_id):
    """Chercher l'ID Telegram du client depuis Supabase"""
    try:
        r = req_lib.get(
            f"{SB_URL}/rest/v1/pufferie_state?key=eq.commandes&select=value",
            headers={"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"},
            timeout=5
        )
        data = r.json()
        if data and data[0].get('value'):
            commandes = data[0]['value']
            cmd = next((c for c in commandes if c.get("orderId") == order_id), None)
            if cmd:
                return cmd.get("telegram_id")
    except Exception as e:
        print(f"get_client_id error: {e}")
    return None

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"statut": "dispo", "commandes": []}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    is_admin = uid in ADMIN_IDS
    role = "👑 Administrateur" if is_admin else "👤 Client"
    nom = f"{user.first_name} {user.last_name or ''}".strip()

    texte = (
        f"💨 Mon Profil\n\n"
        f"👤 Nom : {nom}\n"
        f"🆔 ID : {uid}\n"
        f"Role : {role}\n"
    )

    webapp_link = f"https://t.me/{BOT_USERNAME}/{APP_SHORTNAME}"

    if is_admin:
        kb = [
            [InlineKeyboardButton("📊 Statut boutique", callback_data="admin_statut")],
            [InlineKeyboardButton("📦 Commandes reçues", callback_data="admin_commandes")],
            [InlineKeyboardButton("🛍️ Ouvrir la boutique", web_app=WebAppInfo(url=WEBAPP_URL))],
        ]
    else:
        kb = [[InlineKeyboardButton("🛍️ Ouvrir la boutique", web_app=WebAppInfo(url=WEBAPP_URL))]]

    await update.message.reply_text(texte, reply_markup=InlineKeyboardMarkup(kb))

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    # ─── LIVREUR : confirmer commande ───
    if data.startswith("confirm_"):
        order_id = data.replace("confirm_", "")
        kb = [[InlineKeyboardButton("⏰ Modifier l'horaire", callback_data=f"horaire_{order_id}")]]
        await query.edit_message_text(
            f"✅ Commande {order_id} confirmée !\n\nTu peux encore modifier l'horaire si besoin.",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        # Chercher le client dans Supabase
        client_id = await get_client_id(order_id)
        if client_id:
            try:
                await ctx.bot.send_message(
                    chat_id=client_id,
                    text=f"✅ Ta commande {order_id} est confirmée !\n🛵 Le livreur est en route, tu seras livré très vite !"
                )
            except Exception as e:
                print(f"Erreur notif client: {e}")
        return

    # ─── LIVREUR : choisir horaire ───
    if data.startswith("horaire_"):
        order_id = data.replace("horaire_", "")
        # Vérifier si c'est une précommande ou une livraison
        client_id = await get_client_id(order_id)
        is_preorder = order_id.startswith('#PRE-') if order_id else False

        if is_preorder:
            horaires = ["4 jours", "7 jours", "10 jours", "Impossible"]
            titre = f"📦 Précommande {order_id}\n\nDélai de disponibilité estimé ?"
        else:
            horaires = ["15 min", "30 min", "45 min", "1h", "1h30", "2h"]
            titre = f"⏰ Commande {order_id}\n\nCombien de temps avant la livraison ?"

        kb = [[InlineKeyboardButton("⏱ "+h, callback_data=f"settime_{order_id}_{h}")] for h in horaires]
        await query.edit_message_text(titre, reply_markup=InlineKeyboardMarkup(kb))
        return

    # ─── LIVREUR : confirmer horaire ───
    if data.startswith("settime_"):
        parts = data.replace("settime_", "").split("_", 1)
        order_id = parts[0]
        heure = parts[1] if len(parts) > 1 else "?"
        await query.edit_message_text(
            f"✅ Horaire confirmé : livraison dans {heure}\n📋 Commande {order_id}"
        )
        # Notifier le client via Supabase
        client_id = await get_client_id(order_id)
        if client_id:
            try:
                await ctx.bot.send_message(
                    chat_id=client_id,
                    text=f"🛵 Ton livreur arrive dans {heure} !\n📋 Commande {order_id}\n\nPrépare-toi 😎"
                )
            except Exception as e:
                print(f"Erreur notif client: {e}")
        return

    # ─── ADMIN ───
    if uid not in ADMIN_IDS:
        await query.edit_message_text("❌ Accès refusé.")
        return

    state = load_state()
    STATUTS = {
        "dispo":   "🟢 Disponible",
        "15min":   "🟡 ~15 min",
        "1h":      "🟡 ~1 heure",
        "pause":   "🟠 Pause",
        "indispo": "🔴 Indisponible",
    }

    if data == "admin_statut":
        current = state.get("statut", "dispo")
        kb = [[InlineKeyboardButton(("✅ " if k==current else "")+v, callback_data=f"set_{k}")] for k,v in STATUTS.items()]
        kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="menu")])
        await query.edit_message_text(
            "Statut actuel : "+STATUTS.get(current, current)+"\n\nChoisis :",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data.startswith("set_"):
        nouveau = data[4:]
        state["statut"] = nouveau
        save_state(state)
        await query.edit_message_text(
            "✅ Statut : "+STATUTS.get(nouveau, nouveau),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="menu")]])
        )

    elif data == "admin_commandes":
        commandes = state.get("commandes", [])
        txt = "📦 Aucune commande." if not commandes else "📦 Commandes :\n\n"+"".join(
            f"{c.get('orderId','?')} — {c.get('total','?')} €\n{c.get('items','?')}\n{c.get('payMethod','?')}\n{c.get('livraison','?')}\n──\n"
            for c in commandes[-10:][::-1])
        await query.edit_message_text(txt,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="menu")]]))

    elif data == "menu":
        kb = [
            [InlineKeyboardButton("📊 Statut boutique", callback_data="admin_statut")],
            [InlineKeyboardButton("📦 Commandes reçues", callback_data="admin_commandes")],
            [InlineKeyboardButton("🛍️ Ouvrir la boutique", web_app=WebAppInfo(url=WEBAPP_URL))],
        ]
        await query.edit_message_text(
            f"👑 Admin — Pufferie Nancy",
            reply_markup=InlineKeyboardMarkup(kb)
        )

def get_app():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    return app

if __name__ == "__main__":
    import asyncio
    async def main():
        app = get_app()
        await app.bot.delete_webhook(drop_pending_updates=True)
        await app.run_polling(allowed_updates=Update.ALL_TYPES)
    asyncio.run(main())
