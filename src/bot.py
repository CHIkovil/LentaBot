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
async def _send_welcome(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not data:
        await message.answer(emojize("Тута:eyes:"))
        await message.answer(emojize("Псс придумай мне кличку!"))
        await StartQuestion.enter_new_bot_nickname.set()
    else:
        await message.answer(emojize(f"Мы уже начинали когда-то."))
        await message.answer(emojize(f"Когда были моложе:grinning_face_with_sweat:"))
        await message.answer(emojize(f"Напомню, обращайся ко мне как {data['bot_nickname']}:smirking_face:"))


@_DP.message_handler(state=StartQuestion.enter_new_bot_nickname)
async def _enter_new_bot_name(message: types.Message, state: FSMContext):
    async with state.proxy() as proxy:
        proxy['bot_nickname'] = message.text
    await message.answer(emojize("Учти, отныне я буду прислушиваться только к ней:face_with_tongue:"))
    await message.answer(emojize("..."))
    await message.answer(emojize("Ну и наконец перечисли каналы из которых мы сформируем твою ЛИЧНУЮ ленту!"))
    await message.answer(emojize("Через запятую конечно же."))
    await StartQuestion.enter_channels.set()


@_DP.message_handler(state=StartQuestion.enter_channels)
async def _enter_channels(message: types.Message, state: FSMContext):
    async with state.proxy() as proxy:
        channels = message.text.split(',')
        proxy['channels'] = channels
        valid_channels, not_valid_channels = await check_channels_valid(channels)

    await message.answer(emojize("Запомнил:OK_hand:"))
    await state.reset_state(with_data=False)


@_DP.message_handler()
async def _echo(message: types.Message):
    await message.answer("Тах тах не флуди...")
    await message.answer(emojize("Мы же тут ленту читаем:oncoming_fist:"))


async def check_channels_valid(channels):
    valid_ch = []
    not_valid_ch = []
    for ch in channels:
        try:
            _ = await _CLIENT.get_entity(ch)
            valid_ch.append(ch)
        except ValueError:
            not_valid_ch.append(ch)
    return valid_ch, not_valid_ch


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
