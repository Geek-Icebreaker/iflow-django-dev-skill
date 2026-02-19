# Django Admin 高级配置

> ⚠️ **优先使用代码生成器**：大部分 Model 应该使用 `code-generation.md` 中的 **ListAdminMixin 动态注册**，零配置自动推断所有字段。
>
> 本文档仅适用于以下场景：
> - 需要复杂自定义逻辑（自定义 Action、复杂权限控制）
> - 安全敏感的 Model（User、Permission 等）
> - 需要 Inline 编辑或特殊表单布局
> - 需要覆盖动态生成的配置

## 📊 何时手写 Admin

**✅ 需要手写的场景**：
- User/Permission 等核心 Model（安全考虑）
- 需要自定义 Action（批量操作、导出等）
- 需要 Inline 编辑（一对多/多对多关系）
- 需要复杂权限控制（对象级权限）
- 需要自定义表单验证

**❌ 不需要手写的场景**：
- 简单 CRUD Model → 用 ListAdminMixin
- 只需要调整字段顺序 → 在 `model_list_fields` 配置
- 只需要添加搜索字段 → 在 `addition_search_fields` 配置

## 📊 基础配置（手写方式）

### 注册 Model

```python
from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Trial
from .resources import TrialResource

# ✅ 完整配置
@admin.register(Trial)
class TrialAdmin(ImportExportModelAdmin):
    resource_class = TrialResource

    # 列表页显示字段
    list_display = ['name', 'status', 'principal_investigator', 'budget', 'subject_count', 'created_at']

    # 列表页过滤器
    list_filter = ['status', 'created_at', 'principal_investigator']

    # 搜索字段
    search_fields = ['name', 'code', 'principal_investigator__name']

    # 只读字段
    readonly_fields = ['created_at', 'updated_at', 'subject_count']

    # 每页显示数量
    list_per_page = 50

    # 排序
    ordering = ['-created_at']

    # 日期层级导航
    date_hierarchy = 'created_at'

    # 详情页字段分组
    fieldsets = [
        ('基本信息', {
            'fields': ['name', 'code', 'status']
        }),
        ('财务信息', {
            'fields': ['budget', 'actual_cost'],
            'classes': ['collapse']  # 可折叠
        }),
        ('时间信息', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    def subject_count(self, obj):
        """自定义列"""
        return obj.subjects.count()
    subject_count.short_description = '受试者数'

    def get_queryset(self, request):
        """优化查询"""
        qs = super().get_queryset(request)
        return qs.select_related('principal_investigator').annotate(
            subject_count=Count('subjects')
        )

# ❌ 简单注册（功能受限）
admin.site.register(Trial)
```

---

## 🎨 自定义操作

### Batch Actions

```python
@admin.register(Trial)
class TrialAdmin(admin.ModelAdmin):
    actions = ['make_active', 'export_selected']

    @admin.action(description='激活选中的试验')
    def make_active(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} 个试验已激活')

    def export_selected(self, request, queryset):
        """导出选中项"""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="trials.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'Name', 'Status', 'Budget'])

        for trial in queryset:
            writer.writerow([trial.id, trial.name, trial.status, trial.budget])

        return response
    export_selected.short_description = '导出选中项'
```

---

## 🔧 Inline 编辑

### TabularInline

```python
class SubjectInline(admin.TabularInline):
    model = Subject
    extra = 1  # 空白表单数量
    fields = ['name', 'age', 'gender', 'status']
    readonly_fields = ['created_at']
    can_delete = True

@admin.register(Trial)
class TrialAdmin(admin.ModelAdmin):
    inlines = [SubjectInline]
```

### StackedInline

```python
class MedicalRecordInline(admin.StackedInline):
    model = MedicalRecord
    extra = 0
    fieldsets = [
        ('基本信息', {'fields': ['diagnosis', 'notes']}),
        ('检查结果', {'fields': ['lab_results'], 'classes': ['collapse']}),
    ]
```

---

## 📋 Admin 检查清单

**优先级排序**：
1. [ ] 检查是否可用 ListAdminMixin（code-generation.md）
2. [ ] 如果需要手写，是否配置了 list_display
3. [ ] 如果需要手写，是否配置了 search_fields
4. [ ] 如果需要手写，是否配置了 list_filter
5. [ ] 是否使用 ImportExportModelAdmin
6. [ ] 在 get_queryset 中优化查询
7. [ ] 自定义列有 short_description
8. [ ] 时间字段设为 readonly

**记住：80% 的 Model 应该用动态生成（ListAdminMixin），只有 20% 需要手写。**
