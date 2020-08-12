# devops-bot

## Overview
![](assets/DevOps%20Bot%20-%20AWS%20Overview.png)

## File structure
```
.
├── assets                                          <- images
├── client                                          <- client code
│   ├── main.py
│   ├── Pipfile
│   ├── Pipfile.lock
│   └── sounds                                      <- sounds folder
│       ├── mario
│       └── orc
├── README.md                                       <- this file
└── server                                          <- server side components
    ├── main.yaml                                   < server side cloudformation template
    ├── Pipfile
    ├── Pipfile.lock
    └── src                                         <- server side code
        ├── config.py
        ├── main_forwarder.py
        ├── main_webhook.py
        └── main_websocket.py

```

## Server Side Components

### API Gateway
There's 2 API Gateway

#### WebSocket
This is where client made websocket connection to. All websocket events are handled by the websocket lambda

### Webhook
This is meant receive webhook calls from the internet. It's handled by the webhook lambda

## Lambda

### WebSocket
This lambda handles all the websocket activities and store connected client-id in DynamoDB

### Webhook
This lambda received the webhook calls and send the payload to each connected client via API Gateway

### Forwarder
This lambda is used to forward events from another AWS account to the webhook lambda

## Client Side Components
Client side consist of a simple websocket client which receive event payload from the server side and plays sound according to the content
