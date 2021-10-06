# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
from aws_cdk import (
    aws_ec2 as _ec2,
    aws_ecs as _ecs,
    aws_rds as _rds,
    aws_efs as _efs,
    aws_ecr_assets as _ecr_assets,
    aws_elasticloadbalancingv2 as _elbv2,
    aws_logs as _logs,
    aws_iam as _iam,
    aws_secretsmanager as _sm,
    core as cdk
)

class MoodleApplicationStackProperties:

    def __init__(
            self,
            vpc: _ec2.Vpc,
            loadbalancer: _elbv2.ApplicationLoadBalancer,
            database: _rds.DatabaseInstance,
            filesystem: _efs.FileSystem,
    ) -> None:

        self.vpc = vpc
        self.loadbalancer = loadbalancer
        self.database = database
        self.filesystem = filesystem

class MoodleApplicationStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str,
                 properties: MoodleApplicationStackProperties, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

         # set container image
        docker_build_path = os.path.dirname(__file__) + "../../src"
        moodle_image =_ecr_assets.DockerImageAsset(
            self, "MoodleImage",
            directory=docker_build_path,
            file="Docker.moodle",
        )

        # define ecs cluster with container insights
        moodle_cluster = _ecs.Cluster(
            self, 'MoodleCluster',
            vpc=properties.vpc,
            container_insights=True,            
        )

        # mount efs in ecs cluster
        moodle_volume = _ecs.Volume(
            name="MoodleVolume",
            efs_volume_configuration=_ecs.EfsVolumeConfiguration(
                file_system_id=properties.filesystem.file_system_id
            )
        )

        # define task execution role and attach ECSTaskExecutionRole managed policy
        taskRole = _iam.Role(self, "MoodleTaskExecutionRole", assumed_by=_iam.ServicePrincipal("ecs-tasks.amazonaws.com"))
        taskRole.add_managed_policy(_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy"))

        # set task definition with 1 vCPU and 2GB RAM     
        task = _ecs.FargateTaskDefinition(
            self, "MoodleTaskDefinition",
            volumes=[moodle_volume],cpu=1024,memory_limit_mib=2048,
            task_role=taskRole, 
        )
     
        # define container with logging enabled
        container = task.add_container(
            "MoodleImage",
            environment={
                'MOODLE_USERNAME': "admin",                
                'MOODLE_PASSWORD': "initialch@ngeit",
                'MOODLE_EMAIL': "admin@localhost.localdomain",
                'MOODLE_DATABASE_TYPE': 'mysqli',
                'ALLOW_EMPTY_PASSWORD':'no',
                'BITNAMI_DEBUG':'false',
                'MOODLE_DATABASE_HOST':properties.database.db_instance_endpoint_address,
                'MOODLE_DATABASE_PORT_NUMBER':properties.database.db_instance_endpoint_port,
                'PHP_ENABLE_OPCACHE':"yes"
            },
            secrets={                
                'MOODLE_DATABASE_NAME':
                    _ecs.Secret.from_secrets_manager(properties.database.secret, field="dbname"),
                'MOODLE_DATABASE_USER':
                    _ecs.Secret.from_secrets_manager(properties.database.secret, field="username"),
                'MOODLE_DATABASE_PASSWORD':
                    _ecs.Secret.from_secrets_manager(properties.database.secret, field="password")                   
            },
            image=_ecs.ContainerImage.from_docker_image_asset(moodle_image),
            logging=_ecs.LogDrivers.aws_logs(stream_prefix="ecs-cdk-moodle", log_retention=_logs.RetentionDays.FIVE_DAYS)
        )

        # define mount point to /bitnami
        moodle_mount_point = _ecs.MountPoint(
            read_only=False,
            container_path="/bitnami",
            source_volume=moodle_volume.name
        )
        
        # add mount point to container 
        container.add_mount_points(moodle_mount_point)

        # set mapping port in container
        container.add_port_mappings(
            _ecs.PortMapping(container_port=8080)
        )

        # create ecs service in Fargate mode with execute command enabled  
        service = _ecs.FargateService(
            self, "MoodleFargateService",
            task_definition=task,
            platform_version=_ecs.FargatePlatformVersion.VERSION1_4,
            cluster=moodle_cluster,
            desired_count=1,
            health_check_grace_period=cdk.Duration.seconds(900),
            enable_execute_command=True,
        )

        # set ecs auto scale mix and max capacity
        autoscale = service.auto_scale_task_count(
            min_capacity=1,
            max_capacity=4
        )

        # define ecs auto scale based on cpu utilization of 75%
        autoscale.scale_on_cpu_utilization(
            "MoodleAutoscale",
            target_utilization_percent=75,
            scale_in_cooldown=cdk.Duration.seconds(300),
            scale_out_cooldown=cdk.Duration.seconds(300),
        )

        #configure security groups
        service.connections.allow_to(other=properties.database, port_range=_ec2.Port.tcp(3306))
        service.connections.allow_to(other=properties.filesystem, port_range=_ec2.Port.tcp(2049))
        service.connections.allow_from(other=properties.loadbalancer, port_range=_ec2.Port.tcp(80))      

        # refer to existing certificate by arn
        #cert = _cm.Certificate.from_certificate_arn(self, "cert","arn:aws:acm:*:*:certificate/*")

        # set load balancer listener on port 80/443
        http_listener = properties.loadbalancer.add_listener(
            "MoodleHttpListener",
            port=80,
            #certificates=[cert]
        )

        # add load balancer target and health checks with threshold values
        http_listener.add_targets(
            "MoodleHttpServiceTarget",
            protocol=_elbv2.ApplicationProtocol.HTTP,
            targets=[service],
            health_check=_elbv2.HealthCheck(healthy_http_codes="200-299,301,302",
            healthy_threshold_count=3,
            unhealthy_threshold_count=2,            
            interval=cdk.Duration.seconds(10))
        )

        # output load balancer dns
        cdk.CfnOutput(
            self, "MoodleLoadBalancerDNSName",
            value=properties.loadbalancer.load_balancer_dns_name
        )
