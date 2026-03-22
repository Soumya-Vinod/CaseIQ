import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(name='audit.cleanup_old_logs')
def cleanup_old_audit_logs():
    """Delete audit logs older than 90 days to keep DB clean."""
    try:
        from apps.audit.models import AuditLog
        cutoff = timezone.now() - timedelta(days=90)
        deleted_count, _ = AuditLog.objects.filter(
            created_at__lt=cutoff,
            is_flagged=False
        ).delete()
        logger.info(f"Cleaned up {deleted_count} old audit logs")
        return {'deleted': deleted_count}
    except Exception as e:
        logger.error(f"Audit cleanup failed: {e}")
        raise


@shared_task(name='audit.flag_suspicious_activity')
def flag_suspicious_activity():
    """Flag users with excessive queries in last hour."""
    try:
        from apps.audit.models import AuditLog
        from django.db.models import Count
        from datetime import timedelta

        one_hour_ago = timezone.now() - timedelta(hours=1)

        suspicious = AuditLog.objects.filter(
            created_at__gte=one_hour_ago,
            action='legal_query'
        ).values('ip_address').annotate(
            count=Count('id')
        ).filter(count__gt=30)

        flagged = 0
        for item in suspicious:
            AuditLog.objects.filter(
                ip_address=item['ip_address'],
                created_at__gte=one_hour_ago,
                is_flagged=False
            ).update(is_flagged=True, flag_reason='Excessive queries detected')
            flagged += 1

        logger.info(f"Flagged {flagged} suspicious IPs")
        return {'flagged': flagged}
    except Exception as e:
        logger.error(f"Suspicious activity check failed: {e}")
        raise