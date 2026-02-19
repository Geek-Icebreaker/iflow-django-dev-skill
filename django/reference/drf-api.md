# Django REST Framework API 设计

> DRF 是 Django 生态中最流行的 API 框架,正确使用能大幅提升开发效率。

## 📦 基础配置

### 安装与配置

```bash
# 安装 DRF 及相关库
uv add djangorestframework django-filter djangorestframework-simplejwt
```

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'rest_framework',
    'django_filters',
]

REST_FRAMEWORK = {
    # 认证
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',  # 仅开发环境
    ],

    # 权限
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],

    # 分页（必须配置）
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,

    # 限流（必须配置）
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },

    # 过滤
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],

    # 渲染器（生产环境移除 BrowsableAPIRenderer）
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],

    # 异常处理
    'EXCEPTION_HANDLER': 'myapp.utils.custom_exception_handler',
}
```

---

## 🔧 Serializer 设计

### 1. 单 Serializer + 明确标记（推荐默认方案）

**✅ 大多数场景的最佳实践**：清晰、简洁、代码少

```python
from rest_framework import serializers

class TrialSerializer(serializers.ModelSerializer):
    # ✅ 只读字段：显示用，不能修改
    pi_name = serializers.CharField(source='principal_investigator.name', read_only=True)
    subject_count = serializers.IntegerField(read_only=True)

    # ✅ 只写字段：接收输入，不返回
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Trial
        fields = [
            'id', 'name', 'pi_name', 'budget',
            'status', 'subject_count', 'created_at'
        ]

        # ✅ 批量标记只读字段
        read_only_fields = ['id', 'created_at', 'subject_count']

        # ✅ 额外配置（可选）
        extra_kwargs = {
            'budget': {'min_value': 0},  # 验证规则
            'status': {'default': 'draft'},
        }

    def validate_budget(self, value):
        """字段级验证"""
        if value < 0:
            raise serializers.ValidationError('预算不能为负数')
        return value

    def validate(self, attrs):
        """跨字段验证"""
        if attrs.get('status') == 'active' and not attrs.get('principal_investigator'):
            raise serializers.ValidationError('激活的试验必须指定 PI')
        return attrs
```

**何时使用单 Serializer**：
- ✅ 简单 CRUD（标签、分类、配置项）
- ✅ 读写字段差异 < 50%
- ✅ 无复杂安全需求（无密码/权限字段）
- ✅ 团队偏好简洁代码

---

### 2. 读写完全分离（复杂场景）

**仅在以下情况使用**：
- 涉及敏感字段（密码、权限、is_staff）
- 读写字段集合差异 > 50%
- 嵌套序列化复杂（读取要嵌套对象，写入只要 ID）

```python
# 读取 Serializer：展示用，字段多
class UserReadSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    trial_count = serializers.IntegerField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'trial_count', 'last_login']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

# 写入 Serializer：操作用，字段少+验证严格
class UserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name']
        # ⚠️ is_staff/is_superuser 不在 fields 中，无法被篡改

    def validate_password(self, value):
        # 密码强度验证
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError('密码必须包含数字')
        return value

    def create(self, validated_data):
        # ✅ 安全的密码哈希
        return User.objects.create_user(**validated_data)
```

**在 ViewSet 中切换**：
```python
class UserViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UserWriteSerializer
        return UserReadSerializer
```

---

### 3. 嵌套序列化

**只读场景**：
```python
class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name', 'age']

class TrialDetailSerializer(serializers.ModelSerializer):
    subjects = SubjectSerializer(many=True, read_only=True)  # ✅ 嵌套只读

    class Meta:
        model = Trial
        fields = ['id', 'name', 'subjects']
```

**写场景**：
```python
class TrialCreateSerializer(serializers.ModelSerializer):
    # ✅ 写场景用 PrimaryKeyRelatedField
    subject_ids = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(),
        many=True,
        write_only=True
    )

    class Meta:
        model = Trial
        fields = ['name', 'subject_ids']

    def create(self, validated_data):
        subject_ids = validated_data.pop('subject_ids')
        trial = Trial.objects.create(**validated_data)
        trial.subjects.set(subject_ids)
        return trial
