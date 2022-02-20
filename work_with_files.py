import json
import os

from aiofile import AIOFile

TOKEN_FILE = 'token.json'


async def get_token_from_file():
    if not os.path.exists(TOKEN_FILE):
        return

    async with AIOFile(TOKEN_FILE, 'r') as file:
        contents = await file.read()
        username_with_token = json.loads(contents)
        return username_with_token.get('account_hash')


async def save_history_to_file(filepath, queue):
    async with AIOFile(filepath, 'a') as outfile:
        while True:
            message = await queue.get()
            await outfile.write(f'{message}\n')


async def upload_history_to_chat(filepath, queue):
    async with AIOFile(filepath, 'r') as file:
        contents = await file.read()
        queue.put_nowait(contents.rstrip())
