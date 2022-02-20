import argparse
import asyncio
from datetime import datetime
import json
import logging
import sys
from time import time

from environs import Env
from tkinter import messagebox

from gui import (
    draw,
    NicknameReceived,
    ReadingConnectionState,
    SendingConnectionState,
)
from work_with_files import (
    get_token_from_file,
    save_history_to_file,
    upload_history_to_chat,
)


class InvalidToken(Exception):
    pass


async def authenticate_user(
    connection: tuple[asyncio.StreamReader, asyncio.StreamWriter],
    auth_token: str,
) -> str:
    reader, writer = connection

    received_message = await reader.readline()

    writer.write(f'{auth_token}\n'.encode())
    await writer.drain()

    received_message = await reader.readline()

    is_token_valid = json.loads(received_message.decode().rstrip()) is not None

    if not is_token_valid:
        messagebox.showinfo(
            'Invalid token', 'Check it, server didn\'t recognize it.'
        )
        raise InvalidToken

    username_with_token = json.loads(received_message.decode())
    username = username_with_token.get('nickname')

    received_message = await reader.readline()

    return username


async def initalize_arguments(env: Env) -> argparse.Namespace:
    if not (token := await get_token_from_file()):
        token = env.str('TOKEN', 'random_token')

    parser = argparse.ArgumentParser(
        description='Define optional arguments like host, port, history file.'
    )
    parser.add_argument(
        '--host',
        type=str,
        default=env.str('HOST', 'minechat.dvmn.org'),
        help='Chat host',
    )
    parser.add_argument(
        '--rport',
        type=int,
        default=env.int('READING_PORT', 5000),
        help='Chat port to read messages from',
    )
    parser.add_argument(
        '--wport',
        type=int,
        default=env.int('WRITING_PORT', 5050),
        help='Chat port to send messages to',
    )
    parser.add_argument(
        '--token',
        type=str,
        default=token,
        help='Token to authenticate the user',
    )
    parser.add_argument(
        '--history',
        type=str,
        default=env.str('HISTORY', 'minechat.history'),
        help='The file to save chat history to',
    )
    args = parser.parse_args()

    return args


async def main(
    env: Env,
    messages_queue: asyncio.queues.Queue,
    saving_queue: asyncio.queues.Queue,
    sending_queue: asyncio.queues.Queue,
    status_updates_queue: asyncio.queues.Queue,
    watchdog_queue: asyncio.queues.Queue,
):
    args = await initalize_arguments(env)
    await upload_history_to_chat(args.history, messages_queue)

    status_updates_queue.put_nowait(ReadingConnectionState.INITIATED)
    reading_connection = await asyncio.open_connection(args.host, args.rport)
    status_updates_queue.put_nowait(ReadingConnectionState.ESTABLISHED)

    status_updates_queue.put_nowait(SendingConnectionState.INITIATED)
    sending_connection = await asyncio.open_connection(args.host, args.wport)
    status_updates_queue.put_nowait(SendingConnectionState.ESTABLISHED)

    try:
        watchdog_queue.put_nowait('Connection is alive. Prompt before auth')
        username = await authenticate_user(sending_connection, args.token)
    except InvalidToken:
        sys.exit(1)
    else:
        watchdog_queue.put_nowait('Connection is alive. Authorization done')
        status_updates_queue.put_nowait(NicknameReceived(username))

    await asyncio.gather(
        read_messages(
            reading_connection, messages_queue, saving_queue, watchdog_queue
        ),
        save_history_to_file(args.history, saving_queue),
        send_messages(sending_connection, sending_queue, watchdog_queue),
        watch_for_connection(watchdog_queue),
        draw(messages_queue, sending_queue, status_updates_queue),
    )


async def read_messages(
    connection: tuple[asyncio.StreamReader, asyncio.StreamWriter],
    messages_queue: asyncio.queues.Queue,
    saving_queue: asyncio.queues.Queue,
    watchdog_queue: asyncio.queues.Queue,
):
    reader, _ = connection

    while not reader.at_eof():
        chat_message = await reader.readline()
        watchdog_queue.put_nowait('Connection is alive. New message in chat.')

        current_time = datetime.now().strftime('[%m.%d.%Y %H:%M]')
        formatted_message = f'{current_time} {chat_message.decode().rstrip()}'

        for queue in [messages_queue, saving_queue]:
            queue.put_nowait(formatted_message)


async def send_messages(
    connection: tuple[asyncio.StreamReader, asyncio.StreamWriter],
    sending_queue: asyncio.queues.Queue,
    watchdog_queue: asyncio.queues.Queue,
):
    _, writer = connection
    while True:
        message = await sending_queue.get()
        writer.write(f'{message}\n\n'.encode())
        await writer.drain()
        watchdog_queue.put_nowait('Connection is alive. Message sent.')


async def watch_for_connection(queue):
    while True:
        message = await queue.get()
        watchdog_logger.debug(message)


if __name__ == '__main__':
    logging.basicConfig(
        format=u'%(levelname)s:%(message)s',
        level=logging.DEBUG,
    )
    watchdog_logger = logging.getLogger(__name__)

    env = Env()
    env.read_env()

    messages_queue = asyncio.Queue()
    saving_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    watchdog_queue = asyncio.Queue()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        main(
            env,
            messages_queue,
            saving_queue,
            sending_queue,
            status_updates_queue,
            watchdog_queue,
        )
    )
