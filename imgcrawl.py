import logging
import requests
import random
from discord.ext import tasks
from datetime import datetime

# ✅ API 엔드포인트
COUNT_API_URL = "https://nenekomashiro.com/image/list/count?code=999&search="
POST_API_URL = "https://nenekomashiro.com/image/post?page={}&perPage=30&sort=0&code=999&search="
IMAGE_BASE_URL = "https://nenekomashiro.com/"

# ✅ 제외할 파일 리스트
EXCLUDED_IMAGES = {
    "extension.png", "login.png", "option.png",
    "edit.png", "like.png", "profile6.png", "scroll.png"
}

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

# ✅ 자동으로 랜덤 이미지 전송
@tasks.loop(minutes=1)
async def send_random_image(bot, channel_id):
    await bot.wait_until_ready()
    now = datetime.now()
    if now.hour == 10 and now.minute == 0:
        logging.info("🔔 10시가 되어 랜덤 이미지를 전송합니다.")
        channel = bot.get_channel(channel_id)
        if channel:
            image_url = await get_random_image()
            if image_url:
                await channel.send(image_url)
