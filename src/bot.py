import logging

from Support import *
import conf


class StartQuestionStates(StatesGroup):
    enter_personal_channel = State()
    enter_initial_listen_channels = State()


class UpdateStates(StatesGroup):
    enter_add_listen_channels = State()
    enter_delete_listen_channel = State()


_BOT = Bot(token=conf.API_BOT_TOKEN)
_STORAGE = MongoStorage(db_name=conf.APP_NAME)
_DP = Dispatcher(_BOT, storage=_STORAGE)
_CLIENT = TelegramClient(conf.APP_NAME, api_id=conf.API_ID, api_hash=conf.API_HASH)
_LOGGER = logging.getLogger(conf.APP_NAME)


def run():
    _CLIENT.start(phone=conf.PHONE)
    _CLIENT.loop.run_until_complete(_notify_users_about_engineering_works(is_start=True))
    _CLIENT.loop.run_until_complete(_reload_listener())
    executor.start_polling(_DP, skip_updates=True, loop=_CLIENT.loop)


# COMMAND
@_DP.message_handler(commands=['start'], state='*')
async def _on_start(message: bot_types.Message, state: FSMContext):
    if not await state.get_data():
        await message.answer(emojize("Тута:eyes:"))
        await message.answer(emojize("Ну смотри, для ленты нужно создать свой ПУБЛИЧНЫЙ канал!"))
        await message.answer(emojize("Потом добавь меня "
                                     "как администратора:smiling_face_with_sunglasses:"))
        await message.answer(emojize("Учти, что правильность пунктов выше очень важна для нашей дружбы!"))
        await message.answer(emojize("Какая ссылка на твой личный канал, чтобы не запутаться?"))
        await StartQuestionStates.enter_personal_channel.set()
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
        await message.answer(emojize(f"Лента запущена:rocket:"))


@_DP.message_handler(commands=['off'], state='*')
async def _stop_tape(message: bot_types.Message, state: FSMContext):
    if (await state.get_data())['is_listen']:
        async with state.proxy() as data:
            data['is_listen'] = False
        await message.answer(
            emojize(f"Лента остановлена :stop_sign:"))
    else:
        await message.answer(emojize("Как остановить то, что даже не запустили:smiling_face_with_tear:"))


@_DP.message_handler(commands=['add'])
async def _add_listen_channel(message: bot_types.Message):
    await message.answer(emojize("Слушаю:ear:"))
    await message.answer(emojize("Накидывай каналы, которые хочешь добавить."))
    await message.answer(emojize("Как закончишь скажи просто \n /everything"))
    await UpdateStates.enter_add_listen_channels.set()


@_DP.message_handler(commands=['delete'], state='*')
async def _delete_listen_channel(message: bot_types.Message, state: FSMContext):
    if (await state.get_data())['listen_channels']:
        await message.answer(emojize("Внимаю:baby_chick:"))
        await message.answer(emojize("Какой канал хочешь удалить?"))
        await message.answer(emojize("Можешь просто кинуть его порядковый номер в списке твоих подписок:winking_face:"))
        await UpdateStates.enter_delete_listen_channel.set()
    else:
        await message.answer(emojize("Что мы решили удалить из подписок, если нет ни одной:thought_balloon:"))
        await message.answer(emojize("Сначала добавь хоть одну /add"))


@_DP.message_handler()
async def _echo(message: bot_types.Message):
    await message.answer(emojize("Тах тах не флуди...:oncoming_fist:"))
    await message.answer("Воспользуйся /help")


