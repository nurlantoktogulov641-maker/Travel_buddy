from django.contrib import admin
from django.db.models import Q
from travel_buddy.admin_mixins import OwnObjectsOnlyAdmin
from .models import Review


@admin.register(Review)
class ReviewAdmin(OwnObjectsOnlyAdmin, admin.ModelAdmin):
    list_display = ('id', 'author', 'target_user', 'route', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('author__username', 'target_user__username', 'route__title')
    actions = ['delete_selected']

    def get_own_filter(self, request):
        # Свои отзывы (которые я написал) + отзывы обо мне.
        return Q(author=request.user) | Q(target_user=request.user)

    def is_own(self, request, obj):
        return obj.author_id == request.user.id or obj.target_user_id == request.user.id
