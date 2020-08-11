import os
from time import sleep
import asyncio
import websockets
import socket
import json
import subprocess
from rich import print, table
from datetime import datetime
import urllib

IS_RPI = os.uname()[4] == 'armv7l'

API_GATEWAY_ROOT = os.environ['API_GATEWAY_ROOT']

if IS_RPI:
    import pygame
    # The following code is to mute the noisy amplifier on startup
    # from gpiozero import LED, DigitalOutputDevice
    # amp_mute = DigitalOutputDevice(17, active_high=True, initial_value=True)

CI_START = 'ci_start'
CI_FAILED = 'ci_failed'
CI_SUCCESS = 'ci_success'

sound_root = '/home/pi/devops-bot/client/sounds/'
sound_chime = sound_root + 'effects/gchat.mp3'
account_env_mappings = {
    '123456789012': 'dev',
}
sound_mappings_ci = {
    'dev': {
        'default': {
            CI_START: 'orc/wc3-peon-says-work-work-only-.mp3',
            CI_SUCCESS: 'orc/peon-work-complete.wav',
            CI_FAILED: 'orc/PeonDeath.wav',
        }
    }
}

sound_mappings_sns = {
    'target_hit': 'mario/flagpole.mp3',
    'new_order': 'mario/coin.mp3',
    'new_customer': 'mario/stage-clear.mp3',
}


def play(sound):
    print('\t\tplaying: ', sound)
    if not IS_RPI:
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.load(sound_root + sound)
        # amp_mute.off()
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            sleep(0.1)
        sleep(0.5)
        # amp_mute.on()
        sleep(0.5)


def process_event(payload):
    aws_eventbridge_keys = ['source', 'detail-type',
                            'time', 'resources',
                            'detail', 'account']
    sns_keys = ['EventSource', 'Sns']
    sns_sub_keys = ['Message']
    if all(key in payload for key in aws_eventbridge_keys):
        account = payload['account']
        env = account_env_mappings.get(account)
        if not env:
            # Hardcoding for demo
            env = 'dev'
            # print(f'ERROR: Account {account} not found')
            # return
        sounds = sound_mappings_ci.get(env)
        if payload['source'] == 'aws.codepipeline':
            if payload['detail-type'] == 'CodePipeline Pipeline ' \
                                         'Execution State Change':
                print('\t', payload['detail-type'], ' - ',
                      payload['time'])
                codepipeline_detail_keys = ['state',
                                            'pipeline']
                if all(key in payload['detail'] for key in
                       codepipeline_detail_keys):
                    pipeline = payload['detail']['pipeline']
                    state = payload['detail']['state']
                    print(f'\t[bold green]{pipeline}:{state}[/bold green]')
                    sound_category = 'default'
                    if not IS_RPI:
                        subprocess.getoutput(
                            f'notify-send "DevOps-bot: CI {pipeline} - {state}"')
                    if state == 'STARTED':
                        play(sounds[sound_category][CI_START])
                    elif state == 'SUCCEEDED':
                        play(sounds[sound_category][CI_SUCCESS])
                    elif state == 'FAILED':
                        play(sounds[sound_category][CI_FAILED])
            else:
                print(json.dumps(payload))
        else:
            print(json.dumps(payload))
    elif 'Records' in payload:
        print('SNS: Records Count: ', len(payload['Records']))
        for record in payload['Records']:
            if all(key in record for key in sns_keys):
                sns = record['Sns']
                if all(key in sns for key in sns_sub_keys):
                    message = sns['Message']
                    timestamp = sns['Timestamp']
                    message_type = sns['Type']
                    if message:
                        tbl = table.Table()
                        tbl.add_column("Key", style="dim")
                        tbl.add_column("Value")
                        tbl.add_row('Type: ', message_type)
                        tbl.add_row('Timestamp: ', f'[bold blue]{timestamp}[/ bold blue]')
                        tbl.add_row('Message: ', message)
                        print(tbl)
                        if message in sound_mappings_sns:
                            play(sound_mappings_sns[message])
            else:
                print(json.dumps(record))
    elif 'message' in payload:
        print(json.dumps(payload))
    elif 'headers' in payload and 'body' in payload and 'requestContext' in payload:
        if 'identity' in payload['requestContext'] and 'userAgent' in \
                payload['requestContext']['identity']:
            if 'Slackbot' in payload['requestContext']['identity']['userAgent']:
                print(json.dumps(urllib.parse.parse_qs(payload['body']),
                                 indent=2))
        else:
            print(json.dumps(payload))
    else:
        print(json.dumps(payload))


async def ws_client():
    while True:
        # outer loop restarted every time the connection fails
        try:
            async with websockets.connect(API_GATEWAY_ROOT) as ws:
                while True:
                    # listener loop
                    try:
                        reply = await asyncio.wait_for(ws.recv(),
                                                       timeout=None)
                    except (asyncio.TimeoutError,
                            websockets.exceptions.ConnectionClosed):
                        try:
                            pong = await ws.ping()
                            await asyncio.wait_for(pong, timeout=5)
                            print('Ping OK, keeping connection alive...')
                            continue
                        except:
                            await asyncio.sleep(0.1)
                            break  # inner loop
                    # do stuff with reply object
                    try:
                        payload = json.loads(reply)
                        print(
                            f'[bold blue] {datetime.utcnow().isoformat()} {list(payload.keys())} [/bold blue]')
                        process_event(payload)
                    except Exception as e:
                        print('ERROR: ', reply)
                        print(e)
        except socket.gaierror:
            # log something
            continue
        except ConnectionRefusedError:
            # log something else
            continue


if __name__ == '__main__':
    print('[bold blue]Starting up[/bold blue]')
    if IS_RPI:
        pygame.mixer.init()
    asyncio.get_event_loop().run_until_complete(ws_client())