# STATE
@_DP.message_handler(state=StartQuestionStates.enter_personal_channel)
async def _enter_personal_channel(message: bot_types.Message, state: FSMContext):
    exist_channels, not_exist_channel_entities = await _check_channels_exist([message.text])

    if not_exist_channel_entities:
        await message.answer(emojize("Хмм..."))
        await message.answer(emojize("Что-то не похоже на канал:thinking_face:"))
        return

    if not await _check_bot_is_channel_admin(list(exist_channels.keys())[0]):
        await message.answer(emojize("Тах тах я не администратор этого канала:red_question_mark:"))
        await message.answer(emojize("Жду cсылку на канал..."))
        await message.answer(emojize("Учти, я проверю:smiling_face_with_horns:"))
        return

    async with state.proxy() as data:
        data['tape_channel'] = list(exist_channels.keys())[0]

    await message.answer(emojize("Далее перечисли ПУБЛИЧНЫЕ каналы из которых мы сформируем твою ЛИЧНУЮ ленту!"))
    await message.answer(emojize("Через запятую конечно же."))
    await message.answer(emojize("Можешь скинуть пока хотя бы одну, чтобы не тратить время..."))
    await message.answer(
        emojize("После того как познакомимся, сможешь быстро накидать мне остальные:winking_face_with_tongue:"))
    await message.answer(emojize("Учти, что некоторые каналы могут запрещать пересылку сообщений."))
    await message.answer(emojize("С такими мы не дружим:warning:"))
    await StartQuestionStates.enter_initial_listen_channels.set()


@_DP.message_handler(state=StartQuestionStates.enter_initial_listen_channels)
async def _enter_initial_listen_channels(message: bot_types.Message, state: FSMContext):
    channels = list(set(message.text.split(',')))
    exist_channels, not_exist_channel_entities = await _check_channels_exist(channels)

    if not_exist_channel_entities:
        await message.answer("Что-то, но не каналы:\n"
                             f"{','.join(not_exist_channel_entities)}\n")
        if exist_channels:
            await message.answer("Существующие каналы:\n"
                                 f"{','.join(list(exist_channels.values()))}\n")

        await message.answer("Внеси исправления и снова скинь все мне!")
        await message.answer(emojize("Не забудь про запятую:smiling_face_with_horns:"))
        return

    async with state.proxy() as data:
        data['listen_channels'] = list(exist_channels.keys())
        data['is_listen'] = False
        await _join_new_listen_channels_to_client(list(exist_channels.keys()))
        await _save_new_listen_channels_to_common_collection(list(exist_channels.keys()), user_id=message.from_user.id)
        await _reload_listener()
        await message.answer(emojize("Все запомнил:OK_hand:"))
        await message.answer("Воспользуйся /help")
        await state.reset_state(with_data=False)


@_DP.message_handler(state=UpdateStates.enter_add_listen_channels)
async def _enter_add_listen_channels(message: bot_types.Message, state: FSMContext):
    if message.text == '/everything':
        await message.answer(emojize("Принял:handshake:"))
        await _reload_listener()
        await state.reset_state(with_data=False)
        return

    exist_channels, not_exist_channel_entities = await _check_channels_exist([message.text])

    if not_exist_channel_entities:
        await message.answer(emojize("Что-то не похоже на канал:thinking_face:"))
        await message.answer(emojize("Исправь и снова скинь мне..."))
        return

    async with state.proxy() as data:
        new_channel_id = list(exist_channels.keys())[0]
        if new_channel_id not in data['listen_channels']:
            data['listen_channels'].append(new_channel_id)
            await _join_new_listen_channels_to_client([new_channel_id])
            await _save_new_listen_channels_to_common_collection([new_channel_id], message.from_user.id)
            await message.answer(emojize("Добавил:check_mark_button:"))
        else:
            await message.answer(emojize("А такой канал уже есть в твоих подписках..."))
            await message.answer(emojize("Давай другой:beaming_face_with_smiling_eyes:"))


