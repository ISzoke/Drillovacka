"""
================================================================================
 Module: serializers.py
 Description: 
        Defines serializers for converting model instances to and from JSON format
 Author: Dominik Horut (xhorut01)
================================================================================
"""

from rest_framework import serializers
from . import models


class ExampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Example
        fields = '__all__' 

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Skill
        fields = '__all__' 

class RecordInitSerializer(serializers.ModelSerializer):
    practiced_skills = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True
    )
    
    class Meta:
        model = models.StudentExample
        fields = ['student', 'anonymous_session', 'example', 'practiced_skills', 'practice_session_key']
    
    def create(self, validated_data):
        practiced_skill_ids = validated_data.pop('practiced_skills', [])

        # Auto-fill task from the example's task
        example = validated_data.get('example')
        if example and not validated_data.get('task'):
            validated_data['task'] = example.task

        student_example = models.StudentExample.objects.create(**validated_data)

        if practiced_skill_ids:
            skills = models.Skill.objects.filter(id__in=practiced_skill_ids)
            student_example.practiced_skills.set(skills)

        return student_example


class ExampleAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ExampleAttempt
        fields = '__all__'
