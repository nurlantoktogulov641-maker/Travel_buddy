from django.db import migrations


def backfill_is_staff(apps, schema_editor):
    """Помечаем всех существующих юзеров как staff, чтобы они получили доступ к /admin/."""
    User = apps.get_model('users', 'User')
    User.objects.filter(is_staff=False).update(is_staff=True)


def reverse_backfill(apps, schema_editor):
    """Откат: возвращаем is_staff=False всем, кроме суперпользователей."""
    User = apps.get_model('users', 'User')
    User.objects.filter(is_superuser=False).update(is_staff=False)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_alter_user_is_staff'),
    ]

    operations = [
        migrations.RunPython(backfill_is_staff, reverse_backfill),
    ]
