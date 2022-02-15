import argparse
import asyncio
from datetime import datetime

import aiofiles
from environs import Env

async def listen_chat(host: str, port: int, history_file: str):
    reader, writer = await asyncio.open_connection(host, port)

    async with aiofiles.open(history_file, 'a') as file:
        while not reader.at_eof():
            chat_message = await reader.readline()

            current_time = datetime.now().strftime('[%m.%d.%Y %H:%M]')
            logged_message = f'{current_time} {chat_message.decode()}'

            await file.write(logged_message)
            print(logged_message.rstrip())

    writer.close()
    await writer.wait_closed()


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

    asyncio.run(listen_chat(args.host, args.port, args.history))
