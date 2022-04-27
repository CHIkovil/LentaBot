from src import *


class StartQuestion(StatesGroup):
    enter_new_bot_name = State()
    enter_channels = State()


class LentaBot(object):
    _BOT = Bot(token=conf.API_TOKEN)
    _DP = Dispatcher(_BOT, storage=MemoryStorage())

    def __init__(self):
        pass

    def run(self):
        executor.start_polling(self._DP, skip_updates=True)

    def stop(self):
        self._DP.stop_polling()

    @staticmethod
    @_DP.message_handler(commands=['start'])
    async def send_welcome(message: types.Message):
        """
        This handler will be called when user sends `/start`.
        """
        await message.answer(emojize("Тута:eyes:"))
        await message.answer(emojize("Псс псс придумай мне кличку!"))
        await StartQuestion.enter_new_bot_name.set()

    @staticmethod
    @_DP.message_handler(state=StartQuestion.enter_new_bot_name)
    async def enter_new_bot_name(message: types.Message):
        print(message.text)
        await message.answer(emojize("Учти, отныне я буду прислушиваться только к ней:face_with_tongue:"))
        await message.answer(emojize("..."))
        await message.answer(emojize("Ну и наконец перечисли каналы из которых мы сформируем твою ЛИЧНУЮ ленту!"))
        await message.answer(emojize("Через запятую конечно же."))
        await StartQuestion.enter_channels.set()

    @staticmethod
    @_DP.message_handler(state=StartQuestion.enter_channels)
    async def enter_new_bot_name(message: types.Message, state: FSMContext):
        print(message.text)
        await state.finish()

    @staticmethod
    @_DP.message_handler()
    async def echo(message: types.Message):
        await message.answer("Тах тах не флуди...")
        await message.answer(emojize("Мы же занимаемся серьезными вопросами:oncoming_fist:"))
        await message.answer("Не отвлекай")


if __name__ == '__main__':
    bot = LentaBot()

    try:
        bot.run()
    finally:
        bot.stop()
