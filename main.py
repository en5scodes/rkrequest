import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import aiohttp
import json
import random
import datetime
from datetime import timedelta
from typing import Optional, Union, List
import config
import os
import math

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix=config.PREFIX, intents=intents)

ticket_data = {}
giveaway_data = {}
next_giveaway_id = 1

MEMBER_EMOJI_ID = 123456789012345678
QUESTION_EMOJI_ID = 123456789012345678
DOLLAR_EMOJI_ID = 123456789012345678
ROCKET_EMOJI_ID = 123456789012345678
SERVICE_EMOJI_ID = 123456789012345678
BELL_EMOJI_ID = 123456789012345678
SHOP_EMOJI_ID = 123456789012345678
SQUARE_TICK_EMOJI_ID = 123456789012345678
CIRCLE_TICK_EMOJI_ID = 123456789012345678
CONFETTI_EMOJI_ID = 123456789012345678
TIME_EMOJI_ID = 123456789012345678
GIFT_EMOJI_ID = 123456789012345678
INFO_EMOJI_ID = 123456789012345678
KEY_EMOJI_ID = 123456789012345678
LIKE_EMOJI_ID = 123456789012345678
LINK_EMOJI_ID = 123456789012345678
NEWS_EMOJI_ID = 123456789012345678
NO_EMOJI_ID = 123456789012345678

GIVEAWAY_GIFT_EMOJI_ID = 123456789012345678
GIVEAWAY_TIME_EMOJI_ID = 123456789012345678
GIVEAWAY_MEMBER_EMOJI_ID = 123456789012345678
RED_ARROW_EMOJI_ID = 123456789012345678
GIVEAWAY_KEY_EMOJI_ID = 123456789012345678

COINGECKO_SIMPLE = "https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"

ASSET_MAP = {
    "btc": "bitcoin", "bitcoin": "bitcoin",
    "eth": "ethereum", "ethereum": "ethereum",
    "sol": "solana", "solana": "solana",
    "doge": "dogecoin", "dogecoin": "dogecoin",
    "usdt": "tether", "tether": "tether",
    "bnb": "binancecoin", "xrp": "ripple",
    "ltc": "litecoin", "litecoin": "litecoin"
}

DATA = {"addresses": {}}

class TicketSelect(discord.ui.Select):
    def __init__(self):
        purchase_emoji = discord.PartialEmoji(
            name="shop", 
            id=config.PURCHASE_EMOJI_ID, 
            animated=config.PURCHASE_EMOJI_ANIMATED
        )
        support_emoji = discord.PartialEmoji(
            name="service", 
            id=config.SUPPORT_EMOJI_ID, 
            animated=config.SUPPORT_EMOJI_ANIMATED
        )
        
        options = [
            discord.SelectOption(label="Purchase", description="Open a purchase ticket", emoji=purchase_emoji, value="purchase"),
            discord.SelectOption(label="Support", description="Open a support ticket", emoji=support_emoji, value="support")
        ]
        
        super().__init__(placeholder="Select a ticket type...", min_values=1, max_values=1, options=options, custom_id="ticket_select")
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "purchase":
            await interaction.response.send_modal(PurchaseTicketModal())
        elif self.values[0] == "support":
            await interaction.response.send_modal(SupportTicketModal())

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

class PurchaseTicketModal(discord.ui.Modal, title="Purchase Ticket"):
    def __init__(self):
        super().__init__()
        self.product = discord.ui.TextInput(label="Product", placeholder="What product would you like to purchase?", style=discord.TextStyle.short, required=True, max_length=100)
        self.payment = discord.ui.TextInput(label="Payment Method", placeholder="How would you like to pay? (Crypto, Paypal, etc.)", style=discord.TextStyle.short, required=True, max_length=100)
        self.add_item(self.product)
        self.add_item(self.payment)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        ticket_id = f"purchase-{interaction.user.id}-{int(interaction.created_at.timestamp())}"
        ticket_data[ticket_id] = {
            "user_id": interaction.user.id, "user_name": str(interaction.user),
            "product": self.product.value, "payment": self.payment.value,
            "type": "Purchase", "created_at": interaction.created_at, "channel_id": None
        }
        
        category = bot.get_channel(config.TICKET_CATEGORY_ID)
        if not category:
            embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Ticket category not found! Please contact an administrator.", color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        clean_name = ''.join(c for c in interaction.user.name if c.isalnum() or c in ('-', '_')).rstrip('_').rstrip('-')
        if not clean_name: clean_name = str(interaction.user.id)
        
        existing_tickets = 0
        for channel in category.channels:
            if str(interaction.user.id) in channel.name:
                existing_tickets += 1
        
        if existing_tickets == 0:
            channel_name = f"purchase-{clean_name}"
        else:
            channel_name = f"purchase-{clean_name}-{existing_tickets+1}"
        
        if len(channel_name) > 32:
            if existing_tickets == 0:
                channel_name = f"purchase-{interaction.user.id}"
            else:
                channel_name = f"purchase-{interaction.user.id}-{existing_tickets+1}"
        
        try:
            channel = await category.create_text_channel(name=channel_name[:32], overwrites={
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }, topic=f"Purchase ticket for {interaction.user} | ID: {ticket_id}")
        except Exception as e:
            embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Failed to create ticket channel.", color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        ticket_data[ticket_id]["channel_id"] = channel.id
        
        embed = discord.Embed(title=f"<:infoey:{INFO_EMOJI_ID}> **Welcome to your ticket**", color=discord.Color.green(), timestamp=interaction.created_at)
        embed.add_field(name="", value=f"<:likey:{LIKE_EMOJI_ID}> **Hello {interaction.user.mention} Thanks for opening a ticket!**\n<:keyy:{KEY_EMOJI_ID}> **Ticket type:** ```Purchase```\n<:shop:{SHOP_EMOJI_ID}> **Product:** ```{self.product.value}```\n<:__:{DOLLAR_EMOJI_ID}> **Payment Method:** ```{self.payment.value}```\n<:infoey:{INFO_EMOJI_ID}> **Information**\nA staff member will be with you shortly. Please be patient and do not ping any staff member.", inline=False)
        embed.set_footer(text=f"<:ticky:{SQUARE_TICK_EMOJI_ID}> Ticket ID: {ticket_id}")
        
        view = TicketChannelView(ticket_id=ticket_id)
        await channel.send(f"<@{config.OWNER_ID}>", embed=embed, view=view)
        
        embed = discord.Embed(description=f"<:tick:{CIRCLE_TICK_EMOJI_ID}> Purchase ticket created! Please check {channel.mention}", color=discord.Color.green())
        await interaction.followup.send(embed=embed, ephemeral=True)

