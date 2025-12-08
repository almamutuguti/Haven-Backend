import random
import string
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

def generate_otp(length=6):
    """Generate a random OTP"""
    return ''.join(random.choices(string.digits, k=length))

def generate_email_token(length=50):
    """Generate a random email verification token"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def send_verification_email(user):
    """Send email verification link"""
    token = generate_email_token()
    user.email_verification_token = token
    user.email_verification_sent_at = timezone.now()
    user.save()
    
    verification_url = f"{settings.FRONTEND_URL}/verify-email/{token}/"
    
    subject = "Verify Your Email - Haven"
    message = f"""
    Hello {user.first_name},
    
    Please verify your email address by clicking the link below:
    {verification_url}
    
    This link will expire in 24 hours.
    
    If you didn't create an account, please ignore this email.
    
    Best regards,
    Haven Team
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    
    return token

def send_otp_email(user, is_password_reset=False):
    """Send OTP to user's email"""
    otp = generate_otp()
    user.otp = otp
    user.otp_created_at = timezone.now()
    user.otp_verified = False
    user.otp_for_password_reset = is_password_reset
    user.save()
    
    action = "password reset" if is_password_reset else "login"
    
    subject = f"Your OTP for {action} - Haven"
    message = f"""
    Hello {user.first_name},
    
    Your OTP for {action} is: {otp}
    
    This OTP will expire in 10 minutes.
    
    If you didn't request this, please ignore this email.
    
    Best regards,
    Haven Team
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    
    return otp

def is_otp_valid(user, otp):
    """Check if OTP is valid and not expired"""
    if not user.otp or not user.otp_created_at:
        return False
    
    # OTP expires after 10 minutes
    expiry_time = user.otp_created_at + timedelta(minutes=10)
    
    if timezone.now() > expiry_time:
        return False
    
    return user.otp == otp

def is_email_token_valid(user, token):
    """Check if email verification token is valid"""
    if not user.email_verification_token or not user.email_verification_sent_at:
        return False
    
    # Token expires after 24 hours
    expiry_time = user.email_verification_sent_at + timedelta(hours=24)
    
    if timezone.now() > expiry_time:
        return False
    
    return user.email_verification_token == token