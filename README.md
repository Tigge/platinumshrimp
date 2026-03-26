platinumshrimp
=================================================

[![Build status](https://github.com/Tigge/platinumshrimp/workflows/Build/badge.svg)](https://github.com/Tigge/platinumshrimp/actions?query=workflow%3ABuild)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Packaging: poetry](https://img.shields.io/badge/packaging-poetry-%23299BD7)](https://python-poetry.org/)

**platinumshrimp** is a modern, multiprocess IRC bot written in Python 3. It
is designed for stability, extensibility, and ease of use, featuring a plugin
architecture where each plugin runs in its own isolated process.

Key Features
------------

- **Multiprocessing Architecture:** Each plugin runs in a separate process. If
  a plugin crashes, it won't affect the main bot or other plugins.
- **Asynchronous & Fast:** Uses `asyncio` for the main bot loop and
  `ZeroMQ (ZMQ)` for high-performance IPC between the bot and its plugins.
- **Integrated CLI:** Manage the bot in real-time through a built-in
  command-line interface. Load/unload plugins, join channels, send messages,
  and reload settings without restarting the bot.
- **Multi-Server Support:** Connect to multiple IRC networks simultaneously.
- **Secure Connections:** Built-in SSL/TLS support for encrypted communication.
- **Extensible Plugins:** Supports plugins written in multiple languages
  (through ZMQ).

Quick Start
-----------

### Get the code

```bash
git clone https://github.com/Tigge/platinumshrimp.git
cd platinumshrimp
```

### Install dependencies

**Debian/Ubuntu:**
```bash
sudo apt-get install python3-pip libzmq3-dev
```

**Fedora:**
```bash
sudo dnf install python3-devel python3-pip zeromq-devel
```

### Install Poetry & Environment

```bash
curl -sSL https://install.python-poetry.org/ | python -
poetry update
```

### Run the Bot

```bash
poetry run python bot.py
```

Configuration
-------------

The bot is configured via `settings.json`. If the file does not exist, a
default one will be created on the first run.

### Example `settings.json`

```json
{
  "nickname": "platinumshrimp",
  "realname": "Platinumshrimp",
  "username": "shrimp",
  "servers": {
    "libera": {
      "host": "irc.libera.chat",
      "port": 6697,
      "ssl": true
    }
  },
  "plugins": {
    "autojoiner": {
      "libera": ["#platinumshrimp"]
    },
    "titlegiver": {
      "yt-key": "your-youtube-api-key"
    },
    "shrimpgemini": {
      "key": "your-gemini-api-key",
      "trigger": "shrimp:"
    }
  }
}
```

### Configuration Fields

- **nickname/realname/username**: The bot's identity on IRC.
- **servers**: A map of server configurations. Each server needs a `host` and
  `port`. Set `ssl: true` for secure connections.
- **plugins**: A map of plugins to load and their specific settings.

Key Plugins
-----------

- **autojoiner**: Automatically joins channels on connect and remembers channels
  the bot is invited to.
- **titlegiver**: Fetches and displays the title of URLs posted in chat.
  Includes rich YouTube metadata support if an API key is provided.
- **feedretriever**: Tracks various feeds (like RSS, Reddit, CNN News, &c) to
  automatically get updates on new posts.
- **shrimpgemini**: Integration with Google Gemini for interactive AI chat.
  Supports custom prompts, conversation history and context.
- **youtubesummarizer**: Summarizes YouTube videos using AI based on their
  transcripts.
- **sqllogger**: Log events to an sql database.  Includes an extensive
  viewer to search through and find messages and events based on different
  filters.
- **wikilooker**: Search and display summaries from Wikipedia in any language.

Management CLI
--------------

When running the bot, you have access to a CLI to control it:

- `list_plugins`: Show currently loaded plugins.
- `load_plugin <name>` / `unload_plugin <name>`: Manage plugins dynamically.
- `join_channel <server> <channel>`: Join a new channel.
- `send_message <server> <channel> <message>`: Send a message as the bot.
- `reload_settings`: Reload `settings.json` without restarting.

Development
-----------

### Run Unit Tests

```bash
poetry run python -m unittest discover -v
```

### Linting

```bash
black .
```

### Clean up IPC files

Clean up temporary IPC sockets, bytecode, logs and caches:

```bash
rm -Rf `find . -name "*.pyc" -or -name __pycache__ -or -name _trial_temp -or -name "*.log" -or -name "ipc_plugin_*"`
```

License
-------

See [LICENCE.md](LICENCE.md) for details.
