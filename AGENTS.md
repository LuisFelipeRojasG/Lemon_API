# AGENTS.md - Lemon_API Development Guide

Guidelines for agents working on the Lemon_API project.

## Project Overview

- **Framework**: Django 5.2.10 + Django REST Framework 3.16.1
- **Database**: MySQL (mysqlclient)
- **Dependencies**: drf-spectacular, django-cors-headers
- **Structure**: Django project with one app (`Restaurant`)

## Build/Test Commands

```bash
# Run server, run all tests
python manage.py runserver
python manage.py test

# Run specific test
python manage.py test Restaurant.tests.<TestClassName>.<method_name>

# Migrations and checks
python manage.py makemigrations
python manage.py migrate
python manage.py check
```

## Code Style

### Imports (in order)

1. Standard library
2. Third-party (rest_framework, etc.)
3. Django (django.db, etc.)
4. Local application

```python
from pathlib import Path
from rest_framework import serializers
from django.db import models
from .models import Category
```

### Formatting

- Max line length: 100 characters
- 4 spaces indentation (no tabs)
- Trailing commas in multiline
- Blank line between top-level definitions

### Naming

| Element | Convention | Example |
|---------|------------|---------|
| Classes/Models | PascalCase | `CategoryViewSet`, `MenuItem` |
| Functions/Variables | snake_case | `get_queryset`, `menu_items` |
| Constants | SCREAMING_SNAKE_CASE | `MAX_PRICE` |
| Filenames | snake_case | `serializer.py` |
| URLs | kebab-case | `/api/menu-items/` |

### Type Hints

Use type hints where they add clarity. Avoid redundant hints.

```python
def to_representation(self, instance: MenuItem) -> dict:
    ...

def validate_price(self, price: Decimal) -> Decimal:
    ...
```

### Comments and Documentation

- Document all classes, methods, and functions with docstrings
- Use Google-style docstrings
- Add inline comments for non-obvious logic
- Write in English

```python
class MenuItemViewSet(viewsets.ModelViewSet):
    """ViewSet for managing menu items. Provides CRUD operations."""

    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer

    def get_queryset(self) -> QuerySet:
        """Return queryset filtered by category if provided."""
        queryset = super().get_queryset()
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        return queryset
```

### Error Handling

- Use DRF's exception handling patterns
- Return appropriate HTTP status codes: 200, 201, 400, 404, 500
- Use serializers for validation:

```python
def validate(self, attrs: dict) -> dict:
    if attrs.get('price', 0) <= 0:
        raise serializers.ValidationError({'price': 'Price must be positive'})
    return attrs
```

## Django/DRF Conventions

### Models

- Define `__str__` method for all models
- Add `related_name` for ForeignKey relationships
- Add indexes for frequently queried fields
- Use Meta class for ordering

```python
class MenuItem(models.Model):
    """Menu item in the restaurant."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='menu_items'
    )

    class Meta:
        ordering = ['name']
        indexes = [models.Index('category')]

    def __str__(self) -> str:
        return self.name
```

### Serializers

- Use `ModelSerializer` for simple cases
- Specify fields explicitly: `fields = ['id', 'name', 'price']`
- Avoid `fields = '__all__'` for API serializers

### Views

- Use `ModelViewSet` for CRUD operations
- Define `queryset` and `serializer_class`
- Override methods for custom behavior

### URLs

- Use `DefaultRouter` for ViewSets

## General Guidelines

- Follow PEP 8
- Run `python manage.py check` before committing
- Test changes locally
- Use meaningful variable names
- Keep functions focused (single responsibility)
- Handle queries efficiently (`select_related`, `prefetch_related`)
- Never commit secrets - use environment variables
- Write tests for new features