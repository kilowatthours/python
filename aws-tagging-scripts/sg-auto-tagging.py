################################################################################
##    FILE:  	sg-auto-tagging.py                                            ##
##                                                                            ##
##    NOTES: 	Script to automatically apply tags for security groups        ##
##                                                                            ##
##    AUTHOR:	Stepan Litsevych                                              ##
##                                                                            ##
##    Copyright 2020 - Baxter Planning Systems, Inc. All rights reserved      ##
################################################################################

import boto3
import argparse
import re
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

class TagHandler:
    
    def __init__(self, DEBUG):   
        self.DEBUG = DEBUG
        self.ec2 = boto3.resource('ec2', region_name='us-west-2')
    
    def department_check(self, env_tag) -> str:
        """
        Evaluating Department tag using tags retrieved either via boto3 client, event details or regex env tag

        Args:
            tags ([list]): list of tags to parse
            type ([str]): type of list to iterate over: dict-event, dict-boto or dict-str

        Returns:
            [str]: dep_tag variable 
        """    
        try:
            dep_tag = ''
            dev_tags = {'dev', 'demo', 'ins', 'tst'}
            ops_tags = {'qa', 'ops'}
            prd_tags = {'prd', 'prodtest', 'uat', 'sim'}
            env_tags = {'qa', 'ops', 'prd', 'prodtest', 'uat', 'sim', 'ins', 'dev', 'tst', 'demo', 'ins'}
            if env_tag in env_tags:
                if env_tag in dev_tags: dep_tag = "Development"
                elif env_tag in ops_tags: dep_tag = "Operations"
                elif env_tag in prd_tags: dep_tag = "Production"
            if dep_tag != '':
                return dep_tag

        except Exception as error:
            print(f'Something went wrong with department_check: {str(error)}')


    # 5. Evaluating Env tag using regex and instance name
    def regex_search(self, sgName: str) -> str:
        """[summary]

        Args:
            tag_to_search ([str]): env tags to search
            instance_name ([str]): instance name to check with regex

        Returns:
            [str]: env tag variable
        """
        env_tags = ['qa', 'ops', 'prd', 'prodtest', 'uat', 'sim', 'ins', 'dev', 'tst', 'demo', 'ins', 'imp', 'test', 'performance', 'training', 'prod', 'ia']
        try:
            env_tag = ""
            for tag_to_search in env_tags:
                search = re.search(tag_to_search, sgName)
                if search:
                    env_tag = tag_to_search
                    if env_tag == "imp" or env_tag == "performance": env_tag = "uat"
                    elif env_tag == "test": env_tag = "dev"
                    elif env_tag == "training": env_tag = "trn"
                    elif env_tag == "prod" or env_tag == "production": env_tag = "prd"
                    elif env_tag == "ia": env_tag = "ins"
                    break
                else: env_tag = "ops"
            if env_tag != "":
                return env_tag

        except Exception as error:
            print(f'Something went wrong with regex_search: {str(error)}')
            
    def tagging(self, sgId, tags):
        try:
            if not self.DEBUG:
                self.ec2.create_tags(
                            Resources=[sgId],
                            Tags=tags
                            )
            else:
                print(f'{tags}')

        except Exception as error:
            print(f"{color.RED}Encountered errors with tagging: {str(error)}")


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


def sg_parser():
    try:
        
        print_message('Running')
        
        ec2client = boto3.client('ec2', region_name='us-west-2')
        taghandler = TagHandler(DEBUG)
        sgs = ec2client.describe_security_groups()
        
        for sg in sgs['SecurityGroups']:
            sgName = sg['GroupName']
            sgId = sg['GroupId']
                        
            if 'Tags' in sg: sg_tags = sg['Tags']
            else: sg_tags = []
            
            if 'Name' not in [tagkey['Key'] for tagkey in sg_tags]:
                print(f'{color.YELLOW}\nSG without Name: {sgName} ({sgId}){color.END}')
                print(f'{color.BOLD}adding Name tag{color.END}')
                tags = [{
                            "Key": "Env",
                            "Value": "ops"
                            },
                            {
                            "Key": "Department",
                            "Value": "Operations"
                            },
                            {
                            "Key": "Name",
                            "Value": sgName
                            }]
                print(f'{color.BOLD}adding tags: {json.dumps(tags)}{color.END}')
                taghandler.tagging(sgId, tags)
                
            elif 'stage' in [tagkey['Key'] for tagkey in sg_tags] and 'tenant' in [tagkey['Key'] for tagkey in sg_tags] and 'Env' not in [tagkey['Key'] for tagkey in sg_tags]:
                if 'Beanstalk' not in [tagkey['Value'] for tagkey in sg_tags if tagkey['Key'] == 'Department']:
                    print(f'{color.YELLOW}\nbeanstalk SG without Department tag: {sgName} ({sgId}){color.END}')
                    print(f'{color.BOLD}adding Beanstalk Department tag{color.END}')
                    tags = [{"Key": "Department", "Value": "Beanstalk"}]
                    taghandler.tagging(sgId, tags)
            
            elif 'Name' in [tagkey['Key'] for tagkey in sg_tags] and 'Department' not in [tagkey['Key'] for tagkey in sg_tags] and 'stage' not in [tagkey['Key'] for tagkey in sg_tags]:
                print(f'{color.YELLOW}\nSG without Env/Department (and not Beanstalk): {sgName} ({sgId}){color.END}')
                print(f'{color.BOLD}adding Env/Department tag{color.END}')
                env_tag = taghandler.regex_search(sgName)
                if env_tag:
                    print('Env tag: ' + str(env_tag))
                    print('adding Department tag')
                    dep_tag = taghandler.department_check(env_tag)
                    if dep_tag:
                        print(f'Department tag: {str(dep_tag)}')
                
                else: 
                    env_tag = "ops"
                    dep_tag = "Operations"
                
                tags = [{
                    "Key": "Env",
                    "Value": env_tag
                    },
                    {
                    "Key": "Department",
                    "Value": dep_tag
                    }]
                        
                taghandler.tagging(sgId, tags)
                        
        print_message('Finished')
                    
    except Exception as error:
        print(f"{color.RED}Encountered errors with sg_parser: {str(error)}")
        raise error

##########################################

parser = argparse.ArgumentParser()
parser.add_argument("--apply", "-A", "--true", default=True, dest='debug', action='store_false')
args = parser.parse_args()
DEBUG = args.debug

##########################################

if __name__ == '__main__':
    sg_parser()
