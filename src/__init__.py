import logging
import conf
import time
from emoji import emojize
import asyncio
from telethon import TelegramClient, events
from aiogram import Bot, Dispatcher, executor, types, filters
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.utils.callback_data import CallbackData
from aiogram.contrib.fsm_storage.mongo import MongoStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

logging.basicConfig(level=logging.ERROR)
LOGGER = logging.getLogger(conf.LOGGER_NAME)
