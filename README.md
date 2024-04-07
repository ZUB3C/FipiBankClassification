# Индивидуальный проект

Типизация задач ЕГЭ Открытого банка ФИПИ с использованием средств автоматической обработки
информации

## Описание

Типизация задач ЕГЭ по некоторым предметам из [нового Открытого банка тестовых заданий
ФИПИ](https://ege.fipi.ru/bank) по номерам в экзамене на основе их текста.

## Установка (Linux)

```shell
git clone https://github.com/ZUB3C/FipiBankClassification
cd FipiBankClassification
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Установка (Windows)

```shell
git clone https://github.com/ZUB3C/FipiBankClassification
cd FipiBankClassification
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Для разработчиков
```shell
python -m pip install -r dev-requirements.txt
```

## Сбор базы данных с задачами ЕГЭ по информатике

```shell
python -m parse
```
