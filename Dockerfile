FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8-slim

RUN apt-get update
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt
ENV MAX_WORKERS=1
ENV WEB_CONCURRENCY=1
EXPOSE 80
COPY ./app /app
ENV PYTHONPATH=/
