# Django Model 设计规范

## 🎯 BaseModel 模式（推荐）

### 标准 BaseModel

```python
from django.db import models

class BaseModel(models.Model):
    """
    所有业务 Model 的基类
    提供通用字段：软删除、审计字段
    """
    # 软删除
    is_show = models.BooleanField(default=False, verbose_name="是否显示")

    # 审计字段
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="修改时间")
    creator = models.ForeignKey(
        'account.User',
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_%(class)s",  # ✅ 动态生成 related_name
        verbose_name="创建人"
    )
    editor = models.ForeignKey(
        'account.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="edited_%(class)s",  # ✅ 避免反向关系冲突
        verbose_name="修改人"
    )

    class Meta:
        abstract = True  # ✅ 抽象基类，不创建表

# 使用
class Trial(BaseModel):
    name = models.CharField(max_length=200)
    # 自动继承: is_show, created_at, updated_at, creator, editor
```

### 审核流程 BaseCheckModel

```python
class BaseCheckModel(BaseModel):
    """
    需要审核的 Model 继承此类
    """
    is_checked = models.BooleanField(null=True, blank=True, verbose_name="是否审核")
    check_time = models.DateTimeField(blank=True, null=True, verbose_name="审核时间")
    check_user = models.ForeignKey(
        'account.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="check_user_%(class)s",
        verbose_name="审核人"
    )
    check_note = models.CharField(max_length=200, blank=True, null=True, verbose_name="审核备注")

    class Meta:
        abstract = True

# 使用
class Order(BaseCheckModel):
    order_number = models.CharField(max_length=50)
    # 自动继承: is_checked, check_time, check_user, check_note
```

### related_name 动态生成

```python
# ✅ 使用 %(class)s 占位符
creator = models.ForeignKey(
    'User',
    related_name="created_%(class)s"  # Trial → created_trial
)

# 自动生成的反向关系：
user.created_trial.all()      # 用户创建的 Trial
user.created_order.all()      # 用户创建的 Order
user.created_product.all()    # 用户创建的 Product

# ❌ 不使用占位符会导致冲突
creator = models.ForeignKey('User', related_name="created_objects")
# 多个 Model 都用相同的 related_name 会报错！
```

---

## 🏗️ 字段设计

### 基础字段规范

```python
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class Trial(models.Model):
    # ✅ UUID 主键（推荐）
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ✅ CharField 必须指定 max_length
    name = models.CharField(max_length=200, db_index=True)  # 常查询字段加索引

    # ✅ 选择字段用 choices
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('active', '进行中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True  # 状态常用于过滤
    )

    # ✅ 金额用 DecimalField
    budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    # ✅ 大文本用 TextField
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True, null=True)

    # ✅ 时间戳字段
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'trials'  # ✅ 明确表名
        ordering = ['-created_at']  # ✅ 默认排序
        verbose_name = '临床试验'
        verbose_name_plural = '临床试验'

        # ✅ 复合索引
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['principal_investigator', 'status']),
        ]

        # ✅ 约束
        constraints = [
            models.CheckConstraint(
                check=models.Q(budget__gte=0),
                name='budget_non_negative'
            ),
            models.UniqueConstraint(
                fields=['name', 'principal_investigator'],
                name='unique_trial_per_pi'
            )
        ]

    def __str__(self):
        return self.name
```

### 关系字段

