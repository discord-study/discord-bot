import logging
import discord
import yt_dlp as youtube_dl
from discord.ext import commands
import asyncio
from functools import partial

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}
YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True'}

song_queues = {}
queue_locks = {}

def get_queue(guild_id):
    if guild_id not in song_queues:
        song_queues[guild_id] = []
    return song_queues[guild_id]

def get_lock(guild_id):
    if guild_id not in queue_locks:
        queue_locks[guild_id] = asyncio.Lock()
    return queue_locks[guild_id]

def get_best_audio_url(video_info):
    """ 유튜브에서 최적의 오디오 URL 가져오기 """
    for fmt in video_info.get('formats', []):
        if fmt.get('acodec') != 'none':  
            return fmt['url']
    return None

def play_next_callback(ctx, error):
    if error:
        logging.error(f"Error during playback: {error}")
    ctx.bot.loop.create_task(play_next(ctx))

async def play_next(ctx):
    """ 다음 곡을 재생하는 함수 """
    guild_id = ctx.guild.id
    lock = get_lock(guild_id)
    
    async with lock:
        queue = get_queue(guild_id)
        if not queue:
            if ctx.voice_client:
                await ctx.voice_client.disconnect()
            return

        next_song = queue.pop(0)

    try:
        ctx.voice_client.play(
            next_song["source"],
            after=partial(play_next_callback, ctx)
        )
        await ctx.send(f"🎵 **{next_song['title']}** 재생 중!")
    except Exception as e:
        logging.error(f"Error during playback: {e}")

async def setup_music_commands(bot):
    """ 음악 명령어를 봇에 등록하는 함수 """
    
    @bot.tree.command(name="join", description="음성 채널에 봇을 참여시킵니다.")
    async def join(ctx: discord.Interaction):
        if ctx.user.voice:
            channel = ctx.user.voice.channel
            if ctx.guild.voice_client is None:
                await channel.connect()
                await ctx.response.send_message(f"✅ **{channel.name}** 채널에 접속했습니다.")
            else:
                await ctx.response.send_message("❌ 이미 음성 채널에 접속되어 있습니다.")
        else:
            await ctx.response.send_message("❌ 먼저 음성 채널에 접속해주세요.")

    @bot.tree.command(name="play", description="유튜브에서 노래 제목을 검색하여 재생합니다.")
    async def play(ctx: discord.Interaction, query: str):
        if ctx.guild.voice_client is None:
            if ctx.user.voice:
                await ctx.user.voice.channel.connect()
            else:
                await ctx.response.send_message("❌ 음성 채널에 먼저 접속해주세요.")
                return

        async with ctx.channel.typing():
            try:
                search_query = f"ytsearch:{query}"
                with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
                    info = ydl.extract_info(search_query, download=False)
                    if 'entries' in info and len(info['entries']) > 0:
                        video = info['entries'][0]
                        audio_url = get_best_audio_url(video)
                        title = video.get('title', 'Unknown Title')
                    else:
                        await ctx.response.send_message("❌ 검색 결과가 없습니다.")
                        return
            except Exception as e:
                logging.exception("오류 발생 during YouTube 검색:")
                await ctx.response.send_message("❌ 오류가 발생했습니다. 다시 시도해주세요.")
                return

            if not audio_url:
                await ctx.response.send_message("❌ 오디오 스트림을 찾을 수 없습니다.")
                return

            song = {
                "source": discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS),
                "title": title
            }

        guild_id = ctx.guild.id
        lock = get_lock(guild_id)

        if ctx.guild.voice_client.is_playing():
            queue = get_queue(guild_id)
            queue.append(song)
            await ctx.response.send_message(f"🎶 **{title}** 큐에 추가됨!")
            return

        async with lock:
            ctx.guild.voice_client.play(song["source"], after=partial(play_next_callback, ctx))
            await ctx.response.send_message(f"🎵 **{title}** 재생 중!")

    @bot.tree.command(name="skip", description="현재 재생 중인 노래를 건너뜁니다.")
    async def skip(ctx: discord.Interaction):
        if ctx.guild.voice_client and ctx.guild.voice_client.is_playing():
            ctx.guild.voice_client.stop()
            await ctx.response.send_message("⏩ 현재 노래를 건너뜁니다.")
            await play_next(ctx)
        else:
            await ctx.response.send_message("❌ 재생 중인 노래가 없습니다.")

    @bot.tree.command(name="stop", description="음악 재생을 중지하고 봇이 음성 채널에서 나갑니다.")
    async def stop(ctx: discord.Interaction):
        if ctx.guild.voice_client:
            guild_id = ctx.guild.id
            lock = get_lock(guild_id)
            async with lock:
                get_queue(guild_id).clear()
            await ctx.guild.voice_client.disconnect()
            await ctx.response.send_message("🔌 음성 채널에서 나갔습니다.")
        else:
            await ctx.response.send_message("❌ 봇이 음성 채널에 연결되어 있지 않습니다.")
