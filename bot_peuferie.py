#!/usr/bin/env python3
import json, os, logging, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "8968952235:AAFvHPoQ1rTXmDdJQvWt-BYhmvXu4RYXyCs"
ADMIN_IDS = {1090117356}
WEBAPP_URL = "https://lapeuferie-production.up.railway.app"
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

    # 1. Envoyer l'ID à l'utilisateur
    await update.message.reply_text(
        f"👤 Ton ID Telegram : `{uid}`",
        parse_mode="Markdown"
    )

    # 2. Envoyer la boutique avec l'ID dans l'URL
    from urllib.parse import quote
    first = quote(user.first_name or 'Membre')
    uname = quote(user.username or '')
    webapp_url = f"{WEBAPP_URL}?tg_id={uid}&username={uname}&first_name={first}"

    if is_admin:
        kb = [[InlineKeyboardButton(
            "⚡ Ouvrir la boutique (Admin)",
            web_app=WebAppInfo(url=webapp_url)
        )]]
        await update.message.reply_text(
            f"👑 Bienvenue patron !\n\nTu es connecté en tant qu'*administrateur*.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )
    else:
        kb = [[InlineKeyboardButton(
            "🛍️ Ouvrir la boutique",
            web_app=WebAppInfo(url=webapp_url)
        )]]
        await update.message.reply_text(
            f"💨 *Pufferie Nancy*\n\nBienvenue {user.first_name} ! Clique ci-dessous pour accéder à la boutique.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    if uid not in ADMIN_IDS:
        await query.edit_message_text("❌ Accès refusé.")
        return

    state = load_state()
    data = query.data

    STATUTS = {
        "dispo":   "🟢 Disponible — Livraisons en cours",
        "15min":   "🟡 ~15 minutes d'attente",
        "1h":      "🟡 ~1 heure d'attente",
        "pause":   "🟠 Pause — On revient vite",
        "indispo": "🔴 Indisponible — Boutique fermée",
    }

    if data == "admin_statut":
        current = state.get("statut", "dispo")
        kb = []
        for k, v in STATUTS.items():
            mark = "✅ " if k == current else ""
            kb.append([InlineKeyboardButton(mark + v, callback_data=f"set_{k}")])
        kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")])
        await query.edit_message_text(
            "📊 Statut actuel : " + STATUTS[current] + "\n\nChoisis le nouveau statut :",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data.startswith("set_"):
        nouveau = data.replace("set_", "")
        state["statut"] = nouveau
        save_state(state)
        await query.edit_message_text(
            "✅ Statut mis à jour : " + STATUTS.get(nouveau, nouveau),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Menu admin", callback_data="admin_menu")
            ]])
        )

    elif data == "admin_commandes":
        commandes = state.get("commandes", [])
        if not commandes:
            txt = "📦 Aucune commande pour le moment."
        else:
            txt = "📦 *Dernières commandes :*\n\n"
            for c in commandes[-10:][::-1]:
                txt += (
                    f"*{c.get('orderId','?')}* — {c.get('total','?')} €\n"
                    f"🛒 {c.get('items','?')}\n"
                    f"💳 {c.get('payMethod','?')}\n"
                    f"📍 {c.get('livraison','?')}\n"
                    f"──────────────\n"
                )
        await query.edit_message_text(
            txt, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Menu admin", callback_data="admin_menu")
            ]])
        )

    elif data == "admin_menu":
        kb = [
            [InlineKeyboardButton("📊 Statut boutique", callback_data="admin_statut")],
            [InlineKeyboardButton("📦 Commandes", callback_data="admin_commandes")],
        ]
        await query.edit_message_text(
            "👑 *Panel Admin — Pufferie Nancy*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("🚀 Bot Pufferie Nancy démarré...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
