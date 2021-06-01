################################################################################
##    FILE:  	main.py (ec2-instances-state-report)                          ##
##                                                                            ##
##    NOTES: 	Contains code required to create report on EC2 instance       ##
##              state per Env tag                                             ##
##                                                                            ##
##    AUTHOR:	Stepan Litsevych                                              ##
##                                                                            ##
##    Copyright 2021 - Baxter Planning Systems, Inc. All rights reserved      ##
################################################################################

# importing main modules
import os
import boto3
import logging
import datetime
import base64
import json
import requests
import pandas as pd

# importing methods for email and datetime
from time import sleep as timesleep
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from dateutil.relativedelta import relativedelta
from botocore.exceptions import ClientError

# importing testing deps
from tabulate import tabulate
from typing import Union
from pytz import timezone

# defining logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# defining global vars
S3_BUCKET = os.environ.get('S3_BUCKET') if os.environ.get('S3_BUCKET') else "cf-templates-oregon-bp"
DEFAULT_REGION = os.environ.get('DEFAULT_REGION') if os.environ.get('DEFAULT_REGION') else "us-west-2"
SES_SEND_FROM = os.environ.get('SES_SEND_FROM') if os.environ.get('SES_SEND_FROM') else "instances-state-report@baxterplanning.com"
SES_SEND_COMBINED = os.environ.get('SES_SEND_COMBINED') if os.environ.get('SES_SEND_COMBINED') else os.environ.get('LOCAL_SES_SEND_COMBINED')
SES_SEND_PRODTEST = os.environ.get('SES_SEND_PRODTEST') if os.environ.get('SES_SEND_PRODTEST') else os.environ.get('LOCAL_SES_SEND_PRODTEST')
JIRA_SECRET_NAME = os.environ['JIRA_SECRET_NAME'] if os.environ.get('JIRA_SECRET_NAME') else os.environ.get('LOCAL_JIRA_SECRET')
JIRA_USERNAME = os.environ['JIRA_USERNAME'] if os.environ.get('JIRA_USERNAME') else os.environ.get('LOCAL_JIRA_USER')

# create connection to Cost Explorer API
cost_explorer_client = boto3.client('ce', region_name='us-east-1')
# create EC2 API connection to describe instances
ec2_instances = boto3.client('ec2', region_name=DEFAULT_REGION).describe_instances(Filters=[{'Name': 'tag-key', 'Values': ['Env']}])
rds_instances = boto3.client('rds', region_name=DEFAULT_REGION).describe_db_instances()

def getJiraPasswordSecret() -> str:
    """
    Function retrieving AWS Secret

    Returns:
        str: [description]
    """
    secret_name = JIRA_SECRET_NAME
    region_name = DEFAULT_REGION

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        
    except ClientError as error:
        if error.response['Error']['Code'] == 'DecryptionFailureException':
            raise error
        elif error.response['Error']['Code'] == 'InternalServiceErrorException':
            raise error
        elif error.response['Error']['Code'] == 'InvalidParameterException':
            raise error
        elif error.response['Error']['Code'] == 'InvalidRequestException':
            raise error
        elif error.response['Error']['Code'] == 'ResourceNotFoundException':
            raise error
        
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            j = json.loads(secret)
            password = j['password']
            
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
            password = decoded_binary_secret.password 
            
        return password

