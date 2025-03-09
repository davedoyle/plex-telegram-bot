import logging
from logging.handlers import RotatingFileHandler
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import psutil
import uptime
import subprocess
import gpustat
from datetime import timedelta, datetime
import time
import xml.etree.ElementTree as ET
from textwrap import wrap
import matplotlib.pyplot as plt
import json
import threading
import sqlite3
import re

#test comment

DB_PATH = "/serverbot/server_logs.db"

def initialize_database():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS temperature_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cpu_temp REAL,
                gpu_temp REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ethernet_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                speed TEXT,
                duplex TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hdd_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                device TEXT NOT NULL,
                total_space REAL,
                used_space REAL,
                available_space REAL,
                folder_count INTEGER,
                file_count INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS network_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                rx_mbps REAL,
                tx_mbps REAL
            )
        """)

        conn.commit()




# Replace 'YOUR_TELEGRAM_BOT_API_TOKEN' with your actual bot token
TOKEN = 'YOUR_TELEGRAM_BOT_API_TOKEN'
if not TOKEN:
    raise ValueError("Please set the TELEGRAM_BOT_TOKEN environment variable.")

# List of authorized user IDs
AUTHORIZED_USERS = [262231547, 123456789]  # Add your user IDs here
SHUTDOWN_USER_ID = 262231547  # User allowed to execute shutdown
UPDATE_UPGRADE_USER_ID = 262231547  # User allowed to execute update/upgrade

# Configure logging with RotatingFileHandler
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

log_handler = RotatingFileHandler(
    '/serverbot/server_bot.log',  # Ensure this path is correct
    maxBytes=5*1024*1024,  # 5 MB
    backupCount=3
)
log_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)

def check_authorization(update: Update) -> bool:
    user_id = update.message.from_user.id
    return user_id in AUTHORIZED_USERS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not check_authorization(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        user_id = update.message.from_user.id
        logger.info(f"User {user_id} started the bot.")

        # ✅ UPDATED KEYBOARD WITH NETWORK OPTIONS
        keyboard = [
            ['🔄 Restart', '⏱ Uptime'],
            ['🛠 Services', '🌡 CPU Temp'],
            ['🌡 GPU Temp', '📊 CPU Load'],
            ['👥 Plex Users', '💾 HDD Capacity'],
            ['📁 Disk Usage', '💻 Memory'],
            ['📡 Network Speed', '📊 Network Activity'],  # ✅ UPDATED ROW
            ['🔍 Processes', '⬆️ Update & Upgrade'],
            ['📉 Temp Trend', '🔻 Shutdown']
        ]

        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)
        await update.message.reply_text('Choose an option:', reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text("An error occurred in the start command.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not check_authorization(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        text = update.message.text
        user_id = update.message.from_user.id
        logger.info(f"Received message '{text}' from user {user_id}")

        if text == '🔄 Restart':
            await restart(update, context)
        elif text == '⏱ Uptime':
            await check_uptime(update, context)
        elif text == '🛠 Services':
            await check_services(update, context)
        elif text == '🌡 CPU Temp':
            await check_cpu_temp(update, context)
        elif text == '🌡 GPU Temp':
            await check_gpu_temp(update, context)
        elif text == '📊 CPU Load':
            await check_cpu_load(update, context)
        elif text == '👥 Plex Users':
            await check_plex_users(update, context)
        elif text == '💾 HDD Capacity':
            await check_hdd_capacity(update, context)
        elif text == '📁 Disk Usage':
            await check_disk_usage(update, context)
        elif text == '💻 Memory':
            await check_memory_usage(update, context)
        elif text == '🌐 Network Info':
            await check_network_info(update, context)
        elif text == '📡 Network Speed':  # Added NIC speed function
            await check_network_speed_status(update, context)
        elif text == '📊 Network Activity':  # Added real-time Mbps activity function
            await check_network_activity(update, context)
        elif text == '🔍 Processes':
            await check_running_processes(update, context)
        elif text == '⬆️ Update & Upgrade':
            await confirm_update_upgrade(update, context)
        elif text == 'Yes, proceed with Update & Upgrade':
            await update_upgrade(update, context)
        elif text == 'No, cancel Update & Upgrade':
            await cancel_update_upgrade(update, context)
        elif text == '🔻 Shutdown':
            await shutdown(update, context)
        elif text == '📉 Temp Trend':
            await check_temperature_trend(update, context)
        else:
            logger.warning(f"Unknown command '{text}' received from user {user_id}")
            await update.message.reply_text('Unknown command. Please choose an option from the keyboard.')
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await update.message.reply_text("An error occurred while handling the message.")





async def check_network_speed_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not check_authorization(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        user_id = update.message.from_user.id
        logger.info(f"User {user_id} checked network speed status.")

        # ✅ Auto-detect active network interface
        result = subprocess.run(['ip', '-o', 'link'], capture_output=True, text=True)
        interfaces = re.findall(r'^\d+: (\w+):', result.stdout, re.MULTILINE)
        
        active_interface = None
        for interface in interfaces:
            if not interface.startswith("lo"):  # Ignore loopback
                active_interface = interface
                break

        if not active_interface:
            await update.message.reply_text("❌ No active network interface found.")
            return

        # Run ethtool on detected interface
        result = subprocess.run(['ethtool', active_interface], capture_output=True, text=True)
        speed, duplex = None, None
        for line in result.stdout.splitlines():
            if "Speed:" in line:
                speed = line.split(":")[1].strip()
            if "Duplex:" in line:
                duplex = line.split(":")[1].strip()

        if speed and duplex:
            response = f"📡 **Network Interface ({active_interface}) Speed:** {speed}\n🔄 **Duplex Mode:** {duplex}"
        else:
            response = "❌ Unable to retrieve network speed status."

        await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error in check_network_speed_status: {e}")
        await update.message.reply_text("An error occurred while checking network speed status.")


async def check_network_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        timestamps, rx_mbps, tx_mbps = [], [], []

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT timestamp, rx_mbps, tx_mbps FROM network_logs ORDER BY timestamp DESC LIMIT 60")
            rows = cursor.fetchall()
            for row in rows[::-1]:
                timestamps.append(row[0])
                rx_mbps.append(row[1] if row[1] is not None else 0)
                tx_mbps.append(row[2] if row[2] is not None else 0)

        if not rx_mbps:
            await update.message.reply_text("No network activity data available.")
            return

        plt.figure(figsize=(10, 5))
        plt.plot(range(len(rx_mbps)), rx_mbps, label='Download (RX Mbps)', marker='o')
        plt.plot(range(len(tx_mbps)), tx_mbps, label='Upload (TX Mbps)', marker='x')

        plt.xticks([])  # Remove timestamps
        plt.xlabel("Last 60 Minutes")
        plt.ylabel("Mbps")
        plt.title("📊 Network Activity (Last 60 Minutes)")
        plt.legend()
        plt.tight_layout()
        plt.savefig('/tmp/network_activity.png')
        plt.close()

        await context.bot.send_photo(chat_id=update.message.chat_id, photo=open('/tmp/network_activity.png', 'rb'))

    except Exception as e:
        logger.error(f"Error in check_network_activity: {e}")
        await update.message.reply_text("An error occurred while generating the network activity graph.")

def log_network_activity():
    try:
        # ✅ Detect active network interface
        with open("/proc/net/dev", "r") as f:
            lines = f.readlines()

        active_interface = None
        for line in lines:
            if "eth0" in line or "ens" in line or "enp" in line or "wlan" in line:
                active_interface = line.split(":")[0].strip()
                break  # Use the first matching interface

        if not active_interface:
            logger.error("No active network interface found.")
            return

        for line in lines:
            if active_interface in line:
                data = line.split()
                rx_bytes = int(data[1])  # Received bytes
                tx_bytes = int(data[9])  # Transmitted bytes

                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Convert bytes to Mbps (assuming a 1-minute interval)
                rx_mbps = (rx_bytes * 8) / (1024 ** 2)
                tx_mbps = (tx_bytes * 8) / (1024 ** 2)

                with sqlite3.connect(DB_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO network_logs (timestamp, rx_mbps, tx_mbps)
                        VALUES (?, ?, ?)
                    """, (timestamp, rx_mbps, tx_mbps))
                    conn.commit()

                logger.info(f"Logged network activity: RX {rx_mbps:.2f} Mbps, TX {tx_mbps:.2f} Mbps on {active_interface}")

    except Exception as e:
        logger.error(f"Error logging network activity: {e}")



