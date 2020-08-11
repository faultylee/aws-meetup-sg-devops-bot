import json
import boto3
import time
from config import *

session = boto3.session.Session()


def lambda_handler(event, context):
    requestContext = event.get('requestContext')
    websocket_event = {
        'message': event.get('body'),
        'connectedAt': requestContext.get('connectedAt'),
        'connectionId': requestContext.get('connectionId'),
        'eventType': requestContext.get('eventType'),
        'messageDirection': requestContext.get('messageDirection'),
    }
    dynamodb = session.client('dynamodb')

    if websocket_event['eventType'] == 'CONNECT':
        dynamodb.put_item(TableName=DDB_TABLE_NAME,
                          Item={'client-id': {
                              'S': websocket_event['connectionId']
                          },
                              'timestamp': {
                                  'N': str(int(time.time()) + (12 * 60 * 60))
                              }
                          })
    elif websocket_event['eventType'] == 'DISCONNECT':
        dynamodb.delete_item(TableName=DDB_TABLE_NAME,
                             Key={'client-id':
                                      {'S': websocket_event['connectionId']}
                                  })
    elif websocket_event['eventType'] == 'IN':
        pass
    return {
        'statusCode': 200
    }
