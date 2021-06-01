################################################################################
##    FILE:  	department-tag-auto-tagging.py                                ##
##                                                                            ##
##    NOTES: 	Script to create Department tag based on Env tag              ##
##              for EC2 resources:                                            ##
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

def resource_parser(filters, tags, **scope):
    try:
        for svc in scope.values():
            if svc == 'ec2':
                service = ec2.instances
                filtered_list(service, filters, tags)
            elif svc == 'snapshot':
                service = ec2.snapshots
                filtered_list(service, filters, tags)
            elif svc == 'ami':
                service = ec2.images
                filtered_list(service, filters, tags)
            elif svc == 'volumes':
                service = ec2.volumes
                filtered_list(service, filters, tags)
            else:
                print(f"{color.RED}Scope has not been properly defined: scope_1='ec2', scope_2='snapshot', scope_3='ami', scope_4='volumes'{color.END}")
                exit()

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def filtered_list(service, filters, tags):
    try:
        filtered_list = [
            resource for resource in service.filter(Filters=filters).all()]
        for resource in filtered_list:
            resource_name = [tag['Value']
                             for tag in resource.tags if tag['Key'] == 'Name'][0]
            if 'Department' not in [tagkey['Key'] for tagkey in resource.tags]:
                if not DEBUG:
                    print(f"{color.DARKCYAN}--creating {color.CYAN}\"Department\"{color.END}{color.DARKCYAN} tag for{color.END} {color.CYAN}{resource.id} ({resource_name}){color.END}")
                    ec2.create_tags(
                        Resources=[resource.id],
                        Tags=tags
                    )
                else:
                    print(f"{color.RED}DEBUG MODE: {color.END}{color.DARKCYAN}--creating {color.END}{color.CYAN}\"Department\"{color.END}{color.DARKCYAN} tag for{color.END} {color.CYAN}{resource.id}{color.END}")

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def department_tagging(departments):
    
    opsfilters = [{'Name': 'tag:Env', 'Values': ['qa', 'ops']}]
    prodfilters = [{'Name': 'tag:Env', 'Values': ['prd', 'uat', 'sim', 'prodtest']}]
    devfilters = [{'Name': 'tag:Env', 'Values': ['trn', 'dev', 'demo', 'ins']}]
    beanstalkfilters = [{'Name': 'tag:stage', 'Values': ['Prd', 'Tgt', 'Dev']}]

    scope = dict(scope1='ec2', scope2='snapshot',
                 scope3='ami', scope4='volumes')
    try:
        for department in departments:
            print(f"{color.GREEN}Parsing {color.PURPLE}{department}{color.END}{color.GREEN} department tag{color.END}")
            tags = [{
                "Key": "Department",
                "Value": "%s" % (department)
            }]
            if department == "Development":
                filters = devfilters
                resource_parser(filters, tags, **scope)
            elif department == "Production":
                filters = prodfilters
                resource_parser(filters, tags, **scope)
            elif department == "Operations":
                filters = opsfilters
                resource_parser(filters, tags, **scope)
            elif department == "Beanstalk":
                filters = beanstalkfilters
                tags = [{
                    "Key": "Department",
                    "Value": "%s" % (department)
                }]
                
                resource_parser(filters, tags, **scope)

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error

##########################################


parser = argparse.ArgumentParser()
parser.add_argument("--apply", "-A", "--true", default=True, dest='debug', action='store_false')
parser.add_argument("--departments", nargs="+", dest='departments',
                    default=["Development", "Production", "Operations", "Beanstalk"])
args = parser.parse_args()

DEBUG = args.debug
departments = args.departments

##########################################

if __name__ == '__main__':
    department_tagging(departments)
