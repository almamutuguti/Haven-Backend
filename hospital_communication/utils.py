from datetime import datetime, timedelta
from django.utils import timezone
from .models import EmergencyHospitalCommunication

def calculate_estimated_arrival(hospital_lat, hospital_lng, patient_lat, patient_lng, traffic_conditions='normal'):
    """
    Calculate estimated arrival time based on distance and traffic conditions
    This is a simplified version - in production, integrate with Google Maps API
    """
    # Base travel time calculation (simplified)
    # In production, use actual distance matrix API
    base_travel_time_minutes = 15  # Default base time
    
    # Adjust for traffic conditions
    traffic_multipliers = {
        'light': 0.8,
        'normal': 1.0,
        'heavy': 1.5,
        'severe': 2.0
    }
    
    multiplier = traffic_multipliers.get(traffic_conditions, 1.0)
    estimated_minutes = base_travel_time_minutes * multiplier
    
    return int(estimated_minutes)

def format_emergency_message(communication):
    """
    Format emergency message for different communication channels
    """
    base_message = f"""
    EMERGENCY ALERT - {communication.alert_reference_id}
    Hospital: {communication.hospital.name}
    Patient: {communication.victim_name or 'Unknown'}, {communication.victim_age or 'N/A'}
    Priority: {communication.priority.upper()}
    Chief Complaint: {communication.chief_complaint}
    ETA: {communication.estimated_arrival_minutes} minutes
    First Aider: {communication.first_aider.get_full_name()}
    """.strip()
    
    return base_message

def check_communication_timeout():
    """
    Check for communications that haven't been acknowledged within timeout period
    """
    timeout_threshold = timezone.now() - timedelta(minutes=10)  # 10 minute timeout
    
    timed_out_comms = EmergencyHospitalCommunication.objects.filter(
        status='sent',
        sent_to_hospital_at__lt=timeout_threshold,
        hospital_acknowledged_at__isnull=True
    )
    
    for comm in timed_out_comms:
        # Mark as failed and trigger fallback
        comm.status = 'failed'
        comm.save()
        
        # Log the timeout
        from .models import CommunicationLog
        CommunicationLog.objects.create(
            communication=comm,
            channel='system',
            direction='outgoing',
            message_type='timeout',
            message_content="Communication timeout - no hospital response",
            is_successful=False,
            error_message="Hospital did not respond within timeout period"
        )

def get_communication_stats(hospital=None, first_aider=None, days=7):
    """
    Get communication statistics for dashboard
    """
    start_date = timezone.now() - timedelta(days=days)
    
    queryset = EmergencyHospitalCommunication.objects.filter(
        created_at__gte=start_date
    )
    
    if hospital:
        queryset = queryset.filter(hospital=hospital)
    if first_aider:
        queryset = queryset.filter(first_aider=first_aider)
    
    stats = {
        'total_communications': queryset.count(),
        'acknowledged': queryset.filter(status='acknowledged').count(),
        'ready': queryset.filter(status='ready').count(),
        'arrived': queryset.filter(status='arrived').count(),
        'failed': queryset.filter(status='failed').count(),
        'average_response_time': None,
    }
    
    # Calculate average response time for acknowledged communications
    acknowledged_comms = queryset.filter(
        status__in=['acknowledged', 'ready', 'arrived'],
        hospital_acknowledged_at__isnull=False,
        sent_to_hospital_at__isnull=False
    )
    
    if acknowledged_comms.exists():
        total_seconds = 0
        for comm in acknowledged_comms:
            response_time = comm.hospital_acknowledged_at - comm.sent_to_hospital_at
            total_seconds += response_time.total_seconds()
        
        avg_seconds = total_seconds / acknowledged_comms.count()
        stats['average_response_time'] = round(avg_seconds / 60, 1)  # Convert to minutes
    
    return stats