import logging
import discord
import asyncio
import os
import random
import requests
import time
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime

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

# ✅ API 엔드포인트
COUNT_API_URL = "https://nenekomashiro.com/image/list/count?code=999&search="
POST_API_URL = "https://nenekomashiro.com/image/post?page={}&perPage=30&sort=0&code=999&search="
IMAGE_BASE_URL = "https://nenekomashiro.com/"

# ✅ 제외할 파일 리스트
EXCLUDED_IMAGES = {
    "extension.png",
    "login.png",
    "option.png",
    "edit.png",
    "like.png",
    "profile6.png",
    "scroll.png"
}

@bot.event
async def on_ready():
    logging.info(f"✅ Bot logged in as {bot.user}")
    await bot.tree.sync()
    logging.info("✅ Slash commands synced")
    if not send_random_image.is_running():
        send_random_image.start()

# ✅ Ping-Pong 명령어
@bot.command()
async def ping(ctx):
    """Ping 테스트"""
    start_time = time.monotonic()
    message = await ctx.send("🏓 Pong! 측정 중...")
    end_time = time.monotonic()
    latency = round((end_time - start_time) * 1000)
    await message.edit(content=f"🏓 Pong! ({latency}ms)")

# ✅ API에서 랜덤 이미지 가져오기
async def get_random_image():
    try:
        response = requests.get(COUNT_API_URL, timeout=10)
        response.raise_for_status()
        total_images = int(response.text.strip())
        if total_images == 0:
            return None

        total_pages = (total_images // 30) + 1
        random_page = random.randint(1, total_pages)

        post_response = requests.get(POST_API_URL.format(random_page), timeout=10)
        post_response.raise_for_status()
        images = post_response.json().get("post", [])
        if not images:
            return None

        random_img_data = random.choice(images)
        return IMAGE_BASE_URL + random_img_data["src"]
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ 크롤링 중 오류 발생: {e}")
        return None

# ✅ 이미지 크롤링 명령어
@bot.command()
async def imgcrawl(ctx):
    """네코마시로 사이트에서 전체 이미지 중 랜덤으로 1개 가져오기"""
    image_url = await get_random_image()
    if image_url:
        await ctx.send(image_url)
    else:
        await ctx.send("❌ 이미지를 찾을 수 없습니다.")

# ✅ 매일 10시에 자동으로 이미지 보내기
@tasks.loop(seconds=60)
async def send_random_image():
    await bot.wait_until_ready()
    now = datetime.now()
    if now.hour == 10 and now.minute == 0:
        logging.info("🔔 10시가 되어 이미지 전송을 시작합니다.")
        channel = bot.get_channel(DISCORD_CHANNEL_ID)
        if channel:
            image_url = await get_random_image()
            if image_url:
                await channel.send(image_url)

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
