################################################################################
##    FILE:  	main.py (autotagging-function)                                ##
##                                                                            ##
##    NOTES: 	Contains code required to automatically tag AWS resources     ##
##              in response to API events from CloudTrail                     ##
##                                                                            ##
##    AUTHOR:	Stepan Litsevych                                              ##
##                                                                            ##
##    Copyright 2020 - Baxter Planning Systems, Inc. All rights reserved      ##
################################################################################

import boto3
import logging
import json
import re
from time import sleep as timesleep
from botocore.exceptions import ClientError

# Defining logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class TagEvaluator:
    """
    TagEvaluator Class containing functions evaluating Env and Department tags
    """
      
    def __init__(self):
        """
        main __init__ function
        
        Args:
        Returns: 
        """        
        
        logger.info("Initializing TagEvaluator")
    
    @staticmethod
    def determine_env_tag_with_regex(name: str) -> str:
        """
        Evaluate Env tag using regex and instance name
        
        Args:
            name ([str]): instance name to check with regex

        Returns:
            [str]: env_tag variable
        """
        name = str(name.lower())
        env_tag = None
        env_tags = ['function', 'qa', 'ops', 'prd', 'prodtest', 'uat', 'dev', 'tst', 'demo', 'imp', 'test', 'performance', 'training', 'prod', 'ia', 'base', 'pince', 'sim', 'ins', 'trn']
        try:
            for tag_to_search in env_tags:
                # compare a received name with all env tags to find any matches
                search = re.search(tag_to_search, name, re.IGNORECASE)
                if search:
                    # if there is a match, create env_tag, but filter the result through certain conditions
                    env_tag = tag_to_search
                    if env_tag == "imp" or env_tag == "performance": env_tag = "uat"
                    elif env_tag == "test" or env_tag == "pince": env_tag = "dev"
                    elif env_tag == "training": env_tag = "trn"
                    elif env_tag == "prod": env_tag = "prd"
                    elif env_tag == "ia": env_tag = "ins"
                    elif env_tag == "base": env_tag = "ops"
                    elif env_tag == "function": env_tag = "ops"
                    break
                else: env_tag = "ops"
            
            # if env_tag is not empty, return it
            if env_tag:
                return env_tag
            
            elif not env_tag:
                logger.error('Cannot determine env tag')

        except Exception as error:
            logger.error(f'Error message: {str(error)}')
            logger.exception('Something went wrong with determine_env_tag_with_regex: ')
            return False
    
    @staticmethod      
    def determine_department_tag(env_tag: str) -> str:
        """
        Evaluate Department tag using tags retrieved either via boto3 client, event details or regex env tag

        Args:
            env_tag ([str]): env tag to assess

        Returns:
            [str]: dep_tag variable 
        """    
        try:
            # define lists of department tags
            dev_tags = ['dev', 'demo', 'ins', 'tst', 'trn']
            ops_tags = ['qa', 'ops']
            prd_tags = ['prd', 'prodtest', 'uat', 'sim']

            # determine department tag by checking all lists
            dep_tag = "Development" if env_tag in dev_tags else "Operations" if env_tag in ops_tags else "Production" if env_tag in prd_tags else None
            
            # if dep_tag is not empty, return it
            if dep_tag:
                return dep_tag

        except Exception as error:
            logger.error(f'Error message: {str(error)}')
            logger.exception('Something went wrong with determine_department_tag: ')
            return False
    
    
    def evaluate_env_and_dep_tags(self, name: str) -> str:
        """
        Call class methods to evaluate and return Env and Department tags

        Args:
            name (str): resource name to pass onto class methods

        Returns:
            str: return env_tag, dep_tag
        """        
        try:
            # call determine_env_tag_with_regex method to get env_tag
            logger.info(name)
            env_tag = str(self.determine_env_tag_with_regex(name))
            logger.info(f'Env tag: {str(env_tag)}')
            # call determine_department_tag method to get env_tag                        
            dep_tag = str(self.determine_department_tag(env_tag))
            logger.info(f'Department tag: {str(dep_tag)}')

            # return both tags
            return env_tag, dep_tag
        
        except Exception as error:
            logger.error(f'Error message: {str(error)}')
            logger.exception('Something went wrong with evaluate_env_and_dep_tags: ')
            return False

class TagHandler:
    """
    TagHandler Class containing instance, image and volume iterators
    """

      
    def __init__(self, id: str = None, region: str = None, **scope: str):
        """
        main __init__ function
        
        Args: 
            instance_id ([str]): instance_id to filter
            region ([str]): region of event
    
        Returns:
            self
        """        
        # assign class properties
        self.region = region
        self.scope = scope
        self.id = id
        # create boto3 client/resource connection
        self.ec2_client = boto3.client('ec2', region_name=region)
        
        # attempt to assign properties based on type of the ec2 resource
        if self.id and self.region:
            for id_type in scope.values():
                # assign properties for ec2_instance 
                if id_type == 'ec2':
                    self.instance_id = self.id
                    logger.info(f'Initializing TagHandler with EC2 Instance ID: {str(self.instance_id)}')
                    self.instances = self.ec2_client.describe_instances(InstanceIds=[self.instance_id])
                    if self.instances['Reservations']:
                        for self.reservation in self.instances['Reservations']:
                            for self.instance in self.reservation['Instances']:
                                # assign instance_tags
                                if 'Tags' in self.instance:
                                    self.instance_tags = self.instance['Tags']
                                # assign instance_name
                                    if 'Name' in [tag['Key'] for tag in self.instance_tags] and 'eks:nodegroup-name' not in [tag['Key'] for tag in self.instance_tags]:
                                        self.instance_name = [tag['Value'] for tag in self.instance_tags if tag['Key'] == 'Name'][0] or ''
                                    elif 'eks:nodegroup-name' in [tag['Key'] for tag in self.instance_tags]:
                                        self.instance_name = [tag['Value'] for tag in self.instance_tags if tag['Key'] == 'eks:nodegroup-name'][0] + '-instance'
                                elif not ['Tags'] in self.instance:
                                    self.instance_tags = []
                                  
                    elif not self.instances['Reservations']:
                        logger.error(f'Instance seems to be terminated: {str(self.instance_id)}')
                        self.instance_tags = []
                
                # assign properties for eni interface 
                elif id_type == 'eni':
                    self.eni_id = self.id
                    logger.info(f'Initializing TagHandler with ENI ID: {str(self.eni_id)}')
                    self.interfaces = self.ec2_client.describe_network_interfaces(NetworkInterfaceIds=[self.eni_id])
                    
                # assign properties for eni interface 
                elif id_type == 'ami':
                    self.ami_image_id = self.id
                    logger.info(f'Initializing TagHandler with AMI ID: {str(self.ami_image_id)}')
                    self.ami_images = self.ec2_client.describe_images(ImageIds=[self.ami_image_id], Owners=['461796779995'])
                    for self.ami_image in self.ami_images['Images']:
                        if 'Tags' in self.ami_image:
                            self.ami_image_tags = self.ami_image['Tags']
                            self.ami_image_name = [tag['Value'] for tag in self.ami_image_tags if tag['Key'] == 'Name'][0] or ''
                        else:
                            self.ami_image_tags = []
                    
                elif id_type == 'none':
                    logger.info("proceeding to method")

                else:
                    logger.info("scope is not properly defined; should be \"ec2\", \"eni\" or \"none\"")
                            
    def reset_handler(self, new_id: str = None) -> None:
        """
        Reset handler to apply changes

        Args:
            id (str, optional): id of a resource

        Returns:
            None
        """       
        try:
            logger.info('Resetting handler')
            # assign new resource id if new_id is not empty else leave self.id
            self.id = new_id if new_id is not None else self.id

            # reinitiliaze class properties with either new or old resource id
            self.__init__(self.id, self.region, **self.scope)
        
        except Exception as error:
            logger.error(f'Error message: {str(error)}')
            logger.exception('Something went wrong with reset_handler: ')
            return False
        
    def get_instance_tags(self) -> list:
        """
        Retrieve tags of an instance

        Args: 
            self
            
        Returns: 
            list --> list of tags
        """        
        try:
            # if instance_tags are not empty, return them
            if self.instance_tags and self.instance_name:
                logger.info(f'getting tags of {self.instance_name}')
                return self.instance_tags
            elif not self.instance_tags and self.instance_name:
                logger.info(f'getting tags of {self.instance_id}')
                return self.instance_tags
            elif not self.instance_tags:
                logger.info('no tags found, returning empty list')
                return self.instance_tags
            
        except Exception as error:
            logger.error(f'Error message: {str(error)}')
            logger.exception('Something went wrong with get_instance_tags: ')
            return False
        
    def get_image_tags(self) -> list:
        """
        Retrieve tags of an AMI image

        Args: 
            self
            
        Returns: 
            list --> list of tags
        """        
        try:
            # if image_tags are not empty, return them
            if self.ami_image_tags and self.ami_image_name:
                logger.info(f'getting tags of {self.ami_image_name}')
                return self.ami_image_tags
            elif self.ami_image_tags and not self.ami_image_name:
                logger.info(f'getting tags of {self.ami_image_id}')
                return self.ami_image_tags
            elif not self.ami_image_tags:
                logger.info('no tags found, returning empty list')
                return self.ami_image_tags
            
        except Exception as error:
            logger.error(f'Error message: {str(error)}')
            logger.exception('Something went wrong with get_image_tags: ')
            return False
        
    def parse_and_tag_volumes_and_eni(self, TagEni: bool = True) -> bool:
        """ 
        Parse and tag instance volumes and ENI's using boto3 client

        Args: 
            self
            TagEni (bool): if True create tags for ENI interface as well; if False create tags for volumes only
            
        Returns: 
            bool --> True or False

        """    
        try:
            if is_test_event:
                logger.info(f'tags on parse_and_tag_volumes_and_eni stage: {json.dumps(self.instance_tags, indent=1, sort_keys=True, default=str)}')
                
            newtags = []
            tags_list = ['Name', 'Env', 'Department', 'Customers', 'Cluster', 'Owner', 'Id', 'tenant', 'stage', 'Project', 'Class', 'Role', 'application']
            for tag in self.instance_tags:
                for item in tags_list:
                    if tag['Key'] == item:
                        newtags.append(tag)
            if newtags:
                logger.info(f'Parsing volumes of instance: {str(self.instance_name)}')
                for volume in self.instance['BlockDeviceMappings']:
                    volume_id = volume['Ebs']['VolumeId']
                    logger.info(f'Tagging volume: {str(volume_id)}')
                    # apply tags using ec2_client
                    self.ec2_client.create_tags(Resources=[volume_id], Tags=newtags)
                
                if TagEni:
                    for eni in self.instance['NetworkInterfaces']:
                        eni_id = eni['NetworkInterfaceId']
                        logger.info(f'Tagging ENI: {str(eni_id)}')
                        # apply tags using ec2_client
                        self.ec2_client.create_tags(Resources=[eni_id], Tags=newtags)
                    
                return True
            
            else:
                logger.error('Cannot process tags')
                return False            
                            
        except IndexError as indexerror:
            # in case of IndexError wait 5 seconds and retry the method
            timesleep(5)
            logger.info(f'Retrying parse_and_tag_volumes_and_eni after IndexError: {str(indexerror)}')
            self.reset_handler()
            self.parse_and_tag_volumes_and_eni()

        except Exception as error:
            logger.error(f'Error message: {str(error)}')
            logger.exception('Something went wrong with parse_and_tag_volumes_and_eni: ')
            return False


    def parse_and_tag_ec2_instance(self) -> bool:
        """ 
        Parse and tag instances by instance_id using boto3 client

        Args: 
            self
            
        Returns: 
            bool --> True or False
        """
        try:
            
            # initiliaze TagEvaluator to determine Env and Department tags# Initiliaze TagEvaluator class
            tagevaluator = TagEvaluator()
            logger.info(f'Checking instance: {str(self.instance_name)}')
            # get tag keys from self.instance_tags property
            tagkeys = [tag['Key'] for tag in self.instance_tags]
            
            if is_test_event:
                logger.info(f'tags on parse_and_tag_ec2_instance stage: {json.dumps(self.instance_tags, indent=1, sort_keys=True, default=str)}')
            
            # determine Department tag based on available Env tag
            if 'Env' in tagkeys and 'Department' not in tagkeys:
                    env_tag = [tag['Value'] for tag in self.instance_tags if tag['Key'] == "Env"][0].lower()
                    logger.info('adding Department tag')
                    dep_tag = str(tagevaluator.determine_department_tag(env_tag))
                    if dep_tag != '':
                        logger.info(f'Department tag: {str(dep_tag)}')
                        # apply tags using ec2_client
                        self.ec2_client.create_tags(Resources=[self.instance_id], Tags=[{'Key': 'Department', 'Value': dep_tag}])
                    else:
                        logger.info('Cannot determine a correct Department tag, tagging as Development')
                        # apply tags using ec2_client
                        self.ec2_client.create_tags(Resources=[self.instance_id], Tags=[{'Key': 'Department', 'Value': 'Development'}])
            
            # determine Env tag based on available Name tag (ignore elasticbeanstalk instances)
            elif 'Env' not in tagkeys and 'Name' in tagkeys and 'elasticbeanstalk:environment-name' not in tagkeys:
                logger.info('adding Env tag')
                env_tag = str(tagevaluator.determine_env_tag_with_regex(self.instance_name))
                logger.info(f'Env tag: {str(env_tag)}')
                # apply tags using ec2_client
                self.ec2_client.create_tags(Resources=[self.instance_id], Tags=[{'Key': 'Env', 'Value': env_tag}])
                logger.info('adding Department tag')
                dep_tag = str(tagevaluator.determine_department_tag(env_tag))
                logger.info(f'Department tag: {str(dep_tag)}')
                # apply tags using ec2_client
                self.ec2_client.create_tags(Resources=[self.instance_id], Tags=[{'Key': 'Department', 'Value': dep_tag}])
            
            # use instance id as Name tag for unnamed instances
            elif 'Name' not in tagkeys and 'eks:nodegroup-name' not in tagkeys:
                logger.info('detected unnamed instance without Env tag')
                # apply tags using ec2_client
                self.ec2_client.create_tags(Resources=[self.instance_id], Tags=[
                                                                            {'Key': 'Name', 'Value': self.instance_id},
                                                                            {'Key': 'Env', 'Value': 'dev'},
                                                                            {'Key': 'Department', 'Value': 'Development'}
                                                                            ])
                
            # tag unnamed EKS instances
            elif 'eks:nodegroup-name' in tagkeys:
                logger.info('detected unnamed instance without Env tag')
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(self.instance_name)
                logger.info(f'Env tag: {str(env_tag)}')
                logger.info(f'Department tag: {str(dep_tag)}')
                # apply tags using ec2_client
                self.ec2_client.create_tags(Resources=[self.instance_id], Tags=[
                                                                            {'Key': 'Name', 'Value': self.instance_name},
                                                                            {'Key': 'Env', 'Value': env_tag},
                                                                            {'Key': 'Department', 'Value': dep_tag}
                                                                            ])
                    
            else:
                logger.info('Cannot find proper conditions')
                pass
            
            return True

        except Exception as error:
            logger.error(f'Error message: {str(error)}')
            logger.exception('Something went wrong with parse_and_tag_ec2_instance: ')
            return False


    def get_tags_for_ami_image(self) -> list:
        """ 
        Create list of tags for AMI images using boto3 client

        Args:
            self
            
        Returns:
            [list]: list of tags
        """    
        try:
            # create empty list for image tags
            image_tags = []
            # fill image tags with tags derived from instance tags
            if self.instance_tags:
                for tag in self.instance_tags:
                    tagkey = tag['Key']
                    if tagkey == 'Owner' or tagkey == 'LastStartedBy' or tagkey == 'LastStoppedBy':
                        pass
                    else:
                        image_tags.append(tag)
                
                if image_tags:
                    logger.info(f'Formed tags for instance: {str(self.instance_name)}')
                    # append more tags if we are processing Packer Builder instance
                    if self.instance_name == 'Packer Builder':
                        packertags = [{'Key': 'BuiltBy', 'Value': 'packer'}, {'Key': 'Env', 'Value': 'qa'}, {'Key': 'Department', 'Value': 'Operations'}]
                        for tag in packertags:
                            image_tags.append(tag)
                    logger.info(f'tags: {json.dumps(image_tags, indent=1, sort_keys=True, default=str)}')
                    # return tags if list is not empty
                    return image_tags
                
            elif not self.instance_tags:
                logger.error('No tags found, returning empty list')
                return image_tags

        except Exception as error:
            logger.error(f'Error message: {str(error)}')
            logger.exception('Something went wrong with get_tags_for_ami_image: ')
            return False
        
        
    def get_tags_for_eip_and_eni(self) -> list:
        """ 
        Create list of tags for EIP or ENI using boto3 client

        Args:
            self
            
        Returns:
            [list]: list of tags
        """    
        try:
            # create empty list
            eip_eni_tags = []
            tags_list = ['Name', 'Env', 'Department', 'Customers', 'Cluster', 'Id', 'tenant', 'stage', 'Project', 'Class', 'Role', 'application']
            # fill list of tags with tags checking only certain tag keys actualized before in tags_list 
            for tag in self.instance_tags:
                tagkey = tag['Key']
                for item in tags_list:
                    if tagkey == item:
                        eip_eni_tags.append(tag)
            
            # return tags if list is not empty
            if eip_eni_tags:
                logger.info(f'Formed tags based on instance: {str(self.instance_name)}')
                logger.info(f'tags: {json.dumps(eip_eni_tags, indent=1, sort_keys=True, default=str)}')
                return eip_eni_tags

        except Exception as error:
            logger.error(f'Error message: {str(error)}')
            logger.exception('Something went wrong with get_tags_for_eip_and_eni: ')
            return False
        
    def get_tags_for_nat_eni(self) -> list:
        """ 
        Parse and tag NAT gateway ENI using boto3 client

        Args:
            self
            
        Returns:
            [list]: list of tags
        """    
        try:
            # get tags for eni interface from self.interfaces
            for eni in self.interfaces['NetworkInterfaces']:
                # create predefined tags if eni type if nat_gateway
                if eni['InterfaceType'] == 'nat_gateway':
                    nat_name = eni['Description'].split()[4]
                    
                    eni_tags = [
                        {'Key': 'Name', 'Value': nat_name},
                        {'Key': 'Env', 'Value': 'ops'},
                        {'Key': 'Department', 'Value': 'Operations'}
                                ]
                
                    if eni_tags:
                        return eni_tags

        except Exception as error:
            logger.error(f'Error message: {str(error)}')
            logger.exception('Something went wrong with get_tags_for_nat_eni: ')
            return False
        
    def parse_and_tag_ecs_eni(self, user) -> list:
        """ 
        Parse and tag ENI attached to ECS entities using boto3 client and security group

        Args:
            self
            
        Returns:
            [list]: list of tags
        """    
        try:
            # create tags for eni interface attached to ECS based on security group attached to it
            for eni in self.interfaces['NetworkInterfaces']:
                # assign Name tag for eni interface
                if eni['Groups']:
                    sg_id = eni['Groups'][0]['GroupId']
                    eni_name_ecs = ''
                    
                    # check if there are any existing tags and based on that determine name for the eni interface
                    if eni['TagSet']:
                        if 'aws:ecs:serviceName' in [tag['Key'] for tag in eni['TagSet']]:
                            eni_name_ecs = [tag['Value'] for tag in eni['TagSet'] if tag['Key'] == "aws:ecs:serviceName"][0]
                        elif 'aws:ecs:serviceName' not in [tag['Key'] for tag in eni['TagSet']] and 'aws:ecs:clusterName'in [tag['Key'] for tag in eni['TagSet']]:
                            eni_name_ecs = [tag['Value'] for tag in eni['TagSet'] if tag['Key'] == "aws:ecs:clusterName"][0]
                        else:
                            eni_name_ecs = eni['Groups'][0]['GroupName']
                            
                    elif not eni['TagSet']:
                        # if no tags found, create a nem using description
                        eni_name_ecs = re.sub(' ', '-', eni['Description'])
                    
                    # get security group tags
                    sg_tags = list(self.get_tags_from_security_group(sg_id))
                    # apply security group tags and three more tags including Owner and Name
                    if sg_tags:
                        # apply tags using ec2_client
                        self.ec2_client.create_tags(Resources=[self.eni_id], Tags=sg_tags)
                        self.ec2_client.create_tags(Resources=[self.eni_id], Tags=[
                                                                        {'Key': 'Name', 'Value': 'eni-ecs-task-' + eni_name_ecs},
                                                                        {'Key': 'eni:ecs', 'Value': 'tagged'},
                                                                        {'Key': 'Owner', 'Value': user}
                                                                        ])
        except Exception as error:
            logger.error(f'Error message: {str(error)}')
            logger.exception('Something went wrong with parse_and_tag_ecs_eni: ')
            return False
        
    def get_tags_from_security_group(self, sg_id: str) -> list:
        """ 
        Get tags from security group

        Args:
            self
            
        Returns:
            [list]: list of tags
        """    
        try:
            # get security group 
            security_groups = self.ec2_client.describe_security_groups(GroupIds=[sg_id])
            # derive existing security group tags and create a new list of tags
            for s_group in security_groups['SecurityGroups']:
                existing_sg_tags = s_group['Tags']
                sg_tags = []
                tags_list = ['Env', 'Owner', 'Department', 'Customers', 'Cluster', 'Id', 'tenant', 'stage', 'Project', 'Class', 'Role', 'application']
                # create a new list of tags based on existing tags
                for tag in existing_sg_tags:
                    tagkey = tag['Key']
                    for item in tags_list:
                        if tagkey == item:
                            sg_tags.append(tag)
                
                # return a new list of tags
                if sg_tags:
                    logger.info(f'Formed tags based on SG: {str(sg_id)}')
                    
                    return sg_tags

        except Exception as error:
            logger.error(f'Error message: {str(error)}')
            logger.exception('Something went wrong with get_tags_from_security_group: ')
            return False
        
    def processing_ec2_tags(self, seconds: int, additional_reset: bool = False) -> bool:
        """
        Parse tags for instances which tags have not been created by the time of receiving event

        Args:
            seconds (int): timeout value

        Returns:
            bool: True or False
        """                    
        try:
            logger.info(f'tags not found, pausing for {str(seconds)} seconds until we get tags')
            timesleep(seconds)
            if additional_reset:
                self.reset_handler()
            # invoke parse_and_tag_ec2_instance method
            if self.parse_and_tag_ec2_instance() is True:           
                # invoke reset_handler and reinitialize class properties (this way we will get actual tags)
                self.reset_handler()
                # invoke parse_and_tag_volumes_and_eni method to tag volumes and eni attached to instance 
                if self.parse_and_tag_volumes_and_eni() is True:
                    # if it exits without error, return True
                    return True
                else:
                    # or exit with error
                    return False
            else:
                return False

        except Exception as error:
            logger.error(f'Error message: {str(error)}')
            logger.exception('Exception thrown at inner processing_ec2_tags function: ')
            return False      

def finishing_sequence(context: object = None, eventname: str = None, status: str = None, error: str = None, exception: bool = True) -> bool:
    
    """
    Internal function outputting used/remaining time and results of the event processing

    Args:
        context (object): receive context from lambda_handler
        eventname (str): receive context from lambda_handler
        status (str): determine if sequence succeeded or failed
        error (str, optional): output error if status is "fail". Defaults to None.

    Returns:
        bool: [description]
    """        
    try:
        if status == "success":
            if is_test_event is True:
                logger.info(f"TestEvent succeeded while processing {str(eventname)}")
            elif is_test_event is False:
                logger.info(f"Function {str(context.function_name)} (version: {str(context.function_version)}) succeeded while processing {str(eventname)}")
                            
        elif status == "fail":
            logger.error(f'Error message: {str(error)}')
            logger.exception(f'Exception thrown at {eventname}: ') if exception is True else ...
            if is_test_event is True:
                logger.info(f"TestEvent failed while processing {str(eventname)} due to {str(error)}")
            elif is_test_event is False:
                logger.info(f"Function {str(context.function_name)} (version: {str(context.function_version)}) failed while processing {str(eventname)} due to {str(error)}")
        
        logger.info(f'Used time: {"{:.3f}".format(int(360.000) - (int(context.get_remaining_time_in_millis()) / 1000))} seconds || Remaining time: {str((int(context.get_remaining_time_in_millis()) / 1000))} seconds')
            
    except Exception as error:
        logger.error(f'Error message: {str(error)}')
        logger.exception('Something went wrong with finishing_sequence: ')

# inner function for test event
def test_event(detail: dict, user: str, region: str, event_time: str) -> bool:
    """
    Internal function for processing test CreateFunction20150331 during bitbucket pipelines execution

    Args:
        detail (dict): receive detail from event
        user (str): receive user from lambda_handler
        region (str): receive region from lambda_handler

    Returns:
        bool: True of False
    """                
    logger.info('PIPELINE TEST EVENT')
    
    assert len(detail) !=0, "Event details are not available"
    assert len(user) !=0, "User is not defined"
    assert len(region) !=0, "Region is not defined"
    
    # Create boto3 client connection
    lambda_client = boto3.client('lambda', region_name=region)
    try:
        function_arn = detail['responseElements']['functionArn']
        function_name = detail['responseElements']['functionName']
        logger.info(f'Tagging lambda function code during PIPELINE TEST EVENT: {str(function_name)} (user: {str(user)})')
        
        # use lambda-python function to apply tags using lambda_client
        tagging = lambda key, value: lambda_client.tag_resource(Resource=function_arn, Tags={key: value})
    
        tagging('TestEvent', 'successful')
        tagging('TestEventAt', event_time)
        
        return True
        
    except ClientError as clienterror:
        logger.error(f'Received botocore exception: {str(clienterror)}')
        logger.exception('Botocore Exception thrown at PIPELINE TEST EVENT: ')
        return False 
    
    except Exception as error:
        logger.error(f'Error message: {str(error)}')
        logger.exception('Exception thrown at PIPELINE TEST EVENT: ')
        return False

