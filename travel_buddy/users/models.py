from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import Avg
from django.utils.timezone import now

class User(AbstractUser):
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True)
    interests = models.TextField(blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    
    # ===== НОВЫЕ ПОЛЯ ДЛЯ УРОВНЯ ДОВЕРИЯ =====
    trust_level = models.IntegerField(default=1, verbose_name='Уровень доверия (1-10)')
    total_completed_trips = models.IntegerField(default=0, verbose_name='Завершённых поездок')

    def __str__(self):
        return self.username

    def update_trust_level(self):
        """Обновление уровня доверия на основе отзывов и поездок"""
        from reviews.models import Review
        from responses.models import Response
        
        # 1. Средний рейтинг полученных отзывов
        avg_rating = Review.objects.filter(target_user=self).aggregate(Avg('rating'))['rating__avg'] or 0
        
        # 2. Количество завершённых поездок (отклик принят и дата окончания маршрута прошла)
        completed_trips = Response.objects.filter(
            user=self,
            status='ACCEPTED',
            route__end_date__lt=now().date()
        ).count()
        
        self.total_completed_trips = completed_trips
        
        # 3. Расчёт уровня доверия (от 1 до 10)
        # База: 1
        # + рейтинг (максимум +4 балла при рейтинге 5)
        # + поездки (максимум +5 баллов за 10+ поездок)
        trust = 1
        trust += min(int(avg_rating), 4)           # рейтинг 5 → +4
        trust += min(completed_trips // 2, 5)      # 10 поездок → +5
        
        self.trust_level = min(trust, 10)
        self.save()
        return self.trust_level

    def get_trust_level_display(self):
        """Возвращает текстовое описание уровня доверия"""
        if self.trust_level >= 9:
            return "Легендарный путешественник 👑"
        elif self.trust_level >= 7:
            return "Надёжный профессионал 🌟"
        elif self.trust_level >= 5:
            return "Опытный попутчик ⭐"
        elif self.trust_level >= 3:
            return "Активный участник 👍"
        else:
            return "Новичок 🌱"

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'