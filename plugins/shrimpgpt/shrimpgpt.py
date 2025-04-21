# This plugin will act as an interactive ChatGPT.  It has the option to save the last few messages,
# but note that each message save will incur a higher token usage when communitcating with OpenAI
# as each message is included in the query to OpenAI.  Also note that messages sent by other
# plugins are currently not being saved.
#
# You can specify a "history_timeout" if you only want the plugin to only remember messages within a
# specified timeframe (like in the past 2 minutes).  This can help filter out old messages that
# might not be related to the current discussion.
#
# Sample setting:
#
# "shrimpgpt": {
#   "key": "your-openai-app-key",
#   "trigger": "chatgpt:", # Only respond to direct questions
#   "channel": "#chatgpt", # Only monitor one specific channel
#   "prompt": "You are an IRC bot. Users will post questions that you answer.",
#   "model": "gpt-4o-mini",
#   "max_tokens": 256,
#   "temperature": 0.2,
#   "max_history": 5, # Let the plugin "remember" the past 5 messages (including responses)
#   "history_timeout": 120 # Clean the chat history if no message is posted within 2 min
# }
#
# The only required parameter is "key".
# If "trigger" is not specified, the plugin will respond to every message.
# If "channel" is not specified, the plugin will respond in every channel.
#
# Commands:
# * !gpt history reset
# Will manually trigger a reset of any previous messages saved.

import logging
import sys
import json
import plugin

from utils import openai

DEFAULT_PROMPT = """You are an IRC bot. Users will post questions that you answer."""
DEFAULT_MODEL = "gpt-4o-mini"


class shrimpgpt(plugin.Plugin):
    def __init__(self):
        plugin.Plugin.__init__(self, "shrimpgpt")

    def started(self, settings):
        s = json.loads(settings)
        self.key = s["key"]
        self.trigger = s["trigger"] if "trigger" in s else ""
        self.channel = s["channel"] if "channel" in s else ""
        prompt = s["prompt"] if "prompt" in s else DEFAULT_PROMPT
        self.system_message = {"role": "system", "content": prompt}
        self.model = s["model"] if "model" in s else DEFAULT_MODEL
        self.max_tokens = int(s["max_tokens"]) if "max_tokens" in s else 256
        self.temperature = int(s["temperature"]) if "temperature" in s else 0.2
        self.history = []
        self.max_history = int(s["max_history"]) if "max_history" in s else 5
        # Max number of seconds of inactivity before cleaning out the message history
        self.history_timeout = int(s["history_timeout"]) if "history_timeout" in s else 120
        self.update_count = 0
        logging.info(
            "ShrimpGPT: Trigger: %s, channel: %s, model: %s, max_tokens: %i, temp: %i",
            self.trigger,
            self.channel,
            self.model,
            self.max_tokens,
            self.temperature,
        )

    def update(self):
        if self.history_timeout < 0:
            return
        self.update_count += 1
        # Reset history if update_count exceeds "update_count"
        if self.update_count >= self.history_timeout:
            logging.info("ShrimpGPT: Resetting history: []")
            self.history = []
            self.update_count = 0

    def reset_history(self, server, channel):
        logging.info("ShrimpGPT: Manual history reset")
        self.history = []
        self.safe_privmsg(server, channel, "Reset!")

    def add_to_history(self, message):
        # Reset history countdown on each new message
        self.update_count = 0
        # if len(h) >= max: h = h[len(h)-max:len(h)]
        while len(self.history) >= self.max_history:
            self.history.pop(0)
        self.history.append(message)
        logging.info(", ".join(str(x) for x in self.history))

    def respond_to_message(self, query, server, channel):
        message = {"role": "user", "content": query}
        self.add_to_history(message)
        messages = [self.system_message] + self.history
        result = openai.get_response(
            self.key, messages, self.model, self.max_tokens, self.temperature
        )
        self.add_to_history({"role": "assistant", "content": result})
        self.safe_privmsg(server, channel, result)

    def on_pubmsg(self, server, user, channel, message):
        if self.channel and channel != self.channel:
            # Message is not in the specified channel
            return
        if message.startswith("!gpt history reset"):
            self._thread(self.reset_history, server, channel)
            return
        username = user.split("!", 1)[0]
        if self.trigger and not message.startswith(self.trigger):
            # With the correct channel but no trigger, we just save the message and do not respond:
            message = {"role": "user", "content": username + ": " + message}
            self.add_to_history(message)
            return
        # Correct channel and trigger, remove the trigger from the message and respond:
        query = message[len(self.trigger) :]
        # Send to plugin thread, as we can't call back with privmsg on the current one:
        self._thread(self.respond_to_message, username + ": " + query, server, channel)


if __name__ == "__main__":
    sys.exit(shrimpgpt.run())
