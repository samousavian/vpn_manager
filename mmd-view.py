from .models import Server
from .forms import AddInboundForm
from django.shortcuts import render
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
from operator import attrgetter
from urllib.parse import urlencode, quote_plus
from datetime import datetime, timedelta
import json
import base64
import random
import uuid
import string
import requests


# class Inbound:
#     inbounds = []
#
#     def __init__(self, remark, inbound_id, port, protocol, settings, stream_settings, sniffing, remaining_status):
#         self.inbound_id = inbound_id
#         self.remark = remark
#         self.port = port
#         self.protocol = protocol
#         self.settings = settings
#         self.stream_settings = stream_settings
#         self.sniffing = sniffing
#         self.remaining_status = remaining_status
#         self.inbounds.append(self)
#
#     def __str__(self):
#         return self.remark
#
#     @classmethod
#     def get_inbound_by_id(cls, inbound_id):
#         return [inbound for inbound in cls.inbounds if inbound.inbound_id == inbound_id]


def home(request):
    return render(request, 'home.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')

    form = AuthenticationForm(request)
    context = {
        "form": form,
    }
    return render(request, "login.html", context)


@login_required(login_url='login_view')
def logout_view(request):
    logout(request)
    return redirect('login_view')


@login_required(login_url='login_view')
def dashboard(request):
    return render(request, 'status/dashboard.html')


def login_to_server(host, username, password):
    url = f"{host}/login"

    payload = f'username={username}&password={password}'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    try:
        response = requests.request("POST", url, headers=headers, data=payload)
    except Exception:
        raise ConnectionError

    if response.status_code == 200 and response.json()['success']:
        return response.headers.get("Set-Cookie")
    else:
        raise ConnectionError


def get_set_cookie(server):
    now = timezone.now()
    set_cookie = server.set_cookie
    set_cookie_expires = server.set_cookie_expires
    error_flag = False
    if not set_cookie or set_cookie_expires < now:
        try:
            set_cookie = login_to_server(server.host, server.username, server.password)
            set_cookie_expires = now + timedelta(days=25)
            server.set_cookie = set_cookie
            server.set_cookie_expires = set_cookie_expires
            server.save()
        except ConnectionError:
            server.last_disabled_users = f"ERROR"
            server.save()
            error_flag = True
    return error_flag, set_cookie


def get_inbounds_list(server):
    error_flag, set_cookie = get_set_cookie(server)
    if error_flag:
        raise ConnectionError

    url = f"{server.host}/xui/inbound/list"

    payload = {}
    headers = {
        'Cookie': set_cookie
    }

    try:
        response = requests.request("POST", url, headers=headers, data=payload)
    except Exception:
        raise ConnectionError

    if response.status_code == 200 and response.json()["success"]:
        return response.json()["obj"]
    else:
        raise ConnectionError


def calc_remaining_traffic(up, down, total):
    up = up / 2 ** 30
    down = down / 2 ** 30
    total = total / 2 ** 30
    return round(total - up - down, 1)


def calc_remaining_credit(expiry_time):
    now = datetime.now()
    expiration = datetime.fromtimestamp(expiry_time / 1000)
    return (expiration - now).days


