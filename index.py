import logging
import discord
import os
import time
import sys
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# 로깅 설정을 먼저 구성 - 콘솔과 파일에 모두 로깅
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# 환경 변수 로드
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# 토큰 체크
if not DISCORD_TOKEN:
    logging.critical("❌ DISCORD_TOKEN 환경 변수가 설정되지 않았습니다.")
    sys.exit(1)

# ✅ `commands.Bot` 사용
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ✅ 확장 로드 (비동기 방식 적용)
async def load_extensions():
    # 기본 확장 모듈
    extensions = ["schedule", "imgcrawl", "twitter"]
    
    # 확장 모듈 로드 시도
    failed_extensions = []
    for ext in extensions:
        try:
            await bot.load_extension(ext)
            logging.info(f"✅ {ext}.py 로드 완료")
        except Exception as e:
            failed_extensions.append(ext)
            logging.error(f"❌ {ext}.py 로드 실패: {e}")
    
    # 실패한 모듈이 있는 경우 경고
    if failed_extensions:
        logging.warning(f"⚠️ 다음 확장 모듈을 로드하지 못했습니다: {', '.join(failed_extensions)}")
        return False
    return True

@bot.event
async def on_ready():
    # 봇이 준비된 후에 확장 모듈 로드
    logging.info(f"✅ Bot logged in as {bot.user}")
    
    # 확장 모듈 로드
    success = await load_extensions()
    if success:
        logging.info("✅ 모든 확장 모듈이 성공적으로 로드되었습니다.")
    
    # 슬래시 명령어 동기화
    try:
        await bot.tree.sync()
        logging.info("✅ Slash commands synced")
    except Exception as e:
        logging.error(f"❌ Slash commands sync 실패: {e}")

# 기본 명령어 정의
@bot.command()
async def ping(ctx):
    """Ping 테스트"""
    start_time = time.monotonic()
    message = await ctx.send("🏓 Pong! 측정 중...")
    end_time = time.monotonic()
    latency = round((end_time - start_time) * 1000)
    await message.edit(content=f"🏓 Pong! ({latency}ms)")

# ✅ 봇 실행
async def main():
    try:
        async with bot:
            await bot.start(DISCORD_TOKEN)
    except discord.LoginFailure:
        logging.critical("❌ 디스코드 로그인 실패: 토큰이 유효하지 않습니다.")
    except Exception as e:
        logging.critical(f"❌ 봇 실행 중 오류 발생: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())  # ✅ asyncio.run() 사용
    except KeyboardInterrupt:
        logging.info("❌ 사용자에 의해 봇이 종료되었습니다.")
    except Exception as e:
        logging.critical(f"❌ 예상치 못한 오류가 발생했습니다: {e}")
        sys.exit(1)