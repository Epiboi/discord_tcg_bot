# config.py

# ====== Bot Economy Settings =====
PACK_COST = 100
DAILY_REWARD = 100

# ===== Cooldowns (seconds) =====
DAILY_COOLDOWN = 86400 # 24 Hours
PAYCHECK_COOLDOWN = 7200 # 2 Hours

# ===== Slot Machine Settings =====
SLOTS = (["🍒"] * 8 + ["🍉"] * 5 + ["🍆"] * 2 + ["🔔"] * 10 # Weights
)

MULTIPLIERS = {
        "🍆": 10,
        "🍉": 5,
        "🍒": 2,
        "🔔": 1.2
}

# ===== Database =====
DB_PATH = "data/economy.db"