def getCostUsage(instance_name: str, start: str, end: str, service: str) -> Union[float,int]:
    """
    Function retrieving unblended cost for instance using AWS CostExplorer api

    Args:
        instance_name (str): instance name to filter costs
        start (str): start date
        end (str): end date

    Returns:
        Union[float,int]: current_cost_usage (unblended cost for instance) in either float or int amounts
    """
    try:
        # define filters
        Filters = (
            {
            "And": 
                [
                    {"Not": 
                        {"Dimensions": 
                            {"Key": "RECORD_TYPE", "Values": ["Credit", "Refund", "Upfront", "Support"]}
                        }
                    },
                    {"Dimensions": 
                            {"Key": "SERVICE", "Values": ['Amazon Elastic Compute Cloud - Compute', 'EC2 - Other']}
                    },
                    {"Tags": 
                            {"Key": 'Name', "Values": [instance_name]}
                    }
                ]
            } if service == 'ec2' else 
            {
            "And": 
                [
                    {"Not": 
                        {"Dimensions": 
                            {"Key": "RECORD_TYPE", "Values": ["Credit", "Refund", "Upfront", "Support"]}
                        }
                    },
                    {"Dimensions": 
                            {"Key": "SERVICE", "Values": ['Amazon Relational Database Service']}
                    },
                    {"Tags": 
                            {"Key": 'Name', "Values": [instance_name]}
                    }
                ]
            } if service == 'rds' else None
        )
            
        
        # create Cost Explorer method to get cost for instance
        response = cost_explorer_client.get_cost_and_usage(
                        TimePeriod={
                            'Start': start,
                            'End': end
                        },
                        Granularity='MONTHLY',
                        Metrics=['UnblendedCost'],
                        GroupBy=[{"Type": "TAG", "Key": 'Name'}],
                        Filter=Filters
                    )
        
        # if cost is available save it as float amount
        if response['ResultsByTime'][0]['Groups']:
            current_cost_usage = (
                float("%0.3f" % float([amount['Metrics']['UnblendedCost']['Amount'] 
                                       for item in response['ResultsByTime'] 
                                       for amount in item['Groups']][0]))
            )
        # if cost is 0 save it as integer
        else:
            current_cost_usage = int([amount['Total']['UnblendedCost']['Amount'] for amount in response['ResultsByTime']][0])

        return current_cost_usage
            
    except Exception:
        logger.exception('Exception thrown at getCostUsage: ')
        raise       

