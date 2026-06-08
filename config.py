import os
import pathlib

import dotenv

dotenv.load_dotenv()


THEME_DIRECTORY = pathlib.Path(r"M:\dev\rcmreloaded\data\themes")

ATPROTO_CLIENT_USERNAME = os.getenv("ATPROTO_CLIENT_USERNAME")
ATPROTO_CLIENT_PASSWORD = os.getenv("ATPROTO_CLIENT_PASSWORD")