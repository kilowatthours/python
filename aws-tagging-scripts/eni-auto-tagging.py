###########################################################################
#    FILE:  	eni-auto-tagging.py                                       #
#                                                                         #
#    NOTES: 	Script to automatically apply tags for ENI                #
#                                                                         #
#    AUTHOR:	Stepan Litsevych                                          #
#                                                                         #
#    Copyright 2020 - Baxter Planning Systems, Inc. All rights reserved   #
###########################################################################

import boto3
import re
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


class EC2Handler:
    """
    EC2Handler Class containing instance, image and volume iterators
    """

    def __init__(self, instanceId: str, region: str):
        """
        main __init__ function

        Args:
            instanceId ([str]): instanceId to filter
            region ([str]): region of event

        Returns:
            self
        """

        if self:
            print("Initiliazing EC2Handler")
            self.instanceId = instanceId
            self.region = region
            self.ec2_client = boto3.client('ec2', region_name=region)
            self.instances = self.ec2_client.describe_instances(InstanceIds=[instanceId])
            for self.reservation in self.instances['Reservations']:
                for self.instance in self.reservation['Instances']:
                    self.instance_tags = self.instance['Tags']
                    self.instance_name = [tag['Value'] for tag in self.instance_tags if tag['Key'] == 'Name'][0]

    def eni_tags_handler(self) -> list:
        """
        Parsing and tagging Elastic Ip's using boto3 client

        Args:
            self

        Returns:
            [list]: list of tags
        """
        try:
            eni_tags = []
            tags_list = ['Name',
                         'Env',
                         'Owner',
                         'Department',
                         'Customers',
                         'Cluster',
                         'Id',
                         'tenant',
                         'stage',
                         'Project',
                         'Class',
                         'Role',
                         'application']
            for tag in self.instance_tags:
                tagkey = tag['Key']
                for item in tags_list:
                    if tagkey == item:
                        eni_tags.append(tag)

            if eni_tags:
                print(f'Formed tags based on instance: {str(self.instance_name)}')
                return eni_tags

        except Exception as error:
            print(f'Something went wrong with eni_tags_handler: {str(error)}')
            exit()


class SGHandler:
    """
    SGHandler Class containing security group iterator
    """

    def __init__(self, sgId: str, region: str):
        """
        main __init__ function

        Args:
            sgId ([str]): sgId to filter
            region ([str]): region of event

        Returns:
            self
        """

        if self:
            print("Initiliazing SGHandler")
            self.sgId = sgId
            self.region = region
            self.ec2_client = boto3.client('ec2', region_name=region)
            self.security_groups = self.ec2_client.describe_security_groups(GroupIds=[sgId])
            for self.sg in self.security_groups['SecurityGroups']:
                self.sg_tags = self.sg['Tags']

    def eni_tags_handler(self) -> list:
        """
        Parsing and tagging Elastic Ip's using boto3 client

        Args:
            self

        Returns:
            [list]: list of tags
        """
        try:
            eni_tags = []
            tags_list = ['Env', 'Owner', 'Department', 'Customers', 'Cluster', 'Id', 'tenant', 'stage', 'Project', 'Class', 'Role', 'application']
            for tag in self.sg_tags:
                tagkey = tag['Key']
                for item in tags_list:
                    if tagkey == item:
                        eni_tags.append(tag)

            if eni_tags:
                print(f'Formed tags based on SG: {str(self.sgId)}')
                return eni_tags

        except Exception as error:
            print(f'Something went wrong with eni_tags_handler: {str(error)}')
            exit()


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


