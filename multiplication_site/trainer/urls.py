from django.urls import path
from . import views

urlpatterns = [
    path('', views.trainer_view, name='trainer'),
    path('start-session/', views.start_session, name='start_session'),
    path('start-daily-challenge/', views.start_daily_challenge_session, name='start_daily_challenge_session'),
    path('check-answer/', views.check_answer, name='check_answer'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('end-session/', views.end_session, name='end_session'),
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.session_settings, name='session_settings'),
    path('number-training/', views.number_training, name='number_training'),
    path('number-training-select/', views.number_training_select, name='number_training_select'),
    path('change-password/', views.change_password, name='change_password'),
    path('password-reset-request/', views.password_reset_request_view, name='password_reset_request'),
    path('admin-password-reset/<int:request_id>/', views.password_reset_confirm_admin, name='password_reset_confirm_admin'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
]