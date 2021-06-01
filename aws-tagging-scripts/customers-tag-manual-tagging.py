################################################################################
##    FILE:  	customers-tag-manual-tagging.py                               ##
##                                                                            ##
##    NOTES: 	Script to create Customers tags for EC2 resources based on    ##
##              predefined server names and GID associations                  ##
##              (e.g., 'pluto':'F5N GIMO PLS')                                ##
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

def set_gcid(server_name) -> str:
    try:
        switcher = {
            'pluto': 'F5N GIMO PLS',
            'republic': 'AVA RVBD',
            'pluto': 'F5N GIMO PLS',
            'phobos': 'BD SCHN',
            'odyssey': 'COH TRI',
            'neptune': 'CUC NET',
            'oberon': 'TEL',
            'saturn': 'BDKL',
            'tgcs': 'TGCS',
            'titania': 'CSA',
            'theia': 'SMIT MDI',
            'jupiter': 'CRAY JJDS MDC PAN',
            'lucent': 'LUC',
            'luna': 'RICO',
            'mars': 'FCS',
            'mercury': 'EXT',
            'infoprint': 'ARI NVDA',
            'eris': 'BIO BRCD NWAZ',
            'ceres': 'BMS QTM TD',
            'venus': 'CIE CST',
            'intrepid': 'CIT LSC VGY',
            'earth': 'DSL NOK NX PURE SNE TFI',
            'apollo': 'VMS',
            'europa': 'VZN VZT',
            'uranus': 'VZO VZW',
            'juniper': 'JNPR',
            'tmh': 'TMH',
            'tke': 'TKE',
            'bd': 'BD'
        }
        customer_tag = switcher.get(server_name, "Invalid server name")
        
        if customer_tag:
            return customer_tag

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def set_tags(server_name, env) -> list:
    try:
        tags = []
        department = ''
        
        if env == 'uat' or env == 'prd':
            department = "Production"
        elif env == 'dev':
            department = "Development"
        elif env == 'ins':
            department = "Development"
        else:
            print("--env is not correct")
            
        tags = [
        {
            "Key": "Customers",
            "Value": "%s" % (set_gcid(server_name))
        },
        {
            "Key": "Env",
            "Value": env
        },
        {
            "Key": "Department",
            "Value": department
        }]

        if tags:
            return tags

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def set_filters(server_name, env) -> list:
    try:
        filters = []
        
        if env == 'dev':
            filters = [{'Name': 'tag:Name', 'Values': ['dev-' + server_name + '-*']}]
        elif env == 'ins':
            filters = [{'Name': 'tag:Name', 'Values': ['ia-' + server_name , 'ia-' + server_name + 'db']}]
        elif env == 'uat':
            filters = [{'Name': 'tag:Name', 'Values': ['uat-' + server_name, 'uat-' + server_name + 'db']}]
        elif env == 'prd':
            filters = [{'Name': 'tag:Name', 'Values': [server_name, server_name + 'db']}]
        else:
            print(f"{color.RED}Env has not been defined{color.END}")
            exit()
        
        if filters != '':
            return filters

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def resources_parser(filters, tags, scopes) -> None:
    try:
        for svc in scopes:
            if svc in ['ec2', 'instances']:
                service = ec2.instances
                filtered_list(service, filters, tags)
            elif svc in ['snapshot', 'snaps', 'snap']:
                service = ec2.snapshots
                filtered_list(service, filters, tags)
            elif svc in ['ami', 'images', 'image']:
                service = ec2.images
                filtered_list(service, filters, tags)
            elif svc in ['volumes', 'vols', 'vol']:
                service = ec2.volumes
                filtered_list(service, filters, tags)
            else:
                print(f"{color.RED}Scope has not been properly defined{color.END}")
                exit()

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def filtered_list(service, filters, tags) -> None:
    try:
        filtered_list = [resource for resource in service.filter(Filters=filters).all()]
        
        for resource in filtered_list:
            resource_name = [tag['Value'] for tag in resource.tags if tag['Key'] == 'Name'][0]
            
            if not DEBUG:
                print(f"{color.DARKCYAN}--creating tags for {resource.id} ({resource_name}) {color.END}")
                
                ec2.create_tags(
                    Resources=[resource.id],
                    Tags=tags
                )
                
            else:
                print(f"{color.RED}DEBUG MODE: {color.END}{color.DARKCYAN}--creating tags for {resource.id} ({resource_name}) {color.END}")
                print(json.dumps(tags))

    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error


def customers_parser(customers_servers) -> None:
    try:
        for server_name in customers_servers:
            print(f"{color.CYAN}Parsing {color.END}{color.PURPLE}{server_name}{color.END} {color.CYAN}server:{color.END}")
            
            filters = set_filters(server_name, env)
            tags = set_tags(server_name, env)
            
            resources_parser(filters, tags, scopes)
            
    except Exception as error:
        print(f"{color.RED}Encountered errors{color.END}")
        raise error

##########################################


parser = argparse.ArgumentParser()
parser.add_argument("--apply", "-A", "-a", "--true", default=True, help="apply ?", dest='debug', action='store_false')
parser.add_argument("--servers", "--customers", "-c", nargs="+", dest='servers', default=["neptune", "odyssey", "venus", "titania", "uranus", "eris", "apollo", "intrepid",
                                                                     "lucent", "jupiter", "earth", "infoprint", "europa", "pluto", "mars", "luna", "mercury",
                                                                     "phobos", "republic", "oberon", "theia", "tgcs", "ceres", "juniper"])
parser.add_argument("--env", "-e", nargs="?", dest='env', default="prd")
parser.add_argument("--scopes", "--scope", "-s", nargs="+", dest='scopes', default=["ec2", "volumes", 'ami', 'snapshot'])
args = parser.parse_args()

DEBUG = args.debug

customers = args.servers
env = args.env
scopes = args.scopes

##########################################

if __name__ == '__main__':
    customers_parser(customers)
