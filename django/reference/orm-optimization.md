# Django ORM 查询优化

> N+1 查询问题是 Django 性能问题的头号杀手。

## 🚨 N+1 查询问题

### 问题识别

```python
# ❌ N+1 查询陷阱
trials = Trial.objects.all()  # 1 次查询
for trial in trials:  # 遍历 100 次
    print(trial.principal_investigator.name)  # 每次 1 次查询
# 总共: 1 + 100 = 101 次查询！

# 检测方法
from django.db import connection
from django.test.utils import override_settings

@override_settings(DEBUG=True)
def test_queries():
    connection.queries = []
    # 执行操作
    trials = Trial.objects.all()
    for trial in trials:
        print(trial.principal_investigator.name)
    print(f"查询次数: {len(connection.queries)}")
```

### 解决方案：select_related

```python
# ✅ 一对一 / 外键关系优化
trials = Trial.objects.select_related('principal_investigator')
for trial in trials:
    print(trial.principal_investigator.name)  # 不再查询数据库
# 总共: 1 次 JOIN 查询

# 多层关联
Trial.objects.select_related(
    'principal_investigator',
    'principal_investigator__department'
)
```

### 解决方案：prefetch_related

```python
# ✅ 多对多 / 反向外键优化
trials = Trial.objects.prefetch_related('subjects')
for trial in trials:
    for subject in trial.subjects.all():  # 不再查询
        print(subject.name)
# 总共: 2 次查询（1 次 Trial, 1 次 Subject）

# 条件预加载
from django.db.models import Prefetch

trials = Trial.objects.prefetch_related(
    Prefetch(
        'subjects',
        queryset=Subject.objects.filter(status='active')
    )
)
```

---

## 📊 聚合与注解

### 聚合函数

```python
from django.db.models import Count, Sum, Avg, Max, Min

# 统计
total_trials = Trial.objects.count()
total_budget = Trial.objects.aggregate(Sum('budget'))['budget__sum']
avg_budget = Trial.objects.aggregate(Avg('budget'))['budget__avg']

# 条件聚合
from django.db.models import Q
active_count = Trial.objects.aggregate(
    active=Count('id', filter=Q(status='active')),
    recruiting=Count('id', filter=Q(status='recruiting'))
)
```

### 注解（Annotate）

```python
# 为每个对象添加计算字段
trials = Trial.objects.annotate(
    subject_count=Count('subjects'),
    total_cost=Sum('costs__amount'),
    avg_age=Avg('subjects__age')
)

for trial in trials:
    print(f"{trial.name}: {trial.subject_count} 受试者")

# 条件注解
from django.db.models import Case, When, Value, IntegerField

trials = Trial.objects.annotate(
    risk_level=Case(
        When(budget__gt=5000000, then=Value('high')),
        When(budget__gt=1000000, then=Value('medium')),
        default=Value('low'),
        output_field=CharField()
    )
)
```

---

## 🔧 查询优化技巧

### 1. only / defer

```python
# only: 只加载指定字段
trials = Trial.objects.only('id', 'name')  # 减少数据传输

# defer: 延迟加载指定字段
trials = Trial.objects.defer('description', 'notes')  # 大字段延迟
```

### 2. values / values_list

```python
# values: 返回字典
trials = Trial.objects.values('id', 'name')
# [{'id': 1, 'name': 'Trial 1'}, ...]

# values_list: 返回元组
trial_ids = Trial.objects.values_list('id', flat=True)
# [1, 2, 3, ...]

# 用于子查询
active_pis = User.objects.filter(
    id__in=Trial.objects.filter(status='active').values_list('principal_investigator_id', flat=True)
)
```

### 3. exists / count

```python
# ✅ 检查存在性用 exists
if Trial.objects.filter(name='Test').exists():
    # 快速检查，不加载数据
    pass

# ❌ 不要用 count
if Trial.objects.filter(name='Test').count() > 0:  # 慢
    pass
```

### 4. iterator

