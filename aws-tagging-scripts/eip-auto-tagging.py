################################################################################
##    FILE:  	volume-auto-tagging.py                                        ##
##                                                                            ##
##    NOTES: 	Script to automatically apply tags for Elastic Ip's           ##
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
        
    def address_tags_handler(self) -> list:
        """ 
        Parsing and tagging Elastic Ip's using boto3 client

        Args:
            self
            
        Returns:
            [list]: list of tags
        """    
        try:
            address_tags = []
            tags_list = ['Name', 'Env', 'Department', 'Customers', 'Cluster', 'Id', 'tenant', 'stage', 'Project', 'Class', 'Role', 'application']
            for tag in self.instance_tags:
                tagkey = tag['Key']
                tagvalue = tag['Value']
                for item in tags_list:
                    if tagkey == item:
                        address_tags.append(tag)
                if tagkey == 'Owner':
                    ownertag = {"Key": "AllocatedBy", "Value": tagvalue}
                    address_tags.append(ownertag)
                        
            if address_tags:
                print(f'Formed tags based on instance: {str(self.instance_name)}')
                return address_tags

        except Exception as error:
            print(f'Something went wrong with address_tags_handler: {str(error)}')
            exit()
            
            
class ENIHandler:
    """
    ENIHandler Class containing eni iterator
    """

      
    def __init__(self, eniId: str, region: str):
        """
        main __init__ function
        
        Args: 
            eniId ([str]): Eni ID to filter
            region ([str]): region of event
    
        Returns:
            self
        """        
        
        if self:   
            print("Initiliazing ENIHandler")
            self.eniId = eniId
            self.region = region
            self.ec2_client = boto3.client('ec2', region_name=region)
            self.interfaces = self.ec2_client.describe_network_interfaces(NetworkInterfaceIds=[eniId])
        
    def eni_tags_handler(self) -> list:
        """ 
        Parsing and tagging Elastic NAT Ip's using boto3 client

        Args:
            self
            
        Returns:
            [list]: list of tags
        """    
        try:
            for eni in self.interfaces['NetworkInterfaces']:
                if eni['InterfaceType'] == 'nat_gateway':
                    nat_name = eni['Description'].split()[4]
                    address_tags = [{'Key': 'Name', 'Value': nat_name},
                                    {'Key': 'Env', 'Value': 'ops'},
                                    {'Key': 'Department', 'Value': 'Operations'}
                                ]
                
                    if address_tags:
                        return address_tags

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
        describe_addresses = ec2_client.describe_addresses()

        for address in describe_addresses['Addresses']:
            instanceId = ''
            allocationId = address['AllocationId']
            publicip = address['PublicIp']
            # print(f'\n- {color.GREEN}{publicip} ({allocationId}){color.END}:')
            if 'InstanceId' in address:
                instanceId = address['InstanceId']
                if 'Tags' not in address:
                    print(f'\n- {color.YELLOW}\nFound EC2 EIP: {publicip} ({allocationId}){color.END}:')
                    print(f'{color.BOLD}- no tags found{color.END}')
                    ec2handler = EC2Handler(instanceId, region)
                    address_tags = list(ec2handler.address_tags_handler())
                    
                    if not DEBUG:
                        print(f'{color.PURPLE}tagging EC2 instance IP without tags: {publicip} ({allocationId})\n{color.DARKCYAN}Tags: {address_tags}{color.END}')
                        ec2_client.create_tags(Resources=[allocationId], Tags=address_tags)
                    elif DEBUG:
                        print(f'{color.PURPLE}tagging EC2 instance IP without tags: {publicip} ({allocationId})\n{color.DARKCYAN}Tags: {address_tags}{color.END}')
                        
                elif 'Tags' in address:
                    address_tags = address['Tags']
                    if 'Name' not in [tag['Key'] for tag in address_tags] or 'Department' not in [tag['Key'] for tag in address_tags]:
                        print(f'\n- {color.YELLOW}\nFound EC2 EIP: {publicip} ({allocationId}){color.END}:')
                        print(f'{color.BOLD}- found tags{color.END}')
                        print(f'{color.BOLD}name|department tag not found{color.END}')
                        ec2handler = EC2Handler(instanceId, region)
                        address_tags = list(ec2handler.address_tags_handler())
                        
                        if not DEBUG:
                            print(f'{color.PURPLE}tagging EC2 instance IP with tags but without Name or Department tag: {publicip} ({allocationId})\n{color.DARKCYAN}Tags: {address_tags}{color.END}')
                            ec2_client.create_tags(Resources=[allocationId], Tags=address_tags)
                        elif DEBUG:
                            print(f'{color.PURPLE}tagging EC2 instance IP with tags but without Name or Department tag: {publicip} ({allocationId})\n{color.DARKCYAN}Tags: {address_tags}{color.END}')
                    
                else:
                    print(f'{color.RED}Cannot locate tags status{color.END}')
                    exit()
            elif 'InstanceId' not in address:
                if 'NetworkInterfaceId' in address:
                    eni_id = address['NetworkInterfaceId']
                    if 'Tags' not in address:
                        print(f'\n- {color.YELLOW}\nFound non-EC2 EIP: {publicip} ({allocationId}){color.END}:')
                        print(f'{color.BOLD}- no tags found; checking if NatGateway{color.END}')
                        enihandler = ENIHandler(eni_id, region)
                        address_tags = list(enihandler.eni_tags_handler())
                        
                        if not DEBUG:
                            print(f'{color.BLUE}tagging NAT IP without tags: {publicip} ({allocationId})\n{color.DARKCYAN}Tags: {address_tags}{color.END}')
                            ec2_client.create_tags(Resources=[allocationId], Tags=address_tags)
                        elif DEBUG:
                            print(f'{color.BLUE}tagging NAT IP without tags: {publicip} ({allocationId})\n{color.DARKCYAN}Tags: {address_tags}{color.END}')

                    elif 'Tags' in address:
                        address_tags = address['Tags']
                        if 'Name' not in [tag['Key'] for tag in address_tags] or 'Department' not in [tag['Key'] for tag in address_tags]:
                            print(f'\n- {color.YELLOW}\nFound non-EC2 EIP: {publicip} ({allocationId}){color.END}:')
                            print(f'{color.BOLD}- found tags; checking if NatGateway{color.END}')
                            print(f'{color.BOLD}name|department tag not found{color.END}')
                            enihandler = ENIHandler(eni_id, region)
                            address_tags = list(enihandler.eni_tags_handler())
                            
                            if not DEBUG:
                                print(f'{color.BLUE}tagging NAT IP with tags but without Name or Department tag: {publicip} ({allocationId})\n{color.DARKCYAN}Tags: {address_tags}{color.END}')
                                ec2_client.create_tags(Resources=[allocationId], Tags=address_tags)
                            elif DEBUG:
                                print(f'{color.BLUE}tagging NAT IP with tags but without Name or Department tag: {publicip} ({allocationId})\n{color.DARKCYAN}Tags: {address_tags}{color.END}')
                                                    
                elif 'NetworkInterfaceId' not in address:
                    if 'Tags' not in address:
                        print(f'\n- {color.YELLOW}\nFound not associated EIP: {publicip} ({allocationId}){color.END}:')
                        print(f'{color.BOLD}- not tags found{color.END}')
                        address_tags = [
                                    {'Key': 'Name', 'Value': '[NOT-ASSOCIATED]'},
                                    {'Key': 'AllocatedBy', 'Value': 'Baxter'},
                                    {'Key': 'Env', 'Value': 'ops'},
                                    {'Key': 'Department', 'Value': 'Operations'}
                                    ]
                        if not DEBUG:
                            print(f'{color.RED}tagging not associated IP without tags: {publicip}\n{color.DARKCYAN}Tags: {address_tags}{color.END}')
                            ec2_client.create_tags(Resources=[allocationId], Tags=address_tags)
                        elif DEBUG:
                            print(f'{color.RED}tagging not associated IP without tags:: {publicip}\n{color.DARKCYAN}Tags: {address_tags}{color.END}')
                            
                    elif 'Tags' in address:
                        address_tags = address['Tags']
                        if 'Name' not in [tag['Key'] for tag in address_tags] or 'Department' not in [tag['Key'] for tag in address_tags]:
                            print(f'\n- {color.YELLOW}\nFound not associated EIP: {publicip} ({allocationId}){color.END}:')
                            print(f'{color.BOLD}- found tags{color.END}')
                            print(f'{color.BOLD}name|department tag not found{color.END}')
                            new_address_tags = [
                                        {'Key': 'Name', 'Value': '[NOT-ASSOCIATED]'},
                                        {'Key': 'AllocatedBy', 'Value': 'Baxter'},
                                        {'Key': 'Env', 'Value': 'ops'},
                                        {'Key': 'Department', 'Value': 'Operations'}
                                        ]
                            if not DEBUG:
                                print(f'{color.RED}tagging not associated IP with tags but without Name or Department tag: {publicip}\n{color.DARKCYAN}Tags: {new_address_tags}{color.END}')
                                ec2_client.create_tags(Resources=[allocationId], Tags=new_address_tags)
                            elif DEBUG:
                                print(f'{color.RED}tagging not associated IP with tags but without Name or Department tag: {publicip}\n{color.DARKCYAN}Tags: {new_address_tags}{color.END}')
        
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