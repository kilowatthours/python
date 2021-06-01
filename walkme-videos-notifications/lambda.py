################################################################################
##    FILE:  	lambda.py (walkme-videos-notifications)                       ##
##                                                                            ##
##    NOTES: 	A script to send notifications upong uploading video file     ##
##              to S3 bucket                                                  ##
##                                                                            ##
##    AUTHOR:	Stepan Litsevych                                              ##
##                                                                            ##
##    Copyright 2020 - Baxter Planning Systems, Inc. All rights reserved      ##
################################################################################

#!/usr/bin/env python

# importing modules and packages
from __future__ import print_function

import boto3
import re
import os
import logging

from urllib.parse import unquote_plus
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate

# assigning variables from global vars
SES_REGION = os.environ.get('SES_REGION') if os.environ.get('SES_REGION') else "us-west-2"
ENV = os.environ.get('ENV')
COMMIT = os.environ.get('COMMIT')

# creating logger object
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# creating s3 connection using boto3 client
s3_client = boto3.client('s3')

# function setting email logic, email destinations and sending emails using SES etc
def sendSESEmail(html_text: str = None,
                 type: str = None) -> None:
    """
    Internal function dealing with email login and sending notification via email using SES.

    Args:
        html_text (str, optional): html email body text. Defaults to None.
        type (str, optional): evaluate if we're processing image or video. Defaults to None.
    """    
    try:
        # determine a list of email addresses to send emails to
        email_destinations = os.environ.get('SES_SEND_TO').split(",")
        # creating email message logic
        msg = MIMEMultipart()
        msg['From'] = os.environ.get('SES_SEND_FROM')
        msg['To'] = COMMASPACE.join(email_destinations)
        msg['Date'] = formatdate(localtime=True)
        
        # determining email subject based on type of uploaded files
        if type == "video":
            msg['Subject'] = "New video file for Walkme has been uploaded!"
        elif type == "image":
            msg['Subject'] = "New image file for Walkme has been uploaded!"
        elif type == "test":
            msg['Subject'] = "TESTING MODE: walkme-videos-notifications has been updated!"
             
        msg.attach(MIMEText(html_text, 'html'))

        # send the notification via email using SES
        logger.info(f'sending email to {email_destinations}')
        ses_client = boto3.client('ses', region_name=SES_REGION)
        ses_client.send_raw_email(
            Source=msg['From'],
            Destinations=email_destinations,
            RawMessage={'Data': msg.as_string()}
        )
    
    except Exception:
        logger.exception('Something went wrong with sendSESEmail function: ')
        raise

