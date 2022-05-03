from src import *


class StartQuestion(StatesGroup):
    enter_new_bot_nickname = State()
    enter_channels = State()


_BOT = Bot(token=conf.API_BOT_TOKEN)
_STORAGE = MongoStorage(db_name=conf.APP_NAME)
_DP = Dispatcher(_BOT, storage=_STORAGE)
_CLIENT = TelegramClient(conf.APP_NAME, api_id=conf.API_ID, api_hash=conf.API_HASH)

_is_listen_event = asyncio.Event()


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
        await message.answer(emojize("Перечисли каналы из которых мы сформируем твою ЛИЧНУЮ ленту!"))
        await message.answer(emojize("Через запятую конечно же."))
        await StartQuestion.enter_channels.set()
    else:
        await message.answer(emojize(f"Мы уже начинали когда-то."))
        await message.answer(emojize(f"Когда были моложе:grinning_face_with_sweat:"))


@_DP.message_handler(state=StartQuestion.enter_channels)
async def _enter_channels(message: bot_types.Message, state: FSMContext):
    channels = list(set(message.text.split(',')))
    exist_channels, not_exist_channel_urls = await _check_channels_exist(channels)

    if not_exist_channel_urls:
        await message.answer("Что-то, но не канал:\n"
                             f"{','.join(not_exist_channel_urls)}\n"
                             "Существующие каналы:\n"
                             f"{','.join(list(exist_channels.values()))}\n"
                             )
        await message.answer("Внеси исправления и снова скинь мне!")
        await message.answer(emojize("Не забудь про запятую:smiling_face_with_horns:"))
        await message.answer(emojize("А может это вообще не каналы..."))
        return

    async with state.proxy() as data:
        data['channel_ids'] = list(exist_channels.keys())

    await _save_new_listen_channels(channels=exist_channels, user_id=message.from_user.id)
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
            entity = await _CLIENT.get_entity(url)
            if isinstance(entity, client_types.Channel):
                tg_str = '(https://)?(t.me/)?(\s+)?'
                channel_id = entity.id
                exist_channels[channel_id] = re.sub(tg_str, '', url)
            else:
                raise ValueError
        except ValueError:
            not_exist_channel_urls.append(url)
    return exist_channels, not_exist_channel_urls


async def _save_new_listen_channels(channels, user_id, db_name=conf.APP_NAME):
    client = await _STORAGE.get_client()
    db = client[db_name]

    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]
    if conf.LISTEN_CHANNELS_COLL_NAME in list(await db.list_collection_names()):
        for channel_id, channel_url in channels.items():
            channel_bson = [obj async for obj in channels_coll.find({"_id": object_id_from_int(channel_id)})]
            if channel_bson:
                await channels_coll.update_one({'_id': object_id_from_int(channel_id)},
                                               {'$push': {'user_ids': user_id}})
            else:
                await channels_coll.insert_one(
                    {'_id': object_id_from_int(channel_id), "url": channel_url, 'user_ids': [user_id]})
    else:
        data = [{'_id': object_id_from_int(id), "url": url, 'user_ids': [user_id]} for id, url in channels.items()]
        await channels_coll.insert_many(data)


def object_id_from_int(n):
    s = str(n)
    s = '0' * (24 - len(s)) + s
    return bson.ObjectId(s)


def int_from_object_id(obj):
    return int(str(obj))


# LISTENER
def _run_listener(channel_urls):
    async def _listen():
        _CLIENT.add_event_handler(_on_new_channel_message, events.NewMessage(channel_urls))
        while not _is_listen_event.is_set():
            await asyncio.sleep(1)

    _CLIENT.loop.run_until_complete(_listen())


async def _on_new_channel_message():
    pass


if __name__ == '__main__':
    try:
        run()
    finally:
        _is_listen_event.set()
        stop()
