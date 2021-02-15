#!/usr/bin/python
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: ecs_service
short_description: create, terminate, start or stop a service in ecs
description:
  - Creates or terminates ecs services.
notes:
  - the service role specified must be assumable (i.e. have a trust relationship for the ecs service, ecs.amazonaws.com)
  - for details of the parameters and returns see U(http://boto3.readthedocs.org/en/latest/reference/services/ecs.html)
dependencies:
  - An IAM role must have been created
version_added: "2.1"
author: Mark Chance (@java1guy)
options:
    state:
        description:
          - The desired state of the service
        required: true
        choices: ["present", "absent", "deleting", "update"]
    name:
        description:
          - The name of the service
        required: true
    cluster:
        description:
          - The name of the cluster in which the service exists
        required: false
    task_definition:
        description:
          - The task definition the service will run
        required: false
    load_balancers:
        description:
          - The list of ELBs defined for this service
        required: false
    desired_count:
        description:
          - The count of how many instances of the service
        required: false
    deployment_config:
        description:
            - A deployment configuration dictionary describing the minimumHealthPercent and maximumPercent deployment parameters for the service
        required: false
    client_token:
        description:
          - Unique, case-sensitive identifier you provide to ensure the idempotency of the request. Up to 32 ASCII characters are allowed.
        required: false
    role:
        description:
          - The name or full Amazon Resource Name (ARN) of the IAM role that allows your Amazon ECS container agent to make calls to your load balancer on your behalf. This parameter is only required if you are using a load balancer with your service.
        required: false
    delay:
        description:
          - The time to wait before checking that the service is available
        required: false
        default: 10
    repeat:
        description:
          - The number of times to check that the service is available
        required: false
        default: 10
    wait:
        description:
            - Wait for the task to complete (stop).
        required: False
        default: no
extends_documentation_fragment:
    - aws
    - ec2
'''

EXAMPLES = '''
# Note: These examples do not set authentication details, see the AWS Guide for details.
- ecs_service:
    state: present
    name: console-test-service
    cluster: new_cluster
    task_definition: new_cluster-task:1
    desired_count: 0

# Basic provisioning example
- ecs_service:
    name: default
    state: present
    cluster: new_cluster

# Simple example to delete
- ecs_service:
    name: default
    state: absent
    cluster: new_cluster

# Setting the deployment configuratino
- ecs_service:
    state: present
    name: console-test-service
    cluster: new_cluster
    task_definition: my_task_definition
    desired_count: 1
    deployment_config:
        minimumHealthyPercent: 50
        maximumPercent: 200
'''

# Disabled the RETURN as it was breaking docs building.  Someone needs to fix
# this
RETURN = '''# '''
'''
# Create service
service: On create service, it returns the new values; on delete service, it returns the values for the service being deleted.
    clusterArn: The Amazon Resource Name (ARN) of the of the cluster that hosts the service.
    desiredCount: The desired number of instantiations of the task definition to keep running on the service.
    loadBalancers: A list of load balancer objects
        loadBalancerName: the name
        containerName: The name of the container to associate with the load balancer.
        containerPort: The port on the container to associate with the load balancer.
    pendingCount: The number of tasks in the cluster that are in the PENDING state.
    runningCount: The number of tasks in the cluster that are in the RUNNING state.
    serviceArn: The Amazon Resource Name (ARN) that identifies the service. The ARN contains the arn:aws:ecs namespace, followed by the region of the service, the AWS account ID of the service owner, the service namespace, and then the service name. For example, arn:aws:ecs:region :012345678910 :service/my-service .
    serviceName: A user-generated string used to identify the service
    status: The valid values are ACTIVE, DRAINING, or INACTIVE.
    taskDefinition: The ARN of a task definition to use for tasks in the service.
# Delete service
ansible_facts: When deleting a service, the values described above for the service prior to its deletion are returned.
'''
try:
    import boto
    import botocore
    HAS_BOTO = True
except ImportError:
    HAS_BOTO = False

try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

class EcsServiceManager:
    """Handles ECS Services"""

    def __init__(self, module):
        self.module = module

        try:
            # self.ecs = boto3.client('ecs')
            region, ec2_url, aws_connect_kwargs = get_aws_connection_info(module, boto3=True)
            if not region:
                module.fail_json(msg="Region must be specified as a parameter, in EC2_REGION or AWS_REGION environment variables or in boto configuration file")
            self.ecs = boto3_conn(module, conn_type='client', resource='ecs', region=region, endpoint=ec2_url, **aws_connect_kwargs)
        except boto.exception.NoAuthHandlerFound, e:
            self.module.fail_json(msg="Can't authorize connection - "+str(e))

    # def list_clusters(self):
    #     return self.client.list_clusters()
    # {'failures=[],
    # 'ResponseMetadata={'HTTPStatusCode=200, 'RequestId='ce7b5880-1c41-11e5-8a31-47a93a8a98eb'},
    # 'clusters=[{'activeServicesCount=0, 'clusterArn='arn:aws:ecs:us-west-2:777110527155:cluster/default', 'status='ACTIVE', 'pendingTasksCount=0, 'runningTasksCount=0, 'registeredContainerInstancesCount=0, 'clusterName='default'}]}
    # {'failures=[{'arn='arn:aws:ecs:us-west-2:777110527155:cluster/bogus', 'reason='MISSING'}],
    # 'ResponseMetadata={'HTTPStatusCode=200, 'RequestId='0f66c219-1c42-11e5-8a31-47a93a8a98eb'},
    # 'clusters=[]}

    def find_in_array(self, array_of_services, service_name, field_name='serviceArn'):
        for c in array_of_services:
            if c[field_name].endswith(service_name):
                return c
        return None

    def describe_service(self, cluster_name, service_name):
        response = self.ecs.describe_services(
            cluster=cluster_name,
            services=[
                service_name
        ])
        msg = ''
        if len(response['failures'])>0:
            c = self.find_in_array(response['failures'], service_name, 'arn')
            msg += ", failure reason is "+c['reason']
            if c and c['reason']=='MISSING':
                return {}
            # fall thru and look through found ones
        if len(response['services'])>0:
            c = self.find_in_array(response['services'], service_name)
            if c:
                return c
        raise StandardError("Unknown problem describing service %s." % service_name)

    def create_service(self, service_name, cluster_name, task_definition,
        load_balancers, desired_count, client_token, role, deployment_config):
        response = self.ecs.create_service(
            cluster=cluster_name,
            serviceName=service_name,
            taskDefinition=task_definition,
            loadBalancers=load_balancers,
            desiredCount=desired_count,
            clientToken=client_token,
            role=role,
            deploymentConfiguration=deployment_config)
        if wait:
            """Waits for service to become stable"""
            waiter = self.ecs.get_waiter('services_stable')
            waiter.wait(cluster=cluster_name, services=[ service_name ])
            response['service'] = self.describe_service(cluster_name, service_name)
        service = response['service']
        return service

    def update_service(self, service_name, cluster_name, task_definition, desired_count, deployment_config, wait):
        response = self.ecs.update_service(
            cluster=cluster_name,
            service=service_name,
            taskDefinition=task_definition,
            desiredCount=desired_count,
            deploymentConfiguration=deployment_config)
        if wait:
            """Waits for service to become stable"""
            waiter = self.ecs.get_waiter('services_stable')
            waiter.wait(cluster=cluster_name, services=[ service_name ])
            response['service'] = self.describe_service(cluster_name, service_name)
        service = response['service']
        return service

    def delete_service(self, service, cluster=None):
        return self.ecs.delete_service(cluster=cluster, service=service)

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime.datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError ("Type not serializable")

def fix_datetime(result):
    """Temporary fix to convert datetime fields from Boto3 to datetime string."""
    """See https://github.com/ansible/ansible-modules-extras/issues/1348."""
    """Not required for Ansible 2.1"""
    return json.loads(json.dumps(result, default=json_serial))

def main():

    argument_spec = ec2_argument_spec()
    argument_spec.update(dict(
        state=dict(required=True, choices=['present', 'absent', 'deleting', 'update'] ),
        name=dict(required=True, type='str' ),
        cluster=dict(required=False, type='str' ),
        task_definition=dict(required=False, type='str' ),
        load_balancers=dict(required=False, type='list' ),
        deployment_config=dict(required=False, type='dict'),
        desired_count=dict(required=False, type='int' ),
        client_token=dict(required=False, type='str' ),
        role=dict(required=False, type='str' ),
        delay=dict(required=False, type='int', default=10),
        repeat=dict(required=False, type='int', default=10),
        wait=dict(required=False, type='bool', default=True)
    ))

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    if not HAS_BOTO:
      module.fail_json(msg='boto is required.')

    if not HAS_BOTO3:
      module.fail_json(msg='boto3 is required.')
    
    if module.params['state'] == 'update':
        update_params = [module.params.get(key) for key in ['task_definition', 'desired_count', 'deployment_config']]
        if update_params.count(None) == len(update_params):
            module.fail_json(msg="To update a service, you must specify one of task_definition, desired_count or deployment_config")
    else:
        if not module.params.get('task_definition'):
            module.fail_json(msg="To use create a service, a task_definition must be specified")
        if not module.params.get('desired_count'):
            module.fail_json(msg="To use create a service, a desired_count must be specified")
                
    service_mgr = EcsServiceManager(module)
    try:
        existing = service_mgr.describe_service(module.params['cluster'], module.params['name'])
    except Exception, e:
        module.fail_json(msg="Exception describing service '"+module.params['name']+"' in cluster '"+module.params['cluster']+"': "+str(e))

    # Check service exists and is active for updates
    if (not existing or existing.get('status') != "ACTIVE") and module.params['state'] == 'update':
        module.fail_json(msg="Service was not found or is not active.")

    results = dict(changed=False)
    if module.params['state'] == 'present':
        if existing and existing.get('status') == "ACTIVE":
            results['service']=existing
        else:
            if not module.check_mode:
                if existing.get('status') != "ACTIVE":
                    existing={}
                loadBalancers = module.params.get('load_balancers') or []
                role = module.params.get('role') or ''
                desiredCount = module.params.get('desired_count')
                taskDefinition = module.params.get('task_definition')
                deploymentConfig = module.params.get('deployment_config')
                clientToken = module.params.get('client_token') or ''
                wait = module.params.get('wait')

                # Service doesn't exist or is inactive so create the service
                response = fix_datetime(service_mgr.create_service(module.params['name'],
                    module.params['cluster'],
                    taskDefinition,
                    loadBalancers,
                    desiredCount,
                    clientToken,
                    role,
                    deploymentConfig,
                    wait))
                results['service'] = response
            results['changed'] = True

    elif module.params['state'] == 'update':
        if not module.check_mode:
            loadBalancers = module.params.get('load_balancers') or []
            desiredCount = module.params.get('desired_count') or existing.get('desiredCount')
            taskDefinition = module.params.get('task_definition') or existing.get('taskDefinition')
            deploymentConfig = module.params.get('deployment_config') or existing.get('deploymentConfiguration')
            wait = module.params.get('wait') 
            response = fix_datetime(service_mgr.update_service(module.params['name'],
                module.params['cluster'],
                taskDefinition,
                desiredCount,
                deploymentConfig,
                wait))
            results['service'] = response
        results['changed'] = True

    elif module.params['state'] == 'absent':
        if not existing:
            pass
        else:
            # it exists, so we should delete it and mark changed.
            # return info about the cluster deleted
            del existing['deployments']
            del existing['events']
            results['ansible_facts'] = existing
            if 'status' in existing and existing['status']=="INACTIVE":
                results['changed'] = False
            else:
                if not module.check_mode:
                    try:
                        fix_datetime(service_mgr.delete_service(
                            module.params['name'],
                            module.params['cluster']
                        ))
                    except botocore.exceptions.ClientError, e:
                        module.fail_json(msg=e.message)
                results['changed'] = True

    elif module.params['state'] == 'deleting':
        if not existing:
            module.fail_json(msg="Service '"+module.params['name']+" not found.")
            return
        # it exists, so we should delete it and mark changed.
        # return info about the cluster deleted
        delay = module.params['delay']
        repeat = module.params['repeat']
        time.sleep(delay)
        for i in range(repeat):
            existing = service_mgr.describe_service(module.params['cluster'], module.params['name'])
            status = existing['status']
            if status == "INACTIVE":
                results['changed'] = True
                break
            time.sleep(delay)
        if i is repeat-1:
            module.fail_json(msg="Service still not deleted after "+str(repeat)+" tries of "+str(delay)+" seconds each.")
            return

    module.exit_json(**results)

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.ec2 import *

if __name__ == '__main__':
    main()