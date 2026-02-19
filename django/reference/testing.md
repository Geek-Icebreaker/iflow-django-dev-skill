# Django 测试策略

## 🧪 测试分层

### 1. Model 测试

```python
from django.test import TestCase
from .models import Trial

class TrialModelTest(TestCase):
    def setUp(self):
        self.trial = Trial.objects.create(
            name='Test Trial',
            budget=100000
        )

    def test_trial_creation(self):
        """测试创建"""
        self.assertEqual(self.trial.status, 'draft')
        self.assertIsNotNone(self.trial.created_at)

    def test_str_method(self):
        """测试字符串表示"""
        self.assertEqual(str(self.trial), 'Test Trial')

    def test_budget_validation(self):
        """测试验证"""
        from django.core.exceptions import ValidationError
        trial = Trial(name='Test', budget=-100)
        with self.assertRaises(ValidationError):
            trial.full_clean()
```

### 2. API 测试

```python
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

class TrialAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('test', 'test@test.com', 'pass')
        self.client.force_authenticate(user=self.user)

    def test_create_trial(self):
        """测试创建 API"""
        data = {'name': 'New Trial', 'budget': '100000.00'}
        response = self.client.post('/api/trials/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Trial.objects.count(), 1)
        self.assertEqual(Trial.objects.first().name, 'New Trial')

    def test_list_trials(self):
        """测试列表 API"""
        Trial.objects.create(name='Trial 1', budget=100000)
        Trial.objects.create(name='Trial 2', budget=200000)

        response = self.client.get('/api/trials/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_permission_denied(self):
        """测试权限"""
        self.client.logout()
        response = self.client.get('/api/trials/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

---

## 🏭 测试数据工厂

### Factory Boy

```bash
uv add factory-boy
```

```python
import factory
from django.contrib.auth import get_user_model

User = get_user_model()

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    first_name = factory.Faker('first_name')

class TrialFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Trial

    name = factory.Faker('catch_phrase')
    principal_investigator = factory.SubFactory(UserFactory)
    budget = factory.Faker('pydecimal', left_digits=6, right_digits=2, positive=True)
    status = 'draft'

# 使用
trial = TrialFactory.create()
trials = TrialFactory.create_batch(10)
trial = TrialFactory.build()  # 不保存到数据库
```

---

## 🎭 Mock 与隔离

```python
from unittest.mock import patch, MagicMock

class EmailServiceTest(TestCase):
    @patch('myapp.services.EmailService.send')
    def test_welcome_email(self, mock_send):
        """测试邮件发送"""
        User.objects.create_user('test', 'test@test.com', 'pass')
        mock_send.assert_called_once()

    @patch('myapp.services.requests.post')
    def test_api_retry(self, mock_post):
        """测试 API 重试"""
        mock_post.side_effect = [
            Exception('Timeout'),
            MagicMock(status_code=200, json=lambda: {'result': 'ok'})
        ]
        result = ExternalAPIService.call_with_retry()
        self.assertEqual(mock_post.call_count, 2)
        self.assertEqual(result['result'], 'ok')
```

---

## 📊 覆盖率

```bash
# 运行测试并生成覆盖率报告
uv run pytest --cov=myapp --cov-report=html --cov-report=term

# 查看报告
open htmlcov/index.html
```

```python
# pytest.ini
[tool:pytest]
DJANGO_SETTINGS_MODULE = myproject.settings.test
python_files = tests.py test_*.py *_tests.py
```

---

## 📋 测试检查清单

- [ ] Model 测试覆盖核心逻辑
- [ ] API 测试覆盖所有端点
- [ ] 使用 Factory 生成测试数据
- [ ] Mock 外部依赖
- [ ] 测试覆盖率 > 80%
- [ ] 测试可独立运行
- [ ] 使用 TestCase 而不是 TransactionTestCase（性能更好）

**记住：好的测试是代码质量的保障。**
