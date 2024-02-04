from django.db import models
from django.contrib.auth.models import User


class Updated_Inbound(models.Model):
    remark = models.CharField(max_length=256, default="")
    uuid = models.CharField(max_length=256, default="")
    total_used = models.IntegerField(null=True, blank=True, default="")
    expiry_time = models.DateTimeField(null=True, blank=True, default="")
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.remark