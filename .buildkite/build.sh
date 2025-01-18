#!/bin/bash
DOCKER_USERNAME=bassmatt
APPLICATION_NAME=magic512bot
GIT_HASH=git log --format="%h" -n 1

docker build --tag ${DOCKER_USERNAME}/${APPLICATION_NAME}:${GIT_HASH} .

docker push ${DOCKER_USERNAME}/${APPLICATION_NAME}:${GIT_HASH}