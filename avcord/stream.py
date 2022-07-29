import threading
import av
import io
from .errors import StreamHTTPError

# https://github.com/mansuf/pyav-django-server/blob/main/pyav/io.py
class LibAVIO(io.RawIOBase):
    """
    IO for PyAV.
    There is few differences between built-in IO and this IO:
    - There is no seek() and tell()
    - using bytearray for storing data
    - once data is readed it will automatically removed
    """
    def __init__(self):
        self.buf = bytearray()
        self.lock = threading.Lock()

    @property
    def length(self):
        return len(self.buf)

    def read(self, n=-1):
        with self.lock:
            if n <= 0:
                data = self.buf[0:]
                del self.buf[0:]
            else:
                data = self.buf[:n]
                del self.buf[:n]
        return bytes(data)

    def write(self, buf):
        with self.lock:
            self.buf += buf
        return len(buf)

    def getvalue(self):
        return self.buf

    def writable(self) -> bool:
        return True

# https://github.com/mansuf/discord-ext-music/blob/main/discord/ext/music/voice_source/av/stream.py#L7
# With some modifications (seek feature is gone)
class LibAVAudioStream(io.RawIOBase):
    """A file-like class represent LibAV audio-only stream"""

    # Known HTTP Errors
    # According to https://github.com/PyAV-Org/PyAV/blob/main/av/error.pyx#L162-L167
    AV_HTTP_ERRORS = (
        av.HTTPBadRequestError,
        av.HTTPUnauthorizedError,
        av.HTTPForbiddenError,
        av.HTTPNotFoundError,
        av.HTTPOtherClientError,
        av.HTTPServerError
    )
    def __init__(self, url, format, codec, rate, mux=True) -> None:
        self.url = url
        # Will be used later
        self.kwargs = {
            "url": url,
            "format": format,
            "codec": codec,
            "rate": rate,
        }
        self.buffer = LibAVIO()
        self.pos = 0
        self.durations = None
        self.stream = None
        self.output_stream = None
        self.mux = mux
        self.muxer = None
        self.demuxer = None
        self._lock = threading.Lock()
        self._closed = threading.Event()
        self._stopped = threading.Event()

        # Will be used in Decoder Stream
        self._stream_buffer = LibAVIO()

        # Check connection
        stream = self._open_connection(url)
        stream.close()

        # Iteration data LibAV
        self.iter_data = self._iter_av_packets()

    def _open_connection(self, url):
        try:
            stream = av.open(url, 'r')
        except self.AV_HTTP_ERRORS as e:
            raise StreamHTTPError(f'Failed to open connection stream, reason: {e}')
        else:
            return stream

    def reconnect(self, seek=None):
        # Speed up grab kwargs
        _seek_kwarg = self.kwargs.get('seek')
        format = self.kwargs.get('format')
        codec = self.kwargs.get('codec')
        rate = self.kwargs.get('rate')

        self.stream = self._open_connection(self.url)
        self.durations = self.stream.duration
        _seek_durations = 0
        # If seek argument is defined in __init__()
        if _seek_kwarg:
            _seek_durations += _seek_kwarg
            # Delete seek argument, since we don't need it anyway
            self.kwargs.pop('seek')
        if seek:
            _seek_durations += seek
        # Begin the seek process
        if _seek_durations:
            self.stream.seek(int(_seek_durations * av.time_base), any_frame=True)

        # Change current stream durations
        self.pos += _seek_durations

        # Set up Encoder and Decoder
        self._stream_buffer = LibAVIO()
        self.demuxer = self.stream.demux(audio=0)
        self.muxer = av.open(self._stream_buffer, 'w', format=format)
        self.output_stream = self.muxer.add_stream(codec, rate=rate)

    def is_closed(self):
        return self._closed.is_set()

    def _close(self):
        if self.stream:
            self.stream.close()
        if self.muxer:
            self.muxer.close()
        self.output_stream = None
        self.demuxer = None
        self._closed.set()

    def close(self):
        self._close()
        self.buffer = LibAVIO()
        self.iter_data.close()

    def _iter_av_packets(self, seek=None):
        self.reconnect(seek)
        while True:
            try:
                packet = next(self.demuxer, b'')
            except av.error.FFmpegError:
                # Fail to get packet such as invalidated session, etc

                # Close the stream and muxer to stop PyAV yelling some errors
                self.stream.close()
                self.muxer.close()

                # Reconnect the stream
                self.reconnect(self.pos)
                continue

            # If stream is exhausted, close connection
            if not packet:
                self._close()
                return b''
            
            # If packet is corrupted, reconnect it
            if packet.is_corrupt:
                # Close the stream and muxer to stop PyAV yelling some errors
                self.stream.close()
                self.muxer.close()

                # Reconnect the stream
                self.reconnect(self.pos)
                continue

            # According PyAV if demuxer sending packet with attribute dts with value None
            # that means demuxer is sending dummy packet.
            # If dummy packet is decoded it will flush the buffers.
            if packet.dts is None:
                packet.decode()
                self._close()
                return b''

            # Decode the packet
            frames = packet.decode()

            for frame in frames:
                self.pos = frame.time
                # https://github.com/PyAV-Org/PyAV/issues/281
                # frame.pts = None
                new_packets = self.output_stream.encode(frame)
                if not self.mux:
                    data = bytearray()
                    for packet in new_packets:
                        data += packet
                    yield bytes(data)
                else:
                    self.muxer.mux(new_packets)
                    yield self._stream_buffer.read()

    def tell(self):
        return self.pos

    def read(self, n=-1):
        while True:
            data = next(self.iter_data, b'')
            self.buffer.write(data)
            if not self.is_closed() and self.buffer.length < n:
                continue
            # Make sure the buffer are empty, if stream already ended.
            elif self.is_closed() and not self.buffer:
                return b''
            return self.buffer.read(n)