# Django 安全检查清单

> 安全问题是 Django 开发中最容易被忽视但后果最严重的部分。

## 🔐 认证与授权

### 1. 认证系统

**✅ 推荐做法**：
```python
# 使用 Django 内置认证
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login

# 或使用成熟的第三方库
# JWT 认证
from rest_framework_simplejwt.tokens import RefreshToken

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

# OAuth2 认证
# pip install django-allauth
INSTALLED_APPS += ['allauth', 'allauth.account', 'allauth.socialaccount']
```

**❌ 绝对禁止**：
```python
# ❌ 自己实现密码哈希
import hashlib
password_hash = hashlib.md5(password.encode()).hexdigest()  # 不安全！

# ❌ 自己实现 Token 生成
import random
token = str(random.randint(1000, 9999))  # 可预测！

# ❌ 在 URL 中传递密码
/api/login/?username=admin&password=123456  # 泄露！
```

### 2. 权限控制

**对象级权限**：
```python
# 安装 django-guardian
# uv add django-guardian

from guardian.shortcuts import assign_perm, get_objects_for_user

# 分配权限
assign_perm('view_trial', user, trial)
assign_perm('change_trial', user, trial)

# 检查权限
if user.has_perm('view_trial', trial):
    # 允许访问
    pass

# 在 ViewSet 中使用
from rest_framework import viewsets
from guardian.shortcuts import get_objects_for_user

class TrialViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        # ✅ 只返回用户有权限查看的对象
        return get_objects_for_user(
            self.request.user,
            'myapp.view_trial',
            Trial
        )
```

**DRF 权限类**：
```python
from rest_framework import permissions

class IsTrialManagerOrReadOnly(permissions.BasePermission):
    """
    试验管理员可以修改，其他人只读
    """
    def has_object_permission(self, request, view, obj):
        # 读取权限允许任何请求
        if request.method in permissions.SAFE_METHODS:
            return True

        # 写权限只给试验管理员
        return obj.principal_investigator == request.user

class TrialViewSet(viewsets.ModelViewSet):
    permission_classes = [IsTrialManagerOrReadOnly]
```

### 3. 常见权限陷阱

**❌ 只在 View 层检查权限**：
```python
# ❌ 错误：View 层检查，但直接查询可绕过
class TrialViewSet(viewsets.ModelViewSet):
    queryset = Trial.objects.all()  # 返回所有数据！

    def list(self, request):
        if not request.user.is_staff:
            raise PermissionDenied
        # 但 queryset 已经暴露了所有数据
```

**✅ 在 QuerySet 层过滤**：
```python
class TrialViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        # ✅ 在数据层过滤
        user = self.request.user
        if user.is_staff:
            return Trial.objects.all()
        return Trial.objects.filter(principal_investigator=user)
```

---

## 🛡️ 数据保护

### 1. SQL 注入防护

**✅ 使用 ORM 参数化查询**：
```python
# ✅ 安全：ORM 自动参数化
trials = Trial.objects.filter(name=user_input)

# ✅ 安全：使用占位符
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT * FROM trials WHERE name = %s", [user_input])
```

**❌ 字符串拼接**：
```python
# ❌ SQL 注入漏洞！
query = f"SELECT * FROM trials WHERE name = '{user_input}'"
cursor.execute(query)

# 攻击示例：
# user_input = "' OR '1'='1"
# 结果查询：SELECT * FROM trials WHERE name = '' OR '1'='1'
# 返回所有数据！
```

**Raw SQL 的安全使用**：
```python
# ✅ 使用 %s 占位符
Trial.objects.raw(
    "SELECT * FROM trials WHERE name = %s",
    [user_input]
)

# ❌ 不要用 f-string
Trial.objects.raw(f"SELECT * FROM trials WHERE name = '{user_input}'")
```

### 2. XSS 防护

**Django 模板自动转义**：
```django
{# ✅ 自动转义 #}
<p>{{ user_input }}</p>

{# ❌ 禁用转义（危险！） #}
<p>{{ user_input|safe }}</p>

{# ✅ 只在确认安全时禁用 #}
{% autoescape off %}
    {{ trusted_html }}
{% endautoescape %}
```

