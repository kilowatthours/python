################################################################################
##    FILE:  	ami-manual-tagging.py                                         ##
##                                                                            ##
##    NOTES: 	Script to manually apply tags for EC2 AMI's and their         ##
##              snapshots based on corresponding instance tags                ##
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

def image_tagger(filters):
    images = ec2client.describe_images(Filters=filters)
    try:
        for image in images['Images']:
            image_Id = image['ImageId']
            image_name = [tag['Value'] for tag in image['Tags'] if tag['Key'] == 'Name'][0]
            if not DEBUG and not delete:
                print(f"{color.GREEN}--creating tags for {color.END}{color.DARKCYAN} {image_Id} ({image_name}) {color.END}")
                ec2client.create_tags(Resources=[image_Id], Tags=tags)
            elif not DEBUG and delete:
                print(f"{color.GREEN}--deleting tags for {color.END}{color.DARKCYAN} {image_Id} ({image_name}) {color.END}")
                ec2client.delete_tags(DryRun=False, Resources=[image_Id], Tags=tags)                
            elif DEBUG and delete:
                print(f"{color.CYAN}DRY-RUN MODE: --deleting tags for {color.END}{color.DARKCYAN} {image_Id} ({image_name}) {color.END}")
                print(f"{tags}")
            else:
                print(f"{color.RED}DEBUG MODE: {color.END}{color.CYAN}--creating tags for {color.END}{color.DARKCYAN}{image_Id}{color.END}")
                print(f"{tags}")
                
            snap_tagger(image_Id)
            
    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def snap_tagger(imageId):
    images = ec2client.describe_images(ImageIds=[imageId], Owners=['461796779995'])
    try:
        for ami in images['Images']:
            print(f"{color.DARKCYAN}Parsing snaphots of: {str(imageId)}{color.END}")
            for snapshot in ami['BlockDeviceMappings']:
                snapshotid = snapshot['Ebs']['SnapshotId']
                print(f"{color.CYAN}--snapshot: {str(snapshotid)}{color.END}\n")
                if not DEBUG and not delete:
                    ec2client.create_tags(Resources=[snapshotid], Tags=tags)
                elif not DEBUG and delete:
                    ec2client.delete_tags(DryRun=False, Resources=[snapshotid], Tags=tags)
                else:
                    pass

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def resource_parser(images):
    try:
        for image in images:
            filters = [{'Name': 'tag:Name', 'Values': [image]}]
            print(f"Checking {color.GREEN}{image}{color.END}")
            image_tagger(filters)

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error

##########################################
class StoreDictKeyPair(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self._nargs = nargs
        super(StoreDictKeyPair, self).__init__(
            option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        listtags = []
        print("values: {}".format(values))
        for kv in values:
            k, v = kv.split("=")
            tags = {}
            tags["Key"] = k
            tags["Value"] = v
            listtags.append(tags)
        setattr(namespace, self.dest, listtags)

##########################################

parser = argparse.ArgumentParser()
parser.add_argument("--apply", "-A", default=True, dest='debug', action='store_false')
parser.add_argument("--delete", "-D", default=False, dest='delete', action='store_true')
parser.add_argument("--images", nargs="+", dest='images', default=[""])
parser.add_argument("--tags", dest="tags", action=StoreDictKeyPair, nargs="+", metavar="KEY=VAL")
args = parser.parse_args()

DEBUG = args.debug
delete = args.delete
images = args.images
tags = args.tags

##########################################

if __name__ == '__main__':
    resource_parser(images)
