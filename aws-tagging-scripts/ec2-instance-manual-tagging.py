################################################################################
##    FILE:  	ec2-instance-manual-tagging.py                                ##
##                                                                            ##
##    NOTES: 	Script to create tags for instances and their volumes         ##
##              based on resource names                                       ##
##                                                                            ##
##    AUTHOR:	Stepan Litsevych                                              ##
##                                                                            ##
##    Copyright 2020 - Baxter Planning Systems, Inc. All rights reserved      ##
################################################################################

import boto3
import argparse
import json


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

def print_message(message):
    try:
        if DEBUG:
            messagecolor = color.RED
            if message == 'Running':
                message = "Running in DEBUG mode"
                print(f'{messagecolor}{message}\n{"=" * len(message)}\n{color.END}')
                
            elif message == 'Finished':
                message = "Finished in DEBUG mode"
                print(f'{messagecolor}\n{"=" * len(message)}\n{message}{color.END}')
                
        elif not DEBUG:
            messagecolor = color.GREEN
            if message == 'Running':
                message = "Running in ACTIVE mode"
                print(f'{messagecolor}{message}\n{"=" * len(message)}\n{color.END}')
            elif message == 'Finished':
                message = "Finished in ACTIVE mode"
                print(f'{messagecolor}\n{"=" * len(message)}\n{message}{color.END}')
                
        else:
            print('Cannot define DEBUG status')
            exit()
    
    except Exception as error:
        print(f'Something went wrong with print_message: {str(error)}')
        exit()


def tagging(resourceid: str = None, tags: list = None) -> bool:
    try:
        if not DEBUG and not delete:
            print(f"{color.DARKCYAN}--creating tags for {color.CYAN}{resourceid} {color.END}")
            ec2.create_tags(
                        Resources=[resourceid],
                        Tags=tags
                        )
            return True
        
        elif not DEBUG and delete:
            print(f"{color.DARKCYAN}--removing tags for {color.CYAN}{resourceid} {color.END}")
            ec2client.delete_tags(
                Resources=[resourceid],
                Tags=tags
            )
            return True
        
        elif DEBUG:
            print(f"{color.RED}DEBUG{color.END}: {color.DARKCYAN}--tagging {color.CYAN}{resourceid} {color.END}")
            return True

    except Exception as error:
        print(f"{color.RED}Encountered errors with tagging: {str(error)}")
        return False
        

def instance_handler(instances, input_tags):
    try:
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_name = [tag['Value'] for tag in instance['Tags'] if tag['Key'] == 'Name'][0]
                
                print(f"{color.GREEN}-parsing instance: {color.CYAN}{instance_name}{color.END}")
                
                if tagging(resourceid=instance_id, tags=input_tags) is True:
                    
                    if not delete:
                        instance_tags = []
                        tags_list = ['Name', 'Env', 'Department', 'Customers', 'Cluster', 'Owner',
                                    'Id', 'tenant', 'stage', 'Project', 'Class', 'Role', 'application']
                        
                        for tag in instance['Tags']:
                            for item in tags_list:
                                if tag['Key'] == item:
                                    instance_tags.append(tag)
                                    
                        if instance_tags:
                            vol_and_eni_parser(instance_id, tags=instance_tags)
                            vol_and_eni_parser(instance_id, tags=input_tags)
                            
                    elif delete:
                        vol_and_eni_parser(instance_id, tags=input_tags)
                        

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def vol_and_eni_parser(instance_id, tags):
    volumes = ec2.volumes.filter(Filters=[{'Name': 'attachment.instance-id', 'Values': [instance_id]}]).all()
    enis = ec2.network_interfaces.filter(Filters=[{'Name': 'attachment.instance-id', 'Values': [instance_id]}]).all()
    try:
        for volume in volumes:
            tagging(resourceid=volume.id, tags=tags)
        
        for eni in enis:
            tagging(resourceid=eni.id, tags=tags)

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def resource_parser(resources, input_tags):
    try:
        print_message('Running')
        for resource in resources:
            filters = [{'Name': 'tag:Name', 'Values': [resource]}]
            instances = ec2client.describe_instances(Filters=filters)
            print(f"Checking {color.GREEN}{resource}{color.END}")
            instance_handler(instances, input_tags)
        
        print_message('Finished')

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
        # print("values: {}".format(values))
        for kv in values:
            k, v = kv.split("=")
            tags = {}
            tags["Key"] = k
            tags["Value"] = v
            listtags.append(tags)
        setattr(namespace, self.dest, listtags)


parser = argparse.ArgumentParser()
parser.add_argument("--apply", "-A", "--true", default=True, dest='debug', action='store_false')
parser.add_argument("--resources", "--servers", "--instances", "-I", "-S", "-R", nargs="+", dest='resources', default=[""])
parser.add_argument("--tags", "-T", dest="input_tags", action=StoreDictKeyPair, nargs="+", metavar="KEY=VAL")
parser.add_argument("--delete", "-D", default=False, dest='delete', action='store_true')
args = parser.parse_args()

DEBUG = args.debug
delete = args.delete
resources = args.resources
input_tags = args.input_tags

##########################################

if __name__ == '__main__':
    resource_parser(resources, input_tags)
