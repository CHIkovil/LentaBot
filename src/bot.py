from src import *
from src import store
from Support import messages, states, commands
from src.Handlers.error_handler import ErrorHandler
from src.conf import *

_BOT = Bot(token=API_BOT_TOKEN)
_DP = Dispatcher(_BOT, storage=store.STORAGE)
_CLIENT = TelegramClient(APP_NAME, api_id=API_ID, api_hash=API_HASH)

# LOGGER
logging.basicConfig(format='%(asctime)s, [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%m-%d %H:%M:%S',
                    level=logging.ERROR)
_LOGGER = logging.getLogger(APP_NAME)
_LOGGER.addHandler(ErrorHandler(send_func=_BOT.send_message, error_channel_id=ERROR_CHANNEL_ID))


# KEYBOARD
def _get_menu_keyboard(is_admin):
    func = lambda A, n=2: [A[i:i + n] for i in range(0, len(A), n)]

    keyboard = bot_types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [cmd[1] for cmd in commands.MENU_COMMANDS.values()]
    if is_admin:
        buttons += [cmd[1] for cmd in commands.ADMIN_COMMANDS.values()]

    buttons_rows = func(buttons)
    for row in buttons_rows:
        keyboard.row(*row)

    return keyboard


SUPPORT_KEYBOARD = bot_types.ReplyKeyboardMarkup(resize_keyboard=True).add(
    *[commands.MAIN_COMMANDS['help'][1], commands.MAIN_COMMANDS['menu'][1]])
END_KEYBOARD = bot_types.ReplyKeyboardMarkup(resize_keyboard=True).add(*[commands.TEMP_COMMAND['end'][1]])
CHOICE_KEYBOARD = bot_types.ReplyKeyboardMarkup(resize_keyboard=True).add(
    *[commands.TEMP_COMMAND['yes'][1], commands.TEMP_COMMAND['no'][1]])

MEDIA_PATH = 'Temp'


# ADMIN
@_DP.message_handler(filters.Text(equals=commands.ADMIN_COMMANDS['post']),
                     filters.ChatTypeFilter(chat_type=bot_types.ChatType.PRIVATE), state='*')
