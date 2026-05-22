from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.core.paginator import Paginator
# from django_ratelimit.decorators import ratelimit  # ← УДАЛИТЕ ЭТУ СТРОКУ
from .models import User
from routes.models import Route
from reviews.models import Review
from responses.models import Response
from .forms import RegisterForm
from travel_buddy.utils import log_action


@log_action('Регистрация пользователя')
# @ratelimit(key='ip', rate='3/h', method='POST')  # ← УДАЛИТЕ ЭТУ СТРОКУ
def register(request):
    # Проверка лимита (удалите этот блок, если есть)
    # was_limited = getattr(request, 'limited', False)
    # if was_limited:
    #     messages.error(request, '❌ Слишком много попыток регистрации. Попробуйте позже.')
    #     return redirect('home')
    
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})


@log_action('Вход в систему')
# @ratelimit(key='ip', rate='5/m', method='POST')  # ← УДАЛИТЕ ЭТУ СТРОКУ
def user_login(request):
    # Проверка лимита (удалите этот блок, если есть)
    # was_limited = getattr(request, 'limited', False)
    # if was_limited:
    #     messages.error(request, '❌ Слишком много попыток входа. Подождите минуту и попробуйте снова.')
    #     return redirect('login')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Добро пожаловать, {username}!')
            return redirect('home')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    return render(request, 'registration/login.html')


@log_action('Выход из системы')
def user_logout(request):
    from django.contrib.auth import logout
    logout(request)
    messages.info(request, 'Вы вышли из системы')
    return redirect('home')


@login_required
def profile(request, user_id):
    profile_user = get_object_or_404(User, id=user_id)
    user_routes = Route.objects.filter(author=profile_user).order_by('-created_at')
    user_responses = Response.objects.filter(user=profile_user).order_by('-created_at')
    reviews_about = Review.objects.filter(target_user=profile_user).order_by('-created_at')
    return render(request, 'users/profile.html', {
        'profile_user': profile_user,
        'user_routes': user_routes,
        'user_responses': user_responses,
        'reviews_about': reviews_about,
    })


@login_required
@log_action('Редактирование профиля')
def profile_edit(request, user_id):
    profile_user = get_object_or_404(User, id=user_id)
    if profile_user != request.user:
        return redirect('profile', user_id=profile_user.id)
    if request.method == 'POST':
        profile_user.bio = request.POST.get('bio', '')
        profile_user.interests = request.POST.get('interests', '')
        if request.FILES.get('avatar'):
            profile_user.avatar = request.FILES['avatar']
        profile_user.save()
        messages.success(request, 'Профиль обновлён!')
        return redirect('profile', user_id=profile_user.id)
    return render(request, 'users/profile_edit.html', {'profile_user': profile_user})


@login_required
def my_routes(request):
    routes = Route.objects.filter(author=request.user).order_by('-created_at')
    paginator = Paginator(routes, 6)
    page_number = request.GET.get('page')
    routes = paginator.get_page(page_number)
    return render(request, 'users/my_routes.html', {'routes': routes})


@login_required
def my_responses(request):
    responses = Response.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(responses, 6)
    page_number = request.GET.get('page')
    responses = paginator.get_page(page_number)
    return render(request, 'users/my_responses.html', {'responses': responses})