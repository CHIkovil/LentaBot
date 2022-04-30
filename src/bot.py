from src import *


class StartQuestion(StatesGroup):
    enter_new_bot_nickname = State()
    enter_channels = State()


_BOT = Bot(token=conf.API_BOT_TOKEN)
_STORAGE = MongoStorage(db_name=conf.APP_NAME)
_DP = Dispatcher(_BOT, storage=_STORAGE)
_CLIENT = TelegramClient(conf.APP_NAME, api_id=conf.API_ID, api_hash=conf.API_HASH)

_is_listen = False
_all_channels = set()


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
    exist_channels, not_exist_channels = await _check_channels_exist(channels)

    if not_exist_channels:
        await message.answer("Что-то, но не канал:\n"
                             f"{','.join(not_exist_channels)}\n"
                             "Существующие каналы:\n"
                             f"{','.join(exist_channels)}\n"
                             )
        await message.answer("Внеси исправления и снова скинь мне!")
        await message.answer(emojize("Не забудь про запятую:smiling_face_with_horns:"))
        await message.answer(emojize("А может это вообще не каналы..."))
        return

    async with state.proxy() as data:
        data['channels'] = exist_channels

    await message.answer(emojize("Все запомнил:OK_hand:"))
    await state.reset_state(with_data=False)


@_DP.message_handler()
async def _echo(message: bot_types.Message):
    await message.answer("Тах тах не флуди...")
    await message.answer(emojize("Мы же тут ленту читаем:oncoming_fist:"))


# SUPPORT
async def _check_channels_exist(channels):
    exist_channels = []
    not_exist_channels = {}
    for channel in channels:
        try:
            if isinstance(await _CLIENT.get_entity(channel), client_types.Channel):
                exist_channels.append(channel)
            else:
                raise ValueError
        except ValueError:
            not_exist_channels.append(channel)
    return exist_channels, not_exist_channels


# LISTENER
def _run_listener():
    _CLIENT.loop.run_until_complete(_listen())


async def _listen():
    _is_listen = True
    _add_listen_handler()
    while True:
        await asyncio.sleep(1)


def _add_listen_handler():
    _CLIENT.add_event_handler(_on_new_channel_message, events.NewMessage(chats=_all_channels))


async def _on_new_channel_message():
    pass


if __name__ == '__main__':
    try:
        run()
    finally:
        stop()
