import asyncio
import logging
import random
from datetime import datetime, time
from pathlib import Path

import anthropic
from aiogram import Bot, Dispatcher, F
from aiogram.types import ChatMemberUpdated, FSInputFile, Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import config

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
claude = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


async def send_scheduled(text=None, image=None):
    if image and Path(image).exists():
        photo = FSInputFile(image)
        if text:
            await bot.send_photo(config.CHAT_ID, photo, caption=text)
        else:
            await bot.send_photo(config.CHAT_ID, photo)
    elif text:
        await bot.send_message(config.CHAT_ID, text)


def schedule_next_random():
    delay = random.randint(config.RANDOM_INTERVAL_MIN, config.RANDOM_INTERVAL_MAX)
    run_dt = datetime.fromtimestamp(datetime.now().timestamp() + delay)
    scheduler.add_job(
        send_random_content,
        "date",
        run_date=run_dt,
        id="random_content",
        replace_existing=True,
    )


async def send_random_content():
    now = datetime.now().time()
    if not (time(16, 30) <= now <= time(20, 30)):
        schedule_next_random()
        return

    memes_dir = Path(config.MEMES_DIR)
    available_memes = []
    if memes_dir.exists():
        available_memes = [
            f for f in memes_dir.iterdir()
            if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif")
            and f.name not in config.EXCLUDED_FROM_RANDOM
        ]

    if available_memes and random.random() < 0.5:
        photo = FSInputFile(str(random.choice(available_memes)))
        await bot.send_photo(config.CHAT_ID, photo)
    else:
        await bot.send_message(config.CHAT_ID, random.choice(config.JOKES))

    schedule_next_random()


@dp.my_chat_member()
async def on_bot_added(event: ChatMemberUpdated):
    if event.new_chat_member.status in ("member", "administrator"):
        await bot.send_message(event.chat.id, config.WELCOME_TEXT)


@dp.message(F.text.func(lambda t: t and f"@{config.BOT_USERNAME}" in t))
async def on_mention(message: Message):
    text = message.text.replace(f"@{config.BOT_USERNAME}", "").strip()
    if not text:
        return
    response = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=config.SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    await message.reply(response.content[0].text)


def setup_jobs():
    for item in config.SCHEDULED_MESSAGES:
        hour, minute = map(int, item["time"].split(":"))
        scheduler.add_job(
            send_scheduled,
            CronTrigger(hour=hour, minute=minute, timezone="Europe/Moscow"),
            kwargs={"text": item.get("text"), "image": item.get("image")},
        )
    schedule_next_random()


async def main():
    setup_jobs()
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
