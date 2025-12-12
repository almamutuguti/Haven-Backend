import csv
from datetime import datetime, timedelta
from io import StringIO
from itertools import count
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

class ReportGenerator:
    """Service class for generating hospital reports"""
    
    @staticmethod
    def get_date_range_for_period(period, start_date=None, end_date=None):
        """Get date range based on period"""
        now = timezone.now()
        
        if period == 'daily':
            start = now - timedelta(days=1)
            return start.date(), now.date()
        elif period == 'weekly':
            start = now - timedelta(weeks=1)
            return start.date(), now.date()
        elif period == 'monthly':
            start = now - timedelta(days=30)
            return start.date(), now.date()
        elif period == 'quarterly':
            start = now - timedelta(days=90)
            return start.date(), now.date()
        elif period == 'yearly':
            start = now - timedelta(days=365)
            return start.date(), now.date()
        elif period == 'custom' and start_date and end_date:
            return start_date, end_date
        else:
            # Default to monthly
            start = now - timedelta(days=30)
            return start.date(), now.date()
    
    @staticmethod
    def calculate_statistics(hospital, start_date, end_date):
        """Calculate statistics for the given date range"""
        # Get communications in date range
        communications = EmergencyHospitalCommunication.objects.filter(
            hospital=hospital,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        total_communications = communications.count()
        
        if total_communications == 0:
            return {
                'total_communications': 0,
                'avg_response_time_minutes': 0,
                'acceptance_rate': 0,
                'success_rate': 0,
                'patient_arrivals': 0,
                'critical_cases': 0,
                'avg_preparation_time_minutes': 0,
                'avg_treatment_time_minutes': 0,
            }
        
        # Calculate response times
        accepted_comms = communications.filter(
            hospital_acknowledged_at__isnull=False
        )
        
        response_times = []
        for comm in accepted_comms:
            if comm.sent_to_hospital_at and comm.hospital_acknowledged_at:
                response_time = (comm.hospital_acknowledged_at - comm.sent_to_hospital_at).total_seconds() / 60
                response_times.append(response_time)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Calculate acceptance rate
        accepted_count = accepted_comms.count()
        acceptance_rate = (accepted_count / total_communications) * 100 if total_communications > 0 else 0
        
        # Calculate patient arrivals
        patient_arrivals = communications.filter(status='arrived').count()
        success_rate = (patient_arrivals / accepted_count) * 100 if accepted_count > 0 else 0
        
        # Count critical cases
        critical_cases = communications.filter(priority='critical').count()
        
        # Calculate preparation times
        prepared_comms = communications.filter(
            hospital_ready_at__isnull=False,
            hospital_acknowledged_at__isnull=False
        )
        
        preparation_times = []
        for comm in prepared_comms:
            prep_time = (comm.hospital_ready_at - comm.hospital_acknowledged_at).total_seconds() / 60
            preparation_times.append(prep_time)
        
        avg_preparation_time = sum(preparation_times) / len(preparation_times) if preparation_times else 0
        
        # Calculate treatment times
        treated_comms = communications.filter(
            patient_arrived_at__isnull=False,
            sent_to_hospital_at__isnull=False
        )
        
        treatment_times = []
        for comm in treated_comms:
            treatment_time = (comm.patient_arrived_at - comm.sent_to_hospital_at).total_seconds() / 60
            treatment_times.append(treatment_time)
        
        avg_treatment_time = sum(treatment_times) / len(treatment_times) if treatment_times else 0
        
        # Get breakdowns
        status_breakdown = communications.values('status').annotate(count=count('id')).order_by('-count')
        status_dict = {item['status']: item['count'] for item in status_breakdown}
        
        priority_breakdown = communications.values('priority').annotate(count=count('id')).order_by('-count')
        priority_dict = {item['priority']: item['count'] for item in priority_breakdown}
        
        # Hourly breakdown (for 24-hour analysis)
        hourly_breakdown = {}
        for hour in range(24):
            hour_comms = communications.filter(created_at__hour=hour).count()
            hourly_breakdown[f"{hour:02d}:00"] = hour_comms
        
        return {
            'total_communications': total_communications,
            'avg_response_time_minutes': round(avg_response_time, 1),
            'acceptance_rate': round(acceptance_rate, 1),
            'success_rate': round(success_rate, 1),
            'patient_arrivals': patient_arrivals,
            'critical_cases': critical_cases,
            'avg_preparation_time_minutes': round(avg_preparation_time, 1),
            'avg_treatment_time_minutes': round(avg_treatment_time, 1),
            'communications_by_status': status_dict,
            'communications_by_priority': priority_dict,
            'communications_by_time': hourly_breakdown,
        }
    
    @staticmethod
    def get_communications_summary(hospital, start_date, end_date, limit=20):
        """Get summary of communications for report"""
        communications = EmergencyHospitalCommunication.objects.filter(
            hospital=hospital,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).order_by('-created_at')[:limit]
        
        summary = []
        for comm in communications:
            summary.append({
                'id': str(comm.id),
                'alert_reference_id': comm.alert_reference_id,
                'victim_name': comm.victim_name,
                'priority': comm.priority,
                'status': comm.status,
                'chief_complaint': comm.chief_complaint[:100] if comm.chief_complaint else '',
                'created_at': comm.created_at.isoformat(),
                'hospital_acknowledged_at': comm.hospital_acknowledged_at.isoformat() if comm.hospital_acknowledged_at else None,
                'patient_arrived_at': comm.patient_arrived_at.isoformat() if comm.patient_arrived_at else None,
                'estimated_arrival_minutes': comm.estimated_arrival_minutes,
            })
        
        return summary
    
    @staticmethod
    def generate_recommendations(statistics):
        """Generate recommendations based on statistics"""
        recommendations = []
        
        if statistics.get('avg_response_time_minutes', 0) > 15:
            recommendations.append({
                'priority': 'high',
                'title': 'Improve Response Time',
                'description': f"Average response time of {statistics['avg_response_time_minutes']} minutes exceeds the recommended 15-minute threshold. Consider implementing automated alert systems and staff training.",
                'action': 'Review and optimize alert notification processes'
            })
        
        if statistics.get('acceptance_rate', 0) < 90:
            recommendations.append({
                'priority': 'medium',
                'title': 'Increase Acceptance Rate',
                'description': f"Current acceptance rate of {statistics['acceptance_rate']}% can be improved. Review staffing levels during peak hours.",
                'action': 'Analyze peak hours and adjust staffing accordingly'
            })
        
        if statistics.get('critical_cases', 0) > 0:
            recommendations.append({
                'priority': 'high',
                'title': 'Critical Case Management',
                'description': f"Handled {statistics['critical_cases']} critical cases. Ensure dedicated critical care teams are always available.",
                'action': 'Implement critical case review process'
            })
        
        if statistics.get('success_rate', 0) < 80:
            recommendations.append({
                'priority': 'medium',
                'title': 'Improve Success Rate',
                'description': f"Success rate of {statistics['success_rate']}% indicates room for improvement in patient treatment and arrival processes.",
                'action': 'Review treatment protocols and patient handoff procedures'
            })
        
        return recommendations
    
    @staticmethod
    def generate_csv_report(hospital, start_date, end_date, communications):
        """Generate CSV report data"""
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        headers = [
            'ID', 'Alert Reference', 'Patient Name', 'Age', 'Gender',
            'Priority', 'Status', 'Chief Complaint', 'Created At',
            'Response Time (min)', 'Arrival Time', 'ETA (min)',
            'First Aider', 'Hospital Acknowledged'
        ]
        writer.writerow(headers)
        
        # Write data
        for comm in communications:
            response_time = ''
            if comm.hospital_acknowledged_at and comm.sent_to_hospital_at:
                response_time = str(round((comm.hospital_acknowledged_at - comm.sent_to_hospital_at).total_seconds() / 60, 1))
            
            writer.writerow([
                str(comm.id),
                comm.alert_reference_id or 'N/A',
                comm.victim_name or 'Unknown',
                comm.victim_age or '',
                comm.victim_gender or '',
                comm.priority,
                comm.status,
                (comm.chief_complaint or '')[:100],
                comm.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                response_time,
                comm.patient_arrived_at.strftime('%Y-%m-%d %H:%M:%S') if comm.patient_arrived_at else '',
                comm.estimated_arrival_minutes or '',
                comm.first_aider.get_full_name() if comm.first_aider else '',
                'Yes' if comm.hospital_acknowledged_at else 'No'
            ])
        
        return output.getvalue()