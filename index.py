import logging
import discord
import os
import time
from discord.ext import commands
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ `commands.Bot` 사용
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ✅ 확장 로드 (비동기 방식 적용)
async def load_extensions():
    extensions = ["schedule", "imgcrawl"]
    for ext in extensions:
        try:
            await bot.load_extension(ext)  # ✅ 비동기 방식 적용
            logging.info(f"✅ {ext}.py 로드 완료")
        except Exception as e:
            logging.error(f"❌ {ext}.py 로드 실패: {e}")

@bot.event
async def on_ready():
    logging.info(f"✅ Bot logged in as {bot.user}")
    await bot.tree.sync()
    logging.info("✅ Slash commands synced")

# ✅ 봇 실행
async def main():
    async with bot:
        await load_extensions()  # ✅ 비동기 확장 로드
        await bot.start(DISCORD_TOKEN)

@bot.command()
async def ping(ctx):
    """Ping 테스트"""
    start_time = time.monotonic()
    message = await ctx.send("🏓 Pong! 측정 중...")
    end_time = time.monotonic()
    latency = round((end_time - start_time) * 1000)
    await message.edit(content=f"🏓 Pong! ({latency}ms)")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())  # ✅ asyncio.run() 사용
