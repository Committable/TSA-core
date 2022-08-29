import logging
import os
import time

import global_params


def get_logger(name=''):
    logger = logging.getLogger('mylogger')
    logger.setLevel(logging.DEBUG)  # 统一设置log打印级别
    logger.handler = []
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] '
        '[%(thread)d]: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')
    root_time = time.time() * 1000000
    fh = logging.FileHandler(
        os.path.join(global_params.DEST_PATH,
                     name + '_' + str(int(root_time)) + '.log'))
    fh.setFormatter(formatter)

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)

    if global_params.DEBUG_MOD:
        fh.setLevel(logging.DEBUG)
        ch.setLevel(logging.DEBUG)
    else:
        fh.setLevel(logging.INFO)
        ch.setLevel(logging.INFO)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


mylogger = None
