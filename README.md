# DEADCADE's Matrix Selfbot

![GitHub Repo stars](https://img.shields.io/github/stars/0xDEADCADE/Matrix-Selfbot?label=%E2%98%85&logo=github)

### Installing
- Install the required dependencies (`pip install -r requirements.txt`) [Requires libolm setup](https://github.com/poljar/matrix-nio#installation=)
- Configure settings and credentials in `data/settings.json` and `data/credentials.json`
- Make sure the prefix is set to something that other bots aren't using
- Run the bot (`python3 main.py`) (Starting the bot may take a couple minutes, depending on homeserver speed)

### Commands
`!` is used here as a template prefix. This should be changed due to it being a common prefix and likely used by other bots. It is possible you might accidentally send a command to more than one bot.
- !help: Guide on how to use commands
- !ping: Ping the selfbot, or as the user behind the selfbot, ping a host.
- !roll: Roll a dice
- !xkcd: Get an xkcd and post it in chat
- !shrug: Add `¯\_(ツ)_/¯` to the end of your message
- !emoji_size: Set the default size for custom emojis
- !emoji_list: Get a list of available emojis
#### Ratelimit
Commands activated by users that aren't from the user itself are ratelimited, with a default of 1 command every 10 seconds. Commands activated by the user running the bot are not ratelimited.

### Custom emojis
To use custom emojis, they must be added to the bot. Put any square image in the `data/emojis/` directory. The image has to be square due to the resizing method used. Any image type that can be opened by Pillow, the Python image library, is supported. The name of the file is used as the name of the emoji. For example, the file `kekw.png` can be used as a custom emoji by typing `:kekw:` in chat. The bot does not need to reload for new emojis to be added.

To set a different size for a single emoji, use the syntax `:emoji:size:`. For example, `:kekw:64:` will put a 64x64 version of `kekw.png` in chat

To set the default size for emojis, use the `emoji_size` command.

### Kaomojis/Tags
By default, some kaomojis are added to `data/textreplace.json`. This json file contains a map of text the user types, and text to replace to. The text to be replaced has to be inside semicolons.
- Example config: `{"glasses": "(⌐■_■)"}`
- Example usage: `;glasses;` which gets replaced with `(⌐■_■)`

### Encrypted rooms
By default, the bot's session is not verified. Verification is required to view and participate in encrypted rooms. To verify it's session, any other verified client with the "Manually verify by text" feature can be used. Element Android (and possibly iOS) is the only client I have found to support manual verification by choice instead of defaulting to verifying by emoji.

### Messages sent by selfbot
Any messages sent by this selfbot, like responses to commands, will include `(SelfBot)` (and if linked, the source code) at the end of the message. This is to help room moderators quickly identify why exactly a user account is responding automatically, and will hopefully give the user running the selfbot a chance to disable it in a specific room before being removed by moderators. This does not affect edited messages.

### Broken features
Using a feature of the bot that edits your message, like custom emojis, replacement text, or !shrug, while replying to another message, duplicates the reply in the edit.

### Support room
The support room can be found [here](https://matrix.to/#/#deadcade-selfbot:deadca.de). It is recommended to keep testing in this room or another private room, as it is unencrypted and does not clutter other rooms.
