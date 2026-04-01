from django.db import transaction
from rest_framework import serializers

from .models import Material, MaterialFile
from courses.models import Course


class MaterialFileSerializer(serializers.ModelSerializer):
    filename = serializers.CharField(read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = MaterialFile
        fields = ("id", "file", "file_url", "filename", "uploaded_at")
        read_only_fields = ("id", "file_url", "filename", "uploaded_at")

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not obj.file:
            return None
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url


class MaterialReadSerializer(serializers.ModelSerializer):
    files = MaterialFileSerializer(many=True, read_only=True)
    creator = serializers.StringRelatedField(read_only=True)
    creator_email = serializers.EmailField(source="creator.email", read_only=True)
    course = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Material
        fields = (
            "id",
            "course",
            "creator",
            "creator_email",
            "title",
            "description",
            "files",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class MaterialWriteSerializer(serializers.ModelSerializer):
    course_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Material
        fields = ("id", "course_id", "title", "description")
        read_only_fields = ("id",)

    def validate_course_id(self, value):
        if not Course.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Course with this id does not exist.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        course_id = validated_data.pop("course_id")
        return Material.objects.create(course_id=course_id, **validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        course_id = validated_data.pop("course_id", None)
        if course_id is not None:
            instance.course_id = course_id

        instance.title = validated_data.get("title", instance.title)
        instance.description = validated_data.get("description", instance.description)
        instance.save()
        return instance
