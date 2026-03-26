import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'be.settings')

import django
django.setup()

from api.models import Task, Skill, ExampleSkill

tasks = Task.objects.filter(
    grade_levels__isnull=False,
    is_private=False,
    primary_skill__isnull=True,
).distinct()

created = 0
for task in tasks:
    grades = task.grade_levels.all()
    if not grades.exists():
        continue
    skill = Skill.objects.create(name=task.name, skill_type='TASK')
    skill.grade_levels.set(grades)
    task.primary_skill = skill
    task.save(update_fields=['primary_skill'])
    for example in task.example_set.all():
        ExampleSkill.objects.get_or_create(example=example, skill=skill)
    created += 1
    print(f'  Migrated task [{task.id}] {task.name!r} -> skill {skill.id}')

print(f'Done: {created} tasks migrated')
