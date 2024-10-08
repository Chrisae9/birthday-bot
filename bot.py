import asyncio
import discord
from discord.ext import commands, tasks  # Import tasks from discord.ext
from discord import app_commands
import os
import json
from datetime import datetime, timedelta
import pytz
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()  # This will print to the console
    ]
)

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
    async def remember_birthday(self, interaction: discord.Interaction, month: int, day: int, year: int = None, user: discord.Member = None):
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

        year_text = f"/{year}" if year else ""
        embed = create_embed(
            title="Birthday Remembered",
            description=f"Birthday for {user.mention} remembered: {month}/{day}{year_text}."
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logging.info(f"{interaction.user} used /bday remember with parameters: month={month}, day={day}, year={year}, user={user}")

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
        logging.info(f"{interaction.user} used /bday forget with parameters: user={user}")

    @app_commands.command(name="check", description="Check a user's birthday")
    async def check_birthday(self, interaction: discord.Interaction, user: discord.Member):
        server_id = str(interaction.guild.id)

        if server_id in servers_data and str(user.id) in servers_data[server_id]["birthdays"]:
            bday = servers_data[server_id]["birthdays"][str(user.id)]
            year_text = f"/{bday['year']}" if bday.get('year') else ""
            embed = create_embed(
                title="Birthday Check",
                description=f"{user.mention}'s birthday is {bday['month']}/{bday['day']}{year_text}."
            )
        else:
            embed = create_embed(
                title="Birthday Not Found",
                description=f"No birthday found for {user.mention}."
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        logging.info(f"{interaction.user} used /bday check with parameters: user={user}")

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

        # Get the current date and time in the US/Eastern timezone
        now = datetime.now(pytz.timezone('US/Eastern'))
        today = now.date()  # Date object for today
        upcoming_birthdays = []

        for user_id, bday in servers_data[server_id]["birthdays"].items():
            # Calculate the next occurrence of the birthday
            bday_date = datetime(year=now.year, month=bday['month'], day=bday['day'], tzinfo=now.tzinfo).date()
            if bday_date < today:
                bday_date = bday_date.replace(year=now.year + 1)

            days_until = (bday_date - today).days  # Calculate the number of days until the next birthday

            # Append the birthday data to the list
            upcoming_birthdays.append((user_id, bday_date, days_until))

        # Sort birthdays by the number of days until they occur
        upcoming_birthdays.sort(key=lambda x: x[2])

        # Prepare the embed description with the closest 5 birthdays
        description = ""
        for user_id, bday_date, days_until in upcoming_birthdays[:5]:
            user = await bot.fetch_user(int(user_id))
            if days_until == 0:
                description += f"{user.mention}: {bday_date.month}/{bday_date.day} (today)\n"
            elif days_until == 1:
                description += f"{user.mention}: {bday_date.month}/{bday_date.day} (in 1 day)\n"
            else:
                description += f"{user.mention}: {bday_date.month}/{bday_date.day} (in {days_until} days)\n"

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
        logging.info(f"{interaction.user} used /bday channel with parameters: channel={channel}")

    @app_commands.command(name="send", description="Send a happy birthday message on demand")
    async def send_birthday_message(self, interaction: discord.Interaction, user: discord.Member):
        server_id = str(interaction.guild.id)

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

        await interaction.response.send_message(embed=embed, ephemeral=True)
        logging.info(f"{interaction.user} used /bday send with parameters: user={user}")
        logging.info(f"Birthday message sent for user {user.mention}")

@tasks.loop(hours=24)
async def check_birthdays():
    """Loop to check for birthdays at 10 AM ET daily."""
    while True:
        # Get the current time in the US/Eastern timezone
        now = datetime.now(pytz.timezone('US/Eastern'))
        logging.info(f"Current time is: {now}")

        # Calculate the next 10 AM time
        target_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
        logging.info(f"Initial target time for 10 AM ET is: {target_time}")

        if now > target_time:
            # If we've already passed 10 AM today, target 10 AM tomorrow
            target_time += timedelta(days=1)
            logging.info(f"Target time adjusted to next day: {target_time}")

        # Calculate the time difference until the next 10 AM
        time_until_target = (target_time - now).total_seconds()
        logging.info(f"Time until next 10 AM ET: {time_until_target} seconds")

        # Sleep until 10 AM
        logging.info(f"Sleeping until the next 10 AM ET...")
        await asyncio.sleep(time_until_target)

        # Now it's 10 AM, we can run the birthday check
        today = (target_time.month, target_time.day)
        logging.info(f"Checking birthdays for today: {today}")

        for server_id, data in servers_data.items():
            channel_id = data.get("channel_id")
            if channel_id is None:
                logging.info(f"No channel set for server {server_id}, skipping...")
                continue

            # Gather all users whose birthday is today
            birthday_people = [user_id for user_id, bday in data["birthdays"].items() if (bday['month'], bday['day']) == today]

            if birthday_people:
                channel = bot.get_channel(channel_id)
                if channel:
                    birthday_mentions = ", ".join([f"<@{user_id}>" for user_id in birthday_people])
                    await channel.send(f"🎉🎉🎉 Happy Birthday {birthday_mentions}! 🎉🎉🎉")
                    logging.info(f"Birthday message sent for users {birthday_mentions} in server {server_id}")
                else:
                    logging.error(f"Channel {channel_id} not found for server {server_id}. Unable to send birthday messages.")
            else:
                # Log when no birthdays are found
                logging.info(f"No birthdays found for server {server_id} today.")
                
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
        check_birthdays.start()  # Start the task loop
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')


bot.run(DISCORD_BOT_TOKEN)
