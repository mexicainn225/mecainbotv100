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

# --- LOGIQUE DE PAIRES DE MINUTES ---
def get_next_signal():
    now = datetime.now()
    pailles_minutes = [
        (2, 3), (8, 10), (12, 13), (18, 20), 
        (22, 23), (28, 30), (32, 33), (38, 40),
        (42, 43), (48, 50), (52, 53), (58, 59)
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
    time_s2 = now.replace(hour=target_hour, minute=s2_f, second=0, microsecond=0)

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

# --- GESTION DES ID & NOTIFICATION ADMIN ---
@bot.message_handler(func=lambda m: m.text.isdigit() and len(m.text) >= 7)
def handle_id(msg):
    # Enregistre l'ID dans la DB
    users_col.update_one({"_id": msg.from_user.id}, {"$set": {"player_id": msg.text}}, upsert=True)
    
    # Message de confirmation à l'utilisateur
    bot.send_message(msg.chat.id, "⏳ **ID enregistré !**\nL'administrateur va vérifier et activer votre accès sous peu.")
    
    # Envoi de la notification à l'ADMIN avec bouton d'activation
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("✅ ACTIVER VIP", callback_data=f"val_{msg.from_user.id}"))
    
    bot.send_message(
        ADMIN_ID, 
        f"🆕 **NOUVEL ID REÇU**\n\n👤 Utilisateur : @{msg.from_user.username or 'Sans nom'}\n🆔 ID Joueur : `{msg.text}`\n🆔 Telegram ID : `{msg.from_user.id}`", 
        reply_markup=markup, 
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("val_"))
def valider(c):
    uid = int(c.data.split("_")[1])
    users_col.update_one({"_id": uid}, {"$set": {"is_vip": True}})
    
    # Confirme à l'admin
    bot.answer_callback_query(c.id, "VIP Activé !")
    bot.edit_message_text(f"✅ Accès VIP activé pour l'utilisateur `{uid}`", c.message.chat.id, c.message.message_id)
    
    # Prévient l'utilisateur
    try:
        bot.send_message(uid, "🌟 **Félicitations !** Votre accès VIP a été activé par l'administrateur. Cliquez sur **🚀 SIGNAL** pour commencer.")
    except:
        pass

@bot.message_handler(func=lambda m: m.text == "📊 STATISTIQUES")
def stats_handler(msg):
    total_users = users_col.count_documents({})
    bot.send_message(msg.chat.id, f"📊 **STATISTIQUES**\n✅ Succès : `98.4%` \n👥 Joueurs : `{total_users}`", parse_mode='Markdown')

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
    return "Robot 1 - Mode Paires & Admin Ready"

if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    render_port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=render_port), daemon=True).start()
    bot.infinity_polling(timeout=20)
