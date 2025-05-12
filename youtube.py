import os
import logging
import asyncio
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from discord.ext import commands, tasks

# config.py에서 설정 정보 가져오기
from config import YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID, DISCORD_YOUTUBE_CHANNEL_ID

class YouTube(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        self.channel_id = YOUTUBE_CHANNEL_ID
        self.discord_channel_id = DISCORD_YOUTUBE_CHANNEL_ID
        self.latest_video_id = None
        self.check_youtube.start()

    async def cog_unload(self):
        self.check_youtube.cancel()

    @tasks.loop(minutes=60)  # 1시간마다 확인
    async def check_youtube(self):
        await self.bot.wait_until_ready()
        try:
            channel = self.bot.get_channel(self.discord_channel_id)
            if not channel:
                logging.error(f"YouTube 알림 채널을 찾을 수 없습니다: {self.discord_channel_id}")
                return

            # 최신 동영상 정보 가져오기
            request = self.youtube.search().list(
                part="id,snippet",
                channelId=self.channel_id,
                maxResults=1,
                order="date",
                type="video"
            )
            response = request.execute()

            if not response["items"]:
                logging.info("새로운 YouTube 동영상이 없습니다.")
                return

            video_id = response["items"][0]["id"]["videoId"]
            video_title = response["items"][0]["snippet"]["title"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            # 첫 실행이거나 새로운 동영상이 올라왔을 경우 알림 전송
            if self.latest_video_id is None or video_id != self.latest_video_id:
                self.latest_video_id = video_id
                await channel.send(f"새로운 YouTube 동영상: {video_title} - {video_url}")
                logging.info(f"YouTube 알림 전송 완료: {video_title} - {video_url}")

        except HttpError as e:
            logging.error(f"YouTube API 오류 발생: {e}")
        except Exception as e:
            logging.error(f"YouTube 알림 확인 중 오류 발생: {e}")

    @check_youtube.before_loop
    async def before_check_youtube(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(YouTube(bot))