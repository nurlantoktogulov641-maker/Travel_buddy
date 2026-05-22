from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.utils.timezone import now
from datetime import timedelta


class SimpleRateLimitMiddleware:
    """Простой rate limiting без дополнительных пакетов"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Только для POST запросов к определённым URL
        if request.method == 'POST':
            ip = request.META.get('REMOTE_ADDR')
            
            # Лимиты для разных URL
            limits = {
                '/login/': {'rate': 5, 'window': 60},  # 5 попыток в минуту
                '/users/register/': {'rate': 3, 'window': 3600},  # 3 в час
                '/responses/create/': {'rate': 10, 'window': 3600},  # 10 в час
                '/reviews/create/': {'rate': 10, 'window': 3600},  # 10 в час
            }
            
            for path, limit in limits.items():
                if request.path.startswith(path):
                    key = f'ratelimit_{path}_{ip}'
                    count = cache.get(key, 0)
                    
                    if count >= limit['rate']:
                        from django.contrib import messages
                        messages.warning(request, '❌ Слишком много запросов. Подождите.')
                        return HttpResponseForbidden('Too many requests')
                    
                    cache.set(key, count + 1, limit['window'])
                    break
        
        return self.get_response(request)