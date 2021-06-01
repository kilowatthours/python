################################################################################
##    FILE:  	lambda.py (aws-cost-explorer-report)                          ##
##                                                                            ##
##    NOTES: 	A script to generate CostExplorer excel graphs                ##
##                                                                            ##
##    AUTHOR:	Stepan Litsevych                                              ##
##                                                                            ##
##    Copyright 2020 - Baxter Planning Systems, Inc. All rights reserved      ##
################################################################################

#!/usr/bin/env python

# importing modules and packages
from __future__ import print_function

import os
import sys
import re

# required to load modules from vendored subfolder (for clean development env)
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "./vendored"))

import boto3
import datetime
import logging
import pandas as pd

from dateutil.relativedelta import relativedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate

# assigning variables from global vars
SES_REGION = os.environ.get('SES_REGION')
if not SES_REGION: SES_REGION = "us-west-2"

ACCOUNT_LABEL = os.environ.get('ACCOUNT_LABEL')
if not ACCOUNT_LABEL: ACCOUNT_LABEL = 'Email'

INC_SUPPORT = os.environ.get('INC_SUPPORT')
if not INC_SUPPORT: INC_SUPPORT = True

# internal function to evaluate a passed global variable and convert it to bool
def evaluateVar(var: str = None):
    """
    internal function to evaluate a passed global variable and convert it to bool or int

    Args:
        var (str, optional): evaluates value of a variable. Defaults to None.

    Returns:
        var
    """    
    var = True if var == 'true' else False if var == 'false' else False if var == '' else int(var) if var != '' else print(f"cannot evaluate var: {var}")
    return var

## For local tests
# CurrentMonth = 'false'
# LastMonthOnly = 'true'
# ExactMonth = ''
# ExactYear = ''
# LastMonthsPeriod = '2'

# CurrentMonth = evaluateVar(CurrentMonth)
# LastMonthOnly = evaluateVar(LastMonthOnly)
# ExactMonth = evaluateVar(ExactMonth)
# ExactYear = evaluateVar(ExactYear)
# LastMonthsPeriod = evaluateVar(LastMonthsPeriod)

CurrentMonth = evaluateVar(os.environ.get('CURRENT_MONTH'))
LastMonthOnly = evaluateVar(os.environ.get('LAST_MONTH_ONLY'))
ExactMonth = evaluateVar(os.environ.get('EXACT_MONTH'))
ExactYear = evaluateVar(os.environ.get('EXACT_YEAR'))
LastMonthsPeriod = evaluateVar(os.environ.get('LAST_MONTHS_PERIOD'))

