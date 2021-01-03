# -*- coding: utf-8 -*-

import csv
import json
import logging
import os
import uuid
import boto3
from urllib.parse import unquote_plus


# Initializing s3 client
s3_client = boto3.client('s3')

# Initializing Logger
LOGGER = logging.getLogger()
LOGGER.setLevel(level=os.getenv('LOG_LEVEL', 'DEBUG').upper())


def convert_csv_to_json_list(file):
    """This function takes a csv file and
    converts it to an array of items (which are rows)

    Keyword Arguments:
        file -- csv file to convert
    """

    LOGGER.info("Converting csv to json.")
    items = []
    with open(file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            items.append(row)
    LOGGER.info("Conversion completed.")
    return items


def batch_write(items):
    """This function takes an array of entries and
    saves them into DynamoDB.
    The TableName is configured through environment variable.

    Keyword Arguments:
        items -- Array of entries
    """

    LOGGER.info(f"Writing to DynamoDB table: {os.environ.get('TABLE_NAME')}")

    # Configure dynamodb table
    dynamodb = boto3.resource('dynamodb')
    db = dynamodb.Table(os.environ.get('TABLE_NAME'))

    # Write to db with batch writing for a better performance
    with db.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
    LOGGER.info("CSV file was successfully written to DynamoDB.")


def lambda_handler(event, context):
    """This function will be triggered by an S3 create event.
    It takes an event and validates it. If the event has one or more 'Records',
    it downloads the csv file from the S3 Bucket and tries to save it to the DynamoDB.
    If it successfully saves the records to DynamoDB, it returns with a 200 code,
    if the record is malformed, it will return wit 400.

    Keyword Arguments:
        event -- Event of S3 Bucket Create Notification
    """

    # Validate event argument
    if event is not None and isinstance(event['Records'], list):
        LOGGER.info(f"received_event:{event['Records'][0]['s3']}")
    else:
        LOGGER.error("Event is malformed.")
        return {
            "statusCode": 400,
            "body": json.dumps({
                "message": "Event is malformed."
            })
        }

    # Loop in event's Records
    for record in event['Records']:

        # Get the bucket name
        bucket = record['s3']['bucket']['name']

        # Get the object key
        key = unquote_plus(record['s3']['object']['key'])
        LOGGER.info(f"Bucket is '{bucket}' and Key is '{key}'.")

        # Set download path
        tmpkey = key.replace('/', '')
        download_path = '/tmp/{}{}'.format(uuid.uuid4(), tmpkey)
        LOGGER.info(f"Downloading to: '{download_path}'")

        # Download the file from S2 Bucket
        s3_client.download_file(bucket, key, download_path)
        LOGGER.info(f"Download completed: '{download_path}'")

        # Convert CSV file to an array of rows
        json_data = convert_csv_to_json_list(download_path)

        # Write to DynamoDB
        batch_write(json_data)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "CSV file was successfully written to DynamoDB."
        })
    }