# function composing a email message text and returning it further
def composeHtmlText(bucket:str = None,
              key: str = None,
              version: str = None,
              type: str = None) -> str:
    
    """
    Internal function composing text and passing data to composeEmail function

    Args:
        bucket (str, optional): bucket name. Defaults to None.
        key (str, optional): bucket object name. Defaults to None.
        version (str, optional): function version. Defaults to None.
        type (str, optional): evaluate if we're processing image or video. Defaults to None.
    """    
    try:
        # get file size and file name
        filename = key.split('/')[1]
        filesize = str(round(s3_client.head_object(Bucket=bucket, Key=key)['ContentLength'] / (1000**2), 2))

        if os.environ.get('SES_SEND_TO') and type == 'video':
            html_text = f"""
                <html>
                    <head></head>
                        <body>
                            <br>
                            Video file has been successfully uploaded to the S3 bucket of Walkme!
                            <br>
                            Information about the video file:
                            <br><br>
                            <u>Name</u>: {filename}
                            <br>
                            <u>Size</u>: {filesize} MB
                            <br><br>
                            Use the following link to post the video in Walkme:
                            <a href="https://walkme.baxterplanning.com/{key}">https://walkme.baxterplanning.com/{key}</a>
                            <br><br>
                            To check the video prior to posting it into Walkme, paste the URL in:
                            <a href="https://walkme-upload.baxterplanning.com/player/">Walkme Videos Player</a>
                            <br><br>
                            <i>(please kindly note that video URL's are not allowed to be viewed directly in browser, use them only in Walkme or <a href="https://walkme-upload.baxterplanning.com/player/">Walkme Videos Player</a>)</i>
                            <br><br>
                            <br><br>
                            <br><br>
                            <br><br>
                            ----------------------
                            <br>
                            Bucket: {bucket}
                            <br>
                            Key: {key}
                            <br>
                            environment: {ENV}
                            <br>
                            commit: {COMMIT}
                            <br>
                            version: {version}
                            <br>
                        </body>
                </html>
                """        
        elif os.environ.get('SES_SEND_TO') and type == "image":
            html_text = f"""
                <html>
                    <head></head>
                        <body>
                            <br>
                            Image file has been successfully uploaded to the S3 bucket of Walkme!
                            <br>
                            Information about the image:
                            <br><br>
                            <u>Name</u>: {filename}
                            <br>
                            <u>Size</u>: {filesize} MB
                            <br><br>
                            Use the following link to paste the image in Walkme:
                            <br><br>
                            <a href="https://walkme.baxterplanning.com/{key}">https://walkme.baxterplanning.com/{key}</a>
                            <br><br>
                            <br><br>
                            <br><br>
                            <br><br>
                            ----------------------
                            <br>
                            Bucket: {bucket}
                            <br>
                            Key: {key}
                            <br>
                            environment: {ENV}
                            <br>
                            commit: {COMMIT}
                            <br>
                            version: {version}
                            <br>
                        </body>
                </html>
                """        
        elif type == "test":
            html_text = f"""
                <html>
                    <head></head>
                        <body>
                            <br>
                            TESTING MODE:
                            <br>
                            "Walkme-videos-notifications" function has been successfully updated.
                            <br><br>
                            Information about S3 object:
                            <br>
                            Bucket: <b>{bucket}</b>
                            <br>
                            Key: <b>{key}</b>
                            <br><br>
                            Information about the image file:
                            <br>
                            Name: {filename}
                            <br>
                            Size: {filesize} MB
                            <br>
                            Use the following link to paste the file in Walkme:
                            <a href="https://walkme.baxterplanning.com/{key}">https://walkme.baxterplanning.com/{key}</a>
                            <br><br>
                            <br><br>
                            <br><br>
                            <br><br>
                            ----------------------
                            <br>
                            Bucket: {bucket}
                            <br>
                            Key: {key}
                            <br>
                            environment: {ENV}
                            <br>
                            commit: {COMMIT}
                            <br>
                            version: {version}
                            <br>
                        </body>
                </html>
                """
                
        if html_text:
            return html_text
        else:
            logger.error('Cannot create html_text')
                
    except Exception:
        logger.exception('Something went wrong with composeHtmlText function: ')
        raise

# main handler function with event details
def main_handler(event, context) -> None:
    """
    This functions processes events from S3, filters filenames, and publishes to SES
    :param event: List of S3 Events
    :param context: AWS Lambda Context Object
    :return: bool True or False
    """
    # iterate over event records
    for record in event['Records']:
        # get bucket name
        bucket = record['s3']['bucket']['name']
        # get object key
        key = unquote_plus(record['s3']['object']['key'], encoding='utf-8')
        # get version of the function
        version = context.function_version     
        try:
            # get all details on an uploaded object from bucket using its key
            response = s3_client.get_object(Bucket=bucket, Key=key)
            content_type = response['ContentType'].split(';')[0]
            type = None
            
            # check folder in object key and its content type; based on this compose an email for specific type
            # compose email for video file of mp4 type uploaded to videos folder
            if re.search('videos/', key) and content_type == "video/mp4":
                logger.info('detected mp4 file uploaded to /videos folder, sending email')
                type = 'video'
            # compose email for image file (not .bmp) accidentally uploaded to videos folder
            elif re.search('videos/', key) and re.search('image/', content_type) and not content_type == "image/bmp":
                logger.info('detected image file uploaded to /videos folder, sending email')
                type = 'image'
            # compose email for video file of mp4 type accidentally uploaded to images folder
            elif re.search('images/', key) and content_type == "video/mp4":
                logger.info('detected mp4 file uploaded to /images folder, sending email')
                type = 'video'
            # compose email for image file (not .bmp) uploaded to images folder
            elif re.search('images/', key) and re.search('image/', content_type) and not content_type == "image/bmp":
                logger.info('detected image file uploaded to /images folder, sending email')
                type = 'image'
            # compose test email for .bmp image file
            elif re.search('images/', key) and content_type == "image/bmp":
                logger.info('detected test image file, sending email')
                type = 'test'
            
            # get html_text from composeHtmlText function
            html_text = composeHtmlText(bucket, key, version, type)
            # invoke function to send email
            sendSESEmail(html_text, type)
        
        except Exception:
            logger.exception('Something went wrong with main_handler: ')
            raise

# main entrypoint
if __name__ == '__main__':
    main_handler()
