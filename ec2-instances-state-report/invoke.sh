#!/usr/bin/env bash

######################################################################################
##    FILE:  	invoke.sh                                                             ##
##                                                                                  ##
##    NOTES: 	This script invokes EC2EnvStatusReport function                       ##
##                                                                                  ##
##    AUTHOR:	Stepan Litsevych                                                      ##
##                                                                                  ##
##    Copyright 2021 - Baxter Planning Systems, Inc. All rights reserved            ##
######################################################################################

###
### Bootstrap stage ###
###
set -o errexit
set -o pipefail

###
### Script stage ###
###

# Declare main function
function main {

    # make sure that we're in the script directory
    cd $(dirname $0)

    for command in aws
    do
      if ! [ -x "$(command -v ${command})" ]; then
        echo -e "${command} does not exist"
      fi
    done

    # invoke function using awscli
    aws lambda invoke \
    --region us-west-2 \
    --function-name ec2-instances-state-report \
    --qualifier PROD \
    --invocation-type Event\
    --payload '{}' \
    response.json

    rm -f response.json
}

# entrypoint
main 