from django.db import IntegrityError
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.conf import settings
from .models import Inbound, Server
import sqlite3, json, uuid, os, subprocess
import pandas as pd


def db_path(server):
    # Define the directory path inside the project folder
    directory_path = os.path.join(settings.BASE_DIR, "data")
    # Ensure the directory exists
    os.makedirs(directory_path, exist_ok=True)
    # Define the destination file path
    destination_file_path = directory_path + "/" + server.name + ".db"
    return destination_file_path


def refresher_db(request):
    servers = Server.objects.all()
    for server in servers:
        try:
            destination_file_path = db_path(server)
            command = f"scp root@{server.ip}:/etc/x-ui/x-ui.db {destination_file_path}"
            subprocess.run(command, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    referer_url = request.META.get('HTTP_REFERER')
    return HttpResponseRedirect(referer_url) if referer_url else JsonResponse({'status': 'success'})


def refresher_state(request):
    servers = Server.objects.all()
    for server in servers:
        destination_file_path = db_path(server)
        conn = sqlite3.connect(destination_file_path)
        query = "SELECT * FROM inbounds;"
        df_output = pd.read_sql_query(query, conn)
        server_id = server.id
        save_inbounds(df_output, server_id)
        conn.close()
    referer_url = request.META.get('HTTP_REFERER')
    return HttpResponseRedirect(referer_url) if referer_url else HttpResponse("ok")

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
                    'user_id': row['user_id'],
                    'up': row['up'],
                    'down': row['down'],
                    'total': row['total'],
                    'remark': row['remark'],
                    'enable': row['enable'],
                    'expiry_time': row['expiry_time'],
                    'listen': row['listen'],
                    'port': row['port'],
                    'protocol': row['protocol'],
                    'settings': row['settings'],
                    'stream_settings': row['stream_settings'],
                    'tag': row['tag'],
                    'sniffing': row['sniffing'],
                }
            )

            if not created:
                # Update the existing record
                data.id = row['id']
                data.user_id = row['user_id']
                data.up = row['up']
                data.down = row['down']
                data.total = row['total']
                data.remark = row['remark']
                data.enable = row['enable']
                data.expiry_time = row['expiry_time']
                data.listen = row['listen']
                data.port = row['port']
                data.protocol = row['protocol']
                data.settings = row['settings']
                data.stream_settings = row['stream_settings']
                data.tag = row['tag']
                data.sniffing = row['sniffing']
                data.save()
        except IntegrityError as e:
            print(f"An integrity error occurred: {e}")