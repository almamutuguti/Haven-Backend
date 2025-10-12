import json
import logging
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from medical.services import MedicalProfileService, EmergencyDataService
from medical.serializers import MedicalProfileSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = 'Export medical data for a user (GDPR compliance)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Export data for specific user by ID'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Export data for specific user by email'
        )
        parser.add_argument(
            '--output-format',
            choices=['json', 'fhir'],
            default='json',
            help='Output format for the data'
        )

    def handle(self, *args, **options):
        user = self.get_user(options)
        if not user:
            self.stdout.write(
                self.style.ERROR('User not found. Please provide --user-id or --email')
            )
            return

        try:
            if options['output_format'] == 'fhir':
                data = EmergencyDataService.generate_fhir_compliant_data(user)
                output_file = f"medical_data_fhir_{user.id}.json"
            else:
                data = MedicalProfileService.get_medical_profile(user)
                if data:
                    
                    serializer = MedicalProfileSerializer(data)
                    data = serializer.data
                output_file = f"medical_data_{user.id}.json"

            if not data:
                self.stdout.write(
                    self.style.ERROR(f'No medical data found for user {user.email}')
                )
                return

            # Save to file
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            self.stdout.write(
                self.style.SUCCESS(f'Medical data exported to {output_file}')
            )

        except Exception as e:
            logger.error(f"Medical data export failed: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f'Export failed: {str(e)}')
            )

    def get_user(self, options):
        if options['user_id']:
            return User.objects.filter(id=options['user_id']).first()
        elif options['email']:
            return User.objects.filter(email=options['email']).first()
        return None