# Autotagging AWS Lambda function

Function automatically applies tags to appropriate AWS resources in response to API events from CloudTrail.

Short summary on files in directory:

**autotagging-template.cfn.yml**:
>CloudFormation template for deploying function and related resources;

**deploy.sh**:
>script to verify main.py, validate template, zip and copy files to S3;

**event.json**:
>test event in json format;

**main.py**:
>main code of the function;

## List of all supported events

| Event     | Service    | Applied tags | Additional notes |
| ----------|------------|--------------|------------|
| RunInstances | EC2 | Owner, CreatedAt, Env, Department |also tagging underlying volumes and ENI's |
| StartInstances | EC2 | LastStartedBy, LastStartedAt, Owner (occasionally) ||
| StopInstances | EC2 | LastStoppedBy, LastStoppedAt ||
| RebootInstances | EC2 | LastRebootedBy, LastRebootedAt ||
| CreateVolume | EC2 | Owner, CreatedAt, Env, Department, Name (occasionally) ||
| CreateImage | EC2 | Owner, CreatedAt, Env, Department, instance tags | also tagging underlying snapshots|
| CopyImage | EC2 | Owner, CopiedAt ||
| RegisterImage | EC2 | Owner, RegisteredAt ||
| CreateSnapshot | EC2 | Owner, CreatedAt ||
| CopySnapshot | EC2 | Owner, CopiedAt ||
| ImportSnapshot | EC2 | Owner, ImportedAt ||
| CreateSecurityGroup | EC2 | Owner, CreatedAt, Env, Department, Name ||
| CreateLaunchTemplate | EC2 | CreatedBy, CreatedAt, Name, Env, Department ||
| ModifyLaunchTemplate | EC2 | LastModifiedBy, LastModifiedAt ||
| CreateLaunchTemplateVersion | EC2 | LastVersion, LastVersionAddedBy ||
| CreateVpc | EC2 | CreatedBy, CreatedAt, Name, Env, Department ||
| CreateNetworkInterface | EC2 | Owner, Name, CreatedAt, Env, Department, instance tags (or sg tags) ||
| AllocateAddress | EC2 | Owner, AllocatedAt, Name, Env, Department, instance tags (or eni tags) ||
| CreateInternetGateway | EC2 | CreatedBy, CreatedAt ||
| CreateRouteTable | EC2 | CreatedBy, CreatedAt ||
| CreateSubnet | EC2 | CreatedBy, CreatedAt, Name, Env, Department ||
| CreateNatGateway | EC2 | CreatedBy, CreatedAt ||
| CreateEgressOnlyInternetGateway | EC2 | CreatedBy, CreatedAt ||
| CreateDhcpOptions | EC2 | CreatedBy, CreatedAt ||
| CreateVpnGateway | EC2 | CreatedBy, CreatedAt ||
| CreateVpnConnection | EC2 | CreatedBy, CreatedAt ||
| CreateCustomerGateway | EC2 | CreatedBy, CreatedAt ||
| CreateVpcPeeringConnection | EC2 | CreatedBy, CreatedAt ||
| CreateManagedPrefixList | EC2 | CreatedBy, CreatedAt ||
| CreateTransitGateway | EC2 | CreatedBy, CreatedAt ||
| CreateNetworkAcl | EC2 | CreatedBy, CreatedAt ||
| CreateVpcEndpoint | EC2 | CreatedBy, CreatedAt ||
| CreateVpcEndpointServiceConfiguration | EC2 | CreatedBy, CreatedAt ||
| CreateKeyPair | EC2 | Name, CreatedBy, CreatedAt, Env, Department ||
| CreatePlacementGroup | EC2 | Name, CreatedBy, CreatedAt, Env, Department ||
| CreateCapacityReservation | EC2 | Name, CreatedBy, CreatedAt, Env, Department ||
| ModifyCapacityReservation | EC2 | LastModifiedBy, LastModifiedAt ||
| ModifyInstanceAttribute | EC2 | LastModifiedBy, LastModifiedAt ||
| CreateAutoScalingGroup | EC2, Autoscaling | Name, CreatedBy, CreatedAt, Env, Department ||
| RegisterInstancesWithLoadBalancer | ELB, EC2 | LB_registered, LB_type, LB_registered_with, LB_registered_by, LB_registered_at | tagging EC2 instances |
| DeregisterInstancesFromLoadBalancer | ELB, EC2 | LB_registered, LB_deregistered_from, LB_deregistered_by, LB_deregistered_at | tagging EC2 instances |
| RegisterTargets | ELBv2, EC2 | LB_registered, LB_type, LB_registered_with, LB_registered_by, LB_registered_at, LB_target_groups | tagging EC2 instances |
| DeregisterTargets | ELBv2, EC2 | LB_registered, LB_deregistered_from, LB_deregistered_by, LB_deregistered_at | tagging EC2 instances |
| CreateLoadBalancer | ELBv2 | Name, CreatedBy, CreatedAt, Env, Department, Name ||
| CreateTargetGroup | ELBv2 | Name, CreatedBy, CreatedAt, Env, Department, Name ||
| CreateFunction20150331 | Lambda | Name, CreatedBy, CreatedAt, Env, Department, Name ||
| UpdateFunctionConfiguration20150331v2 | Lambda | LastConfigModifiedBy, LastConfigModifiedAt, LastConfigUpdateStatus ||
| UpdateFunctionCode20150331v2 | Lambda | LastCodeModifiedBy, LastCodeModifiedAt, LastCodeUpdateStatus ||
| CreateDBInstance | RDS | Name, CreatedBy, CreatedAt, Env, Department, Name ||
| StartDBInstance | RDS | LastStartedBy, LastStartedAt ||
| StopDBInstance | RDS | LastStoppedBy, LastStoppedAt ||
| RebootDBInstance | RDS | LastRebootedBy, LastRebootedAt ||
| ModifyDBInstance | RDS | LastModifiedBy, LastModifiedAt  ||
| CreateDBSnapshot | RDS | CreatedBy, CreatedAt, Env, Department, Name, SourceDB  ||
| CreateDBClusterSnapshot | RDS | CreatedBy, CreatedAt, Env, Department, Name, SourceDB  ||
| CreateDBInstanceReadReplica | RDS | CreatedBy, CreatedAt, Env, Department, Name, SourceDB  ||
| CreateDBSubnetGroup | RDS | Name, CreatedBy, CreatedAt, Env, Department, Name ||
| CreateDBParameterGroup | RDS | Name, CreatedBy, CreatedAt, Env, Department, Name ||
| CreateDBClusterParameterGroup | RDS | Name, CreatedBy, CreatedAt, Env, Department, Name ||
| CreateDBCluster | RDS | Name, CreatedBy, CreatedAt, Env, Department, Name, Engine, EngineVersion, ClusterType ||
| CreateGlobalCluster | RDS | Name, CreatedBy, CreatedAt, Env, Department, GlobalClusterName, Engine, EngineVersion, ClusterType ||
| CreateOptionGroup | RDS | Name, CreatedBy, CreatedAt, Env, Department, Name ||
| CreateEventSubscription | RDS | Name, CreatedBy, CreatedAt, Env, Department, Name ||
| CreateDBProxy | RDS | Name, CreatedBy, CreatedAt, Env, Department, Name ||
| ModifyDBSubnetGroup | RDS | LastModifiedBy, LastModifiedAt ||
| ModifyDBParameterGroup | RDS | LastModifiedBy, LastModifiedAt ||
| ModifyDBClusterParameterGroup | RDS | LastModifiedBy, LastModifiedAt ||
| ModifyDBCluster | RDS | LastModifiedBy, LastModifiedAt ||
| ModifyGlobalCluster | RDS | LastModifiedBy, LastModifiedAt ||
| ModifyOptionGroup | RDS | LastModifiedBy, LastModifiedAt ||
| ModifyEventSubscription | RDS | LastModifiedBy, LastModifiedAt ||
| ModifyDBProxy | RDS | LastModifiedBy, LastModifiedAt ||
| CreateSecret | Secrets | Name, CreatedBy, CreatedAt, Env, Department, Name ||
| UpdateSecret | Secrets | LastUpdatedBy, LastUpdatedAt ||
| PutParameter | Secrets | Name, CreatedBy, CreatedAt, Env, Department, Name ||
| CreateDocument | Secrets | Name, CreatedBy, CreatedAt, Env, Department, Name ||
| UpdateDocument | Secrets | LastUpdatedBy, LastUpdatedAt ||
| UpdateDocumentDefaultVersion | Secrets | DefaultVersionUpdatedBy, DefaultVersionUpdatedAt ||
| CreateCluster | Redshift | Name, CreatedBy, CreatedAt, Env, Department, Name ||
| CreateCacheCluster | Elasticache | Name, CreatedBy, CreatedAt, Env, Department, Name ||
| CreateBucket | S3 | Name, CreatedBy, CreatedAt, Env, Department ||
| CreateTable | DynamoDB | Name, CreatedBy, CreatedAt, Env, Department ||
| CreateGlobalTable | DynamoDB | Name, CreatedBy, CreatedAt, Env, Department ||
| UpdateTable | DynamoDB | LastUpdatedBy, LastUpdatedAt ||
| UpdateGlobalTable | DynamoDB | LastUpdatedBy, LastUpdatedAt ||
| RunJobFlow | EMR | Name, CreatedBy, CreatedAt, Env, Department ||
| CreateUser | IAM | Name, CreatedBy, CreatedAt ||
| CreateRole | IAM | Name, CreatedBy, CreatedAt ||
| CreatePolicy | IAM | Name, CreatedBy, CreatedAt ||
| CreateOpenIDConnectProvider | IAM | Name, CreatedBy, CreatedAt ||
| CreateSAMLProvider | IAM | Name, CreatedBy, CreatedAt ||
| CreatePolicyVersion | IAM | LastVersionUpdatedBy, LastVersionUpdatedAt ||
| UpdateRole | IAM | LastUpdatedBy, LastUpdatedAt ||
| CreateTrail | Cloudtrail | Name, CreatedBy, CreatedAt, Env, Department ||
| UpdateTrail | Cloudtrail | LastUpdatedBy, LastUpdatedAt ||
| CreateStack | CloudFormation | cfn:stack:name, cfn:stack:resource, cfn:stack:created-by, cfn:stack:created-at, Env, Department ||
| CreateStack | Opsworks | Name, CreatedBy, CreatedAt, Env, Department ||
| CloneStack | Opsworks | Name, ClonnedBy, ClonnedAt, Env, Department ||
| CreateServer | OpsworksCM | Name, CreatedBy, CreatedAt, Env, Department ||
| UpdateServer | OpsworksCM | LastUpdatedBy, LastUpdatedAt ||
| CreateDistribution | Cloudfront | Name, CreatedBy, CreatedAt, Env, Department ||
| CreateCluster | EKS, ECS | Name, CreatedBy, CreatedAt, Env, Department ||
| CreateNodegroup | EKS | Name, CreatedBy, CreatedAt, Env, Department ||
| CreateService | ECS | Name, CreatedBy, CreatedAt, Env, Department | also tagging underlying tasks and their ENI's |
| UpdateService | ECS | LastUpdatedBy, LastUpdatedAt | also tagging underlying tasks and their ENI's |
| RegisterTaskDefinition | ECS | CreatedBy, CreatedAt, TaskDefinitionFamily ||
| RunTask | ECS | Name, CreatedBy, CreatedAt | also tagging underlying ENI's |
| CreateFileSystem | EFS, FSx | Name, CreatedBy, CreatedAt, Env, Department ||
| CreateAccessPoint | EFS | Name, CreatedBy, CreatedAt, Env, Department ||
| UpdateFileSystem | EFS, FSx | LastUpdatedBy, LastUpdatedAt ||
| CreateMountTarget | EFS | MountAddedBy, MountAddedAt ||
| CreateUserPool | Cognito | Name, CreatedBy, CreatedAt, Env, Department ||
| UpdateUserPool | Cognito | LastUpdatedBy, LastUpdatedAt ||
| CreateTopic | SNS | Name, CreatedBy, CreatedAt, Env, Department ||
| CreateQueue | SQS | Name, CreatedBy, CreatedAt, Env, Department ||
| CreateRepository | ECR | Name, CreatedBy, CreatedAt, Env, Department ||
| CreateBackupVault | AWS Backup | Name, CreatedBy, CreatedAt, Env, Department ||
| CreateBackupPlan | AWS Backup | Name, CreatedBy, CreatedAt, Env, Department ||
| UpdateBackupPlan | AWS Backup | LastUpdatedBy, LastUpdatedAt ||
| CreateStream | Kinesis | Name, CreatedBy, CreatedAt, Env, Department ||
| CreateDeliveryStream | Kinesis Firehose | Name, CreatedBy, CreatedAt, Env, Department ||
| CreateApplication | Kinesis Analytics | Name, CreatedBy, CreatedAt, Env, Department ||
| UpdateApplication | Kinesis Analytics | LastUpdatedBy, LastUpdatedAt ||
| CreateKey | KMS | Name, CreatedBy, CreatedAt, Env, Department ||
| ImportCertificate | ACM | ImportedBy, ImportedAt, Name ||
| RequestCertificate | ACM | RequestedBy, RequestedAt, Name ||
| CreateWorkspaces | AWS Workspaces | Name, CreatedBy, CreatedAt, Env, Department ||
| CreateEnvironment | Elastic Beanstalk | CreatedBy, CreatedAt, Department ||
| UpdateEnvironment | Elastic Beanstalk | LastUpdatedBy, LastUpdatedAt ||
| CreateApplication | Elastic Beanstalk | CreatedBy, CreatedAt, Department ||
| UpdateApplication | Elastic Beanstalk | LastUpdatedBy, CreatedAt, LastUpdatedAt ||
| CreateApplicationVersion | Elastic Beanstalk | CreatedBy, CreatedAt, Department ||
| CreateApi | API Gateway | Name, Env, Department, Protocol, CreatedBy, CreatedAt ||
| CreateRestApi | API Gateway | Name, Env, Department, Protocol, CreatedBy, CreatedAt ||
| CreateStage | API Gateway | Name, API id, CreatedBy, CreatedAt ||
| ImportApi | API Gateway | Name, Env, Department, Protocol, CreatedBy, CreatedAt ||
| CreateApiKey | API Gateway | Name, Env, Department, Id, CreatedBy, CreatedAt ||
| CreateDomainName | API Gateway | Name, Env, Department, CreatedBy, CreatedAt ||
| CreateVpcLink | API Gateway | Name, Env, Department, Id, CreatedBy, CreatedAt ||
| CreateUsagePlan | API Gateway | Name, Env, Department, Id, CreatedBy, CreatedAt ||
| GenerateClientCertificate | API Gateway | Env, Department, Id, CreatedBy, CreatedAt ||
| UpdateClientCertificate | API Gateway | LastUpdatedBy, LastUpdatedAt ||
| UpdateVpcLink | API Gateway | LastUpdatedBy, LastUpdatedAt ||
| UpdateUsagePlan | API Gateway | LastUpdatedBy, LastUpdatedAt ||
| UpdateDomainName | API Gateway | LastUpdatedBy, LastUpdatedAt ||
| UpdateApiKey | API Gateway | LastUpdatedBy, LastUpdatedAt ||
| UpdateApi | API Gateway | LastUpdatedBy, LastUpdatedAt ||
| UpdateRestApi | API Gateway | LastUpdatedBy, LastUpdatedAt ||
| UpdateStage | API Gateway | LastUpdatedBy, LastUpdatedAt ||
| CreatePipeline | CodePipeline | Name, Env, Department, CreatedAt, CreatedBy ||
| UpdatePipeline | CodePipeline | LastUpdatedBy, LastUpdatedAt ||
| CreateProject | CodeBuild | Name, Env, Department, CreatedAt, CreatedBy ||
| CreateApplication | CodeDeploy | Name, Env, Department, CreatedAt, CreatedBy ||
| CreateDeploymentGroup | CodeDeploy | Name, Env, Application, Department, CreatedAt, CreatedBy ||
| UpdateDeploymentGroup | CodeDeploy | Name, Env, Application, Department, LastUpdatedBy, LastUpdatedAt ||
| CreateRepository | CodeArtifact | Name, Env, Domain, Department, CreatedBy, CreatedAt ||
| CreateDomain | CodeArtifact | Name, Env, Department, CreatedBy, CreatedAt ||
| UpdateRepository | CodeArtifact | LastUpdatedBy, LastUpdatedAt ||
| CreateRepository | CodeCommit | Name, Env, Department, CreatedBy, CreatedAt ||
| CreateRepositoryName | CodeCommit | Name, NameUpdatedBy, NameUpdatedAt ||
| CreateRepositoryDescription | CodeCommit | DescriptionUpdatedBy, DescriptionUpdatedAt ||
| CreateProject | CodeStar | Name, Env, Department, CreatedBy, CreatedAt ||
| UpdateProject | CodeStar | LastUpdatedBy, LastUpdatedAt ||
| CreateAccount | Organizations | Name, CreatedBy, CreatedAt ||
| CreateVault | S3 Glacier | Name, Env, Department, CreatedBy, CreatedAt ||
| CreatePortfolio | Service Catalog | Name, Env, Department, CreatedBy, CreatedAt ||
| CreateProduct | Service Catalog | Name, Env, Department, CreatedBy, CreatedAt ||
| UpdatePortfolio | Service Catalog | LastUpdatedBy, LastUpdatedAt ||
| UpdateProduct | Service Catalog | LastUpdatedBy, LastUpdatedAt ||
| PutRule | EventBridge | Name, Env, Department, CreatedBy, CreatedAt ||
| CreateStateMachine | StepFunctions | Name, Env, Department, CreatedBy, CreatedAt ||
| CreateActivity | StepFunctions | Name, Env, Department, CreatedBy, CreatedAt ||
| UpdateStateMachine | StepFunctions | LastUpdatedBy, LastUpdatedAt ||
| CreateFlow | Appflow | Name, Env, Department, CreatedBy, CreatedAt ||
| UpdateFlow | Appflow | LastUpdatedBy, LastUpdatedAt ||
| CreateComputeEnvironment | Batch | Name, Type, Env, Department, CreatedBy, CreatedAt ||
| UpdateComputeEnvironment | Batch | LastUpdatedBy, LastUpdatedAt ||
| CreateJobQueue | Batch | Name, Env, Department, CreatedBy, CreatedAt ||
| RegisterJobDefinition | Batch | Name, Type, Env, Department, CreatedBy, CreatedAt ||
| SubmitJob | Batch | Name, Env, Queue, Department, CreatedBy, CreatedAt ||
| UpdateJobQueue | Batch | LastUpdatedBy, LastUpdatedAt ||
| CreateCrawler | Glue | Name, Env, Department, CreatedBy, CreatedAt ||
| UpdateCrawler | Glue | LastUpdatedBy, LastUpdatedAt ||
| StartCrawler | Glue | LastStartedBy, LastStartedAt ||
| CreateRegistry | Glue | Name, Env, Department, CreatedBy, CreatedAt ||
| UpdateRegistry | Glue | LastUpdatedBy, LastUpdatedAt ||
| CreateSchema | Glue | Name, Registry, Env, Department, CreatedBy, CreatedAt ||
| UpdateSchema | Glue | LastUpdatedBy, LastUpdatedAt ||
| CreateWorkflow | Glue | Name, Env, Department, CreatedBy, CreatedAt ||
| UpdateWorkflow | Glue | LastUpdatedBy, LastUpdatedAt ||
| CreateJob | Glue | Name, Env, Department, CreatedBy, CreatedAt ||
| UpdateJob | Glue | LastUpdatedBy, LastUpdatedAt ||
| CreateTrigger | Glue | Name, Env, Department, CreatedBy, CreatedAt ||
| UpdateTrigger | Glue | LastUpdatedBy, LastUpdatedAt ||
| CreateGraphqlApi | Appsync | Name, Env, Department, CreatedBy, CreatedAt ||
| UpdateGraphqlApi | Appsync | LastUpdatedBy, LastUpdatedAt ||
| CreateHostedZone | route53 | Name, CreatedBy, CreatedAt ||
| CreateHealthCheck | route53 | Name, CreatedBy, CreatedAt ||
| UpdateHealthCheck | route53 | LastUpdatedBy, LastUpdatedAt ||
| CreateResolverRule | route53resolver | Name, CreatedBy, CreatedAt ||
| UpdateResolverRule | route53resolver | LastUpdatedBy, LastUpdatedAt ||
| CreateResolverEndpoint | route53resolver | Name, CreatedBy, CreatedAt ||
| UpdateResolverEndpoint | route53resolver | LastUpdatedBy, LastUpdatedAt ||
| CreateLogGroup | CloudwatchLogs | Name, Env, Department, CreatedBy, CreatedAt ||
| PutMetricAlarm | Cloudwatch | alarm:name, alarm:created-by, alarm:created-at ||
| PutInsightRule | Cloudwatch | insights-rule:name, insights-rule:created-by, insights-rule:created-at ||
