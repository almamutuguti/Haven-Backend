import random
import string
import threading
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction

from accounts.models import CustomUser

def generate_otp(length=6):
    """Generate a random OTP"""
    return ''.join(random.choices(string.digits, k=length))

def generate_email_token(length=50):
    """Generate a random email verification token"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def _send_email_sync(subject, message, recipient_email):
    """Internal function to send email with proper error handling"""
    try:
        # Add timeout to prevent hanging
        import socket
        socket.setdefaulttimeout(15)  # 15 seconds max timeout
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
            fail_silently=False,
        )
        print(f"Email sent successfully to {recipient_email}")
        return True
        
    except socket.timeout:
        print(f"Email timeout for {recipient_email} (SMTP connection too slow)")
        return False
    except Exception as e:
        print(f"Email sending failed for {recipient_email}: {str(e)}")
        return False

def send_verification_email(user_email):
    """
    Send email verification link - ASYNC VERSION
    
    IMPORTANT: Accept email instead of user object to avoid reference issues
    This version sends email in background thread to prevent server crashes
    """
    print(f"\n{'='*80}")
    print("SENDING VERIFICATION EMAIL (ASYNC)")
    print(f"User email: {user_email}")
    
    # Get user from database using email
    try:
        user = CustomUser.objects.get(email=user_email)
        print(f"Found user in DB: {user.email} (ID: {user.id})")
    except CustomUser.DoesNotExist:
        print(f"ERROR: User with email {user_email} not found in database!")
        raise ValueError(f"User with email {user_email} not found")
    
    # Generate token
    token = generate_email_token()
    print(f"Generated token: '{token}'")
    print(f"Token length: {len(token)}")
    
    # SAVE TOKEN TO DATABASE - Use atomic transaction
    try:
        with transaction.atomic():
            # Update the user in database
            user.email_verification_token = token
            user.email_verification_sent_at = timezone.now()
            user.save(update_fields=['email_verification_token', 'email_verification_sent_at'])
            
            print(f"Token saved to user object")
            
            # Force refresh from database
            user.refresh_from_db()
            print(f"After refresh - Token: '{user.email_verification_token}'")
            
            # Double-check by direct query
            db_check = CustomUser.objects.get(id=user.id)
            print(f"Direct query - Token: '{db_check.email_verification_token}'")
            print(f"Tokens match: {db_check.email_verification_token == token}")
            
    except Exception as e:
        print(f"Error saving token: {str(e)}")
        raise
    
    # Create verification URL
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
    verification_url = f"{frontend_url}/verify-email/{token}/"
    
    print(f"Verification URL: {verification_url}")
    
    # Email content
    subject = "Verify Your Email - Haven"
    message = f"""Hello {user.first_name or user.username},

Please verify your email address by clicking the link below:
{verification_url}

This link will expire in 24 hours.

If you didn't create an account, please ignore this email.

Best regards,
Haven Team"""
    
    # Send email in BACKGROUND THREAD to prevent server crashes
    def send_email_background():
        """Background thread function for email sending"""
        print(f"Starting background email thread for {user.email}")
        success = _send_email_sync(subject, message, user.email)
        if success:
            print(f"Background email completed for {user.email}")
        else:
            print(f"Background email failed for {user.email} (but request completed)")
    
    # Start background thread
    email_thread = threading.Thread(target=send_email_background)
    email_thread.daemon = True  # Thread won't block server shutdown
    email_thread.start()
    
    print(f"Email thread started for {user.email}. Main request returning immediately.")
    
    # Return immediately - email will send in background
    return {
        'token': token,
        'user_id': user.id,
        'email': user.email,
        'verification_url': verification_url,
        'message': 'Verification email is being sent in background'
    }

def send_verification_email_sync(user_email):
    """
    Original synchronous version - kept for backward compatibility
    Use only for testing, not in production on Render
    """
    print(f"\n{'='*80}")
    print("SENDING VERIFICATION EMAIL (SYNC - FOR TESTING ONLY)")
    
    try:
        user = CustomUser.objects.get(email=user_email)
        
        # Generate token
        token = generate_email_token()
        
        # Save to database
        with transaction.atomic():
            user.email_verification_token = token
            user.email_verification_sent_at = timezone.now()
            user.save(update_fields=['email_verification_token', 'email_verification_sent_at'])
        
        # Create verification URL
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        verification_url = f"{frontend_url}/verify-email/{token}/"
        
        # Email content
        subject = "Verify Your Email - Haven"
        message = f"""Hello {user.first_name or user.username},

Please verify your email address by clicking the link below:
{verification_url}

This link will expire in 24 hours.

If you didn't create an account, please ignore this email.

Best regards,
Haven Team"""
        
        # Send email (may hang/crash on Render)
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        print(f"Sync email sent to {user.email}")
        return {
            'token': token,
            'user_id': user.id,
            'email': user.email
        }
        
    except Exception as e:
        print(f"Sync email failed: {str(e)}")
        raise

def send_otp_email(user, is_password_reset=False):
    """Send OTP to user's email - ASYNC VERSION"""
    otp = generate_otp()
    
    # Use transaction to ensure OTP is saved
    with transaction.atomic():
        user.otp = otp
        user.otp_created_at = timezone.now()
        user.otp_verified = False
        user.otp_for_password_reset = is_password_reset
        user.save(update_fields=['otp', 'otp_created_at', 'otp_verified', 'otp_for_password_reset'])
    
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
    
    # Send email in background thread
    def send_otp_background():
        try:
            import socket
            socket.setdefaulttimeout(15)
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            print(f"OTP email sent to {user.email}")
        except Exception as e:
            print(f"OTP email sending failed: {str(e)}")
    
    otp_thread = threading.Thread(target=send_otp_background)
    otp_thread.daemon = True
    otp_thread.start()
    
    print(f"OTP thread started for {user.email}")
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