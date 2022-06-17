import logging

from Support import *
from Support import store
from Support.messages import bot_messages_ru
from Support.conf import *

_BOT = Bot(token=API_BOT_TOKEN)
_DP = Dispatcher(_BOT, storage=store.STORAGE)
_CLIENT = TelegramClient(APP_NAME, api_id=API_ID, api_hash=API_HASH)
logging.basicConfig(level=logging.ERROR)
_LOGGER = logging.getLogger(APP_NAME)


class StartQuestionStates(StatesGroup):
    enter_initial_listen_channels = State()


class UpdateStates(StatesGroup):
    enter_add_listen_channels = State()
    enter_delete_listen_channel = State()


class SupportStates(StatesGroup):
    switch_wish = State()
    enter_wish = State()


class AdminStates(StatesGroup):
    enter_post = State()


DELETE_STATE_NAME = re.sub(r"[^A-Za-z_:]+", '', UpdateStates.enter_delete_listen_channel.__str__()).replace('State',

                                                                                                            '', 1)
ADD_STATE_NAME = re.sub(r"[^A-Za-z_:]+", '', UpdateStates.enter_add_listen_channels.__str__()).replace('State',

                                                                                                       '', 1)

ADMIN_COMMANDS = {'/post': 'post',
                  '/statistics': 'statistics'
                  }

MAIN_COMMANDS = {'/start': 'start',
                 '/menu': 'menu',
                 '/help': 'help',
                 }

MENU_COMMANDS = {'/on': 'on',
                 '/off': 'off',
                 '/subscriptions': 'subscriptions',
                 '/add': 'add',
                 '/delete': 'delete',
                 '/wish': 'wish'
                 }
ALL_COMMANDS = set(list(ADMIN_COMMANDS.keys()) + list(MAIN_COMMANDS.keys()) + list(MENU_COMMANDS.keys()))

SUPPORT_KEYBOARD = bot_types.ReplyKeyboardMarkup(resize_keyboard=True).add(*['/menu', '/help'])
END_KEYBOARD = bot_types.ReplyKeyboardMarkup(resize_keyboard=True).add(*['/end'])


