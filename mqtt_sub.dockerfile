FROM python:alpine3.6

ARG TZ='Asia/Taipei'

ENV TZ $TZ

ADD ./requirement_file/mqtt_sub.requirements.txt /code/
WORKDIR /code

# Install dependency library
RUN apk update && apk add --no-cache \
    postgresql-dev \
    gcc \
    musl-dev \
    tzdata 

# Set timzeon
RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

RUN pip install --no-cache-dir -r mqtt_sub.requirements.txt 

RUN apk del \
    gcc \
    musl-dev

RUN rm mqtt_sub.requirements.txt

COPY src/artichoke_server /code/src/artichoke_server
WORKDIR /code

CMD ["python", "./src/artichoke_server/mqtt_sub_postgres.py"]
