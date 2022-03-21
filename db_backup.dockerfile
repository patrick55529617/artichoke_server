FROM python:alpine3.6

ARG TZ='Asia/Taipei'

ENV TZ $TZ

ADD ./requirement_file/db_backup.requirements.txt /code/
WORKDIR /code

# Install dependency library
RUN apk update && apk add --no-cache \
    postgresql-dev \
    gcc \
    musl-dev \
    tzdata

# Set timezone
RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r db_backup.requirements.txt

RUN rm db_backup.requirements.txt

COPY src/utility/Artichoke_db_backup.py /code/src/
WORKDIR /code

CMD ["python", "./src/Artichoke_db_backup.py"]
