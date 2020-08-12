import asyncio
import json
import os
import socket
import subprocess
import urllib
from datetime import datetime
from time import sleep

import pygame
import websockets
from rich import print, table

IS_RPI = True  # os.uname()[4] == 'armv7l'

WEBSOCKET_URL = os.environ["WEBSOCKET_URL"]

amp_mute_control = None
# The following code is to mute the noisy amplifier on startup
# if IS_RPI:
#     # from gpiozero import LED, DigitalOutputDevice
#     amp_mute_control = DigitalOutputDevice(17, active_high=True, initial_value=True)

CI_START = "STARTED"
CI_FAILED = "FAILED"
CI_SUCCESS = "SUCCEEDED"

sound_root = "./sounds/"

# Not used for demo
account_env_mappings = {
    "123456789012": "dev",
}
sound_mappings_ci = {
    "dev": {
        "default": {
            CI_START: "orc/wc3-peon-says-work-work-only-.mp3",
            CI_SUCCESS: "orc/peon-work-complete.wav",
            CI_FAILED: "orc/PeonDeath.wav",
        }
    }
}

sound_mappings_sns = {
    "target_hit": "mario/flagpole.mp3",
    "new_order": "mario/coin.mp3",
    "new_customer": "mario/stage-clear.mp3",
}

aws_eventbridge_keys = [
    "source",
    "detail-type",
    "time",
    "resources",
    "detail",
    "account",
]
sns_keys = ["Message"]
webhook_keys = ["headers", "body", "requestContext"]


def play_sound(sound):
    print("\tplaying: ", sound)
    if not IS_RPI:
        return

    pygame.mixer.music.set_volume(1.0)
    pygame.mixer.music.load(sound_root + sound)
    if amp_mute_control:
        amp_mute_control.off()
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        sleep(0.1)
    sleep(0.5)
    if amp_mute_control:
        amp_mute_control.on()
    sleep(0.5)


def process_event(payload):
    if all(key in payload for key in aws_eventbridge_keys):
        account = payload["account"]
        env = account_env_mappings.get(account)
        if not env:
            # Hardcoding for demo
            env = "dev"
        sounds = sound_mappings_ci.get(env)
        event_source = payload["source"]
        if (
            event_source == "aws.codepipeline"
            and payload["detail-type"] == "CodePipeline Pipeline Execution State Change"
        ):
            print("\t", payload["detail-type"], " - ", payload["time"])
            codepipeline_detail_keys = {"state", "pipeline"}
            if not all(key in payload["detail"] for key in codepipeline_detail_keys):
                return

            pipeline = payload["detail"]["pipeline"]
            state = payload["detail"]["state"]
            print(f"\t[bold green]{pipeline}:{state}[/bold green]")
            sound_category = "default"

            if not IS_RPI:
                # for local desktop notification
                subprocess.getoutput(
                    f'notify-send "DevOps-bot: CI {pipeline} - {state}"'
                )

            if state in sounds[sound_category]:
                play_sound(sounds[sound_category][state])
        else:
            print(f"[bold red]Unknown Event Source[/bold red]: {event_source}")
            print(json.dumps(payload))
    elif "Records" in payload:
        print("[bold red]SNS[/bold red]: Records Count: ", len(payload["Records"]))
        for record in payload["Records"]:
            sns = record.get("Sns")

            if not sns:
                continue

            if any(key not in sns for key in sns_keys):
                continue

            message = sns["Message"]
            if not message:
                continue

            timestamp = sns["Timestamp"]
            message_type = sns["Type"]
            tbl = table.Table()
            tbl.add_column("Key", style="dim")
            tbl.add_column("Value")
            tbl.add_row('Type: ', message_type)
            tbl.add_row('Timestamp: ', f'[bold blue]{timestamp}[/ bold blue]')
            tbl.add_row('Message: ', message)
            print(tbl)
            if message in sound_mappings_sns:
                play_sound(sound_mappings_sns[message])
    elif "message" in payload:
        print("[bold red]Message[/bold red]")
        print(json.dumps(payload))
    elif all(key in payload for key in webhook_keys):
        if (
            "identity" in payload["requestContext"]
            and "userAgent" in payload["requestContext"]["identity"]
        ):
            if "Slackbot" in payload["requestContext"]["identity"]["userAgent"]:
                print("Slack Webhook")
                print(json.dumps(urllib.parse.parse_qs(payload["body"]), indent=2))
            else:
                print("[bold red]Unknown Webhook[/bold red]")
                print(json.dumps(payload))
        else:
            print("[bold red]Unknown Webhook[/bold red]")
            print(json.dumps(payload))
    else:
        print("[bold red]Unknown[/bold red]")
        print(json.dumps(payload))


async def ws_client():
    while True:
        # outer loop restarted every time the connection fails
        try:
            async with websockets.connect(WEBSOCKET_URL) as ws:
                while True:
                    # listener loop
                    try:
                        reply = await asyncio.wait_for(ws.recv(), timeout=None)
                    except (
                        asyncio.TimeoutError,
                        websockets.exceptions.ConnectionClosed,
                    ):
                        try:
                            pong = await ws.ping()
                            await asyncio.wait_for(pong, timeout=5)
                            print("Ping OK, keeping connection alive...")
                            continue
                        except:
                            await asyncio.sleep(0.1)
                            break  # inner loop
                    try:
                        payload = json.loads(reply)
                        print(
                            f"[bold blue]{datetime.utcnow().isoformat()}"
                            f" {list(payload.keys())} [/bold blue]"
                        )
                        process_event(payload)
                    except Exception as e:
                        print("ERROR: ", reply)
                        print(e)
        except socket.gaierror:
            continue
        except ConnectionRefusedError:
            continue


if __name__ == "__main__":
    print("[bold blue]Starting up[/bold blue]")
    if IS_RPI:
        pygame.mixer.init()
    asyncio.get_event_loop().run_until_complete(ws_client())
