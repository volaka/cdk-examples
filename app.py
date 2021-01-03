#!/usr/bin/env python3

from aws_cdk import core

from cdk.s3_to_dynamodb_stack import S3ToDynamodbStack
from cdk.ecs_infra import ECSInfra
from cdk.pipeline import Pipeline
from cdk.pipeline_base import PipelineBase

props = {}

app = core.App()
namespace = app.node.try_get_context('namespace')

S3ToDynamodbStack(app, "s3-to-dynamodb")

ecs_infra = ECSInfra(app, f"{namespace}-container-infra")
props['container-infra'] = ecs_infra.outputs

pipeline_base = PipelineBase(app, f"{namespace}-pipeline-base", props)
# pipeline_base.add_dependency(container_infra_stack)
props['pipeline-base'] = pipeline_base.outputs

# pipeline stack
pipeline = Pipeline(app, f"{namespace}-pipeline", props)
# pipeline.add_dependency(pipeline_base)

app.synth()
