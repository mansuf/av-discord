class AVDiscordError(Exception):
    "Base exception for av-discord library"
    pass

class StreamHTTPError(AVDiscordError):
    """Raised when error happened in PyAV stream"""
    pass