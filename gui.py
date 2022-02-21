import asyncio
from enum import Enum
import sys
import tkinter
from tkinter.scrolledtext import ScrolledText

from anyio import create_task_group


class TkAppClosed(Exception):
    pass


class ReadingConnectionState(Enum):
    INITIATED = 'устанавливаем соединение'
    ESTABLISHED = 'соединение установлено'
    CLOSED = 'соединение закрыто'

    def __str__(self):
        return str(self.value)


class SendingConnectionState(Enum):
    INITIATED = 'устанавливаем соединение'
    ESTABLISHED = 'соединение установлено'
    CLOSED = 'соединение закрыто'

    def __str__(self):
        return str(self.value)


class NicknameReceived:
    def __init__(self, nickname):
        self.nickname = nickname


def process_new_message(input_field, sending_queue):
    text = input_field.get()
    sending_queue.put_nowait(text)
    input_field.delete(0, tkinter.END)


async def update_tk(root_frame, interval=1 / 120):
    while True:
        try:
            root_frame.update()
        except tkinter.TclError:
            # if application has been destroyed/closed
            sys.exit(0)
        await asyncio.sleep(interval)


async def update_conversation_history(panel, messages_queue):
    while True:
        msg = await messages_queue.get()

        panel['state'] = 'normal'
        if panel.index('end-1c') != '1.0':
            panel.insert('end', '\n')
        panel.insert('end', msg)
        # TODO сделать промотку умной, чтобы не мешала просматривать историю сообщений
        # ScrolledText.frame
        # ScrolledText.vbar
        panel.yview(tkinter.END)
        panel['state'] = 'disabled'


async def update_status_panel(status_labels, status_updates_queue):
    nickname_label, read_label, write_label = status_labels

    read_label['text'] = f'Чтение: нет соединения'
    write_label['text'] = f'Отправка: нет соединения'
    nickname_label['text'] = f'Имя пользователя: неизвестно'

    while True:
        msg = await status_updates_queue.get()
        if isinstance(msg, ReadingConnectionState):
            read_label['text'] = f'Чтение: {msg}'

        if isinstance(msg, SendingConnectionState):
            write_label['text'] = f'Отправка: {msg}'

        if isinstance(msg, NicknameReceived):
            nickname_label['text'] = f'Имя пользователя: {msg.nickname}'


def create_status_panel(root_frame):
    status_frame = tkinter.Frame(root_frame)
    status_frame.pack(side="bottom", fill=tkinter.X)

    connections_frame = tkinter.Frame(status_frame)
    connections_frame.pack(side="left")

    nickname_label = tkinter.Label(
        connections_frame, height=1, fg='grey', font='arial 10', anchor='w'
    )
    nickname_label.pack(side="top", fill=tkinter.X)

    status_read_label = tkinter.Label(
        connections_frame, height=1, fg='grey', font='arial 10', anchor='w'
    )
    status_read_label.pack(side="top", fill=tkinter.X)

    status_write_label = tkinter.Label(
        connections_frame, height=1, fg='grey', font='arial 10', anchor='w'
    )
    status_write_label.pack(side="top", fill=tkinter.X)

    return (nickname_label, status_read_label, status_write_label)


async def draw(messages_queue, sending_queue, status_updates_queue):
    root = tkinter.Tk()

    root.title('Minechat')

    root_frame = tkinter.Frame()
    root_frame.pack(fill="both", expand=True)

    status_labels = create_status_panel(root_frame)

    input_frame = tkinter.Frame(root_frame)
    input_frame.pack(side="bottom", fill=tkinter.X)

    input_field = tkinter.Entry(input_frame)
    input_field.pack(side="left", fill=tkinter.X, expand=True)

    input_field.bind(
        "<Return>",
        lambda event: process_new_message(input_field, sending_queue),
    )

    send_button = tkinter.Button(input_frame)
    send_button["text"] = "Отправить"
    send_button["command"] = lambda: process_new_message(
        input_field,
        sending_queue,
    )
    send_button.pack(side="left")

    conversation_panel = ScrolledText(root_frame, wrap='none')
    conversation_panel.pack(side="top", fill="both", expand=True)

    async with create_task_group() as tg:
        tg.start_soon(update_tk, root_frame)
        tg.start_soon(
            update_conversation_history, conversation_panel, messages_queue
        )
        tg.start_soon(
            update_status_panel, status_labels, status_updates_queue
        )
