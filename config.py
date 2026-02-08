import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
TICKET_CATEGORY_ID = 1453134431249236078
STAFF_ROLE_NAME = "Staff"
TICKET_LOGS_CHANNEL = "ticket-logs"