**DRF 自动安全**：
```python
# ✅ DRF 返回 JSON，天然防 XSS
class TrialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trial
        fields = ['name', 'description']

# 但要注意富文本字段
class TrialSerializer(serializers.ModelSerializer):
    description_html = serializers.SerializerMethodField()

    def get_description_html(self, obj):
        # ✅ 清理 HTML
        import bleach
        allowed_tags = ['p', 'br', 'strong', 'em']
        return bleach.clean(obj.description, tags=allowed_tags)
```

### 3. CSRF 保护

**Session 认证必须启用 CSRF**：
```python
# settings.py
MIDDLEWARE = [
    # ...
    'django.middleware.csrf.CsrfViewMiddleware',  # ✅ 必须
]

# View 中
from django.views.decorators.csrf import csrf_protect

@csrf_protect
def my_view(request):
    # ...
    pass
```

**API 场景**：
```python
# JWT 认证不需要 CSRF（无状态）
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}

# 但要防重放攻击
from rest_framework_simplejwt.settings import api_settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),  # 短期 Token
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,  # 刷新时轮换 Token
}
```

**CORS 配置**：
```python
# uv add django-cors-headers
INSTALLED_APPS += ['corsheaders']

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # ✅ 在最前面
    # ...
]

# ✅ 生产环境：明确允许的域名
CORS_ALLOWED_ORIGINS = [
    "https://example.com",
    "https://app.example.com",
]

# ❌ 不要在生产环境使用
CORS_ALLOW_ALL_ORIGINS = True  # 危险！
```

---

## 🔒 敏感数据处理

### 1. 密码存储

**✅ Django 自动安全存储**：
```python
from django.contrib.auth.models import User

# ✅ 自动使用 PBKDF2 哈希
user = User.objects.create_user(
    username='john',
    password='secret123'
)

# ✅ 验证密码
user.check_password('secret123')  # True
```

**自定义密码哈希**：
```python
# settings.py
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',  # 推荐
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]
```

### 2. 环境变量管理

**✅ 使用 django-environ**：
```python
# uv add django-environ

# settings.py
import environ
env = environ.Env(
    DEBUG=(bool, False)
)
environ.Env.read_env()  # 读取 .env 文件

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
DATABASE_URL = env('DATABASE_URL')

DATABASES = {
    'default': env.db()
}
```

**.env 文件**：
```bash
# .env
SECRET_KEY=your-secret-key-here
DEBUG=False
DATABASE_URL=postgresql://user:pass@localhost/dbname
```

**.gitignore**：
```
# ✅ 永远不要提交
.env
local_settings.py
*.sqlite3
```

**.env.example**（提交到版本控制）：
```bash
# .env.example
SECRET_KEY=change-me
DEBUG=False
DATABASE_URL=postgresql://user:pass@localhost/dbname
```

### 3. 敏感字段加密

**使用 django-cryptography**：
```python
# uv add django-cryptography

from django_cryptography.fields import encrypt

class Patient(models.Model):
    name = models.CharField(max_length=100)
    # ✅ 加密存储身份证号
    id_number = encrypt(models.CharField(max_length=18))
    # ✅ 加密存储病历
    medical_record = encrypt(models.TextField())
```

**日志中排除敏感信息**：
```python
import logging

logger = logging.getLogger(__name__)

# ❌ 错误：记录密码
logger.info(f"User {username} login with password {password}")

# ✅ 正确：不记录敏感信息
logger.info(f"User {username} login successful")

# ✅ 使用过滤器
class SensitiveDataFilter(logging.Filter):
    def filter(self, record):
        # 移除敏感字段
        if hasattr(record, 'password'):
            record.password = '***'
        return True
```

---

## 🚨 生产环境安全配置

### 必须配置的安全设置

```python
# settings/production.py

# ✅ 关闭调试模式
DEBUG = False

# ✅ 设置允许的主机
ALLOWED_HOSTS = [
    '.example.com',
    'api.example.com',
]

# ✅ HTTPS 强制
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ✅ HSTS
SECURE_HSTS_SECONDS = 31536000  # 1 年
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ✅ 其他安全头
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# ✅ Cookie 安全
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_SAMESITE = 'Strict'
```

