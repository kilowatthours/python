# AWS Tagging Scripts

**ami-auto-tagging.py**:
>automatiically apply tags for AMI images and their snapshots based on instance tags of corresponding instances;

* usage: `python ami-auto-tagging.py --images aminames`

* example: *check apollodb and JIRA images*

    `python ami-auto-tagging.py --images JIRA apollodb`

* example #2: *check all images*

    `python ami-auto-tagging.py`

* by default script runs in DEBUG mode; to apply tags execute it with `"-A || --apply || -a || --true"` argument.

**ami-manual-tagging.py**:
>Script to manually apply tags for EC2 AMI's and their snapshots based on corresponding instance tags;

* usage: `python ami-manual-tagging.py --images aminames --tags KEY=VAL KEY=VAL`

* example: *apply Env and Departments tags for Jenkins images*

    `python ami-manual-tagging.py --images ops-jenkins --tags Env=ops Department=Operations`

* example #2: *delete Env and Departments tags for Jenkins images*

    `python ami-manual-tagging.py --images ops-jenkins --tags Env=ops Department=Operations -D`

*check all images and apply tags in ACTIVE mode*:
    `python ami-manual-tagging.py -A'

* by default script runs in DEBUG mode; to apply tags execute it with arguments: `"-A || --apply || -a"`
* script support deleting tags by passing arguments: `"-D || --delete"`.

**asg-manual-tagging.py**:
>create tags for EC2 AutoScaling Groups; expects correct arguments from the command line;

* usage: `python asg-manual-tagging.py --scope new --resources ASG_1 ASG_2 --tagkey TAGKEY --tagvalue TAGVALUE`

* example: *tag AS groups S3VirusScan-ScanAutoScalingGroup-1XCZIQ10PB3J2 and bp-tc-AutoScalingGroup with tag Env=dev:*

    `python asg-manual-tagging.py --scope new --resources S3VirusScan-ScanAutoScalingGroup-1XCZIQ10PB3J2 bp-tc-AutoScalingGroup --tagkey Env --tagvalue dev`

* `scope` supports following variants:

    1. new/dev/prd/ops - create new tags

    2. beanstalk/eb/bean - create tags for Elastic Beanstalk ASG's

    3. department - automatically create "Department" tag if "Env" tag is present

* by default script runs in DEBUG mode; to apply tags execute it with `"-A || --apply || --true"` argument.

**customers-tag-manual-tagging.py**:
>create Customers tags for EC2 resources based on predefined server names and GID associations (e.g., 'pluto':'F5N GIMO PLS')

* usage: `python customers-tag-manual-tagging.py --servers CUSTOMER_SERVER1 CUSTOMER_SERVER2`

* example: *apply Customers tag for 'pluto' and 'neptune' servers:*

    `python customers-tag-manual-tagging.py --servers neptune pluto`

* default value for `--servers` argument: *`["neptune", "odyssey", "venus", "titania", "uranus", "eris", "apollo", "intrepid", "lucent", "jupiter", "earth", "infoprint", "europa", "pluto", "mars", "luna", "mercury", "phobos", "republic", "oberon", "theia", "tgcs"]`*

* by default script runs in DEBUG mode; to apply tags execute it with `"-A || --apply || --true"` argument.

**department-tag-auto-tagging.py**:
>create Department tag based on Env tag for EC2 resources:

* usage and example: `python department-tag-auto-tagging.py`

* script support `--departments` argument to limit a scope of departments:

    `python department-tag-auto-tagging.py --department Operations`

* by default script runs in DEBUG mode; to apply tags execute it with `"-A || --apply || --true"` argument.

**department-tag-remove-rename-tagging.py**:
>renames or removes specific Department tags; requires to uncomment and define values manually in the script code:

* usage: `python department-tag-remove-rename-tagging.py`

* example: *to rename 'beanstalk' tag with 'Beanstalk' tag set* `rename_department = "beanstalk"`, `rename_value = "Beanstalk"`; *uncomment* `rename_tagging(rename_department,rename_value)`;*run script as* `python department-tag-remove-rename-tagging.py`

* by default script runs in DEBUG mode; to apply tags execute it with `"-A || --apply || --true"` argument.

**ec2-beanstalk-delete-tags.py**:
>delete tag for Beanstalk EC2 instances;

* usage: `python ec2-beanstalk-delete-tags.py --tag tagkey`

* example: *delete Env tag:*

    `python ec2-beanstalk-delete-tags.py --tag Env`

* by default script runs in DEBUG mode; to apply tags execute it with `"-A || --apply"` argument.

**ec2-instance-manual-tagging.py**:
>create (or delete) tags for instances, their volumes and network interfaces filtering resources based on instance names;

* usage: `python ec2-instance-manual-tagging.py --resources (or --servers, --instances, -I, -R, -S) RESOURCE1 --tags (or --T) TAGKEY1=TAGVALUE1 TAGKEY2=TAGVALUE2`

* example: *tag instances named dev-stepan\* (including db server) and then associated volumes named with Env and Department tags:*

    `python ec2-instance-manual-tagging.py --resources dev-stepan* --tags Env=dev Department=Development`

* by default script runs in DEBUG mode; to apply tags execute it with `"-A || --apply || --true"` argument.
* script also supports deleting tags, for that it requires `"-D || --delete"` along with `"-A || --apply || --true"` argument.

**eip-auto-tagging.py**:
>automatically apply tags for elastic ip's

* usage: `python eip-auto-tagging.py`

* by default script runs in DEBUG mode; to apply tags execute it with `"-A || --apply || --true"` argument.

**elb-auto-department-tagging.py**:
>create Department tag based on Env tag for Application Load Balancers:

* usage and example: `python elb-auto-department-tagging.py`

* by default script runs in DEBUG mode; to apply tags execute it with `"-A || --apply || --true"` argument.

**elb-manual-tagging.py**:
>create custom tags for Application Load Balancers:

* usage and example: `python elb-manual-tagging.py --resources lb-kla-imp lb-kla-uat --tags Env=prd Department=Production`

* by default script runs in DEBUG mode; to apply tags execute it with `"-A || --apply || --true"` argument.

**elb-tag-instances.py**:
>script to tag instances registered with LB's:

* usage and example: `python elb-tag-instances.py`

* by default script runs in DEBUG mode; to apply tags execute it with `"-A || --apply || --true"` argument.

**eni-auto-tagging.py**:
>automatically apply tags for elastic ip's

* usage: `python eni-auto-tagging.py`

* by default script runs in DEBUG mode; to apply tags execute it with `"-A || --apply || --true"` argument.

**name-manual-tagger.py**:
>create tags for instances/images/snapshots/volumes/enis based on a provided resource name;

* usage: `python name-manual-tagger.py --resources (or --names, -R, -N) RESOURCE1 --tags (or --T) TAGKEY1=TAGVALUE1 TAGKEY2=TAGVALUE2`

* example: *tag resources containing \*stepan\* in name with Owner tag:*

    `python name-manual-tagger.py --resources *stepan* --tags Owner=slitsevych`

* by default script runs in DEBUG mode; to apply tags execute it with `"-A || --apply || --true"` argument.
* script also supports deleting tags, for that it requires `"-D || --delete"` along with `"-A || --apply || --true"` argument.

**sg-auto-tagging.py**:
>automatically apply tags for security groups

* usage: `python sg-auto-tagging.py`

* by default script runs in DEBUG mode; to apply tags execute it with `"-A || --apply || --true"` argument.

**snapshot-auto-tagging.py**:
>automatically apply tags for snapshots without tags based on tags from volumes; also tags snapshots with unknown volume

* usage and example: `python snapshot-auto-tagging.py`

* by default script runs in DEBUG mode; to apply tags execute it with `"-A || --apply || --true"` argument.

**snapshot-manual-tagging.py**:
>create tags for snapshots based on their names and tags of associated volumes:

* usage and example: `python snapshot-manual-tagging.py --resources RESOURCE1`

* example: *tag snapshots named metco-kla\* (includes db server) with tags derived from associated volumes:*

    `python snapshot-manual-tagging.py --resources metco-kla*`

* by default script runs in DEBUG mode; to apply tags execute it with `"-A || --apply || --true"` argument.

**target-group-auto-tagging.py**:
>automatically apply tags for Target Groups of Load Balancers:

* usage and example: `python target-group-auto-tagging.py`

* by default script runs in DEBUG mode; to apply tags execute it with `"-A || --apply || --true"` argument.

**target-group-manual-tagging.py**:
>apply tags for Target Groups of specified Load Balancers:

* usage: `python target-group-manual-tagging.py --lb LB_NAME`

* usage: *tag target groups associated with `lb-pince` load balancer with current LB tags;*

    `python target-group-manual-tagging.py --lb lb-pince`

* by default script runs in DEBUG mode; to apply tags execute it with `"-A || --apply || --true"` argument.

**volume-auto-tagging.py**:
>automatically apply tags for volumes without tags or without Department tag:

* usage and example: `python volume-auto-tagging.py`

* by default script runs in DEBUG mode; to apply tags execute it with `"-A || --apply || --true"` argument.

**volume-manual-tagging.py**:
>create tags for volumes based on EC2 instance name:

* usage and example: `python volume-manual-tagging.py --resources RESOURCE1`

* example: *tag volumes of instances named dev-stepan\* (includes db server) with current instance tags:*

    `python volume-manual-tagging.py --resources dev-stepan*`

* by default script runs in DEBUG mode; to apply tags execute it with `"-A || --apply || --true"` argument.
