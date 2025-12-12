from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import CustomUser, Organization

class TrainingProgram(models.Model):
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    LEVEL_CHOICES = [
        ('basic', 'Basic'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='basic')
    
    # Schedule
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.PositiveIntegerField(default=1)
    
    # Capacity
    max_participants = models.PositiveIntegerField(default=20, validators=[MinValueValidator(1)])
    current_participants = models.PositiveIntegerField(default=0)
    
    # Location
    location = models.CharField(max_length=200, blank=True)
    address = models.TextField(blank=True)
    
    # Instructor Information
    instructor_name = models.CharField(max_length=100)
    instructor_qualifications = models.TextField(blank=True)
    
    # Organization (if applicable)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='training_programs'
    )
    
    # Hospital (if applicable)
    hospital = models.ForeignKey(
        'hospitals.Hospital',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='training_programs'
    )
    
    # Cost and Certification
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    provides_certification = models.BooleanField(default=True)
    certification_validity_months = models.PositiveIntegerField(default=12)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_trainings'
    )
    
    class Meta:
        ordering = ['start_date']
    
    def __str__(self):
        return self.title
    
    @property
    def available_slots(self):
        return self.max_participants - self.current_participants
    
    @property
    def is_full(self):
        return self.current_participants >= self.max_participants
    
    @property
    def duration_text(self):
        if self.duration_days == 1:
            return "1 day"
        return f"{self.duration_days} days"


class TrainingParticipant(models.Model):
    """Tracks participants in training programs"""
    training = models.ForeignKey(
        TrainingProgram,
        on_delete=models.CASCADE,
        related_name='participants_list'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='trainings_attended'
    )
    registration_date = models.DateTimeField(auto_now_add=True)
    attended = models.BooleanField(default=False)
    certificate_issued = models.BooleanField(default=False)
    certificate_issue_date = models.DateField(null=True, blank=True)
    certificate_number = models.CharField(max_length=50, blank=True)
    feedback = models.TextField(blank=True)
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    
    class Meta:
        unique_together = ['training', 'user']
        ordering = ['-registration_date']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.training.title}"