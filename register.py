import asyncio
import json
import sys
import tkinter

from anyio import create_task_group
from environs import Env

from gui import TkAppClosed, update_tk
from helpers.handle_arguments import initalize_arguments
from helpers.handle_files import save_token_to_file


async def register_user(host, port, username):
    reader, writer = await asyncio.open_connection(host, port)

    await reader.readline()
    writer.write('register\n'.encode())
    await writer.drain()
    await reader.readline()
    await reader.readline()
    writer.write(f'{username}\n\n'.encode())
    await writer.drain()

    received_message = await reader.readline()
    username_with_token = json.loads(received_message.decode())
    username = username_with_token.get('nickname')
    await save_token_to_file(username_with_token)

    await reader.readline()
    writer.close()
    await writer.wait_closed()

    return username


async def handle_new_username_received(queue, args, label):
    while True:
        preferred_username = await queue.get()
        username = await register_user(*args, preferred_username)
        label['text'] = f'User <{username}> registered'


def handle_button_click(input, queue):
    username = input.get()
    queue.put_nowait(username)
    input.delete(0, tkinter.END)


def get_root_and_label_elms_from_drawn_form(queue):
    root = tkinter.Tk()
    root.title('Registration')
    root.geometry('250x150')

    label = tkinter.Label(root, text='Enter preferred username to register:')
    label.place(x=10, y=10)

    input_frame = tkinter.Frame(root)
    input_frame.place(x=10, y=40)

    input_field = tkinter.Entry(input_frame)
    input_field.pack(side='left', fill=tkinter.X, expand=True)

    send_button = tkinter.Button(input_frame)
    send_button['text'] = 'Register'
    send_button['command'] = lambda: handle_button_click(input_field, queue)
    send_button.pack(side='right')

    succes_reg_label = tkinter.Label(root, text='')
    succes_reg_label.place(x=10, y=75)

    return root, succes_reg_label


async def main(env):
    args = await initalize_arguments(env)
    args = args.host, args.wport

    queue = asyncio.Queue()
    root_elm, label = get_root_and_label_elms_from_drawn_form(queue)

    async with create_task_group() as tg:
        tg.start_soon(update_tk, root_elm)
        tg.start_soon(handle_new_username_received, queue, args, label)


if __name__ == '__main__':
    env = Env()
    env.read_env()

    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(main(env))
    except (KeyboardInterrupt, TkAppClosed):
        sys.exit(0)
