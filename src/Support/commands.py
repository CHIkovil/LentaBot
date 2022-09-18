def _get_all_commands():
    result = []
    all_commands_values = list(ADMIN_COMMANDS.values()) + list(MAIN_COMMANDS.values()) + list(MENU_COMMANDS.values())
    for commands in all_commands_values:
        result += list(commands)

    return set(result)


ADMIN_COMMANDS = {'add_keyword': ('/add_keyword', '➕добавить ключ. слово'),
                  'delete_keyword': ('/delete_keyword', '➖удалить ключ. слово'),
                  'keywords': ('/keywords', '📂ключевые слова'),
                  'statistics': ('/statistics', '📈статистика'),
                  'reset_wish': ('/reset_wish', '📩сбор пожеланий'),
                  'post': ('/post', '💌пост'),
                  }

MAIN_COMMANDS = {'start': ('/start', '☀️старт'),
                 'menu': ('/menu', '⌨️меню'),
                 'help': ('/help', '🙏помощь'),
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
