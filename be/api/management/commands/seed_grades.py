"""
================================================================================
 Module: seed_grades.py
 Description: 
        Management command to seed grade levels (1-9) into the database
 Author: Martin Eugen Minarčík (xminarm00)
================================================================================
"""

from django.core.management.base import BaseCommand
from api.models import GradeLevel 

class Command(BaseCommand):
    help = 'Seeds grade levels 1-9 into the database'

    def handle(self, *args, **kwargs):
        # Create grade levels 1-9
        for grade in range(1, 10):
            grade_level, created = GradeLevel.objects.get_or_create(grade=grade)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created grade level: {grade}'))
            else:
                self.stdout.write(f'Grade level {grade} already exists')
        
        self.stdout.write(self.style.SUCCESS('Grade levels seeded successfully!'))
