#!/bin/sh
apk update && apk add --no-cache git
DOCKER_USERNAME=bassmatt
APPLICATION_NAME=magic512bot
GIT_HASH=$(git log --format="%h" -n 1)

sleep 20 # sidecar takes a while to start up

docker build --tag ${DOCKER_USERNAME}/${APPLICATION_NAME}:${GIT_HASH} --tag ${DOCKER_USERNAME}/${APPLICATION_NAME}:latest .

docker push ${DOCKER_USERNAME}/${APPLICATION_NAME}:latest