def gatherReportData(tag: str, type: str) -> object:
    """
    Function parsing EC2 instances to gather necessary info and create a pandas dataframe

    Args:
        tag (str): Env tag to sort instances out
        type (str): tag type, Department or Env

    Returns:
        object: df (pandas dataframe)
    """
    # anonymous lambda function calculating instance age
    get_instance_age = lambda date: (datetime.datetime.today() - datetime.datetime.strptime(date, '%Y-%m-%d')).days
        
    # variable with current date in form of month names Apr, May, June, etc
    current_month = datetime.datetime.today().strftime("%B")
    
    # retrieving actual JIRA user's password
    jira_password = getJiraPasswordSecret() if type == 'Prodtest' else None
    
    # anonymous lambda function unifying mapping of tag value
    tag_mapper = lambda tagkey,passed_tags: [tag['Value'] for tag in passed_tags if tag['Key'] == tagkey][0]
    
    # define start and end dates (1st day of the current month and current day) for further getCostUsage calls
    ce_start_date = (datetime.date.today() - relativedelta()).replace(day=1).isoformat()
    ce_end_date = datetime.date.today().isoformat()
    
    # main iteration
    try:
        # create empty list for all found instances
        all_found_instances = []
        # make sure that we iterate over RDS instances
        if type == 'RDS':
            # iterate over all filtered RDS instances
            for dbinstance in rds_instances['DBInstances']:
                # empty list for instance data
                instance_info = []
                # saving current instance tags
                tags = dbinstance['TagList'] if dbinstance['TagList'] and 'TagList' in dbinstance else None
                # instance launch date (stripping time)
                instance_launch_date = str(dbinstance['InstanceCreateTime']).split(' ')[0]
                # get instance age in days by calling anonymous instanceAge function
                instance_age = get_instance_age(instance_launch_date)
                # get Name tag
                instance_name = tag_mapper('Name', tags) if 'Name' in [tag['Key'] for tag in tags] else dbinstance['DBInstanceIdentifier']
                # get Env tag
                env_tag = tag_mapper('Env', tags) if 'Env' in [tag['Key'] for tag in tags] else "n/a"
                # get Owner/CreatedBy tag
                owner_tag = tag_mapper('CreatedBy', tags) if 'CreatedBy' in [tag['Key'] for tag in tags] else "n/a"
                # get current usage cost by calling getCostUsage function
                current_cost_usage = getCostUsage(instance_name, ce_start_date, ce_end_date, service='rds')
                
                # save all retrieved values in instance_info list
                instance_info.extend(
                                    [
                                        instance_name, 
                                        dbinstance['DBInstanceClass'], 
                                        dbinstance['DBInstanceStatus'],
                                        dbinstance['Engine'],
                                        dbinstance['EngineVersion'],
                                        instance_launch_date, 
                                        instance_age,
                                        current_cost_usage,
                                        env_tag,
                                        owner_tag
                                    ]
                )
                
                # append instance_info list to the all_found_instances list making it a nested list
                if instance_info: all_found_instances.append(instance_info)
                
        elif type in ['Env', 'Department', 'Prodtest']:
            tag = tag.lower() if type in ['Prodtest', 'Env']  else tag
            # iterate over all filtered EC2 instances
            for reservation in ec2_instances['Reservations']:
                for instance in reservation['Instances']:
                    tags = instance['Tags']
                    # assign instance tag either Env or Departmend based on type
                    instance_tag = (
                        tag_mapper('Env', tags) if type in ['Prodtest', 'Env'] 
                        else tag_mapper('Department', tags) if type == 'Department' 
                        else None
                    )
                    # verify that instance tag matches tag we indicate in reports
                    if tag == instance_tag:
                        # empty list for instance data
                        instance_info = []
                        # instance launch date (stripping time)
                        instance_launch_date = str(instance['LaunchTime']).split(' ')[0]
                        # instance name based on Name tag
                        instance_name = (
                            tag_mapper('Name', tags) if 'Name' in [tag['Key'] for tag in tags] 
                            else instance['InstanceId']
                        )
                        # get current usage cost by calling getCostUsage function
                        current_cost_usage = getCostUsage(instance_name, ce_start_date, ce_end_date, service='ec2')
                        # get instance age in days by calling anonymous instanceAge function
                        instance_age = get_instance_age(instance_launch_date)
                        
                        # get Env tag
                        env_tag = (
                            tag_mapper('Env', tags) if 'Env' in [tag['Key'] for tag in tags] 
                            and type in ['Department', 'Env'] 
                            else "n/a"
                        )
                        # get Owner tag
                        owner_tag = (
                            tag_mapper('Owner', tags) if 'Owner' in [tag['Key'] for tag in tags] 
                            and type in ['Department', 'Env'] 
                            else "n/a"
                        ) 
                        # get Customers tag
                        customers_tag = (
                            tag_mapper('Customers', tags) if 'Customers' in [tag['Key'] for tag in tags]
                            else " "
                        ) 
                                
                        # Jira ticket value based on JIRA tag
                        sow_ticket = (
                            tag_mapper('JIRA', tags) if 'JIRA' in [tag['Key'] for tag in tags] 
                            and type == 'Prodtest' 
                            else "n/a"
                        )
                        # Quering JIRA API to get ticket status and resolution status
                        if sow_ticket != 'n/a':
                            try:
                                timesleep(1)
                                # calling API to get status
                                if JIRA_USERNAME and jira_password is not None:
                                    response = requests.get(f'https://jira.baxterplanning.com/rest/api/2/issue/{sow_ticket}?fields=status', auth=(JIRA_USERNAME, jira_password))
                                    response.raise_for_status()
                                    if response.status_code == 200:
                                        # saving JSON data
                                        response_dict = json.loads(response.text)
                                        if 'fields' in response_dict:
                                            # assigning ticket's status
                                            ticket_status = response_dict['fields']['status']['name']
                                            # assigning ticket's resolution status
                                            ticket_resolution_status = response_dict['fields']['status']['statusCategory']['name']
                                        else:
                                            logger.info(f'cannot get fields in response:{sow_ticket}')
                                            ticket_status, ticket_resolution_status = 'n/a', 'n/a'
                                    elif response.status_code != 200:
                                        logger.info(f'cannot get ticket:{sow_ticket};status_code:{response.status_code}')
                                        ticket_status, ticket_resolution_status = 'n/a', 'n/a'
                                else:
                                    print('cannot authenticate to JIRA:{sow_ticket}; username:{JIRA_USERNAME}, password:{jira_password}')
                                    ticket_status, ticket_resolution_status = 'n/a', 'n/a'
                                    
                            except requests.exceptions.RequestException as err:
                                logger.error("Requests Exception", err)
                                ticket_status, ticket_resolution_status = 'n/a', 'n/a'
                                break
                            except requests.exceptions.HTTPError as errh:
                                logger.error("HTTP Error:", errh)
                                ticket_status, ticket_resolution_status = 'n/a', 'n/a'
                                break
                            except requests.exceptions.ConnectionError as errc:
                                logger.error("Connection Error:", errc)
                                ticket_status, ticket_resolution_status = 'n/a', 'n/a'
                                break
                            except requests.exceptions.Timeout as errt:
                                logger.error("Timeout Error:", errt)
                                ticket_status, ticket_resolution_status = 'n/a', 'n/a'
                                break
                                
                        else:
                            # for empty JIRA values populate 'n/a' value
                            ticket_status, ticket_resolution_status = 'n/a', 'n/a'
                        
                        # save all retrieved values in instance_info list
                        (instance_info.extend(
                                [
                                instance_name, 
                                instance['InstanceId'], 
                                instance['InstanceType'], 
                                instance['State']['Name'],
                                instance_launch_date, 
                                instance_age,
                                current_cost_usage,
                                env_tag,
                                owner_tag,
                                customers_tag
                                ]
                            ) if type in ['Department', 'Env'] 
                        else instance_info.extend(
                                [
                                instance_name, 
                                instance['InstanceId'], 
                                instance['InstanceType'], 
                                instance['State']['Name'],
                                instance_launch_date, 
                                instance_age,
                                current_cost_usage,
                                sow_ticket,
                                ticket_status,
                                ticket_resolution_status,
                                customers_tag
                                ]
                            ) if type == 'Prodtest' 
                        else None
                        )
                            
                        # append instance_info list to the all_found_instances list making it a nested list
                        if instance_info: all_found_instances.append(instance_info)
        
        # proceed to submitting all found instances data to pandas dataframe
        if all_found_instances:
            columns = (
                ['Name', 'ID', 'Type', 'State', 'Launch Date', 'Age (days)', 'Cost (' + current_month + ')', 'JIRA', 'Status', 'Resolution', 'Customer'] if type == 'Prodtest' 
                else ['Name', 'ID', 'Type', 'State', 'Launch Date', 'Age (days)', 'Cost (' + current_month + ')', 'Env', 'Created By', 'Customer'] if type in ['Department', 'Env'] 
                else ['Name', 'Type', 'State', 'Engine', 'Version', 'Launch Date', 'Age (days)', 'Cost (' + current_month + ')', 'Env', 'Created By'] if type == 'RDS' 
                else logger.error('cannot evaluate type')
            )
            # create pandas dataframe using all_found_instances list with nested lists and defined columns
            df = pd.DataFrame(data=all_found_instances, columns=columns) 
            # set index to Name column
            df.set_index('Name', inplace=True)
            # sort all values by 'Age (days)' column
            df.sort_values(by=['Age (days)', 'Name'], ascending=[True, True], inplace=True)
            # reset numeration
            df.reset_index(inplace=True)
            # correctly fill zero values 
            df['Cost (' + current_month + ')'].fillna(0, inplace=True)
            # start index with 1 instead of 0
            df.index = df.index + 1
            # return df object
            return df
        
        else:
            logger.error('all_found_instances empty')
            raise Exception
    
    except Exception:
        logger.exception('Exception thrown at gatherReportData: ')
        raise
    