class CostExplorer:
    """
    Retrieves BillingInfo checks from CostExplorer API
    >>> costexplorer = CostExplorer()
    >>> costexplorer.addReport(GroupBy=[{"Type": "DIMENSION","Key": "SERVICE"}])
    >>> costexplorer.generateExcel()
    
    """

    def __init__(self, CurrentMonth: bool = False, LastMonthOnly: bool = True, ExactMonth: int = 0, ExactYear: int = 0):
        """
        Initialization method

        Args:
            CurrentMonth (bool, optional): defines if a current month (unfinished) is included in report or not. Defaults to False.
            LastMonthOnly (bool, optional): defines if report evaluates last 12 months or only a previous (completed; last) month. Defaults to True.
            ExactMonth (int, optional): being used to retrieve reports for specifed months (within last 12 months period). Defaults to 0.
            ExactYear (int, optional): being used to retrieve reports for specifed months (within last 12 months period). Defaults to 0.
        """        
        # Array of reports ready to be output to Excel.
        self.reports = []
        self.client = boto3.client('ce', region_name='us-east-1')
        self.end = datetime.date.today().replace(day=1)
        self.riend = datetime.date.today()
        
        # 1st day of month 11 months ago
        self.ristart = (datetime.date.today() - relativedelta(months=+11)).replace(day=1)
        # 1st day of month 6 months ago, so RI util has savings values
        self.sixmonth = (datetime.date.today() - relativedelta(months=+6)).replace(day=1)
                
        if CurrentMonth:
            self.end = self.riend

        if LastMonthOnly:
            # 1st day of a previous month (a month ago)
            self.start = (datetime.date.today() - relativedelta(months=+1)).replace(day=1)
        elif not LastMonthOnly:
            # starting of a 1st day of a month 12 months ago
            self.start = (datetime.date.today() - relativedelta(months=+12)).replace(day=1)
        
        # check only specified year and month
        if ExactMonth and ExactYear:
            print('Creating report for exact month and year')
            LastMonthOnly = False
            CurrentMonth = False
            
            self.start = (datetime.date.today() - relativedelta(year=int(ExactYear), month=int(ExactMonth))).replace(day=1)
            self.end = (self.start + relativedelta(months=+1))
            
        # generate for last {n} months
        if LastMonthsPeriod:
            print('Creating report for last months range')
            LastMonthOnly = False
            CurrentMonth = False
            ExactMonth = False
            ExactYear = False
            
            self.start = (datetime.date.today() - relativedelta(months=+LastMonthsPeriod)).replace(day=1)
            self.end = datetime.date.today().replace(day=1)
            
            print(self.start)
            print(self.end)

        # get account names
        try:
            self.accounts = self.getAccounts()
        except:
            logging.exception("Getting Account names failed")
            self.accounts = {}

    def getAccounts(self) -> None:
        """
        Iterate over account using boto3 API
        
        Args:
            None

        Returns:
            None
        """        
        accounts = {}
        client = boto3.client('organizations', region_name='us-east-1')
        paginator = client.get_paginator('list_accounts')
        response_iterator = paginator.paginate()
        for response in response_iterator:
            for acc in response['Accounts']:
                accounts[acc['Id']] = acc
        return accounts
    
    def evaluateMonth(self, date: str = '', exactmonth: str = '') -> str:
        """
        Retrieve month in word format from numeric dates
        
        Args:
            date: str
            exactmonth: str
        Returns:
            month -> str
        """   
        month = None
        
        if exactmonth:
            if re.match('^\d$', exactmonth):
                exactmonth = "0" + exactmonth
            elif re.match(r"1[0-2]", exactmonth):
                pass
        
        # convert dates into names of months
        if date or exactmonth:
            if "-01-" in date or "01" in exactmonth: month = "January"
            elif "-02-" in date or "02" in exactmonth: month = "February"
            elif "-03-" in date or "03" in exactmonth: month = "March"
            elif "-04-" in date or "04" in exactmonth: month = "April"
            elif "-05-" in date or "05" in exactmonth: month = "May"
            elif "-06-" in date or "06" in exactmonth: month = "June"
            elif "-07-" in date or "07" in exactmonth: month = "July"
            elif "-08-" in date or "08" in exactmonth: month = "August"
            elif "-09-" in date or "09" in exactmonth: month = "September"
            elif "-10-" in date or "10" in exactmonth: month = "October"
            elif "-11-" in date or "11" in exactmonth: month = "November"
            elif "-12-" in date or "12" in exactmonth: month = "December"
            else: month = "Category"
            
        return month
    
    # Function generating RI (Reserved Instance) reports
    # Call with Savings True to get Utilization report in dollar savings
    def addRiReport(self, Name: str = 'RICoverage', 
                    Savings: bool = False, 
                    PaymentOption: str = 'PARTIAL_UPFRONT',
                    Service: str = 'Amazon Elastic Compute Cloud - Compute') -> None:
        
        """
        Generate RI (Reserved Instance) report
        
        Args:
            Name: str - name of the report (random; default: "RICoverage")
            Savings: bool - include Savings Plan (default: "False")
            PaymentOption: str - indicate supported payment options (default: "PARTIAL_UPFRONT")
            Service: str - output costs for specific services (default: "Amazon Elastic Compute Cloud - Compute")
            
        Returns:
            None
        """   
        
        type = 'chart'  # other type is "table"
        df = None
        if Name == "RICoverage":
            results = []
            # call CostExplorer API to get reservation coverage
            response = self.client.get_reservation_coverage(
                TimePeriod={
                    'Start': self.ristart.isoformat(),
                    'End': self.riend.isoformat()
                },
                Granularity='MONTHLY'
            )
            results.extend(response['CoveragesByTime'])
            while 'nextToken' in response:
                nextToken = response['nextToken']
                response = self.client.get_reservation_coverage(
                    TimePeriod={
                        'Start': self.ristart.isoformat(),
                        'End': self.riend.isoformat()
                    },
                    Granularity='MONTHLY',
                    NextPageToken=nextToken
                )
                results.extend(response['CoveragesByTime'])
                if 'nextToken' in response:
                    nextToken = response['nextToken']
                else:
                    nextToken = False
            
            # create rows to pass data into pandas dataframe
            rows = []
            for v in results:
                date = str(v['TimePeriod']['Start'])
                month = self.evaluateMonth(date=date)
                row = {'Date': str(month)}
                row.update({'Coverage(%)': float("%0.2f" % float(v['Total']['CoverageHours']['CoverageHoursPercentage']))})
                rows.append(row)

            # create DataFrame object and change its properties
            df = pd.DataFrame(rows)
            df.set_index("Date", inplace=True)
            df = df.fillna(0.0)
            df = df.T
            
        elif Name in ['RIUtilization', 'RIUtilizationSavings']:
            # Only Six month to support savings
            results = []
            # call CostExplorer API to get reservation utilization
            response = self.client.get_reservation_utilization(
                TimePeriod={
                    'Start': self.sixmonth.isoformat(),
                    'End': self.riend.isoformat()
                },
                Granularity='MONTHLY'
            )
            results.extend(response['UtilizationsByTime'])
            while 'nextToken' in response:
                nextToken = response['nextToken']
                response = self.client.get_reservation_utilization(
                    TimePeriod={
                        'Start': self.sixmonth.isoformat(),
                        'End': self.riend.isoformat()
                    },
                    Granularity='MONTHLY',
                    NextPageToken=nextToken
                )
                results.extend(response['UtilizationsByTime'])
                if 'nextToken' in response:
                    nextToken = response['nextToken']
                else:
                    nextToken = False

            # create rows to pass data into pandas dataframe
            rows = []
            if results:
                for v in results:
                    date = str(v['TimePeriod']['Start'])
                    month = self.evaluateMonth(date=date)
                    
                    row = {'date': str(month)}
                    if Savings:
                        row.update({'Savings($)': float("%0.2f" % float(v['Total']['NetRISavings']))})
                    else:
                        row.update({'Utilization(%)': float("%0.2f" % float(v['Total']['UtilizationPercentage']))})                        
                    rows.append(row)

                # create DataFrame object and change its properties for chart type
                df = pd.DataFrame(rows)
                df.set_index("date", inplace=True)
                df = df.fillna(0.0)
                df = df.T
                type = 'chart'
            else:
                # create DataFrame object and change its properties for table type
                df = pd.DataFrame(rows)
                type = 'table'  # Dont try chart empty result
                
        elif Name == 'RIRecommendation':
            results = []
            # call CostExplorer API to get reservation purchase recommendations
            response = self.client.get_reservation_purchase_recommendation(
                # AccountId='string', May use for Linked view
                LookbackPeriodInDays='SIXTY_DAYS',
                TermInYears='ONE_YEAR',
                PaymentOption=PaymentOption,
                Service=Service
            )
            results.extend(response['Recommendations'])
            while 'nextToken' in response:
                nextToken = response['nextToken']
                response = self.client.get_reservation_purchase_recommendation(
                    # AccountId='string', May use for Linked view
                    LookbackPeriodInDays='SIXTY_DAYS',
                    TermInYears='ONE_YEAR',
                    PaymentOption=PaymentOption,
                    Service=Service,
                    NextPageToken=nextToken
                )
                results.extend(response['Recommendations'])
                if 'nextToken' in response:
                    nextToken = response['nextToken']
                else:
                    nextToken = False

            # create rows to pass data into pandas dataframe
            rows = []
            for i in results:
                for v in i['RecommendationDetails']:
                    row = v['InstanceDetails'][list(v['InstanceDetails'].keys())[0]]
                    row['Recommended'] = v['RecommendedNumberOfInstancesToPurchase']
                    row['Minimum'] = float("%0.2f" % float(v['MinimumNumberOfInstancesUsedPerHour']))
                    row['Maximum'] = float("%0.2f" % float(v['MaximumNumberOfInstancesUsedPerHour']))
                    row['Savings'] = float("%0.2f" % float(v['EstimatedMonthlySavingsAmount']))
                    row['OnDemand'] = float("%0.2f" % float(v['EstimatedMonthlyOnDemandCost']))
                    row['BreakEvenIn'] = float("%0.2f" % float(v['EstimatedBreakEvenInMonths']))
                    row['UpfrontCost'] = float("%0.2f" % float(v['UpfrontCost']))
                    row['MonthlyCost'] = float("%0.2f" % float(v['RecurringStandardMonthlyCost']))
                    rows.append(row)

            # create DataFrame object and change its properties for table type
            df = pd.DataFrame(rows)
            df = df.fillna(0.0)
            type = 'table'  # "chart" is not available here
            
        # add all generated reports to the list of reports
        self.reports.append({'Name': Name, 'Data': df, 'Type': type})

    # function generating standard CostExplorer reports
    def addReport(self, Name: str = "Default",
                  GroupBy: list = [{"Type": "DIMENSION", "Key": "SERVICE"}, ],
                  Style: str = 'Total',
                  FilterByServices: list = None,
                  TagKey: str = None,
                  TagValueFilter: list = None,
                  NoCredits: bool = True, 
                  CreditsOnly: bool = False, 
                  RefundOnly: bool = False,
                  UpfrontOnly: bool = False, 
                  TypeExcel: str = 'chart',
                  IncSupport: bool = False,
                  KeySplit: bool = False,
                  CostCategoryCalculated: bool = False) -> None:
        
        """
        Generate standard CostExplorer report
        
        Args:
            Name: str - name of the report (random; default: "Default")
            GroupBy: list - indicate GroupBy DIMENSION parameter (SERVICE, LINKED_ACCOUNT, REGION, etc;
                            default: "[{"Type": "DIMENSION", "Key": "SERVICE"}, ]")
            Style: str - choose to either output "Total" costs or "Change" style to output changes 
                         comparing with previous months (default: "Total")
            FilterByServices: list - set Filters by certain services (default: None)
            TagKey: str - indicate tag key parameter to filter over GroupBy results (default: None)
            TagValueFilter: list - indicate list of tag values to filter with TagKey (default: None)
            NoCredits: bool - disregard costs for Credits category (default: "True")
            CreditsOnly: bool - include only costs for Credits (default: "False")
            RefundOnly: bool - include only Refund costs (default: "False")
            UpfrontOnly: bool - include only Upfront costss (default: "False")
            IncSupport: bool - include costs for AWS Support (default: "False")
            TypeExcel: str - choose type "chart" or "table" (default: "chart")
            KeySplit: bool - parameter is required for more correct output of reports of "Type": "TAG" and 
                             "Type": "COST_CATEGORY" parameter (default: "False")
            CostCategoryCalculated: bool - enable or disable calculation of percents for certain Cost Categories containing
                                           list of Customers (default: "False")
            
        Returns:
            None
        """
        type = 'chart'
        
        if TypeExcel == 'table':
            type = 'table'
            
        results = []
        if not NoCredits:
            response = self.client.get_cost_and_usage(
                TimePeriod={
                    'Start': self.start.isoformat(),
                    'End': self.end.isoformat()
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost',],
                GroupBy=GroupBy
            )
        else:
            # create filters and dimensions required for getting cost and usage
            Filter = {"And": []}

            Dimensions = {"Not": {"Dimensions": {"Key": "RECORD_TYPE", "Values": ["Credit", "Refund", "Upfront", "Support"]}}}
            
            # If global set for including support, we dont exclude it
            if IncSupport:
                Dimensions = {"Not": {"Dimensions": {
                    "Key": "RECORD_TYPE", "Values": ["Credit", "Refund", "Upfront"]}}}           
            if CreditsOnly:
                Dimensions = {"Dimensions": {
                    "Key": "RECORD_TYPE", "Values": ["Credit", ]}}        
            if RefundOnly:
                Dimensions = {"Dimensions": {
                    "Key": "RECORD_TYPE", "Values": ["Refund", ]}}
            if UpfrontOnly:
                Dimensions = {"Dimensions": {
                    "Key": "RECORD_TYPE", "Values": ["Upfront", ]}}
            
            # tagValues = None
            FilterDimensions = None
            tag_values_list = []
            
            if TagKey:
                for value in TagValueFilter:
                    get_tags = self.client.get_tags(
                        SearchString=value,
                        TimePeriod={
                            'Start': self.start.isoformat(),
                            'End': datetime.date.today().isoformat()
                        },
                        TagKey=TagKey
                    )
                    tag_values_list.extend(get_tags['Tags'])
            
            if not TagKey and FilterByServices:
                FilterDimensions = {"Dimensions": {"Key": "SERVICE", "Values": FilterByServices}}
                Filter["And"].append(Dimensions)
                Filter["And"].append(FilterDimensions)

            elif TagKey and not FilterByServices:
                Filter["And"].append(Dimensions)
                if len(tag_values_list) > 0:
                    Tags = {"Tags": {"Key": TagKey,
                                     "Values": tag_values_list}}
                    Filter["And"].append(Tags)
                        
            elif TagKey and FilterByServices:
                FilterDimensions = {"Dimensions": {"Key": "SERVICE", "Values": FilterByServices}}
                Filter["And"].append(Dimensions)
                if len(tag_values_list) > 0:
                    Tags = {"Tags": {"Key": TagKey,
                                     "Values": tag_values_list}}
                    Filter["And"].append(Tags)
                    Filter["And"].append(FilterDimensions)
                        
            elif not TagKey and not FilterByServices:
                Filter = Dimensions.copy()
            
            # Call CostExplorer API to get cost and usage using previously determined filters and dimensions
            response = self.client.get_cost_and_usage(
                TimePeriod={
                    'Start': self.start.isoformat(),
                    'End': self.end.isoformat()
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost',],
                GroupBy=GroupBy,
                Filter=Filter
            )

        if response:
            results.extend(response['ResultsByTime'])

            while 'nextToken' in response:
                nextToken = response['nextToken']
                response = self.client.get_cost_and_usage(
                    TimePeriod={
                        'Start': self.start.isoformat(),
                        'End': self.end.isoformat()
                    },
                    Granularity='MONTHLY',
                    Metrics=['UnblendedCost',],
                    GroupBy=GroupBy,
                    NextPageToken=nextToken
                )

                results.extend(response['ResultsByTime'])
                if 'nextToken' in response:
                    nextToken = response['nextToken']
                else:
                    nextToken = False
        
        # create rows to pass into pandas dataframe
        rows = []
        amount = ''
        date = ''
        
        for v in results:
                
            date = v['TimePeriod']['Start']
            row = {'date': str(date)}
            
            # calculate usage percents for Customers (will be applied if report has CostCategoryCalculated bool set to True) 
            if CostCategoryCalculated:
                KeySplit = True
                percent80 = ['SCHN', 'BD']
                percent75 = []
                percent66 = []
                percent50 = ['AVA', 'ARI', 'RVBD', 'MDI', 'NVDA', 'VZN', 'VZT', 'VZO', 'COH', 'CUC', 'NET', 'TRI', 'VZW', 'NOK', 'CIE', 'CST', 'SMIT']
                percent33 = ['BIO', 'BRCD', 'NWAZ', 'TD', 'CIT', 'LSC', 'NX', 'QTM', 'BMS', 'VGY']
                percent25 = ['AVT', 'F5N', 'GIMO', 'PLS']
                percent20 = ['CRAY', 'JJDC', 'MDC', 'PAN', 'DLR']
                percent16 = ['DSL', 'PURE', 'SNE', 'TFI']
                
                for i in v['Groups']:
                    key = str(i['Keys'][0].split('$')[1])
                    amount = float(i['Metrics']['UnblendedCost']['Amount'])
                    
                    if key == '':
                        key = str("NoTag" + i['Keys'][0].split('$')[0])
                    elif key.find("percents"):
                        key = str(key.split('--')[0].rstrip())
                    else:
                        pass
                                            
                    if key in percent80:
                        calculated_amount = float(amount * 0.8)
                    elif key in percent75:
                        calculated_amount = float(amount * 0.75)
                    elif key in percent66:
                        calculated_amount = float(amount * 0.66)
                    elif key in percent50:
                        calculated_amount = float(amount * 0.5)
                    elif key in percent33:
                        calculated_amount = float(amount * 0.33)
                    elif key in percent25:
                        calculated_amount = float(amount * 0.25)
                    elif key in percent20:
                        calculated_amount = float(amount * 0.2)
                    elif key in percent16:
                        calculated_amount = float(amount * 0.16)
                    else:
                        calculated_amount = float(amount)
                        
                    amount = float("%0.3f" % float(calculated_amount))
                    row.update({str(key): float(amount)})
                    
                rows.append(row)
                
            else:
                for i in v['Groups']:
                    if KeySplit:
                        key = i['Keys'][0].split('$')[1]
                        if key == '':
                            key = "NoTag" + i['Keys'][0].split('$')[0]
                    else:
                        key = i['Keys'][0]
                        
                    if key in self.accounts:
                        key = self.accounts[key][ACCOUNT_LABEL]
                    
                    amount = float("%0.3f" % float(i['Metrics']['UnblendedCost']['Amount']))
                    row.update({str(key): float(amount)})
                    
                if not v['Groups']:
                    amount = float("%0.3f" % float(v['Total']['UnblendedCost']['Amount']))
                    row.update({'Total': float(amount)})
                rows.append(row)
        
        # create dataframe object and change its properties
        df = pd.DataFrame(rows)
        df.set_index("date", inplace=True)
        df = df.fillna(0.0)

        if Style == 'Change':
            dfc = df.copy()
            lastindex = None
            for index, row in df.iterrows():
                if lastindex:
                    for i in row.index:
                        try:
                            df.at[index, i] = dfc.at[index, i] - \
                                dfc.at[lastindex, i]
                        except:
                            logging.exception("Error")
                            df.at[index, i] = 0
                lastindex = index
                
        df = df.T
        
        for column in df.columns:
            df = df.sort_values(column, ascending=False)
            date_month = lambda x: self.evaluateMonth(date=x)
            df.rename(columns={column: date_month(column)}, inplace=True)
        
        # add all generated reports to the list of reports
        self.reports.append({'Name': Name, 'Data': df, 'Type': type})

    # Function generating excel report using pd.ExcelWriter
    def generateExcel(self) -> None:
        
        """
        Create a Pandas Excel writer using XlsxWriter as the engine, sends report to email and saves to S3.
        
        Args:
            None
        Returns:
            None
        """
        filename = None
        today = datetime.date.today()
        currentMonth = today.month
        lastMonth = (today.replace(day=1) - datetime.timedelta(days=1)).month
        date_month = lambda month_to_check: self.evaluateMonth(exactmonth=str(month_to_check))
        
        if LastMonthOnly and CurrentMonth and not ExactMonth and not ExactYear and not LastMonthsPeriod:
            filename = 'ce_report.last_and_current_months.%s_%s.created_on_%s.xlsx' % (date_month(lastMonth).lower(), date_month(currentMonth).lower(), today)
        elif LastMonthOnly and not CurrentMonth and not ExactMonth and not ExactYear and not LastMonthsPeriod:
            filename = 'ce_report.last_month.%s.created_on_%s.xlsx' % (date_month(lastMonth).lower(),today)
        elif not LastMonthOnly and not CurrentMonth and not ExactMonth and not ExactYear and not LastMonthsPeriod:
            filename = 'cost_explorer_report.last_12_months.created_on_%s.xlsx' % (today)
        elif not LastMonthOnly and CurrentMonth and not ExactMonth and not ExactYear and not LastMonthsPeriod:
            filename = 'cost_explorer_report.last_12_and_current_months.created_on_%s.xlsx' % (today)
        elif ExactMonth and ExactYear:
            filename = 'cost_explorer_report.for_%s_%s.created_on_%s.xlsx' % (ExactYear, ExactMonth, today)
        elif LastMonthsPeriod:
            filename = 'cost_explorer_report.for_last_%s_months.created_on_%s.xlsx' % (LastMonthsPeriod, today)
        else:
            filename = 'cost_explorer_report.%s.xlsx' % (today)
            
        os.chdir('/tmp')

        pd.io.formats.excel.header_style = None
        writer = pd.ExcelWriter(filename, engine='xlsxwriter')
        workbook = writer.book
        
        format = workbook.add_format()
        format.set_align('center')
        format.set_align('vcenter')
        
        # iterate over previously generated reports
        for report in self.reports:
            print(report['Name'], report['Type'])
            dataframe = report['Data']
            dataframe.to_excel(writer, sheet_name=report['Name'])
            worksheet = writer.sheets[report['Name']]
            
            # function adjusting columnbs widths
            def get_col_widths(dataframe: object) -> int:
                # First we find the maximum length of the index column 
                idx_max = max([len(str(s)) for s in dataframe.index.values] + [len(str(dataframe.index.name))])
                # Then, we concatenate this to the max of the lengths of column name and its values for each column, left to right
                return [idx_max] + [max([len(str(s)) for s in dataframe[col].values] + [len(col)]) for col in dataframe.columns]
            
            # use get_col_widths to change widths in place
            for i, width in enumerate(get_col_widths(dataframe)):
                worksheet.set_column(i, i, int(width + 5), format)
            
            # create graphical plots for charts 
            if report['Type'] == 'chart':
                # Create a chart object.
                chart = workbook.add_chart({'type': 'column', 'subtype': 'stacked'})
                
                if CurrentMonth:
                    chartend = 13
                else: 
                    chartend = 12
                    
                for row_num in range(1, len(report['Data']) + 1):
                    chart.add_series({
                        'name':       [report['Name'], row_num, 0],
                        'categories': [report['Name'], 0, 1, 0, chartend],
                        'values':     [report['Name'], row_num, 1, row_num, chartend],
                    })
                chart.set_y_axis({'label_position': 'low'})
                chart.set_x_axis({'label_position': 'low'})
                worksheet.insert_chart('O2', chart, {'x_scale': 2.0, 'y_scale': 2.0})
                
        writer.save()

        # Deliver the excel report to S3
        if os.environ.get('S3_BUCKET'):
            s3 = boto3.client('s3')
            s3.upload_file(filename, os.environ.get('S3_BUCKET'), "aws-cost-explorer-report/cost-reports/%s" % (filename))

        # Send the excel report via email using SES
        if os.environ.get('SES_SEND'):
            # Email logic
            msg = MIMEMultipart()
            msg['From'] = os.environ.get('SES_FROM')
            msg['To'] = COMMASPACE.join(os.environ.get('SES_SEND').split(","))
            msg['Date'] = formatdate(localtime=True)
            if LastMonthOnly and CurrentMonth and not ExactMonth and not ExactYear and not LastMonthsPeriod:
                msg['Subject'] = "Cost Explorer Report for the last and the current months (%s,%s)" % (date_month(lastMonth), date_month(currentMonth))
            elif LastMonthOnly and not CurrentMonth and not ExactMonth and not ExactYear and not LastMonthsPeriod:
                msg['Subject'] = "Cost Explorer Report for the last month (%s)" % (date_month(lastMonth))
            elif not LastMonthOnly and not CurrentMonth and not ExactMonth and not ExactYear and not LastMonthsPeriod:
                msg['Subject'] = "Cost Explorer Report for the last 12 months"
            elif not LastMonthOnly and CurrentMonth and not ExactMonth and not ExactYear:
                msg['Subject'] = "Cost Explorer Report for the last 12 months + the current month (%s)" % (date_month(currentMonth))
            elif ExactMonth and ExactYear:
                exactmonth = self.evaluateMonth(exactmonth=str(ExactMonth))
                msg['Subject'] = "Cost Explorer Report for %s'%s period" % (ExactYear,exactmonth)
            elif LastMonthsPeriod:
                msg['Subject'] = "Cost Explorer Report for the last %s months period" % (LastMonthsPeriod)
            html_text = f"""
                <html>
                    <head></head>
                        <body>
                            <br>
                            <b>Kindly find your AWS Cost Explorer report attached below (report file: {filename})</b>
                            <br><br>
                            ----------------------
                            <br>
                            <i>generated by aws-cost-explorer-report lambda function</i>
                            <br>
                            ----------------------
                            <br>
                            <img src="https://baxterplanning.com/wp-content/uploads/2019/08/BXPL_300x80.png" alt="baxter planning">
                            <br>
                        </body>
                </html>
                """
            msg.attach(MIMEText(html_text, 'html'))

            with open(filename, "rb") as fil:
                part = MIMEApplication(
                    fil.read(), Name=filename)

            part['Content-Disposition'] = 'attachment; filename="%s"' % (filename)
            msg.attach(part)

            # SES Sending
            ses = boto3.client('ses', region_name=SES_REGION)
            ses.send_raw_email(
                Source=msg['From'],
                Destinations=os.environ.get('SES_SEND').split(","),
                RawMessage={'Data': msg.as_string()}
            )


def main_handler(event, context) -> None:
    
    """
    Main handler where we define reports we want to generate
    
    Args:
        None
    Returns:
        None
    """   
    # Create CostExplorer object
    costexplorer = CostExplorer(CurrentMonth, LastMonthOnly, ExactMonth, ExactYear)

    # add 'Total' report with total sum for month
    costexplorer.addReport(Name="Total", GroupBy=[], NoCredits=False, IncSupport=True)

    # GroupBy Reports
    # add 'Services' report with total sum per services
    costexplorer.addReport(Name="Services", GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}], IncSupport=True)
    # add 'Accounts' report with total sum per accounts
    costexplorer.addReport(Name="Accounts", GroupBy=[{"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"}], IncSupport=True)
    # add 'Region' report with total sum per regions
    costexplorer.addReport(Name="Regions", GroupBy=[{"Type": "DIMENSION", "Key": "REGION"}], IncSupport=True)
    
    # add 'SP-Tax-Support' report with total sum for Savings Plan, Tax and Support
    costexplorer.addReport(Name="SP-Tax-Support",
                           GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
                           FilterByServices=['Savings Plans for AWS Compute usage', 'Tax', 
                                            'AWS Support (Business)'],
                           IncSupport=True)
    
    # add 'SP-EC2-Total' report with total sum for EC2, Savings Plan + ELB/Cloudwatch
    costexplorer.addReport(Name="SP-EC2-Total",
                           GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
                           FilterByServices=['Amazon Elastic Compute Cloud - Compute', 'EC2 - Other', 
                                            'Amazon Elastic Load Balancing', 'AmazonCloudwatch',
                                            'Savings Plans for AWS Compute usage'])
    
    # add 'CC-EC2_SP_Tax_Support' report with total sum for EC2, Savings Plan, Tax and Support using Cost Category 'EC2-SP-Tax-Support'
    costexplorer.addReport(Name="CC-EC2_SP_Tax_Support", GroupBy=[{"Type": "COST_CATEGORY", "Key": "EC2-SP-Tax-Support"}], KeySplit=True)

    # add Cost Allocation tags Reports
    for tagkey in ['Customers', 'Env', 'Name']:  # Support for multiple/different Cost Allocation tags
        if tagkey == 'Customers':
            
            # add 'Tag-Customers-AllEnvs' report with total sum sorted by Customers tag and filtered by EC2/ELB/Cloudwatch/SavingsPlan services only
            costexplorer.addReport(Name='Tag-' + tagkey + '-AllEnvs',
                                    GroupBy=[{"Type": "TAG", "Key": tagkey}],
                                    FilterByServices=['Amazon Elastic Compute Cloud - Compute', 'EC2 - Other', 
                                                    'Amazon Elastic Load Balancing', 'AmazonCloudwatch',
                                                    'Savings Plans for AWS Compute usage'], 
                                    KeySplit=True)
            
            # add 'Tag-Customers-ProdEnvs' report with total sum sorted by Customers tag and filtered by Env tags ['prd', 'prodtest', 'uat', 'ins']
            costexplorer.addReport(Name='Tag-' + tagkey + '-ProdEnvs',
                                    GroupBy=[{"Type": "TAG", "Key": tagkey}],
                                    FilterByServices=['Amazon Elastic Compute Cloud - Compute', 'EC2 - Other', 
                                                    'Amazon Elastic Load Balancing', 'AmazonCloudwatch',
                                                    'Savings Plans for AWS Compute usage'],
                                    TagKey='Env', TagValueFilter=['prd', 'prodtest', 'uat', 'ins'], 
                                    KeySplit=True)
        if tagkey == 'Env':
            # add 'Tag-Env-Total' report with total sum sorted by Env tag
            costexplorer.addReport(Name='Tag-' + tagkey + "-Total",
                                    GroupBy=[{"Type": "TAG", "Key": tagkey}], 
                                    KeySplit=True)
            
        if tagkey == 'Name':
            # add 'Tag-Name-Instances' report with total sum sorted by Name tag (Instance names) and filtered by EC2 services
            costexplorer.addReport(Name='Tag-' + tagkey + "-Instances",
                                    GroupBy=[{"Type": "TAG", "Key": tagkey}],
                                    FilterByServices=['Amazon Elastic Compute Cloud - Compute', 'EC2 - Other', 
                                                    'Amazon Elastic Load Balancing'],  
                                    KeySplit=True, TypeExcel='table')
            
        if tagkey == 'Department':
            # add 'Tag-Department' report with total sum sorted by Department tag
            costexplorer.addReport(Name='Tag-' + tagkey,
                                    GroupBy=[{"Type": "TAG", "Key": tagkey}],
                                    FilterByServices=['*'],  
                                    KeySplit=True)


    # Cost Categories Reports: Total usage with and without included Savings Plan fees
    # add 'CC>Usage-SP_excluded' report with total usage sum and where Savings Plan fees are excluded; using Cost Category 'Combined-services-usage'
    costexplorer.addReport(Name="CC>Usage-SP_excluded",
                        GroupBy=[{"Type": "COST_CATEGORY", "Key": "Combined-services-usage"}],
                        KeySplit=True)
    # add 'CC>Usage-SP_included' report with total usage sum and where Savings Plan fees are included for all rows; using Cost Category 'Combined-services-usage and sp'
    costexplorer.addReport(Name="CC>Usage-SP_included",
                        GroupBy=[{"Type": "COST_CATEGORY", "Key": "Combined-services-usage and sp"}],
                        KeySplit=True)
    
    # add 'CC>Calculated-SP_excluded' report with total usage sum and where Savings Plan fees are excluded for all rows and all percentage calculated; using Cost Category 'Customers Only - Usage'
    costexplorer.addReport(Name="CC>Calculated-SP_excluded",
                        GroupBy=[{"Type": "COST_CATEGORY", "Key": "Customers Only - Usage"}],
                        CostCategoryCalculated=True)
        # add 'CC>Calculated-SP_excluded' report with total usage sum and where Savings Plan fees are included for all rows and all percentage calculated; using Cost Category 'Customers Only - Usage and SP Covered Use'
    costexplorer.addReport(Name="CC>Calculated-SP_included",
                        GroupBy=[{"Type": "COST_CATEGORY", "Key": "Customers Only - Usage and SP Covered Use"}],
                        CostCategoryCalculated=True)
            
    # RI Reports
    # add RI report with RICoverage
    costexplorer.addRiReport(Name="RICoverage")
    # add RI report with RIUtilization
    costexplorer.addRiReport(Name="RIUtilization")
    # add RI report with RIUtilizationSavings
    costexplorer.addRiReport(Name="RIUtilizationSavings", Savings=True)
    
    # add RI report with RIRecommendation (service supported value(s): Amazon Elastic Compute Cloud - Compute, Amazon Relational Database Service)
    costexplorer.addRiReport(Name="RIRecommendation")
    
    # generate and upload/send excel file
    costexplorer.generateExcel()
    
    return "Report Generated"


if __name__ == '__main__':
    main_handler()
