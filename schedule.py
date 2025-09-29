import logging
import requests
import discord
import asyncio
import aiohttp
from discord.ext import tasks, commands
from datetime import datetime, timedelta
from config import DISCORD_CHANNEL_ID
from typing import Dict, List, Optional

# 로깅 설정
logger = logging.getLogger(__name__)

# API 엔드포인트
STELLARS_API_URL = "https://stellight.fans/api/v1/stellars"
SCHEDULES_API_URL = "https://stellight.fans/api/v1/schedules?startDateTimeAfter={}&startDateTimeBefore={}"

# 캐시 설정
CACHE_TIMEOUT = 3600  # 1시간

class Schedule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stellars = {}  # 방송인 정보 캐시
        self.stellars_cache_time = None
        self.send_schedule.start()

    async def cog_unload(self):
        """Cog 언로드 시 태스크 정리"""
        self.send_schedule.cancel()

    async def get_stellars(self) -> Dict[int, str]:
        """방송인 정보 가져오기 (캐시 적용)"""
        current_time = datetime.now()

        # 캐시가 유효한 경우 재사용
        if (self.stellars and self.stellars_cache_time and
            (current_time - self.stellars_cache_time).seconds < CACHE_TIMEOUT):
            logger.debug("스텔라 정보 캐시 사용")
            return self.stellars

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(STELLARS_API_URL) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.stellars = {s["id"]: s["nameKor"] for s in data}
                        self.stellars_cache_time = current_time
                        logger.info(f"✅ 스텔라 정보 로드 완료: {len(self.stellars)}명")
                        return self.stellars
                    else:
                        logger.error(f"❌ 스텔라 API 응답 오류: {response.status}")

        except asyncio.TimeoutError:
            logger.error("❌ 스텔라 API 요청 타임아웃")
        except aiohttp.ClientError as e:
            logger.error(f"❌ 스텔라 API 연결 오류: {e}")
        except Exception as e:
            logger.error(f"❌ 스텔라 정보 로드 중 예상치 못한 오류: {e}")

        return self.stellars if self.stellars else {}

    async def get_schedules(self, date: datetime) -> List[dict]:
        """특정 날짜의 방송 일정 가져오기"""
        date_str = date.strftime("%Y-%m-%dT00:00:00")
        next_date_str = (date + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
        url = SCHEDULES_API_URL.format(date_str, next_date_str)

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()

                        # API 응답 구조 확인: {"content": [...]} 형태
                        if isinstance(data, dict) and "content" in data:
                            schedules = data["content"]
                        elif isinstance(data, list):
                            schedules = data
                        else:
                            logger.warning(f"예상치 못한 API 응답 구조: {type(data)}")
                            schedules = []

                        logger.info(f"✅ 일정 조회 완료: {len(schedules)}개")
                        return schedules
                    else:
                        logger.error(f"❌ 일정 API 응답 오류: {response.status}")

        except asyncio.TimeoutError:
            logger.error("❌ 일정 API 요청 타임아웃")
        except aiohttp.ClientError as e:
            logger.error(f"❌ 일정 API 연결 오류: {e}")
        except Exception as e:
            logger.error(f"❌ 일정 조회 중 예상치 못한 오류: {e}")

        return []

    def format_schedule_message(self, schedules: List[dict], stellars: Dict[int, str]) -> str:
        """일정 메시지 포맷"""
        if not schedules:
            return "📢 오늘 예정된 방송이 없습니다."

        message = "**📅 오늘의 방송 일정**\n"
        schedule_dict = {}

        try:
            for schedule in schedules:
                stellar_id = schedule.get("stellarId")
                if not stellar_id:
                    logger.warning(f"일정에서 stellarId 누락: {schedule}")
                    continue

                name = stellars.get(stellar_id, f"알 수 없음(ID:{stellar_id})")

                # 날짜 파싱 안전하게 처리
                try:
                    start_datetime = schedule.get("startDateTime", "")
                    if start_datetime:
                        time = datetime.fromisoformat(start_datetime.replace("Z", "+00:00")).strftime("%H:%M")
                    else:
                        time = "시간미정"
                except (ValueError, TypeError) as e:
                    logger.warning(f"날짜 파싱 오류: {start_datetime}, {e}")
                    time = "시간오류"

                title = schedule.get("title", "제목없음")

                # 휴방 일정 처리
                if name in schedule_dict and "휴방" in schedule_dict[name]["titles"]:
                    continue

                if "휴방" in title:
                    schedule_dict[name] = {"time": time, "titles": ["휴방"]}
                    continue

                # 중복 "방송 예정" 방지
                if "방송 예정" in title:
                    if name in schedule_dict and any("방송 예정" in t for t in schedule_dict[name]["titles"]):
                        continue

                # 방송 일정 저장
                if name not in schedule_dict:
                    schedule_dict[name] = {"time": time, "titles": []}

                schedule_dict[name]["titles"].append(title)

            # 메시지 생성
            if schedule_dict:
                # 시간순 정렬
                sorted_items = sorted(schedule_dict.items(), key=lambda x: x[1]["time"])
                for name, info in sorted_items:
                    joined_titles = ", ".join(info["titles"])
                    message += f"🕒 `{info['time']}` | **{name}** - {joined_titles}\n"
            else:
                message = "📢 오늘 예정된 방송이 없습니다."

        except Exception as e:
            logger.error(f"❌ 일정 메시지 포맷 중 오류: {e}")
            return "❌ 일정 정보를 처리하는 중 오류가 발생했습니다."

        return message

    @tasks.loop(minutes=1)
    async def send_schedule(self):
        """자동으로 방송 일정 전송"""
        await self.bot.wait_until_ready()
        now = datetime.now()

        if now.hour == 10 and now.minute == 0:
            logger.info("🔔 10시가 되어 방송 일정을 전송합니다.")
            try:
                channel = self.bot.get_channel(DISCORD_CHANNEL_ID)
                if not channel:
                    logger.error(f"❌ 채널을 찾을 수 없습니다: {DISCORD_CHANNEL_ID}")
                    return

                stellars = await self.get_stellars()
                schedules = await self.get_schedules(now)
                message = self.format_schedule_message(schedules, stellars)

                await channel.send(message)
                logger.info("✅ 방송 일정 자동 전송 완료")

            except discord.HTTPException as e:
                logger.error(f"❌ Discord 메시지 전송 오류: {e}")
            except Exception as e:
                logger.error(f"❌ 방송 일정 자동 전송 중 오류: {e}")

    @discord.app_commands.command(name="schedule", description="오늘의 방송 일정을 확인합니다")
    async def show_schedule(self, interaction: discord.Interaction):
        """오늘의 방송 일정을 수동으로 확인합니다."""
        try:
            await interaction.response.defer()

            stellars = await self.get_stellars()
            schedules = await self.get_schedules(datetime.now())
            message = self.format_schedule_message(schedules, stellars)

            await interaction.followup.send(message)
            logger.info(f"✅ 수동 일정 조회 완료 - 사용자: {interaction.user}")

        except discord.HTTPException as e:
            logger.error(f"❌ Discord 메시지 전송 오류: {e}")
            if interaction.response.is_done():
                await interaction.followup.send("❌ 메시지 전송 중 오류가 발생했습니다.")
            else:
                await interaction.response.send_message("❌ 메시지 전송 중 오류가 발생했습니다.")
        except Exception as e:
            logger.error(f"❌ 수동 일정 조회 중 오류: {e}")
            if interaction.response.is_done():
                await interaction.followup.send("❌ 일정을 조회하는 중 오류가 발생했습니다.")
            else:
                await interaction.response.send_message("❌ 일정을 조회하는 중 오류가 발생했습니다.")

    @discord.app_commands.command(name="schedule_debug", description="스케줄 API 연결 상태를 디버깅합니다")
    async def debug_schedule(self, interaction: discord.Interaction):
        """스케줄 디버깅용 명령어"""
        try:
            await interaction.response.defer()

            await interaction.followup.send("🔍 API 연결 상태를 확인합니다...")

            # 스텔라 정보 확인
            stellars = await self.get_stellars()
            stellar_count = len(stellars)

            # 오늘 일정 확인
            schedules = await self.get_schedules(datetime.now())
            schedule_count = len(schedules)

            debug_msg = f"""**🔍 스케줄 디버그 정보**
📊 스텔라 정보: {stellar_count}명 로드됨
📅 오늘 일정: {schedule_count}개 발견됨
🕒 현재 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📍 알림 채널: <#{DISCORD_CHANNEL_ID}>
💾 캐시 상태: {'유효' if self.stellars_cache_time else '없음'}"""

            await interaction.followup.send(debug_msg)

            if schedule_count > 0:
                # 샘플 일정 데이터 표시 (첫 번째 일정)
                sample_schedule = schedules[0]

                # 주요 필드만 추출하여 가독성 향상
                sample_info = {
                    "id": sample_schedule.get("id"),
                    "stellarId": sample_schedule.get("stellarId"),
                    "stellarNameKor": sample_schedule.get("stellarNameKor", "N/A"),
                    "title": sample_schedule.get("title"),
                    "startDateTime": sample_schedule.get("startDateTime"),
                    "isFixedTime": sample_schedule.get("isFixedTime")
                }

                sample_msg = f"**샘플 일정 데이터:**\n```json\n{sample_info}\n```"
                await interaction.followup.send(sample_msg)

                # 실제 포맷 메시지도 테스트
                test_message = self.format_schedule_message(schedules, stellars)
                if len(test_message) > 1900:  # Discord 메시지 길이 제한 고려
                    test_message = test_message[:1900] + "..."

                await interaction.followup.send(f"**포맷된 메시지 미리보기:**\n{test_message}")

        except Exception as e:
            logger.error(f"❌ 디버그 명령어 실행 중 오류: {e}")
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ 디버그 실행 중 오류: {str(e)}")
            else:
                await interaction.response.send_message(f"❌ 디버그 실행 중 오류: {str(e)}")

# ✅ Cog 등록
async def setup(bot):
    await bot.add_cog(Schedule(bot))
