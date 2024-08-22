import discord
from discord.ext import commands
from discord import app_commands
import os
import json
from datetime import datetime
import pytz
from dotenv import load_dotenv

# Load environment variables from .envrc file
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Fetch and parse the GUILD_IDS from the environment
GUILD_IDS = os.getenv('GUILD_IDS', '').split(',')

# File path for storing birthdays and channels
DATA_FILE = "birthdays.json"

# Create a bot instance with minimal intents
intents = discord.Intents.default()
intents.guilds = True  # Required to access basic guild information

bot = commands.Bot(command_prefix='!', intents=intents)

# Data storage
servers_data = {}

# Load data from JSON file
def load_data():
    global servers_data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as file:
            servers_data = json.load(file)

# Save data to JSON file
def save_data():
    with open(DATA_FILE, "w") as file:
        json.dump(servers_data, file, indent=4)

# Load data when the bot starts
load_data()

# Create a pretty embed for messages
def create_embed(title: str, description: str) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
    return embed

# Define the /bday command group
class BirthdayGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="bday", description="Manage birthdays")

    @app_commands.command(name="remember", description="Remember a user's birthday")
    async def remember_birthday(self, interaction: discord.Interaction, month: int, day: int, year: int, user: discord.Member = None):
        user = user or interaction.user
        server_id = str(interaction.guild.id)

        if server_id not in servers_data:
            servers_data[server_id] = {"birthdays": {}, "channel_id": None}

        servers_data[server_id]["birthdays"][str(user.id)] = {
            'month': month,
            'day': day,
            'year': year,
            'username': str(user)
        }
        save_data()

        embed = create_embed(
            title="Birthday Remembered",
            description=f"Birthday for {user.mention} remembered: {month}/{day}/{year}."
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="forget", description="Forget a user's birthday")
    async def forget_birthday(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        server_id = str(interaction.guild.id)

        if server_id in servers_data and str(user.id) in servers_data[server_id]["birthdays"]:
            del servers_data[server_id]["birthdays"][str(user.id)]
            save_data()
            embed = create_embed(
                title="Birthday Forgotten",
                description=f"Birthday for {user.mention} has been forgotten."
            )
        else:
            embed = create_embed(
                title="Birthday Not Found",
                description=f"No birthday found for {user.mention}."
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="check", description="Check a user's birthday")
    async def check_birthday(self, interaction: discord.Interaction, user: discord.Member):
        server_id = str(interaction.guild.id)

        if server_id in servers_data and str(user.id) in servers_data[server_id]["birthdays"]:
            bday = servers_data[server_id]["birthdays"][str(user.id)]
            embed = create_embed(
                title="Birthday Check",
                description=f"{user.mention}'s birthday is {bday['month']}/{bday['day']}/{bday['year']}."
            )
        else:
            embed = create_embed(
                title="Birthday Not Found",
                description=f"No birthday found for {user.mention}."
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="upcoming", description="List the upcoming birthdays")
    async def upcoming_birthdays(self, interaction: discord.Interaction):
        server_id = str(interaction.guild.id)

        if server_id not in servers_data or not servers_data[server_id]["birthdays"]:
            embed = create_embed(
                title="No Upcoming Birthdays",
                description="No birthdays are remembered on this server."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        now = datetime.now(pytz.timezone('US/Eastern'))
        upcoming_birthdays = sorted(
            servers_data[server_id]["birthdays"].items(), 
            key=lambda item: ((item[1]['month'], item[1]['day']) >= (now.month, now.day), item[1]['month'], item[1]['day'])
        )[:5]

        if not upcoming_birthdays:
            embed = create_embed(
                title="No Upcoming Birthdays",
                description="No upcoming birthdays found."
            )
        else:
            description = ""
            for user_id, bday in upcoming_birthdays:
                user = await bot.fetch_user(int(user_id))
                bday_date = datetime(year=now.year, month=bday['month'], day=bday['day'])
                bday_date = now.tzinfo.localize(bday_date)  # Make bday_date timezone-aware
                if bday_date < now:
                    bday_date = bday_date.replace(year=now.year + 1)
                days_until = (bday_date - now).days
                description += f"{user.mention}: {bday['month']}/{bday['day']}/{bday['year']} (in {days_until} days)\n"

            embed = create_embed(
                title="Upcoming Birthdays",
                description=description
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="channel", description="Set the birthday announcement channel")
    async def set_birthday_channel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        server_id = str(interaction.guild.id)

        if server_id not in servers_data:
            servers_data[server_id] = {"birthdays": {}, "channel_id": None}

        if channel:
            servers_data[server_id]["channel_id"] = channel.id
            description = f"Birthday notifications will be sent in {channel.mention}."
        else:
            servers_data[server_id]["channel_id"] = None
            description = "Birthday notifications have been disabled."

        save_data()
        embed = create_embed(title="Channel Set", description=description)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="send", description="Send a happy birthday message on demand")
    async def send_birthday_message(self, interaction: discord.Interaction, user: discord.Member):
        server_id = str(interaction.guild.id)

        if server_id in servers_data and str(user.id) in servers_data[server_id]["birthdays"]:
            bday_channel_id = servers_data[server_id].get("channel_id")
            if bday_channel_id:
                channel = bot.get_channel(bday_channel_id)
                if channel:
                    await channel.send(f"🎉🎉🎉 Happy Birthday {user.mention} 🎉🎉🎉")
                    embed = create_embed(
                        title="Birthday Message Sent",
                        description=f"Happy Birthday message sent for {user.mention}."
                    )
                else:
                    embed = create_embed(
                        title="Error",
                        description="Birthday channel not found."
                    )
            else:
                embed = create_embed(
                    title="Error",
                    description="Birthday channel not set."
                )
        else:
            embed = create_embed(
                title="Birthday Not Found",
                description=f"No birthday found for {user.mention}."
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

# Register the command group
birthday_group = BirthdayGroup()

# Add the command group to all specified guilds
for guild_id in GUILD_IDS:
    guild = discord.Object(id=int(guild_id))
    bot.tree.add_command(birthday_group, guild=guild)

# Sync commands and run the bot
@bot.event
async def on_ready():
    try:
        # Clear global commands
        bot.tree.clear_commands(guild=None)

        for guild_id in GUILD_IDS:
            guild = discord.Object(id=int(guild_id))
            synced = await bot.tree.sync(guild=guild)  # Sync the slash commands with each specified guild
            print(f'Successfully synced {len(synced)} commands to guild {guild_id}:\n')
            for command in synced:
                print(f'Command Name: {command.name}')
                print(f'Description: {command.description}')
                print(f'ID: {command.id}')
                print(f'Guild ID: {guild_id}')
                print('-' * 20)
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')

bot.run(DISCORD_BOT_TOKEN)
