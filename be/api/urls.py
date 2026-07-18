"""
================================================================================
 Module: urls.py
 Description: 
        Defines URL routing for HTTP views and WebSocket consumers in the app.
 Author: Dominik Horut (xhorut01)
================================================================================
"""

from django.urls import path
from . import views 
from .consumers import SpeechRecognitionConsumer
from .consumersSurvey import SurveySpeechTranscriptionConsumer

urlpatterns = [

    path('tasks/', views.get_tasks, name='get-tasks'),
    path('tasks/assignment-overview/', views.get_task_assignment_overview, name='get-task-assignment-overview'),
    path('tasks/<int:task_id>/', views.get_task, name='get-task'),
    path('tasks/<int:task_id>/stats/', views.get_task_stats, name='get-task-stats'),
    path('tasks/<int:task_id>/history/', views.get_task_history, name='get-task-history'),
    path('tasks/<int:task_id>/grade-levels/', views.update_task_grade_levels, name='update-task-grade-levels'),
    path('create-task/', views.create_task, name='create-task'),
    path('edit-task/', views.edit_task, name='edit-task'),
    path('tasks/<int:task_id>/delete/', views.delete_task, name='delete_task'),
    
    path('examples/', views.get_examples, name='get-examples'),
    path('examples/<int:example_id>/answer/', views.reveal_example_answer, name='reveal-example-answer'),
    path('example/<int:example_id>/delete/', views.delete_example, name='delete_example'),

    path('create-record/', views.create_example_record, name='create-example-record'),
    path('my-data/', views.get_my_data, name='get-my-data'),
    path('attempt-audio/<int:attempt_id>/', views.get_attempt_audio, name='get-attempt-audio'),
    path('attempt-sidecar/<int:attempt_id>/', views.get_attempt_sidecar, name='get-attempt-sidecar'),
    path('attempt-logs/', views.get_attempt_logs, name='get-attempt-logs'),
    path('example-reports/', views.get_example_reports, name='get-example-reports'),
    path('survey-feedbacks/', views.get_survey_feedbacks, name='get-survey-feedbacks'),
    path('survey-feedback-audio/<int:feedback_id>/', views.get_survey_feedback_audio, name='get-survey-feedback-audio'),
    path('update-record/', views.update_example_record, name='update-example-record'),
    path('delete-record/', views.delete_example_record, name='delete-example-record'),
    path('skip-example/', views.skip_example, name='skip-example'),
    path('check-answer/', views.check_answer, name='check-answer'),


    path('create-skill/', views.create_skill, name='create_skill'),
    path('skills/<int:skill_id>/delete/', views.delete_skill, name='delete-skill'),
    path('skill/<int:skill_id>/', views.get_skill, name='get-skill'),
    
    path('skill-tree/', views.get_skill_tree, name='get-skill-tree'),
    path('landing-page-skills/', views.get_landing_page_skills, name='get-landing-page-skills'),
    path('skills/<int:skill_id>/tree/related', views.get_related_skills_tree, name='related_skills_tree'),
    path('skills/<int:skill_id>/tree/children', views.get_children_skills_tree, name='children_skills_tree'),
    path('skills/<int:skill_id>/operations', views.get_operation_skills, name='operation_skills'),
    
    path('skills/search/', views.search_skills, name='skill-search'),
    path('skills/paths/sandbox/', views.get_paths_for_sandbox, name='get-sandbox-paths'),
    path('skills/related-counts/', views.get_skill_related_counts, name='get-skill-related-counts'),

    path('register/student', views.register_student, name='register_student'),
    path('login/student', views.login_student, name='login_student'),
    path('login/admin', views.login_admin, name='login_admin'),
    path('register/teacher', views.register_teacher, name='register_teacher'),
    path('login/teacher', views.login_teacher, name='login_teacher'),

    path('session/init/', views.init_session, name='init-session'),
    path('session/update-language/', views.update_session_language, name='update-session-language'),
    path('student/update-language/', views.update_student_language, name='update-student-language'),
    path('student/<int:student_id>/grade/', views.update_student_grade, name='update-student-grade'),

    path('survey-answer/', views.save_survey_answer, name='save-survey-answer'),
    path('example-report/', views.save_example_report, name='save-example-report'),
    
    path('grade-levels/', views.get_grade_levels, name='get-grade-levels'),
    path('skills/<int:skill_id>/grade-levels/', views.update_skill_grade_levels, name='update-skill-grade-levels'),
    path('skills/by-grade/<int:grade_id>/', views.get_skills_by_grade, name='get-skills-by-grade'),
    path('tasks/by-grade/<int:grade_id>/', views.get_tasks_by_grade, name='get-tasks-by-grade'),

    # Analytics & Skill Tracking
    path('analytics/students/', views.get_all_students_stats, name='all-students-stats'),
    path('analytics/anonymous-sessions/', views.get_all_anonymous_sessions_stats, name='all-anonymous-sessions-stats'),
    path('analytics/student/<int:student_id>/skills/', views.get_student_skill_stats, name='student-skill-stats'),
    path('analytics/student/<int:student_id>/skill-combinations/', views.get_student_skill_combinations, name='student-skill-combinations'),
    path('analytics/progress-overview/', views.get_progress_overview, name='progress-overview'),
    path('analytics/examples/', views.get_group_example_stats, name='group-example-stats'),
    path('analytics/skills/', views.get_group_skill_stats, name='group-skill-stats'),

    # Bulk import & export
    path('bulk-import-tasks/', views.bulk_import_tasks, name='bulk-import-tasks'),
    path('export/csv/', views.export_attempts_csv, name='export-attempts-csv'),

    # Gamification
    path('gamification/leaderboard/', views.get_leaderboard, name='gamification-leaderboard'),
    path('gamification/leaderboard/grade/', views.get_leaderboard_by_grade, name='gamification-leaderboard-grade'),
    path('gamification/student/<int:student_id>/stats/', views.get_student_gamification_stats, name='gamification-student-stats'),
    path('gamification/badges/', views.get_all_badges, name='gamification-badges'),
    path('example-requests/', views.save_example_request, name='example-requests'),
    path('example-requests/all/', views.get_all_example_requests, name='example-requests-all'),

    # AI Example Generation
    path('generation-quota/', views.generation_quota, name='generation-quota'),
    path('generate-examples/', views.generate_examples, name='generate-examples'),
    path('generated-batches/', views.get_all_generated_batches, name='generated-batches-all'),
    path('generated-batches/<int:batch_id>/survey/', views.submit_batch_survey, name='generated-batch-survey'),
    path('generated-batches/<int:batch_id>/approve/', views.approve_generated_batch, name='generated-batch-approve'),
    path('generated-batches/<int:batch_id>/reject/', views.reject_generated_batch, name='generated-batch-reject'),
    path('my-generated-batches/', views.get_my_generated_batches, name='my-generated-batches'),
    path('generated-batches/<int:batch_id>/delete/', views.delete_generated_batch, name='generated-batch-delete'),

    # Classrooms
    path('classrooms/', views.manage_classrooms, name='manage-classrooms'),
    path('classrooms/<int:classroom_id>/', views.classroom_detail, name='classroom-detail'),
    path('classrooms/join/', views.join_classroom, name='join-classroom'),
    path('classrooms/student/', views.get_student_classrooms, name='student-classrooms'),
    path('classrooms/info/', views.get_classroom_by_code, name='classroom-by-code'),
    path('classrooms/<int:classroom_id>/leave/', views.leave_classroom, name='leave-classroom'),
    path('classrooms/<int:classroom_id>/remove-student/', views.remove_student_from_classroom, name='remove-student'),
    path('classrooms/<int:classroom_id>/tasks/', views.manage_classroom_tasks, name='classroom-tasks'),
    path('classrooms/<int:classroom_id>/tasks/<int:task_id>/', views.classroom_task_detail, name='classroom-task-detail'),
    path('classrooms/<int:classroom_id>/analytics/', views.get_classroom_analytics, name='classroom-analytics'),
    path('classrooms/<int:classroom_id>/tasks/<int:task_id>/details/', views.get_classroom_task_details, name='classroom-task-details'),
    path('classrooms/<int:classroom_id>/tasks/<int:task_id>/homework-stats/', views.get_classroom_task_homework_stats, name='classroom-task-homework-stats'),
    path('classrooms/<int:classroom_id>/students/<int:student_id>/', views.get_classroom_student_detail, name='classroom-student-detail'),
    path('tasks/browse/', views.browse_tasks, name='browse-tasks'),
    path('teacher/generate-task/', views.teacher_generate_task_preview, name='teacher-generate-task'),
    path('teacher/save-task/', views.teacher_save_task, name='teacher-save-task'),
    path('teacher/examples/', views.teacher_examples, name='teacher-examples'),
    path('teacher/examples/<int:example_id>/', views.teacher_example_detail, name='teacher-example-detail'),
    path('teacher/tasks/copy/', views.teacher_copy_task, name='teacher-copy-task'),
    path('teacher/tasks/<int:task_id>/delete/', views.teacher_delete_task, name='teacher-delete-task'),
    path('teacher/tasks/<int:task_id>/examples/', views.teacher_task_examples, name='teacher-task-examples'),
    path('teacher/tasks/<int:task_id>/examples/attach/', views.teacher_attach_example, name='teacher-attach-example'),
    path('teacher/tasks/<int:task_id>/examples/detach/', views.teacher_detach_example, name='teacher-detach-example'),
    path('teacher/tasks/<int:task_id>/examples/copy-in/', views.teacher_copy_example_in, name='teacher-copy-example-in'),
    path('analytics/activity/', views.get_recent_activity, name='recent-activity'),
    path('admin/teachers/', views.get_all_teachers, name='admin-teachers'),
    path('admin/classrooms/<int:classroom_id>/students/', views.admin_classroom_students, name='admin-classroom-students'),
    path('admin/tasks/<int:task_id>/examples/', views.admin_task_examples, name='admin-task-examples'),
    path('admin/tasks/<int:task_id>/publish/', views.admin_publish_teacher_task, name='admin-publish-task'),
]

websocket_urlpatterns = [

    path('ws/speech/', SpeechRecognitionConsumer.as_asgi()),
    path('ws/survey/', SurveySpeechTranscriptionConsumer.as_asgi()),

]
