# Wedding Bot — Deploy

## На VPS

```bash
# 1. Скопировать проект
scp -r bot/ ubuntu@YOUR_VPS_IP:/home/ubuntu/wedding-bot

# 2. Зайти на VPS
ssh ubuntu@YOUR_VPS_IP

# 3. Установить зависимости
cd /home/ubuntu/wedding-bot
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# 4. Создать .env
cp .env.example .env
nano .env  # заполнить все 4 значения

# 5. Залить мемы (с локальной машины)
scp memes/* ubuntu@YOUR_VPS_IP:/home/ubuntu/wedding-bot/memes/
# boarding.jpg и disembark.jpg — обязательно

# 6. Установить и запустить сервис
sudo cp wedding-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable wedding-bot
sudo systemctl start wedding-bot

# 7. Проверить логи
journalctl -u wedding-bot -f
```

## Получить токен бота

1. Написать @BotFather в Telegram
2. `/newbot` → следовать инструкциям → скопировать токен

## Получить CHAT_ID группы

1. Добавить бота в группу
2. Написать любое сообщение в группу
3. Открыть: `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Найти `"chat":{"id": ...}` — отрицательное число и есть `TELEGRAM_CHAT_ID`

## Структура memes/

```
memes/
  boarding.jpg      ← отправляется в 16:30 при посадке (обязательно)
  disembark.jpg     ← отправляется в 20:20 перед высадкой (обязательно)
  meme_1.jpg        ← случайная ротация
  meme_2.jpg
  ...
```

## Команды управления

```bash
sudo systemctl stop wedding-bot    # остановить
sudo systemctl start wedding-bot   # запустить
sudo systemctl restart wedding-bot # перезапустить
journalctl -u wedding-bot -f       # логи в реальном времени
```
