# Django 部署配置

## 🔧 环境配置分离

### 目录结构

```
myproject/
├── settings/
│   ├── __init__.py
│   ├── base.py      # 通用配置
│   ├── dev.py       # 开发环境
│   ├── prod.py      # 生产环境
│   └── test.py      # 测试环境
```

### base.py（通用配置）

```python
import environ

env = environ.Env()
environ.Env.read_env()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = env('SECRET_KEY')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_filters',
    'import_export',
    # 你的 apps
    'myapp',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'myproject.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# 时区
USE_TZ = True
TIME_ZONE = 'Asia/Shanghai'

# 国际化
USE_I18N = True
LANGUAGE_CODE = 'zh-hans'
```

### prod.py（生产环境）

```python
from .base import *

DEBUG = False

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# 数据库
DATABASES = {
    'default': env.db()
}

# 缓存
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# 静态文件
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 安全配置
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# 日志
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
        },
        'myapp': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    },
}
```

### dev.py（开发环境）

```python
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

INSTALLED_APPS += [
    'django_extensions',
    'debug_toolbar',
]

MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

INTERNAL_IPS = ['127.0.0.1']
```

---

## 🚀 WSGI/ASGI 服务器

### Gunicorn 配置

```python
# gunicorn.conf.py
import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 50

accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"
```

```bash
# 启动
gunicorn myproject.wsgi:application -c gunicorn.conf.py
```

### Uvicorn（异步）

```bash
uvicorn myproject.asgi:application --workers 4 --host 0.0.0.0 --port 8000
```

---

## 🐳 Docker 部署

### Dockerfile

```dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# 安装 uv
RUN pip install uv

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装依赖
RUN uv sync --no-dev

# 复制代码
COPY . .

# 收集静态文件
RUN uv run python manage.py collectstatic --noinput

# 创建非 root 用户
RUN useradd -m -u 1000 django && chown -R django:django /app
USER django

EXPOSE 8000

CMD ["uv", "run", "gunicorn", "myproject.wsgi:application", "-c", "gunicorn.conf.py"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: myuser
      POSTGRES_PASSWORD: mypass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7

  web:
    build: .
    command: gunicorn myproject.wsgi:application -c gunicorn.conf.py
    volumes:
      - ./staticfiles:/app/staticfiles
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    env_file:
      - .env

volumes:
  postgres_data:
```

---

## 📋 部署检查清单

```bash
# 安全检查
python manage.py check --deploy

# Migration 检查
python manage.py makemigrations --check

# 收集静态文件
python manage.py collectstatic --noinput

# 测试
uv run pytest
```

### 环境变量（.env）

```bash
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=example.com,www.example.com
DATABASE_URL=postgresql://user:pass@localhost/dbname
REDIS_URL=redis://localhost:6379/0
```

---

## 📋 部署检查清单

- [ ] DEBUG = False
- [ ] SECRET_KEY 从环境变量读取
- [ ] ALLOWED_HOSTS 明确指定
- [ ] 配置了 HTTPS 强制重定向
- [ ] 配置了安全头
- [ ] 使用 Gunicorn/Uvicorn
- [ ] 配置了日志
- [ ] 配置了数据库连接池
- [ ] 静态文件用 Nginx 托管
- [ ] 运行了 check --deploy

**记住：部署前必须通过所有安全检查。**
