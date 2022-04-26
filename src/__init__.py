import logging
import conf
from emoji import emojize
from aiogram import Bot, Dispatcher, executor, types

logging.basicConfig(level=logging.ERROR)
LOGGER = logging.getLogger(conf.LOGGER_NAME)
