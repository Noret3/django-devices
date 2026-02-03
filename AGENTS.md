# Django Devices Project Context

## Project Overview
Django Devices is a Python/Django backend application designed to manage and track devices. It likely serves as a backend for a frontend application or as a standalone API service.

## Architecture
- **Pattern**: Django MVT (Model-View-Template) / DRF (Django Rest Framework)
- **API**: RESTful API
- **Database**: PostgreSQL (assumed based on typical Django stack)
- **Task Queue**: Celery (assumed if async tasks are needed)

## Technology Stack
- **Language**: Python 3.12+
- **Framework**: Django 5.x
- **Dependency Management**: uv
- **Testing**: pytest

## Code Standards

### Code Formatting Style
- **PEP 8**: Strict adherence to PEP 8 guidelines.
- **Type Hinting**: Mandatory type hints for all function arguments and return values.
- **Docstrings**: Google style docstrings for all public modules, classes, and functions with arguments, exception and returning.
- **Imports**: Sorted and grouped (Standard Library, Third Party, Local Application).

### Code Writing Rules

**Models:**
- Use `TextChoices` or `IntegerChoices` for Enums.
- Define meaningful `__str__` methods.
- Move Enums to (`constants.py`) file of app.
- Set explicit and clear `related_name` for foreign keys.

**Services & Selectors:**
- **Services (`services.py`)**: Handle business logic and write operations.
- **ORM logic (`managers.py`)**: Write hard reusable db-queries.



## Development Practices
- **Testing**: Write unit tests for all services and selectors. Use `pytest`.
- **Git**: Use meaningful commit messages. Create feature branches.
- **Environment Variables**: Use `.env` files for configuration.

## What to Avoid
- **Fat Views**: Logic belongs in Services.
- **Magic Numbers**: Use constants or Enums.
- **Implicit Types**: Missing type hints.
- **N+1 Queries**: Use `select_related` and `prefetch_related`.
- **Comments**: Avoid to write simple comments in methods.

## Common Commands
```bash
# Run server
python manage.py runserver

# Run tests
pytest

# Make migrations
python manage.py makemigrations

# Migrate
python manage.py migrate
```