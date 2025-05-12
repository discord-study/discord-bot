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
            # 타임아웃 및 rate limit 처리 개선
            self.client_v2 = tweepy.Client(
                bearer_token=TWITTER_BEARER_TOKEN, 
                wait_on_rate_limit=True
            )
            
            # 타임아웃 시간 증가
            self.client_v2.session.request = functools.partial(
                self.client_v2.session.request, 
                timeout=30  # 30초 타임아웃으로 증가
            )
            
            # 사용자 ID 가져오기
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

    @tasks.loop(minutes=15.0)  # 5분에서 15분으로 증가하여 API 요청 빈도 감소
    async def check_tweets(self):
        """주기적으로 새 트윗 확인"""
        if not self.user_id or not self.client_v2:
            if not self.init_twitter():
                logging.warning("Twitter API 연결이 불가능합니다. 다음 시도까지 대기합니다.")
                return
        
        if not self.notify_channel:
            try:
                channel_id = int(TWITTER_NOTIFY_CHANNEL_ID)
                channel = self.bot.get_channel(channel_id)
                if channel:
                    self.notify_channel = channel
                else:
                    logging.warning(f"❌ 알림 채널을 찾을 수 없음: {channel_id}")
                    return
            except ValueError:
                logging.error(f"❌ 유효하지 않은 채널 ID: {TWITTER_NOTIFY_CHANNEL_ID}")
                return
        
        try:
            # API 요청 파라미터 수정
            params = {
                "id": self.user_id,
                "exclude": "retweets,replies",
                # tweet.fields 파라미터 수정 - 주의: API 버전에 따라 이 부분이 동작하지 않을 수 있음
                "expansions": "author_id",  # tweet.fields 대신 다른 파라미터 사용
                "max_results": 5  # 결과 수 감소
            }
            
            # 이전에 저장된 tweet_id가 있으면 since_id 파라미터 추가
            if self.latest_tweet_id:
                params["since_id"] = self.latest_tweet_id
            
            # 타임아웃과 함께 API 호출
            try:
                # API 호출을 실행 대기열에 제출
                loop = asyncio.get_event_loop()
                tweets_future = loop.run_in_executor(
                    None,
                    lambda: self.client_v2.get_users_tweets(**params)
                )
                
                # 타임아웃 시간 증가
                tweets = await asyncio.wait_for(tweets_future, timeout=30.0)
                
                # 트윗 데이터 처리
                if not tweets.data:
                    logging.info("새로운 트윗이 없습니다.")
                    return
                
                # 첫 실행이면 최신 트윗 ID만 저장하고 알림은 보내지 않음
                if not self.latest_tweet_id:
                    self.latest_tweet_id = tweets.data[0].id
                    logging.info(f"✅ 첫 실행: 최신 트윗 ID({self.latest_tweet_id})를 저장했습니다.")
                    return
                
                # 여러 트윗을 처리하기 위해 정렬 (오래된 것부터 처리)
                sorted_tweets = sorted(tweets.data, key=lambda tweet: tweet.id)
                
                for tweet in sorted_tweets:
                    # 트윗 ID가 이미 처리한 ID보다 큰 경우만 처리
                    if tweet.id <= self.latest_tweet_id:
                        continue
                        
                    # 트윗 URL 생성
                    tweet_url = f"https://twitter.com/{TWITTER_USERNAME}/status/{tweet.id}"
                    
                    # 알림 임베드 생성
                    embed = discord.Embed(
                        title=f"{TWITTER_USERNAME}님의 새 트윗",
                        description=tweet.text,
                        color=0x1DA1F2,
                        url=tweet_url
                    )
                    
                    # 생성 시간 정보가 있는 경우에만 처리
                    try:
                        if hasattr(tweet, 'created_at'):
                            created_at = tweet.created_at
                            korean_time = created_at + datetime.timedelta(hours=9)
                            time_str = korean_time.strftime("%Y-%m-%d %H:%M:%S")
                            embed.set_footer(text=f"작성 시간: {time_str}")
                    except AttributeError:
                        # 생성 시간 정보가 없으면 현재 시간 사용
                        now = datetime.datetime.now()
                        embed.set_footer(text=f"알림 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    await self.notify_channel.send(embed=embed)
                    logging.info(f"✅ 새 트윗 알림 전송 완료: {tweet.id}")
                    
                    # 처리한 트윗 ID 업데이트
                    self.latest_tweet_id = tweet.id
                
            except asyncio.TimeoutError:
                logging.warning("⏱️ Twitter API 요청 타임아웃. 다음 시도에서 재시도합니다.")
                return
            except tweepy.TooManyRequests as e:
                # Rate limit에 걸렸을 때 자동으로 대기하도록 설정
                retry_after = getattr(e, 'retry_after', 300)  # 기본값 5분
                logging.warning(f"❌ Rate limit exceeded. Waiting for {retry_after} seconds.")
                # 봇 실행을 멈추지 않기 위해 sleep은 사용하지 않음
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