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

    grade_levels = models.ManyToManyField(
        'GradeLevel',
        blank=True,
        related_name='tasks',
    )

    primary_skill = models.OneToOneField(
        'Skill',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='task',
    )

    form = models.CharField(
        max_length=20,
        choices=FORM_CHOICES,
        default='classic',
    )

    # Private tasks: only visible to the student who generated them
    # Set to False when admin approves the task for public use
    is_private = models.BooleanField(default=False)
    owner_student = models.ForeignKey(
        'Student', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='private_tasks'
    )
    owner_session = models.ForeignKey(
        'AnonymousSession', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='private_tasks'
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
        ('TASK', 'Task'),
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

    # Grade level (1-9), set at registration, changeable once
    grade = models.IntegerField(null=True, blank=True)
    grade_change_used = models.BooleanField(default=False)

    # Gamification fields (denormalized for fast leaderboard queries)
    total_xp = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_practice_date = models.DateField(null=True, blank=True)

class AnonymousSession(models.Model):
    LANGUAGE_CHOICES = [
        ('cs', 'Czech'),
        ('sk', 'Slovak'),
        ('en', 'English'),
    ]
    
    session_id = models.CharField(max_length=255, unique=True, db_index=True)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='sk')
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

class ExampleReport(models.Model):
    REPORT_TYPE_CHOICES = [
        ('wrong_answer', 'Wrong Answer'),
        ('wrong_grade', 'Wrong Grade'),
        ('unclear', 'Unclear'),
        ('other', 'Other'),
    ]

    student = models.ForeignKey(Student, null=True, blank=True, on_delete=models.CASCADE)
    anonymous_session = models.ForeignKey(AnonymousSession, null=True, blank=True, on_delete=models.CASCADE)
    example = models.ForeignKey(Example, on_delete=models.CASCADE, related_name='reports')

    created_at = models.DateTimeField(auto_now_add=True)
    report_type = models.CharField(max_length=32, choices=REPORT_TYPE_CHOICES)
    note = models.TextField(blank=True, default='')

    input_type = models.CharField(max_length=32, blank=True, default='')
    language = models.CharField(max_length=10, blank=True, default='')
    example_text = models.CharField(max_length=255, blank=True, default='')
    correct_answer = models.CharField(max_length=255, blank=True, default='')

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
        constraints = [
            models.CheckConstraint(
                check=Q(student__isnull=False) | Q(anonymous_session__isnull=False),
                name='report_student_or_session_required'
            )
        ]


class SurveyFeedback(models.Model):
    SOURCE_CHOICES = [
        ('text', 'Text'),
        ('voice', 'Voice'),
    ]

    student = models.ForeignKey(Student, null=True, blank=True, on_delete=models.CASCADE)
    anonymous_session = models.ForeignKey(AnonymousSession, null=True, blank=True, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    question_type = models.CharField(max_length=64, blank=True, default='')
    question_text = models.TextField(blank=True, default='')
    answer = models.TextField(blank=True, default='')
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES, default='text')
    language = models.CharField(max_length=10, blank=True, default='')

    practiced_skill_ids = models.JSONField(default=list, blank=True)
    practiced_skill_names = models.JSONField(default=list, blank=True)

    audio_file_path = models.CharField(max_length=500, blank=True, default='')
    audio_format = models.CharField(max_length=50, blank=True, default='')
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'created_at']),
            models.Index(fields=['anonymous_session', 'created_at']),
            models.Index(fields=['question_type', 'created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(student__isnull=False) | Q(anonymous_session__isnull=False),
                name='survey_feedback_student_or_session_required'
            )
        ]

class Badge(models.Model):
    CATEGORY_CHOICES = [
        ('activity', 'Activity'),
        ('accuracy', 'Accuracy'),
        ('speed', 'Speed'),
        ('streak', 'Streak'),
        ('milestone', 'Milestone'),
    ]

    key = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=512)
    icon = models.CharField(max_length=64)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    xp_reward = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.name} ({self.key})"


class StudentBadge(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='earned_badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='student_badges')
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'badge')

    def __str__(self):
        return f"{self.student.username} — {self.badge.key}"


class ExampleRequest(models.Model):
    SOURCE_CHOICES = [
        ('text', 'Text'),
        ('voice', 'Voice'),
    ]

    student = models.ForeignKey(Student, null=True, blank=True, on_delete=models.CASCADE)
    anonymous_session = models.ForeignKey(AnonymousSession, null=True, blank=True, on_delete=models.CASCADE)
    grade = models.IntegerField(null=True, blank=True)
    text = models.TextField()
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES, default='text')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Grade {self.grade} request: {self.text[:60]}"


class Admin(models.Model):
    username = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, password):
        return check_password(password, self.password)


class GeneratedTaskBatch(models.Model):
    """
    Central connector for the AI example generation pipeline.
    Links: student query → generated JSON → private Task → survey answers → admin review.
    """
    GENERATION_MODE_CHOICES = [
        ('ai_free', 'AI Free Hand'),
        ('backend_generator', 'Backend Generator'),
    ]
    STATUS_CHOICES = [
        ('preview',        'Preview'),         # generated, shown to student
        ('survey_done',    'Survey Done'),      # student completed survey (Q5=No)
        ('pending_review', 'Pending Review'),   # Q5=Yes → awaiting admin
        ('approved',       'Approved'),
        ('rejected',       'Rejected'),
    ]
    GRADE_GROUP_CHOICES = [
        (1, 'Grades 1–3'),
        (2, 'Grades 4–6'),
        (3, 'Grades 7–9'),
    ]

    student = models.ForeignKey(
        Student, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='generated_batches'
    )
    example_request = models.ForeignKey(
        ExampleRequest, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='generated_batches'
    )

    grade = models.IntegerField()
    grade_group = models.IntegerField(choices=GRADE_GROUP_CHOICES)
    generation_mode = models.CharField(max_length=20, choices=GENERATION_MODE_CHOICES, default='ai_free')

    description = models.TextField()          # student's original query (denormalized)
    parser_output = models.JSONField(default=dict, blank=True)  # Phase 2: AI-parsed config
    raw_json = models.JSONField()             # generated task + examples JSON

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='preview')
    rejection_note = models.TextField(blank=True, default='')

    created_task = models.ForeignKey(
        Task, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='generated_batch'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Batch #{self.pk} — grade {self.grade} — {self.status}"


class GeneratedTaskBatchSurvey(models.Model):
    """
    Post-generation survey answers linked to a GeneratedTaskBatch.
    If q5_satisfied=True the batch is moved to pending_review for admin approval.
    """
    DIFFICULTY_CHOICES = [
        ('easy',  'Ľahké'),
        ('ok',    'Primerané'),
        ('hard',  'Ťažké'),
    ]

    batch = models.OneToOneField(
        GeneratedTaskBatch, on_delete=models.CASCADE, related_name='survey'
    )

    q1_as_requested     = models.BooleanField()  # Boli príklady to, o čo si žiadal?
    q2_solvable_display = models.BooleanField()  # Boli počitateľné? Zobrazili sa správne?
    q3_difficulty       = models.CharField(max_length=8, choices=DIFFICULTY_CHOICES)
    q4_has_errors       = models.BooleanField()  # Mali príklady chyby?
    q5_satisfied        = models.BooleanField()  # Si spokojný? → True triggers pending_review

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Survey for Batch #{self.batch_id} — satisfied={self.q5_satisfied}"
