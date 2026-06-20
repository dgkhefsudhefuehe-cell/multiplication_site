from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.contrib.auth.models import User
from .forms import RegisterForm, LoginForm
from .models import UserProfile, TrainingSession, DailyChallenge, TrainingOnNumber, PasswordResetRequest
import random
from datetime import datetime
from django.utils.timezone import make_aware


def generate_example():
    a = random.randint(2, 9)
    b = random.randint(2, 9)
    return a, b, a * b


def generate_number_example(number):
    b = random.randint(2, 9)
    a = number
    return a, b, a * b


def get_encouragement_message(correct_percent):
    if correct_percent >= 90:
        return "Ты настоящий гений! Продолжай в том же духе! 🌟"
    elif correct_percent >= 70:
        return "Отличная работа! Ты очень стараешься! 🎉"
    elif correct_percent >= 50:
        return "Неплохо! Ещё немного практики и будет отлично! 💪"
    elif correct_percent >= 30:
        return "Хороший прогресс! Продолжай тренироваться! 📚"
    else:
        return "Ты молодец! С каждой тренировкой ты становишься лучше! ✨"


def register_view(request):
    if request.user.is_authenticated:
        return redirect('trainer')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}! 🎉')
            return redirect('trainer')
    else:
        form = RegisterForm()

    return render(request, 'trainer/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('trainer')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'С возвращением, {username}! 👋')
                return redirect('trainer')
        messages.error(request, 'Неверное имя пользователя или пароль ❌')
    else:
        form = LoginForm()

    return render(request, 'trainer/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


def password_reset_request_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        if not email:
            messages.error(request, 'Пожалуйста, введите email')
            return redirect('password_reset_request')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, 'Пользователь с таким email не найден.')
            return redirect('password_reset_request')

        reset_request = PasswordResetRequest.objects.create(
            user=user,
            email=email,
            status='pending'
        )

        messages.success(request, f'Запрос на сброс пароля для пользователя {user.username} отправлен администратору.')
        return redirect('login')

    return render(request, 'trainer/password_reset_request.html')


def password_reset_confirm_admin(request, request_id):
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('login')

    reset_request = get_object_or_404(PasswordResetRequest, id=request_id)

    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not new_password or not confirm_password:
            messages.error(request, 'Пожалуйста, заполните все поля')
        elif new_password != confirm_password:
            messages.error(request, 'Пароли не совпадают')
        elif len(new_password) < 4:
            messages.error(request, 'Пароль должен быть не короче 4 символов')
        else:
            user = reset_request.user
            user.set_password(new_password)
            user.save()

            reset_request.status = 'completed'
            reset_request.save()

            messages.success(request, f'Пароль для пользователя {user.username} успешно изменён!')
            return redirect('admin_panel')

    context = {
        'reset_request': reset_request,
        'user': reset_request.user,
    }
    return render(request, 'trainer/password_reset_admin.html', context)


@login_required
def change_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')

        if not request.user.check_password(old_password):
            messages.error(request, 'Неверный старый пароль ❌')
            return redirect('profile')

        if new_password1 != new_password2:
            messages.error(request, 'Новые пароли не совпадают ❌')
            return redirect('profile')

        if len(new_password1) < 4:
            messages.error(request, 'Пароль должен быть не короче 4 символов ❌')
            return redirect('profile')

        request.user.set_password(new_password1)
        request.user.save()
        update_session_auth_hash(request, request.user)

        messages.success(request, 'Пароль успешно изменён! ✅')
        return redirect('profile')

    return redirect('profile')


def is_admin(user):
    return user.is_staff or user.is_superuser


@user_passes_test(is_admin)
def admin_panel(request):
    total_users = User.objects.count()
    total_sessions = TrainingSession.objects.count()
    total_questions_solved = TrainingSession.objects.aggregate(Sum('total_questions'))['total_questions__sum'] or 0
    total_correct = TrainingSession.objects.aggregate(Sum('correct_answers'))['correct_answers__sum'] or 0
    pending_requests = PasswordResetRequest.objects.filter(status='pending').count()

    recent_users = User.objects.order_by('-date_joined')[:10]
    recent_sessions = TrainingSession.objects.select_related('user').order_by('-start_time')[:10]
    reset_requests = PasswordResetRequest.objects.select_related('user').filter(status='pending').order_by(
        '-created_at')

    total_challenges = DailyChallenge.objects.count()
    total_solved = 0
    for challenge in DailyChallenge.objects.all():
        total_solved += challenge.solved_by.count()

    context = {
        'total_users': total_users,
        'total_sessions': total_sessions,
        'total_questions_solved': total_questions_solved,
        'total_correct': total_correct,
        'average_percent': round(total_correct / total_questions_solved * 100) if total_questions_solved > 0 else 0,
        'recent_users': recent_users,
        'recent_sessions': recent_sessions,
        'total_challenges': total_challenges,
        'total_solved': total_solved,
        'pending_requests': pending_requests,
        'reset_requests': reset_requests,
    }
    return render(request, 'trainer/admin_panel.html', context)


@login_required
def profile_view(request):
    profile = request.user.profile
    all_sessions = TrainingSession.objects.filter(user=request.user).order_by('-start_time')
    last_sessions = all_sessions[:10]

    daily_stats = TrainingSession.objects.filter(
        user=request.user
    ).annotate(
        date=TruncDate('start_time')
    ).values('date').annotate(
        total_questions=Sum('total_questions'),
        correct_answers=Sum('correct_answers')
    ).order_by('-date')[:7]

    number_trainings = TrainingOnNumber.objects.filter(user=request.user)

    context = {
        'profile': profile,
        'all_sessions': all_sessions,
        'last_sessions': last_sessions,
        'daily_stats': daily_stats,
        'total_sessions': all_sessions.count(),
        'number_trainings': number_trainings,
    }
    return render(request, 'trainer/profile.html', context)


@login_required
def start_session(request):
    if request.method == 'POST':
        mode = request.POST.get('mode', 'normal')

        question_count_str = request.POST.get('question_count', '10')
        if question_count_str == 'custom':
            question_count = int(request.POST.get('custom_questions', 10))
        else:
            question_count = int(question_count_str)

        # Получаем общее время
        total_time_str = request.POST.get('total_time', '300')
        if total_time_str == 'custom':
            custom_time = request.POST.get('custom_time', '5')
            # Парсим время (поддерживаем формат 1.30, 2.5, 60)
            try:
                if '.' in custom_time:
                    parts = custom_time.split('.')
                    minutes = int(parts[0]) if parts[0] else 0
                    seconds = float('0.' + parts[1]) * 100 if len(parts) > 1 else 0
                    total_time = int(minutes * 60 + seconds)
                else:
                    total_time = int(float(custom_time))
            except (ValueError, IndexError):
                total_time = 300
        else:
            total_time = int(total_time_str)

        # Валидация на сервере
        def get_min_total(count):
            if count >= 100: return 600
            if count >= 50: return 300
            if count >= 30: return 180
            if count >= 20: return 120
            if count >= 10: return 60
            return 30

        min_total = get_min_total(question_count)

        if total_time < min_total:
            messages.error(request, f'Для {question_count} вопросов нужно минимум {min_total} секунд.')
            return redirect('trainer')

        if question_count < 1:
            question_count = 1
        if total_time < 1:
            total_time = 1

        time_per_question = max(1, total_time // question_count)

        request.session.pop('current_session_id', None)
        request.session.pop('session_stats', None)
        request.session.pop('current_example', None)
        request.session.pop('question_start_time', None)

        request.session['session_settings'] = {
            'question_count': question_count,
            'time_per_question': time_per_question,
            'mode': mode
        }

        session = TrainingSession.objects.create(
            user=request.user,
            question_count=question_count,
            time_limit=time_per_question
        )
        request.session['current_session_id'] = session.id
        request.session['session_stats'] = {'total': 0, 'correct': 0}

        messages.success(request,
                         f'Тренировка началась! {question_count} вопросов. ⏱️ На каждый вопрос: {time_per_question} сек.')
        return redirect('trainer')

    return redirect('trainer')


@login_required
def start_daily_challenge_session(request):
    profile = request.user.profile

    if not profile.can_do_daily_challenge():
        messages.warning(request, 'Ты уже выполнил задание дня сегодня! Приходи завтра! ⭐')
        return redirect('trainer')

    today = timezone.now().date()
    challenge, created = DailyChallenge.objects.get_or_create(
        date=today,
        defaults={'a': random.randint(2, 9), 'b': random.randint(2, 9), 'correct_answer': 0}
    )
    if challenge.correct_answer == 0:
        challenge.correct_answer = challenge.a * challenge.b
        challenge.save()

    request.session.pop('current_session_id', None)
    request.session.pop('session_stats', None)
    request.session.pop('current_example', None)
    request.session.pop('question_start_time', None)

    request.session['session_settings'] = {
        'question_count': 1,
        'time_per_question': 0,
        'mode': 'daily_challenge'
    }

    session = TrainingSession.objects.create(
        user=request.user,
        question_count=1,
        time_limit=0
    )
    request.session['current_session_id'] = session.id
    request.session['session_stats'] = {'total': 0, 'correct': 0}

    messages.success(request, f'Задание дня началось! Реши пример {challenge.a} × {challenge.b} 🌟')
    return redirect('trainer')


@login_required
def trainer_view(request):
    current_session_id = request.session.get('current_session_id')

    if not current_session_id:
        return render(request, 'trainer/start_session.html')

    try:
        session = TrainingSession.objects.get(id=current_session_id, user=request.user)
    except TrainingSession.DoesNotExist:
        request.session.pop('current_session_id', None)
        return render(request, 'trainer/start_session.html')

    settings = request.session.get('session_settings', {'question_count': 10, 'total_time': 300})

    # Проверяем, закончилась ли тренировка по времени
    total_time = settings.get('total_time', 300)
    if total_time > 0:
        start_time = request.session.get('session_start_time')
        if start_time is None:
            start_time = timezone.now()
            request.session['session_start_time'] = start_time.isoformat()
        elif isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
            if timezone.is_naive(start_time):
                start_time = make_aware(start_time)

        elapsed = (timezone.now() - start_time).total_seconds()
        if elapsed >= total_time:
            # Время вышло - завершаем тренировку
            request.session['message'] = "⏰ Время вышло!"
            return redirect('end_session')
        time_left = max(0, int(total_time - elapsed))
    else:
        time_left = 0

    # Проверяем, ответил ли пользователь на все вопросы
    if session.total_questions >= settings.get('question_count', 10):
        return redirect('end_session')

    # Генерируем текущий пример
    current_example = request.session.get('current_example')
    if current_example is None:
        if settings.get('mode') == 'number_train':
            number = settings.get('train_number', 2)
            a, b, correct = generate_number_example(number)
        elif settings.get('mode') == 'daily_challenge':
            today = timezone.now().date()
            challenge = DailyChallenge.objects.get(date=today)
            a, b, correct = challenge.a, challenge.b, challenge.correct_answer
        else:
            a, b, correct = generate_example()
        current_example = {'a': a, 'b': b, 'correct': correct}
        request.session['current_example'] = current_example

    profile = request.user.profile
    session_stats = request.session.get('session_stats', {'total': 0, 'correct': 0})
    encouragement = get_encouragement_message(
        profile.success_rate) if profile.total_questions > 0 else "Начни тренировку! 🎓"

    context = {
        'a': current_example['a'],
        'b': current_example['b'],
        'session_total': session_stats['total'],
        'session_correct': session_stats['correct'],
        'session_percent': round(session_stats['correct'] / session_stats['total'] * 100) if session_stats[
                                                                                                 'total'] > 0 else 0,
        'total_questions': profile.total_questions,
        'total_correct': profile.correct_answers,
        'total_percent': profile.success_rate,
        'encouragement': encouragement,
        'question_count': settings.get('question_count', 10),
        'questions_done': session.total_questions,
        'time_left': time_left,
        'time_limit': total_time,
        'mode': settings.get('mode', 'normal'),
    }
    return render(request, 'trainer/index.html', context)


@login_required
def check_answer(request):
    if request.method == 'POST':
        user_answer = request.POST.get('answer')
        current_example = request.session.get('current_example')
        settings = request.session.get('session_settings', {'question_count': 10, 'total_time': 300})

        if current_example and user_answer is not None:
            try:
                user_answer = int(user_answer)
                correct_answer = current_example['correct']

                session_stats = request.session.get('session_stats', {'total': 0, 'correct': 0})
                session_stats['total'] += 1

                is_correct = user_answer == correct_answer
                if is_correct:
                    session_stats['correct'] += 1
                    message = "Верно! Отличный ответ! ✅"
                else:
                    message = f"Неверно. {current_example['a']} × {current_example['b']} = {correct_answer} ❌"

                request.session['session_stats'] = session_stats

                session_id = request.session.get('current_session_id')
                if session_id:
                    try:
                        training_session = TrainingSession.objects.get(id=session_id, user=request.user)
                        training_session.total_questions += 1
                        if is_correct:
                            training_session.correct_answers += 1
                        training_session.save()
                    except TrainingSession.DoesNotExist:
                        pass

                request.session['message'] = message

                # Генерируем новый пример
                if settings.get('mode') == 'number_train':
                    number = settings.get('train_number', 2)
                    a, b, correct = generate_number_example(number)
                elif settings.get('mode') == 'daily_challenge':
                    today = timezone.now().date()
                    challenge = DailyChallenge.objects.get(date=today)
                    a, b, correct = challenge.a, challenge.b, challenge.correct_answer
                else:
                    a, b, correct = generate_example()

                request.session['current_example'] = {'a': a, 'b': b, 'correct': correct}

            except ValueError:
                request.session['message'] = "Введите число ⚠️"

    return redirect('trainer')


@login_required
def end_session(request):
    request.session.pop('current_session_id', None)
    request.session.pop('session_stats', None)
    request.session.pop('current_example', None)
    request.session.pop('question_start_time', None)
    messages.info(request, 'Сессия завершена. 🏁')
    return redirect('trainer')


@login_required
def session_settings(request):
    if request.method == 'POST':
        time_per_question = int(request.POST.get('time_per_question', 30))
        question_count = int(request.POST.get('question_count', 10))

        request.session['session_settings'] = {
            'question_count': question_count,
            'time_per_question': time_per_question,
            'mode': 'normal'
        }
        request.session.pop('current_session_id', None)
        request.session.pop('session_stats', None)
        request.session.pop('current_example', None)
        request.session.pop('question_start_time', None)
        messages.success(request, 'Настройки сохранены! ⚙️')
    return redirect('trainer')


@login_required
def number_training(request):
    if request.method == 'POST':
        number = request.POST.get('number')

        if not number:
            messages.error(request, 'Пожалуйста, выберите число')
            return redirect('number_training_select')

        number = int(number)

        request.session.pop('current_session_id', None)
        request.session.pop('session_stats', None)
        request.session.pop('current_example', None)
        request.session.pop('question_start_time', None)

        request.session['session_settings'] = {
            'question_count': 10,
            'time_per_question': 0,
            'mode': 'number_train',
            'train_number': number
        }

        session = TrainingSession.objects.create(
            user=request.user,
            question_count=10,
            time_limit=0
        )
        request.session['current_session_id'] = session.id
        request.session['session_stats'] = {'total': 0, 'correct': 0}

        messages.success(request, f'Тренировка на число {number} началась! 🔢')
        return redirect('trainer')

    return redirect('trainer')


@login_required
def number_training_select(request):
    if request.method == 'POST':
        number = request.POST.get('number')
        if not number:
            messages.error(request, 'Пожалуйста, выберите число')
            return redirect('number_training_select')

        number = int(number)

        request.session.pop('current_session_id', None)
        request.session.pop('session_stats', None)
        request.session.pop('current_example', None)
        request.session.pop('question_start_time', None)

        request.session['session_settings'] = {
            'question_count': 10,
            'time_per_question': 0,
            'mode': 'number_train',
            'train_number': number
        }

        session = TrainingSession.objects.create(
            user=request.user,
            question_count=10,
            time_limit=0
        )
        request.session['current_session_id'] = session.id
        request.session['session_stats'] = {'total': 0, 'correct': 0}

        messages.success(request, f'Тренировка на число {number} началась! 🔢')
        return redirect('trainer')

    return render(request, 'trainer/number_select.html')