```

### 4. SerializerMethodField

```python
class TrialSerializer(serializers.ModelSerializer):
    # ✅ 计算字段
    days_since_created = serializers.SerializerMethodField()
    is_large_trial = serializers.SerializerMethodField()

    def get_days_since_created(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.created_at
        return delta.days

    def get_is_large_trial(self, obj):
        return obj.budget > 1000000

    class Meta:
        model = Trial
        fields = ['id', 'name', 'days_since_created', 'is_large_trial']
```

### 5. 性能优化

```python
# ❌ N+1 查询问题
class TrialSerializer(serializers.ModelSerializer):
    pi_name = serializers.CharField(source='principal_investigator.name')
    # 每个对象都会查询一次 principal_investigator

# ✅ 在 ViewSet 中预加载
class TrialViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return Trial.objects.select_related('principal_investigator')
```

---

## 🎯 ViewSet 设计

### 1. ViewSet 选择

```python
# 标准 CRUD
from rest_framework import viewsets

class TrialViewSet(viewsets.ModelViewSet):
    """完整的 CRUD 操作"""
    queryset = Trial.objects.all()
    serializer_class = TrialSerializer

# 只读 API
class TrialViewSet(viewsets.ReadOnlyModelViewSet):
    """只有 list 和 retrieve"""
    queryset = Trial.objects.all()
    serializer_class = TrialSerializer

# 自定义操作
from rest_framework import viewsets, mixins

class TrialViewSet(mixins.ListModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.CreateModelMixin,
                   viewsets.GenericViewSet):
    """只有 list, retrieve, create"""
    queryset = Trial.objects.all()
    serializer_class = TrialSerializer
```

### 2. get_queryset 与权限过滤

```python
class TrialViewSet(viewsets.ModelViewSet):
    serializer_class = TrialSerializer

    def get_queryset(self):
        """✅ 在这里实现权限过滤和预加载"""
        user = self.request.user

        # 权限过滤
        if user.is_staff:
            qs = Trial.objects.all()
        else:
            qs = Trial.objects.filter(principal_investigator=user)

        # 预加载关联对象
        qs = qs.select_related('principal_investigator')
        qs = qs.prefetch_related('subjects')

        # 添加计算字段
        qs = qs.annotate(subject_count=Count('subjects'))

        return qs
```

### 3. get_serializer_class

```python
class TrialViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        """✅ 根据操作返回不同的 Serializer"""
        if self.action in ['create', 'update', 'partial_update']:
            return TrialWriteSerializer
        elif self.action == 'retrieve':
            return TrialDetailSerializer
        return TrialListSerializer
```

### 4. 自定义 Action

```python
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

class TrialViewSet(viewsets.ModelViewSet):
    @action(detail=True, methods=['post'], permission_classes=[IsTrialManager])
    def enroll_subject(self, request, pk=None):
        """
        自定义操作：入组受试者
        POST /api/trials/{id}/enroll_subject/
        """
        trial = self.get_object()
        serializer = SubjectEnrollSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subject = serializer.save(trial=trial)

        return Response(
            SubjectSerializer(subject).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['get'])
    def my_trials(self, request):
        """
        列表级自定义操作
        GET /api/trials/my_trials/
        """
        trials = self.get_queryset().filter(
            principal_investigator=request.user
        )
        serializer = self.get_serializer(trials, many=True)
        return Response(serializer.data)
```

---

## 🔍 过滤、搜索、排序

### 1. FilterSet

```python
# filters.py
from django_filters import rest_framework as filters

class TrialFilter(filters.FilterSet):
    # 精确匹配
    status = filters.ChoiceFilter(choices=Trial.STATUS_CHOICES)

    # 范围过滤
    budget_min = filters.NumberFilter(field_name='budget', lookup_expr='gte')
    budget_max = filters.NumberFilter(field_name='budget', lookup_expr='lte')

    # 日期过滤
    created_after = filters.DateFilter(field_name='created_at', lookup_expr='gte')

    # 关联对象过滤
    pi_name = filters.CharFilter(field_name='principal_investigator__name', lookup_expr='icontains')

    class Meta:
        model = Trial
        fields = ['status', 'budget_min', 'budget_max', 'created_after', 'pi_name']

# ViewSet
class TrialViewSet(viewsets.ModelViewSet):
    queryset = Trial.objects.all()
    serializer_class = TrialSerializer
    filterset_class = TrialFilter
    search_fields = ['name', 'description']  # 全文搜索
    ordering_fields = ['created_at', 'budget']  # 允许排序的字段
    ordering = ['-created_at']  # 默认排序
```

**使用**：
```
GET /api/trials/?status=active&budget_min=100000&search=cancer&ordering=-budget
```

### 2. 简单过滤

```python
class TrialViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        qs = Trial.objects.all()

        # URL 参数过滤
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)

        pi_id = self.request.query_params.get('pi_id')
        if pi_id:
            qs = qs.filter(principal_investigator_id=pi_id)

        return qs
