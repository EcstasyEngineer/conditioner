"""
This example bot is structured in multiple files and is made with the goal of showcasing commands, events and cogs.
Although this example is not intended as a complete bot, but as a reference aimed to give you a basic understanding for 
creating your bot, feel free to use these examples and point out any issue.
+ These examples are made with educational purpose and there are plenty of docstrings and explanation about most of the code.
+ This example is made with Python 3.8.5 and Discord.py 1.4.0a (rewrite).
Documentation:
+    Discord.py latest:    https://discordpy.readthedocs.io/en/latest/
+    Migration to rewrite:    https://discordpy.readthedocs.io/en/latest/migrating.html
+    Commands documentation:        https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html
+    Cogs documentation:        https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html
+    Tasks documentation:    https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html
The example files are organized in this directory structure:
...
    /discord
        -bot.py
        /cogs
            -dev.py
            -tools.py
            -quote.py
"""
from itertools import cycle
from discord.ext import commands, tasks
import discord
from os import listdir
from dotenv import load_dotenv
import os
from config import Config
import random  # Added import for randomness
from datetime import datetime, timedelta  # Added import for scheduling

def get_prefix(bot, message):
    """This function returns a Prefix for our bot's commands.
    
    Args:
        bot (commands.Bot): The bot that is invoking this function.
        message (discord.Message): The message that is invoking.
        
    Returns:
        string or iterable conteining strings: A string containing prefix or an iterable containing prefixes
    Notes:
        Through a database (or even a json) this function can be modified to returns per server prefixes.
        This function should returns only strings or iterable containing strings.
        This function shouldn't returns numeric values (int, float, complex).
        Empty strings as the prefix always matches, and should be avoided, at least in guilds. 
    """
    if not isinstance(message.guild, discord.Guild):
        """Checks if the bot isn't inside of a guild. 
        Returns a prefix string if true, otherwise passes.
        """
        return '!'

    return ['!']

bot = commands.Bot(command_prefix=get_prefix, intents=discord.Intents.all())

# Initialize a config cache dictionary to store configs by guild ID
bot.config_cache = {}

# Function to get a config for a specific guild
def get_config(guild_id=None):
    """Get a config instance for the specified guild, or the global config if None.
    Caches the config instances to prevent multiple file reads/writes.
    """
    if guild_id is None:
        # Global config
        if 'global' not in bot.config_cache:
            bot.config_cache['global'] = Config()
        return bot.config_cache['global']
    
    # Guild-specific config
    if str(guild_id) not in bot.config_cache:
        bot.config_cache[str(guild_id)] = Config(guild_id)
    return bot.config_cache[str(guild_id)]

# Add the get_config method to the bot object for easy access
bot.get_config = get_config

# Function to load all cogs in the './cogs_static' and './cogs_dynamic' directories
async def load_cogs():
    for filename in listdir('./cogs/static'):
        if filename.endswith('.py'):
            cog_name = f'cogs.static.{filename[:-3]}'
            try:
                await bot.load_extension(cog_name)
                print(f'Successfully loaded {cog_name}')
            except Exception as e:
                print(f'Failed to load {cog_name}: {e}')
    for filename in listdir('./cogs/dynamic'):
        if filename.endswith('.py'):
            cog_name = f'cogs.dynamic.{filename[:-3]}'
            try:
                await bot.load_extension(cog_name)
                print(f'Successfully loaded {cog_name}')
            except Exception as e:
                print(f'Failed to load {cog_name}: {e}')

@bot.event
#This is the decorator for events (outside of cogs).
async def on_ready():
    """This coroutine is called when the bot is connected to Discord.
    Note:
        `on_ready` doesn't take any arguments.
    
    Documentation:
    https://discordpy.readthedocs.io/en/latest/api.html#discord.on_ready
    """

    await load_cogs()
    
    print(f'{bot.user.name} is online and ready!')
    #Prints a message with the bot name.

    change_status.start()
    await schedule_change_avatar()  # Schedule the avatar change task

    await bot.tree.sync()
    # Sync application commands with Discord


# Teasy Hypnotic Statuses
statuslist = cycle([
        "Obey",
        "Submit",
        "Surrender",
        "Go Deeper",
        "Give In",
        "Drop",
        "Sleep",
        "Relax",
        "Let Go",
    ])


@tasks.loop(seconds=16)
async def change_status():
    """This is a background task that loops every 16 seconds.
    The coroutine looped with this task will change status over time.
    The statuses used are in the cycle list called `statuslist`_.
    
    Documentation:
        https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html
    """
    await bot.change_presence(activity=discord.Game(next(statuslist)))

async def schedule_change_avatar():
    """Schedules the avatar change task to run at a specific time of the day."""
    target_time = datetime.now().replace(hour=2, minute=0, second=0, microsecond=0)  # Set to 2:00 AM
    now = datetime.now()
    if now >= target_time:
        # If the target time has already passed today, schedule for tomorrow
        target_time += timedelta(days=1)
    delay = (target_time - now).total_seconds()
    await discord.utils.sleep_until(target_time)  # Wait until the target time
    await change_avatar()  # Run the avatar change once
    change_avatar.start()  # Start the loop to run daily at the same time

@tasks.loop(hours=24)
async def change_avatar():
    """Updates bot avatar with a random image from spirals folder every day at the scheduled time."""
    folder = "media/spirals"
    try:
        files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
        if not files:
            print("No image files found in spirals folder.")
            return
        random_file = random.choice(files)
        file_path = os.path.join(folder, random_file)
        with open(file_path, "rb") as image:
            await bot.user.edit(avatar=image.read())
        print(f"Avatar updated with {random_file}")
    except Exception as e:
        print(f"Failed to update avatar: {e}")

if __name__ == "__main__":
    #Grab token from the token.txt file
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')

    bot.run(TOKEN) #Runs the bot with its token. Don't put code below this command.
