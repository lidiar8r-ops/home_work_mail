# Сервис управления рассылками

Учебный проект на Django: управление клиентами, сообщениями и рассылками,
ручной запуск отправки, журнал попыток, статистика, роли и кеширование.

## Стек

- Python 3.13
- Django 6.1
- PostgreSQL 18
- python-dotenv

## Запуск

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

Письма по умолчанию выводятся в терминал: console backend печатает тему,
текст и ссылки подтверждения/восстановления пароля.

## Структура

- `config/` — настройки проекта.
- `users/` — пользователь, регистрация, вход, восстановление пароля.
- `mailings/` — клиенты, сообщения, рассылки, попытки, статистика.
- `templates/` — общие шаблоны.
- `static/` — стили.
