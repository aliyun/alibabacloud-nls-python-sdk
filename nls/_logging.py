"""
_logging.py

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

_logger = logging.getLogger("nls")

try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

_logger.addHandler(NullHandler())
_traceEnabled = False
__LOG_FORMAT__ = "%(asctime)s - %(levelname)s - %(message)s"

__all__=["enableTrace", "dump", "error", "warning", "debug", "trace",
        "isEnabledForError", "isEnabledForDebug", "isEnabledForTrace"]

def enableTrace(traceable, handler=logging.StreamHandler()):
    """
    enable log print

    Parameters
    ----------
    traceable: bool
        whether enable log print, default log level is logging.DEBUG
    handler: Handler object
        handle how to print out log, default to stdio
    """
    global _traceEnabled
    _traceEnabled = traceable
    if traceable:
        _logger.addHandler(handler)
        _logger.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(__LOG_FORMAT__))

def dump(title, message):
    if _traceEnabled:
        _logger.debug("### " + title + " ###")
        _logger.debug(message)
        _logger.debug("########################################")

def error(msg):
    _logger.error(msg)

def warning(msg):
    _logger.warning(msg)

def debug(msg):
    _logger.debug(msg)

def trace(msg):
    if _traceEnabled:
        _logger.debug(msg)

def isEnabledForError():
    return _logger.isEnabledFor(logging.ERROR)

def isEnabledForDebug():
    return _logger.isEnabledFor(logging.Debug)

def isEnabledForTrace():
    return _traceEnabled
