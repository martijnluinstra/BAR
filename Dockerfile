FROM python:3.10-slim

COPY requirements.txt /app/requirements.txt

WORKDIR /app

RUN apt-get -y update \
    && apt-get -y install python3-dev build-essential libmariadb-dev-compat git \
    && pip install -r requirements.txt

COPY --chmod=0755 entrypoint.sh /app
COPY uwsgi.ini /app
COPY config.py.docker /app/config.py
COPY bar /app/bar
COPY migrations /app/migrations

CMD ["./entrypoint.sh"]
