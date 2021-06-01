#!/bin/bash

################################################################################
##    FILE:  	s3-size-calculation.sh                                        ##
##                                                                            ##
##    NOTES: 	This script calculates size of all S3 buckets                 ##
##                                                                            ##
##    AUTHOR:	Stepan Litsevych                                              ##
##                                                                            ##
##    Copyright 2020 - Baxter Planning Systems, Inc. All rights reserved      ##
################################################################################

set -o errexit;
set -o nounset;

UE2_BUCKETS=(bp-ops-jenkins bp-prod-backup-secondary bps-dev-prototype)
UE1_BUCKETS=(bps-rundeck-backups bp-prophet-argus bp-infrastructure-us-east-1 bp-dev-menshen-mvp bp-dev-menshen bp-dev-bps aws-logs-461796779995-us-east-1 aws-codestar-us-east-1-461796779995 elasticbeanstalk-us-east-1-461796779995)
Total_num_of_buckets=`aws s3 ls s3:// | awk '{print $3}'| wc -l`
Total_num_of_buckets_in_UW2=`aws s3 ls s3:// | egrep -v "${UE1_BUCKETS[@]/#/-e }|${UE2_BUCKETS[@]/#/-e }" | awk '{print $3}'| wc -l`
Total_num_of_buckets_in_UE2=`aws s3 ls s3:// | egrep "${UE2_BUCKETS[@]/#/-e }" | awk '{print $3}'| wc -l`
Total_num_of_buckets_in_UE1=`aws s3 ls s3:// | egrep "${UE1_BUCKETS[@]/#/-e }" | awk '{print $3}'| wc -l`

OS_TYPE=`uname`
if [ ${OS_TYPE} == 'Darwin' ]; then
        Yesterday=`date -v-1d +%FT%H:%M`
        dbf_yes=`date -v-2d +%FT%H:%M`
elif [ ${OS_TYPE} == 'Linux' ]; then
        Yesterday=`date -d "1 day ago" '+%FT%H:%M'`
        dbf_yes=`date -d "2 day ago" '+%FT%H:%M'`
fi

function uswest2_buckets {
        for i in `aws s3 ls s3:// | awk '{print $NF}'| egrep -v ${UE1_BUCKETS[@]/#/-e }| egrep -v ${UE2_BUCKETS[@]/#/-e }` ; do  
                size=`aws cloudwatch get-metric-statistics --namespace AWS/S3 --region us-west-2 --metric-name BucketSizeBytes --dimensions Name=BucketName,Value=${i} Name=StorageType,Value=StandardStorage --start-time ${dbf_yes} --end-time ${Yesterday} --period 86400 --statistic Average | jq .Datapoints[0].Average`
                size_in_gb=`echo "scale=2;$size / 1024 / 1024 / 1024" | bc -l | sed -e 's/^\./0./'`
                if ! [ "${size_in_gb}" = "0" ]; then echo -e "${i}: ${size_in_gb} GB"; fi
        done
}

function useast2_buckets {       
        for i in `aws s3 ls s3:// | awk '{print $NF}'| egrep ${UE2_BUCKETS[@]/#/-e }` ; do  
                size=`aws cloudwatch get-metric-statistics --namespace AWS/S3 --region us-east-2 --metric-name BucketSizeBytes --dimensions Name=BucketName,Value=${i} Name=StorageType,Value=StandardStorage --start-time ${dbf_yes} --end-time ${Yesterday} --period 86400 --statistic Average | jq .Datapoints[0].Average`
                size_in_gb=`echo "scale=2;$size / 1024 / 1024 / 1024" | bc -l | sed -e 's/^\./0./'`
                if ! [ "${size_in_gb}" = "0" ]; then echo -e "${i}: ${size_in_gb} GB"; fi
        done
}

function useast1_buckets { 
        for i in `aws s3 ls s3:// | awk '{print $NF}'| egrep ${UE1_BUCKETS[@]/#/-e }` ; do  
                size=`aws cloudwatch get-metric-statistics --namespace AWS/S3 --region us-east-1 --metric-name BucketSizeBytes --dimensions Name=BucketName,Value=${i} Name=StorageType,Value=StandardStorage --start-time ${dbf_yes} --end-time ${Yesterday} --period 86400 --statistic Average | jq .Datapoints[0].Average`
                size_in_gb=`echo "scale=2;$size / 1024 / 1024 / 1024" | bc -l | sed -e 's/^\./0./'`
                if ! [ "${size_in_gb}" = "0" ]; then echo -e "${i}: ${size_in_gb} GB"; fi
        done
}

function main {
        printf "%s: %2d\n" "Total Number of s3 buckets" ${Total_num_of_buckets}
        printf "\n%s\n" "US-WEST-2 Region"
        printf "%s: %2d\n" "Total Number of s3 buckets in US-WEST-2 Region" ${Total_num_of_buckets_in_UW2}
        uswest2_buckets
        printf "\n%s\n" "US-EAST-2 Region"
        printf "%s: %2d\n" "Total Number of s3 buckets in US-EAST-2 Region" ${Total_num_of_buckets_in_UE2}
        useast2_buckets
        printf "\n%s\n" "US-EAST-1 Region"
        printf "%s: %2d\n" "Total Number of s3 buckets in US-EAST-1 Region" ${Total_num_of_buckets_in_UE1}
        useast1_buckets
}

main