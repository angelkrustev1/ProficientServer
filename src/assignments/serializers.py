from django.db import transaction
from rest_framework import serializers

from .models import Assignment, AssignmentFile, Submission, SubmissionFile
from courses.models import Course


class AssignmentFileSerializer(serializers.ModelSerializer):
    filename = serializers.CharField(read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = AssignmentFile
        fields = ("id", "file", "file_url", "filename", "uploaded_at")

    def get_file_url(self, obj):
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url


class AssignmentReadSerializer(serializers.ModelSerializer):
    files = AssignmentFileSerializer(many=True, read_only=True)
    creator = serializers.StringRelatedField()
    course = serializers.StringRelatedField()

    class Meta:
        model = Assignment
        fields = (
            "id",
            "course",
            "creator",
            "title",
            "description",
            "files",
            "created_at",
            "updated_at",
        )


class AssignmentWriteSerializer(serializers.ModelSerializer):
    course_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Assignment
        fields = ("id", "course_id", "title", "description")

    def validate_course_id(self, value):
        if not Course.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Course does not exist.")
        return value

    def create(self, validated_data):
        course_id = validated_data.pop("course_id")
        return Assignment.objects.create(course_id=course_id, **validated_data)

    def update(self, instance, validated_data):
        course_id = validated_data.pop("course_id", None)

        if course_id:
            instance.course_id = course_id

        instance.title = validated_data.get("title", instance.title)
        instance.description = validated_data.get("description", instance.description)
        instance.save()

        return instance


class SubmissionFileSerializer(serializers.ModelSerializer):
    filename = serializers.CharField(read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = SubmissionFile
        fields = ("id", "file", "file_url", "filename", "uploaded_at")

    def get_file_url(self, obj):
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url


class SubmissionReadSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    assignment = serializers.StringRelatedField()
    files = SubmissionFileSerializer(many=True, read_only=True)

    class Meta:
        model = Submission
        fields = (
            "id",
            "assignment",
            "user",
            "is_submitted",
            "submitted_at",
            "files",
            "created_at",
            "updated_at",
        )
