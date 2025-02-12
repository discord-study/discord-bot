import logging
import discord
import time
import os
import random
import requests
from discord.ext import commands
from dotenv import load_dotenv
from twitter import init_twitter, start_tweet_loop
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


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

    # ✅ 트위터 초기화 및 루프 시작
    try:
        init_twitter()
        channel = bot.get_channel(int(DISCORD_CHANNEL_ID))
        if channel:
            start_tweet_loop(channel)
        else:
            logging.error("❌ 텍스트 채널을 찾을 수 없습니다. DISCORD_CHANNEL_ID를 확인하세요.")
    except Exception as e:
        logging.exception("❌ Twitter 초기화 실패, 봇을 종료합니다.")
        await bot.close()

# ✅ Ping-Pong 명령어
@bot.command()
async def ping(ctx):
    """실제 요청-응답(RTT) 기반 Ping 테스트"""
    start_time = time.monotonic()  # 시작 시간 기록
    message = await ctx.send("🏓 Pong! 측정 중...")
    end_time = time.monotonic()  # 응답 완료 시간 기록

    rtt_latency = round((end_time - start_time) * 1000)  # RTT 기반 핑 (밀리초 변환)
    ws_latency = round(bot.latency * 1000)  # WebSocket 기반 핑 (밀리초 변환)

    await message.edit(content=f"🏓 Pong! RTT: {rtt_latency}ms | WebSocket: {ws_latency}ms")

# ✅ 이미지 크롤링 기능
@bot.command()
async def imgcrawl(ctx):
    """네코마시로 사이트에서 랜덤 이미지를 가져옵니다."""
    url = "https://nenekomashiro.com/all"

    # ✅ "이미지 생성 중..." 메시지 전송
    loading_message = await ctx.send("🖼 이미지 생성 중...")

    # ✅ Chrome 옵션 설정
    options = Options()
    options.add_argument("--headless")  # 브라우저 창 없이 실행
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # ✅ Chrome WebDriver 실행
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url)
        time.sleep(3)  # 페이지 로드 대기 (JavaScript 실행 대기)

        # ✅ 모든 이미지 태그 가져오기
        images = driver.find_elements(By.TAG_NAME, "img")

        # ✅ 'src' 속성이 있고 제외할 파일이 아닌 이미지 URL만 추출
        image_urls = [
            img.get_attribute("src") for img in images
            if img.get_attribute("src") and 
               "nenekomashiro.com" in img.get_attribute("src") and 
               not any(excluded in img.get_attribute("src") for excluded in EXCLUDED_IMAGES)
        ]

        driver.quit()  # WebDriver 종료

        if not image_urls:
            await loading_message.edit(content="❌ 이미지를 찾을 수 없습니다.")
            return

        # ✅ 랜덤 이미지 선택 후 기존 메시지 수정
        random_img = random.choice(image_urls)
        await loading_message.edit(content=f"🖼 랜덤 이미지:\n{random_img}")

    except Exception as e:
        await loading_message.edit(content=f"❌ 크롤링 중 오류 발생: {e}")
        driver.quit()

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
