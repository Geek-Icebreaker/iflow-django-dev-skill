"""
Django REST Framework ViewSet 标准示例
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import Article
from .serializers import ArticleSerializer, ArticleDetailSerializer


class ArticleViewSet(viewsets.ModelViewSet):
    """
    Article CRUD API.

    list: 获取文章列表
    retrieve: 获取文章详情
    create: 创建文章
    update: 更新文章
    partial_update: 部分更新文章
    destroy: 删除文章
    """

    queryset = Article.objects.select_related("author").prefetch_related("tags")
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "author"]
    search_fields = ["title", "content"]
    ordering_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        """根据 action 返回不同的 serializer."""
        if self.action == "retrieve":
            return ArticleDetailSerializer
        return ArticleSerializer

    def get_queryset(self):
        """根据用户权限过滤 queryset."""
        queryset = super().get_queryset()

        # 普通用户只能看到已发布的文章
        if not self.request.user.is_staff:
            queryset = queryset.filter(status="published")

        return queryset

    def perform_create(self, serializer):
        """创建时自动设置作者."""
        serializer.save(author=self.request.user)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """发布文章."""
        article = self.get_object()

        if article.status == "published":
            return Response(
                {"detail": "文章已发布"},
                status=status.HTTP_400_BAD_REQUEST
            )

        article.status = "published"
        article.save(update_fields=["status"])

        serializer = self.get_serializer(article)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def my_articles(self, request):
        """获取当前用户的文章."""
        articles = self.get_queryset().filter(author=request.user)

        page = self.paginate_queryset(articles)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(articles, many=True)
        return Response(serializer.data)
