from django.contrib import admin
from travel_buddy.admin_mixins import SuperuserOnlyAdmin
from .models import Message, PrivateMessage


@admin.register(Message)
class MessageAdmin(SuperuserOnlyAdmin, admin.ModelAdmin):
    pass


@admin.register(PrivateMessage)
class PrivateMessageAdmin(SuperuserOnlyAdmin, admin.ModelAdmin):
    pass
