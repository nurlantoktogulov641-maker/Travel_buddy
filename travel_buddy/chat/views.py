from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
# from django_ratelimit.decorators import ratelimit  # ← УДАЛИТЕ
from .models import Message, PrivateMessage
from routes.models import Route
from responses.models import Response
from travel_buddy.utils import log_action, send_notification
from django.http import JsonResponse


@login_required
# @ratelimit(key='user', rate='30/m', method='POST')  # ← УДАЛИТЕ
@log_action('Отправка сообщения в чат')
def chat_room(request, route_id):
    # Проверка лимита (удалите этот блок, если есть)
    # was_limited = getattr(request, 'limited', False)
    # if was_limited:
    #     messages.warning(request, '❌ Слишком много сообщений. Подождите немного перед отправкой новых сообщений.')
    #     return redirect('chat_room', route_id=route_id)
    
    route = get_object_or_404(Route, id=route_id)
    
    is_participant = (request.user == route.author)
    if not is_participant:
        response = Response.objects.filter(route=route, user=request.user, status='ACCEPTED').first()
        if response:
            is_participant = True
    
    if not is_participant:
        messages.warning(request, 'У вас нет доступа к этому чату')
        return redirect('route_detail', route_id=route.id)
    
    if request.method == 'POST':
        text = request.POST.get('text')
        if text:
            message = Message.objects.create(
                route=route,
                sender=request.user,
                text=text
            )
            
            # ===== УВЕДОМЛЕНИЯ ВСЕМ УЧАСТНИКАМ (кроме отправителя) =====
            
            # Собираем получателей: автор маршрута
            recipients_emails = []
            if route.author != request.user and route.author.email:
                recipients_emails.append(route.author.email)
            
            # Добавляем участников с принятым откликом
            accepted_responses = Response.objects.filter(route=route, status='ACCEPTED')
            for resp in accepted_responses:
                if resp.user != request.user and resp.user.email:
                    recipients_emails.append(resp.user.email)
            
            # Убираем дубликаты
            recipients_emails = list(set(recipients_emails))
            
            # Отправляем уведомления
            for email in recipients_emails:
                send_notification(
                    email,
                    f'Новое сообщение в чате маршрута "{route.title}"',
                    f'Здравствуйте!\n\n'
                    f'Пользователь {request.user.username} отправил сообщение в чате маршрута "{route.title}":\n\n'
                    f'"{text[:200]}{"..." if len(text) > 200 else ""}"\n\n'
                    f'🔗 Перейти в чат: http://127.0.0.1:8000/chat/{route.id}/\n\n'
                    f'---\nС уважением, команда Travel Buddy'
                )
            
        return redirect('chat_room', route_id=route.id)
    
    messages_list = Message.objects.filter(route=route).order_by('created_at')
    
    return render(request, 'chat/room.html', {
        'route': route,
        'messages': messages_list
    })


@login_required
# @ratelimit(key='user', rate='30/m', method='POST')  # ← УДАЛИТЕ
@log_action('Отправка личного сообщения')
def private_chat(request, user_id):
    """Личный чат с пользователем"""
    # Проверка лимита (удалите этот блок, если есть)
    # was_limited = getattr(request, 'limited', False)
    # if was_limited:
    #     messages.warning(request, '❌ Слишком много сообщений. Подождите немного перед отправкой новых сообщений.')
    #     return redirect('private_chat', user_id=user_id)
    
    from users.models import User
    receiver = get_object_or_404(User, id=user_id)
    
    if request.user == receiver:
        messages.warning(request, 'Нельзя написать самому себе')
        return redirect('profile', user_id=user_id)
    
    # Переименовали messages_list (чтобы не конфликтовать с django.contrib.messages)
    messages_list = PrivateMessage.objects.filter(
        (models.Q(sender=request.user, receiver=receiver) |
         models.Q(sender=receiver, receiver=request.user))
    ).order_by('created_at')
    
    messages_list.filter(receiver=request.user, is_read=False).update(is_read=True)
    
    if request.method == 'POST':
        text = request.POST.get('text')
        if text:
            message = PrivateMessage.objects.create(
                sender=request.user,
                receiver=receiver,
                text=text
            )
            
            # ===== УВЕДОМЛЕНИЕ ПОЛУЧАТЕЛЮ О ЛИЧНОМ СООБЩЕНИИ =====
            if receiver.email:
                send_notification(
                    receiver.email,
                    f'Новое личное сообщение от {request.user.username}',
                    f'Здравствуйте, {receiver.username}!\n\n'
                    f'Пользователь {request.user.username} отправил вам личное сообщение:\n\n'
                    f'"{text[:200]}{"..." if len(text) > 200 else ""}"\n\n'
                    f'🔗 Перейти в чат: http://127.0.0.1:8000/chat/private/{user_id}/\n\n'
                    f'---\nС уважением, команда Travel Buddy'
                )
            
            messages.success(request, 'Сообщение отправлено!')
            return redirect('private_chat', user_id=user_id)
    
    return render(request, 'chat/private_chat.html', {
        'receiver': receiver,
        'messages': messages_list
    })


@login_required
def unread_count(request):
    """Возвращает количество непрочитанных личных сообщений"""
    count = PrivateMessage.objects.filter(receiver=request.user, is_read=False).count()
    return JsonResponse({'count': count})


@login_required
def mark_as_read(request, user_id):
    """Отмечает все сообщения от пользователя как прочитанные"""
    from users.models import User
    sender = get_object_or_404(User, id=user_id)
    PrivateMessage.objects.filter(sender=sender, receiver=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'ok'})


@login_required
def chat_list(request):
    """Список всех чатов пользователя"""
    from django.db.models import Max
    
    # Находим всех пользователей, с которыми были сообщения
    sent_users = PrivateMessage.objects.filter(sender=request.user).values_list('receiver_id', flat=True)
    received_users = PrivateMessage.objects.filter(receiver=request.user).values_list('sender_id', flat=True)
    chat_user_ids = set(list(sent_users) + list(received_users))
    
    chats = []
    from users.models import User
    for user_id in chat_user_ids:
        other_user = User.objects.get(id=user_id)
        
        # Получаем последнее сообщение
        last_message = PrivateMessage.objects.filter(
            (models.Q(sender=request.user, receiver=other_user) |
             models.Q(sender=other_user, receiver=request.user))
        ).order_by('-created_at').first()
        
        # Считаем непрочитанные сообщения от этого пользователя
        unread_count = PrivateMessage.objects.filter(
            sender=other_user, receiver=request.user, is_read=False
        ).count()
        
        chats.append({
            'user': other_user,
            'last_message': last_message.text[:50] if last_message else '',
            'last_message_time': last_message.created_at if last_message else None,
            'unread_count': unread_count,
        })
    
    # Сортируем по времени последнего сообщения
    chats.sort(key=lambda x: x.get('last_message_time') or '', reverse=True)
    
    return render(request, 'chat/chat_list.html', {'chats': chats})