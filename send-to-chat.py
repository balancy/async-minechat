import argparse
import asyncio
import json
import logging
import os

from environs import Env

TOKEN_FILE = 'token.json'

async def send_to_chat(host: str, port: int, token: str, message: str):
    reader, writer = await asyncio.open_connection(host, port)

    received_message = await reader.readline()
    logger.debug(f'sender:{received_message.decode().rstrip()}')

    writer.write(f'{token}\n'.encode())
    logger.debug(f'receiver:{token}')
    await writer.drain()

    received_message = await reader.readline()
    is_token_valid = json.loads(received_message.decode().rstrip()) is not None

    if not is_token_valid:
        logger.debug(f'sender:Invalid token. Check it or register a new user.')
    else:
        received_message = await reader.readline()
        logger.debug(f'sender:{received_message.decode().rstrip()}')

        writer.write(f'{message}\n\n'.encode())
        logger.debug(f'receiver:{message}')
        await writer.drain()

    writer.close()
    logger.debug('receiver:close connection')
    await writer.wait_closed()


def get_token_from_file():
    if not os.path.exists(TOKEN_FILE):
        return

    with open(TOKEN_FILE, 'r') as infile:
        username_with_token = json.load(infile)
        return username_with_token.get('account_hash')


if __name__ == '__main__':
    logging.basicConfig(
        format = u'%(levelname)s:%(message)s',
        level = logging.DEBUG,
    )
    logger = logging.getLogger(__name__)

    env = Env()
    env.read_env()

    parser = argparse.ArgumentParser(
        description='Define optional arguments like host, port, token.'
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
        default=env.int('WRITE_PORT', 5050),
        help='Chat port to write to',
    )
    parser.add_argument(
        '--token',
        type=str,
        default=env.str('TOKEN'),
        help='Token to authenticate the user',
    )
    args = parser.parse_args()

    message = 'Some message'

    if not (token := get_token_from_file()):
        token = args.token

    asyncio.run(send_to_chat(args.host, args.port, token, message))
