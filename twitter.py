import discord
from discord.ext import commands, tasks
import tweepy
import logging
import asyncio
import functools
import datetime
# 변수명 일치시키기
from config import BEARER_TOKEN as TWITTER_BEARER_TOKEN
from config import TWITTER_USERNAME
from config import DISCORD_CHANNEL_ID as TWITTER_NOTIFY_CHANNEL_ID

class Twitter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client_v2 = None
        self.user_id = None
        self.latest_tweet_id = None
        self.notify_channel = None
        self.check_tweets.start()
    
    def init_twitter(self):
        """트위터 클라이언트 초기화"""
        try:
            self.client_v2 = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN, wait_on_rate_limit=True)
            # 타임아웃 설정
            self.client_v2.session.request = functools.partial(
                self.client_v2.session.request, 
                timeout=10  # 10초 타임아웃
            )
            
            # 사용자 ID 가져오기 (with timeout)
            try:
                user_data = self.client_v2.get_user(username=TWITTER_USERNAME)
                if user_data and user_data.data:
                    self.user_id = user_data.data.id
                    logging.info(f"✅ Twitter user id for {TWITTER_USERNAME}: {self.user_id}")
                    return True
                else:
                    logging.error(f"❌ Twitter 사용자를 찾을 수 없음: {TWITTER_USERNAME}")
                    return False
            except Exception as e:
                logging.error(f"❌ Twitter 사용자 ID 가져오기 실패: {e}")
                return False
        except Exception as e:
            logging.error(f"❌ Twitter 클라이언트 초기화 실패: {e}")
            return False

    @tasks.loop(minutes=5.0)
    async def check_tweets(self):
        """주기적으로 새 트윗 확인"""
        if not self.user_id or not self.client_v2:
            if not self.init_twitter():
                logging.warning("Twitter API 연결이 불가능합니다. 다음 시도까지 대기합니다.")
                return
        
        if not self.notify_channel:
            channel = self.bot.get_channel(TWITTER_NOTIFY_CHANNEL_ID)
            if channel:
                self.notify_channel = channel
            else:
                logging.warning(f"❌ 알림 채널을 찾을 수 없음: {TWITTER_NOTIFY_CHANNEL_ID}")
                return
        
        try:
            # 비동기로 API 요청 처리
            params = {
                "id": self.user_id,
                "exclude": ["retweets", "replies"],
                "tweet.fields": ["created_at"],
                "max_results": 5
            }
            
            # 타임아웃과 함께 API 호출
            try:
                # API 호출을 실행 대기열에 제출하여 메인 루프 차단 방지
                loop = asyncio.get_event_loop()
                tweets_future = loop.run_in_executor(
                    None,
                    lambda: self.client_v2.get_users_tweets(**params)
                )
                
                # 타임아웃 적용
                tweets = await asyncio.wait_for(tweets_future, timeout=15.0)
                
                # 트윗 데이터 처리
                if not tweets.data:
                    return
                
                newest_tweet = tweets.data[0]
                
                if self.latest_tweet_id and self.latest_tweet_id == newest_tweet.id:
                    return
                
                # 첫 실행이면 최신 트윗 ID만 저장하고 알림은 보내지 않음
                if not self.latest_tweet_id:
                    self.latest_tweet_id = newest_tweet.id
                    return
                
                # 새 트윗이 있으면 알림
                self.latest_tweet_id = newest_tweet.id
                
                # 생성 시간 파싱
                created_at = newest_tweet.created_at
                korean_time = created_at + datetime.timedelta(hours=9)
                time_str = korean_time.strftime("%Y-%m-%d %H:%M:%S")
                
                # 트윗 URL 생성
                tweet_url = f"https://twitter.com/{TWITTER_USERNAME}/status/{newest_tweet.id}"
                
                # 알림 임베드 생성
                embed = discord.Embed(
                    title=f"{TWITTER_USERNAME}님의 새 트윗",
                    description=newest_tweet.text,
                    color=0x1DA1F2,
                    url=tweet_url
                )
                embed.set_footer(text=f"작성 시간: {time_str}")
                
                await self.notify_channel.send(embed=embed)
                logging.info(f"✅ 새 트윗 알림 전송 완료: {newest_tweet.id}")
                
            except asyncio.TimeoutError:
                logging.warning("⏱️ Twitter API 요청 타임아웃. 다음 시도에서 재시도합니다.")
                return
            except tweepy.TooManyRequests:
                logging.warning("❌ Rate limit exceeded. Waiting for the next window.")
                return
            except Exception as e:
                logging.error(f"❌ 트윗 가져오기 오류: {e}")
                # 네트워크 문제로 클라이언트 재설정
                self.client_v2 = None
                return
                
        except Exception as e:
            logging.error(f"❌ 트윗 확인 중 예상치 못한 오류: {e}")
            
    @check_tweets.before_loop
    async def before_check_tweets(self):
        """봇이 준비될 때까지 대기"""
        await self.bot.wait_until_ready()
        logging.info("✅ Twitter 모니터링 시작")
        self.init_twitter()
    
    def cog_unload(self):
        """Cog가 언로드될 때 task 정리"""
        self.check_tweets.cancel()

async def setup(bot):
    await bot.add_cog(Twitter(bot))