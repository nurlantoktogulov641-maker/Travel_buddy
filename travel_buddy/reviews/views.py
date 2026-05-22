from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
# from django_ratelimit.decorators import ratelimit  # ← УДАЛИТЕ
from routes.models import Route
from users.models import User
from .models import Review
from .forms import ReviewForm
from travel_buddy.utils import log_action


@login_required
# @ratelimit(key='user', rate='10/h', method='POST')  # ← УДАЛИТЕ
@log_action('Оставление отзыва')
def review_create(request, route_id, user_id):
    # Проверка лимита (удалите этот блок)
    # was_limited = getattr(request, 'limited', False)
    # if was_limited:
    #     messages.warning(request, '❌ Слишком много отзывов. Подождите немного перед новыми отзывами.')
    #     return redirect('route_detail', route_id=route_id)
    
    route = get_object_or_404(Route, id=route_id)
    target_user = get_object_or_404(User, id=user_id)
    
    if request.user == target_user:
        messages.warning(request, 'Нельзя оставить отзыв о себе')
        return redirect('route_detail', route_id=route.id)
    
    existing = Review.objects.filter(author=request.user, target_user=target_user, route=route).first()
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.author = request.user
            review.target_user = target_user
            review.route = route
            review.save()
            
            # Обновляем рейтинг
            reviews = Review.objects.filter(target_user=target_user)
            avg_rating = sum(r.rating for r in reviews) / reviews.count()
            target_user.rating = avg_rating
            target_user.save()
            
            # Обновляем уровень доверия получателя
            target_user.update_trust_level()
            
            messages.success(request, 'Отзыв успешно добавлен!')
            return redirect('route_detail', route_id=route.id)
    else:
        form = ReviewForm()
    
    return render(request, 'reviews/create.html', {
        'form': form,
        'route': route,
        'target_user': target_user,
        'existing': existing
    })


@login_required
@log_action('Редактирование отзыва')
def review_edit(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    
    if review.author != request.user:
        return redirect('route_detail', route_id=review.route.id)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            
            # Обновляем рейтинг
            reviews = Review.objects.filter(target_user=review.target_user)
            avg_rating = sum(r.rating for r in reviews) / reviews.count()
            review.target_user.rating = avg_rating
            review.target_user.save()
            
            # Обновляем уровень доверия получателя
            review.target_user.update_trust_level()
            
            messages.success(request, 'Отзыв изменён!')
            return redirect('route_detail', route_id=review.route.id)
    else:
        form = ReviewForm(instance=review)
    
    return render(request, 'reviews/edit.html', {'form': form, 'review': review})


@login_required
@log_action('Удаление отзыва')
def review_delete(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    route_id = review.route.id
    target_user = review.target_user
    
    if review.author == request.user:
        review.delete()
        
        # Обновляем рейтинг
        reviews = Review.objects.filter(target_user=target_user)
        if reviews.exists():
            avg_rating = sum(r.rating for r in reviews) / reviews.count()
            target_user.rating = avg_rating
        else:
            target_user.rating = 0
        target_user.save()
        
        # Обновляем уровень доверия получателя
        target_user.update_trust_level()
        
        messages.success(request, 'Отзыв удалён!')
    
    return redirect('route_detail', route_id=route_id)