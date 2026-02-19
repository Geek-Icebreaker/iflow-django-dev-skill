# Django Import-Export 导入导出

> 必须使用 django-import-export 库处理数据导入导出。

## 📦 安装与配置

```bash
uv add django-import-export
```

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'import_export',
]
```

---

## 🔧 Resource 定义

### 基础 Resource

```python
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Trial, User

class TrialResource(resources.ModelResource):
    # ✅ 自定义字段映射
    pi_name = fields.Field(
        column_name='principal_investigator',
        attribute='principal_investigator',
        widget=ForeignKeyWidget(User, 'name')
    )

    class Meta:
        model = Trial
        fields = ('id', 'name', 'pi_name', 'budget', 'status')
        export_order = ('id', 'name', 'pi_name', 'budget', 'status')

        # ✅ 导入选项
        skip_unchanged = True  # 跳过未变更的行
        report_skipped = True  # 报告跳过的行
        import_id_fields = ['id']  # 用于识别现有记录

        # ✅ 批量导入优化
        use_bulk = True
        batch_size = 500

    def before_import_row(self, row, **kwargs):
        """导入前验证"""
        if not row.get('name'):
            raise ValueError('试验名称不能为空')

    def after_import_row(self, row, row_result, **kwargs):
        """导入后处理"""
        pass

    def skip_row(self, instance, original):
        """自定义跳过逻辑"""
        # 跳过已完成的试验
        return instance.status == 'completed'
```

---

## 🎯 Admin 集成

```python
from import_export.admin import ImportExportModelAdmin, ImportExportMixin

@admin.register(Trial)
class TrialAdmin(ImportExportModelAdmin):
    resource_class = TrialResource
    list_display = ['name', 'status', 'budget']

    # ✅ 自定义导入表单
    def get_import_formats(self):
        from import_export.formats.base_formats import XLSX, CSV
        return [XLSX, CSV]
```

---

## 📥 View 中使用

### 导出

```python
from django.http import HttpResponse
from .resources import TrialResource

def export_trials(request):
    dataset = TrialResource().export()

    # Excel 格式
    response = HttpResponse(
        dataset.xlsx,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="trials.xlsx"'
    return response
```

### 导入

```python
from import_export.forms import ImportForm
from tablib import Dataset

def import_trials(request):
    if request.method == 'POST':
        file = request.FILES['import_file']
        dataset = Dataset()
        dataset.load(file.read(), format='xlsx')

        resource = TrialResource()
        result = resource.import_data(dataset, dry_run=True)  # 先测试

        if not result.has_errors():
            resource.import_data(dataset, dry_run=False)  # 真正导入
            return HttpResponse('导入成功')
        else:
            return HttpResponse(f'导入失败: {result.errors}')

    return render(request, 'import.html')
```

---

## 📋 检查清单

- [ ] 使用 django-import-export（不手写 CSV）
- [ ] 配置了 skip_unchanged
- [ ] 设置了 batch_size 优化性能
- [ ] 实现了 before_import_row 验证
- [ ] 使用 dry_run 测试导入

**记住：永远不要手写导入导出逻辑。**
