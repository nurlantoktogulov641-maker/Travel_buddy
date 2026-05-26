from django.contrib import admin
from django.db.models import Q
from travel_buddy.admin_mixins import OwnObjectsOnlyAdmin
from .models import Response


@admin.register(Response)
class ResponseAdmin(OwnObjectsOnlyAdmin, admin.ModelAdmin):
    list_display = ('id', 'route', 'user', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('route__title', 'user__username')
    actions = ['accept_responses', 'reject_responses']

    def get_own_filter(self, request):
        # Свои отклики (которые я отправил) + отклики, пришедшие на мои маршруты.
        return Q(user=request.user) | Q(route__author=request.user)

    def is_own(self, request, obj):
        return obj.user_id == request.user.id or obj.route.author_id == request.user.id

    def accept_responses(self, request, queryset):
        updated = queryset.update(status='ACCEPTED')
        self.message_user(request, f'{updated} откликов принято.')
    accept_responses.short_description = 'Принять выбранные отклики'

    def reject_responses(self, request, queryset):
        updated = queryset.update(status='REJECTED')
        self.message_user(request, f'{updated} откликов отклонено.')
    reject_responses.short_description = 'Отклонить выбранные отклики'
