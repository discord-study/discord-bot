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
        self.stellars = self.get_stellars()  # 방송인 정보 캐싱
        self.send_schedule.start()  # ✅ 여기서 tasks.loop를 시작하면 문제 해결됨

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
    def format_schedule_message(self, schedules):
        if not schedules:
            return "📢 오늘 예정된 방송이 없습니다."

        message = "**📅 오늘의 방송 일정**\n"
        schedule_dict = {}

        for schedule in schedules:
            name = self.stellars.get(schedule["stellarId"], "알 수 없음")
            time = datetime.fromisoformat(schedule["startDateTime"]).strftime("%H:%M")
            title = schedule["title"]

            # 🚨 "휴방" 일정이 있으면, 같은 사람의 다른 일정 제거
            if name in schedule_dict and "휴방" in schedule_dict[name]["titles"]:
                continue

            # 🚨 "휴방" 일정이 먼저 나오면 덮어쓰기
            if "휴방" in title:
                schedule_dict[name] = {"time": time, "titles": ["휴방"]}
                continue

            # 🚨 "방송 예정"이 여러 개 나오지 않도록 방지
            if "방송 예정" in title:
                if name in schedule_dict and any("방송 예정" in t for t in schedule_dict[name]["titles"]):
                    continue

            # ✅ 방송 일정 저장
            if name not in schedule_dict:
                schedule_dict[name] = {"time": time, "titles": []}
            
            schedule_dict[name]["titles"].append(title)

        # ✅ 메시지 생성
        for name, info in schedule_dict.items():
            joined_titles = ", ".join(info["titles"])
            message += f"🕒 `{info['time']}` | **{name}** - {joined_titles}\n"

        return message

    # ✅ 자동으로 방송 일정 전송 (self 사용 X)
    @tasks.loop(minutes=1)
    async def send_schedule(self):
        await self.bot.wait_until_ready()
        now = datetime.now()
        if now.hour == 10 and now.minute == 0:
            logging.info("🔔 10시가 되어 방송 일정을 전송합니다.")
            channel = self.bot.get_channel(DISCORD_CHANNEL_ID)
            if channel:
                schedules = self.get_schedules(now)
                message = self.format_schedule_message(schedules)
                await channel.send(message)

    # ✅ !schedule 명령어 추가
    @commands.command(name="schedule")
    async def show_schedule(self, ctx):
        """오늘의 방송 일정을 수동으로 확인합니다."""
        schedules = self.get_schedules(datetime.now())
        message = self.format_schedule_message(schedules)
        await ctx.send(message)

# ✅ Cog 등록
async def setup(bot):
    await bot.add_cog(Schedule(bot))
