import os
import sqlite3
from config import PAYCHECK_COOLDOWN, DAILY_COOLDOWN, DB_PATH

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "economy.db")


# Create or open the database file
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()


# Coins and User Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    coins INTEGER NOT NULL
)
""")
conn.commit()

# Card ID Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS cards (
    card_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    rarity TEXT NOT NULL,
    description TEXT
)
""")
conn.commit()

# Card User Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_cards (
    user_id INTEGER NOT NULL,
    card_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY(user_id, card_id),
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(card_id) REFERENCES cards(card_id)
)
""")


# Seed Cards, Rarities, and Descriptions
cards = [
    ("Rusty Scrap", "common", "A bent piece of scrap metal pulled from the trash."),
    ("Shiny Trinket", "rare", "A small object that gleams despite its humble origin."),
    ("Encrypted Relic", "epic", "An ancient device humming with unknown power."),
    ("Crown of the Forgotton", "legendary", "A lost artifact whispered about in legends.")
    
]
cursor.executemany(
    "INSERT OR IGNORE INTO cards (name, rarity, description) VALUES (?, ?, ?)",
    cards
)
conn.commit()



# Check if 'last_daily' column exists
cursor.execute("PRAGMA table_info(users)")
columns = [col[1] for col in cursor.fetchall()]

if 'last_daily' not in columns:
    cursor.execute("ALTER TABLE users ADD COLUMN last_daily INTEGER")
    conn.commit()

try:
    cursor.execute("ALTER TABLE users ADD COLUMN last_earn INTEGER")
except sqlite3.OperationalError:
    # Column already exists
    pass
conn.commit()

def add_card_to_user(user_id, card_id, amount=1):
    cursor.execute("""
    INSERT INTO user_cards (user_id, card_id, quantity) VALUES (?, ?, ?)
    ON CONFLICT(user_id, card_id) 
    DO UPDATE SET quantity = quantity + ?
    """,
    (user_id, card_id, amount, amount))
    conn.commit()

def get_cards_by_rarity(rarity):
    cursor.execute("SELECT card_id, name FROM cards WHERE rarity = ?", (rarity,))
    return cursor.fetchall()
    
def get_user_inventory(user_id):
    cursor.execute("""
        SELECT c.name, c.rarity, uc.quantity
        FROM user_cards uc
        JOIN cards c ON uc.card_id = c.card_id
        WHERE uc.user_id = ?
        ORDER BY c.rarity
    """, (user_id,))
    
    return cursor.fetchall()


def get_user(user_id):
    cursor.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if result is None:
        cursor.execute(
            "INSERT INTO users (user_id, coins) VALUES (?, ?)",
            (user_id, 0)
        )
        conn.commit()
        return 0
    
    return result[0]
 
 
def add_coins(user_id, amount):
    coins = get_user(user_id)
    coins += amount
    
    cursor.execute(
        "UPDATE users SET coins = ? WHERE user_id = ?",
        (coins, user_id)
    )
    conn.commit()
    
    return coins
    
def can_add_coins(user_id):
    cursor.execute("SELECT last_earn FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    now = int(time.time())
    
    if result is None or result[0] is None:
        cursor.execute("INSERT OR IGNORE INTO users (user_id, coins, last_earn) VALUES (?, ?, ?)", (user_id, 0, None))
        conn.commit()
        return True, 0
        
    elapsed = now - result[0]
    
    if elapsed >= PAYCHECK_COOLDOWN:
        return True, 0
    else:
        return False, PAYCHECK_COOLDOWN - elapsed
    
def update_last_earn(user_id):
    cursor.execute("UPDATE users SET last_earn = ? WHERE user_id = ?", (int(time.time()), user_id))
    conn.commit()
    
def remove_coins(user_id, amount):
    coins = get_user(user_id)
    
    if coins < amount:
        return None
        
    coins -= amount
    
    cursor.execute(
        "UPDATE users SET coins = ? WHERE user_id = ?",
        (coins, user_id)
    )
    conn.commit()
    
    return coins
    
import time

def can_claim_daily(user_id):
    cursor.execute(
        "SELECT last_daily FROM users WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    
    now = int(time.time())
    
    if result is None or result[0] is None:
        return True, 0
        
    elapsed = now - result[0]
    
    if elapsed >= DAILY_COOLDOWN:
        return True, 0
    else:
        return False, DAILY_COOLDOWN - elapsed
        
def claim_daily(user_id, reward):
    now = int(time.time())
    
    coins = add_coins(user_id, reward)
    
    cursor.execute(
        "UPDATE users SET last_daily = ? WHERE user_id = ?",
        (now, user_id)
    )
    conn.commit()
    
    return coins
    
def get_top_users(limit=10):
    """
    Returns a list of tuples: (user_id, coins) for the top users by coins.
    """
    
    cursor.execute("SELECT user_id, coins FROM users ORDER BY coins DESC LIMIT ?",
    (limit,)
    )
    return cursor.fetchall()