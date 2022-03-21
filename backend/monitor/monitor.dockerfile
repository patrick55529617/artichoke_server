FROM python:alpine3.6
LABEL maintainers="patrick.hu@testritegroup.com"
# Set timezone
ARG TZ='Asia/Taipei'
ENV TZ $TZ
RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

# setup dev-tools
RUN apk update && apk add --no-cache \
  postgresql-dev \
  gcc \
  musl-dev \
  apk-cron \
  wget \
  openssl \
  libffi-dev \
  vim \
  alpine-sdk \
  tzdata

RUN pip3 install --upgrade pip
COPY ./monitor.requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

RUN ["mkdir", "/monitor"]
ENV PYTHONPATH="/monitor"
COPY ./main.py /monitor/main.py
COPY ./monitor_module.py /monitor/monitor_module.py
COPY ./__init__.py /monitor/__init__.py
COPY ./artichoke_base_service.ini /monitor/artichoke_base_service.ini

WORKDIR /monitor
CMD ["python", "main.py"]
