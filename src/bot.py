import logging

from Support import *
from Support import conf
from Support import store
from Support.messages import bot_messages_ru


class StartQuestionStates(StatesGroup):
    enter_tape_channel = State()
    enter_initial_listen_channels = State()


class UpdateStates(StatesGroup):
    enter_add_listen_channels = State()
    enter_delete_listen_channel = State()


class SupportStates(StatesGroup):
    switch_wish = State()
    enter_wish = State()


class AdminStates(StatesGroup):
    enter_post = State()


_BOT = Bot(token=conf.API_BOT_TOKEN)
_DP = Dispatcher(_BOT, storage=store.STORAGE)
_CLIENT = TelegramClient(conf.APP_NAME, api_id=conf.API_ID, api_hash=conf.API_HASH)
logging.basicConfig(level=logging.ERROR)
_LOGGER = logging.getLogger(conf.APP_NAME)


# ADMIN
@_DP.message_handler(commands=['admin_post'], state='*')
async def _on_post(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        if message.from_user.id == conf.ADMIN_ID:
            await message.answer("Внимаю создатель🤩")
            await message.answer("Какой пост хотите опубликовать для всех пользователей?")
            await AdminStates.enter_post.set()
        else:
            for text in bot_messages_ru['echo']:
                await message.answer(text)
    else:
        for text in bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(state=AdminStates.enter_post)
async def _enter_post(message: bot_types.Message, state: FSMContext):
    await message.answer("Опубликовал💌")

    await _send_message_all_users("❗❗❗ "
                                  "От создателя😎: "
                                  "❗❗❗\n\n" + message.text)
    await state.reset_state(with_data=False)


@_DP.message_handler(commands=['admin_statistics'], state='*')
async def _get_statistics(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        if message.from_user.id == conf.ADMIN_ID:
            all_users_len = len(await store.get_all_users())
            all_listen_users = len(await store.get_all_listen_users())
            all_listen_channels_len = len(await store.get_all_listen_channel_ids())

            await message.answer("Статистика📋:\n" + f'Всего пользователей🧘‍: ↔ {all_users_len}\n'
                                                     f'Всего лент запущено👂: ↔ {all_listen_users}\n'
                                                     f'Всего каналов 🌍: ↔ {all_listen_channels_len}\n')
        else:
            for text in bot_messages_ru['echo']:
                await message.answer(text)
    else:
        for text in bot_messages_ru['state_if_exist']:
            await message.answer(text)


# COMMANDS
@_DP.message_handler(commands=['help'])
async def _on_help(message: bot_types.Message):
    await message.answer(bot_messages_ru['help'])
    if message.from_user.id == conf.ADMIN_ID:
        await message.answer(bot_messages_ru['admin_help'])


@_DP.message_handler(commands=['start'], state='*')
async def _on_start(message: bot_types.Message, state: FSMContext):
    if not await state.get_data():
        for text in bot_messages_ru['start'][0]:
            await message.answer(text)
        await StartQuestionStates.enter_tape_channel.set()
    else:
        for text in bot_messages_ru['start'][1]:
            await message.answer(text)


@_DP.message_handler(state=StartQuestionStates.enter_tape_channel)
async def _enter_tape_channel(message: bot_types.Message, state: FSMContext):
    exist_channels, not_exist_channel_entities = await _check_channels_exist([message.text])

    if not_exist_channel_entities:
        for text in bot_messages_ru['enter_new_tape'][0]:
            await message.answer(text)
        return

    if not await _check_bot_is_channel_admin(list(exist_channels.keys())[0]):
        for text in bot_messages_ru['enter_new_tape'][1]:
            await message.answer(text)
        return

    async with state.proxy() as data:
        data['tape_channel'] = list(exist_channels.keys())[0]

    if (await state.get_data())['listen_channels'] is not None:
        for text in bot_messages_ru['enter_new_tape'][2]:
            await message.answer(text)
        await state.reset_state(with_data=False)
        return

    for text in bot_messages_ru['enter_new_tape'][3]:
        await message.answer(text)
    await StartQuestionStates.enter_initial_listen_channels.set()


@_DP.message_handler(state=StartQuestionStates.enter_initial_listen_channels)
async def _enter_initial_listen_channels(message: bot_types.Message, state: FSMContext):
    channels = list(set(message.text.split(',')))
    exist_channels, not_exist_channel_entities = await _check_channels_exist(channels)

    if not_exist_channel_entities:
        for text in bot_messages_ru['enter_init_listen'][0]:
            await message.answer(text + f"{','.join(not_exist_channel_entities)}\n")

        if exist_channels:
            for text in bot_messages_ru['enter_init_listen'][1]:
                await message.answer(text + f"{','.join(list(exist_channels.values()))}\n")

        for text in bot_messages_ru['enter_init_listen'][2]:
            await message.answer(text)
        return

    for text in bot_messages_ru['enter_init_listen'][3]:
        await message.answer(text)

    async with state.proxy() as data:
        data['listen_channels'] = list(exist_channels.keys())
        data['is_listen'] = False

    await _join_new_listen_channels_to_client(list(exist_channels.keys()))
    await store.save_new_listen_channels_to_common_collection(exist_channels, user_id=message.from_user.id)
    await _reload_listener()
    await state.reset_state(with_data=False)


@_DP.message_handler(commands=['on'], state='*')
async def _start_tape(message: bot_types.Message, state: FSMContext):
    data = await state.get_data()
    if data['is_listen']:
        for text in bot_messages_ru['start_tape'][0]:
            await message.answer(text)
    else:
        if data.get('tape_channel') is None:
            for text in bot_messages_ru['start_tape'][1]:
                await message.answer(text)
        elif not data['listen_channels']:
            for text in bot_messages_ru['start_tape'][2]:
                await message.answer(text)
        else:
            for text in bot_messages_ru['start_tape'][3]:
                await message.answer(text)

            async with state.proxy() as data:
                data['is_listen'] = True


@_DP.message_handler(commands=['off'], state='*')
async def _stop_tape(message: bot_types.Message, state: FSMContext):
    if (await state.get_data())['is_listen']:
        for text in bot_messages_ru['stop_tape'][0]:
            await message.answer(text)

        async with state.proxy() as data:
            data['is_listen'] = False
    else:
        for text in bot_messages_ru['stop_tape'][1]:
            await message.answer(text)


@_DP.message_handler(commands=['add'], state='*')
async def _add_listen_channel(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        for text in bot_messages_ru['add_listen']:
            await message.answer(text)
        await UpdateStates.enter_add_listen_channels.set()
    else:
        for text in bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(state=UpdateStates.enter_add_listen_channels)
async def _enter_add_listen_channels(message: bot_types.Message, state: FSMContext):
    if message.text == '/everything':
        for text in bot_messages_ru['everything']:
            await message.answer(text)
        await _reload_listener()
        await state.reset_state(with_data=False)
        return

    exist_channels, not_exist_channel_entities = await _check_channels_exist([message.text])

    if not_exist_channel_entities:
        for text in bot_messages_ru['enter_add_listen'][0]:
            await message.answer(text)
        return

    async with state.proxy() as data:
        new_channel_id = list(exist_channels.keys())[0]
        if new_channel_id not in set(data['listen_channels']):
            data['listen_channels'].append(new_channel_id)
        else:
            for text in bot_messages_ru['enter_add_listen'][1]:
                await message.answer(text)
            return

    for text in bot_messages_ru['enter_add_listen'][2]:
        await message.answer(text)
    await _join_new_listen_channels_to_client([new_channel_id])
    await store.save_new_listen_channels_to_common_collection(exist_channels, message.from_user.id)


@_DP.message_handler(commands=['delete'], state='*')
async def _delete_listen_channel(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        if (await state.get_data())['listen_channels']:
            for text in bot_messages_ru['delete_listen'][0]:
                await message.answer(text)
            await UpdateStates.enter_delete_listen_channel.set()
        else:
            for text in bot_messages_ru['delete_listen'][1]:
                await message.answer(text)
    else:
        for text in bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(state=UpdateStates.enter_delete_listen_channel)
async def _enter_delete_listen_channel(message: bot_types.Message, state: FSMContext):
    text = message.text

    if text == '/everything':
        for text in bot_messages_ru['everything']:
            await message.answer(text)
        await state.reset_state(with_data=False)
        return

    if text[0] == '/':
        text = '@' + text[1:]

    exist_channels, not_exist_channel_entities = await _check_channels_exist([text])

    if not_exist_channel_entities:
        for text in bot_messages_ru['enter_delete_listen'][0]:
            await message.answer(text)
        return

    del_channel_id = list(exist_channels.keys())[0]
    async with state.proxy() as data:
        if del_channel_id in set(data['listen_channels']):
            data['listen_channels'].remove(del_channel_id)

        else:
            for text in bot_messages_ru['enter_delete_listen'][1]:
                await message.answer(text)
            return

    for text in bot_messages_ru['enter_delete_listen'][2]:
        await message.answer(text)

    empty_users_channel_ids = await store.delete_listen_channels_to_common_collection([del_channel_id],
                                                                                      user_id=message.from_user.id)
    if empty_users_channel_ids:
        await _delete_channels_to_client(empty_users_channel_ids)


@_DP.message_handler(commands=['change_my_channel'], state='*')
async def _change_tape_channel(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        await store.drop_tape_channel_for_user(message.from_user.id)
        for text in bot_messages_ru['change_tape']:
            await message.answer(text)
        await StartQuestionStates.enter_tape_channel.set()
    else:
        for text in bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(commands=['subscriptions'], state='*')
async def _get_subscriptions_table(message: bot_types.Message, state: FSMContext):
    state_name = await state.get_state()
    delete_state_name = re.sub(r"[^A-Za-z_:]+", '', UpdateStates.enter_delete_listen_channel.__str__()).replace('State',
                                                                                                                '', 1)
    if not state_name or state_name == delete_state_name:
        listen_channel_ids = (await state.get_data())['listen_channels']

        if listen_channel_ids:
            exist_channels, not_exist_channel_ids = await _check_channels_exist(listen_channel_ids)
            await store.check_channel_nicknames_actuality_to_common_collection(exist_channels)

            if exist_channels:
                table_text_arr = list(bot_messages_ru['subscriptions'][0]) + list(
                    map(lambda nickname: f"-> {nickname.replace('@', '/')}"
                    if state_name == delete_state_name else f"-> {nickname}", list(exist_channels.values())))

                await message.answer('\n'.join(table_text_arr))
            else:
                await message.answer(bot_messages_ru['subscriptions'][1])

            if not_exist_channel_ids:
                await _send_message_channel_subscribers(bot_messages_ru['channel_not_exist'], not_exist_channel_ids)
                await store.delete_everywhere_listen_channels_to_store(not_exist_channel_ids)
                await _delete_channels_to_client(not_exist_channel_ids)
        else:
            for text in bot_messages_ru['subscriptions'][2]:
                await message.answer(text)
    else:
        for text in bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(commands=['wish'], state='*')
async def _on_wish(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        text = await store.get_user_wish(message.from_user.id)
        if text:
            await message.answer(
                bot_messages_ru['wish'][0][0] + bot_messages_ru['wish'][0][1] + text + bot_messages_ru['wish'][0][2])
            for text in bot_messages_ru['wish'][1]:
                await message.answer(text)
            await SupportStates.switch_wish.set()
        else:
            for text in bot_messages_ru['wish'][2]:
                await message.answer(text)
            await SupportStates.enter_wish.set()
    else:
        for text in bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(state=SupportStates.switch_wish)
async def _switch_wish(message: bot_types.Message, state: FSMContext):
    if message.text == 'Да':
        for text in bot_messages_ru['switch_wish'][0]:
            await message.answer(text)
        await SupportStates.enter_wish.set()
    elif message.text == 'Нет':
        for text in bot_messages_ru['switch_wish'][1]:
            await message.answer(text)
        await state.reset_state(with_data=False)
    else:
        for text in bot_messages_ru['switch_wish'][2]:
            await message.answer(text)
        await state.reset_state(with_data=False)


@_DP.message_handler(state=SupportStates.enter_wish)
async def _enter_wish(message: bot_types.Message, state: FSMContext):
    for text in bot_messages_ru['enter_wish']:
        await message.answer(text)
    await store.add_user_wish(message.from_user.id, message.text)
    await state.reset_state(with_data=False)


@_DP.message_handler()
async def _echo(message: bot_types.Message):
    for text in bot_messages_ru['echo']:
        await message.answer(text)


# CHECK
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


# CLIENT
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


async def _delete_channels_to_client(channel_ids):
    channel_dialog_ids = {dialog.entity.id async for dialog in _CLIENT.iter_dialogs(archived=True) if dialog.is_channel}
    for id in channel_ids:
        if id in channel_dialog_ids:
            await _CLIENT.delete_dialog(id)


# NOTIFICATION
async def _send_message_channel_subscribers(post_text, channel_ids):
    client = await store.STORAGE.get_client()
    db = client[conf.APP_NAME]
    users_coll = db["aiogram_data"]
    channels_coll = db[conf.LISTEN_CHANNELS_COLL_NAME]

    async for channel_obj in channels_coll.find({"id": {"$in": channel_ids}}):
        async for obj in users_coll.find({"data.listen_channels": {'$in': [channel_obj['id']]}}):
            await _BOT.send_message(chat_id=obj["user"],
                                    text=
                                    f"К глубочайшему сожалению, канал {channel_obj['nickname']} "
                                    + post_text)


async def _notify_users_about_engineering_works(is_start):
    client = await store.STORAGE.get_client()
    db = client[conf.APP_NAME]
    users_coll = db["aiogram_data"]

    async for obj in users_coll.find({}):
        text = bot_messages_ru['engineering_works'][0] if not is_start \
            else bot_messages_ru['engineering_works'][1]
        await _BOT.send_message(chat_id=obj["user"],
                                text=text)


async def _send_message_all_users(post_text):
    client = await store.STORAGE.get_client()
    db = client[conf.APP_NAME]
    users_coll = db["aiogram_data"]

    async for obj in users_coll.find({}):
        try:
            await _BOT.send_message(chat_id=obj["user"],
                                    text=post_text)
        except Unauthorized:
            pass
        except Exception as err:
            _LOGGER.error(err)


# LISTENER
async def _reload_listener():
    listen_channel_ids = await store.get_all_listen_channel_ids()

    if not listen_channel_ids:
        return

    if _CLIENT.list_event_handlers():
        _CLIENT.remove_event_handler(_on_new_channel_message, events.NewMessage())

    _CLIENT.add_event_handler(_on_new_channel_message, events.NewMessage(chats=listen_channel_ids))


async def _on_new_channel_message(event: events.NewMessage.Event):
    listen_channel_id = abs(10 ** 12 + event.chat_id)

    client = await store.STORAGE.get_client()
    db = client[conf.APP_NAME]
    users_coll = db["aiogram_data"]

    async for obj in users_coll.find({"$and": [{"data.listen_channels": {'$in': [listen_channel_id]}},
                                               {"data.is_listen": True}]}):
        try:
            await _CLIENT.forward_messages(entity=conf.MAIN_TAPE_CHANNEL_NAME, messages=event.message)
            async for message in _CLIENT.iter_messages(conf.MAIN_TAPE_CHANNEL_NAME, limit=500):
                if message.forward.chat_id == event.chat_id:
                    await _BOT.forward_message(chat_id=-(10 ** 12 + obj['data']['tape_channel']),
                                               from_chat_id=conf.MAIN_TAPE_CHANNEL_ID,
                                               message_id=message.id)
                    break
        except AuthKeyError:
            try:
                await _send_message_channel_subscribers(bot_messages_ru['channel_on_protection'], [listen_channel_id])
                await store.delete_everywhere_listen_channels_to_store([listen_channel_id])
                await _delete_channels_to_client([listen_channel_id])
                await _reload_listener()
            except Unauthorized:
                await store.stop_listen_for_user(obj['user'])
            except Exception as err:
                _LOGGER.error(err)
        except Unauthorized:
            try:
                for text in bot_messages_ru['tape_not_exist']:
                    await _BOT.send_message(chat_id=obj['user'],
                                            text=text)
                await store.drop_tape_channel_for_user(obj['user'])
            except Unauthorized:
                await store.stop_listen_for_user(obj['user'])
            except Exception as err:
                _LOGGER.error(err)
        except Exception as err:
            _LOGGER.error(err)


def run():
    _CLIENT.start(phone=conf.PHONE)
    _CLIENT.loop.run_until_complete(_notify_users_about_engineering_works(is_start=True))
    _CLIENT.loop.run_until_complete(_reload_listener())
    executor.start_polling(_DP, skip_updates=True, loop=_CLIENT.loop)


if __name__ == '__main__':
    run()
    _CLIENT.loop.run_until_complete(_notify_users_about_engineering_works(is_start=False))
    _CLIENT.disconnect()
