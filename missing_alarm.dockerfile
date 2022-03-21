# FROM amancevice/pandas:0.23.0-python3-slim
FROM python:alpine3.6

ARG TZ='Asia/Taipei'

ENV TZ $TZ

ADD ./requirement_file/missing_alarm.requirements.txt /code/
WORKDIR /code

# Install dependency library
RUN apk update && apk add --no-cache \
    postgresql-dev \
    gcc \
    musl-dev \
    tzdata \
    libffi-dev \
    alpine-sdk

# Set timezone
RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r missing_alarm.requirements.txt

RUN rm missing_alarm.requirements.txt

COPY src/utility/artichoke_rawdata_missing_alarm.py /code/src/
COPY src/utility/get_db_session.py /code/src/

CMD ["python", "./src/artichoke_rawdata_missing_alarm.py"]
