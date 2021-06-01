################################################################################
##    FILE:  	snapshot-manual-tagging.py                                    ##
##                                                                            ##
##    NOTES: 	Script to create tags for snapshots based on their names      ##
##              and tags of associated volumes                                ##
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
ec2client = boto3.client('ec2')


def resource_parser(resources):
    filters = [{'Name': 'tag:Name', 'Values': resources}]
    snapshots = ec2.snapshots.filter(OwnerIds=['461796779995'], Filters=filters).all()
    try:
        global snap
        for snap in snapshots:
            volumes = ec2client.describe_volumes(VolumeIds=[snap.volume_id])
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
                    snap_parser(snapshot=snap.id, tags=tags)

    except ClientError as clienterror:
        if clienterror.response['Error']['Code'] == 'InvalidVolume.NotFound':
            print(f"{color.RED}Found unknown volume: {snap.volume_id}{color.END}")
            unknown_tagging(snapshot=snap.id)
            resource_parser(resources)
        else:
            print("Unexpected error: %s" % clienterror)
    except Exception as error:
        print(color.RED + "Encountered errors" + color.END)
        raise error


def snap_parser(snapshot, tags):
    try:
        snapshots = ec2client.describe_snapshots(SnapshotIds=[snapshot])
        for snap in snapshots['Snapshots']:
            snapshotid = snap['SnapshotId']
            if not DEBUG and not delete:
                print(f"{color.DARKCYAN}--creating tags for {color.CYAN}{snapshotid}{color.END}")
                ec2client.create_tags(
                    Resources=[snapshotid],
                    Tags=tags
                )
            elif not DEBUG and delete:
                print(f"{color.DARKCYAN}--deleting tags for {color.CYAN}{snapshotid}{color.END}")
                ec2client.delete_tags(
                    Resources=[snapshotid],
                    Tags=tags
                )
            elif DEBUG:
                print(f"{color.RED}DEBUG MODE: {color.END}{color.DARKCYAN}--creating tags for {color.CYAN}{snapshotid}{color.END}")
                print(f"{tags}")

    except ClientError as clienterror:
        if clienterror.response['Error']['Code'] == 'InvalidParameterValue':
            print(f"{color.RED}Found empty snapshot {color.END}")
        else:
            print(f"{color.RED}Unexpected error: {clienterror}{color.END}")
    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
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
            print(f"{color.DARKCYAN}--creating tags for {snapshot}{color.END}")
            snapshot.create_tags(Tags=tags)
        else:
            print(f"{color.RED}DEBUG MODE: {color.END}{color.DARKCYAN}--creating tags for {snapshot}{color.END}")
            print(f"{color.BOLD}{tags}{color.END}")

    except Exception as error:
        print(f"{color.RED}Encountered errors:{color.END}")
        raise error

##########################################

parser = argparse.ArgumentParser()
parser.add_argument("--apply", "-A", "--true", default=True, dest='debug', action='store_false')
parser.add_argument("--delete", "-D", default=False, dest='delete', action='store_true')
parser.add_argument("--resources", nargs="+", dest='resources', default=[""])
args = parser.parse_args()

DEBUG = args.debug
delete = args.delete
resources = args.resources

##########################################

if __name__ == '__main__':
    resource_parser(resources)
