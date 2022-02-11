"""
_speech_synthesizer.py

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


import logging
import uuid
import json
import threading

from nls._core import NlsCore
from . import _logging
from . import _util

__SPEECH_SYNTHESIZER_NAMESPACE__ = "SpeechSynthesizer"

__SPEECH_SYNTHESIZER_REQUEST_CMD__ = {
    "start": "StartSynthesis"
}

__URL__ = "wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1"

__all__ = ["NlsSpeechSynthesizer"]


class NlsSpeechSynthesizer:
    """
    Api for text-to-speech 

    """
    def __init__(self, url=__URL__,
                 akid=None, aksecret=None,
                 token=None, appkey=None,
                 on_metainfo=None,
                 on_data=None,
                 on_completed=None,
                 on_error=None, on_close=None,
                 callback_args=[]):
        """
        NlsSpeechSynthesizer initialization

        Parameters:
        -----------
        url: str
            websocket url.
        akid: str
            access id from aliyun. if you provide a token, ignore this argument.
        aksecret: str
            access secret key from aliyun. if you provide a token, ignore this
            argument.
        token: str
            access token. if you do not have a token, provide access id and key
            secret from your aliyun account.
        appkey: str
            appkey from aliyun
        on_metainfo: function
            Callback object which is called when recognition started.
            on_start has two arguments.
            The 1st argument is message which is a json format string.
            The 2nd argument is *args which is callback_args.
        on_data: function
            Callback object which is called when partial synthesis result arrived
            arrived.
            on_result_changed has two arguments.
            The 1st argument is binary data corresponding to aformat in start
            method.
            The 2nd argument is *args which is callback_args.
        on_completed: function
            Callback object which is called when recognition is completed.
            on_completed has two arguments.
            The 1st argument is message which is a json format string.
            The 2nd argument is *args which is callback_args.
        on_error: function
            Callback object which is called when any error occurs.
            on_error has two arguments.
            The 1st argument is message which is a json format string.
            The 2nd argument is *args which is callback_args.
        on_close: function
            Callback object which is called when connection closed.
            on_close has one arguments.
            The 1st argument is *args which is callback_args.
        callback_args: list
            callback_args will return in callbacks above for *args.
        """

        self.__response_handler__ = {
            "MetaInfo": self.__metainfo,
            "SynthesisCompleted": self.__synthesis_completed,
            "TaskFailed": self.__task_failed
        }
        self.__callback_args = callback_args
        self.__url = url
        self.__appkey = appkey
        self.__akid = akid
        self.__aksecret = aksecret
        self.__token = token
        self.__start_cond = threading.Condition()
        self.__start_flag = False
        self.__on_metainfo = on_metainfo
        self.__on_data = on_data
        self.__on_completed = on_completed
        self.__on_error = on_error
        self.__on_close = on_close
        self.__allow_aformat = (
            "pcm", "wav", "mp3"
                )
        self.__allow_sample_rate = (
            8000, 11025, 16000, 22050,
            24000, 32000, 44100, 48000
                )

    def __handle_message(self, message):
        _logging.debug("__handle_message")
        try:
            __result = json.loads(message)
            if __result["header"]["name"] in self.__response_handler__:
                __handler = self.__response_handler__[__result["header"]["name"]]
                __handler(message)
            else:
                _logging.error("cannot handle cmd{}".format(
                    __result["header"]["name"]))
                return
        except json.JSONDecodeError:
            _logging.error("cannot parse message:{}".format(message))
            return

    def __syn_core_on_open(self):
        _logging.debug("__syn_core_on_open")
        with self.__start_cond:
            self.__start_flag = True
            self.__start_cond.notify()

    def __syn_core_on_data(self, data, opcode, flag):
        _logging.debug("__syn_core_on_data")
        if self.__on_data:
            self.__on_data(data, *self.__callback_args)

    def __syn_core_on_msg(self, msg, *args):
        _logging.debug("__syn_core_on_msg:msg={} args={}".format(msg, args))
        self.__handle_message(msg)

    def __syn_core_on_error(self, msg, *args):
        _logging.debug("__sr_core_on_error:msg={} args={}".format(msg, args))

    def __syn_core_on_close(self):
        _logging.debug("__sr_core_on_close")
        if self.__on_close:
            self.__on_close(*self.__callback_args)
        with self.__start_cond:
            self.__start_flag = False
            self.__start_cond.notify()

    def __metainfo(self, message):
        _logging.debug("__metainfo")
        if self.__on_metainfo:
            self.__on_metainfo(message, *self.__callback_args)

    def __synthesis_completed(self, message):
        _logging.debug("__synthesis_completed")
        self.__nls.shutdown()
        _logging.debug("__synthesis_completed shutdown done")
        if self.__on_completed:
            self.__on_completed(message, *self.__callback_args)
        with self.__start_cond:
            self.__start_flag = False
            self.__start_cond.notify()

    def __task_failed(self, message):
        _logging.debug("__task_failed")
        with self.__start_cond:
            self.__start_flag = False
            self.__start_cond.notify()
        if self.__on_error:
            self.__on_error(message, *self.__callback_args)

    def start(self, text="", voice="xiaoyun",
              aformat="pcm", sample_rate=16000,
              volume=50, speech_rate=0, pitch_rate=0,
              wait_complete=True,
              start_timeout=10,
              completed_timeout=60,
              ex={}):
        """
        Synthesis start 

        Parameters:
        -----------
        text: str
            utf-8 text
        voice: str
            voice for text-to-speech, default is xiaoyun
        aformat: str
            audio binary format, support: "pcm", "wav", "mp3", default is "pcm"
        sample_rate: int
            audio sample rate, default is 16000, support:8000, 11025, 16000, 22050,
            24000, 32000, 44100, 48000
        volume: int
            audio volume, from 0~100, default is 50
        speech_rate: int
            speech rate from -500~500, default is 0
        pitch_rate: int
            pitch for voice from -500~500, default is 0
        wait_complete: bool
            whether block until syntheis completed or timeout for completed timeout
        start_timeout: int
            timeout for connection established
        completed_timeout: int
            timeout for waiting synthesis completed from connection established
        ex: dict
            dict which will merge into "payload" field in request
        """
        self.__nls = NlsCore(
            url=self.__url, akid=self.__akid,
            aksecret=self.__aksecret,
            token=self.__token,
            on_open=self.__syn_core_on_open,
            on_message=self.__syn_core_on_msg,
            on_data=self.__syn_core_on_data,
            on_close=self.__syn_core_on_close,
            on_error=self.__syn_core_on_error,
            callback_args=[])

        if aformat not in self.__allow_aformat:
            raise ValueError("format {} not support".format(aformat))
        if sample_rate not in self.__allow_sample_rate:
            raise ValueError("samplerate {} not support".format(sample_rate))
        
        if volume < 0 or volume > 100:
            raise ValueError("volume {} not support".format(volume))
        
        if speech_rate < -500 or speech_rate > 500:
            raise ValueError("speech_rate {} not support".format(speech_rate))
        
        if pitch_rate < -500 or pitch_rate > 500:
            raise ValueError("pitch rate {} not support".format(pitch_rate))

        __id4 = uuid.uuid4().hex
        self.__task_id = uuid.uuid4().hex

        __header = {
            "message_id": __id4,
            "task_id": self.__task_id,
            "namespace": __SPEECH_SYNTHESIZER_NAMESPACE__,
            "name": __SPEECH_SYNTHESIZER_REQUEST_CMD__["start"],
            "appkey": self.__appkey
        }
        __payload = {
            "text": text,
            "voice": voice,
            "format": aformat,
            "sample_rate": sample_rate,
            "volume": volume,
            "speech_rate": speech_rate,
            "pitch_rate": pitch_rate
        }

        for key in ex:
            __payload[key] = ex[key]

        __msg = {
            "header": __header,
            "payload": __payload,
            "context": _util.GetDefaultContext()    
        }
        __jmsg = json.dumps(__msg)
        with self.__start_cond:
            if self.__start_flag:
                _logging.debug("already start...")
                return False
            if self.__nls.start(__jmsg, ping_interval=0, ping_timeout=None):
                if self.__start_flag == False:
                    if not self.__start_cond.wait(start_timeout):
                        _logging.debug("syn start timeout")
                        return False
                    if not wait_complete:
                        _logging.debug("do not wait completed")
                        return self.__start_flag == True
                    if not self.__start_flag:
                        _logging.debug("started but flag not true")
                        return False
            else:
                _logging.debug("nls core start failed")
                return False
            if self.__start_flag:
                if not self.__start_cond.wait(completed_timeout):
                    _logging.debug("wait completed timeout")
                    return False
                else:
                    return self.__start_flag == False
            else:
                _logging.debug("wait completed but start flag is false")
                return True

    def shutdown(self):
        """
        Shutdown connection immediately
        """
        self.__nls.shutdown()
