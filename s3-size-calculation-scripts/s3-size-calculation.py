################################################################################
##    FILE:  	s3-size-calculation.py                                        ##
##                                                                            ##
##    NOTES: 	This script calculates size of all S3 buckets                 ##
##                                                                            ##
##    AUTHOR:	Stepan Litsevych                                              ##
##                                                                            ##
##    Copyright 2020 - Baxter Planning Systems, Inc. All rights reserved      ##
################################################################################

import boto3
import datetime

class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

##########################################

def humansize(nbytes):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    i = 0
    while nbytes >= 1024 and i < len(suffixes)-1:
        nbytes /= 1024.
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[i])

def cw(region: str, cws: dict = {}):
    if region not in cws:
        cws[region] = boto3.client('cloudwatch', region_name = region)

    return cws[region]

def bucket_stats(name, date):
    results = {}

    for metric_name, storage_type in measurable_metrics:
        for region in regions:
            metrics = cw(region).get_metric_statistics(
                Namespace = 'AWS/S3',
                MetricName = metric_name,
                StartTime = date - datetime.timedelta(days = 365),
                EndTime = date,
                Period = 86400,
                Statistics = ['Average'],
                Unit='Bytes',
                Dimensions = [
                    {'Name': 'BucketName', 'Value': name},
                    {'Name': 'StorageType', 'Value': storage_type},
                ]
            )

            if metrics['Datapoints']:
                bucket_size_bytes = metrics['Datapoints'][-1]['Average']
                results[metric_name] = bucket_size_bytes
                continue

    return results

if __name__ == '__main__':
    regions = ['us-east-1', 'us-west-2', 'us-east-2']
    measurable_metrics = [('BucketSizeBytes', 'StandardStorage')]
    s3 = boto3.resource('s3')
    date = datetime.datetime.utcnow().replace(hour = 0, minute = 0, second = 0, microsecond = 0)

    print(color.UNDERLINE + 'Name'.ljust(46) + "|" + 'Size'.rjust(26) + color.END)

    for bucket in sorted(s3.buckets.all(), key = lambda bucket: bucket.name):
        results = bucket_stats(bucket.name, date)
        size=int(results.get('BucketSizeBytes', 0))
        print("|" + color.GREEN + bucket.name.ljust(45) + color.END + "|" + color.PURPLE + humansize(size).rjust(25) + color.END + "|")