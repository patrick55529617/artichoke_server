#!/bin/bash
set -eu

# Build 

FROM golang:1.8 as frpBuild

COPY . /go/src/github.com/fatedier/frp

ENV CGO_ENABLED=0

RUN cd /go/src/github.com/fatedier/frp \
 && make
