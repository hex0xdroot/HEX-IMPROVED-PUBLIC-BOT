import disnake
from disnake.ext import commands



bot = commands.Bot(command_prefix="!", help_command=None, intents=disnake.Intents.all(), activity=disnake.Streaming(name="hex0xdroot ❤️ Galaxia", url="https://www.twitch.tv/xfandie"))