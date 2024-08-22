# Birthday Bot 🎉

Birthday Bot is a Discord bot that helps you manage and celebrate birthdays in your Discord server. The bot allows users to remember, forget, check, and list upcoming birthdays, as well as send birthday messages on demand.

## Features

- Remember Birthdays: Add a user's birthday with the `/bday remember` command.
- Forget Birthdays: Remove a user's birthday with the `/bday forget` command.
- Check Birthdays: Check a specific user's birthday with the `/bday check` command.
- Upcoming Birthdays: List the next 5 upcoming birthdays with the `/bday upcoming` command.
- Send Birthday Message: Manually send a birthday message with the `/bday send` command.
- Customizable Notification Channel: Set a channel for birthday notifications with the `/bday channel` command.

## Setup and Installation

### Prerequisites

- Docker
- Docker Compose

### Environment Variables

Create a `.env` file in the project root with the following content:

DISCORD_BOT_TOKEN=your_discord_bot_token
GUILD_IDS=853753727847628841,123456789012345678

- DISCORD_BOT_TOKEN: Your Discord bot token.
- GUILD_IDS: Comma-separated list of Discord server IDs where the bot will be active.

### Building and Running the Bot

1. Build the Docker Image:

   docker-compose up --build -d

2. Check if the Bot is Running:

   docker ps

   You should see the `birthday-bot` container running.

### Persistent Data

The bot uses a `birthdays.json` file to store birthday data. This file is mounted as a volume in the Docker container to ensure data persists between restarts.

### Development

For local development without Docker, you can set up a virtual environment:

python -m venv env
source env/bin/activate
pip install -r requirements.txt

Run the bot with:

python bot.py

### Contributing

Feel free to open issues or submit pull requests for any improvements or bug fixes.

### License

This project is licensed under the MIT License.

