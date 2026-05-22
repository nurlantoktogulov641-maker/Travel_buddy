import logging
import functools
from django.utils.timezone import now
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger('travel_buddy')


def log_action(message):
    """Декоратор для логирования действий пользователя"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated:
                log_msg = f"[{now()}] Пользователь: {request.user.username} | IP: {request.META.get('REMOTE_ADDR')} | {message} | URL: {request.path}"
            else:
                log_msg = f"[{now()}] Пользователь: Аноним | IP: {request.META.get('REMOTE_ADDR')} | {message} | URL: {request.path}"
            logger.info(log_msg)
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def send_notification(email, subject, message):
    """Отправка email уведомления (простой текст) - для обратной совместимости"""
    if not email:
        print(f"Нет email для отправки уведомления: {subject}")
        return False
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        print(f"✓ Email отправлен на {email}: {subject}")
        return True
    except Exception as e:
        print(f"✗ Ошибка отправки email на {email}: {e}")
        return False


def send_html_notification(email, subject, template_name, context):
    """
    Отправка HTML email уведомления с использованием шаблона
    """
    if not email:
        print(f"Нет email для отправки уведомления: {subject}")
        return False
    
    try:
        # Рендерим HTML из шаблона
        html_message = render_to_string(template_name, context)
        # Создаём plain-text версию (для старых почтовых клиентов)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"✓ HTML email отправлен на {email}: {subject}")
        return True
    except Exception as e:
        print(f"✗ Ошибка отправки HTML email на {email}: {e}")
        return False


# ========== УВЕДОМЛЕНИЯ ДЛЯ ОТКЛИКОВ (HTML версии) ==========

def notify_new_response(route, response):
    """
    Уведомление автору маршрута о новом отклике (HTML)
    Вызывается, когда пользователь оставляет отклик на маршрут
    """
    subject = f"Новый отклик на маршрут «{route.title}»"
    
    context = {
        'route': route,
        'response': response,
    }
    
    return send_html_notification(
        route.author.email, 
        subject, 
        'emails/new_response.html', 
        context
    )


def notify_response_status_changed(route, response, old_status, new_status):
    """
    Уведомление пользователя об изменении статуса его отклика (HTML)
    Вызывается, когда автор маршрута принимает или отклоняет отклик
    """
    # Словарь для заголовков писем в зависимости от статуса
    subject_map = {
        'ACCEPTED': f"✅ Ваш отклик принят! Маршрут «{route.title}»",
        'REJECTED': f"❌ Статус отклика на маршрут «{route.title}» изменён",
    }
    subject = subject_map.get(new_status, f"Статус отклика изменён: {new_status}")
    
    context = {
        'route': route,
        'response': response,
        'old_status': old_status,
        'new_status': new_status,
    }
    
    return send_html_notification(
        response.user.email, 
        subject, 
        'emails/response_status_changed.html', 
        context
    )


# ========== УВЕДОМЛЕНИЯ ДЛЯ ЧАТА (HTML версии) ==========

def notify_new_message_in_chat(route, message_obj, recipient):
    """
    Уведомление участнику маршрута о новом сообщении в чате (HTML)
    """
    subject = f"Новое сообщение в чате маршрута «{route.title}»"
    
    context = {
        'route': route,
        'message': message_obj,
        'recipient': recipient,
    }
    
    return send_html_notification(
        recipient.email, 
        subject, 
        'emails/new_chat_message.html', 
        context
    )


def notify_route_participants(route, message_obj, exclude_user):
    """
    Отправить уведомление всем участникам маршрута (кроме отправителя)
    Участники: автор маршрута + пользователи с принятым откликом
    """
    from responses.models import Response
    
    # Собираем получателей
    recipients_emails = []
    recipients_users = []
    
    # Автор маршрута
    if route.author != exclude_user and route.author.email:
        recipients_emails.append(route.author.email)
        recipients_users.append(route.author)
    
    # Участники с принятым откликом
    accepted_responses = Response.objects.filter(route=route, status='ACCEPTED')
    for resp in accepted_responses:
        if resp.user != exclude_user and resp.user.email:
            recipients_emails.append(resp.user.email)
            recipients_users.append(resp.user)
    
    # Убираем дубликаты
    unique_recipients = []
    seen_emails = set()
    for user in recipients_users:
        if user.email not in seen_emails:
            seen_emails.add(user.email)
            unique_recipients.append(user)
    
    # Отправляем уведомления
    for recipient in unique_recipients:
        notify_new_message_in_chat(route, message_obj, recipient)
    
    logger.info(f"Уведомления о сообщении отправлены {len(unique_recipients)} участникам маршрута {route.id}")
    return len(unique_recipients)


# ========== УВЕДОМЛЕНИЯ ДЛЯ ЛИЧНОГО ЧАТА (HTML версии) ==========

def notify_private_message(sender, receiver, message_text):
    """
    Уведомление получателю о новом личном сообщении (HTML)
    """
    subject = f"Новое личное сообщение от {sender.username}"
    
    context = {
        'sender': sender,
        'receiver': receiver,
        'message_text': message_text,
    }
    
    return send_html_notification(
        receiver.email, 
        subject, 
        'emails/private_message.html', 
        context
    )


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def send_test_email(email):
    """Отправка тестового письма для проверки настроек"""
    subject = "Тестовое письмо от Travel Buddy"
    context = {
        'email': email,
    }
    return send_html_notification(email, subject, 'emails/test_email.html', context)