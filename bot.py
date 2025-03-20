import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
import time
import yt_dlp as youtube_dl

# تكوين عام
FFMPEG_PATH = 'ffmpeg'
print(f"Using FFmpeg: {FFMPEG_PATH}")

# الألوان المستخدمة في الرسائل
COLORS = {
    'success': 0x2ecc71,  # أخضر
    'error': 0xe74c3c,    # أحمر
    'info': 0x3498db,     # أزرق
    'warning': 0xf1c40f   # أصفر
}

# الرموز التعبيرية
EMOJIS = {
    'play': '▶️',
    'pause': '⏸️',
    'stop': '⏹️',
    'skip': '⏭️',
    'volume': '🔊',
    'repeat': '🔁',
    'music': '🎵',
    'error': '❌',
    'success': '✅',
    'wave': '👋',
    'search': '🔍',
    'time': '⏱️',
    'channel': '🎙️',
    'bot': '🤖'
}

# إعدادات yt-dlp
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'force-ipv4': True,
    'cachedir': False,
    'rm_cachedir': True,
    'extractor_retries': 5,
    'socket_timeout': 30,
    'retries': 5,
    'fragment_retries': 5,
    'hls_prefer_native': True,
    'cookiefile': './cookies.txt',
    'extract_flat': False,
    'compat_opts': ['youtube-dl'],
    'youtube_include_dash_manifest': False,
    'prefer_ffmpeg': True,
    'http_chunk_size': 10485760,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '320',
    }],
}

# إعدادات FFmpeg
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

print(f"Using cookies file: {ytdl_format_options['cookiefile']}")
youtube_dl.utils.bug_reports_message = lambda: ''

# تكوين yt-dlp مع محاولات إعادة المحاولة
class YTDLPWrapper:
    def __init__(self, ytdl_opts):
        self.ytdl = youtube_dl.YoutubeDL(ytdl_opts)
        self.max_retries = 3
        self.retry_delay = 1

    async def extract_info(self, url, download=False):
        for attempt in range(self.max_retries):
            try:
                return await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: self.ytdl.extract_info(url, download=download)
                )
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == self.max_retries - 1:
                raise
            await asyncio.sleep(self.retry_delay)

ytdl = YTDLPWrapper(ytdl_format_options)

