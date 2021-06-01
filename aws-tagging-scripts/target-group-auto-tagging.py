################################################################################
##    FILE:  	target-group-auto-tagging.py                                  ##
##                                                                            ##
##    NOTES: 	Script to automatically apply tags for TG's of LB's           ##
##                                                                            ##
##    AUTHOR:	Stepan Litsevych                                              ##
##                                                                            ##
##    Copyright 2020 - Baxter Planning Systems, Inc. All rights reserved      ##
################################################################################

import boto3
import json
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


elb = boto3.client('elbv2')
tgs = elb.describe_target_groups()['TargetGroups']


def tag_tg():
    try:
        for tg in tgs:
            tg_arn = tg['TargetGroupArn']
            tg_name = tg['TargetGroupName']
            lb_arn = tg['LoadBalancerArns']
            if lb_arn:
                print(f"{color.GREEN}Creating tags for target group {color.CYAN}{tg_name}{color.END}")
                nametag = {
                    'Key': 'Name',
                    'Value': tg_name
                }
                tags = process_lb_tags(lb_arn)
                tags.append(nametag)
                
                if tags:
                    tagger(tg_arn, tags)

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def process_lb_tags(lb_arn):
    lbs = elb.describe_load_balancers(LoadBalancerArns=lb_arn)
    try:
        for lb in lbs['LoadBalancers']:
            tags = elb.describe_tags(ResourceArns=lb_arn)['TagDescriptions'][0]['Tags']
            print(f"{color.DARKCYAN}LB: {color.CYAN}{lb['LoadBalancerName']}{color.END}")
            lbtags = []
            tags_list = ['Env', 'Department', 'Customers', 'Cluster', 'Owner',
                'Id', 'tenant', 'stage', 'Project', 'Class', 'Role', 'application']
            for tag in tags:
                for item in tags_list:
                    if tag['Key'] == item:
                        lbtags.append(tag)
                    if tag['Key'] == 'Name':
                        lb_nametag = {
                            'Key': 'LB_Name',
                            'Value': tag['Value']
                        }
                        lbtags.append(lb_nametag)
                        
            if lbtags:
                return lbtags

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def tagger(tg_arn, tags):
    try:
        if not DEBUG:
            elb.add_tags(ResourceArns=[tg_arn], Tags=tags)
        else:
            print(f"{color.RED}DEBUG mode{color.END}")
            print(json.dumps(tags, indent=1))

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
    tag_tg()
