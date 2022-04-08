#!/usr/bin/env python3
# Created by @deadcade:deadca.de
# DEADCADE's Matrix Self Bot v1.2.0
# builtins
import asyncio # Required by nio
import json # Settings and xkcd command
import hashlib # File cache
import os # Filesystem
import mimetypes # Uploading files to homeserver
import html # HTML formatting
import requests # XKCD command
import subprocess # ping command (admin)
import random # roll command
import datetime # Ratelimiting

# External dependencies
import nio # Matrix library, matirx-nio[e2e]
from PIL import Image # Resizing images, pillow

# Set the settings path
settings_path = "./data/settings.json"
# Open and read settings or exit
if os.path.isfile(settings_path):
    with open(settings_path) as settings_file:
        settings = json.load(settings_file)
else:
    print("Please create a settings file at " + settings_path)
    exit()

# Basic function for loading data from disk or returning a default value
def load_data(path, default={}):
    if os.path.isfile(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except json.decoder.JSONDecodeError:
            return default
    else:
        return default

# Cache for files sent to the homeserver, prevents reuploading existing files
file_cache = load_data(settings["file_cache_path"])

# Emojis
emojis = load_data(settings["emojis_path"], {"default_size": 24})

# Get text to replace when enclosed in semicolons
text_replace = load_data(settings["text_replace_path"])

# Credentials
credentials = load_data(settings["credentials_path"])

# Set up global variables
client = None
ratelimits = {}

# Common function definitions
# Grab a list of all emojis on disk
def list_emojis():
    global settings
    emojislist = {}
    for filename in os.listdir(settings["emojis_folder_path"]):
        if "_resized" in filename:
            continue
        orig = filename
        filename = settings["emojis_folder_path"] + filename
        emojislist[orig.split(".")[0]] = filename
    return emojislist

# Downlaod an external file to disk
def download_file(url, filename):
    if os.path.exists(filename):
        return filename
    r = requests.get(url, stream=True, allow_redirects=True)
    if r.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(r.content)
        return filename
    else:
        return False

# Resize an image (squares only)
def resize_image(filename, size):
    im = Image.open(filename)
    im = im.resize((size,size))
    # Remove .ext from the filename, insert _resized into it, and save it
    filename = filename[:-4] + "_resized" + filename[-4:]
    im.save(filename)
    return filename

# Mentions a user
def mention(user):
    return f"[{user.split(':')[0][1:]}](https://matrix.to/#/{user})"

# Send file to homeserver
async def send_file(filename):
    global client, settings, file_cache
    with open(filename, "rb") as f:
        hash = hashlib.sha512(f.read()).hexdigest()
    if hash in file_cache.keys():
        return file_cache[hash]

    mime_type = mimetypes.guess_type(filename)
    file_stat = os.stat(filename)
    with open(filename, "r+b") as f:
        resp, maybe_keys = await client.upload(f, content_type=mime_type[0], filename=os.path.basename(filename), filesize=file_stat.st_size)
    if (isinstance(resp, nio.UploadResponse)):
        file_cache[hash] = resp.content_uri
        with open(settings["file_cache_path"], "w") as f:
            json.dump(file_cache, f)
        return resp.content_uri
    else:
        return ""

# Send an image as a message to a room
async def send_image(room_id, url, text):
    global client
    return await client.room_send(room_id=room_id, message_type="m.room.message", content={"msgtype": "m.image", "body": text, "url": url}, ignore_unverified_devices=True)

# Edits a message (without HTML formatting)
async def edit_message_unformatted(room_id, original_event, text):
    global client
    return await client.room_send(room_id=room_id, message_type="m.room.message", content={"msgtype": "m.text", "body": "* " + text, "m.new_content": {"msgtype": "m.text", "body": text}, "m.relates_to": {'rel_type': 'm.replace', 'event_id': original_event.event_id}}, ignore_unverified_devices=True)

# Edits a message (with HTML formatting)
async def edit_message(room_id, original_event, text):
    global client
    unformatted, formatted = text, text
    unformatted = "".join([part.split(">")[-1] for part in unformatted.split("<")])
    unformatted = html.unescape(unformatted)
    # Before replacing newlines in formatted, check if both are equal
    if unformatted == formatted:
        # This check is here to prevent sending "formatted" text that is exactly the same as unformatted text
        return await edit_message_unformatted(room_id, original_event, text)
    # \n doesn't work in HTML, replace it with <br>
    formatted = formatted.replace("\n", "<br>")
    return await client.room_send(room_id=room_id, message_type="m.room.message", content={"msgtype": "m.text", "body": "* " + unformatted, "format": "org.matrix.custom.html", "formatted_body": "* " + formatted, "m.new_content": {"msgtype": "m.text", "body": unformatted, "format": "org.matrix.custom.html", "formatted_body": formatted}, "m.relates_to": {'rel_type': 'm.replace', 'event_id': original_event.event_id}}, ignore_unverified_devices=True)

# Send a message (with HTML formatting)
async def send_text(room_id, text):
    unformatted, formatted = text, text
    unformatted = "".join([part.split(">")[-1] for part in unformatted.split("<")])
    unformatted = html.unescape(unformatted)
    # \n doesn't work in HTML, replace it with <br>
    formatted = formatted.replace("\n", "<br>")
    return await client.room_send(room_id=room_id, message_type="m.room.message", content={"msgtype": "m.text", "body": unformatted + " (SelfBot)", "format": "org.matrix.custom.html", "formatted_body": formatted + (f" (<a href=\"{settings['source_url']}\">SelfBot</a>)" if settings["source_url"] else " (SelfBot)")}, ignore_unverified_devices=True)

# Commands definition
# Appends shrug to the end of the message
async def shrug(args, room, event):
    if event.body == settings["prefix"] + "shrug":
        new_message = "¯\\_(ツ)_/¯"
    else:
        new_message = event.body.replace(settings["prefix"] + "shrug ", "").replace(settings["prefix"] + "shrug", "") + " ¯\\_(ツ)_/¯"
    return await edit_message(room.room_id, event, new_message)

# Help command
async def help(args, room, event):
    if len(args) == 0:
        # No command specified, send command list
        source_text = f"\n<a href=\"{settings['source_url']}\">Source Code</a>" if settings["source_url"] else ""
        return await send_text(room.room_id, settings["help_messages"]["help"].replace("{prefix}", settings["prefix"]) + source_text)
    else:
        help_command = args[0].lower().split(settings["prefix"])[-1]
        if help_command in settings["help_messages"].keys():
            return await send_text(room.room_id, "Usage:\n" + settings["help_messages"][help_command].replace("{prefix}", settings["prefix"]) + "\n")
        else:
            return await send_text(room.room_id, "Unknown command!")

# Set default emoji size
async def emoji_size(args, room, event):
    global emojis
    if len(args) == 1 and args[0].isdecimal():
        emojis["default_size"] = args[0]
        with open(settings["emojis_path"], "w") as f:
            json.dump(emojis, f)
        return await send_text(room.room_id, "Set default size to: " + args[0])
    return await send_text(room.room_id, "Please provide the size argument")

# Lists possible emojis
async def emoji_list(args, room, event):
    global emojis
    emojislist = list_emojis()
    message = f"Default emoji size: {emojis['default_size']}\nAvailable emojis:\n"
    for emoji in emojislist:
        message += emoji + ": :" + emoji + ":24:, "
    message += "\n"
    message = message[:-1]  # Remove the last comma
    return await send_text(room.room_id, message)

# Ping the selfbot or an external host
async def ping(args, room, event):
    # If no external host is provided, or the user pinging is not the account itself
    if len(args) == 0 or event.sender != client.user_id:
        return await send_text(room.room_id, "Selfbot is online and accepting messages in " + room.display_name + ".")
    else:
        # If the user is allowed to ping, and a host is provided, ping
        # Linux only, replace -c with -n (and possibly find -W alternative)
        ping = subprocess.run(["ping", "-c", "1", "-W", "2", args[0]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        successful = ping.returncode
        message = "Ping to " + args[0] + " was " + ("successful" if not successful else "unsuccessful")
        return await send_text(room.room_id, message)

# Roll a dice!
async def roll(args, room, event):
    sides = 6 if len(args) == 0 or not args[0].isdecimal() else int(args[0])
    out = random.randint(1, sides)
    return await send_text(room.room_id, "You rolled a " + str(out) + "!")

# Send an XKCD in chat (Date, number, title, and image)
async def xkcd(args, room, event):
    global settings
    comic = ""
    if len(args) == 1 and args[0].isdecimal():
        comic = args[0] + "/"
    try:
        r = requests.get(f"https://xkcd.com/{comic}info.0.json")
        rj = json.loads(r.text)
        filename = download_file(rj["img"], settings["cache_path"] + "/" + str(rj["num"]) + "." + rj["img"].split(".")[-1])
        image = await send_file(filename)
        await send_text(room.room_id, f"{rj['year']}/{rj['month']}/{rj['day']}, {str(rj['num'])}: <a href=\"https://xkcd.com/{str(rj['num'])}/\">{rj['safe_title']}</a>")
        return await send_image(room.room_id, image, rj['alt'])
    except Exception:
        return await send_text(room.room_id, "Failed to get XKCD!")

async def message_callback(room: nio.MatrixRoom, event: nio.RoomMessageText) -> None:
    global client, settings, emojis
    if settings["debug"]:
        print(f"Message received in room {room.display_name}\n{event.sender} | {event.body}")
    admin = False
    if event.sender == client.user_id: # If this is our message
        admin = True
    if "m.new_content" in event.source["content"]:
        return
    # If the message is a command, process it as such
    if event.body.lower().startswith(settings["prefix"]):
        command = event.body.split(" ")[0][len(settings["prefix"]):].lower()
        args = event.body.split(" ")[1:]
        if event.sender in ratelimits and not admin:
            if ratelimits[event.sender] > int(datetime.datetime.utcnow().timestamp()):
                return
        ratelimits[event.sender] = int(datetime.datetime.utcnow().timestamp()) + settings["ratelimit"]
        if command in settings["command_list"] or (admin and command in settings["admin_command_list"]):
            command_function = globals()[command]
            await command_function(args, room, event)
        return
    if admin:
        # If it is not a command, process regular message parsing.
        new_body, orig_body = event.body, event.body
        # Emoji processor
        if event.body.count(":") > 1: # Reduce searching by a significant margin
            # Get a list of emojis on disk
            emojislist = list_emojis()
            for emoji in emojislist.keys():
                # If the emoji is in there (While because we're replacing one at a time for size support)
                while ":" + emoji + ":" in new_body:
                    # Get the size
                    size = new_body[new_body.find(f":{emoji}:") + len(f":{emoji}:"):].split(":")[0]
                    sizeset = True
                    # Make sure emoji size ends with :, do not process size with :emoji:24
                    try:
                        third_colon = new_body[new_body.find(f":{emoji}:") + len(f":{emoji}:") + len(str(size)):][0]
                    except IndexError:
                        third_colon = ""
                    # If the size is processable
                    if (not size.isdecimal()) or third_colon != ":":
                        sizeset = False
                        size = str(emojis["default_size"])
                    # Prevent KeyError
                    if str(size) not in emojis.keys():
                        emojis[str(size)] = {}
                    # If this emoji is not uploaded yet for this size
                    if emoji not in emojis[str(size)].keys():
                        # Upload and index it
                        emojis[str(size)][emoji] = await send_file(resize_image(emojislist[emoji], int(size)))
                        with open(settings["emojis_path"], "w") as f:
                            json.dump(emojis, f)
                    # Replace the emoij with the respective file
                    new_body = new_body.replace(":" + emoji + ":" + ("" if not sizeset else f"{size}:"), f"<img src=\"{emojis[size][emoji]}\" alt=\"{emoji}\">", 1)
        # Text replace processor
        if event.body.count(";") > 1:
            for to_replace in text_replace.keys():
                if ";" + to_replace + ";" in new_body:
                    new_body = new_body.replace(";" + to_replace + ";", text_replace[to_replace])
        # If anything was changed processing the message, edit it
        if not new_body == orig_body:
            await edit_message(room.room_id, event, new_body)

async def decryption_failure_callback(room: nio.MatrixRoom, event: nio.MegolmEvent) -> None:
    print(f"Failed to decrypt {event.event_id} in room {room.display_name}")
    return

async def main() -> None:
    global client, settings, credentials
    # Create client config
    config = nio.AsyncClientConfig(store_sync_tokens=True, encryption_enabled=True)
    # If there are no previously-saved credentials, we'll use the password
    if not os.path.exists(credentials["session_path"]):
        client = nio.AsyncClient(credentials["homeserver"], credentials["user"], config=config, store_path=credentials["store_path"])
        resp = await client.login(credentials["password"], device_name=credentials["device_name"])
        # check that we logged in succesfully
        if (isinstance(resp, nio.LoginResponse)):
            # open the config file in write-mode
            with open(credentials["session_path"], "w") as f:
                # write the login details to disk
                json.dump({"homeserver": credentials["homeserver"], "user_id": resp.user_id, "device_id": resp.device_id, "access_token": resp.access_token},f)
        else:
            print(f"homeserver = \"{credentials['homeserver']}\"; user = \"{credentials['user']}\"")
            print(f"Failed to log in: {resp}")
            return
    # Otherwise the config file exists, so we'll use the stored credentials
    else:
        # open the file in read-only mode
        with open(credentials["session_path"], "r") as f:
            session = json.load(f)
            client = nio.AsyncClient(session['homeserver'], config=config, store_path=credentials["store_path"])
            client.restore_login(user_id=session['user_id'], access_token=session['access_token'], device_id=session['device_id'])

    credentials = {}
    print(f"Logged in as: {client.user_id} with device {client.device_id}")
    await client.sync(timeout=60000, full_state=True) # Ignore any messages sent before now.
    client.add_event_callback(message_callback, nio.RoomMessageText)
    client.add_event_callback(decryption_failure_callback, (nio.MegolmEvent,))
    if client.should_upload_keys:
        await client.keys_upload()
    while True:
        # If we're in debug mode, exit on error
        if settings["debug"]:
            await client.sync_forever(timeout=int(0xDEADCADE * 8.03012557499132e-06), full_state=True)
        else:
            # Else just print the error and continue
            try:
                await client.sync_forever(timeout=int(0xDEADCADE * 8.03012557499132e-06), full_state=True)
            except Exception as e:
                print(e)
                await asyncio.sleep(int(0xDEADCADE * 2.676708524997107e-10))

if __name__ == "__main__":
    asyncio.run(main())
