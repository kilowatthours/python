# Ansible playbook installing AWSlogs agent

Installation of awslogs agent allows to inject an required awslogs configuration via "defaults" variables: roles/awslogs-agent/defaults/main.yml:

1. **CW Log Group name is a hostname of an instance**

2. **CW Log Stream names correlate with names of different prophet logs**.
Example of this structure is here: `Log groups->dev-stepan.baxterplanning.com`
I've decided to use this kind of structure in order to get rid of issues with sending multiple logs into the same stream (*CW throws errors when it detects that stream is already being used by other process*).

3. **Timestamp format for all logs is now (after completing *PHT-22624*):** `%Y-%m-%d %H:%M:%S.%f`
Due to the fact that CW does not support milliseconds, we had to use 6-digits microseconds and that's why we set `%f` in format.
Having this setting we fully comply with CW requirements.

**/group_vars**:
>contains specific ssh details for hosts which are discoved using inventory yaml file (as I used playbook against my test instance, I created "tag_Name_dev_stepan.yml" file with settings for connecting to the specific host):

**/inventory**:
>contains test inventory template utilizing aws_ec2 plugin: it provides an automated service discovery of EC2 instances, supports filtering and requires an active boto session (basically in our case it needs an active SAML session of an authenticated user/role with proper IAM permissions):

* usage: `ansible-inventory -i inventory/dev-stepan.aws_ec2.yml --list`

**/roles**:
>contains tasks, handler and variables for the role:

**ansible.cfg**:
>some of the default ansible settings for the playbook:

**main.yml**:
>main file of the playbook defining execution role, certain environment conditions and list of hosts:

* usage: `ansible-playbook -i inventory/dev-stepan.aws_ec2.yml main.yml` or simply `ansible-playbook main.yml`

**remove-agent.sh**:
>removes awslogs agent, use on an instance directly:

* usage: `bash remove-agent.sh`
