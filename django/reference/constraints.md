# Django 开发硬性约束

> 这些规则**不可协商**，违反将导致严重问题。

## 🚫 绝对禁止

### 1. 缓存层（除非明确要求）

**规则**：除非用户明确要求，不要主动添加缓存层。

**原因**：
- 增加系统复杂度
- 引入缓存一致性问题
- 过早优化

**正确做法**：
```python
# ❌ 错误：主动添加缓存
def get_trials(request):
    cache_key = 'all_trials'
    trials = cache.get(cache_key)
    if not trials:
        trials = Trial.objects.all()
        cache.set(cache_key, trials, 300)
    return trials

# ✅ 正确：简单查询
def get_trials(request):
    return Trial.objects.all()

# ✅ 只在性能瓶颈确认后，经用户同意再添加
# 用户说："查询太慢，加个缓存"
def get_trials(request):
    cache_key = 'all_trials'
    trials = cache.get(cache_key)
    if not trials:
        trials = Trial.objects.all()
        cache.set(cache_key, trials, 300)
    return trials
```

---

### 2. Migration 文件（永远不要手写）

**规则**：必须使用 `python manage.py makemigrations` 生成。

**原因**：
- 手写易出错（依赖关系、字段类型）
- 破坏 Django 的迁移系统
- 导致无法回滚

**正确做法**：
```bash
# ✅ 正确流程
# 1. 修改 models.py
class Trial(models.Model):
    name = models.CharField(max_length=200)
    # 添加新字段
    budget = models.DecimalField(max_digits=12, decimal_places=2)

# 2. 生成 migration
python manage.py makemigrations

# 3. 检查生成的文件
cat <app>/migrations/0002_trial_budget.py

# 4. 应用迁移
python manage.py migrate

# ❌ 绝对禁止手动创建
# touch myapp/migrations/0002_add_budget.py
```

**如果 migration 有问题**：
```bash
# ✅ 正确做法：创建新 migration 修正
python manage.py makemigrations --empty <app> -n fix_budget_field

# 然后在新 migration 中修正
class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0002_trial_budget'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trial',
            name='budget',
            field=models.DecimalField(max_digits=15, decimal_places=2),
        ),
    ]

# ❌ 错误做法：直接修改已应用的 migration
```

**已应用的 migration 处理**：
```bash
# 检查哪些 migration 已应用
python manage.py showmigrations

# 如果已经 migrate，绝对不要修改该文件
# 应该：
# 1. 回滚到之前版本
python manage.py migrate <app> <previous_migration_name>
# 2. 删除错误的 migration 文件
# 3. 重新生成
python manage.py makemigrations
```

---

### 3. Django 命令生成的代码（禁止手写）

**规则**：Django 能生成的代码，必须用命令生成。

**必须用命令的场景**：

```bash
# ✅ 创建项目
python manage.py startproject myproject
# ❌ mkdir myproject && touch settings.py  # 错误！

# ✅ 创建应用
python manage.py startapp trials
# ❌ mkdir trials && touch models.py  # 错误！

# ✅ 生成 migration
python manage.py makemigrations
# ❌ 手写 0001_initial.py  # 错误！

# ✅ 创建超级用户
python manage.py createsuperuser
# ❌ User.objects.create_superuser(...)  # 在脚本中可以，但优先用命令

# ✅ 收集静态文件
python manage.py collectstatic
# ❌ cp -r static/* staticfiles/  # 错误！

# ✅ 生成翻译文件
python manage.py makemessages -l zh_Hans
# ❌ 手写 .po 文件  # 错误！

# ✅ 创建自定义管理命令
python manage.py startapp myapp
# 然后在 myapp/management/commands/ 创建
# ❌ 直接写 Python 脚本  # 应该用管理命令框架
```

**自定义管理命令模板**：
```python
# myapp/management/commands/import_data.py
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = '导入数据'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str)

    def handle(self, *args, **options):
        file_path = options['file']
        self.stdout.write(f'导入文件: {file_path}')
        # 业务逻辑
```

---

### 4. 导入导出（必须用 django-import-export）

**规则**：所有数据导入导出必须使用 `django-import-export` 库。

**原因**：
- 手写 CSV/Excel 处理容易出错
- 缺少验证和错误处理
- 重复造轮子

**安装**：
```bash
uv add django-import-export
```

**配置**：
```python
# settings.py
INSTALLED_APPS = [
    # ...
    'import_export',
]
```

**正确做法**：
```python
# ✅ 使用 django-import-export
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin

class TrialResource(resources.ModelResource):
    # 自定义字段映射
    pi_name = fields.Field(
        column_name='principal_investigator',
        attribute='principal_investigator__name'
    )

    class Meta:
        model = Trial
        skip_unchanged = True  # 跳过未变更的行
        report_skipped = True  # 报告跳过的行
        fields = ('id', 'name', 'pi_name', 'budget', 'status')
        export_order = ('id', 'name', 'pi_name', 'budget', 'status')

    def before_import_row(self, row, **kwargs):
        """导入前验证"""
        if not row.get('name'):
            raise ValueError('试验名称不能为空')

@admin.register(Trial)
class TrialAdmin(ImportExportModelAdmin):
    resource_class = TrialResource
    list_display = ['name', 'budget', 'status']

# ❌ 错误：手写 CSV 处理
import csv
def export_trials(request):
    response = HttpResponse(content_type='text/csv')
    writer = csv.writer(response)
    writer.writerow(['ID', 'Name', 'Budget'])
    for trial in Trial.objects.all():
        writer.writerow([trial.id, trial.name, trial.budget])
    return response
```

