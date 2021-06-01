# WalkmeVideosNotifications AWS Lambda function

![Python](https://www.python.org/static/community_logos/python-logo-generic.svg)

Short summary on files in directory:

**deploy.sh**:
>script to verify main.py, validate template, zip and copy files to S3;

**event.json**:
>test event in json format;

**invoke.sh**:
>script to invoke function;

**lambda.py**:
>main code of the function;

**walkme-videos-notification.cfn.yaml**:
>CloudFormation template for deploying function and related resources;

Details about **WalkmeVideosNotifications** function:

**CloudFormation/SAM stack**: [walkme-videos-notifications](https://us-west-2.console.aws.amazon.com/cloudformation/home?region=us-west-2#/stacks/stackinfo?filteringText=&filteringStatus=active&viewNested=true&hideStacks=false&stackId=arn%3Aaws%3Acloudformation%3Aus-west-2%3A461796779995%3Astack%2Fwalkme-videos-notifications%2Fe479b730-54c3-11eb-a1e9-06b1b80a4e11)

**Function**: [WalkmeVideosNotification](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions/WalkmeVideosNotification?tab=configuration)

Function sends email notification upon detecting a successful upload of a video file to the specified S3 bucket (*for walkme videos*).

Upon successful invocation of the function, email goes to predefined email addresses (*SES-configured*):

Function is getting invoked by S3 event notification (`s3:ObjectCreated:*`) in bucket [bp-walkme-videostorage](https://s3.console.aws.amazon.com/s3/buckets/bp-walkme-videostorage?region=us-west-2&tab=objects).

**Important nuance**: due to the limitations of SAM Transform templating engine, it is not possible to define S3 Event inside of AWS::Serverless::Function indicating an already existing bucket. Thus the event notification (trigger) has been setup manually in AWS GUI console (in AWS Lambda trigger indicating Lambda ARN "arn:aws:lambda:us-west-2:461796779995:function:WalkmeVideosNotification:PROD").

Test event for this function:

    {
    "Records": [
    {
      "eventVersion": "2.0",
      "eventSource": "aws:s3",
      "awsRegion": "us-west-2",
      "eventTime": "1970-01-01T00:00:00.000Z",
      "eventName": "ObjectCreated:Put",
      "userIdentity": {
        "principalId": "EXAMPLE"
      },
      "requestParameters": {
        "sourceIPAddress": "127.0.0.1"
      },
      "responseElements": {
        "x-amz-request-id": "EXAMPLE123456789",
        "x-amz-id-2": "EXAMPLE123/5678abcdefghijklambdaisawesome/mnopqrstuvwxyzABCDEFGH"
      },
      "s3": {
        "s3SchemaVersion": "1.0",
        "configurationId": "testConfigRule",
        "bucket": {
          "name": "bp-walkme-videostorage",
          "ownerIdentity": {
            "principalId": "EXAMPLE"
          },
          "arn": "arn:aws:s3:::bp-walkme-videostorage"
        },
        "object": {
          "key": "images/test.jpg",
          "size": 1024,
          "eTag": "0123456789abcdef0123456789abcdef",
          "sequencer": "0A1B2C3D4E5F678901"
        }
      }
    } 
    ] 
    }
