
# CostExplorerReport AWS Lambda function

![Python](https://www.python.org/static/community_logos/python-logo-generic.svg)

Short summary on files in directory:

**aws-cost-explorer-template.cfn.yml**:
>CloudFormation template for deploying function and related resources;

**deploy.sh**:
>script to verify main.py, validate template, zip and copy files to S3;

**invoke.sh**:
>script to invoke function;

**lambda.py**:
>main code of the function;

Details about CostExplorerReportLambda function:
CloudFormation/SAM stack: [aws-cost-explorer-report](https://us-west-2.console.aws.amazon.com/cloudformation/home?region=us-west-2#/stacks/stackinfo?filteringText=&filteringStatus=active&viewNested=true&hideStacks=false&stackId=arn%3Aaws%3Acloudformation%3Aus-west-2%3A461796779995%3Astack%2Faws-cost-explorer-report%2F92912030-2420-11eb-9532-022108f33b95)
Function: [CostExplorerReportLambda](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#functions/CostExplorerReportLambda)

Function generates an excel document with multiple cost reports located in their own tabs.

Upon successful invocation of the function, generated report goes to:

- S3 bucket: [cf-templates-oregon-bp/aws-cost-explorer-report/cost-reports/](https://s3.console.aws.amazon.com/s3/buckets/cf-templates-oregon-bp?region=us-west-2&prefix=aws-cost-explorer-report/cost-reports/&showversions=false)

- Predefined email addresses (SES-configured):
to add your email address please either contact me or set it under [Environment variables of the function](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions/CostExplorerReportLambda/edit/environment-variables?tab=configuration): add additional addresses in **SES_SEND** variable separating each address with comma without spaces.

Function is getting invoked via eventbridge cron on each 3th day of the month, but it is more efficient to invoke it via aws cli:

    aws lambda --region us-west-2 invoke --function-name CostExplorerReportLambda --payload '{}' response.json

or clone the repository, go to aws-cost-explorer-report folder and execute:

    bash invoke.sh

Reports generation is defined in `def main_handler(event, context)` section of the `lambda.py` file.
Function creates an instance of the main class:

    costexplorer = CostExplorer(CurrentMonth=False)

And then start to generate reports by invoking the main `addReport` method:

Functions supports different time ranges applied to generated reports:

- **CURRENT_MONTH**:

>true - include cost data for a current month
>false - do not include cost data for a current month

- **LAST_MONTH_ONLY**:

>true - include cost data only for a last completed month
>false - include cost data for the last 12 months (more earlier dates are not supported by AWS CE API)

- **EXACT_MONTH**:

>if set along with EXACT_YEAR - include only the data for a specified month (within last 12 months)

- **EXACT_YEAR**:

>if set along with EXACT_MONTH - include only the data for a specified month (within last 12 months)

- **LAST_MONTHS_PERIOD**:

>if set generate report for last defined period of full months (within last 12 months)

Notes:

- setting of EXACT_MONTH and EXACT_YEAR disables LAST_MONTH_ONLY and CURRENT_MONTH evaluation
- EXACT_MONTH possible values: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
- EXACT_YEAR possible values: 2020, 2021
- All variables can be set in [AWS Lambda GUI console](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions/CostExplorerReportLambda?tab=configuration);
- To invoke the function after changing variables please either use test action in GUI: **SendReport** or via script `bash invoke.sh`

List of reports:

# Overall Billing Report

- **Total** (***excel tab name***)

        costexplorer.addReport(Name="Total", GroupBy=[], NoCredits=False, IncSupport=True)

> **Description**: total cost for previous month

# GroupBy Reports

- **Services**

        costexplorer.addReport(Name="Services", GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}], IncSupport=True)

> **Description**: total cost for all services including support

- **Accounts**

        costexplorer.addReport(Name="Services", GroupBy=[{"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"}], IncSupport=True)

> **Description**: total cost by linked AWS accounts

- **Regions**

        costexplorer.addReport(Name="Services", GroupBy=[{"Type": "DIMENSION", "Key": "REGION"}], IncSupport=True)

> **Description**: total cost by AWS regions

- **Service-SP_Tax_Support**

        costexplorer.addReport(Name="SP-TaxSupport", GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
                            FilterByServices=['Savings Plans for AWS Compute usage', 'Tax','AWS Support (Business)'],
                            IncSupport=True)

> **Description**: total cost for Savings Plan, Support and Tax by filtering services

- **SP-EC2-Total**

        costexplorer.addReport(Name="SP-EC2-Total", GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}], FilterByServices=
                        ['Amazon Elastic Compute Cloud - Compute', 'EC2 - Other','Amazon Elastic Load Balancing',
                        'AmazonCloudwatch','Savings Plans for AWS Compute usage'])

> **Description**: total cost for EC2, Savings Plan + ELB/Cloudwatch

- **CC-EC2_SP_Tax_Support**

        costexplorer.addReport(Name="CC-EC2_SP_Tax_Support", GroupBy=[{"Type": "COST_CATEGORY", "Key": "EC2-SP-Tax-Support"}], KeySplit=True)

> **Description**: total cost for EC2, Savings Plan, Tax and Support using predefined Cost Category "EC2-SP-Tax-Support"

# Cost Allocation tags reports

