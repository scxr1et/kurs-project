from django.contrib import admin
from .models import LoginAttempt, BlockedIP, IPRangeCountry
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'phone_number', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительные поля', {'fields': ('phone_number',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Дополнительные поля', {'fields': ('phone_number',)}),
    )


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('username', 'ip_address', 'successful', 'timestamp')
    list_filter = ('successful', 'timestamp')
    search_fields = ('username', 'ip_address')
    ordering = ('-timestamp',)


@admin.register(BlockedIP)
class BlockedIPAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'added_at')
    search_fields = ('ip_address',)



@admin.register(IPRangeCountry)
class IPRangeAdmin(admin.ModelAdmin):
    list_display = ('ip_start_str', 'ip_end_str', 'country_code')
    search_fields = ('country_code',)
    list_filter = ('country_code',)