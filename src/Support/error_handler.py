from . import *


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
        msg = record.msg

        error_msg = f'Time: {error_time}\n' \
                    f'Project: {project_name}\n' \
                    f'File: {file_name}\n' \
                    f'Line: {lineno}\n' \
                    f'Msg: {msg}'
        asyncio.ensure_future(self.send_func(self.error_channel_id, error_msg))