@_DP.message_handler(state=UpdateStates.enter_delete_listen_channel)
async def _enter_delete_listen_channel(message: bot_types.Message, state: FSMContext):

    del_channel_id = None

    if message.text.isnumeric():
        async with state.proxy() as data:
            channel_ind = int(message.text)
            if len(data['listen_channels']) > channel_ind:
                listen_channels = data['listen_channels']
                del_channel_id = listen_channels[channel_ind]
            elif len(data['listen_channels']) == channel_ind:
                await message.answer(emojize("Не забывай, что номера каналов в списке подписок начинаются с 0!"))
                await message.answer(emojize("Учти это и попробуй снова:smiling_face_with_smiling_eyes:"))
            else:
                await message.answer(emojize("Тах тах, почему номер канала, "
                                             "больше чем количество этих самых подписок?:face_with_hand_over_mouth:"))
                await message.answer(emojize("Попробуй снова:oncoming_fist:"))

    else:
        exist_channels, not_exist_channel_entities = await _check_channels_exist([message.text])

        if not_exist_channel_entities:
            await message.answer(emojize("Что-то не похоже на канал:thinking_face:"))
            await message.answer(emojize("Исправь и снова скинь мне..."))
            return

        del_channel_id = list(exist_channels.keys())[0]
        async with state.proxy() as data:
            if del_channel_id not in data['listen_channels']:
                await message.answer(emojize("Такого канала нет в твоих подписках:thinking_face:"))
                return

    async with state.proxy() as data:
        data['listen_channels'].remove(del_channel_id)
        deleted_channel_ids = await _delete_listen_channels_to_common_collection([del_channel_id],
                                                                                 user_id=message.from_user.id)
        if deleted_channel_ids:
            await _delete_channels_to_client(deleted_channel_ids)
            await _reload_listener()

        await message.answer(emojize("Удалил:check_mark_button:"))
        await state.reset_state(with_data=False)
        return


# SUPPORT
async def _check_channels_exist(channel_entities):
    exist_channels = {}
    not_exist_channel_entities = []
    for entity in channel_entities:
        try:
            obj = await _CLIENT.get_entity(entity)
            if isinstance(obj, client_types.Channel):
                exist_channels[obj.id] = f"https://t.me/{obj.username}"
            else:
                not_exist_channel_entities.append(entity)
        except ValueError:
            not_exist_channel_entities.append(entity)
        except Exception as err:
            _LOGGER.error(err)
    return exist_channels, not_exist_channel_entities


async def _join_new_listen_channels_to_client(channel_ids):
    channel_dialog_ids = {dialog.entity.id async for dialog in _CLIENT.iter_dialogs(archived=True) if dialog.is_channel}
    not_join_channel = list(set(channel_ids) - channel_dialog_ids)

    if not_join_channel:
        for id in not_join_channel:
            await _CLIENT(JoinChannelRequest(channel=id))
            await _CLIENT(UpdateNotifySettingsRequest(peer=id,
                                                      settings=client_types.InputPeerNotifySettings(
                                                          mute_until=2 ** 31 - 1
                                                      )))
            await _CLIENT.edit_folder(id, folder=1)


async def _save_new_listen_channels_to_common_collection(channel_ids, user_id, db_name=conf.APP_NAME):
    client = await _STORAGE.get_client()
    db = client[db_name]
    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]

    if conf.LISTEN_CHANNELS_COLL_NAME in list(await db.list_collection_names()):
        for id in channel_ids:
            channel_obj = [obj async for obj in channels_coll.find({"id": id})]
            if channel_obj:
                await channels_coll.update_one({'id': id},
                                               {'$push': {'users': user_id}})
            else:
                await channels_coll.insert_one(
                    {'id': id, 'users': [user_id]})
    else:
        data = [{'id': id, 'users': [user_id]} for id in channel_ids]
        await channels_coll.insert_many(data)


async def _check_bot_is_channel_admin(channel_id):
    try:
        member = await _BOT.get_chat_member(-(10 ** 12 + channel_id), conf.API_BOT_TOKEN.split(":")[0])
        if member.status == 'administrator':
            return True
        else:
            return False
    except ChatNotFound:
        return False
    except Exception as err:
        _LOGGER.error(err)


async def _delete_everywhere_listen_channels(channel_ids):
    client = await _STORAGE.get_client()
    db = client[conf.APP_NAME]
    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]
    users_coll = db["aiogram_data"]

    await channels_coll.delete_many({"id": {'$in': channel_ids}})
    await users_coll.update_many({}, {"$pull": {"data.listen_channels": {'$in': channel_ids}}})
    await _delete_channels_to_client(channel_ids)


