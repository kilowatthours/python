################################################################################
##    FILE:  	elb-tag-instances.py                                          ##
##                                                                            ##
##    NOTES: 	Script to tag instances registered with LB's                  ##
##                                                                            ##
##    AUTHOR:	Stepan Litsevych                                              ##
##                                                                            ##
##    Copyright 2020 - Baxter Planning Systems, Inc. All rights reserved      ##
################################################################################

import boto3
import json
import re
import argparse
from datetime import datetime, timezone

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

elbv1 = boto3.client('elb')
elbv2 = boto3.client('elbv2')
ec2 = boto3.client('ec2')


class EC2Handler:
    """
    EC2Handler Class containing instance, image and volume iterators
    """

      
    def __init__(self, instance_id: str):
        """
        main __init__ function
        
        Args: 
            instance_id ([str]): instance_id to filter
    
        Returns:
            self
        """        
        
        if self:   
            self.instance_id = instance_id
            self.ec2_client = boto3.client('ec2')
            self.instances = self.ec2_client.describe_instances(InstanceIds=[instance_id])
            for self.reservation in self.instances['Reservations']:
                for self.instance in self.reservation['Instances']:
                    self.instance_tags = self.instance['Tags']
                    self.instance_name = [tag['Value'] for tag in self.instance_tags if tag['Key'] == 'Name'][0]
        
    def get_instance_tags(self) -> list:
        if self.instance_tags:
            return self.instance_tags
        
    def reset(self):
        self.__init__(self.instance_id)


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
        

def elb_parser():
    try:
        print_message('Running')
        elbv1_parser()
        elbv2_parser()
        print_message('Finished')
        
    except Exception as error:
        print(f"{color.RED}Encountered errors with elb_parser: {str(error)}")
        raise error

def elbv1_parser():
    try:
        get_elbs = elbv1.describe_load_balancers()
        for elb in get_elbs['LoadBalancerDescriptions']:
            lb_time = json.dumps(elb['CreatedTime'], indent=1, sort_keys=True, default=str).strip("\"").split(".")[0]
            lb_name = elb['LoadBalancerName']
            for instance in elb['Instances']:
                instance_id = instance['InstanceId']
                
                ec2_handler = EC2Handler(instance_id)
                tags = ec2_handler.get_instance_tags()
                
                if 'LB_registered' not in [tag['Key'] for tag in tags] and 'LB_registered_with' not in [tag['Key'] for tag in tags]:
                    
                    
                    print(f'{color.PURPLE}\nChecking instances registered with LB: {lb_name}{color.END}')
                    print(f'{color.CYAN}Instance: {instance_id}{color.END}')
                    
                    tags = [
                            {'Key': 'LB_registered', 'Value': 'yes'},
                            {'Key': 'LB_type', 'Value': 'classic'},
                            {'Key': 'LB_registered_with', 'Value': lb_name},
                            {'Key': 'LB_registered_at', 'Value': lb_time}
                        ]

                    if not DEBUG:
                        ec2.create_tags(Resources=[instance_id], Tags=tags)
                    elif DEBUG:
                        print(f'tags: {tags}')
                
    except Exception as error:
        print(f"{color.RED}Encountered errors with elbv1_parser: {str(error)}")
        raise error
    
def elbv2_parser():
    try:
        get_albs = elbv2.describe_load_balancers()
        for alb in get_albs['LoadBalancers']:
            lb_arn = alb['LoadBalancerArn']
            lb_name = alb['LoadBalancerName']
            lb_time = json.dumps(alb['CreatedTime'], indent=1, sort_keys=True, default=str).strip("\"").split(".")[0]
            
            get_tg = elbv2.describe_target_groups(LoadBalancerArn=lb_arn)
            for tg in get_tg['TargetGroups']:
                if tg['TargetType'] == 'instance':
                    tg_arn = tg['TargetGroupArn']
                    tg_name = tg['TargetGroupName']
                    
                    get_targets = elbv2.describe_target_health(TargetGroupArn=tg_arn)
                    for target in get_targets['TargetHealthDescriptions']:
                        instance_id = target['Target']['Id']
                        
                        ec2_handler = EC2Handler(instance_id)
                        tags = ec2_handler.get_instance_tags()
                        
                        if 'LB_target_groups' in [tag['Key'] for tag in tags]:
                            tgs = [tag['Value'] for tag in tags if tag['Key'] == 'LB_target_groups'][0]
                                
                            if not re.search(tg_name, tgs):
                                ec2.create_tags(Resources=[instance_id], Tags=[{'Key': 'LB_target_groups', 'Value': tgs+":"+tg_name}])
                                
                        elif 'LB_target_groups' not in [tag['Key'] for tag in tags]:
                            ec2.create_tags(Resources=[instance_id], Tags=[{'Key': 'LB_target_groups', 'Value': tg_name}])
                            
                        if 'LB_registered' not in [tag['Key'] for tag in tags] and 'LB_registered_with' not in [tag['Key'] for tag in tags]:
                            
                            print(f'{color.PURPLE}\nChecking instances registered with LB: {lb_name}{color.END}')
                            print(f'{color.DARKCYAN}Target Group: {tg_name}{color.END}')
                            print(f'{color.CYAN}Instance: {instance_id}{color.END}')
                            
                            tags = [
                                    {'Key': 'LB_registered', 'Value': 'yes'},
                                    {'Key': 'LB_type', 'Value': 'application'},
                                    {'Key': 'LB_registered_with', 'Value': lb_name},
                                    {'Key': 'LB_registered_at', 'Value': lb_time}
                            ]
                        
                            if not DEBUG:
                                ec2.create_tags(Resources=[instance_id], Tags=tags)
                                
                            elif DEBUG:
                                print(f'tags: {tags}')
                    
    except Exception as error:
        print(f"{color.RED}Encountered errors with elbv2_parser: {str(error)}")
        raise error

##########################################

parser = argparse.ArgumentParser()
parser.add_argument("--apply", "-A", "--true", default=True, dest='debug', action='store_false')
args = parser.parse_args()
DEBUG = args.debug

##########################################

if __name__ == '__main__':
    elb_parser()