```python
class Subject(models.Model):
    # ✅ 外键必须指定 on_delete
    trial = models.ForeignKey(
        'Trial',
        on_delete=models.CASCADE,  # 试验删除时级联删除受试者
        related_name='subjects'
    )

    # ✅ 可选外键
    assigned_doctor = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,  # 医生删除时设为 NULL
        null=True,
        blank=True,
        related_name='assigned_subjects'
    )

    # ✅ 一对一
    medical_record = models.OneToOneField(
        'MedicalRecord',
        on_delete=models.CASCADE,
        related_name='subject'
    )

    # ✅ 多对多（无额外字段）
    medications = models.ManyToManyField(
        'Medication',
        related_name='subjects',
        blank=True
    )

    # ✅ 多对多（有额外字段 - 使用中间表）
    adverse_events = models.ManyToManyField(
        'AdverseEvent',
        through='SubjectAdverseEvent',
        related_name='affected_subjects'
    )

class SubjectAdverseEvent(models.Model):
    """中间表"""
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    adverse_event = models.ForeignKey(AdverseEvent, on_delete=models.CASCADE)
    severity = models.CharField(max_length=20)
    occurred_at = models.DateTimeField()

    class Meta:
        unique_together = [['subject', 'adverse_event']]
```

---

## 📝 Model Meta 选项

### 必须设置的选项

```python
class Trial(models.Model):
    class Meta:
        # ✅ 明确表名（避免自动生成）
        db_table = 'trials'

        # ✅ 默认排序（影响 QuerySet）
        ordering = ['-created_at', 'name']

        # ✅ Admin 显示名称
        verbose_name = '临床试验'
        verbose_name_plural = '临床试验'

        # ✅ 权限（可选）
        permissions = [
            ('view_trial_data', 'Can view trial data'),
            ('export_trial', 'Can export trial'),
        ]
```

### 索引策略

```python
class Meta:
    # ✅ 单字段索引
    # 方式 1: 字段级别
    status = models.CharField(max_length=20, db_index=True)

    # 方式 2: Meta 级别
    indexes = [
        models.Index(fields=['status']),

        # ✅ 复合索引（常一起查询的字段）
        models.Index(fields=['status', 'created_at']),
        models.Index(fields=['principal_investigator', 'status']),

        # ✅ 命名索引
        models.Index(fields=['name'], name='trial_name_idx'),

        # ✅ 部分索引（Django 4.0+）
        models.Index(
            fields=['status'],
            condition=models.Q(status='active'),
            name='active_trials_idx'
        ),
    ]

    # ❌ 不要对低基数字段建索引
    # is_active = models.BooleanField(db_index=True)  # 通常只有 True/False，索引效果差
```

### 唯一约束

```python
class Meta:
    # 方式 1: unique_together（老式，但仍可用）
    unique_together = [
        ['name', 'principal_investigator']
    ]

    # 方式 2: UniqueConstraint（推荐，功能更强）
    constraints = [
        models.UniqueConstraint(
            fields=['name', 'principal_investigator'],
            name='unique_trial_per_pi'
        ),

        # ✅ 条件唯一约束
        models.UniqueConstraint(
            fields=['email'],
            condition=models.Q(is_active=True),
            name='unique_active_email'
        ),
    ]
```

---

## 🎯 自定义 Manager 和 QuerySet

### 自定义 QuerySet

```python
class TrialQuerySet(models.QuerySet):
    def active(self):
        """活跃试验"""
        return self.filter(status='active')

    def with_subject_count(self):
        """添加受试者计数"""
        from django.db.models import Count
        return self.annotate(subject_count=Count('subjects'))

    def for_user(self, user):
        """用户可见的试验"""
        if user.is_staff:
            return self
        return self.filter(principal_investigator=user)

class Trial(models.Model):
    # ...
    objects = TrialQuerySet.as_manager()  # ✅ 使用自定义 QuerySet

# 使用
active_trials = Trial.objects.active().with_subject_count()
user_trials = Trial.objects.for_user(request.user).active()
```

### 自定义 Manager

```python
class ActiveTrialManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status='active')

class Trial(models.Model):
    # ...
    objects = TrialQuerySet.as_manager()  # 默认 Manager
    active_objects = ActiveTrialManager()  # 额外 Manager

# 使用
all_trials = Trial.objects.all()
active_trials = Trial.active_objects.all()
```

---

## 🔧 Model 方法

### 实例方法

