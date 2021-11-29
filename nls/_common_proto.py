"""
_common_proto.py

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

__URL__ = "wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1"
__all__ = ["NlsCommonProto"]


class NlsCommonProto:
    """
    Api for users to define their own protocols correspond to cloud
    applications. 

    """
    def __init__(self, url=__URL__,
                 akid=None, aksecret=None,
                 token=None, appkey=None,
                 namespace=None,
                 on_open=None,
                 on_error=None,
                 on_close=None,
                 on_data=None,
                 user_callback={},
                 callback_args=[]):
        """
        NlsCommonProto initialization

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
            appkey from aliyun.
        namespace: str
            protocol namespace.
        on_open: function
            Callback object which is called when connection established.
            on_start has one argument.
            The 1st argument is *args which is callback_args.
        on_error: function
            Callback object which is called when any error occurs.
            on_error has two arguments.
            The 1st argument is message which is a json format string.
            The 2nd argument is *args which is callback_args.
        on_close: function
            Callback object which is called when connection closed.
            on_close has one arguments.
            The 1st argument is *args which is callback_args.
        on_data: function
            Callback object which is called when partial synthesis result arrived
            arrived.
            on_result_changed has two arguments.
            The 1st argument is binary data corresponding to aformat in start
            method.
            The 2nd argument is *args which is callback_args.
        user_callback: dict
            Dict for users to define their handlers. Key is name for cloud response
            "name" field in "head". Value is method to handle this response.
        callback_args: list
            callback_args will return in callbacks above for *args.
        """
        if not namespace:
            raise ValueError("no namespace provided")
        self.__namespace = namespace
        self.__response_handler__ = {
            "TaskFailed": self.__task_failed
        }
        for key in user_callback:
            self.__response_handler__[key] = user_callback[key]
        self.__callback_args = callback_args
        self.__appkey = appkey
        self.__url = url
        self.__akid = akid
        self.__aksecret = aksecret
        self.__token = token
        self.__on_open = on_open
        self.__on_error = on_error
        self.__on_close = on_close
        self.__on_data = on_data
        
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

    def __common_core_on_open(self):
        _logging.debug("__common_core_on_open")
        if self.__on_open:
            self.__on_open(*self.__callback_args)

    def __common_core_on_msg(self, msg, *args):
        _logging.debug("__common_core_on_msg:msg={} args={}".format(msg, args))
        self.__handle_message(msg)

    def __common_core_on_data(self, data, opcode, flag):
        _logging.debug("__common_core_on_data")
        if self.__on_data:
            self.__on_data(data, *self.__callback_args)

    def __common_core_on_error(self, msg, *args):
        _logging.debug("__common_core_on_error:msg={} args={}".format(msg, args))

    def __common_core_on_close(self):
        _logging.debug("__common_core_on_close")
        if self.__on_close:
            self.__on_close(*self.__callback_args)

    def __task_failed(self, message):
        _logging.debug("__task_failed")
        with self.__start_cond:
            self.__start_flag = False
            self.__start_cond.notify()
        if self.__on_error:
            self.__on_error(message, *self.__callback_args)

    def start(self, name="",
              payload={},
              context={},
              ping_interval=8,
              ping_timeout=None):
        """
        Protocol async starts

        Parameters:
        -----------
        name: str
            current request "name" in "header" field
        payload: dict
            payload for current request
        context: dict
            context for current request
        ping_interval: int
            send ping interval, 0 for disable ping send, default is 8
        ping_timeout: int
            timeout after send ping and recive pong, set None for disable timeout check and default is None
        """
        self.__nls = NlsCore(
            url=self.__url, akid=self.__akid,
            aksecret=self.__aksecret, token=self.__token,
            on_open=self.__common_core_on_open,
            on_message=self.__common_core_on_msg,
            on_data=self.__common_core_on_data,
            on_close=self.__common_core_on_close,
            on_error=self.__common_core_on_error,
            asynch=True,
            callback_args=[])

        if not name:
            raise ValueError("no name provided")
        __id4 = uuid.uuid4().hex
        self.__task_id = uuid.uuid4().hex

        __header = {
            "message_id": __id4,
            "task_id": self.__task_id,
            "namespace": self.__namespace,
            "name": name,
            "appkey": self.__appkey
        }

        __msg = {
            "header": __header,
            "payload": payload,
            "context": context
        }
        __jmsg = json.dumps(__msg)
        return self.__nls.start(__jmsg, ping_interval, ping_timeout)
    
    def shutdown(self):
        """
        Shutdown connection immediately
        """
        self.__nls.shutdown()


    def send_text(self, name="", payload={}, context={}):
        """
        Send text request to cloud

        Parameters:
        -----------
        name: str
            "name" in "header" field
        payload: dict
            "payload" in request
        context: dict
            "context" in request
        """
        if not name:
            raise ValueError("no name provided")
        __id4 = uuid.uuid4().hex
        __header = {
            "message_id": __id4,
            "task_id": self.__task_id,
            "namespace": self.__namespace,
            "name": name,
            "appkey": self.__appkey
        }

        __msg = {
            "header": __header,
            "payload": payload,
            "context": context
        }
        __jmsg = json.dumps(__msg)
        try:
            self.__nls.send(__jmsg, False)
        except ConnectionResetError as e:
            _logging.error("connection reset")
            self.__nls.shutdown()
            raise e
            return False
        return True

    def send_binary(self, pcm_data):
        """
        Send binary data to cloud

        Parameters:
        -----------
        pcm_data: bytes
            binary data
        """
        try:
            self.__nls.send(pcm_data, True)
        except ConnectionResetError as __e:
            _logging.error("connection reset")
            self.__nls.shutdown()
            raise __e
            return False
        return True
