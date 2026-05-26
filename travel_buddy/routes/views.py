import json

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Count, Q
from django.views.decorators.cache import never_cache
from datetime import date, timedelta
from itertools import chain

from .models import Route, Tag, RouteImage, Favorite, RouteComment, RouteLike
from responses.models import Response
from reviews.models import Review
from .forms import RouteForm, CommentForm
from travel_buddy.utils import log_action
from .utils import generate_route_pdf
from travel_buddy.utils import notify_new_response, notify_response_status_changed


@log_action('Просмотр главной страницы')
def home(request):
    routes_list = Route.objects.filter(status='ACTIVE').annotate(
        responses_count=Count('responses', filter=Q(responses__status='ACCEPTED'))
    )
    
    # Фильтрация по тегам (множественный выбор)
    tags_ids = request.GET.getlist('tags')
    if tags_ids and tags_ids[0]:
        routes_list = routes_list.filter(tags__id__in=tags_ids).distinct()
    
    min_budget = request.GET.get('min_budget')
    max_budget = request.GET.get('max_budget')
    if min_budget:
        routes_list = routes_list.filter(budget__gte=min_budget)
    if max_budget:
        routes_list = routes_list.filter(budget__lte=max_budget)
    
    search = request.GET.get('search')
    if search:
        routes_list = routes_list.filter(title__icontains=search)
    
    sort = request.GET.get('sort', '-created_at')
    if sort == 'budget':
        routes_list = routes_list.order_by('budget')
    elif sort == '-budget':
        routes_list = routes_list.order_by('-budget')
    elif sort == 'start_date':
        routes_list = routes_list.order_by('start_date')
    else:
        routes_list = routes_list.order_by('-created_at')
    
    paginator = Paginator(routes_list, 6)
    page_number = request.GET.get('page')
    routes = paginator.get_page(page_number)
    
    tags = Tag.objects.all()
    popular_routes = Route.objects.filter(status='ACTIVE').order_by('-views_count')[:5]
    
    return render(request, 'routes/home.html', {
        'routes': routes,
        'tags': tags,
        'popular_routes': popular_routes,
        'selected_tags': tags_ids,
    })


@never_cache
@log_action('Просмотр маршрута')
def route_detail(request, route_id):
    route = get_object_or_404(Route, id=route_id)
    route.views_count += 1
    route.save()
    
    # ===== ОТКЛИК ПОЛЬЗОВАТЕЛЯ =====
    user_response = None
    if request.user.is_authenticated:
        user_response = Response.objects.filter(route=route, user=request.user).first()
    
    responses = Response.objects.filter(route=route).order_by('-created_at')
    reviews = Review.objects.filter(route=route).order_by('-created_at')
    
    # ===== УЛУЧШЕННЫЕ ПОХОЖИЕ МАРШРУТЫ =====
    similar_routes_base = Route.objects.filter(
        status='ACTIVE'
    ).exclude(id=route.id)

    # 1. По тегам (основной критерий)
    similar_by_tags = similar_routes_base.filter(
        tags__in=route.tags.all()
    ).distinct()

    # 2. По бюджету (±30%) - ИСПРАВЛЕНО
    if route.budget:
        budget_value = float(route.budget)
        budget_min = budget_value * 0.7
        budget_max = budget_value * 1.3
        similar_by_budget = similar_routes_base.filter(
            budget__gte=budget_min,
            budget__lte=budget_max
        )
    else:
        similar_by_budget = Route.objects.none()

    # 3. По датам (близкие даты ±30 дней)
    if route.start_date:
        similar_by_dates = similar_routes_base.filter(
        start_date__gte=route.start_date - timedelta(days=30),
        start_date__lte=route.start_date + timedelta(days=30)
    )
    else:
        similar_by_dates = Route.objects.none()

    # Объединяем и убираем дубликаты
    similar_combined = list(chain(similar_by_tags, similar_by_budget, similar_by_dates))
    seen_ids = set()
    unique_similar = []
    for r in similar_combined:
        if r.id not in seen_ids:
            seen_ids.add(r.id)
            unique_similar.append(r)

    similar_routes_result = unique_similar[:5]
    
    # ===== ИСТОРИЯ ПРОСМОТРОВ =====
    viewed_routes = request.session.get('viewed_routes', [])
    
    if route_id in viewed_routes:
        viewed_routes.remove(route_id)
    
    viewed_routes.insert(0, route_id)
    
    if len(viewed_routes) > 10:
        viewed_routes = viewed_routes[:10]
    
    request.session['viewed_routes'] = viewed_routes
    
    # Получаем объекты маршрутов из истории
    recent_routes = []
    if viewed_routes:
        recent_routes_qs = Route.objects.filter(id__in=viewed_routes, status='ACTIVE')
        recent_routes = sorted(recent_routes_qs, key=lambda x: viewed_routes.index(x.id))
    
    # ===== КОММЕНТАРИИ =====
    comments = RouteComment.objects.filter(route=route).order_by('-created_at')
    
    if request.method == 'POST' and 'comment_text' in request.POST:
        if request.user.is_authenticated:
            form = CommentForm(request.POST)
            if form.is_valid():
                RouteComment.objects.create(
                    route=route,
                    author=request.user,
                    text=form.cleaned_data['text']
                )
                messages.success(request, 'Комментарий добавлен!')
                return redirect('route_detail', route_id=route.id)
        else:
            messages.error(request, 'Чтобы оставить комментарий, войдите в систему')
            return redirect('login')
    else:
        form = CommentForm()

    # ===== ДАННЫЕ ДЛЯ КАРТЫ (Leaflet + OpenStreetMap) =====
    # Готовые координаты из модели (если есть)
    map_points = route.get_map_points()

    # Названия городов для клиентского геокодинга через Nominatim
    geocode_names = []
    if route.start_city:
        geocode_names.append(route.start_city.strip())
    if route.waypoints:
        for point in route.waypoints.split(','):
            point = point.strip()
            if point:
                geocode_names.append(point)
    if route.end_city:
        geocode_names.append(route.end_city.strip())

    map_points_json = json.dumps(map_points, ensure_ascii=False)
    geocode_names_json = json.dumps(geocode_names, ensure_ascii=False)

    return render(request, 'routes/detail.html', {
        'route': route,
        'user_response': user_response,
        'responses': responses,
        'reviews': reviews,
        'similar_routes': similar_routes_result,
        'recent_routes': recent_routes,
        'comments': comments,
        'comment_form': form,
        'map_points_json': map_points_json,
        'geocode_names_json': geocode_names_json,
    })


