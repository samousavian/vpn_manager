import base64
import json
from operator import attrgetter
import random
import string
import uuid
from django.http import HttpResponse
from django.shortcuts import redirect, render
import requests
from .forms import *
from presenter.models import *
from datarefresher.models import *
from operator import attrgetter
from urllib.parse import urlencode, quote_plus


def generate_payload(
    is_new, remark, total, expiry_time, domain, protocol, port=None, settings=None
):
    if is_new:
        if protocol == "trojan":
            UUID = str(
                "".join(
                    random.choice(string.ascii_letters + string.digits)
                    for _ in range(10)
                )
            )
        else:
            UUID = str(uuid.uuid4())
        port = random.randint(10000, 60000)
    else:
        if protocol == "trojan":
            UUID = settings["clients"][0]["password"]
        else:
            UUID = settings["clients"][0]["id"]

    settings, stream_settings, sniffing = generate_config_settings(
        UUID, protocol, domain
    )

    data = {
        "up": 0,
        "down": 0,
        "total": total * (2**30),
        "remark": remark,
        "enable": True,
        "expiryTime": round(expiry_time.timestamp() * 1000 - 3600000 * 3.5),
        "port": port,
        "protocol": protocol,
        "settings": json.dumps(settings),
        "streamSettings": json.dumps(stream_settings),
        "sniffing": json.dumps(sniffing),
    }

    link = generate_config_link(domain, port, protocol, remark, settings)

    return urlencode(data), link


def generate_config_settings(UUID, protocol, server_url):
    if protocol == "vmess":
        settings = {
            "clients": [{"id": UUID, "alterId": 0}],
            "disableInsecureEncryption": False,
        }
        stream_settings = {
            "network": "tcp",
            "security": "tls",
            "tlsSettings": {
                "serverName": server_url,
                "certificates": [
                    {
                        "certificateFile": "/root/cert.crt",
                        "keyFile": "/root/private.key",
                    }
                ],
            },
            "tcpSettings": {"header": {"type": "none"}},
        }
    elif protocol == "vless":
        settings = {
            "clients": [{"id": UUID, "flow": "xtls-rprx-direct"}],
            "decryption": "none",
            "fallbacks": [],
        }
        stream_settings = {
            "network": "tcp",
            "security": "xtls",
            "xtlsSettings": {
                "serverName": server_url,
                "certificates": [
                    {
                        "certificateFile": "/root/cert.crt",
                        "keyFile": "/root/private.key",
                    }
                ],
            },
            "tcpSettings": {"header": {"type": "none"}},
        }
    else:
        settings = {
            "clients": [{"password": UUID, "flow": "xtls-rprx-direct"}],
            "fallbacks": [],
        }
        stream_settings = {
            "network": "tcp",
            "security": "xtls",
            "xtlsSettings": {
                "serverName": server_url,
                "certificates": [
                    {
                        "certificateFile": "/root/cert.crt",
                        "keyFile": "/root/private.key",
                    }
                ],
            },
            "tcpSettings": {"header": {"type": "none"}},
        }

    sniffing = {"enabled": True, "destOverride": ["http", "tls"]}
    return settings, stream_settings, sniffing


def generate_config_link(domain, port, protocol, remark, settings):
    if protocol == "vmess":
        link_data = {
            "v": "2",
            "ps": remark,
            "add": domain,
            "port": port,
            "id": settings["clients"][0]["id"],
            "aid": 0,
            "net": "tcp",
            "type": "none",
            "host": "",
            "path": "",
            "tls": "tls",
        }
        link = "vmess://" + base64.b64encode(json.dumps(link_data).encode()).decode()
    elif protocol == "vless":
        link = (
            f"vless://{settings['clients'][0]['id']}@{domain}:{port}?"
            f"type=tcp&security=xtls&flow=xtls-rprx-direct#{quote_plus(remark)}"
        )
    else:
        link = f"trojan://{settings['clients'][0]['password']}@{domain}:{port}#{quote_plus(remark)}"
    return link


def add_inbound(request):
    if not request.user.is_authenticated:
        return redirect("login")

    if request.user.is_staff:
        servers = Server.objects.all()
        server_names = [(name, name) for name in servers.values_list('name', flat=True)]
        sorted_servers = sorted(
            servers, key=attrgetter("user_name")
        )  # Use a different variable for the sorted list
        print(server_names)
        form = AddInboundForm(server_name_choices=server_names)

        if request.method == "POST":
            form = AddInboundForm(request.POST, server_name_choices=server_names)
            if form.is_valid():
                server_name = form.cleaned_data["server_name"]
                remark = form.cleaned_data["remark"]
                total = form.cleaned_data["total"]
                expiry_time = form.cleaned_data["expiry_time"]
                protocol = form.cleaned_data["protocol"]

                server = Server.objects.get(name=server_name)
                s = requests.Session()
                url = server.url + "login"
                payload = f"username={server.user_name}&password={server.password}"
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                }
                response = s.request("POST", url, headers=headers, data=payload)

                if not response.ok:
                    return HttpResponse(f"login failed{server.name}")

                # Make another request using the same session
                # url = server.url + "xui/inbound/list"
                # headers = {'Accept': 'application/json',}
                # response = s.request("POST", url, headers=headers)
                domain = server.url

                payload, link = generate_payload(
                    True, remark, total, expiry_time, domain, protocol
                )

                try:
                    response = s.request(
                        "POST", url, headers=headers, data=payload
                    )
                    if response.status_code == 200:
                        success = True
                        message = f"{remark} Added Successfully"
                        context = {"success": success, "message": message, "link": link}
                        return render(request, "modifier/add_inbound.html", context)
                    else:
                        raise ConnectionError
                except ConnectionError:
                    context = {
                        "success": False,
                        "message": "Add Inbound Failed",
                        "servers": sorted_servers,
                        "form": form,
                    }
                    return render(request, "modifier/add_inbound.html", context)

            else:
                return render(
                    request,
                    "modifier/add_inbound.html",
                    {
                        "success": False,
                        "message": "Invalid Form",
                        "servers": sorted_servers,
                        "form": form,
                    },
                )

        return render(
            request,
            "modifier/add_inbound.html",
            {"servers": sorted_servers, "form": form},
        )
    else:
        return HttpResponse("You Shall Not Pass!!")
