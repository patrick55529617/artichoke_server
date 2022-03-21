FROM python:alpine3.6
LABEL maintainers="patrick.hu@testritegroup.com"
# Set timezone
ARG TZ='Asia/Taipei'
ENV TZ $TZ
RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

# setup dev-tools
RUN sed -i 's/http\:\/\/dl-cdn.alpinelinux.org/https\:\/\/alpine.global.ssl.fastly.net/g' /etc/apk/repositories
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
COPY ./worker_requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt


# For epos connection.
RUN echo "https://alpine.global.ssl.fastly.net/alpine/edge/community/" >> /etc/apk/repositories && \
  apk update && apk add --no-cache \
  libaio \
  libnsl

RUN ["mkdir", "/worker"]
ENV PYTHONPATH="/worker"
COPY ./main.py /worker/main.py
COPY ./worker_tmp_alg.py /worker/worker_tmp_alg.py
COPY ./__init__.py /worker/__init__.py
COPY ./utility /worker/utility
COPY ./artichoke_base_service.ini /worker/artichoke_base_service.ini

# For epos connection. Add oracle lib
RUN mkdir -p /worker/instantclient_11_2
COPY ./instantclient_11_2 /worker/instantclient_11_2
ENV LD_LIBRARY_PATH='/worker/instantclient_11_2'
RUN ln -s /usr/lib/libnsl.so.2 /usr/lib/libnsl.so.1

WORKDIR /worker
CMD ["python", "main.py"]
