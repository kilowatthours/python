#!/usr/bin/env bash

set -o errexit
set -o pipefail

ENV=$1

if [[ -z ${ENV} ]]; then echo "\$ENV is not defined; choose LOCAL or REMOTE"; exit 1; fi

function is_root_is_file {
  if [[ -z ${ENV} ]]; then echo "\$ENV is not defined; choose LOCAL or REMOTE"; exit 1; fi
  if [ "$(id -u)" != "0" ]; then echo "This script must be run as root or sudo!" 2>&1; exit 1; fi
}

function removing_agent {
    service awslogs stop && \
    rm -rfv /var/awslogs && \
    rm -fv /etc/cron.d/awslogs* && \
    rm -fv /etc/init.d/awslogs && \
    rm -fv /var/log/awslogs* 
}

function are_we_proceeding {
  read -p "would you like to remove agent? [yes|y|Yes or no|n|No]: " ANSWER

  for x in $ANSWER
  do
      case $x in 
          y|yes|Yes )
            :
            ;;
          no|n|No )
            echo "Ok, not this time"
            exit 1
            ;;
          * )
            echo "Please choose something"
            are_we_proceeding
            ;;
      esac
  done
}

function main {
    is_root_is_file

    if [[ $ENV == "LOCAL" ]]; then 
      are_we_proceeding
    elif [[ $ENV == "REMOTE" ]]; then
      :
    else
      echo "\$ENV is not defined; choose LOCAL or REMOTE"
      exit 1
    fi

    if [[ ${?} == 0 ]]; then removing_agent; fi
}

main "$@"