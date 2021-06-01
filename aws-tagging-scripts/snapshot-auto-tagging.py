################################################################################
##    FILE:  	snapshot-auto-tagging.py                                      ##
##                                                                            ##
##    NOTES: 	Script to automatically apply tags for snapshots without tags ##
##              based on tags from volumes;                                   ##
##              also tags snapshots with unknown volume                       ##
##                                                                            ##
##    AUTHOR:	Stepan Litsevych                                              ##
##                                                                            ##
##    Copyright 2020 - Baxter Planning Systems, Inc. All rights reserved      ##
################################################################################

import boto3
import argparse
from botocore.exceptions import ClientError


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
ec2client = boto3.client('ec2', region_name='us-west-2')

def snapshot_parser():
    snapshots = ec2.snapshots.filter(OwnerIds=['461796779995']).all()
    try:
        for snap in snapshots:
            if snap.tags is None or 'Name' not in [tagkey['Key'] for tagkey in snap.tags]:
                if snap.volume_id == 'vol-ffffffff':
                    print(
                        f"{color.RED}Found vol-ffffffff volume: {snap.id}{color.END}")
                    unknown_tagging(snapshot=snap)
                else:
                    volume_parser(volume_id=snap.volume_id, snapshot=snap)

    except ClientError as clienterror:
        if clienterror.response['Error']['Code'] == 'InvalidVolume.NotFound':
            print(f"{color.RED}Found unknown volume: {snap.volume_id}{color.END}")
            unknown_tagging(snapshot=snap)
            snapshot_parser()
        else:
            print(f"{color.RED}Unexpected error: {clienterror}{color.END}")
    except Exception as error:
        print(f"{color.RED}Encountered errors:{color.END}")
        raise error


def volume_parser(volume_id, snapshot):
    volumes = ec2client.describe_volumes(VolumeIds=[volume_id])
    try:
        for vol in volumes['Volumes']:
            tags = []
            tags_list = ['Name', 'Env', 'Department', 'Customers', 'Cluster', 'Owner',
                         'Id', 'tenant', 'stage', 'Project', 'Class', 'Role', 'application']
            for tag in vol['Tags']:
                for item in tags_list:
                    if tag['Key'] == item:
                        tags.append(tag)
            if tags:
                print(f"{color.PURPLE}Parsing volume: {vol['VolumeId']}:")
                tagging(snapshot, tags)

    except Exception as error:
        print(f"{color.RED}Encountered errors:{color.END}")
        raise error


def tagging(snapshot, tags):
    try:
        if not DEBUG:
            print(f"{color.DARKCYAN}--creating tags for {snapshot.id}{color.END}")
            snapshot.create_tags(Tags=tags)
        else:
            print(
                f"{color.RED}DEBUG MODE: {color.END}{color.DARKCYAN}--creating tags for {snapshot.id}{color.END}")
            print(f"{color.BOLD}{tags}{color.END}")

    except Exception as error:
        print(f"{color.RED}Encountered errors:{color.END}")
        raise error


def unknown_tagging(snapshot):
    
    tags = [{
        "Key": "Name",
        "Value": "[unknown-volume]"
    },
        {
        "Key": "Env",
        "Value": "ops"
    },
        {
        "Key": "Department",
        "Value": "Operations"
    }]
    
    try:
        if not DEBUG:
            print(f"{color.DARKCYAN}--creating tags for {snapshot.id}{color.END}")
            snapshot.create_tags(Tags=tags)
        else:
            print(f"{color.RED}DEBUG MODE: {color.END}{color.DARKCYAN}--creating tags for {snapshot.id}{color.END}")
            print(f"{color.BOLD}{tags}{color.END}")

    except Exception as error:
        print(f"{color.RED}Encountered errors:{color.END}")
        raise error

##########################################


parser = argparse.ArgumentParser()
parser.add_argument("--apply", "-A", "--true", default=True, dest='debug', action='store_false')
args = parser.parse_args()
DEBUG = args.debug

##########################################

if __name__ == '__main__':
    snapshot_parser()
