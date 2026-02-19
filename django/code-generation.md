# Django 代码生成器最佳实践

> 通过代码生成器消除重复劳动，提升开发效率。

## 🎯 代码生成器架构

### 目录结构

```
tools/code_generator/
├── generate_all.py      # 统一入口
├── serializers.py       # 生成 Serializer
├── views.py             # 生成 ViewSet
├── filters.py           # 生成 Filter
├── admin.py             # 生成 Admin（可选）
└── common.py            # 共享配置
```

### 统一入口

```python
# tools/code_generator/generate_all.py
import os
import sys
import django

sys.path.append("../")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from tools.code_generator.filters import do_generate_filters
from tools.code_generator.serializers import do_generate_serializers
from tools.code_generator.views import do_generate_viewsets

if __name__ == '__main__':
    do_generate_filters()
    do_generate_serializers()
    do_generate_viewsets()
```

---

## 🔧 Serializer 生成器

### 核心实现

```python
# tools/code_generator/serializers.py
import black
from django.apps import apps

# 配置：嵌套序列化
embed_obj_serializer = {
    # Order: ["customer", "products"],  # 嵌入关联对象详情
}

serializer_template = """from rest_framework import serializers
from api.serializers.base import BaseSerializer
{import_content}


class {serializer_name}(BaseSerializer):
    '''
    AUTO-GENERATED - DO NOT EDIT
    Generated from tools.code_generator.serializers
    '''
    {custom_fields}

    class Meta:
        model = {model}
        fields = {fields}
        read_only_fields = {read_only_fields}
"""

def do_generate_serializers():
    for model in apps.get_models():
        if model in except_models:
            continue

        serializer_name = model.__name__ + 'Serializer'
        serializer_file = f"api/serializers/{model._meta.app_label}/{model.__name__}.py"

        # 自动推断字段
        fields = [f.name for f in model._meta.fields] + ["url"]
        read_only_fields = ["id", "created_at", "updated_at"]

        # 生成代码
        code = serializer_template.format(
            import_content=get_import_line(model),
            serializer_name=serializer_name,
            custom_fields="",
            model=model.__name__,
            fields=fields,
            read_only_fields=read_only_fields
        )

        # 格式化代码（✅ 关键实践）
        code = black.format_str(code, mode=black.FileMode())

        # 写入文件
        if not os.path.exists(serializer_file):
            with open(serializer_file, 'w') as f:
                f.write(code)
```

---

## 🌐 ViewSet 生成器

### 核心实现

```python
# tools/code_generator/views.py
viewset_template = """from api.views.base import BaseViewSet
{import_content}


class {viewset_name}(BaseViewSet):
    queryset = {queryset}
    serializer_class = {serializer_class}
    filterset_class = {filter_class}
    search_fields = {search_fields}
"""

def do_generate_viewsets():
    for model in apps.get_models():
        if model in except_models:
            continue

        # 自动推断 queryset
        queryset_str = f"{model.__name__}.objects"
        if hasattr(model, "is_show"):
            queryset_str += ".filter(is_show=True)"
        queryset_str += ".all()"

        # 自动推断搜索字段（✅ 关键实践）
        search_fields = []
        for field in model._meta.fields:
            if isinstance(field, (CharField, TextField)):
                search_fields.append(field.name)

        # 生成代码
        code = viewset_template.format(
            import_content=get_imports(model),
            viewset_name=model.__name__ + 'ViewSet',
            queryset=queryset_str,
            serializer_class=model.__name__ + 'Serializer',
            filter_class=model.__name__ + 'Filter',
            search_fields=search_fields
        )

        code = black.format_str(code, mode=black.FileMode())

        # 写入文件
        viewset_file = f"api/views/{model._meta.app_label}/{model.__name__}.py"
        if not os.path.exists(viewset_file):
            with open(viewset_file, 'w') as f:
                f.write(code)
```

---

## 🎨 Admin 动态注册（推荐默认方案）

> ✅ **这是 Admin 配置的默认方案**：零配置，自动推断所有字段。
>
> 手写 Admin 配置（`admin-config.md`）仅适用于：User/Permission 等安全敏感 Model、需要复杂自定义逻辑的场景。

### ListAdminMixin（✅ 核心实践）

```python
# utils/admin.py
from django.contrib import admin
from django.apps import apps
from import_export.admin import ExportActionModelAdmin

class ListAdminMixin:
    """
    零配置 Admin：自动推断 list_display/search_fields/list_filter
    """
    def __init__(self, model, admin_site):
        # ✅ 自动推断 list_display
        except_fields = ["id", "created_at", "updated_at"]
        self.list_display = [
            field.name for field in model._meta.fields
            if field.name not in except_fields
        ]

        # ✅ 自动推断 search_fields
        self.search_fields = [
            field.name for field in model._meta.fields
            if isinstance(field, (CharField, TextField, EmailField))
        ]

        # ✅ 自动推断 autocomplete_fields
        self.autocomplete_fields = [
            field.name for field in model._meta.fields
            if isinstance(field, ForeignKey)
        ]

        # ✅ 自动推断 list_filter
        self.list_filter = []
        for field in model._meta.fields:
            if isinstance(field, BooleanField):
                self.list_filter.append(field.name)
            elif isinstance(field, DateTimeField):
                self.list_filter.append((field.name, DateTimeRangeFilter))

        # ✅ 自动设置 readonly_fields
        self.readonly_fields = ["creator", "editor", "created_at", "updated_at"]

        super().__init__(model, admin_site)

    def save_model(self, request, obj, form, change):
        """自动记录创建人和修改人"""
        if not change:  # 新增
            obj.creator = request.user
        else:  # 修改
            obj.editor = request.user
        super().save_model(request, obj, form, change)

# ✅ 批量注册
for model in apps.get_models():
    if model not in except_models:
        admin_class = type('AdminClass', (ListAdminMixin, ExportActionModelAdmin), {})
        admin.site.register(model, admin_class)
```