class SupportTicketModal(discord.ui.Modal, title="Support Ticket"):
    def __init__(self):
        super().__init__()
        self.where = discord.ui.TextInput(label="Where did you buy from", placeholder="For eg, Ticket, Website, etc.", style=discord.TextStyle.short, required=True, max_length=100)
        self.description = discord.ui.TextInput(label="Description", placeholder="Please describe your issue in detail", style=discord.TextStyle.paragraph, required=True, max_length=1000)
        self.add_item(self.where)
        self.add_item(self.description)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        ticket_id = f"support-{interaction.user.id}-{int(interaction.created_at.timestamp())}"
        ticket_data[ticket_id] = {
            "user_id": interaction.user.id, "user_name": str(interaction.user),
            "where": self.where.value, "description": self.description.value,
            "type": "Support", "created_at": interaction.created_at, "channel_id": None
        }
        
        category = bot.get_channel(config.TICKET_CATEGORY_ID)
        if not category:
            embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Ticket category not found! Please contact an administrator.", color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        clean_name = ''.join(c for c in interaction.user.name if c.isalnum() or c in ('-', '_')).rstrip('_').rstrip('-')
        if not clean_name: clean_name = str(interaction.user.id)
        
        existing_tickets = 0
        for channel in category.channels:
            if str(interaction.user.id) in channel.name:
                existing_tickets += 1
        
        if existing_tickets == 0:
            channel_name = f"support-{clean_name}"
        else:
            channel_name = f"support-{clean_name}-{existing_tickets+1}"
        
        if len(channel_name) > 32:
            if existing_tickets == 0:
                channel_name = f"support-{interaction.user.id}"
            else:
                channel_name = f"support-{interaction.user.id}-{existing_tickets+1}"
        
        try:
            channel = await category.create_text_channel(name=channel_name[:32], overwrites={
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }, topic=f"Support ticket for {interaction.user} | ID: {ticket_id}")
        except Exception as e:
            embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Failed to create ticket channel.", color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        ticket_data[ticket_id]["channel_id"] = channel.id
        
        embed = discord.Embed(title=f"<:infoey:{INFO_EMOJI_ID}> **Welcome to your ticket**", color=discord.Color.blue(), timestamp=interaction.created_at)
        embed.add_field(name="", value=f"<:likey:{LIKE_EMOJI_ID}> **Hello {interaction.user.mention} Thanks for opening a ticket!**\n<:keyy:{KEY_EMOJI_ID}> **Ticket type:** ```Support```\n<:shop:{SHOP_EMOJI_ID}> **Where did you buy from:** ```{self.where.value}```\n<:infoey:{INFO_EMOJI_ID}> **Description:** ```{self.description.value}```\n<:infoey:{INFO_EMOJI_ID}> **Information**\nA staff member will be with you shortly. Please be patient and do not ping any staff member.", inline=False)
        embed.set_footer(text=f"<:ticky:{SQUARE_TICK_EMOJI_ID}> Ticket ID: {ticket_id}")
        
        view = TicketChannelView(ticket_id=ticket_id)
        await channel.send(f"<@{config.OWNER_ID}>", embed=embed, view=view)
        
        embed = discord.Embed(description=f"<:tick:{CIRCLE_TICK_EMOJI_ID}> Support ticket created! Please check {channel.mention}", color=discord.Color.green())
        await interaction.followup.send(embed=embed, ephemeral=True)

