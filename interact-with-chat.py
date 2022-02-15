import argparse
import asyncio
import json
import logging
import os

import aiofiles
from environs import Env


TOKEN_FILE = 'token.json'


class InvalidToken(Exception):
    pass


async def get_token_from_file():
    if not os.path.exists(TOKEN_FILE):
        return

    async with aiofiles.open(TOKEN_FILE, 'r') as file:
        contents = await file.read()
        username_with_token = json.loads(contents)
        return username_with_token.get('account_hash')


async def register_user(
    reader: asyncio.streams.StreamReader,
    writer: asyncio.streams.StreamWriter,
    username: str,
):
    received_message = await reader.readline()
    logger.debug(f'sender:{received_message.decode().rstrip()}')

    writer.write(f'{username}\n\n'.encode())
    logger.debug(f'receiver:{username}')
    await writer.drain()

    received_message = await reader.readline()
    logger.debug(f'sender:{received_message.decode().rstrip()}')

    username_with_token = json.loads(received_message.decode())

    async with aiofiles.open(TOKEN_FILE, 'w') as outfile:
        await outfile.write(json.dumps(username_with_token))

    received_message = await reader.readline()
    logger.debug(f'sender:{received_message.decode().rstrip()}')


async def authenticate_user(
    reader: asyncio.streams.StreamReader,
    writer: asyncio.streams.StreamWriter,
    auth_token: str,
):
    writer.write(f'{auth_token}\n'.encode())
    logger.debug(f'receiver:{auth_token}')
    await writer.drain()

    received_message = await reader.readline()
    is_token_valid = json.loads(received_message.decode().rstrip()) is not None

    if not is_token_valid:
        logger.debug(f'sender:Invalid token. Check it or register a new user.')
        raise InvalidToken

    logger.debug(f'sender:{received_message.decode().rstrip()}')
    received_message = await reader.readline()
    logger.debug(f'sender:{received_message.decode().rstrip()}')


async def submit_message(
    writer: asyncio.streams.StreamWriter,
    message: str,
):
    writer.write(f'{message}\n\n'.encode())
    logger.debug(f'receiver:{message}')
    await writer.drain()


async def send_message_to_chat(
    host: str,
    port: int,
    token: str,
    username: str,
    message: str,
):
    reader, writer = await asyncio.open_connection(host, port)

    received_message = await reader.readline()
    logger.debug(f'sender:{received_message.decode().rstrip()}')

    try:
        await authenticate_user(reader, writer, token)
    except InvalidToken:
        await register_user(reader, writer, username)

    await submit_message(writer, message)

    writer.close()
    logger.debug('receiver:close connection')
    await writer.wait_closed()


async def main(env: Env):
    if not (token := await get_token_from_file()):
        token = env.str('TOKEN', 'random_token')

    host = env.str('HOST', 'minechat.dvmn.org')
    port = env.int('WRITE_PORT', 5050)
    username = env.str('USERNAME', 'funky')

    parser = argparse.ArgumentParser(
        description=(
            'Define message to send to the chat and optional arguments like '
            'host, port, token, username if needed.'
        )
    )
    parser.add_argument(
        '--message',
        required=True,
        type=str,
        help='Message to send to the chat',
    )
    parser.add_argument(
        '--host',
        type=str,
        default=host,
        help='Chat host',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=port,
        help='Chat port to write to',
    )
    parser.add_argument(
        '--token',
        type=str,
        default=token,
        help='Token to authenticate the user',
    )
    parser.add_argument(
        '--username',
        type=str,
        default=username,
        help='Username to use in the chat',
    )
    args = parser.parse_args()

    await send_message_to_chat(
        args.host, args.port, args.token, args.username, args.message
    )


if __name__ == '__main__':
    logging.basicConfig(
        format = u'%(levelname)s:%(message)s',
        level = logging.DEBUG,
    )
    logger = logging.getLogger(__name__)

    env = Env()
    env.read_env()

    asyncio.run(main(env))
