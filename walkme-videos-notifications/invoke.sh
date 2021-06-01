#!/usr/bin/env bash

######################################################################################
##    FILE:  	invoke.sh                                                           ##
##                                                                                  ##
##    NOTES: 	This script invokes WalkmeVideosNotification function               ##
##                                                                                  ##
##    AUTHOR:	Stepan Litsevych                                                    ##
##                                                                                  ##
##    Copyright 2020 - Baxter Planning Systems, Inc. All rights reserved            ##
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

    # assign local variables
    local -r EVENT_FILE="event.json"
    local -r ENV_QUALIFIER=${1}

    # make sure that ENV_QUALIFIER argument has been passed and EVENT_FILE exists
    if [[ -z ${ENV_QUALIFIER} ]] || ! [[ -f ${EVENT_FILE} ]]; then 
        echo -e "\${EVENT_FILE} could not be found or \${ENV_QUALIFIER} has not been passed \n
event file: ${EVENT_FILE} \n 
env qualifier: ${ENV_QUALIFIER}"
        exit 1
    fi

    for command in aws
    do
      if ! [ -x "$(command -v ${command})" ]; then
        echo -e "${command} does not exist"
      fi
    done

    # invoke function using awscli
    aws lambda invoke \
    --region us-west-2 \
    --function-name WalkmeVideosNotification-${ENV_QUALIFIER} \
    --qualifier ${ENV_QUALIFIER} \
    --payload file://${EVENT_FILE} \
    response.json

    rm -f response.json

}

# entrypoint
main "$@"