from django.db import models
from django.contrib.auth.models import User


class Server(models.Model):
    name = models.CharField(max_length=256, null=True, blank=True, default="")
    user_name = models.CharField(max_length=256, null=True, blank=True, default="")
    password = models.CharField(max_length=256, null=True, blank=True, default="")
    ip = models.CharField(max_length=256, null=True, blank=True, default="")
    url = models.URLField(null=True, blank=True, default="")

    def __str__(self):
        return self.name or ''


class Seller(models.Model):
    server = models.ForeignKey(Server, on_delete=models.CASCADE)
    remark = models.CharField(max_length=300, null=True, blank=True, default="")
    email = models.CharField(max_length=300, null=True, blank=True, default="")
    seller = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.remark if self.remark else self.email


class Purchased(models.Model):
    user_id = models.CharField(max_length=300)
    remark = models.CharField(max_length=300)
    seller = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.remark