.ONESHELL:

login:
	@aws ecr get-login-password --region us-west-2 | sudo docker login --username AWS --password-stdin 461796779995.dkr.ecr.us-west-2.amazonaws.com

image:
	@sudo docker build -t base-bitbucket-pipelines-stepan .

tag:
	@sudo docker tag base-bitbucket-pipelines-stepan:latest 461796779995.dkr.ecr.us-west-2.amazonaws.com/base-bitbucket-pipelines-stepan:latest

push:
	@sudo docker push 461796779995.dkr.ecr.us-west-2.amazonaws.com/base-bitbucket-pipelines-stepan:latest

build: login image tag push

.PHONY: login image tag push build