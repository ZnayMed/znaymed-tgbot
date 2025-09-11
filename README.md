# znaymed-tgbot

```
znaymed-tgbot/                ← корень git-репозитория
├── pyproject.toml            ← манифест Poetry (name, deps, packages)
├── poetry.lock               ← зафиксированные версии пакетов
├── README.md                 ← что делает бот, как запускать
├── .env.example              ← шаблон переменных окружения
├── .gitignore
├── Dockerfile
├── docker-compose.yml        ← локальные сервисы: pg, redis, etc.
├── src/                      ← **весь исполняемый код живёт здесь**
│   └── tgbot/                ← сам пакет (имя совпадает с include в pyproject)
│       ├── __init__.py
│       ├── main.py           ← entry-point: создаёт Bot, Dispatcher, polling
│       ├── config.py         ← pydantic.BaseSettings (чтение .env)
│       ├── handlers/         ← файлы-хендлеры по теме
│       │   ├── __init__.py
│       │   ├── common.py     ← /start, /help
│       │   ├── payments.py   ← колбэки платёжки
│       │   └── courses.py    ← навигация по курсам
│       ├── keyboards/        ← Inline/Reply builders
│       │   ├── __init__.py
│       │   └── course.py
│       ├── middlewares/      ← лог, антифлуд, локализация
│       │   └── __init__.py
│       ├── services/         ← «инфраструктура» (БД, Kafka, HTTP-API)
│       │   └── __init__.py
│       ├── utils/            ← мелкие общие функции/классы
│       │   └── exceptions.py
│       └── typing.py         ← общие TypedDict / Protocol
├── tests/                    ← pytest-тесты (зеркалят src/…)
│   ├── __init__.py
│   ├── conftest.py           ← фикстуры: event loop, bot, fake DB
│   └── handlers/
│       └── test_common.py
└── docs/                     ← (опц.) MKDocs или Sphinx
    └── architecture.md

```
