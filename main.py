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

# --- LOGIQUE DE PAIRES DE MINUTES (TES EXEMPLES) ---
def get_next_signal():
    now = datetime.now()
    
    # Ici, on définit manuellement chaque Signal 1 et son Signal 2 correspondant
    # (Minute_S1, Minute_S2)
    pailles_minutes = [
        (2, 3),   # Ton exemple 1
        (8, 10),  # Ton exemple 2
        (12, 13), # Ton exemple 3
        (18, 20), 
        (22, 23),
        (28, 30), # Ton exemple 4
        (32, 33),
        (38, 40),
        (42, 43),
        (48, 50),
        (52, 53),
        (58, 59)
    ]
    
    current_min = now.minute
    target_pair = None
    target_hour = now.hour

    # Trouver la prochaine paire dont le Signal 1 n'est pas encore passé
    for s1, s2 in pailles_minutes:
        if s1 > current_min:
            target_pair = (s1, s2)
            break
    
    # Si on a fini l'heure, on reprend la première paire à l'heure suivante
    if target_pair is None:
        target_pair = pailles_minutes[0]
        target_hour = (now.hour + 1) % 24

    s1_final, s2_final = target_pair
    
    # Création des objets datetime pour l'affichage propre
    time_s1 = now.replace(hour=target_hour, minute=s1_final, second=0, microsecond=0)
    time_s2 = now.replace(hour=target_hour, minute=s2_final, second=0, microsecond=0)

    # GÉNÉRATION DES CÔTES (SÉCURITÉ 1.5X TOUJOURS)
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
    bot.send_message(msg.chat.id, "🛰 **Système Connecté**", reply_markup=markup)

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
        bot.send_message(msg.chat.id, "⚠️ **ACCÈS VIP REQUIS**")

# --- LE RESTE DU CODE (ID, STATS, WEBHOOK) ---
@bot.message_handler(func=lambda m: m.text.isdigit() and len(m.text) >= 7)
def handle_id(msg):
    users_col.update_one({"_id": msg.from_user.id}, {"$set": {"player_id": msg.text}}, upsert=True)
    bot.send_message(msg.chat.id, "⏳ ID enregistré.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("val_"))
def valider(c):
    uid = int(c.data.split("_")[1])
    users_col.update_one({"_id": uid}, {"$set": {"is_vip": True}})
    bot.send_message(uid, "🌟 VIP activé !")

if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    render_port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=render_port), daemon=True).start()
    bot.infinity_polling(timeout=20)
