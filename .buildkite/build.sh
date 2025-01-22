#!/bin/sh
DOCKER_USERNAME=bassmatt
APPLICATION_NAME=magic512bot

sleep 20 # sidecar takes a while to start up

docker build --tag ${DOCKER_USERNAME}/${APPLICATION_NAME}:${BUILDKITE_BUILD_NUMBER} --tag ${DOCKER_USERNAME}/${APPLICATION_NAME}:latest .

docker push ${DOCKER_USERNAME}/${APPLICATION_NAME}:${BUILDKITE_BUILD_NUMBER}