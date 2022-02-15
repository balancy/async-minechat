# Async chat interaction

The app represents a client which connects to Minechat (chat dedicated to Minecraft game) and could interact with it. A user via client could authenticate himself if he's already registered or register a new account, and send messages to the chat.

## Install

Clone the repository

```bash
git clone https://github.com/balancy/async-minechat
```

Go inside the cloned repository, create the virtual environment and activate it.

```bash
cd async-chat
```

```bash
python -m venv .venv
```

```bash
. .venv
```

## RUN

There are two scripts:

- `listen-to-chat.py` - for listening to the chat.

- `interact-with-chat.py` - for interacting with the chat.

### Environmant variables

You can use environment variables for settings. It's not mandatory. You has the possibility to provide those settings via command line arguments or use default values. To set environment variables, create `.env` file and define environment variables.

```bash
nano .env
```

- `HOST` - hostname of the chat. By default it's `minechat.dvmn.org`.
- `LISTEN_PORT` - port of the chat to listen to messages from. By default it's `5000`.
- `WRITE_PORT` - port of the chat to write messages to. By default it's `5050`.
- `HISTORY` - name of the file to save chat history. By default it's `minechat.history`.
- `TOKEN` - authentication token to join the chat.
- `USERNAME` - name of the user you want to be registered with. By default it's `funky`.

### Command line arguments

You could also provide command line arguments for both scripts.

Command example for `listen-to-chat.py`:

```bash
python listen-to-chat.py --host <hostname> --port <port> --history <history-file>
```

- `hostname` - hostname of the chat. By default it's `minechat.dvmn.org`. This argument is optional.
- `port` - port of the chat to listen to messages from. By default it's `5000`. This argument is optional.
- `history-file` - name of the file to save chat history. By default it's `minechat.history`. This argument is optional.

Command example for `interact-with-chat.py`:

```bash
python interact-with-chat.py --host <hostname> --port <port> --token <token> --username <username> --message <message>
```

- `message` - message to send to the chat. This argument is **required**.
- `hostname` - hostname of the chat. By default it's `minechat.dvmn.org`. This argument is optional.
- `port` - port of the chat to write messages to. By default it's `5050`. This argument is optional.
- `token` - authentication token to join the chat. This argument is optional.
- `username` - name of the user you want to be registered with. By default it's `funky`.

Normal use flow of scripts:
1. You run `listen-to-chat.py` to read the chat.
2. When you need to send message, you run `interact-with-chat.py`, providing a message and some optional arguments if needed.