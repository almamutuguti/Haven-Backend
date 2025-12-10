from rest_framework import views, status, permissions
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Count, Q
from django.core.mail import send_mail
from django.conf import settings

from .models import Verification
from .serializers import (
    VerificationSerializer, 
    VerificationActionSerializer,
    VerificationStatsSerializer
)
from accounts.permissions import IsSystemAdmin
from accounts.utils import send_verification_email, send_otp_email

class PendingVerificationsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def get(self, request):
        verifications = Verification.objects.filter(status='pending').order_by('-created_at')
        serializer = VerificationSerializer(verifications, many=True)
        return Response(serializer.data)

class VerificationHistoryView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def get(self, request):
        verifications = Verification.objects.exclude(status='pending').order_by('-reviewed_at')
        serializer = VerificationSerializer(verifications, many=True)
        return Response(serializer.data)

class ApproveVerificationView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def post(self, request, verification_id):
        try:
            verification = Verification.objects.get(id=verification_id, status='pending')
        except Verification.DoesNotExist:
            return Response(
                {"detail": "Verification not found or already processed"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = VerificationActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Update verification status
        verification.status = 'approved'
        verification.reviewed_by = request.user
        verification.reviewed_at = timezone.now()
        verification.review_notes = serializer.validated_data.get('reason', '')
        verification.save()
        
        # Update the actual entity based on verification type
        if verification.verification_type == 'user' and verification.user:
            user = verification.user
            user.is_email_verified = True
            user.save()
            
        elif verification.verification_type == 'hospital' and verification.hospital:
            hospital = verification.hospital
            hospital.is_operational = True
            hospital.save()
            
        elif verification.verification_type == 'organization' and verification.organization:
            organization = verification.organization
            organization.is_verified = True
            organization.save()
        
        return Response({
            "message": "Verification approved successfully",
            "verification": VerificationSerializer(verification).data
        })

class RejectVerificationView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def post(self, request, verification_id):
        try:
            verification = Verification.objects.get(id=verification_id, status='pending')
        except Verification.DoesNotExist:
            return Response(
                {"detail": "Verification not found or already processed"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = VerificationActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        reason = serializer.validated_data.get('reason')
        if not reason:
            return Response(
                {"detail": "Reason is required for rejection"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update verification status
        verification.status = 'rejected'
        verification.reviewed_by = request.user
        verification.reviewed_at = timezone.now()
        verification.review_notes = reason
        verification.save()
        
        return Response({
            "message": "Verification rejected",
            "verification": VerificationSerializer(verification).data
        })

class RequestInfoVerificationView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def post(self, request, verification_id):
        try:
            verification = Verification.objects.get(id=verification_id, status='pending')
        except Verification.DoesNotExist:
            return Response(
                {"detail": "Verification not found or already processed"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = VerificationActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        info_request = serializer.validated_data.get('request')
        if not info_request:
            return Response(
                {"detail": "Information request details are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update verification status
        verification.status = 'info_requested'
        verification.reviewed_by = request.user
        verification.reviewed_at = timezone.now()
        verification.review_notes = f"More information requested: {info_request}"
        verification.save()
        
        return Response({
            "message": "Information request sent successfully",
            "verification": VerificationSerializer(verification).data
        })

class VerificationStatsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def get(self, request):
        stats = Verification.objects.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            approved=Count('id', filter=Q(status='approved')),
            rejected=Count('id', filter=Q(status='rejected'))
        )
        
        serializer = VerificationStatsSerializer(stats)
        return Response(serializer.data)

class SendVerificationNotificationView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def post(self, request):
        verification_id = request.data.get('verification_id')
        notification_status = request.data.get('status')
        reason = request.data.get('reason')
        
        try:
            verification = Verification.objects.get(id=verification_id)
        except Verification.DoesNotExist:
            return Response(
                {"detail": "Verification not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        email = verification.get_entity_email()
        if not email:
            return Response(
                {"detail": "No email address found for this verification"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Send notification email
        subject = f"Verification {notification_status.title()} - Haven"
        
        if notification_status == 'approved':
            message = f"""Hello,
            
Your verification has been approved. You can now access all features of Haven.

Best regards,
Haven Support Team"""
        
        elif notification_status == 'rejected':
            message = f"""Hello,
            
Your verification has been rejected. Reason: {reason}

Please review your submission and try again, or contact support if you have questions.

Best regards,
Haven Support Team"""
        
        else:
            return Response(
                {"detail": "Invalid notification status"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            return Response({"message": "Notification sent successfully"})
        except Exception as e:
            return Response(
                {"detail": f"Failed to send notification: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ManualEmailVerificationView(views.APIView):
    """Manual email verification fallback for system admins"""
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response(
                {"detail": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from accounts.models import CustomUser
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response(
                {"detail": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if user.is_email_verified:
            return Response(
                {"detail": "Email is already verified"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create verification record
        verification = Verification.objects.create(
            user=user,
            verification_type='email',
            status='pending',
            submitted_data={
                'email': user.email,
                'username': user.username,
                'requested_by': request.user.username
            }
        )
        
        # Manually verify the email
        user.is_email_verified = True
        user.email_verification_token = None
        user.email_verification_sent_at = None
        user.save()
        
        # Update verification as approved
        verification.status = 'approved'
        verification.reviewed_by = request.user
        verification.reviewed_at = timezone.now()
        verification.review_notes = 'Manually verified by system admin'
        verification.save()
        
        # Send notification
        send_mail(
            "Email Manually Verified - Haven",
            f"""Hello {user.first_name or user.username},
            
Your email has been manually verified by a system administrator. You can now access all features of Haven.

Best regards,
Haven Support Team""",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        return Response({
            "message": "Email manually verified successfully",
            "user": {
                "email": user.email,
                "username": user.username,
                "is_email_verified": user.is_email_verified
            }
        })