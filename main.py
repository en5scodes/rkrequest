import discord
from discord.ext import commands
from discord import ui
import asyncio
from datetime import datetime
from config import TOKEN, TICKET_CATEGORY_ID, STAFF_ROLE_NAME, TICKET_LOGS_CHANNEL
from ticket_embed import create_welcome_embed

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Store ticket questions and answers temporarily
ticket_data = {}

class TicketQuestions(ui.Modal):
    def __init__(self, ticket_type):
        super().__init__(title=f"{ticket_type.title()} Ticket Questions")
        self.ticket_type = ticket_type
        
        if ticket_type == "purchase":
            self.product = ui.TextInput(
                label="What is the product you will be purchasing?",
                placeholder="e.g., VIP rank, Custom bot, etc.",
                style=discord.TextStyle.short,
                required=True,
                max_length=100
            )
            self.add_item(self.product)
            
            self.payment = ui.TextInput(
                label="What is your payment method?",
                placeholder="e.g., Crypto, Robux, PayPal, etc.",
                style=discord.TextStyle.short,
                required=True,
                max_length=50
            )
            self.add_item(self.payment)
        else:  # support ticket
            self.issue = ui.TextInput(
                label="What is the issue with your order?",
                placeholder="e.g., didn't receive product, wrong item, defective product, etc.",
                style=discord.TextStyle.paragraph,
                required=True,
                max_length=500
            )
            self.add_item(self.issue)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Store the answers
        ticket_data[interaction.user.id] = {
            'type': self.ticket_type,
            'answers': {}
        }
        
        if self.ticket_type == "purchase":
            ticket_data[interaction.user.id]['answers'] = {
                'Product': self.product.value,
                'Payment Method': self.payment.value
            }
        else:
            ticket_data[interaction.user.id]['answers'] = {
                'Order Issue': self.issue.value
            }
        
        # Create the ticket channel
        await self.create_ticket_channel(interaction)
    
    async def create_ticket_channel(self, interaction):
        guild = interaction.guild
        member = interaction.user
        
        # Get the ticket category
        category = guild.get_channel(TICKET_CATEGORY_ID)
        if not category:
            category = await guild.create_category(name="Tickets")
        
        # Get ticket number
        existing_tickets = [c for c in category.channels if self.ticket_type in c.name]
        ticket_number = len(existing_tickets) + 1
        
        # Create channel name with username and ticket number
        username = member.name.replace(" ", "-").lower()
        channel_name = f"{username}-{ticket_number:03d}"
        
        # Setup permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        
        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        # Create channel
        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"{self.ticket_type.title()} Ticket | Opened by: {member.display_name} | ID: {member.id}"
        )
        
        # Send welcome message
        welcome_embed = create_welcome_embed(self.ticket_type)
        await ticket_channel.send(embed=welcome_embed)
        
        # Create answers summary embed
        answers_embed = discord.Embed(
            title=f"{self.ticket_type.title()} Ticket Information",
            color=discord.Color.blue() if self.ticket_type == "support" else discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        for question, answer in ticket_data[interaction.user.id]['answers'].items():
            answers_embed.add_field(
                name=question,
                value=answer,
                inline=False
            )
        
        answers_embed.set_footer(text=f"Ticket #{ticket_number} | Opened by: {member.display_name}")
        await ticket_channel.send(embed=answers_embed)
        
        # Ping staff
        if staff_role:
            await ticket_channel.send(f"{staff_role.mention} A new {self.ticket_type} ticket has been created.")
        
        # Log ticket creation
        log_channel = discord.utils.get(guild.text_channels, name=TICKET_LOGS_CHANNEL)
        if log_channel:
            log_embed = discord.Embed(
                title="Ticket Created",
                description=f"**Type:** {self.ticket_type.title()}\n**User:** {member.mention}\n**Channel:** {ticket_channel.mention}\n**Ticket #:** {ticket_number}",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            await log_channel.send(embed=log_embed)
        
        # Send confirmation to user
        confirm_embed = discord.Embed(
            title="Ticket Created",
            description=f"Your {self.ticket_type} ticket has been created: {ticket_channel.mention}",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)
        
        # Clean up stored data
        del ticket_data[interaction.user.id]

class TicketTypeSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Support", description="Order issues, refunds, or general support"),
            discord.SelectOption(label="Purchase", description="Purchase products or inquire about products")
        ]
        super().__init__(placeholder="Select a ticket type...", min_values=1, max_values=1, options=options)
    
    async def callback(self, interaction: discord.Interaction):
        ticket_type = self.values[0].lower()
        
        # Open modal with questions
        modal = TicketQuestions(ticket_type)
        await interaction.response.send_modal(modal)

class TicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # Add the dropdown directly to the view
        self.add_item(TicketTypeSelect())

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is ready!')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="!help"))

@bot.command(name="ticket")
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx):
    """Setup the ticket system in the current channel"""
    embed = discord.Embed(
        title="Ticket System",
        description="Select an option from the dropdown below to create a ticket!",
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
    
    view = TicketView()
    await ctx.send(embed=embed, view=view)

@bot.command(name="close")
async def close_ticket(ctx):
    """Close the current ticket"""
    # Check if channel is a ticket channel (has username-number format)
    if ctx.channel.category and ctx.channel.category.id == TICKET_CATEGORY_ID:
        embed = discord.Embed(
            title="Closing Ticket",
            description="This ticket will be closed in 5 seconds...",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        await asyncio.sleep(5)
        await ctx.channel.delete()

@bot.command(name="send")
@commands.has_permissions(administrator=True)
async def send_embed(ctx, channel: discord.TextChannel, *, text):
    """Send an embed to a specific channel"""
    embed = discord.Embed(
        title="Announcement",
        description=text,
        color=discord.Color.blue()
    )
    await channel.send(embed=embed)
    
    confirm_embed = discord.Embed(
        title="Message Sent",
        description=f"Embed sent to {channel.mention}",
        color=discord.Color.green()
    )
    await ctx.send(embed=confirm_embed)

@bot.command(name="adduser")
async def add_user(ctx, member: discord.Member):
    """Add a user to the current ticket"""
    if ctx.channel.category and ctx.channel.category.id == TICKET_CATEGORY_ID:
        await ctx.channel.set_permissions(member, read_messages=True, send_messages=True)
        embed = discord.Embed(
            title="User Added",
            description=f"{member.mention} has been added to the ticket",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

@bot.command(name="removeuser")
async def remove_user(ctx, member: discord.Member):
    """Remove a user from the current ticket"""
    if ctx.channel.category and ctx.channel.category.id == TICKET_CATEGORY_ID:
        await ctx.channel.set_permissions(member, overwrite=None)
        embed = discord.Embed(
            title="User Removed",
            description=f"{member.mention} has been removed from the ticket",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

@bot.command(name="rename")
async def rename_ticket(ctx, *, new_name):
    """Rename the current ticket channel"""
    if ctx.channel.category and ctx.channel.category.id == TICKET_CATEGORY_ID:
        old_name = ctx.channel.name
        # Remove spaces and special characters
        new_name = new_name.replace(" ", "-").lower()
        await ctx.channel.edit(name=new_name)
        embed = discord.Embed(
            title="Channel Renamed",
            description=f"Channel renamed from `{old_name}` to `{new_name}`",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

@bot.command(name="help")
async def help_command(ctx):
    """Show all available commands"""
    embed = discord.Embed(
        title="Bot Commands",
        description="Here are all the available commands:",
        color=discord.Color.blue()
    )
    
    # General Commands
    embed.add_field(
        name="General Commands",
        value=(
            "`!help` - Shows this message\n"
            "`!ticket` - Setup ticket system (Admin only)\n"
            "`!send #channel <text>` - Send embed to channel (Admin only)"
        ),
        inline=False
    )
    
    # Ticket Commands
    embed.add_field(
        name="Ticket Commands",
        value=(
            "`!close` - Close the current ticket\n"
            "`!adduser @user` - Add user to ticket\n"
            "`!removeuser @user` - Remove user from ticket\n"
            "`!rename <name>` - Rename ticket channel"
        ),
        inline=False
    )
    
    # How to use
    embed.add_field(
        name="How to Create a Ticket",
        value=(
            "1. Select 'Support' or 'Purchase' from the dropdown below\n"
            "2. Answer the questions in the popup form\n"
            "3. Your ticket will be created automatically"
        ),
        inline=False
    )
    
    embed.set_footer(text="For any issues, contact a staff member")
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="Permission Denied",
            description="You don't have permission to use this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="Missing Argument",
            description=f"Missing required argument: {error.param.name}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.ChannelNotFound):
        embed = discord.Embed(
            title="Channel Not Found",
            description="The specified channel could not be found.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MemberNotFound):
        embed = discord.Embed(
            title="Member Not Found",
            description="The specified member could not be found.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@setup_ticket.error
async def ticket_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="Permission Denied",
            description="You need administrator permissions to set up the ticket system.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

if __name__ == "__main__":
    bot.run(TOKEN)