```python
# 处理大量数据
for trial in Trial.objects.iterator(chunk_size=500):
    # 分批加载，减少内存占用
    process_trial(trial)
```

---

## 💾 批量操作

### bulk_create

```python
# ❌ 慢：逐个创建
for data in subject_data:
    Subject.objects.create(**data)  # N 次 INSERT

# ✅ 快：批量创建
subjects = [Subject(**data) for data in subject_data]
Subject.objects.bulk_create(subjects, batch_size=500)  # 1 次批量 INSERT
```

### bulk_update

```python
# ❌ 慢：逐个更新
for subject in subjects:
    subject.status = 'enrolled'
    subject.save()  # N 次 UPDATE

# ✅ 快：批量更新
for subject in subjects:
    subject.status = 'enrolled'
Subject.objects.bulk_update(subjects, ['status'], batch_size=500)
```

### update

```python
# ✅ 批量更新相同值
Trial.objects.filter(status='draft').update(status='active')  # 1 次 UPDATE

# ❌ 不要循环 save
for trial in Trial.objects.filter(status='draft'):
    trial.status = 'active'
    trial.save()
```

---

## 🔐 事务管理

### 原子操作

```python
from django.db import transaction

# 方式 1: 上下文管理器
with transaction.atomic():
    trial = Trial.objects.create(name='Test')
    Subject.objects.bulk_create([...])
    # 任何异常会回滚所有操作

# 方式 2: 装饰器
@transaction.atomic
def create_trial_with_subjects(trial_data, subject_data):
    trial = Trial.objects.create(**trial_data)
    subjects = [Subject(trial=trial, **data) for data in subject_data]
    Subject.objects.bulk_create(subjects)
    return trial
```

### 保存点

```python
from django.db import transaction

with transaction.atomic():
    trial = Trial.objects.create(name='Test')

    sid = transaction.savepoint()
    try:
        # 风险操作
        risky_operation(trial)
        transaction.savepoint_commit(sid)
    except Exception:
        transaction.savepoint_rollback(sid)
```

### select_for_update（悲观锁）

```python
with transaction.atomic():
    # 锁定行，防止并发修改
    trial = Trial.objects.select_for_update().get(id=trial_id)
    trial.budget += 100000
    trial.save()
```

---

## 🎯 复杂查询

### Q 对象（复杂条件）

```python
from django.db.models import Q

# OR 查询
trials = Trial.objects.filter(
    Q(status='active') | Q(status='recruiting')
)

# NOT 查询
trials = Trial.objects.filter(~Q(status='closed'))

# 复杂组合
trials = Trial.objects.filter(
    (Q(status='active') | Q(status='recruiting')) &
    Q(budget__gte=100000)
)
```

### F 对象（字段引用）

```python
from django.db.models import F

# 字段比较
trials = Trial.objects.filter(actual_cost__gt=F('budget'))

# 字段运算
Trial.objects.update(budget=F('budget') * 1.1)  # 预算增加 10%
```

### Subquery

```python
from django.db.models import Subquery, OuterRef

# 子查询
recent_subject = Subject.objects.filter(
    trial=OuterRef('pk')
).order_by('-created_at')

trials = Trial.objects.annotate(
    latest_subject_name=Subquery(recent_subject.values('name')[:1])
)
```

---

## 📋 ORM 优化检查清单

- [ ] 使用 `select_related` 优化外键查询
- [ ] 使用 `prefetch_related` 优化多对多查询
- [ ] 用 `only` / `defer` 减少字段加载
- [ ] 批量操作用 `bulk_create` / `bulk_update`
- [ ] 检查存在性用 `exists` 不用 `count`
- [ ] 大数据集用 `iterator` 减少内存
- [ ] 复杂条件用 Q 对象
- [ ] 原子操作用 `transaction.atomic`
- [ ] 并发修改用 `select_for_update`
- [ ] 用 `connection.queries` 检测 N+1
- [ ] 用 django-debug-toolbar 监控查询

**记住：ORM 优化的核心是减少查询次数和数据传输量。**
