import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

# 필수 환경 변수 체크
missing_vars = [var for var in ["DISCORD_TOKEN", "DISCORD_CHANNEL_ID", "TWITTER_USERNAME", "BEARER_TOKEN"]
                if not globals().get(var)]
if missing_vars:
    raise ValueError(f"❌ 필수 환경 변수 누락: {', '.join(missing_vars)}")
