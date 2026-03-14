"""
================================================================================
 Module: migrate_examples_to_leaf_skills.py
 Description:
        Migrates examples from broad operation skills to specific leaf skills.
        For addition/subtraction, analyzes the operands and result to determine
        which leaf skill they should go to (e.g., "do 10", "do 20", etc).
        
        Only migrates examples with WHOLE NUMBERS - skips fractions (/) and decimals (.).
================================================================================
"""

import re
from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Example, ExampleSkill, Skill


def is_whole_numbers_only(example_text):
    """Check if example contains only whole numbers (no fractions or decimals)."""
    return '/' not in example_text and '.' not in example_text


def parse_operands(example_text):
    """Extract all numeric operands from example (addition/subtraction)."""
    operands = []
    for match in re.findall(r'\d+', example_text):
        operands.append(int(match))
    return operands[:2] if operands else [0, 0]


def has_no_carry(example_text):
    """Check if addition requires no carry (ones place: a+b < 10, tens place: a+b < 10)."""
    if not is_whole_numbers_only(example_text):
        return False
    
    match = re.match(r'(\d+)\+(\d+)', example_text.strip())
    if not match:
        return False
    a, b = int(match.group(1)), int(match.group(2))
    
    # For single digit: no carry needed
    if a < 10 and b < 10:
        return True
    
    # For two digits: check if ones and tens separately don't carry
    if a >= 10 and b >= 10:
        ones_a, ones_b = a % 10, b % 10
        tens_a, tens_b = a // 10, b // 10
        return (ones_a + ones_b < 10) and (tens_a + tens_b < 10)
    
    return False


def has_no_borrow(example_text):
    """Check if subtraction requires no borrow."""
    if not is_whole_numbers_only(example_text):
        return False
    
    match = re.match(r'(\d+)-(\d+)', example_text.strip())
    if not match:
        return False
    a, b = int(match.group(1)), int(match.group(2))
    
    # For single digit: no borrow needed if a >= b
    if a < 10 and b < 10:
        return a >= b
    
    # For two digits: check if ones don't borrow
    if a >= 10 and b >= 10:
        ones_a, ones_b = a % 10, b % 10
        tens_a, tens_b = a // 10, b // 10
        return (ones_a >= ones_b) and (tens_a >= tens_b)
    
    return False


class Command(BaseCommand):
    help = "Migrate examples from broad to leaf skills based on content analysis (whole numbers only)."

    def get_migration_rules(self):
        """Get migration rules."""
        return {
            "Sčítání": [
                (lambda ex: is_whole_numbers_only(ex) and sum(parse_operands(ex)) <= 10, "Sčítanie do 10"),
                (lambda ex: is_whole_numbers_only(ex) and sum(parse_operands(ex)) <= 20 and has_no_carry(ex), "Sčítanie do 20 bez prechodu cez desiatku"),
            ],
            "Odčítání": [
                (lambda ex: is_whole_numbers_only(ex) and max(parse_operands(ex)) <= 10, "Odčítanie do 10"),
                (lambda ex: is_whole_numbers_only(ex) and max(parse_operands(ex)) <= 20 and has_no_borrow(ex), "Odčítanie do 20 bez prechodu cez desiatku"),
            ],
        }

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag, dry-run only.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]

        migration_log = {}

        for broad_skill_name, rules in self.get_migration_rules().items():
            broad_skill = Skill.objects.filter(name=broad_skill_name, deleted=False).first()
            if not broad_skill:
                self.stdout.write(self.style.WARNING(f"Broad skill '{broad_skill_name}' not found, skipping."))
                continue

            # Get all examples linked to this broad skill
            example_skills = ExampleSkill.objects.filter(skill=broad_skill)
            total_count = example_skills.count()
            self.stdout.write(f"\nProcessing '{broad_skill_name}' ({total_count} examples)...")

            for leaf_skill_name in set([name for _, name in rules]):
                leaf_skill = Skill.objects.filter(name=leaf_skill_name, deleted=False).first()
                if leaf_skill:
                    migration_log[leaf_skill_name] = {"from": broad_skill_name, "count": 0}
                else:
                    self.stdout.write(self.style.WARNING(f"  ! Leaf skill '{leaf_skill_name}' not found"))

            # Classify examples
            classified = {rule[1]: [] for _, rule in enumerate(rules)}
            unclassified = []

            for es in example_skills.values('example__id', 'example__example'):
                ex_text = es['example__example'].strip()
                matched = False

                for condition, leaf_name in rules:
                    try:
                        if condition(ex_text):
                            classified[leaf_name].append(es['example__id'])
                            matched = True
                            break
                    except Exception as e:
                        pass  # Silent skip on error

                if not matched:
                    unclassified.append((es['example__id'], ex_text))

            # Report counts
            for leaf_name, ex_ids in classified.items():
                count = len(ex_ids)
                if leaf_name in migration_log:
                    migration_log[leaf_name]["count"] = count
                self.stdout.write(f"  → {leaf_name}: {count} examples")

            if unclassified:
                self.stdout.write(f"  ⚠ Unclassified: {len(unclassified)} examples")
                for ex_id, ex_text in unclassified[:5]:
                    self.stdout.write(f"    - {ex_id}: {ex_text[:50]}")

            if not apply_changes:
                continue

            # Migrate
            with transaction.atomic():
                for leaf_name, ex_ids in classified.items():
                    if not ex_ids:
                        continue
                    leaf_skill = Skill.objects.get(name=leaf_name, deleted=False)
                    for ex_id in ex_ids:
                        ExampleSkill.objects.filter(example__id=ex_id, skill=broad_skill).update(skill=leaf_skill)

        if not apply_changes:
            self.stdout.write("\n" + "=" * 70)
            self.stdout.write("Dry-run only. Re-run with --apply to migrate examples.")
        else:
            self.stdout.write("\n" + "=" * 70)
            self.stdout.write(self.style.SUCCESS("✓ Examples migrated successfully."))
