FROM python:3.9-slim

WORKDIR /src

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data

WORKDIR /app

COPY . /app

CMD ["python", "src/ebird_media_ratings.py"]