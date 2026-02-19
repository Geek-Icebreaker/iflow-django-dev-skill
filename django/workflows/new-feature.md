# Django 新功能开发工作流

## 适用场景
为 Django 项目添加新功能（模型、API、业务逻辑等）。

## 工作流步骤

### 1. 需求分析
- [ ] 明确功能需求和验收标准
- [ ] 识别涉及的模型和 API 端点
- [ ] 确定权限和安全要求

### 2. 数据建模
- [ ] 设计模型字段和关系（参考 `model-design.md`）
- [ ] 添加类型注解和 docstring
- [ ] 考虑索引和查询优化
- [ ] 创建 migration: `python manage.py makemigrations`

### 3. 编写测试（TDD）
- [ ] 创建模型测试 (`tests/test_models.py`)
- [ ] 创建 API 测试 (`tests/test_views.py`)
- [ ] 创建 serializer 测试（如需要）
- [ ] 运行测试确认失败: `pytest`

### 4. 实现功能
- [ ] 创建/更新 models
- [ ] 创建 serializers（参考 `drf-api.md`）
- [ ] 创建 viewsets/views
- [ ] 配置 URL 路由
- [ ] 添加权限控制

### 5. 优化与安全
- [ ] ORM 查询优化（`select_related`, `prefetch_related`）
- [ ] 添加数据验证
- [ ] 检查安全问题（参考 `security.md`）
- [ ] 添加日志记录

### 6. 测试与验证
- [ ] 运行所有测试: `pytest`
- [ ] 检查测试覆盖率: `pytest --cov`
- [ ] 手动测试 API（可选）
- [ ] 运行 migration: `python manage.py migrate`

### 7. 文档与清理
- [ ] 更新 API 文档
- [ ] 代码格式化: `black . && ruff check .`
- [ ] 类型检查: `mypy .`
- [ ] 提交代码

## 检查清单

参考 `checklist.md` 确保质量。

## 常用命令

```bash
# 创建 app
python manage.py startapp <app_name>

# 创建 migration
python manage.py makemigrations

# 应用 migration
python manage.py migrate

# 运行测试
pytest

# 代码质量检查
black . && ruff check . && mypy .
```

## 参考文档
- `model-design.md` - 模型设计规范
- `drf-api.md` - DRF API 开发
- `security.md` - 安全最佳实践
- `checklist.md` - 质量检查清单
