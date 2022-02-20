import argparse
import asyncio
import json
from datetime import datetime

from environs import Env

import gui
from work_with_files import (
    get_token_from_file,
    save_history_to_file,
    upload_history_to_chat,
)


class InvalidToken(Exception):
    pass


async def authenticate_user(
    reader: asyncio.streams.StreamReader,
    writer: asyncio.streams.StreamWriter,
    auth_token: str,
):
    received_message = await reader.readline()

    writer.write(f'{auth_token}\n'.encode())
    await writer.drain()

    received_message = await reader.readline()
    # username_with_token = json.loads(received_message.decode())
    # username = username_with_token.get('nickname')
    # print(f'Выполнена авторизация. Пользователь {username}')

    is_token_valid = json.loads(received_message.decode().rstrip()) is not None

    if not is_token_valid:
        raise InvalidToken

    received_message = await reader.readline()


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
    sending_queue: asyncio.queues.Queue,
    status_updates_queue: asyncio.queues.Queue,
    saving_queue: asyncio.queues.Queue,
):
    args = await initalize_arguments(env)
    await upload_history_to_chat(args.history, messages_queue)

    reader, writer = await asyncio.open_connection(args.host, args.wport)
    await authenticate_user(reader, writer, args.token)

    await asyncio.gather(
        read_messages(args.host, args.rport, messages_queue, saving_queue),
        save_history_to_file(args.history, saving_queue),
        send_messages(writer, sending_queue),
        gui.draw(messages_queue, sending_queue, status_updates_queue),
    )


async def read_messages(
    host: str,
    port: int,
    messages_queue: asyncio.queues.Queue,
    saving_queue: asyncio.queues.Queue,
):
    reader, _ = await asyncio.open_connection(host, port)

    while not reader.at_eof():
        chat_message = await reader.readline()

        current_time = datetime.now().strftime('[%m.%d.%Y %H:%M]')
        formatted_message = f'{current_time} {chat_message.decode().rstrip()}'

        for queue in [messages_queue, saving_queue]:
            queue.put_nowait(formatted_message)


async def send_messages(
    writer: asyncio.streams.StreamWriter,
    queue: asyncio.queues.Queue,
):
    while True:
        message = await queue.get()
        writer.write(f'{message}\n\n'.encode())
        await writer.drain()


if __name__ == '__main__':
    env = Env()
    env.read_env()

    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    saving_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        main(
            env,
            messages_queue,
            sending_queue,
            status_updates_queue,
            saving_queue,
        )
    )
