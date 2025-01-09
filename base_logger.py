#!/usr/bin/python

# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License

"""Provides a consistent logging setup for the Migratool.

This module sets up a logger named "Migratool" with configurable handler, level, and format. # noqa
It supports logging to a file or stream, and uses a custom formatter for colored output.  # noqa
Environment variables can be used to control the logger's behavior.

Environment Variables:

- `EXEC_INFO`: If set to "True", exception information will be included.  
- `LOG_HANDLER`: Specifies the logging handler. Can be "File" or "Stream".
- `LOG_FILE_PATH`: If LOG_HANDLER is "File", this specifies the file path.
- `LOGLEVEL`: Sets the logging level. 
    Can be one of 
    "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", or "NOTSET".
    Defaults to "WARNING".
"""

import os
import logging

EXEC_INFO = os.getenv("EXEC_INFO") == "True"
LOG_HANDLER = os.getenv("LOG_HANDLER", "Stream")
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "app.log")
LOGLEVEL = os.getenv('LOGLEVEL', 'INFO').upper()

if LOG_HANDLER not in {"File", "Stream"}:
    LOG_HANDLER = "Stream"

if LOGLEVEL not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}:
    LOGLEVEL = "WARNING"


class CustomFormatter(logging.Formatter):
    """A custom formatter for colored logging output.

    Provides colored output for different log levels using ANSI escape codes.
    The format includes timestamp, logger name, level, message
    and file location.
    """

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"  # noqa pylint: disable=C0301

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):  # pylint: disable=E0102
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


logger = logging.getLogger("Migratool")

if LOG_HANDLER == "File":
    ch = logging.FileHandler(LOG_FILE_PATH, mode="a")
else:
    ch = logging.StreamHandler()

# Set handler and logger to the same level
ch.setLevel(getattr(logging, LOGLEVEL))
logger.setLevel(ch.level)

ch.setFormatter(CustomFormatter())

logger.addHandler(ch)
