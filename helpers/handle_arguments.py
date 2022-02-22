import argparse

from helpers.handle_files import get_token_from_file


async def initalize_arguments(env):
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
