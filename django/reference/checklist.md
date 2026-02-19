# Django Code Review 检查清单

> 提交 PR 前必须通过所有检查项。

## 🔒 安全检查

- [ ] 没有硬编码敏感信息（SECRET_KEY, 密码, API Key）
- [ ] 所有 API 端点有权限检查
- [ ] 使用 ORM 参数化查询（无 SQL 注入风险）
- [ ] 富文本字段经过 HTML 清理
- [ ] 文件上传有类型和大小限制
- [ ] 生产环境 `DEBUG = False`
- [ ] `.env` 文件不在版本控制中

## 🗄️ 数据库与 Migration

- [ ] Migration 是用 `makemigrations` 生成（不是手写）
- [ ] Migration 可回滚（测试过 `migrate <app> <previous>`）
- [ ] 外键指定了 `on_delete`
- [ ] Model 设置了 `db_table` 和 `ordering`
- [ ] 常查询字段加了索引
- [ ] 没有 N+1 查询（用 `select_related`/`prefetch_related`）
- [ ] 批量操作用 `bulk_create`/`bulk_update`

## 🌐 DRF API

- [ ] 配置了分页（避免返回所有数据）
- [ ] 配置了限流（防止滥用）
- [ ] Serializer 字段标记了 `read_only`/`write_only`（默认用单 Serializer）
- [ ] 复杂场景才用读写完全分离（User/敏感数据）
- [ ] Serializer 明确指定 `fields`（不用 `__all__`）
- [ ] `get_queryset` 中实现了权限过滤
- [ ] 自定义 action 指定了 `permission_classes`

## 📦 导入导出

- [ ] 使用 `django-import-export`（不手写 CSV）
- [ ] Admin 使用 `ImportExportModelAdmin`
- [ ] Resource 配置了 `skip_unchanged`
- [ ] 实现了 `before_import_row` 验证

## 🧪 测试

- [ ] 新功能有单元测试
- [ ] API 端点有测试覆盖
- [ ] 所有测试通过 `pytest`
- [ ] 覆盖率 ≥ 80%

## 📝 代码质量

- [ ] 通过 `uv run black .` 格式化
- [ ] 通过 `uv run ruff check .` 检查
- [ ] 通过 `uv run mypy .` 类型检查
- [ ] 所有公共函数有 docstring
- [ ] 所有函数有类型注解

## 🚀 部署就绪

- [ ] 运行 `python manage.py check --deploy` 无警告
- [ ] 运行 `python manage.py makemigrations --check` 无未生成的 migration
- [ ] 静态文件可正常收集 `collectstatic`
- [ ] 环境变量文档已更新（`.env.example`）

## 🗑️ 清理

- [ ] 没有注释掉的代码（需要回溯用 Git）
- [ ] 没有调试残留（`print`, `pdb`, `breakpoint`）
- [ ] 删除了无用的导入
- [ ] 删除了无用的文件

## 📄 文档

- [ ] README 已更新（如有新功能）
- [ ] API 文档已更新（如有新端点）
- [ ] Commit message 清晰描述了改动

---

## ✅ 快速检查命令

```bash
# 代码质量
uv run black . --check
uv run ruff check .
uv run mypy .

# 测试
uv run pytest --cov

# Django 检查
python manage.py check --deploy
python manage.py makemigrations --check --dry-run

# 查找调试残留
git diff | grep -i "print\|pdb\|breakpoint"
```

---

**所有检查项通过后才能合并 PR！**
