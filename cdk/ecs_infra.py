from aws_cdk import (
    core,
    aws_ec2 as _ec2,
    aws_ecs as _ecs,
    aws_ecs_patterns as _ecs_patterns,
    aws_ecr as _ecr,
    aws_iam as _iam,
    aws_s3 as _s3
)


class ECSInfra(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        """In this stack, we create 
        - an ECS cluster, 
        - an ECR repository,
        - a Task Definition
        - a Fargate Service
        - an S3 bucket.
        """

        # variables from context
        namespace = self.node.try_get_context('namespace')
        application = self.node.try_get_context('application')
        image_name_context = application['image-name']

        ### ECR ###
        ecr = _ecr.Repository(
            self, f"{namespace.upper()}-ECR",
            repository_name=f"{namespace}/{application['image-name']}",
            removal_policy=core.RemovalPolicy.DESTROY
        )

        ### ECS ###

        # vpc for ecs cluster
        vpc = _ec2.Vpc(
            self, "Vpc",
            max_azs=3,
            nat_gateways=1,
            cidr='10.0.0.0/16'
        )

        # ecs cluster to deploy containerized application
        cluster = _ecs.Cluster(self, "ECSCluster", vpc=vpc)

        ### Task definition ###

        # logging for taskDef
        logging = _ecs.AwsLogDriver(stream_prefix="ecs-logs")
        # task role
        taskRole = _iam.Role(
            self, "ECSTaskRole",
            role_name="EcsTaskRole",
            assumed_by=_iam.ServicePrincipal("ecs-tasks.amazonaws.com")
        )
        # ECR policy for taskDef
        executionPolicy = _iam.PolicyStatement(
            effect=_iam.Effect.ALLOW,
            resources=['*'],
            actions=[
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ]
        )
        # ECS Fargate taskDef
        taskDef = _ecs.FargateTaskDefinition(
            self, "EcsTaskdef", task_role=taskRole)
        # Add execution policy to taskDef
        taskDef.add_to_execution_role_policy(executionPolicy)
        # Add container to taskDef
        container = taskDef.add_container(
            "flask-app",
            image=_ecs.ContainerImage.from_registry("bitnami/express"),
            memory_limit_mib=256,
            cpu=256,
            logging=logging
        )
        # Add 3000 port to container. NodeJS example uses this port
        container.add_port_mappings(
            _ecs.PortMapping(
                container_port=3000,
                protocol=_ecs.Protocol.TCP
            )
        )

        ### Fargate Service ###

        # Service creation with the taskDef and ecs cluster
        fargateService = _ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "EcsService",
            cluster=cluster,
            task_definition=taskDef,
            public_load_balancer=True,
            desired_count=1,
            listener_port=80
        )

        # Scaling policies for Fargate Service
        scaling = fargateService.service.auto_scale_task_count(max_capacity=3)
        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=80,
            scale_in_cooldown=core.Duration.seconds(60),
            scale_out_cooldown=core.Duration.seconds(60)
        )

        ### S3 ###

        # S3 bucket for all cdk automation. It will be used by the Pipeline
        pipeline_bucket = _s3.Bucket(
            self, f"{namespace.upper()}-PIPELINE-ARTIFACTS",
            bucket_name=f"{namespace}-{image_name_context}-{core.Aws.ACCOUNT_ID}",
            versioned=True,
            removal_policy=core.RemovalPolicy.DESTROY,
            block_public_access=_s3.BlockPublicAccess.BLOCK_ALL,
            encryption=_s3.BucketEncryption.S3_MANAGED
        )

        # Service exporting
        self.output_props = {
            'pipeline-bucket': pipeline_bucket,
            'cluster': cluster,
            'vpc': vpc,
            'ecr': ecr,
            'fargateService': fargateService
        }

        core.CfnOutput(
            self, "LBOut",
            value=fargateService.load_balancer.load_balancer_dns_name
        )

    # pass objects to another stack
    @property
    def outputs(self):
        return self.output_props
