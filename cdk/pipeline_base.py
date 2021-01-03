from aws_cdk import (
    aws_codebuild as _codebuild,
    core,
    aws_codecommit as _codecommit,
    aws_iam as _iam
)


class PipelineBase(core.Stack):
    def __init__(self, app: core.App, id: str, props, **kwargs) -> None:
        super().__init__(app, id, **kwargs)

        # variables

        # context variables
        namespace = self.node.try_get_context('namespace')
        application = self.node.try_get_context('application')
        image_name_context = application['image-name']
        image_tag_context = application['image-tag']

        # Services from Infra stack
        ecr = props['container-infra']['ecr']
        cluster = props['container-infra']['cluster']

        ### CODE COMMIT SERVICE REPOSITORY ###

        codecommit = _codecommit.Repository(
            self,
            "CodeCommitRepo",
            repository_name=f"{namespace}-{image_name_context}",
            description=f"Code repository for {image_name_context}"
        )

        ### CODE BUILD ###

        # Environmnet variables for CodeBuild
        ECR_REPOSITORY_URL = _codebuild.BuildEnvironmentVariable(
            value=ecr.repository_uri)
        IMAGE_NAME = _codebuild.BuildEnvironmentVariable(
            value=image_name_context)
        IMAGE_TAG = _codebuild.BuildEnvironmentVariable(
            value=image_tag_context)
        AWS_ACCOUNT_ID = _codebuild.BuildEnvironmentVariable(
            value=core.Aws.ACCOUNT_ID)

        # codebuild project meant to run in pipeline
        codebuild = _codebuild.PipelineProject(
            self, "CodeBuildDocker",
            project_name=f"{namespace}-{image_name_context}-docker-build",
            build_spec=_codebuild.BuildSpec.from_source_filename(
                filename='buildspec.yml'),
            environment=_codebuild.BuildEnvironment(privileged=True),
            environment_variables={
                'ECR_REPOSITORY_URL': ECR_REPOSITORY_URL,
                'IMAGE_NAME': IMAGE_NAME,
                'IMAGE_TAG': IMAGE_TAG,
                'AWS_ACCOUNT_ID': AWS_ACCOUNT_ID
            },
            description='Pipeline for CodeBuild',
            timeout=core.Duration.minutes(60),
        )

        # codebuild iam permissions to read write codecommit repository
        codecommit.grant_read(codebuild.role)

        # codebuild permissions to interact with ecr
        ecr.grant_pull_push(codebuild)
        codebuild.add_to_role_policy(
            _iam.PolicyStatement(
                actions=[
                    "ecs:DescribeCluster",
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:BatchGetImage",
                    "ecr:GetDownloadUrlForLayer"
                ],
                resources=[f"{cluster.cluster_arn}"]
            )
        )

        core.CfnOutput(
            self, "CodeCommitSSH",
            description="Code Commit Repository SSH URL",
            value=codecommit.repository_clone_url_ssh
        )

        self.output_props = {
            'codecommit': codecommit,
            'codebuild': codebuild
        }

    # pass objects to another stack
    @property
    def outputs(self):
        return self.output_props
