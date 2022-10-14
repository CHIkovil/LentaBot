from . import *


class StartQuestionStates(StatesGroup):
    enter_initial_listen_channels = State()


class UpdateStates(StatesGroup):
    enter_add_listen_channels = State()
    enter_delete_listen_channel = State()


class SupportStates(StatesGroup):
    switch_wish = State()
    enter_wish = State()


class AdminStates(StatesGroup):
    switch_post = State()
    enter_post = State()
    add_spam_word = State()
    delete_spam_word = State()


DELETE_CHANNEL_STATE_NAME = re.sub(r"[^A-Za-z_:]+", '', UpdateStates.enter_delete_listen_channel.__str__()).replace('State',

                                                                                                            '', 1)
ADD_CHANNEL_STATE_NAME = re.sub(r"[^A-Za-z_:]+", '', UpdateStates.enter_add_listen_channels.__str__()).replace('State',

                                                                                                       '', 1)

ADD_SPAM_WORD_STATE_NAME = re.sub(r"[^A-Za-z_:]+", '', AdminStates.add_spam_word.__str__()).replace('State',

                                                                                                       '', 1)

DELETE_SPAM_WORD_STATE_NAME = re.sub(r"[^A-Za-z_:]+", '', AdminStates.delete_spam_word.__str__()).replace('State',

                                                                                                       '', 1)