# Main section
def lambda_handler(event, context) -> bool:
    """
    Main section

    Args:
        event: received event from Cloudtrail
        context: a context object to the handler

    Returns:
        [bool]: True or False
    """
        
    try:
        # Define general vars
        region = event['region']
        detail = event['detail']
        detailtype = event['detail-type']
        aws_account_id = event['account']
        eventname = detail['eventName']
        eventsource = detail['eventSource']
        event_time = f"{re.sub('T', ' ', re.sub('Z', '', detail['eventTime']))} UTC"
        arn = detail['userIdentity']['arn']
        principal = detail['userIdentity']['principalId']
        user_type = detail['userIdentity']['type']
        
        # Check if we are running a test event or not
        global is_test_event
        is_test_event = True if detailtype == "TestEvent" else False
        logger.info('RUNNING TEST EVENT') if is_test_event == True else ...

        # Attempt to determine "user" (owner; createdby) based on usertype and principal conditions
        if user_type == 'IAMUser': 
            user = detail['userIdentity']['userName']

        elif user_type != 'IAMUser':
            session_arn = detail['userIdentity']['sessionContext']['sessionIssuer']['arn']
            user = principal.split(':')[1].split('@')[0]
            if user == "start_step": user = "cloudranger"
            elif user == "OpsWorksCM": user = "opsworks"
            elif user == "AWSBackup-AWSBackupDefaultServiceRole": user = "awsbackup"
            elif user == "i-0995fe389a6bd1363": user = "qa-jenkins"
            elif user == "i-05de6e243fbd8874f": user = "dev-jenkins"
            elif user == "i-0f6db606f4c1d387a": user = "ops-jenkins"
            elif user == "1600788278874920070": user = "eks-cluster"
            elif user == "CCSSession": user = "emr-cluster"
            elif user == "SLRManagement": user = "aws-rds"
            elif user == "InstanceLaunch": user = "aws-spot-instance"
            elif user == "AutoScaling":
                if 'tagSpecificationSet' in detail['requestParameters']:
                    tags = detail['requestParameters']['tagSpecificationSet']['items'][0]['tags']
                    if 'eks:cluster-name' in [tag['key'] for tag in tags]:
                        user = "eks-autoscaling"
                    elif 'elasticbeanstalk:environment-id' in [tag['key'] for tag in tags]:
                        user = "eb-autoscaling"
                    elif 'AWSBatchServiceTag' in [tag['key'] for tag in tags]:
                        user = "batch-autoscaling"
                    else: 
                        user = "autoscaling"
            
            if re.search('botocore-session-.*', user): user = arn.split("/")[1]
        
        else:
            logger.error('Cannot detect user_type')
            return False

        # Print some of the retrieved details
        logger.info(f'event {str(eventname)} in region {str(region)}')
        logger.info(f'usertype: {str(user_type)}')
        logger.info(f'ARN: {str(arn)}')
        logger.info(f'user: {str(user)}')
        logger.info(f'event details: {json.dumps(detail, indent=1, sort_keys=True, default=str)}')

        # Exit on error in payload
        if 'errorCode' in detail and 'errorMessage' in detail:
            error_code = detail['errorCode']
            error_message = detail['errorMessage']
            if error_code == 'Client.VPCIdNotSpecified' and user:
                logger.error('Detected Client.VPCIdNotSpecified error in event')
                logger.error(f'Error code: {str(error_code)}')
                logger.error(f'Error message: {str(error_message)}')
                for instance in detail['requestParameters']['instancesSet']['items']:
                    logger.info(f"Attempted to create instance: {str(instance['keyName'])}")
                    logger.info(f'User: {str(user)}')
            else:
                logger.error('Detected error in event')
                logger.error(f'Error code: {str(error_code)}')
                logger.error(f'Error message: {str(error_message)}')
            
            finishing_sequence(context, eventname, status='fail', error=error_code)
            return False
        
        # Proceed if event does not contain errors
        elif 'errorCode' not in detail and 'errorMessage' not in detail:
            pass
        
        # Start of Events sequence:
        # EC2 Instance events
        
        # processing of RunInstances event
        if eventname == 'RunInstances':
            # Create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                instance_id = None
                # Iterate through instances in event response elements
                for instance in detail['responseElements']['instancesSet']['items']:
                    # Declare empty list for resource ids
                    ids = []
                    instance_id = instance['instanceId']
                    # append instance id to the list of ids
                    ids.append(instance_id)
                    
                    # filtering instance resources
                    base = ec2_client.instances.filter(InstanceIds=[instance_id])

                    for instance in base:
                        for vol in instance.volumes.all():
                            # appending volumes attached to an instance
                            ids.append(vol.id)
                        for eni in instance.network_interfaces:
                            # appending ENI attached to an instance
                            ids.append(eni.id)                            

                    # Adding Owner and CreatedAt tag
                    if ids:
                        for resourceid in ids:
                            logger.info(f'Tagging EC2 resources: {str(resourceid)}')
                            # apply tags using boto3 ec2_client method
                            ec2_client.create_tags(Resources=[resourceid], 
                                                Tags=[
                                                    {'Key': 'Owner', 'Value': user},
                                                    {'Key': 'CreatedAt', 'Value': event_time}
                                                    ]
                                                )
                    if not ids:
                        logger.error('Cannot locate resource ids')
                        finishing_sequence(context, eventname, status='fail', error='Cannot locate resource ids', exception=False)
                        return False
                
                    #######################
                    # Initialize TagHandler class
                    ec2handler = TagHandler(instance_id, region, scope="ec2")
                    
                    # Check if tags are in place
                    if 'tagSpecificationSet' in detail['requestParameters']:
                        
                        # initiliaze TagEvaluator to determine Env and Department tags# Initialize TagEvaluator class
                        tagevaluator = TagEvaluator()
                        logger.info('found instance tags')
                        tags = detail['requestParameters']['tagSpecificationSet']['items'][0]['tags']
                        # Process instance without Env tag but with defined Name (and not related to elasticbeanstalk)
                        if 'Env' not in [tag['key'] for tag in tags] and 'Name' in [tag['key'] for tag in tags] and 'elasticbeanstalk:environment-name' not in [tag['key'] for tag in tags]:
                            logger.info('adding Env tag')
                            for tag in tags:
                                if tag['key'] == 'Name':
                                    # retrieve Name tag from available tags
                                    instance_name = tag['value']
                                    # call a TagEvaluator class method to determine Env and Department tags
                                    env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(instance_name)
                                    # create tags with boto3 client method
                                    for resourceid in ids:
                                        ec2_client.create_tags(Resources=[resourceid], 
                                                            Tags=[
                                                                {'Key': 'Env', 'Value': env_tag},
                                                                {'Key': 'Department', 'Value': dep_tag}
                                                                ]
                                                            )
                                    # call a TagHandler class method to parse and tag attached volumes and eni
                                    ec2handler.parse_and_tag_volumes_and_eni()

                        # Process instance with Env tag but without Department tag
                        elif 'Env' in [tag['key'] for tag in tags] and 'Department' not in [tag['key'] for tag in tags]:
                            # retrieve Env tag from available tags
                            env_tag = [tag['value'] for tag in tags if tag['key'] == 'Env'][0].lower()
                            logger.info(f'Env tag: {str(env_tag)}')
                            logger.info('adding Department tag')
                            # call a TagEvaluator class method to determine Department tags
                            dep_tag = str(tagevaluator.determine_department_tag(env_tag))
                            logger.info(f'Department tag: {str(dep_tag)}')
                            # create tags with boto3 client method
                            for resourceid in ids:
                                ec2_client.create_tags(Resources=[resourceid], 
                                                        Tags=[
                                                            {'Key': 'Env', 'Value': env_tag},
                                                            {'Key': 'Department', 'Value': dep_tag}
                                                            ]
                                                        )
                            # call a TagHandler class method to parse and tag attached volumes and eni
                            ec2handler.parse_and_tag_volumes_and_eni()
                        
                        # Process elasticbeanstalk instance without Department tag
                        elif 'elasticbeanstalk:environment-name' in [tag['key'] for tag in tags] and 'Department' not in [tag['key'] for tag in tags]:
                            logger.info('adding Department tag for Beanstalk resource')
                            dep_tag = "Beanstalk"
                            # create tags with boto3 client method
                            for resourceid in ids:
                                ec2_client.create_tags(Resources=[resourceid], 
                                                        Tags=[{'Key': 'Department', 'Value': dep_tag}])
                            
                            # call a TagHandler class method to parse and tag attached volumes and eni
                            ec2handler.parse_and_tag_volumes_and_eni()
                        
                        # Process instance without Name tag
                        elif 'Name' not in [tag['key'] for tag in tags] and 'eks:nodegroup-name' not in [tag['key'] for tag in tags]:
                            logger.info('found unnamed instance')
                            try:
                                # call a TagHandler class method to parse delayed tags
                                if ec2handler.processing_ec2_tags(30) is True:
                                    logger.info('Tags have been processed')
                                    pass
                                
                                else:
                                    finishing_sequence(context, eventname, status='fail', error='Error running processing_ec2_tags function', exception=False)
                                    return False
                                
                            except Exception as error:
                                logger.error('Exception thrown at EC2 RunInstances when tagging unnamed instance: ')
                                finishing_sequence(context, eventname, status='fail', error=error)
                                return False
                            
                        # Process instance without Name tag
                        elif 'eks:nodegroup-name' in [tag['key'] for tag in tags]:
                            logger.info('found unnamed EKS instance')
                            try:
                                # call a TagHandler class method to parse delayed tags
                                if ec2handler.processing_ec2_tags(60) is True:
                                    logger.info('Tags have been processed')
                                    pass
                                
                                else:
                                    finishing_sequence(context, eventname, status='fail', error='Error running processing_ec2_tags function', exception=False)
                                    return False
                                
                            except Exception as error:
                                logger.error('Exception thrown at EC2 RunInstances when tagging unnamed EKS instance: ')
                                finishing_sequence(context, eventname, status='fail', error=error)
                                return False
                        
                        else:
                            # call a TagHandler class method to parse and tag attached volumes and eni
                            ec2handler.parse_and_tag_volumes_and_eni()

                    # Process instances without specified list of tags; in such case we will wait until it is being created
                    elif 'tagSpecificationSet' not in detail['requestParameters']:
                        try:
                            # call a TagHandler class method to parse delayed tags
                            if ec2handler.processing_ec2_tags(120, additional_reset=True) is True:
                                logger.info('Tags have been processed')
                                pass
                            
                            else:
                                finishing_sequence(context, eventname, status='fail', error='Error running processing_ec2_tags function', exception=False)
                                return False
                                    
                        except Exception as error:
                            logger.error('Exception thrown at EC2 RunInstances when tagging instance without tagSpecificationSet: ')
                            finishing_sequence(context, eventname, status='fail', error=error)
                            return False

                    else:
                        finishing_sequence(context, eventname, status='fail', error='cannot determine status of tagSpecificationSet', exception=False)
                        return False
            
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # processing of StartInstances event
        elif eventname == 'StartInstances':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # iterate over instances in event and get instance id
                for instance in detail['responseElements']['instancesSet']['items']:
                    instance_id = instance['instanceId']
                    logger.info(f'EC2 Instance {str(instance_id)} started by: {str(user)}')
                    # apply tags using ec2_client
                    ec2_client.create_tags(Resources=[instance_id], Tags=[
                                                                        {'Key': 'LastStartedBy', 'Value': user},
                                                                        {'Key': 'LastStartedAt', 'Value': event_time}
                                                                        ]
                                        )
                    
                    # initialize Taghandler and get instance tags
                    ec2handler = TagHandler(instance_id, region, scope="ec2")
                    tags = ec2handler.get_instance_tags()
                    if 'Owner' not in [tag['Key'] for tag in tags]:
                        logger.info(f'Owner tag not found, setting: {str(user)}')
                        
                        # apply tags using ec2_client
                        ec2_client.create_tags(Resources=[instance_id], Tags=[{'Key': 'Owner', 'Value': user}])
                    
                        
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # processing of StopInstances event
        elif eventname == 'StopInstances':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # iterate over instances in event and get instance id
                for instance in detail['responseElements']['instancesSet']['items']:
                    instance_id = instance['instanceId']
                    logger.info(f'EC2 Instance {str(instance_id)} stopped by: {str(user)}')
                    
                    # apply tags using ec2_client
                    ec2_client.create_tags(Resources=[instance_id], 
                                           Tags=[
                                               {'Key': 'LastStoppedBy', 'Value': user},
                                               {'Key': 'LastStoppedAt', 'Value': event_time}
                                                 ])
                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of RebootInstances event
        elif eventname == 'RebootInstances':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # iterate over instances in event and get instance id
                for instance in detail['requestParameters']['instancesSet']['items']:
                    instance_id = instance['instanceId']
                    logger.info(f'EC2 Instance {str(instance_id)} rebooted by: {str(user)}')
                    
                    # apply tags using ec2_client
                    ec2_client.create_tags(Resources=[instance_id], 
                                           Tags=[
                                               {'Key': 'LastRebootedBy', 'Value': user},
                                               {'Key': 'LastRebootedAt', 'Value': event_time}
                                               ])
                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of RequestSpotInstances event
        elif eventname == 'RequestSpotInstances':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # iterate over spot instances in event and get spot_request_id
                for spot_instance in detail['responseElements']['spotInstanceRequestSet']['items']:
                    spot_request_id = spot_instance['spotInstanceRequestId']
                    logger.info(f'Request for Spot Instances {str(spot_request_id)} submitted by: {str(user)}')
                    
                    # apply tags using ec2_client
                    ec2_client.create_tags(Resources=[spot_request_id], 
                                           Tags=[
                                               {'Key': 'RequestedBy', 'Value': user},
                                               {'Key': 'RequestedAt', 'Value': event_time}
                                               ])
                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
        
        ## EC2 ALB/ELB events
        # classic ELB events
        # processing of RegisterInstancesWithLoadBalancer event
        elif eventname == 'RegisterInstancesWithLoadBalancer' and eventsource == 'elasticloadbalancing.amazonaws.com':
            # wait 30 seconds to get all details
            timesleep(30)
            # Create boto3 client/resource connections
            ec2_client = boto3.client('ec2', region_name=region)
            try:
                # get ln_name from event
                lb_name = detail['requestParameters']['loadBalancerName']
                # iterate over instances in event and get spot_request_id
                for instance in detail['responseElements']['instances']:
                    instance_id = instance['instanceId']
                    logger.info(f'EC2 Instance {str(instance_id)} registered with LB: {str(lb_name)}')
                    
                    # apply tags using ec2_client
                    ec2_client.create_tags(Resources=[instance_id], 
                                           Tags=[
                                               {'Key': 'LB_registered', 'Value': 'yes'},
                                               {'Key': 'LB_type', 'Value': 'classic'},
                                               {'Key': 'LB_registered_with', 'Value': lb_name},
                                               {'Key': 'LB_registered_by', 'Value': user},
                                               {'Key': 'LB_registered_at', 'Value': event_time}
                                               ])
                    
                    # initialize Taghandler and get instance tags
                    ec2handler = TagHandler(instance_id, region, scope="ec2")
                    tags = ec2handler.get_instance_tags()
                    # remove tags which are no longer actual
                    if 'LB_deregistered_at' in [tag['Key'] for tag in tags] or 'LB_deregistered_from' in [tag['Key'] for tag in tags] or 'LB_deregistered_by' in [tag['Key'] for tag in tags]:
                        ec2_client.delete_tags(Resources=[instance_id], 
                                           Tags=[
                                               {'Key': 'LB_deregistered_at'},
                                               {'Key': 'LB_deregistered_by'},
                                               {'Key': 'LB_deregistered_from'}
                                               ])
                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of DeregisterInstancesFromLoadBalancer event
        elif eventname == 'DeregisterInstancesFromLoadBalancer' and eventsource == 'elasticloadbalancing.amazonaws.com':
            # wait 30 seconds to get all details
            timesleep(30)
            # Create boto3 client/resource connections
            ec2_client = boto3.client('ec2', region_name=region)
            try:
                # get ln_name from event
                lb_name = detail['requestParameters']['loadBalancerName']
                # iterate over instances in event and get spot_request_id
                for instance in detail['responseElements']['instances']:
                    instance_id = instance['instanceId']
                    logger.info(f'EC2 Instance {str(instance_id)} deregistered from LB: {str(lb_name)}')
                    
                    # apply tags using ec2_client
                    ec2_client.create_tags(Resources=[instance_id], 
                                           Tags=[
                                               {'Key': 'LB_registered', 'Value': 'no'},
                                               {'Key': 'LB_deregistered_from', 'Value': lb_name},
                                               {'Key': 'LB_deregistered_by', 'Value': user},
                                               {'Key': 'LB_deregistered_at', 'Value': event_time}
                                               ])
                    
                    # initialize Taghandler and get instance tags
                    ec2handler = TagHandler(instance_id, region, scope="ec2")
                    tags = ec2handler.get_instance_tags()
                    if 'LB_registered_with' in [tag['Key'] for tag in tags] or 'LB_registered_at' in [tag['Key'] for tag in tags] or 'LB_registered_by' in [tag['Key'] for tag in tags]:
                        # remove tags which are no longer actual
                        ec2_client.delete_tags(Resources=[instance_id], 
                                            Tags=[
                                                {'Key': 'LB_registered_with'},
                                                {'Key': 'LB_registered_by'},
                                                {'Key': 'LB_registered_at'},
                                                {'Key': 'LB_type'},
                                                ])
                        
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
        
        # ALB events
        # processing of RegisterTargets event
        elif eventname == 'RegisterTargets' and eventsource == 'elasticloadbalancing.amazonaws.com':
            # wait 30 seconds to get all details
            timesleep(30)
            # Create boto3 client/resource connections to alb and ec2
            ec2_client = boto3.client('ec2',region_name=region)
            alb_client = boto3.client('elbv2', region_name=region)
            try:
                # get target group arn from event
                tg_arn = detail['requestParameters']['targetGroupArn']
                # get information about target group
                get_tg = alb_client.describe_target_groups(TargetGroupArns=[tg_arn])
                for tg in get_tg['TargetGroups']:
                    # re-assign target group arn and retrieve its name
                    tg_arn = tg['TargetGroupArn']
                    tg_name = tg['TargetGroupName']
                    # proceed if target group is attached to LB
                    if tg['LoadBalancerArns']:
                        # get LB name and arn
                        lb_arn = tg['LoadBalancerArns'][0]
                        lb_name = [alb['LoadBalancerName'] for alb in alb_client.describe_load_balancers(LoadBalancerArns=[lb_arn])['LoadBalancers']]
                        logger.info(f'Identified LB: {lb_name}')
                        # proceed if target group is attached to instance
                        if tg['TargetType'] == 'instance':
                            logger.info(f'Checking instances registered with TargetGroup: {tg_name}')
                            # get instance_id from target group health status
                            get_targets = alb_client.describe_target_health(TargetGroupArn=tg_arn)
                            if get_targets['TargetHealthDescriptions']:
                                for target in get_targets['TargetHealthDescriptions']:
                                    instance_id = target['Target']['Id']
                                    logger.info(f'Reviewing instance: {instance_id}')
                                    
                                    # initialize TagHandler to get instance tags
                                    ec2_handler = TagHandler(instance_id, region, scope="ec2")
                                    tags = ec2_handler.get_instance_tags()

                                    # check if LB_target_groups tag is present
                                    if 'LB_target_groups' in [tag['Key'] for tag in tags]:
                                        t_groups = [tag['Value'] for tag in tags if tag['Key'] == 'LB_target_groups'][0]
                                        
                                        # if target group is not in values of LB_target_groups, add it
                                        if not re.search(tg_name, t_groups):
                                            # apply tags using ec2_client
                                            ec2_client.create_tags(Resources=[instance_id], Tags=[{'Key': 'LB_target_groups', 'Value': t_groups + ":" + tg_name}])
                                    
                                    # if LB_target_groups tag is not present, create it
                                    elif 'LB_target_groups' not in [tag['Key'] for tag in tags]:
                                        # apply tags using ec2_client
                                        ec2_client.create_tags(Resources=[instance_id], Tags=[{'Key': 'LB_target_groups', 'Value': tg_name}])
                                    
                                    # if target group is not tagged as registered, add necessary groups
                                    if 'LB_registered' not in [tag['Key'] for tag in tags] or 'no' in [tag['Value'] for tag in tags if tag['Key'] == 'LB_registered'] or 'LB_registered_with' not in [tag['Key'] for tag in tags]:
                                        # apply tags using ec2_client
                                        ec2_client.create_tags(Resources=[instance_id], Tags=[
                                                                                            {'Key': 'LB_registered', 'Value': 'yes'},
                                                                                            {'Key': 'LB_type', 'Value': 'application'},
                                                                                            {'Key': 'LB_registered_with', 'Value': lb_name},
                                                                                            {'Key': 'LB_registered_at', 'Value': event_time},
                                                                                            {'Key': 'LB_registered_by', 'Value': user}
                                                                                        ])
                                    # if target group was previously deregistered from LB and tagged accordingly, remove those tags
                                    if 'LB_deregistered_from' in [tag['Key'] for tag in tags]:
                                        # delete tags using ec2_client
                                        ec2_client.delete_tags(Resources=[instance_id], Tags=[
                                                            {'Key': 'LB_deregistered_from'},
                                                            {'Key': 'LB_deregistered_at'},
                                                            {'Key': 'LB_deregistered_by'}
                                                        ])
                            
                            # if target group does not have instances attached, exit            
                            elif not get_targets['TargetHealthDescriptions']:
                                logger.info(f'Target group {tg_name} without instances')
                        
                        # if target group type is not 'instance', exit
                        elif tg['TargetType'] != 'instance':
                            logger.info(f'\'TargetType\' of TG {tg_name} is not \'instance\'')
                            
                    # if target group is not attached to LB, exit
                    elif not tg['LoadBalancerArns']:
                        logger.info(f'Target group {tg_name} is not connected to LB')    
                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of DeregisterTargets event
        elif eventname == 'DeregisterTargets' and eventsource == 'elasticloadbalancing.amazonaws.com':
            # wait 30 seconds to get all details
            timesleep(30)
            # Create boto3 client/resource connections to alb and ec2
            ec2_client = boto3.client('ec2', region_name=region)   
            alb_client = boto3.client('elbv2', region_name=region)
            try:
                # get target group arn from event
                tg_arn = detail['requestParameters']['targetGroupArn']
                # get information about target group
                get_tg = alb_client.describe_target_groups(TargetGroupArns=[tg_arn])
                for tg in get_tg['TargetGroups']:
                    # retrieve target group name
                    tg_name = tg['TargetGroupName']
                    # proceed if target group is attached to LB
                    if tg['LoadBalancerArns']:
                        # get LB name and arn
                        lb_arn = tg['LoadBalancerArns'][0]
                        lb_name = [alb['LoadBalancerName'] for alb in alb_client.describe_load_balancers(LoadBalancerArns=[lb_arn])['LoadBalancers']]
                        logger.info(f'Identified LB: {lb_name}')
                        # proceed if target group is attached to instance
                        if tg['TargetType'] == 'instance':
                            
                            logger.info(f'Checking instances deregistered with TargetGroup: {tg_name}')
                            # get instance_id from target group health status
                            get_targets = alb_client.describe_target_health(TargetGroupArn=tg_arn)
                            if get_targets['TargetHealthDescriptions']:
                                for target in get_targets['TargetHealthDescriptions']:
                                    instance_id = target['Target']['Id']
                                        
                                    logger.info(f'Reviewing instance: {instance_id}')
                                    
                                    # initialize TagHandler to get instance tags
                                    ec2_handler = TagHandler(instance_id, region, scope="ec2")
                                    tags = ec2_handler.get_instance_tags()
                                    
                                    # if target group was previously registered with LB and tagged accordingly, remove those tags and create deregistered tags
                                    if 'LB_registered_with' in [tag['Key'] for tag in tags] and 'yes' in [tag['Value'] for tag in tags if tag['Key'] == 'LB_registered']:
                                        # apply tags using ec2_client
                                        ec2_client.create_tags(Resources=[instance_id], Tags=[
                                                                                            {'Key': 'LB_registered', 'Value': 'no'},
                                                                                            {'Key': 'LB_deregistered_from', 'Value': lb_name},
                                                                                            {'Key': 'LB_deregistered_at', 'Value': event_time},
                                                                                            {'Key': 'LB_deregistered_by', 'Value': user},
                                                                                        ])
                                        # apply tags using ec2_client
                                        ec2_client.delete_tags(Resources=[instance_id], Tags=[
                                                                                            {'Key': 'LB_type'},
                                                                                            {'Key': 'LB_registered_with'},
                                                                                            {'Key': 'LB_registered_at'},
                                                                                            {'Key': 'LB_registered_by'},
                                                                                            {'Key': 'LB_target_groups'}
                                                                                        ])
                            # if target group does not have instances attached, exit
                            elif not get_targets['TargetHealthDescriptions']:
                                logger.info(f'TargetG group {tg_name} without instances')
                                
                        # if target group type is not 'instance', exit        
                        elif tg['TargetType'] != 'instance':
                            logger.info(f'\'TargetType\' of TG {tg_name} is not \'instance\'')
                            
                    # if target group is not attached to LB, exit        
                    elif not tg['LoadBalancerArns']:
                        logger.info(f'Target group {tg_name} is not connected to LB')
                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # EC2 Volume events
        # processing of CreateVolume event
        elif eventname == 'CreateVolume':
            # Create boto3 client/resource connection
            ec2_client = boto3.client('ec2', region_name=region)
            try:
                # get required values for tagging
                volume_id = detail['responseElements']['volumeId']
                logger.info(f'Adding Owner tag for volume: {str(volume_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[volume_id], 
                                       Tags=[{'Key': 'Owner', 'Value': user}])
                
                logger.info('Applying tags from instance')
                # get details about volumes
                volumes = ec2_client.describe_volumes(VolumeIds=[volume_id])
                for vol in volumes['Volumes']:
                    # if volume is attached to instance, get instance id and initiliaze TagHandler to parse and apply tags
                    if vol['Attachments']:
                        for attached_vol in vol['Attachments']:
                            instance_id = attached_vol['InstanceId']
                            ec2handler = TagHandler(instance_id, region, scope="ec2")
                            ec2handler.parse_and_tag_volumes_and_eni(TagEni=False)
                            
                    # if volume is not attached check its tags
                    elif not vol['Attachments']:
                        logger.info('Volume is not attached to instance')
                        # if Name tag is not available, apply predefined tags
                        if 'Name' not in [tag['Key'] for tag in vol['Tags']]:
                            # apply tags using ec2_client
                            ec2_client.create_tags(Resources=[volume_id], 
                                        Tags=[
                                            {'Key': 'Name', 'Value': '[not-attached-volume]'},
                                            {'Key': 'CreatedAt', 'Value': event_time},
                                            {'Key': 'Env', 'Value': 'ops'},
                                            {'Key': 'Department', 'Value': 'Operations'},
                                            ]
                                        )
                        # if Name tag is present, proceed to determining Env and Department tags
                        elif 'Name' in [tag['Key'] for tag in vol['Tags']]:
                            volume_name = [tag['Value'] for tag in vol['Tags'] if tag['Key'] == 'Name'][0]
                            
                            # initiliaze TagEvaluator to determine Env and Department tags
                            tagevaluator = TagEvaluator()
                            env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(volume_name)
                            # apply tags using ec2_client          
                            ec2_client.create_tags(Resources=[volume_id], 
                                                    Tags=[
                                                        {'Key': 'Env', 'Value': env_tag},
                                                        {'Key': 'Department', 'Value': dep_tag},
                                                        {'Key': 'CreatedAt', 'Value': event_time}
                                                        ]
                                                    )                     
            
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # EC2 AMI events
        # processing of CreateImage event
        elif eventname == 'CreateImage':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                image_id = detail['responseElements']['imageId']
                origin_instance_id = detail['requestParameters']['instanceId'] if detail['requestParameters']['instanceId'] else ''
                logger.info(f'Adding Owner tag for image: {str(image_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[image_id], Tags=[
                                                            {'Key': 'Owner', 'Value': user},
                                                            {'Key': 'CreatedAt', 'Value': event_time}
                                                            ]
                                       )

                # if there is no origin instance, invoke TagHandler and get a list of image_tags
                if origin_instance_id != '':
                    ec2handler = TagHandler(origin_instance_id, region, scope="ec2")
                    event_image_tags = list(ec2handler.get_tags_for_ami_image())
                    
                    # if images tags available check AMI name
                    if event_image_tags:
                        aminame = detail['requestParameters']['name']
                        if re.search('cent7-.*', aminame): 
                            aminame = aminame.split('-')[1]
                        # if its packer builder instance, retrieve real instance id behind it
                        if 'packer' in [tag['Value'] for tag in event_image_tags if tag['Key'] == 'BuiltBy']:
                            instances = boto3.client('ec2', region_name=region).describe_instances(Filters=[{'Name': 'tag:Name', 'Values': [aminame]}])
                            real_instance_id = [instance['InstanceId'] for reservation in instances['Reservations'] for instance in reservation['Instances']][0] if 'InstanceId' in (instance for reservation in instances['Reservations'] for instance in reservation['Instances']) else ''
                            if real_instance_id != '':
                                logger.info(f'Tagging AMI created by Packer: {str(aminame)}')
                                # reset TagHandler to get tags of a real instance
                                ec2handler.reset_handler(new_id=real_instance_id)
                                real_image_tags = list(ec2handler.get_tags_for_ami_image())
                                # apply tags using ec2_client
                                ec2_client.create_tags(Resources=[image_id], Tags=real_image_tags)
                            elif real_instance_id == '':
                                logger.error(f'Cannot find real instance id tagging with packer tags: {str(aminame)}')
                                # apply tags using ec2_client
                                ec2_client.create_tags(Resources=[image_id], Tags=event_image_tags)
                        else:
                            logger.info(f'Tagging standard AMI: {str(aminame)}')
                            # apply tags using ec2_client
                            ec2_client.create_tags(Resources=[image_id], Tags=event_image_tags)

                        # Tagging snapshots created for ami 
                        # wait 35 seconds to get all needed details
                        logger.info('Pausing to tag snapshots of AMI')
                        timesleep(35)
                        # Create new boto3 client/resource connection
                        ec2_client = boto3.client('ec2', region_name=region)
                        # get info about AMI images
                        images = ec2_client.describe_images(ImageIds=[image_id], Owners=['461796779995'])
                        for ami in images['Images']:
                            aminame = ami['Name']
                            logger.info(f'Parsing snaphots of ami: {str(aminame)}')
                            # iterate over snapshots attached to AMI
                            for snapshot in ami['BlockDeviceMappings']:
                                snapshot_id = snapshot['Ebs']['SnapshotId']
                                logger.info(f'Tagging snapshot: {str(snapshot_id)}')
                                event_image_tags.append({'Key': 'Owner', 'Value': user})
                                # apply tags using ec2_client
                                ec2_client.create_tags(Resources=[snapshot_id], Tags=event_image_tags)
                        
                        logger.info('Tags have been processed')
                        pass
                    
                    else:
                        finishing_sequence(context, eventname, status='fail', error='Cannot process event image tags', exception=False)
                        return False
                
                else:
                    finishing_sequence(context, eventname, status='fail', error='Cannot determine InstanceId', exception=False)
                    return False

            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # processing of CopyImage event
        elif eventname == 'CopyImage':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                image_id = detail['responseElements']['imageId']
                image_name = detail['requestParameters']['name']
                source_image_id = detail['requestParameters']['sourceImageId']
                logger.info(f'Tagging copied image: {str(image_id)} (source ami: {str(source_image_id)})')
                
                tags_to_add = [
                                {'Key': 'Name', 'Value': image_name},
                                {'Key': 'CopiedBy', 'Value': user},
                                {'Key': 'CopiedAt', 'Value': event_time},
                                {'Key': 'Copied', 'Value': 'yes'},
                                {'Key': 'SourceAMI', 'Value': source_image_id}
                            ]
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[image_id], Tags=tags_to_add)
                # invoke TagHandler to get tags from source AMI
                amihandler = TagHandler(source_image_id, region, scope="ami")
                source_image_tags = list(amihandler.get_image_tags())
                for item in source_image_tags:
                    if item['Key'] in [tag['Key'] for tag in tags_to_add]:
                        source_image_tags = [tag for tag in source_image_tags if tag.get('Key') != item['Key']]
                if is_test_event:
                    logger.info(f'source_image_tags: {json.dumps(source_image_tags, indent=1, sort_keys=True, default=str)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[image_id], Tags=source_image_tags)
                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # processing of RegisterImage event
        elif eventname == 'RegisterImage':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                image_id = detail['responseElements']['imageId']
                logger.info(f'Tagging registered image: {str(image_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[image_id], 
                                        Tags=[
                                            {'Key': 'Owner', 'Value': user},
                                            {'Key': 'RegisteredAt', 'Value': event_time}
                                            ]
                                        )
                           
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # EC2 Snapshot events
        # processing of CreateSnapshot event
        elif eventname == 'CreateSnapshot':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                snapshot_id = detail['responseElements']['snapshotId']
                logger.info(f'Tagging snapshot: {str(snapshot_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[snapshot_id], 
                                        Tags=[
                                            {'Key': 'Owner', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time}
                                            ]
                                        )
                                   
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # processing of CopySnapshot event
        elif eventname == 'CopySnapshot':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                snapshot_id = detail['responseElements']['snapshotId']
                logger.info(f'Tagging copied snapshot: {str(snapshot_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[snapshot_id], 
                                        Tags=[
                                            {'Key': 'Owner', 'Value': user},
                                            {'Key': 'CopiedAt', 'Value': event_time}
                                            ]
                                        )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # processing of ImportSnapshot event
        elif eventname == 'ImportSnapshot':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                snapshot_id = detail['responseElements']['snapshotId']
                logger.info(f'Tagging imported snapshot: {str(snapshot_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[snapshot_id], 
                                        Tags=[
                                            {'Key': 'Owner', 'Value': user},
                                            {'Key': 'ImportedAt', 'Value': event_time}
                                            ]
                                        )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # processing of CreateSecurityGroup event
        elif eventname == 'CreateSecurityGroup':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                sg_name = detail['requestParameters']['groupName']
                sg_id = detail['responseElements']['groupId']
                
                logger.info(f'Tagging new EC2 security group: {sg_name})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(sg_name)
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[sg_id], Tags=[
                                                                {'Key': 'Name', 'Value': sg_name},
                                                                {'Key': 'CreatedAt', 'Value': event_time},
                                                                {'Key': 'CreatedBy', 'Value': user}, 
                                                                {'Key': 'Env', 'Value': env_tag}, 
                                                                {'Key': 'Department', 'Value': dep_tag}
                                                                ]
                                        )         
                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateLaunchTemplate event
        elif eventname == 'CreateLaunchTemplate':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details from event details
                template_name_id = detail['responseElements']['CreateLaunchTemplateResponse']['launchTemplate']['launchTemplateId']
                template_name = detail['responseElements']['CreateLaunchTemplateResponse']['launchTemplate']['launchTemplateName']
                logger.info(f'Tagging new EC2 launch template: {template_name})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(template_name)
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[template_name_id], 
                                        Tags=[
                                            {'Key': 'Name', 'Value': template_name},
                                            {'Key': 'CreateBy', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time},
                                            {'Key': 'Env', 'Value': env_tag},
                                            {'Key': 'Department', 'Value': dep_tag}
                                            ]
                                        )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of ModifyLaunchTemplate event
        elif eventname == 'ModifyLaunchTemplate':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                template_name_id = detail['responseElements']['ModifyLaunchTemplateResponse']['launchTemplate']['launchTemplateId']
                template_name = detail['responseElements']['ModifyLaunchTemplateResponse']['launchTemplate']['launchTemplateName']
                
                logger.info(f'Tagging modified EC2 LaunchTemplate: {template_name})')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[template_name_id], 
                                        Tags=[
                                            {'Key': 'LastModifiedBy', 'Value': user},
                                            {'Key': 'LastModifiedAt', 'Value': event_time},
                                            ]
                                        )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateLaunchTemplateVersion event
        elif eventname == 'CreateLaunchTemplateVersion':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                template_name_id = detail['responseElements']['CreateLaunchTemplateVersionResponse']['launchTemplateVersion']['launchTemplateId']
                template_name = detail['responseElements']['CreateLaunchTemplateVersionResponse']['launchTemplateVersion']['launchTemplateName']
                version_number = int(detail['responseElements']['CreateLaunchTemplateVersionResponse']['launchTemplateVersion']['versionNumber'])
                logger.info(f'Tagging EC2 LaunchTemplate (version: {str(version_number)}): {str(template_name)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[template_name_id], 
                                        Tags=[
                                            {'Key': 'LastVersion', 'Value': str(version_number)},
                                            {'Key': 'LastVersionAddedBy', 'Value': user},
                                            {'Key': 'LastVersionAddedAt', 'Value': event_time}
                                            ]
                                        )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
                        
        # EC2 Other events:
        # processing of CreateKeyPair event
        elif eventname == 'CreateKeyPair':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                keypair_id = detail['responseElements']['keyPairId']
                keypair_name = detail['responseElements']['keyName']
                logger.info(f'Tagging new keypair name: {str(keypair_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(keypair_name)
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[keypair_id], 
                                        Tags=[
                                            {'Key': 'Name', 'Value': keypair_name},
                                            {'Key': 'CreatedBy', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time},
                                            {'Key': 'Env', 'Value': env_tag},
                                            {'Key': 'Department', 'Value': dep_tag}
                                            ]
                                            )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreatePlacementGroup event
        elif eventname == 'CreatePlacementGroup':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                placement_group_id = detail['responseElements']['placementGroup']['groupId']
                placement_group_name = detail['responseElements']['placementGroup']['groupName']
                logger.info(f'Tagging new EC2 placement group: {str(placement_group_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(placement_group_name)
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[placement_group_id], 
                                        Tags=[
                                            {'Key': 'Name', 'Value': placement_group_name},
                                            {'Key': 'CreatedBy', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time},
                                            {'Key': 'Env', 'Value': env_tag},
                                            {'Key': 'Department', 'Value': dep_tag}
                                            ]
                                            )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateCapacityReservation event
        elif eventname == 'CreateCapacityReservation':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                capacity_reservation_id = detail['responseElements']['CreateCapacityReservationResponse']['capacityReservation']['capacityReservationId']
                logger.info(f'Tagging new EC2 capacity reservation: {str(capacity_reservation_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[capacity_reservation_id], 
                                        Tags=[
                                            {'Key': 'id', 'Value': capacity_reservation_id},
                                            {'Key': 'CreatedBy', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time},
                                            {'Key': 'Env', 'Value': 'ops'},
                                            {'Key': 'Department', 'Value': 'Operations'}
                                            ]
                                            )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of ModifyCapacityReservation event
        elif eventname == 'ModifyCapacityReservation':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                capacity_reservation_id = detail['requestParameters']['ModifyCapacityReservationRequest']['CapacityReservationId']
                logger.info(f'Tagging modified EC2 capacity reservation: {str(capacity_reservation_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[capacity_reservation_id], 
                                        Tags=[
                                            {'Key': 'LastModifiedBy', 'Value': user},
                                            {'Key': 'LastModifiedAt', 'Value': event_time}
                                            ]
                                            )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of ModifyInstanceAttribute event
        elif eventname == 'ModifyInstanceAttribute':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                instance_id = detail['requestParameters']['instanceId']
                logger.info(f'Tagging modified EC2 instance: {str(instance_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[instance_id], 
                                        Tags=[
                                            {'Key': 'LastModifiedBy', 'Value': user},
                                            {'Key': 'LastModifiedAt', 'Value': event_time}
                                            ]
                                            )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # VPC events:    
        # processing of CreateVpc event
        elif eventname == 'CreateVpc':
            # Create boto3 client/resource connection
            ec2_client = boto3.client('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                vpc_id = detail['responseElements']['vpc']['vpcId']
                logger.info(f'Tagging new VPC: {str(vpc_id)}')
                
                # check if VPC contains tags
                if 'tagSet' in detail['responseElements']['vpc']:
                    logger.info('found tags')
                    tags = detail['responseElements']['vpc']['tagSet']['items']
                    # determine if Name tag is present
                    if 'Name' in [tag['key'] for tag in tags]:
                        vpc_name = [tag['value'] for tag in tags if tag['key'] == 'Name'][0]
                        logger.info(f'VPC name: {str(vpc_name)}')
                        
                        # initiliaze TagEvaluator to determine Env and Department tags
                        tagevaluator = TagEvaluator()
                        env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(vpc_name)

                        # apply tags using ec2_client
                        ec2_client.create_tags(Resources=[vpc_id], 
                                                Tags=[
                                                    {'Key': 'Name', 'Value': vpc_name},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'CreatedAt', 'Value': event_time},
                                                    {'Key': 'Env', 'Value': env_tag},
                                                    {'Key': 'Department', 'Value': dep_tag}
                                                    ]
                                                    )
                    
                    # if VPC is unnamed, use its id as a Name tag
                    elif 'Name' not in [tag['key'] for tag in tags]:
                        logger.info('VPC name is not available')

                        # apply tags using ec2_client
                        ec2_client.create_tags(Resources=[vpc_id], 
                                                Tags=[
                                                    {'Key': 'Name', 'Value': vpc_id},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'CreatedAt', 'Value': event_time},
                                                    {'Key': 'Env', 'Value': 'ops'},
                                                    {'Key': 'Department', 'Value': 'Operations'}
                                                    ]
                                                    )
                
                # if tags are not available, apply predefined tags
                elif 'tagSet' not in detail['responseElements']['vpc']:
                    logger.info('tags not found')
                    
                    # apply tags using ec2_client
                    ec2_client.create_tags(Resources=[vpc_id], 
                        Tags=[
                            {'Key': 'Name', 'Value': vpc_id},
                            {'Key': 'CreatedBy', 'Value': user},
                            {'Key': 'CreatedAt', 'Value': event_time},
                            {'Key': 'Env', 'Value': 'ops'},
                            {'Key': 'Department', 'Value': 'Operations'}
                            ]
                            )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # processing of CreateSubnet event
        elif eventname == 'CreateSubnet':
            # Create boto3 client/resource connection
            ec2_client = boto3.client('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                subnet_id = detail['responseElements']['subnet']['subnetId']
                logger.info(f'Tagging new VPC subnet: {str(subnet_id)}')
                
                # check if subnet contains tags
                if 'tagSet' in detail['responseElements']['subnet']:
                    logger.info('found tags')
                    tags = detail['responseElements']['subnet']['tagSet']['items']
                    # determine if Name tag is present
                    if 'Name' in [tag['key'] for tag in tags]:
                        subnet_name = [tag['value'] for tag in tags if tag['key'] == 'Name'][0]
                        logger.info(f'VPC subnet name: {str(subnet_name)}')
                        
                        # initiliaze TagEvaluator to determine Env and Department tags
                        tagevaluator = TagEvaluator()
                        env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(subnet_name)

                        # apply tags using ec2_client
                        ec2_client.create_tags(Resources=[subnet_id], 
                                                Tags=[
                                                    {'Key': 'Name', 'Value': subnet_name},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'CreatedAt', 'Value': event_time},
                                                    {'Key': 'Env', 'Value': env_tag},
                                                    {'Key': 'Department', 'Value': dep_tag}
                                                    ]
                                                    )
                    
                    # if subnet is unnamed, use its id as a Name tag
                    elif 'Name' not in [tag['key'] for tag in tags]:
                        logger.info('VPC subnet name is not available')
                
                        ec2_client.create_tags(Resources=[subnet_id], 
                                                Tags=[
                                                    {'Key': 'Name', 'Value': subnet_id},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'CreatedAt', 'Value': event_time},
                                                    {'Key': 'Env', 'Value': 'ops'},
                                                    {'Key': 'Department', 'Value': 'Operations'}
                                                    ]
                                                    )
                
                # if tags are not available, apply predefined tags
                elif 'tagSet' not in detail['responseElements']['subnet']:
                    logger.info('tags not found')
                    
                    # apply tags using ec2_client
                    ec2_client.create_tags(Resources=[subnet_id], 
                        Tags=[
                            {'Key': 'Name', 'Value': subnet_id},
                            {'Key': 'CreatedBy', 'Value': user},
                            {'Key': 'CreatedAt', 'Value': event_time},
                            {'Key': 'Env', 'Value': 'ops'},
                            {'Key': 'Department', 'Value': 'Operations'}
                            ]
                            )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateNetworkInterface event
        elif eventname == 'CreateNetworkInterface':
            # wait up to 60 seconds to get all details 
            timesleep(1)
            # Create boto3 client/resource connection
            ec2_client = boto3.client('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                eni_id = detail['responseElements']['networkInterface']['networkInterfaceId']
                logger.info(f'Tagging new NetworkInterface: {str(eni_id)}')
                # get details about ENI interface
                describe_interfaces = ec2_client.describe_network_interfaces(NetworkInterfaceIds=[eni_id])
                for eni in describe_interfaces['NetworkInterfaces']:
                    eni_interface_type = eni['InterfaceType']
                    # check if ENI is attached
                    if 'Attachment' in eni:
                        # if attached to Instance, get instance id
                        if eni_interface_type == 'interface' and 'InstanceId' in eni['Attachment']:
                            instance_id = eni['Attachment']['InstanceId']
                            logger.info(f'Tagging ENI attached to instance: {str(instance_id)}')
                            # initialize tagHandler to get instance tags
                            ec2handler = TagHandler(instance_id, region, scope="ec2")
                            instance_tags = list(ec2handler.get_tags_for_eip_and_eni())
                            
                            # apply tags using ec2_client if instance_tags are not empty
                            if instance_tags:
                                ec2_client.create_tags(Resources=[eni_id], Tags=instance_tags)
                                ec2_client.create_tags(Resources=[eni_id], Tags=[{'Key': 'Owner', 'Value': user}])
                        
                        # if ENI is not attached to Instance, check if it there an info about security group 
                        elif eni_interface_type == 'interface' and 'InstanceId' not in eni['Attachment']:
                            # if attached to SG, get security group id 
                            if eni['Groups']:
                                sg_id = eni['Groups'][0]['GroupId']
                                logger.info(f'Tagging ENI attached with security group: {str(sg_id)}')
                                eni_name = re.sub(' ', '-', eni['Description'])
                                # initialize tagHandler to get security group tags
                                sghandler = TagHandler(region, scope="none")
                                sg_tags = list(sghandler.get_tags_from_security_group(sg_id))
                                
                                # apply tags using ec2_client if sg_tags are not empty
                                if sg_tags:
                                    ec2_client.create_tags(Resources=[eni_id], Tags=sg_tags)
                                    ec2_client.create_tags(Resources=[eni_id], Tags=[
                                                                                {'Key': 'Name', 'Value': eni_name},
                                                                                {'Key': 'Owner', 'Value': user}
                                                                                ])
                                    
                                # check if ENI is attached to ECS tasks to assign a Name tag
                                if eni['TagSet']:
                                    if re.search('ecs', eni['Description']):
                                        if 'eni:ecs' not in [tag['Key'] for tag in eni['TagSet']]:
                                            eni_name_ecs = ''
                                            if 'aws:ecs:serviceName' in [tag['Key'] for tag in eni['TagSet']]:
                                                eni_name_ecs = [tag['Value'] for tag in eni['TagSet'] if tag['Key'] == "aws:ecs:serviceName"][0]
                                            elif 'aws:ecs:serviceName' not in [tag['Key'] for tag in eni['TagSet']] and 'aws:ecs:clusterName' in [tag['Key'] for tag in eni['TagSet']]:
                                                eni_name_ecs = [tag['Value'] for tag in eni['TagSet'] if tag['Key'] == "aws:ecs:clusterName"][0]
                                            elif 'aws:ecs:serviceName' not in [tag['Key'] for tag in eni['TagSet']] and 'aws:ecs:clusterName' not in [tag['Key'] for tag in eni['TagSet']]:
                                                eni_name_ecs = eni['Groups'][0]['GroupName']
                                            
                                            # apply tags using ec2_client                                           
                                            ec2_client.create_tags(Resources=[eni_id], Tags=[
                                                                        {'Key': 'eni:ecs', 'Value': 'tagged'},
                                                                        {'Key': 'Name', 'Value': 'eni-ecs-task-' + eni_name_ecs}
                                                                    ])
                            
                            # if there is no affiliation to security group, apply predefined tags
                            elif not eni['Groups']:
                                logger.info('Tagging ENI without security group')
                                eni_name = re.sub(' ', '-', eni['Description'])
                                eni_tags = [
                                            {'Key': 'Name', 'Value': eni_name},
                                            {'Key': 'Owner', 'Value': user},
                                            {'Key': 'Env', 'Value': 'ops'},
                                            {'Key': 'Department', 'Value': 'Operations'},
                                        ]
                                # apply tags using ec2_client
                                ec2_client.create_tags(Resources=[eni_id], Tags=eni_tags)
                                      
                        # apply tags for eni interfaces attached to nat gateways
                        elif eni_interface_type == 'nat_gateway':
                            eni_name = re.search(r'.*(nat-.*)$', eni['Description'], re.DOTALL) or ''
                            if eni_name == '': eni_name = re.sub(' ', '-', eni['Description']).split('-')[5]
                            
                            logger.info(f'Tagging ENI attached to nat_gateway: {str(eni_name)}')
                            
                            eni_tags = [
                                        {'Key': 'Name', 'Value': eni_name},
                                        {'Key': 'Owner', 'Value': user},
                                        {'Key': 'Env', 'Value': 'ops'},
                                        {'Key': 'Department', 'Value': 'Operations'},
                                    ]
                            # apply tags using ec2_client
                            ec2_client.create_tags(Resources=[eni_id], Tags=eni_tags)
                            
                        # apply tags for lambda interfaces attached to AWS lambda functions
                        elif eni_interface_type == 'lambda':
                            if re.search('role/service-role/.*', session_arn): 
                                user = session_arn.split('/')[2]
                                
                            eni_name = re.sub(' ', '-', eni['Description'])
                            
                            logger.info(f'Tagging ENI attached to AWS lambda function: {str(eni_name)}')
                            
                            eni_tags = [
                                        {'Key': 'Name', 'Value': eni_name},
                                        {'Key': 'Owner', 'Value': user},
                                        {'Key': 'Env', 'Value': 'ops'},
                                        {'Key': 'Department', 'Value': 'Operations'},
                                    ]
                            # apply tags using ec2_client
                            ec2_client.create_tags(Resources=[eni_id], Tags=eni_tags)           
                    
                    # if ENI is not attached, apply predefined tags
                    elif 'Attachment' not in eni:
                        eni_tags = [
                                {'Key': 'Name', 'Value': '[NOT-ATTACHED]'},
                                {'Key': 'Owner', 'Value': user},
                                {'Key': 'Env', 'Value': 'ops'},
                                {'Key': 'Department', 'Value': 'Operations'}
                            ]
                        # apply tags using ec2_client                    
                        ec2_client.create_tags(Resources=[eni_id], Tags=eni_tags)
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of AllocateAddress event
        elif eventname == 'AllocateAddress':
            # wait up to 90 seconds to get all details 
            timesleep(90)
            # Create boto3 client/resource connection
            ec2_client = boto3.client('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                allocation_id = detail['responseElements']['allocationId']
                ip_address = detail['responseElements']['publicIp']
                logger.info(f'Tagging new ElasticIP Address: {str(ip_address)}')
                # get info about Elastic IP
                describe_addresses = ec2_client.describe_addresses(PublicIps=[ip_address], AllocationIds=[allocation_id])
                for address in describe_addresses['Addresses']:
                    instance_id = ''
                    # if EIP is attached to instance, get instance id and get instance tags using TagHandler
                    if 'InstanceId' in address:
                        logger.info('Elastic IP has instance association')
                        logger.info('tagging EC2 Elastic IP')
                        instance_id = address['InstanceId']
                        ec2handler = TagHandler(instance_id, region, scope="ec2")
                        instance_tags = list(ec2handler.get_tags_for_eip_and_eni())
                        
                        # apply tags using ec2_client if instance_tags are not empty
                        if instance_tags:
                            ec2_client.create_tags(Resources=[allocation_id], Tags=instance_tags)
                            ec2_client.create_tags(Resources=[allocation_id], Tags=[
                                                                                {'Key': 'AllocatedBy', 'Value': user},
                                                                                {'Key': 'AllocatedAt', 'Value': event_time}
                                                                                ]
                                                    )
                    
                    # if EIP is not attached to instance, check if its NAT EIP
                    elif 'InstanceId' not in address:
                        logger.info('Elastic IP does not have instance association')
                        # proceed if EIP is attached to NAT gateway ENI
                        if 'NetworkInterfaceId' in address:
                            logger.info('tagging NAT Elastic IP')
                            eni_id = address['NetworkInterfaceId']
                            # get ENI tags using TagHandler
                            enihandler = TagHandler(eni_id, region, scope="eni")
                            eni_tags = list(enihandler.get_tags_for_nat_eni())
                            
                            # apply tags using ec2_client if eni_tags are not empty
                            if eni_tags:
                                ec2_client.create_tags(Resources=[allocation_id], Tags=eni_tags)
                                ec2_client.create_tags(Resources=[allocation_id], Tags=[
                                                                                    {'Key': 'AllocatedBy', 'Value': user},
                                                                                    {'Key': 'AllocatedAt', 'Value': event_time}
                                                                                    ]
                                                       )
                        # if EIP is not attached to NAT ENI, apply predefined tags                                    
                        elif 'NetworkInterfaceId' not in address:
                            logger.info('Elastic IP does not have any association')
                            address_tags = [
                                            {'Key': 'AllocatedBy', 'Value': user},
                                            {'Key': 'AllocatedAt', 'Value': event_time},
                                            {'Key': 'Env', 'Value': 'ops'},
                                            {'Key': 'Department', 'Value': 'Operations'}
                                        ]
                            
                            # apply tags using ec2_client
                            ec2_client.create_tags(Resources=[allocation_id], Tags=address_tags)
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # processing of CreateInternetGateway event
        elif eventname == 'CreateInternetGateway':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                igw_id = detail['responseElements']['internetGateway']['internetGatewayId']
                logger.info(f'Tagging new VPC internet gateway: {str(igw_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[igw_id], 
                                        Tags=[
                                            {'Key': 'CreatedBy', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time}
                                            ]
                                            )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # processing of CreateRouteTable event
        elif eventname == 'CreateRouteTable':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                rtable_id = detail['responseElements']['routeTable']['routeTableId']
                logger.info(f'Tagging new VPC route table: {str(rtable_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[rtable_id], 
                                        Tags=[
                                            {'Key': 'CreatedBy', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time}
                                            ]
                                            )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # processing of CreateNatGateway event
        elif eventname == 'CreateNatGateway':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                nat_gw_id = detail['responseElements']['CreateNatGatewayResponse']['natGateway']['natGatewayId']
                logger.info(f'Tagging new VPC NAT gateway: {str(nat_gw_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[nat_gw_id], 
                                        Tags=[
                                            {'Key': 'CreatedBy', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time}
                                            ]
                                            )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateEgressOnlyInternetGateway event
        elif eventname == 'CreateEgressOnlyInternetGateway':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                egress_gw_id = detail['responseElements']['CreateEgressOnlyInternetGatewayResponse']['egressOnlyInternetGateway']['egressOnlyInternetGatewayId']
                logger.info(f'Tagging new VPC EgressOnlyInternetGateway: {str(egress_gw_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[egress_gw_id], 
                                        Tags=[
                                            {'Key': 'CreatedBy', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time}
                                            ]
                                            )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateDhcpOptions event
        elif eventname == 'CreateDhcpOptions':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                dhcp_options_id = detail['responseElements']['dhcpOptions']['dhcpOptionsId']
                logger.info(f'Tagging new VPC DhcpOptions set: {str(dhcp_options_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[dhcp_options_id], 
                                        Tags=[
                                            {'Key': 'CreatedBy', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time}
                                            ]
                                            )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateVpnGateway event
        elif eventname == 'CreateVpnGateway':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                vpn_gw_id = detail['responseElements']['vpnGateway']['vpnGatewayId']
                logger.info(f'Tagging new VPC VpnGateway: {str(vpn_gw_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[vpn_gw_id], 
                                        Tags=[
                                            {'Key': 'CreatedBy', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time}
                                            ]
                                            )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateVpnConnection event
        elif eventname == 'CreateVpnConnection':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                vpn_conn_id = detail['responseElements']['vpnConnection']['vpnConnectionId']
                logger.info(f'Tagging new VPC VpnConnection: {str(vpn_conn_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[vpn_conn_id], 
                                        Tags=[
                                            {'Key': 'CreatedBy', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time}
                                            ]
                                            )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateCustomerGateway event
        elif eventname == 'CreateCustomerGateway':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                customer_gw_id = detail['responseElements']['customerGateway']['customerGatewayId']
                customer_gw_type = detail['responseElements']['customerGateway']['type']
                logger.info(f'Tagging new VPC CustomerGateway (type: {str(customer_gw_type)}): {str(customer_gw_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[customer_gw_id], 
                                        Tags=[
                                            {'Key': 'CreatedBy', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time}
                                            ]
                                            )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateVpcPeeringConnection event
        elif eventname == 'CreateVpcPeeringConnection':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                vpc_peering_conn_id = detail['responseElements']['vpcPeeringConnection']['vpcPeeringConnectionId']
                logger.info(f'Tagging new VPC VpcPeeringConnection: {str(vpc_peering_conn_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[vpc_peering_conn_id], 
                                        Tags=[
                                            {'Key': 'CreatedBy', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time}
                                            ]
                                            )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateManagedPrefixList event
        elif eventname == 'CreateManagedPrefixList':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                prefix_list_id = detail['responseElements']['CreateManagedPrefixListResponse']['prefixList']['prefixListId']
                prefix_list_name = (detail['responseElements']['CreateManagedPrefixListResponse']['prefixList']['prefixListName'])
                logger.info(f'Tagging new VPC ManagedPrefixList: {str(prefix_list_name)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[prefix_list_id], 
                                        Tags=[
                                        {'Key': 'CreatedBy', 'Value,': user},
                                        {'Key': 'CreatedAt', 'Value': event_time}
                                        ]
                                        )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateTransitGateway event
        elif eventname == 'CreateTransitGateway':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                transit_gw_id = detail['responseElements']['CreateTransitGatewayResponse']['transitGateway']['transitGatewayId']
                transit_gw_arn = detail['responseElements']['CreateTransitGatewayResponse']['transitGateway']['transitGatewayArn']
                logger.info(f'Tagging new VPC TransitGateway: {str(transit_gw_arn)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[transit_gw_id], 
                                        Tags=[
                                        {'Key': 'CreatedBy', 'Value,': user},
                                        {'Key': 'CreatedAt', 'Value': event_time}
                                        ]
                                        )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateTransitGatewayRouteTable event
        elif eventname == 'CreateTransitGatewayRouteTable':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                transit_gw_rtable_id = detail['responseElements']['CreateTransitGatewayRouteTableResponse']['transitGatewayRouteTable']['transitGatewayRouteTableId']
                logger.info(f'Tagging new VPC TransitGatewayRouteTable: {str(transit_gw_rtable_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[transit_gw_rtable_id], 
                                        Tags=[
                                        {'Key': 'CreatedBy', 'Value,': user},
                                        {'Key': 'CreatedAt', 'Value': event_time}
                                        ]
                                        )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of RunInstances event
        elif eventname == 'CreateNetworkAcl':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                network_acl_id = detail['responseElements']['networkAcl']['networkAclId']
                logger.info(f'Tagging new VPC NetworkAcl: {str(network_acl_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[network_acl_id], 
                                        Tags=[
                                        {'Key': 'CreatedBy', 'Value,': user},
                                        {'Key': 'CreatedAt', 'Value': event_time}
                                        ]
                                        )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateVpcEndpoint event
        elif eventname == 'CreateVpcEndpoint':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                vpc_endpoint_id = detail['responseElements']['CreateVpcEndpointResponse']['vpcEndpoint']['vpcEndpointId']
                endpoint_type = detail['responseElements']['CreateVpcEndpointResponse']['vpcEndpoint']['vpcEndpointType']
                logger.info(f'Tagging new VPC VpcEndpoint (type: {str(endpoint_type)}): {str(vpc_endpoint_id)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[vpc_endpoint_id], 
                                        Tags=[
                                        {'Key': 'CreatedBy', 'Value,': user},
                                        {'Key': 'CreatedAt', 'Value': event_time}
                                        ]
                                        )
                                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateVpcEndpointServiceConfiguration event
        elif eventname == 'CreateVpcEndpointServiceConfiguration':
            # create boto3 client/resource connection
            ec2_client = boto3.resource('ec2', region_name=region)
            try:
                # get values required for tagging from event details
                vpc_endpoint_service_id = detail['responseElements']['CreateVpcEndpointServiceConfigurationResponse']['serviceConfiguration']['serviceId']
                vpc_endpoint_service_name = detail['responseElements']['CreateVpcEndpointServiceConfigurationResponse']['serviceConfiguration']['serviceName']
                vpc_endpoint_service_type = detail['responseElements']['CreateVpcEndpointServiceConfigurationResponse']['serviceConfiguration']['serviceType']
                logger.info(f'Tagging new VPC VpcEndpointServiceConfiguration (type: {str(vpc_endpoint_service_type)}): {str(vpc_endpoint_service_name)}')
                
                # apply tags using ec2_client
                ec2_client.create_tags(Resources=[vpc_endpoint_service_id], 
                                        Tags=[
                                        {'Key': 'CreatedBy', 'Value,': user},
                                        {'Key': 'CreatedAt', 'Value': event_time}
                                        ]
                                        )

            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # AWS Lambda events
        # processing of CreateFunction20150331 event
        elif eventname == 'CreateFunction20150331' and detailtype != "TestEvent":
            # Create boto3 client/resource connection
            lambda_client = boto3.client('lambda', region_name=region)
            try:
                # get values required for tagging from event details
                function_arn = detail['responseElements']['functionArn']
                function_name = detail['responseElements']['functionName']
                logger.info(f'Tagging new lambda function: {str(function_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(function_name)
                
                # use lambda-python function to apply tags using lambda_client
                tagging = lambda key, value: lambda_client.tag_resource(Resource=function_arn, Tags={key: value})
                
                tagging('Name', function_name)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        elif eventname == 'CreateFunction20150331' and detailtype == "TestEvent":
            if test_event(detail, user, region, event_time) is True: pass
            else: return False

        # processing of UpdateFunctionConfiguration20150331v2 event
        elif eventname == 'UpdateFunctionConfiguration20150331v2':
            # Create boto3 client/resource connection
            lambda_client = boto3.client('lambda', region_name=region)
            try:
                # get values required for tagging from event details
                function_arn = detail['responseElements']['functionArn']
                function_name = detail['responseElements']['functionName']
                last_update_status = detail['responseElements']['lastUpdateStatus']
                logger.info(f'Tagging updated Lambda function config: {str(function_name)}')
                
                # use lambda-python function to apply tags using lambda_client
                tagging = lambda key, value: lambda_client.tag_resource(Resource=function_arn, Tags={key: value})
                
                tagging('LastConfigModifiedBy', user)
                tagging('LastConfigModifiedAt', event_time)
                tagging('LastConfigUpdateStatus', last_update_status)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # processing of UpdateFunctionCode20150331v2 event
        elif eventname == 'UpdateFunctionCode20150331v2':
            # Create boto3 client/resource connection
            lambda_client = boto3.client('lambda', region_name=region)
            try:
                # get values required for tagging from event details
                function_arn = detail['responseElements']['functionArn']
                function_name = detail['responseElements']['functionName']
                last_update_status = detail['responseElements']['lastUpdateStatus']
                logger.info(f'Tagging updated Lambda function code: {str(function_name)}')
                
                # use lambda-python function to apply tags using lambda_client
                tagging = lambda key, value: lambda_client.tag_resource(Resource=function_arn, Tags={key: value})
                
                tagging('LastCodeModifiedBy', user)
                tagging('LastCodeModifiedAt', event_time)
                tagging('LastCodeUpdateStatus', last_update_status)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # Step Functions events
        # processing of CreateStateMachine event
        elif eventname == 'CreateStateMachine':
            # Create boto3 client/resource connection
            stepfunctions_client = boto3.client('stepfunctions', region_name=region)
            try:
                # get values required for tagging from event details
                state_machine_name = detail['requestParameters']['name']
                state_machine_arn = detail['responseElements']['stateMachineArn']
                logger.info(f'Tagging new Step Function machine: {str(state_machine_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(state_machine_name)
                
                stepfunctions_client.tag_resource(resourceArn=state_machine_arn,
                                                tags=[
                                                    {'key': 'Name', 'value': state_machine_name},
                                                    {'key': 'CreatedBy', 'value': user},
                                                    {'key': 'CreatedAt', 'value': event_time},
                                                    {'key': 'Env', 'value': env_tag},
                                                    {'key': 'Department', 'value': dep_tag}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateStateMachine event
        elif eventname == 'UpdateStateMachine':
            # Create boto3 client/resource connection
            stepfunctions_client = boto3.client('stepfunctions', region_name=region)
            try:
                # get values required for tagging from event details
                state_machine_name = detail['requestParameters']['stateMachineArn'].split(":")[6]
                state_machine_arn = detail['requestParameters']['stateMachineArn']
                logger.info(f'Tagging updated Step Function machine: {str(state_machine_name)}')
                
                # apply tags using stepfunctions_client
                stepfunctions_client.tag_resource(resourceArn=state_machine_arn,
                                                tags=[
                                                    {'key': 'LastUpdatedBy', 'value': user},
                                                    {'key': 'LastUpdatedAt', 'value': event_time}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateActivity event
        elif eventname == 'CreateActivity':
            # Create boto3 client/resource connection
            stepfunctions_client = boto3.client('stepfunctions', region_name=region)
            try:
                # get values required for tagging from event details
                activity_name = detail['requestParameters']['name']
                activity_arn = detail['responseElements']['activityArn']
                logger.info(f'Tagging new Step Function activity: {str(activity_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(activity_name)
                
                # apply tags using stepfunctions_client
                stepfunctions_client.tag_resource(resourceArn=activity_arn,
                                                tags=[
                                                    {'key': 'Name', 'value': activity_name},
                                                    {'key': 'CreatedBy', 'value': user},
                                                    {'key': 'CreatedAt', 'value': event_time},
                                                    {'key': 'Env', 'value': env_tag},
                                                    {'key': 'Department', 'value': dep_tag}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # AppFlow events    
        # processing of CreateFlow event
        elif eventname == 'CreateFlow':
            # Create boto3 client/resource connection
            appflow_client = boto3.client('appflow', region_name=region)
            try:
                # get values required for tagging from event details
                appflow_name = detail['requestParameters']['flowName']
                appflow_arn = detail['responseElements']['flowArn']
                logger.info(f'Tagging new appflow Flow: {str(appflow_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(appflow_name)
                
                # use lambda-python function to apply tags using appflow_client
                tagging = lambda key, value: appflow_client.tag_resource(resourceArn=appflow_arn, tags={key: value})
                
                tagging('Name', appflow_name)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateFlow event
        elif eventname == 'UpdateFlow':
            appflow_client = boto3.client('appflow', region_name=region)
            try:
                # get values required for tagging from event details
                appflow_name = detail['requestParameters']['flowName']
                appflow_arn = f'arn:aws:appflow:{region}:{aws_account_id}:flow/{appflow_name}'
                logger.info(f'Tagging updated appflow Flow: {str(appflow_name)}')
                
                # use lambda-python function to apply tags using appflow_client
                tagging = lambda key, value: appflow_client.tag_resource(resourceArn=appflow_arn, tags={key: value})
                
                tagging('LastUpdatedBy', user)
                tagging('LastUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # Batch events    
        # processing of CreateJobQueue event
        elif eventname == 'CreateJobQueue':
            # Create boto3 client/resource connection
            batch_client = boto3.client('batch', region_name=region)
            try:
                # get values required for tagging from event details
                batch_job_queue_name = detail['responseElements']['jobQueueName']
                batch_job_queue_arn = detail['responseElements']['jobQueueArn']
                logger.info(f'Tagging new batch Job Queue: {str(batch_job_queue_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(batch_job_queue_name)
                
                # use lambda-python function to apply tags using batch_client
                tagging = lambda key, value: batch_client.tag_resource(resourceArn=batch_job_queue_arn, tags={key: value})
                
                tagging('Name', batch_job_queue_name)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateComputeEnvironment event
        elif eventname == 'CreateComputeEnvironment':
            # Create boto3 client connection
            batch_client = boto3.client('batch', region_name=region)
            try:
                # get values required for tagging from event details
                batch_compute_env_name = detail['responseElements']['computeEnvironmentName']
                batch_compute_env_arn = detail['responseElements']['computeEnvironmentArn']
                batch_compute_env_type = detail['requestParameters']['computeResources']['type']
                logger.info(f'Tagging new batch compute environment: {str(batch_compute_env_name)} (type: {str(batch_compute_env_type)})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(batch_compute_env_name)
                
                # use lambda-python function to apply tags using batch_client
                tagging = lambda key, value: batch_client.tag_resource(resourceArn=batch_compute_env_arn, tags={key: value})
                
                tagging('Name', batch_compute_env_name)
                tagging('Type', batch_compute_env_type)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of RegisterJobDefinition event
        elif eventname == 'RegisterJobDefinition':
            # Create boto3 client/resource connection
            batch_client = boto3.client('batch', region_name=region)
            try:
                # get values required for tagging from event details
                batch_job_definition_name = detail['responseElements']['jobDefinitionName']
                batch_job_definition_arn = detail['responseElements']['jobDefinitionArn']
                batch_job_definition_type = [type for type in detail['requestParameters']['platformCapabilities']][0]
                logger.info(f'Tagging new batch job definition: {str(batch_job_definition_name)} (type: {str(batch_job_definition_type)})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(batch_job_definition_name)
                
                # use lambda-python function to apply tags using batch_client
                tagging = lambda key, value: batch_client.tag_resource(resourceArn=batch_job_definition_arn, tags={key: value})
                
                tagging('Name', batch_job_definition_name)
                tagging('Type', batch_job_definition_type)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of SubmitJob event
        elif eventname == 'SubmitJob':
            # Create boto3 client/resource connection
            batch_client = boto3.client('batch', region_name=region)
            try:
                # get values required for tagging from event details
                batch_job_name = detail['responseElements']['jobName']
                batch_job_arn = detail['responseElements']['jobArn']
                batch_job_queue = detail['requestParameters']['jobQueue']
                logger.info(f'Tagging new batch job definition: {str(batch_job_name)} (queue: {str(batch_job_queue)})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(batch_job_name)
                
                # use lambda-python function to apply tags using batch_client
                tagging = lambda key, value: batch_client.tag_resource(resourceArn=batch_job_arn, tags={key: value})
                
                tagging('Name', batch_job_name)
                tagging('Queue', batch_job_queue)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)            
                return False
            
        # processing of UpdateJobQueue event
        elif eventname == 'UpdateJobQueue':
            # Create boto3 client/resource connection
            batch_client = boto3.client('batch', region_name=region)
            try:
                # get values required for tagging from event details
                batch_job_queue_name = detail['responseElements']['jobQueueName']
                batch_job_queue_arn = detail['responseElements']['jobQueueArn']
                logger.info(f'Tagging updated batch Job Queue: {str(batch_job_queue_name)}')
                
                # use lambda-python function to apply tags using batch_client
                tagging = lambda key, value: batch_client.tag_resource(resourceArn=batch_job_queue_arn, tags={key: value})
                
                tagging('LastUpdatedBy', user)
                tagging('LastUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateComputeEnvironment event
        elif eventname == 'UpdateComputeEnvironment':
            # Create boto3 client/resource connection
            batch_client = boto3.client('batch', region_name=region)
            try:
                # get values required for tagging from event details
                batch_compute_env_name = detail['responseElements']['computeEnvironmentName']
                batch_compute_env_arn = detail['responseElements']['computeEnvironmentArn']
                batch_compute_env_type = [compute_env['computeResources']['type'] for compute_env in batch_client.describe_compute_environments(computeEnvironments=[batch_compute_env_name])['computeEnvironments']][0]

                logger.info(f'Tagging updated batch compute environment: {str(batch_compute_env_name)} (type: {str(batch_compute_env_type)})')
                
                # use lambda-python function to apply tags using batch_client
                tagging = lambda key, value: batch_client.tag_resource(resourceArn=batch_compute_env_arn, tags={key: value})
                
                tagging('LastUpdatedBy', user)
                tagging('LastUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # Route53 events
        # processing of CreateHostedZone event
        elif eventname == 'CreateHostedZone':
            # Create boto3 client/resource connection
            route53_client = boto3.client('route53', region_name=region)
            try:
                # get values required for tagging from event details
                hosted_zone_id = detail['responseElements']['hostedZone']['id'].split('/')[2]
                hosted_zone_name = detail['responseElements']['hostedZone']['name']
                logger.info(f'Tagging new route53 hosted zone: {str(hosted_zone_name)}')
                
                # apply tags using route53_client
                route53_client.change_tags_for_resource(
                                                ResourceType='hostedzone',
                                                ResourceId=hosted_zone_id,
                                                AddTags=[
                                                    {'Key': 'Name', 'Value': hosted_zone_name},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'CreatedAt', 'Value': event_time}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateHealthCheck event
        elif eventname == 'CreateHealthCheck':
            # Create boto3 client/resource connection
            route53_client = boto3.client('route53', region_name=region)
            try:
                # get values required for tagging from event details
                health_check_id = detail['responseElements']['healthCheck']['id']
                health_check_name = detail['responseElements']['healthCheck']['healthCheckConfig']
                logger.info(f'Tagging new route53 health check: {json.dumps(health_check_name, indent=1, sort_keys=True, default=str)}')
                
                # apply tags using route53_client
                route53_client.change_tags_for_resource(
                                                ResourceType='healthcheck',
                                                ResourceId=health_check_id,
                                                AddTags=[
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'CreatedAt', 'Value': event_time}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateHealthCheck event
        elif eventname == 'UpdateHealthCheck':
            # Create boto3 client/resource connection
            route53_client = boto3.client('route53', region_name=region)
            try:
                # get values required for tagging from event details
                health_check_id = detail['responseElements']['healthCheck']['id']
                logger.info(f'Tagging updated route53 health check: {str(health_check_id)}')
                
                # apply tags using route53_client
                route53_client.change_tags_for_resource(
                                                ResourceType='healthcheck',
                                                ResourceId=health_check_id,
                                                AddTags=[
                                                    {'Key': 'LastUpdatedBy', 'Value': user},
                                                    {'Key': 'LastUpdatedAt', 'Value': event_time}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
        
        # Route53 Resolver events    
        # processing of CreateResolverRule event
        elif eventname == 'CreateResolverRule':
            # Create boto3 client/resource connection
            route53resolver_client = boto3.client('route53resolver', region_name=region)
            try:
                # get values required for tagging from event details
                resolver_rule_arn = detail['responseElements']['resolverRule']['arn']
                resolver_rule_name = detail['responseElements']['resolverRule']['name']
                logger.info(f'Tagging new route53 resolver rule: {str(resolver_rule_name)}')
                
                # apply tags using route53resolver_client
                route53resolver_client.tag_resource(
                                                ResourceArn=resolver_rule_arn,
                                                Tags=[
                                                    {'Key': 'Name', 'Value': resolver_rule_name},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'CreatedAt', 'Value': event_time}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateResolverRule event
        elif eventname == 'UpdateResolverRule':
            # Create boto3 client/resource connection
            route53resolver_client = boto3.client('route53resolver', region_name=region)
            try:
                # get values required for tagging from event details
                resolver_rule_arn = detail['responseElements']['resolverRule']['arn']
                resolver_rule_name = detail['responseElements']['resolverRule']['name']
                logger.info(f'Tagging updated route53 resolver rule: {str(resolver_rule_name)}')
                
                # apply tags using route53resolver_client
                route53resolver_client.tag_resource(
                                                ResourceArn=resolver_rule_arn,
                                                Tags=[
                                                    {'Key': 'LastUpdatedBy', 'Value': user},
                                                    {'Key': 'LastUpdatedAt', 'Value': event_time}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateResolverEndpoint event
        elif eventname == 'CreateResolverEndpoint':
            # Create boto3 client/resource connection
            route53resolver_client = boto3.client('route53resolver', region_name=region)
            try:
                # get values required for tagging from event details
                resolver_endpoint_arn = detail['responseElements']['resolverEndpoint']['arn']
                resolver_endpoint_name = detail['responseElements']['resolverEndpoint']['name']
                logger.info(f'Tagging new route53 resolver rule: {str(resolver_endpoint_name)}')
                
                # apply tags using route53resolver_client
                route53resolver_client.tag_resource(
                                                ResourceArn=resolver_endpoint_arn,
                                                Tags=[
                                                    {'Key': 'Name', 'Value': resolver_endpoint_name},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'CreatedAt', 'Value': event_time}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateResolverEndpoint event
        elif eventname == 'UpdateResolverEndpoint':
            # Create boto3 client/resource connection
            route53resolver_client = boto3.client('route53resolver', region_name=region)
            try:
                # get values required for tagging from event details
                resolver_endpoint_arn = detail['responseElements']['resolverEndpoint']['arn']
                resolver_endpoint_name = detail['responseElements']['resolverEndpoint']['name']
                logger.info(f'Tagging updated route53 resolver rule: {str(resolver_endpoint_name)}')
                
                # apply tags using route53resolver_client
                route53resolver_client.tag_resource(
                                                ResourceArn=resolver_endpoint_arn,
                                                Tags=[
                                                    {'Key': 'LastUpdatedBy', 'Value': user},
                                                    {'Key': 'LastUpdatedAt', 'Value': event_time}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # RDS events
        # processing of CreateDBInstance event
        elif eventname == 'CreateDBInstance':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_instance_identifier = detail['responseElements']['dBInstanceIdentifier']
                db_instance_arn = detail['responseElements']['dBInstanceArn']
                logger.info(f'Tagging new RDS DB instance: {str(db_instance_identifier)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(db_instance_identifier)
                
                # apply tags using rds_client
                rds_client.add_tags_to_resource(ResourceName=db_instance_arn,
                                                Tags=[
                                                    {'Key': 'Name', 'Value': db_instance_identifier},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'CreatedAt', 'Value': event_time},
                                                    {'Key': 'Env', 'Value': env_tag},
                                                    {'Key': 'Department', 'Value': dep_tag}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateDBInstanceReadReplica event
        elif eventname == 'CreateDBInstanceReadReplica':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_replica_instance_identifier = detail['responseElements']['dBInstanceIdentifier']
                db_replica_instance_arn = detail['responseElements']['dBInstanceArn']
                db_source_instance_arn = detail['requestParameters']['sourceDBInstanceIdentifier']
                # get db_source_instance_identifier from arn
                db_source_instance_identifier = db_source_instance_arn.split(":")[6]
                logger.info(f'Tagging read replica RDS DB instance: {str(db_replica_instance_identifier)} (replica of {str(db_source_instance_identifier)})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(db_replica_instance_identifier)
                
                # apply tags using rds_client
                rds_client.add_tags_to_resource(ResourceName=db_replica_instance_arn,
                                                Tags=[
                                                    {'Key': 'Name', 'Value': db_replica_instance_identifier},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'CreatedAt', 'Value': event_time},
                                                    {'Key': 'Env', 'Value': env_tag},
                                                    {'Key': 'Department', 'Value': dep_tag},
                                                    {'Key': 'SourceDB', 'Value': db_source_instance_identifier}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateDBSnapshot event
        elif eventname == 'CreateDBSnapshot':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_snapshot_identifier = detail['responseElements']['dBSnapshotIdentifier']
                db_snapshot_arn = detail['responseElements']['dBSnapshotArn']
                db_instance_identifier = detail['responseElements']['dBInstanceIdentifier']
                logger.info(f'Tagging new DB Instance Snapshot: {str(db_snapshot_identifier)} (taken from {str(db_instance_identifier)} instance)')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(db_snapshot_identifier)
                
                # apply tags using rds_client
                rds_client.add_tags_to_resource(ResourceName=db_snapshot_arn,
                                                Tags=[
                                                    {'Key': 'Name', 'Value': db_snapshot_identifier},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'CreatedAt', 'Value': event_time},
                                                    {'Key': 'Env', 'Value': env_tag},
                                                    {'Key': 'Department', 'Value': dep_tag},
                                                    {'Key': 'SourceDB', 'Value': db_instance_identifier}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateDBClusterSnapshot event
        elif eventname == 'CreateDBClusterSnapshot':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_cluster_snapshot_identifier = detail['responseElements']['dBClusterSnapshotIdentifier']
                db_cluster_snapshot_arn = detail['responseElements']['dBClusterSnapshotArn']
                db_cluster_identifier = detail['responseElements']['dBClusterIdentifier']
                logger.info(f'Tagging new DB Cluster Snapshot: {str(db_cluster_snapshot_identifier)} (taken from {str(db_cluster_identifier)} cluster)')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(db_cluster_snapshot_identifier)
                
                # apply tags using rds_client
                rds_client.add_tags_to_resource(ResourceName=db_cluster_snapshot_arn,
                                                Tags=[
                                                    {'Key': 'Name', 'Value': db_cluster_snapshot_identifier},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'CreatedAt', 'Value': event_time},
                                                    {'Key': 'Env', 'Value': env_tag},
                                                    {'Key': 'Department', 'Value': dep_tag},
                                                    {'Key': 'SourceDB', 'Value': db_cluster_identifier}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of RebootDBInstance event
        elif eventname == 'RebootDBInstance':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_instance_identifier = detail['responseElements']['dBInstanceIdentifier']
                db_instance_arn = detail['responseElements']['dBInstanceArn']
                logger.info(f'RDS DB instance has been rebooted: {str(db_instance_identifier)}')
                
                # apply tags using rds_client
                rds_client.add_tags_to_resource(ResourceName=db_instance_arn,
                                                Tags=[
                                                    {'Key': 'LastRebootedBy', 'Value': user},
                                                    {'Key': 'LastRebootedAt', 'Value': event_time}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of StartDBInstance event
        elif eventname == 'StartDBInstance':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_instance_identifier = detail['responseElements']['dBInstanceIdentifier']
                db_instance_arn = detail['responseElements']['dBInstanceArn']
                logger.info(f'RDS DB instance has been started: {str(db_instance_identifier)}')
                
                # apply tags using rds_client
                rds_client.add_tags_to_resource(ResourceName=db_instance_arn,
                                                Tags=[
                                                    {'Key': 'LastStartedBy', 'Value': user},
                                                    {'Key': 'LastStartedAt', 'Value': event_time}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)                
                return False
            
        # processing of StopDBInstance event
        elif eventname == 'StopDBInstance':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_instance_identifier = detail['responseElements']['dBInstanceIdentifier']
                db_instance_arn = detail['responseElements']['dBInstanceArn']
                logger.info(f'RDS DB instance has been stopped: {str(db_instance_identifier)}')
                
                # apply tags using rds_client
                rds_client.add_tags_to_resource(ResourceName=db_instance_arn,
                                                Tags=[
                                                    {'Key': 'LastStoppedBy', 'Value': user},
                                                    {'Key': 'LastStoppedAt', 'Value': event_time}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)               
                return False
            
        # processing of ModifyDBInstance event
        elif eventname == 'ModifyDBInstance':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_instance_identifier = detail['responseElements']['dBInstanceIdentifier']
                db_instance_arn = detail['responseElements']['dBInstanceArn']
                logger.info(f'RDS DB instance has been modified: {str(db_instance_identifier)}')
                
                # apply tags using rds_client
                rds_client.add_tags_to_resource(ResourceName=db_instance_arn,
                                                Tags=[
                                                    {'Key': 'LastModifiedBy', 'Value': user},
                                                    {'Key': 'LastModifiedAt', 'Value': event_time}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateDBSubnetGroup event
        elif eventname == 'CreateDBSubnetGroup':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_subnet_group_name = detail['responseElements']['dBSubnetGroupName']
                db_subnet_group_arn = detail['responseElements']['dBSubnetGroupArn']
                logger.info(f'Tagging new RDS DB Subnet Group: {str(db_subnet_group_name)} ({str(db_subnet_group_arn)})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(db_subnet_group_name)
                
                # apply tags using rds_client
                rds_client.add_tags_to_resource(ResourceName=db_subnet_group_arn,
                                                Tags=[
                                                    {'Key': 'Name', 'Value': db_subnet_group_name},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'Env', 'Value': env_tag},
                                                    {'Key': 'Department', 'Value': dep_tag}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of ModifyDBSubnetGroup event
        elif eventname == 'ModifyDBSubnetGroup':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_subnet_group_name = detail['responseElements']['dBSubnetGroupName']
                db_subnet_group_arn = detail['responseElements']['dBSubnetGroupArn']
                logger.info(f'Tagging modified RDS DB Subnet Group: {str(db_subnet_group_name)} ({str(db_subnet_group_arn)})')
                
                # apply tags using rds_client
                rds_client.add_tags_to_resource(ResourceName=db_subnet_group_arn,
                                                Tags=[
                                                    {'Key': 'LastModifiedBy', 'Value': user},
                                                    {'Key': 'LastModifiedAt', 'Value': event_time}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateDBParameterGroup event
        elif eventname == 'CreateDBParameterGroup':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_param_group_name = detail['responseElements']['dBParameterGroupName']
                db_param_group_arn = detail['responseElements']['dBParameterGroupArn']
                logger.info(f'Tagging new RDS DB Parameter Group: {str(db_param_group_name)} ({str(db_param_group_arn)})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(db_param_group_name)
                
                # apply tags using rds_client
                rds_client.add_tags_to_resource(ResourceName=db_param_group_arn,
                                                Tags=[
                                                    {'Key': 'Name', 'Value': db_param_group_name},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'Env', 'Value': env_tag},
                                                    {'Key': 'Department', 'Value': dep_tag}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of ModifyDBParameterGroup event
        elif eventname == 'ModifyDBParameterGroup':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_param_group_name = detail['requestParameters']['dBParameterGroupName']
                # get details on db parameter group
                describe_db_param_group = rds_client.describe_db_parameter_groups(DBParameterGroupName=db_param_group_name)
                for db_param_group in describe_db_param_group['DBParameterGroups']:
                    # get arn
                    db_param_group_arn = db_param_group['DBParameterGroupArn']
                    logger.info(f'Tagging modified RDS DB Parameter Group: {str(db_param_group_name)} ({str(db_param_group_arn)})')

                    # apply tags using rds_client
                    rds_client.add_tags_to_resource(ResourceName=db_param_group_arn,
                                                    Tags=[
                                                        {'Key': 'LastModifiedBy', 'Value': user},
                                                        {'Key': 'LastModifiedAt', 'Value': event_time}
                                                        ]
                                                    )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateOptionGroup event
        elif eventname == 'CreateOptionGroup':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_option_group_name = detail['responseElements']['optionGroupName']
                db_option_group_arn = detail['responseElements']['optionGroupArn']
                logger.info(f'Tagging new RDS DB Option Group: {str(db_option_group_name)} ({str(db_option_group_arn)})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(db_option_group_name)
                
                # apply tags using rds_client
                rds_client.add_tags_to_resource(ResourceName=db_option_group_arn,
                                                Tags=[
                                                    {'Key': 'Name', 'Value': db_option_group_name},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'Env', 'Value': env_tag},
                                                    {'Key': 'Department', 'Value': dep_tag}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of ModifyOptionGroup event
        elif eventname == 'ModifyOptionGroup':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_option_group_name = detail['responseElements']['optionGroupName']
                db_option_group_arn = detail['responseElements']['optionGroupArn']
                logger.info(f'Tagging modified RDS DB Option Group: {str(db_option_group_name)} ({str(db_option_group_arn)})')
                
                # apply tags using rds_client
                rds_client.add_tags_to_resource(ResourceName=db_option_group_arn,
                                                Tags=[
                                                    {'Key': 'LastModifiedBy', 'Value': user},
                                                    {'Key': 'LastModifiedAt', 'Value': event_time}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
            
        # processing of CreateEventSubscription event
        elif eventname == 'CreateEventSubscription':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_event_subscription_name = detail['responseElements']['custSubscriptionId']
                db_event_subscription_arn = detail['responseElements']['eventSubscriptionArn']
                logger.info(f'Tagging new RDS DB Event Subscription: {str(db_event_subscription_name)} ({str(db_event_subscription_arn)})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(db_event_subscription_name)
                
                # apply tags using rds_client
                rds_client.add_tags_to_resource(ResourceName=db_event_subscription_arn,
                                                Tags=[
                                                    {'Key': 'Name', 'Value': db_event_subscription_name},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'Env', 'Value': env_tag},
                                                    {'Key': 'Department', 'Value': dep_tag}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of ModifyEventSubscription event
        elif eventname == 'ModifyEventSubscription':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_event_subscription_name = detail['responseElements']['custSubscriptionId']
                db_event_subscription_arn = detail['responseElements']['eventSubscriptionArn']
                logger.info(f'Tagging modified RDS DB Event Subscription: {str(db_event_subscription_name)} ({str(db_event_subscription_arn)})')
                
                # apply tags using rds_client
                rds_client.add_tags_to_resource(ResourceName=db_event_subscription_arn,
                                                Tags=[
                                                    {'Key': 'LastModifiedBy', 'Value': user},
                                                    {'Key': 'LastModifiedAt', 'Value': event_time}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateDBProxy event
        elif eventname == 'CreateDBProxy':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_proxy_name = detail['responseElements']['dBProxy']['dBProxyName']
                db_proxy_arn = detail['responseElements']['dBProxy']['dBProxyArn']
                logger.info(f'Tagging new RDS DB Proxy: {str(db_proxy_name)} ({str(db_proxy_arn)})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(db_proxy_name)
                
                # apply tags using rds_client
                rds_client.add_tags_to_resource(ResourceName=db_proxy_arn,
                                                Tags=[
                                                    {'Key': 'Name', 'Value': db_proxy_name},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'Env', 'Value': env_tag},
                                                    {'Key': 'Department', 'Value': dep_tag}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)              
                return False
            
        # processing of ModifyDBProxy event
        elif eventname == 'ModifyDBProxy':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_proxy_name = detail['responseElements']['dBProxy']['dBProxyName']
                db_proxy_arn = detail['responseElements']['dBProxy']['dBProxyArn']
                logger.info(f'Tagging modified RDS DB Proxy: {str(db_proxy_name)} ({str(db_proxy_arn)})')
                
                # apply tags using rds_client
                rds_client.add_tags_to_resource(ResourceName=db_proxy_arn,
                                                Tags=[
                                                    {'Key': 'LastModifiedBy', 'Value': user},
                                                    {'Key': 'LastModifiedAt', 'Value': event_time}    
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)             
                return False
            
        # processing of CreateDBClusterParameterGroup event
        elif eventname == 'CreateDBClusterParameterGroup':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_cluster_param_group_name = detail['responseElements']['dBClusterParameterGroupName']
                db_cluster_param_group_arn = detail['responseElements']['dBClusterParameterGroupArn']
                logger.info(f'Tagging new RDS DB Cluster Parameter group: {str(db_cluster_param_group_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(db_cluster_param_group_name)
                
                # apply tags using rds_client
                rds_client.add_tags_to_resource(ResourceName=db_cluster_param_group_arn,
                                                Tags=[
                                                    {'Key': 'Name', 'Value': db_cluster_param_group_name},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'Env', 'Value': env_tag},
                                                    {'Key': 'Department', 'Value': dep_tag}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of ModifyDBClusterParameterGroup event
        elif eventname == 'ModifyDBClusterParameterGroup':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_cluster_param_group_name = detail['responseElements']['dBClusterParameterGroupName']
                # get details on db cluster parameter group to get its arn
                describe_db_cluster_param_group = rds_client.describe_db_cluster_parameter_groups(DBClusterParameterGroupName=db_cluster_param_group_name)
                for db_cluster_param_group in describe_db_cluster_param_group['DBClusterParameterGroups']:
                    db_param_group_arn = db_cluster_param_group['DBClusterParameterGroupArn']
                    logger.info(f'Tagging modified RDS DB Cluster Parameter group: {str(db_cluster_param_group_name)}')

                    # apply tags using rds_client
                    rds_client.add_tags_to_resource(ResourceName=db_param_group_arn,
                                                    Tags=[
                                                        {'Key': 'LastModifiedBy', 'Value': user},
                                                        {'Key': 'LastModifiedAt', 'Value': event_time}
                                                        ]
                                                    )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateDBCluster event
        elif eventname == 'CreateDBCluster':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_cluster_identifier = detail['responseElements']['dBClusterIdentifier']
                db_cluster_arn = detail['responseElements']['dBClusterArn']
                db_cluster_engine = detail['responseElements']['engine']
                db_cluster_engine_version = detail['responseElements']['engineVersion']
                logger.info(f'Tagging new RDS DB cluster: {str(db_cluster_identifier)} ({str(db_cluster_engine)}-{str(db_cluster_engine_version)})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(db_cluster_identifier)
                
                # apply tags using rds_client
                rds_client.add_tags_to_resource(ResourceName=db_cluster_arn,
                                                Tags=[
                                                    {'Key': 'Name', 'Value': db_cluster_identifier},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'ClusterType', 'Value': 'regional'},
                                                    {'Key': 'Env', 'Value': env_tag},
                                                    {'Key': 'Engine', 'Value': db_cluster_engine},
                                                    {'Key': 'EngineVersion', 'Value': db_cluster_engine_version},
                                                    {'Key': 'Department', 'Value': dep_tag}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)                
                return False
            
        # processing of ModifyDBCluster event
        elif eventname == 'ModifyDBCluster':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                db_cluster_identifier = detail['responseElements']['dBClusterIdentifier']
                db_cluster_arn = detail['responseElements']['dBClusterArn']
                logger.info(f'Tagging modified RDS DB Cluster: {str(db_cluster_identifier)} ({str(db_cluster_arn)})')
                
                # apply tags using rds_client
                rds_client.add_tags_to_resource(ResourceName=db_cluster_arn,
                                                Tags=[
                                                    {'Key': 'LastModifiedBy', 'Value': user},
                                                    {'Key': 'LastModifiedAt', 'Value': event_time}    
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)                
                return False
        
        # processing of CreateGlobalCluster event
        elif eventname == 'CreateGlobalCluster':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                global_cluster_identifier = detail['responseElements']['globalClusterIdentifier']
                global_cluster_engine = detail['responseElements']['engine']
                global_cluster_engine_version = detail['responseElements']['engineVersion']
                logger.info(f'Tagging new RDS global cluster: {str(global_cluster_identifier)} ({str(global_cluster_engine)}-{str(global_cluster_engine_version)})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(global_cluster_identifier)
                
                # get db cluster arn
                for db_cluster in detail['responseElements']['globalClusterMembers']:
                    db_cluster_arn = db_cluster['dBClusterArn']
                    
                    logger.info(f'Tagging member of RDS global cluster: {str(db_cluster_arn)}')
                    
                    # apply tags using rds_client
                    rds_client.add_tags_to_resource(ResourceName=db_cluster_arn,
                                                    Tags=[
                                                        {'Key': 'CreatedBy', 'Value': user},
                                                        {'Key': 'ClusterType', 'Value': 'global'},
                                                        {'Key': 'GlobalClusterName', 'Value': global_cluster_identifier},
                                                        {'Key': 'Engine', 'Value': global_cluster_engine},
                                                        {'Key': 'EngineVersion', 'Value': global_cluster_engine_version},
                                                        {'Key': 'Env', 'Value': env_tag},
                                                        {'Key': 'Department', 'Value': dep_tag}
                                                        ]
                                                    )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of ModifyGlobalCluster event
        elif eventname == 'ModifyGlobalCluster':
            # Create boto3 client/resource connection
            rds_client = boto3.client('rds', region_name=region)
            try:
                # get values required for tagging from event details
                global_cluster_identifier = detail['responseElements']['globalClusterIdentifier']
                logger.info(f'Tagging modified RDS Global Cluster: {str(global_cluster_identifier)}')
                
                # get db global cluster arn
                for db_global_cluster in detail['responseElements']['globalClusterMembers']:
                    db_global_cluster_arn = db_global_cluster['dBClusterArn']
                    
                    logger.info(f'Tagging modified member of RDS Global Cluster: {str(db_global_cluster_arn)}')
                
                    # apply tags using rds_client
                    rds_client.add_tags_to_resource(ResourceName=db_global_cluster_arn,
                                                    Tags=[
                                                        {'Key': 'LastModifiedBy', 'Value': user},
                                                        {'Key': 'LastModifiedAt', 'Value': event_time}    
                                                        ]
                                                    )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
        
        # Secrets Manager events   
        # processing of CreateSecret event
        elif eventname == 'CreateSecret':
            # Create boto3 client/resource connection
            secretsmanager_client = boto3.client('secretsmanager', region_name=region)
            try:
                # get values required for tagging from event details
                secret_name = detail['requestParameters']['name']
                logger.info(f'Tagging AWS Secret: {str(secret_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(secret_name)
                
                # apply tags using secretsmanager_client
                secretsmanager_client.tag_resource(SecretId=secret_name,
                                                Tags=[
                                                    {'Key': 'Name', 'Value': re.sub('[\!\?\;\>\<]','', secret_name)},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'Env', 'Value': env_tag},
                                                    {'Key': 'Department', 'Value': dep_tag}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateSecret event
        elif eventname == 'UpdateSecret':
            # Create boto3 client/resource connection
            secretsmanager_client = boto3.client('secretsmanager', region_name=region)
            try:
                # get values required for tagging from event details
                secret_name = detail['requestParameters']['secretId']
                logger.info(f'Tagging updated AWS Secret: {str(secret_name)}')
                
                # apply tags using secretsmanager_client
                secretsmanager_client.tag_resource(SecretId=secret_name,
                                                Tags=[
                                                    {'Key': 'LastUpdatedBy', 'Value': user},
                                                    {'Key': 'LastUpdatedAt', 'Value': event_time}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # CodePipeline events   
        # processing of CreatePipeline event
        elif eventname == 'CreatePipeline':
            # Create boto3 client/resource connection
            codepipeline_client = boto3.client('codepipeline', region_name=region)
            try:
                # get values required for tagging from event details
                pipeline_name = detail['responseElements']['pipeline']['name']
                # # get arn using get_pipeline boto3 method
                pipeline_arn = codepipeline_client.get_pipeline(name=pipeline_name)['metadata']['pipelineArn']
                logger.info(f'Tagging new code pipeline: {str(pipeline_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(pipeline_name)
                
                # apply tags using codepipeline_client
                codepipeline_client.tag_resource(resourceArn=pipeline_arn,
                                                tags=[
                                                    {'key': 'Name', 'value': pipeline_name},
                                                    {'key': 'CreatedBy', 'value': user},
                                                    {'key': 'CreatedAt', 'value': event_time},
                                                    {'key': 'Env', 'value': env_tag},
                                                    {'key': 'Department', 'value': dep_tag}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdatePipeline event
        elif eventname == 'UpdatePipeline':
            # Create boto3 client/resource connection
            codepipeline_client = boto3.client('codepipeline', region_name=region)
            try:
                pipeline_name = detail['responseElements']['pipeline']['name']
                pipeline_arn = codepipeline_client.get_pipeline(name=pipeline_name)['metadata']['pipelineArn']
                logger.info(f'Tagging updated code pipeline: {str(pipeline_name)}')
                
                # apply tags using codepipeline_client
                codepipeline_client.tag_resource(resourceArn=pipeline_arn,
                                                tags=[
                                                    {'key': 'LastUpdatedBy', 'value': user},
                                                    {'key': 'LastUpdatedAt', 'value': event_time}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False      
            
        # CodeStar events   
        # processing of CreateProject event
        elif eventname == 'CreateProject' and eventsource == 'codestar.amazonaws.com':
            # Create boto3 client/resource connection
            codestar_client = boto3.client('codestar', region_name=region)
            try:
                # get values required for tagging from event details
                codestar_project_id = detail['responseElements']['id']
                codestar_project_name = detail['requestParameters']['name']
                logger.info(f'Tagging new CodeStar project: {str(codestar_project_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(codestar_project_name)
                
                # use lambda-python function to apply tags using codestar_client
                tagging = lambda key, value: codestar_client.tag_project(id=codestar_project_id, tags={key: value})
                
                tagging('Name', codestar_project_name)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateProject event
        elif eventname == 'UpdateProject' and eventsource == 'codestar.amazonaws.com':
            # Create boto3 client/resource connection
            codestar_client = boto3.client('codestar', region_name=region)
            try:
                # get values required for tagging from event details
                codestar_project_id = detail['requestParameters']['id']
                codestar_project_name = detail['requestParameters']['name']
                logger.info(f'Tagging updated CodeStart project: {str(codestar_project_name)}')
                
                # use lambda-python function to apply tags using codestar_client
                tagging = lambda key, value: codestar_client.tag_project(id=codestar_project_id, tags={key: value})
                
                tagging('LastUpdateBy', user)
                tagging('LastUpdateAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # CodeArtifact events   
        # processing of CreateRepository event
        elif eventname == 'CreateRepository' and eventsource == 'codeartifact.amazonaws.com':
            # Create boto3 client/resource connection
            codeartifact_client = boto3.client('codeartifact', region_name=region)
            try:
                # get values required for tagging from event details
                codeartifact_domain_name = detail['responseElements']['repository']['domainName']
                codeartifact_repo_name = detail['responseElements']['repository']['name']
                codeartifact_repo_arn = detail['responseElements']['repository']['arn']
                logger.info(f'Tagging new CodeArtifact repository: {str(codeartifact_repo_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(codeartifact_repo_name)
                
                # apply tags using codeartifact_client
                codeartifact_client.tag_resource(resourceArn=codeartifact_repo_arn,
                                                tags=[
                                                    {'key': 'Name', 'value': codeartifact_repo_name},
                                                    {'key': 'Domain', 'value': codeartifact_domain_name},
                                                    {'key': 'CreatedBy', 'value': user},
                                                    {'key': 'CreatedAt', 'value': event_time},
                                                    {'key': 'Env', 'value': env_tag},
                                                    {'key': 'Department', 'value': dep_tag}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateDomain event
        elif eventname == 'CreateDomain' and eventsource == 'codeartifact.amazonaws.com':
            # Create boto3 client/resource connection
            codeartifact_client = boto3.client('codeartifact', region_name=region)
            try:
                # get values required for tagging from event details
                codeartifact_domain_name = detail['responseElements']['domain']['name']
                codeartifact_domain_arn = detail['responseElements']['domain']['arn']
                logger.info(f'Tagging new CodeArtifact domain: {str(codeartifact_domain_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(codeartifact_domain_name)
                
                # apply tags using codeartifact_client
                codeartifact_client.tag_resource(resourceArn=codeartifact_domain_arn,
                                                tags=[
                                                    {'key': 'Name', 'value': codeartifact_domain_name},
                                                    {'key': 'CreatedBy', 'value': user},
                                                    {'key': 'CreatedAt', 'value': event_time},
                                                    {'key': 'Env', 'value': env_tag},
                                                    {'key': 'Department', 'value': dep_tag}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateRepository event
        elif eventname == 'UpdateRepository' and eventsource == 'codeartifact.amazonaws.com':
            # Create boto3 client/resource connection
            codeartifact_client = boto3.client('codeartifact', region_name=region)
            try:
                # get values required for tagging from event details
                codeartifact_domain_name = detail['responseElements']['repository']['domainName']
                codeartifact_repo_name = detail['responseElements']['repository']['name']
                codeartifact_repo_arn = detail['responseElements']['repository']['arn']
                logger.info(f'Tagging updated CodeArtifact repository: {str(codeartifact_repo_name)}')
                
                # apply tags using codeartifact_client
                codeartifact_client.tag_resource(resourceArn=codeartifact_repo_arn,
                                                tags=[
                                                    {'key': 'LastUpdatedBy', 'value': user},
                                                    {'key': 'LastUpdatedAt', 'value': event_time}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # CodeCommit events   
        # processing of CreateRepository event
        elif eventname == 'CreateRepository' and eventsource == 'codecommit.amazonaws.com':
            # Create boto3 client/resource connection           
            codecommit_client = boto3.client('codecommit', region_name=region)
            try:
                # get values required for tagging from event details
                codecommit_repo_name = detail['responseElements']['repositoryMetadata']['repositoryName']
                codecommit_repo_arn = detail['responseElements']['repositoryMetadata']['arn']
                logger.info(f'Tagging new CodeCommit repository: {str(codecommit_repo_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(codecommit_repo_name)
                
                # use lambda-python function to apply tags using codecommit_client
                tagging = lambda key, value: codecommit_client.tag_resource(resourceArn=codecommit_repo_arn, tags={key: value})
                
                tagging('Name', codecommit_repo_name)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateRepositoryName event
        elif eventname == 'UpdateRepositoryName' and eventsource == 'codecommit.amazonaws.com':
            # Create boto3 client/resource connection           
            codecommit_client = boto3.client('codecommit', region_name=region)
            try:
                # get values required for tagging from event details
                codecommit_repo_new_name = detail['requestParameters']['newName']
                # determine arn using aws arn convention
                codecommit_repo_arn = f'arn:aws:codecommit:{region}:{aws_account_id}:{codecommit_repo_new_name}'
                logger.info(f'Tagging updated CodeCommit repository name: {str(codecommit_repo_new_name)}')
                
                # use lambda-python function to apply tags using codecommit_client
                tagging = lambda key, value: codecommit_client.tag_resource(resourceArn=codecommit_repo_arn, tags={key: value})
                
                tagging('Name', codecommit_repo_new_name)
                tagging('NameUpdatedBy', user)
                tagging('NameUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateRepositoryDescription event
        elif eventname == 'UpdateRepositoryDescription' and eventsource == 'codecommit.amazonaws.com':
            # Create boto3 client/resource connection           
            codecommit_client = boto3.client('codecommit', region_name=region)
            try:
                # get values required for tagging from event details
                codecommit_repo_name = detail['requestParameters']['repositoryName']
                # determine arn using aws arn convention
                codecommit_repo_arn = f'arn:aws:codecommit:{region}:{aws_account_id}:{codecommit_repo_name}'
                logger.info(f'Tagging updated CodeCommit repository description: {str(codecommit_repo_name)}')
                
                # use lambda-python function to apply tags using codecommit_client
                tagging = lambda key, value: codecommit_client.tag_resource(resourceArn=codecommit_repo_arn, tags={key: value})
                
                tagging('DescriptionUpdatedBy', user)
                tagging('DescriptionUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # CodeBuild events   
        # processing of CreateProject event
        elif eventname == 'CreateProject' and eventsource == 'codebuild.amazonaws.com':
            # Create boto3 client/resource connection
            codebuild_client = boto3.client('codebuild', region_name=region)
            try:
                # get values required for tagging from event details
                project_name = detail['responseElements']['project']['name']
                logger.info(f'Tagging new Codebuild project: {str(project_name)}')          
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(project_name)
                
                # create predefined tags
                tags_to_add = [
                            {'key': 'Name', 'value': project_name},
                            {'key': 'CreatedBy', 'value': user},
                            {'key': 'CreatedAt', 'value': event_time},
                            {'key': 'Env', 'value': env_tag},
                            {'key': 'Department', 'value': dep_tag}
                            ]
                
                # get project information
                describe_projects = codebuild_client.batch_get_projects(names=[project_name])
                for project in describe_projects['projects']:
                    # retrieve existing project tags
                    if 'tags' in project:
                        project_tags = project['tags']
                        # check if tags_to_add do not interfere with existing tags
                        for item in tags_to_add:
                            if item['key'] in [tag['key'] for tag in project_tags]:
                                tags_to_add = [tag for tag in tags_to_add if tag.get('key') != item['key']]
                                
                        # combine tags into one list
                        tags = project_tags + tags_to_add
                        
                        # apply tags using codebuild_client
                        codebuild_client.update_project(name=project_name, tags=tags)
                    
                    # if there are no existing tags, apply tags_to_add
                    elif 'tags' not in project:
                        # apply tags using codebuild_client
                        codebuild_client.update_project(name=project_name, tags=tags_to_add)
                        
                    else:
                        logger.error('Cannot evaluate tags status')
                        finishing_sequence(context, eventname, status='fail', error='Cannot evaluate tags status', exception=False)
                        return False  
                        
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # CodeDeploy events   
        # processing of CreateApplication event
        elif eventname == 'CreateApplication' and eventsource == 'codedeploy.amazonaws.com':
            # Create boto3 client/resource connection           
            codedeploy_client = boto3.client('codedeploy', region_name=region)
            try:
                # get values required for tagging from event details
                deploy_app_name = detail['requestParameters']['applicationName']
                # retrieve arn using aws arn convention
                deploy_app_arn = f'arn:aws:codedeploy:{region}:{aws_account_id}:application:{deploy_app_name}'
                logger.info(f'Tagging new CodeDeploy application: {str(deploy_app_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(deploy_app_name)
                
                # apply tags using codedeploy_client
                codedeploy_client.tag_resource(ResourceArn=deploy_app_arn,
                                                Tags=[
                                                    {'Key': 'Name', 'Value': deploy_app_name},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'CreatedAt', 'Value': event_time},
                                                    {'Key': 'Env', 'Value': env_tag},
                                                    {'Key': 'Department', 'Value': dep_tag}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateDeploymentGroup event
        elif eventname == 'CreateDeploymentGroup' and eventsource == 'codedeploy.amazonaws.com':
            # Create boto3 client/resource connection           
            codedeploy_client = boto3.client('codedeploy', region_name=region)
            try:
                # get values required for tagging from event details
                deploy_group_name = detail['requestParameters']['deploymentGroupName']
                deploy_app_name = detail['requestParameters']['applicationName']
                # retrieve arn using aws arn convention
                deploy_group_arn = f'arn:aws:codedeploy:{region}:{aws_account_id}:deploymentgroup:{deploy_app_name}/{deploy_group_name}'
                logger.info(f'Tagging new CodeDeploy deployment group: {str(deploy_group_name)} (connected to application {str(deploy_app_name)})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(deploy_group_name)
                
                # apply tags using codedeploy_client     
                codedeploy_client.tag_resource(ResourceArn=deploy_group_arn,
                                                Tags=[
                                                    {'Key': 'Name', 'Value': deploy_group_name},
                                                    {'Key': 'Application', 'Value': deploy_app_name},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'CreatedAt', 'Value': event_time},
                                                    {'Key': 'Env', 'Value': env_tag},
                                                    {'Key': 'Department', 'Value': dep_tag}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateDeploymentGroup event
        elif eventname == 'UpdateDeploymentGroup' and eventsource == 'codedeploy.amazonaws.com':
            # Create boto3 client/resource connection           
            codedeploy_client = boto3.client('codedeploy', region_name=region)
            try:
                # get values required for tagging from event details
                deploy_group_name = detail['requestParameters']['newDeploymentGroupName']
                deploy_app_name = detail['requestParameters']['applicationName']
                # retrieve arn using aws arn convention
                deploy_group_arn = f'arn:aws:codedeploy:{region}:{aws_account_id}:deploymentgroup:{deploy_app_name}/{deploy_group_name}'
                logger.info(f'Tagging new CodeDeploy deployment group: {str(deploy_group_name)} (connected to application {str(deploy_app_name)})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(deploy_group_name)
                
                # apply tags using codedeploy_client    
                codedeploy_client.tag_resource(ResourceArn=deploy_group_arn,
                                                Tags=[
                                                    {'Key': 'Name', 'Value': deploy_group_name},
                                                    {'Key': 'Application', 'Value': deploy_app_name},
                                                    {'Key': 'LastUpdatedBy', 'Value': user},
                                                    {'Key': 'LastUpdatedAt', 'Value': event_time},
                                                    {'Key': 'Env', 'Value': env_tag},
                                                    {'Key': 'Department', 'Value': dep_tag}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # API Gateway events
        # processing of CreateApi event
        elif eventname == 'CreateApi':
            # Create boto3 client/resource connection
            apigw_client = boto3.client('apigatewayv2', region_name=region)        
            try:
                # get values required for tagging from event details
                api_name = detail['responseElements']['name']
                api_id = detail['responseElements']['apiId']
                api_type = detail['responseElements']['protocolType']
                # retrieve arn using aws arn convention
                api_arn = f'arn:aws:apigateway:{region}::/apis/{api_id}'
                logger.info(f'Tagging new API: {str(api_name)} (type: {str(api_type)})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(api_name)
                
                # use lambda-python function to apply tags using apigw_client
                tagging = lambda key, value: apigw_client.tag_resource(ResourceArn=api_arn, Tags={key: value})
                
                tagging('Name', api_name)
                tagging('Protocol', api_type)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of ImportApi event
        elif eventname == 'ImportApi':
            # Create boto3 client/resource connection
            apigw_client = boto3.client('apigatewayv2', region_name=region)        
            try:
                # get values required for tagging from event details
                api_name = detail['responseElements']['name']
                api_id = detail['responseElements']['apiId']
                api_type = detail['responseElements']['protocolType']
                # retrieve arn using aws arn convention
                api_arn = f'arn:aws:apigateway:{region}::/apis/{api_id}'
                logger.info(f'Tagging new imported API: {str(api_name)} (type: {str(api_type)})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(api_name)
                
                # use lambda-python function to apply tags using apigw_client
                tagging = lambda key, value: apigw_client.tag_resource(ResourceArn=api_arn, Tags={key: value})
                
                tagging('Name', api_name)
                tagging('Protocol', api_type)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateApi event
        elif eventname == 'UpdateApi':
            # Create boto3 client/resource connection
            apigw_client = boto3.client('apigatewayv2', region_name=region)        
            try:
                # get values required for tagging from event details
                api_name = detail['responseElements']['name']
                api_id = detail['responseElements']['apiId']
                api_type = detail['responseElements']['protocolType']
                # retrieve arn using aws arn convention
                api_arn = f'arn:aws:apigateway:{region}::/apis/{api_id}'
                logger.info(f'Tagging updated API: {str(api_name)} (type: {str(api_type)})')
                
                # use lambda-python function to apply tags using apigw_client
                tagging = lambda key, value: apigw_client.tag_resource(ResourceArn=api_arn, Tags={key: value})
                
                tagging('LastUpdatedBy', user)
                tagging('LastUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateRestApi event
        elif eventname == 'CreateRestApi':
            # Create boto3 client/resource connection
            apigw_client = boto3.client('apigateway', region_name=region)        
            try:
                # get values required for tagging from event details
                api_name = detail['responseElements']['name']
                api_id = detail['responseElements']['id']
                api_type = "REST"
                # retrieve arn using aws arn convention
                api_arn = f'arn:aws:apigateway:{region}::/restapis/{api_id}'
                logger.info(f'Tagging new REST API: {str(api_name)} (type: {str(api_type)})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(api_name)
                
                # use lambda-python function to apply tags using apigw_client
                tagging = lambda key, value: apigw_client.tag_resource(resourceArn=api_arn, tags={key: value})
                
                tagging('Name', api_name)
                tagging('Protocol', api_type)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateRestApi event
        elif eventname == 'UpdateRestApi':
            # Create boto3 client/resource connection
            apigw_client = boto3.client('apigateway', region_name=region)        
            try:
                # get values required for tagging from event details
                api_name = detail['responseElements']['name']
                api_id = detail['responseElements']['id']
                api_type = "REST"
                # retrieve arn using aws arn convention
                api_arn = f'arn:aws:apigateway:{region}::/restapis/{api_id}'
                logger.info(f'Tagging updated REST API: {str(api_name)} (type: {str(api_type)})')
                
                # use lambda-python function to apply tags using apigw_client
                tagging = lambda key, value: apigw_client.tag_resource(resourceArn=api_arn, tags={key: value})
                
                tagging('LastUpdatedBy', user)
                tagging('LastUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateStage event
        elif eventname == 'CreateStage':    
            try:
                # check if stage is related to REST API or not
                if 'restApiId' in detail['requestParameters']:
                    # Create boto3 client/resource connection
                    apigw_client = boto3.client('apigateway', region_name=region)
                    
                    # get values required for tagging from event details
                    api_stage_name = detail['responseElements']['stageName'] 
                    api_id = detail['requestParameters']['restApiId']
                    # retrieve arn using aws arn convention
                    api_stage_arn = f'arn:aws:apigateway:{region}::/restapis/{api_id}/stages/{api_stage_name}'
                    logger.info(f'Tagging new REST API stage: {str(api_stage_name)} (API ID: {str(api_id)})')
                    
                    # use lambda-python function to apply tags using apigw_client
                    tagging = lambda key, value: apigw_client.tag_resource(resourceArn=api_stage_arn, tags={key: value})
                    
                elif 'restApiId' not in detail['requestParameters']:
                    # Create boto3 client/resource connection
                    apigw_client = boto3.client('apigatewayv2', region_name=region)
                    
                    # get values required for tagging from event details
                    api_stage_name = detail['responseElements']['stageName']
                    api_id = detail['requestParameters']['apiId']
                    # retrieve arn using aws arn convention
                    api_stage_arn = f'arn:aws:apigateway:{region}::/apis/{api_id}/stages/{api_stage_name}'
                    logger.info(f'Tagging new HTTP API stage: {str(api_stage_name)} (API ID: {str(api_id)})')
                    
                    # use lambda-python function to apply tags using apigw_client
                    tagging = lambda key, value: apigw_client.tag_resource(ResourceArn=api_stage_arn, Tags={key: value})
                
                else:
                    logger.error('Cannot determine API type')
                    finishing_sequence(context, eventname, status='fail', error='Cannot determine API type', exception=False)
                    return False
                
                if tagging:
                    # remove $ sign from 'default' stage
                    if re.search('\$', api_stage_name): api_stage_name = "default"             
                    tagging('Name', api_stage_name)
                    tagging('API Id', api_id)
                    tagging('CreatedBy', user)
                    tagging('CreatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateStage event
        elif eventname == 'UpdateStage':
            try:
                # check if Stage is related to REST API or not
                if 'restApiId' in detail['requestParameters']:
                    # Create boto3 client/resource connection
                    apigw_client = boto3.client('apigateway', region_name=region)
                    
                    # get values required for tagging from event details
                    api_stage_name = detail['responseElements']['stageName']
                    api_id = detail['requestParameters']['restApiId']
                    # retrieve arn using aws arn convention
                    api_stage_arn = f'arn:aws:apigateway:{region}::/restapis/{api_id}/stages/{api_stage_name}'
                    logger.info(f'Tagging updated REST API stage: {str(api_stage_name)} (API ID: {str(api_id)})')
                    
                    # use lambda-python function to apply tags using apigw_client
                    tagging = lambda key, value: apigw_client.tag_resource(resourceArn=api_stage_arn, tags={key: value})
                    
                elif 'restApiId' not in detail['requestParameters']:
                    # Create boto3 client/resource connection
                    apigw_client = boto3.client('apigatewayv2',region_name=region)    
                    
                    # get values required for tagging from event details
                    api_stage_name = detail['responseElements']['stageName']
                    api_id = detail['requestParameters']['apiId']
                    # retrieve arn using aws arn convention
                    api_stage_arn = f'arn:aws:apigateway:{region}::/apis/{api_id}/stages/{api_stage_name}'
                    logger.info(f'Tagging updated HTTP API stage: {str(api_stage_name)} (API ID: {str(api_id)})')
                
                    # use lambda-python function to apply tags using apigw_client
                    tagging = lambda key, value: apigw_client.tag_resource(ResourceArn=api_stage_arn, Tags={key: value})
                
                if tagging:
                    tagging('LastUpdatedBy', user)
                    tagging('LastUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateApiKey event
        elif eventname == 'CreateApiKey':
            # Create boto3 client/resource connection
            apigw_client = boto3.client('apigateway', region_name=region)        
            try:
                # get values required for tagging from event details
                api_key_name = detail['responseElements']['name']
                api_key_id = detail['responseElements']['id']
                # retrieve arn using aws arn convention
                api_key_arn = f'arn:aws:apigateway:{region}::/apikeys/{api_key_id}'
                logger.info(f'Tagging new API key: {str(api_key_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(api_key_name)
                
                # use lambda-python function to apply tags using apigw_client
                tagging = lambda key, value: apigw_client.tag_resource(resourceArn=api_key_arn, tags={key: value})
                
                tagging('Name', api_key_name)
                tagging('Id', api_key_id)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateApiKey event
        elif eventname == 'UpdateApiKey':
            # Create boto3 client/resource connection
            apigw_client = boto3.client('apigatewayv2', region_name=region)        
            try:
                # get values required for tagging from event details
                api_key_name = detail['responseElements']['name']
                api_key_id = detail['responseElements']['id']
                # retrieve arn using aws arn convention
                api_key_arn = f'arn:aws:apigateway:{region}::/apikeys/{api_key_id}'
                logger.info(f'Tagging updated API key: {str(api_key_name)}')
                
                # use lambda-python function to apply tags using apigw_client
                tagging = lambda key, value: apigw_client.tag_resource(resourceArn=api_key_arn, tags={key: value})

                tagging('LastUpdatedBy', user)
                tagging('LastUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateDomainName event
        elif eventname == 'CreateDomainName':
            # Create boto3 client/resource connection
            apigw_client = boto3.client('apigatewayv2', region_name=region)        
            try:
                # get values required for tagging from event details
                domain_name = detail['responseElements']['domainName']
                # retrieve arn using aws arn convention
                domain_name_arn = f'arn:aws:apigateway:{region}::/domainnames/{domain_name}'
                logger.info(f'Tagging new API custom domain name: {str(domain_name)}')
                
                # use lambda-python function to apply tags using apigw_client
                tagging = lambda key, value: apigw_client.tag_resource(ResourceArn=domain_name_arn, Tags={key: value})
                
                tagging('Name', domain_name)
                tagging('Env', 'ops')
                tagging('Department', 'Operations')
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateDomainName event
        elif eventname == 'UpdateDomainName':
            # Create boto3 client/resource connection
            apigw_client = boto3.client('apigatewayv2', region_name=region)        
            try:
                # get values required for tagging from event details
                domain_name = detail['responseElements']['domainName']
                # retrieve arn using aws arn convention
                domain_name_arn = f'arn:aws:apigateway:{region}::/domainnames/{domain_name}'
                logger.info(f'Tagging updated API custom domain name: {str(domain_name)}')
                
                # use lambda-python function to apply tags using apigw_client
                tagging = lambda key, value: apigw_client.tag_resource(ResourceArn=domain_name_arn, Tags={key: value})
                
                tagging('LastUpdatedBy', user)
                tagging('LastUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateVpcLink event
        elif eventname == 'CreateVpcLink':
            # Create boto3 client/resource connection
            apigw_client = boto3.client('apigatewayv2', region_name=region)        
            try:
                # get values required for tagging from event details
                vpc_link_name = detail['responseElements']['name']
                vpc_link_id = detail['responseElements']['id']
                # retrieve arn using aws arn convention
                vpc_link_arn = f'arn:aws:apigateway:{region}::/vpclinks/{vpc_link_id}'
                logger.info(f'Tagging new API VPC link: {str(vpc_link_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(vpc_link_name)
                
                # use lambda-python function to apply tags using apigw_client
                tagging = lambda key, value: apigw_client.tag_resource(ResourceArn=vpc_link_arn, Tags={key: value})
                
                tagging('Name', vpc_link_name)
                tagging('Id', vpc_link_id)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateVpcLink event
        elif eventname == 'UpdateVpcLink':
            # Create boto3 client/resource connection
            apigw_client = boto3.client('apigatewayv2', region_name=region)        
            try:
                # get values required for tagging from event details
                vpc_link_name = detail['responseElements']['name']
                vpc_link_id = detail['responseElements']['id']
                # retrieve arn using aws arn convention
                vpc_link_arn = f'arn:aws:apigateway:{region}::/vpclinks/{vpc_link_id}'
                logger.info(f'Tagging updated API VPC link: {str(vpc_link_name)}')
                
                # use lambda-python function to apply tags using apigw_client
                tagging = lambda key, value: apigw_client.tag_resource(ResourceArn=vpc_link_arn, Tags={key: value})
                
                tagging('LastUpdatedBy', user)
                tagging('LastUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateUsagePlan event
        elif eventname == 'CreateUsagePlan':
            # Create boto3 client/resource connection
            apigw_client = boto3.client('apigateway', region_name=region)        
            try:
                # get values required for tagging from event details
                usage_plan_name = detail['responseElements']['name']
                usage_plan_id = detail['responseElements']['id']
                # retrieve arn using aws arn convention
                usage_plan_arn = f'arn:aws:apigateway:{region}::/usageplans/{usage_plan_id}'
                logger.info(f'Tagging new API usage plan: {str(usage_plan_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(usage_plan_name)
                
                # use lambda-python function to apply tags using apigw_client
                tagging = lambda key, value: apigw_client.tag_resource(resourceArn=usage_plan_arn, tags={key: value})
                
                tagging('Name', usage_plan_name)
                tagging('Id', usage_plan_id)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateUsagePlan event
        elif eventname == 'UpdateUsagePlan':
            # Create boto3 client/resource connection
            apigw_client = boto3.client('apigateway', region_name=region)        
            try:
                # get values required for tagging from event details
                usage_plan_name = detail['responseElements']['name']
                usage_plan_id = detail['responseElements']['id']
                # retrieve arn using aws arn convention
                usage_plan_arn = f'arn:aws:apigateway:{region}::/usageplans/{usage_plan_id}'
                logger.info(f'Tagging updated API usage plan: {str(usage_plan_name)}')
                
                # use lambda-python function to apply tags using apigw_client
                tagging = lambda key, value: apigw_client.tag_resource(resourceArn=usage_plan_arn, tags={key: value})
                
                tagging('LastUpdatedBy', user)
                tagging('LastUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of GenerateClientCertificate event
        elif eventname == 'GenerateClientCertificate':
            # Create boto3 client/resource connection
            apigw_client = boto3.client('apigateway', region_name=region)        
            try:
                # get values required for tagging from event details
                cert_id = detail['responseElements']['self']['clientCertificateId']
                # retrieve arn using aws arn convention
                cert_arn = f'arn:aws:apigateway:{region}::/clientcertificates/{cert_id}'
                logger.info(f'Tagging new generated API client certificate: {str(cert_id)}')
                
                # use lambda-python function to apply tags using apigw_client
                tagging = lambda key, value: apigw_client.tag_resource(resourceArn=cert_arn, tags={key: value})
                
                tagging('Id', cert_id)
                tagging('Env', 'ops')
                tagging('Department', 'Operations')
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateClientCertificate event
        elif eventname == 'UpdateClientCertificate':
            # Create boto3 client/resource connection
            apigw_client = boto3.client('apigateway', region_name=region)        
            try:
                # get values required for tagging from event details
                cert_id = detail['responseElements']['self']['clientCertificateId']
                # retrieve arn using aws arn convention
                cert_arn = f'arn:aws:apigateway:{region}::/clientcertificates/{cert_id}'
                logger.info(f'Tagging updated API client certificate: {str(cert_id)}')
                
                # use lambda-python function to apply tags using apigw_client
                tagging = lambda key, value: apigw_client.tag_resource(resourceArn=cert_arn, tags={key: value})
                
                tagging('LastUpdatedBy', user)
                tagging('LastUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
        
        # SSM events
        # processing of PutParameter event
        elif eventname == 'PutParameter':
            # Create boto3 client/resource connection
            ssm_client = boto3.client('ssm', region_name=region)
            try:
                # get values required for tagging from event details
                param_name = detail['requestParameters']['name']
                logger.info(f'Tagging SSM Parameter: {str(param_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(param_name)
                
                # apply tags using ssm_client
                ssm_client.add_tags_to_resource(ResourceType='Parameter',
                                                ResourceId=param_name,
                                                Tags=[
                                                    {'Key': 'Name', 'Value': param_name},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'Env', 'Value': env_tag},
                                                    {'Key': 'Department', 'Value': dep_tag}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateDocument event
        elif eventname == 'CreateDocument':
            # Create boto3 client/resource connection
            ssm_client = boto3.client('ssm', region_name=region)
            try:
                # get values required for tagging from event details
                document_name = detail['requestParameters']['name']
                logger.info(f'Tagging SSM Document: {str(document_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(document_name)
                
                # apply tags using ssm_client
                ssm_client.add_tags_to_resource(ResourceType='Document',
                                                ResourceId=document_name,
                                                Tags=[
                                                    {'Key': 'Name', 'Value': document_name},
                                                    {'Key': 'CreatedBy', 'Value': user},
                                                    {'Key': 'Env', 'Value': env_tag},
                                                    {'Key': 'Department', 'Value': dep_tag}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateDocument event
        elif eventname == 'UpdateDocument':
            # Create boto3 client/resource connection
            ssm_client = boto3.client('ssm', region_name=region)
            try:
                # get values required for tagging from event details
                document_name = detail['requestParameters']['name']
                logger.info(f'Tagging updated SSM Document: {str(document_name)}')
                
                # apply tags using ssm_client
                ssm_client.add_tags_to_resource(ResourceType='Document',
                                                ResourceId=document_name,
                                                Tags=[
                                                    {'Key': 'LastUpdatedBy', 'Value': user},
                                                    {'Key': 'LastUpdatedAt', 'Value': event_time}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateDocumentDefaultVersion event
        elif eventname == 'UpdateDocumentDefaultVersion':
            # Create boto3 client/resource connection
            ssm_client = boto3.client('ssm', region_name=region)
            try:
                # get values required for tagging from event details
                document_name = detail['requestParameters']['name']
                logger.info(f'Tagging updated default version of SSM Document: {str(document_name)}')
                
                # apply tags using ssm_client
                ssm_client.add_tags_to_resource(ResourceType='Document',
                                                ResourceId=document_name,
                                                Tags=[
                                                    {'Key': 'DefaultVersionUpdatedBy', 'Value': user},
                                                    {'Key': 'DefaultVersionUpdatedAt', 'Value': event_time}
                                                    ]
                                                )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # Redshift events
        # processing of CreateCluster event
        elif eventname == 'CreateCluster' and eventsource == 'redshift.amazonaws.com':
            # Create boto3 client/resource connection
            redshift_client = boto3.client('redshift', region_name=region)
            try:
                # get values required for tagging from event details
                cluster_identifier = detail['responseElements']['clusterIdentifier']
                # get details on clusters
                describe_clusters = redshift_client.describe_clusters(ClusterIdentifier=cluster_identifier)
                for cluster in describe_clusters['Clusters']:
                    # get cluster arn
                    cluster_arn = cluster['ClusterNamespaceArn']
                    logger.info(f'Tagging Redshift Cluster: {str(cluster_arn)} ({str(cluster_identifier)})')
                
                    # initiliaze TagEvaluator to determine Env and Department tags
                    tagevaluator = TagEvaluator()
                    env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(cluster_identifier)
                    
                    # apply tags using redshift_client
                    redshift_client.create_tags(ResourceName=cluster_arn,
                                                    Tags=[
                                                        {'Key': 'Name', 'Value': cluster_identifier},
                                                        {'Key': 'CreatedBy', 'Value': user},
                                                        {'Key': 'Env', 'Value': env_tag},
                                                        {'Key': 'Department', 'Value': dep_tag}
                                                        ]
                                                    )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # Elasticache events
        # processing of CreateCacheCluster event
        elif eventname == 'CreateCacheCluster' and eventsource == 'elasticache.amazonaws.com':
            # Create boto3 client/resource connection
            elasticache_client = boto3.client('elasticache', region_name=region)
            try:
                # get values required for tagging from event details
                cache_cluster_id  = detail['responseElements']['cacheClusterId']
                cluster_engine = detail['responseElements']['engine']
                # get details on clusters
                describe_cache_clusters = elasticache_client.describe_cache_clusters(CacheClusterId=cache_cluster_id)
                for cache_cluster in describe_cache_clusters['CacheClusters']:
                     # get cluster arn
                    cache_cluster_arn = cache_cluster['ARN']
                    logger.info(f'Tagging Elasticache cluster ({str(cluster_engine)}): {str(cache_cluster_id)} ({str(cache_cluster_arn)})')
                
                    # initiliaze TagEvaluator to determine Env and Department tags
                    tagevaluator = TagEvaluator()
                    env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(cache_cluster_id)
                    
                    # apply tags using elasticache_client
                    elasticache_client.add_tags_to_resource(ResourceName=cache_cluster_id,
                                                    Tags=[
                                                        {'Key': 'Name', 'Value': cache_cluster_id},
                                                        {'Key': 'CreatedBy', 'Value': user},
                                                        {'Key': 'Env', 'Value': env_tag},
                                                        {'Key': 'Department', 'Value': dep_tag}
                                                        ]
                                                    )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # S3 events
        # processing of CreateBucket event
        elif eventname == 'CreateBucket':
            # Create boto3 client/resource connection
            s3_client = boto3.client('s3', region_name=region)
            try:
                # get values required for tagging from event details
                bucket_name = detail['requestParameters']['bucketName']
                logger.info(f'Tagging new S3 bucket: {str(bucket_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(bucket_name)
                
                # apply tags using s3_client
                s3_client.put_bucket_tagging(Bucket=bucket_name,
                                             Tagging={'TagSet':
                                                        [
                                                        {'Key': 'Name', 'Value': bucket_name},
                                                        {'Key': 'CreatedBy', 'Value': user},
                                                        {'Key': 'CreatedAt', 'Value': event_time},
                                                        {'Key': 'Env', 'Value': env_tag},
                                                        {'Key': 'Department', 'Value': dep_tag}
                                                        ]
                                                    }
                                             )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # Glacier events
        # processing of CreateVault event
        elif eventname == 'CreateVault':
            # Create boto3 client/resource connection
            glacier_client = boto3.client('glacier', region_name=region)
            try:
                # get values required for tagging from event details
                vault_name = detail['requestParameters']['vaultName']
                logger.info(f'Tagging new Glacier vault: {str(vault_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(vault_name)
                
                # use lambda-python function to apply tags using glacier_client
                tagging = lambda key, value: glacier_client.add_tags_to_vault(vaultName=vault_name, Tags={key: value})
                
                tagging('Name', vault_name)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # Organizations events
        # processing of CreateAccount event
        elif eventname == 'CreateAccount':
            # Create boto3 client/resource connection
            organizations_client = boto3.client('organizations', region_name=region)
            try:
                # get values required for tagging from event details
                create_account_request_id = detail['responseElements']['createAccountStatus']['id']
                # get account id using describe_create_account_status boto3 method
                account_id = organizations_client.describe_create_account_status(CreateAccountRequestId=create_account_request_id)['CreateAccountStatus']['AccountId']
                # get account id using describe_account boto3 method
                account_name = organizations_client.describe_account(AccountId=account_id)['Account']['Name']
                logger.info(f'Tagging new Organizations account: {str(account_name)} (account id: {str(account_id)})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(account_name)
                
                # apply tags using organizations_client
                organizations_client.tag_resource(ResourceId=account_id, 
                                        Tags=[
                                            {'Key': 'Name', 'Value': account_name},
                                            {'Key': 'CreatedBy', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time},
                                            {'Key': 'Env', 'Value': env_tag},
                                            {'Key': 'Department', 'Value': dep_tag}
                                            ])
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # ServiceCatalog events
        # processing of CreatePortfolio event
        elif eventname == 'CreatePortfolio':
            # Create boto3 client/resource connection
            servicecatalog_client = boto3.client('servicecatalog', region_name=region)
            try:
                # get values required for tagging from event details
                portfolio_id = detail['responseElements']['portfolioDetail']['id']
                portfolio_name = detail['responseElements']['portfolioDetail']['displayName']
                logger.info(f'Tagging new servicecatalog portfolio: {str(portfolio_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(portfolio_name)
                
                # apply tags using servicecatalog_client
                servicecatalog_client.update_portfolio(
                                                        Id=portfolio_id,
                                                        DisplayName=portfolio_name,
                                                        AddTags=
                                                            [
                                                            {'Key': 'Name', 'Value': portfolio_name},
                                                            {'Key': 'CreatedBy', 'Value': user},
                                                            {'Key': 'CreatedAt', 'Value': event_time},
                                                            {'Key': 'Env', 'Value': env_tag},
                                                            {'Key': 'Department', 'Value': dep_tag}
                                                            ]
                                                        )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateProduct event
        elif eventname == 'CreateProduct':
            # Create boto3 client/resource connection
            servicecatalog_client = boto3.client('servicecatalog', region_name=region)
            try:
                # get values required for tagging from event details
                product_id = detail['responseElements']['productViewDetail']['productViewSummary']['productId']
                product_name = detail['responseElements']['productViewDetail']['productViewSummary']['name']
                logger.info(f'Tagging new servicecatalog product: {str(product_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(product_name)
                
                # apply tags using servicecatalog_client
                servicecatalog_client.update_product(
                                                    Id=product_id,
                                                    Name=product_name,
                                                    AddTags=
                                                            [
                                                            {'Key': 'Name', 'Value': product_name},
                                                            {'Key': 'CreatedBy', 'Value': user},
                                                            {'Key': 'CreatedAt', 'Value': event_time},
                                                            {'Key': 'Env', 'Value': env_tag},
                                                            {'Key': 'Department', 'Value': dep_tag}
                                                            ]
                                                    )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdatePortfolio event
        elif eventname == 'UpdatePortfolio':
            # Create boto3 client/resource connection
            servicecatalog_client = boto3.client('servicecatalog', region_name=region)
            try:
                # get values required for tagging from event details
                portfolio_id = detail['responseElements']['portfolioDetail']['id']
                portfolio_name = detail['responseElements']['portfolioDetail']['displayName']
                logger.info(f'Tagging updated servicecatalog portfolio: {str(portfolio_name)}')
                
                # apply tags using servicecatalog_client
                servicecatalog_client.update_portfolio(
                                                        Id=portfolio_id,
                                                        DisplayName=portfolio_name,
                                                        AddTags=
                                                            [
                                                            {'Key': 'Name', 'Value': portfolio_name},
                                                            {'Key': 'LastUpdatedBy', 'Value': user},
                                                            {'Key': 'LastUpdatedAt', 'Value': event_time}
                                                            ]
                                                        )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateProduct event
        elif eventname == 'UpdateProduct':
            # Create boto3 client/resource connection
            servicecatalog_client = boto3.client('servicecatalog', region_name=region)
            try:
                # get values required for tagging from event details
                product_id = detail['responseElements']['productViewDetail']['productViewSummary']['productId']
                product_name = detail['responseElements']['productViewDetail']['productViewSummary']['name']
                logger.info(f'Tagging updated servicecatalog product: {str(product_name)}')
                
                # apply tags using servicecatalog_client
                servicecatalog_client.update_product(
                                                        Id=product_id,
                                                        Name=product_name,
                                                        AddTags=
                                                            [
                                                            {'Key': 'Name', 'Value': product_name},
                                                            {'Key': 'LastUpdatedBy', 'Value': user},
                                                            {'Key': 'LastUpdatedAt', 'Value': event_time}
                                                            ]
                                                    )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # DynamoDB events
        # processing of CreateTable event
        elif eventname == 'CreateTable':
            # Create boto3 client/resource connection
            dynamodb_client = boto3.client('dynamodb', region_name=region)
            try:
                # get values required for tagging from event details
                table_arn = detail['responseElements']['tableDescription']['tableArn']
                table_name = detail['responseElements']['tableDescription']['tableName']
                logger.info(f'Tagging new DynamoDB table: {str(table_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(table_name)
                
                # apply tags using dynamodb_client
                dynamodb_client.tag_resource(ResourceArn=table_arn, 
                                        Tags=[
                                            {'Key': 'Name', 'Value': table_name},
                                            {'Key': 'CreatedBy', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time},
                                            {'Key': 'Env', 'Value': env_tag},
                                            {'Key': 'Department', 'Value': dep_tag}
                                            ])
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateGlobalTable event
        elif eventname == 'CreateGlobalTable':
            # Create boto3 client/resource connection
            dynamodb_client = boto3.client('dynamodb', region_name=region)
            try:
                # get values required for tagging from event details
                global_table_arn = detail['responseElements']['globalTableDescription']['globalTableArn']
                global_table_name = detail['responseElements']['globalTableDescription']['globalTableName']
                logger.info(f'Tagging new global DynamoDB table: {str(global_table_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(global_table_name)
                
                # apply tags using dynamodb_client
                dynamodb_client.tag_resource(ResourceArn=global_table_arn, 
                                        Tags=[
                                            {'Key': 'Name', 'Value': global_table_name},
                                            {'Key': 'CreatedBy', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time},
                                            {'Key': 'Env', 'Value': env_tag},
                                            {'Key': 'Department', 'Value': dep_tag}
                                            ])
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateTable event
        elif eventname == 'UpdateTable':
            # Create boto3 client/resource connection
            dynamodb_client = boto3.client('dynamodb', region_name=region)
            try:
                # get values required for tagging from event details
                table_arn = detail['responseElements']['tableDescription']['tableArn']
                table_name = detail['responseElements']['tableDescription']['tableName']
                logger.info(f'Tagging updated DynamoDB table: {str(table_name)}')
                
                # apply tags using dynamodb_client
                dynamodb_client.tag_resource(ResourceArn=table_arn, 
                                        Tags=[
                                            {'Key': 'LastUpdatedBy', 'Value': user},
                                            {'Key': 'LastUpdatedAt', 'Value': event_time}
                                            ])
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateGlobalTable event
        elif eventname == 'UpdateGlobalTable':
            # Create boto3 client/resource connection
            dynamodb_client = boto3.client('dynamodb', region_name=region)
            try:
                # get values required for tagging from event details
                global_table_arn = detail['responseElements']['globalTableDescription']['globalTableArn']
                global_table_name = detail['responseElements']['globalTableDescription']['globalTableName']
                logger.info(f'Tagging updated global DynamoDB table: {str(global_table_name)}')
                
                # apply tags using dynamodb_client
                dynamodb_client.tag_resource(ResourceArn=global_table_arn, 
                                        Tags=[
                                            {'Key': 'LastUpdatedBy', 'Value': user},
                                            {'Key': 'LastUpdatedAt', 'Value': event_time}
                                            ])
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # ELB/ALB events    
        # processing of CreateLoadBalancer event
        elif eventname == 'CreateLoadBalancer':
            try:
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                if 'type' in detail['requestParameters']:
                    # Create boto3 client/resource connection
                    elb_client = boto3.client('elbv2', region_name=region)
                    # get values required for tagging from event details
                    lb_type = detail['requestParameters']['type']
                    lb_name = detail['responseElements']['loadBalancers'][0]['loadBalancerName']
                    lb_arn = detail['responseElements']['loadBalancers'][0]['loadBalancerArn']
                    logger.info(f'Tagging LB of {str(lb_type)}: {str(lb_name)}')                    
                    
                    # determine Env and Department tags
                    env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(lb_name)
                    
                    # apply tags using elb_client
                    elb_client.add_tags(ResourceArns=[lb_arn], 
                                        Tags=[
                                            {'Key': 'CreatedBy', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time},
                                            {'Key': 'Name', 'Value': lb_name},
                                            {'Key': 'Env', 'Value': env_tag}, 
                                            {'Key': 'Department', 'Value': dep_tag}
                                            ])
                    
                else:           
                    # Create boto3 client/resource connection
                    elb_client = boto3.client('elb', region_name=region)
                    # get values required for tagging from event details
                    lb_name = detail['requestParameters']['loadBalancerName']
                    logger.info(f'Tagging LB of Classic type: {str(lb_name)}')
                    # apply tags using elb_client 
                    elb_client.add_tags(LoadBalancerNames=[lb_name], 
                                        Tags=[
                                            {'Key': 'CreatedBy', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time}
                                            ]
                                        )
                    
                    # check if there are existing tags
                    if 'tags' in detail['requestParameters']:
                        tags = detail['requestParameters']['tags']
                        # if Name tag is not present, create it
                        if 'Name' not in [tag['key'] for tag in tags]:
                            logger.info(f'Name tag: {str(lb_name)}')
                            # apply tags using elb_client
                            elb_client.add_tags(LoadBalancerNames=[lb_name], Tags=[{'Key': 'Name', 'Value': lb_name}])
                        # if Env tag is not present, create it along with Department tag
                        if 'Env' not in [tag['key'] for tag in tags]:
                            # determine Env and Department tags
                            env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(lb_name)
                            # apply tags using elb_client
                            elb_client.add_tags(LoadBalancerNames=[lb_name], 
                                                Tags=[
                                                        {'Key': 'Env', 'Value': env_tag},
                                                        {'Key': 'Department', 'Value': dep_tag}
                                                     ]
                                                )
                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # processing of CreateTargetGroup event
        elif eventname == 'CreateTargetGroup' and eventsource == 'elasticloadbalancing.amazonaws.com':
            # Create boto3 client/resource connection
            elb_client = boto3.client('elbv2', region_name=region)
            try:
                # get values required for tagging from event details
                for tg in detail['responseElements']['targetGroups']:
                    tg_name = tg['targetGroupName']
                    tg_arn = tg['targetGroupArn']
                    logger.info(f'Tagging Target Group: {str(tg_name)}')
                    
                    # get details on target group using boto3 describe_target_groups method
                    describe_tg = elb_client.describe_target_groups(TargetGroupArns=[tg_arn])
                    for tg in describe_tg['TargetGroups']:
                        # check if target group is attached to LB
                        if tg['LoadBalancerArns']:
                            # get arn of LB
                            lb_arn = tg['LoadBalancerArns']
                            logger.info(f'Found LB behind Target Group: {str(lb_arn)}')
                            # get tags of LB
                            describe_tags = elb_client.describe_tags(ResourceArns=lb_arn)
                            tags = describe_tags['TagDescriptions'][0]['Tags']
                            # create a list of tags for target group using LB tags
                            newtags = []
                            tags_list = ['Env', 'Department', 'Customers', 'Cluster', 'Id', 'tenant', 'stage', 'Project', 'Class', 'Role', 'application']
                            for tag in tags:
                                for item in tags_list:
                                    if tag['Key'] == item:
                                        newtags.append(tag)
                                        
                            logger.info(f'tags: {json.dumps(newtags, indent=1, sort_keys=True, default=str)}')
                            
                            # apply tags using elb_client
                            elb_client.add_tags(ResourceArns=[tg_arn], 
                                Tags=[
                                    {'Key': 'CreatedBy', 'Value': user},
                                    {'Key': 'Name', 'Value': tg_name}
                                    ])
                            elb_client.add_tags(ResourceArns=[tg_arn], Tags=newtags)

                        # if target group is not attached to LB, apply predefined tags
                        if not tg['LoadBalancerArns']:
                            logger.info('LB not found')
                            
                            # initiliaze TagEvaluator to determine Env and Department tags
                            tagevaluator = TagEvaluator()
                            env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(tg_name)
                            
                            # apply tags using elb_client
                            elb_client.add_tags(ResourceArns=[tg_arn], 
                                Tags=[
                                    {'Key': 'CreatedBy', 'Value': user},
                                    {'Key': 'Name', 'Value': tg_name},
                                    {'Key': 'Env', 'Value': env_tag}, 
                                    {'Key': 'Department', 'Value': dep_tag}
                                    ])
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # ASG events
        # processing of CreateAutoScalingGroup event
        elif eventname == 'CreateAutoScalingGroup':
            # Create boto3 client/resource connection
            asg_client = boto3.client('autoscaling', region_name=region)
            try:
                # get values required for tagging from event details
                asg_name = detail['requestParameters']['autoScalingGroupName']
                logger.info(f'Tagging ASG: {str(asg_name)}')
                # create owner tags
                owner_tags = [
                    {
                    'Key': 'CreatedBy',
                    'PropagateAtLaunch': True,
                    'ResourceId': asg_name,
                    'ResourceType': 'auto-scaling-group',
                    'Value': user,
                    },
                    {
                    'Key': 'CreatedAt',
                    'PropagateAtLaunch': True,
                    'ResourceId': asg_name,
                    'ResourceType': 'auto-scaling-group',
                    'Value': event_time,
                    }
                    ]
                # apply tags using asg_client
                asg_client.create_or_update_tags(Tags=owner_tags)
                
                # check if there are any existing tags in ASG
                if 'tags' in detail['requestParameters']:
                    # get tags
                    asg_tags = detail['requestParameters']['tags']
                    # apply tag for elasticbeanstalk ASG
                    if 'elasticbeanstalk:environment-name' in [tag['key'] for tag in asg_tags]:
                        logger.info(f'Tagging Beanstalk ASG: {str(asg_name)}')
                        logger.info('Department tag: Beanstalk')
                        # create Department tag
                        department_tag = [{
                                'Key': 'Department',
                                'PropagateAtLaunch': True,
                                'ResourceId': asg_name,
                                'ResourceType': 'auto-scaling-group',
                                'Value': 'Beanstalk',
                                }]
                        # apply tags using asg_client
                        asg_client.create_or_update_tags(Tags=department_tag)
                    
                    # apply tags for EKS ASG
                    elif 'eks:cluster-name' in [tag['key'] for tag in asg_tags]:
                        eks_cluster_name = [tag['value'] for tag in asg_tags if tag['key'] == "eks:cluster-name"][0]
                        logger.info(f'Tagging EKS ASG: {str(asg_name)}')
                        
                        # initiliaze TagEvaluator to determine Env and Department tags
                        tagevaluator = TagEvaluator()
                        env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(eks_cluster_name)
                        
                        # create Env/Dep tags
                        env_dep_tags = [
                            {
                                'Key': 'Env',
                                'PropagateAtLaunch': True,
                                'ResourceId': asg_name,
                                'ResourceType': 'auto-scaling-group',
                                'Value': env_tag,
                            },
                            {
                                'Key': 'Department',
                                'PropagateAtLaunch': True,
                                'ResourceId': asg_name,
                                'ResourceType': 'auto-scaling-group',
                                'Value': dep_tag,
                            }
                               ]
                        asg_client.create_or_update_tags(Tags=env_dep_tags)
                    
                    # apply tags for standard (EC2) ASG
                    elif 'eks:cluster-name' not in [tag['key'] for tag in asg_tags] and 'elasticbeanstalk:environment-name' not in [tag['key'] for tag in asg_tags]:
                        logger.info(f'Tagging standard ASG: {str(asg_name)}')
                        
                        # initiliaze TagEvaluator to determine Env and Department tags
                        tagevaluator = TagEvaluator()
                        env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(asg_name)
                        
                        # create Env/Dep tags
                        env_dep_tags = [
                            {
                                'Key': 'Env',
                                'PropagateAtLaunch': True,
                                'ResourceId': asg_name,
                                'ResourceType': 'auto-scaling-group',
                                'Value': env_tag,
                            },
                            {
                                'Key': 'Department',
                                'PropagateAtLaunch': True,
                                'ResourceId': asg_name,
                                'ResourceType': 'auto-scaling-group',
                                'Value': dep_tag,
                            }
                               ]
                        # apply tags using asg_client
                        asg_client.create_or_update_tags(Tags=env_dep_tags)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # EMR events
        # processing of RunJobFlow event
        elif eventname == 'RunJobFlow':
            # Create boto3 client/resource connection
            emr_client = boto3.client('emr', region_name=region)
            try:
                # get values required for tagging from event details
                emr_job_id = detail['responseElements']['jobFlowId']
                emr_name = detail['requestParameters']['name']
                logger.info(f'Tagging EMR job: {str(emr_job_id)} ({str(emr_name)})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(emr_name)
                
                # apply tags using emr_client
                emr_client.add_tags(ResourceId=emr_job_id, 
                                    Tags=[
                                        {'Key': 'CreatedBy', 'Value': user},
                                        {'Key': 'Env', 'Value': env_tag},
                                        {'Key': 'Department', 'Value': dep_tag}
                                        ])
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # IAM events
        # processing of CreateUser event
        elif eventname == 'CreateUser':
            # Create boto3 client/resource connection
            iam_client = boto3.client('iam', region_name=region)
            try:
                # get values required for tagging from event details
                iam_user_name = detail['requestParameters']['userName']
                logger.info(f'Tagging new IAM user: {str(iam_user_name)}')
                
                # apply tags using iam_client
                iam_client.tag_user(UserName=iam_user_name, 
                                    Tags=[
                                        {'Key': 'Name', 'Value': iam_user_name},
                                        {'Key': 'CreatedBy', 'Value': user},
                                        {'Key': 'CreatedAt', 'Value': event_time}
                                        ]
                                    )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateRole event
        elif eventname == 'CreateRole':
            # Create boto3 client/resource connection
            iam_client = boto3.client('iam', region_name=region)
            try:
                # get values required for tagging from event details
                iam_role_name = detail['requestParameters']['roleName']
                logger.info(f'Tagging new IAM role: {str(iam_role_name)}')
                
                # apply tags using iam_client
                iam_client.tag_role(RoleName=iam_role_name, 
                                    Tags=[
                                        {'Key': 'Name', 'Value': iam_role_name},
                                        {'Key': 'CreatedBy', 'Value': user},
                                        {'Key': 'CreatedAt', 'Value': event_time}
                                        ]
                                    )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateRole event
        elif eventname == 'UpdateRole':
            # Create boto3 client/resource connection
            iam_client = boto3.client('iam', region_name=region)
            try:
                # get values required for tagging from event details
                iam_role_name = detail['requestParameters']['roleName']
                logger.info(f'Tagging updated IAM role: {str(iam_role_name)}')
                
                # apply tags using iam_client
                iam_client.tag_role(RoleName=iam_role_name, 
                                    Tags=[
                                        {'Key': 'LastUpdatedBy', 'Value': user},
                                        {'Key': 'LastUpdatedAt', 'Value': event_time}
                                        ]
                                    )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreatePolicy event
        elif eventname == 'CreatePolicy':
            # Create boto3 client/resource connection
            iam_client = boto3.client('iam', region_name=region)
            try:
                # get values required for tagging from event details
                iam_policy_name = detail['responseElements']['policy']['policyName']
                iam_policy_arn = detail['responseElements']['policy']['arn']
                logger.info(f'Tagging new IAM policy: {str(iam_policy_name)}')
                
                # apply tags using iam_client
                iam_client.tag_policy(PolicyArn=iam_policy_arn, 
                                    Tags=[
                                        {'Key': 'Name', 'Value': iam_policy_name},
                                        {'Key': 'CreatedBy', 'Value': user},
                                        {'Key': 'CreatedAt', 'Value': event_time}
                                        ]
                                    )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreatePolicyVersion event
        elif eventname == 'CreatePolicyVersion':
            # Create boto3 client/resource connection
            iam_client = boto3.client('iam', region_name=region)
            try: 
                # get values required for tagging from event details
                iam_policy_arn = detail['requestParameters']['policyArn']
                iam_policy_name = iam_policy_arn.split("/")[1]
                logger.info(f'Tagging new IAM policy version: {str(iam_policy_name)}')
                
                # apply tags using iam_client
                iam_client.tag_policy(PolicyArn=iam_policy_arn, 
                                    Tags=[
                                        {'Key': 'LastVersionUpdatedBy', 'Value': user},
                                        {'Key': 'LastVersionUpdatedAt', 'Value': event_time}
                                        ]
                                    )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateOpenIDConnectProvider event
        elif eventname == 'CreateOpenIDConnectProvider':
            # Create boto3 client/resource connection
            iam_client = boto3.client('iam', region_name=region)
            try:
                # get values required for tagging from event details
                open_id_provider_arn = detail['responseElements']['openIDConnectProviderArn']
                logger.info(f'Tagging new IAM OpenID Connect Provider: {str(open_id_provider_arn)}')
                
                # apply tags using iam_client
                iam_client.tag_open_id_connect_provider(OpenIDConnectProviderArn=open_id_provider_arn, 
                                    Tags=[
                                        {'Key': 'CreatedBy', 'Value': user},
                                        {'Key': 'CreatedAt', 'Value': event_time}
                                        ]
                                    )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateSAMLProvider event
        elif eventname == 'CreateSAMLProvider':
            # Create boto3 client/resource connection
            iam_client = boto3.client('iam', region_name=region)
            try:
                # get values required for tagging from event details
                saml_provider_name = detail['requestParameters']['name']
                saml_provider_arn = detail['responseElements']['SAMLProviderArn']
                logger.info(f'Tagging new IAM SAML Provider: {str(saml_provider_arn)}')
                
                # apply tags using iam_client
                iam_client.tag_saml_provider(SAMLProviderArn=saml_provider_arn, 
                                    Tags=[
                                        {'Key': 'Name', 'Value': saml_provider_name},
                                        {'Key': 'CreatedBy', 'Value': user},
                                        {'Key': 'CreatedAt', 'Value': event_time}
                                        ]
                                    )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # CloudTrail events
        # processing of CreateTrail event
        elif eventname == 'CreateTrail':
            # Create boto3 client/resource connection
            cloudtrail_client = boto3.client('cloudtrail', region_name=region)
            try:
                # get values required for tagging from event details
                cloudtrail_arn = detail['responseElements']['TrailARN']
                cloudtrail_name = detail['responseElements']['Name']
                logger.info(f'Tagging created Cloudtrail resource: {str(cloudtrail_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(cloudtrail_name)
                
                # apply tags using cloudtrail_client
                cloudtrail_client.add_tags(ResourceId=cloudtrail_arn, 
                                    TagsList=[
                                        {'Key': 'Name', 'Value': cloudtrail_name},
                                        {'Key': 'CreatedBy', 'Value': user},
                                        {'Key': 'CreatedAt', 'Value': event_time},
                                        {'Key': 'Env', 'Value': env_tag},
                                        {'Key': 'Department', 'Value': dep_tag},
                                              ])
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateTrail event
        elif eventname == 'UpdateTrail':
            # Create boto3 client/resource connection
            cloudtrail_client = boto3.client('cloudtrail', region_name=region)
            try:
                # get values required for tagging from event details
                cloudtrail_arn = detail['responseElements']['TrailARN']
                cloudtrail_name = detail['responseElements']['Name']
                logger.info(f'Tagging updated Cloudtrail resource: {str(cloudtrail_name)}')
                
                # apply tags using cloudtrail_client
                cloudtrail_client.add_tags(ResourceId=cloudtrail_arn, 
                                    TagsList=[
                                            {'Key': 'LastUpdatedBy', 'Value': user},
                                            {'Key': 'LastUpdatedAt', 'Value': event_time}
                                            ]
                                    )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # OpsWorks events
        # processing of CreateStack event for OpsWorks
        elif eventname == 'CreateStack':
            if eventsource == 'opsworks.amazonaws.com':
                # Create boto3 client/resource connection
                opsworks_client = boto3.client('opsworks', region_name=region)
                try:
                    # get values required for tagging from event details
                    stack_name_request = detail['requestParameters']['name']
                    # get info on stacks
                    stacks = opsworks_client.describe_stacks()
                    # iterate over stacks
                    for stack in stacks['Stacks']:
                        stack_name_response = stack['Name']
                        # determine that stack in request is the same as in the event
                        if stack_name_request == stack_name_response:
                            # get stack arn
                            stack_arn = stack['Arn']
                            logger.info(f'Tagging new OpsWorks stack: {str(stack_name_request)}')
                            
                            # initiliaze TagEvaluator to determine Env and Department tags
                            tagevaluator = TagEvaluator()
                            env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(stack_name_response)
                            
                            # use lambda-python function to apply tags using opsworks_client
                            tagging = lambda key, value: opsworks_client.tag_resource(ResourceArn=stack_arn, Tags={key: value})
                    
                            tagging('Name', stack_name_response)
                            tagging('CreatedBy', user)
                            tagging('CreatedAt', event_time)
                            tagging('Env', env_tag)
                            tagging('Department', dep_tag)
                            
                        else:
                            logger.error('Cannot find stack: ' + str(stack_name_request))
                            finishing_sequence(context, eventname, status='fail', error='Cannot find stack', exception=False)
                            return False
                            
                except Exception as error:
                    logger.error(f'Error message: {str(error)}')
                    logger.exception('Exception thrown at OpsWorks CreateStack: ')
                    finishing_sequence(context, eventname, status='fail', error=error)
                    return False
            
            # processing of CreateStack event for Cloudformation 
            elif eventsource == 'cloudformation.amazonaws.com':
                # timesleep(300)
                # cloudformation_client = boto3.client('cloudformation', region_name=region)
                
                # def update_cfn_stack(stack_name: str, tags: list) -> bool:
                #     try:
                #         describe_stacks = cloudformation_client.describe_stacks(StackName=stack_name)
                #         for stack in describe_stacks['Stacks']:
                #             stack_status = stack['StackStatus']
                            
                #             stack_capabilities = list(stack['Capabilities']) if 'Capabilities' in stack else None
                #             stack_params = list(stack['Parameters']) if 'Parameters' in stack else None
                            
                #             if stack_status == 'CREATE_COMPLETE' or stack_status == 'UPDATE_COMPLETE':
                #                 logger.info(f'Updating Cloudformation stack: (status: {str(stack_status)})')
                                
                #                 updating_stack = lambda params, capabils: cloudformation_client.update_stack(StackName=stack_name, UsePreviousTemplate=True, Tags=tags,
                #                                                     Parameters=params, Capabilities=capabils)
                                
                #                 if stack_params and stack_capabilities:
                #                     logger.info('found stack with parameters and capabilities')
                #                     print(stack_params)
                #                     print(stack_capabilities)
                #                     updating_stack(stack_params, stack_capabilities)
                                    
                #                 elif stack_params and not stack_capabilities:
                #                     logger.info('found stack with parameters only')
                #                     print(stack_params)
                #                     updating_stack(stack_params, [])
                                    
                #                 elif not stack_params and stack_capabilities:
                #                     logger.info('found stack with capabilities only')
                #                     print(stack_capabilities)
                #                     updating_stack([], stack_capabilities)
                                    
                #                 elif not stack_params and not stack_capabilities:
                #                     logger.info('found stack without parameters and capabilities')
                #                     updating_stack([], [])
                                
                #                 return True
                                    
                #             else:
                #                 logger.error(f'Cannot update Cloudformation stack due to the current stack status: {str(stack_status)}')
                #                 return False
                            
                #     except Exception as error:
                #         logger.error(f'Error message: {str(error)}')
                #         logger.exception('Exception thrown at Cloudformation CreateStack update_cfn_stack: ')
                #         finishing_sequence(context, eventname, status='fail', error=error)
                #         return False
                
                try:
                    logger.info('Detected Cloudformation CreateStack event, skipping')
                    pass
                
                    # stack_name = detail['requestParameters']['stackName']
                    # logger.info(f'Tagging new Cloudformation stack: {str(stack_name)}')
                    
                    # initiliaze TagEvaluator to determine Env and Department tags
                    # tagevaluator = TagEvaluator()
                    # env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(stack_name)
                    
                    # tags_to_add = [
                    #                 {'Key': 'cfn:stack:name', 'Value': stack_name},
                    #                 {'Key': 'cfn:stack:resource', 'Value': 'true'},
                    #                 {'Key': 'cfn:stack:created-by', 'Value': user},
                    #                 {'Key': 'cfn:stack:created-at', 'Value': event_time},
                    #                 {'Key': 'Env', 'Value': env_tag},
                    #                 {'Key': 'Department', 'Value': dep_tag}
                    #             ]
                    
                    # if 'tags' in detail['requestParameters']:
                    #     logger.info('found predefined stack tags')
                    #     stack_tags = list(detail['requestParameters']['tags'])                       
                        
                    #     if stack_tags:
                    #         new_stack_tags = []
                        
                    #         for item in stack_tags:
                    #             new_stack_tags.append({k.capitalize():v for k,v in item.items()})
                                                                                                                                                                                    
                    #         for item in tags_to_add:
                    #             if item['Key'] in [tag['Key'] for tag in new_stack_tags]:
                    #                 tags_to_add = [tag for tag in tags_to_add if tag.get('Key') != item['Key']]
                                    
                    #         tags = new_stack_tags + tags_to_add
                        
                    #     elif not stack_tags:
                    #         tags = tags_to_add
                                                
                    # elif 'tags' not in detail['requestParameters']:
                    #     logger.info('not found predefined stack tags')
                    #     tags = tags_to_add
                    
                    # if tags:
                    #     if update_cfn_stack(stack_name, tags) is True:
                    #         logger.error('Stack update succeeded')
                    #         pass
                    #     else:
                    #         logger.error('Stack update failed')
                    #         return False
                    
                    # elif not tags:
                    #     logger.error('Cannot form tags')
                    #     return False
                
                except Exception as error:
                    logger.error(f'Error message: {str(error)}')
                    logger.exception('Exception thrown at Cloudformation CreateStack: ')
                    finishing_sequence(context, eventname, status='fail', error=error)
                    return False
            

        # processing of CloneStack event
        elif eventname == 'CloneStack':
            if eventsource == 'opsworks.amazonaws.com':
                # Create boto3 client/resource connection
                opsworks_client = boto3.client('opsworks', region_name=region)
                try:
                    # get values required for tagging from event details
                    stack_name_request = detail['requestParameters']['stackName']
                    # get info on stacks
                    stacks = opsworks_client.describe_stacks()
                    # iterate over stacks
                    for stack in stacks['Stacks']:
                        stack_name_response = stack['Name']
                        # determine that stack in request is the same as in the event
                        if stack_name_request == stack_name_response:
                            # get stack arn
                            stack_arn = stack['Arn']
                            logger.info(f'Tagging copied OpsWorks stack: {str(stack_name_request)}')
                            
                            # initiliaze TagEvaluator to determine Env and Department tags
                            tagevaluator = TagEvaluator()
                            env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(stack_name_response)
                            
                            # use lambda-python function to apply tags using opsworks_client
                            tagging = lambda key, value: opsworks_client.tag_resource(ResourceArn=stack_arn, Tags={key: value})
                    
                            tagging('Name', stack_name_response)
                            tagging('ClonnedBy', user)
                            tagging('ClonnedAt', event_time)
                            tagging('Env', env_tag)
                            tagging('Department', dep_tag)
                            
                        else:
                            logger.error('Cannot find stack: ' + str(stack_name_request))
                            
                except Exception as error:
                    logger.error(f'Error message: {str(error)}')
                    logger.error('Exception thrown at OpsWorks CloneStack: ')
                    finishing_sequence(context, eventname, status='fail', error=error)
                    return False

        # OpsWorksCM events
        # processing of CreateServer event
        elif eventname == 'CreateServer':
            # Create boto3 client/resource connection
            opsworkscm_client = boto3.client('opsworkscm', region_name=region)
            try:
                # get values required for tagging from event details
                server_arn = detail['responseElements']['server']['serverArn']
                server_name = detail['responseElements']['server']['serverName']
                logger.info(f'Tagging Chef Automate server: {str(server_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(server_name)
                
                # apply tags using opsworkscm_client
                opsworkscm_client.tag_resource(ResourceArn=server_arn, 
                                               Tags=[
                                                   {'Key': 'Name', 'Value': server_name},
                                                   {'Key': 'CreatedBy', 'Value': user},
                                                   {'Key': 'CreatedAt', 'Value': event_time},
                                                   {'Key': 'Env', 'Value': env_tag},
                                                   {'Key': 'Department', 'Value': dep_tag}
                                                   ]
                                               )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # processing of UpdateServer event
        elif eventname == 'UpdateServer':
            # Create boto3 client/resource connection
            opsworkscm_client = boto3.client('opsworkscm', region_name=region)
            try:
                # get values required for tagging from event details
                server_arn = detail['responseElements']['server']['serverArn']
                server_name = detail['responseElements']['server']['serverName']
                logger.info(f'Tagging updated Chef Automate server: {str(server_name)}')
                
                # apply tags using opsworkscm_client
                opsworkscm_client.tag_resource(ResourceArn=server_arn, 
                                               Tags=[
                                                     {'Key': 'LastUpdatedBy', 'Value': user}, 
                                                     {'Key': 'LastUpdatedAt', 'Value': event_time}
                                                     ]
                                               )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # Cloudfront events
        # processing of CreateDistribution event
        elif eventname == 'CreateDistribution':
            # Create boto3 client/resource connection           
            cloudfront_client = boto3.client('cloudfront', region_name=region)
            try:
                # get values required for tagging from event details
                cf_distribution_arn = detail['responseElements']['distribution']['aRN']
                cf_distribution_id = detail['responseElements']['distribution']['id']
                logger.info(f'Tagging updated CloudFront distribution: {str(cf_distribution_id)}')
                
                # apply tags using cloudfront_client
                cloudfront_client.tag_resource(Resource=cf_distribution_arn, 
                                               Tags={'Items': 
                                                   [
                                                   {'Key': 'CreatedBy', 'Value': user},
                                                   {'Key': 'CreatedAt', 'Value': event_time},
                                                   {'Key': 'Env', 'Value': 'ops'},
                                                   {'Key': 'Department', 'Value': 'Operations'}
                                                   ]
                                                     })
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # EKS & ECS events
        # processing of CreateCluster event
        elif eventname == 'CreateCluster':
            try:
                # check if cluster is related to ECS or EKS
                if eventsource == 'ecs.amazonaws.com':
                    # Create boto3 client/resource connection
                    ecs_client = boto3.client('ecs', region_name=region)
                    # get values required for tagging from event details
                    cluster_arn = detail['responseElements']['cluster']['clusterArn']
                    cluster_name = detail['responseElements']['cluster']['clusterName']
                    logger.info(f'Tagging ECS cluster: {str(cluster_name)}')
                    
                    # initiliaze TagEvaluator to determine Env and Department tags
                    tagevaluator = TagEvaluator()       
                    env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(cluster_name)
                    
                    # apply tags using ecs_client
                    ecs_client.tag_resource(resourceArn=cluster_arn, 
                                            tags=[
                                                {'key': 'Name', 'value': cluster_name},
                                                {'key': 'CreatedBy', 'value': user},
                                                {'key': 'CreatedAt', 'value': event_time},
                                                {'key': 'Env', 'value': env_tag},
                                                {'key': 'Department', 'value': dep_tag},
                                                ]
                                            )
                    
                elif eventsource == 'eks.amazonaws.com':
                    # Create boto3 client/resource connection
                    eks_client = boto3.client('eks', region_name=region)
                    # get values required for tagging from event details
                    cluster_arn = detail['responseElements']['cluster']['arn']
                    cluster_name = detail['responseElements']['cluster']['name']
                    logger.info(f'Tagging EKS cluster: {str(cluster_name)}')
                    
                    # initiliaze TagEvaluator to determine Env and Department tags
                    tagevaluator = TagEvaluator()     
                    env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(cluster_name)
                    
                    # use lambda-python function to apply tags using eks_client
                    tagging = lambda key, value: eks_client.tag_resource(resourceArn=nodegroup_arn, tags={key: value})
                    
                    tagging('Name', cluster_name)
                    tagging('CreatedBy', user)
                    tagging('CreatedAt', event_time)
                    tagging('Env', env_tag)
                    tagging('Department', dep_tag)
                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateNodegroup event
        elif eventname == 'CreateNodegroup' and eventsource == 'eks.amazonaws.com':
            # Create boto3 client/resource connection
            eks_client = boto3.client('eks', region_name=region)
            try:            
                # get values required for tagging from event details
                nodegroup_arn = detail['responseElements']['nodegroup']['nodegroupArn']
                nodegroup_name = detail['responseElements']['nodegroup']['nodegroupName']
                nodegroup_cluster = detail['responseElements']['nodegroup']['clusterName']
                logger.info(f'Tagging EKS Nodegroup: {str(nodegroup_name)} of cluster: {str(nodegroup_cluster)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()            
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(nodegroup_name)
                
                # use lambda-python function to apply tags using eks_client
                tagging = lambda key, value: eks_client.tag_resource(resourceArn=nodegroup_arn, tags={key: value})
                
                tagging('Name', nodegroup_name)
                tagging('Cluster', nodegroup_cluster)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateService event
        elif eventname == 'CreateService' and eventsource == 'ecs.amazonaws.com':
            # Create boto3 client/resource connection
            ecs_client = boto3.client('ecs', region_name=region)
            try:
                # get values required for tagging from event details
                service_arn = detail['responseElements']['service']['serviceArn']
                service_name = detail['responseElements']['service']['serviceName']
                cluster_name = detail['requestParameters']['cluster']
                logger.info(f'Tagging ECS service: {str(service_name)} (cluster: {cluster_name})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()            
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(service_name)
                
                # apply tags using ecs_client
                ecs_client.tag_resource(resourceArn=service_arn, 
                                        tags=[
                                            {'key': 'Name', 'value': service_name},
                                            {'key': 'Cluster', 'value': cluster_name},
                                            {'key': 'CreatedBy', 'value': user},
                                            {'key': 'CreatedAt', 'value': event_time},
                                            {'key': 'Env', 'value': env_tag},
                                            {'key': 'Department', 'value': dep_tag},
                                              ]
                                        )
                
                logger.info('Checking ECS service tasks and network interfaces')
                # wait 60 seconds to get details on tasks created within service
                timesleep(60)
                list_tasks = ecs_client.list_tasks(cluster=cluster_name, serviceName=service_name)
                if 'taskArns' in list_tasks:
                    for task_arn in list_tasks['taskArns']:
                        logger.info(f'found task: {task_arn}')
                        
                        # apply tags using ecs_client                
                        ecs_client.tag_resource(resourceArn=task_arn, 
                                                tags=[
                                                    {'key': 'CreatedBy', 'value': user},
                                                    {'key': 'CreatedAt', 'value': event_time},
                                                    {'key': 'ECS_Service', 'value': service_name},
                                                    {'key': 'Env', 'value': env_tag},
                                                    {'key': 'Department', 'value': dep_tag},
                                                    ]
                                                )
                        
                        # get details on tasks
                        describe_tasks = ecs_client.describe_tasks(
                            cluster=cluster_name,
                            tasks=[task_arn]
                        )
                        
                        # iterate over all found tasks and retrieve ENI interfaces
                        for task in describe_tasks['tasks']:
                            for attachment in task['attachments']:
                                for detail in attachment['details']:
                                    if detail['name'] == 'networkInterfaceId':
                                        eni_id = detail['value']
                                        logger.info(f'Tagging ECS task ENI: {str(eni_id)}')
                                        # initiliaze TagHandler to parse and tags ECS ENI
                                        enihandler = TagHandler(eni_id, region, scope="eni")
                                        enihandler.parse_and_tag_ecs_eni(user)
                                        
            except ecs_client.exceptions.InvalidParameterException as error:
                # handle exception of long arn format
                if 'Long arn format must be used for tagging operations' in error.response['Error']['Message']:
                    logger.info('Detected cluster using long ARN format, cannot tag ECS resources, proceeding with tagging ENI')
                    logger.info('Checking network interfaces')
                    timesleep(25)
                    # list existing tasks
                    list_tasks = ecs_client.list_tasks(cluster=cluster_name, serviceName=service_name)
                    if 'taskArns' in list_tasks:
                        for task_arn in list_tasks['taskArns']:
                            logger.info(f'found task: {task_arn}')
                            
                            # get details on tasks
                            describe_tasks = ecs_client.describe_tasks(
                                cluster=cluster_name,
                                tasks=[task_arn]
                            )
                            
                            # iterate over all found tasks and retrieve ENI interfaces
                            for task in describe_tasks['tasks']:
                                for attachment in task['attachments']:
                                    for detail in attachment['details']:
                                        if detail['name'] == 'networkInterfaceId':
                                            eni_id = detail['value']
                                            logger.info(f'Tagging ECS task ENI: {str(eni_id)}')
                                            # initiliaze TagHandler to parse and tags ECS ENI
                                            enihandler = TagHandler(eni_id, region, scope="eni")
                                            enihandler.parse_and_tag_ecs_eni(user)
                                            
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateService event
        elif eventname == 'UpdateService' and eventsource == 'ecs.amazonaws.com':
            # Create boto3 client/resource connection
            ecs_client = boto3.client('ecs', region_name=region)
            try:
                # get values required for tagging from event details
                service_arn = detail['responseElements']['service']['serviceArn']
                service_name = detail['requestParameters']['service']
                cluster_name = detail['requestParameters']['cluster']
                logger.info(f'Tagging updated ECS service: {str(service_name)} (cluster: {cluster_name})')
                
                # apply tags using ecs_client
                ecs_client.tag_resource(resourceArn=service_arn, 
                                        tags=[
                                            {'key': 'LastUpdatedBy', 'value': user},
                                            {'key': 'LastUpdatedAt', 'value': event_time}
                                            ]
                                        )
                
                # wait 60 seconds to get details on tasks created within service
                logger.info('Checking ECS service tasks and network interfaces')
                timesleep(60)
                # list existing tasks
                list_tasks = ecs_client.list_tasks(cluster=cluster_name, serviceName=service_name)
                if 'taskArns' in list_tasks:
                    for task_arn in list_tasks['taskArns']:
                        logger.info(f'found task: {task_arn}')
                        
                        # get details on tasks
                        describe_tasks = ecs_client.describe_tasks(
                            cluster=cluster_name,
                            tasks=[task_arn]
                        )
                        
                        # apply tags using ecs_client
                        ecs_client.tag_resource(resourceArn=task_arn, 
                        tags=[
                            {'key': 'CreatedBy', 'value': user},
                            {'key': 'LastUpdatedBy', 'value': user},
                            {'key': 'ECS_Service', 'value': service_name},
                            {'key': 'LastUpdatedAt', 'value': event_time}
                            ]
                        )
                        
                        # iterate over all found tasks and retrieve ENI interfaces
                        for task in describe_tasks['tasks']:
                            for attachment in task['attachments']:
                                for detail in attachment['details']:
                                    if detail['name'] == 'networkInterfaceId':
                                        eni_id = detail['value']
                                        logger.info(f'Tagging ECS task ENI: {str(eni_id)}')
                                        # initiliaze TagHandler to parse and tags ECS ENI
                                        enihandler = TagHandler(eni_id, region, scope="eni")
                                        enihandler.parse_and_tag_ecs_eni(user)
                                    
            except ecs_client.exceptions.InvalidParameterException as error:
                # handle exception of long arn format
                if 'Long arn format must be used for tagging operations' in error.response['Error']['Message']:
                    logger.info('Detected cluster using long ARN format, cannot tag ECS resources, proceeding with tagging ENI')
                    logger.info('Checking network interfaces')
                    timesleep(25)
                    # list existing tasks
                    list_tasks = ecs_client.list_tasks(cluster=cluster_name, serviceName=service_name)
                    if 'taskArns' in list_tasks:
                        for task_arn in list_tasks['taskArns']:
                            logger.info(f'found task: {task_arn}')
                            
                            # get details on tasks
                            describe_tasks = ecs_client.describe_tasks(
                                cluster=cluster_name,
                                tasks=[task_arn]
                            )
                            
                            # iterate over all found tasks and retrieve ENI interfaces
                            for task in describe_tasks['tasks']:
                                for attachment in task['attachments']:
                                    for detail in attachment['details']:
                                        if detail['name'] == 'networkInterfaceId':
                                            eni_id = detail['value']
                                            logger.info(f'Tagging ECS task ENI: {str(eni_id)}')
                                            # initiliaze TagHandler to parse and tags ECS ENI
                                            enihandler = TagHandler(eni_id, region, scope="eni")
                                            enihandler.parse_and_tag_ecs_eni(user)
                                                        
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of RegisterTaskDefinition event
        elif eventname == 'RegisterTaskDefinition':
            # Create boto3 client/resource connection
            ecs_client = boto3.client('ecs', region_name=region)
            try:
                # get values required for tagging from event details
                task_definition_arn = detail['responseElements']['taskDefinition']['taskDefinitionArn']
                task_definition_family = detail['responseElements']['taskDefinition']['family']
                logger.info(f'Tagging ECS task definition (family): {str(task_definition_family)}')
                
                # apply tags using ecs_client
                ecs_client.tag_resource(resourceArn=task_definition_arn, 
                                        tags=[
                                            {'key': 'TaskDefinitionFamily', 'value': task_definition_family},
                                            {'key': 'CreatedBy', 'value': user},
                                            {'key': 'CreatedAt', 'value': event_time}
                                            ]
                                        )
                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of RunTask event
        elif eventname == 'RunTask':
            # Create boto3 client/resource connection
            ecs_client = boto3.client('ecs', region_name=region)
            try:
                # get values required for tagging from event details
                cluster_name = detail['requestParameters']['cluster']
                for task in detail['responseElements']['tasks']:
                    task_arn = task['taskArn']
                    task_name = [taskname['name'] for taskname in task['containers']][0]
                    logger.info(f'Tagging ECS task: {str(task_name)}')
                    
                    # apply tags using ecs_client
                    ecs_client.tag_resource(resourceArn=task_arn, 
                                            tags=[
                                                {'key': 'Name', 'value': task_name},
                                                {'key': 'CreatedBy', 'value': user},
                                                {'key': 'CreatedAt', 'value': event_time}
                                                ]
                                            )
                    
                    
                    logger.info('Checking network interfaces')
                    timesleep(60)
                    # get details on tasks
                    describe_tasks = ecs_client.describe_tasks(cluster=cluster_name, tasks=[task_arn])
                    # iterate over all found tasks and retrieve ENI interfaces
                    for task in describe_tasks['tasks']:
                        for attachment in task['attachments']:
                            for detail in attachment['details']:
                                if detail['name'] == 'networkInterfaceId':
                                    eni_id = detail['value']
                                    logger.info(f'Tagging ECS task ENI: {str(eni_id)}')
                                    # initiliaze TagHandler to parse and tags ECS ENI
                                    enihandler = TagHandler(eni_id, region, scope="eni")
                                    enihandler.parse_and_tag_ecs_eni(user)

            except ecs_client.exceptions.InvalidParameterException as error:
                # handle exception of long arn format
                if 'Long arn format must be used for tagging operations' in error.response['Error']['Message']:
                    logger.info('Detected cluster using long ARN format, cannot tag ECS resources, proceeding with tagging ENI')
                    logger.info('Checking network interfaces')
                    timesleep(25)
                    # get tasks from event
                    for task in detail['responseElements']['tasks']:
                        task_arn = task['taskArn']
                        # get details on tasks
                        describe_tasks = ecs_client.describe_tasks(cluster=cluster_name, tasks=[task_arn])
                        if 'taskArns' in describe_tasks:
                            for task_arn in describe_tasks['taskArns']:
                                logger.info(f'found task: {task_arn}')
                                # get details on tasks again
                                describe_tasks = ecs_client.describe_tasks(
                                    cluster=cluster_name,
                                    tasks=[task_arn]
                                )
                                # iterate over all found tasks and retrieve ENI interfaces
                                for task in describe_tasks['tasks']:
                                    for attachment in task['attachments']:
                                        for detail in attachment['details']:
                                            if detail['name'] == 'networkInterfaceId':
                                                eni_id = detail['value']
                                                logger.info(f'Tagging ECS task ENI: {str(eni_id)}')
                                                # initiliaze TagHandler to parse and tags ECS ENI
                                                enihandler = TagHandler(eni_id, region, scope="eni")
                                                enihandler.parse_and_tag_ecs_eni(user)                  
                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # FSx and EFS events
        # processing of CreateFileSystem event
        elif eventname == 'CreateFileSystem':
            try:
                # processing of CreateFileSystem event for FSx
                if eventsource == 'fsx.amazonaws.com':
                    # Create boto3 client/resource connection
                    fsx_client = boto3.client('fsx', region_name=region)
                    
                    # get values required for tagging from event details
                    fsx_arn = detail['responseElements']['fileSystem']['resourceARN']
                    fsx_id = detail['responseElements']['fileSystem']['fileSystemId']
                    logger.info(f'Tagging FSx file system: {str(fsx_id)}')
                    
                    # apply tags using fsx_client
                    fsx_client.tag_resource(ResourceARN=fsx_arn, 
                                        Tags=[
                                            {'Key': 'CreatedBy', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time}
                                            ]
                                        )
                    
                    # if existing tags found, get Name tag
                    if 'tags' in detail['responseElements']['fileSystem']:
                        logger.info('found tags')
                        tags = detail['responseElements']['fileSystem']['tags']
                        # if Name tag is available use it to get Env and Department tags
                        if 'Name' in [tag['key'] for tag in tags]:
                            logger.info('found Name tag')
                            fsx_name = [tag['value'] for tag in tags if tag['key'] == 'Name'][0]
                            
                            # initiliaze TagEvaluator to determine Env and Department tags
                            tagevaluator = TagEvaluator()            
                            env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(fsx_name)
                            
                            # apply tags using fsx_client
                            fsx_client.tag_resource(ResourceARN=fsx_arn, Tags=[
                                                                                {'Key': 'Env', 'Value': env_tag},
                                                                                {'Key': 'Department', 'Value': dep_tag}
                                                                                ])
                    # if tags are not availabe, apply predefined tags
                    elif 'tags' not in detail['responseElements']['fileSystem']:
                        logger.info('no tags')
                        fsx_client.tag_resource(ResourceARN=fsx_arn, Tags=[
                                                                                {'Key': 'Env', 'Value': 'ops'},
                                                                                {'Key': 'Department', 'Value': 'Operations'}
                                                                                ])     
                
                # processing of CreateFileSystem event for EFS
                elif eventsource == 'elasticfilesystem.amazonaws.com':
                    # Create boto3 client/resource connection
                    efs_client = boto3.client('efs', region_name=region)
                    # get values required for tagging from event details
                    filesystem_id = detail['responseElements']['fileSystemId']
                    filesystem_name = detail['responseElements']['name']
                    logger.info(f'Tagging EFS file system: {str(filesystem_name)}')
                    
                    # apply tags using efs_client
                    efs_client.tag_resource(ResourceId=filesystem_id, 
                                        Tags=[
                                            {'Key': 'Name', 'Value': filesystem_name},
                                            {'Key': 'CreatedBy', 'Value': user},
                                            {'Key': 'CreatedAt', 'Value': event_time}
                                            ]
                                        )
                    
                    # if there are existing tags, get Name tag
                    if 'tags' in detail['responseElements']:
                        logger.info('found tags')
                        tags = detail['responseElements']['tags']
                        # if Name tag is available use it to get Env and Department tags
                        if 'Name' in [tag['key'] for tag in tags]:
                            logger.info('found Name tag')
                            fs_name = [tag['value'] for tag in tags if tag['key'] == 'Name'][0]
                            
                            # initiliaze TagEvaluator to determine Env and Department tags
                            tagevaluator = TagEvaluator()            
                            env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(fs_name)
                            
                            # apply tags using efs_client
                            efs_client.tag_resource(ResourceId=filesystem_id, Tags=[
                                                                                {'Key': 'Env', 'Value': env_tag},
                                                                                {'Key': 'Department', 'Value': dep_tag}
                                                                                 ])
                    # if tags not availabe, apply predefined tags
                    elif 'tags' not in detail['responseElements']:
                        logger.info('no tags')
                        efs_client.tag_resource(ResourceId=filesystem_id, Tags=[
                                                                                {'Key': 'Env', 'Value': 'ops'},
                                                                                {'Key': 'Department', 'Value': 'Operations'}
                                                                                ])                 
                            
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateFileSystem event
        elif eventname == 'UpdateFileSystem':
            try:
                if eventsource == 'fsx.amazonaws.com':
                    # Create boto3 client/resource connection
                    fsx_client = boto3.client('fsx', region_name=region)
                    # get values required for tagging from event details
                    fsx_arn = detail['responseElements']['fileSystem']['resourceARN']
                    fsx_id = detail['responseElements']['fileSystem']['fileSystemId']
                    logger.info(f'Tagging updated FSx file system: {str(fsx_id)}')
                    
                    # apply tags using fsx_client
                    fsx_client.tag_resource(ResourceARN=fsx_arn, 
                                        Tags=[
                                            {'Key': 'LastUpdatedBy', 'Value': user},
                                            {'Key': 'LastUpdatedAt', 'Value': event_time}
                                            ]
                                        )  
                    
                elif eventsource == 'elasticfilesystem.amazonaws.com':
                    # Create boto3 client/resource connection
                    efs_client = boto3.client('efs', region_name=region)
                    # get values required for tagging from event details
                    filesystem_id = detail['responseElements']['fileSystemId']
                    filesystem_name = detail['responseElements']['name']
                    logger.info(f'Tagging updated EFS file system: {str(filesystem_name)}')
                    
                    # apply tags using efs_client
                    efs_client.tag_resource(ResourceId=filesystem_id, 
                                        Tags=[
                                            {'Key': 'LastUpdatedBy', 'Value': user},
                                            {'Key': 'LastUpdatedAt', 'Value': event_time}
                                            ]
                                        )                                      
                
            except Exception as error:
                eventsource = eventsource.split('.')[0].upper()
                logger.error(f'Error message: {str(error)}')
                logger.exception(f'Exception thrown at {str(eventsource)} UpdateFileSystem: ')
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateMountTarget event
        elif eventname == 'CreateMountTarget':
            # Create boto3 client/resource connection
            efs_client = boto3.client('efs', region_name=region)
            try:
                # get values required for tagging from event details
                filesystem_id = detail['requestParameters']['fileSystemId']
                logger.info(f'Tagging EFS mount created for: {str(filesystem_id)}')
                
                # apply tags using efs_client
                efs_client.tag_resource(ResourceId=filesystem_id, 
                                       Tags=[
                                           {'Key': 'MountAddedBy', 'Value': user},
                                           {'Key': 'MountAddedAt', 'Value': event_time}
                                           ]
                                       )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateAccessPoint event
        elif eventname == 'CreateAccessPoint' and eventsource == 'elasticfilesystem.amazonaws.com':
            # Create boto3 client/resource connection
            efs_client = boto3.client('efs', region_name=region)
            try:
                # get values required for tagging from event details
                access_point_name = detail['responseElements']['name']
                access_point_id = detail['responseElements']['accessPointId']
                filesystem_id = detail['responseElements']['fileSystemId']
                logger.info(f'Tagging EFS access point: {str(access_point_name)} (created for {str(filesystem_id)})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()            
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(access_point_name)
                
                # apply tags using efs_client
                efs_client.tag_resource(ResourceId=access_point_id, 
                                       Tags=[
                                           {'Key': 'Name', 'Value': access_point_name},
                                           {'Key': 'CreatedBy', 'Value': user},
                                           {'Key': 'CreatedAt', 'Value': event_time},
                                           {'Key': 'Env', 'Value': env_tag},
                                           {'Key': 'Department', 'Value': dep_tag}
                                           ]
                                       )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # Cognito events
        # processing of CreateUserPool event
        elif eventname == 'CreateUserPool':
            # Create boto3 client/resource connection        
            cognito_client = boto3.client('cognito-idp', region_name=region)
            try:
                # get values required for tagging from event details
                userpool_arn = detail['responseElements']['userPool']['arn']
                userpool_name = detail['responseElements']['userPool']['name']
                logger.info(f'Tagging Cognito userpool: {str(userpool_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()            
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(userpool_name)
                
                # use lambda-python function to apply tags using cognito_client
                tagging = lambda key, value: cognito_client.tag_resource(ResourceArn=userpool_arn, Tags={key: value})
                
                tagging('Name', userpool_name)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateUserPool event
        elif eventname == 'UpdateUserPool':
            # Create boto3 client/resource connection        
            cognito_client = boto3.client('cognito-idp', region_name=region)
            try:
                # get values required for tagging from event details
                userpool_id = detail['requestParameters']['userPoolId']
                userpool_name = cognito_client.describe_user_pool(UserPoolId=userpool_id)['UserPool']['Name']
                userpool_arn = cognito_client.describe_user_pool(UserPoolId=userpool_id)['UserPool']['Arn']
                logger.info(f'Tagging updated Cognito userpool: {str(userpool_name)}')
                
                # use lambda-python function to apply tags using cognito_client
                tagging = lambda key, value: cognito_client.tag_resource(ResourceArn=userpool_arn, Tags={key: value})
                
                tagging('LastUpdatedBy', user)
                tagging('LastUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # EventBridge events
        # processing of PutRule event
        elif eventname == 'PutRule':
            # Create boto3 client/resource connection
            eventbridge_client = boto3.client('events', region_name=region)
            try:
                # get values required for tagging from event details
                event_rule_arn = detail['responseElements']['ruleArn']
                event_rule_name = detail['requestParameters']['name']
                logger.info(f'Tagging new EventBridge rule: {str(event_rule_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()            
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(event_rule_name)
                
                # apply tags using eventbridge_client
                eventbridge_client.tag_resource(ResourceARN=event_rule_arn, 
                                    Tags=[
                                        {'Key': 'Name', 'Value': event_rule_name},
                                        {'Key': 'CreatedBy', 'Value': user},
                                        {'Key': 'CreatedAt', 'Value': event_time},
                                        {'Key': 'Env', 'Value': env_tag},
                                        {'Key': 'Department', 'Value': dep_tag}
                                        ])
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # SNS events
        # processing of CreateTopic event
        elif eventname == 'CreateTopic':
            # Create boto3 client/resource connection
            sns_client = boto3.client('sns', region_name=region)
            try:
                # get values required for tagging from event details
                topic_arn = detail['responseElements']['topicArn']
                topic_name = detail['requestParameters']['name']
                logger.info(f'Tagging SNS topic: {str(topic_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()            
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(topic_name)
                
                # apply tags using sns_client
                sns_client.tag_resource(ResourceArn=topic_arn, 
                                    Tags=[
                                        {'Key': 'Name', 'Value': topic_name},
                                        {'Key': 'CreatedBy', 'Value': user},
                                        {'Key': 'CreatedAt', 'Value': event_time},
                                        {'Key': 'Env', 'Value': env_tag},
                                        {'Key': 'Department', 'Value': dep_tag}
                                        ])
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # SQS events
        # processing of CreateQueue event
        elif eventname == 'CreateQueue':
            # Create boto3 client/resource connection    
            sqs_client = boto3.client('sqs', region_name=region)
            try:
                # get values required for tagging from event details
                queue_url = detail['responseElements']['queueUrl']
                queue_name = detail['requestParameters']['queueName']
                logger.info(f'Tagging SQS queue: {str(queue_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()            
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(queue_name)
                
                # use lambda-python function to apply tags using sqs_client
                tagging = lambda key, value: sqs_client.tag_queue(QueueUrl=queue_url, Tags={key: value})
                
                tagging('Name', queue_name)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # ECR events
        # processing of CreateRepository event
        elif eventname == 'CreateRepository' and eventsource == 'ecr.amazonaws.com':
            # Create boto3 client/resource connection    
            ecr_client = boto3.client('ecr', region_name=region)
            try:
                # get values required for tagging from event details
                repo_arn = detail['responseElements']['repository']['repositoryArn']
                repo_name = detail['responseElements']['repository']['repositoryName']
                logger.info(f'Tagging ECR repository: {str(repo_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()            
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(repo_name)
                
                # apply tags using ecr_client
                ecr_client.tag_resource(resourceArn=repo_arn, 
                                    tags=[
                                        {'Key': 'Name', 'Value': repo_name},
                                        {'Key': 'CreatedBy', 'Value': user},
                                        {'Key': 'CreatedAt', 'Value': event_time},
                                        {'Key': 'Env', 'Value': env_tag},
                                        {'Key': 'Department', 'Value': dep_tag}
                                        ])
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # AWS Backup events
        # processing of CreateBackupVault event
        elif eventname == 'CreateBackupVault':
            # Create boto3 client/resource connection       
            backup_client = boto3.client('backup', region_name=region)
            try:
                # get values required for tagging from event details
                backup_vault_arn = detail['responseElements']['backupVaultArn']
                backup_vault_name = detail['responseElements']['backupVaultName']
                logger.info(f'Tagging Backup Vault: {str(backup_vault_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()            
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(backup_vault_name)
                
                # use lambda-python function to apply tags using backup_client
                tagging = lambda key, value: backup_client.tag_resource(ResourceArn=backup_vault_arn, Tags={key: value})
                
                tagging('Name', backup_vault_name)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateBackupPlan event
        elif eventname == 'CreateBackupPlan':
            # Create boto3 client/resource connection       
            backup_client = boto3.client('backup', region_name=region)
            try:
                # get values required for tagging from event details
                backup_plan_arn = detail['responseElements']['backupPlanArn']
                backup_plan_name = detail['requestParameters']['backupPlan']['backupPlanName']
                logger.info(f'Tagging Backup Plan: {str(backup_plan_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()            
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(backup_plan_name)
                
                # use lambda-python function to apply tags using backup_client
                tagging = lambda key, value: backup_client.tag_resource(ResourceArn=backup_plan_arn, Tags={key: value})
                
                tagging('Name', backup_plan_name)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateBackupPlan event
        elif eventname == 'UpdateBackupPlan':
            # Create boto3 client/resource connection       
            backup_client = boto3.client('backup', region_name=region)
            try:
                # get values required for tagging from event details
                backup_plan_arn = detail['responseElements']['backupPlanArn']
                backup_plan_name = detail['requestParameters']['backupPlan']['backupPlanName']
                logger.info(f'Tagging updated Backup Plan: {str(backup_plan_name)}')
                
                # use lambda-python function to apply tags using backup_client
                tagging = lambda key, value: backup_client.tag_resource(ResourceArn=backup_plan_arn, Tags={key: value})
                
                tagging('LastUpdatedBy', user)
                tagging('LastUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
        
        # Kinesis Data Stream events
        # processing of CreateStream event
        elif eventname == 'CreateStream':
            # Create boto3 client/resource connection        
            kinesis_client = boto3.client('kinesis', region_name=region)
            try:
                # get values required for tagging from event details
                kinesis_stream_name = detail['requestParameters']['streamName']
                logger.info(f'Tagging Kinesis Stream: {str(kinesis_stream_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()            
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(kinesis_stream_name)
                
                # use lambda-python function to apply tags using kinesis_client
                tagging = lambda key, value: kinesis_client.add_tags_to_stream(StreamName=kinesis_stream_name, Tags={key: value})
                
                tagging('Name', kinesis_stream_name)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
        
        # Kinesis Analytics events
        # processing of CreateApplication event for kinesisanalytics
        elif eventname == 'CreateApplication' and eventsource == 'kinesisanalytics.amazonaws.com':
            # Create boto3 client/resource connection
            kinesisanalytics_client = boto3.client('kinesisanalytics', region_name=region)
            try:
                # get values required for tagging from event details
                app_arn = detail['responseElements']['applicationDetail']['applicationARN']
                app_name = detail['responseElements']['applicationDetail']['applicationName']
                logger.info(f'Tagging KinesisAnalytics Application: {str(app_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()            
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(app_name)
                
                kinesisanalytics_client.tag_resource(ResourceARN=app_arn, 
                                    Tags=[
                                        {'Key': 'Name', 'Value': app_name},
                                        {'Key': 'CreatedBy', 'Value': user},
                                        {'Key': 'CreatedAt', 'Value': event_time},
                                        {'Key': 'Env', 'Value': env_tag},
                                        {'Key': 'Department', 'Value': dep_tag}
                                          ])
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateApplication event
        elif eventname == 'UpdateApplication' and eventsource == 'kinesisanalytics.amazonaws.com':
            # Create boto3 client/resource connection
            kinesisanalytics_client = boto3.client('kinesisanalytics', region_name=region)
            try:
                # get values required for tagging from event details
                app_arn = detail['responseElements']['applicationDetail']['applicationARN']
                app_name = detail['responseElements']['applicationDetail']['applicationName']
                logger.info(f'Tagging KinesisAnalytics Application: {str(app_name)}')
                
                # apply tags using kinesisanalytics_client
                kinesisanalytics_client.tag_resource(ResourceARN=app_arn, 
                                    Tags=[
                                          {'Key': 'LastUpdatedBy', 'Value': user}, 
                                          {'Key': 'LastUpdatedAt', 'Value': event_time}
                                          ]
                                    )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # Kinesis Firehose events
        # processing of CreateDeliveryStream event
        elif eventname == 'CreateDeliveryStream':
            # Create boto3 client/resource connection         
            firehose_client = boto3.client('firehose', region_name=region)
            try:
                # get values required for tagging from event details
                firehose_stream_name = detail['requestParameters']['deliveryStreamName']
                logger.info(f'Tagging Kinesis Firehose Delivery Stream: {str(firehose_stream_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()            
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(firehose_stream_name)
                
                # apply tags using firehose_client
                firehose_client.tag_delivery_stream(DeliveryStreamName=firehose_stream_name, 
                                           Tags=[
                                               {'Key': 'Name', 'Value': firehose_stream_name},
                                               {'Key': 'CreatedBy', 'Value': user},
                                               {'Key': 'CreatedAt', 'Value': event_time},
                                               {'Key': 'Env', 'Value': env_tag},
                                               {'Key': 'Department', 'Value': dep_tag}                                           
                                                 ])
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # AWS KMS events
        # processing of CreateKey event
        elif eventname == 'CreateKey' and eventsource == 'kms.amazonaws.com':
            # Create boto3 client/resource connection    
            kms_client = boto3.client('kms', region_name=region)
            try:
                # get values required for tagging from event details
                key_arn = detail['responseElements']['keyMetadata']['arn']
                key_id = detail['responseElements']['keyMetadata']['keyId']
                logger.info(f'Tagging KMS CMK key: {str(key_arn)}')
                
                # apply tags using kms_client
                kms_client.tag_resource(KeyId=key_id, 
                                    Tags=[
                                        {'TagKey': 'CreatedBy', 'TagValue': user},
                                        {'TagKey': 'CreatedAt', 'TagValue': event_time},
                                        {'TagKey': 'Env', 'TagValue': 'ops'},
                                        {'TagKey': 'Department', 'TagValue': 'Operations'}
                                        ])
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # AWS ACM (certificate manager) events
        # processing of ImportCertificate event
        elif eventname == 'ImportCertificate':
            # Create boto3 client/resource connection    
            acm_client = boto3.client('acm', region_name=region)
            try:
                # get values required for tagging from event details
                certificate_arn = detail['responseElements']['certificateArn']
                logger.info(f'Tagging ACM imported certificate: {str(certificate_arn)}')
                
                # apply tags using acm_client               
                acm_client.add_tags_to_certificate(CertificateArn=certificate_arn, 
                                    Tags=[
                                        {'Key': 'ImportedBy', 'Value': user},
                                        {'Key': 'ImportedBy', 'Value': event_time}
                                        ]
                                    )
                
                # wait 60 seconds to get certificat details
                timesleep(60)
                get_cert = acm_client.describe_certificate(CertificateArn=certificate_arn)
                domain_name = get_cert['Certificate']['DomainName']
                
                # remove wildcard from Name tag and assing certificate Name tag
                if re.search('\*', domain_name):
                    domain_name = '.'.join(domain_name.split('.')[1:3])
                    certificate_name = region + ':wildcard:' + domain_name
                else:
                    certificate_name = region + ':' + domain_name
                
                logger.info(f'ACM Name tag: {str(certificate_name)}')
                
                # apply tags using acm_client   
                acm_client.add_tags_to_certificate(CertificateArn=certificate_arn, 
                                    Tags=[{'Key': 'Name', 'Value': certificate_name}])
                                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of RequestCertificate event
        elif eventname == 'RequestCertificate':
            # Create boto3 client/resource connection    
            acm_client = boto3.client('acm', region_name=region)
            try:            
                certificate_arn = detail['responseElements']['certificateArn']
                domain_name = detail['requestParameters']['domainName']
                
                # get all alternative domain name into one list
                if 'subjectAlternativeNames' in detail['requestParameters']:
                    domain_names = []
                    domain_names.append(domain_name)
                    for alter_name in detail['requestParameters']['subjectAlternativeNames']:
                        domain_names.append(alter_name)
                    
                    logger.info(f'Tagging ACM requested certificate: {str(certificate_arn)} (domain names: {domain_names})')
                
                # if no alternative domain names found, proceed further
                elif 'subjectAlternativeNames' not in detail['requestParameters']:
                    logger.info(f'Tagging ACM requested certificate: {str(certificate_arn)} (domain name: {domain_name})')
                
                # remove wildcard from Name tag and assing certificate Name tag
                if re.search('\*', domain_name):
                    domain_name = '.'.join(domain_name.split('.')[1:3])
                    certificate_name = region + ':wildcard:' + domain_name
                else:
                    certificate_name = region + ':' + domain_name
                
                logger.info(f'ACM Name tag: {str(certificate_name)}')
                
                # apply tags using acm_client
                acm_client.add_tags_to_certificate(CertificateArn=certificate_arn, 
                                    Tags=[
                                        {'Key': 'RequestedBy', 'Value': user},
                                        {'Key': 'RequestedAt', 'Value': event_time},
                                        {'Key': 'Name', 'Value': certificate_name}
                                          ])
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False

        # AWS WorkSpaces events
        # processing of CreateWorkspaces event
        elif eventname == 'CreateWorkspaces':
            # Create boto3 client/resource connection           
            workspaces_client = boto3.client('workspaces', region_name=region)
            try:
                # get values required for tagging from event details
                for id in detail['responseElements']['pendingRequests']:
                    directory_id = id['directoryId']
                    workspace_id = id['workspaceId']
                    logger.info(f'Tagging AWS Directory: {str(directory_id)}')
                    
                    # apply tags to directory using workspaces_client
                    workspaces_client.create_tags(ResourceId=directory_id, 
                                       Tags=[
                                           {'Key': 'CreatedBy', 'Value': user},
                                           {'Key': 'CreatedAt', 'Value': event_time},
                                           {'Key': 'Env', 'Value': 'ops'},
                                           {'Key': 'Department', 'Value': 'Operations'}
                                           ])
                    logger.info(f'Tagging AWS Workspace: {str(workspace_id)}')
                    
                    # apply tags to workspace using workspaces_client
                    workspaces_client.create_tags(ResourceId=workspace_id, 
                                       Tags=[
                                           {'Key': 'CreatedBy', 'Value': user},
                                           {'Key': 'CreatedAt', 'Value': event_time},
                                           {'Key': 'Env', 'Value': 'ops'},
                                           {'Key': 'Department', 'Value': 'Operations'}
                                             ])
                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # Elastic Beanstalk events            
        # processing of CreateEnvironment event
        elif eventname == 'CreateEnvironment' and eventsource == 'elasticbeanstalk.amazonaws.com':
            # Create boto3 client/resource connection   
            eb_client = boto3.client('elasticbeanstalk', region_name=region)
            try:
                # get values required for tagging from event details
                environment_name = detail['requestParameters']['environmentName']
                application_name = detail['requestParameters']['applicationName']
                version_label = detail['requestParameters']['versionLabel']
                
                # get details on EB environment
                describe_environment = eb_client.describe_environments(ApplicationName=application_name, 
                                                                    VersionLabel=version_label,
                                                                    EnvironmentNames=[environment_name])
                                
                if describe_environment['Environments']:
                    # iterate over EB env details to get more required values
                    for environment in describe_environment['Environments']:
                        environment_name = environment['EnvironmentName']
                        application_name = environment['ApplicationName']
                        version_label = environment['VersionLabel']
                        environment_arn = environment['EnvironmentArn']
                        logger.info(f'Tagging EB Environment (application {str(application_name)}, version {str(version_label)}): {str(environment_name)}')
                        
                        # apply tags using eb_client   
                        eb_client.update_tags_for_resource(ResourceArn=environment_arn, 
                                                        TagsToAdd=[
                                                            {'Key': 'CreatedBy', 'Value': user},
                                                            {'Key': 'CreatedAt', 'Value': event_time},
                                                            {'Key': 'Department', 'Value': 'Beanstalk'}
                                                            ])
                        
                elif not describe_environment['Environments']:
                    logger.info('EB Environment is empty')
                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateEnvironment event
        elif eventname == 'UpdateEnvironment' and eventsource == 'elasticbeanstalk.amazonaws.com':
            # Create boto3 client/resource connection   
            eb_client = boto3.client('elasticbeanstalk', region_name=region)
            try:
                # get values required for tagging from event details
                environment_name = detail['requestParameters']['environmentName']
                # get details on EB environment
                describe_environment = eb_client.describe_environments(EnvironmentNames=[environment_name])
                
                if describe_environment['Environments']:
                    # iterate over EB env details to get more required values
                    for environment in describe_environment['Environments']:
                        environment_name = environment['EnvironmentName']
                        environment_arn = environment['EnvironmentArn']
                        logger.info(f'Tagging updated EB Environment: {str(environment_name)}')
                        
                        # apply tags using eb_client   
                        eb_client.update_tags_for_resource(ResourceArn=environment_arn, 
                                                        TagsToAdd=[
                                                            {'Key': 'LastUpdatedBy', 'Value': user},
                                                            {'Key': 'LastUpdatedAt', 'Value': event_time},
                                                            {'Key': 'Department', 'Value': 'Beanstalk'}
                                                            ]
                                                        )
                elif not describe_environment['Environments']:
                    logger.info('EB Environment is empty')
                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateApplication event
        elif eventname == 'CreateApplication' and eventsource == 'elasticbeanstalk.amazonaws.com':
            # Create boto3 client/resource connection   
            eb_client = boto3.client('elasticbeanstalk', region_name=region)
            try:
                # get values required for tagging from event details
                application_name = detail['requestParameters']['applicationName']
                # get details on EB application
                describe_application = eb_client.describe_applications(ApplicationNames=[application_name])
                
                # iterate over EB app details to get more required values
                for application in describe_application['Applications']:
                    application_name = application['ApplicationName']
                    application_arn = application['ApplicationArn']
                    logger.info(f'Tagging EB Application: {str(application_name)}')
                    
                    # apply tags using eb_client   
                    eb_client.update_tags_for_resource(ResourceArn=application_arn, 
                                                    TagsToAdd=[
                                                        {'Key': 'CreatedBy', 'Value': user},
                                                        {'Key': 'CreatedAt', 'Value': event_time},
                                                        {'Key': 'Department', 'Value': 'Beanstalk'}
                                                        ])
                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateApplication event
        elif eventname == 'UpdateApplication' and eventsource == 'elasticbeanstalk.amazonaws.com':
            # Create boto3 client/resource connection   
            eb_client = boto3.client('elasticbeanstalk', region_name=region)
            try:
                # get values required for tagging from event details
                application_name = detail['requestParameters']['applicationName']
                # get details on EB application
                describe_application = eb_client.describe_applications(ApplicationNames=[application_name])
                
                # iterate over EB app details to get more required values
                for application in describe_application['Applications']:
                    application_name = application['ApplicationName']
                    application_arn = application['ApplicationArn']
                    logger.info(f'Tagging updated EB Application: {str(application_name)}')
                    
                    # apply tags using eb_client   
                    eb_client.update_tags_for_resource(ResourceArn=application_arn, 
                                                    TagsToAdd=[
                                                        {'Key': 'LastUpdatedBy', 'Value': user},
                                                        {'Key': 'LastUpdatedAt', 'Value': event_time},
                                                        {'Key': 'Department', 'Value': 'Beanstalk'}
                                                        ]
                                                    )
                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
                        
        # processing of CreateApplicationVersion event
        elif eventname == 'CreateApplicationVersion' and eventsource == 'elasticbeanstalk.amazonaws.com':
            # Create boto3 client/resource connection   
            eb_client = boto3.client('elasticbeanstalk', region_name=region)
            try:
                # get values required for tagging from event details
                application_name = detail['requestParameters']['applicationName']
                version_label = detail['requestParameters']['versionLabel']
                # get details on EB application versions
                describe_app_version = eb_client.describe_application_versions(ApplicationName=application_name, VersionLabels=[version_label])
                
                # iterate over EB app version details to get more required values
                for app_version in describe_app_version['ApplicationVersions']:
                    application_name = app_version['ApplicationName']
                    version_label = app_version['VersionLabel']
                    app_version_arn = app_version['ApplicationVersionArn']
                    logger.info(f'Tagging EB Application Version (application {str(application_name)}): {str(version_label)}')
                    
                    # apply tags using eb_client   
                    eb_client.update_tags_for_resource(ResourceArn=app_version_arn, 
                                                    TagsToAdd=[
                                                        {'Key': 'CreatedBy', 'Value': user},
                                                        {'Key': 'CreatedAt', 'Value': event_time},
                                                        {'Key': 'Department', 'Value': 'Beanstalk'}
                                                        ])
                    
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # AWS Glue events
        # processing of CreateCrawler event
        elif eventname == 'CreateCrawler':
            # Create boto3 client/resource connection     
            glue_client = boto3.client('glue', region_name=region)
            try:
                # get values required for tagging from event details
                crawler_name = detail['requestParameters']['name']
                # determine arn using aws arn convention
                crawler_arn = f'arn:aws:glue:{region}:{aws_account_id}:crawler/{crawler_name}'
                logger.info(f'Tagging new Glue crawler: {str(crawler_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(crawler_name)
                
                # use lambda-python function to apply tags using glue_client
                tagging = lambda key, value: glue_client.tag_resource(ResourceArn=crawler_arn, TagsToAdd={key: value})
                
                tagging('Name', crawler_name)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateCrawler event
        elif eventname == 'UpdateCrawler':
            # Create boto3 client/resource connection     
            glue_client = boto3.client('glue', region_name=region)
            try:
                # get values required for tagging from event details
                crawler_name = detail['requestParameters']['name']
                # determine arn using aws arn convention
                crawler_arn = f'arn:aws:glue:{region}:{aws_account_id}:crawler/{crawler_name}'
                logger.info(f'Tagging updated Glue crawler: {str(crawler_name)}')
                
                # use lambda-python function to apply tags using glue_client
                tagging = lambda key, value: glue_client.tag_resource(ResourceArn=crawler_arn, TagsToAdd={key: value})
                
                tagging('LastUpdatedBy', user)
                tagging('LastUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of StartCrawler event
        elif eventname == 'StartCrawler':
            # Create boto3 client/resource connection     
            glue_client = boto3.client('glue', region_name=region)
            try:
                # get values required for tagging from event details
                crawler_name = detail['requestParameters']['name']
                # determine arn using aws arn convention
                crawler_arn = f'arn:aws:glue:{region}:{aws_account_id}:crawler/{crawler_name}'
                logger.info(f'Tagging started Glue crawler: {str(crawler_name)}')
                
                # use lambda-python function to apply tags using glue_client
                tagging = lambda key, value: glue_client.tag_resource(ResourceArn=crawler_arn, TagsToAdd={key: value})
                
                tagging('LastStartedBy', user)
                tagging('LastStartedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateRegistry event
        elif eventname == 'CreateRegistry':
            # Create boto3 client/resource connection     
            glue_client = boto3.client('glue', region_name=region)
            try:
                # get values required for tagging from event details
                registry_name = detail['responseElements']['registryName']
                registry_arn = detail['responseElements']['registryArn']
                logger.info(f'Tagging new Glue registry: {str(registry_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(registry_name)
                
                # use lambda-python function to apply tags using glue_client
                tagging = lambda key, value: glue_client.tag_resource(ResourceArn=registry_arn, TagsToAdd={key: value})
                
                tagging('Name', registry_name)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateRegistry event
        elif eventname == 'UpdateRegistry':
            # Create boto3 client/resource connection     
            glue_client = boto3.client('glue', region_name=region)
            try:
                # get values required for tagging from event details
                registry_name = detail['responseElements']['registryName']
                # determine arn using aws arn convention
                registry_arn = f'arn:aws:glue:{region}:{aws_account_id}:registry/{registry_name}'
                logger.info(f'Tagging updated Glue registry: {str(registry_name)}')
                
                # use lambda-python function to apply tags using glue_client
                tagging = lambda key, value: glue_client.tag_resource(ResourceArn=registry_arn, TagsToAdd={key: value})
                
                tagging('LastUpdatedBy', user)
                tagging('LastUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateSchema event
        elif eventname == 'CreateSchema':
            # Create boto3 client/resource connection     
            glue_client = boto3.client('glue', region_name=region)
            try:
                # get values required for tagging from event details
                schema_name = detail['responseElements']['schemaName']
                registry_name = detail['responseElements']['registryName']
                schema_arn = detail['responseElements']['schemaArn']
                logger.info(f'Tagging new Glue schema: {str(schema_name)} (registry: {str(registry_name)})')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(schema_name)
                
                # use lambda-python function to apply tags using glue_client
                tagging = lambda key, value: glue_client.tag_resource(ResourceArn=schema_arn, TagsToAdd={key: value})
                
                tagging('Name', schema_name)
                tagging('Registry', registry_name)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateSchema event
        elif eventname == 'UpdateSchema':
            # Create boto3 client/resource connection     
            glue_client = boto3.client('glue', region_name=region)
            try:
                # get values required for tagging from event details
                schema_name = detail['responseElements']['schemaName']
                registry_name = detail['responseElements']['registryName']
                # determine arn using aws arn convention
                schema_arn = f'arn:aws:glue:{region}:{aws_account_id}:schema/{registry_name}/{schema_name}'
                logger.info(f'Tagging updated Glue schema: {str(schema_name)} (registry: {str(registry_name)})')
                
                # use lambda-python function to apply tags using glue_client
                tagging = lambda key, value: glue_client.tag_resource(ResourceArn=schema_arn, TagsToAdd={key: value})
                
                tagging('LastUpdatedBy', user)
                tagging('LastUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateJob event
        elif eventname == 'CreateJob':
            # Create boto3 client/resource connection     
            glue_client = boto3.client('glue', region_name=region)
            try:
                # get values required for tagging from event details
                job_name = detail['responseElements']['name']
                # determine arn using aws arn convention
                job_arn = f'arn:aws:glue:{region}:{aws_account_id}:job/{job_name}'
                logger.info(f'Tagging new Glue job: {str(job_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(job_name)
                
                # use lambda-python function to apply tags using glue_client
                tagging = lambda key, value: glue_client.tag_resource(ResourceArn=job_arn, TagsToAdd={key: value})
                
                tagging('Name', job_name)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateJob event
        elif eventname == 'UpdateJob':
            # Create boto3 client/resource connection     
            glue_client = boto3.client('glue', region_name=region)
            try:
                # get values required for tagging from event details
                job_name = detail['responseElements']['jobName']
                # determine arn using aws arn convention
                job_arn = f'arn:aws:glue:{region}:{aws_account_id}:job/{job_name}'
                logger.info(f'Tagging updated Glue job: {str(job_name)}')
                
                # use lambda-python function to apply tags using glue_client
                tagging = lambda key, value: glue_client.tag_resource(ResourceArn=job_arn, TagsToAdd={key: value})
                
                tagging('LastUpdatedBy', user)
                tagging('LastUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateWorkflow event
        elif eventname == 'CreateWorkflow':
            # Create boto3 client/resource connection     
            glue_client = boto3.client('glue', region_name=region)
            try:
                # get values required for tagging from event details
                workflow_name = detail['responseElements']['name']
                # determine arn using aws arn convention
                workflow_arn = f'arn:aws:glue:{region}:{aws_account_id}:workflow/{workflow_name}'
                logger.info(f'Tagging new Glue workflow: {str(workflow_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(workflow_name)
                
                # use lambda-python function to apply tags using glue_client
                tagging = lambda key, value: glue_client.tag_resource(ResourceArn=workflow_arn, TagsToAdd={key: value})
                
                tagging('Name', workflow_name)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateWorkflow event
        elif eventname == 'UpdateWorkflow':
            # Create boto3 client/resource connection     
            glue_client = boto3.client('glue', region_name=region)
            try:
                # get values required for tagging from event details
                workflow_name = detail['responseElements']['name']
                # determine arn using aws arn convention
                workflow_arn = f'arn:aws:glue:{region}:{aws_account_id}:workflow/{workflow_name}'
                logger.info(f'Tagging updated Glue workflow: {str(workflow_name)}')
                
                # use lambda-python function to apply tags using glue_client
                tagging = lambda key, value: glue_client.tag_resource(ResourceArn=workflow_arn, TagsToAdd={key: value})
                
                tagging('LastUpdatedBy', user)
                tagging('LastUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of CreateTrigger event
        elif eventname == 'CreateTrigger':
            # Create boto3 client/resource connection     
            glue_client = boto3.client('glue', region_name=region)
            try:
                # get values required for tagging from event details
                trigger_name = detail['responseElements']['name']
                # determine arn using aws arn convention
                trigger_arn = f'arn:aws:glue:{region}:{aws_account_id}:trigger/{trigger_name}'
                logger.info(f'Tagging new Glue trigger: {str(trigger_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(trigger_name)
                
                # use lambda-python function to apply tags using glue_client
                tagging = lambda key, value: glue_client.tag_resource(ResourceArn=trigger_arn, TagsToAdd={key: value})
                
                tagging('Name', trigger_name)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateTrigger event
        elif eventname == 'UpdateTrigger':
            # Create boto3 client/resource connection     
            glue_client = boto3.client('glue', region_name=region)
            try:
                # get values required for tagging from event details
                trigger_name = detail['requestParameters']['name']
                # determine arn using aws arn convention
                trigger_arn = f'arn:aws:glue:{region}:{aws_account_id}:trigger/{trigger_name}'
                logger.info(f'Tagging updated Glue trigger: {str(trigger_name)}')
                
                # use lambda-python function to apply tags using glue_client
                tagging = lambda key, value: glue_client.tag_resource(ResourceArn=trigger_arn, TagsToAdd={key: value})
                
                tagging('LastUpdatedBy', user)
                tagging('LastUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # AppSync events
        # processing of CreateGraphqlApi event
        elif eventname == 'CreateGraphqlApi':
            # Create boto3 client/resource connection        
            appsync_client = boto3.client('appsync', region_name=region)
            try:
                # get values required for tagging from event details
                graphql_api_name = detail['responseElements']['graphqlApi']['name']
                graphql_api_arn = detail['responseElements']['graphqlApi']['arn']
                logger.info(f'Tagging new AppSync GraphqlApi: {str(graphql_api_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(graphql_api_name)
                
                # use lambda-python function to apply tags using appsync_client
                tagging = lambda key, value: appsync_client.tag_resource(resourceArn=graphql_api_arn, tags={key: value})
                
                tagging('Name', graphql_api_name)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of UpdateGraphqlApi event
        elif eventname == 'UpdateGraphqlApi':
            # Create boto3 client/resource connection        
            appsync_client = boto3.client('appsync', region_name=region)
            try:
                # get values required for tagging from event details
                graphql_api_name = detail['responseElements']['graphqlApi']['name']
                graphql_api_arn = detail['responseElements']['graphqlApi']['arn']
                logger.info(f'Tagging updated AppSync GraphqlApi: {str(graphql_api_name)}')
                
                # use lambda-python function to apply tags using appsync_client
                tagging = lambda key, value: appsync_client.tag_resource(resourceArn=graphql_api_arn, tags={key: value})
                
                tagging('LastUpdatedBy', user)
                tagging('LastUpdatedAt', event_time)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # CloudWatch events
        # processing of CreateLogGroup event
        elif eventname == 'CreateLogGroup':
            # Create boto3 client/resource connection
            cloudwatch_logs_client = boto3.client('logs', region_name=region)
            try:
                # get values required for tagging from event details
                log_group_name = detail['requestParameters']['logGroupName']
                logger.info(f'Tagging new CloudWatch Log Group: {str(log_group_name)}')
                
                # initiliaze TagEvaluator to determine Env and Department tags
                tagevaluator = TagEvaluator()
                env_tag, dep_tag = tagevaluator.evaluate_env_and_dep_tags(log_group_name)
                
                # use lambda-python function to apply tags using cloudwatch_logs_client
                tagging = lambda key, value: cloudwatch_logs_client.tag_log_group(logGroupName=log_group_name, tags={key: value})
                
                tagging('Name', log_group_name)
                tagging('CreatedBy', user)
                tagging('CreatedAt', event_time)
                tagging('Env', env_tag)
                tagging('Department', dep_tag)
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # processing of PutMetricAlarm event
        elif eventname == 'PutMetricAlarm':
            # Create boto3 client/resource connection           
            cloudwatch_client = boto3.client('cloudwatch', region_name=region)
            try:
                # get values required for tagging from event details
                metric_alarm_name = detail['requestParameters']['alarmName']
                # determine arn using aws arn convention
                metric_alarm_arn = f'arn:aws:cloudwatch:{region}:{aws_account_id}:alarm:{metric_alarm_name}'
                logger.info(f'Tagging new Cloudwatch metric alarm: {str(metric_alarm_name)}')
                
                # apply tags using cloudwatch_client
                cloudwatch_client.tag_resource(ResourceARN=metric_alarm_arn, 
                                          Tags=[
                                            {'Key': 'alarm:name', 'Value': 'string'},
                                            {'Key': 'alarm:created-by', 'Value': user},
                                            {'Key': 'alarm:created-at', 'Value': event_time}
                                          ]
                                          )
                                          
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
                
        # processing of PutInsightRule event
        elif eventname == 'PutInsightRule':
            # create boto3 client connection
            cloudwatch_client = boto3.client('cloudwatch', region_name=region)
            try:
                # get values required for tagging from event details
                insights_rule_name = detail['requestParameters']['ruleName']
                # determine arn using aws arn convention
                insights_rule_arn = f'arn:aws:cloudwatch:{region}:{aws_account_id}:insight-rule/{insights_rule_name}'
                logger.info(f'Tagging new Cloudwatch insights rule: {str(insights_rule_name)}')
                
                # apply tags using cloudwatch_client
                cloudwatch_client.tag_resource(ResourceARN=insights_rule_arn, 
                                          Tags=[
                                            {'Key': 'insights-rule:name', 'Value': 'string'},
                                            {'Key': 'insights-rule:created-by', 'Value': user},
                                            {'Key': 'insights-rule:created-at', 'Value': event_time}
                                            ]
                                          )
                
            except Exception as error:
                finishing_sequence(context, eventname, status='fail', error=error)
                return False
            
        # End of Events sequence
        ########################
        
        else:
            # if no matching eventname found, log the status and exit with False boolean
            logger.warning('No matching eventname found')
            finishing_sequence(context, eventname, status='fail', error="NoMatchingEventName")
            return False
        
        # if event processing exits without error, output "success" status and return True boolean
        finishing_sequence(context, eventname, status='success')
        return True

    except Exception as lambda_handler_error:
        logger.error(f'Error message: {str(lambda_handler_error)}')
        logger.exception('Something went wrong with lambda_handler: ')
        
         # if event processing exits with error/exception, output "success" status and return True boolean
        finishing_sequence(context, eventname, status='fail', error=lambda_handler_error)
        return False
