from django.http import HttpResponse
from django.shortcuts import render
from datarefresher.models import Inbound
from datetime import datetime
from datarefresher.models import Server
import pandas as pd
import json, requests, uuid, random
from django.shortcuts import get_object_or_404


def add_inbound(request):
    server_id = 3
    server = get_object_or_404(Server, name="ir33")

    s = requests.Session()
    url = server.url + "login"
    payload = f'username={server.user_name}&password={server.password}'
    headers = {'Content-Type': 'application/x-www-form-urlencoded',}
    response = s.request("POST", url, headers=headers, data=payload)

    if not response.ok:
        return HttpResponse(f'login failed{server.name}')

    # Make another request using the same session
    url = server.url + "xui/inbound/add"

    random_id = str(uuid.uuid4())
    random_port = random.randint(1024, 65535)
    user_remark = "test_user2"
    # url = "https://ir33.yaqoot.top:8080/xui/inbound/add"

    settings = {
        "clients": [
            {
                "id": random_id,
                "alterId": 0
            }
        ],
        "disableInsecureEncryption": False
    }

    streamSettings = {
        "network": "tcp",
        "security": "tls",
        "tlsSettings": {
            "serverName": server.url,
            "certificates": [
                {
                    "certificateFile": "/root/cert.crt",
                    "keyFile": "/root/private.key"
                }
            ]
        },
        "tcpSettings": {
            "header": {
                "type": "none"
            }
        }
    }

    sniffing = {
        "enabled": True,
        "destOverride": [
            "http",
            "tls"
        ]
    }

    payload = {
        "up": 0,
        "down": 0,
        "total": 32212254720,
        "remark": user_remark,
        "enable": "true",
        "expiryTime": 1694498646275,
        "listen": "",
        "port": random_port,
        "protocol": "vmess",
        "settings": json.dumps(settings),
        "streamSettings": json.dumps(streamSettings),
        "sniffing": json.dumps(sniffing)
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0"
    }

    response = s.request("POST", url, data=payload, headers=headers)

    print(response.text)
    return HttpResponse(response.text)

def inbounds_all():
    servers = Server.objects.all()
    df_all_inbounds = pd.DataFrame()
    for server in servers:
        s = requests.Session()
        url = server.url + "login"
        payload = f'username={server.user_name}&password={server.password}'
        headers = {'Content-Type': 'application/x-www-form-urlencoded',}
        response = s.request("POST", url, headers=headers, data=payload)

        if not response.ok:
            return HttpResponse(f'login failed{server.name}')

        # Make another request using the same session
        url = server.url + "xui/inbound/list"
        headers = {'Accept': 'application/json',}
        response = s.request("POST", url, headers=headers)

        json_content = json.loads(response.text)
        obj_data = json_content['obj']
        df = pd.DataFrame(obj_data)
        df['server'] = server.name
        df_all_inbounds = pd.concat([df_all_inbounds, df], ignore_index=True)
    return df_all_inbounds


def all_inbounds(request):
    now = datetime.utcnow()
    df_all_inbounds = inbounds_all()

    df_all_inbounds['is_over_traffic'] = df_all_inbounds.apply(lambda row: row['total'] < (row['up'] + row['down']), axis=1)
    df_all_inbounds['traffic'] = df_all_inbounds.apply(lambda row: (row['up'] + row['down']) / 1073741824 , axis=1)
    df_all_inbounds['total'] = df_all_inbounds.apply(lambda row: row['total'] / 1073741824 , axis=1)
    df_all_inbounds['up'] = df_all_inbounds.apply(lambda row: row['up'] / 1073741824 , axis=1)
    df_all_inbounds['down'] = df_all_inbounds.apply(lambda row: row['down'] / 1073741824 , axis=1)
    df_all_inbounds['expiry_time'] = df_all_inbounds.apply(lambda row: datetime.utcfromtimestamp(row['expiryTime'] / 1000) , axis=1)
    df_all_inbounds['is_expired'] = df_all_inbounds.apply(lambda row: row['expiry_time'] < now, axis=1)
    
    df_disabled_inbounds =  df_all_inbounds[df_all_inbounds['enable'] == False]
    df_enabled_inbounds =  df_all_inbounds[df_all_inbounds['enable'] == True]
        
    all_inbounds = df_all_inbounds.to_dict(orient='records')
    disabled_inbounds = df_disabled_inbounds.to_dict(orient='records')
    enabled_inbounds = df_enabled_inbounds.to_dict(orient='records')

    # Pass the filtered objects to a template   
    context = {'disabled_inbounds': disabled_inbounds, 'enabled_inbounds': enabled_inbounds, 'all_inbounds': all_inbounds, 'now':now}
    return render(request, 'presenter/all_inbounds.html', context)

