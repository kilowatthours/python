################################################################################
##    FILE:  	asg-manual-tagging.py                                        ##
##                                                                            ##
##    NOTES: 	Script to create tags for EC2 AutoScaling Groups;             ##
##              expects correct arguments from the command line               ##
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

asg = boto3.client('autoscaling', region_name='us-west-2')

def create_tag(resourceid, key, value):
    try:
        tag = [{
            'Key': key,
            'PropagateAtLaunch': True,
            'ResourceId': resourceid,
            'ResourceType': 'auto-scaling-group',
            'Value': value,
        }]

        if DEBUG:
            print(f"{color.RED}DEBUG mode: {color.END}--creating tag {color.BOLD}\'{key}\':\'{value}\'{color.END} for {color.PURPLE}{resourceid}{color.END}")
        else:
            print(f"--creating tag {color.BOLD}\'{key}\':\'{value}\'{color.END} for {color.PURPLE}{resourceid}{color.END}")
            
            asg.create_or_update_tags(Tags=tag)

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def asg_iterator(tagkey, tagvalue, resources=[""], **scope):
    
    paginator = asg.get_paginator('describe_auto_scaling_groups')
    asg_page_iterator = paginator.paginate(PaginationConfig={'PageSize': 100, 'NextToken': None})

    try:
        all_asg_instances = []
        for asg_page in asg_page_iterator:
            all_asg_instances += asg_page['AutoScalingGroups']

        for asgroup in all_asg_instances:
            asg_name = asgroup['AutoScalingGroupName']
            for svc in scope.values():
                # tag beanstalk groups
                if svc == 'beanstalk' or svc == 'eb' or svc == 'bean':
                    if 'stage' in [tagkey['Key'] for tagkey in asgroup['Tags']]:
                        create_tag(asg_name, tagkey, tagvalue)

                # tag with Department tag
                elif svc == 'department':
                    dev_tags = {'dev', 'demo', 'ins', 'tst'}
                    ops_tags = {'qa', 'ops'}
                    prd_tags = {'prd', 'prodtest', 'uat', 'sim'}

                    if 'Env' in [tagkey['Key'] for tagkey in asgroup['Tags']]:
                        for tag in asgroup['Tags']:
                            if tag['Value'] [ops_tags, dev_tags, prd_tags]:
                                create_tag(asg_name, tagkey, tagvalue)

                # tag with Env tag (skip Elastic Beanstalk)
                elif svc == 'env':
                    if 'Env' not in [tagkey['Key'] for tagkey in asgroup['Tags']] and 'stage' not in [tagkey['Key'] for tagkey in asgroup['Tags']]:
                        create_tag(asg_name, tagkey, tagvalue)

                # tag with any tag (make sure to pass asg name as resource)
                elif svc == 'new' or svc == 'dev' or svc == 'prd' or svc == 'ops':
                    for resource in resources:
                        if asg_name == resource:
                            create_tag(resource, tagkey, tagvalue)

                else:
                    print(f"{color.RED}Scope was not properly defined{color.END}")
                    exit()

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error

##########################################


parser = argparse.ArgumentParser()
parser.add_argument("--apply", "-A", "--true", default=True, dest='debug', action='store_false')
parser.add_argument("--tagkey", nargs="?", dest='tagkey', default='')
parser.add_argument("--tagvalue", nargs="?", dest='tagvalue', default='')
parser.add_argument("--scope", nargs="?", dest='scope', default='')
parser.add_argument("--resources" "--asgs", "--asg", nargs="+", dest='resources', default=[""])
args = parser.parse_args()

DEBUG = args.debug
tagkey = args.tagkey
tagvalue = args.tagvalue
scope = args.scope
resource = args.resources

##########################################

if __name__ == '__main__':
    asg_iterator(tagkey, tagvalue, resources=resource, scope=scope)
