import importlib
from importlib.util import find_spec

from .stream import LibAVAudioStream
from .encoder import LibAVEncoder

_module = None
_oggparse_module = None

__all__ = (
    'setup_av', 'setup_encoder',
    'AVPCMAudio', 'AVOpusAudio'
)

def setup_av(name_module) -> None:
    """Setup PyAV audio sources by importing discord module

    Parameters
    -----------
    name_module: :class:`str`
        Module want to be imported (must from discord.py, disnake, or pycord package)
    """
    global _module
    global _oggparse_module

    # Only allow these modules
    allowed_modules = ['disnake', 'discord']
    if name_module not in allowed_modules:
        raise ValueError(f"module must be '{allowed_modules}', not {name_module}")

    # Find the module
    module_loc = find_spec(name_module)
    if module_loc is None:
        raise ImportError(f"Module '{name_module}' cannot be found")

    _module = importlib.import_module(name_module)
    _oggparse_module = importlib.import_module(f'{name_module}.oggparse')

def setup_encoder(vc) -> None:
    """Use PyAV opus encoder instead of native opus encoder for given ``VoiceClient``
    
    It is highly recommended to call this function before playing audio in given ``VoiceClient``. 
    To avoid "Segmentation fault" error when playing PyAV audio sources.

    Parameters
    -----------
    vc: ``VoiceClient``
        Connected voice client
    """
    if _module is None:
        raise ValueError("setup_av() is not called")
    
    if not isinstance(vc, _module.VoiceClient):
        raise ValueError(f"vc must be VoiceClient not '{vc.__class__.__name__}'")

    vc.encoder = LibAVEncoder()

class _AVAudioSource:
    """Provide typing for PyAV audio sources"""
    def read(self) -> bytes:
        pass

    def is_opus(self) -> bool:
        pass

    def cleanup(self) -> None:
        pass

def AVPCMAudio(url) -> _AVAudioSource:
    """PyAV PCM audio source

    The source will take and convert to pcm audio.
    
    Parameters
    -----------
    url: :class:`str`
        web or file URL location to stream
    """
    if _module is None:
        raise ValueError("setup_av() is not called")

    class _AVPCMAudio(_module.PCMAudio):
        """Low-level class used in AVPCMAudio() function"""
        def __init__(self, url):
            self.url = url

            stream = LibAVAudioStream(
                url,
                's16le',
                'pcm_s16le',
                48000,
                False
            )

            super().__init__(stream)
        
        def cleanup(self):
            self.stream.close()

    return _AVPCMAudio(url)

def AVOpusAudio(url) -> _AVAudioSource:
    """PyAV Opus audio source
    
    The source will take and convert to opus audio.

    Parameters
    -----------
    url: :class:`str`
        web or file URL location to stream
    """
    if _module is None:
        raise ValueError("setup_av() is not called")

    class _AVOpusAudio(_module.AudioSource):
        """Low-level class used in AVPCMAudio() function"""
        def __init__(self, url):
            self.url = url

            stream = LibAVAudioStream(
                url,
                'ogg',
                'libopus',
                48000,
                True
            )

            self._ogg_stream = _oggparse_module.OggStream(stream).iter_packets()
            self.stream = stream
            super().__init__()

        def is_opus(self):
            return True

        def read(self):
            return next(self._ogg_stream, b'')

        def cleanup(self):
            self.stream.close()
    
    return _AVOpusAudio(url)