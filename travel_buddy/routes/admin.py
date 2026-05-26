from django.contrib import admin
from travel_buddy.admin_mixins import SuperuserOnlyAdmin
from .models import Route, Tag, RouteImage, Favorite


@admin.register(Route)
class RouteAdmin(SuperuserOnlyAdmin, admin.ModelAdmin):
    list_display = ('id', 'title', 'author', 'countries', 'start_date', 'end_date', 'status', 'views_count', 'created_at')
    list_filter = ('status', 'tags', 'created_at', 'start_date', 'end_date')
    search_fields = ('title', 'description', 'countries', 'author__username')
    readonly_fields = ('views_count', 'created_at', 'updated_at')
    list_per_page = 25
    actions = ['make_active', 'make_archived', 'make_cancelled']

    fieldsets = (
        ('Основная информация', {
            'fields': ('author', 'title', 'description', 'countries', 'cities', 'tags')
        }),
        ('Даты и бюджет', {
            'fields': ('start_date', 'end_date', 'budget')
        }),
        ('Статус и статистика', {
            'fields': ('status', 'views_count', 'created_at', 'updated_at')
        }),
    )

    def make_active(self, request, queryset):
        updated = queryset.update(status='ACTIVE')
        self.message_user(request, f'{updated} маршрутов сделано активными.')
    make_active.short_description = 'Сделать выбранные маршруты активными'

    def make_archived(self, request, queryset):
        updated = queryset.update(status='ARCHIVED')
        self.message_user(request, f'{updated} маршрутов архивировано.')
    make_archived.short_description = 'Архивировать выбранные маршруты'

    def make_cancelled(self, request, queryset):
        updated = queryset.update(status='CANCELLED')
        self.message_user(request, f'{updated} маршрутов отменено.')
    make_cancelled.short_description = 'Отменить выбранные маршруты'


@admin.register(Tag)
class TagAdmin(SuperuserOnlyAdmin, admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    search_fields = ('name',)


@admin.register(RouteImage)
class RouteImageAdmin(SuperuserOnlyAdmin, admin.ModelAdmin):
    list_display = ('id', 'route', 'image', 'order')
    list_filter = ('route',)


@admin.register(Favorite)
class FavoriteAdmin(SuperuserOnlyAdmin, admin.ModelAdmin):
    list_display = ('id', 'user', 'route', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'route__title')
