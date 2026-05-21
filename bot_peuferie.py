#!/usr/bin/env python3
import json, os, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "8968952235:AAFvHPoQ1rTXmDdJQvWt-BYhmvXu4RYXyCs"
ADMIN_IDS = {1090117356, 8371219330}
BOT_USERNAME = "Lapeuferie_nancy_bot"
APP_SHORTNAME = "Pufferie"
STATE_FILE = "peuferie_state.json"
PORT = int(os.environ.get("PORT", 8080))
WEBHOOK_URL = os.environ.get("RAILWAY_STATIC_URL", "https://lapeuferie.onrender.com")

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
    webapp_link = f"https://t.me/{BOT_USERNAME}/{APP_SHORTNAME}?startapp={uid}"

    nom = f"{user.first_name} {user.last_name or ''}".strip()
    texte = (
        f"💨 Mon Profil\n\n"
        f"👤 Nom : {nom}\n"
        f"🆔 ID : {uid}\n"
        f"🎭 Role : {role}\n"
    )

    if is_admin:
        kb = [
            [InlineKeyboardButton("📊 Statut boutique", callback_data="admin_statut")],
            [InlineKeyboardButton("📦 Commandes reçues", callback_data="admin_commandes")],
            [InlineKeyboardButton("🛍️ Ouvrir la boutique", web_app=WebAppInfo(url="https://lapeuferie.onrender.com"))],
        ]
    else:
        kb = [[InlineKeyboardButton("🛍️ Ouvrir la boutique", web_app=WebAppInfo(url="https://lapeuferie.onrender.com"))]]

    await update.message.reply_text(texte,
        reply_markup=InlineKeyboardMarkup(kb))

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
        kb = [[InlineKeyboardButton(("✅ " if k==current else "")+v, callback_data=f"set_{k}")] for k,v in STATUTS.items()]
        kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="menu")])
        await query.edit_message_text("📊 Statut : *"+STATUTS.get(current,current)+"*\n\nChoisis :",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("set_"):
        nouveau = data[4:]
        state["statut"] = nouveau
        save_state(state)
        await query.edit_message_text("✅ Statut : *"+STATUTS.get(nouveau,nouveau)+"*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="menu")]]))

    elif data == "admin_commandes":
        commandes = state.get("commandes", [])
        txt = "📦 Aucune commande." if not commandes else "📦 *Commandes :*\n\n"+"".join(
            f"*{c.get('orderId','?')}* — {c.get('total','?')} €\n🛒 {c.get('items','?')}\n💳 {c.get('payMethod','?')}\n📍 {c.get('livraison','?')}\n──\n"
            for c in commandes[-10:][::-1])
        await query.edit_message_text(txt, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="menu")]]))

    elif data == "menu":
        uid2 = query.from_user.id
        link = f"https://t.me/{BOT_USERNAME}/{APP_SHORTNAME}?startapp={uid2}"
        kb = [
            [InlineKeyboardButton("📊 Statut boutique", callback_data="admin_statut")],
            [InlineKeyboardButton("📦 Commandes reçues", callback_data="admin_commandes")],
            [InlineKeyboardButton("🛍️ Ouvrir la boutique", web_app=WebAppInfo(url="https://lapeuferie.onrender.com"))],
        ]
        await query.edit_message_text(f"👑 *Admin — Pufferie Nancy*\n🆔 `{uid2}`",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

def get_app():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    return app
