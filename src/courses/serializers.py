from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Course

User = get_user_model()


class CourseMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email")


class CourseListSerializer(serializers.ModelSerializer):
    members_count = serializers.IntegerField(source="members.count", read_only=True)
    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Course
        fields = (
            "id",
            "title",
            "description",
            "image",
            "creator",
            "creator_code",
            "join_code",
            "members_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "creator",
            "join_code",
            "members_count",
            "created_at",
            "updated_at",
        )


class CourseDetailSerializer(serializers.ModelSerializer):
    members = CourseMemberSerializer(many=True, read_only=True)
    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Course
        fields = (
            "id",
            "title",
            "description",
            "image",
            "creator",
            "creator_code",
            "join_code",
            "members",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "creator",
            "join_code",
            "members",
            "created_at",
            "updated_at",
        )


class CourseCreateSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Course
        fields = ("title", "description", "creator_code", "image")

    def create(self, validated_data):
        request = self.context["request"]

        course = Course.objects.create(
            creator=request.user,
            **validated_data
        )

        course.members.add(request.user)
        return course


class CourseUpdateSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Course
        fields = ("title", "description", "creator_code", "image")


class CourseJoinSerializer(serializers.Serializer):
    code = serializers.CharField()

    def validate_code(self, value: str):
        value = value.strip().upper()
        if not value:
            raise serializers.ValidationError("Code is required.")
        return value


class CourseLeaveSerializer(serializers.Serializer):
    pass