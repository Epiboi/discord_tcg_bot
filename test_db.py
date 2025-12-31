from database import add_card_to_user, get_user, get_cards_by_rarity, conn, cursor

user_id = 12345
card_id = 1

add_card_to_user(user_id, card_id)

cursor.execute("SELECT * FROM user_cards WHERE user_id = ?", (user_id,))
rows = cursor.fetchall() 

print("Current rows for user:", rows)

conn.close()