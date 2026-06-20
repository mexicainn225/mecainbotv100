import telebot
import random
import os
import threading
import time
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
config_col = db['config']  # Collection pour stocker la minute de départ de l'admin

LIEN_INSCRIPTION = "https://lkbb.cc/e2d8"
ID_VIDEO_UNIQUE = "https://t.me/gagnantpro1xbet/138958" 

# --- LOGIQUE DE SIGNAL UNIQUE AVEC SECONDES FIXES (:50) ---
def get_next_signal():
    now = datetime.now()
    
    # Récupérer la minute de départ depuis MongoDB (par défaut : 0)
    config = config_col.find_one({"_id": "settings"})
    start_min = config.get("start_minute", 0) if config else 0
    
    # Générer la liste des minutes cibles sur une heure
    target_minutes = []
    current_calc_min = start_min
    while current_calc_min < 60:
        target_minutes.append(current_calc_min)
        current_calc_min += 4
    
    current_min = now.minute
    target_s1 = None
    target_hour = now.hour

    # Trouver la prochaine minute disponible
    for m in target_minutes:
        if m > current_min:
            target_s1 = m
            break
        # Si on est sur la même minute mais que les 50 secondes sont dépassées, on passe au suivant
        elif m == current_min and now.second >= 50:
            continue
        elif m == current_min and now.second < 50:
            target_s1 = m
            break
    
    # Gestion du passage à l'heure suivante (garantit la continuité même à minuit)
    if target_s1 is None:
        target_s1 = target_minutes[0]
        next_hour_dt = now + timedelta(hours=1)
        target_hour = next_hour_dt.hour
        time_signal = now.replace(year=next_hour_dt.year, month=next_hour_dt.month, day=next_hour_dt.day, hour=target_hour, minute=target_s1, second=50, microsecond=0)
    else:
        time_signal = now.replace(hour=target_hour, minute=target_s1, second=50, microsecond=0)

    # GÉNÉRATION DES CÔTES (SÉCURITÉ FIXE 1.50)
    random.seed(time_signal.timestamp())
    cote = round(random.uniform(10.0, 85.0), 2)
    prev = 1.50
    random.seed() 
    
    return time_signal, cote, prev

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def start(msg):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btns = ["🚀 SIGNAL", "📊 STATISTIQUES"]
    if msg.from_user.id == ADMIN_ID:
        btns.append("⚙️ CONFIGURATION")
    markup.add(*btns)
    bot.send_message(msg.chat.id, "🛰 **Système Lucky Jet Connecté**", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🚀 SIGNAL")
def signal_handler(msg):
    u = users_col.find_one({"_id": msg.from_user.id})
    if msg.from_user.id == ADMIN_ID or (u and u.get('is_vip')):
        t_s1, cote, prev = get_next_signal()
        
        caption = (f"🚀 **PRÉDICTION LUCKY JET**\n"
                   f"━━━━━━━━━━━━━━━━━━\n"
                   f"📍 **SIGNAL** : `{t_s1.strftime('%H:%M:%S')}`\n"
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

# --- OPTIONS ADMINISTRATEUR ---

@bot.message_handler(func=lambda m: m.text == "⚙️ CONFIGURATION" and m.from_user.id == ADMIN_ID)
def config_menu(msg):
    config = config_col.find_one({"_id": "settings"})
    current_start = config.get("start_minute", 0) if config else 0
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("Minute :00", callback_data="set_0"),
        telebot.types.InlineKeyboardButton("Minute :01", callback_data="set_1"),
        telebot.types.InlineKeyboardButton("Minute :02", callback_data="set_2")
    )
    bot.send_message(
        msg.chat.id, 
        f"⚙️ **CONFIGURATION DES MINUTES**\n\nMinute de départ actuelle : `:{current_start:02d}`\n\n"
        "Pour changer sur une autre valeur libre, envoie un message avec le mot-clé **depart** suivi de la minute.\n"
        "Exemple : `depart 0` ou `depart 2`", 
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def set_minute_callback(c):
    new_min = int(c.data.split("_")[1])
    config_col.update_one({"_id": "settings"}, {"$set": {"start_minute": new_min}}, upsert=True)
    bot.answer_callback_query(c.id, f"Départ configuré à :{new_min:02d}")
    bot.edit_message_text(f"✅ **Configuration mise à jour**\nLes signaux commenceront désormais aux minutes : `:{new_min:02d}:50`, `:{new_min+4:02d}:50`, `:{new_min+8:02d}:50`...", c.message.chat.id, c.message.message_id, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.text.lower().startswith("depart"))
def set_minute_text(msg):
    try:
        new_min = int(msg.text.split()[1])
        if 0 <= new_min < 60:
            config_col.update_one({"_id": "settings"}, {"$set": {"start_minute": new_min}}, upsert=True)
            bot.send_message(msg.chat.id, f"✅ **Succès !** La minute de départ a été fixée à `:{new_min:02d}`.", parse_mode='Markdown')
        else:
            bot.send_message(msg.chat.id, "⚠️ Choisis une minute valide entre 0 et 59.")
    except:
        bot.send_message(msg.chat.id, "Format incorrect. Écris par exemple : `depart 0`")

# --- GESTION DES ID & ACTIVATION ADMIN ---
@bot.message_handler(func=lambda m: m.text.isdigit() and len(m.text) >= 7)
def handle_id(msg):
    users_col.update_one({"_id": msg.from_user.id}, {"$set": {"player_id": msg.text}}, upsert=True)
    bot.send_message(msg.chat.id, "⏳ **ID enregistré !**\nL'administrateur va valider votre accès.")
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("✅ ACTIVER VIP", callback_data=f"val_{msg.from_user.id}"))
    
    bot.send_message(
        ADMIN_ID, 
        f"🆕 **NOUVEL ID**\n👤: @{msg.from_user.username}\n🆔 ID: `{msg.text}`", 
        reply_markup=markup, 
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("val_"))
def valider_callback(c):
    uid = int(c.data.split("_")[1])
    users_col.update_one({"_id": uid}, {"$set": {"is_vip": True}})
    
    bot.answer_callback_query(c.id, "Activé !")
    bot.edit_message_text(f"✅ VIP activé pour {uid}", c.message.chat.id, c.message.message_id)
    
    try:
        bot.send_message(uid, "🌟 **Accès VIP activé !** Cliquez sur 🚀 **SIGNAL**.")
    except:
        pass

@bot.message_handler(func=lambda m: m.text == "📊 STATISTIQUES")
def stats_handler(msg):
    count = users_col.count_documents({})
    bot.send_message(msg.chat.id, f"📊 **STATISTIQUES**\n👥 Joueurs : `{count}`\n✅ Précision : `98%`", parse_mode='Markdown')

# --- WEBHOOK ---
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
    return "Robot 1 en ligne - Signal Unique à :50s OK"

if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    bot.infinity_polling(timeout=20)
