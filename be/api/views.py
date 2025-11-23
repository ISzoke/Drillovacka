"""
================================================================================
 Module: views.py
 Description:
        Contains API views that serve the frontend with data manipulation functionality.
        It includes CRUD operations for tasks, examples, skills, and student records.
        It also handles user authentication and answer checking.

 Author: Dominik Horut (xhorut01)
================================================================================
"""

from rest_framework import generics
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth.hashers import make_password, check_password
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Count, Sum, Avg, Max, Q, F
from django.utils import timezone
import math
from .models import Task, Example, Answer, Student, Skill, ExampleSkill, StudentExample, Admin, Step, GradeLevel, AnonymousSession
from .serializers import ExampleSerializer, SkillSerializer, RecordInitSerializer
from .utils import get_height, build_skill_tree, get_skill_paths, get_skill_names_string_sync
from .answerChecker import InlineAnswerChecker, FractionAnswerChecker, VariableAnswerChecker
import json
import random
from datetime import datetime
import uuid
import os

# Helper function to get student or anonymous session from request
def get_user_identity(request):
    """
    Returns (student_obj, anonymous_session_obj) tuple.
    One will be None, the other will have a value.
    """
    student_id = request.data.get('student_id')
    session_id = request.data.get('session_id')
    
    if student_id:
        try:
            student = Student.objects.get(id=student_id)
            return (student, None)
        except Student.DoesNotExist:
            return (None, None)
    elif session_id:
        try:
            session = AnonymousSession.objects.get(session_id=session_id)
            return (None, session)
        except AnonymousSession.DoesNotExist:
            return (None, None)
    
    return (None, None)

# Add all skill_ids to the related_skills field of each skill
def create_skill_relations(skill_ids):

    skills = Skill.objects.filter(id__in=skill_ids)

    for skill in skills:
        related_skills = [s for s in skills if s != skill and s.skill_type != skill.skill_type]
        skill.related_skills.add(*related_skills)  

# Creates a new task and its examples
@api_view(['POST'])
def create_task(request):
    task_name = request.data.get('task_name')
    task_form = request.data.get('task_form')
    skill_ids = request.data.get('skill_ids', [])
    examples_data = request.data.get('examples', [])  

    if not task_name:
        return Response({"error": "Nebyl zadán název sady"}, status=status.HTTP_400_BAD_REQUEST)

    skills = Skill.objects.filter(id__in=skill_ids)

    if not skills.exists():
        return Response({"error": "Nebyly zadány žádné dovednosti"}, status=status.HTTP_400_BAD_REQUEST)

    task_instance, created = Task.objects.get_or_create(name=task_name)

    task_instance.form = task_form 

    task_instance.save()

    # Assign skills to the task
    task_instance.skills.add(*skills)

    created_examples = []

    # Loop through each example data and create it
    for example_data in examples_data:
        example_text = example_data.get('example')
        input_type = example_data.get('input_type')
        answer_text = example_data.get('answer')
        steps = example_data.get('steps', [])

        # Validate required fields
        if not example_text or not input_type:
            continue 

        
        example_payload = {
            'example': example_text,
            'input_type': input_type,
            'task': task_instance.id  
        }
        example_serializer = ExampleSerializer(data=example_payload)
        
        if example_serializer.is_valid():
            with transaction.atomic():  
                example_instance = example_serializer.save()

                # Create answer of example
                if answer_text:
                    Answer.objects.create(example=example_instance, answer=answer_text)

                # Assign skills to the example
                for skill in skills:
                    ExampleSkill.objects.create(example=example_instance, skill=skill)
                
                create_skill_relations(skill_ids)

                # Create example steps if any
                for index, step_text in enumerate(steps, start=1):
                    if step_text:  
                        Step.objects.create(
                            example=example_instance,
                            text=step_text,
                            order=index  
                        )

                
                created_examples.append(example_serializer.data)
    
    return Response({"created_examples": created_examples}, status=status.HTTP_201_CREATED)

