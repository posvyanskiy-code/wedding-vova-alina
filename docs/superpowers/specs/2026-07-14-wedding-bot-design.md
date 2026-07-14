# Wedding Telegram Bot — Design Spec
Date: 2026-07-14

## Overview

A Telegram bot that writes to the wedding guest group chat. Three behaviors:
1. Sends hardcoded messages at fixed times during the wedding day
2. Sends random jokes/memes every 20-50 minutes between events
3. Responds to @mentions with Claude AI (acts as a wedding MC assistant)

No interaction from guests beyond mentions. Bot only writes, never reads commands.

## Architecture

Single Python process on VPS under systemd. Two components share one asyncio event loop:

- **APScheduler** — fires scheduled jobs (fixed times + random interval jobs)
- **aiogram dispatcher** — listens for @mentions, calls Claude API, replies

```
bot.py          — main entry point, wires scheduler + dispatcher
config.py       — tokens, chat_id, schedule texts, jokes list
requirements.txt
wedding-bot.service  — systemd unit
memes/
  boarding.jpg      — "Prepare yourselves, a party is coming" (sent at 16:30)
  disembark.jpg     — "When you're getting married at 1 but the games on at 3" (sent at 20:20)
  meme_1.jpg        — "Где находится Израиль? Тут"
  meme_2.jpg        — "Татарская пауза"
  meme_3.jpg        — "Татары в моде при любой погоде"
  meme_4.jpg        — Свадебное фото с джином
```

Tokens stored in `.env` on VPS, never in code.

## Scheduled Messages (Moscow time, UTC+3)

| Time  | Type    | Content |
|-------|---------|---------|
| 16:30 | text + image | «Дамы и господа, добро пожаловать на борт Лодки Любви 🛥️ Яхта «Алиса» готова к отплытию. Пристегните ремни, приготовьте бокалы — берега Подмосковья сами себя не будут разглядывать.» + `boarding.jpg` |
| 18:30 | text    | «Горячее на борту! 🍽️ Просим всех занять места за столом. Яхта качается — суп нет.» |
| 19:45 | text    | «Внимание, внимание. На горизонте замечен торт 🎂 Просим всех собраться на палубе.» |
| 20:20 | image   | `disembark.jpg` |
| 20:30 | text    | «Причаливаем! ⚓️ Лодка Любви завершает свой первый и последний рейс. Просьба захватить все свои вещи, всех своих людей и хорошее настроение — оно нам ещё понадобится на Сретенке.» |

## Random Content (every 20-50 minutes)

Scheduler fires at a random interval between 20 and 50 minutes. Each fire:
1. Picks randomly between sending a text joke or a random meme image
2. For images: picks a random file from `memes/` excluding `boarding.jpg` and `disembark.jpg`
3. For text: picks a random joke from the hardcoded list

Random jokes list:
- «На свадьбе тамада кричит: «Горько!» Соломон встаёт: «Дайте хоть допить — вы же знаете, сколько стоит это вино.»»
- «Татарская бабушка на свадьбе: «Ешь, ешь. Ты что, на диете? На диете замуж не выходят.»»
- «Еврейская мама на свадьбе сына: «Такой умный мальчик. Мог бы стать врачом. Ну ладно, пусть будет счастлив.»»
- «Брак — это когда двое становятся одним целым. Споры начинаются, когда не могут решить каким именно.»
- «После 35 «лечь пораньше» звучит как мечта, а не наказание.»
- «— Папа, я хочу жениться. — На ком? — На Маше. — Но она бедная! — А на Рахиль? — Богатая, но некрасивая. — Сынок, богатую сделаем красивой. Ищи умную.»
- «Почему татары так хорошо пляшут? Потому что если не будешь танцевать, заставят есть чак-чак до утра.»
- «В 20 лет думаешь: «Хочу найти себя». В 30: «Кажется, нашёл». В 40: «Лучше бы не находил».»
- «Свадьба — единственное мероприятие, где мужчина добровольно надевает галстук и не знает когда снимет.»
- «— Дорогой, мы 10 лет вместе. Может сходим куда-нибудь? — Отличная идея. Ты в ресторан, я на рыбалку.»

Random content fires between 16:30 and 20:30 only (during the boat trip).

## Welcome Message

When the bot is added to a group chat, it sends:

> Привет! Я AI-распорядитель свадьбы Владимира и Алины 🎩 Буду с вами весь вечер — шутки шутить, программу объявлять и отвечать на вопросы если тегнете меня.

Triggered by the `my_chat_member` event when bot status changes to `member`/`administrator`.

## @Mention Handler

When any message in the group contains a mention of the bot (`@botusername`), the bot:
1. Extracts the message text (strips the mention)
2. Sends to Claude API with system prompt
3. Replies in the group thread

System prompt:
```
Ты — весёлый распорядитель свадьбы Владимира и Алины. 
Отвечай коротко, дружелюбно, с лёгким юмором. 
Программа дня: 
  16:30 — посадка на яхту «Алиса», яхт-клуб «Буревестник»
  18:30 — горячее
  19:45 — торт
  20:30 — причаливаем, трансфер на Сретенку (паб Speakers)
На вопросы отвечай как тамада, знающий программу.
```

No conversation history stored — each mention is an independent Claude API call.

## Environment Variables

```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...        # group chat id (negative number)
ANTHROPIC_API_KEY=...
BOT_USERNAME=...            # without @, used for mention detection
```

## Deployment

```bash
# On VPS
pip install aiogram apscheduler anthropic python-dotenv
# Copy files, create .env
systemctl enable wedding-bot
systemctl start wedding-bot
```

systemd unit restarts on failure, logs to journald.

## Dependencies

- `aiogram>=3.0` — Telegram bot framework
- `apscheduler>=3.10` — async-compatible scheduler
- `anthropic` — Claude API client
- `python-dotenv` — .env loading
