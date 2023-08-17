from django.db import models
from django.contrib.auth.models import User


class Purchased(models.Model):
    user_id = models.CharField(max_length=300)
    remark = models.CharField(max_length=300)
    buyer = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.remark
