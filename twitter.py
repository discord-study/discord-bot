import logging
import aiofiles
import asyncio
import tweepy
from config import BEARER_TOKEN, TWITTER_USERNAME, DISCORD_CHANNEL_ID
from discord.ext import tasks

CACHE_FILE = "last_tweet_id.txt"

client_v2 = tweepy.Client(bearer_token=BEARER_TOKEN)
twitter_user_id = None  # 이후 init_twitter()에서 설정

async def load_last_tweet_id():
    try:
        async with aiofiles.open(CACHE_FILE, "r") as f:
            return (await f.read()).strip()
    except FileNotFoundError:
        return None

async def save_last_tweet_id(tweet_id):
    async with aiofiles.open(CACHE_FILE, "w") as f:
        await f.write(str(tweet_id))

def init_twitter():
    """트위터 사용자 ID를 가져오는 함수"""
    global twitter_user_id
    user_data = client_v2.get_user(username=TWITTER_USERNAME)
    if user_data and user_data.data:
        twitter_user_id = user_data.data.id
        logging.info(f"✅ Twitter user id for {TWITTER_USERNAME}: {twitter_user_id}")
    else:
        logging.error("❌ Twitter 사용자 정보를 가져올 수 없습니다.")
        raise Exception("Twitter 초기화 실패")

def start_tweet_loop(bot_channel):
    """주기적 트윗 체크 작업을 시작합니다."""
    @tasks.loop(minutes=5)
    async def check_tweets():
        global twitter_user_id
        try:
            last_tweet_id = await load_last_tweet_id()
            tweets = client_v2.get_users_tweets(
                id=twitter_user_id,
                max_results=5,
                since_id=last_tweet_id,
                tweet_fields=["created_at", "text"]
            )
            if tweets.data:
                new_last_tweet_id = last_tweet_id
                for tweet in reversed(tweets.data):
                    message = f"https://twitter.com/{TWITTER_USERNAME}/status/{tweet.id}"
                    await bot_channel.send(message)
                    new_last_tweet_id = tweet.id
                await save_last_tweet_id(new_last_tweet_id)
            else:
                logging.info("✅ 새로운 트윗이 없습니다.")
        except tweepy.errors.TooManyRequests:
            logging.warning("❌ Rate limit exceeded. Waiting for the next window.")
            await asyncio.sleep(60)
        except Exception as e:
            logging.exception("❌ Unexpected error during tweet check:")

    check_tweets.start()
