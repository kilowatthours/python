################################################################################
##    FILE:  	ami-auto-tagging.py                                           ##
##                                                                            ##
##    NOTES: 	Script to automatically apply tags for EC2 AMI's and their    ##
##              snapshots based on corresponding instance tags                ##
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

class ImageHandler:
    """
    EC2Handler Class containing instance, image and volume iterators
    """

      
    def __init__(self, images: list = "*", region: str = 'us-west-2', DEBUG: bool = True):
        """
        main __init__ function
        
        Args: 
            images ([str]): list of images to parse
            region ([str]): us-west-2 by default
            DEBUG ([bool]): true or false
    
        Returns:
            self
        """        
        
        if self:
            try:
                print("Initiliazing ImageHandler")
                self.images = images
                self.region = region
                self.DEBUG = DEBUG
                
                if DEBUG:
                    print(f"{color.RED}Running in DEBUG{color.END}")
                else:
                    print(f"{color.GREEN}Running in ACTIVE MODE{color.END}")
                    
                self.ec2 = boto3.resource('ec2', region_name=region)
                self.ec2_client = boto3.client('ec2', region_name=region)
                
                for self.imagename in self.get_imagenames(images):
                    print(f"{color.BOLD}Parsing image name: {str(self.imagename)}{color.END}")
                    for self.imageid in self.get_imageids(self.imagename):
                        print(f"{color.CYAN}-Parsing image: {str(self.imageid)}{color.END}")
                        self.image_tags = self.get_instancetags(self.imagename)
                        
                        if not self.image_tags:
                            print(f"{color.YELLOW}Attempting to evaluate tags by originId{color.END}")
                            intanceId = self.get_instanceid_by_originid(self.imagename)
                            if intanceId != "":
                                self.image_tags = self.get_instancetags_by_originid(intanceId)
                            else:
                                print(f"{color.RED}Cannot process tags, please tag manually: {self.imageid}{color.END}")
                                pass
                            
                        if self.image_tags:
                            self.apply_tags()
                            self.snap_tagger()
                            print(f"\n")
                            
            except Exception as error:
                print(f"{color.RED}Error message when processing EC2Handler: {str(error)}{color.END}")
                exit()

    def get_imagenames(self, images: list):
        try:
            self.images = self.ec2_client.describe_images(Filters=[{'Name': 'tag:Name', 'Values': images}])
            images = []
            for image in self.images['Images']:
                imagename = [tag['Value'] for tag in image['Tags'] if tag['Key'] == 'Name'][0]
                if imagename not in images:
                    images.append(imagename)
                    
            return images

        except Exception as error:
            print(f"{color.RED}Error message when attempting to get_imagenames: {str(error)}{color.END}")
            exit()
            
            
    def get_imageids(self, imagename: str):
        try:
            self.images = self.ec2_client.describe_images(Filters=[{'Name': 'tag:Name', 'Values': [imagename]}])
            imageIds = []
            for image in self.images['Images']:
                imageId = image['ImageId']
                imageIds.append(imageId)
            
            return imageIds

        except Exception as error:
            print(f"{color.RED}Error message when attempting to get_imageids: {str(error)}{color.END}")
            exit()
            
            
    def get_instancetags(self, imagename: str) -> bool:
        try:
            instances = self.ec2_client.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': [imagename]}])
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    instance_tags = instance['Tags']
                    image_tags = self.get_tags(instance_tags)
                    
                    if image_tags:
                        return image_tags
                    else:
                        return False

        except Exception as error:
            print(f"{color.RED}Error message when attempting to get_instancetags: {str(error)}{color.END}")
            exit()
            
    def get_instanceid_by_originid(self, imagename: str):
        try:
            self.images = self.ec2_client.describe_images(Filters=[{'Name': 'tag:Name', 'Values': [imagename]}])
            originId = ""
            for image in self.images['Images']:
                image_tags = image['Tags']
                if "Origin.Id" in [tag['Key'] for tag in image_tags]:
                    originId = [tag['Value'] for tag in image_tags if tag['Key'] == "Origin.Id"][0]
                
            return originId
                
        except Exception as error:
            print(f"{color.RED}Error message when attempting to get_instanceid_by_originid: {str(error)}{color.END}")
            exit()
            
            
    def get_instancetags_by_originid(self, instanceId: str) -> bool:
        try:
            instances = self.ec2_client.describe_instances(InstanceIds=[instanceId])
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    instance_tags = instance['Tags']
                    image_tags = self.get_tags(instance_tags)
                    
                    if image_tags:
                        return image_tags
                    else:
                        return False

        except Exception as error:
            print(f"{color.RED}Error message when attempting to get_instancetags_by_originid: {str(error)}{color.END}")
            exit()
            
            
    def get_tags(self, instance_tags: list):
        try:
            image_tags = []
            for tag in instance_tags:
                image_tags.append(tag)
                
            if image_tags:
                print(f"{color.GREEN}Formed tags: {color.END}{image_tags}")
                
                return image_tags

        except Exception as error:
            print(f"{color.RED}Error message when attempting to get_tags: {str(error)}{color.END}")
            exit()
    
    
    def apply_tags(self, resourceid):
        try:
            if not self.DEBUG:
                self.ec2_client.create_tags(Resources=[resourceid], Tags=self.image_tags)
            else:
                pass

        except Exception as error:
            print(f"{color.RED}Error message when attempting to apply_tags: {str(error)}{color.END}")
            exit()
            
    def snap_tagger(self):
        images = self.ec2_client.describe_images(ImageIds=[self.imageid], Owners=['461796779995'])
        try:
            for ami in images['Images']:
                print(f"{color.DARKCYAN}--Parsing snaphots of: {str(self.imageid)}{color.END}")
                for snapshot in ami['BlockDeviceMappings']:
                    snapshotid = snapshot['Ebs']['SnapshotId']
                    print(f"{color.CYAN}---snapshot: {str(snapshotid)}{color.END}")
                    self.apply_tags(snapshotid)

        except Exception as error:
            print(f"{color.RED}Encountered errors{color.END}")
            raise error


##########################################

parser = argparse.ArgumentParser()
parser.add_argument("--apply", "-A", "-a", default=True, dest='debug', action='store_false')
parser.add_argument("--images", "--amis", "--names", nargs="+", dest='images', default=["*"])
args = parser.parse_args()

DEBUG = args.debug
images = args.images

##########################################

if __name__ == '__main__':
    ec2handler = ImageHandler(images, DEBUG)