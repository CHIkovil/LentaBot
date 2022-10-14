def _get_all_commands():
    result = []
    all_commands_values = list(ADMIN_COMMANDS.values()) + list(MAIN_COMMANDS.values()) + list(MENU_COMMANDS.values())
    for commands in all_commands_values:
        result += list(commands)

    return set(result)


ADMIN_COMMANDS = {'add_spam_word': ('/add_spam_word', '➕добавить спам слово'),
                  'delete_spam_word': ('/delete_spam_word', '➖удалить спам слово'),
                  'spam_words': ('/spam_words', '📂спам слова'),
                  'statistics': ('/statistics', '📈статистика'),
                  'reset_wish': ('/reset_wish', '📩сбор пожеланий'),
                  'post': ('/post', '💌пост'),
                  }

MAIN_COMMANDS = {'start': ('/start', '☀️старт'),
                 'menu': ('/menu', '⌨️меню'),
                 'help': ('/help', '🙏помощь'),
                 'admin_panel': ('/admin_panel', '👽админ панель'),
                 'back': ('/back', '🔙Назад')
                 }

MENU_COMMANDS = {'on': ('/on', '🚀вкл. ленту'),
                 'off': ('/off', '🛑выкл. ленту'),
                 'add': ('/add', '➕добавить подписку'),
                 'delete': ('/delete', '➖удалить подписку'),
                 'subscriptions': ('/subscriptions', '📋твои подписки'),
                 'wish': ('/wish', '💬оставить пожелание')
                 }

TEMP_COMMAND = {'end': ('/end', '🔚Закончить'),
                'yes': ('/уes', '👍Да'),
                'no': ('/no', '👎Нет'),
                }

ALL_COMMANDS = _get_all_commands()
