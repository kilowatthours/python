################################################################################
##    FILE:  	elb-manual-tagging.py                                         ##
##                                                                            ##
##    NOTES: 	Script to create custom tags for ALB's                        ##
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

def tag_lb(lbalancers, tags):

    lbs = elb.describe_load_balancers()
    
    try:
        for lb in lbs['LoadBalancers']:
            arn = lb['LoadBalancerArn']
            lb_name = lb['LoadBalancerName']
            for lbalancer in lbalancers:
                if lb_name == lbalancer:
                    print(f"{color.GREEN}\nTagging {color.CYAN}{lb_name}{color.END}")
                    tagger(arn, tags)

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def tagger(arn, tags):
    try:
        if not DEBUG and not delete:
            print(f"{color.GREEN}Creating tags{color.END}")
            print(json.dumps(tags, indent=1))
            elb.add_tags(ResourceArns=[arn], Tags=tags)
        elif not DEBUG and delete:
            print(f"{color.RED}Removing tags{color.END}")
            tagkey = [tag['Key'] for tag in tags]
            elb.remove_tags(ResourceArns=[arn], TagKeys=tagkey)
        elif DEBUG:
            print(f"--{color.RED}DEBUG{color.END}--")
            print(arn)
            print(json.dumps(tags, indent=1))
        else:
            pass

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


parser = argparse.ArgumentParser()
parser.add_argument("--apply", "-A", "--true", default=True, dest='debug', action='store_false')
parser.add_argument("--delete", "-D", default=False, dest='delete', action='store_true')
parser.add_argument("--resources", "--lbs", "--balancers", nargs="+", dest='resources', default=[""])
parser.add_argument("--tags", dest="tags", action=StoreDictKeyPair, nargs="+", metavar="KEY=VAL")
args = parser.parse_args()

DEBUG = args.debug
delete = args.delete
lbalancers = args.resources
tags = args.tags

##########################################

if __name__ == '__main__':
    tag_lb(lbalancers, tags)
