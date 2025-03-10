import logging
import discord
import os
import time
import sys
from discord.ext import commands
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# 토큰 체크
if not DISCORD_TOKEN:
    logging.critical("❌ DISCORD_TOKEN 환경 변수가 설정되지 않았습니다.")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ `commands.Bot` 사용
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ✅ 확장 로드 (비동기 방식 적용)
async def load_extensions():
    extensions = ["schedule", "imgcrawl", "twitter"]  # twitter 확장 추가
    for ext in extensions:
        try:
            await bot.load_extension(ext)  # ✅ 비동기 방식 적용
            logging.info(f"✅ {ext}.py 로드 완료")
        except Exception as e:
            logging.error(f"❌ {ext}.py 로드 실패: {e}")

@bot.event
async def on_ready():
    logging.info(f"✅ Bot logged in as {bot.user}")
    try:
        await bot.tree.sync()
        logging.info("✅ Slash commands synced")
    except Exception as e:
        logging.error(f"❌ Slash commands sync 실패: {e}")

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
    try:
        import asyncio
        asyncio.run(main())  # ✅ asyncio.run() 사용
    except KeyboardInterrupt:
        logging.info("❌ 사용자에 의해 봇이 종료되었습니다.")
    except Exception as e:
        logging.critical(f"❌ 예상치 못한 오류가 발생했습니다: {e}")
        sys.exit(1)