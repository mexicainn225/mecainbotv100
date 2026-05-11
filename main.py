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
config_col = db['config']

LIEN_INSCRIPTION = "https://lkbb.cc/e2d8"
ID_VIDEO_UNIQUE = "https://t.me/gagnantpro1xbet/138958" 

# --- LOGIQUE DE MINUTES FIXES ---
def get_next_signal():
    now = datetime.now()
    
    # Liste des minutes pour le Signal 1
    # Le Signal 2 sera calculé automatiquement à +2 minutes
    minutes_fixes = [1, 8, 11, 18, 21, 28, 31, 38, 41, 48, 51, 58]
    
    current_min = now.minute
    target_min = None
    target_hour = now.hour

    # On cherche la prochaine minute disponible dans la liste
    for m in minutes_fixes:
        if m > current_min:
            target_min = m
            break
    
    # Si on a passé 58, on repart à 01 l'heure suivante
    if target_min is None:
        target_min = minutes_fixes[0]
        target_hour = (now.hour + 1) % 24

    target_time = now.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)

    # GÉNÉRATION DES CÔTES
    random.seed(target_time.timestamp())
    cote = round(random.uniform(10.0, 85.0), 2) # Objectif
    prev = 1.50 # Sécurité fixe
    random.seed() 
    
    return target_time, cote, prev

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def start(msg):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🚀 SIGNAL", "📊 STATISTIQUES")
    bot.send_message(msg.chat.id, "🛰 **Système Lucky Jet Connecté**", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🚀 SIGNAL")
def signal_handler(msg):
    # Vérification VIP
    u = users_col.find_one({"_id": msg.from_user.id})
    if msg.from_user.id == ADMIN_ID or (u and u.get('is_vip')):
        t_time, cote, prev = get_next_signal()
        
        # Signal 2 = Signal 1 + 2 minutes
        rappel_time = t_time + timedelta(minutes=2)
        
        caption = (f"🚀 **PRÉDICTION LUCKY JET**\n"
                   f"━━━━━━━━━━━━━━━━━━\n"
                   f"📍 **SIGNAL 1** : `{t_time.strftime('%H:%M')}`\n"
                   f"📍 **SIGNAL 2** : `{rappel_time.strftime('%H:%M')}`\n"
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
        bot.send_message(msg.chat.id, "⚠️ **ACCÈS VIP REQUIS**\n\nEnvoyez votre ID joueur pour commencer.")

@bot.message_handler(func=lambda m: m.text.isdigit() and len(m.text) >= 7)
def handle_id(msg):
    player_id = msg.text
    users_col.update_one({"_id": msg.from_user.id}, {"$set": {"player_id": player_id}}, upsert=True)
    bot.send_message(msg.chat.id, "⏳ **ID Joueur enregistré !**\n\nFaites votre dépôt pour activer l'accès.")
    
    markup = telebot.types.InlineKeyboardMarkup().add(
        telebot.types.InlineKeyboardButton("✅ ACTIVER VIP", callback_data=f"val_{msg.from_user.id}")
    )
    bot.send_message(ADMIN_ID, f"🆕 **NOUVEL ID** : `{player_id}`", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "📊 STATISTIQUES")
def stats_handler(msg):
    total_users = users_col.count_documents({})
    bot.send_message(msg.chat.id, f"📊 **STATISTIQUES**\n✅ Succès : `98.4%` \n👥 Joueurs : `{total_users}`", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda c: c.data.startswith("val_"))
def valider_vip(c):
    uid = int(c.data.split("_")[1])
    users_col.update_one({"_id": uid}, {"$set": {"is_vip": True}})
    bot.send_message(uid, "🌟 **Félicitations !** Ton accès VIP est désormais activé.")
    bot.answer_callback_query(c.id, "Activé")

# --- WEBHOOK & LANCEMENT ---
@app.route('/webhook1win', methods=['POST'])
def handle_1win():
    data = request.json
    p_id = str(data.get('uid') or data.get('player_id'))
    if p_id:
        user = users_col.find_one({"player_id": p_id})
        if user:
            users_col.update_one({"_id": user['_id']}, {"$set": {"is_vip": True}})
            bot.send_message(user['_id'], "✅ **DÉPÔT DÉTECTÉ**\nAccès VIP activé !")
            return "OK", 200
    return "Ignored", 200

@app.route('/')
def home():
    return "Système Lucky Jet Robot 1 - En ligne"

if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    render_port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=render_port), daemon=True).start()
    bot.infinity_polling(timeout=20)
