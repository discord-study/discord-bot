import logging
import os
import random
import requests
import discord
from discord.ext import tasks, commands
from dotenv import load_dotenv
from datetime import datetime

# 환경 변수 로드
load_dotenv()
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

# ✅ API 엔드포인트
COUNT_API_URL = "https://nenekomashiro.com/image/list/count?code=999&search="
POST_API_URL = "https://nenekomashiro.com/image/post?page={}&perPage=30&sort=0&code=999&search="
IMAGE_BASE_URL = "https://nenekomashiro.com/"

class Imgcrawl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.send_random_image.start()

    # ✅ 랜덤 이미지 가져오기
    async def get_random_image(self):
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

    # ✅ /imgcrawl 슬래시 명령어
    @discord.app_commands.command(name="imgcrawl", description="네코마시로 사이트에서 랜덤 이미지를 가져옵니다")
    async def imgcrawl(self, interaction: discord.Interaction):
        """네코마시로 사이트에서 전체 이미지 중 랜덤으로 1개 가져오기"""
        await interaction.response.defer()

        image_url = await self.get_random_image()
        if image_url:
            await interaction.followup.send(image_url)
        else:
            await interaction.followup.send("❌ 이미지를 찾을 수 없습니다.")

    # ✅ 매일 10시에 자동으로 이미지 보내기
    @tasks.loop(minutes=1)
    async def send_random_image(self):
        await self.bot.wait_until_ready()
        now = datetime.now()
        if now.hour == 10 and now.minute == 0:
            logging.info("🔔 10시가 되어 이미지 전송을 시작합니다.")
            channel = self.bot.get_channel(DISCORD_CHANNEL_ID)
            if channel:
                image_url = await self.get_random_image()
                if image_url:
                    await channel.send(image_url)

# ✅ Cog 등록
async def setup(bot):
    await bot.add_cog(Imgcrawl(bot))
