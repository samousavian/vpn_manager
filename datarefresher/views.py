from django.db import IntegrityError
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.conf import settings
from concurrent.futures import ThreadPoolExecutor
from .models import Inbound, Server
import json, uuid, requests
import pandas as pd


def login(server):
    s = requests.Session()
    url = server.url + "login"
    payload = f'username={server.user_name}&password={server.password}'
    headers = {'Content-Type': 'application/x-www-form-urlencoded',}
    response = s.request("POST", url, headers=headers, data=payload)
    if response.ok:
        return s
    else:
        return False


import requests
from requests.exceptions import ConnectionError
# ... other imports ...

def inbounds_all():
    servers = Server.objects.all()
    df_all_inbounds = pd.DataFrame()
    for server in servers:
        server_id = server.id
        # s = login(server)
        s = requests.Session()
        url = server.url + "login"
        payload = f'username={server.user_name}&password={server.password}'
        headers = {'Content-Type': 'application/x-www-form-urlencoded',}
        try:
            response = s.request("POST", url, headers=headers, data=payload)
            # Check if login was successful
            if not response.ok:
                return HttpResponse("login failed")

            # Make another request using the same session
            url = server.url + "xui/inbound/list"
            headers = {'Accept': 'application/json',}
            response = s.request("POST", url, headers=headers)

            json_content = json.loads(response.text)
            obj_data = json_content['obj']
            df = pd.DataFrame(obj_data)
            df['server'] = server.name
            df_all_inbounds = pd.concat([df_all_inbounds, df], ignore_index=True)
        except ConnectionError as ce:
            return HttpResponse(f"Connection error occurred: {ce}")
        except Exception as e:
            return HttpResponse(f"An error occurred: {e}")
    return df_all_inbounds


def save_inbounds(df_output, server_id):
    server = Server.objects.get(pk=server_id)
    # Iterate over the rows and create or update objects
    for index, row in df_output.iterrows():
        settings = json.loads(row['settings'])
        uuid_value = uuid.UUID(settings['clients'][0]['id'])

        # Get or create the record based on the uuid
        try:
            data, created = Inbound.objects.get_or_create(
                uuid=uuid_value,
                defaults={
                    'server': server,
                    'id': row['id'],
                    'up': row['up'],
                    'down': row['down'],
                    'total': row['total'],
                    'remark': row['remark'],
                    'enable': row['enable'],
                    'expiry_time': row['expiryTime'],
                    'listen': row['listen'],
                    'port': row['port'],
                    'protocol': row['protocol'],
                    'settings': row['settings'],
                    'stream_settings': row['streamSettings'],
                    'tag': row['tag'],
                    'sniffing': row['sniffing'],
                }
            )

            if not created:
                # Update the existing record
                data.id = row['id']
                data.up = row['up']
                data.down = row['down']
                data.total = row['total']
                data.remark = row['remark']
                data.enable = row['enable']
                data.expiry_time = row['expiryTime']
                data.listen = row['listen']
                data.port = row['port']
                data.protocol = row['protocol']
                data.settings = row['settings']
                data.stream_settings = row['streamSettings']
                data.tag = row['tag']
                data.sniffing = row['sniffing']
                data.save()
        except IntegrityError as e:
            print(f"An integrity error occurred: {e}")