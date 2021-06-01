################################################################################
##    FILE:  	jenkins-auto-tagging.py                                       ##
##                                                                            ##
##    NOTES: 	Script to create Env/Department tags for AMI's and Snapshots  ##
##              of Jenkins instance                                           ##
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


def tagging(resourceid, tags):
    try:
        if not DEBUG and not delete:
            print(f"{color.DARKCYAN}--creating tags for {color.CYAN}{resourceid}{color.END}")
            ec2client.create_tags(
                        Resources=[resourceid],
                        Tags=tags
                        )
        elif not DEBUG and delete:
            print(f"{color.DARKCYAN}--removing tags for {color.CYAN}{resourceid}{color.END}")
            ec2client.delete_tags(
                Resources=[resourceid],
                Tags=tags
            )
        elif DEBUG:
            print(f"{color.RED}DEBUG{color.END}: {color.DARKCYAN}--tagging {color.CYAN}{resourceid}{color.END}")

    except Exception as error:
        print(f"{color.RED}Encountered errors with tagging: {str(error)}")
        

def resource_parser(resources, tags, **scope):
    try:
        print_message('Running')
        for resource in resources:
            filters = [{'Name': 'tag:Name', 'Values': [resource]}]
            
            for service in [ec2.instances, ec2.images, ec2.volumes, ec2.network_interfaces, ec2.snapshots]:
                service_filters = service.filter(Filters=filters).all()
                filtered_list(service_filters, tags)
        
        print_message('Finished')

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def filtered_list(service_filters, tags):
    try:
        filtered_list = [resource for resource in service_filters]
        for resource in filtered_list:
            tagging(resourceid=resource.id, tags=tags)

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
parser.add_argument("--tags", "-T", dest="tags", action=StoreDictKeyPair, nargs="+", metavar="KEY=VAL")
parser.add_argument("--resources", "--names", "-R", "-N", nargs="+", dest='resources', default=[''])

args = parser.parse_args()

DEBUG = args.debug
resources = args.resources
delete = args.delete
tags = args.tags

##########################################

if __name__ == '__main__':
    resource_parser(resources, tags)
