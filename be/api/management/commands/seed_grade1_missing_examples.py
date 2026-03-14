"""
================================================================================
 Module: seed_grade1_missing_examples.py
 Description:
        Creates examples for Grade 1 skills that currently have 0 examples:
        1. Doplňovanie čísla (7 + ? = 10) - missing addend problems
        2. Porovnávanie čísel < > = - comparison problems
================================================================================
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Task, Example, Answer, ExampleSkill, Skill


class Command(BaseCommand):
    help = "Create examples for Grade 1 missing skills."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag, dry-run only.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]

        # Find the skills
        skill_doplnovanie = Skill.objects.filter(
            name="Doplňovanie čísla (7 + ? = 10)", 
            deleted=False
        ).first()
        
        skill_porovnavanie = Skill.objects.filter(
            name="Porovnávanie čísel < > =", 
            deleted=False
        ).first()

        if not skill_doplnovanie or not skill_porovnavanie:
            self.stdout.write(self.style.ERROR("Skills not found!"))
            return

        self.stdout.write("=== Grade 1 missing examples - Preview ===\n")

        # === 1. DOPLŇOVANIE ČÍSLA ===
        doplnovanie_examples = []
        
        # Doplňovanie do 10: x + ? = 10
        for x in range(1, 10):
            missing = 10 - x
            example_text = f"{x} + ? = 10"
            doplnovanie_examples.append({
                "example": example_text,
                "answer": str(missing),
                "input_type": "INLINE"
            })

        # Doplňovanie do 20 (jednoduchšie): x + ? = 20 kde x > 10
        for x in [11, 12, 13, 14, 15, 16, 17, 18, 19]:
            missing = 20 - x
            example_text = f"{x} + ? = 20"
            doplnovanie_examples.append({
                "example": example_text,
                "answer": str(missing),
                "input_type": "INLINE"
            })
        
        # Doplňovanie do 5, 6, 7, 8, 9 (pre malé deti)
        for target in [5, 6, 7, 8, 9]:
            for x in range(1, target):
                missing = target - x
                example_text = f"{x} + ? = {target}"
                doplnovanie_examples.append({
                    "example": example_text,
                    "answer": str(missing),
                    "input_type": "INLINE"
                })

        self.stdout.write(f"1. Doplňovanie čísla: {len(doplnovanie_examples)} examples")
        for ex in doplnovanie_examples[:5]:
            self.stdout.write(f"   {ex['example']} → {ex['answer']}")

        # === 2. POROVNÁVANIE ČÍSEL ===
        porovnavanie_examples = []
        
        # Porovnávanie čísel do 10
        numbers = list(range(0, 11))
        for i, a in enumerate(numbers):
            for b in numbers[i+1:]:
                # a < b
                porovnavanie_examples.append({
                    "example": f"{a} ☐ {b}",
                    "answer": "<",
                    "input_type": "INLINE"
                })
                # b > a
                porovnavanie_examples.append({
                    "example": f"{b} ☐ {a}",
                    "answer": ">",
                    "input_type": "INLINE"
                })
        
        # Rovnosť
        for a in range(0, 11):
            porovnavanie_examples.append({
                "example": f"{a} ☐ {a}",
                "answer": "=",
                "input_type": "INLINE"
            })
        
        # Porovnávanie čísel 11-20 (menej príkladov)
        for a in [11, 12, 15, 18, 20]:
            for b in [11, 12, 15, 18, 20]:
                if a < b:
                    porovnavanie_examples.append({
                        "example": f"{a} ☐ {b}",
                        "answer": "<",
                        "input_type": "INLINE"
                    })
                elif a > b:
                    porovnavanie_examples.append({
                        "example": f"{a} ☐ {b}",
                        "answer": ">",
                        "input_type": "INLINE"
                    })

        self.stdout.write(f"\n2. Porovnávanie čísel: {len(porovnavanie_examples)} examples")
        for ex in porovnavanie_examples[:5]:
            self.stdout.write(f"   {ex['example']} → {ex['answer']}")

        if not apply_changes:
            self.stdout.write("\nDry-run only. Re-run with --apply to create examples.")
            return

        # === CREATE TASKS AND EXAMPLES ===
        with transaction.atomic():
            # Task 1: Doplňovanie
            task_doplnovanie, _ = Task.objects.get_or_create(
                name="Doplňovanie čísla do 10 a 20",
                defaults={"form": "classic"}
            )
            task_doplnovanie.skills.add(skill_doplnovanie)

            for ex_data in doplnovanie_examples:
                example_instance = Example.objects.create(
                    example=ex_data["example"],
                    input_type=ex_data["input_type"],
                    task=task_doplnovanie
                )
                Answer.objects.create(
                    example=example_instance,
                    answer=ex_data["answer"]
                )
                ExampleSkill.objects.create(
                    example=example_instance,
                    skill=skill_doplnovanie
                )

            # Task 2: Porovnávanie
            task_porovnavanie, _ = Task.objects.get_or_create(
                name="Porovnávanie čísel do 20",
                defaults={"form": "classic"}
            )
            task_porovnavanie.skills.add(skill_porovnavanie)

            for ex_data in porovnavanie_examples:
                example_instance = Example.objects.create(
                    example=ex_data["example"],
                    input_type=ex_data["input_type"],
                    task=task_porovnavanie
                )
                Answer.objects.create(
                    example=example_instance,
                    answer=ex_data["answer"]
                )
                ExampleSkill.objects.create(
                    example=example_instance,
                    skill=skill_porovnavanie
                )

        self.stdout.write(self.style.SUCCESS("\n✓ Grade 1 examples created successfully!"))
