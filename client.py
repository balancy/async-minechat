import argparse
import asyncio
from datetime import datetime
import json
import logging
from socket import gaierror
import sys
from time import sleep, time

from anyio import create_task_group

from async_timeout import timeout
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
    upload_history_from_file,
)


DOWNTIME = 5
MAX_RECONNECTS_AMOUNT = 3
TIMEOUT_LIMIT = 1


class InvalidToken(Exception):
    pass


class ReconnectsCount:
    def __init__(self, max_reconnects, downtime):
        self.count = 0
        self.max_reconnects = max_reconnects
        self.downtime = downtime

    def reset(self):
        self.count = 0

    def increment(self):
        self.count += 1

    def overpassed_max_reconnects_amount(self):
        return self.count >= self.max_reconnects

    def get_idle_time(self):
        return (self.count - self.max_reconnects) * self.downtime


async def authenticate_user(
    connection: tuple[asyncio.StreamReader, asyncio.StreamWriter],
    auth_token: str,
    watchdog_queue: asyncio.queues.Queue,
) -> str:
    reader, writer = connection

    received_message = await reader.readline()
    watchdog_queue.put_nowait('Connection is alive. Prompt before auth')

    writer.write(f'{auth_token}\n'.encode())
    await writer.drain()

    received_message = await reader.readline()

    is_token_valid = json.loads(received_message.decode().rstrip()) is not None

    if not is_token_valid:
        messagebox.showinfo(
            'Invalid token', 'Check it, server didn\'t recognize it.'
        )
        raise InvalidToken

    watchdog_queue.put_nowait('Connection is alive. Authorization done')
    username_with_token = json.loads(received_message.decode())
    username = username_with_token.get('nickname')

    received_message = await reader.readline()

    return username


async def handle_connection(
    reading_connection,
    sending_connection,
    messages_queue,
    saving_queue,
    watchdog_queue,
    status_queue,
):
    reconnects_count = ReconnectsCount(MAX_RECONNECTS_AMOUNT, DOWNTIME)

    while True:
        try:
            async with create_task_group() as tg:
                tg.start_soon(
                    read_messages,
                    reading_connection,
                    messages_queue,
                    saving_queue,
                    watchdog_queue,
                    status_queue,
                )
                tg.start_soon(
                    send_messages,
                    sending_connection,
                    sending_queue,
                    watchdog_queue,
                    status_queue,
                )
                tg.start_soon(
                    watch_for_connection, watchdog_queue, reconnects_count
                )
        except ConnectionError:
            reconnects_count.increment()
            status_queue.put_nowait(ReadingConnectionState.CLOSED)
            status_queue.put_nowait(SendingConnectionState.CLOSED)

            if reconnects_count.overpassed_max_reconnects_amount():
                tg.cancel_scope.cancel()
                time_to_sleep = reconnects_count.get_idle_time()
                logger.debug(
                    f'[{int(time())}] Waiting for {time_to_sleep} seconds.'
                )
                sleep(time_to_sleep)


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
    status_queue: asyncio.queues.Queue,
    watchdog_queue: asyncio.queues.Queue,
):
    args = await initalize_arguments(env)
    await upload_history_from_file(args.history, messages_queue)

    status_queue.put_nowait(ReadingConnectionState.INITIATED)
    status_queue.put_nowait(SendingConnectionState.INITIATED)

    try:
        reading_connection = await asyncio.open_connection(
            args.host, args.rport
        )
    except gaierror:
        logger.debug(f'Could not resolve {args.host}')
        sys.exit(1)

    sending_connection = await asyncio.open_connection(args.host, args.wport)

    try:
        username = await authenticate_user(
            sending_connection,
            args.token,
            watchdog_queue,
        )
        status_queue.put_nowait(NicknameReceived(username))
    except InvalidToken:
        sys.exit(1)

    async with create_task_group() as tg:
        tg.start_soon(
            handle_connection,
            reading_connection,
            sending_connection,
            messages_queue,
            saving_queue,
            watchdog_queue,
            status_queue,
        )
        tg.start_soon(save_history_to_file, args.history, saving_queue)
        tg.start_soon(draw, messages_queue, sending_queue, status_queue)


async def read_messages(
    connection: tuple[asyncio.StreamReader, asyncio.StreamWriter],
    messages_queue: asyncio.queues.Queue,
    saving_queue: asyncio.queues.Queue,
    watchdog_queue: asyncio.queues.Queue,
    status_queue: asyncio.queues.Queue,
):
    reader, _ = connection

    while not reader.at_eof():
        chat_message = await reader.readline()

        status_queue.put_nowait(ReadingConnectionState.ESTABLISHED)
        watchdog_queue.put_nowait('Connection is alive. New message in chat.')

        current_time = datetime.now().strftime('[%m.%d.%Y %H:%M]')
        formatted_message = f'{current_time} {chat_message.decode().rstrip()}'

        for queue in [messages_queue, saving_queue]:
            queue.put_nowait(formatted_message)


async def send_messages(
    connection: tuple[asyncio.StreamReader, asyncio.StreamWriter],
    sending_queue: asyncio.queues.Queue,
    watchdog_queue: asyncio.queues.Queue,
    status_queue: asyncio.queues.Queue,
):
    _, writer = connection
    status_queue.put_nowait(SendingConnectionState.INITIATED)

    while True:
        message = await sending_queue.get()
        status_queue.put_nowait(SendingConnectionState.ESTABLISHED)
        watchdog_queue.put_nowait('Connection is alive. Message sent.')

        writer.write(f'{message}\n\n'.encode())
        await writer.drain()


async def watch_for_connection(queue, reconnects_count):
    while True:
        timestamp = f'[{int(time())}]'

        try:
            async with timeout(TIMEOUT_LIMIT):
                message = await queue.get()
            reconnects_count.reset()
            logger.debug(f'{timestamp} {message}')

        except asyncio.exceptions.TimeoutError:
            logger.debug(f'{timestamp} {TIMEOUT_LIMIT} timeout is elapsed.')
            raise ConnectionError


if __name__ == '__main__':
    logging.basicConfig(
        format=u'%(levelname)s:%(message)s',
        level=logging.DEBUG,
    )
    logger = logging.getLogger(__name__)

    env = Env()
    env.read_env()

    messages_queue = asyncio.Queue()
    saving_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_queue = asyncio.Queue()
    watchdog_queue = asyncio.Queue()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        main(
            env,
            messages_queue,
            saving_queue,
            sending_queue,
            status_queue,
            watchdog_queue,
        )
    )
