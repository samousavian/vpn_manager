from django.http import HttpResponse
from django.shortcuts import render, redirect
import numpy as np
from datetime import datetime
from .models import Server, Seller
import pandas as pd
import json, requests, uuid, random
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, login, logout


class ServerLoginError(Exception):
    pass


def add_inbound(request):
    if request.user.is_staff:
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
    else:
        return HttpResponse("You Shall Not Pass!!")


def profile(request, server_name, email):
    now = datetime.utcnow()
    server = Server.objects.filter(name=server_name)

    df = get_clients(servers=server)

    filtered_df = df.loc[df['email'] == email]
    filtered_data = filtered_df.to_dict('records')
    context = {'filtered_data': filtered_data, 'now':now, 'email': email}

    return render(request, 'presenter/profile.html', context)


def get_clients(servers):
    client_data = []
    now = datetime.utcnow()

    for server in servers:
        server_name = server.name
        try:
            s = requests.Session()
            url = server.url + "login"
            payload = f'username={server.user_name}&password={server.password}'
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            response = s.request("POST", url, headers=headers, data=payload)
            # Handle non-200 responses or check response content as needed
            if response.status_code != 200:  # or other success codes as appropriate
                    error_message = f"Login failed for server: {server.name}. Status code: {response.status_code}"
                    raise ServerLoginError(error_message)
        except requests.exceptions.RequestException as e:
            error_message = f"An error occurred with server: {server.name}. Error details: {e}"
            raise ServerLoginError(error_message)
        
        # Make another request using the same session
        url = server.url + "panel/api/inbounds/list"
        headers = {'Accept': 'application/json',}
        response = s.request("GET", url, headers=headers)

        data = json.loads(response.text)
        for obj in data['obj']:
            for client in obj['clientStats']:
                client_data.append({
                    'remark': obj['remark'],
                    'id': client['id'],
                    'enable': client['enable'],
                    'email': client['email'],
                    'up': client['up'],
                    'down': client['down'],
                    'expiry_time': client['expiryTime'],
                    'total': client['total'],
                    'reset': client['reset'],
                    'server': server_name,
        })
    df = pd.DataFrame(client_data)

    df['traffic'] = df.apply(lambda row: (row['up'] + row['down']) / 1073741824 , axis=1)
    df['total'] = df.apply(lambda row: row['total'] / 1073741824 , axis=1)
    df['up'] = df.apply(lambda row: row['up'] / 1073741824 , axis=1)
    df['down'] = df.apply(lambda row: row['down'] / 1073741824 , axis=1)
    df['expiry_time'] = df.apply(lambda row: datetime.utcfromtimestamp(row['expiry_time'] / 1000) , axis=1)
    df['is_expired'] = df.apply(lambda row: row['expiry_time'] < now, axis=1)
    df['time_remaining'] = (df['expiry_time'] - now).dt.days
    df['time_remaining'] = df['time_remaining'].apply(lambda x: max(x, 0))
    df['progress_percentage'] = df.apply(lambda row: int(min(max(0, (float(row['traffic']) / float(row['total']) * 100) if float(row['total']) > 0 else 0), 100)), axis=1)
    return df


def all_clients(request):
    if not request.user.is_authenticated:
        return redirect('login')
    elif request.user.is_superuser:
        servers = Server.objects.all()
        df_all_clients = get_clients(servers=servers)
        df = df_all_clients.copy()
    elif request.user.is_staff:
        sellers = Seller.objects.filter(seller=request.user)
        servers = Server.objects.filter(seller__in=sellers).distinct()
        df_all_clients = get_clients(servers=servers)

        remarks_list = sellers.values_list('remark', flat=True)
        filtered_df_1 = df_all_clients[df_all_clients['remark'].isin(remarks_list)]

        emails_list = sellers.values_list('email', flat=True)
        filtered_df_2 = df_all_clients[df_all_clients['email'].isin(emails_list)]

        df = pd.concat([filtered_df_1, filtered_df_2]).drop_duplicates().reset_index(drop=True)

    else:
        return HttpResponse("You Have No Power Here!!")

    now = datetime.utcnow()
    
    # df["account_id"] = df["settings"].apply(extract_account_id)
    df['formatted_expiry_time'] = df['expiry_time'].dt.strftime('%Y%m%d%H%M')
    df['int_traffic'] = np.ceil(df['traffic']).astype(int)
    df['int_total'] = np.ceil(df['total']).astype(int)

    sorted_df = df.sort_values(by='email')

    df_disabled_clients =  sorted_df[df['enable'] == False]
    df_enabled_clients =  sorted_df[df['enable'] == True]
    disabled_clients = df_disabled_clients.to_dict(orient='records')
    enabled_clients = df_enabled_clients.to_dict(orient='records')

    context = {'disabled_clients': disabled_clients, 'enabled_clients': enabled_clients, 'now':now}
    return render(request, 'presenter/all_clients.html', context)


def logout_view(request):
    logout(request)
    return redirect('login')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('all_clients')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('all_clients')
        else:
            error_message = "کاربری با این مشخصات یافت نشد"
            return render(request, 'login.html', {'error_message': error_message})
    
    return render(request, 'login.html')

