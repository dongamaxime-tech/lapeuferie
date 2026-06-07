#!/usr/bin/env python3
import json, os, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "8968952235:AAFvHPoQ1rTXmDdJQvWt-BYhmvXu4RYXyCs"
ADMIN_IDS = {1090117356, 8371219330}
LIVREUR_IDS = {1090117356, 8371219330}  # Recoit les commandes avec boutons livreur
BOT_USERNAME = "Lapeuferie_nancy_bot"
APP_SHORTNAME = "Pufferie"
WEBAPP_URL = "https://lapeuferie.onrender.com"
STATE_FILE = "peuferie_state.json"

logging.basicConfig(level=logging.INFO)

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
            f"✅ Commande {order_id} confirmée !\n\nLe client sera notifié.\n\nTu peux modifier l'horaire si besoin.",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        # Notifier le client si possible (via le contexte)
        state = load_state()
        commandes = state.get("commandes", [])
        cmd = next((c for c in commandes if c.get("orderId") == order_id), None)
        if cmd and cmd.get("telegram_id"):
            try:
                await ctx.bot.send_message(
                    chat_id=cmd["telegram_id"],
                    text=f"✅ Bonne nouvelle ! Ta commande {order_id} est confirmée.\n🛵 Le livreur est en route !"
                )
            except Exception:
                pass
        return

    # ─── LIVREUR : choisir horaire ───
    if data.startswith("horaire_"):
        order_id = data.replace("horaire_", "")
        horaires = ["15 min", "30 min", "45 min", "1h", "1h30", "2h"]
        kb = [[InlineKeyboardButton("⏱ "+h, callback_data=f"settime_{order_id}_{h}")] for h in horaires]
        await query.edit_message_text(
            f"⏰ Commande {order_id}\n\nCombien de temps avant la livraison ?",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    # ─── LIVREUR : confirmer horaire ───
    if data.startswith("settime_"):
        parts = data.replace("settime_", "").split("_", 1)
        order_id = parts[0]
        heure = parts[1] if len(parts) > 1 else "?"
        await query.edit_message_text(
            f"✅ Horaire mis à jour : {order_id}\n⏱ Livraison dans {heure}"
        )
        # Notifier le client
        state = load_state()
        commandes = state.get("commandes", [])
        cmd = next((c for c in commandes if c.get("orderId") == order_id), None)
        if cmd and cmd.get("telegram_id"):
            try:
                await ctx.bot.send_message(
                    chat_id=cmd["telegram_id"],
                    text=f"⏱ Ta commande {order_id} sera livrée dans {heure} !\n🛵 Le livreur est en chemin."
                )
            except Exception:
                pass
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
