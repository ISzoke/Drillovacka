"""
================================================================================
 Module: assign_grade_levels.py
 Description: 
        Management command to assign grade levels to skills based on 
        Slovak/Czech elementary school curriculum (ZŠ 1-9)
 Author: GitHub Copilot
================================================================================
"""

from django.core.management.base import BaseCommand
from api.models import GradeLevel, Skill

class Command(BaseCommand):
    help = 'Assigns grade levels to skills according to Slovak/Czech curriculum'

    def handle(self, *args, **kwargs):
        """
        Grade level assignments based on typical Slovak/Czech ZŠ math curriculum:
        
        1. ročník (6-7 years): Numbers to 20, basic addition/subtraction
        2. ročník (7-8 years): Numbers to 100, multiplication/division basics
        3. ročník (8-9 years): Numbers to 1000, multiplication tables
        4. ročník (9-10 years): Numbers to 10,000, fractions introduction
        5. ročník (10-11 years): Numbers to 1,000,000, decimals, unit conversions
        6. ročník (11-12 years): Ratios, percentages, integers, basic equations
        7. ročník (12-13 years): Algebraic expressions, Pythagorean theorem
        8. ročník (13-14 years): Powers, roots, advanced equations
        9. ročník (14-15 years): Advanced algebra, complex equations
        """
        
        # Skill ID to grade levels mapping
        skill_grades = {
            # 1. ročník (6-7 rokov)
            88: [1],  # Do 10
            70: [1, 2],  # Do 20
            65: [1, 2, 3, 4, 5, 6, 7, 8, 9],  # Sčítání (všetky ročníky)
            66: [1, 2, 3, 4, 5, 6, 7, 8, 9],  # Odčítání (všetky ročníky)
            
            # 2. ročník (7-8 rokov)
            82: [2],  # Do 50
            71: [2, 3],  # Do 100
            67: [2, 3, 4, 5, 6, 7, 8, 9],  # Násobení (od 2. ročníka)
            68: [2, 3, 4, 5, 6, 7, 8, 9],  # Dělení (od 2. ročníka)
            
            # 3. ročník (8-9 rokov)
            80: [3],  # Přes 10
            81: [3],  # Přes 20
            
            # 4. ročník (9-10 rokov)
            95: [4, 5],  # Do 10 tisíc
            75: [4, 5, 6, 7, 8, 9],  # Zlomky (od 4. ročníka)
            89: [4, 5, 6],  # Krácení
            
            # 5. ročník (10-11 rokov)
            94: [5, 6],  # Do 1 milionu
            87: [5, 6, 7, 8, 9],  # Nad 100
            83: [5, 6],  # Desetiny
            72: [5, 6, 7, 8, 9],  # Desetinná čísla
            91: [5, 6, 7, 8, 9],  # Převody jednotek
            92: [5, 6, 7],  # Délkové
            93: [5, 6, 7],  # Plošné
            
            # 6. ročník (11-12 rokov)
            90: [6, 7, 8],  # Poměry
            69: [6, 7, 8, 9],  # Celá čísla
            79: [6, 7, 8, 9],  # Jednokrokové (rovnice)
            74: [6, 7, 8, 9],  # Rovnice
            
            # 7. ročník (12-13 rokov)
            73: [7, 8, 9],  # Algebra
            84: [7, 8, 9],  # Pythagorova věta
            
            # 8-9. ročník (13-15 rokov)
            85: [8, 9],  # Druhá mocnina
            86: [8, 9],  # Druhá odmocnina
            
            # Základné kategórie (všetky ročníky)
            54: [1, 2, 3, 4, 5, 6, 7, 8, 9],  # Matematika
            55: [1, 2, 3, 4, 5, 6, 7, 8, 9],  # Aritmetika
            56: [1, 2, 3, 4, 5, 6, 7, 8, 9],  # Operace
            61: [4, 5, 6, 7, 8, 9],  # Číselné obory
        }
        
        updated_count = 0
        not_found = []
        
        for skill_id, grades in skill_grades.items():
            try:
                skill = Skill.objects.get(id=skill_id, deleted=False)
                grade_levels = GradeLevel.objects.filter(grade__in=grades)
                
                # Clear existing and add new grade levels
                skill.grade_levels.clear()
                skill.grade_levels.add(*grade_levels)
                
                grade_list = ', '.join([f"{g}." for g in sorted(grades)])
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ {skill.name} (ID: {skill_id}) -> ročníky: {grade_list}'
                    )
                )
                updated_count += 1
                
            except Skill.DoesNotExist:
                not_found.append(skill_id)
                self.stdout.write(
                    self.style.WARNING(f'! Skill ID {skill_id} not found or deleted')
                )
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Successfully assigned grade levels to {updated_count} skills!'
            )
        )
        
        if not_found:
            self.stdout.write(
                self.style.WARNING(
                    f'\n⚠ Could not find {len(not_found)} skills: {not_found}'
                )
            )
