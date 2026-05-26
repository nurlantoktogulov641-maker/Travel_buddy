from django.contrib import admin
from travel_buddy.admin_mixins import SuperuserOnlyAdmin
from .models import Complaint


@admin.register(Complaint)
class ComplaintAdmin(SuperuserOnlyAdmin, admin.ModelAdmin):
    list_display = ('id', 'complainant', 'target_user', 'reason', 'status', 'created_at')
    list_filter = ('status', 'reason')
    search_fields = ('complainant__username', 'target_user__username')
    actions = ['approve_complaints', 'reject_complaints']

    def approve_complaints(self, request, queryset):
        for complaint in queryset:
            complaint.status = 'approved'
            complaint.save()
        self.message_user(request, f'{queryset.count()} жалоб подтверждено')
    approve_complaints.short_description = 'Подтвердить жалобы'

    def reject_complaints(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, f'{queryset.count()} жалоб отклонено')
    reject_complaints.short_description = 'Отклонить жалобы'
