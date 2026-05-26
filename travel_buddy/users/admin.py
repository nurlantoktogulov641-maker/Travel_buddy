from django.contrib import admin
from travel_buddy.admin_mixins import SuperuserOnlyAdmin
from .models import User


@admin.register(User)
class UserAdmin(SuperuserOnlyAdmin, admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'is_staff', 'is_superuser', 'is_active', 'rating')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email')
