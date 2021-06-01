################################################################################
##    FILE:  	volume-manual-tagging.py                                      ##
##                                                                            ##
##    NOTES: 	Script to create tags for volumes based on EC2 instance name  ##
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

ec2 = boto3.resource('ec2', region_name='us-west-2')
ec2client = boto3.client('ec2')


def instance_parser(resources):
    filters = [{'Name': 'tag:Name', 'Values': resources}]
    instances = ec2client.describe_instances(Filters=filters)
    try:
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_name = [tag['Value'] for tag in instance['Tags'] if tag['Key'] == 'Name'][0]
                tags = []
                tags_list = ['Name', 'Env', 'Department', 'Customers', 'Cluster', 'Owner',
                             'Id', 'tenant', 'stage', 'Project', 'Class', 'Role', 'application']
                for tag in instance['Tags']:
                    for item in tags_list:
                        if tag['Key'] == item:
                            tags.append(tag)
                print(
                    f"{color.DARKCYAN}Checking {instance_id} ({instance_name}){color.END}")
                volume_parser(instance_id, tags)

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def volume_parser(instance_id, tags):
    volumes = ec2.volumes.all()
    try:
        for volume in volumes:
            for attachments in volume.attachments:
                if attachments['InstanceId'] == instance_id:
                    volumeid = attachments['VolumeId']
                    if not DEBUG and not delete:
                        print(f"{color.CYAN}--creating tags for {color.END}{color.DARKCYAN}{volumeid}{color.END}")
                        ec2client.create_tags(Resources=[volumeid], Tags=tags)
                    if not DEBUG and not delete:
                        print(f"{color.CYAN}--removing tags for {color.END}{color.DARKCYAN}{volumeid}{color.END}")
                        ec2client.delete_tags(Resources=[volumeid], Tags=tags)
                    else:
                        print(f"{color.RED}DEBUG MODE: {color.END}{color.CYAN}Tagging {color.END}{color.DARKCYAN}{volumeid}{color.END}")
                        print(f"{tags}")

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error

##########################################


parser = argparse.ArgumentParser()
parser.add_argument("--apply", "-A", "--true", default=True, dest='debug', action='store_false')
parser.add_argument("--resources", nargs="+", dest='resources', default=[""])
parser.add_argument("--delete", "-D", default=False, dest='delete', action='store_true')
args = parser.parse_args()

DEBUG = args.debug
resources = args.resources
delete = args.delete

##########################################

if __name__ == '__main__':
    instance_parser(resources)
