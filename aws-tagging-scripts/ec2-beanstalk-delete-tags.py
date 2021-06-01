################################################################################
##    FILE:  	ec2-beanstalk-delete-tags.py                                  ##
##                                                                            ##
##    NOTES: 	Script to delete tags for EC2 Beanstalk instances             ##
##                                                                            ##
##    AUTHOR:	Stepan Litsevych                                              ##
##                                                                            ##
##    Copyright 2020 - Baxter Planning Systems, Inc. All rights reserved      ##
################################################################################

import boto3
import argparse

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


def delete_tags(tags_to_delete: list):
    
    ec2client = boto3.client('ec2')
    instances = ec2client.describe_instances()
    
    for tag in tags_to_delete:
        print(f"{color.BOLD}Deleting tag: {str(tag)}{color.END}")
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_name = [tag['Value'] for tag in instance['Tags'] if tag['Key'] == 'Name'][0]
                tags = instance['Tags']
                if 'Beanstalk' in [tag['Value'] for tag in tags if tag['Key'] == 'Department']:
                    if tag in [tag['Key'] for tag in tags]:
                        print(f"{'-' * 3} {instance_name} {'-' * 3}")
                        if DEBUG:
                            print(f"{color.RED}DEBUG mode{color.END}")
                        else:
                            ec2client.delete_tags(Resources=[instance_id], Tags=[{"Key": tag}])
   
   
##########################################
parser = argparse.ArgumentParser()
parser.add_argument("--apply", "-A", default=True, dest='debug', action='store_false')
parser.add_argument("--tags", "-T", nargs="+", dest='tags', default=[""])
args = parser.parse_args()

DEBUG = args.debug
tags = args.tags
##########################################

if __name__ == '__main__':
    delete_tags(tags_to_delete=tags)