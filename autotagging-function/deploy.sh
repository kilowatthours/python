#!/usr/bin/env bash

######################################################################################
##    FILE:  	deploy.sh                                                             ##
##                                                                                  ##
##    NOTES: 	This script uploads lambda function's code and CF/SAM templates to S3 ##
##                                                                                  ##
##    AUTHOR:	Stepan Litsevych                                                      ##
##                                                                                  ##
##    Copyright 2020 - Baxter Planning Systems, Inc. All rights reserved            ##
######################################################################################

###
### Bootstrap stage ###
###
set -o errexit
set -o pipefail

# color vars
nocolor="\033[0m"
red="\033[0;31m"
green="\033[0;32m"
yellow="\033[0;33m"
blue="\033[0;34m"
magenta="\033[0;35m"

# log functions
function log {
  local -r level="$1"
  local -r message="$2"
  local -r timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  local -r script_name="$(basename "$0")"
  >&2 echo -e "${timestamp} [${level}] [$script_name] ${message}"
}

function log_info {
  local -r message="$1"
  log "${green}INFO${nocolor}" "${green}$message${nocolor}"
}

function log_error {
  local -r message="$1"
  log "${red}ERROR${nocolor}" "${red}$message${nocolor}"
}

function status {
  exit_code=$?
  local -r message="$1"

  if [[ ${exit_code} == 0 ]] ; then
    log_info "Passed: ${message}\n"
  else
    log_error "Failed: ${message}\n"
    exit 1
  fi
}

###
### Script stage ###
###

# Assign BITBUCKET_COMMIT var from cmd argument
BITBUCKET_COMMIT=${1}

# Declare function which will check consistency and validate python code and CFN template; once done it will zip the code of the function
function verify_validate_zip {

    for command in aws pyflakes zip python-lambda-local
    do
      if ! [ -x "$(command -v ${command})" ]; then
        log_error "${command} does not exist"
      fi
    done

    pyflakes main.py
    aws cloudformation validate-template --template-body file://autotagging-template.cfn.yaml 2>&1 > /dev/null
    zip code-${BITBUCKET_COMMIT}.zip main.py
}

# Declare function which will run the function locally using python-lambda-local and event.json imitating an event invocation and processing
function python_lambda_local_test {
    
    for file in event.json main.py
    do 
        if ! [[ -f ${file} ]]; then 
            log_error "${file} could not be found"
            exit 1
        fi 
    done

    python-lambda-local -f lambda_handler main.py event.json -t 360 &> result

    echo -e "Result: " && cat result
    if [[ `cat result | tail -1` == 'False' ]]; then
        log_error "Test event failed" && rm -f result
        exit 1
    elif [[ `cat result | tail -1` == 'True' ]]; then
        log_info "Test event succeeded" && rm -f result
    else :
    fi
}

# Declare main function
function main {

    # assign local variables
    local -r BUCKET_VIRGINIA="cf-templates-virginia/autotag_template"
    local -r BUCKET_OREGON="cf-templates-oregon-bp/autotag_template"
    local -r BITBUCKET_COMMIT=${1}

    # make sure that we're in the script directory
    cd $(dirname $0)

    # make sure that BITBUCKET_COMMIT argument has been passed
    if [[ -z ${BITBUCKET_COMMIT} ]] ; then
      log_error "BITBUCKET_COMMIT is empty"
      exit 1
    fi

    # run validation function and output its status
    verify_validate_zip ${BITBUCKET_COMMIT} ; status "verifying, validating and zipping function"

    # run testing function and output its status
    python_lambda_local_test; status "invoking python_lambda_local test"

    # if everything went well, copy template file and zip archive to S3 buckets in Oregon and Virginia
    for file in code-${BITBUCKET_COMMIT}.zip autotagging-template.cfn.yaml
    do
        aws s3 cp ${file} s3://${BUCKET_OREGON}/
        aws s3 cp ${file} s3://${BUCKET_VIRGINIA}/
    done
    
    # output uploading status
    status "uploading new code.zip and template to S3"

}

# entrypoint
main "$@"


