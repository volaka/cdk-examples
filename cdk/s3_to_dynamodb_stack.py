from aws_cdk import (
    core,
    aws_lambda as _lambda,
    aws_logs as _logs,
    aws_s3 as _s3,
    aws_s3_notifications as _s3_notifications,
    aws_dynamodb as _dynamodb
)


class S3ToDynamodbStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get the DynamoDB environment variables from context
        DYNAMODB_ENV = self.node.try_get_context('dynamodb')

        # Create lambda function. It gets the code from the ./assets folder
        from_s3_to_dynamo_db_function = _lambda.Function(
            self, "FromS3ToDynamoDBFunction",
            function_name="from-s3-to-dynamodb",
            runtime=_lambda.Runtime.PYTHON_3_7,
            handler="s3_trigger.lambda_handler",
            code=_lambda.Code.asset("./cdk/assets"),
            timeout=core.Duration.seconds(3),
            reserved_concurrent_executions=1,
            environment={
                'LOG_LEVEL': 'INFO',
                'TABLE_NAME': DYNAMODB_ENV['TABLE_NAME']
            }
        )

        # create log group to manage it with cdk
        _logs.LogGroup(
            self,
            "FromS3ToDynamoDBLogGroup",
            log_group_name=f"/aws/lambda/{from_s3_to_dynamo_db_function.function_name}",
            removal_policy=core.RemovalPolicy.DESTROY
        )

        # create s3 bucket with encryption, versioning and blocked public access
        s3_to_dynamo_db_bucket = _s3.Bucket(
            self,
            "S3ToDynamoDBBucket",
            bucket_name="s3-to-dynamo-db-workshop",
            encryption=_s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            block_public_access=_s3.BlockPublicAccess.BLOCK_ALL
        )

        # Grant read access to Lambda Function to access S3 Bucket
        s3_to_dynamo_db_bucket.grant_read(from_s3_to_dynamo_db_function)

        # Create s3 notification for lambda function
        notification = _s3_notifications.LambdaDestination(
            from_s3_to_dynamo_db_function)

        # Assign notification for the s3 event type
        s3_to_dynamo_db_bucket.add_event_notification(
            _s3.EventType.OBJECT_CREATED,
            notification,
            _s3.NotificationKeyFilter(suffix='.csv')
        )

        # Create DynamoDb table
        dynamo_db = _dynamodb.Table(
            self,
            'FromS3ToDynamoDBTable',
            table_name=DYNAMODB_ENV['TABLE_NAME'],
            billing_mode=_dynamodb.BillingMode.PAY_PER_REQUEST,
            partition_key=_dynamodb.Attribute(
                name=DYNAMODB_ENV['PARTITION_KEY_NAME'],
                type=_dynamodb.AttributeType.STRING
            )
        )

        # Grant full access to Lambda Function to access DynamoDb
        dynamo_db.grant_full_access(from_s3_to_dynamo_db_function)
