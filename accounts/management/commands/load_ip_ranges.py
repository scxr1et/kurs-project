import csv
import ipaddress
from django.core.management.base import BaseCommand
from accounts.models import IPRangeCountry

class Command(BaseCommand):
    help = "Загружает диапазоны IP-адресов и страны в базу"

    def handle(self, *args, **options):
        filepath = 'ip-to-country.csv'
        added = 0

        with open(filepath, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                try:
                    ip_from = int(ipaddress.ip_address(row[0].replace('"','')))
                    ip_to = int(ipaddress.ip_address(row[1].replace('"','')))
                    country_code = row[2].replace('"','')

                    IPRangeCountry.objects.create(
                        ip_start=ip_from,
                        ip_end=ip_to,
                        country_code=country_code
                    )
                    added += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Ошибка на строке: {row} → {e}"))

        self.stdout.write(self.style.SUCCESS(f"✅ Загружено {added} диапазонов IP"))
