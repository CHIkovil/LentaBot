from Support import *


class ErrorHandler(logging.Handler):
    def __init__(self, send_func: Bot.send_message, error_channel_id):
        logging.Handler.__init__(self)
        self.send_func = send_func
        self.error_channel_id = error_channel_id

    def emit(self, record: LogRecord) -> None:
        error_time = datetime.datetime.utcfromtimestamp(record.created).strftime("%m/%d/%Y, %H:%M:%S")
        project_name = record.name
        file_name = record.filename
        lineno = record.lineno
        func_name = record.funcName
        error_name = record.args[0] if record.args else 'None'
        msg = record.msg

        error_msg = f'Time: {error_time}\n' \
                    f'Project: {project_name}\n' \
                    f'File: {file_name}\n' \
                    f'Line: {lineno}\n' \
                    f'Func: {func_name}\n' \
                    f'Error: {error_name}\n' \
                    f'Msg: {msg}\n'

        asyncio.ensure_future(self.send_func(self.error_channel_id, error_msg))