# ADMIN
@_DP.message_handler(commands=[ADMIN_COMMANDS['/post']], state='*')
async def _on_post(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        if message.from_user.id == ADMIN_ID:
            await message.answer("Внимаю создатель🤩")
            await message.answer("Какой пост хотите опубликовать для всех пользователей?",
                                 reply_markup=SUPPORT_KEYBOARD)
            await AdminStates.enter_post.set()
        else:
            for text in bot_messages_ru['echo']:
                await message.answer(text)
    else:
        for text in bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(state=AdminStates.enter_post)
async def _enter_post(message: bot_types.Message, state: FSMContext):
    if message.text not in ALL_COMMANDS:
        await message.answer("Опубликовал💌")
        await _send_and_pin_message_all_users(message.text)
        await state.reset_state(with_data=False)
    else:
        await message.answer("Пока рано для команд создатель!")
        await message.answer("Давай сначала сделаем публикацию😎")


@_DP.message_handler(commands=[ADMIN_COMMANDS['/statistics']], state='*')
async def _get_statistics(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        if message.from_user.id == ADMIN_ID:
            all_users_len = len(await store.get_all_users())
            all_listen_users = len(await store.get_all_listen_users())
            all_listen_channels_len = len(await store.get_all_listen_channel_ids())

            await message.answer("Общая статистика📋:\n\n" + f'♦️ Пользователей 🙆‍‍‍ - {all_users_len}\n'
                                                             f'♦️ Лент запущено👂 - {all_listen_users}\n'
                                                             f'♦️ Каналов 🌍 -  {all_listen_channels_len}\n',
                                 reply_markup=SUPPORT_KEYBOARD)
        else:
            for text in bot_messages_ru['echo']:
                await message.answer(text)
    else:
        for text in bot_messages_ru['state_if_exist']:
            await message.answer(text)


# COMMANDS
@_DP.message_handler(commands=[MAIN_COMMANDS['/menu']], state='*')
async def _on_menu(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        menu_keyboard = bot_types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = list(MENU_COMMANDS.keys())
        if message.from_user.id == ADMIN_ID:
            buttons += list(ADMIN_COMMANDS.keys())
        menu_keyboard.add(*buttons)
        await message.answer(bot_messages_ru['menu'], reply_markup=menu_keyboard)
    else:
        for text in bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(commands=[MAIN_COMMANDS['/start']], state='*')
async def _on_start(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        if not await state.get_data():
            for text in bot_messages_ru['start'][0]:
                await message.answer(text)
            await StartQuestionStates.enter_initial_listen_channels.set()
        else:
            for text in bot_messages_ru['start'][1]:
                await message.answer(text)
    else:
        for text in bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(state=StartQuestionStates.enter_initial_listen_channels)
async def _enter_initial_listen_channels(message: bot_types.Message, state: FSMContext):
    channels = list(set(message.text.split(',')))
    exist_channels, not_exist_channel_entities = await _check_channel_urls_exist(channels)

    if not exist_channels and not not_exist_channel_entities:
        for text in bot_messages_ru['state_if_exist']:
            await message.answer(text)
        return

    if not_exist_channel_entities:
        for text in bot_messages_ru['enter_init_listen'][0]:
            await message.answer(text + f"{','.join(not_exist_channel_entities)}\n")

        if exist_channels:
            for text in bot_messages_ru['enter_init_listen'][1]:
                await message.answer(text + f"{','.join(list(exist_channels.values()))}\n")

        for text in bot_messages_ru['enter_init_listen'][2]:
            await message.answer(text)
        return

    await message.answer(bot_messages_ru['enter_init_listen'][3][0], reply_markup=SUPPORT_KEYBOARD)
    for text in bot_messages_ru['enter_init_listen'][3][1:]:
        await message.answer(text)

    async with state.proxy() as data:
        data['listen_channels'] = list(exist_channels.keys())
        data['is_listen'] = True

    await _join_new_listen_channels_to_client(list(exist_channels.keys()))
    await store.save_new_listen_channels_to_common_collection(exist_channels, user_id=message.from_user.id)
    await _reload_listener()
    await state.reset_state(with_data=False)


@_DP.message_handler(commands=[MENU_COMMANDS['/on']], state='*')
async def _start_tape(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        data = await state.get_data()
        if data['is_listen']:
            await message.answer(bot_messages_ru['start_tape'][0][0], reply_markup=SUPPORT_KEYBOARD)
        else:
            if not data['listen_channels']:
                await message.answer(bot_messages_ru['start_tape'][1][0], reply_markup=SUPPORT_KEYBOARD)
                for text in bot_messages_ru['start_tape'][1][1:]:
                    await message.answer(text, reply_markup=SUPPORT_KEYBOARD)
            else:
                await message.answer(bot_messages_ru['start_tape'][2][0], reply_markup=SUPPORT_KEYBOARD)
                async with state.proxy() as data:
                    data['is_listen'] = True
    else:
        for text in bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(commands=[MENU_COMMANDS['/off']], state='*')
async def _stop_tape(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        if (await state.get_data())['is_listen']:
            await message.answer(bot_messages_ru['stop_tape'][0][0], reply_markup=SUPPORT_KEYBOARD)
            async with state.proxy() as data:
                data['is_listen'] = False
        else:
            await message.answer(bot_messages_ru['stop_tape'][1][0], reply_markup=SUPPORT_KEYBOARD)
    else:
        for text in bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(commands=[MAIN_COMMANDS['/help']], state='*')
async def _on_help(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        await message.answer(bot_messages_ru['help'])
    else:
        for text in bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(commands=[MENU_COMMANDS['/subscriptions']], state='*')
async def _get_subscriptions_table(message: bot_types.Message, state: FSMContext):
    state_name = await state.get_state()

    if not state_name or state_name == DELETE_STATE_NAME or state_name == ADD_STATE_NAME:
        listen_channel_ids = (await state.get_data())['listen_channels']
        exist_channel, not_exist_channel_ids = await _get_exist_channel_with_titles_to_client(listen_channel_ids)

        if exist_channel:
            table_text = f"{bot_messages_ru['subscriptions'][0][0]}\n"

            for username, title in list(exist_channel.values()):
                if state_name == DELETE_STATE_NAME:
                    table_text += f"🔸 /{username} - {title}\n"
                else:
                    table_text += f"🔸 @{username} - {title}\n"
            if state_name == DELETE_STATE_NAME or state_name == ADD_STATE_NAME:
                await message.answer(table_text)
            else:
                await message.answer(table_text, reply_markup=SUPPORT_KEYBOARD)

            if not_exist_channel_ids:
                await _send_message_channel_subscribers(bot_messages_ru['channel_not_exist'], not_exist_channel_ids)
                await store.delete_everywhere_listen_channels_to_store(not_exist_channel_ids)
        else:
            await message.answer(bot_messages_ru['subscriptions'][1])
    else:
        for text in bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(commands=[MENU_COMMANDS['/add']], state='*')
async def _add_listen_channel(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        await message.answer(bot_messages_ru['add_listen'][0], reply_markup=END_KEYBOARD)
        for text in bot_messages_ru['add_listen'][1:]:
            await message.answer(text)
        await UpdateStates.enter_add_listen_channels.set()
    else:
        for text in bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(state=UpdateStates.enter_add_listen_channels)
async def _enter_add_listen_channels(message: bot_types.Message, state: FSMContext):
    if message.text == '/end':
        await message.answer(bot_messages_ru['end'][0], reply_markup=SUPPORT_KEYBOARD)
        for text in bot_messages_ru['end'][1:]:
            await message.answer(text)
        await _reload_listener()
        await state.reset_state(with_data=False)
        return

    exist_channels, not_exist_channel_entities = await _check_channel_urls_exist([message.text])

    if not exist_channels and not not_exist_channel_entities:
        for text in bot_messages_ru['state_if_exist']:
            await message.answer(text)
        return

    if not_exist_channel_entities:
        for text in bot_messages_ru['enter_add_listen'][0]:
            await message.answer(text)
        return

    async with state.proxy() as data:
        new_channel_id = list(exist_channels.keys())[0]
        if new_channel_id not in set(data['listen_channels']):
            for text in bot_messages_ru['enter_add_listen'][2]:
                await message.answer(text)

            if not data['listen_channels']:
                data['is_listen'] = True
                for text in bot_messages_ru['start_tape'][2]:
                    await message.answer(text)

            data['listen_channels'].append(new_channel_id)
        else:
            for text in bot_messages_ru['enter_add_listen'][1]:
                await message.answer(text)
            return
    await _join_new_listen_channels_to_client([new_channel_id])
    await store.save_new_listen_channels_to_common_collection(exist_channels, message.from_user.id)


@_DP.message_handler(commands=[MENU_COMMANDS['/delete']], state='*')
async def _delete_listen_channel(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        if (await state.get_data())['listen_channels']:
            await message.answer(bot_messages_ru['delete_listen'][0][0], reply_markup=END_KEYBOARD)
            for text in bot_messages_ru['delete_listen'][0][1:]:
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

    if text == '/end':
        await message.answer(bot_messages_ru['end'][0], reply_markup=SUPPORT_KEYBOARD)
        for text in bot_messages_ru['end'][1:]:
            await message.answer(text)
        await state.reset_state(with_data=False)
        return

    if text[0] == '/' and text not in ALL_COMMANDS:
        text = '@' + text[1:]
    elif text in ALL_COMMANDS:
        for text in bot_messages_ru['state_if_exist']:
            await message.answer(text)
    else:
        pass

    exist_channels_to_store = await store.check_exist_channel_usernames_to_store([text], message.from_user.id)

    if exist_channels_to_store:
        channel_id = list(exist_channels_to_store.keys())[0]
        async with state.proxy() as data:
            data['listen_channels'].remove(channel_id)

            for text in bot_messages_ru['enter_delete_listen'][1]:
                await message.answer(text)

            if not data['listen_channels']:
                data['is_listen'] = False
                await message.answer(bot_messages_ru['enter_delete_listen'][0][0], reply_markup=SUPPORT_KEYBOARD)
                for text in bot_messages_ru['enter_delete_listen'][0][1:]:
                    await message.answer(text)
                for text in bot_messages_ru['stop_tape'][0]:
                    await message.answer(text)
                await state.reset_state(with_data=False)
                return

        await _get_subscriptions_table(message=message, state=state)
        _ = await store.delete_listen_channels_to_common_collection([channel_id],
                                                                    user_id=message.from_user.id)
    else:
        for text in bot_messages_ru['enter_delete_listen'][2]:
            await message.answer(text)


@_DP.message_handler(commands=[MENU_COMMANDS['/wish']], state='*')
async def _on_wish(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        text = await store.get_user_wish(message.from_user.id)
        if text:
            await message.answer(
                bot_messages_ru['wish'][0][0] + bot_messages_ru['wish'][0][1] + text + bot_messages_ru['wish'][0][2],
                reply_markup=SUPPORT_KEYBOARD)
            for text in bot_messages_ru['wish'][1]:
                await message.answer(text)
            await SupportStates.switch_wish.set()
        else:
            await message.answer(bot_messages_ru['wish'][2][0], reply_markup=SUPPORT_KEYBOARD)
            for text in bot_messages_ru['wish'][2][1:]:
                await message.answer(text)
            await SupportStates.enter_wish.set()
    else:
        for text in bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(state=SupportStates.switch_wish)
async def _switch_wish(message: bot_types.Message, state: FSMContext):
    if message.text == 'да':
        for text in bot_messages_ru['switch_wish'][0]:
            await message.answer(text)
        await SupportStates.enter_wish.set()
    elif message.text == 'нет':
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
async def _check_channel_urls_exist(urls):
    valid_urls = list(set(urls) - ALL_COMMANDS)
    if not valid_urls:
        return {}, []

    exist_channels = {}
    not_exist_channel_urls = []

    exist_channel_to_client, not_exist_channel_urls_to_client = await _check_channel_exist_to_client(valid_urls)
    exist_channels.update(exist_channel_to_client)

    for url in not_exist_channel_urls_to_client:
        try:
            obj = await _CLIENT.get_entity(url)
            if isinstance(obj, client_types.Channel):
                exist_channels[obj.id] = f"@{obj.username}"
            else:
                not_exist_channel_urls.append(url)
        except ValueError:
            not_exist_channel_urls.append(url)
        except Exception as err:
            not_exist_channel_urls.append(url)
            _LOGGER.error(err)
    return exist_channels, not_exist_channel_urls


async def _check_channel_exist_to_client(urls):
    exist_channel = {}
    not_exist_channel_urls = []

    usernames = {await store.on_telegram_username(url) for url in urls}
    all_dialogs = {dialog.entity.username: dialog.entity.id async for dialog in _CLIENT.iter_dialogs(archived=True)}

    for username in usernames:
        if all_dialogs.get(username):
            exist_channel[all_dialogs[username]] = f"@{username}"
        else:
            not_exist_channel_urls.append(await store.on_telegram_url(username))
    return exist_channel, not_exist_channel_urls


async def _check_bot_is_channel_admin(channel_id):
    try:
        member = await _BOT.get_chat_member(-(10 ** 12 + channel_id), API_BOT_TOKEN.split(":")[0])
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


async def _get_exist_channel_with_titles_to_client(channel_ids):
    channel_ids_set = set(channel_ids)
    exist_channel = {dialog.entity.id: (dialog.entity.username, dialog.entity.title) async for dialog in
                     _CLIENT.iter_dialogs(archived=True) if dialog.entity.id in channel_ids_set}

    not_exist_channel_ids = list(channel_ids_set - set(exist_channel.keys()))

    return exist_channel, not_exist_channel_ids


# NOTIFICATION
async def _send_message_channel_subscribers(post_text, channel_ids):
    client = await store.STORAGE.get_client()
    db = client[MONGO_DBNAME]
    users_coll = db["aiogram_data"]
    channels_coll = db[LISTEN_CHANNELS_COLL_NAME]

    async for channel_obj in channels_coll.find({"id": {"$in": channel_ids}}):
        async for obj in users_coll.find({"data.listen_channels": {'$in': [channel_obj['id']]}}):
            try:
                await _BOT.send_message(chat_id=obj["user"],
                                        text=
                                        f"К глубочайшему сожалению, канал {channel_obj['nickname']} "
                                        + post_text)
            except Unauthorized:
                await store.stop_listen_for_user(obj['user'])
            except Exception as err:
                _LOGGER.error(err)


async def _notify_users_about_engineering_works(is_start):
    client = await store.STORAGE.get_client()
    db = client[MONGO_DBNAME]
    users_coll = db["aiogram_data"]

    async for obj in users_coll.find({}):
        try:
            if not is_start:
                await _BOT.send_message(chat_id=obj["user"],
                                        text=bot_messages_ru['engineering_works'][0],
                                        reply_markup=bot_types.ReplyKeyboardRemove())
            else:
                await _BOT.send_message(chat_id=obj["user"],
                                        text=bot_messages_ru['engineering_works'][1], reply_markup=SUPPORT_KEYBOARD)
        except Unauthorized:
            await store.stop_listen_for_user(obj['user'])
        except Exception as err:
            _LOGGER.error(err)


async def _send_and_pin_message_all_users(post_text):
    client = await store.STORAGE.get_client()
    db = client[MONGO_DBNAME]
    users_coll = db["aiogram_data"]

    async for obj in users_coll.find({}):
        try:
            message = await _BOT.send_message(chat_id=obj["user"],
                                    text=post_text)
            await _BOT.pin_chat_message(obj["user"], message.message_id)
        except Unauthorized:
            await store.stop_listen_for_user(obj['user'])
        except Exception as err:
            _LOGGER.error(err)


# LISTENER
MEDIA_PATH = 'Media'


async def _reload_listener():
    listen_channel_ids = await store.get_all_listen_channel_ids()

    if not listen_channel_ids:
        return

    if _CLIENT.list_event_handlers():
        _CLIENT.remove_event_handler(_on_new_channel_album_message, events.Album())
        _CLIENT.remove_event_handler(_on_new_channel_message, events.NewMessage())

    _CLIENT.add_event_handler(_on_new_channel_album_message, events.Album(chats=listen_channel_ids))
    _CLIENT.add_event_handler(_on_new_channel_message, events.NewMessage(chats=listen_channel_ids))


async def _on_new_channel_album_message(event):
    await _forward_new_message(event)


async def _on_new_channel_message(event):
    if not event.message.grouped_id:
        await _forward_new_message(event)


async def _forward_new_message(event):
    listen_channel_id = abs(10 ** 12 + event.chat_id)

    client = await store.STORAGE.get_client()
    db = client[MONGO_DBNAME]
    users_coll = db["aiogram_data"]

    listen_user_ids = [obj['user'] async for obj in
                       users_coll.find({"$and": [{"data.listen_channels": {'$in': [listen_channel_id]}},
                                                 {"data.is_listen": True}]})]
    try:
        message = await event.forward_to(MAIN_TAPE_CHANNEL_ID)
        if isinstance(message, list):
            temp_folder = f'{listen_channel_id}/{event.grouped_id}'
            file_paths = await _download_media(message, temp_folder)

            media = bot_types.MediaGroup()
            caption_text = message[0].text + f'\n\nПереслано из https://t.me/{event.chat.username}/{event.messages[0].id}'
            for index, path in enumerate(file_paths):
                media.attach_photo(bot_types.InputFile(path), caption=caption_text if index == 0 else '')

            for id in listen_user_ids:
                try:
                    await _BOT.send_media_group(chat_id=id, media=media)
                except Unauthorized:
                    await store.stop_listen_for_user(id)
                except Exception as err:
                    _LOGGER.error(err)

            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, _delete_media_group, temp_folder)
        else:
            for id in listen_user_ids:
                try:
                    await _BOT.forward_message(chat_id=id,
                                               from_chat_id=MAIN_TAPE_CHANNEL_ID,
                                               message_id=message.id)
                except Unauthorized:
                    await store.stop_listen_for_user(id)
                except Exception as err:
                    _LOGGER.error(err)
    except AuthKeyError:
        await _send_message_channel_subscribers(bot_messages_ru['channel_on_protection'], [listen_channel_id])
        await store.delete_everywhere_listen_channels_to_store([listen_channel_id])
        await _reload_listener()


async def _download_media(messages, temp_folder):
    file_paths = []
    group_path = f'{MEDIA_PATH}/{temp_folder}'
    for index, message in enumerate(messages):
        file_path = f"{group_path}/{index}"
        file_paths.append(await _CLIENT.download_media(message.media, file_path))
    return file_paths


def _delete_media_group(temp_folder):
    group_path = f'{MEDIA_PATH}/{temp_folder}'
    shutil.rmtree(group_path)


def run():
    _CLIENT.start(phone=PHONE)
    # _CLIENT.loop.run_until_complete(_notify_users_about_engineering_works(is_start=True))
    _CLIENT.loop.run_until_complete(_reload_listener())
    executor.start_polling(_DP, skip_updates=True)


if __name__ == '__main__':
    run()
    # _CLIENT.loop.run_until_complete(_notify_users_about_engineering_works(is_start=False))
    _CLIENT.disconnect()