class TicketChannelView(discord.ui.View):
    def __init__(self, ticket_id: str):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
    
    @discord.ui.button(emoji=discord.PartialEmoji(name="bell", id=config.CLOSE_EMOJI_ID, animated=config.CLOSE_EMOJI_ANIMATED), label="Close", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != config.OWNER_ID:
            embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> You cannot close this ticket", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        data = ticket_data.get(self.ticket_id)
        if not data:
            embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Ticket data not found", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(title=f"<:newsy:{NEWS_EMOJI_ID}> **Purchase Ticket Transcripts**", color=discord.Color.red(), timestamp=interaction.created_at)
        if data["type"] == "Purchase":
            embed.add_field(name="", value=f"<:shop:{SHOP_EMOJI_ID}> **Product:** ```{data['product']}```\n<:__:{DOLLAR_EMOJI_ID}> **Payment Method:** ```{data['payment']}```\n<:bell:{BELL_EMOJI_ID}> **Closed by:** <@{interaction.user.id}>\n<:taday:{CONFETTI_EMOJI_ID}> You are more than welcome to purchase another product.", inline=False)
        else:
            embed.add_field(name="", value=f"<:shop:{SHOP_EMOJI_ID}> **Where did you buy from:** ```{data['where']}```\n<:infoey:{INFO_EMOJI_ID}> **Description:** ```{data['description']}```\n<:bell:{BELL_EMOJI_ID}> **Closed by:** <@{interaction.user.id}>\n<:taday:{CONFETTI_EMOJI_ID}> You are more than welcome to purchase another product.", inline=False)
        
        embed.set_footer(text=f"<:ticky:{SQUARE_TICK_EMOJI_ID}> Ticket ID: {self.ticket_id}")
        
        user = bot.get_user(data["user_id"])
        if user:
            try: await user.send(embed=embed)
            except: pass
        
        channel = interaction.channel
        await interaction.response.defer()
        
        closing_embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Closing ticket...", color=discord.Color.red())
        await interaction.followup.send(embed=closing_embed, ephemeral=False)
        
        await asyncio.sleep(2)
        await channel.delete()
        
        if self.ticket_id in ticket_data:
            del ticket_data[self.ticket_id]
    
    @discord.ui.button(emoji=discord.PartialEmoji(name="bell", id=config.NOTIFY_EMOJI_ID, animated=config.NOTIFY_EMOJI_ANIMATED), label="Notify", style=discord.ButtonStyle.gray, custom_id="notify_user")
    async def notify_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = ticket_data.get(self.ticket_id)
        if not data:
            embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Ticket data not found", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(description=f"<:bell:{BELL_EMOJI_ID}> You are being notified, Please reply in this channel {interaction.channel.mention}", color=discord.Color.yellow())
        
        user = bot.get_user(data["user_id"])
        if user:
            try:
                await user.send(embed=embed)
                success_embed = discord.Embed(description=f"<:tick:{CIRCLE_TICK_EMOJI_ID}> User has been notified", color=discord.Color.green())
                await interaction.response.send_message(embed=success_embed, ephemeral=True)
            except:
                error_embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Could not DM the user. They might have DMs closed.", color=discord.Color.red())
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
        else:
            error_embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Could not find the user.", color=discord.Color.red())
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id: int):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id
    
    @discord.ui.button(emoji="🎉", label="Enter Giveaway", style=discord.ButtonStyle.green, custom_id="enter_giveaway")
    async def enter_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        giveaway = giveaway_data.get(self.giveaway_id)
        if not giveaway or giveaway["ended"]:
            embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> This giveaway has ended!", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if interaction.user.id in giveaway["participants"]:
            embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> You have already entered this giveaway!", color=discord.Color.orange())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        giveaway["participants"].append(interaction.user.id)
        embed = discord.Embed(description=f"<:tick:{CIRCLE_TICK_EMOJI_ID}> Successfully entered the giveaway!", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def send_ticket_panel():
    try:
        channel = bot.get_channel(config.PANEL_CHANNEL_ID)
        if not channel:
            print(f"Error: Could not find channel with ID {config.PANEL_CHANNEL_ID}")
            return
        
        if not channel.permissions_for(channel.guild.me).send_messages:
            print(f"Error: Bot doesn't have permission to send messages in channel {config.PANEL_CHANNEL_ID}")
            return
        
        async for message in channel.history(limit=10):
            if message.author == bot.user and message.embeds:
                for embed in message.embeds:
                    if embed.title and "Welcome to tickets!" in embed.title:
                        print("Ticket panel already exists in channel")
                        return
        
        embed = discord.Embed(title=f"<:newsy:{NEWS_EMOJI_ID}> **Welcome to tickets!**", color=discord.Color.blue())
        line_emoji = f"<:rockety:{ROCKET_EMOJI_ID}>"
        embed.add_field(name="", value=f"{line_emoji} Please read our Terms of service before opening a ticket.\n{line_emoji} Please wait patiently until a owner responds to your ticket.\n{line_emoji} (By buying a product you are automatically agreeing to our terms of service)", inline=False)
        embed.add_field(name="", value="━━━━━━━━━━━━━━━━━━\n**Click the button below to select a ticket type:**\n{line_emoji} Make a purchase ticket to purchase\n{line_emoji} Make a support ticket for support", inline=False)
        
        view = TicketView()
        await channel.send(embed=embed, view=view)
        print(f"Ticket panel sent to channel {config.PANEL_CHANNEL_ID}")
        
    except Exception as e:
        print(f"Error sending ticket panel: {e}")

@tasks.loop(seconds=30)
async def check_giveaways():
    current_time = datetime.datetime.now()
    
    for giveaway_id, giveaway in list(giveaway_data.items()):
        if not giveaway["ended"] and current_time >= giveaway["end_time"]:
            giveaway["ended"] = True
            
            channel = bot.get_channel(giveaway["channel_id"])
            if not channel:
                continue
            
            try:
                message = await channel.fetch_message(giveaway["message_id"])
            except:
                continue
            
            participants = giveaway["participants"]
            if not participants:
                embed = discord.Embed(title=f"<:taday:{CONFETTI_EMOJI_ID}> **Giveaway Ended** <:taday:{CONFETTI_EMOJI_ID}>", description=f"<:gift:{GIVEAWAY_GIFT_EMOJI_ID}> **{giveaway['prize']}**\n\nNo one entered the giveaway!", color=discord.Color.red())
                await message.edit(embed=embed, view=None)
                continue
            
            winners_count = min(giveaway["winners"], len(participants))
            winners = random.sample(participants, winners_count)
            
            winners_mention = ", ".join([f"<@{winner_id}>" for winner_id in winners])
            
            embed = discord.Embed(title=f"<:taday:{CONFETTI_EMOJI_ID}> **Giveaway Ended** <:taday:{CONFETTI_EMOJI_ID}>", color=discord.Color.red())
            description = f"<:gift:{GIVEAWAY_GIFT_EMOJI_ID}> **{giveaway['prize']}**\n\n"
            description += f"<:time:{GIVEAWAY_TIME_EMOJI_ID}> **Ended at:** <t:{int(giveaway['end_time'].timestamp())}:F>\n\n"
            description += f"<:18690member:{GIVEAWAY_MEMBER_EMOJI_ID}> **Winners:** {winners_mention}\n\n"
            description += f"<:keyy:{GIVEAWAY_KEY_EMOJI_ID}> **Hosted by:** <@{giveaway['host_id']}>\n\n"
            
            if giveaway["image_url"]:
                embed.set_image(url=giveaway["image_url"])
            
            embed.description = description
            embed.set_footer(text=f"<:ticky:{SQUARE_TICK_EMOJI_ID}> Giveaway ID: {giveaway_id} • Ended")
            
            await message.edit(embed=embed, view=None)
            
            winner_embed = discord.Embed(title=f"<:taday:{CONFETTI_EMOJI_ID}> **Congratulations!** <:taday:{CONFETTI_EMOJI_ID}>", description=f"<:taday:{CONFETTI_EMOJI_ID}> Congratulations {winners_mention}! You have won **{giveaway['prize']}**!\n\n<:infoey:{INFO_EMOJI_ID}> Please dm or make a ticket to claim your prize!", color=discord.Color.gold())
            await channel.send(embed=winner_embed)
            
            giveaway["winners"] = winners

async def fetch_json(session, url):
    async with session.get(url) as response:
        return await response.json()

async def get_basic_balance(address: str):
    address = address.strip()
    
    if address.startswith("0x") and len(address) == 42:
        chain = "ethereum"
    elif address.startswith("bc1") or address.startswith("1") or address.startswith("3"):
        chain = "bitcoin"
    elif address.lower().startswith("ltc1") or address.startswith("L") or address.startswith("M"):
        chain = "litecoin"
    else:
        chain = "unknown"
    
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        if chain == "bitcoin":
            try:
                url = f"https://api.blockchair.com/bitcoin/dashboards/address/{address}"
                data = await fetch_json(session, url)
                info = data["data"][address]["address"]
                confirmed = int(info.get("balance", 0))
                unconfirmed = int(info.get("unconfirmed_balance", 0))
                received = int(info.get("received", 0))
                total = confirmed + unconfirmed
                return chain, total / 1e8, unconfirmed / 1e8, received / 1e8, "Source: Blockchair"
            except:
                return chain, None, None, None, "Error fetching Bitcoin balance"
        
        elif chain == "ethereum":
            try:
                url = f"https://api.blockchair.com/ethereum/dashboards/address/{address}"
                data = await fetch_json(session, url)
                info = data["data"][address]["address"]
                confirmed = int(info.get("balance", 0))
                unconfirmed = int(info.get("unconfirmed_balance", 0))
                received = int(info.get("received", 0))
                total = confirmed + unconfirmed
                return chain, total / 1e18, unconfirmed / 1e18, received / 1e18, "Source: Blockchair"
            except:
                return chain, None, None, None, "Error fetching Ethereum balance"
        
        elif chain == "litecoin":
            try:
                url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}/balance"
                data = await fetch_json(session, url)
                balance = float(data.get("balance", 0)) / 1e8
                unconfirmed = float(data.get("unconfirmed_balance", 0)) / 1e8
                received = float(data.get("total_received", 0)) / 1e8
                return chain, balance + unconfirmed, unconfirmed, received, "Source: BlockCypher"
            except:
                return chain, None, None, None, "Error fetching Litecoin balance"
        
        else:
            return chain, None, None, None, "Unsupported address format"

