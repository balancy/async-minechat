import argparse
import json
import os

from environs import Env

TOKEN_FILE = 'token.json'


def get_token_from_file() -> None:
    if not os.path.exists(TOKEN_FILE):
        return

    with open(TOKEN_FILE, 'r') as infile:
        username_with_token = json.load(infile)
        return username_with_token.get('account_hash')


def read_env_variables(env: Env) -> tuple:
    if not (token := get_token_from_file()):
        token = env.str('TOKEN', 'random_token')

    host = env.str('HOST', 'minechat.dvmn.org')
    port = env.int('WRITE_PORT', 5050)
    username = env.str('USERNAME', 'funky')

    return host, port, token, username


def read_cli_arguments(
    default_host: str,
    default_port: int,
    default_token: str,
    default_username: str
) -> argparse.Namespace:
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
        default=default_host,
        help='Chat host',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=default_port,
        help='Chat port to write to',
    )
    parser.add_argument(
        '--token',
        type=str,
        default=default_token,
        help='Token to authenticate the user',
    )
    parser.add_argument(
        '--username',
        type=str,
        default=default_username,
        help='Username to use in the chat',
    )
    args = parser.parse_args()

    return (
        args.host,
        args.port,
        args.token,
        args.username.rstrip(),
        args.message.rstrip(),
    )


class InvalidToken(Exception):
    pass