# Function generating excel report using pd.ExcelWriter
def generateExcelReport(reports: list) -> object:
    
    """
    Function generating Excel report using pandas dataframe
    
    Args:
        reports (list): list of reports with pandas dataframe.
    Returns:
        object: report_file (excel workbook)
    """
    # save current date
    current_date = datetime.datetime.today().strftime('%Y-%m-%d')
    # predefined value for report file name
    report_file = f'ec2-instances-state-report.{current_date}.xlsx'
        
    os.chdir('/tmp')

    # main iteration
    try:
        pd.io.formats.excel.header_style = None
        # create excel writer object using report file name and xlsxwriter engine
        writer = pd.ExcelWriter(report_file, engine='xlsxwriter')
        # create workbook
        workbook = writer.book
        
        # add formatting options
        format = workbook.add_format()
        format.set_align('center')
        format.set_align('vcenter')
        
        # iterate over previously generated reports
        for report in reports:
            logger.info(f"creating excel report: {report['Name']}")
            dataframe = report['Data']
            # append dataframe data to excel file
            dataframe.to_excel(writer, sheet_name=report['Name'])
            worksheet = writer.sheets[report['Name']]
            
            # function adjusting columnbs widths
            def get_col_widths(dataframe: object) -> int:
                idx_max = max([len(str(s)) for s in dataframe.index.values] + [len(str(dataframe.index.name))])
                return [idx_max] + [max([len(str(s)) for s in dataframe[col].values] + [len(col)]) for col in dataframe.columns]
            
            link_format = workbook.add_format({
                        'align':    'center',
                        'valign':   'vcenter',
                        'bg_color': 'white',
                        'font_color': 'blue',
                        'pattern': 0
                    })
            
            name_format = workbook.add_format({
                        'align':    'center',
                        'valign':   'vcenter',
                        'bg_color': 'white',
                        'bold': True
                    })
            
            state_format = lambda color: workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bg_color': color })
            
            if report['Name'] != 'RDS instances':    
                
                for index, value in enumerate(dataframe['ID'].values, start=2):
                    worksheet.write_url("C%d" % index, url="https://us-west-2.console.aws.amazon.com/ec2/v2/home?region=us-west-2#Instances:instanceId=%s" % value, cell_format=link_format, string=value)
                
                for index, value in enumerate(dataframe['Name'].values, start=2):
                    worksheet.write_string("B%d" % index, string=value, cell_format=name_format)
                    
                for index, value in enumerate(dataframe['State'].values, start=2):
                    if value == 'stopped':
                        worksheet.write_string("E%d" % index, string=value, cell_format=state_format('red'))
                    elif value == 'running':
                        worksheet.write_string("E%d" % index, string=value, cell_format=state_format('green'))
                    elif value == 'terminated':
                        worksheet.write_string("E%d" % index, string=value, cell_format=state_format('gray'))
                    else:
                        worksheet.write_string("E%d" % index, string=value, cell_format=state_format('white'))
                        
                if report['Name'] == 'Prodtest instances':
                    for index, value in enumerate(dataframe['JIRA'].values, start=2):
                        if value != 'n/a':
                            worksheet.write_url("I%d" % index, url="https://jira.baxterplanning.com/browse/%s" % value, cell_format=link_format, string=value)
                        
            elif report['Name'] == 'RDS instances':
                for index, value in enumerate(dataframe['Name'].values, start=2):
                    worksheet.write_url("B%d" % index, url="https://us-west-2.console.aws.amazon.com/rds/home?region=us-west-2#database:id=%s;is-cluster=false" % value, cell_format=link_format, string=value)

                for index, value in enumerate(dataframe['State'].values, start=2):
                    if value == 'stopped':
                        worksheet.write_string("D%d" % index, string=value, cell_format=state_format('red'))
                    elif value == 'available':
                        worksheet.write_string("D%d" % index, string=value, cell_format=state_format('green'))
                    else:
                        worksheet.write_string("D%d" % index, string=value, cell_format=state_format('white'))
                        
            for i, width in enumerate(get_col_widths(dataframe)):
                worksheet.set_column(i, i, int(width + 2), format)
        
        # save changes in file
        writer.save()
        
        # upload excel file to S3 bucket
        if S3_BUCKET:
            s3 = boto3.client('s3')
            s3.upload_file(report_file, S3_BUCKET, "ec2-instances-state-report/reports/%s" % (report_file))
        
        elif not S3_BUCKET:
            logger.info('S3 bucket not set')

        return report_file
    
    except Exception:
        logger.exception('Exception thrown at generateExcel: ')
        raise

