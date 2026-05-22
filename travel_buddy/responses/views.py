from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.timezone import now
# from django_ratelimit.decorators import ratelimit  # ← УДАЛИТЕ
from routes.models import Route
from .models import Response
from travel_buddy.utils import log_action, send_notification


@login_required
# @ratelimit(key='user', rate='10/h', method='POST')  # ← УДАЛИТЕ
@log_action('Отклик на маршрут')
def response_create(request, route_id):
    # Проверка лимита (удалите этот блок)
    # was_limited = getattr(request, 'limited', False)
    # if was_limited:
    #     messages.warning(request, '❌ Слишком много откликов. Подождите немного перед новыми откликами.')
    #     return redirect('route_detail', route_id=route_id)
    
    route = get_object_or_404(Route, id=route_id)
    
    # Нельзя откликнуться на свой маршрут
    if route.author == request.user:
        messages.warning(request, 'Нельзя откликнуться на свой маршрут')
        return redirect('route_detail', route_id=route.id)
    
    # Проверяем, есть ли уже отклик
    existing = Response.objects.filter(route=route, user=request.user).first()
    if not existing:
        Response.objects.create(
            route=route,
            user=request.user,
            status='PENDING'
        )
        messages.success(request, 'Отклик отправлен!')
        
        # Уведомление на email автору маршрута
        if route.author.email:
            send_notification(
                route.author.email,
                f'Новый отклик на маршрут "{route.title}"',
                f'Здравствуйте, {route.author.username}!\n\n'
                f'Пользователь {request.user.username} хочет присоединиться к вашему маршруту "{route.title}".\n\n'
                f'Перейдите по ссылке, чтобы принять или отклонить отклик:\n'
                f'http://127.0.0.1:8000/route/{route.id}/\n\n'
                f'---\nС уважением, команда Travel Buddy'
            )
    else:
        messages.info(request, 'Вы уже откликались на этот маршрут')
    
    return redirect('route_detail', route_id=route.id)


@login_required
@log_action('Изменение статуса отклика')
def response_update(request, response_id):
    response = get_object_or_404(Response, id=response_id)
    
    # Только автор маршрута может менять статус
    if response.route.author == request.user:
        status = request.POST.get('status')
        if status in ['ACCEPTED', 'REJECTED']:
            old_status = response.status
            response.status = status
            response.save()
            status_display = dict(Response.STATUS_CHOICES).get(status, status)
            messages.success(request, f'Статус отклика изменён на "{status_display}"')
            
            # Обновляем уровень доверия, если отклик принят и маршрут завершён
            if status == 'ACCEPTED' and response.route.end_date < now().date():
                response.user.update_trust_level()
            
            # Уведомление на email участнику
            if response.user.email and old_status != status:
                status_text = 'принят' if status == 'ACCEPTED' else 'отклонён'
                send_notification(
                    response.user.email,
                    f'Статус вашего отклика изменён',
                    f'Здравствуйте, {response.user.username}!\n\n'
                    f'Ваш отклик на маршрут "{response.route.title}" был {status_text}.\n\n'
                    f'Подробнее: http://127.0.0.1:8000/route/{response.route.id}/\n\n'
                    f'---\nС уважением, команда Travel Buddy'
                )
    
    return redirect('route_detail', route_id=response.route.id)