import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from api.models import Student, Example, StudentExample
from django.utils import timezone

class Command(BaseCommand):
    help = 'Seed fake student activity for analytics testing.'

    def add_arguments(self, parser):
        parser.add_argument('--student_id', type=int, required=True, help='ID študenta')
        parser.add_argument('--minutes', type=int, default=20, help='Dĺžka simulácie v minútach')
        parser.add_argument('--examples', type=int, default=12, help='Počet rôznych príkladov (default 12)')

    def handle(self, *args, **options):
        student_id = options['student_id']
        minutes = options['minutes']
        n_examples = options['examples']

        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'Student {student_id} neexistuje.'))
            return

        all_examples = list(Example.objects.all())
        if not all_examples:
            self.stderr.write(self.style.ERROR('V databáze nie sú žiadne príklady.'))
            return
        examples = random.sample(all_examples, min(n_examples, len(all_examples)))

        now = timezone.now()
        start_time = now - timedelta(minutes=minutes)
        total_attempts = 0
        for i, example in enumerate(examples):
            # Simuluj 1-3 pokusy na príklad, niekedy správne, niekedy nie
            n_attempts = random.randint(1, 3)
            solved = random.random() < 0.7  # 70% šanca, že vyrieši
            skipped = not solved and random.random() < 0.2  # 20% z nevyriešených preskočí
            duration = random.randint(10, 60) * n_attempts  # 10-60s na pokus
            when = start_time + timedelta(seconds=(i * minutes * 60) // len(examples))
            StudentExample.objects.create(
                student=student,
                example=example,
                date=when,
                duration=duration,
                attempts=n_attempts,
                solved=solved,
                skipped=skipped,
            )
            total_attempts += n_attempts
        self.stdout.write(self.style.SUCCESS(f'Vygenerovaných {len(examples)} príkladov, {total_attempts} pokusov pre študenta {student_id}.'))
