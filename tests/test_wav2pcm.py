from struct import *

__all__=["wav2pcm"]

def wav2pcm(wavfile, pcmfile):
    with open(wavfile, "rb") as i, open(pcmfile, "wb") as o:
        i.seek(0)
        _id = i.read(4)
        _id = unpack('>I', _id)
        _size = i.read(4)
        _size = unpack('<I', _size)
        print("size={}".format(_size))
        _type = i.read(4)
        _type = unpack(">I", _type)
        if _id[0] != 0x52494646 or _type[0] != 0x57415645:
            raise ValueError("not a wav!")
        i.read(32)
        result = i.read()
        o.write(result)

wav2pcm("tests/tts_test.wav", "tests/tts_test.pcm")
