from django.contrib import admin
from .models import Purchased, Server, Seller

# Register your models here.
admin.site.register(Purchased)
admin.site.register(Server)
admin.site.register(Seller)