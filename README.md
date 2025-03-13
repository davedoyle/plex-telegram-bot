Plex Telegram Bot
A Telegram bot for remotely managing and monitoring a Linux-based home server, including Plex user tracking, system uptime, network speed, temperature trends, and more.

🚀 Features
Category	Features
| Category              | Features                                                |
|----------------------|---------------------------------------------------------|
| Server Management     | Restart, Shutdown, Update & Upgrade                     |
| System Monitoring     | CPU/GPU Temp, CPU Load, Memory Usage, Running Processes |
| Storage Monitoring    | HDD Capacity, Disk Usage Trends                         |
| Network Monitoring    | Network Speed, Network Activity Trends                  |
| Plex Integration      | View Active Plex Users                                  |
| Database & Logging    | Stores logs in SQLite                                   |

🛠️ Setup Instructions

1️⃣ Install Required Packages
Run the following command to install dependencies:

# Update package lists and install required system packages
sudo apt update && sudo apt install -y python3 python3-pip sqlite3 ethtool

# Install required Python packages
pip install python-telegram-bot matplotlib psutil uptime gpustat


2️⃣ Set Up a Telegram Bot

Open Telegram and search for @BotFather.
Run /newbot and follow the instructions.
Copy the bot token and save it.

3️⃣ Get Your Plex Token

To allow the bot to check active Plex users:

Open Plex Web App → Go to Settings.
Click Network and find X-Plex-Token.
Save this token.

4️⃣ Run the One-Time Setup Script (one_off.py)
Before running the bot, you need to store your credentials and add authorized users to this python file.

Run:

python3 one_off.py


✅ This script will:

Store the Telegram bot token
Store the Plex token
Add authorized users to the database
⚠️ Important: Do not enter your bot token as a user ID
When adding users, enter your Telegram user ID, not your bot's key.
Refer to the Python code comments if unsure.

Example of adding an admin user in one_off.py:

add_authorized_user(123456789, "admin")  # Replace 123456789 with your Telegram user ID

A friend can also use the bot

You can add their Telegram ID to let them check stats like network speed.
If you make them an admin, they can also restart the server or shut it down.

5️⃣ Start the Bot
Run:

python3 server_bot.py
✅ On the first run, the bot will automatically:

Generate the necessary SQLite tables if they don't already exist.
Retrieve stored credentials and start monitoring the system.

🔹 How It Works
The bot runs on a Linux server and connects via Telegram.
It logs temperature, network activity, and disk usage in an SQLite database.
Admin users can execute server management commands.
Plex users can check who is currently watching content.

💡 Why I Built This
I was tired of SSH-ing into my server just to:

Restart it.
Check temperature trends with custom graphs.
Monitor network speed issues (it sometimes dropped to 100Mbps instead of gigabit).
See who was watching Plex without opening the Plex UI.
This bot is my solution, and while it still needs refinement, it’s a great starting point for home server automation.

🔹 Example Bot Commands
After starting the bot with /start, you can send the following commands:

| Command            | Description                          |
|--------------------|--------------------------------------|
| /restart           | Restart the server (admin only)      |
| /shutdown          | Shutdown the server (admin only)     |
| /uptime            | Check server uptime                  |
| /services          | View active services                 |
| /cputemp           | View CPU temperature                 |
| /gputemp           | View GPU temperature                 |
| /cpuload           | View CPU load                        |
| /memory            | View memory usage                    |
| /processes         | View running processes               |
| /networkspeed      | Check network speed                  |
| /networkactivity   | View network activity trends         |
| /hddcapacity       | Check HDD capacity                   |
| /diskusage         | View disk usage trends               |
| /plex              | Check active Plex users              |



🔹 Future Improvements
✅ Better admin/user role management (e.g., add/remove admins dynamically)
✅ More detailed Plex integration (e.g., user streaming history)
✅ Improved error handling & logging
