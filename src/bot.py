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
logging.basicConfig(level=logging.ERROR)
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
        await message.answer(emojize(f"Не забудь перезапустить ленту!"))
        await message.answer("Воспользуйся /help")


@_DP.message_handler(commands=['add'], state='*')
async def _add_listen_channel(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        await message.answer(emojize("Слушаю:ear:"))
        await message.answer(emojize("Накидывай каналы, которые хочешь добавить."))
        await message.answer(emojize("Как закончишь скажи просто \n /everything"))
        await UpdateStates.enter_add_listen_channels.set()
    else:
        await message.answer(emojize("Все и сразу не получится:seedling:"))
        await message.answer(emojize("Сначала закончи предыдущие действия!"))


@_DP.message_handler(commands=['delete'], state='*')
async def _delete_listen_channel(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        if (await state.get_data())['listen_channels']:
            await message.answer(emojize("Внимаю:clapping_hands:"))
            await message.answer(emojize("Накидывай каналы, которые хочешь удалить."))
            await message.answer(emojize("Как закончишь скажи просто \n /everything"))
            await UpdateStates.enter_delete_listen_channel.set()
        else:
            await message.answer(emojize("Что мы решили удалить из подписок, если даже нет ни одной...."))
            await message.answer(emojize("Сначала добавь хоть одну /add"))
    else:
        await message.answer(emojize("Все и сразу не получится:seedling:"))
        await message.answer(emojize("Сначала закончи предыдущие действия!"))


@_DP.message_handler(commands=['change_my_channel'], state='*')
async def _recreate_tape_channel(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        await _drop_tape_channel_for_user(message.from_user.id)
        await message.answer(emojize(f"Ну что, пора переезжать на новый канал для ленты:clinking_beer_mugs:"))
        await message.answer(
            emojize(f"Напомню, для ленты нужно создать свой ПУБЛИЧНЫЙ канал и добавить меня как администратора!"))
        await StartQuestionStates.enter_personal_channel.set()
    else:
        await message.answer(emojize("Все и сразу не получится:seedling:"))
        await message.answer(emojize("Сначала закончи предыдущие действия!"))


@_DP.message_handler(commands=['help'])
async def _on_help(message: bot_types.Message):
    await message.answer(emojize("Помощь, которую мы заслуживаем:backhand_index_pointing_down:\n\n"
                                 f":rocket::stop_sign: /on, /off - вкл/выкл ленту, состоящую из публикаций каналов на которые ты подписал/ся-ась через меня.\n"
                                 ":thought_balloon:(Приходит на твой личный канал, который мы добавили в самом начале нашего пути.)\n\n"
                                 ":check_mark_button: /add - добавляет новые каналы в подписки.\n"
                                 ":thought_balloon:(Можно быстро накидать ссылки каналов, с помощью пересылки в телеграм, не общаясь со мной лицом к лицу.\n"
                                 "Главное в конце не забудь отправить мне команду /everything.)\n\n"
                                 ":check_mark_button: /delete - удаляет каналы из подписок.\n"
                                 ":thought_balloon:(После начала процесса удаления будет автоматически появляться команды на удаление твоих подписок.\n"
                                 "Главное в конце не забудь отправить мне команду /everything.)\n\n"
                                 ":check_mark_button: /change_my_channel - заменяет канал на который будут приходить публикации от подписок.\n\n"
                                 ":clipboard: /subscriptions - показывает список подписок."
                                 ))


@_DP.message_handler(commands=['subscriptions'], state='*')
async def _get_subscriptions_table(message: bot_types.Message, state: FSMContext):
    state_name = await state.get_state()
    delete_state_name = re.sub(r"[^A-Za-z_:]+", '', UpdateStates.enter_delete_listen_channel.__str__()).replace('State',
                                                                                                                '', 1)
    if not state_name or state_name == delete_state_name:
        listen_channel_ids = (await state.get_data())['listen_channels']

        if listen_channel_ids:
            exist_channels, not_exist_channel_ids = await _check_channels_exist(listen_channel_ids)
            await _check_channels_nickname_actuality_to_store(exist_channels)
            if not_exist_channel_ids:
                post_text = emojize("больше не существует, "
                                    "поэтому он будет удален из ваших подписок:warning:")
                await _send_message_channel_subscribers(post_text, not_exist_channel_ids)
                await _delete_everywhere_listen_channels_to_store(not_exist_channel_ids)
                await _delete_channels_to_client(not_exist_channel_ids)
                await _reload_listener()

            if exist_channels:
                table_text_arr = [emojize("Твои подписки:clipboard:")] + list(map(lambda nickname: f"-> {nickname.replace('@', '/')}"
                                    if state_name == delete_state_name else f"-> {nickname}",list(exist_channels.values())))

                await message.answer('\n'.join(table_text_arr))

        else:
            await message.answer(emojize("Cначала добавь хотя бы одну подписку:smiling_face_with_open_hands:"))
            await message.answer(emojize("Воспользуйся /add"))
    else:
        await message.answer(emojize("Все и сразу не получится:seedling:"))
        await message.answer(emojize("Сначала закончи предыдущие действия!"))


@_DP.message_handler(commands=['on'], state='*')
async def _start_tape(message: bot_types.Message, state: FSMContext):
    data = await state.get_data()
    if data['is_listen']:
        await message.answer(emojize("Как бы лента уже запущена:grinning_face_with_sweat:"))
    else:
        if data.get('tape_channel') is None:
            await message.answer(emojize("Тах тах, добавь сначала канал, "
                                         "куда я буду скидывать публикации "
                                         "твоих подписок /change_my_channel!"))
        elif not data['listen_channels']:
            await message.answer(emojize("Все хорошо, только добавь сначала хотя бы один канал в подписки..."))
            await message.answer(emojize("Воспользуйся /add"))
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
        if data.get('listen_channels') is not None:
            await message.answer(emojize("Запомнил:check_mark_button:"))
            await message.answer(emojize(f"Не забудь перезапустить ленту:smiling_face_with_smiling_eyes:"))
            await state.reset_state(with_data=False)
            return

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
        await _save_new_listen_channels_to_common_collection(exist_channels, user_id=message.from_user.id)
        await _reload_listener()
        await message.answer(emojize("Все запомнил:OK_hand:"))
        await message.answer("Воспользуйся /help")
        await state.reset_state(with_data=False)


@_DP.message_handler(state=UpdateStates.enter_add_listen_channels)
async def _enter_add_listen_channels(message: bot_types.Message, state: FSMContext):
    if message.text == '/everything':
        await message.answer(emojize("Принял:handshake:"))
        await message.answer(emojize("Воспользуйся /help"))
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
        if new_channel_id not in set(data['listen_channels']):
            data['listen_channels'].append(new_channel_id)
            await _join_new_listen_channels_to_client([new_channel_id])
            await _save_new_listen_channels_to_common_collection(exist_channels, message.from_user.id)
            await message.answer(emojize("Добавил:check_mark_button:"))
        else:
            await message.answer(emojize("Канал уже есть в твоих подписках..."))
            await message.answer(emojize("Давай другой:beaming_face_with_smiling_eyes:"))


@_DP.message_handler(state=UpdateStates.enter_delete_listen_channel)
async def _enter_delete_listen_channel(message: bot_types.Message, state: FSMContext):
    text = message.text

    if text == '/everything':
        await message.answer(emojize("Принял:handshake:"))
        await message.answer(emojize("Воспользуйся /help"))
        await _reload_listener()
        await state.reset_state(with_data=False)
        return

    if text[0] == '/':
        text = '@' + text[1:]

    exist_channels, not_exist_channel_entities = await _check_channels_exist([text])

    if not_exist_channel_entities:
        await message.answer(emojize("Что-то не похоже на канал:thinking_face:"))
        await message.answer(emojize("Исправь и снова скинь мне..."))
        return

    del_channel_id = list(exist_channels.keys())[0]
    async with state.proxy() as data:
        if del_channel_id in set(data['listen_channels']):
            data['listen_channels'].remove(del_channel_id)
            empty_users_channel_ids = await _delete_listen_channels_to_common_collection([del_channel_id],
                                                                                         user_id=message.from_user.id)
            if empty_users_channel_ids:
                await _delete_channels_to_client(empty_users_channel_ids)

            await message.answer(emojize("Удалил:check_mark_button:"))
        else:
            await message.answer(emojize("Такого канала нет в твоих подписках:thinking_face:"))


# SUPPORT
async def _check_channels_exist(channel_entities):
    exist_channels = {}
    not_exist_channel_entities = []
    for entity in channel_entities:
        try:
            obj = await _CLIENT.get_entity(entity)
            if isinstance(obj, client_types.Channel):
                exist_channels[obj.id] = f"@{obj.username}"
            else:
                not_exist_channel_entities.append(entity)
        except ValueError:
            not_exist_channel_entities.append(entity)
        except Exception as err:
            not_exist_channel_entities.append(entity)
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


async def _delete_channels_to_client(channel_ids):
    channel_dialog_ids = {dialog.entity.id async for dialog in _CLIENT.iter_dialogs(archived=True) if dialog.is_channel}
    for id in channel_ids:
        if id in channel_dialog_ids:
            await _CLIENT.delete_dialog(id)


async def _send_message_channel_subscribers(post_text, channel_ids):
    client = await _STORAGE.get_client()
    db = client[conf.APP_NAME]
    users_coll = db["aiogram_data"]
    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]

    async for channel_obj in channels_coll.find({"id": {"$in": channel_ids}}):
        async for obj in users_coll.find({"data.listen_channels": {'$in': [channel_obj['id']]}}):
            await _BOT.send_message(chat_id=obj["user"],
                                    text=emojize(
                                        f"К глубочайшему сожалению, канал {channel_obj['nickname']} "
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


# DBStore
async def _check_channels_nickname_actuality_to_store(exist_channels):
    client = await _STORAGE.get_client()
    db = client[conf.APP_NAME]
    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]

    exist_listen_channel = {obj['nickname']: obj['id'] async for obj in
                            channels_coll.find({"id": {"$in": list(exist_channels.keys())}})}

    not_equal_old_nicknames = list(set(exist_listen_channel.keys()) - set(exist_channels.values()))

    if not_equal_old_nicknames:
        for old_nickname in not_equal_old_nicknames:
            await channels_coll.update_one({'id': exist_listen_channel[old_nickname]},
                                           {"$set": {'nickname': exist_channels[exist_listen_channel[old_nickname]]}})


async def _save_new_listen_channels_to_common_collection(channels, user_id, db_name=conf.APP_NAME):
    client = await _STORAGE.get_client()
    db = client[db_name]
    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]

    if conf.LISTEN_CHANNELS_COLL_NAME in set(await db.list_collection_names()):
        for id, nickname in channels.items():
            channel_obj = [obj async for obj in channels_coll.find({"id": id})]
            if channel_obj:
                await channels_coll.update_one({'id': id},
                                               {'$push': {'users': user_id}})
            else:
                await channels_coll.insert_one(
                    {'id': id, 'nickname': nickname, 'users': [user_id]})
    else:
        data = [{'id': id, 'nickname': nickname, 'users': [user_id]} for id, nickname in channels.items()]
        await channels_coll.insert_many(data)


async def _delete_everywhere_listen_channels_to_store(channel_ids):
    client = await _STORAGE.get_client()
    db = client[conf.APP_NAME]
    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]
    users_coll = db["aiogram_data"]

    await channels_coll.delete_many({"id": {'$in': channel_ids}})
    await users_coll.update_many({}, {"$pull": {"data.listen_channels": {'$in': channel_ids}}})


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


async def _stop_listen_for_user(user_id):
    client = await _STORAGE.get_client()
    db = client[conf.APP_NAME]
    users_coll = db["aiogram_data"]

    await users_coll.update_one({"user": user_id}, {"$set": {"data.is_listen": False}})


async def _drop_tape_channel_for_user(user_id):
    client = await _STORAGE.get_client()
    db = client[conf.APP_NAME]
    users_coll = db["aiogram_data"]

    await _stop_listen_for_user(user_id=user_id)
    await users_coll.update_one({"user": user_id}, {"$set": {"data.tape_channel": None}})


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
                try:
                    post_text = emojize("включил защиту на пересылку сообщений, "
                                        "поэтому он будет удален из ваших подписок:warning:")
                    await _send_message_channel_subscribers(post_text, [listen_channel_id])
                    await _delete_everywhere_listen_channels_to_store([listen_channel_id])
                    await _delete_channels_to_client([listen_channel_id])
                    await _reload_listener()
                except Unauthorized:
                    await _stop_listen_for_user(user['user'])
                except Exception as err:
                    await _stop_listen_for_user(user['user'])
                    _LOGGER.error(err)
            except (Unauthorized, ChatNotFound):
                try:
                    await _BOT.send_message(chat_id=user['user'],
                                            text=emojize(
                                                f"А что с каналом, "
                                                f"в который я скидываю публикации твоих подписок?:anguished_face:"))
                    await _BOT.send_message(chat_id=user['user'],
                                            text=emojize(
                                                f"Попробуй изменить свой канал /change_my_channel :smirking_face:"))
                    await _drop_tape_channel_for_user(user['user'])
                except Unauthorized:
                    await _stop_listen_for_user(user['user'])
                except Exception as err:
                    await _stop_listen_for_user(user['user'])
                    _LOGGER.error(err)
            except Exception as err:
                await _stop_listen_for_user(user['user'])
                _LOGGER.error(err)


if __name__ == '__main__':
    run()
    _CLIENT.loop.run_until_complete(_notify_users_about_engineering_works(is_start=False))
    _CLIENT.disconnect()
