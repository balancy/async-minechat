import asyncio

HOST = ('minechat.dvmn.org', 5000)


async def listen_chat():
    reader, writer = await asyncio.open_connection(*HOST)

    while not reader.at_eof():
        data = await reader.readline()
        print(data.decode().rstrip())

    writer.close()


if __name__ == '__main__':
    asyncio.run(listen_chat())