@login_required
@log_action('Создание маршрута')
def route_create(request):
    if request.method == 'POST':
        form = RouteForm(request.POST, request.FILES)
        if form.is_valid():
            route = form.save(commit=False)
            route.author = request.user
            route.save()
            form.save_m2m()
            
            if request.FILES.get('image'):
                route.image = request.FILES['image']
                route.save()
            
            extra_images = request.FILES.getlist('extra_images')
            for idx, img in enumerate(extra_images):
                RouteImage.objects.create(
                    route=route,
                    image=img,
                    order=idx
                )
            
            messages.success(request, 'Маршрут успешно создан!')
            return redirect('route_detail', route_id=route.id)
    else:
        form = RouteForm()
    return render(request, 'routes/create_with_2gis.html', {'form': form})


@login_required
@log_action('Редактирование маршрута')
def route_edit(request, route_id):
    route = get_object_or_404(Route, id=route_id)
    if route.author != request.user:
        return redirect('route_detail', route_id=route.id)
    
    if request.method == 'POST':
        form = RouteForm(request.POST, request.FILES, instance=route)
        if form.is_valid():
            form.save()
            messages.success(request, 'Маршрут успешно обновлён!')
            return redirect('route_detail', route_id=route.id)
    else:
        form = RouteForm(instance=route)
    return render(request, 'routes/edit.html', {'form': form, 'route': route})


@login_required
@log_action('Удаление маршрута')
def route_delete(request, route_id):
    route = get_object_or_404(Route, id=route_id)
    if route.author == request.user:
        route.delete()
        messages.success(request, 'Маршрут удалён!')
    return redirect('home')


@login_required
@log_action('Добавление в избранное')
def add_to_favorites(request, route_id):
    route = get_object_or_404(Route, id=route_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, route=route)
    if created:
        messages.success(request, f'Маршрут "{route.title}" добавлен в избранное!')
    else:
        messages.info(request, f'Маршрут "{route.title}" уже в избранном')
    return redirect('route_detail', route_id=route.id)


@login_required
@log_action('Удаление из избранного')
def remove_from_favorites(request, route_id):
    route = get_object_or_404(Route, id=route_id)
    Favorite.objects.filter(user=request.user, route=route).delete()
    messages.success(request, f'Маршрут "{route.title}" удалён из избранного')
    return redirect('route_detail', route_id=route.id)


@login_required
@log_action('Просмотр избранных маршрутов')
def my_favorites(request):
    favorites_list = Favorite.objects.filter(user=request.user).select_related('route').order_by('-created_at')
    paginator = Paginator(favorites_list, 6)
    page_number = request.GET.get('page')
    favorites = paginator.get_page(page_number)
    return render(request, 'routes/my_favorites.html', {'favorites': favorites})


@log_action('Просмотр участников маршрута')
def route_participants(request, route_id):
    route = get_object_or_404(Route, id=route_id)
    participants = Response.objects.filter(route=route, status='ACCEPTED').select_related('user')
    return render(request, 'routes/participants.html', {
        'route': route,
        'participants': participants
    })


@login_required
def export_route_pdf(request, route_id):
    route = get_object_or_404(Route, id=route_id)
    return generate_route_pdf(route, request)


@login_required
def toggle_like(request, route_id):
    route = get_object_or_404(Route, id=route_id)
    like, created = RouteLike.objects.get_or_create(route=route, user=request.user)
    if not created:
        like.delete()
        messages.success(request, 'Лайк убран')
    else:
        messages.success(request, 'Вы лайкнули маршрут!')
    return redirect('route_detail', route_id=route.id)