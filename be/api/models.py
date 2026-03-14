"""
================================================================================
 Module: models.py
 Description: 
        Defines the data models used in the application. 
 Author: Dominik Horut (xhorut01)
================================================================================
"""

from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Q


class Task(models.Model):
    FORM_CHOICES = [
        ('classic', 'Classic'),
        ('word-problem', 'Word Problem'),
    ]

    name = models.CharField(max_length=255)

    skills = models.ManyToManyField(
        'Skill',  
        blank=True,  
        related_name='tasks' 
    )

    form = models.CharField(
        max_length=20, 
        choices=FORM_CHOICES, 
        default='classic', 
    )

class Example(models.Model):
    example = models.CharField(max_length=255)
    input_type = models.CharField(max_length=255)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)

class Step(models.Model):
    example = models.ForeignKey(Example, on_delete=models.CASCADE, related_name='steps')
    text = models.TextField()

    order = models.PositiveIntegerField(
        default=0,
    )

class Answer(models.Model):
    example = models.ForeignKey(Example, on_delete=models.CASCADE, related_name='answers')
    answer = models.CharField(max_length=255)

class GradeLevel(models.Model):
    """Represents a grade level in elementary school (ZŠ 1-9)"""
    grade = models.IntegerField(unique=True)
    
    class Meta:
        ordering = ['grade']
    
    def __str__(self):
        return f"{self.grade}. ročník"

class Skill(models.Model):
    name = models.CharField(max_length=255)
    height = models.IntegerField(default=0) 
    deleted = models.BooleanField(default=False)
    
    parent_skill = models.ForeignKey(
        'self',                  
        null=True,               
        blank=True,              
        on_delete=models.SET_NULL,
        related_name='subskills'
    )

    SKILL_TYPES = [
        ('OPERATION', 'Operation'),
        ('NUMBER_DOMAIN', 'Number Domain'),
    ]
    
    skill_type = models.CharField(
        max_length=50, 
        choices=SKILL_TYPES, 
        null=True,               
        blank=True   
    )

    related_skills = models.ManyToManyField(
        'self',  
        blank=True,  
        symmetrical=True,  
    )
    
    grade_levels = models.ManyToManyField(
        'GradeLevel',
        blank=True,
        related_name='skills'
    )
    
class ExampleSkill(models.Model):
    example = models.ForeignKey(Example, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)

class Student(models.Model):
    LANGUAGE_CHOICES = [
        ('cs', 'Czech'),
        ('sk', 'Slovak'),
        ('en', 'English'),
    ]
    
    username = models.CharField(max_length=255, unique=True)
    passphrase = models.CharField(max_length=255)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='sk')
    audio_threshold = models.IntegerField(default=50)

class AnonymousSession(models.Model):
    LANGUAGE_CHOICES = [
        ('cs', 'Czech'),
        ('sk', 'Slovak'),
        ('en', 'English'),
    ]
    
    session_id = models.CharField(max_length=255, unique=True, db_index=True)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='cs')
    audio_threshold = models.IntegerField(default=50)
    created_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Anonymous {self.session_id[:8]}... ({self.language})"

class StudentExample(models.Model):
    student = models.ForeignKey(Student, null=True, blank=True, on_delete=models.CASCADE)
    anonymous_session = models.ForeignKey(AnonymousSession, null=True, blank=True, on_delete=models.CASCADE)
    example = models.ForeignKey(Example, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    duration = models.IntegerField(default=0)
    attempts = models.IntegerField(default=0) 
    solved = models.BooleanField(default=False)
    skipped = models.BooleanField(default=False)
    
    # Skills that were selected for practice in this session
    # This allows tracking mastery for specific skill combinations (e.g., "addition" + "up to 10")
    # rather than counting progress separately for each parent skill
    practiced_skills = models.ManyToManyField(
        'Skill',
        blank=True,
        related_name='student_examples'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['student', 'example', 'date'], name='unique_student_example_date'),
            models.CheckConstraint(
                check=Q(student__isnull=False) | Q(anonymous_session__isnull=False),
                name='student_or_session_required'
            )
        ]

class ExampleAttempt(models.Model):
    ACTION_CHOICES = [
        ('evaluated', 'Evaluated'),
        ('skipped', 'Skipped'),
        ('terminated', 'Terminated'),
        ('no_match', 'No Match'),
        ('error', 'Error'),
    ]

    SOURCE_CHOICES = [
        ('speech', 'Speech'),
        ('text', 'Text'),
    ]

    student_example = models.ForeignKey(StudentExample, on_delete=models.CASCADE, related_name='attempt_logs')
    student = models.ForeignKey(Student, null=True, blank=True, on_delete=models.SET_NULL, related_name='example_attempts')
    anonymous_session = models.ForeignKey(AnonymousSession, null=True, blank=True, on_delete=models.SET_NULL, related_name='example_attempts')
    example = models.ForeignKey(Example, on_delete=models.CASCADE, related_name='attempt_logs')

    created_at = models.DateTimeField(auto_now_add=True)
    attempt_number = models.PositiveIntegerField(default=1)
    duration = models.IntegerField(default=0)

    source = models.CharField(max_length=16, choices=SOURCE_CHOICES, default='speech')
    input_type = models.CharField(max_length=32, blank=True, default='')
    language = models.CharField(max_length=10, blank=True, default='')
    action = models.CharField(max_length=32, choices=ACTION_CHOICES, default='evaluated')
    is_correct = models.BooleanField(null=True, blank=True)

    transcription = models.TextField(blank=True, default='')
    parsed_answer = models.CharField(max_length=255, blank=True, default='')
    example_text = models.CharField(max_length=255, blank=True, default='')
    correct_answer = models.CharField(max_length=255, blank=True, default='')

    audio_file_path = models.CharField(max_length=500, blank=True, default='')
    audio_format = models.CharField(max_length=50, blank=True, default='')

    practiced_skill_ids = models.JSONField(default=list, blank=True)
    practiced_skill_names = models.JSONField(default=list, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'created_at']),
            models.Index(fields=['anonymous_session', 'created_at']),
            models.Index(fields=['example', 'created_at']),
        ]

class Admin(models.Model):
    username = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        if self.pk is None: 
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, password):
        return check_password(password, self.password)

