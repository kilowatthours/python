################################################################################
##    FILE:  	volume-auto-tagging.py                                        ##
##                                                                            ##
##    NOTES: 	Script to automatically apply tags for volumes without tags   ##
##              or without Department tag                                     ##
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

##########################################

def volume_parser():
    ec2 = boto3.resource('ec2', region_name='us-west-2')
    volumes = ec2.volumes.all()
    
    try:
        for vol in volumes:
            if vol.tags is None or 'Name' not in [tagkey['Key'] for tagkey in vol.tags]:
                for attachments in vol.attachments:
                    instance_id = attachments['InstanceId']
                    instance_parser(vol, instance_id)
            elif 'Name' in [tagkey['Key'] for tagkey in vol.tags] and 'Owner' in [tagkey['Key'] for tagkey in vol.tags] and 'Department' not in [tagkey['Key'] for tagkey in vol.tags]:
                volume_name, volume_owner = ''
                for tagkey in vol.tags:
                    if tagkey['Key'] == 'Name':
                        volume_name = tagkey['Value'] or ''
                    if tagkey['Key'] == 'Owner':
                        volume_owner = tagkey['Value'] or ''
                for attachments in vol.attachments:
                    instance_id = attachments['InstanceId']
                    instance_parser(instance_id, vol,
                                    volume_name, volume_owner)

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def instance_parser(instance_id, vol, volume_name=None, volume_owner=None):
    
    ec2client = boto3.client('ec2')
    instances = ec2client.describe_instances(InstanceIds=[instance_id])
    
    try:
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                tags = []
                tags_list = ['Name', 'Env', 'Department', 'Customers', 'Cluster', 'Owner',
                             'Id', 'tenant', 'stage', 'Project', 'Class', 'Role', 'application']
                instance_name = [tag['Value'] for tag in instance['Tags'] if tag['Key'] == 'Name'][0]
                for tag in instance['Tags']:
                    for item in tags_list:
                        if tag['Key'] == item:
                            if tag['Key'] == 'Name':
                                if volume_name:
                                    pass
                            if tag['Key'] == 'Owner':
                                if volume_owner:
                                    pass
                            tags.append(tag)
                    if tag['Key'] == 'Name':
                        if volume_name:
                            pass
                        else:
                            tags.append(tag)
                if tags:
                    print(
                        f"{color.CYAN}--creating tags for volumes of {color.END}{color.DARKCYAN}{instance_id} ({instance_name}){color.END}")
                    tagging(vol, tags)

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def tagging(vol, tags):
    try:
        if not DEBUG:
            print(f"{color.DARKCYAN}{vol.id}{color.END}")
            
            vol.create_tags(Tags=tags)
        else:
            print(f"{color.RED}DEBUG MODE: {color.END}{color.DARKCYAN}{vol.id}{color.END}")
            print(f"{tags}")

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error

##########################################

parser = argparse.ArgumentParser()
parser.add_argument("--apply", "-A", "--true", default=True, dest='debug', action='store_false')
args = parser.parse_args()
DEBUG = args.debug

##########################################

if __name__ == '__main__':
    volume_parser()