### 部署前安全检查

```bash
# ✅ 运行安全检查
python manage.py check --deploy

# 示例输出：
# System check identified some issues:
# WARNINGS:
# ?: (security.W004) You have not set a value for the SECURE_HSTS_SECONDS setting.
# ?: (security.W008) Your SECURE_SSL_REDIRECT setting is not set to True.
```

---

## 🔍 常见安全漏洞检查

### 1. 未授权访问

**❌ 漏洞示例**：
```python
# ❌ 任何人都可以删除试验
class TrialViewSet(viewsets.ModelViewSet):
    queryset = Trial.objects.all()
    # 缺少权限检查！
```

**✅ 修复**：
```python
class TrialViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsTrialManager]

    def get_queryset(self):
        return Trial.objects.filter(
            principal_investigator=self.request.user
        )
```

### 2. 敏感信息泄露

**❌ 漏洞示例**：
```python
# ❌ 返回所有用户字段（包括密码哈希）
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'  # 危险！可能暴露 password_hash, is_superuser 等
```

**✅ 修复**：
```python
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        # 明确指定字段，不使用 __all__

# ⚠️ 绝对禁止在 Serializer fields 中包含的敏感字段
SENSITIVE_FIELDS = [
    'password', 'password_hash', 'is_superuser', 'is_staff',
    'user_permissions', 'groups', 'last_login'
]
```

**🔧 代码生成器安全措施**：
如果使用代码生成器自动生成 Serializer（详见 `code-generation.md`）:
1. **必须**自动排除敏感字段
2. **禁止**使用 `fields = '__all__'`
3. 生成器应该明确列出所有字段
4. 特别注意 User、Permission 等权限相关 Model

### 3. 批量赋值

**❌ 漏洞示例**：
```python
# ❌ 用户可以修改任何字段
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'is_staff', 'is_superuser']

# 攻击：POST /api/users/ {"username": "hacker", "is_superuser": true}
```

**✅ 修复**：
```python
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email']
        read_only_fields = ['is_staff', 'is_superuser']  # ✅ 只读
```

### 4. 文件上传

**✅ 安全的文件上传**：
```python
from django.core.validators import FileExtensionValidator

class Document(models.Model):
    file = models.FileField(
        upload_to='documents/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'doc', 'docx']
            )
        ]
    )

    def save(self, *args, **kwargs):
        # ✅ 验证文件大小
        if self.file.size > 10 * 1024 * 1024:  # 10MB
            raise ValidationError('文件大小不能超过 10MB')

        # ✅ 验证文件类型（不仅看扩展名）
        import magic
        file_type = magic.from_buffer(self.file.read(1024), mime=True)
        if file_type not in ['application/pdf', 'application/msword']:
            raise ValidationError('不支持的文件类型')

        super().save(*args, **kwargs)
```

---

## 📋 安全检查清单

开发完成后，逐项检查：

- [ ] 使用 Django 内置认证或成熟的第三方库
- [ ] 所有 API 端点都有权限检查
- [ ] QuerySet 在数据层过滤（不只在 View 层）
- [ ] 没有 SQL 注入风险（使用 ORM 或参数化查询）
- [ ] 富文本字段经过 HTML 清理
- [ ] CSRF 保护已启用（Session 认证）
- [ ] CORS 配置正确（生产环境不使用 ALLOW_ALL）
- [ ] 密码使用 Django 内置哈希
- [ ] 敏感信息用环境变量管理
- [ ] `.env` 文件不在版本控制中
- [ ] 生产环境 `DEBUG = False`
- [ ] `ALLOWED_HOSTS` 明确指定
- [ ] HTTPS 强制重定向
- [ ] 安全头已配置（HSTS, X-Frame-Options 等）
- [ ] 文件上传有类型和大小限制
- [ ] 敏感字段加密存储
- [ ] 日志不包含密码等敏感信息
- [ ] 运行 `python manage.py check --deploy` 无警告

---

**记住：安全不是可选项，而是必需品。每个检查点都要认真对待。**
