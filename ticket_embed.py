import discord

def create_ticket_embed():
    """Create the initial ticket embed with purchase button"""
    embed = discord.Embed(
        title="Ticket System",
        description="Click the button below to create a ticket!",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Support Ticket",
        value="For order issues, refunds, or general support",
        inline=False
    )
    embed.add_field(
        name="Purchase Ticket",
        value="To purchase products or inquire about products",
        inline=False
    )
    return embed

def create_welcome_embed(ticket_type="support"):
    """Create welcome embed for tickets"""
    if ticket_type == "purchase":
        title = "Purchase Ticket"
    else:
        title = "Support Ticket"
    
    embed = discord.Embed(
        title=title,
        description="Welcome! Please wait until a staff member comes to assist you. In the meantime, you can view our other products and see if you are interested.",
        color=discord.Color.green()
    )
    embed.set_footer(text="A staff member will be with you shortly.")
    return embed

def create_question_embed(ticket_type="support"):
    """Create question embed based on ticket type"""
    if ticket_type == "purchase":
        embed = discord.Embed(
            title="Purchase Questions",
            description="Please answer the following questions:",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="1. Product Inquiry",
            value="What is the product you will be purchasing?",
            inline=False
        )
        embed.add_field(
            name="2. Payment Method",
            value="What is your payment method? (e.g., Crypto, Robux, PayPal, etc.)",
            inline=False
        )
    else:  # support ticket
        embed = discord.Embed(
            title="Support Questions",
            description="Please describe your issue:",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="Order Issue",
            value="What is the issue with your order? (e.g., didn't receive product, wrong item, etc.)",
            inline=False
        )
    
    return embed

def create_general_embed(title, description, color=discord.Color.blue()):
    """Create a general embed for bot messages"""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    return embed
