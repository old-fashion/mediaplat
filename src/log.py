# -*- coding: utf-8 -*-

import logging
from logging.handlers import RotatingFileHandler

DEBUG  = True
FORMAT = '%(asctime)s %(levelname)-8s %(filename)s:%(funcName)s() : %(message)s'

class ColoredFormatter(logging.Formatter):
    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

    #These are the sequences need to get colored ouput
    RESET_SEQ  = "\033[0m"
    COLOR_SEQ  = "\033[1;40;%dm"
    PASTEL_SEQ = "\033[0;40;%dm"
    BOLD_SEQ = "\033[1m"

    COLORS = {
        'DEBUG': BLUE,
        'INFO': CYAN,
        'CRITICAL': YELLOW,
        'WARNING': BLACK,
        'ERROR': MAGENTA,
        'EXCEPTION': RED
    }

    FORMAT = '%(asctime)s %(levelname)-8s %(filename)s:%(funcName)s() : %(message)s'

    def __init__(self):
        logging.Formatter.__init__(self, self.formatter_message(FORMAT))

    def formatter_message(self, message):
        return message.replace("$RESET", self.RESET_SEQ).replace("$BOLD", self.BOLD_SEQ)

    def format(self, record):
        levelname = record.levelname
        record.asctime   = self.BOLD_SEQ + record.asctime + self.RESET_SEQ
        record.filename  = self.BOLD_SEQ + self.COLOR_SEQ  % (30 + self.GREEN) + record.filename 
        record.funcName  = self.PASTEL_SEQ % (30 + self.GREEN) + record.funcName + self.RESET_SEQ
        record.levelname = self.COLOR_SEQ  % (30 + self.COLORS[levelname]) + levelname + self.RESET_SEQ
        return logging.Formatter.format(self, record)

def init_log(filter=None):
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)

    formatter = logging.Formatter(FORMAT)

    # add file rotation handler 
    file_handler = RotatingFileHandler(
                        filename = '/var/log/mediaplat/mediaplat.log',
                        maxBytes = 1024 * 1024,
                        backupCount = 5,
                        mode = 'a+')

    stream_handler = logging.StreamHandler()

    if filter:
        file_handler.addFilter(filter)
        stream_handler.addFilter(filter)

    # log to file
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    log.addHandler(file_handler)

    if DEBUG:
        # duplicate log to stdout with color
        stream_handler.setLevel(logging.DEBUG)
        stream_handler.setFormatter(ColoredFormatter())
        log.addHandler(stream_handler)

init_log(logging.Filter('mediaplat.plugin'))

log  = logging.getLogger('mediaplat.plugin')
clog = logging.getLogger('mediaplat.content')