def sendReport(report_file: object, recipients: str) -> None:
    """
    Function sending email using SES

    Args:
        report_file (object): Excel workbook object received from generateExcelReport function.
        recipients (str): list of email recipients.
    """    

    try:
        # get current time in US/Central timezone
        central_time = datetime.datetime.now().astimezone(timezone("US/Central")).strftime('%Y-%m-%d %H:%M:%S')
        current_month = datetime.datetime.today().strftime("%Y/%m/%d")
        # Send the excel report via email using SES
        if recipients:
            # define email options
            msg = MIMEMultipart()
            msg['From'] = SES_SEND_FROM
            msg['To'] = recipients
            msg['Date'] = formatdate(localtime=True)
            if recipients == SES_SEND_PRODTEST:
                msg['Subject'] = f'Prodtest instances state report ({current_month})'
            elif recipients == SES_SEND_COMBINED:
                msg['Subject'] = f'AWS dev/ops/uat/rds instances state report ({current_month})'

            # create html_text for email body contents
            html_text = f"""
                <html>
                    <head></head>
                        <body>
                            <br>
                            Kindly find report attached below (report file: {report_file})
                            <br><br>
                            ----------------------
                            <br>
                            <i>generated on {central_time} (US/Central time)</i>
                            <br>
                            <i>generated in {DEFAULT_REGION} AWS region</i>
                            <br>
                            <i>generated by ec2-instances-state-report function</i>
                            <br>
                            ----------------------
                            <br>
                            <img src="https://baxterplanning.com/wp-content/uploads/2019/08/BXPL_300x80.png" alt="baxter planning">
                            <br>
                        </body>
                </html>
                """
            msg.attach(MIMEText(html_text, 'html'))

            # attach excel report file to email
            with open(report_file, "rb") as file:
                part = MIMEApplication(file.read(), Name=report_file)

            part['Content-Disposition'] = 'attachment; filename="%s"' % (report_file)
            msg.attach(part)

            # create SES connection and use send_raw_email method to send email message
            ses = boto3.client('ses', region_name=DEFAULT_REGION)
            ses.send_raw_email(
                Source=msg['From'],
                Destinations=recipients.split(","),
                RawMessage={'Data': msg.as_string()}
            )
        
        elif not recipients:
            logger.error('recipients are empty, skipping sendReport')
    
    except Exception:
        logger.exception('Exception thrown at sendReport: ')
        raise

