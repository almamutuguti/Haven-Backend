import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from medical.models import MedicalProfile

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = 'Anonymize medical data for GDPR compliance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Anonymize data for specific user by ID'
        )
        parser.add_argument(
            '--inactive-users',
            action='store_true',
            help='Anonymize data for users inactive for more than 2 years'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be anonymized without making changes'
        )

    def handle(self, *args, **options):
        if options['user_id']:
            users = User.objects.filter(id=options['user_id'])
        elif options['inactive_users']:
            cutoff_date = timezone.now() - timezone.timedelta(days=730)  # 2 years
            users = User.objects.filter(last_login__lt=cutoff_date, is_active=False)
        else:
            self.stdout.write(
                self.style.ERROR('Please specify --user-id or --inactive-users')
            )
            return

        anonymized_count = 0
        
        for user in users:
            try:
                if self.anonymize_user_medical_data(user, options['dry_run']):
                    anonymized_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Anonymized medical data for {user.email}')
                    )
            except Exception as e:
                logger.error(f"Failed to anonymize data for {user.email}: {str(e)}")
                self.stdout.write(
                    self.style.ERROR(f'Failed to anonymize {user.email}: {str(e)}')
                )

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would anonymize {anonymized_count} users')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully anonymized {anonymized_count} users')
            )

    def anonymize_user_medical_data(self, user, dry_run=False):
        """
        Anonymize user's medical data
        """
        try:
            medical_profile = MedicalProfile.objects.filter(user=user).first()
            if not medical_profile:
                return True  # No data to anonymize

            if dry_run:
                return True

            # Delete all related medical data
            medical_profile.conditions.all().delete()
            medical_profile.allergies.all().delete()
            medical_profile.medications.all().delete()
            medical_profile.emergency_contacts.all().delete()
            medical_profile.insurance_info.all().delete()
            medical_profile.surgical_history.all().delete()
            medical_profile.documents.all().delete()

            # Anonymize the profile itself
            medical_profile.blood_type = 'unknown'
            medical_profile.height_cm = None
            medical_profile.weight_kg = None
            medical_profile.organ_donor = False
            medical_profile.dnr_order = False
            medical_profile.advance_directive = ''
            medical_profile.primary_care_physician = ''
            medical_profile.physician_phone = ''
            medical_profile.data_consent_given = False
            medical_profile.consent_given_at = None
            medical_profile.data_sharing_preferences = {}
            medical_profile.save()

            return True

        except Exception as e:
            logger.error(f"Anonymization failed for {user.email}: {str(e)}")
            return False