@bot.tree.command(name="gstart", description="Start a giveaway")
@app_commands.describe(
    prize="The prize for the giveaway",
    duration="Duration (e.g., 1h, 30m, 2d, 1w, 1M)",
    winners="Number of winners",
    image="Optional image URL for the giveaway"
)
@app_commands.default_permissions(manage_messages=True)
async def gstart(interaction: discord.Interaction, prize: str, duration: str, winners: int, image: Optional[str] = None):
    global next_giveaway_id
    
    try:
        duration = duration.lower().strip()
        if duration.endswith('s'):
            seconds = int(duration[:-1])
            end_time = datetime.datetime.now() + timedelta(seconds=seconds)
            update_interval = "second" if seconds < 60 else "minute"
        elif duration.endswith('m'):
            minutes = int(duration[:-1])
            end_time = datetime.datetime.now() + timedelta(minutes=minutes)
            update_interval = "second" if minutes < 1 else "minute"
        elif duration.endswith('h'):
            hours = int(duration[:-1])
            end_time = datetime.datetime.now() + timedelta(hours=hours)
            update_interval = "minute" if hours < 24 else "hour"
        elif duration.endswith('d'):
            days = int(duration[:-1])
            end_time = datetime.datetime.now() + timedelta(days=days)
            update_interval = "hour" if days < 7 else "day"
        elif duration.endswith('w'):
            weeks = int(duration[:-1])
            end_time = datetime.datetime.now() + timedelta(weeks=weeks)
            update_interval = "day" if weeks < 4 else "week"
        elif duration.endswith('mo') or duration.endswith('month'):
            months = int(duration[:-2] if duration.endswith('mo') else duration[:-5])
            end_time = datetime.datetime.now() + timedelta(days=months*30)
            update_interval = "week"
        else:
            hours = int(duration)
            end_time = datetime.datetime.now() + timedelta(hours=hours)
            update_interval = "minute" if hours < 24 else "hour"
    except ValueError:
        embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Invalid duration format! Use like: 30s, 10m, 2h, 3d, 1w, 1mo", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if winners < 1:
        embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Number of winners must be at least 1!", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    giveaway_id = next_giveaway_id
    next_giveaway_id += 1
    
    giveaway_data[giveaway_id] = {
        "prize": prize,
        "end_time": end_time,
        "winners": winners,
        "image_url": image,
        "host_id": interaction.user.id,
        "channel_id": interaction.channel_id,
        "message_id": None,
        "participants": [],
        "winners": [],
        "ended": False,
        "update_interval": update_interval,
        "last_update": datetime.datetime.now()
    }
    
    embed = discord.Embed(
        title="🎉 **GIVEAWAY** 🎉",
        color=discord.Color.green()
    )
    
    time_remaining = end_time - datetime.datetime.now()
    seconds_remaining = int(time_remaining.total_seconds())
    
    if seconds_remaining < 60:
        time_str = f"{seconds_remaining}s"
    elif seconds_remaining < 3600:
        time_str = f"{seconds_remaining // 60}m"
    elif seconds_remaining < 86400:
        time_str = f"{seconds_remaining // 3600}h"
    elif seconds_remaining < 604800:
        time_str = f"{seconds_remaining // 86400}d"
    else:
        time_str = f"{seconds_remaining // 604800}w"
    
    description = f"**<:gift:{GIVEAWAY_GIFT_EMOJI_ID}> Prize : {prize}**\n"
    description += f"<:time:{GIVEAWAY_TIME_EMOJI_ID}> Ending in : {time_str}\n"
    description += f"<:18690member:{GIVEAWAY_MEMBER_EMOJI_ID}> Participants : 0\n"
    description += f"<a:redarrow:{RED_ARROW_EMOJI_ID}> Winners : {winners}\n"
    description += f"<:keyy:{GIVEAWAY_KEY_EMOJI_ID}> Hosted by : <@{interaction.user.id}>\n\n"
    
    if image:
        embed.set_image(url=image)
    
    embed.description = description
    embed.set_footer(text=f"Giveaway ID: {giveaway_id}")
    
    view = GiveawayView(giveaway_id=giveaway_id)
    message = await interaction.channel.send(embed=embed, view=view)
    
    giveaway_data[giveaway_id]["message_id"] = message.id
    
    bot.loop.create_task(update_giveaway_timer(giveaway_id, message, update_interval))
    
    embed = discord.Embed(description=f"<:tick:{CIRCLE_TICK_EMOJI_ID}> Giveaway started! Giveaway ID: {giveaway_id}", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def update_giveaway_timer(giveaway_id: int, message: discord.Message, interval: str):
    giveaway = giveaway_data.get(giveaway_id)
    if not giveaway:
        return
    
    while not giveaway["ended"]:
        try:
            time_remaining = giveaway["end_time"] - datetime.datetime.now()
            seconds_remaining = int(time_remaining.total_seconds())
            
            if seconds_remaining <= 0:
                giveaway["ended"] = True
                break
            
            if seconds_remaining < 60:
                time_str = f"{seconds_remaining}s"
                wait_time = 1
            elif seconds_remaining < 3600:
                time_str = f"{seconds_remaining // 60}m {seconds_remaining % 60}s"
                wait_time = 60 if interval == "minute" else 1
            elif seconds_remaining < 86400:
                hours = seconds_remaining // 3600
                minutes = (seconds_remaining % 3600) // 60
                time_str = f"{hours}h {minutes}m"
                wait_time = 3600 if interval == "hour" else 60
            elif seconds_remaining < 604800:
                days = seconds_remaining // 86400
                hours = (seconds_remaining % 86400) // 3600
                time_str = f"{days}d {hours}h"
                wait_time = 86400 if interval == "day" else 3600
            else:
                weeks = seconds_remaining // 604800
                days = (seconds_remaining % 604800) // 86400
                time_str = f"{weeks}w {days}d"
                wait_time = 604800 if interval == "week" else 86400
            
            participants_count = len(giveaway["participants"])
            
            embed = message.embeds[0] if message.embeds else discord.Embed(title="🎉 **GIVEAWAY** 🎉", color=discord.Color.green())
            
            description = f"**<:gift:{GIVEAWAY_GIFT_EMOJI_ID}> Prize : {giveaway['prize']}**\n"
            description += f"<:time:{GIVEAWAY_TIME_EMOJI_ID}> Ending in : {time_str}\n"
            description += f"<:18690member:{GIVEAWAY_MEMBER_EMOJI_ID}> Participants : {participants_count}\n"
            description += f"<a:redarrow:{RED_ARROW_EMOJI_ID}> Winners : {giveaway['winners']}\n"
            description += f"<:keyy:{GIVEAWAY_KEY_EMOJI_ID}> Hosted by : <@{giveaway['host_id']}>\n\n"
            
            if giveaway["image_url"]:
                embed.set_image(url=giveaway["image_url"])
            
            embed.description = description
            embed.set_footer(text=f"Giveaway ID: {giveaway_id}")
            
            await message.edit(embed=embed)
            
            await asyncio.sleep(wait_time)
            
        except Exception as e:
            print(f"Error updating giveaway timer: {e}")
            break

@bot.tree.command(name="greroll", description="Reroll a giveaway winner")
@app_commands.describe(giveaway_id="The ID of the giveaway to reroll")
@app_commands.default_permissions(manage_messages=True)
async def greroll(interaction: discord.Interaction, giveaway_id: int):
    giveaway = giveaway_data.get(giveaway_id)
    
    if not giveaway:
        embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Giveaway not found!", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if not giveaway["ended"]:
        embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> This giveaway hasn't ended yet!", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    participants = giveaway["participants"]
    if not participants:
        embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> No participants in this giveaway!", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    winners_count = min(giveaway["winners"], len(participants))
    new_winners = random.sample(participants, winners_count)
    
    winners_mention = ", ".join([f"<@{winner_id}>" for winner_id in new_winners])
    
    embed = discord.Embed(title=f"<:taday:{CONFETTI_EMOJI_ID}> **Giveaway Rerolled!** <:taday:{CONFETTI_EMOJI_ID}>", description=f"<:taday:{CONFETTI_EMOJI_ID}> Congratulations {winners_mention}! You have won **{giveaway['prize']}** in the reroll!\n\n<:infoey:{INFO_EMOJI_ID}> Please dm or make a ticket to claim your prize!", color=discord.Color.gold())
    
    channel = bot.get_channel(giveaway["channel_id"])
    if channel:
        await channel.send(embed=embed)
    
    embed = discord.Embed(description=f"<:tick:{CIRCLE_TICK_EMOJI_ID}> Giveaway rerolled! New winners: {winners_mention}", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="bal", description="Check cryptocurrency balance for an address")
@app_commands.describe(address="The cryptocurrency address to check")
async def bal(interaction: discord.Interaction, address: str):
    await interaction.response.defer(thinking=True)
    
    chain, total_bal, unconf_bal, total_recv, note = await get_basic_balance(address)
    
    if total_bal is None:
        embed = discord.Embed(title=f"<a:no:{NO_EMOJI_ID}> Balance Check Failed", description=f"**<:linky:{LINK_EMOJI_ID}> Address:** `{address}`\n\n{note}\n\nPlease check the address format and try again.", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return
    
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        try:
            asset_id = ASSET_MAP.get(chain.lower())
            if asset_id:
                price_data = await fetch_json(session, COINGECKO_SIMPLE.format(ids=asset_id))
                usd_price = price_data.get(asset_id, {}).get("usd")
            else:
                usd_price = None
        except:
            usd_price = None
    
    unit_map = {"bitcoin": "BTC", "ethereum": "ETH", "litecoin": "LTC", "solana": "SOL", "dogecoin": "DOGE"}
    unit = unit_map.get(chain, chain.upper())
    
    embed = discord.Embed(title=f"<:__:{DOLLAR_EMOJI_ID}> {unit} Balance", color=discord.Color.green(), timestamp=interaction.created_at)
    embed.add_field(name=f"<:linky:{LINK_EMOJI_ID}> Address", value=f"`{address}`", inline=False)
    embed.add_field(name=f"<:service:{SERVICE_EMOJI_ID}> Chain", value=chain.capitalize(), inline=True)
    
    if usd_price:
        total_usd = total_bal * usd_price
        unconf_usd = unconf_bal * usd_price if unconf_bal else 0
        recv_usd = total_recv * usd_price
        
        embed.add_field(name=f"<:__:{DOLLAR_EMOJI_ID}> Total Balance", value=f"**{total_bal:.8f} {unit}**\n≈ **${total_usd:,.2f} USD**", inline=False)
        if unconf_bal > 0:
            embed.add_field(name=f"<:time:{TIME_EMOJI_ID}> Unconfirmed", value=f"**{unconf_bal:.8f} {unit}**\n≈ **${unconf_usd:,.2f} USD**", inline=True)
        embed.add_field(name=f"<:newsy:{NEWS_EMOJI_ID}> Total Received", value=f"**{total_recv:.8f} {unit}**\n≈ **${recv_usd:,.2f} USD**", inline=False)
        embed.add_field(name=f"<:__:{DOLLAR_EMOJI_ID}> Current Price", value=f"**${usd_price:,.2f} USD/{unit}**", inline=True)
    else:
        embed.add_field(name=f"<:__:{DOLLAR_EMOJI_ID}> Total Balance", value=f"**{total_bal:.8f} {unit}**", inline=False)
        if unconf_bal > 0:
            embed.add_field(name=f"<:time:{TIME_EMOJI_ID}> Unconfirmed", value=f"**{unconf_bal:.8f} {unit}**", inline=True)
        embed.add_field(name=f"<:newsy:{NEWS_EMOJI_ID}> Total Received", value=f"**{total_recv:.8f} {unit}**", inline=False)
    
    embed.add_field(name=f"<:infoey:{INFO_EMOJI_ID}> Note", value=note, inline=False)
    embed.set_footer(text=f"<:ticky:{SQUARE_TICK_EMOJI_ID}> Balance Check")
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="price", description="Check cryptocurrency price")
@app_commands.describe(asset="The cryptocurrency to check (btc, eth, sol, doge, usdt, bnb, xrp, ltc)")
async def price(interaction: discord.Interaction, asset: str):
    asset_key = asset.strip().lower()
    cg_id = ASSET_MAP.get(asset_key)
    
    if not cg_id:
        embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Unknown asset. Try: btc, eth, sol, doge, usdt, bnb, xrp, ltc", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    await interaction.response.defer()
    
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        try:
            data = await fetch_json(session, COINGECKO_SIMPLE.format(ids=cg_id))
            usd = data.get(cg_id, {}).get("usd")
            
            if usd is None:
                embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Could not fetch price.", color=discord.Color.red())
                await interaction.followup.send(embed=embed)
                return
            
            embed = discord.Embed(title=f"<:__:{DOLLAR_EMOJI_ID}> {asset_key.upper()} Price", description=f"**1 {asset_key.upper()} = ${usd:,.2f} USD**", color=discord.Color.green(), timestamp=interaction.created_at)
            embed.set_footer(text=f"<:ticky:{SQUARE_TICK_EMOJI_ID}> Price Check")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Error fetching price: {str(e)}", color=discord.Color.red())
            await interaction.followup.send(embed=embed)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guild(s)')
    
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Tickets"))
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    
    try:
        bot.add_view(TicketView())
        bot.add_view(GiveawayView(giveaway_id=0))
        print("Persistent views added")
    except Exception as e:
        print(f"Error adding persistent views: {e}")
    
    check_giveaways.start()
    print("Giveaway checker started")
    
    await send_ticket_panel()

@bot.tree.command(name="resend_panel", description="Resend the ticket panel")
@app_commands.default_permissions(administrator=True)
async def resend_panel(interaction: discord.Interaction):
    try:
        channel = bot.get_channel(config.PANEL_CHANNEL_ID)
        if not channel:
            embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Could not find panel channel", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(title=f"<:newsy:{NEWS_EMOJI_ID}> **Welcome to tickets!**", color=discord.Color.blue(), timestamp=interaction.created_at)
        line_emoji = f"<:rockety:{ROCKET_EMOJI_ID}>"
        embed.add_field(name="", value=f"{line_emoji} Please read our Terms of service before opening a ticket.\n{line_emoji} Please wait patiently until a owner responds to your ticket.\n{line_emoji} (By buying a product you are automatically agreeing to our terms of service)", inline=False)
        embed.add_field(name="", value="━━━━━━━━━━━━━━━━━━\n**Click the button below to select a ticket type:**\n{line_emoji} Make a purchase ticket to purchase\n{line_emoji} Make a support ticket for support", inline=False)
        
        view = TicketView()
        await channel.send(embed=embed, view=view)
        
        success_embed = discord.Embed(description=f"<:tick:{CIRCLE_TICK_EMOJI_ID}> Ticket panel resent to <#{config.PANEL_CHANNEL_ID}>", color=discord.Color.green())
        await interaction.response.send_message(embed=success_embed, ephemeral=True)
        
    except Exception as e:
        embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Failed to resend panel", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="send", description="Send a message in an embed")
@app_commands.describe(text="The text to send", channel="The channel to send the message in", title="Optional title for the embed")
@app_commands.default_permissions(manage_messages=True)
async def send(interaction: discord.Interaction, text: str, channel: discord.TextChannel, title: Optional[str] = None):
    embed = discord.Embed(description=text, color=discord.Color.blue(), timestamp=interaction.created_at)
    if title: embed.title = title
    embed.set_footer(text=f"<:ticky:{SQUARE_TICK_EMOJI_ID}> Sent by {interaction.user}")
    await channel.send(embed=embed)
    success_embed = discord.Embed(description=f"<:tick:{CIRCLE_TICK_EMOJI_ID}> Message sent to {channel.mention}", color=discord.Color.green())
    await interaction.response.send_message(embed=success_embed, ephemeral=True)

@bot.tree.command(name="nuke", description="Delete all messages in a channel")
@app_commands.describe(channel="The channel to nuke", text="Optional text to send after nuking")
@app_commands.default_permissions(manage_channels=True)
async def nuke(interaction: discord.Interaction, channel: discord.TextChannel, text: Optional[str] = None):
    confirm_embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Are you sure you want to nuke {channel.mention}? This action cannot be undone!", color=discord.Color.orange())
    
    class ConfirmView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
        
        @discord.ui.button(label="Confirm", style=discord.ButtonStyle.red)
        async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != interaction.user.id:
                embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> You cannot confirm this action.", color=discord.Color.red())
                await button_interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            try:
                new_channel = await channel.clone()
                await channel.delete()
                
                embed = discord.Embed(title=f"<:newsy:{NEWS_EMOJI_ID}> **Channel nuked by <@{button_interaction.user.id}>**", color=discord.Color.red(), timestamp=button_interaction.created_at)
                if text: embed.add_field(name="", value=text, inline=False)
                embed.set_footer(text="<:ticky:{SQUARE_TICK_EMOJI_ID}> Channel nuked")
                await new_channel.send(embed=embed)
                
                success_embed = discord.Embed(description=f"<:tick:{CIRCLE_TICK_EMOJI_ID}> Channel nuked and recreated as {new_channel.mention}", color=discord.Color.green())
                await button_interaction.response.edit_message(embed=success_embed, view=None)
                
            except Exception as e:
                embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Failed to nuke channel", color=discord.Color.red())
                await button_interaction.response.edit_message(embed=embed, view=None)
        
        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
        async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != interaction.user.id:
                embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> You cannot cancel this action.", color=discord.Color.red())
                await button_interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Nuke cancelled", color=discord.Color.gray())
            await button_interaction.response.edit_message(embed=embed, view=None)
    
    await interaction.response.send_message(embed=confirm_embed, view=ConfirmView(), ephemeral=True)

@bot.tree.command(name="dm", description="DM a user or role")
@app_commands.describe(target="The user or role to DM", text="The text to send", title="Optional title for the embed")
@app_commands.default_permissions(administrator=True)
async def dm(interaction: discord.Interaction, target: Union[discord.Member, discord.Role], text: str, title: Optional[str] = None):
    embed = discord.Embed(description=text, color=discord.Color.blue(), timestamp=interaction.created_at)
    if title: embed.title = title
    embed.set_footer(text=f"<:ticky:{SQUARE_TICK_EMOJI_ID}> From {interaction.guild.name}")
    
    if isinstance(target, discord.Role):
        count = 0
        failed = 0
        
        progress_embed = discord.Embed(description=f"<:bell:{BELL_EMOJI_ID}> Sending DMs to {len(target.members)} members with the {target.mention} role...", color=discord.Color.yellow())
        await interaction.response.send_message(embed=progress_embed, ephemeral=True)
        
        for member in target.members:
            if not member.bot:
                try:
                    await member.send(embed=embed)
                    count += 1
                    await asyncio.sleep(1)
                except:
                    failed += 1
                await asyncio.sleep(0.5)
        
        result_embed = discord.Embed(description=f"<:tick:{CIRCLE_TICK_EMOJI_ID}> Message sent to {count} members with the {target.mention} role\nFailed to send to {failed} members", color=discord.Color.green())
        await interaction.edit_original_response(embed=result_embed)
    else:
        try:
            await target.send(embed=embed)
            success_embed = discord.Embed(description=f"<:tick:{CIRCLE_TICK_EMOJI_ID}> Message sent to {target.mention}", color=discord.Color.green())
            await interaction.response.send_message(embed=success_embed, ephemeral=True)
        except:
            embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> Could not DM {target.mention}. They might have DMs closed.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ticket_info", description="Get information about a ticket")
@app_commands.default_permissions(manage_channels=True)
async def ticket_info(interaction: discord.Interaction):
    if not isinstance(interaction.channel, discord.TextChannel):
        embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> This command can only be used in text channels", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    ticket_info = None
    for ticket_id, data in ticket_data.items():
        if data.get("channel_id") == interaction.channel.id:
            ticket_info = data
            ticket_info["id"] = ticket_id
            break
    
    if not ticket_info:
        embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> This is not a ticket channel or ticket data was not found", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(title=f"<:infoey:{INFO_EMOJI_ID}> **Ticket Information**", color=discord.Color.blue(), timestamp=ticket_info["created_at"])
    embed.add_field(name=f"<:keyy:{KEY_EMOJI_ID}> Ticket ID", value=f"```{ticket_info['id']}```", inline=False)
    embed.add_field(name=f"<:18690member:{MEMBER_EMOJI_ID}> User", value=f"<@{ticket_info['user_id']}>\n```{ticket_info['user_name']}```", inline=True)
    embed.add_field(name=f"<:ticky:{SQUARE_TICK_EMOJI_ID}> Ticket Type", value=f"```{ticket_info['type']}```", inline=True)
    embed.add_field(name=f"<:time:{TIME_EMOJI_ID}> Created", value=f"<t:{int(ticket_info['created_at'].timestamp())}:R>", inline=True)
    
    if ticket_info["type"] == "Purchase":
        embed.add_field(name=f"<:shop:{SHOP_EMOJI_ID}> Product", value=f"```{ticket_info['product']}```", inline=False)
        embed.add_field(name=f"<:__:{DOLLAR_EMOJI_ID}> Payment Method", value=f"```{ticket_info['payment']}```", inline=False)
    else:
        embed.add_field(name=f"<:shop:{SHOP_EMOJI_ID}> Where", value=f"```{ticket_info['where']}```", inline=False)
        desc = ticket_info['description']
        embed.add_field(name=f"<:infoey:{INFO_EMOJI_ID}> Description", value=f"```{desc[:500]}...```" if len(desc) > 500 else f"```{desc}```", inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_guild_channel_delete(channel):
    for ticket_id, data in list(ticket_data.items()):
        if data.get("channel_id") == channel.id:
            del ticket_data[ticket_id]
            print(f"Cleaned up ticket data for deleted channel: {ticket_id}")
            break

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> You don't have permission to use this command", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=5)
    else:
        embed = discord.Embed(description=f"<a:no:{NO_EMOJI_ID}> An error occurred", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=10)

if __name__ == "__main__":
    print("Starting Tickets Bot...")
    try:
        bot.run(config.TOKEN)
    except Exception as e:
        print(f"Failed to start bot: {e}")
