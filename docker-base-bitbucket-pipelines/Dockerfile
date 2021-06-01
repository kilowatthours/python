FROM python:3.6.12-slim-stretch
RUN apt-get update && apt-get install -y zip && \
pip install awscli pyflakes boto3 python-lambda-local 2>&1 > /dev/null