import asyncio
from datetime import datetime

import aiofiles

HOST = ('minechat.dvmn.org', 5000)


async def listen_chat():
    reader, writer = await asyncio.open_connection(*HOST)

    async with aiofiles.open('chat_history.txt', 'a') as file:
        while not reader.at_eof():
            data = await reader.readline()
            current_time = datetime.now().strftime('[%m.%d.%Y %H:%M]')
            chat_message = data.decode()
            logged_message = f'{current_time} {chat_message}'
            await file.write(logged_message)
            print(logged_message.rstrip())

    writer.close()


if __name__ == '__main__':
    asyncio.run(listen_chat())
