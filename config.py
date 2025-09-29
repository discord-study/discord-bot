# config.py
import os
import logging
from dotenv import load_dotenv
from typing import Optional

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def validate_int(value: str, var_name: str, default: int = 0) -> int:
    """정수 타입 환경변수 검증"""
    if not value:
        if default is not None:
            logger.warning(f"⚠️ {var_name}이 설정되지 않아 기본값 {default}을 사용합니다.")
            return default
        raise ValueError(f"❌ {var_name}이 설정되지 않았습니다.")

    try:
        return int(value)
    except ValueError:
        raise ValueError(f"❌ {var_name}은 정수여야 합니다. 현재값: '{value}'")

def validate_string(value: Optional[str], var_name: str, required: bool = True) -> Optional[str]:
    """문자열 타입 환경변수 검증"""
    if not value:
        if required:
            raise ValueError(f"❌ 필수 환경변수 {var_name}이 설정되지 않았습니다.")
        else:
            logger.warning(f"⚠️ 선택적 환경변수 {var_name}이 설정되지 않았습니다.")
            return None
    return value.strip()

# 환경변수 로드 및 검증
try:
    DISCORD_TOKEN = validate_string(os.getenv("DISCORD_TOKEN"), "DISCORD_TOKEN")
    DISCORD_CHANNEL_ID = validate_int(os.getenv("DISCORD_CHANNEL_ID"), "DISCORD_CHANNEL_ID")
    TWITTER_USERNAME = validate_string(os.getenv("TWITTER_USERNAME"), "TWITTER_USERNAME")
    BEARER_TOKEN = validate_string(os.getenv("BEARER_TOKEN"), "BEARER_TOKEN")

    # YouTube API 설정 (선택적)
    YOUTUBE_API_KEY = validate_string(os.getenv("YOUTUBE_API_KEY"), "YOUTUBE_API_KEY", required=False)
    YOUTUBE_CHANNEL_ID = validate_string(os.getenv("YOUTUBE_CHANNEL_ID"), "YOUTUBE_CHANNEL_ID", required=False)
    DISCORD_YOUTUBE_CHANNEL_ID = validate_int(os.getenv("DISCORD_YOUTUBE_CHANNEL_ID"), "DISCORD_YOUTUBE_CHANNEL_ID", default=0)

    logger.info("✅ 모든 환경변수가 성공적으로 로드되었습니다.")

except ValueError as e:
    logger.critical(str(e))
    raise