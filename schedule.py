import logging
import requests
import discord
from discord.ext import tasks, commands
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# 환경 변수 로드
load_dotenv()
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

# ✅ API 엔드포인트
STELLARS_API_URL = "https://stellight.fans/api/v1/stellars"
SCHEDULES_API_URL = "https://stellight.fans/api/v1/schedules?startDateTimeAfter={}&startDateTimeBefore={}"

class Schedule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.send_schedule.start()

    # ✅ 방송인 정보 가져오기
    def get_stellars(self):
        response = requests.get(STELLARS_API_URL, timeout=10)
        if response.status_code == 200:
            return {s["id"]: s["nameKor"] for s in response.json()}
        return {}

    # ✅ 특정 날짜의 방송 일정 가져오기
    def get_schedules(self, date):
        date_str = date.strftime("%Y-%m-%dT00:00:00")
        next_date_str = (date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")

        response = requests.get(SCHEDULES_API_URL.format(date_str, next_date_str), timeout=10)
        if response.status_code == 200:
            return response.json()
        return []

    # ✅ 일정 메시지 포맷
    def format_schedule_message(self, schedules, stellars):
        if not schedules:
            return "📢 오늘 예정된 방송이 없습니다."

        message = "**📅 오늘의 방송 일정**\n"
        for schedule in schedules:
            name = stellars.get(schedule["stellarId"], "알 수 없음")
            time = datetime.fromisoformat(schedule["startDateTime"]).strftime("%H:%M")
            message += f"🕒 `{time}` | **{name}** - {schedule['title']}\n"
        return message

    # ✅ 자동으로 방송 일정 전송
    @tasks.loop(minutes=1)
    async def send_schedule(self):
        await self.bot.wait_until_ready()
        now = datetime.now()
        if now.hour == 1 and now.minute == 0:
            logging.info("🔔 10시가 되어 방송 일정을 전송합니다.")
            channel = self.bot.get_channel(DISCORD_CHANNEL_ID)
            if channel:
                stellars = self.get_stellars()
                schedules = self.get_schedules(now)
                message = self.format_schedule_message(schedules, stellars)
                await channel.send(message)

    # ✅ !schedule 명령어 추가
    @commands.command(name="schedule")
    async def show_schedule(self, ctx):
        """오늘의 방송 일정을 수동으로 확인합니다."""
        stellars = self.get_stellars()
        schedules = self.get_schedules(datetime.now())
        message = self.format_schedule_message(schedules, stellars)
        await ctx.send(message)

# ✅ Cog 등록
async def setup(bot):
    await bot.add_cog(Schedule(bot))
