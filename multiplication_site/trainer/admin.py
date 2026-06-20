from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, TrainingSession, DailyChallenge, TrainingOnNumber, PasswordResetRequest


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Профиль'


class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'date_joined')
    search_fields = ('username', 'email')

    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ()}),
    )


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_questions', 'correct_answers', 'success_rate', 'last_daily_challenge_date']
    list_filter = ['last_daily_challenge_date']
    search_fields = ['user__username']
    readonly_fields = ['success_rate']

    def success_rate(self, obj):
        return f"{obj.success_rate}%"

    success_rate.short_description = "Успеваемость"


@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'start_time', 'end_time', 'total_questions', 'correct_answers', 'question_count',
                    'time_limit', 'success_rate']
    list_filter = ['user', 'start_time', 'question_count']
    search_fields = ['user__username']
    readonly_fields = ['start_time']

    def success_rate(self, obj):
        return f"{obj.success_rate}%"

    success_rate.short_description = "Успеваемость"


@admin.register(DailyChallenge)
class DailyChallengeAdmin(admin.ModelAdmin):
    list_display = ['date', 'a', 'b', 'correct_answer', 'solved_count']
    list_filter = ['date']
    search_fields = ['date']

    def solved_count(self, obj):
        return obj.solved_by.count()

    solved_count.short_description = "Решило пользователей"


@admin.register(TrainingOnNumber)
class TrainingOnNumberAdmin(admin.ModelAdmin):
    list_display = ['user', 'number', 'total_questions', 'correct_answers', 'success_rate']
    list_filter = ['number']
    search_fields = ['user__username']

    def success_rate(self, obj):
        return f"{obj.success_rate}%"

    success_rate.short_description = "Успеваемость"


@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'email', 'created_at', 'status']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'email']
    readonly_fields = ['user', 'email', 'created_at']
    list_editable = ['status']

    fieldsets = (
        ('Информация о запросе', {
            'fields': ('user', 'email', 'created_at', 'status')
        }),
        ('Заметки администратора', {
            'fields': ('admin_note',),
            'classes': ('wide',),
        }),
    )

    actions = ['approve_requests', 'reject_requests']

    def approve_requests(self, request, queryset):
        for reset_request in queryset:
            reset_request.status = 'approved'
            reset_request.save()
        self.message_user(request, f'Выбрано запросов: {queryset.count()}. Статус изменён на "Одобрено"')

    approve_requests.short_description = 'Одобрить выбранные запросы'

    def reject_requests(self, request, queryset):
        for reset_request in queryset:
            reset_request.status = 'rejected'
            reset_request.save()
        self.message_user(request, f'Выбрано запросов: {queryset.count()}. Статус изменён на "Отклонено"')

    reject_requests.short_description = 'Отклонить выбранные запросы'