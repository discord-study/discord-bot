import logging
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from twitter import init_twitter, start_tweet_loop

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

@bot.event
async def on_ready():
    logging.info(f"✅ Bot logged in as {bot.user}")

    # ✅ 1. 슬래시 명령어를 디스코드 서버에 동기화
    await bot.tree.sync()
    logging.info("✅ Slash commands synced")

    # ✅ 2. 트위터 초기화 및 루프 시작
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

################ Ping-Pong 명령어 추가 #######################
##############################################################
##############################################################
@bot.command()
async def ping(ctx):
    """Ping을 입력하면 Pong!과 응답 속도를 반환합니다."""
    latency = round(bot.latency * 1000)  # 밀리초 단위 변환
    await ctx.send(f"Pong! 🏓 ({latency}ms)")

###############################################################
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
