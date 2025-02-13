import logging
import requests
from discord.ext import tasks
from datetime import datetime, timedelta

# ✅ API 엔드포인트
STELLARS_API_URL = "https://stellight.fans/api/v1/stellars"
SCHEDULES_API_URL = "https://stellight.fans/api/v1/schedules?startDateTimeAfter={}&startDateTimeBefore={}"

# ✅ 방송인 정보 가져오기
def get_stellars():
    response = requests.get(STELLARS_API_URL, timeout=10)
    if response.status_code == 200:
        return {s["id"]: s["nameKor"] for s in response.json()}
    return {}

# ✅ 특정 날짜의 방송 일정 가져오기
def get_schedules(date):
    date_str = date.strftime("%Y-%m-%dT00:00:00")
    next_date_str = (date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
    
    response = requests.get(SCHEDULES_API_URL.format(date_str, next_date_str), timeout=10)
    if response.status_code == 200:
        return response.json()
    return []

# ✅ 일정 메시지 포맷
def format_schedule_message(schedules, stellars):
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
async def send_schedule(bot, channel_id):
    await bot.wait_until_ready()
    now = datetime.now()
    if now.hour == 9 and now.minute == 0:
        logging.info("🔔 9시가 되어 방송 일정을 전송합니다.")
        channel = bot.get_channel(channel_id)
        if channel:
            stellars = get_stellars()
            schedules = get_schedules(now)
            message = format_schedule_message(schedules, stellars)
            await channel.send(message)