async def _on_post(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        if message.from_user.id == ADMIN_ID:
            await message.answer(messages.bot_messages_ru["admin_post"][0])
            await message.answer(messages.bot_messages_ru["admin_post"][1],
                                 reply_markup=CHOICE_KEYBOARD)
            await states.AdminStates.switch_post.set()
        else:
            for text in messages.bot_messages_ru['echo']:
                await message.answer(text)
    else:
        for text in messages.bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(state=states.AdminStates.switch_post)
async def _switch_post(message: bot_types.Message, state: FSMContext):
    if message.text == commands.TEMP_COMMAND['yes'][1]:
        await message.answer(messages.bot_messages_ru["admin_switch_post"][0],
                             reply_markup=SUPPORT_KEYBOARD)
        await states.AdminStates.enter_post.set()
    else:
        await message.answer(messages.bot_messages_ru["admin_switch_post"][1], reply_markup=SUPPORT_KEYBOARD)
        await state.reset_state(with_data=False)


@_DP.message_handler(state=states.AdminStates.enter_post)
async def _enter_post(message: bot_types.Message, state: FSMContext):
    if message.text not in commands.ALL_COMMANDS:
        await message.answer(messages.bot_messages_ru["admin_enter_post"][0])
        await _send_and_pin_message_all_users(message.text)
        await state.reset_state(with_data=False)
    else:
        for msg in messages.bot_messages_ru["admin_not_commands"]:
            await message.answer(msg)


@_DP.message_handler(filters.Text(equals=commands.ADMIN_COMMANDS['statistics']),
                     filters.ChatTypeFilter(chat_type=bot_types.ChatType.PRIVATE), state='*')
async def _get_statistics(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        if message.from_user.id == ADMIN_ID:
            all_users_len = len(await store.get_all_users())
            all_listen_users = len(await store.get_all_listen_users())
            all_listen_channels_len = len(await store.get_all_listen_channel_ids())
            all_users_wishes = len(await store.get_all_wish_texts())

            await message.answer(messages.bot_messages_ru["admin_statistics"][0] +
                                 messages.bot_messages_ru["admin_statistics"][1] + f'{all_users_len}\n' +
                                 messages.bot_messages_ru["admin_statistics"][2] + f'{all_listen_users}\n' +
                                 messages.bot_messages_ru["admin_statistics"][3] + f'{all_listen_channels_len}\n' +
                                 messages.bot_messages_ru["admin_statistics"][
                                     4] + f'{all_users_wishes}/{all_users_len}\n',
                                 reply_markup=SUPPORT_KEYBOARD)
        else:
            for text in messages.bot_messages_ru['echo']:
                await message.answer(text)
    else:
        for text in messages.bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(filters.Text(equals=commands.ADMIN_COMMANDS['reset_wish']),
                     filters.ChatTypeFilter(chat_type=bot_types.ChatType.PRIVATE), state='*')
async def _reset_all_wishes(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        if message.from_user.id == ADMIN_ID:
            await message.answer(messages.bot_messages_ru["admin_reset_wish"][0], reply_markup=SUPPORT_KEYBOARD)
            texts = await store.get_all_wish_texts()
            loop = asyncio.get_event_loop()
            file_path = await loop.run_in_executor(None, _write_wishes_to_txt, texts)
            await message.answer_document(open(file_path, 'rb'))
            loop.run_in_executor(None, _delete_wishes_txt, file_path)
            await store.drop_wish()
        else:
            for text in messages.bot_messages_ru['echo']:
                await message.answer(text)
    else:
        for text in messages.bot_messages_ru['state_if_exist']:
            await message.answer(text)


def _write_wishes_to_txt(texts):
    if not os.path.exists(MEDIA_PATH):
        os.mkdir(MEDIA_PATH)

    file_path = f'{MEDIA_PATH}/wishes.txt'
    with open(file_path, 'w') as f:
        f.writelines(texts)
    return file_path


def _delete_wishes_txt(path):
    os.remove(path)


@_DP.message_handler(filters.Text(equals=commands.ADMIN_COMMANDS['keywords']),
                     filters.ChatTypeFilter(chat_type=bot_types.ChatType.PRIVATE), state='*')
async def _get_keywords(message: bot_types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        keywords = await store.get_all_keywords()
        if keywords:
            state_name = await state.get_state()
            table_text = messages.bot_messages_ru['admin_keywords'][0][0]
            for word in keywords:
                table_text += f"🔸 {word}\n"

            if state_name == states.DELETE_KEYWORD_STATE_NAME or state_name == states.ADD_KEYWORD_STATE_NAME:
                await message.answer(table_text)
            else:
                await message.answer(table_text, reply_markup=SUPPORT_KEYBOARD)
        else:
            await message.answer(messages.bot_messages_ru['admin_keywords'][1])
    else:
        for text in messages.bot_messages_ru['echo']:
            await message.answer(text)


@_DP.message_handler(filters.Text(equals=commands.ADMIN_COMMANDS['add_keyword']),
                     filters.ChatTypeFilter(chat_type=bot_types.ChatType.PRIVATE), state='*')
async def _add_keywords(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        if message.from_user.id == ADMIN_ID:
            await message.answer(messages.bot_messages_ru['admin_add_keyword'][0], reply_markup=END_KEYBOARD)
            for text in messages.bot_messages_ru['admin_add_keyword'][1:]:
                await message.answer(text)
            await states.AdminStates.add_keyword.set()
        else:
            for text in messages.bot_messages_ru['echo']:
                await message.answer(text)
    else:
        for text in messages.bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(filters.Text(equals=commands.ADMIN_COMMANDS['delete_keyword']),
                     filters.ChatTypeFilter(chat_type=bot_types.ChatType.PRIVATE), state='*')
async def _delete_keyword(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        if message.from_user.id == ADMIN_ID:
            await message.answer(messages.bot_messages_ru['admin_delete_keyword'][0], reply_markup=END_KEYBOARD)
            for text in messages.bot_messages_ru['admin_delete_keyword'][1:]:
                await message.answer(text)
            await states.AdminStates.delete_keyword.set()
        else:
            for text in messages.bot_messages_ru['echo']:
                await message.answer(text)
    else:
        for text in messages.bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(state=states.AdminStates.add_keyword)
async def _enter_add_keywords(message: bot_types.Message, state: FSMContext):
    if message.text not in commands.ALL_COMMANDS:
        if message.text in commands.TEMP_COMMAND['end']:
            await message.answer(messages.bot_messages_ru['end'][0], reply_markup=SUPPORT_KEYBOARD)
            for text in messages.bot_messages_ru['end'][1:]:
                await message.answer(text)
            await state.reset_state(with_data=False)
            return
        result = await store.add_keyword(message.text.lower())
        if result:
            for text in messages.bot_messages_ru['admin_enter_add_keyword'][0]:
                await message.answer(text)
        else:
            for text in messages.bot_messages_ru['admin_enter_add_keyword'][1]:
                await message.answer(text)
    else:
        for msg in messages.bot_messages_ru["admin_not_commands"]:
            await message.answer(msg)


@_DP.message_handler(state=states.AdminStates.delete_keyword)
async def _enter_delete_keywords(message: bot_types.Message, state: FSMContext):
    if message.text not in commands.ALL_COMMANDS:
        if message.text in commands.TEMP_COMMAND['end']:
            await message.answer(messages.bot_messages_ru['end'][0], reply_markup=SUPPORT_KEYBOARD)
            for text in messages.bot_messages_ru['end'][1:]:
                await message.answer(text)
            await state.reset_state(with_data=False)
            return
        text = message.text
        if text[0] == '/':
            text = text[1:]
        result = await store.delete_keyword(text)
        if result:
            for text in messages.bot_messages_ru['admin_enter_delete_keyword'][0]:
                await message.answer(text)
        else:
            for text in messages.bot_messages_ru['admin_enter_delete_keyword'][1]:
                await message.answer(text)

        await _get_keywords(message=message, state=state)
    else:
        for msg in messages.bot_messages_ru["admin_not_commands"]:
            await message.answer(msg)


# USER
@_DP.message_handler(filters.Text(equals=commands.MAIN_COMMANDS['menu']),
                     filters.ChatTypeFilter(chat_type=bot_types.ChatType.PRIVATE), state='*')
async def _on_menu(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        is_admin = message.from_user.id == ADMIN_ID
        menu_keyboard = _get_menu_keyboard(is_admin)
        await message.answer(messages.bot_messages_ru['menu'], reply_markup=menu_keyboard)
    else:
        for text in messages.bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(filters.Text(equals=commands.MAIN_COMMANDS['start']),
                     filters.ChatTypeFilter(chat_type=bot_types.ChatType.PRIVATE), state='*')
async def _on_start(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        if not await state.get_data():
            for text in messages.bot_messages_ru['start'][0]:
                await message.answer(text)
            await states.StartQuestionStates.enter_initial_listen_channels.set()
        else:
            for text in messages.bot_messages_ru['start'][1]:
                await message.answer(text)
            await _start_tape(message, state)
    else:
        for text in messages.bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(state=states.StartQuestionStates.enter_initial_listen_channels)
async def _enter_initial_listen_channels(message: bot_types.Message, state: FSMContext):
    channels = list(set(message.text.split(',')))
    exist_channels, not_exist_channel_entities = await _check_channel_urls_exist(channels)

    if not exist_channels and not not_exist_channel_entities:
        for text in messages.bot_messages_ru['state_if_exist']:
            await message.answer(text)
        return

    if not_exist_channel_entities:
        for text in messages.bot_messages_ru['enter_init_listen'][0]:
            await message.answer(text + f"{','.join(not_exist_channel_entities)}\n")

        if exist_channels:
            for text in messages.bot_messages_ru['enter_init_listen'][1]:
                await message.answer(text + f"{','.join(list(exist_channels.values()))}\n")

        for text in messages.bot_messages_ru['enter_init_listen'][2]:
            await message.answer(text)
        return

    await message.answer(messages.bot_messages_ru['enter_init_listen'][3][0], reply_markup=SUPPORT_KEYBOARD)
    for text in messages.bot_messages_ru['enter_init_listen'][3][1:]:
        await message.answer(text)

    async with state.proxy() as data:
        data['listen_channels'] = list(exist_channels.keys())
        data['is_listen'] = True

    await _join_new_listen_channels_to_client(list(exist_channels.keys()))
    await store.save_new_listen_channels_to_common_collection(exist_channels, user_id=message.from_user.id)
    await _reload_listener()
    await state.reset_state(with_data=False)


@_DP.message_handler(filters.Text(equals=commands.MENU_COMMANDS['on']),
                     filters.ChatTypeFilter(chat_type=bot_types.ChatType.PRIVATE), state='*')
async def _start_tape(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        data = await state.get_data()
        if data['is_listen']:
            await message.answer(messages.bot_messages_ru['start_tape'][0][0], reply_markup=SUPPORT_KEYBOARD)
        else:
            if not data['listen_channels']:
                await message.answer(messages.bot_messages_ru['start_tape'][1][0], reply_markup=SUPPORT_KEYBOARD)
                for text in messages.bot_messages_ru['start_tape'][1][1:]:
                    await message.answer(text, reply_markup=SUPPORT_KEYBOARD)
            else:
                await message.answer(messages.bot_messages_ru['start_tape'][2][0], reply_markup=SUPPORT_KEYBOARD)
                async with state.proxy() as data:
                    data['is_listen'] = True
    else:
        for text in messages.bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(filters.Text(equals=commands.MENU_COMMANDS['off']),
                     filters.ChatTypeFilter(chat_type=bot_types.ChatType.PRIVATE), state='*')
async def _stop_tape(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        if (await state.get_data())['is_listen']:
            await message.answer(messages.bot_messages_ru['stop_tape'][0][0], reply_markup=SUPPORT_KEYBOARD)
            async with state.proxy() as data:
                data['is_listen'] = False
        else:
            await message.answer(messages.bot_messages_ru['stop_tape'][1][0], reply_markup=SUPPORT_KEYBOARD)
    else:
        for text in messages.bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(filters.Text(equals=commands.MAIN_COMMANDS['help']),
                     filters.ChatTypeFilter(chat_type=bot_types.ChatType.PRIVATE), state='*')
async def _on_help(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        await message.answer(messages.bot_messages_ru['help'])
    else:
        for text in messages.bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(filters.Text(equals=commands.MENU_COMMANDS['subscriptions']),
                     filters.ChatTypeFilter(chat_type=bot_types.ChatType.PRIVATE), state='*')
async def _get_subscriptions_table(message: bot_types.Message, state: FSMContext):
    state_name = await state.get_state()

    if not state_name or state_name == states.DELETE_CHANNEL_STATE_NAME or state_name == states.ADD_CHANNEL_STATE_NAME:
        listen_channel_ids = (await state.get_data())['listen_channels']
        exist_channel, not_exist_channel_ids = await _get_exist_channel_with_titles_to_client(listen_channel_ids)

        if exist_channel:
            table_text = f"{messages.bot_messages_ru['subscriptions'][0][0]}"

            for username, title in list(exist_channel.values()):
                if state_name == states.DELETE_CHANNEL_STATE_NAME:
                    table_text += f"🔹 /{username} - {title}\n"
                else:
                    table_text += f"🔹 @{username} - {title}\n"

            if state_name == states.DELETE_CHANNEL_STATE_NAME or state_name == states.ADD_CHANNEL_STATE_NAME:
                await message.answer(table_text)
            else:
                await message.answer(table_text, reply_markup=SUPPORT_KEYBOARD)

        else:
            await message.answer(messages.bot_messages_ru['subscriptions'][1])

        if not_exist_channel_ids:
            await _send_message_channel_subscribers(messages.bot_messages_ru['channel_not_exist'],
                                                    not_exist_channel_ids)
            await store.delete_everywhere_listen_channels_to_store(not_exist_channel_ids)
    else:
        for text in messages.bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(filters.Text(equals=commands.MENU_COMMANDS['add']),
                     filters.ChatTypeFilter(chat_type=bot_types.ChatType.PRIVATE), state='*')
async def _add_listen_channel(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        await message.answer(messages.bot_messages_ru['add_listen'][0], reply_markup=END_KEYBOARD)
        for text in messages.bot_messages_ru['add_listen'][1:]:
            await message.answer(text)
        await states.UpdateStates.enter_add_listen_channels.set()
    else:
        for text in messages.bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(state=states.UpdateStates.enter_add_listen_channels)
async def _enter_add_listen_channels(message: bot_types.Message, state: FSMContext):
    if message.text == commands.TEMP_COMMAND['end'][0] or message.text == commands.TEMP_COMMAND['end'][1]:
        await message.answer(messages.bot_messages_ru['end'][0], reply_markup=SUPPORT_KEYBOARD)
        for text in messages.bot_messages_ru['end'][1:]:
            await message.answer(text)
        await _reload_listener()
        await state.reset_state(with_data=False)
        return

    exist_channels, not_exist_channel_entities = await _check_channel_urls_exist([message.text])

    if not exist_channels and not not_exist_channel_entities:
        for text in messages.bot_messages_ru['state_if_exist']:
            await message.answer(text)
        return

    if not_exist_channel_entities:
        for text in messages.bot_messages_ru['enter_add_listen'][0]:
            await message.answer(text)
        return

    async with state.proxy() as data:
        new_channel_id = list(exist_channels.keys())[0]
        if new_channel_id not in set(data['listen_channels']):
            for text in messages.bot_messages_ru['enter_add_listen'][2]:
                await message.answer(text)

            if not data['listen_channels']:
                data['is_listen'] = True
                for text in messages.bot_messages_ru['start_tape'][2]:
                    await message.answer(text)

            data['listen_channels'].append(new_channel_id)
        else:
            for text in messages.bot_messages_ru['enter_add_listen'][1]:
                await message.answer(text)
            return
    await _join_new_listen_channels_to_client([new_channel_id])
    await store.save_new_listen_channels_to_common_collection(exist_channels, message.from_user.id)


@_DP.message_handler(filters.Text(equals=commands.MENU_COMMANDS['delete']),
                     filters.ChatTypeFilter(chat_type=bot_types.ChatType.PRIVATE), state='*')
async def _delete_listen_channel(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        if (await state.get_data())['listen_channels']:
            await message.answer(messages.bot_messages_ru['delete_listen'][0][0], reply_markup=END_KEYBOARD)
            for text in messages.bot_messages_ru['delete_listen'][0][1:]:
                await message.answer(text)
            await states.UpdateStates.enter_delete_listen_channel.set()
        else:
            for text in messages.bot_messages_ru['delete_listen'][1]:
                await message.answer(text)
    else:
        for text in messages.bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(state=states.UpdateStates.enter_delete_listen_channel)
async def _enter_delete_listen_channel(message: bot_types.Message, state: FSMContext):
    text = message.text

    if text == commands.TEMP_COMMAND['end'][0] or text == commands.TEMP_COMMAND['end'][1]:
        await message.answer(messages.bot_messages_ru['end'][0], reply_markup=SUPPORT_KEYBOARD)
        for text in messages.bot_messages_ru['end'][1:]:
            await message.answer(text)
        await state.reset_state(with_data=False)
        return

    if text[0] == '/' and text not in commands.ALL_COMMANDS:
        text = '@' + text[1:]
    elif text in commands.ALL_COMMANDS:
        for text in messages.bot_messages_ru['state_if_exist']:
            await message.answer(text)
    else:
        pass

    exist_channels_to_store = await store.check_exist_channel_usernames_to_store([text], message.from_user.id)

    if exist_channels_to_store:
        channel_id = list(exist_channels_to_store.keys())[0]
        async with state.proxy() as data:
            data['listen_channels'].remove(channel_id)

            for text in messages.bot_messages_ru['enter_delete_listen'][1]:
                await message.answer(text)

            if not data['listen_channels']:
                data['is_listen'] = False
                await message.answer(messages.bot_messages_ru['enter_delete_listen'][0][0],
                                     reply_markup=SUPPORT_KEYBOARD)
                for text in messages.bot_messages_ru['enter_delete_listen'][0][1:]:
                    await message.answer(text)
                for text in messages.bot_messages_ru['stop_tape'][0]:
                    await message.answer(text)
                await state.reset_state(with_data=False)
                return

        await _get_subscriptions_table(message=message, state=state)
        _ = await store.delete_listen_channels_to_common_collection([channel_id],
                                                                    user_id=message.from_user.id)
    else:
        for text in messages.bot_messages_ru['enter_delete_listen'][2]:
            await message.answer(text)


@_DP.message_handler(filters.Text(equals=commands.MENU_COMMANDS['wish']),
                     filters.ChatTypeFilter(chat_type=bot_types.ChatType.PRIVATE), state='*')
async def _on_wish(message: bot_types.Message, state: FSMContext):
    if not (await state.get_state()):
        text = await store.get_user_wish(message.from_user.id)
        if text:
            await message.answer(
                messages.bot_messages_ru['wish'][0][0] + text,
                reply_markup=CHOICE_KEYBOARD)
            for text in messages.bot_messages_ru['wish'][1]:
                await message.answer(text)
            await states.SupportStates.switch_wish.set()
        else:
            await message.answer(messages.bot_messages_ru['wish'][2][0], reply_markup=SUPPORT_KEYBOARD)
            for text in messages.bot_messages_ru['wish'][2][1:]:
                await message.answer(text)
            await states.SupportStates.enter_wish.set()
    else:
        for text in messages.bot_messages_ru['state_if_exist']:
            await message.answer(text)


@_DP.message_handler(state=states.SupportStates.switch_wish)
async def _switch_wish(message: bot_types.Message, state: FSMContext):
    if message.text == commands.TEMP_COMMAND['yes'][1]:
        await message.answer(messages.bot_messages_ru['switch_wish'][0][0], reply_markup=SUPPORT_KEYBOARD)
        await states.SupportStates.enter_wish.set()
    elif message.text == commands.TEMP_COMMAND['no'][1]:
        await message.answer(messages.bot_messages_ru['switch_wish'][1][0], reply_markup=SUPPORT_KEYBOARD)
        await state.reset_state(with_data=False)
    else:
        await message.answer(messages.bot_messages_ru['switch_wish'][2][0], reply_markup=SUPPORT_KEYBOARD)
        await state.reset_state(with_data=False)


@_DP.message_handler(state=states.SupportStates.enter_wish)
async def _enter_wish(message: bot_types.Message, state: FSMContext):
    await message.answer(messages.bot_messages_ru['enter_wish'][0], reply_markup=SUPPORT_KEYBOARD)
    for text in messages.bot_messages_ru['enter_wish'][1:]:
        await message.answer(text)
    await store.add_user_wish(message.from_user.id, message.text)
    await state.reset_state(with_data=False)


@_DP.message_handler(filters.ChatTypeFilter(chat_type=bot_types.ChatType.PRIVATE))
async def _echo(message: bot_types.Message):
    await message.answer(messages.bot_messages_ru['echo'][0], reply_markup=SUPPORT_KEYBOARD)
    for text in messages.bot_messages_ru['echo'][1:]:
        await message.answer(text)


# CHECK
async def _check_channel_urls_exist(urls):
    valid_urls = list(set(urls) - commands.ALL_COMMANDS)
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
                     _CLIENT.iter_dialogs(archived=True) if
                     dialog.entity.id in channel_ids_set and dialog.entity.username is not None}

    not_exist_channel_ids = list(channel_ids_set - set(exist_channel.keys()))

    return exist_channel, not_exist_channel_ids


# NOTIFICATION
async def _send_message_channel_subscribers(post_text, channel_ids):
    result = await store.get_user_ids_with_channel_nicknames(channel_ids=channel_ids)

    for channel_nickname, user_ids in result.items():
        for user in user_ids:
            try:
                await _BOT.send_message(chat_id=user,
                                        text=
                                        f"К глубочайшему сожалению, канал {channel_nickname} "
                                        + post_text)
            except Unauthorized:
                await store.stop_listen_for_user(user)
            except Exception as err:
                _LOGGER.error(err)


async def _notify_users_about_engineering_works(is_start):
    result = await store.get_all_users()

    for obj in result:
        try:
            if not is_start:
                await _BOT.send_message(chat_id=obj["user"],
                                        text=messages.bot_messages_ru['engineering_works'][0],
                                        reply_markup=bot_types.ReplyKeyboardRemove())
            else:
                await _BOT.send_message(chat_id=obj["user"],
                                        text=messages.bot_messages_ru['engineering_works'][1],
                                        reply_markup=SUPPORT_KEYBOARD)
        except Unauthorized:
            await store.stop_listen_for_user(obj['user'])
        except Exception as err:
            _LOGGER.error(err)


async def _send_and_pin_message_all_users(post_text):
    result = await store.get_all_users()

    for obj in result:
        try:
            message = await _BOT.send_message(chat_id=obj["user"],
                                              text=post_text)
            await _BOT.pin_chat_message(obj["user"], message.message_id)
        except Unauthorized:
            await store.stop_listen_for_user(obj['user'])
        except Exception as err:
            _LOGGER.error(err)


# LISTENER
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

    listen_user_ids = await store.get_listen_user_ids_for_channel(listen_channel_id)

    try:
        if await check_dublication_event(event):
            return
        message = await event.forward_to(MAIN_TAPE_CHANNEL_ID)
        if isinstance(message, list):
            await _on_bot_forward_messages_group(event, message=message, user_ids=listen_user_ids)
        else:
            await _on_bot_forward_message(message=message, user_ids=listen_user_ids)
    except AuthKeyError:
        await _send_message_channel_subscribers(messages.bot_messages_ru['channel_on_protection'], [listen_channel_id])
        await store.delete_everywhere_listen_channels_to_store([listen_channel_id])
        await _reload_listener()
    except Exception as err:
        _LOGGER.error(err)


async def _on_bot_forward_messages_group(event, message, user_ids):
    temp_folder = f'{event.grouped_id}'
    file_paths = await _download_media(message, temp_folder)

    media = bot_types.MediaGroup()
    caption_message = [msg for msg in message if msg.text != '']
    caption_text = ''
    link_text = f'\n\nПереслано от https://t.me/{event.chat.username}/'
    if caption_message:
        link_text += f'{caption_message[0].forward.channel_post}'
        caption_text += caption_message[0].text
    else:
        link_text += f'{event.messages[0].id}'

    full_caption_text = caption_text + link_text
    for index, path in enumerate(file_paths):
        media.attach_photo(bot_types.InputFile(path), caption=full_caption_text if index == 0 else '')

    for id in user_ids:
        try:
            await _BOT.send_media_group(chat_id=id, media=media)
        except Unauthorized:
            await store.stop_listen_for_user(id)
        except Exception as err:
            _LOGGER.error(err)

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _delete_media_group, temp_folder)


async def _on_bot_forward_message(message, user_ids):
    for id in user_ids:
        try:
            await _BOT.forward_message(chat_id=id,
                                       from_chat_id=MAIN_TAPE_CHANNEL_ID,
                                       message_id=message.id)
        except Unauthorized:
            await store.stop_listen_for_user(id)
        except Exception as err:
            _LOGGER.error(err)


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


async def check_dublication_event(event):
    messages = {message.forward.channel_post: message.grouped_id async for message in
                _CLIENT.iter_messages(MAIN_TAPE_CHANNEL_ID, limit=25) if message.forward}
    if event.grouped_id:
        if event.grouped_id not in set(messages.values()):
            return False
    else:
        if event.message.id not in set(messages.keys()):
            return False

    return True


def run():
    _CLIENT.start(phone=PHONE)
    # _CLIENT.loop.run_until_complete(_notify_users_about_engineering_works(is_start=True))
    _CLIENT.loop.run_until_complete(_reload_listener())
    executor.start_polling(_DP, skip_updates=True)


if __name__ == '__main__':
    run()
    # _CLIENT.loop.run_until_complete(_notify_users_about_engineering_works(is_start=False))
    _CLIENT.disconnect()