### 自定义覆盖

```python
# 配置：自定义 list_display
model_list_fields = {
    Order: ["id", "customer", "order_number", "created_at"],
    Product: ["id", "name", "price", "stock"],
}

# 配置：额外搜索字段（关联字段）
addition_search_fields = {
    Order: ["customer__name", "customer__phone"],
    Product: ["category__name"],
}

# 配置：排除自动注册的Model(重要)
except_models = [
    User,  # 使用自定义Admin
    Session,  # Django内置,无需管理
    LogEntry,  # 日志表,只读
    ContentType,  # Django内置
    Permission,  # 权限表,不要动态注册
]

class ListAdminMixin:
    def __init__(self, model, admin_site):
        # 检查是否在排除列表
        if model in except_models:
            return super().__init__(model, admin_site)

        # 使用自定义配置（如果有）
        if model in model_list_fields:
            self.list_display = model_list_fields[model]
        else:
            # 自动推断
            self.list_display = [...]

        # 合并额外搜索字段
        if model in addition_search_fields:
            self.search_fields.extend(addition_search_fields[model])
```

---

## 🔑 代码生成器关键实践

### 1. 使用 Black 自动格式化

```python
import black

code = generate_code(model)
formatted_code = black.format_str(code, mode=black.FileMode())

with open(output_file, 'w') as f:
    f.write(formatted_code)
```

### 2. 添加生成标记

```python
code_template = """
# AUTO-GENERATED - DO NOT EDIT
# Generated at: {timestamp}
# Generator: tools.code_generator.serializers

from rest_framework import serializers
...
"""
```

### 2.5. 安全:排除敏感字段(重要)

```python
# ⚠️ 安全警告:绝对不要在Serializer中使用 fields = '__all__'
# 原因:可能暴露敏感字段(password_hash, is_staff, is_superuser等)

# ✅ 正确做法:自动推断字段并排除敏感字段
SENSITIVE_FIELDS = {
    'password', 'password_hash', 'is_superuser', 'is_staff',
    'user_permissions', 'groups', 'last_login'
}

def get_safe_fields(model):
    """获取安全的字段列表"""
    all_fields = [f.name for f in model._meta.fields]
    # 排除敏感字段
    safe_fields = [f for f in all_fields if f not in SENSITIVE_FIELDS]
    return safe_fields

# 生成器中使用
fields = get_safe_fields(model)
code = serializer_template.format(
    model=model.__name__,
    fields=fields,  # ✅ 明确列出安全字段
    ...
)
```

### 3. 检测文件是否被修改

```python
import hashlib

def file_was_modified(filepath):
    """检查文件是否被手动修改"""
    with open(filepath, 'r') as f:
        content = f.read()

    # 检查是否有生成标记
    if "AUTO-GENERATED" not in content:
        return True

    # 检查 hash（可选）
    if "# Hash:" in content:
        stored_hash = content.split("# Hash:")[1].split("\n")[0].strip()
        current_hash = hashlib.md5(content.encode()).hexdigest()
        return stored_hash != current_hash

    return False

# 使用
if not os.path.exists(filepath) or not file_was_modified(filepath):
    generate_code(filepath)
else:
    print(f"⚠️ {filepath} has been manually modified. Skipping...")
```

### 4. 配置驱动生成

```python
# common.py
except_models = [User, Session, LogEntry]  # 不生成的 Model

embed_obj_serializer = {
    Order: ["customer", "products"],  # 嵌套序列化
}

model_list_fields = {
    Order: ["id", "order_number", "customer", "created_at"],  # 自定义字段
}

# 所有生成器共享这些配置
```

---

## 📋 代码生成器使用清单

- [ ] 使用 `black` 自动格式化生成的代码
- [ ] 添加 `AUTO-GENERATED` 标记
- [ ] **排除敏感字段(password, is_superuser等)** ⚠️
- [ ] **明确列出fields,不使用`__all__`** ⚠️
- [ ] 检测文件是否被手动修改
- [ ] 配置文件集中管理（`common.py`）
- [ ] 自动推断常用字段（`search_fields`/`list_display`）
- [ ] 支持自定义覆盖（不是全自动）
- [ ] 生成的代码包含注释说明
- [ ] 使用模板而不是字符串拼接

**记住：代码生成器是提效工具，不是银弹。复杂逻辑仍需手写。安全性永远是第一位。**
