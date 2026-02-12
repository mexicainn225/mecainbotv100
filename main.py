import telebot, random, os, threading, time
from datetime import datetime, timedelta
from flask import Flask
from pymongo import MongoClient

app = Flask(__name__)

@app.route('/')
def home():
    return "Système Mexicain225 - Grosse Côte +2H"

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
CODE_PROMO = "COK225"
ID_VIDEO_UNIQUE = "https://t.me/gagnantpro1xbet/138958" 

admin_state = {}

# --- FONCTIONS SYSTÈME ---
def get_user(u_id):
    user = users_col.find_one({"_id": u_id})
    if not user:
        user = {"_id": u_id, "is_vip": False}
        users_col.insert_one(user)
    return user

def get_grosse_cote_list():
    conf = config_col.find_one({"_id": "grosse_cote"})
    return conf['minutes'] if conf and 'minutes' in conf else []

def notify_all_vips(message_text):
    vips = users_col.find({"is_vip": True})
    for v in vips:
        try:
            bot.send_message(v['_id'], message_text, parse_mode='Markdown')
        except:
            pass

# --- LOGIQUE GROSSE CÔTE (+2 HEURES) ---
def get_grosse_cote_signal():
    now = datetime.now()
    minutes_list = get_grosse_cote_list()
    if not minutes_list: return None
    
    sorted_mins = sorted(minutes_list)
    target_time = None

    for m in sorted_mins:
        # On calcule l'heure cible (Heure actuelle + 2 heures)
        # Si tu donnes '15' à 18h, target devient 20h15
        t_target = now.replace(hour=(now.hour + 2) % 24, minute=m, second=0, microsecond=0)
        
        # Si on dépasse minuit, on ajuste le jour si nécessaire (automatique avec replace/now)
        # Mais on vérifie surtout que ce créneau n'est pas déjà passé
        if t_target > now:
            target_time = t_target
            break

    # Si aucune minute de la liste ne donne un futur (liste épuisée)
    if not target_time:
        return "EXPIRED"

    # Sécurité : Si le prochain signal trouvé est trop loin (plus de 3h), on arrête
    if (target_time - now).total_seconds() > 10800: # 3 heures max
        return "EXPIRED"

    random.seed(target_time.timestamp())
    cote = round(random.uniform(10.0, 200.0), 2)
    prev = round(random.uniform(10.0, 25.0), 2)
    random.seed()
    return target_time, cote, prev, "CONFIRMÉ 💎"

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(msg):
    get_user(msg.from_user.id)
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btns = ["🚀 SIGNAL", "💎 GROSSE CÔTE", "📊 STATS"]
    if msg.from_user.id == ADMIN_ID:
        btns.append("⚙️ SET 02")
    markup.add(*btns)
    bot.send_message(msg.chat.id, "Session en ligne.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💎 GROSSE CÔTE")
def big_sig(msg):
    u = get_user(msg.from_user.id)
    if msg.from_user.id == ADMIN_ID or u.get('is_vip'):
        res = get_grosse_cote_signal()
        
        if res == "EXPIRED" or res is None:
            bot.send_message(msg.chat.id, "📊 **CALCULE EN COURS**\n\nLes prochaines analyses arrivent. Vous recevrez une notification dès validation.")
            return
        
        t_time, cote, prev, label = res
        time_fmt = f"{t_time.strftime('%H:%M')} - {(t_time + timedelta(minutes=1)).strftime('%H:%M')}"
        txt = (f"💎 **{label}**\n\n📅 **HEURE** : `{time_fmt}`\n📈 **OBJECTIF** : `{cote}X+` \n🎯 **VALEUR** : `{prev}X+` \n\n🎁 **CODE PROMO** : `{CODE_PROMO}`")
        bot.send_video(msg.chat.id, ID_VIDEO_UNIQUE, caption=txt, reply_markup=telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("ACCÈS JEU", url=LIEN_INSCRIPTION)), parse_mode='Markdown')
    else:
        bot.send_message(msg.chat.id, "⚠️ Accès VIP requis.")

@bot.message_handler(func=lambda m: m.text == "⚙️ SET 02" and m.from_user.id == ADMIN_ID)
def config_grosse(msg):
    admin_state[ADMIN_ID] = "WAIT_GROSSE"
    bot.send_message(ADMIN_ID, "Entrez les minutes (ex: 15, 40) :")

@bot.message_handler(func=lambda m: admin_state.get(ADMIN_ID) == "WAIT_GROSSE" and m.from_user.id == ADMIN_ID)
def save_grosse(msg):
    try:
        mins = [int(x.strip()) for x in msg.text.split(',')]
        config_col.update_one({"_id": "grosse_cote"}, {"$set": {"minutes": mins}}, upsert=True)
        bot.send_message(ADMIN_ID, "✅ Programmation +2H enregistrée.")
        
        txt_notif = "🔔 **ALERTE GROSSE CÔTE**\n\nNouveaux signaux disponibles (décalage +2H). Consultez la section **💎 GROSSE CÔTE**."
        threading.Thread(target=notify_all_vips, args=(txt_notif,)).start()
    except:
        bot.send_message(ADMIN_ID, "Erreur format.")
    admin_state[ADMIN_ID] = None

# ... (Le reste des handlers SIGNAL et ID reste inchangé) ...

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    bot.infinity_polling(timeout=20)
