import base64, json, random, string, uuid, requests
from urllib.parse import urlencode, quote_plus, urlparse
from django.http import HttpResponse
from django.shortcuts import redirect, render
from .forms import *
from presenter.models import *
from datarefresher.models import *
# from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from presenter.models import Purchased


# @csrf_exempt
@login_required(login_url="login_view")
def update_inbound(request, user_id, remark, server_name, pre_traffic):
    if not request.user.is_staff:
        return redirect("login")

    server = Server.objects.get(name=server_name)
    uuid = user_id
    remark = remark
    pre_traffic = pre_traffic
        

    if request.method == "GET":
        form = UpdateInboundFrom()

        return render(
            request,
            "modifier/update_inbound.html",
            {"pre_traffic": pre_traffic, "remark": remark, "form": form},
        )
    
    elif request.method == "POST":
        form = UpdateInboundFrom(request.POST)
        if form.is_valid():
            traffic = form.cleaned_data["traffic"]
            days = form.cleaned_data["days"]
        else:
            print(form.errors)
            return HttpResponse("Form is not valid!!")

        if int(traffic) == 0:
            return HttpResponse("Form is not valid!!")

        inbounds = get_inbounds_list(server)
        def find_inbound_with_uuid(inbounds, uuid):
            for inbound in inbounds:
                settings = json.loads(inbound['settings'])
                for client in settings['clients']:
                    if client['id'] == uuid:
                        return inbound
        inbound = find_inbound_with_uuid(inbounds, uuid)
        inbound_id = inbound["id"]
        domain = urlparse(server.url).hostname

        s = requests.Session()
        url = server.url + "login"
        payload = f"username={server.user_name}&password={server.password}"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        response = s.request("POST", url, headers=headers, data=payload)

        if not response.ok:
            return HttpResponse(f"login failed{server.name}")
        
        payload, _ = generate_payload(
            False,
            inbound["remark"],
            traffic,
            datetime.now() + timedelta(days=days),
            domain,
            inbound["protocol"],
            inbound["port"],
            json.loads(inbound["settings"]),
        )

        url = f"{server.url}xui/inbound/update/{inbound_id}"
        domain = urlparse(server.url).hostname
        try:
            message = f"{request.user} wants to update {remark} with {traffic}GB in {days} days!"
            send_to_discord(message)
        except:
            return HttpResponse("Code D")

        try:
            response = s.request(
                "POST", url, headers=headers, data=payload
            )
            if response.status_code == 200:
                success = True
                message = f"{remark} updated Successfully"
                request.session['success'] = success
                request.session['message'] = message
                return redirect("inbound_updated")
            else:
                raise ConnectionError
        except ConnectionError:
            success = False
            message = f"{remark} update Failed"
            request.session['success'] = success
            request.session['message'] = message
            return redirect("inbound_updated")

def inbound_updated(request):
    # Fetch data from the session
    message = request.session.get('message', '')
    success = request.session.get('success', '')

    # Remove the data from the session after fetching
    if 'message' in request.session:
        del request.session['message']
    if 'success' in request.session:
        del request.session['success']
    
    context = {"success": success, "message": message}
    return render(request, "modifier/inbound_updated.html", context)


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

    return urlencode(data), link, UUID


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




def add_to_purchased(user, remark, uuid):
    buyer = user
    uuid = uuid
    purchased = Purchased(user_id=uuid, remark=remark, buyer=buyer)
    purchased.save()

    return



def add_inbound(request):
    if not request.user.is_authenticated:
        return redirect("login")

    if request.user.is_staff:
        servers = Server.objects.all()
        server_names = [(name, name) for name in servers.values_list('name', flat=True)]

        server_name_data = []

        for server in servers:
            try:
                inbounds_count = len(get_inbounds_list(server))
                label = f"{server.name} ({inbounds_count} inbounds)"
                server_name_data.append((server.name, label, inbounds_count))
            except ConnectionError:
                label = f"{server.name} (? inbounds)"
                server_name_data.append((server.name, label, float('inf')))  # Use a high value for sort
                continue

        # Sort by inbounds_count
        server_name_data.sort(key=lambda x: x[2])

        # Construct final server_name_choices without inbounds_count
        server_name_choices = [(item[0], item[1]) for item in server_name_data]

        form = AddInboundForm(server_name_choices=server_name_choices)

        # If you want the one with the least inbounds_count to be the default
        form.fields['server_name'].initial = server_name_data[0][0] if server_name_data else None

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

                url = f"{server.url}xui/inbound/add"
                domain = urlparse(server.url).hostname
                payload, link, uuid = generate_payload(True, remark, total, expiry_time, domain, protocol)
                try:
                    message = f"{request.user} wants to add {remark} with {total}GB in {expiry_time}!"
                    send_to_discord(message)
                except:
                    return HttpResponse("Code D")
                try:
                    response = s.request(
                        "POST", url, headers=headers, data=payload
                    )
                    if response.status_code == 200:
                        add_to_purchased(request.user, remark,  uuid)
                        success = True
                        message = f"{remark} Added Successfully"
                        request.session['success'] = success
                        request.session['message'] = message
                        request.session['link'] = link
                        request.session['remark'] = remark
                        return redirect("inbound_added")
                    else:
                        raise ConnectionError
                except ConnectionError:
                    context = {
                        "success": False,
                        "message": "Add Inbound Failed",
                        "servers": server_name_choices,
                        "form": form,
                    }
                return render(request, "modifier/add_inbound.html", context)
            else:
                return render(
                    request,
                    "modifier/add_inboxund.html",
                    {
                        "success": False,
                        "message": "Invalid Form",
                        "servers": server_name_choices,
                        "form": form,
                    },
                )

        return render(
            request,
            "modifier/add_inbound.html",
            {"servers": server_name_choices, "form": form},
        )
    else:
        return HttpResponse("You Shall Not Pass!!")


def inbound_added(request):
    # Fetch data from the session
    message = request.session.get('message', '')
    link = request.session.get('link', '')
    success = request.session.get('success', '')
    remark = request.session.get('remark', '')

    # Remove the data from the session after fetching
    if 'message' in request.session:
        del request.session['message']
    if 'link' in request.session:
        del request.session['link']
    if 'success' in request.session:
        del request.session['success']
    if 'remark' in request.session:
        del request.session['remark']
    
    context = {"success": success, "message": message, "link": link, "remark": remark}
    return render(request, "modifier/inbound_added.html", context)


def get_inbounds_list(server):
    s = requests.Session()
    url = server.url + "login"
    payload = f'username={server.user_name}&password={server.password}'
    headers = {'Content-Type': 'application/x-www-form-urlencoded',}
    response = s.request("POST", url, headers=headers, data=payload)

    if not response.ok:
        return HttpResponse(f'login failed{server.name}')

    url = server.url + "xui/inbound/list"
    headers = {'Accept': 'application/json',}
    try:
        response = s.request("POST", url, headers=headers)
    except Exception:
        raise ConnectionError
    if response.status_code == 200 and response.json()["success"]:
        return response.json()["obj"]
    else:
        raise ConnectionError


def send_to_discord(message):
    webhook_url = "https://discord.com/api/webhooks/1187483519438565426/KcUXef_ziRl-VMnHNdHMT2qhHsJ4uuUHvIswigzfm3AVJkAbBrEb6p40IRFTz8IJ52oe"
    data = {
        "content": message,
        "username": "Django App"
    }
    response = requests.post(webhook_url, json=data)
    return response.status_code
