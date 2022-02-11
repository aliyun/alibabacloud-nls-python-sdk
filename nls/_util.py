"""
_util.py

Copyright 1999-present Alibaba Group Holding Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""



from struct import *

__all__=["wav2pcm", "GetDefaultContext"]

def GetDefaultContext():
    """
    Return Default Context Object
    """
    return {
        "sdk": {
            "name": "nls-python-sdk",
            "version": "0.0.1",
            "language": "python"
        }
    }


def wav2pcm(wavfile, pcmfile):
    """
    Turn wav into pcm
    
    Parameters
    ----------
    wavfile: str
        wav file path
    pcmfile: str
        output pcm file path
    """
    with open(wavfile, "rb") as i, open(pcmfile, "wb") as o:
        i.seek(0)
        _id = i.read(4)
        _id = unpack('>I', _id)
        _size = i.read(4)
        _size = unpack('<I', _size)
        _type = i.read(4)
        _type = unpack(">I", _type)
        if _id[0] != 0x52494646 or _type[0] != 0x57415645:
            raise ValueError("not a wav!")
        i.read(32)
        result = i.read()
        o.write(result)

