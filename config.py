# config.py
import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

# YouTube API 설정 추가
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")
DISCORD_YOUTUBE_CHANNEL_ID = int(os.getenv("DISCORD_YOUTUBE_CHANNEL_ID", 0))  # 기본값 0

# 필수 환경 변수 체크
required_vars = {
    "DISCORD_TOKEN": DISCORD_TOKEN,
    "DISCORD_CHANNEL_ID": DISCORD_CHANNEL_ID,
    "TWITTER_USERNAME": TWITTER_USERNAME,
    "BEARER_TOKEN": BEARER_TOKEN,
    "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
    "YOUTUBE_CHANNEL_ID": YOUTUBE_CHANNEL_ID,
    "DISCORD_YOUTUBE_CHANNEL_ID": DISCORD_YOUTUBE_CHANNEL_ID,
}

missing_vars = [name for name, value in required_vars.items() if not value]

if missing_vars:
    raise ValueError(f"❌ 필수 환경 변수 누락: {', '.join(missing_vars)}")