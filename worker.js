// ═══════════════════════════════════════════════════════════
// Pufferie Nancy — Cloudflare Worker
// Remplace serveur_web.py — zéro cold start, 50ms partout
// ═══════════════════════════════════════════════════════════

const BOT_TOKEN = "8767598218:AAEERKo-T0w5deGvS_rZekHX8d9ri3ouAiM";
const ADMIN_IDS = [1090117356, 8371219330];
const SB_URL = "https://veqzfrsuiibgrruzjrgc.supabase.co";

// ── Supabase helpers ──────────────────────────────────────
async function sbGet(key, sbKey) {
  const r = await fetch(`${SB_URL}/rest/v1/pufferie_state?key=eq.${key}&select=value`, {
    headers: { apikey: sbKey, Authorization: `Bearer ${sbKey}` }
  });
  const data = await r.json();
  return data?.[0]?.value ?? null;
}

async function sbSet(key, value, sbKey) {
  const r = await fetch(`${SB_URL}/rest/v1/pufferie_state`, {
    method: "POST",
    headers: {
      apikey: sbKey,
      Authorization: `Bearer ${sbKey}`,
      "Content-Type": "application/json",
      Prefer: "resolution=merge-duplicates,return=minimal"
    },
    body: JSON.stringify({ key, value })
  });
  return r.status < 300;
}

// ── CORS headers ──────────────────────────────────────────
function cors(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type"
    }
  });
}

// ── Telegram notification ─────────────────────────────────
async function tgSend(chatId, text, replyMarkup = null) {
  const body = { chat_id: chatId, text };
  if (replyMarkup) body.reply_markup = replyMarkup;
  await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
}

