
# Welcome to CDK ECS and Lambda Examples

This is a project which has two examples.

- A stack for a lambda function, which is triggered by S3. This lambda function downloads the uploaded csv file from target S3 and writes file's content to DynamoDB.

- A stack for an ecs ci/cd pipeline. This stack creates an ecs cluster, a code pipeline which includes code commit repo, code build stage and a code deploy stage. All these three stages are connected and code commit stage is triggered by
a master branch commit.

## Prerequisites

- AWS Cli. [Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
- AWS Account (with an admin user in it. [Documentation on getting target and creating a user.](https://docs.aws.amazon.com/polly/latest/dg/setting-up.html))
- Node.js. [Installation of NVM (node version manager)](https://github.com/nvm-sh/nvm#installing-and-updating)
- IDE (VSCode of PyCharm Community are recommended. But it doesn't a must.)
- AWS CDK Toolkit.

  ```bash
  npm install -g aws-cdk
  ```

- Python. [Installation Guide](https://docs.python-guide.org/starting/installation/)

## CDK Info

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```bash
python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```bash
source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```powershell
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```bash
pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```bash
cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

### Useful commands

- `cdk bootstrap`: initialize cdk for your AWS Account.

- `cdk ls`: list all stacks in the app

- `cdk synth`: emits the synthesized CloudFormation template

- `cdk deploy`: deploy this stack to your default AWS account/region

- `cdk diff`: compare deployed stack with current state

- `cdk docs`: open CDK documentation

# Guides for Projects

First of all, clone this repo. Then create a venv and install the requirements.

```bash
git clone https://github.com/volaka/cdk-examples.git
cd cdk-examples
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

There are two projects in this repo:

- [Lambda DynamoDB Example](#Lambda---DynamoDB-Example)
- [ECS Pipeline Deployment](#ECS-Pipeline-Deployment)

## Lambda - DynamoDB Example

- **Stack File**: `./cdk/s3_to_dynamodb_stack.py`
- **Stack Lambda Assets**: `./cdk/assets`

This stack is independant from others. To run this stack:

```bash
cdk ls
cdk deploy s3-to-dynamodb
```

### Brief explanation

This stack creates:

- a Lambda function. This function contains a code (`./cdk/assets/s3_trigger.py`) which downloads an uploaded s3 file and writes it's content to DynamoDb

- a DynamoDB to hold the csv contents

- an S3 bucket for us to upload csv files.

- an S3 permission for Lambda function to access itself

- a notification on S3 to trigger the Lambda function

- a DynamoDB permission for the Lambda function to write contents.

### Notes

- The csv files id section is assumed as `guid`. So with a differend primary key, you should manipulate the context variables:

    ```python
    # ./cdk/s3_to_dynamodb_stack.py
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
    ```

    ```json
    // cdk.json ['context'] key
    "dynamodb": {
      "TABLE_NAME": "s3csv",
      "PARTITION_KEY_NAME": "guid"
    },
    ```

After you ran `cdk deploy s3-to-dynamodb` command, the output will be similar to the following:

```bash
$ cdk deploy s3-to-dynamodb
Outputs:
s3-to-dynamodb.LambdaS3StackBucket = s3-to-dynamo-db-workshop.s3.amazonaws.com
```

`s3-to-dynamo-db-workshop.s3.amazonaws.com` is the url of our bucket and `s3://s3-to-dynamo-db-workshop` is the s3 bucket url for the aws command:

```bash
aws cp <file> s3://s3-to-dynamo-db-workshop
```

When you upload a csv file to this bucket, the function will be triggered and it will write to it's contents to the database.

### Lambda Code

There are comments in the lambda function code. It is self-descriptive.

## ECS Pipeline Deployment

- **Stack Files**:
  - `./cdk/ecs_infra.py`
  - `./cdk/pipeline_base.py`
  - `./cdk/pipeline.py`

This project is to demonstrate a ci/cd pipeline using AWS services, and deploy it to an ECS Cluster. AWS CodePipeline service manages the ci/cd processes.

- **ECS Cluster** is the service to deploy containerized application.
- **ECR** is the service to store docker images
- **S3** is to store pipeline artifacts
- **AWS CodePipeline** is the service to create a ci/cd pipeline
  - **AWS CodeCommit** is the service which manages the git repo.
  - **AWS CodeBuild** is the service which manages the build processes. It is triggered by the Source -CodeCommit- stage and it builds a container image from the source and pushes the img to ECR.
  - **AWS CodeDeploy** is the service which deploys the image created by the Build -CodeBuild- stage to an ECS Cluster.

### Stacks

This project creates many services. It has 3 stacks which all manages different steps of the automation.

1. ECSInfra stack creates all the base AWS infra services.
    - an ECS cluster,
    - an ECR repository,
    - a Task Definition
    - a Fargate Service
    - an S3 bucket.
2. PipelineBase stack which manages components of the pipeline.
    - CodeCommit definitions
    - CodeBuild definitions
3. Pipeline stack creates the pipeline and add the stages to the pipeline.
    - Pipeline
    - Pipeline Actions
      - CodeCommit
      - CodeBuild
      - CodeDeploy (ECSDeployAction)

The context variables are defined in the `cdk.json` file.

### Notes

- `cdk deploy --all` to deploy all stacks.

- Once you deployed the cdk stack, you should push an application witch has a `buildspec.yaml` file. [Here](https://github.com/volaka/Factorial-Calculator) is an example application named factorial calculator. You can clone this repo and change the *remote* to the **ssh url of your codecommit service**.

- Once you changed your ssh remote, you can trigger the application pipeline by pushing to the master branch of the codecommit repo.

- To be able to push to the code commit repo, you should add your SSH Key to IAM. You can follow [this guideline](https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up-ssh-unixes.html) to add your SSH key.