**批量导入优化**：
```python
class TrialResource(resources.ModelResource):
    class Meta:
        model = Trial
        use_bulk = True  # 使用 bulk_create
        batch_size = 500  # 每批 500 条
```

**在 View 中使用**：
```python
from import_export.formats.base_formats import XLSX

def export_trials(request):
    dataset = TrialResource().export()
    response = HttpResponse(
        dataset.xlsx,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="trials.xlsx"'
    return response
```

---

### 5. 最小开发单元原则

**规则**：以最小可测试、可运行的单元进行开发。

**原因**：
- 降低出错风险
- 快速验证反馈
- 便于定位问题

**正确做法**：

**场景 1：添加新功能**
```python
# ❌ 错误：一次写完所有代码
# 同时写：Model + Serializer + ViewSet + URL + Test + Admin
# 写了 500 行代码，运行测试才发现 Model 设计有问题

# ✅ 正确：分步实现
# 步骤 1：Model + Migration（最小单元）
class Trial(models.Model):
    name = models.CharField(max_length=200)

# 生成并应用 migration
python manage.py makemigrations
python manage.py migrate

# 步骤 2：测试 Model
python manage.py shell_plus
>>> trial = Trial.objects.create(name="Test")
>>> trial.name  # 验证工作

# 步骤 3：Serializer
class TrialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trial
        fields = ['id', 'name']

# 步骤 4：简单测试
python manage.py shell_plus
>>> from myapp.serializers import TrialSerializer
>>> serializer = TrialSerializer(trial)
>>> serializer.data  # 验证序列化

# 步骤 5：ViewSet
# 步骤 6：URL
# 步骤 7：单元测试
# 步骤 8：集成测试
```

**场景 2：优化查询**
```python
# ❌ 错误：一次优化所有查询
# 同时优化 10 个 View 的查询，改了 50 处代码

# ✅ 正确：一次优化一个查询
# 1. 找到最慢的查询
from django.db import connection
from django.test.utils import override_settings

@override_settings(DEBUG=True)
def test_query():
    connection.queries = []
    trials = list(Trial.objects.all())
    print(len(connection.queries))  # 查询次数

# 2. 优化这一个查询
trials = Trial.objects.select_related('principal_investigator')

# 3. 验证优化效果
print(len(connection.queries))  # 应该减少

# 4. 提交
# 5. 继续下一个查询
```

**小步提交**：
```bash
# ✅ 正确的提交节奏
git add models.py migrations/
git commit -m "feat: add Trial model"

git add serializers.py
git commit -m "feat: add Trial serializer"

git add views.py urls.py
git commit -m "feat: add Trial API endpoint"

git add tests/
git commit -m "test: add Trial API tests"

# ❌ 错误：累积大量代码再提交
git add .
git commit -m "add trial feature"  # 包含 20 个文件，500 行代码
```

---

## ✅ 必须遵守的工作流

### Migration 工作流

```bash
# 1. 修改 Model
vim myapp/models.py

# 2. 生成 migration
python manage.py makemigrations

# 3. 检查生成的 migration
cat myapp/migrations/0002_*.py

# 4. 测试 migration（在开发环境）
python manage.py migrate

# 5. 测试回滚
python manage.py migrate myapp 0001

# 6. 重新应用
python manage.py migrate

# 7. 提交代码（migration 和 model 一起）
git add myapp/models.py myapp/migrations/0002_*.py
git commit -m "feat: add budget field to Trial model"
```

### 功能开发工作流

```bash
# 1. 创建分支
git checkout -b feature/trial-api

# 2. 最小单元开发
# - 修改 Model
# - 运行 makemigrations
# - 测试 Model

# 3. 提交第一个单元
git commit -m "feat: add Trial model"

# 4. 继续下一个单元
# - 添加 Serializer
# - 测试 Serializer

# 5. 提交第二个单元
git commit -m "feat: add Trial serializer"

# 6. 重复直到功能完成

# 7. 运行完整测试
pytest

# 8. 合并到主分支
```

---

## 🔍 检查清单

开发完成后，自查：

```bash
# ✅ Migration 检查
python manage.py makemigrations --check --dry-run

# ✅ 没有手写的 migration
ls myapp/migrations/  # 文件名应该是自动生成的格式

# ✅ 没有调试代码
git diff | grep -i "print\|pdb\|breakpoint"  # 应该为空

# ✅ 测试通过
pytest

# ✅ 代码格式
uv run black . --check
uv run ruff check .

# ✅ 类型检查
uv run mypy .
```

---

## 违反约束的后果

| 约束 | 违反后果 |
|------|---------|
| 主动添加缓存 | 缓存一致性问题，难以调试 |
| 手写 migration | 迁移失败，无法回滚，数据丢失 |
| 手写 Django 生成的代码 | 结构不正确，无法使用 Django 工具 |
| 手写导入导出 | 数据验证缺失，易出错，安全风险 |
| 不遵循最小单元 | 大量代码出错，难以定位问题 |

---

**记住：这些约束是基于大量实践总结的，违反必然导致问题。**