@login_required(login_url='login_view')
def check_status(request):
    if request.GET.get("start") == "true":
        if request.user.is_staff:
            servers = Server.objects.all()
        else:
            servers = Server.objects.filter(Q(owner=request.user) | Q(viewer=request.user))
        servers = sorted(servers, key=attrgetter('username', 'sort_number'))

        servers_context = []
        for server in servers:
            try:
                inbounds = get_inbounds_list(server)
                disabled_inbounds = []
                disabled_inbounds_json = {}
                for inbound in inbounds:
                    if not inbound["enable"]:
                        remark = inbound['remark']
                        ID = inbound['id']
                        remaining_credit = calc_remaining_credit(inbound['expiryTime'])
                        remaining_traffic = calc_remaining_traffic(inbound['up'], inbound['down'], inbound['total'])

                        if round(remaining_traffic, 1) > 0:
                            status = f"{remark}({remaining_traffic} GB left)"
                        elif remaining_credit > 0:
                            status = f"{remark}({remaining_credit} days left)"
                        else:
                            status = f"{remark}(Nothing left)"

                        disabled_inbound = {"remaining_status": status, "id": ID}
                        disabled_inbounds.append(disabled_inbound)
                        disabled_inbounds_json[ID] = inbound

                if not disabled_inbounds:
                    disabled_inbounds = "EMPTY"
                    disabled_inbounds_json = {}
            except ConnectionError:
                disabled_inbounds = "ERROR"
                disabled_inbounds_json = {}
                server.last_disabled_users = json.dumps(disabled_inbounds_json)
                server.save()

            servers_context.append({
                'name': server.name,
                'owner': server.owner,
                'expired_inbounds': disabled_inbounds,
                'address': server.host
            })
            server.last_disabled_users = str(json.dumps(disabled_inbounds_json))
            server.save()

        context = {"request": request, 'servers_context': servers_context}
        return render(request, "status/status.html", context)

    else:
        return render(request, "status/status.html")


def generate_payload(is_new, remark, total, expiry_time, domain, protocol,
                     port=None, settings=None):
    if is_new:
        if protocol == 'trojan':
            UUID = str(''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10)))
        else:
            UUID = str(uuid.uuid4())
        port = random.randint(10000, 60000)
    else:
        if protocol == 'trojan':
            UUID = settings['clients'][0]['password']
        else:
            UUID = settings['clients'][0]['id']

    settings, stream_settings, sniffing = generate_config_settings(UUID, protocol, domain)

    data = {
        "up": 0,
        "down": 0,
        "total": total * (2 ** 30),
        "remark": remark,
        "enable": True,
        "expiryTime": round(expiry_time.timestamp() * 1000 - 3600000 * 3.5),
        "port": port,
        "protocol": protocol,
        "settings": json.dumps(settings),
        "streamSettings": json.dumps(stream_settings),
        "sniffing": json.dumps(sniffing)
    }

    link = generate_config_link(domain, port, protocol, remark, settings)

    return urlencode(data), link


