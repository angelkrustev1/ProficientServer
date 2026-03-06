from rest_framework import serializers

from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    author_id = serializers.IntegerField(source="author.id", read_only=True)
    author_email = serializers.EmailField(source="author.email", read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    liked_by_me = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "course",
            "author_id",
            "author_email",
            "content",
            "created_at",
            "updated_at",
            "likes_count",
            "liked_by_me",
        ]
        read_only_fields = [
            "id",
            "course",
            "author_id",
            "author_email",
            "created_at",
            "updated_at",
            "likes_count",
            "liked_by_me",
        ]

    def get_liked_by_me(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        return obj.likes.filter(user=request.user).exists()


class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["content"]

    def create(self, validated_data):
        request = self.context["request"]
        course = self.context["course"]

        return Message.objects.create(
            course=course,
            author=request.user,
            **validated_data,
        )
