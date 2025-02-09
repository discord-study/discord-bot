import discord
import wavelink

# Lavalink 서버 정보
LAVALINK_HOST = "localhost"
LAVALINK_PORT = 2333
LAVALINK_PASSWORD = "youshallnotpass"

async def setup_music_commands(bot):
    """ 음악 관련 명령어를 설정하는 함수 """

    @bot.event
    async def on_ready():
        print(f"✅ {bot.user} 봇이 실행됨!")
        node = await wavelink.NodePool.create_node(bot=bot, host=LAVALINK_HOST, port=LAVALINK_PORT, password=LAVALINK_PASSWORD)
        print("✅ Lavalink 서버 연결 완료!")

    @bot.command()
    async def join(ctx):
        if not ctx.author.voice:
            return await ctx.send("❌ 먼저 음성 채널에 들어가세요!")

        channel = ctx.author.voice.channel
        vc = await channel.connect(cls=wavelink.Player)
        await ctx.send(f"🔊 {channel.name} 채널에 접속함!")

    @bot.command()
    async def play(ctx, *, query: str):
        if not ctx.voice_client:
            return await ctx.send("❌ 먼저 `!join` 명령어로 음성 채널에 들어가세요!")

        search = await wavelink.YouTubeTrack.search(query)
        if not search:
            return await ctx.send("❌ 노래를 찾을 수 없습니다!")

        track = search[0]
        vc: wavelink.Player = ctx.voice_client
        await vc.play(track)

        await ctx.send(f"🎵 재생 중: **{track.title}**")

    @bot.command()
    async def stop(ctx):
        if not ctx.voice_client:
            return await ctx.send("❌ 봇이 음성 채널에 없습니다!")

        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ 음악 중지 및 채널 퇴장")
