import logging
import conf
import time
from emoji import emojize
import asyncio
from telethon import TelegramClient, events, types as client_types
from aiogram import Bot, Dispatcher, executor, filters, types as bot_types
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.utils.callback_data import CallbackData
from aiogram.contrib.fsm_storage.mongo import MongoStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

logging.basicConfig(level=logging.ERROR)
LOGGER = logging.getLogger(conf.APP_NAME)