async def _delete_channels_to_client(channel_ids):
    for id in channel_ids:
        await _CLIENT.delete_dialog(id)


async def _delete_listen_channels_to_common_collection(channel_ids, user_id, db_name=conf.APP_NAME):
    client = await _STORAGE.get_client()
    db = client[db_name]
    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]

    for id in channel_ids:
        await channels_coll.update_one({"id": id}, {"$pull": {"users": {'$in': [user_id]}}})

    empty_users_channel_ids = [obj['id'] async for obj in channels_coll.find({"users": {"$in": [None, []]}})]

    if empty_users_channel_ids:
        channels_coll.delete_many({"id": {'$in': empty_users_channel_ids}})
        return empty_users_channel_ids


async def _send_message_channels_subscribers(post_text, channel_ids):
    client = await _STORAGE.get_client()
    db = client[conf.APP_NAME]
    users_coll = db["aiogram_data"]

    for id in channel_ids:
        entity = await _CLIENT.get_entity(id)

        async for obj in users_coll.find({"data.listen_channels": {'$in': [id]}}):
            await _BOT.send_message(chat_id=obj["user"],
                                    text=emojize(
                                        f"К глубочайшему сожалению, канал https://t.me/{entity.username} "
                                        + post_text))


async def _notify_users_about_engineering_works(is_start):
    client = await _STORAGE.get_client()
    db = client[conf.APP_NAME]
    users_coll = db["aiogram_data"]

    async for obj in users_coll.find({}):
        text = emojize("Don't worry, проводятся технические работы:man_technologist:") if not is_start \
            else emojize("А все, технические работы закончились:fire:")
        await _BOT.send_message(chat_id=obj["user"],
                                text=text)


# LISTENER
async def _reload_listener():
    client = await _STORAGE.get_client()
    db = client[conf.APP_NAME]
    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]

    listen_channel_ids = [obj['id'] async for obj in channels_coll.find({})]

    if not listen_channel_ids:
        return

    if _CLIENT.list_event_handlers():
        _CLIENT.remove_event_handler(_on_new_channel_message, events.NewMessage())

    _CLIENT.add_event_handler(_on_new_channel_message, events.NewMessage(chats=listen_channel_ids))


async def _on_new_channel_message(event: events.NewMessage.Event):
    client = await _STORAGE.get_client()
    db = client[conf.APP_NAME]
    users_coll = db["aiogram_data"]

    listen_channel_id = abs(10 ** 12 + event.chat_id)
    listen_users = [obj
                    async for obj in users_coll.find({"$and": [{"data.listen_channels": {'$in': [listen_channel_id]}},
                                                               {"data.is_listen": True}]})]

    if listen_users:
        for user in listen_users:
            try:
                await _CLIENT.forward_messages(entity=conf.MAIN_TAPE_CHANNEL_NAME, messages=event.message)
                async for message in _CLIENT.iter_messages(conf.MAIN_TAPE_CHANNEL_NAME, limit=500):
                    if message.forward.chat_id == event.chat_id:
                        await _BOT.forward_message(chat_id=-(10 ** 12 + user['data']['tape_channel']),
                                                   from_chat_id=conf.MAIN_TAPE_CHANNEL_ID,
                                                   message_id=message.id)
                        break
            except AuthKeyError:
                post_text = emojize("включил защиту на пересылку сообщений, "
                                    "поэтому он будет удален из ваших подписок:warning:")
                await _send_message_channels_subscribers(post_text, [listen_channel_id])
                await _delete_everywhere_listen_channels([listen_channel_id])
                await _reload_listener()
                return
            except Exception as err:
                _LOGGER.error(err)


if __name__ == '__main__':
    run()
    _CLIENT.loop.run_until_complete(_notify_users_about_engineering_works(is_start=False))
    _CLIENT.disconnect()
