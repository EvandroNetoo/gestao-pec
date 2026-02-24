from django.contrib import admin
from django.contrib.auth import admin as auth_admin

from accounts.models import User


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    model = User
    add_form_template = ''
    search_fields = ['email']
    list_filter = ['is_superuser', 'is_staff', 'is_active']
    list_display = ['email', 'is_active']
    list_display_links = ['email']
    readonly_fields = ['date_joined', 'last_login']
    ordering = ['email']
    fieldsets = (
        (
            'Informações de login',
            {
                'fields': (
                    'email',
                    'password',
                )
            },
        ),
        (
            'Permissões',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                ),
            },
        ),
        (
            'Datas importantes',
            {
                'fields': (
                    'last_login',
                    'date_joined',
                )
            },
        ),
    )
    add_fieldsets = (
        (
            'Informações de importantes',
            {
                'fields': (
                    'email',
                    'password1',
                    'password2',
                ),
            },
        ),
    )