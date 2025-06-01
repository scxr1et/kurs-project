import ipaddress
from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid




class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.username


class LoginAttempt(models.Model):
    username = models.CharField(max_length=150, blank=True, null=True)
    ip_address = models.GenericIPAddressField()
    successful = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.username} - {"Успех" if self.successful else "Ошибка"} - {self.ip_address}'

class BlockedIP(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.ip_address
    
class IPRangeCountry(models.Model):
    ip_start = models.BigIntegerField()
    ip_end = models.BigIntegerField()
    country_code = models.CharField(max_length=2)

    def __str__(self):
        return f"{self.country_code}: {self.ip_start} - {self.ip_end}"

    @staticmethod
    def ip_to_int(ip_str):
        return int(ipaddress.ip_address(ip_str))
    
    @staticmethod
    def int_to_ip(ip_int):
        return str(ipaddress.ip_address(ip_int))

    
    def ip_start_str(self):
        return self.int_to_ip(self.ip_start)

    def ip_end_str(self):
        return self.int_to_ip(self.ip_end)
    
    ip_start_str.short_description = "Начальный IP"
    ip_end_str.short_description = "Конечный IP"

    @classmethod
    def get_country(cls, ip_str):
        ip_int = cls.ip_to_int(ip_str)
        match = cls.objects.filter(ip_start__lte=ip_int, ip_end__gte=ip_int).first()
        return match.country_code if match else None