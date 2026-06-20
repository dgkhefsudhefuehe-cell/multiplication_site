from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    total_questions = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    last_daily_challenge_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'

    def __str__(self):
        return f"Профиль {self.user.username}"

    @property
    def success_rate(self):
        if self.total_questions == 0:
            return 0
        return round((self.correct_answers / self.total_questions) * 100)

    def can_do_daily_challenge(self):
        today = timezone.now().date()
        return self.last_daily_challenge_date != today


class TrainingSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    total_questions = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    question_count = models.IntegerField(default=10)
    time_limit = models.IntegerField(default=60)

    class Meta:
        verbose_name = 'Сессия тренировки'
        verbose_name_plural = 'Сессии тренировок'

    def __str__(self):
        return f"Сессия {self.user.username} - {self.start_time}"

    @property
    def success_rate(self):
        if self.total_questions == 0:
            return 0
        return round((self.correct_answers / self.total_questions) * 100)


class DailyChallenge(models.Model):
    date = models.DateField(default=timezone.now, unique=True)
    a = models.IntegerField()
    b = models.IntegerField()
    correct_answer = models.IntegerField()
    solved_by = models.ManyToManyField(User, blank=True, related_name='completed_challenges')

    class Meta:
        verbose_name = 'Задание дня'
        verbose_name_plural = 'Задания дня'

    def __str__(self):
        return f"Задание на {self.date}: {self.a} × {self.b}"


class TrainingOnNumber(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='number_trainings')
    number = models.IntegerField()
    total_questions = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Тренировка на число'
        verbose_name_plural = 'Тренировки на числа'
        unique_together = ['user', 'number']

    @property
    def success_rate(self):
        if self.total_questions == 0:
            return 0
        return round((self.correct_answers / self.total_questions) * 100)


class PasswordResetRequest(models.Model):
    """Модель для хранения запросов на сброс пароля"""
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
        ('completed', 'Выполнено'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_requests')
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_note = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Запрос на сброс пароля'
        verbose_name_plural = 'Запросы на сброс пароля'
        ordering = ['-created_at']

    def __str__(self):
        return f"Запрос от {self.user.username} - {self.created_at.strftime('%d.%m.%Y %H:%M')}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()