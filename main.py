import discord
from discord.ext import commands
from discord import ui
import asyncio
from config import TOKEN, TICKET_CATEGORY_ID, STAFF_ROLE_NAME, TICKET_LOGS_CHANNEL
from ticket_embed import create_ticket_embed, create_welcome_embed, create_question_embed, create_general_embed

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

class TicketTypeSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Support", description="Order issues, refunds, or general support"),
            discord.SelectOption(label="Purchase", description="Purchase products or inquire about products")
        ]
        super().__init__(placeholder="Select ticket type...", min_values=1, max_values=1, options=options)
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        ticket_type = self.values[0].lower()
        
        # Create ticket channel
        guild = interaction.guild
        member = interaction.user
        
        # Get the ticket category
        category = guild.get_channel(TICKET_CATEGORY_ID)
        
        if not category:
            # If category doesn't exist, create it
            category = await guild.create_category(name="Tickets")
        
        # Create ticket channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        
        # Add staff role if it exists
        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        # Create channel with sequential number
        ticket_number = len([c for c in category.channels if c.name.startswith(ticket_type)]) + 1
        channel_name = f"{ticket_type}-{ticket_number:03d}"
        
        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Ticket for {member.display_name} | {ticket_type.title()} Ticket"
        )
        
        # Send welcome message
        welcome_embed = create_welcome_embed(ticket_type)
        await ticket_channel.send(embed=welcome_embed)
        
        # Send questions after a short delay
        await asyncio.sleep(1)
        questions_embed = create_question_embed(ticket_type)
        await ticket_channel.send(embed=questions_embed)
        
        # Log ticket creation
        log_channel = discord.utils.get(guild.text_channels, name=TICKET_LOGS_CHANNEL)
        if log_channel:
            log_embed = create_general_embed(
                "Ticket Created",
                f"Type: {ticket_type.title()}\nUser: {member.mention}\nChannel: {ticket_channel.mention}",
                discord.Color.green()
            )
            await log_channel.send(embed=log_embed)
        
        # Send confirmation to user
        confirm_embed = create_general_embed(
            "Ticket Created",
            f"Your {ticket_type} ticket has been created: {ticket_channel.mention}",
            discord.Color.green()
        )
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)

class TicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="Purchase", style=discord.ButtonStyle.green)
    async def purchase_button(self, interaction: discord.Interaction, button: ui.Button):
        # Create dropdown for ticket type selection
        view = ui.View()
        view.add_item(TicketTypeSelect())
        
        embed = create_general_embed(
            "Ticket Type",
            "Please select the type of ticket you want to create:",
            discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is ready!')

@bot.command(name="ticket")
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx):
    """Setup the ticket system in the current channel"""
    embed = create_ticket_embed()
    view = TicketView()
    await ctx.send(embed=embed, view=view)
    
    # Send a separate message with support button
    support_view = ui.View()
    support_view.add_item(TicketTypeSelect())
    
    support_embed = create_general_embed(
        "Create a Ticket",
        "Click the button below to create a support or purchase ticket",
        discord.Color.blue()
    )
    await ctx.send(embed=support_embed, view=support_view)

@bot.command(name="close")
async def close_ticket(ctx):
    """Close the current ticket"""
    if any(name in ctx.channel.name for name in ["support-", "purchase-"]):
        await ctx.send(embed=create_general_embed(
            "Closing Ticket",
            "This ticket will be closed in 5 seconds...",
            discord.Color.red()
        ))
        await asyncio.sleep(5)
        await ctx.channel.delete()

@bot.command(name="send")
@commands.has_permissions(administrator=True)
async def send_embed(ctx, channel: discord.TextChannel, *, text):
    """Send an embed to a specific channel"""
    embed = create_general_embed("Announcement", text)
    await channel.send(embed=embed)
    await ctx.send(embed=create_general_embed(
        "Message Sent",
        f"Embed sent to {channel.mention}",
        discord.Color.green()
    ))

@bot.command(name="adduser")
async def add_user(ctx, member: discord.Member):
    """Add a user to the current ticket"""
    if any(name in ctx.channel.name for name in ["support-", "purchase-"]):
        await ctx.channel.set_permissions(member, read_messages=True, send_messages=True)
        embed = create_general_embed(
            "User Added",
            f"{member.mention} has been added to the ticket",
            discord.Color.green()
        )
        await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = create_general_embed(
            "Permission Denied",
            "You don't have permission to use this command.",
            discord.Color.red()
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = create_general_embed(
            "Missing Argument",
            f"Missing required argument: {error.param.name}",
            discord.Color.red()
        )
        await ctx.send(embed=embed)

# Error handler for the ticket command
@setup_ticket.error
async def ticket_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = create_general_embed(
            "Permission Denied",
            "You need administrator permissions to set up the ticket system.",
            discord.Color.red()
        )
        await ctx.send(embed=embed)

# Add support ticket button as well
class SupportTicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="Create Ticket", style=discord.ButtonStyle.primary)
    async def create_ticket_button(self, interaction: discord.Interaction, button: ui.Button):
        view = ui.View()
        view.add_item(TicketTypeSelect())
        
        embed = create_general_embed(
            "Ticket Type",
            "Please select the type of ticket you want to create:",
            discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)
