'''
_core.py

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
'''


import logging
import threading

from enum import Enum, unique
from queue import Queue

import nls.websocket as websocket
import nls._token

from . import _logging

__URL__ = "wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1"
__HEADER__ = [
    "Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==",
    "Sec-WebSocket-Version: 13",
]

__FORMAT__ = "%(asctime)s - %(levelname)s - %(message)s"
#__all__ = ["NlsCore"]

def core_on_msg(ws, message, args):
    _logging.debug("core_on_msg:{}".format(message))
    if not args:
        _logging.error("callback core_on_msg with null args")
        return
    nls = args[0]
    nls._NlsCore__issue_callback("on_message", [message])

def core_on_error(ws, message, args):
    _logging.debug("core_on_error:{}".format(message))
    if not args:
        _logging.error("callback core_on_error with null args")
        return
    nls = args[0]
    nls._NlsCore__issue_callback("on_error", [message])

def core_on_close(ws, close_status_code, close_msg, args):
    _logging.debug("core_on_close")
    if not args:
        _logging.error("callback core_on_close with null args")
        return
    nls = args[0]
    nls._NlsCore__issue_callback("on_close")

def core_on_open(ws, args):
    _logging.debug("core_on_open:{}".format(args))
    if not args:
        _logging.debug("callback with null args")
        ws.close()
    elif len(args) != 2:
        _logging.debug("callback args not 2")
        ws.close()
    nls = args[0]
    nls._NlsCore__notify_on_open()
    nls.start(args[1], nls._NlsCore__ping_interval, nls._NlsCore__ping_timeout)
    nls._NlsCore__issue_callback("on_open")

def core_on_data(ws, data, opcode, flag, args):
    _logging.debug("core_on_data opcode={}".format(opcode))
    if not args:
        _logging.error("callback core_on_data with null args")
        return
    nls = args[0]
    nls._NlsCore__issue_callback("on_data", [data, opcode, flag])

@unique
class NlsConnectionStatus(Enum):
    Disconnected = 0
    Connected = 1


class NlsCore:
    """
    NlsCore
    """
    def __init__(self, url=__URL__,
                 akid=None, aksecret=None, token=None,
                 on_open=None, on_message=None, on_close=None,
                 on_error=None, on_data=None, asynch=False, callback_args=[]):
        self.__url = url
        self.__async = asynch
        if not akid or not aksecret:
            if not token:
                raise ValueError("akid aksecret and toke are all None")
            else:
                self.__get_token = False
                self.__token = token
        else:
            self.__get_token = True
        self.__callbacks = {}
        if on_open:
            self.__callbacks["on_open"] = on_open
        if on_message:
            self.__callbacks["on_message"] = on_message
        if on_close:
            self.__callbacks["on_close"] = on_close
        if on_error:
            self.__callbacks["on_error"] = on_error
        if on_data:
            self.__callbacks["on_data"] = on_data

        if not on_open and not on_message and not on_close and not on_error:
            raise ValueError("all callbacks are None, what are you doing?")

        _logging.debug("callback args:{}".format(callback_args))
        self.__callback_args = callback_args

        if self.__get_token:
            token = nls._token.getToken(akid, aksecret)
            _logging.debug("get token {}".format(token))
            self.__token = token
        self.__header = __HEADER__ + ["X-NLS-Token: {}".format(self.__token)]
        websocket.enableTrace(True)
        self.__ws = websocket.WebSocketApp(self.__url,
                                           self.__header,
                                           on_message=core_on_msg,
                                           on_data=core_on_data,
                                           on_error=core_on_error,
                                           on_close=core_on_close,
                                           callback_args=[self])
        self.__ws.on_open = core_on_open
        self.__lock = threading.Lock()
        self.__cond = threading.Condition()
        self.__connection_status = NlsConnectionStatus.Disconnected
        self.__pending_msg = []

    def start(self, msg, ping_interval, ping_timeout):
        self.__lock.acquire()
        self.__ping_interval = ping_interval
        self.__ping_timeout = ping_timeout
        if self.__connection_status == NlsConnectionStatus.Disconnected:
            self.__ws.update_args(self, msg)
            self.__lock.release()
            return self.__connect_before_start(ping_interval, ping_timeout)
        else:
            self.__lock.release()
            self.__ws.send(msg)
            return True

    def __notify_on_open(self):
        _logging.debug("notify on open")
        with self.__cond:
            self.__connection_status = NlsConnectionStatus.Connected
            self.__cond.notify()

    def __issue_callback(self, which, exargs=[]):
        if which not in self.__callbacks:
            _logging.error("no such callback:{}".format(which))
            return
        if which is "on_close":
            with self.__cond:
                self.__connection_status = NlsConnectionStatus.Disconnected
                self.__cond.notify()
        args = exargs+self.__callback_args
        self.__callbacks[which](*args)

    def send(self, msg, binary):
        self.__lock.acquire()
        if self.__connection_status == NlsConnectionStatus.Disconnected:
            self.__lock.release()
            _logging.error("start before send")
            return False
        else:
            self.__lock.release()
            if binary:
                self.__ws.send(msg, opcode=websocket.ABNF.OPCODE_BINARY)
            else:
                _logging.debug("send {}".format(msg))
                self.__ws.send(msg)
            return True
    
    def shutdown(self):
        self.__ws.close()

    def __run(self, ping_interval, ping_timeout):
        _logging.debug("ws run...")
        self.__ws.run_forever(ping_interval=ping_interval,
                ping_timeout=ping_timeout)
        with self.__lock:
            self.__connection_status = NlsConnectionStatus.Disconnected
        _logging.debug("ws exit...")

    def __connect_before_start(self, ping_interval, ping_timeout):
        with self.__cond:
            self.__th = threading.Thread(target=self.__run,
                    args=[ping_interval, ping_timeout])
            self.__th.start()
            if self.__connection_status == NlsConnectionStatus.Disconnected:
                _logging.debug("wait cond wakeup")
                if not self.__async:
                    if self.__cond.wait(timeout=10):
                        _logging.debug("wakeup without timeout")
                        return self.__connection_status == NlsConnectionStatus.Connected
                    else:
                        _logging.debug("wakeup with timeout")
                        return False
        return True
