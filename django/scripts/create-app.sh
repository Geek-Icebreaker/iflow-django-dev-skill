#!/usr/bin/env bash
# Django App 创建脚本
# 用法: ./scripts/create-app.sh <app_name>

set -euo pipefail

APP_NAME="${1:-}"

if [[ -z "$APP_NAME" ]]; then
    echo "用法: $0 <app_name>"
    echo "示例: $0 users"
    exit 1
fi

echo "创建 Django App: $APP_NAME"

# 创建 app
python manage.py startapp "$APP_NAME"

# 创建标准目录结构
mkdir -p "$APP_NAME"/{serializers,tests,migrations}

# 创建 __init__.py
touch "$APP_NAME"/serializers/__init__.py
touch "$APP_NAME"/tests/__init__.py

# 创建标准文件
cat > "$APP_NAME"/serializers.py <<'EOF'
"""
${APP_NAME} serializers.
"""
from rest_framework import serializers

EOF

cat > "$APP_NAME"/urls.py <<'EOF'
"""
${APP_NAME} URL configuration.
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "${APP_NAME}"

router = DefaultRouter()
# router.register(r'items', views.ItemViewSet)

urlpatterns = router.urls
EOF

cat > "$APP_NAME"/tests/test_models.py <<'EOF'
"""
${APP_NAME} model tests.
"""
import pytest
from django.test import TestCase

EOF

cat > "$APP_NAME"/tests/test_views.py <<'EOF'
"""
${APP_NAME} view tests.
"""
import pytest
from rest_framework.test import APITestCase

EOF

echo "✅ App '$APP_NAME' 创建完成"
echo ""
echo "下一步:"
echo "1. 添加 '$APP_NAME' 到 INSTALLED_APPS"
echo "2. 在 urls.py 中引入: path('api/$APP_NAME/', include('$APP_NAME.urls'))"
echo "3. 创建模型并运行: python manage.py makemigrations"
