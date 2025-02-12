import logging
import discord
import time
import os
import random
import requests
from discord.ext import commands
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

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

# ✅ Ping-Pong 명령어
@bot.command()
async def ping(ctx):
    """Ping 테스트"""
    start_time = time.monotonic()
    message = await ctx.send("🏓 Pong! 측정 중...")
    end_time = time.monotonic()
    latency = round((end_time - start_time) * 1000)
    await message.edit(content=f"🏓 Pong! ({latency}ms)")

# ✅ API에서 이미지 크롤링
@bot.command()
async def imgcrawl(ctx):
    """네코마시로 사이트에서 전체 이미지 중 랜덤으로 1개 가져오기"""
    try:
        # ✅ 1️⃣ 전체 이미지 개수 가져오기
        response = requests.get(COUNT_API_URL, timeout=10)
        response.raise_for_status()
        
        total_images = int(response.text.strip())  # 숫자만 추출
        if total_images == 0:
            await ctx.send("❌ 이미지가 없습니다.")
            return

        # ✅ 2️⃣ 랜덤 페이지 선택
        total_pages = (total_images // 30) + 1  # 한 페이지당 30개
        random_page = random.randint(1, total_pages)

        # ✅ 3️⃣ 랜덤 페이지에서 이미지 가져오기
        post_response = requests.get(POST_API_URL.format(random_page), timeout=10)
        post_response.raise_for_status()

        images = post_response.json().get("post", [])
        if not images:
            await ctx.send("❌ 이미지를 찾을 수 없습니다.")
            return

        # ✅ 4️⃣ 랜덤 이미지 선택
        random_img_data = random.choice(images)
        image_url = IMAGE_BASE_URL + random_img_data["src"]

        # ✅ 5️⃣ 메시지 수정하여 이미지 출력
        await ctx.send(f"🖼 랜덤 이미지:\n{image_url}")

    except requests.exceptions.RequestException as e:
        await ctx.send(f"❌ 크롤링 중 오류 발생: {e}")

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
