import argparse
import asyncio

from environs import Env

async def send_to_chat(host: str, port: int, token: str, message: str):
    reader, writer = await asyncio.open_connection(host, port)

    await reader.readline()

    writer.write(f'{token}\n'.encode())
    await writer.drain()

    for _ in range(2):
        await reader.readline()

    writer.write(f'{message}\n\n'.encode())
    await writer.drain()

    writer.close()
    await writer.wait_closed()


if __name__ == '__main__':
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

    asyncio.run(send_to_chat(args.host, args.port, args.token, message))
