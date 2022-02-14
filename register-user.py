import argparse
import asyncio
import json

from environs import Env

async def register_user(host: str, port: int, username: str):
    reader, writer = await asyncio.open_connection(host, port)

    await reader.readline()

    writer.write(f'random\n'.encode())
    await writer.drain()

    for _ in range(2):
        await reader.readline()

    writer.write(f'{username}\n\n'.encode())
    await writer.drain()

    received_message = await reader.readline()
    username_with_token = json.loads(received_message.decode())

    with open('token.json', 'w') as outfile:
        json.dump(username_with_token, outfile)

    writer.close()
    await writer.wait_closed()


if __name__ == '__main__':
    env = Env()
    env.read_env()

    parser = argparse.ArgumentParser(
        description='Define optional arguments like host and port.'
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
    args = parser.parse_args()

    username = input('Enter username: ')

    asyncio.run(register_user(args.host, args.port, username))
