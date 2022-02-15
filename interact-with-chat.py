import asyncio
import json
import logging

from environs import Env

from helpers import InvalidToken, read_cli_arguments, read_env_variables


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

    with open('token.json', 'w') as outfile:
        json.dump(username_with_token, outfile)

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


if __name__ == '__main__':
    logging.basicConfig(
        format = u'%(levelname)s:%(message)s',
        level = logging.DEBUG,
    )
    logger = logging.getLogger(__name__)

    env = Env()
    env.read_env()

    host, port, token, username, message = read_cli_arguments(
        *read_env_variables(env)
    )

    asyncio.run(send_message_to_chat(host, port, token, username, message))
