import discord
from discord.ext import commands, tasks
import yt_dlp
import asyncio
import os


intents = discord.Intents.default()
intents.message_content = True 

bot = commands.Bot(command_prefix='!', intents=intents)

#global queue
music_queue = {}
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10',
    'options': '-vn -filter:a "volume=0.25"'
}

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')



#/join command
@bot.command()
async def join(ctx):
    if ctx.author.voice: #check if user is in vc
        channel = ctx.author.voice.channel #store the channel the user is in
        await channel.connect() #wait for bot to join the channel
        if not check_voice_channel.is_running():
            check_voice_channel.start() #start the background task loop
    else:
        await ctx.send('Fuck you!')

#/leave command
@bot.command()
async def leave(ctx):
    if ctx.voice_client is None:
        await ctx.send('Not in channel dumbass')
        return
    else:
        await ctx.voice_client.disconnect() #disconnect bot
        if check_voice_channel.is_running():
            check_voice_channel.stop() #end the background task loop


# Function to join voice channel
async def join_voice_channel(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        if ctx.voice_client is None:  # Bot is not connected to a voice channel
            voice_client = await channel.connect()
        else:
            voice_client = ctx.voice_client  # Bot is already connected to a voice channel
        return voice_client
    else:
        await ctx.send('Fuck you!')
        return None

#/play command
@bot.command()
async def play(ctx, *, query: str):
    voice_client = await join_voice_channel(ctx)

    # If no queue exists for the server, create one
    if ctx.guild.id not in music_queue:
        music_queue[ctx.guild.id] = []

    # Check if the input is a YouTube URL, SoundCloud URL, or a search query
    if "youtube.com" in query or "youtu.be" in query or "soundcloud.com" in query:
        url = query
    else:
        # Otherwise, treat it as a search query for YouTube
        ydl_opts = {'format': 'bestaudio', 'noplaylist': 'True', 'quiet': True}
        search_query = f"ytsearch:{query}"  # YouTube search

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            video = info['entries'][0]  # Get the top search result
            url = video['url']
            await ctx.send(f"Now Playing: {video['title']}")

    # Check if already playing
    if voice_client.is_playing():
        # Add the new URL to the queue
        music_queue[ctx.guild.id].append(url)
        await ctx.send(f"Added to queue. Position: {len(music_queue[ctx.guild.id])}")
    else:
        await play_song(ctx, url)

# Function to play the song
async def play_song(ctx, url):
    voice_client = ctx.voice_client
    
    ydl_opts = {
        'format': 'bestaudio',
        'noplaylist': 'True',
        'quiet': True,
        'extract_flat': 'True'
    }

    # Extract audio URL using yt-dlp
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']


    # Stream audio using FFmpeg
    source = discord.FFmpegOpusAudio(audio_url, **ffmpeg_options)
    voice_client.play(source, after=lambda e: play_next(ctx))

    await ctx.send(f"Now playing: {info['title']}")

def play_next(ctx):
    if len(music_queue[ctx.guild.id]) > 0:
        next_url = music_queue[ctx.guild.id].pop(0)
        asyncio.run_coroutine_threadsafe(play_song(ctx, next_url), bot.loop)
    else:
        asyncio.run_coroutine_threadsafe(ctx.voice_client.disconnect(), bot.loop)

@bot.command()
async def skip(ctx):
    voice_client = ctx.voice_client

    if not voice_client or not voice_client.is_connected():
        await ctx.send("I'm not connected to a voice channel.")
        return
    
    if voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Skipping the current song...")
    else:
        await ctx.send("There's no song playing to skip.")



#background update loop
@tasks.loop(minutes=1)
async def check_voice_channel():
    for guild in bot.guilds:
        if guild.voice_client: #if bot is connected to vc
            voice_channel = guild.voice_client.channel
            if len(voice_channel.members) == 1:
                await guild.voice_client.disconnect()
        #check for inactivity


bot.run(os.getenv("DISCORD_TOKEN"))