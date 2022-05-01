from src import *


class StartQuestion(StatesGroup):
    enter_new_bot_nickname = State()
    enter_channels = State()


_BOT = Bot(token=conf.API_BOT_TOKEN)
_STORAGE = MongoStorage(db_name=conf.APP_NAME)
_DP = Dispatcher(_BOT, storage=_STORAGE)
_CLIENT = TelegramClient(conf.APP_NAME, api_id=conf.API_ID, api_hash=conf.API_HASH)

_is_listen = asyncio.Event()


def run():
    _CLIENT.start(phone=conf.PHONE)
    executor.start_polling(_DP, skip_updates=True)


def stop():
    _CLIENT.disconnect()
    _DP.stop_polling()


# BOT
@_DP.message_handler(filters.CommandStart(), state='*')
async def _send_welcome(message: bot_types.Message, state: FSMContext):
    data = await state.get_data()
    if not data:
        await message.answer(emojize("Тута:eyes:"))
        await message.answer(emojize("Псс придумай мне позывное имя!"))
        await StartQuestion.enter_new_bot_nickname.set()
    else:
        await message.answer(emojize(f"Мы уже начинали когда-то."))
        await message.answer(emojize(f"Когда были моложе:grinning_face_with_sweat:"))
        await message.answer(emojize(f"Напомню, обращайся ко мне как {data['bot_nickname']}:smirking_face:"))


@_DP.message_handler(state=StartQuestion.enter_new_bot_nickname)
async def _enter_new_bot_name(message: bot_types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['bot_nickname'] = message.text
    await message.answer(emojize("Учти, отныне я буду прислушиваться только к ней:face_with_tongue:"))
    await message.answer(emojize("..."))
    await message.answer(emojize("Ну и наконец перечисли каналы из которых мы сформируем твою ЛИЧНУЮ ленту!"))
    await message.answer(emojize("Через запятую конечно же."))
    await StartQuestion.enter_channels.set()


@_DP.message_handler(state=StartQuestion.enter_channels)
async def _enter_channels(message: bot_types.Message, state: FSMContext):
    channels = list(set(message.text.split(',')))
    exist_channels, not_exist_channel_urls = await _check_channels_exist(channels)

    if not_exist_channel_urls:
        await message.answer("Что-то, но не канал:\n"
                             f"{','.join(not_exist_channel_urls)}\n"
                             "Существующие каналы:\n"
                             f"{','.join(list(exist_channels.items()))}\n"
                             )
        await message.answer("Внеси исправления и снова скинь мне!")
        await message.answer(emojize("Не забудь про запятую:smiling_face_with_horns:"))
        await message.answer(emojize("А может это вообще не каналы..."))
        return

    async with state.proxy() as data:
        data['channels'] = list(exist_channels.keys())

    await _save_new_listen_channels(exist_channels)
    await message.answer(emojize("Все запомнил:OK_hand:"))
    await state.reset_state(with_data=False)


@_DP.message_handler()
async def _echo(message: bot_types.Message):
    await message.answer("Тах тах не флуди...")
    await message.answer(emojize("Мы же тут ленту читаем:oncoming_fist:"))


# SUPPORT
async def _check_channels_exist(channel_urls):
    exist_channels = {}
    not_exist_channel_urls = []
    for url in channel_urls:
        try:
            channel_entity = await _CLIENT.get_entity(url)
            channel_id = channel_entity.id
            if isinstance(channel_entity, client_types.Channel):
                exist_channels[channel_id] = url
            else:
                raise ValueError
        except ValueError:
            not_exist_channel_urls.append(url)
    return exist_channels, not_exist_channel_urls


async def _save_new_listen_channels(channels, user_id):
    db = await _STORAGE.get_db()
    collections = await db.list_collections()

    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]
    if conf.LISTEN_CHANNELS_COLL_NAME in collections:
        for channel_id, channel_url in channels:
            channel_bson = channels_coll.find_one({"_id": ObjectId(channel_id)})
            if channel_bson:
                channels_coll.update({'_id': ObjectId(channel_id)},{'$push': {'user_ids': user_id}})
            else:
                channels_coll.insert_one({'_id': ObjectId(channel_id), "url": channel_url, 'user_ids': [user_id]})
    else:
        channels_coll.insert_many({{'_id': ObjectId(id), "url": url, 'user_ids': [user_id]} for id, url in channels})


# LISTENER
def _run_listener(channel_urls):
    async def _listen():
        _CLIENT.add_event_handler(_on_new_channel_message, events.NewMessage(channel_urls))
        while not _is_listen.is_set():
            await asyncio.sleep(1)

    _CLIENT.loop.run_until_complete(_listen())


async def _on_new_channel_message():
    pass


if __name__ == '__main__':
    try:
        run()
    finally:
        stop()
