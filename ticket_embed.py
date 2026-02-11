import discord

def create_welcome_embed(ticket_type="support"):
    """Create welcome embed for tickets"""
    if ticket_type == "purchase":
        title = "Purchase Ticket"
    else:
        title = "Support Ticket"
    
    embed = discord.Embed(
        title=title,
        description="Welcome! Please wait until a staff member comes to assist you. In the meantime, you can view our other products and see if you are interested.",
        color=discord.Color.green() if ticket_type == "support" else discord.Color.gold()
    )
    embed.set_footer(text="A staff member will be with you shortly.")
    return embed
