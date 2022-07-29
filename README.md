# av-discord

[PyAV](https://github.com/PyAV-Org/PyAV) audio sources for [discord.py](https://github.com/Rapptz/discord.py), 
[pycord](https://github.com/Pycord-Development/pycord), 
and [disnake](https://github.com/DisnakeDev/disnake)

## Installation

### Stable version (PyPI)

```shell
# For Windows
py -3 -m pip install av-discord

# For Linux / Mac OS
python3 -m pip install av-discord
```

### Development version

**NOTE:** You must have git installed. If you don't have it, install it from here https://git-scm.com/.

```shell
git clone https://github.com/mansuf/av-discord.git
cd av-discord
python setup.py install
```

## Usage

```python
from discord.ext.commands import Bot
from avcord import setup_av, AVPCMAudio, setup_encoder

# Do setup
# Use `setup_av('disnake')` if you're using disnake library
setup_av('discord')

bot = Bot()

@bot.command()
async def play(ctx):
    voice_user = ctx.message.author.voice
    vc = await voice_user.channel.connect()

    # It is important to call this function before play audio
    # to avoid "Segmentation fault" error
    setup_encoder(vc)

    source = AVPCMAudio('audio.webm')
    vc.play(source)

@bot.event
async def on_ready():
    print('READY')

bot.run('token')
```