def test_handler(event: object = [], context: object = []) -> None:
    """
    Test Lambda handler outputting dataframe using tabulate
    """
    try:
        # gather data on instances and print it using tabulate in terminal; for local debugging
        for tag in ['Development', 'Operations', 'UAT', 'RDS', 'Prodtest']:
            print(f'Gathering data for {tag} report')
            type = 'Env' if tag == 'UAT' else tag if tag in ['RDS', 'Prodtest'] else 'Department' if tag in ['Development', 'Operations'] else None
            dataframe = gatherReportData(tag, type)
            print(tabulate(dataframe, headers = 'keys', tablefmt = 'psql'))
    
    except Exception:
        print('Exception thrown at test_handler: ')
        raise

def main_handler(event: object, context: object) -> None:
    
    """
    Main Lambda handler processing event and context objects
    """
    try:
        # empty list for storing reports
        reports = []
        
        # iterate over predefined Env tags to create reports for each of them exclusively
        for tag in ['Development', 'Operations', 'UAT', 'RDS', 'Prodtest']:
            
            # define type var based on a tag being processed
            type = 'Env' if tag == 'UAT' else tag if tag in ['RDS', 'Prodtest'] else 'Department' if tag in ['Development', 'Operations'] else None
            
            logger.info(f'Gathering data for {tag} report')
            # create dataframe for tag and based on its type
            df = gatherReportData(tag, type)
            
            # append dataframe to reports lists
            reports.append({'Name': tag + ' instances', 'Data': df})
            
        # send reports to specific email lists 
        for email_list in [{'Combined': SES_SEND_COMBINED}, {'Prodtest': SES_SEND_PRODTEST}]:
            
            # define what reports are getting sent based on email list we're sending to
            reports = reports[-1:] if 'Prodtest' in email_list else reports if 'Combined' in email_list else None
                        
            # generate excel report file based on reports list
            logger.info('Generating report')
            # create report file based on reports
            report_file = generateExcelReport(reports)
        
            # send combined report to list of recipients
            logger.info(f"Sending report to {list(email_list.keys())[0]} list")
            # send report file to the specified email list
            sendReport(report_file, recipients=list(email_list.values())[0])
            
        # finish sequence 
        logger.info('Report generated and sent')
        # output used and remaining time
        logger.info(f'Used time: {"{:.3f}".format(int(300.000) - (int(context.get_remaining_time_in_millis()) / 1000))} seconds || ' \
                    f'Remaining time: {str((int(context.get_remaining_time_in_millis()) / 1000))} seconds')
        return "Report Generated"
    
    except Exception:
        logger.exception('Exception thrown at main_handler: ')
        raise

# main entrypoint; change to test_handler for local debugging
if __name__ == '__main__':
    main_handler()
    # test_handler()