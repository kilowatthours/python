################################################################################
##    FILE:  	department-tag-remove-rename-tagging.py                       ##
##                                                                            ##
##    NOTES: 	Script to rename or remove specific Department tags           ##
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
ec2client = boto3.client('ec2', region_name='us-west-2')

def resource_parser_delete(filters, **scope):
    try:
        for svc in scope.values():
            if svc == 'ec2':
                service = ec2.instances
                filtered_list_delete(service, filters)
            elif svc == 'snapshot':
                service = ec2.snapshots
                filtered_list_delete(service, filters)
            elif svc == 'ami':
                service = ec2.images
                filtered_list_delete(service, filters)
            elif svc == 'volumes':
                service = ec2.volumes
                filtered_list_delete(service, filters)
            else:
                print(f"{color.RED}Scope has not been properly defined: scope_1='ec2', scope_2='snapshot', scope_3='ami', scope_4='volumes'{color.END}")
                exit()

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def filtered_list_delete(service, filters):
    try:
        filtered_list = [
            resource for resource in service.filter(Filters=filters).all()]
        for resource in filtered_list:
            if 'Department' in [tagkey['Key'] for tagkey in resource.tags]:
                if not DEBUG:
                    print(
                        f"{color.DARKCYAN}--removing {color.CYAN}\"Department\"{color.END}{color.DARKCYAN} tag for{color.END} {color.CYAN}{resource.id}{color.END}")
                    ec2client.delete_tags(
                        Resources=[resource.id],
                        Tags=[{'Key': 'Department'}]
                    )
                else:
                    print(f"{color.RED}DEBUG MODE: {color.DARKCYAN}--removing {color.CYAN}\"Department\"{color.END}{color.DARKCYAN} tag for{color.END} {color.CYAN}{resource.id}{color.END}")

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def remove_tagging(remove_departments):
    scope = dict(scope1='ec2', scope2='snapshot',
                 scope3='ami', scope4='volumes')
    try:
        for department in remove_departments:
            print(f"{color.GREEN}Parsing {color.PURPLE}{department}{color.END}{color.GREEN} department tag{color.END}")
            filters = [{'Name': 'tag:Department', 'Values': [department]}]
            resource_parser_delete(filters, **scope)

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def resource_parser_rename(filters, old_department_value, new_department_value, **scope):
    try:
        for svc in scope.values():
            if svc == 'ec2':
                service = ec2.instances
                filtered_list_rename(
                    service, filters, old_department_value, new_department_value)
            elif svc == 'snapshot':
                service = ec2.snapshots
                filtered_list_rename(
                    service, filters, old_department_value, new_department_value)
            elif svc == 'ami':
                service = ec2.images
                filtered_list_rename(
                    service, filters, old_department_value, new_department_value)
            elif svc == 'volumes':
                service = ec2.volumes
                filtered_list_rename(
                    service, filters, old_department_value, new_department_value)
            else:
                print(f"{color.RED}Scope has not been properly defined: scope_1='ec2', scope_2='snapshot', scope_3='ami', scope_4='volumes'{color.END}")
                exit()

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def filtered_list_rename(service, filters, old_department_value, new_department_value):
    try:
        filtered_list = [resource for resource in service.filter(Filters=filters).all()]
        for resource in filtered_list:
            resource_name = [tag['Value'] for tag in resource.tags if tag['Key'] == 'Name'][0]
            if 'Department' in [tagkey['Key'] for tagkey in resource.tags]:
                if old_department_value in [tagvalue['Value'] for tagvalue in resource.tags]:
                    if not DEBUG:
                        print(
                            f"--changing {color.CYAN}{old_department_value}{color.END} department tag with {color.DARKCYAN}{new_department_value}{color.END} for {color.YELLOW}{resource.id} ({resource_name}) {color.END}")
                        ec2.create_tags(
                                        Resources=[resource.id],
                                        Tags=[{'Key': 'Department', 'Value': new_department_value}]
                                        )
                    else:
                        print(f"{color.RED}DEBUG MODE: {color.END}--changing {color.CYAN}{old_department_value}{color.END} department tag with {color.DARKCYAN}{new_department_value}{color.END} for {color.YELLOW}{resource.id} ({resource_name}) {color.END}")

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def rename_tagging(rename_department, rename_value):
    scope = dict(scope1='ec2', scope2='snapshot',
                 scope3='ami', scope4='volumes')
    try:
        print(f"{color.GREEN}Parsing {color.PURPLE}{rename_department}{color.END}{color.GREEN} department tag{color.END}")
        filters = [{'Name': 'tag:Department', 'Values': [rename_department]}]
        resource_parser_rename(filters, rename_department, rename_value, **scope)

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error

##########################################
parser = argparse.ArgumentParser()
parser.add_argument("--apply", "-A", "--true", default=True, dest='debug', action='store_false')
args = parser.parse_args()
DEBUG = args.debug

#############################################################################
####### Indicate departments/values and uncomment appropriate function ######
#############################################################################

remove_departments = ["", "", "", ""]

rename_department = ""
rename_value = ""

##########################################

if __name__ == '__main__':
    remove_tagging(remove_departments)
    rename_tagging(rename_department, rename_value)
