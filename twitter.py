import logging
import aiofiles
import asyncio
import tweepy
from config import BEARER_TOKEN, TWITTER_USERNAME, DISCORD_CHANNEL_ID
from discord.ext import tasks, commands

CACHE_FILE = "last_tweet_id.txt"

# Cog 클래스로 변환
class TwitterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client_v2 = tweepy.Client(bearer_token=BEARER_TOKEN)
        self.twitter_user_id = None
        self.tweet_check_task = None
        
    async def load_last_tweet_id(self):
        try:
            async with aiofiles.open(CACHE_FILE, "r") as f:
                return (await f.read()).strip()
        except FileNotFoundError:
            return None

    async def save_last_tweet_id(self, tweet_id):
        async with aiofiles.open(CACHE_FILE, "w") as f:
            await f.write(str(tweet_id))

    def init_twitter(self):
        """트위터 사용자 ID를 가져오는 함수"""
        user_data = self.client_v2.get_user(username=TWITTER_USERNAME)
        if user_data and user_data.data:
            self.twitter_user_id = user_data.data.id
            logging.info(f"✅ Twitter user id for {TWITTER_USERNAME}: {self.twitter_user_id}")
        else:
            logging.error("❌ Twitter 사용자 정보를 가져올 수 없습니다.")
            raise Exception("Twitter 초기화 실패")

    @tasks.loop(minutes=5)
    async def check_tweets(self):
        try:
            last_tweet_id = await self.load_last_tweet_id()
            
            # API 요청에 since_id 파라미터 조건부 포함
            params = {
                "id": self.twitter_user_id,
                "max_results": 5,
                "tweet_fields": ["created_at", "text"]
            }
            
            # last_tweet_id가 있을 때만 since_id 추가
            if last_tweet_id:
                params["since_id"] = last_tweet_id
            
            tweets = self.client_v2.get_users_tweets(**params)
            
            # 채널 가져오기
            channel = self.bot.get_channel(int(DISCORD_CHANNEL_ID))
            if not channel:
                logging.error(f"❌ Discord 채널({DISCORD_CHANNEL_ID})을 찾을 수 없습니다.")
                return
                
            if tweets.data:
                # 첫 실행 시 (last_tweet_id가 None일 때) 최신 트윗 ID만 저장하고 메시지는 보내지 않음
                if last_tweet_id is None:
                    newest_tweet_id = tweets.data[0].id
                    await self.save_last_tweet_id(newest_tweet_id)
                    logging.info(f"✅ 첫 실행: 최신 트윗 ID({newest_tweet_id})를 저장했습니다.")
                else:
                    # 기존 실행 시에는 정상적으로 모든 새 트윗 처리
                    new_last_tweet_id = last_tweet_id
                    for tweet in reversed(tweets.data):
                        message = f"https://twitter.com/{TWITTER_USERNAME}/status/{tweet.id}"
                        await channel.send(message)
                        new_last_tweet_id = tweet.id
                    await self.save_last_tweet_id(new_last_tweet_id)
                    logging.info(f"✅ {len(tweets.data)}개의 새 트윗을 전송했습니다.")
            else:
                logging.info("✅ 새로운 트윗이 없습니다.")
        except tweepy.errors.TooManyRequests:
            logging.warning("❌ Rate limit exceeded. Waiting for the next window.")
            await asyncio.sleep(60)
        except Exception as e:
            logging.exception("❌ Unexpected error during tweet check:")

    @check_tweets.before_loop
    async def before_check_tweets(self):
        await self.bot.wait_until_ready()
        try:
            self.init_twitter()
        except Exception as e:
            logging.error(f"❌ Twitter 초기화 실패: {e}")
            return
            
        logging.info("✅ Twitter 모니터링 시작")

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.check_tweets.is_running():
            self.check_tweets.start()

# 필수 setup 함수 추가
async def setup(bot):
    await bot.add_cog(TwitterCog(bot))