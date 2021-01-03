from aws_cdk import (
    aws_codepipeline as _codepipeline,
    aws_codepipeline_actions as _codepipeline_actions,
    core,
    aws_codedeploy as _codedeploy,
    aws_iam as _iam
)


class Pipeline(core.Stack):
    def __init__(self, app: core.App, id: str, props, **kwargs) -> None:
        super().__init__(app, id, **kwargs)

        # variables
        # Context Variables
        namespace = self.node.try_get_context('namespace')
        application = self.node.try_get_context('application')
        image_name_context = application['image-name']
        code_branch = application['branch']

        # Services from Infra stack
        fargateService = props['container-infra']['fargateService']
        bucket = props['container-infra']['pipeline-bucket']

        # Services from PipelineBase stack
        codecommit = props['pipeline-base']['codecommit']
        codebuild = props['pipeline-base']['codebuild']

        # define the s3 artifact for stages
        source_output = _codepipeline.Artifact()
        build_output = _codepipeline.Artifact()

        ### defining the pipeline stages ###

        # code commit (source) stage
        code_commit_source_action = _codepipeline_actions.CodeCommitSourceAction(
            repository=codecommit,
            branch=code_branch,
            output=source_output,
            trigger=_codepipeline_actions.CodeCommitTrigger.POLL,
            action_name="CodeCommitSource",
            run_order=1,
            variables_namespace=f"{namespace}"
        )
        source_stage = _codepipeline.StageProps(
            stage_name="Source", actions=[code_commit_source_action])

        # code build (build) stage
        code_build_action = _codepipeline_actions.CodeBuildAction(
            action_name='DockerBuildImages',
            input=source_output,
            project=codebuild,
            run_order=1,
            outputs=[build_output]
        )
        build_stage = _codepipeline.StageProps(
            stage_name="Build", actions=[code_build_action])

        # code deploy (deploy) stage
        deploy_action = _codepipeline_actions.EcsDeployAction(
            action_name="DeployAction",
            service=fargateService.service,
            image_file=_codepipeline.ArtifactPath(
                build_output, "imagedefinitions.json")
        )
        deploy_stage = _codepipeline.StageProps(
            stage_name="Deploy", actions=[deploy_action])

        pipeline = _codepipeline.Pipeline(
            self, "Pipeline",
            pipeline_name=f"{namespace}-{image_name_context}-pipeline",
            artifact_bucket=bucket,
            cross_account_keys=False,
            stages=[
                source_stage,
                build_stage,
                deploy_stage
            ]
        )

        # give pipelinerole read write to the bucket
        bucket.grant_read_write(pipeline.role)
        pipeline.add_to_role_policy(
            _iam.PolicyStatement(
                actions=["s3:*"],
                resources=[f"{bucket.bucket_arn}"]
            )
        )

        # cfn output
        core.CfnOutput(
            self, "PipelineOut",
            description="Pipeline",
            value=pipeline.pipeline_name
        )
