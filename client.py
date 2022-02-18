import argparse
import asyncio
from datetime import datetime

from aiofile import AIOFile
from environs import Env

import gui


async def read_messages(host, port, messages_queue, saving_queue):
    reader, _ = await asyncio.open_connection(host, port)

    while not reader.at_eof():
        chat_message = await reader.readline()

        current_time = datetime.now().strftime('[%m.%d.%Y %H:%M]')
        formatted_message = f'{current_time} {chat_message.decode().rstrip()}'

        for queue in [messages_queue, saving_queue]:
            queue.put_nowait(formatted_message)


async def save_messages(filepath, queue):
    async with AIOFile(filepath, 'a') as outfile:
        while True:
            message = await queue.get()
            await outfile.write(f'{message}\n')


async def main(
    messages_queue,
    sending_queue,
    status_updates_queue,
    saving_queue,
    host,
    port,
    history_file,
):
    await asyncio.gather(
        read_messages(host, port, messages_queue, saving_queue),
        save_messages(history_file, saving_queue),
        gui.draw(messages_queue, sending_queue, status_updates_queue),
    )


if __name__ == '__main__':
    env = Env()
    env.read_env()

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
        '--port',
        type=int,
        default=env.int('LISTEN_PORT', 5000),
        help='Chat port to listen to',
    )
    parser.add_argument(
        '--history',
        type=str,
        default=env.str('HISTORY', 'minechat.history'),
        help='The file to save chat history to',
    )
    args = parser.parse_args()

    loop = asyncio.get_event_loop()

    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    saving_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    loop.run_until_complete(
        main(
            messages_queue,
            sending_queue,
            status_updates_queue,
            saving_queue,
            args.host,
            args.port,
            args.history,
        )
    )
