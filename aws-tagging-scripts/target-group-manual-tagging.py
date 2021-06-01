################################################################################
##    FILE:  	target-group-manual-tagging.py                                ##
##                                                                            ##
##    NOTES: 	Script to apply tags for TG's of specified LB's               ##
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

def tag_tg(lbalancer):
    lbs = elb.describe_load_balancers()
    try:
        for lb in lbs['LoadBalancers']:
            if lbalancer == lb['LoadBalancerName']:
                lb_arn = lb['LoadBalancerArn']
                tgs = elb.describe_target_groups(LoadBalancerArn=lb_arn)['TargetGroups']
                for tg in tgs:
                    if tg:
                        tg_name = tg['TargetGroupName']
                        print(f"{color.GREEN}Tagging target group {color.CYAN}{tg_name}{color.END}")
                        nametag = {
                            'Key': 'Name',
                            'Value': tg_name
                        }
                        tags = process_lb_tags(tg['LoadBalancerArns'])
                        tags.append(nametag)
                        if tags:
                            tagger(tg['TargetGroupArn'], tags)

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
        if not DEBUG and not delete:
            print(f"{color.GREEN}Creating tags{color.END}")
            elb.add_tags(ResourceArns=[tg_arn], Tags=tags)
        elif not DEBUG and delete:
            print(f"{color.GREEN}Removing tags{color.END}")
            elb.remove_tags(ResourceArns=[tg_arn], Tags=tags)
        elif DEBUG:
            print(json.dumps(tags, indent=1))

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error

##########################################


parser = argparse.ArgumentParser()
parser.add_argument("--apply", "-A", "--true", default=True, dest='debug', action='store_false')
parser.add_argument("--lb", nargs="?", dest='lbalancer', default='')
parser.add_argument("--delete", "-D", default=False, dest='delete', action='store_true')
args = parser.parse_args()

DEBUG = args.debug
lbalancer = args.lbalancer
delete = args.delete
##########################################

if __name__ == '__main__':
    tag_tg(lbalancer)
