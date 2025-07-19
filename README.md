# Типизация задач ЕГЭ Открытого банка ФИПИ с использованием средств автоматической обработки информации

## Описание

Типизация задач ЕГЭ по информатике из [нового Открытого банка тестовых заданий
ФИПИ](https://ege.fipi.ru/bank) по номерам в экзамене на основе их текста.

## Установка (с помощью [uv](https://docs.astral.sh/uv/))

Для начала необходимо [установить uv](https://docs.astral.sh/uv/getting-started/installation/)

```shell
git clone https://github.com/ZUB3C/FipiBankClassification
cd FipiBankClassification
uv sync
```

## Сбор базы данных с задачами ЕГЭ по информатике

```shell
uv run -m src.parse --ege -s "Информатика и ИКТ"
```
## Запуск сайта

```shell
uv run -m src.web_ui.app
```