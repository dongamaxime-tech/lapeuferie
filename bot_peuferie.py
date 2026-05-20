#!/usr/bin/env python3
import json, os, logging
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

    # Envoyer l'ID en clair
    role = "👑 ADMINISTRATEUR" if is_admin else "👤 CLIENT"
    await update.message.reply_text(
        f"🔑 Ton ID : `{uid}`\n"
        f"Rôle : *{role}*\n\n"
        f"Clique sur le bouton ci-dessous pour ouvrir la boutique.",
        parse_mode="Markdown"
    )

    # Bouton WebApp avec URL simple sans paramètres
    kb = [[InlineKeyboardButton(
        "🛍️ Ouvrir Pufferie Nancy",
        web_app=WebAppInfo(url=WEBAPP_URL)
    )]]
    await update.message.reply_text(
        "💨 *Pufferie Nancy* — Boutique de référence à Nancy",
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
        "dispo":   "🟢 Disponible",
        "15min":   "🟡 ~15 min",
        "1h":      "🟡 ~1 heure",
        "pause":   "🟠 Pause",
        "indispo": "🔴 Indisponible",
    }

    if data == "admin_statut":
        current = state.get("statut", "dispo")
        kb = [[InlineKeyboardButton(
            ("✅ " if k == current else "") + v,
            callback_data=f"set_{k}"
        )] for k, v in STATUTS.items()]
        kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")])
        await query.edit_message_text(
            "Statut actuel : " + STATUTS.get(current, current),
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data.startswith("set_"):
        nouveau = data.replace("set_", "")
        state["statut"] = nouveau
        save_state(state)
        await query.edit_message_text(
            "✅ Statut : " + STATUTS.get(nouveau, nouveau),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Menu", callback_data="admin_menu")
            ]])
        )

    elif data == "admin_commandes":
        commandes = state.get("commandes", [])
        if not commandes:
            txt = "📦 Aucune commande."
        else:
            txt = "📦 *Dernières commandes :*\n\n"
            for c in commandes[-10:][::-1]:
                txt += f"*{c.get('orderId','?')}* — {c.get('total','?')} €\n🛒 {c.get('items','?')}\n💳 {c.get('payMethod','?')}\n📍 {c.get('livraison','?')}\n──────\n"
        await query.edit_message_text(txt, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menu", callback_data="admin_menu")]]))

    elif data == "admin_menu":
        kb = [
            [InlineKeyboardButton("📊 Statut boutique", callback_data="admin_statut")],
            [InlineKeyboardButton("📦 Commandes", callback_data="admin_commandes")],
        ]
        await query.edit_message_text("👑 *Panel Admin — Pufferie Nancy*",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("🚀 Bot Pufferie Nancy démarré...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