```python
class Trial(models.Model):
    # ...

    def is_recruitable(self) -> bool:
        """是否可招募"""
        return self.status == 'recruiting' and self.subject_count < self.target_subjects

    def get_full_name(self) -> str:
        """完整名称"""
        return f"{self.code}: {self.name}"

    def calculate_remaining_budget(self) -> Decimal:
        """剩余预算"""
        from django.db.models import Sum
        spent = self.costs.aggregate(Sum('amount'))['amount__sum'] or 0
        return self.budget - spent

    def save(self, *args, **kwargs):
        """重写 save 时注意事项"""
        # ✅ 调用父类方法
        super().save(*args, **kwargs)

        # ⚠️ 避免在 save 中触发复杂逻辑
        # 复杂逻辑应放在 Service 层或 Signal 中
```

### 类方法和属性

```python
class Trial(models.Model):
    # ...

    @classmethod
    def create_with_subjects(cls, trial_data, subject_data):
        """工厂方法"""
        trial = cls.objects.create(**trial_data)
        subjects = [Subject(trial=trial, **data) for data in subject_data]
        Subject.objects.bulk_create(subjects)
        return trial

    @property
    def is_active(self) -> bool:
        """计算属性"""
        return self.status == 'active'

    @property
    def days_since_created(self) -> int:
        from django.utils import timezone
        return (timezone.now() - self.created_at).days
```

---

## ⚠️ 常见陷阱

### 1. on_delete 必须指定

```python
# ❌ Django 3.0+ 会报错
trial = models.ForeignKey('Trial')

# ✅ 必须指定
trial = models.ForeignKey('Trial', on_delete=models.CASCADE)

# on_delete 选项：
# CASCADE: 级联删除
# SET_NULL: 设为 NULL（需要 null=True）
# SET_DEFAULT: 设为默认值（需要 default）
# PROTECT: 防止删除（如果有关联对象会报错）
# SET(): 设为指定值
# DO_NOTHING: 什么都不做（危险，可能导致数据库完整性问题）
```

### 2. 循环导入

```python
# ❌ 循环导入
from myapp.models import OtherModel

class Trial(models.Model):
    other = models.ForeignKey(OtherModel, on_delete=models.CASCADE)

# ✅ 使用字符串引用
class Trial(models.Model):
    other = models.ForeignKey('myapp.OtherModel', on_delete=models.CASCADE)
    # 或同一个 app
    other = models.ForeignKey('OtherModel', on_delete=models.CASCADE)
```

### 3. blank vs null

```python
# ✅ 字符串字段：blank=True, null=False（推荐）
name = models.CharField(max_length=100, blank=True, default='')

# ✅ 非字符串字段：blank=True, null=True
age = models.IntegerField(blank=True, null=True)

# blank: 表单验证是否允许为空
# null: 数据库是否允许 NULL

# ❌ 避免
name = models.CharField(max_length=100, null=True)  # 两种空值：'' 和 NULL
```

### 4. 软删除

```python
class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        """批量软删除"""
        return self.update(is_deleted=True, deleted_at=timezone.now())

class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model).filter(is_deleted=False)

class Trial(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()  # 包含已删除

    def delete(self, *args, **kwargs):
        """实例软删除"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
```

---

## 📋 Model 设计检查清单

- [ ] CharField 指定了 max_length
- [ ] 外键指定了 on_delete
- [ ] 设置了 db_table
- [ ] 设置了 ordering
- [ ] 常查询字段加了索引
- [ ] 复合查询用了复合索引
- [ ] 使用了约束保证数据完整性
- [ ] 时间字段使用了 auto_now_add / auto_now
- [ ] 避免了循环导入（使用字符串引用）
- [ ] 正确使用了 blank 和 null
- [ ] 重要数据考虑了软删除
- [ ] 添加了 verbose_name

**记住：好的 Model 设计是系统稳定性的基础。**