```

---

## 📄 分页

### 1. 标准分页

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

**响应格式**：
```json
{
    "count": 100,
    "next": "http://api.example.com/trials/?page=2",
    "previous": null,
    "results": [...]
}
```

### 2. 自定义分页

```python
# pagination.py
from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'  # 允许客户端指定
    max_page_size = 100

class TrialViewSet(viewsets.ModelViewSet):
    pagination_class = StandardResultsSetPagination
```

**使用**：
```
GET /api/trials/?page=2&page_size=50
```

### 3. 游标分页（大数据集）

```python
from rest_framework.pagination import CursorPagination

class TrialCursorPagination(CursorPagination):
    page_size = 20
    ordering = '-created_at'  # 必须指定

class TrialViewSet(viewsets.ModelViewSet):
    pagination_class = TrialCursorPagination
```

---

## 🚨 错误处理

### 统一异常处理

```python
# utils.py
from rest_framework.views import exception_handler
from rest_framework.response import Response

def custom_exception_handler(exc, context):
    # 调用 DRF 默认处理
    response = exception_handler(exc, context)

    if response is not None:
        # 统一错误格式
        custom_response_data = {
            'error': {
                'code': exc.default_code if hasattr(exc, 'default_code') else 'error',
                'message': str(exc),
                'details': response.data
            }
        }
        response.data = custom_response_data

    return response

# settings.py
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'myapp.utils.custom_exception_handler',
}
```

### 业务异常

```python
from rest_framework.exceptions import APIException

class TrialNotRecruitableException(APIException):
    status_code = 400
    default_detail = '试验不在招募阶段'
    default_code = 'trial_not_recruitable'

# 使用
class TrialViewSet(viewsets.ModelViewSet):
    @action(detail=True, methods=['post'])
    def enroll_subject(self, request, pk=None):
        trial = self.get_object()
        if trial.status != 'recruiting':
            raise TrialNotRecruitableException()
        # ...
```

---

## ✅ API 设计最佳实践

### 1. RESTful 规范

```python
# ✅ 正确的 URL 设计
GET    /api/trials/              # 列表
POST   /api/trials/              # 创建
GET    /api/trials/{id}/         # 详情
PUT    /api/trials/{id}/         # 完整更新
PATCH  /api/trials/{id}/         # 部分更新
DELETE /api/trials/{id}/         # 删除

POST   /api/trials/{id}/enroll_subject/  # 自定义操作

# ❌ 错误的 URL 设计
GET    /api/get_trials/          # 动词式
POST   /api/create_trial/        # 动词式
GET    /api/trials/list/         # 冗余
```

### 2. HTTP 状态码

```python
from rest_framework import status

class TrialViewSet(viewsets.ModelViewSet):
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trial = serializer.save()
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED  # ✅ 201 创建成功
        )

    def destroy(self, request, pk=None):
        trial = self.get_object()
        trial.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)  # ✅ 204 删除成功
```

### 3. 版本管理

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1', 'v2'],
}

# urls.py
urlpatterns = [
    path('api/v1/', include('myapp.urls_v1')),
    path('api/v2/', include('myapp.urls_v2')),
]

# ViewSet
class TrialViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        if self.request.version == 'v2':
            return TrialSerializerV2
        return TrialSerializerV1
```

---

## 📋 DRF 开发检查清单

- [ ] 配置了分页（避免返回所有数据）
- [ ] 配置了限流（防止滥用）
- [ ] 生产环境移除 BrowsableAPIRenderer
- [ ] Serializer 字段标记了 `read_only` 或 `write_only`（默认用单 Serializer）
- [ ] 复杂场景才用读写完全分离（User/敏感数据）
- [ ] 在 get_queryset 中预加载关联对象
- [ ] 明确指定 Serializer fields（不用 `__all__`）
- [ ] 自定义 action 指定了 permission_classes
- [ ] 使用 FilterSet 实现复杂过滤
- [ ] 统一异常处理格式
- [ ] API 遵循 RESTful 规范
- [ ] 正确使用 HTTP 状态码

**记住：简洁 > 过度设计。单 Serializer + 明确标记是 80% 场景的最佳选择。**
