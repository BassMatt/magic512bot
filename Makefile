DOCKER_USERNAME=bassmatt
APP_NAME=card-lender

GIT_HASH ?= $(shell git log --format="%h" -n 1)
build:
         docker build --tag ${DOCKER_USERNAME}/${APPLICATION_NAME}:${GIT_HASH} .

release:
         docker pull ${DOCKER_USERNAME}/${APPLICATION_NAME}:${GIT_HASH}
         docker tag  ${DOCKER_USERNAME}/${APPLICATION_NAME}:${GIT_HASH} ${DOCKER_USERNAME}/${APPLICATION_NAME}:latest
         docker push ${DOCKER_USERNAME}/${APPLICATION_NAME}:latest
 
push:
         docker push ${DOCKER_USERNAME}/${APPLICATION_NAME}:${GIT_HASH}