- **TagCustomersAllEnvs**

        costexplorer.addReport(Name='Tag-' + tagkey + 'AllEnvs',
                            GroupBy=[{"Type": "TAG", "Key": tagkey}],
                            FilterByServices=['Amazon Elastic Compute Cloud - Compute',
                            'EC2 - Other','Amazon Elastic Load Balancing', 'AmazonCloudwatch',
                            'Savings Plans for AWS Compute usage'],
                            KeySplit=True)

> **Description**:  total by tag Customers filtered by EC2/ELB/Cloudwatch/SavingsPlan services only

- **TagCustomersProdEnvs**

        costexplorer.addReport(Name='Tag-' + tagkey + 'ProdEnvs',
                        GroupBy=[{"Type": "TAG", "Key": tagkey}],
                        FilterByServices=['Amazon Elastic Compute Cloud - Compute', 'EC2 - Other','Amazon Elastic Load Balancing',
                        'AmazonCloudwatch','Savings Plans for AWS Compute usage'],
                        TagKey='Env', TagValueFilter=['prd', 'prodtest', 'uat', 'ins'],
                        KeySplit=True)

> **Description**:  total cost by tag Customers filtered by Env tags ['prd', 'prodtest', 'uat', 'ins']

- **TagEnvTotal**

        costexplorer.addReport(Name='Tag' + tagkey + "Total", GroupBy=[{"Type": "TAG", "Key": tagkey}], KeySplit=True)

> **Description**:  total cost grouped by Env tag

- **Tag-Name-Instances**

        costexplorer.addReport(Name='Tag-' + tagkey + "Instances",
                        GroupBy=[{"Type": "TAG", "Key": tagkey}],
                        FilterByServices=['Amazon Elastic Compute Cloud - Compute', 'EC2 - Other','Amazon Elastic Load Balancing'],
                        KeySplit=True,
                        TypeExcel='table')

> **Description**:  total cost by tag Name (Instance names) filtered by EC2 services

- **Tag-Department**

        costexplorer.addReport(Name='Tag' + tagkey, GroupBy=[{"Type": "TAG", "Key": tagkey}], FilterByServices=['*'], KeySplit=True)

> **Description**:  total cost by tag Department

# Cost Categories Reports

- CC>Usage-SP_excluded

        costexplorer.addReport(Name="CC>Usage-SP_excluded",
                            GroupBy=[{"Type": "COST_CATEGORY", "Key": "Combined-services-usage and sp"}],
                            KeySplit=True)

> **Description**: total costs calculated with cost category "Combined-services-usage"- EC2 environments grouped by their Env and Customers tags, other services + costs for each Customers tag; Savings Plan is NOT INCLUDED in amount and given as a separated total sum. Costs for EC2 instances with shared customers tags are NOT calculated here (hint as for percentage of utilization is in name row)

- CC>Usage-SP_included

        costexplorer.addReport(Name="CC>Usage-SP_included",
                                GroupBy=[{"Type": "COST_CATEGORY", "Key": "Combined-services-usage"}],
                                KeySplit=True)

> **Description**:  total costs calculated with cost category "Combined-services-usage and sp" - EC2 environments grouped by their Env and Customers tags, other services + costs for each Customers tag; Savings Plan is INCLUDED for all appropriate amounts. Costs for EC2 instances with shared customers tags are NOT calculated here (hint as for percentage of utilization is in name row)

# Experimental reports

(with CostCategoryCalculated=True parameter which performs triggers calculation of final sum according to percentage of resources utilization; e.g: ['CRAY', 'JJDC', 'MDC', 'PAN'] amounts are getting multiplied by 0.25 (25%) because they equally share the same resources between them

- CC>Calculated-SP_excluded

        costexplorer.addReport(Name="CC>Calculated-SP_excluded",
                                GroupBy=[{"Type": "COST_CATEGORY", "Key": "Customers Only - Usage"}],
                                CostCategoryCalculated=True)

> **Description**: total costs calculated with cost category "CustomersOnlyCalculated"- Costs for each Customer; Savings Plan is **NOT INCLUDED** in amount and given as a separated category. Costs for EC2 instances with shared customers tags are calculated here and report shows final results.

- CC>Calculated-SP_included

        costexplorer.addReport(Name="CC>Calculated-SP_included",
                            GroupBy=[{"Type": "COST_CATEGORY", "Key": "Customers Only - Usage and SP Covered Use"}],
                            CostCategoryCalculated=True)

> **Description**: total costs calculated with cost category "CustomersOnlyCalculated"- Costs for each Customer; Savings Plan is **INCLUDED** for all appropriate amounts. Costs for EC2 instances with shared customers tags are calculated here and report shows final results.

# RI Reports

- RICoverage

        costexplorer.addRiReport(Name="RICoverage")

> **Description**: report allows to discover how much of overall instance usage is covered by RIs

- RIUtilization

        costexplorer.addRiReport(Name="RIUtilization")

> **Description**: report allows to visualize RI utilization (i.e., the percentage of purchased RI hours consumed by instances during a period of time)

- RIUtilizationSavings

        costexplorer.addRiReport(Name="RIUtilizationSavings", Savings=True)

> **Description**: RI utilization + savings plan associated with RI

- RIRecommendation

        costexplorer.addRiReport(Name="RIRecommendation")

> **Description**: report allows to visualize RI recommendations for cost optimizations
