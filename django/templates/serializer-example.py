"""
Django REST Framework Serializer 标准示例
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Article, Tag

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    """Tag serializer."""

    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]
        read_only_fields = ["slug"]


class UserSimpleSerializer(serializers.ModelSerializer):
    """简化的用户信息 serializer."""

    class Meta:
        model = User
        fields = ["id", "username", "email"]
        read_only_fields = ["id", "username", "email"]


class ArticleSerializer(serializers.ModelSerializer):
    """
    Article serializer for list/create.

    用于列表和创建操作，包含基本字段。
    """

    author = UserSimpleSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=Tag.objects.all(),
        source="tags"
    )

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "summary",
            "status",
            "author",
            "tags",
            "tag_ids",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "author", "created_at", "updated_at"]

    def validate_title(self, value: str) -> str:
        """验证标题."""
        if len(value) < 5:
            raise serializers.ValidationError("标题至少 5 个字符")
        return value

    def validate(self, attrs: dict) -> dict:
        """跨字段验证."""
        # 示例：草稿状态不需要 summary
        if attrs.get("status") == "published" and not attrs.get("summary"):
            raise serializers.ValidationError({
                "summary": "发布文章必须提供摘要"
            })
        return attrs


class ArticleDetailSerializer(ArticleSerializer):
    """
    Article detail serializer.

    用于详情操作，包含完整字段。
    """

    content = serializers.CharField()
    comments_count = serializers.IntegerField(read_only=True)

    class Meta(ArticleSerializer.Meta):
        fields = ArticleSerializer.Meta.fields + [
            "content",
            "comments_count",
        ]


class ArticleCreateSerializer(serializers.ModelSerializer):
    """
    Article create serializer with nested tags.

    支持嵌套创建 tags。
    """

    tags = TagSerializer(many=True)

    class Meta:
        model = Article
        fields = ["title", "content", "summary", "status", "tags"]

    def create(self, validated_data: dict) -> Article:
        """创建文章并处理嵌套的 tags."""
        tags_data = validated_data.pop("tags", [])

        # 创建文章
        article = Article.objects.create(**validated_data)

        # 创建或获取 tags
        for tag_data in tags_data:
            tag, _ = Tag.objects.get_or_create(**tag_data)
            article.tags.add(tag)

        return article

    def update(self, instance: Article, validated_data: dict) -> Article:
        """更新文章并处理嵌套的 tags."""
        tags_data = validated_data.pop("tags", None)

        # 更新基本字段
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # 更新 tags
        if tags_data is not None:
            instance.tags.clear()
            for tag_data in tags_data:
                tag, _ = Tag.objects.get_or_create(**tag_data)
                instance.tags.add(tag)

        return instance
