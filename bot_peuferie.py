#!/usr/bin/env python3
"""
Bot Telegram - La Peuferie Nancy
@Lapeuferie_nancy_bot
Token: 8968952235:AAFvHPoQ1rTXmDdJQvWt-BYhmvXu4RYXyCs
Admin ID: 1090117356
"""

import json
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BOT_TOKEN  = "8968952235:AAFvHPoQ1rTXmDdJQvWt-BYhmvXu4RYXyCs"
ADMIN_IDS  = {1090117356}   # Ajoute d'autres IDs ici si besoin
WEBAPP_URL = "https://TON_HEBERGEUR.com"  # URL de ta mini app

# Fichier de state partagé avec la mini app (via un simple JSON)
STATE_FILE = "peuferie_state.json"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ─── STATE ────────────────────────────────────────────────────────────────────
STATUTS = {
    "dispo":  "🟢 Disponible — Livraisons en cours",
    "15min":  "🟡 ~15 minutes d'attente",
    "1h":     "🟡 ~1 heure d'attente",
    "pause":  "🟠 Pause — On revient vite",
    "indispo":"🔴 Indisponible — Boutique fermée",
}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"statut": "dispo", "commandes": []}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ─── COMMANDES ────────────────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_admin(uid):
        kb = [
            [InlineKeyboardButton("🛍️ Ouvrir la boutique", web_app={"url": WEBAPP_URL})],
            [InlineKeyboardButton("📊 Statut boutique",    callback_data="admin_statut")],
            [InlineKeyboardButton("📦 Commandes récentes", callback_data="admin_commandes")],
            [InlineKeyboardButton("➕ Ajouter produit",    callback_data="admin_produit")],
        ]
        await update.message.reply_text(
            "👑 *Panel Admin — La Peuferie Nancy*\n\n"
            "Connecté en tant qu'administrateur.\n"
            "Ton ID : `" + str(uid) + "`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )
    else:
        kb = [[InlineKeyboardButton("🛍️ Ouvrir la boutique", web_app={"url": WEBAPP_URL})]]
        await update.message.reply_text(
            "💨 *La Peuferie Nancy*\n\n"
            "Boutique de référence de peuf à Nancy.\n"
            "Clique ci-dessous pour parcourir le catalogue !",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )

async def admin_only(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Vérifie que l'utilisateur est admin"""
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("❌ Accès réservé aux administrateurs.")
        return False
    return True

# ─── CALLBACKS ADMIN ──────────────────────────────────────────────────────────
async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if not is_admin(uid):
        await query.edit_message_text("❌ Accès refusé.")
        return

    data = query.data
    state = load_state()

    # ── Statut ──
    if data == "admin_statut":
        current = state.get("statut", "dispo")
        kb = []
        for k, v in STATUTS.items():
            mark = "✅ " if k == current else ""
            kb.append([InlineKeyboardButton(mark + v, callback_data=f"set_statut_{k}")])
        kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")])
        await query.edit_message_text(
            "📊 *Statut actuel :* " + STATUTS[current] + "\n\nChoisis le nouveau statut :",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data.startswith("set_statut_"):
        nouveau = data.replace("set_statut_", "")
        state["statut"] = nouveau
        save_state(state)
        await query.edit_message_text(
            "✅ Statut mis à jour !\n\n" +
            "*Nouveau statut :* " + STATUTS[nouveau] + "\n\n"
            "Visible immédiatement par tous les clients sur la boutique.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Menu admin", callback_data="admin_menu")]
            ])
        )

    # ── Commandes ──
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
                    f"─────────────────\n"
                )
        await query.edit_message_text(
            txt, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Menu admin", callback_data="admin_menu")]
            ])
        )

    # ── Retour menu ──
    elif data == "admin_menu":
        kb = [
            [InlineKeyboardButton("📊 Statut boutique",    callback_data="admin_statut")],
            [InlineKeyboardButton("📦 Commandes récentes", callback_data="admin_commandes")],
        ]
        await query.edit_message_text(
            "👑 *Panel Admin — La Peuferie Nancy*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )

# ─── RÉCEPTION COMMANDE (webhook depuis la mini app) ─────────────────────────
async def nouvelle_commande(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    La mini app envoie les infos de commande via message au bot.
    En prod : utiliser un webhook HTTP POST.
    """
    pass

# ─── NOTIFY ADMIN (appelé depuis serveur web quand commande reçue) ────────────
async def notify_admin_commande(app, commande: dict):
    """Envoie une notif à l'admin quand une commande arrive."""
    txt = (
        "🛒 *NOUVELLE COMMANDE !*\n\n"
        f"📋 Numéro : `{commande.get('orderId')}`\n"
        f"🛍️ Articles : {commande.get('items')}\n"
        f"💰 Total : *{commande.get('total')} €*\n"
        f"💳 Paiement : {commande.get('payMethod')}\n"
        f"📍 Livraison :\n`{commande.get('livraison')}`"
    )
    for admin_id in ADMIN_IDS:
        await app.bot.send_message(chat_id=admin_id, text=txt, parse_mode="Markdown")
    # Sauvegarde dans state
    state = load_state()
    state.setdefault("commandes", []).append(commande)
    save_state(state)

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("🚀 Bot La Peuferie Nancy démarré...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
