# index.py
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
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# 외부 라이브러리 로그 레벨 조정
logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('discord.http').setLevel(logging.WARNING)
logging.getLogger('aiohttp').setLevel(logging.WARNING)
logging.getLogger('googleapiclient').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# 토큰 체크
if not DISCORD_TOKEN:
    logger.critical("❌ DISCORD_TOKEN 환경 변수가 설정되지 않았습니다.")
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
    extensions = ["schedule", "imgcrawl", "twitter", "youtube"]  # "youtube" 추가

    # 확장 모듈 로드 시도
    failed_extensions = []
    for ext in extensions:
        if ext in bot.extensions:
            logger.info(f"⚠️ {ext}.py 이미 로드되어 건너뜁니다.")
            continue

        try:
            await bot.load_extension(ext)
            logger.info(f"✅ {ext}.py 로드 완료")
        except Exception as e:
            failed_extensions.append(ext)
            logger.error(f"❌ {ext}.py 로드 실패: {e}")

    # 실패한 모듈이 있는 경우 경고
    if failed_extensions:
        logger.warning(f"⚠️ 다음 확장 모듈을 로드하지 못했습니다: {', '.join(failed_extensions)}")
        return False
    return True

@bot.event
async def setup_hook():
    """봇이 로그인하기 전에 확장 모듈을 한 번만 로드"""
    success = await load_extensions()
    if success:
        logger.info("✅ 모든 확장 모듈이 성공적으로 로드되었습니다.")

@bot.event
async def on_ready():
    """봇이 준비되었을 때 실행"""
    logger.info(f"✅ Bot logged in as {bot.user}")

    # 슬래시 명령어 동기화 (재연결 시에도 실행)
    try:
        await bot.tree.sync()
        logger.info("✅ Slash commands synced")
    except Exception as e:
        logger.error(f"❌ Slash commands sync 실패: {e}")

@bot.event
async def on_error(event, *args, **kwargs):
    """에러 발생 시 로깅"""
    logger.error(f"❌ 이벤트 '{event}'에서 오류 발생", exc_info=True)

@bot.event
async def on_command_error(ctx, error):
    """명령어 에러 핸들링"""
    if isinstance(error, commands.CommandNotFound):
        return  # 존재하지 않는 명령어는 무시
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ 필수 인수가 누락되었습니다.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ 잘못된 인수입니다.")
    else:
        logger.error(f"❌ 명령어 '{ctx.command}' 실행 중 오류: {error}", exc_info=True)
        await ctx.send("❌ 명령어 실행 중 오류가 발생했습니다.")

# 기본 슬래시 명령어 정의
@bot.tree.command(name="ping", description="봇의 응답 시간을 확인합니다")
async def ping(interaction: discord.Interaction):
    """Ping 테스트"""
    start_time = time.monotonic()
    await interaction.response.send_message("🏓 Pong! 측정 중...")
    end_time = time.monotonic()
    latency = round((end_time - start_time) * 1000)
    await interaction.edit_original_response(content=f"🏓 Pong! ({latency}ms)")

# ✅ 봇 실행
async def main():
    """메인 실행 함수"""
    try:
        async with bot:
            await bot.start(DISCORD_TOKEN)
    except discord.LoginFailure:
        logger.critical("❌ 디스코드 로그인 실패: 토큰이 유효하지 않습니다.")
    except Exception as e:
        logger.critical(f"❌ 봇 실행 중 오류 발생: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ 사용자에 의해 봇이 종료되었습니다.")
    except Exception as e:
        logger.critical(f"❌ 예상치 못한 오류가 발생했습니다: {e}")
        sys.exit(1)
