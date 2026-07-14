# Wedding Telegram Bot — Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Telegram bot that sends scheduled wedding messages, random jokes/memes, and responds to @mentions via Claude AI.

**Architecture:** Single Python process — aiogram 3 dispatcher + APScheduler in one asyncio event loop. Config fully separated from logic.

**Tech Stack:** Python 3.11+, aiogram 3, APScheduler 3, anthropic SDK, python-dotenv

## Global Constraints

- No automated tests
- Timezone: Europe/Moscow (UTC+3) for all scheduled times
- Random memes folder: `memes/` relative to bot working directory
- `boarding.jpg` and `disembark.jpg` are reserved filenames — excluded from random rotation
- Claude model: `claude-haiku-4-5-20251001` for mention responses (fast + cheap)

---

### Task 1: Project scaffold + config

**Files:**
- Create: `bot/config.py`
- Create: `bot/requirements.txt`
- Create: `bot/.env.example`
- Create: `bot/memes/.gitkeep`

- [ ] Create `bot/` directory and `bot/memes/` subdirectory

- [ ] Create `bot/requirements.txt`:

```
aiogram==3.13.1
APScheduler==3.10.4
anthropic==0.34.2
python-dotenv==1.0.1
```

- [ ] Create `bot/.env.example`:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=-100123456789
ANTHROPIC_API_KEY=your_anthropic_key_here
BOT_USERNAME=your_bot_username_without_at
```

- [ ] Create `bot/config.py`:

```python
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
BOT_USERNAME = os.getenv("BOT_USERNAME")

SCHEDULED_MESSAGES = [
    {
        "time": "16:30",
        "text": "Дамы и господа, добро пожаловать на борт Лодки Любви 🛥️ Яхта «Алиса» готова к отплытию. Пристегните ремни, приготовьте бокалы — берега Подмосковья сами себя не будут разглядывать.",
        "image": "memes/boarding.jpg",
    },
    {
        "time": "18:30",
        "text": "Горячее на борту! 🍽️ Просим всех занять места за столом. Яхта качается — суп нет.",
    },
    {
        "time": "19:45",
        "text": "Внимание, внимание. На горизонте замечен торт 🎂 Просим всех собраться на палубе.",
    },
    {
        "time": "20:20",
        "image": "memes/disembark.jpg",
    },
    {
        "time": "20:30",
        "text": "Причаливаем! ⚓️ Лодка Любви завершает свой первый и последний рейс. Просьба захватить все свои вещи, всех своих людей и хорошее настроение — оно нам ещё понадобится на Сретенке.",
    },
]

JOKES = [
    "На свадьбе тамада кричит: «Горько!» Соломон встаёт: «Дайте хоть допить — вы же знаете, сколько стоит это вино.»",
    "Татарская бабушка на свадьбе: «Ешь, ешь. Ты что, на диете? На диете замуж не выходят.»",
    "Еврейская мама на свадьбе сына: «Такой умный мальчик. Мог бы стать врачом. Ну ладно, пусть будет счастлив.»",
    "Брак — это когда двое становятся одним целым. Споры начинаются, когда не могут решить каким именно.",
    "После 35 «лечь пораньше» звучит как мечта, а не наказание.",
    "— Папа, я хочу жениться. — На ком? — На Маше. — Но она бедная! — А на Рахиль? — Богатая, но некрасивая. — Сынок, богатую сделаем красивой. Ищи умную.",
    "Почему татары так хорошо пляшут? Потому что если не будешь танцевать, заставят есть чак-чак до утра.",
    "В 20 лет думаешь: «Хочу найти себя». В 30: «Кажется, нашёл». В 40: «Лучше бы не находил».",
    "Свадьба — единственное мероприятие, где мужчина добровольно надевает галстук и не знает когда снимет.",
    "— Дорогой, мы 10 лет вместе. Может сходим куда-нибудь? — Отличная идея. Ты в ресторан, я на рыбалку.",
]

SYSTEM_PROMPT = """Ты — весёлый распорядитель свадьбы Владимира и Алины.
Отвечай коротко, дружелюбно, с лёгким юмором.
Программа дня:
  16:30 — посадка на яхту «Алиса», яхт-клуб «Буревестник»
  18:30 — горячее
  19:45 — торт
  20:30 — причаливаем, трансфер на Сретенку (паб Speakers)
На вопросы отвечай как тамада, знающий программу."""

WELCOME_TEXT = (
    "Привет! Я AI-распорядитель свадьбы Владимира и Алины 🎩 "
    "Буду с вами весь вечер — шутки шутить, программу объявлять "
    "и отвечать на вопросы если тегнете меня."
)

RANDOM_INTERVAL_MIN = 20 * 60  # seconds
RANDOM_INTERVAL_MAX = 50 * 60  # seconds
MEMES_DIR = "memes"
EXCLUDED_FROM_RANDOM = {"boarding.jpg", "disembark.jpg"}
```

- [ ] Commit:

```bash
git add bot/
git commit -m "feat: add bot scaffold, config, and requirements"
```

---

### Task 2: Main bot logic

**Files:**
- Create: `bot/bot.py`

- [ ] Create `bot/bot.py`:

```python
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
```

- [ ] Commit:

```bash
git add bot/bot.py
git commit -m "feat: implement bot — scheduler, random content, mention handler, welcome"
```

---

### Task 3: systemd service + deployment instructions

**Files:**
- Create: `bot/wedding-bot.service`
- Create: `bot/README.md`

- [ ] Create `bot/wedding-bot.service` (replace `ubuntu` and path if different on your VPS):

```ini
[Unit]
Description=Wedding Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/wedding-bot
ExecStart=/home/ubuntu/wedding-bot/venv/bin/python bot.py
Restart=on-failure
RestartSec=5
EnvironmentFile=/home/ubuntu/wedding-bot/.env

[Install]
WantedBy=multi-user.target
```

- [ ] Create `bot/README.md` with deploy steps:

```markdown
# Deploy

## On VPS

```bash
# 1. Copy project
scp -r bot/ ubuntu@YOUR_VPS_IP:/home/ubuntu/wedding-bot

# 2. SSH in
ssh ubuntu@YOUR_VPS_IP

# 3. Setup
cd /home/ubuntu/wedding-bot
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# 4. Create .env (copy from .env.example, fill in values)
cp .env.example .env
nano .env

# 5. Upload memes
# From local machine:
scp memes/* ubuntu@YOUR_VPS_IP:/home/ubuntu/wedding-bot/memes/

# 6. Install and start service
sudo cp wedding-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable wedding-bot
sudo systemctl start wedding-bot

# 7. Check logs
journalctl -u wedding-bot -f
```

## Get bot token
1. Message @BotFather on Telegram
2. /newbot → follow prompts → copy token

## Get chat ID
1. Add bot to group
2. Send any message in group
3. Open: https://api.telegram.org/bot<TOKEN>/getUpdates
4. Find "chat":{"id": ...} — that negative number is TELEGRAM_CHAT_ID
```

- [ ] Commit:

```bash
git add bot/wedding-bot.service bot/README.md
git commit -m "feat: add systemd service and deploy instructions"
```
