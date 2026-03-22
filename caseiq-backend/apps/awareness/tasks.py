from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def fetch_legal_news_task(self):
    try:
        from services.news_service import news_service
        saved = news_service.fetch_and_save(count=15)
        logger.info(f'Celery news task completed: saved {saved} articles')
        return {'saved': saved, 'status': 'success'}
    except Exception as e:
        logger.error(f'News task failed: {e}')
        try:
            raise self.retry(countdown=60 * 5)
        except Exception:
            return {'saved': 0, 'status': 'failed', 'error': str(e)}


@shared_task
def cleanup_old_audit_logs():
    try:
        from django.utils import timezone
        from datetime import timedelta
        from apps.audit.models import AuditLog
        cutoff = timezone.now() - timedelta(days=90)
        deleted, _ = AuditLog.objects.filter(created_at__lt=cutoff).delete()
        logger.info(f'Deleted {deleted} old audit logs')
        return deleted
    except Exception as e:
        logger.error(f'Audit cleanup failed: {e}')
        return 0


@shared_task
def flag_suspicious_activity():
    try:
        from django.utils import timezone
        from datetime import timedelta
        from django.contrib.auth import get_user_model
        from apps.legal_query.models import LegalQuery
        from apps.audit.models import AuditLog

        User = get_user_model()
        one_hour_ago = timezone.now() - timedelta(hours=1)
        threshold = 30

        users = User.objects.filter(is_active=True)
        flagged = 0

        for user in users:
            count = LegalQuery.objects.filter(
                user=user,
                created_at__gte=one_hour_ago
            ).count()

            if count > threshold:
                AuditLog.objects.create(
                    user=user,
                    action='suspicious_activity',
                    details={
                        'query_count': count,
                        'threshold': threshold,
                        'window': '1 hour',
                    }
                )
                flagged += 1

        logger.info(f'Suspicious activity check: {flagged} users flagged')
        return flagged
    except Exception as e:
        logger.error(f'Suspicious activity check failed: {e}')
        return 0