def main_handler():
    try:
        print_message('Running')

        region = "us-west-2"
        ec2_client = boto3.client('ec2', region_name=region)
        describe_enis = ec2_client.describe_network_interfaces()

        for eni in describe_enis['NetworkInterfaces']:
            eniId = eni['NetworkInterfaceId']
            eni_interface_type = eni['InterfaceType']
            if 'Attachment' in eni:
                if eni_interface_type == 'interface' and 'InstanceId' in eni['Attachment']:
                    instanceId = eni['Attachment']['InstanceId']
                    if not eni['TagSet']:
                        print(f'{color.YELLOW}\nFound EC2 ENI: {eniId}{color.END}')
                        ec2handler = EC2Handler(instanceId, region)
                        eni_tags = list(ec2handler.eni_tags_handler())

                        if not DEBUG:
                            print(f'{color.PURPLE}tagging EC2 instance ENI without existing tags: {eniId} (instance: {instanceId})\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')
                            ec2_client.create_tags(Resources=[eniId], Tags=eni_tags)
                        elif DEBUG:
                            print(f'{color.PURPLE}tagging EC2 instance ENI without existing tags: {eniId} (instance: {instanceId})\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')

                    elif eni['TagSet']:
                        eni_tags = eni['TagSet']
                        if 'Name' not in [tag['Key'] for tag in eni_tags] or 'Department' not in [tag['Key'] for tag in eni_tags]:
                            print(f'{color.YELLOW}\nFound EC2 ENI: {eniId}{color.END}')
                            print(f'{color.BOLD}name|department tag not found{color.END}')
                            ec2handler = EC2Handler(instanceId, region)
                            eni_tags = list(ec2handler.eni_tags_handler())

                            if not DEBUG:
                                print(f'{color.PURPLE}tagging EC2 instance ENI with existing tags but without Name or Department tag:: {eniId} (instance: {instanceId})\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')
                                ec2_client.create_tags(Resources=[eniId], Tags=eni_tags)
                            elif DEBUG:
                                print(f'{color.PURPLE}tagging EC2 instance ENI with existing tags but without Name or Department tag: {eniId} (instance: {instanceId})\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')

                    else:
                        print(f'{color.RED}Cannot locate tags status{color.END}')
                        exit()

                elif eni_interface_type == 'interface' and 'InstanceId' not in eni['Attachment']:
                    if eni['Groups']:
                        sg_id = eni['Groups'][0]['GroupId']
                        eni_name = re.sub(' ', '-', eni['Description'])
                        if not eni['TagSet']:
                            print(f'{color.YELLOW}\nFound ENI without instance association: {eniId}{color.END}')
                            sghandler = SGHandler(sg_id, region)
                            eni_tags = list(sghandler.eni_tags_handler())

                            if not DEBUG:
                                print(f'{color.BLUE}tagging ENI with SG and without tags: {eniId} (sg: {sg_id})\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')
                                ec2_client.create_tags(Resources=[eniId], Tags=eni_tags)
                                ec2_client.create_tags(Resources=[eniId], Tags=[{'Key': 'Name', 'Value': eni_name}])
                            elif DEBUG:
                                print(f'{color.BLUE}tagging ENI with SG and without tags: {eniId} (sg: {sg_id})\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')

                        elif eni['TagSet']:
                            eni_tags = eni['TagSet']
                            if 'Name' not in [tag['Key'] for tag in eni_tags] or 'Department' not in [tag['Key'] for tag in eni_tags]:
                                print(f'{color.YELLOW}\nFound ENI without instance association: {eniId}{color.END}')
                                print(f'{color.BOLD}name|department tag not found{color.END}')
                                sghandler = SGHandler(sg_id, region)
                                eni_tags = list(sghandler.eni_tags_handler())

                                if not DEBUG:
                                    print(f'{color.BLUE}tagging ENI with SG and with tags but without Name or Department tag: {eniId} (sg: {sg_id})\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')
                                    ec2_client.create_tags(Resources=[eniId], Tags=eni_tags)
                                    ec2_client.create_tags(Resources=[eniId], Tags=[{'Key': 'Name', 'Value': eni_name}])
                                elif DEBUG:
                                    print(f'{color.BLUE}tagging ENI with SG and with tags but without Name or Department tag: {eniId} (sg: {sg_id})\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')

                            if re.search('ecs', eni['Description']):
                                if 'eni:ecs' not in [tag['Key'] for tag in eni_tags]:
                                    eni_name_ecs = ''
                                    if 'aws:ecs:serviceName' in [tag['Key'] for tag in eni_tags]:
                                        eni_name_ecs = [tag['Value'] for tag in eni_tags if tag['Key'] == "aws:ecs:serviceName"][0]
                                    elif 'aws:ecs:serviceName' not in [tag['Key'] for tag in eni_tags] and 'aws:ecs:clusterName' in [tag['Key'] for tag in eni_tags]:
                                        eni_name_ecs = [tag['Value'] for tag in eni_tags if tag['Key'] == "aws:ecs:clusterName"][0]
                                    elif 'aws:ecs:serviceName' not in [tag['Key'] for tag in eni_tags] and 'aws:ecs:clusterName' not in [tag['Key'] for tag in eni_tags]:
                                        eni_name_ecs = eni['Groups'][0]['GroupName']

                                    eni_name_tag = {'Key': 'Name', 'Value': 'eni-ecs-task-' + eni_name_ecs}

                                    if not DEBUG:
                                        print(f'{color.BLUE}tagging ENI of ECS task\nNew Name tag: {eni_name_tag}{color.END}')
                                        ec2_client.create_tags(Resources=[eniId], Tags=[
                                                                {'Key': 'eni:ecs', 'Value': 'tagged'},
                                                                eni_name_tag
                                                            ]
                                                            )
                                    elif DEBUG:
                                        print(f'{color.BLUE}tagging ENI of ECS task: {eniId} (sg: {sg_id})\n{color.DARKCYAN}New Name tag: {eni_name_tag}{color.END}')

                    elif not eni['Groups']:
                        eni_name = re.sub(' ', '-', eni['Description'])
                        if not eni['TagSet']:
                            print(f'{color.RED}\nFound ENI without instance or SG association: {eniId}{color.END}')
                            eni_tags = [
                                    {'Key': 'Name', 'Value': eni_name},
                                    {'Key': 'Owner', 'Value': 'Baxter'},
                                    {'Key': 'Env', 'Value': 'ops'},
                                    {'Key': 'Department', 'Value': 'Operations'},
                                ]
                            if not DEBUG:
                                print(f'{color.RED}tagging NAT/ELB/EKS ENI without tags: {eniId}\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')
                                ec2_client.create_tags(Resources=[eniId], Tags=eni_tags)
                            elif DEBUG:
                                print(f'{color.RED}tagging NAT/ELB/EKS ENI without tags: {eniId}\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')

                        elif eni['TagSet']:
                            eni_tags = eni['TagSet']
                            if 'Name' not in [tag['Key'] for tag in eni_tags] or 'Department' not in [tag['Key'] for tag in eni_tags]:
                                print(f'{color.RED}\nFound ENI without instance or SG association: {eniId}{color.END}')
                                print(f'{color.BOLD}name|department tag not found{color.END}')
                                eni_tags = [
                                        {'Key': 'Name', 'Value': eni_name},
                                        {'Key': 'Owner', 'Value': 'Baxter'},
                                        {'Key': 'Env', 'Value': 'ops'},
                                        {'Key': 'Department', 'Value': 'Operations'},
                                    ]
                                if not DEBUG:
                                    print(f'{color.RED}tagging ELB/EKS ENI with tags but without Name or Department tag: {eniId}\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')
                                    ec2_client.create_tags(Resources=[eniId], Tags=eni_tags)
                                elif DEBUG:
                                    print(f'{color.RED}tagging ELB/EKS ENI with tags but without Name or Department tag: {eniId}\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')

                elif eni_interface_type == 'nat_gateway':
                    eni_name = re.search(r'.*(nat-.*)$', eni['Description'], re.DOTALL) or ''
                    if not eni['TagSet']:
                        print(f'{color.RED}\nFound ENI for NAT: {eniId}{color.END}')
                        eni_tags = [
                                    {'Key': 'Name', 'Value': eni_name},
                                    {'Key': 'Owner', 'Value': 'Baxter'},
                                    {'Key': 'Env', 'Value': 'ops'},
                                    {'Key': 'Department', 'Value': 'Operations'},
                                ]

                        if not DEBUG:
                            print(f'{color.RED}tagging NAT ENI without tags: {eniId}\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')
                            ec2_client.create_tags(Resources=[eniId], Tags=eni_tags)
                        elif DEBUG:
                            print(f'{color.RED}tagging NAT ENI without tags: {eniId}\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')

                    elif eni['TagSet']:
                        eni_tags = eni['TagSet']
                        if 'Name' not in [tag['Key'] for tag in eni_tags] or 'Department' not in [tag['Key'] for tag in eni_tags]:
                            print(f'{color.RED}\nFound ENI for NAT: {eniId}{color.END}')
                            print(f'{color.BOLD}name|department tag not found{color.END}')
                            eni_tags = [
                                    {'Key': 'Name', 'Value': eni_name},
                                    {'Key': 'Owner', 'Value': 'Baxter'},
                                    {'Key': 'Env', 'Value': 'ops'},
                                    {'Key': 'Department', 'Value': 'Operations'},
                                ]
                            if not DEBUG:
                                print(f'{color.RED}tagging NAT ENI with tags but without Name or Department tag: {eniId}\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')
                                ec2_client.create_tags(Resources=[eniId], Tags=eni_tags)
                            elif DEBUG:
                                print(f'{color.RED}tagging NAT ENI with tags but without Name or Department tag: {eniId}\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')

                elif eni_interface_type == 'lambda':
                    eni_name = re.sub(' ', '-', eni['Description'])
                    if not eni['TagSet']:
                        print(f'{color.RED}\nFound ENI for Lambda: {eniId}{color.END}')
                        eni_tags = [
                                    {'Key': 'Name', 'Value': eni_name},
                                    {'Key': 'Env', 'Value': 'ops'},
                                    {'Key': 'Department', 'Value': 'Operations'},
                                ]

                        if not DEBUG:
                            print(f'{color.RED}tagging LAMBDA ENI without tags: {eniId}\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')
                            ec2_client.create_tags(Resources=[eniId], Tags=eni_tags)
                        elif DEBUG:
                            print(f'{color.RED}tagging LAMBDA ENI without tags: {eniId}\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')

                    elif eni['TagSet']:
                        eni_tags = eni['TagSet']
                        if 'Name' not in [tag['Key'] for tag in eni_tags] or 'Department' not in [tag['Key'] for tag in eni_tags]:
                            print(f'{color.RED}\nFound ENI for LAMBDA: {eniId}{color.END}')
                            print(f'{color.BOLD}name|department tag not found{color.END}')
                            eni_tags = [
                                    {'Key': 'Name', 'Value': eni_name},
                                    {'Key': 'Owner', 'Value': 'Baxter'},
                                    {'Key': 'Env', 'Value': 'ops'},
                                    {'Key': 'Department', 'Value': 'Operations'},
                                ]
                            if not DEBUG:
                                print(f'{color.RED}tagging LAMBDA ENI with tags but without Name or Department tag: {eniId}\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')
                                ec2_client.create_tags(Resources=[eniId], Tags=eni_tags)
                            elif DEBUG:
                                print(f'{color.RED}tagging LAMBDA ENI with tags but without Name or Department tag: {eniId}\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')

            elif 'Attachment' not in eni:
                if not eni['TagSet']:
                    print(f'{color.YELLOW}\nFound not attached ENI without tags: {eniId}{color.END}')
                    eni_tags = [
                            {'Key': 'Name', 'Value': '[NOT-ATTACHED]'},
                            {'Key': 'Owner', 'Value': 'Baxter'},
                            {'Key': 'Env', 'Value': 'ops'},
                            {'Key': 'Department', 'Value': 'Operations'}
                        ]
                    if not DEBUG:
                        print(f'{color.BLUE}tagging not attached ENI without tags: {eniId}\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')
                        ec2_client.create_tags(Resources=[eniId], Tags=eni_tags)
                    elif DEBUG:
                        print(f'{color.BLUE}tagging not attached ENI without tags: {eniId}\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')

                elif eni['TagSet']:
                    eni_tags = eni['TagSet']
                    if 'Name' not in [tag['Key'] for tag in eni_tags] or 'Department' not in [tag['Key'] for tag in eni_tags]:
                        print(f'{color.YELLOW}\nFound not attached ENI: {eniId}{color.END}')
                        print(f'{color.BOLD}name|department tag not found{color.END}')
                        eni_tags = [
                                {'Key': 'Name', 'Value': '[NOT-ATTACHED]'},
                                {'Key': 'Owner', 'Value': 'Baxter'},
                                {'Key': 'Env', 'Value': 'ops'},
                                {'Key': 'Department', 'Value': 'Operations'}
                            ]
                        if not DEBUG:
                            print(f'{color.BLUE}tagging not attached ENI with tags but without Name or Department tag: {eniId}\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')
                            ec2_client.create_tags(Resources=[eniId], Tags=eni_tags)
                        elif DEBUG:
                            print(f'{color.BLUE}tagging not attached ENI with tags but without Name or Department tag: {eniId}\n{color.DARKCYAN}Tags: {eni_tags}{color.END}')

        print_message('Finished')

    except Exception as error:
        print(f'Exception thrown at main_handler: {str(error)}')
        exit()


##########################################

parser = argparse.ArgumentParser()
parser.add_argument("--apply", "-A", "--true", default=True, dest='debug', action='store_false')
args = parser.parse_args()
DEBUG = args.debug

##########################################

if __name__ == '__main__':
    main_handler()
