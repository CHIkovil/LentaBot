import logging

from Support import *
import conf


class StartQuestion(StatesGroup):
    enter_personal_channel = State()
    enter_initial_listen_channels = State()


_BOT = Bot(token=conf.API_BOT_TOKEN)
_STORAGE = MongoStorage(db_name=conf.APP_NAME)
_DP = Dispatcher(_BOT, storage=_STORAGE)
_CLIENT = TelegramClient(conf.APP_NAME, api_id=conf.API_ID, api_hash=conf.API_HASH)
_LOGGER = logging.getLogger(conf.APP_NAME)


def run():
    _CLIENT.start(phone=conf.PHONE)
    _CLIENT.loop.run_until_complete(_reload_listener())
    executor.start_polling(_DP, skip_updates=True)


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
        await StartQuestion.enter_personal_channel.set()
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


@_DP.message_handler()
async def _echo(message: bot_types.Message):
    await message.answer(emojize("Тах тах не флуди...:oncoming_fist:"))
    await message.answer("Воспользуйся /help")


# STATE
@_DP.message_handler(state=StartQuestion.enter_personal_channel)
async def _enter_personal_channel(message: bot_types.Message, state: FSMContext):
    exist_channels, not_exist_channel_urls = await _check_channels_exist([message.text])

    if not_exist_channel_urls:
        await message.answer(emojize("Хмм..."))
        await message.answer(emojize("Что-то не похоже на канал:thinking_face:"))
        return

    if not await _check_bot_is_channel_admin(list(exist_channels.keys())[0]):
        await message.answer(emojize("Не понял, почему я все еще не администратор:red_question_mark:"))
        await message.answer(emojize("Жду cсылку на канал, где я администратор..."))
        await message.answer(emojize("Учти, я проверю:smiling_face_with_horns:"))
        return

    async with state.proxy() as data:
        data['tape_channel'] = list(exist_channels.keys())[0]

    await message.answer(emojize("Далее перечисли ПУБЛИЧНЫЕ каналы из которых мы сформируем твою ЛИЧНУЮ ленту!"))
    await message.answer(emojize("Через запятую конечно же."))
    await message.answer(emojize("Учти, что некоторые каналы могут запрещать пересылку сообщений."))
    await message.answer(emojize("С такими мы не дружим:warning:"))
    await StartQuestion.enter_initial_listen_channels.set()


@_DP.message_handler(state=StartQuestion.enter_initial_listen_channels)
async def _enter_initial_listen_channels(message: bot_types.Message, state: FSMContext):
    channels = list(set(message.text.split(',')))
    exist_channels, not_exist_channel_urls = await _check_channels_exist(channels)

    if not_exist_channel_urls:
        await message.answer("Что-то, но не каналы:\n"
                             f"{','.join(not_exist_channel_urls)}\n")
        if exist_channels:
            await message.answer("Существующие каналы:\n"
                                 f"{','.join(list(exist_channels.values()))}\n")

        await message.answer("Внеси исправления и снова скинь мне!")
        await message.answer(emojize("Не забудь про запятую:smiling_face_with_horns:"))
        await message.answer(emojize("А может это вообще не каналы..."))
        return

    async with state.proxy() as data:
        data['listen_channels'] = list(exist_channels.keys())
        data['is_listen'] = False

    await _join_new_listen_channels_to_client(channels=exist_channels)
    await _save_new_listen_channels(channels=exist_channels, user_id=message.from_user.id)
    await message.answer(emojize("Все запомнил:OK_hand:"))
    await message.answer("Воспользуйся /help")
    await state.reset_state(with_data=False)
    await _reload_listener()


# SUPPORT
async def _check_channels_exist(channel_urls):
    exist_channels = {}
    not_exist_channel_urls = []
    for url in channel_urls:
        try:
            entity = await _CLIENT.get_entity(url)
            if isinstance(entity, client_types.Channel):
                exist_channels[entity.id] = url
            else:
                raise ValueError
        except ValueError:
            not_exist_channel_urls.append(url)
        except Exception as err:
            _LOGGER.error(err)
    return exist_channels, not_exist_channel_urls


async def _join_new_listen_channels_to_client(channels):
    channel_dialogs = [dialog.entity.id async for dialog in _CLIENT.iter_dialogs(archived=True) if dialog.is_channel]

    for id, _ in channels.items():
        if id not in channel_dialogs:
            await _CLIENT(JoinChannelRequest(channel=id))
            await _CLIENT(UpdateNotifySettingsRequest(peer=id,
                                                      settings=client_types.InputPeerNotifySettings(
                                                          mute_until=2 ** 31 - 1
                                                      )))
            await _CLIENT.edit_folder(id, folder=1)


async def _save_new_listen_channels(channels, user_id, db_name=conf.APP_NAME):
    client = await _STORAGE.get_client()
    db = client[db_name]
    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]

    if conf.LISTEN_CHANNELS_COLL_NAME in list(await db.list_collection_names()):
        for id, _ in channels.items():
            channel_obj = [obj async for obj in channels_coll.find({"id": id})]
            if channel_obj:
                await channels_coll.update_one({'id': id},
                                               {'$push': {'users': user_id}})
            else:
                await channels_coll.insert_one(
                    {'id': id, 'users': [user_id]})
    else:
        data = [{'id': id, 'users': [user_id]} for id, _ in channels.items()]
        await channels_coll.insert_many(data)


async def _check_bot_is_channel_admin(channel_id):
    try:
        member = await _BOT.get_chat_member(-(10 ** 12 + channel_id), conf.API_BOT_TOKEN.split(":")[0])
        if member['status'] == 'administrator':
            return True
        else:
            raise ChatNotFound
    except ChatNotFound:
        return False
    except Exception as err:
        _LOGGER.error(err)


async def _delete_everywhere_listen_channels(channel_ids):
    client = await _STORAGE.get_client()
    db = client[conf.APP_NAME]
    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]
    users_coll = db["aiogram_data"]

    await channels_coll.delete_one({"id": {'$in': channel_ids}})
    await _reload_listener()
    await users_coll.update_many({}, {"$pull": {"data.listen_channels": {'$in': channel_ids}}})


# LISTENER
async def _reload_listener():
    client = await _STORAGE.get_client()
    db = client[conf.APP_NAME]
    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]

    listen_channels = [obj['id'] async for obj in channels_coll.find({})]

    if not listen_channels:
        return

    if _CLIENT.list_event_handlers():
        _CLIENT.remove_event_handler(_on_new_channel_message, events.NewMessage())

    _CLIENT.add_event_handler(_on_new_channel_message, events.NewMessage(chats=listen_channels))


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
                entity = await _CLIENT.get_entity(listen_channel_id)
                async for obj in users_coll.find({"$and": [{"data.listen_channels": {'$in': [listen_channel_id]}},
                                                           {"data.is_listen": True}]}):
                    await _BOT.send_message(chat_id=obj["user"],
                                            text=emojize(
                                                f"К глубочайшему сожалению, на канале https://t.me/{entity.username}"
                                                f" включена защита на пересылку сообщений,"
                                                f" поэтому он будет удален из ваших подписок:warning:"))

                # await _delete_everywhere_listen_channels([listen_channel_id])
                return
            except Exception as err:
                _LOGGER.error(err)


if __name__ == '__main__':
    run()
    _CLIENT.disconnect()
