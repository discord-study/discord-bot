import logging
import discord
import os
import time
from discord.ext import commands
from dotenv import load_dotenv
from schedule import send_schedule
from imgcrawl import send_random_image, get_random_image

# 환경 변수 로드
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ `commands.Bot` 사용 (슬래시 명령어 지원)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logging.info(f"✅ Bot logged in as {bot.user}")
    await bot.tree.sync()
    logging.info("✅ Slash commands synced")

    if not send_schedule.is_running():
        send_schedule.start(bot, DISCORD_CHANNEL_ID)
    
    if not send_random_image.is_running():
        send_random_image.start(bot, DISCORD_CHANNEL_ID)

# ✅ Ping-Pong 명령어
@bot.command()
async def ping(ctx):
    """Ping 테스트"""
    start_time = time.monotonic()
    message = await ctx.send("🏓 Pong! 측정 중...")
    end_time = time.monotonic()
    latency = round((end_time - start_time) * 1000)
    await message.edit(content=f"🏓 Pong! ({latency}ms)")

# ✅ 이미지 크롤링 명령어
@bot.command()
async def imgcrawl(ctx):
    """네코마시로 사이트에서 전체 이미지 중 랜덤으로 1개 가져오기"""
    image_url = await get_random_image()
    if image_url:
        await ctx.send(image_url)
    else:
        await ctx.send("❌ 이미지를 찾을 수 없습니다.")

# ✅ 봇 실행
def main():
    if not DISCORD_TOKEN:
        logging.error("❌ DISCORD_TOKEN이 설정되지 않았습니다! .env 파일을 확인하세요.")
        return

    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logging.exception("❌ Error starting bot:")

if __name__ == "__main__":
    main()