def generate_config_settings(UUID, protocol, server_url):
    if protocol == 'vmess':
        settings = {
            "clients": [
                {
                    "id": UUID,
                    "alterId": 0
                }
            ],
            "disableInsecureEncryption": False
        }
        stream_settings = {
            "network": "tcp",
            "security": "tls",
            "tlsSettings": {
                "serverName": server_url,
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
    elif protocol == 'vless':
        settings = {
            "clients": [
                {
                    "id": UUID,
                    "flow": "xtls-rprx-direct"
                }
            ],
            "decryption": "none",
            "fallbacks": []
        }
        stream_settings = {
            "network": "tcp",
            "security": "xtls",
            "xtlsSettings": {
                "serverName": server_url,
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
    else:
        settings = {
            "clients": [
                {
                    "password": UUID,
                    "flow": "xtls-rprx-direct"
                }
            ],
            "fallbacks": []
        }
        stream_settings = {
            "network": "tcp",
            "security": "xtls",
            "xtlsSettings": {
                "serverName": server_url,
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
    return settings, stream_settings, sniffing


def generate_config_link(domain, port, protocol, remark, settings):
    if protocol == 'vmess':
        link_data = {"v": "2", "ps": remark, "add": domain, "port": port, "id": settings['clients'][0]['id'],
                     "aid": 0, "net": "tcp", "type": "none", "host": "", "path": "", "tls": "tls"}
        link = 'vmess://' + base64.b64encode(json.dumps(link_data).encode()).decode()
    elif protocol == 'vless':
        link = f"vless://{settings['clients'][0]['id']}@{domain}:{port}?" \
               f"type=tcp&security=xtls&flow=xtls-rprx-direct#{quote_plus(remark)}"
    else:
        link = f"trojan://{settings['clients'][0]['password']}@{domain}:{port}#{quote_plus(remark)}"
    return link


@login_required(login_url='login_view')
def add_inbound(request):
    if request.user.is_staff:
        servers = Server.objects.filter(default_x_ui=True)
    else:
        servers = Server.objects.filter(Q(owner=request.user) & Q(default_x_ui=True))
    servers = sorted(servers, key=attrgetter('username', 'sort_number'))

    server_name_choices = []

    for server in servers:
        try:
            inbounds_count = len(get_inbounds_list(server))
            server_name_choices.append((server.name, f"{server.name} ({inbounds_count} inbounds)"))
        except ConnectionError:
            server_name_choices.append((server.name, f"{server.name} (? inbounds)"))
            continue

    form = AddInboundForm(server_name_choices=server_name_choices)

    if request.method == "POST":
        form = AddInboundForm(request.POST, server_name_choices=server_name_choices)
        if form.is_valid():
            server_name = form.cleaned_data['server_name']
            remark = form.cleaned_data['remark']
            total = form.cleaned_data['total']
            expiry_time = form.cleaned_data['expiry_time']
            protocol = form.cleaned_data['protocol']

            server = Server.objects.get(name=server_name)
            domain = server.host.split(':')[1].replace('/', '')

            url = f"{server.host}/xui/inbound/add"
            headers = {
                'Cookie': server.set_cookie,
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            payload, link = generate_payload(True, remark, total, expiry_time, domain, protocol)

            try:
                response = requests.request("POST", url, headers=headers, data=payload)
                if response.status_code == 200:
                    success = True
                    message = f"{remark} Added Successfully"
                    context = {'success': success, 'message': message, 'link': link}
                    return render(request, 'status/add-inbound.html', context)
                else:
                    raise ConnectionError
            except ConnectionError:
                context = {'success': False, 'message': "Add Inbound Failed", 'servers': servers, 'form': form}
                return render(request, 'status/add-inbound.html', context)

        else:
            return render(request, 'status/add-inbound.html',
                          {'success': False, 'message': "Invalid Form", 'servers': servers, 'form': form})

    return render(request, 'status/add-inbound.html',
                  {'servers': servers, 'form': form})


@csrf_exempt
@login_required(login_url='login_view')
def renew_inbound(request):
    if request.method == 'POST':
        server_name = request.POST.get("server")
        inbound_id = request.POST.get("id")
        traffic = int(request.POST.get("traffic"))
        result = f'Renew inbound: {inbound_id}, from server: {server_name} for {traffic}GB'

        server = Server.objects.get(name=server_name)
        if server.owner.username != request.user.username:
            return JsonResponse({'success': False, 'message': 'You are not the owner!'}, status=401)
        disabled_inbounds = json.loads(server.last_disabled_users)
        renewing_inbound = disabled_inbounds[inbound_id]
        domain = server.host.split(':')[1].replace('/', '')

        payload, _ = generate_payload(False, renewing_inbound['remark'], traffic * 2 ** 30,
                                      datetime.now() + timedelta(days=30),
                                      domain, renewing_inbound['protocol'],
                                      renewing_inbound['port'],
                                      json.loads(renewing_inbound['settings']))

        url = f"{server.host}/xui/inbound/update/{inbound_id}"
        error_flag, set_cookie = get_set_cookie(server)
        if error_flag:
            return JsonResponse({'success': False, 'message': 'Cant login to server'}, status=401)

        headers = {
            "Cookie": set_cookie,
            "Content-Type": "x-www-form-urlencoded"
        }
        print("PAYLOOOOAD: ", payload)
        response = requests.request("POST", url, headers=headers, data=payload)

        print(response)

        return JsonResponse({'success': True, 'message': result}, status=200)
    return JsonResponse({'success': False, 'message': 'Invalid method'}, status=400)


@csrf_exempt
def delete_inbound(request):
    if request.method == 'POST':
        server_name = request.POST.get("server")
        inbound_id = request.POST.get("id")
        result = f'Delete Inbound: {inbound_id}, from server: {server_name}'
        print(result)
        return JsonResponse({'message': result}, status=200)
    return JsonResponse({'message': 'Invalid method'}, status=400)
