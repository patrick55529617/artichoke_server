FROM python:alpine3.6

ARG TZ='Asia/Taipei'

ENV TZ $TZ

ADD ./requirements.txt /code/
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

RUN pip install --no-cache-dir -r requirements.txt 

RUN apk del \
    gcc \
    musl-dev

RUN rm requirements.txt

COPY main.py /code/src/main.py
WORKDIR /code

CMD ["python", "./src/main.py"]
