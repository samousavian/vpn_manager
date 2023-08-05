from django.db import models


class Inbound(models.Model):
    enable = models.IntegerField(null=True, blank=True, default="")
    remark = models.CharField(max_length=256, default="")
    total = models.IntegerField(null=True, blank=True, default="")
    expiry_time = models.IntegerField(null=True, blank=True, default="")

    port = models.IntegerField(null=True, blank=True, default="")
    server = models.ForeignKey('Server', on_delete=models.CASCADE, null=True, blank=True)
    uuid = models.UUIDField(unique=True, primary_key=True)

    up = models.IntegerField(null=True, blank=True, default="")
    down = models.IntegerField(null=True, blank=True, default="")
    id = models.IntegerField(null=True, blank=True, default="")
    listen = models.TextField(null=True, blank=True, default="")
    protocol = models.TextField(null=True, blank=True, default="")
    settings = models.TextField(null=True, blank=True, default="")
    stream_settings = models.TextField(null=True, blank=True, default="")
    tag = models.TextField(null=True, blank=True, default="")
    sniffing = models.TextField(null=True, blank=True, default="")

    def __str__(self):
        return f"{self.remark} - {self.server}"

class Server(models.Model):
    name = models.CharField(max_length=256, null=True, blank=True, default="")
    user_name = models.CharField(max_length=256, null=True, blank=True, default="")
    password = models.CharField(max_length=256, null=True, blank=True, default="")
    ip = models.CharField(max_length=256, null=True, blank=True, default="")
    url = models.URLField(null=True, blank=True, default="")

    def __str__(self):
        return self.name or ''