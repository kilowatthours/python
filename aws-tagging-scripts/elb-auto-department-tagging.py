################################################################################
##    FILE:  	elb-auto-department-tagging.py                                ##
##                                                                            ##
##    NOTES: 	Script to create Department tag based on Env tag for ALB's    ##
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
lbs = elb.describe_load_balancers()


def tag_lb():
    dev_tags = {'dev', 'demo', 'ins', 'tst'}
    ops_tags = {'qa', 'ops'}
    prd_tags = {'prd', 'prodtest', 'uat', 'sim'}
    try:
        for lb in lbs['LoadBalancers']:
            arn = lb['LoadBalancerArn']
            lb_name = lb['LoadBalancerName']
            tags = elb.describe_tags(ResourceArns=[arn])['TagDescriptions'][0]['Tags']
            print(f"{color.GREEN}Creating tags for {color.CYAN}{lb_name}{color.END}")
            newtags = []
            nametag = {
                'Key': 'Name',
                'Value': lb_name
            }
            newtags.append(nametag)
            for tag in tags:
                if tag['Key'] == 'Env':
                    newtags.append(tag)
                    if tag['Value'] in dev_tags:
                        deptag = {
                            'Key': 'Department',
                            'Value': 'Development'
                        }
                    elif tag['Value'] in ops_tags:
                        deptag = {
                            'Key': 'Department',
                            'Value': 'Operations'
                        }
                        newtags.append(deptag)
                    elif tag['Value'] in prd_tags:
                        deptag = {
                            'Key': 'Department',
                            'Value': 'Production'
                        }
                        newtags.append(deptag)
                if tag['Key'] == 'Customers':
                    newtags.append(tag)

            if newtags:
                tagger(arn, newtags)

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def tagger(arn, tags):
    try:
        if not DEBUG:
            elb.add_tags(ResourceArns=[arn], Tags=tags)
        else:
            print("------")
            print(arn)
            print(json.dumps(tags, indent=1))
            print("------")

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
    tag_lb()