// ── Main handler ──────────────────────────────────────────
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    const SB_KEY = env.SUPABASE_KEY;

    // OPTIONS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type"
        }
      });
    }

    // ── API routes ──────────────────────────────────────
    if (path === "/api/statut" && request.method === "GET") {
      const val = await sbGet("statut", SB_KEY);
      return cors({ statut: val || "dispo" });
    }

    if (path === "/api/statut" && request.method === "POST") {
      const data = await request.json();
      await sbSet("statut", data.statut || "dispo", SB_KEY);
      return cors({ ok: true });
    }

    if (path === "/api/produits" && request.method === "GET") {
      const val = await sbGet("produits", SB_KEY);
      return cors(val || []);
    }

    if (path === "/api/produits" && request.method === "POST") {
      const data = await request.json();
      const ok = await sbSet("produits", data.produits || [], SB_KEY);
      console.log(`Save produits: ${data.produits?.length} produits, ok=${ok}`);
      if (ok) return cors({ ok: true, count: data.produits?.length });
      return cors({ ok: false, error: "Supabase save failed" }, 500);
    }

    if (path === "/api/livreurs" && request.method === "GET") {
      const [livreurs, zone] = await Promise.all([
        sbGet("livreurs", SB_KEY),
        sbGet("zone", SB_KEY)
      ]);
      return cors({
        livreurs: livreurs || [],
        zone: zone || "Nancy centre · Maxéville · Laxou · Vandœuvre · Essey-lès-Nancy"
      });
    }

    if (path === "/api/livreurs" && request.method === "POST") {
      const data = await request.json();
      await Promise.all([
        sbSet("livreurs", data.livreurs || [], SB_KEY),
        sbSet("zone", data.zone || "", SB_KEY)
      ]);
      return cors({ ok: true });
    }

    if (path === "/api/loyalty" && request.method === "GET") {
      const val = await sbGet("loyalty", SB_KEY);
      return cors(val || []);
    }

    if (path === "/api/loyalty" && request.method === "POST") {
      const data = await request.json();
      await sbSet("loyalty", data.tiers || [], SB_KEY);
      return cors({ ok: true });
    }

    if (path === "/api/whatsapp" && request.method === "GET") {
      const val = await sbGet("whatsapp", SB_KEY);
      return cors({ number: val || "" });
    }

    if (path === "/api/whatsapp" && request.method === "POST") {
      const data = await request.json();
      await sbSet("whatsapp", data.number || "", SB_KEY);
      return cors({ ok: true });
    }

    if (path === "/api/loader_msgs" && request.method === "GET") {
      const val = await sbGet("loader_msgs", SB_KEY);
      return cors(val || []);
    }

    if (path === "/api/loader_msgs" && request.method === "POST") {
      const data = await request.json();
      await sbSet("loader_msgs", data.msgs || [], SB_KEY);
      return cors({ ok: true });
    }

    if (path === "/api/whoami" && request.method === "POST") {
      const data = await request.json();
      const uid = Number(data.uid || 0);
      return cors({ uid, is_admin: ADMIN_IDS.includes(uid) });
    }

    if (path === "/api/commande" && request.method === "POST") {
      const commande = await request.json();
      const orderId = commande.orderId || "?";

      // Sauvegarder dans Supabase
      const existing = (await sbGet("commandes", SB_KEY)) || [];
      existing.push(commande);
      await sbSet("commandes", existing, SB_KEY);

      // Notifier les admins
      const isPreorder = commande.type === "preorder";
      const txtAdmin = isPreorder
        ? `⭐ PRÉCOMMANDE !\n\n👤 ${commande.telegram_name || "?"}\n📦 ${commande.brand} — ${commande.flavor}\n📏 Format : ${commande.format} × ${commande.qty}\n📝 ${commande.msg || "Aucun message"}`
        : `🛒 NOUVELLE COMMANDE !\n\n📋 ${orderId}\n🛍 ${commande.items}\n💰 ${commande.total} €\n💳 ${commande.payMethod}\n📍 ${commande.livraison}`;

      const txtLivreur = isPreorder ? txtAdmin : `🚨 COMMANDE À LIVRER\n\n📋 ${orderId}\n🛍 ${commande.items}\n💰 ${commande.total} €\n💳 ${commande.payMethod}\n📍 ${commande.livraison}\n\n👇 Confirme ci-dessous`;

      const kb = isPreorder ? null : {
        inline_keyboard: [[
          { text: "✅ Confirmer", callback_data: `confirm_${orderId}` },
          { text: "⏰ Horaire", callback_data: `horaire_${orderId}` }
        ]]
      };

      await Promise.all(ADMIN_IDS.map(id => tgSend(id, txtAdmin)));
      if (!isPreorder) await Promise.all(ADMIN_IDS.map(id => tgSend(id, txtLivreur, kb)));

      return cors({ ok: true });
    }

    // ── Webhook Telegram ──────────────────────────────────
    if (path === `/webhook/${BOT_TOKEN}` && request.method === "POST") {
      const update = await request.json();

      if (update.message?.text === "/start") {
        const user = update.message.from;
        const uid = user.id;
        const isAdmin = ADMIN_IDS.includes(uid);
        const nom = `${user.first_name || ""} ${user.last_name || ""}`.trim();
        const role = isAdmin ? "👑 Administrateur" : "👤 Client";
        const webapp = "https://pufferie-nancy.pages.dev";

        const texte = `💨 Mon Profil\n\n👤 Nom : ${nom}\n🆔 ID : ${uid}\nRole : ${role}`;
        const kb = {
          inline_keyboard: isAdmin ? [
            [{ text: "📊 Statut boutique", callback_data: "admin_statut" }],
            [{ text: "📦 Commandes reçues", callback_data: "admin_commandes" }],
            [{ text: "🛍️ Ouvrir la boutique", web_app: { url: webapp } }]
          ] : [[{ text: "🛍️ Ouvrir la boutique", web_app: { url: webapp } }]]
        };
        await tgSend(uid, texte, kb);
      }

      if (update.callback_query) {
        const query = update.callback_query;
        const uid = query.from.id;
        const data = query.data;
        const SB_KEY = env.SUPABASE_KEY;

        // Répondre au callback
        await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/answerCallbackQuery`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ callback_query_id: query.id })
        });

        if (data.startsWith("confirm_")) {
          const orderId = data.replace("confirm_", "");
          await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/editMessageText`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              chat_id: query.message.chat.id,
              message_id: query.message.message_id,
              text: `✅ Commande ${orderId} confirmée !`,
              reply_markup: { inline_keyboard: [[{ text: "⏰ Modifier horaire", callback_data: `horaire_${orderId}` }]] }
            })
          });
          // Notifier le client
          const commandes = (await sbGet("commandes", SB_KEY)) || [];
          const cmd = commandes.find(c => c.orderId === orderId);
          if (cmd?.telegram_id) await tgSend(cmd.telegram_id, `✅ Ta commande ${orderId} est confirmée !\n🛵 Le livreur est en route !`);
        }

        if (data.startsWith("horaire_")) {
          const orderId = data.replace("horaire_", "");
          const isPreorder = orderId.startsWith("#PRE-");
          const horaires = isPreorder ? ["4 jours", "7 jours", "10 jours", "Impossible"] : ["15 min", "30 min", "45 min", "1h", "1h30", "2h"];
          await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/editMessageText`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              chat_id: query.message.chat.id,
              message_id: query.message.message_id,
              text: isPreorder ? `📦 Délai pour ${orderId} ?` : `⏰ Délai pour ${orderId} ?`,
              reply_markup: { inline_keyboard: horaires.map(h => [{ text: h, callback_data: `settime_${orderId}_${h}` }]) }
            })
          });
        }

        if (data.startsWith("settime_")) {
          const parts = data.replace("settime_", "").split("_");
          const heure = parts.pop();
          const orderId = parts.join("_");
          await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/editMessageText`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              chat_id: query.message.chat.id,
              message_id: query.message.message_id,
              text: `✅ Délai confirmé : ${heure}\n📋 Commande ${orderId}`
            })
          });
          const commandes = (await sbGet("commandes", SB_KEY)) || [];
          const cmd = commandes.find(c => c.orderId === orderId);
          if (cmd?.telegram_id) await tgSend(cmd.telegram_id, `🛵 Livraison dans ${heure} !\n📋 Commande ${orderId}`);
        }

        if (data === "admin_statut") {
          const current = (await sbGet("statut", SB_KEY)) || "dispo";
          const statuts = { dispo: "🟢 Disponible", "15min": "🟡 ~15 min", "1h": "🟡 ~1h", pause: "🟠 Pause", indispo: "🔴 Indisponible" };
          await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/editMessageText`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              chat_id: query.message.chat.id,
              message_id: query.message.message_id,
              text: `Statut actuel : ${statuts[current]}\n\nChoisis :`,
              reply_markup: { inline_keyboard: Object.entries(statuts).map(([k, v]) => [{ text: (k === current ? "✅ " : "") + v, callback_data: `set_${k}` }]) }
            })
          });
        }

        if (data.startsWith("set_")) {
          const nouveau = data.replace("set_", "");
          await sbSet("statut", nouveau, SB_KEY);
          await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/editMessageText`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              chat_id: query.message.chat.id,
              message_id: query.message.message_id,
              text: `✅ Statut mis à jour !`
            })
          });
        }
      }

      return new Response("ok");
    }

    return new Response("Not found", { status: 404 });
  }
};
