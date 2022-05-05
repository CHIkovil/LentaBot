from src import *


class StartQuestion(StatesGroup):
    enter_new_bot_nickname = State()
    enter_channels = State()


_BOT = Bot(token=conf.API_BOT_TOKEN)
_STORAGE = MongoStorage(db_name=conf.APP_NAME)
_DP = Dispatcher(_BOT, storage=_STORAGE)
_CLIENT = TelegramClient(conf.APP_NAME, api_id=conf.API_ID, api_hash=conf.API_HASH)


def run():
    _CLIENT.start(phone=conf.PHONE)
    executor.start_polling(_DP, skip_updates=True)


def stop():
    _CLIENT.disconnect()
    _DP.stop_polling()


# COMMAND
@_DP.message_handler(commands=['start'], state='*')
async def _on_start(message: bot_types.Message, state: FSMContext):
    if not await state.get_data():
        await message.answer(emojize("Тута:eyes:"))
        await message.answer(emojize("Перечисли каналы из которых мы сформируем твою ЛИЧНУЮ ленту!"))
        await message.answer(emojize("Через запятую конечно же."))
        await StartQuestion.enter_channels.set()
    else:
        await message.answer(emojize(f"Мы уже начинали когда-то."))
        await message.answer(emojize(f"Когда были моложе:grinning_face_with_sweat:"))
        await message.answer("Воспользуйся /help")


@_DP.message_handler(commands=['help'])
async def _on_help(message: bot_types.Message):
    await message.answer("Это help")


@_DP.message_handler(commands=['on'], state='*')
async def _start_tape(message: bot_types.Message, state: FSMContext):
    if (await state.get_data())['is_listen']:
        await message.answer(emojize("Как бы лента уже запущена:grinning_face_with_sweat:"))
    else:
        async with state.proxy() as data:
            data['is_listen'] = True
        await message.answer(emojize("Лента запущена:rocket:"))
        await _run_listener()


@_DP.message_handler(commands=['off'], state='*')
async def _stop_tape(message: bot_types.Message, state: FSMContext):
    if (await state.get_data())['is_listen']:
        async with state.proxy() as data:
            data['is_listen'] = False
        await message.answer(emojize("Лента остановлена:stop_sign:"))
        await _stop_listener()
    else:
        await message.answer(emojize("Как остановить то, что даже не запустили:smiling_face_with_tear:"))


@_DP.message_handler()
async def _echo(message: bot_types.Message):
    await message.answer("Тах тах не флуди...")
    await message.answer(emojize("Мы же тут ленту читаем:oncoming_fist:"))
    await message.answer("Воспользуйся /help")


# STATE
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
        data['channels'] = list(exist_channels.keys())
        data['is_listen'] = False

    await _save_new_listen_channels(channels=exist_channels, user_id=message.from_user.id)
    await message.answer(emojize("Все запомнил:OK_hand:"))
    await state.reset_state(with_data=False)


# SUPPORT
async def _check_channels_exist(channel_urls):
    exist_channels = {}
    not_exist_channel_urls = []
    for url in channel_urls:
        try:
            entity = await _CLIENT.get_entity(url)
            if isinstance(entity, client_types.Channel):
                tg_str = r'(https://)?(t.me/)?(\s+)?'
                exist_channels[entity.id] = re.sub(tg_str, '', url)
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
        for id, nickname in channels.items():
            channel_obj = [obj async for obj in channels_coll.find({"id": id})]
            if channel_obj:
                await channels_coll.update_one({'id': id},
                                               {'$push': {'users': user_id}})
            else:
                await channels_coll.insert_one(
                    {'id': id, "nickname": nickname, 'users': [user_id]})
    else:
        data = [{'id': id, "nickname": nickname, 'users': [user_id]} for id, nickname in channels.items()]
        await channels_coll.insert_many(data)


# LISTENER
_listen_channels = None


async def _run_listener():
    client = await _STORAGE.get_client()
    db = client[conf.APP_NAME]
    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]

    _listen_channels = [obj['nickname'] async for obj in channels_coll.find({})]
    _CLIENT.add_event_handler(_on_new_channel_message, events.NewMessage(chats=_listen_channels))


async def _stop_listener():
    _CLIENT.remove_event_handler(_on_new_channel_message, events.NewMessage(chats=_listen_channels))


async def _on_new_channel_message(event: events.NewMessage.Event):
    client = await _STORAGE.get_client()
    db = client[conf.APP_NAME]
    users_coll = db['users']

    channel_id = abs(10 ** 12 + event.chat_id)
    listen_users = [obj['personal_channel']
                    async for obj in users_coll.find({"$and": [{"data.channels": {'$in': [channel_id]}},
                                                               {"data.is_listen": True}]})]

    if listen_users:
        for url in listen_users:
            await _CLIENT.forward_messages(entity=url, messages=event.message)


if __name__ == '__main__':
    try:
        run()
    finally:
        stop()
