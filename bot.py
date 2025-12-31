import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import time
import random #RNG
from database import get_user, add_coins, remove_coins, can_claim_daily, claim_daily, can_add_coins, update_last_earn, add_card_to_user, get_cards_by_rarity
from database import get_user_inventory, get_top_users
from collections import Counter
import asyncio
from config import PACK_COST, DAILY_REWARD, SLOTS, MULTIPLIERS 

# Load Token
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
ADMIN = int(os.getenv("DISCORD_ID"))

# This controls what information Discord sends your bot
intents = discord.Intents.default()
intents.message_content = True

# Create the bot
bot = commands.Bot(command_prefix="!", intents=intents)

# ---- EVENTS ----
@bot.event
async def on_ready():
        print (f"Logged in as {bot.user}")
        
# ---- COMMANDS ---- 
# ctx means Context, Author calls for who called it, Name, ID, and Bot says who called it.

@bot.command() # Balance Check
async def balance(ctx):
    coins = get_user(ctx.author.id)
    await ctx.send(f"💰 {ctx.author.name.title()} has **{coins} coins**")
    
@bot.command() # Leaderboard
async def leaderboard(ctx, top: int = 10):
    results = get_top_users(top)
    
    if not results:
        await ctx.send("No users found in the database yet!")
        return
        
    medals = ["🥇", "🥈", "🥉"]
        
    leaderboard_msg = "**💰Coin Leaderboard 💰**\n"
    for rank, (user_id, coins) in enumerate(results, start=1):
        user = await bot.fetch_user(user_id)
        
        if rank <= 3:
            prefix = medals[rank - 1]
        else:
            prefix = f"{rank}."
        
        leaderboard_msg += f"{prefix} {user.name}: {coins} coins\n"
        
    await ctx.send(leaderboard_msg)
    
@bot.command() # Earning Coins
async def earn(ctx):
    can_claim, remaining = can_add_coins(ctx.author.id)
    
    if can_claim:
        reward = random.randint(1, 10) # Picks value between 1 and 10
        total = add_coins(ctx.author.id, reward)
        update_last_earn(ctx.author.id)
        await ctx.send(f"💰 You earned {reward} coins! Total: {total} coins")
    else:
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        await ctx.send(f"⏳ You must wait {hours}h {minutes}m before earning again!")
        
    
@bot.command() # Spending Coins
async def spend(ctx, amount: int):
    result = remove_coins(ctx.author.id, amount)
    
    if result is None:
        await ctx.send("❌ Not enough coins!")
    else:
        await ctx.send(f"💸 Spent {amount} coins. Remaining: **{result}**")
        
@bot.command()
async def daily(ctx): # Daily Reward & Check
    can_claim, remaining = can_claim_daily(ctx.author.id)
    
    if can_claim:
        coins = claim_daily(ctx.author.id, DAILY_REWARD)
        await ctx.send(
            f"🎁Daily reward claimed!\n" 
            f"You receieved **{DAILY_REWARD} coins**.\n"
            f"Total: **{coins} coins**"
            # \n means new line. If ctx.send was executed 3 times, it would be messy. \n compacts the message.
        )
    else:
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        
        await ctx.send(
            f"⏳ You already claimed your daily.\n"
            f"Try again in **{hours}h {minutes}m**."
        )

@bot.command()
async def openpack(ctx): #Core Gameplay
    
    # Check if user has enough coins
    coins = get_user(ctx.author.id)
    
    if coins < PACK_COST:
        await ctx.send(f"Sorry **{ctx.author.name}**, you need **{PACK_COST} coins** to open a pack! You have **{coins} coins**.")
        return
        
    #Deduct coins
    remove_coins(ctx.author.id, PACK_COST)
    
    # Roll for rarity
    roll = random.randint(1, 100)
    if roll <= 1:
        rarity = "legendary"
    elif roll <= 5:
        rarity = "epic"
    elif roll <= 30:
        rarity = "rare"
    else:
        rarity = "common"
        
    # Pick a random card of that rarity from the DB
    cards = get_cards_by_rarity(rarity)
    if not cards:
        await ctx.send("No cards of rarity legendary found.")
        return
    card_id, card_name = random.choice(cards)
    
    # Add the card to the user's inventory // Zero[0] from index "ID" [1] means String "Name"
    # Can always use card_id or card_name instead if you want to
    add_card_to_user(ctx.author.id, card_id)
    
    # Notify
    await ctx.send(f"{ctx.author.name.title()} opened a pack and got a **{rarity.capitalize()}** card: **{card_name}**!")

@bot.command()    
async def inventory(ctx): # Inventory Get
    inventory = get_user_inventory(ctx.author.id)
    
    if not inventory:
        await ctx.send(f"**{ctx.author.name.title()}**, your inventory is empty! Use **!openpack** to start collecting!")
        return
        
    message = f"📦**{ctx.author.name.title()}'s Card Inventory** 📦\n\n"
    
    for name, rarity, quantity in inventory:
        message += f"**{name}** ({rarity.capitalize()}) x {quantity}\n"
        
    await ctx.send(message)
    
@bot.command()
async def gamble(ctx, amount: int): # Gamba
    user_coins = get_user(ctx.author.id)
    
    if amount > user_coins:
        await ctx.send("You do not have enough coins to gamble with that amount. You have **{coins} coins**.")
        return
    
    # Pay up :)
    remove_coins(ctx.author.id, amount)
    
    #Creates 3x3 grid 
    grid = [[random.choice(SLOTS) for _ in range(3)] for _ in range (3)]
    middle_row = grid[1] #only the middle row matters
    
    # Suspense Factor
    for row in grid:
        await ctx.send(" | ".join(row)) 
        await asyncio.sleep(0.5) # Half-second delay
    
    # Check middle row for win
    counts = Counter(middle_row)
    most_common_emoji, count = counts.most_common(1)[0]
    
    if count ==3:
        winnings = int(amount * MULTIPLIERS[most_common_emoji])
        add_coins(ctx.author.id, winnings)
        result_msg = f"🎉 **JACKPOT!!!** You got 3 {most_common_emoji} in a row and won {winnings} coins!"
    elif count ==2:
        winnings = 0
        result_msg = f"**Almost!!!** You got 2 {most_common_emoji} in a row in the middle row!"
    else:
        winnings = 0
        result_msg = f"Damn... You got {middle_row[0]} | {middle_row[1]} | {middle_row[2]} - better luck next time!"
    
    await ctx.send(result_msg)
    
    
    
# ---- DEV COMMANDS ----
@bot.command()
async def givecoins(ctx, member: discord.Member, amount: int): # You Cheater
    if ctx.author.id != ADMIN:
        await ctx.send("**You do not have permission to do that**.")
        return
        
    if amount <=0:
        await ctx.send("You can't give yourself 0 coins!")
        return
        
    add_coins(member.id, amount)
    await ctx.send(f"Gave **{amount}** coins to **{member.name.title()}**.")
    
bot.run(TOKEN)