class MusicBot:
    def __init__(self, token, bot_id):
        self.token = token
        self.bot_id = bot_id
        self.bot = commands.Bot(command_prefix=commands.when_mentioned_or(''), intents=discord.Intents.all())
        self.volume = {}
        self.ytdl = ytdl
        self.ffmpeg_options = ffmpeg_options
        self.setup_events()
        self.setup_commands()
        self.queue = {}
        self.current_song = {}
        self.allowed_channel_id = 1299567128416096307
        self.target_voice_channel_id = None

    def setup_events(self):
        @self.bot.event
        async def on_ready():
            print(f'{self.bot.user} is ready!')
            print(f'Bot ID: {self.bot.user.id}')
            print(f'Allowed channel ID: {self.allowed_channel_id}')
            
            # تحديد القناة الصوتية المخصصة لكل بوت
            if self.bot.user.id == 1328879114702291079:  # البوت الأول
                self.target_voice_channel_id = 1351711470068568198
                print("تم تحديد البوت الأول")
            elif self.bot.user.id == 1351711159757312040:  # البوت الثاني
                self.target_voice_channel_id = 1351680102634885290
                print("تم تحديد البوت الثاني")
                
            try:
                # البحث عن السيرفر في جميع السيرفرات المتاحة
                guild = None
                for g in self.bot.guilds:
                    print(f"Found guild: {g.name} (ID: {g.id})")
                    if g.id == 1279203388331917482:
                        guild = g
                        break
                
                if guild:
                    print(f"تم العثور على السيرفر: {guild.name}")
                    # البحث عن القناة الصوتية المحددة
                    target_channel = discord.utils.get(guild.channels, id=self.target_voice_channel_id)
                    if target_channel and isinstance(target_channel, discord.VoiceChannel):
                        try:
                            # التحقق مما إذا كان البوت متصلاً بالفعل
                            if not guild.voice_client or guild.voice_client.channel != target_channel:
                                await target_channel.connect()
                                print(f'تم الاتصال بالقناة الصوتية: {target_channel.name} (بوت {self.bot.user.name})')
                                self.volume[guild.id] = 0.5
                            else:
                                print(f'البوت {self.bot.user.name} متصل بالفعل بالقناة {target_channel.name}')
                        except Exception as e:
                            print(f'خطأ في الاتصال بالقناة الصوتية {target_channel.name}: {str(e)}')
                    else:
                        print(f'لم يتم العثور على القناة الصوتية المحددة: {self.target_voice_channel_id}')
                        print("القنوات المتاحة:")
                        for channel in guild.channels:
                            print(f"- {channel.name} (ID: {channel.id}, Type: {type(channel).__name__})")
                else:
                    print('لم يتم العثور على السيرفر المحدد')
                    print("السيرفرات المتاحة:")
                    for g in self.bot.guilds:
                        print(f"- {g.name} (ID: {g.id})")
            except Exception as e:
                print(f'خطأ في حدث on_ready: {str(e)}')

        @self.bot.event
        async def on_message(message):
            # تجاهل رسائل البوت
            if message.author.bot:
                return
                
            # التحقق من أن الرسالة في القناة المسموح بها
            if message.channel.id != self.allowed_channel_id:
                print(f"Message ignored - Wrong channel. Expected: {self.allowed_channel_id}, Got: {message.channel.id}")
                return
                
            print(f"Processing command in channel: {message.channel.name} (ID: {message.channel.id})")
            await self.bot.process_commands(message)

        @self.bot.event
        async def on_voice_state_update(member, before, after):
            # إذا غادر جميع الأعضاء القناة الصوتية
            if before.channel and not after.channel:
                if before.channel.guild.voice_client and before.channel.guild.voice_client.channel == before.channel:
                    if len(before.channel.members) == 1:  # البوت فقط
                        await before.channel.guild.voice_client.disconnect()
                        await before.channel.send("👋 تم قطع الاتصال لعدم وجود أحد في القناة")

    def setup_commands(self):
        @self.bot.command(name='ش')
        async def play(ctx, *, query):
            """تشغيل الأغنية من اليوتيوب"""
            if ctx.channel.id != self.allowed_channel_id:
                return
                
            # التحقق من وجود شخص في نفس القناة الصوتية مع البوت بصمت
            if ctx.voice_client and len(ctx.voice_client.channel.members) <= 1:
                return
                
            print(f"Received play command with query: {query}")
            
            try:
                guild_voice_client = ctx.guild.voice_client
                
                if not guild_voice_client:
                    embed = discord.Embed(
                        title=f"{EMOJIS['error']} خطأ في الاتصال",
                        description="البوت غير متصل بأي قناة صوتية!",
                        color=COLORS['error']
                    )
                    await ctx.send(embed=embed)
                    return

                search_embed = discord.Embed(
                    title=f"{EMOJIS['search']} جاري البحث",
                    description=f"البحث عن: `{query}`",
                    color=COLORS['info']
                )
                await ctx.send(embed=search_embed)

                async with ctx.typing():
                    try:
                        player = await YTDLSource.from_url(query, loop=self.bot.loop, stream=True)
                        
                        if ctx.voice_client.is_playing():
                            ctx.voice_client.stop()
                        
                        def after_playing(error):
                            if error:
                                print(f"Player error: {error}")
                                error_embed = discord.Embed(
                                    title=f"{EMOJIS['error']} خطأ في التشغيل",
                                    description=str(error),
                                    color=COLORS['error']
                                )
                                asyncio.run_coroutine_threadsafe(
                                    ctx.send(embed=error_embed),
                                    self.bot.loop
                                )
                            else:
                                guild_id = ctx.guild.id
                                if loop_status.get(guild_id, False):
                                    asyncio.run_coroutine_threadsafe(
                                        play(ctx, query=query),
                                        self.bot.loop
                                    )
                        
                        ctx.voice_client.play(player, after=after_playing)
                        
                        embed = discord.Embed(
                            title=f"{EMOJIS['music']} قيد التشغيل الآن",
                            color=COLORS['success']
                        )
                        embed.add_field(
                            name="العنوان",
                            value=f"**{player.title}**",
                            inline=False
                        )
                        embed.add_field(
                            name=f"{EMOJIS['channel']} القناة",
                            value=ctx.voice_client.channel.name,
                            inline=True
                        )
                        embed.add_field(
                            name=f"{EMOJIS['bot']} البوت",
                            value=self.bot.user.name,
                            inline=True
                        )
                        if player.thumbnail:
                            embed.set_thumbnail(url=player.thumbnail)
                        if player.duration:
                            minutes = player.duration // 60
                            seconds = player.duration % 60
                            embed.add_field(
                                name=f"{EMOJIS['time']} المدة",
                                value=f"{minutes}:{seconds:02d}",
                                inline=True
                            )
                        
                        await ctx.send(embed=embed)
                        print(f"Now playing: {player.title} in {ctx.voice_client.channel.name}")
                        
                    except Exception as e:
                        print(f"Error during playback setup: {str(e)}")
                        error_embed = discord.Embed(
                            title=f"{EMOJIS['error']} خطأ في التشغيل",
                            description=str(e),
                            color=COLORS['error']
                        )
                        await ctx.send(embed=error_embed)
            except Exception as e:
                print(f"General error: {str(e)}")
                error_embed = discord.Embed(
                    title=f"{EMOJIS['error']} خطأ عام",
                    description=str(e),
                    color=COLORS['error']
                )
                await ctx.send(embed=error_embed)

        @self.bot.command(name='تكرار')
        async def toggle_loop(ctx):
            """تفعيل/إيقاف تكرار الأغنية الحالية"""
            if ctx.channel.id != self.allowed_channel_id:
                return

            # التحقق من وجود شخص في نفس القناة الصوتية مع البوت بصمت
            if ctx.voice_client and len(ctx.voice_client.channel.members) <= 1:
                return

            if ctx.voice_client is None:
                embed = discord.Embed(
                    title=f"{EMOJIS['error']} خطأ",
                    description="البوت غير متصل بأي قناة صوتية!",
                    color=COLORS['error']
                )
                await ctx.send(embed=embed)
                return

            if not ctx.voice_client.is_playing():
                embed = discord.Embed(
                    title=f"{EMOJIS['error']} خطأ",
                    description="لا توجد أغنية قيد التشغيل!",
                    color=COLORS['error']
                )
                await ctx.send(embed=embed)
                return

            guild_id = ctx.guild.id
            loop_status[guild_id] = not loop_status.get(guild_id, False)
            
            if loop_status[guild_id]:
                embed = discord.Embed(
                    title=f"{EMOJIS['repeat']} تكرار",
                    description="تم تفعيل تكرار الأغنية",
                    color=COLORS['success']
                )
            else:
                embed = discord.Embed(
                    title=f"{EMOJIS['repeat']} تكرار",
                    description="تم إيقاف تكرار الأغنية",
                    color=COLORS['info']
                )
            await ctx.send(embed=embed)

        @self.bot.command(name='سكب')
        async def skip(ctx):
            """تخطي الأغنية الحالية"""
            if ctx.channel.id != self.allowed_channel_id:
                return

            # التحقق من وجود شخص في نفس القناة الصوتية مع البوت بصمت
            if ctx.voice_client and len(ctx.voice_client.channel.members) <= 1:
                return

            if ctx.voice_client is None:
                embed = discord.Embed(
                    title=f"{EMOJIS['error']} خطأ",
                    description="البوت غير متصل بأي قناة صوتية!",
                    color=COLORS['error']
                )
                await ctx.send(embed=embed)
                return

            if not ctx.voice_client.is_playing():
                embed = discord.Embed(
                    title=f"{EMOJIS['error']} خطأ",
                    description="لا توجد أغنية قيد التشغيل!",
                    color=COLORS['error']
                )
                await ctx.send(embed=embed)
                return

            ctx.voice_client.stop()
            embed = discord.Embed(
                title=f"{EMOJIS['skip']} تخطي",
                description="تم تخطي الأغنية",
                color=COLORS['success']
            )
            await ctx.send(embed=embed)

        @self.bot.command(name='صوت')
        async def volume(ctx, volume: int):
            """تغيير مستوى الصوت (1-100)"""
            if ctx.channel.id != self.allowed_channel_id:
                return

            # التحقق من وجود شخص في نفس القناة الصوتية مع البوت بصمت
            if ctx.voice_client and len(ctx.voice_client.channel.members) <= 1:
                return

            if ctx.voice_client is None:
                embed = discord.Embed(
                    title=f"{EMOJIS['error']} خطأ",
                    description="البوت غير متصل بأي قناة صوتية!",
                    color=COLORS['error']
                )
                await ctx.send(embed=embed)
                return

            if not ctx.voice_client.is_playing():
                embed = discord.Embed(
                    title=f"{EMOJIS['error']} خطأ",
                    description="لا توجد أغنية قيد التشغيل!",
                    color=COLORS['error']
                )
                await ctx.send(embed=embed)
                return

            if not 0 <= volume <= 100:
                embed = discord.Embed(
                    title=f"{EMOJIS['error']} خطأ",
                    description="يرجى إدخال رقم بين 0 و 100",
                    color=COLORS['error']
                )
                await ctx.send(embed=embed)
                return

            ctx.voice_client.source.volume = volume / 100
            self.volume[ctx.guild.id] = volume / 100
            embed = discord.Embed(
                title=f"{EMOJIS['volume']} مستوى الصوت",
                description=f"تم تغيير مستوى الصوت إلى {volume}%",
                color=COLORS['success']
            )
            await ctx.send(embed=embed)

        @self.bot.command(name='وقف')
        async def pause(ctx):
            """إيقاف مؤقت للأغنية"""
            if ctx.channel.id != self.allowed_channel_id:
                return

            # التحقق من وجود شخص في نفس القناة الصوتية مع البوت بصمت
            if ctx.voice_client and len(ctx.voice_client.channel.members) <= 1:
                return

            if ctx.voice_client is None:
                embed = discord.Embed(
                    title=f"{EMOJIS['error']} خطأ",
                    description="البوت غير متصل بأي قناة صوتية!",
                    color=COLORS['error']
                )
                await ctx.send(embed=embed)
                return

            if not ctx.voice_client.is_playing():
                embed = discord.Embed(
                    title=f"{EMOJIS['error']} خطأ",
                    description="لا توجد أغنية قيد التشغيل!",
                    color=COLORS['error']
                )
                await ctx.send(embed=embed)
                return

            ctx.voice_client.pause()
            embed = discord.Embed(
                title=f"{EMOJIS['pause']} إيقاف مؤقت",
                description="تم إيقاف الأغنية مؤقتاً",
                color=COLORS['info']
            )
            await ctx.send(embed=embed)

        @self.bot.command(name='كمل')
        async def resume(ctx):
            """استئناف تشغيل الأغنية"""
            if ctx.channel.id != self.allowed_channel_id:
                return

            # التحقق من وجود شخص في نفس القناة الصوتية مع البوت بصمت
            if ctx.voice_client and len(ctx.voice_client.channel.members) <= 1:
                return

            if ctx.voice_client is None:
                embed = discord.Embed(
                    title=f"{EMOJIS['error']} خطأ",
                    description="البوت غير متصل بأي قناة صوتية!",
                    color=COLORS['error']
                )
                await ctx.send(embed=embed)
                return

            if not ctx.voice_client.is_paused():
                embed = discord.Embed(
                    title=f"{EMOJIS['error']} خطأ",
                    description="الأغنية ليست متوقفة مؤقتاً!",
                    color=COLORS['error']
                )
                await ctx.send(embed=embed)
                return

            ctx.voice_client.resume()
            embed = discord.Embed(
                title=f"{EMOJIS['play']} استئناف",
                description="تم استئناف تشغيل الأغنية",
                color=COLORS['success']
            )
            await ctx.send(embed=embed)

    async def start(self):
        try:
            await self.bot.start(self.token)
        except Exception as e:
            print(f"Error starting bot: {str(e)}")
            await asyncio.sleep(5)
            await self.start()  # إعادة المحاولة تلقائياً

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.thumbnail = data.get('thumbnail')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        try:
            if not url.startswith('http'):
                url = f'ytsearch:{url}'
            
            data = await ytdl.extract_info(url, download=not stream)
            
            if data is None:
                raise Exception("Failed to extract video information")
                
            if 'entries' in data:
                data = data['entries'][0]

            filename = data['url'] if stream else ytdl.ytdl.prepare_filename(data)
            return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
        except Exception as e:
            print(f"Error in from_url: {str(e)}")
            raise e

    def seek(self, offset):
        """تخطي جزء من الأغنية"""
        try:
            if hasattr(self, 'source') and hasattr(self.source, 'seek'):
                self.source.seek(offset)
                return True
        except Exception as e:
            print(f"Error seeking: {str(e)}")
        return False

loop_status = {}

# إنشاء مجلد مؤقت إذا لم يكن موجوداً
if not os.path.exists("temp"):
    os.makedirs("temp")

# قائمة التوكنات
TOKENS = [
    'MTMyODg3OTExNDcwMjI5MTA3OQ.G-79bn.ItVU1iVX0dDM8QzpqSmDw4Vuf6KPE8avkYaDGo',
    'MTM1MTcxMTE1OTc1NzMxMjA0MA.GR6QK5.Ev3PqOPBSiG5EgQHU8DnMFQ8HBjTbm8opUtQ7o'
]

async def main():
    while True:
        try:
            bots = [MusicBot(token, i) for i, token in enumerate(TOKENS)]
            await asyncio.gather(*(bot.start() for bot in bots))
        except Exception as e:
            print(f"Error in main: {str(e)}")
            await asyncio.sleep(5)  # انتظار 5 ثواني قبل إعادة المحاولة

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        time.sleep(5) 