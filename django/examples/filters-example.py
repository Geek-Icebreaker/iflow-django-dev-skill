"""
Django REST Framework FilterSet 标准示例
"""
from django_filters import rest_framework as filters

from .models import Article, Trial


class ArticleFilter(filters.FilterSet):
    """
    Article 过滤器.

    支持的过滤字段:
    - status: 文章状态（精确匹配）
    - author: 作者ID（精确匹配）
    - created_after/created_before: 创建时间范围
    - title: 标题模糊搜索
    - tag: 标签（多对多）
    """

    # 基本字段过滤
    status = filters.ChoiceFilter(
        choices=[("draft", "草稿"), ("published", "已发布"), ("archived", "已归档")]
    )
    author = filters.NumberFilter(field_name="author_id")

    # 日期范围过滤
    created_after = filters.DateFilter(field_name="created_at", lookup_expr="gte")
    created_before = filters.DateFilter(field_name="created_at", lookup_expr="lte")

    # 文本模糊搜索
    title = filters.CharFilter(field_name="title", lookup_expr="icontains")

    # 关联字段过滤
    author_name = filters.CharFilter(
        field_name="author__username", lookup_expr="icontains"
    )

    # 多对多字段过滤
    tag = filters.CharFilter(field_name="tags__name", lookup_expr="iexact")

    class Meta:
        model = Article
        fields = ["status", "author", "created_after", "created_before"]


class TrialFilter(filters.FilterSet):
    """
    Trial 过滤器（复杂示例）.

    高级功能:
    - 数值范围过滤
    - 多选过滤
    - 自定义过滤方法
    - 排序
    """

    # 状态过滤（多选）
    status = filters.MultipleChoiceFilter(
        choices=[
            ("recruiting", "招募中"),
            ("active", "进行中"),
            ("completed", "已完成"),
        ]
    )

    # 数值范围过滤
    budget_min = filters.NumberFilter(field_name="budget", lookup_expr="gte")
    budget_max = filters.NumberFilter(field_name="budget", lookup_expr="lte")

    # 布尔过滤
    is_public = filters.BooleanFilter(field_name="is_public")

    # 日期范围（使用 DateFromToRangeFilter）
    created_date_range = filters.DateFromToRangeFilter(field_name="created_at")

    # 关联字段的复杂过滤
    pi_name = filters.CharFilter(
        field_name="principal_investigator__name", lookup_expr="icontains"
    )

    # 自定义过滤方法
    has_participants = filters.BooleanFilter(method="filter_has_participants")

    def filter_has_participants(self, queryset, name, value):
        """自定义过滤：是否有参与者."""
        if value:
            return queryset.filter(participants__isnull=False).distinct()
        return queryset.filter(participants__isnull=True)

    # 排序
    ordering = filters.OrderingFilter(
        fields=(
            ("created_at", "created_at"),
            ("updated_at", "updated_at"),
            ("budget", "budget"),
        )
    )

    class Meta:
        model = Trial
        fields = {
            "status": ["exact", "in"],
            "budget": ["gte", "lte", "exact"],
            "created_at": ["gte", "lte"],
        }


class AdvancedTrialFilter(filters.FilterSet):
    """
    高级过滤器示例.

    演示:
    - CharFilter 各种 lookup
    - DateFilter 组合
    - 自定义方法过滤
    """

    # 文本搜索（支持多种匹配方式）
    search = filters.CharFilter(method="filter_search")

    # 日期过滤（多种方式）
    created_year = filters.NumberFilter(field_name="created_at__year")
    created_month = filters.NumberFilter(field_name="created_at__month")

    # IN 查询
    status_in = filters.BaseInFilter(field_name="status")

    # 排除过滤
    exclude_status = filters.CharFilter(field_name="status", exclude=True)

    def filter_search(self, queryset, name, value):
        """
        全文搜索.

        搜索 title, description, principal_investigator__name
        """
        from django.db.models import Q

        return queryset.filter(
            Q(title__icontains=value)
            | Q(description__icontains=value)
            | Q(principal_investigator__name__icontains=value)
        )

    class Meta:
        model = Trial
        fields = []


# ============================================================================
# ViewSet 中使用 FilterSet
# ============================================================================


class ArticleViewSet:
    """ViewSet 中使用过滤器."""

    from rest_framework import viewsets
    from django_filters.rest_framework import DjangoFilterBackend

    queryset = Article.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = ArticleFilter  # 使用自定义 FilterSet

    # 或者简单字段过滤
    # filterset_fields = ['status', 'author']


# ============================================================================
# 使用示例
# ============================================================================

# API 请求示例:
# GET /api/articles/?status=published
# GET /api/articles/?author=1&created_after=2024-01-01
# GET /api/articles/?title=django&author_name=john
# GET /api/articles/?tag=python

# 复杂查询:
# GET /api/trials/?status=recruiting&status=active  # 多选
# GET /api/trials/?budget_min=10000&budget_max=50000  # 范围
# GET /api/trials/?created_date_range_after=2024-01-01&created_date_range_before=2024-12-31
# GET /api/trials/?has_participants=true
# GET /api/trials/?ordering=-created_at  # 排序

# 高级搜索:
# GET /api/trials/?search=cancer&status_in=recruiting,active
# GET /api/trials/?created_year=2024&created_month=1
# GET /api/trials/?exclude_status=completed
