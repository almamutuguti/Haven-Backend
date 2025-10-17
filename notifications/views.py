from rest_framework import viewsets, status, generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import (
    Notification,
    NotificationTemplate,
    SMSLog,
    PushNotificationLog,
    EmailLog,
    UserNotificationPreference
)
from .serializers import (
    NotificationSerializer,
    NotificationCreateSerializer,
    NotificationTemplateSerializer,
    UserNotificationPreferenceSerializer,
    SMSLogSerializer,
    PushNotificationLogSerializer,
    EmailLogSerializer,
    BulkNotificationSerializer,
    NotificationStatsSerializer
)
from .services import NotificationOrchestrator, NotificationTemplateService
from accounts.permissions import IsSystemAdmin, IsHospitalStaff, IsFirstAider


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notifications
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # Users can only see their own notifications
        queryset = Notification.objects.filter(user=user)
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by type if provided
        type_filter = self.request.query_params.get('type')
        if type_filter:
            queryset = queryset.filter(notification_type=type_filter)
        
        # Filter by read status
        read_filter = self.request.query_params.get('read')
        if read_filter is not None:
            if read_filter.lower() == 'true':
                queryset = queryset.filter(read_at__isnull=False)
            else:
                queryset = queryset.filter(read_at__isnull=True)
        
        return queryset.select_related('user', 'emergency_alert', 'hospital_communication')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return NotificationCreateSerializer
        return NotificationSerializer
    
    def perform_create(self, serializer):
        notification = serializer.save()
        
        # Send notification immediately
        orchestrator = NotificationOrchestrator()
        orchestrator.send_notification(notification)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        
        return Response({
            'status': 'success',
            'message': 'Notification marked as read'
        })
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all user notifications as read"""
        user = request.user
        unread_notifications = Notification.objects.filter(
            user=user,
            read_at__isnull=True
        )
        
        count = unread_notifications.count()
        unread_notifications.update(
            status='read',
            read_at=timezone.now()
        )
        
        return Response({
            'status': 'success',
            'message': f'Marked {count} notifications as read'
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = Notification.objects.filter(
            user=request.user,
            read_at__isnull=True
        ).count()
        
        return Response({'unread_count': count})
    
    @action(detail=False, methods=['post'], permission_classes=[IsSystemAdmin])
    def send_bulk(self, request):
        """Send bulk notifications (admin only)"""
        serializer = BulkNotificationSerializer(data=request.data)
        
        if serializer.is_valid():
            notifications = []
            orchestrator = NotificationOrchestrator()
            
            for user in serializer.validated_data['users']:
                notification = Notification.objects.create(
                    user=user,
                    title=serializer.validated_data['title'],
                    message=serializer.validated_data['message'],
                    notification_type=serializer.validated_data['notification_type'],
                    channel=serializer.validated_data['channel'],
                    priority=serializer.validated_data['priority'],
                    metadata=serializer.validated_data.get('metadata', {})
                )
                notifications.append(notification)
            
            # Send all notifications
            results = orchestrator.send_bulk_notifications(notifications)
            
            return Response({
                'status': 'success',
                'message': f"Sent {results['success']} of {results['total']} notifications",
                'results': results
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get notification statistics for the current user"""
        user = request.user
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Basic stats
        total_sent = Notification.objects.filter(
            user=user,
            created_at__gte=thirty_days_ago
        ).count()
        
        total_delivered = Notification.objects.filter(
            user=user,
            status='delivered',
            created_at__gte=thirty_days_ago
        ).count()
        
        total_failed = Notification.objects.filter(
            user=user,
            status='failed',
            created_at__gte=thirty_days_ago
        ).count()
        
        # Channel breakdown
        channel_breakdown = Notification.objects.filter(
            user=user,
            created_at__gte=thirty_days_ago
        ).values('channel').annotate(count=Count('id'))
        
        # Type breakdown
        type_breakdown = Notification.objects.filter(
            user=user,
            created_at__gte=thirty_days_ago
        ).values('notification_type').annotate(count=Count('id'))
        
        # Calculate delivery rate
        delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
        
        stats_data = {
            'total_sent': total_sent,
            'total_delivered': total_delivered,
            'total_failed': total_failed,
            'delivery_rate': round(delivery_rate, 2),
            'average_delivery_time': 0,  # This would require more complex calculation
            'channel_breakdown': {item['channel']: item['count'] for item in channel_breakdown},
            'type_breakdown': {item['notification_type']: item['count'] for item in type_breakdown},
        }
        
        serializer = NotificationStatsSerializer(stats_data)
        return Response(serializer.data)


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notification templates (admin only)
    """
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    serializer_class = NotificationTemplateSerializer
    queryset = NotificationTemplate.objects.all()
    
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test a notification template"""
        template = self.get_object()
        test_user = request.user
        
        # Create test context
        context = {
            'user_name': test_user.get_full_name(),
            'alert_id': 'TEST-123',
            'hospital_name': 'Test Hospital',
            'eta': '15 minutes',
            'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Render template
        template_data = NotificationTemplateService.render_template(template.name, context)
        
        if not template_data:
            return Response({
                'status': 'error',
                'message': 'Failed to render template'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create and send test notification
        notification = Notification.objects.create(
            user=test_user,
            title=template_data['title'],
            message=template_data['message'],
            notification_type='test',
            priority=template_data['priority'],
            channel=template_data['channel'],
            metadata={'test_template': template.name}
        )
        
        # Send notification
        orchestrator = NotificationOrchestrator()
        success = orchestrator.send_notification(notification)
        
        return Response({
            'status': 'success' if success else 'error',
            'message': 'Test notification sent' if success else 'Failed to send test notification',
            'rendered_content': template_data
        })


class UserNotificationPreferenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user notification preferences
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserNotificationPreferenceSerializer
    
    def get_queryset(self):
        return UserNotificationPreference.objects.filter(user=self.request.user)
    
    def get_object(self):
        # Get or create preferences for the current user
        obj, created = UserNotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return obj
    
    def list(self, request, *args, **kwargs):
        # For list view, redirect to detail of current user's preferences
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def quick_toggle(self, request):
        """Quick toggle for emergency notifications"""
        preference = self.get_object()
        
        channel = request.data.get('channel')
        enabled = request.data.get('enabled', True)
        
        if channel == 'emergency':
            preference.emergency_push = enabled
            preference.emergency_sms = enabled
            preference.emergency_voice = enabled
        elif hasattr(preference, f"{channel}_enabled"):
            setattr(preference, f"{channel}_enabled", enabled)
        
        preference.save()
        
        return Response({
            'status': 'success',
            'message': f'{channel} notifications { "enabled" if enabled else "disabled" }'
        })


class SMSLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing SMS logs (admin only)
    """
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    serializer_class = SMSLogSerializer
    queryset = SMSLog.objects.all()
    
    def get_queryset(self):
        return super().get_queryset().select_related('notification', 'notification__user')


class PushNotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing push notification logs (admin only)
    """
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    serializer_class = PushNotificationLogSerializer
    queryset = PushNotificationLog.objects.all()
    
    def get_queryset(self):
        return super().get_queryset().select_related('notification', 'notification__user')


class EmailLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing email logs (admin only)
    """
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    serializer_class = EmailLogSerializer
    queryset = EmailLog.objects.all()
    
    def get_queryset(self):
        return super().get_queryset().select_related('notification', 'notification__user')


class AdminNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin view for all notifications (system admin only)
    """
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    serializer_class = NotificationSerializer
    queryset = Notification.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by user if provided
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by emergency alert if provided
        emergency_alert_id = self.request.query_params.get('emergency_alert_id')
        if emergency_alert_id:
            queryset = queryset.filter(emergency_alert_id=emergency_alert_id)
        
        return queryset.select_related('user', 'emergency_alert', 'hospital_communication')
    
    @action(detail=False, methods=['get'])
    def system_stats(self, request):
        """Get system-wide notification statistics"""
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Overall stats
        total_sent = Notification.objects.filter(
            created_at__gte=thirty_days_ago
        ).count()
        
        total_delivered = Notification.objects.filter(
            status='delivered',
            created_at__gte=thirty_days_ago
        ).count()
        
        # Channel performance
        channel_stats = Notification.objects.filter(
            created_at__gte=thirty_days_ago
        ).values('channel').annotate(
            total=Count('id'),
            delivered=Count('id', filter=Q(status='delivered')),
            failed=Count('id', filter=Q(status='failed'))
        )
        
        # Type distribution
        type_stats = Notification.objects.filter(
            created_at__gte=thirty_days_ago
        ).values('notification_type').annotate(count=Count('id'))
        
        # Recent failures
        recent_failures = Notification.objects.filter(
            status='failed',
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        stats_data = {
            'total_sent': total_sent,
            'total_delivered': total_delivered,
            'delivery_rate': round((total_delivered / total_sent * 100), 2) if total_sent > 0 else 0,
            'channel_performance': list(channel_stats),
            'type_distribution': list(type_stats),
            'recent_failures': recent_failures,
        }
        
        return Response(stats_data)


# Additional Class-Based Views for Custom Endpoints
class MarkAllNotificationsReadAPIView(APIView):
    """
    Mark all user notifications as read
    POST /api/notifications/notifications/mark-all-read/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        unread_notifications = Notification.objects.filter(
            user=user,
            read_at__isnull=True
        )
        
        count = unread_notifications.count()
        unread_notifications.update(
            status='read',
            read_at=timezone.now()
        )
        
        return Response({
            'status': 'success',
            'message': f'Marked {count} notifications as read'
        })


class UnreadNotificationsCountAPIView(APIView):
    """
    Get count of unread notifications
    GET /api/notifications/notifications/unread-count/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        count = Notification.objects.filter(
            user=request.user,
            read_at__isnull=True
        ).count()
        
        return Response({'unread_count': count})


class SendBulkNotificationsAPIView(APIView):
    """
    Send bulk notifications (admin only)
    POST /api/send-bulk/
    """
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def post(self, request):
        serializer = BulkNotificationSerializer(data=request.data)
        
        if serializer.is_valid():
            notifications = []
            orchestrator = NotificationOrchestrator()
            
            for user in serializer.validated_data['users']:
                notification = Notification.objects.create(
                    user=user,
                    title=serializer.validated_data['title'],
                    message=serializer.validated_data['message'],
                    notification_type=serializer.validated_data['notification_type'],
                    channel=serializer.validated_data['channel'],
                    priority=serializer.validated_data['priority'],
                    metadata=serializer.validated_data.get('metadata', {})
                )
                notifications.append(notification)
            
            # Send all notifications
            results = orchestrator.send_bulk_notifications(notifications)
            
            return Response({
                'status': 'success',
                'message': f"Sent {results['success']} of {results['total']} notifications",
                'results': results
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationStatsAPIView(APIView):
    """
    Get notification statistics for the current user
    GET /api/notifications/notifications/stats/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Basic stats
        total_sent = Notification.objects.filter(
            user=user,
            created_at__gte=thirty_days_ago
        ).count()
        
        total_delivered = Notification.objects.filter(
            user=user,
            status='delivered',
            created_at__gte=thirty_days_ago
        ).count()
        
        total_failed = Notification.objects.filter(
            user=user,
            status='failed',
            created_at__gte=thirty_days_ago
        ).count()
        
        # Channel breakdown
        channel_breakdown = Notification.objects.filter(
            user=user,
            created_at__gte=thirty_days_ago
        ).values('channel').annotate(count=Count('id'))
        
        # Type breakdown
        type_breakdown = Notification.objects.filter(
            user=user,
            created_at__gte=thirty_days_ago
        ).values('notification_type').annotate(count=Count('id'))
        
        # Calculate delivery rate
        delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
        
        stats_data = {
            'total_sent': total_sent,
            'total_delivered': total_delivered,
            'total_failed': total_failed,
            'delivery_rate': round(delivery_rate, 2),
            'average_delivery_time': 0,
            'channel_breakdown': {item['channel']: item['count'] for item in channel_breakdown},
            'type_breakdown': {item['notification_type']: item['count'] for item in type_breakdown},
        }
        
        serializer = NotificationStatsSerializer(stats_data)
        return Response(serializer.data)


class MarkNotificationReadAPIView(APIView):
    """
    Mark notification as read
    POST /api/notifications/notifications/{pk}/mark-read/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
            notification.mark_as_read()
            
            return Response({
                'status': 'success',
                'message': 'Notification marked as read'
            })
        except Notification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class NotificationPreferenceToggleAPIView(APIView):
    """
    Quick toggle for emergency notifications
    POST /api/preferences/quick-toggle/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        preference, created = UserNotificationPreference.objects.get_or_create(
            user=request.user
        )
        
        channel = request.data.get('channel')
        enabled = request.data.get('enabled', True)
        
        if channel == 'emergency':
            preference.emergency_push = enabled
            preference.emergency_sms = enabled
            preference.emergency_voice = enabled
        elif hasattr(preference, f"{channel}_enabled"):
            setattr(preference, f"{channel}_enabled", enabled)
        
        preference.save()
        
        return Response({
            'status': 'success',
            'message': f'{channel} notifications { "enabled" if enabled else "disabled" }'
        })


class TestNotificationTemplateAPIView(APIView):
    """
    Test a notification template
    POST /api/notifications/templates/{pk}/test/
    """
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def post(self, request, pk):
        try:
            template = NotificationTemplate.objects.get(pk=pk)
            test_user = request.user
            
            # Create test context
            context = {
                'user_name': test_user.get_full_name(),
                'alert_id': 'TEST-123',
                'hospital_name': 'Test Hospital',
                'eta': '15 minutes',
                'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Render template
            template_data = NotificationTemplateService.render_template(template.name, context)
            
            if not template_data:
                return Response({
                    'status': 'error',
                    'message': 'Failed to render template'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create and send test notification
            notification = Notification.objects.create(
                user=test_user,
                title=template_data['title'],
                message=template_data['message'],
                notification_type='test',
                priority=template_data['priority'],
                channel=template_data['channel'],
                metadata={'test_template': template.name}
            )
            
            # Send notification
            orchestrator = NotificationOrchestrator()
            success = orchestrator.send_notification(notification)
            
            return Response({
                'status': 'success' if success else 'error',
                'message': 'Test notification sent' if success else 'Failed to send test notification',
                'rendered_content': template_data
            })
        except NotificationTemplate.DoesNotExist:
            return Response(
                {'error': 'Template not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class AdminNotificationStatsAPIView(APIView):
    """
    Get system-wide notification statistics
    GET /api/notifications/admin-notifications/system-stats/
    """
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def get(self, request):
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Overall stats
        total_sent = Notification.objects.filter(
            created_at__gte=thirty_days_ago
        ).count()
        
        total_delivered = Notification.objects.filter(
            status='delivered',
            created_at__gte=thirty_days_ago
        ).count()
        
        # Channel performance
        channel_stats = Notification.objects.filter(
            created_at__gte=thirty_days_ago
        ).values('channel').annotate(
            total=Count('id'),
            delivered=Count('id', filter=Q(status='delivered')),
            failed=Count('id', filter=Q(status='failed'))
        )
        
        # Type distribution
        type_stats = Notification.objects.filter(
            created_at__gte=thirty_days_ago
        ).values('notification_type').annotate(count=Count('id'))
        
        # Recent failures
        recent_failures = Notification.objects.filter(
            status='failed',
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        stats_data = {
            'total_sent': total_sent,
            'total_delivered': total_delivered,
            'delivery_rate': round((total_delivered / total_sent * 100), 2) if total_sent > 0 else 0,
            'channel_performance': list(channel_stats),
            'type_distribution': list(type_stats),
            'recent_failures': recent_failures,
        }
        
        return Response(stats_data)