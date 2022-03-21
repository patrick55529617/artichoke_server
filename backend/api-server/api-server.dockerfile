FROM tiangolo/uvicorn-gunicorn:python3.6-alpine3.8
LABEL maintainers="patrick.hu@testritegroup.com"

# Set timezone
ARG TZ='Asia/Taipei'
ENV TZ $TZ

# Set API Version
ARG version=staging
ENV api-version=$version

RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone
RUN sed -i 's/http\:\/\/dl-cdn.alpinelinux.org/https\:\/\/alpine.global.ssl.fastly.net/g' /etc/apk/repositories
RUN apk update && apk add --no-cache \
  postgresql-dev \
  gcc \
  musl-dev \
  wget \
  openssl \
  libffi-dev \
  vim \
  tzdata
COPY ./api-server.requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
COPY ./app /app/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
