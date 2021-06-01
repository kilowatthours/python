# ec2-instance-state-report AWS Lambda function

![Python](https://www.python.org/static/community_logos/python-logo-generic.svg)

Short summary on files in directory:

**deploy.sh**:
>script to verify main.py, validate template, zip and copy files to S3;

**invoke.sh**:
>script to invoke function;

**main.py**:
>main code of the function;

**ec2-instance-state-report.cfn.yaml**:
>CloudFormation template for deploying function and related resources;

Details about **ec2-instance-state-report** function:

**CloudFormation/SAM stack**: [ec2-instance-state-report](https://us-west-2.console.aws.amazon.com/cloudformation/home?region=us-west-2#/stacks/stackinfo?filteringStatus=active&filteringText=&viewNested=true&hideStacks=false&stackId=arn%3Aaws%3Acloudformation%3Aus-west-2%3A461796779995%3Astack%2Fec2-instances-state-report%2Fa81d2db0-a66e-11eb-9ccd-0a133869c3b9)

**Function**: [ec2-instance-state-report](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#functions/ec2-instances-state-report)

Function generates an excel document with multiple reports on EC2 instances with specific Env tags.

Upon successful invocation of the function, generated report goes to:

- S3 bucket: [cf-templates-oregon-bp/ec2-instance-state-report/reports/](https://s3.console.aws.amazon.com/s3/buckets/cf-templates-oregon-bp?region=us-west-2&prefix=ec2-instances-state-report/reports/&showversions=false)

- Predefined email addresses (SES-configured):
to add your email address please either contact me or set it under [Environment variables of the function](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions/ec2-instances-state-report?tab=configure): add additional addresses in **SES_SEND_TO** variable separating each address with commas and without spaces.

Function is getting invoked via eventbridge cron on each Monday at 14-00 UTC (9AM Austin Texas):
Also it can invoked using AWS CLI:

    aws lambda --region us-west-2 invoke --function-name ec2-instance-state-report --qualifier PROD --invocation-type Event\ --payload '{}' response.json

or via bash script available in repository, go to ec2-instance-state-report folder and execute:

    bash invoke.sh

Reports generation is defined in `def main_handler(event, context)` section of the `main.py` file.