async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not check_authorization(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        user_id = update.message.from_user.id
        logger.info(f"User {user_id} issued restart command.")
        await update.message.reply_text('Restarting server...')
        logger.info("Executing reboot command")
        subprocess.run(['sudo', '/sbin/reboot'])
    except Exception as e:
        logger.error(f"Error in restart command: {e}")
        await update.message.reply_text("An error occurred while restarting the server.")

async def shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        if user_id != SHUTDOWN_USER_ID:
            logger.warning(f"User {user_id} attempted to shutdown the server.")
            await update.message.reply_text("You are not authorized to shut down the server.")
            return

        logger.info(f"User {user_id} issued shutdown command.")
        await update.message.reply_text('Shutting down server...')
        subprocess.run(['sudo', '/sbin/shutdown', '-h', 'now'])
    except Exception as e:
        logger.error(f"Error in shutdown command: {e}")
        await update.message.reply_text("An error occurred while shutting down the server.")

async def check_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not check_authorization(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        user_id = update.message.from_user.id
        logger.info(f"User {user_id} checked uptime.")
        up_time_seconds = uptime.uptime()
        up_time = timedelta(seconds=int(up_time_seconds))
        await update.message.reply_text(f'Server Uptime: {up_time}')
    except Exception as e:
        logger.error(f"Error in check_uptime command: {e}")
        await update.message.reply_text("An error occurred while checking the server uptime.")

async def check_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not check_authorization(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        user_id = update.message.from_user.id
        logger.info(f"User {user_id} checked services.")
        time.sleep(1)  # Add a small delay to ensure data is available
        services = [(p.info['name'], p.info['cpu_percent']) for p in psutil.process_iter(['name', 'cpu_percent']) if p.info['cpu_percent'] > 0]
        services.sort(key=lambda x: x[1], reverse=True)
        if not services:
            response = "No services are currently using the CPU."
        else:
            response = "Top Services by CPU Usage:\n"
            for service in services[:10]:
                response += f"{service[0]}: {service[1]}%\n"
        logger.info(f"Services response: {response}")
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in check_services command: {e}")
        await update.message.reply_text("An error occurred while checking the services.")

async def check_plex_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not check_authorization(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        user_id = update.message.from_user.id
        logger.info(f"User {user_id} checked Plex users.")
        #Replace your plex token with your own
        command = "curl http://localhost:32400/status/sessions?X-Plex-Token=YOURPLEXTOKEN"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        xml_data = result.stdout

        # Parse the XML data
        root = ET.fromstring(xml_data)

        # Extract user names
        users = [user.get('title') for user in root.findall('.//User')]

        response = "Plex Users:\n" + "\n".join(users)
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in check_plex_users command: {e}")
        await update.message.reply_text("An error occurred while checking the Plex users.")

async def check_cpu_temp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not check_authorization(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        user_id = update.message.from_user.id
        logger.info(f"User {user_id} checked CPU temperature.")
        temps = psutil.sensors_temperatures()
        cpu_temps = temps.get('coretemp', [])
        response = "CPU Temperatures:\n"
        for temp in cpu_temps:
            response += f"{temp.label}: {temp.current}°C\n"
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in check_cpu_temp command: {e}")
        await update.message.reply_text("An error occurred while checking the CPU temperature.")

async def check_gpu_temp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not check_authorization(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        user_id = update.message.from_user.id
        logger.info(f"User {user_id} checked GPU temperature.")
        gpu_stats = gpustat.new_query()
        response = "GPU Temperatures:\n"
        for gpu in gpu_stats.gpus:
            response += f"{gpu.name}: {gpu.temperature}°C\n"
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in check_gpu_temp command: {e}")
        await update.message.reply_text("An error occurred while checking the GPU temperature.")

async def check_cpu_load(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not check_authorization(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        user_id = update.message.from_user.id
        logger.info(f"User {user_id} checked CPU load.")
        load1, load5, load15 = psutil.getloadavg()
        response = f"CPU Load (1, 5, 15 minutes): {load1}, {load5}, {load15}\n"
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in check_cpu_load command: {e}")
        await update.message.reply_text("An error occurred while checking the CPU load.")

async def check_hdd_capacity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not check_authorization(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        user_id = update.message.from_user.id
        logger.info(f"User {user_id} checked HDD capacity.")
        partitions = psutil.disk_partitions()
        devices = []
        used_space = []
        total_space = []
        for partition in partitions:
            usage = psutil.disk_usage(partition.mountpoint)
            total = usage.total / (1024 ** 3)  # Convert to GB
            used = (usage.total - usage.free) / (1024 ** 3)  # Convert to GB
            devices.append(partition.device)
            used_space.append(used)
            total_space.append(total)

        fig, ax = plt.subplots()
        bar_width = 0.35
        index = range(len(devices))

        bar1 = plt.bar(index, used_space, bar_width, label='Used Space')
        bar2 = plt.bar(index, [t - u for t, u in zip(total_space, used_space)], bar_width, bottom=used_space, label='Free Space')

        plt.xlabel('Device')
        plt.ylabel('Size (GB)')
        plt.title('HDD Capacity')
        plt.xticks(index, devices, rotation=45)
        plt.legend()

        # Save the plot to a file
        plt.tight_layout()
        plt.savefig('/tmp/hdd_capacity.png')
        plt.close()

        await context.bot.send_photo(chat_id=update.message.chat_id, photo=open('/tmp/hdd_capacity.png', 'rb'))
    except Exception as e:
        logger.error(f"Error in check_hdd_capacity command: {e}")
        await update.message.reply_text("An error occurred while checking the HDD capacity.")

async def check_disk_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        timestamps = []
        used_spaces = []
        available_spaces = []

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, used_space, available_space FROM hdd_logs
                ORDER BY timestamp DESC LIMIT 60
            """)
            rows = cursor.fetchall()
            for row in rows[::-1]:  # Reverse to get chronological order
                timestamps.append(row[0])
                used_spaces.append(row[1])
                available_spaces.append(row[2])

        if not timestamps:
            await update.message.reply_text("No HDD data available.")
            return

        plt.figure(figsize=(10, 5))
        plt.plot(timestamps, used_spaces, label='Used Space (GB)', marker='o')
        plt.plot(timestamps, available_spaces, label='Available Space (GB)', marker='x')
        plt.xticks(rotation=45)
        plt.xlabel("Time")
        plt.ylabel("HDD Space (GB)")
        plt.title("HDD Usage Trend (Last 60 Entries)")
        plt.legend()
        plt.tight_layout()

        hdd_trend_path = "/tmp/hdd_trend.png"
        plt.savefig(hdd_trend_path)
        plt.close()

        await context.bot.send_photo(chat_id=update.message.chat_id, photo=open(hdd_trend_path, 'rb'))
    except Exception as e:
        logger.error(f"Error in check_hdd_info: {e}")
        await update.message.reply_text("An error occurred while generating the HDD trend.")

async def check_memory_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not check_authorization(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        user_id = update.message.from_user.id
        logger.info(f"User {user_id} checked memory usage.")
        mem = psutil.virtual_memory()
        
        total_memory = mem.total / (1024 ** 3)  # Convert to GB
        available_memory = mem.available / (1024 ** 3)  # Convert to GB
        used_memory = total_memory - available_memory

        fig, ax = plt.subplots()
        bar_width = 0.35
        index = range(1)

        bar1 = plt.bar(index, [used_memory], bar_width, label='Used Memory')
        bar2 = plt.bar(index, [total_memory - used_memory], bar_width, bottom=[used_memory], label='Available Memory')

        plt.xlabel('Memory')
        plt.ylabel('Size (GB)')
        plt.title('Memory Usage')
        plt.xticks(index, ['Memory'])
        plt.legend()

        # Save the plot to a file
        plt.tight_layout()
        plt.savefig('/tmp/memory_usage.png')
        plt.close()

        await context.bot.send_photo(chat_id=update.message.chat_id, photo=open('/tmp/memory_usage.png', 'rb'))
    except Exception as e:
        logger.error(f"Error in check_memory_usage command: {e}")
        await update.message.reply_text("An error occurred while checking the memory usage.")

async def check_network_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        timestamps = []
        speeds = []
        duplexes = []

        # Fetch data from the database
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT timestamp, speed, duplex FROM ethernet_logs ORDER BY timestamp DESC LIMIT 60")
            rows = cursor.fetchall()
            for row in rows[::-1]:  # Reverse for chronological order
                timestamps.append(row[0])
                speeds.append(float(row[1].replace("Mb/s", "").strip()) if row[1] else 0)  # Extract speed value
                duplexes.append(1 if row[2] == "Full" else 0)  # Encode duplex as binary for plotting

        if not timestamps:
            await update.message.reply_text("No network data available.")
            return

        # Generate a network trend plot
        plt.figure(figsize=(10, 5))
        plt.plot(timestamps, speeds, label="Speed (Mbps)", marker="o")
        plt.plot(timestamps, duplexes, label="Duplex (1=Full, 0=Half)", marker="x")
        plt.xticks(rotation=45)
        plt.xlabel("Time")
        plt.ylabel("Network Stats")
        plt.title("Network Info Trend (Last 60 Entries)")
        plt.legend()
        plt.tight_layout()

        network_trend_path = "/tmp/network_trend.png"
        plt.savefig(network_trend_path)
        plt.close()

        # Send the generated plot to the user
        await context.bot.send_photo(chat_id=update.message.chat_id, photo=open(network_trend_path, "rb"))
    except Exception as e:
        logger.error(f"Error in check_network_info: {e}")
        await update.message.reply_text("An error occurred while generating the network trend.")


async def check_running_processes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not check_authorization(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        user_id = update.message.from_user.id
        logger.info(f"User {user_id} checked running processes.")
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        output = result.stdout
        if len(output) > 4096:  # Telegram message limit
            for chunk in wrap(output, 4096):
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(output)
    except Exception as e:
        logger.error(f"Error in check_running_processes command: {e}")
        await update.message.reply_text("An error occurred while checking the running processes.")

async def confirm_update_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        if user_id != UPDATE_UPGRADE_USER_ID:
            logger.warning(f"User {user_id} attempted to confirm update and upgrade.")
            await update.message.reply_text("You are not authorized to update and upgrade the server.")
            return

        logger.info(f"User {user_id} requested confirmation for update and upgrade.")
        keyboard = [['Yes, proceed with Update & Upgrade', 'No, cancel Update & Upgrade']]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text('Are you sure you want to update and upgrade? This may take some time.', reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in confirm_update_upgrade command: {e}")
        await update.message.reply_text("An error occurred while requesting confirmation for update and upgrade.")

async def update_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        if user_id != UPDATE_UPGRADE_USER_ID:
            logger.warning(f"User {user_id} attempted to update and upgrade the server.")
            await update.message.reply_text("You are not authorized to update and upgrade the server.")
            return

        logger.info(f"User {user_id} issued update and upgrade command.")
        await update.message.reply_text('Updating package lists and upgrading all packages...')
        subprocess.run(['sudo', 'apt-get', 'update'], capture_output=True, text=True)
        subprocess.run(['sudo', 'apt-get', 'upgrade', '-y'], capture_output=True, text=True)
        await update.message.reply_text('Update and upgrade completed.', reply_markup=ReplyKeyboardRemove())
        await start(update, context)  # Restore the keyboard
    except Exception as e:
        logger.error(f"Error in update_upgrade command: {e}")
        await update.message.reply_text("An error occurred while updating and upgrading the server.")

async def cancel_update_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        logger.info(f"User {user_id} canceled the update and upgrade command.")
        await update.message.reply_text('Update and upgrade canceled.', reply_markup=ReplyKeyboardRemove())
        await start(update, context)  # Restore the keyboard
    except Exception as e:
        logger.error(f"Error in cancel_update_upgrade command: {e}")
        await update.message.reply_text("An error occurred while canceling the update and upgrade.")

async def test_graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        logger.info(f"User {user_id} requested test graph.")

        # Dummy data for the test graph
        categories = ['Category 1', 'Category 2', 'Category 3', 'Category 4']
        values = [10, 20, 30, 40]

        fig, ax = plt.subplots()
        bar_width = 0.35
        index = range(len(categories))

        plt.bar(index, values, bar_width, label='Values')

        plt.xlabel('Category')
        plt.ylabel('Values')
        plt.title('Test Graph')
        plt.xticks(index, categories)
        plt.legend()

        # Save the plot to a file
        plt.tight_layout()
        plt.savefig('/tmp/test_graph.png')
        plt.close()

        await context.bot.send_photo(chat_id=update.message.chat_id, photo=open('/tmp/test_graph.png', 'rb'))
    except Exception as e:
        logger.error(f"Error in test_graph command: {e}")
        await update.message.reply_text("An error occurred while generating the test graph.")

#def log_temperature():
#    try:
#        temps = psutil.sensors_temperatures()
#        cpu_temps = temps.get('coretemp', [])
#        gpu_stats = gpustat.new_query()
#        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#
#        data = {
#            'timestamp': timestamp,
#            'cpu_temp': [temp.current for temp in cpu_temps],
#            'gpu_temp': [gpu.temperature for gpu in gpu_stats.gpus]
#        }
#
#        with open('/tmp/temperature_log.json', 'a') as f:
#            json.dump(data, f)
#            f.write('\n')
#    except Exception as e:
#        logger.error(f"Error logging temperatures: {e}")
#
async def check_temperature_trend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cpu_temps, gpu_temps = [], []

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT cpu_temp, gpu_temp FROM temperature_logs ORDER BY timestamp DESC LIMIT 60")
            rows = cursor.fetchall()
            for row in rows[::-1]:
                cpu_temps.append(row[0] if row[0] is not None else 0)
                gpu_temps.append(row[1] if row[1] is not None else 0)

        if not cpu_temps:
            await update.message.reply_text("No temperature data available.")
            return

        plt.figure(figsize=(10, 5))
        plt.plot(range(len(cpu_temps)), cpu_temps, label='CPU Temp (°C)', marker='o')
        plt.plot(range(len(gpu_temps)), gpu_temps, label='GPU Temp (°C)', marker='x')
        
        plt.xticks([])  # Remove x-axis labels
        plt.xlabel("Last 60 Minutes")  # Generalized x-axis label
        plt.ylabel("Temperature (°C)")
        plt.legend()
        plt.tight_layout()
        plt.savefig('/tmp/temp_trend.png')
        plt.close()

        await context.bot.send_photo(chat_id=update.message.chat_id, photo=open('/tmp/temp_trend.png', 'rb'))
    except Exception as e:
        logger.error(f"Error in check_temperature_trend: {e}")
        await update.message.reply_text("An error occurred while generating the temperature trend.")




def log_temperature_to_db():
    try:
        temps = psutil.sensors_temperatures()
        cpu_temps = temps.get('coretemp', [])
        gpu_temp = None
        try:
            gpu_stats = gpustat.new_query()
            gpu_temp = gpu_stats.gpus[0].temperature if gpu_stats.gpus else None
        except Exception:
            pass

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cpu_temp = cpu_temps[0].current if cpu_temps else None

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO temperature_logs (timestamp, cpu_temp, gpu_temp)
                VALUES (?, ?, ?)
            """, (timestamp, cpu_temp, gpu_temp))
            conn.commit()
    except Exception as e:
        logger.error(f"Error logging temperature data to DB: {e}")

def log_ethernet_settings_to_db():
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        result = subprocess.run(['ethtool', 'eth0'], capture_output=True, text=True)
        speed, duplex = None, None
        for line in result.stdout.splitlines():
            if "Speed:" in line:
                speed = line.split(":")[1].strip()
            if "Duplex:" in line:
                duplex = line.split(":")[1].strip()

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ethernet_logs (timestamp, speed, duplex)
                VALUES (?, ?, ?)
            """, (timestamp, speed, duplex))
            conn.commit()
    except Exception as e:
        logger.error(f"Error logging Ethernet settings to DB: {e}")

def log_hdd_to_db():
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        partitions = psutil.disk_partitions()
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                total_space = usage.total / (1024 ** 3)  # Convert to GB
                used_space = usage.used / (1024 ** 3)  # Convert to GB
                available_space = usage.free / (1024 ** 3)  # Convert to GB

                folder_count = 0
                file_count = 0
                for root, dirs, files in os.walk(partition.mountpoint):
                    folder_count += len(dirs)
                    file_count += len(files)
                    break  # Only count the top-level directory

                with sqlite3.connect(DB_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO hdd_logs (timestamp, device, total_space, used_space, available_space, folder_count, file_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (timestamp, partition.device, total_space, used_space, available_space, folder_count, file_count))
                    conn.commit()
            except Exception as e:
                logger.warning(f"Could not log partition {partition.device}: {e}")
    except Exception as e:
        logger.error(f"Error logging HDD data to DB: {e}")



def start_logging():
    while True:
        log_temperature_to_db()
        log_network_activity()  # ✅ Added this to log Mbps activity every minute
        if datetime.now().minute == 0:
            log_ethernet_settings_to_db()
        if datetime.now().hour == 0:
            log_hdd_to_db()
        time.sleep(60)




#def start_temperature_logging():
#    while True:
#        log_temperature()
#        time.sleep(60)

def main():

    initialize_database()


    # Start the temperature logging in a separate thread
    #temperature_thread = threading.Thread(target=start_temperature_logging, daemon=True)
    #temperature_thread.start()
    
    logging_thread = threading.Thread(target=start_logging, daemon=True)
    logging_thread.start()

    # Initialize ApplicationBuilder with bot token
    application = ApplicationBuilder().token(TOKEN).build()

    # Add the command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("restart", restart))
    application.add_handler(CommandHandler("shutdown", shutdown))
    application.add_handler(CommandHandler("uptime", check_uptime))
    application.add_handler(CommandHandler("services", check_services))
    application.add_handler(CommandHandler("cputemp", check_cpu_temp))
    application.add_handler(CommandHandler("gputemp", check_gpu_temp))
    application.add_handler(CommandHandler("cpuload", check_cpu_load))
    application.add_handler(CommandHandler("plex", check_plex_users))
    application.add_handler(CommandHandler("hddcapacity", check_hdd_capacity))
    application.add_handler(CommandHandler("diskusage", check_disk_usage))
    application.add_handler(CommandHandler("memory", check_memory_usage))
    application.add_handler(CommandHandler("network", check_network_info))
    application.add_handler(CommandHandler("processes", check_running_processes))
    application.add_handler(CommandHandler("updateupgrade", update_upgrade))
    application.add_handler(CommandHandler("temptrend", check_temperature_trend))
    application.add_handler(CommandHandler("networkspeed", check_network_speed_status))
    application.add_handler(CommandHandler("networkactivity", check_network_activity))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
