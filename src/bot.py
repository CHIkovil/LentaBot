from src import *


class LentaBot(object):
    _BOT = Bot(token=conf.API_TOKEN)
    _DP = Dispatcher(_BOT)

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
        await message.reply(emojize("Тута:dodo:"))

    @staticmethod
    @_DP.message_handler()
    async def echo(message: types.Message):
        """
        This handler simple resend input message.
        """
        await message.answer(message.text)


if __name__ == '__main__':
    bot = LentaBot()

    try:
        bot.run()
    finally:
        bot.stop()