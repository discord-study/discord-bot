import os
import logging
import discord
import tweepy
import aiofiles
import asyncio
from discord.ext import tasks
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")
if not TWITTER_USERNAME:
    raise ValueError("TWITTER_USERNAME is missing in the environment variables.")

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

if not DISCORD_TOKEN or not DISCORD_CHANNEL_ID:
    raise ValueError("DISCORD_TOKEN or DISCORD_CHANNEL_ID is missing in the environment variables.")
if not BEARER_TOKEN:
    raise ValueError("Twitter API BEARER_TOKEN is missing in the environment variables.")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Tweepy 설정 (v2 API)
client_v2 = tweepy.Client(bearer_token=BEARER_TOKEN)

# 디스코드 클라이언트 설정
intents = discord.Intents.default()
client = discord.Client(intents=intents)

CACHE_FILE = "last_tweet_id.txt"

# 비동기 파일 입출력 (aiofiles 사용)
async def load_last_tweet_id():
    if os.path.exists(CACHE_FILE):
        async with aiofiles.open(CACHE_FILE, "r") as f:
            content = await f.read()
            return content.strip()
    return None

async def save_last_tweet_id(tweet_id):
    async with aiofiles.open(CACHE_FILE, "w") as f:
        await f.write(str(tweet_id))

# 글로벌 변수: Twitter 사용자 ID, Discord 채널 객체 캐싱
twitter_user_id = None
discord_channel = None

@client.event
async def on_ready():
    global twitter_user_id, discord_channel
    logging.info(f'Logged in as {client.user}')
    
    # Discord 채널 객체 캐싱
    discord_channel = client.get_channel(int(DISCORD_CHANNEL_ID))
    if discord_channel is None:
        logging.error(f"Error: Unable to find channel with ID {DISCORD_CHANNEL_ID}")
        await client.close()
        return

    # Twitter 사용자 ID 캐싱
    user_data = client_v2.get_user(username=TWITTER_USERNAME)
    if user_data and user_data.data:
        twitter_user_id = user_data.data.id
        logging.info(f"Twitter user id for {TWITTER_USERNAME} is {twitter_user_id}")
    else:
        logging.error("Twitter 사용자 정보를 가져올 수 없습니다.")
        await client.close()
        return

    # 초기 실행 시, 캐시 파일에 저장된 마지막 트윗 ID가 없으면
    # 최신 트윗 1개만 가져와서 캐시에 저장 (과거 트윗을 불러오지 않음)
    last_tweet_id = await load_last_tweet_id()
    if last_tweet_id is None:
        tweets = client_v2.get_users_tweets(
            id=twitter_user_id,
            max_results=1,
            tweet_fields=["created_at", "text"]
        )
        if tweets.data:
            latest_tweet = tweets.data[0]
            await save_last_tweet_id(latest_tweet.id)
            logging.info("Initialized last_tweet_id with the latest tweet. Old tweets will not be posted.")
        else:
            logging.info("No tweets found for initialization.")
    
    # 주기적 트윗 체크 시작
    check_tweets.start()

@tasks.loop(minutes=5)
async def check_tweets():
    global twitter_user_id, discord_channel
    last_tweet_id = await load_last_tweet_id()
    try:
        tweets = client_v2.get_users_tweets(
            id=twitter_user_id,
            max_results=5,
            since_id=last_tweet_id,
            tweet_fields=["created_at", "text"]
        )
        if tweets.data:
            for tweet in reversed(tweets.data):
                message = f"https://twitter.com/{TWITTER_USERNAME}/status/{tweet.id}"
                await discord_channel.send(message)
                last_tweet_id = tweet.id
            await save_last_tweet_id(last_tweet_id)
    except tweepy.errors.TooManyRequests:
        logging.warning("Rate limit exceeded. Waiting for the next window.")
        await asyncio.sleep(60)
    except Exception as e:
        logging.exception("Unexpected error during tweet check:")

def main():
    try:
        client.run(DISCORD_TOKEN)
    except discord.errors.LoginFailure:
        logging.error("Invalid DISCORD_TOKEN. Please check your token.")
    except Exception as e:
        logging.exception("Error starting bot:")

if __name__ == "__main__":
    main()
