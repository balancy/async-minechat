import asyncio
from datetime import datetime
import json
import logging
from socket import gaierror
import sys
from time import sleep, time

from anyio import ExceptionGroup, create_task_group
from async_timeout import timeout
from environs import Env
from tkinter import messagebox

from gui import (
    draw,
    NicknameReceived,
    ReadingConnectionState,
    SendingConnectionState,
    TkAppClosed,
)
from helpers.handle_arguments import initalize_arguments
from helpers.handle_files import save_history_to_file, upload_history_from_file
from helpers.classes import InvalidToken, Queues, ReconnectsCount


DOWNTIME = 60
MAX_RECONNECTS_AMOUNT = 3
TIMEOUT_LIMIT = 3


async def authenticate_user(connection, auth_token, watchdog_queue):
    reader, writer = connection

    await reader.readline()
    watchdog_queue.put_nowait('Connection is alive. Prompt before auth')

    writer.write(f'{auth_token}\n'.encode())
    await writer.drain()

    received_message = (await reader.readline()).decode()

    is_token_valid = json.loads(received_message.rstrip()) is not None

    if not is_token_valid:
        raise InvalidToken

    watchdog_queue.put_nowait('Connection is alive. Authorization done')
    username = json.loads(received_message).get('nickname')
    watchdog_queue.put_nowait(f'User \'{username}\' entered the chat.')

    await reader.readline()

    return username


async def handle_connection(reading_connection, sending_connection, queues):
    reconnects_count = ReconnectsCount(MAX_RECONNECTS_AMOUNT, DOWNTIME)

    while True:
        try:
            async with create_task_group() as tg:
                tg.start_soon(read_messages, reading_connection, queues)
                tg.start_soon(send_messages, sending_connection, queues)
                tg.start_soon(
                    watch_for_connection,
                    queues.watchdog_queue,
                    reconnects_count,
                )
        except ConnectionError:
            reconnects_count.increment()
            for con_state in [ReadingConnectionState, SendingConnectionState]:
                queues.status_queue.put_nowait(con_state.CLOSED)

            if reconnects_count.overpassed_max_reconnects_amount():
                tg.cancel_scope.cancel()
                time_to_sleep = reconnects_count.get_idle_time()
                logger.debug(
                    f'[{int(time())}] Waiting for {time_to_sleep} seconds.'
                )
                sleep(time_to_sleep)


async def main(env):
    args = await initalize_arguments(env)
    queues = Queues(*[asyncio.Queue() for _ in range(5)])

    await upload_history_from_file(args.history, queues.messages_queue)

    for con_state in [ReadingConnectionState, SendingConnectionState]:
        queues.status_queue.put_nowait(con_state.INITIATED)

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
            queues.watchdog_queue,
        )
        queues.status_queue.put_nowait(NicknameReceived(username))
    except InvalidToken:
        messagebox.showinfo(
            'Invalid token', 'Invalid token. Server didn\'t recognize it.'
        )
        sys.exit(1)

    async with create_task_group() as tg:
        tg.start_soon(
            handle_connection,
            reading_connection,
            sending_connection,
            queues,
        )
        tg.start_soon(save_history_to_file, args.history, queues.saving_queue)
        tg.start_soon(
            draw,
            queues.messages_queue,
            queues.sending_queue,
            queues.status_queue,
        )


async def read_messages(connection, queues):
    reader, _ = connection

    while not reader.at_eof():
        chat_message = await reader.readline()

        queues.status_queue.put_nowait(ReadingConnectionState.ESTABLISHED)
        queues.watchdog_queue.put_nowait(
            'Connection is alive. New message in chat.'
        )

        current_time = datetime.now().strftime('[%m.%d.%Y %H:%M]')
        formatted_message = f'{current_time} {chat_message.decode().rstrip()}'

        for queue in [queues.messages_queue, queues.saving_queue]:
            queue.put_nowait(formatted_message)


async def send_messages(connection, queues):
    _, writer = connection
    queues.status_queue.put_nowait(SendingConnectionState.INITIATED)

    while True:
        message = await queues.sending_queue.get()
        queues.status_queue.put_nowait(SendingConnectionState.ESTABLISHED)
        queues.watchdog_queue.put_nowait('Connection is alive. Message sent.')

        writer.write(f'{message}\n\n'.encode())
        await writer.drain()


async def watch_for_connection(watchdog_queue, reconnects_count):
    while True:
        timestamp = f'[{int(time())}]'

        try:
            async with timeout(TIMEOUT_LIMIT):
                message = await watchdog_queue.get()
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

    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(main(env))
    except (KeyboardInterrupt, ExceptionGroup, TkAppClosed):
        sys.exit(0)
