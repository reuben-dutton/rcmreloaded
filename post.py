import os

import dotenv
import atproto

dotenv.load_dotenv()

USERNAME = os.getenv('ATPROTO_CLIENT_USERNAME')
PASSWORD = os.getenv('ATPROTO_CLIENT_PASSWORD')

client = atproto.Client()
client.login(USERNAME, PASSWORD)




client.send_image()

