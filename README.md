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
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Установка (Windows)

```shell
git clone https://github.com/ZUB3C/FipiBankClassification
cd FipiBankClassification
python -m venv venv
source \venv\Scripts\activate
pip install -r requirements.txt
```

## Сбор базы данных

```shell
python -m parse
```
