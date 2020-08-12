import boto3
import json
from config import *

"""
Extra IAM Policy
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowCrossAccountInvoke",
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": [
                "arn:aws:lambda:{AWS_REGION}:{AWS_ACCOUNT_ID}:function:{WEB_HOOK_FUNCTION_NAME}"
            ]
        }
    ]
}
"""


client = boto3.client("lambda")


def lambda_handler(event, context):
    client.invoke(
        FunctionName=f"arn:aws:lambda:{AWS_REGION}:{AWS_ACCOUNT_ID}:function:{WEB_HOOK_FUNCTION_NAME}",
        InvocationType="Event",
        Payload=json.dumps(event),
    )