# Edits an existing task and its examples
@api_view(['POST'])
def edit_task(request):
    task_id = request.data.get('task_id')
    task_name = request.data.get('task_name')
    task_form = request.data.get('task_form')   
    skill_ids = request.data.get('skill_ids', [])
    examples_data = request.data.get('examples', [])

    if not task_id:
        return Response({"error": "Nebyl zadán ID sady"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        task_instance = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return Response({"error": "Task not found."}, status=status.HTTP_404_NOT_FOUND)

    # Update task attributes
    if task_name:
        task_instance.name = task_name
        task_instance.form = task_form
        task_instance.save()

    skills = Skill.objects.filter(id__in=skill_ids)
    if not skills.exists():
        return Response({"error": "At least one valid skill ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    # Update tasks skills
    task_instance.skills.set(skills)

    updated_examples = []

    # Loop through each example in the request data
    for example_data in examples_data:
        example_id = example_data.get('example_id')
        example_text = example_data.get('example')
        input_type = example_data.get('input_type')
        answer_text = example_data.get('answer')
        steps = example_data.get('steps', [])

        if not example_text or not input_type:
            continue  

        # If example_id is provided, try to update the existing example
        if example_id:
            try:
                example_instance = Example.objects.get(id=example_id, task=task_instance)
                example_instance.example = example_text
                example_instance.input_type = input_type
                example_instance.save()
            except Example.DoesNotExist:
                return Response({"error": f"Example with ID {example_id} not found."},
                                status=status.HTTP_404_NOT_FOUND)
        
        # If no example_id is provided, check by example text or create a new one
        else:
            example_instance, created = Example.objects.update_or_create(
                example=example_text,
                task=task_instance,
                defaults={'input_type': input_type}
            )

        # Update or create answer
        if answer_text:
            answer_instance, _ = Answer.objects.update_or_create(
                example=example_instance,
                defaults={'answer': answer_text}
            )

        # Update related skills to the example
        existing_relations = ExampleSkill.objects.filter(example=example_instance)
        new_skill_ids = set(skill.id for skill in skills)
        existing_relations.exclude(skill_id__in=new_skill_ids).delete()

        for skill in skills:
            ExampleSkill.objects.update_or_create(example=example_instance, skill=skill)
        
        create_skill_relations(skill_ids)

        # Update or create Step instances
        Step.objects.filter(example=example_instance).delete() 
        for index, step_text in enumerate(steps, start=1):
            if step_text:
                Step.objects.create(
                    example=example_instance,
                    order=index,
                    text=step_text
                )

        example_serializer = ExampleSerializer(example_instance)
        updated_examples.append(example_serializer.data)

    
    return Response({"updated_examples": updated_examples}, status=status.HTTP_200_OK)

# Get skill data by provided skill id
@api_view(['GET'])
def get_skill(request, skill_id):
    try:
        skill = Skill.objects.get(id=skill_id)

        if skill.deleted == True:
            return Response({"error": "Skill not found"}, status=status.HTTP_404_NOT_FOUND)
        
        skill_data = SkillSerializer(skill).data
    
        return Response(skill_data, status=status.HTTP_200_OK)

    except Skill.DoesNotExist:
        return Response({"error": "Skill not found"}, status=status.HTTP_404_NOT_FOUND)

# Get all examples for the provided skill ids
@api_view(['GET'])
def get_examples(request):

    skills = request.query_params.get('topics')
    
    if not skills:
        return Response({"error": "No topics provided"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        skills_data = json.loads(skills)

    except json.JSONDecodeError:
        return Response({"error": "Invalid JSON format for topics"}, status=status.HTTP_400_BAD_REQUEST)

    # Get skill paths to get examples containing them
    skill_paths = get_skill_paths(skills_data)

    example_data = []

    for path in skill_paths:

        examples = Example.objects.filter(
            exampleskill__skill__id__in=path
        ).distinct()

        for example in examples:

            example_skill_ids = set(example.exampleskill_set.values_list('skill__id', flat=True))

            # Check if the example skill ids contain all the skills in the current path (no missing skills)
            if example_skill_ids.issuperset(set(path)):

                example_data.append({
                    "id": example.id,
                    "example": example.example,
                    "input_type": example.input_type,
                    "answers": [
                        {
                            "id": answer.id,
                            "answer": answer.answer
                        }
                        for answer in example.answers.all()
                    ],
                    "steps": [
                        {
                            "id": step.id,
                            "order": step.order,
                            "text": step.text
                        }
                        for step in example.steps.all().order_by('order')
                    ]
                })

    # Shuffle the final list of examples to ensure they are mixed
    random.shuffle(example_data)

    return Response(example_data, status=status.HTTP_200_OK)

# Create a new record that user practiced the example
@api_view(['POST'])
def create_example_record(request):
    student, anonymous_session = get_user_identity(request)
    example_id = request.data.get('example_id')
    practiced_skills = request.data.get('practiced_skills', [])
    
    if not student and not anonymous_session:
        return Response({"error": "Student ID or Session ID is required"}, status=status.HTTP_400_BAD_REQUEST)
    if not example_id:
        return Response({"error": "Example ID is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    init_data = {
        'student': student.id if student else None,
        'anonymous_session': anonymous_session.id if anonymous_session else None,
        'example': example_id,
        'practiced_skills': practiced_skills
    }

    record_init_serializer = RecordInitSerializer(data=init_data)

    if record_init_serializer.is_valid():
        record = record_init_serializer.save()

        response_data = record_init_serializer.data
        response_data['date'] = record.date

        return Response(response_data, status=status.HTTP_201_CREATED)

    return Response(record_init_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Updates record that user practiced the example
@api_view(['POST'])
def update_example_record(request):
    # Data to identify the record
    student, anonymous_session = get_user_identity(request)
    example_id = request.data.get('example_id')
    date = request.data.get('date')

    # Duration how long it took user to enter the answer
    duration = request.data.get('time')
  
    if (not student and not anonymous_session) or not example_id or not duration:
        return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Find record by student or anonymous_session
    if student:
        student_example = get_object_or_404(StudentExample, student=student, example_id=example_id, date=date)
    else:
        student_example = get_object_or_404(StudentExample, anonymous_session=anonymous_session, example_id=example_id, date=date)
    
    try:
        with transaction.atomic():
            # Update record data
            student_example.attempts += 1
            student_example.duration = duration

            # Determine if limit of tries is reached and new example should be shown to user
            next_example = student_example.attempts == 3
                         
            student_example.save()
        
        return Response({"message": "Record updated successfully", "next_example": next_example}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Deletes record that user practiced the example        
@api_view(['POST'])
def delete_example_record(request):
    # Data to identify the record
    student, anonymous_session = get_user_identity(request)
    example_id = request.data.get('example_id')
    date = request.data.get('date')

    if (not student and not anonymous_session) or not example_id or not date:
        return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)
    
    if student:
        student_example = get_object_or_404(StudentExample, student=student, example_id=example_id, date=date)
    else:
        student_example = get_object_or_404(StudentExample, anonymous_session=anonymous_session, example_id=example_id, date=date)

    try:
        with transaction.atomic():
            student_example.delete()

        return Response({"message": "Record successfully deleted"}, status=status.HTTP_204_NO_CONTENT)

    except StudentExample.DoesNotExist:
        return Response({"error": "Record not found"}, status=status.HTTP_404_NOT_FOUND)

# Updates example record to skipped
@api_view(['POST'])
def skip_example(request):
    # Data to identify the record
    student, anonymous_session = get_user_identity(request)
    example_id = request.data.get('example_id')
    date = request.data.get('date')

    if (not student and not anonymous_session) or not example_id or not date:
        return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)
    
    if student:
        student_example = get_object_or_404(StudentExample, student=student, example_id=example_id, date=date)
    else:
        student_example = get_object_or_404(StudentExample, anonymous_session=anonymous_session, example_id=example_id, date=date)

    try:
        with transaction.atomic():

            # Record is marked as skipped and attempts and duration are not relevant
            student_example.skipped = True
            student_example.attempts = 0
            student_example.duration = 0
                        
            student_example.save()
        
        return Response({"message": "Example skipped"}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Get all tasks and their examples
@api_view(['GET'])
def get_tasks(request):
    tasks = Task.objects.prefetch_related(
        'example_set__answers',         
        'example_set__exampleskill_set__skill', 
        'example_set__steps'           
    )
    
    data = []
    for task in tasks:
        # Get skills for the task
        skills = []
        # Use the first example to get skills, since all examples share the same skills
        first_example = task.example_set.first()
        if first_example:
            skills = [
                {
                    "id": example_skill.skill.id,
                    "name": example_skill.skill.name,
                    "height": example_skill.skill.height,
                    "skill_type": example_skill.skill.skill_type,
                    "parent_skill": example_skill.skill.parent_skill.id if example_skill.skill.parent_skill else None,
                    "related_skills": list(example_skill.skill.related_skills.values_list('id', flat=True))
                }
                for example_skill in first_example.exampleskill_set.all()
            ]
        
        # Get task data
        task_data = {
            "task_id": task.id,
            "task_name": task.name,
            "task_form": task.form,
            "skills": skills,  
            "examples": [
                {
                    "example_id": example.id,
                    "example": example.example,
                    "input_type": example.input_type,
                    "answers": [
                        {
                            "answer_id": answer.id,
                            "answer_text": answer.answer
                        }
                        for answer in example.answers.all()
                    ],
                    "steps": [
                        {
                            "step_id": step.id,
                            "step_text": step.text,
                            "order": step.order
                        }
                        for step in example.steps.all()
                    ]
                }
                for example in task.example_set.all()
            ]
        }
        data.append(task_data)
    
    return JsonResponse(data, safe=False)

# Delete an example and its related data (answers, steps)
@api_view(['DELETE'])
def delete_example(request, example_id):
    example = get_object_or_404(Example, id=example_id)
    
    try:
        with transaction.atomic():
            example.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Delete a task and its related data
@api_view(['DELETE'])
def delete_task(request, task_id):
    try:
        with transaction.atomic():
            task = get_object_or_404(Task, id=task_id)
            
            related_skills = list(task.skills.all())  

            # Remove connections from the skill-task relationship
            task.skills.clear()

            # Delete the task and its related data (examples, answers, steps)
            task.delete()

            # Check skill relationships and remove them if no other task uses them
            for skill in related_skills:
                for related_skill in skill.related_skills.all():
                    # Get all tasks where both skills are used together
                    shared_tasks = Task.objects.filter(skills=skill).filter(skills=related_skill)
                    
                    # If this was the last task using this relationship, remove the relation
                    if not shared_tasks.exists():
                        skill.related_skills.remove(related_skill)
                        related_skill.related_skills.remove(skill)

        return Response(status=status.HTTP_204_NO_CONTENT)

    except Exception as e:
        return Response(
            {"error": f"Error deleting task: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST
        )

# Create a new skill or restore a deleted one
@api_view(['POST'])
def create_skill(request):
    try:
        name = request.data.get('name')
        parent_skill_id = request.data.get('parent_skill')
        grade_level_ids = request.data.get('grade_levels', [])

        if not name:
            return Response({"error": "Skill name is required."}, status=status.HTTP_400_BAD_REQUEST)

        parent_skill = None
        skill_type = None

        # Prepare new skill data
        if parent_skill_id:
            parent_skill = get_object_or_404(Skill, id=parent_skill_id)
            skill_type = parent_skill.skill_type  
            height = get_height(parent_skill_id) + 1
        
        # No parent skill
        else:
            height = 0  
        # Check if a skill with the same name already exists and is not deleted
        existing_skill = Skill.objects.filter(name=name, deleted=True).first()
        
        if existing_skill:
            # If a deleted skill exists with the same name, restore it
            existing_skill.deleted = False
            existing_skill.save()
            
            # Update grade levels
            if grade_level_ids:
                existing_skill.grade_levels.set(grade_level_ids)

            return JsonResponse({
                "id": existing_skill.id,
                "name": existing_skill.name,
                "parent_skill": existing_skill.parent_skill.id if existing_skill.parent_skill else None,
                "skill_type": existing_skill.skill_type,
                "grade_levels": list(existing_skill.grade_levels.values_list('id', flat=True)),
            }, status=status.HTTP_200_OK)

        # If no deleted skill exists, create a new skill
        else:
            with transaction.atomic():  
                skill = Skill.objects.create(
                    name=name, 
                    parent_skill=parent_skill, 
                    skill_type=skill_type, 
                    height=height
                )
                
                # Add grade levels
                if grade_level_ids:
                    skill.grade_levels.set(grade_level_ids)

            return JsonResponse({
                "id": skill.id,
                "name": skill.name,
                "parent_skill": skill.parent_skill.id if skill.parent_skill else None,
                "skill_type": skill.skill_type,
                "grade_levels": list(skill.grade_levels.values_list('id', flat=True)),
            }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Get all skills in a tree structure
@api_view(['GET'])
def get_skill_tree(request):
    skills = Skill.objects.filter(deleted=False)
    skill_list = SkillSerializer(skills, many=True).data

    # Convert the flat list into a hierarchical structure
    skill_dict = {skill["id"]: {**skill, "children": []} for skill in skill_list}

    root_skills = []

    # Build the tree structure
    for skill in skill_dict.values():

        if skill["parent_skill"] is None:
            root_skills.append(skill)

        else:
            parent = skill_dict.get(skill["parent_skill"])
            if parent:
                parent["children"].append(skill)

    return Response(root_skills)

# Search for skills based on a query and parent skill
@api_view(['GET'])
def search_skills(request):
    query = request.GET.get('q', '') 
    skill_id = request.GET.get('skill_id', None) 

    if not skill_id:
        return Response([]) 

    try:
        parent_skill = Skill.objects.get(id=skill_id)

    except Skill.DoesNotExist:
        return Response([])

    if query:
        # Searched skill name must be children of provided parent skill
        skills = Skill.objects.filter(
            name__icontains=query, 
            parent_skill=parent_skill,
            deleted=False  
        )
    # No query provided, get all children of the parent skill   
    else:
        skills = Skill.objects.filter(parent_skill=parent_skill, deleted=False)

    skill_list = SkillSerializer(skills, many=True).data

    return Response(skill_list)

# Get skills which should be displayed on landing page
@api_view(['GET'])
def get_landing_page_skills(request):

    # Get non-deleted skills
    existing_skills = Skill.objects.filter(deleted=False)

    # Filter skills that should not be displayed (height <= 3)
    skills_with_height = existing_skills.filter(height__lte=3)

    # Get leaf skills
    leaf_skills = skills_with_height.filter(subskills__isnull=True)

    # Get skills with height 3
    skills_with_height_3 = existing_skills.filter(height=3)

    # Displayed skills should be leaf skills or have height == 3    
    skills = (leaf_skills | skills_with_height_3).distinct()

    serializer = SkillSerializer(skills, many=True)

    return Response(serializer.data)

# Get all skills related to the selected skill  
@api_view(['GET'])
def get_related_skills_tree(request, skill_id):
    try:
        main_skill = Skill.objects.get(id=skill_id, deleted=False)  
        visited = set()
        tree = []

        related_skills = main_skill.related_skills.filter(deleted=False)    

        # Build tree structure to be visualized in the frontend
        for skill in related_skills:
            skill_ids = [main_skill.id, skill.id] 
            if skill.id not in visited:
                subtree = build_skill_tree(skill, visited, skill_ids, related_skills, None)
                if subtree:
                    tree.append(subtree)

        return Response(tree)

    except Skill.DoesNotExist:
        return Response({"error": "Skill not found"}, status=404)

# Get all children skills of the selected skill
@api_view(['GET'])
def get_children_skills_tree(request, skill_id):

    # Edge case for Equation skills
    withCounts = request.GET.get('with_counts', 'false') == 'true'

    try:
        main_skill = Skill.objects.get(id=skill_id)  

        if main_skill.deleted:
            return Response({"error": "Skill not found"}, status=404)   
        visited = set()  
        tree = []
        
        # Get all children skills of the selected skill
        children = Skill.objects.filter(parent_skill=main_skill, deleted=False)

        # Build subtree structure of each child to be visualized in the frontend
        for skill in children:
            if skill.id not in visited:
                subtree = build_skill_tree(skill, visited, None, None, withCounts) 
                if subtree:
                    tree.append(subtree)

        return Response(tree)  

    except Skill.DoesNotExist:
        return Response({"error": "Skill not found"}, status=404)

# Get all operation skills related to the selected skill    
@api_view(['GET'])
def get_operation_skills(request, skill_id):
    try:
        main_skill = get_object_or_404(Skill, id=skill_id)

        if main_skill.deleted:
            return Response({"error": "Skill not found"}, status=404)

        # Get all children skills of the selected skill
        children_skills = main_skill.subskills.filter(deleted=False)

        # Get all operation skills related to the selected skill    
        related_operation_skills = main_skill.related_skills.filter(skill_type='OPERATION', deleted=False)

        skills_data = []

        for operation_skill in related_operation_skills:
            child_data = []

            for child_skill in children_skills:
                # Count examples that have both operation_skill and child_skill
                examples_count = ExampleSkill.objects.filter(
                    skill=operation_skill
                ).filter(
                    example__in=ExampleSkill.objects.filter(skill=child_skill).values('example')
                ).count()

                child_data.append({
                    "related_id": child_skill.id,
                    "related_name": child_skill.name,
                    "examples": examples_count
                })

            # Include only single operations not parent skill Operations
            if operation_skill.height >= 3:
                skills_data.append({
                "id": operation_skill.id,
                "name": operation_skill.name,
                "related_skills": child_data
                })

        return Response(skills_data)
    
    except Skill.DoesNotExist:
        return Response({"error": "Skill not found"}, status=404)

# Soft delete a skill and remove all its relations
@api_view(['PATCH'])
def delete_skill(request, skill_id):
    try:
        skill = Skill.objects.get(id=skill_id)
        
        # Mark the skill as deleted
        skill.deleted = True
        skill.save()
        
        # Remove this skill from all related examples
        ExampleSkill.objects.filter(skill=skill).delete()
        
        # Remove this skill from realtions with tasks
        for task in Task.objects.filter(skills=skill):
            task.skills.remove(skill)
        
        # Remove this skill from all related_skills
        for related_skill in skill.related_skills.all():
            skill.related_skills.remove(related_skill)
        
        return Response(
            {"message": f"Skill '{skill.name}' marked as deleted and all relations removed."},
            status=status.HTTP_200_OK
        )
        
    except Skill.DoesNotExist:
        return Response(
            {"error": "Skill not found."},
            status=404
        )

# Create new user account
@api_view(['POST'])
def register_student(request):
    username = request.data.get('username')
    passphrase = request.data.get('passphrase')

    if not username or not passphrase:
        return Response({'error': 'Chybí uživatelské jméno nebo heslo'}, status=status.HTTP_400_BAD_REQUEST)
    
    if Student.objects.filter(username=username).exists():
        return Response({'error': 'Tato přezdívka je již používána jiným uživatelem'}, status=status.HTTP_400_BAD_REQUEST)
    
    hashed_passphrase = make_password(passphrase)

    student = Student.objects.create(username=username, passphrase=hashed_passphrase)
    student.save()

    return Response({'message': 'Student registered successfully!','id': student.id}, status=status.HTTP_201_CREATED)

# Login user account
@api_view(['POST'])
def login_student(request):
    username = request.data.get('username')
    passphrase = request.data.get('passphrase')

    if not username or not passphrase:
        return Response({'error': 'Nebyly zadány všechny potřebné údaje'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        student = Student.objects.get(username=username)
    except Student.DoesNotExist:
        return Response({'error': 'Nesprávné přihlašovací údaje'}, status=status.HTTP_400_BAD_REQUEST)

    if check_password(passphrase, student.passphrase):
        return Response({
            'message': 'Login successful!',
            'id': student.id,
            'role': 'student',
            'language': student.language
        }, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Nesprávné přihlašovací údaje'}, status=status.HTTP_401_UNAUTHORIZED)
    
# Login admin account   
@api_view(['POST'])
def login_admin(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({'error': 'Nebyly zadány všechny potřebné údaje'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        admin = Admin.objects.get(username=username)
    except Admin.DoesNotExist:
        return Response({'error': 'Nesprávné přihlašovací údaje'}, status=status.HTTP_400_BAD_REQUEST)

    if check_password(password, admin.password):
        return Response({'message': 'Přihlášení proběhlo úspěšně!', 'role': 'admin'}, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Nesprávné přihlašovací údaje'}, status=status.HTTP_401_UNAUTHORIZED)

# Initialize or get anonymous session
@api_view(['POST'])
def init_session(request):
    session_id = request.data.get('session_id')
    
    # If no session_id provided, generate new one
    if not session_id:
        session_id = str(uuid.uuid4())
        session = AnonymousSession.objects.create(session_id=session_id)
        return Response({
            'session_id': session_id,
            'language': session.language,
            'created': True
        }, status=status.HTTP_201_CREATED)
    
    # Try to get existing session
    try:
        session = AnonymousSession.objects.get(session_id=session_id)
        # Update last_active timestamp
        session.save()
        return Response({
            'session_id': session.session_id,
            'language': session.language,
            'created': False
        }, status=status.HTTP_200_OK)
    except AnonymousSession.DoesNotExist:
        # Session doesn't exist, create new one
        session = AnonymousSession.objects.create(session_id=session_id)
        return Response({
            'session_id': session.session_id,
            'language': session.language,
            'created': True
        }, status=status.HTTP_201_CREATED)

# Update language preference for anonymous session
@api_view(['POST'])
def update_session_language(request):
    session_id = request.data.get('session_id')
    language = request.data.get('language')
    
    if not session_id or not language:
        return Response({'error': 'Missing session_id or language'}, status=status.HTTP_400_BAD_REQUEST)
    
    if language not in ['cs', 'sk', 'en']:
        return Response({'error': 'Invalid language code'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        session = AnonymousSession.objects.get(session_id=session_id)
        session.language = language
        session.save()
        return Response({
            'message': 'Language updated successfully',
            'language': session.language
        }, status=status.HTTP_200_OK)
    except AnonymousSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

# Update language preference for authenticated student
@api_view(['POST'])
def update_student_language(request):
    student_id = request.data.get('student_id')
    language = request.data.get('language')
    
    print(f"[DEBUG] update_student_language called with student_id={student_id}, language={language}")
    
    if not student_id or not language:
        return Response({'error': 'Missing student_id or language'}, status=status.HTTP_400_BAD_REQUEST)
    
    if language not in ['cs', 'sk', 'en']:
        return Response({'error': 'Invalid language code'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        student = Student.objects.get(id=student_id)
        print(f"[DEBUG] Found student: {student.username}, current language: {student.language}")
        student.language = language
        student.save()
        print(f"[DEBUG] Updated student {student.username} language to: {student.language}")
        return Response({
            'message': 'Language updated successfully',
            'language': student.language
        }, status=status.HTTP_200_OK)
    except Student.DoesNotExist:
        print(f"[DEBUG] Student with id={student_id} not found")
        return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

# Check if the keyboard entered answer is correct
@api_view(['POST'])
def check_answer(request):

    student_id = request.data.get('student_id')
    session_id = request.data.get('session_id')
    example_id = request.data.get('example_id')

    # Data for record creation
    date = request.data.get('date')
    duration = request.data.get('duration')

    student_answer = request.data.get('student_answer')
    answer_type = request.data.get('answer_type')

    if (not student_id and not session_id) or not example_id or not date or not duration or not answer_type:
        return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Choose the answer checker based on the answer type
    # Note: verifyAnswer internally calls updateRecord with student_id/session_id
    match answer_type:
        case "inline" | "word":
            isCorrect, continue_with_next = InlineAnswerChecker.verifyAnswer(student_id, example_id, date, duration, student_answer, session_id=session_id)
            pass

        case "fraction":
            isCorrect, continue_with_next = FractionAnswerChecker.verifyAnswer(student_id, example_id, date, duration, student_answer, session_id=session_id)
            pass

        case "variable":
            isCorrect, continue_with_next = VariableAnswerChecker.verifyAnswer(student_id, example_id, date, duration, student_answer, session_id=session_id)
            pass

        case _:
            return Response({'error': 'Invalid answer type'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Return if answer was corrrect and if new example should be shown
    return Response({'isCorrect': isCorrect, 'continue_with_next': continue_with_next}, status=status.HTTP_200_OK)    

# Get all skill paths from skill ids to be displayed when editing task
@api_view(['GET'])
def get_paths_for_sandbox(request):
    skill_ids = request.GET.getlist('skill_ids', [])  

    if len(skill_ids) == 1 and ',' in skill_ids[0]:
        skill_ids = skill_ids[0].split(',')

    try:
        skill_ids = [int(id) for id in skill_ids] 
        skill_paths = get_skill_paths(skill_ids, False)
        return Response(skill_paths, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Get number of tasks and examples related to the selected skill
@api_view(['GET'])
def get_skill_related_counts(request):
    skill_id = request.GET.get('skill_id')

    skill = get_object_or_404(Skill, id=skill_id)

    task_count = Task.objects.filter(skills=skill).count()

    example_count = ExampleSkill.objects.filter(skill=skill).count()

    data = {
        "task_count": task_count,
        "example_count": example_count
    }

    return Response(data)

# Directory to save survey answers  
SURVEY_DIR = "survey"
os.makedirs(SURVEY_DIR, exist_ok=True)

# Save survey answer to a JSON file
@api_view(['POST'])
def save_survey_answer(request):

    # Survey answer data
    question_type = request.data.get('question_type')
    question_text = request.data.get('question_text')
    answer = request.data.get('answer')
    skills = request.data.get('skills')

    # Skills which were practiced when question was asked
    skill_names = get_skill_names_string_sync(skills)

    if not question_type or not question_text or not answer:
        return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    json_filename = f"{question_type}_{timestamp}.json"
    json_filepath = os.path.join(SURVEY_DIR, json_filename)
        
    survey_question_data = {
        "question_text": question_text,
        "answer": answer,
        "examples_type": skill_names,
        "timestamp": timestamp
    }

    # Save the survey answer to a JSON file
    with open(json_filepath, "w", encoding="utf-8") as json_file:
        json.dump(survey_question_data, json_file, indent=4, ensure_ascii=False)
    
    return Response(status=status.HTTP_200_OK)

# Get all grade levels (1-9)
@api_view(['GET'])
def get_grade_levels(request):
    try:
        grade_levels = GradeLevel.objects.all().order_by('grade')
        data = [{"id": gl.id, "grade": gl.grade} for gl in grade_levels]
        return JsonResponse(data, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Update grade levels for a skill
@api_view(['PATCH'])
def update_skill_grade_levels(request, skill_id):
    try:
        skill = get_object_or_404(Skill, id=skill_id)
        grade_level_ids = request.data.get('grade_levels', [])
        
        # Update the grade levels
        skill.grade_levels.set(grade_level_ids)
        
        return JsonResponse({
            "id": skill.id,
            "name": skill.name,
            "grade_levels": list(skill.grade_levels.values_list('id', flat=True))
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Get skills by grade level
@api_view(['GET'])
def get_skills_by_grade(request, grade_id):
    try:
        grade = get_object_or_404(GradeLevel, id=grade_id)
        
        # Get all skills assigned to this grade level
        # Only get top-level skills (those with skill_type set)
        skills = Skill.objects.filter(
            grade_levels=grade,
            deleted=False,
            skill_type__isnull=False  # Only parent skills
        ).distinct().order_by('name')
        
        skills_data = [
            {
                "id": skill.id,
                "name": skill.name,
                "skill_type": skill.skill_type
            }
            for skill in skills
        ]
        
        return JsonResponse(skills_data, safe=False, status=status.HTTP_200_OK)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ================================
# Analytics & Skill Tracking
# ================================

# Per-student stats aggregated by skill (no new tables; computed on demand)
@api_view(['GET'])
def get_student_skill_stats(request, student_id):
    """
    Returns analytics for skills that the student has practiced.
    
    Key change: Mastery is now calculated ONLY for the specific skill combinations
    that the student selected during practice sessions (practiced_skills),
    rather than separately for each parent skill in the hierarchy.
    
    For example, if a student practices "addition up to 10" (selecting both 
    "addition" and "up to 10" skills), the mastery will be tracked for that
    specific combination, not separately for "addition", "arithmetic", "up to 10", etc.
    """
    try:
        # Optional: filter by subtree root skill
        root_skill_id = request.GET.get('root_skill_id')

        # Get all unique skill IDs that were explicitly selected for practice
        # (from the practiced_skills ManyToMany relationship)
        practiced_skill_ids = StudentExample.objects.filter(
            student_id=student_id
        ).values_list('practiced_skills__id', flat=True).distinct()

        # Remove None values (in case some StudentExamples have no practiced_skills)
        practiced_skill_ids = [sid for sid in practiced_skill_ids if sid is not None]

        if not practiced_skill_ids:
            # Fallback to old behavior if no practiced_skills are set
            # (for backward compatibility with old data)
            practiced_skill_ids = ExampleSkill.objects.filter(
                example__studentexample__student_id=student_id
            ).values_list('skill_id', flat=True).distinct()

        results = []
        for skill_id in practiced_skill_ids:
            # Get all StudentExample records where this skill was in practiced_skills
            records = StudentExample.objects.filter(
                student_id=student_id,
                practiced_skills__id=skill_id
            ).distinct()
            
            if not records.exists():
                continue
            
            skill = Skill.objects.get(id=skill_id)
            examples_practiced = records.count()
            solved_count = records.filter(solved=True).count()
            skip_count = records.filter(skipped=True).count()
            total_attempts = records.aggregate(Sum('attempts'))['attempts__sum'] or 0
            avg_duration = records.aggregate(Avg('duration'))['duration__avg'] or 0
            last_practiced = records.aggregate(Max('date'))['date__max']
            
            results.append({
                'skill_id': skill_id,
                'skill_name': skill.name,
                'examples_practiced': examples_practiced,
                'solved_count': solved_count,
                'skip_count': skip_count,
                'total_attempts': total_attempts,
                'avg_duration': avg_duration,
                'last_practiced': last_practiced,
            })

        # If filtering by a subtree, keep only skills under that subtree
        if root_skill_id:
            try:
                root = Skill.objects.get(id=int(root_skill_id))
            except Exception:
                return Response({"error": "Invalid root_skill_id"}, status=status.HTTP_400_BAD_REQUEST)

            # Collect all descendants (including root)
            descendant_ids = set()
            stack = [root]
            while stack:
                node = stack.pop()
                if node.id not in descendant_ids:
                    descendant_ids.add(node.id)
                    stack.extend(list(node.subskills.filter(deleted=False)))

            results = [r for r in results if r['skill_id'] in descendant_ids]

        # Build response with derived metrics
        now = timezone.now()
        tau_seconds = int(request.GET.get('tau_seconds', '86400'))  # ~1 day default

        data = []
        for row in results:
            practiced = row['examples_practiced'] or 0
            skipped = row['skip_count'] or 0
            denom = max(practiced - skipped, 1)
            accuracy = (row['solved_count'] or 0) / denom
            avg_attempts = (row['total_attempts'] or 0) / practiced if practiced else 0

            # Bayesian mastery with Beta prior (2,2)
            successes = row['solved_count'] or 0
            failures = max(denom - successes, 0)
            alpha = 2 + successes
            beta = 2 + failures
            mastery_mean = alpha / (alpha + beta)

            # Wilson-like lower bound approximation for prioritization
            n = successes + failures
            p = successes / n if n > 0 else 0.0
            z = 1.96
            denom_w = 1 + z*z/n if n > 0 else 1
            center = p + z*z/(2*n) if n > 0 else 0
            margin = z*math.sqrt((p*(1-p) + z*z/(4*n))/n) if n > 0 else 0
            wilson_lower = max(0.0, (center - margin)/denom_w) if n > 0 else 0.0

            # Freshness factor (larger when not practiced recently)
            last = row['last_practiced']
            if last:
                dt = (now - last).total_seconds()
                freshness = 1 - math.exp(-dt / max(tau_seconds, 1))
            else:
                freshness = 1.0

            # Next practice weight: focus on weak + stale skills
            next_weight = (1 - wilson_lower) * freshness

            data.append({
                'skill_id': row['skill_id'],
                'skill_name': row['skill_name'],
                'examples_practiced': practiced,
                'solved_count': row['solved_count'] or 0,
                'skip_count': skipped,
                'total_attempts': row['total_attempts'] or 0,
                'avg_attempts_per_example': round(avg_attempts, 3),
                'avg_duration_ms': row['avg_duration'] or 0,
                'last_practiced': row['last_practiced'],
                'accuracy': round(accuracy, 3),
                'mastery_mean': round(mastery_mean, 3),
                'wilson_lower': round(wilson_lower, 3),
                'next_weight': round(next_weight, 3),
                'observations': n,
            })

        # Sort by lowest accuracy first by default
        order = request.GET.get('order', 'accuracy_asc')
        if order == 'accuracy_desc':
            data.sort(key=lambda x: x['accuracy'], reverse=True)
        elif order == 'recent':
            data.sort(key=lambda x: (x['last_practiced'] is None, x['last_practiced']), reverse=True)
        else:
            data.sort(key=lambda x: x['accuracy'])

        return JsonResponse(data, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Get student stats grouped by skill COMBINATIONS (not individual skills)
# This shows what the student actually practiced together (e.g., "Sčítání + Celé čísla + Do 100")
@api_view(['GET'])
def get_student_skill_combinations(request, student_id):
    """
    Returns analytics grouped by practiced skill combinations.
    
    Instead of showing individual skills separately, this groups records by
    the exact combination of skills that were practiced together.
    
    Example: If student practiced "Sčítání + Celé čísla + Do 100" together,
    it will show as one row, not three separate rows.
    """
    try:
        from collections import defaultdict
        
        # Get all StudentExample records for this student
        records = StudentExample.objects.filter(
            student_id=student_id
        ).prefetch_related('practiced_skills')
        
        if not records.exists():
            return JsonResponse([], safe=False, status=status.HTTP_200_OK)
        
        # Group records by skill combination (tuple of skill IDs)
        combinations = defaultdict(list)
        
        for record in records:
            # Get sorted tuple of skill IDs (for consistent grouping)
            skill_ids = tuple(sorted(record.practiced_skills.values_list('id', flat=True)))
            
            # Skip records with no practiced_skills (old data)
            if not skill_ids:
                continue
                
            combinations[skill_ids].append(record)
        
        # Calculate stats for each combination
        now = timezone.now()
        tau_seconds = int(request.GET.get('tau_seconds', '86400'))
        
        data = []
        for skill_ids, combo_records in combinations.items():
            # Get skill names
            skills = Skill.objects.filter(id__in=skill_ids).values('id', 'name')
            skill_map = {s['id']: s['name'] for s in skills}
            skill_names = [skill_map[sid] for sid in skill_ids]
            
            # Calculate metrics
            examples_practiced = len(combo_records)
            solved_count = sum(1 for r in combo_records if r.solved)
            skip_count = sum(1 for r in combo_records if r.skipped)
            total_attempts = sum(r.attempts for r in combo_records)
            avg_duration = sum(r.duration for r in combo_records) / len(combo_records) if combo_records else 0
            last_practiced = max(r.date for r in combo_records)
            
            # Accuracy & mastery
            denom = max(examples_practiced - skip_count, 1)
            accuracy = solved_count / denom
            avg_attempts = total_attempts / examples_practiced if examples_practiced else 0
            
            # Bayesian mastery
            successes = solved_count
            failures = max(denom - successes, 0)
            alpha = 2 + successes
            beta = 2 + failures
            mastery_mean = alpha / (alpha + beta)
            
            # Wilson lower bound
            n = successes + failures
            p = successes / n if n > 0 else 0.0
            z = 1.96
            denom_w = 1 + z*z/n if n > 0 else 1
            center = p + z*z/(2*n) if n > 0 else 0
            margin = z*math.sqrt((p*(1-p) + z*z/(4*n))/n) if n > 0 else 0
            wilson_lower = max(0.0, (center - margin)/denom_w) if n > 0 else 0.0
            
            # Freshness
            dt = (now - last_practiced).total_seconds()
            freshness = 1 - math.exp(-dt / max(tau_seconds, 1))
            
            # Next practice weight
            next_weight = (1 - wilson_lower) * freshness
            
            data.append({
                'skill_ids': list(skill_ids),
                'skill_names': skill_names,
                'combination_display': ' + '.join(skill_names),
                'examples_practiced': examples_practiced,
                'solved_count': solved_count,
                'skip_count': skip_count,
                'total_attempts': total_attempts,
                'avg_attempts_per_example': round(avg_attempts, 3),
                'avg_duration_ms': round(avg_duration, 3),
                'last_practiced': last_practiced,
                'accuracy': round(accuracy, 3),
                'mastery_mean': round(mastery_mean, 3),
                'wilson_lower': round(wilson_lower, 3),
                'next_weight': round(next_weight, 3),
                'observations': n,
            })
        
        # Sort by next_weight (descending) - most important to practice first
        data.sort(key=lambda x: x['next_weight'], reverse=True)
        
        return JsonResponse(data, safe=False, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        return JsonResponse({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Global example quality stats; flags potentially problematic examples
@api_view(['GET'])
def get_group_example_stats(request):
    try:
        min_records = int(request.GET.get('min_records', '10'))
        flag_threshold = float(request.GET.get('flag_threshold', '0.5'))  # accuracy below threshold => flag
        limit = int(request.GET.get('limit', '100'))

        qs = StudentExample.objects.values(
            'example_id',
            'example__example',
            'example__input_type',
        ).annotate(
            records=Count('id'),
            solved_count=Count('id', filter=Q(solved=True)),
            skip_count=Count('id', filter=Q(skipped=True)),
            total_attempts=Sum('attempts'),
            avg_duration=Avg('duration'),
            last_practiced=Max('date'),
        )

        data = []
        for row in qs:
            practiced = row['records'] or 0
            skipped = row['skip_count'] or 0
            denom = max(practiced - skipped, 1)
            accuracy = (row['solved_count'] or 0) / denom

            # Get skills for the example (names & ids)
            skills = list(ExampleSkill.objects.filter(example_id=row['example_id'])
                          .values('skill_id', 'skill__name'))

            item = {
                'example_id': row['example_id'],
                'example': row['example__example'],
                'input_type': row['example__input_type'],
                'records': practiced,
                'solved_count': row['solved_count'] or 0,
                'skip_count': skipped,
                'total_attempts': row['total_attempts'] or 0,
                'avg_duration_ms': row['avg_duration'] or 0,
                'last_practiced': row['last_practiced'],
                'accuracy': round(accuracy, 3),
                'skills': skills,
                'flagged': practiced >= min_records and accuracy < flag_threshold,
            }
            data.append(item)

        # Order: most problematic first (lowest accuracy with enough data), then by records desc
        data.sort(key=lambda x: (not (x['records'] >= min_records), x['accuracy'], -x['records']))
        data = data[:limit]

        return JsonResponse(data, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Global skill stats across all students
@api_view(['GET'])
def get_group_skill_stats(request):
    try:
        qs = StudentExample.objects.values(
            'example__exampleskill__skill_id',
            'example__exampleskill__skill__name',
        ).annotate(
            records=Count('id'),
            solved_count=Count('id', filter=Q(solved=True)),
            skip_count=Count('id', filter=Q(skipped=True)),
            total_attempts=Sum('attempts'),
            avg_duration=Avg('duration'),
            last_practiced=Max('date'),
        )

        data = []
        for row in qs:
            practiced = row['records'] or 0
            skipped = row['skip_count'] or 0
            denom = max(practiced - skipped, 1)
            accuracy = (row['solved_count'] or 0) / denom
            avg_attempts = (row['total_attempts'] or 0) / practiced if practiced else 0

            data.append({
                'skill_id': row['example__exampleskill__skill_id'],
                'skill_name': row['example__exampleskill__skill__name'],
                'records': practiced,
                'solved_count': row['solved_count'] or 0,
                'skip_count': skipped,
                'total_attempts': row['total_attempts'] or 0,
                'avg_attempts_per_example': round(avg_attempts, 3),
                'avg_duration_ms': row['avg_duration'] or 0,
                'last_practiced': row['last_practiced'],
                'accuracy': round(accuracy, 3),
            })

        # Sort by lowest accuracy first
        data.sort(key=lambda x: x['accuracy'])

        return JsonResponse(data, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Get list of all students with their overall stats
@api_view(['GET'])
def get_all_students_stats(request):
    try:
        students = Student.objects.all().order_by('username')
        data = []
        
        for student in students:
            records = StudentExample.objects.filter(student=student)
            total_examples = records.count()
            solved = records.filter(solved=True).count()
            skipped = records.filter(skipped=True).count()
            total_attempts = records.aggregate(Sum('attempts'))['attempts__sum'] or 0
            avg_duration = records.aggregate(Avg('duration'))['duration__avg'] or 0
            last_practiced = records.aggregate(Max('date'))['date__max']
            
            denom = max(total_examples - skipped, 1)
            accuracy = solved / denom if denom > 0 else 0
            
            data.append({
                'student_id': student.id,
                'username': student.username,
                'total_examples': total_examples,
                'solved_count': solved,
                'skip_count': skipped,
                'total_attempts': total_attempts,
                'avg_duration_ms': round(avg_duration, 1),
                'last_practiced': last_practiced,
                'accuracy': round(accuracy, 3),
            })
        
        return JsonResponse(data, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
