import telebot, random, os, threading, time
from datetime import datetime, timedelta
from flask import Flask, request
from pymongo import MongoClient

app = Flask(__name__)

# --- CONFIGURATION ---
API_TOKEN = os.getenv('API_TOKEN')
ADMIN_ID = 5724620019  
MONGO_URI = os.getenv('MONGO_URI')
bot = telebot.TeleBot(API_TOKEN)

client = MongoClient(MONGO_URI)
db = client['luckyjet_db']
users_col = db['users'] 

LIEN_INSCRIPTION = "https://lkbb.cc/e2d8"
ID_VIDEO_UNIQUE = "https://t.me/gagnantpro1xbet/138958" 

# --- LOGIQUE DE PAIRES AVEC ÉCART DE 2 MIN ---
def get_next_signal():
    now = datetime.now()
    
    # Liste mise à jour : On commence à 03, et chaque S2 est à +2 minutes
    pailles_minutes = [
        (3, 5),   # Signal 1 : 03 | Signal 2 : 05
        (8, 10),  # Signal 1 : 08 | Signal 2 : 10
        (13, 15), # Signal 1 : 13 | Signal 2 : 15
        (18, 20), # Signal 1 : 18 | Signal 2 : 20
        (23, 25), 
        (28, 30), 
        (33, 35),
        (38, 40),
        (43, 45),
        (48, 50),
        (53, 55),
        (58, 00)  # Le dernier signal boucle sur l'heure suivante
    ]
    
    current_min = now.minute
    target_pair = None
    target_hour = now.hour

    for s1, s2 in pailles_minutes:
        if s1 > current_min:
            target_pair = (s1, s2)
            break
    
    if target_pair is None:
        target_pair = pailles_minutes[0]
        target_hour = (now.hour + 1) % 24

    s1_f, s2_f = target_pair
    time_s1 = now.replace(hour=target_hour, minute=s1_f, second=0, microsecond=0)
    
    # Gestion du passage à l'heure suivante pour le Signal 2 si S2 = 00
    h2 = target_hour
    if s2_f < s1_f: 
        h2 = (target_hour + 1) % 24
    time_s2 = now.replace(hour=h2, minute=s2_f, second=0, microsecond=0)

    # GÉNÉRATION DES CÔTES (SÉCURITÉ 1.50)
    random.seed(time_s1.timestamp())
    cote = round(random.uniform(10.0, 85.0), 2)
    prev = 1.50
    random.seed() 
    
    return time_s1, time_s2, cote, prev

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def start(msg):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🚀 SIGNAL", "📊 STATISTIQUES")
    bot.send_message(msg.chat.id, "🛰 **Système Lucky Jet Connecté**", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🚀 SIGNAL")
def signal_handler(msg):
    u = users_col.find_one({"_id": msg.from_user.id})
    if msg.from_user.id == ADMIN_ID or (u and u.get('is_vip')):
        t_s1, t_s2, cote, prev = get_next_signal()
        caption = (f"🚀 **PRÉDICTION LUCKY JET**\n"
                   f"━━━━━━━━━━━━━━━━━━\n"
                   f"📍 **SIGNAL 1** : `{t_s1.strftime('%H:%M')}`\n"
                   f"📍 **SIGNAL 2** : `{t_s2.strftime('%H:%M')}`\n"
                   f"━━━━━━━━━━━━━━━━━━\n"
                   f"📈 **OBJECTIF** : `{cote}X` \n"
                   f"🎯 **SÉCURITÉ** : `{prev}X` \n"
                   f"━━━━━━━━━━━━━━━━━━")
        btn = telebot.types.InlineKeyboardMarkup().add(
            telebot.types.InlineKeyboardButton("💻 JOUER MAINTENANT", url=LIEN_INSCRIPTION)
        )
        try:
            bot.send_video(msg.chat.id, ID_VIDEO_UNIQUE, caption=caption, reply_markup=btn, parse_mode='Markdown')
        except:
            bot.send_message(msg.chat.id, caption, reply_markup=btn, parse_mode='Markdown')
    else:
        bot.send_message(msg.chat.id, "⚠️ **ACCÈS VIP REQUIS**\n\nEnvoyez votre ID joueur pour activation.")

@bot.message_handler(func=lambda m: m.text.isdigit() and len(m.text) >= 7)
def handle_id(msg):
    users_col.update_one({"_id": msg.from_user.id}, {"$set": {"player_id": msg.text}}, upsert=True)
    bot.send_message(msg.chat.id, "⏳ **ID enregistré !**\nL'admin va valider votre accès.")
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("✅ ACTIVER VIP", callback_data=f"val_{msg.from_user.id}"))
    bot.send_message(ADMIN_ID, f"🆕 **NOUVEL ID**\n🆔 ID: `{msg.text}`", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda c: c.data.startswith("val_"))
def valider_callback(c):
    uid = int(c.data.split("_")[1])
    users_col.update_one({"_id": uid}, {"$set": {"is_vip": True}})
    bot.answer_callback_query(c.id, "VIP Activé !")
    bot.edit_message_text(f"✅ VIP activé pour {uid}", c.message.chat.id, c.message.message_id)
    try:
        bot.send_message(uid, "🌟 **Accès VIP activé !** Cliquez sur 🚀 **SIGNAL**.")
    except:
        pass

# --- WEBHOOK & LANCEMENT ---
@app.route('/webhook1win', methods=['POST'])
def handle_webhook():
    data = request.json
    p_id = str(data.get('uid') or data.get('player_id'))
    if p_id:
        user = users_col.find_one({"player_id": p_id})
        if user:
            users_col.update_one({"_id": user['_id']}, {"$set": {"is_vip": True}})
            bot.send_message(user['_id'], "✅ **DÉPÔT DÉTECTÉ**\nVIP activé !")
            return "OK", 200
    return "Ignored", 200

@app.route('/')
def home():
    return "Robot 1 - Mode 03/05 OK"

if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    bot.infinity_polling(timeout=20)
