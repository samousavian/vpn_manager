from django.contrib import admin

from .models import Inbound, Server

admin.site.register(Inbound)
admin.site.register(Server)