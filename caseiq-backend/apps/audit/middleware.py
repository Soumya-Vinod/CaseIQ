import time
import hashlib
import logging

logger = logging.getLogger(__name__)


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        processing_time = int((time.time() - start_time) * 1000)

        # Only log API requests
        if request.path.startswith('/api/'):
            try:
                from apps.audit.models import AuditLog
                user = request.user if request.user.is_authenticated else None
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

                AuditLog.objects.create(
                    user=user,
                    action=self._get_action(request.path),
                    endpoint=request.path,
                    method=request.method,
                    response_status=response.status_code,
                    ip_address=ip,
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                    processing_time_ms=processing_time,
                )
            except Exception as e:
                logger.warning(f"Audit log failed: {e}")

        return response

    def _get_action(self, path):
        if 'auth' in path:
            if 'login' in path:
                return 'user_login'
            if 'logout' in path:
                return 'user_logout'
            if 'register' in path:
                return 'user_register'
        if 'legal' in path:
            return 'legal_query'
        if 'complaint' in path:
            return 'complaint_draft'
        if 'knowledge' in path:
            return 'knowledge_search'
        if 'awareness' in path:
            return 'news_fetch'
        return 'legal_query'