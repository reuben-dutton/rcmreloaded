import os
import pathlib

import dotenv

dotenv.load_dotenv()


ROOT = pathlib.Path(__file__).resolve().parent
DATA_DIRECTORY = ROOT / "data"

ATPROTO_CLIENT_USERNAME = os.getenv("ATPROTO_CLIENT_USERNAME")
ATPROTO_CLIENT_PASSWORD = os.getenv("ATPROTO_CLIENT_PASSWORD")