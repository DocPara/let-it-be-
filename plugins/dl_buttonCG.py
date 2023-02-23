import os
import re
import math
import asyncio
import time
from datetime import datetime
from signal import SIGINT
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from pyrogram.types import Message
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import MessageNotModified
from youtube_dl import YoutubeDL
from youtube_dl.utils import DownloadError
from helper_funcs.display_progress import progress_for_pyrogram, humanbytes
from helper_funcs.help_Nekmo_ffmpeg import transcode
from helper_funcs.admin_check import AdminCheck
from helper_funcs.utils import is_youtube
from helper_funcs.database import *


# ======================================== Basic Requirements =========================================================

bot = Client("YouTube_Downloader")
admin = int(os.environ.get("admin_user_id"))
download_dict = {}


# ======================================== CallBacks ==============================================================


async def download_coroutine(m, umsg):
    try:
        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": os.path.join(os.path.dirname(os.path.abspath(__file__)), "DOWNLOADS", "%(title)s-%(id)s.%(ext)s"),
            "writethumbnail": True,
            "progress_hooks": [lambda d: progress_for_pyrogram(d, umsg)]
        }
        global download_dict
        download_dict[f"{m.chat.id}-{umsg.message_id}"] = True
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([m.text])
        download_dict.pop(f"{m.chat.id}-{umsg.message_id}")
    except Exception as e:
        download_dict.pop(f"{m.chat.id}-{umsg.message_id}")
        await umsg.edit_text(f"An Error Occurred: `{e}`")
        return
    except KeyboardInterrupt:
        download_dict.pop(f"{m.chat.id}-{umsg.message_id}")
        await umsg.edit_text("Download Cancelled")
        return
    await umsg.edit_text("Downloading completed successfully")


async def youtube_dl_call_back(bot, update):
    query_data = update.data
    if query_data.startswith("youtube-dl;"):
        video_link = query_data.split(";")[1]
        user_id = update.from_user.id
        chat_id = update.message.chat.id
        user_msg = update.message.message_id
        await bot.send_chat_action(chat_id, "typing")
        async with bot.conversation(chat_id) as conv:
            try:
                prompt_text = "Enter the name of the file(without extension) to be saved as or type /cancel to abort:"
                response = await conv.send_message(prompt_text)
                reply = await conv.get_response()
                if reply.text.startswith("/cancel"):
                    await bot.send_message(chat_id, "Download Cancelled!")
                    return
                download_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DOWNLOADS")
                if not os.path.isdir(download_dir):
                    os.makedirs(download_dir)
                start = datetime.now()
                reply_text = "Downloading video...."
                reply_markup = InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Cancel Download", callback_data=f"cancel-download;{user_id};{user_msg}")]
                    ]
                )
                message = await bot.send_message(chat_id, reply_text, reply_markup=reply_markup)
                download_task = asyncio.ensure_future(download_coroutine(Message("url", video_link, reply), message))
                download_dict[f"{chat_id}-{message.message_id}"] = download_task
                while download_task in download_dict.values
