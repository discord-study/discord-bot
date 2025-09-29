import discord
import tweepy
import logging
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from discord.ext import commands, tasks
from typing import Optional
from config import BEARER_TOKEN as TWITTER_BEARER_TOKEN
from config import TWITTER_USERNAME
from config import DISCORD_CHANNEL_ID as TWITTER_NOTIFY_CHANNEL_ID

# 로깅 설정
logger = logging.getLogger(__name__)

class Twitter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_id: Optional[str] = None
        self.latest_tweet_id: Optional[str] = None
        self.notify_channel: Optional[discord.TextChannel] = None
        self.last_check_time: Optional[datetime] = None
        self.check_tweets.start()

    async def cog_unload(self):
        """Cog 언로드 시 정리"""
        self.check_tweets.cancel()

    async def init_twitter(self) -> bool:
        """트위터 사용자 ID 초기화"""
        if self.user_id:
            return True

        try:
            headers = {
                "Authorization": f"Bearer {TWITTER_BEARER_TOKEN}",
                "User-Agent": "DiscordBot/1.0"
            }

            url = f"https://api.twitter.com/2/users/by/username/{TWITTER_USERNAME}"

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "data" in data:
                            self.user_id = data["data"]["id"]
                            logger.info(f"✅ Twitter 사용자 ID 초기화: {TWITTER_USERNAME} → {self.user_id}")
                            return True
                        else:
                            logger.error(f"❌ 사용자 데이터가 없습니다: {TWITTER_USERNAME}")
                    elif response.status == 401:
                        logger.error("❌ Twitter API 인증 실패 - Bearer 토큰을 확인하세요")
                    elif response.status == 429:
                        logger.warning("❌ Twitter API Rate Limit 초과")
                    else:
                        logger.error(f"❌ Twitter API 오류: {response.status}")

        except asyncio.TimeoutError:
            logger.error("❌ Twitter API 연결 타임아웃")
        except aiohttp.ClientError as e:
            logger.error(f"❌ Twitter API 연결 오류: {e}")
        except Exception as e:
            logger.error(f"❌ Twitter 초기화 중 예상치 못한 오류: {e}")

        return False

    @tasks.loop(minutes=10.0)
    async def check_tweets(self):
        """주기적으로 새 트윗 확인"""
        await self.bot.wait_until_ready()

        # 초기화 확인
        if not await self.init_twitter():
            logger.warning("Twitter API 초기화 실패. 다음 시도까지 대기합니다.")
            return

        # 알림 채널 설정
        if not self.notify_channel:
            try:
                self.notify_channel = self.bot.get_channel(TWITTER_NOTIFY_CHANNEL_ID)
                if not self.notify_channel:
                    logger.error(f"❌ 알림 채널을 찾을 수 없음: {TWITTER_NOTIFY_CHANNEL_ID}")
                    return
            except Exception as e:
                logger.error(f"❌ 채널 설정 오류: {e}")
                return

        try:
            await self._fetch_and_process_tweets()

        except Exception as e:
            logger.error(f"❌ 트윗 확인 중 예상치 못한 오류: {e}")

    async def _fetch_and_process_tweets(self):
        """트윗 가져오기 및 처리"""
        try:
            headers = {
                "Authorization": f"Bearer {TWITTER_BEARER_TOKEN}",
                "User-Agent": "DiscordBot/1.0"
            }

            # API 파라미터 설정
            params = {
                "max_results": "5",
                "exclude": "retweets,replies",
                "tweet.fields": "created_at,public_metrics"
            }

            if self.latest_tweet_id:
                params["since_id"] = self.latest_tweet_id

            url = f"https://api.twitter.com/2/users/{self.user_id}/tweets"

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        await self._process_tweets_data(data)

                    elif response.status == 401:
                        logger.error("❌ Twitter API 인증 실패")
                    elif response.status == 429:
                        logger.warning("❌ Twitter API Rate Limit 초과")
                    else:
                        logger.error(f"❌ Twitter API 오류: {response.status}")
                        error_text = await response.text()
                        logger.error(f"응답 내용: {error_text}")

        except asyncio.TimeoutError:
            logger.error("❌ Twitter API 요청 타임아웃")
        except aiohttp.ClientError as e:
            logger.error(f"❌ Twitter API 연결 오류: {e}")
        except Exception as e:
            logger.error(f"❌ 트윗 가져오기 중 오류: {e}")

    async def _process_tweets_data(self, data: dict):
        """트윗 데이터 처리"""
        try:
            if "data" not in data or not data["data"]:
                logger.info("새로운 트윗이 없습니다.")
                return

            tweets = data["data"]

            # 첫 실행시 최신 트윗 ID만 저장
            if not self.latest_tweet_id:
                self.latest_tweet_id = tweets[0]["id"]
                logger.info(f"✅ 첫 실행: 최신 트윗 ID({self.latest_tweet_id}) 저장")
                return

            # 오래된 트윗부터 처리
            sorted_tweets = sorted(tweets, key=lambda t: t["id"])

            for tweet in sorted_tweets:
                if int(tweet["id"]) <= int(self.latest_tweet_id):
                    continue

                await self._send_tweet_notification(tweet)
                self.latest_tweet_id = tweet["id"]

        except Exception as e:
            logger.error(f"❌ 트윗 데이터 처리 중 오류: {e}")

    async def _send_tweet_notification(self, tweet: dict):
        """트윗 알림 전송"""
        try:
            tweet_id = tweet["id"]
            tweet_text = tweet["text"]
            tweet_url = f"https://twitter.com/{TWITTER_USERNAME}/status/{tweet_id}"

            embed = discord.Embed(
                title=f"{TWITTER_USERNAME}님의 새 트윗",
                description=tweet_text,
                color=0x1DA1F2,
                url=tweet_url
            )

            # 생성 시간 처리
            if "created_at" in tweet:
                try:
                    created_at = datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00"))
                    korean_time = created_at + timedelta(hours=9)
                    time_str = korean_time.strftime("%Y-%m-%d %H:%M:%S")
                    embed.set_footer(text=f"작성 시간: {time_str}")
                except Exception as e:
                    logger.warning(f"시간 파싱 오류: {e}")

            await self.notify_channel.send(embed=embed)
            logger.info(f"✅ 새 트윗 알림 전송 완료: {tweet_id}")

        except discord.HTTPException as e:
            logger.error(f"❌ Discord 메시지 전송 오류: {e}")
        except Exception as e:
            logger.error(f"❌ 트윗 알림 전송 중 오류: {e}")

    @discord.app_commands.command(name="twitter_debug", description="Twitter API 연결 상태를 디버깅합니다")
    async def debug_twitter(self, interaction: discord.Interaction):
        """트위터 디버깅용 명령어"""
        try:
            await interaction.response.defer()

            await interaction.followup.send("Twitter API 연결 상태를 확인합니다...")

            # 초기화 확인
            init_success = await self.init_twitter()

            debug_msg = f"""**Twitter 디버그 정보**
초기화 상태: {'성공' if init_success else '실패'}
현재 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

            await interaction.followup.send(debug_msg)

            if init_success:
                await interaction.followup.send("Twitter API 연결이 정상적으로 작동합니다.")
            else:
                await interaction.followup.send("Twitter API 연결에 문제가 있습니다. Bearer 토큰을 확인하세요.")

        except Exception as e:
            logger.error(f"❌ Twitter 디버그 명령어 실행 중 오류: {e}")
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ 디버그 실행 중 오류: {str(e)}")
            else:
                await interaction.response.send_message(f"❌ 디버그 실행 중 오류: {str(e)}")

async def setup(bot):
    await bot.add_cog(Twitter(bot))