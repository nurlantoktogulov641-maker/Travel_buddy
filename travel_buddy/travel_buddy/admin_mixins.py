class SuperuserOnlyAdmin:
    """Доступ только для superuser. Применяется к моделям, скрытым от admin-роли."""

    def has_module_permission(self, request):
        return bool(request.user and request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)

    def has_add_permission(self, request):
        return bool(request.user and request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)


class StaffAllowedAdmin:
    """Полный доступ для любого staff-пользователя (включая superuser).
    Игнорирует таблицу auth_permission — права даются по флагу is_staff."""

    def has_module_permission(self, request):
        return bool(request.user and request.user.is_active and request.user.is_staff)

    def has_view_permission(self, request, obj=None):
        return bool(request.user and request.user.is_active and request.user.is_staff)

    def has_add_permission(self, request):
        return bool(request.user and request.user.is_active and request.user.is_staff)

    def has_change_permission(self, request, obj=None):
        return bool(request.user and request.user.is_active and request.user.is_staff)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user and request.user.is_active and request.user.is_staff)


class OwnObjectsOnlyAdmin(StaffAllowedAdmin):
    """Staff видит/правит только связанные с ним объекты. Superuser видит все.

    В наследнике переопредели:
      - get_own_filter(request)  → Q-объект, описывающий принадлежность объекта юзеру
      - is_own(request, obj)     → bool, та же логика на уровне объекта
    """

    def get_own_filter(self, request):
        raise NotImplementedError

    def is_own(self, request, obj):
        raise NotImplementedError

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(self.get_own_filter(request)).distinct()

    def _check_obj(self, request, obj):
        if obj is None or request.user.is_superuser:
            return True
        return self.is_own(request, obj)

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and self._check_obj(request, obj)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and self._check_obj(request, obj)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and self._check_obj(request, obj)
