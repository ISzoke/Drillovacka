"""
================================================================================
 Module: list_and_cleanup_skills.py
 Description: 
        Management command to list all skills and optionally delete broad/generic ones
 Author: GitHub Copilot
================================================================================
"""

from django.core.management.base import BaseCommand
from api.models import Skill, ExampleSkill, Task
from django.db import transaction

class Command(BaseCommand):
    help = 'Lists all skills and optionally deletes broad/generic operation skills'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-broad',
            action='store_true',
            help='Delete broad generic skills (Sčítání, Odčítání, Násobení, Dělení, Operace)',
        )

    def handle(self, *args, **kwargs):
        delete_mode = kwargs['delete_broad']
        
        # List all non-deleted skills
        skills = Skill.objects.filter(deleted=False).order_by('id')
        
        self.stdout.write(self.style.SUCCESS(f'\n=== All Skills ({skills.count()}) ===\n'))
        
        for skill in skills:
            parent_info = f" (parent: {skill.parent_skill.name})" if skill.parent_skill else ""
            skill_type_info = f" [type: {skill.skill_type}]" if skill.skill_type else ""
            grade_info = f" grades: {list(skill.grade_levels.values_list('grade', flat=True))}" if skill.grade_levels.exists() else ""
            self.stdout.write(f"ID {skill.id}: {skill.name}{parent_info}{skill_type_info}{grade_info}")
        
        # Define broad/generic skills to delete
        broad_skill_patterns = [
            'Sčítání',
            'Sčítanie', 
            'Odčítání',
            'Odčítanie',
            'Násobení',
            'Násobenie',
            'Dělení',
            'Delenie',
            'Operace',
            'Operácie',
        ]
        
        # Find matching skills
        broad_skills = skills.filter(name__in=broad_skill_patterns)
        
        if broad_skills.exists():
            self.stdout.write(self.style.WARNING(f'\n=== Broad Generic Skills Found ({broad_skills.count()}) ===\n'))
            for skill in broad_skills:
                example_count = ExampleSkill.objects.filter(skill=skill).count()
                task_count = Task.objects.filter(skills=skill).count()
                self.stdout.write(
                    f"ID {skill.id}: {skill.name} - "
                    f"{example_count} examples, {task_count} tasks"
                )
            
            if delete_mode:
                self.stdout.write(self.style.WARNING('\nDeleting broad skills...'))
                
                with transaction.atomic():
                    for skill in broad_skills:
                        # Mark as deleted
                        skill.deleted = True
                        skill.save()
                        
                        # Remove from examples
                        ExampleSkill.objects.filter(skill=skill).delete()
                        
                        # Remove from tasks
                        for task in Task.objects.filter(skills=skill):
                            task.skills.remove(skill)
                        
                        # Remove from related_skills
                        for related in skill.related_skills.all():
                            skill.related_skills.remove(related)
                        
                        self.stdout.write(f"  ✓ Deleted: {skill.name} (ID {skill.id})")
                
                self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully deleted {broad_skills.count()} broad skills'))
            else:
                self.stdout.write(
                    self.style.WARNING('\nTo delete these skills, run with --delete-broad flag')
                )
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ No broad generic skills found'))
