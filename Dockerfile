# Берём официальный образ Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей и ставим пакеты
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код в контейнер
COPY . .

# Указываем команду запуска
CMD ["python", "main.py"]
