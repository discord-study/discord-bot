import os
import logging
import asyncio
import discord
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from discord.ext import commands, tasks
from typing import Optional

# config.py에서 설정 정보 가져오기
from config import YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID, DISCORD_YOUTUBE_CHANNEL_ID

# 로깅 설정
logger = logging.getLogger(__name__)

class YouTube(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.youtube: Optional[object] = None
        self.channel_id = YOUTUBE_CHANNEL_ID
        self.discord_channel_id = DISCORD_YOUTUBE_CHANNEL_ID
        self.latest_video_id: Optional[str] = None
        self.notify_channel: Optional[discord.TextChannel] = None
        if YOUTUBE_API_KEY and YOUTUBE_CHANNEL_ID:
            self.check_youtube.start()
        else:
            logger.warning("YouTube API 키 또는 채널 ID가 없어 YouTube 모니터링을 시작하지 않습니다.")

    async def cog_unload(self):
        """Cog 언로드 시 정리"""
        if hasattr(self, 'check_youtube'):
            self.check_youtube.cancel()

    def init_youtube_client(self) -> bool:
        """YouTube API 클라이언트 초기화"""
        if self.youtube:
            return True

        try:
            if not YOUTUBE_API_KEY:
                logger.error("❌ YouTube API 키가 설정되지 않았습니다.")
                return False

            self.youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
            logger.info("✅ YouTube API 클라이언트 초기화 완료")
            return True

        except Exception as e:
            logger.error(f"❌ YouTube API 클라이언트 초기화 실패: {e}")
            return False

    @tasks.loop(minutes=30)  # 30분마다 확인 (API 할당량 고려)
    async def check_youtube(self):
        """주기적으로 새 YouTube 동영상 확인"""
        await self.bot.wait_until_ready()

        # YouTube API 클라이언트 초기화
        if not self.init_youtube_client():
            logger.warning("YouTube API 클라이언트 초기화 실패. 다음 시도까지 대기합니다.")
            return

        # 알림 채널 설정
        if not self.notify_channel:
            try:
                self.notify_channel = self.bot.get_channel(self.discord_channel_id)
                if not self.notify_channel:
                    logger.error(f"❌ YouTube 알림 채널을 찾을 수 없습니다: {self.discord_channel_id}")
                    return
            except Exception as e:
                logger.error(f"❌ YouTube 채널 설정 오류: {e}")
                return

        try:
            await self._check_latest_videos()

        except Exception as e:
            logger.error(f"❌ YouTube 동영상 확인 중 예상치 못한 오류: {e}")

    async def _check_latest_videos(self):
        """최신 동영상 확인"""
        try:
            # 최신 동영상 정보 가져오기
            request = self.youtube.search().list(
                part="id,snippet",
                channelId=self.channel_id,
                maxResults=1,
                order="date",
                type="video",
                publishedAfter=(datetime.now() - timedelta(hours=2)).isoformat() + 'Z'  # 최근 2시간 내 동영상
            )

            # API 호출을 비동기로 실행
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, request.execute)

            if not response.get("items"):
                logger.debug("새로운 YouTube 동영상이 없습니다.")
                return

            video_data = response["items"][0]
            video_id = video_data["id"]["videoId"]
            video_title = video_data["snippet"]["title"]
            video_description = video_data["snippet"]["description"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            # 첫 실행시 최신 동영상 ID만 저장
            if self.latest_video_id is None:
                self.latest_video_id = video_id
                logger.info(f"✅ YouTube 첫 실행: 최신 동영상 ID({video_id}) 저장")
                return

            # 새로운 동영상이 있는 경우 알림 전송
            if video_id != self.latest_video_id:
                await self._send_video_notification(video_id, video_title, video_description, video_url)
                self.latest_video_id = video_id

        except HttpError as e:
            if e.resp.status == 403:
                logger.error("❌ YouTube API 할당량 초과 또는 권한 없음")
            elif e.resp.status == 400:
                logger.error("❌ YouTube API 요청 매개변수 오류")
            else:
                logger.error(f"❌ YouTube API HTTP 오류: {e}")
        except Exception as e:
            logger.error(f"❌ YouTube 동영상 확인 중 오류: {e}")

    async def _send_video_notification(self, video_id: str, title: str, description: str, url: str):
        """동영상 알림 전송"""
        try:
            # 설명 길이 제한 (Discord 임베드 제한 고려)
            if len(description) > 300:
                description = description[:297] + "..."

            embed = discord.Embed(
                title="🎥 새로운 YouTube 동영상!",
                description=f"**{title}**",
                color=0xFF0000,  # YouTube 빨간색
                url=url
            )

            if description:
                embed.add_field(name="설명", value=description, inline=False)

            embed.set_footer(text=f"동영상 ID: {video_id}")
            embed.timestamp = datetime.now()

            await self.notify_channel.send(embed=embed)
            logger.info(f"✅ YouTube 알림 전송 완료: {title}")

        except discord.HTTPException as e:
            logger.error(f"❌ Discord 메시지 전송 오류: {e}")
        except Exception as e:
            logger.error(f"❌ YouTube 알림 전송 중 오류: {e}")

    @discord.app_commands.command(name="youtube_debug", description="YouTube API 연결 상태를 디버깅합니다")
    async def debug_youtube(self, interaction: discord.Interaction):
        """YouTube 디버깅용 명령어"""
        try:
            await interaction.response.defer()

            await interaction.followup.send("🔍 YouTube API 연결 상태를 확인합니다...")

            init_success = self.init_youtube_client()

            debug_msg = f"""**🔍 YouTube 디버그 정보**
🔑 API 키: {'설정됨' if YOUTUBE_API_KEY else '없음'}
📺 채널 ID: {YOUTUBE_CHANNEL_ID or '없음'}
🆔 최신 동영상 ID: {self.latest_video_id or '없음'}
📍 알림 채널: <#{self.discord_channel_id}>
✅ 초기화 상태: {'성공' if init_success else '실패'}
🕒 현재 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

            await interaction.followup.send(debug_msg)

            if init_success:
                await interaction.followup.send("✅ YouTube API 연결이 정상적으로 작동합니다.")
            else:
                await interaction.followup.send("❌ YouTube API 연결에 문제가 있습니다. API 키를 확인하세요.")

        except Exception as e:
            logger.error(f"❌ YouTube 디버그 명령어 실행 중 오류: {e}")
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ 디버그 실행 중 오류: {str(e)}")
            else:
                await interaction.response.send_message(f"❌ 디버그 실행 중 오류: {str(e)}")

async def setup(bot):
    await bot.add_cog(YouTube(bot))