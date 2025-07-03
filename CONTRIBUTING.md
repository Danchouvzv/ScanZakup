# Contributing to ScanZakup

## 🎯 Overview

ScanZakup follows **FAANG-level engineering practices**. Quality > Speed. Every PR must meet production standards.

## 🛠 Development Setup

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Node.js 18+ (for pre-commit hooks)
- Git with SSH keys configured

### Quick Start
```bash
# 1. Clone and setup
git clone git@github.com:Danchouvzv/ScanZakup.git
cd ScanZakup

# 2. Install pre-commit hooks
pip install pre-commit
pre-commit install

# 3. Start development stack
docker-compose up -d

# 4. Run tests
cd backend && python -m pytest

# 5. Verify API
curl http://localhost:8000/health
```

## 📋 Code Standards

### Code Quality Gates
- **100% type coverage** (mypy strict mode)
- **≥80% test coverage** (pytest-cov)
- **Zero linting errors** (black, isort, flake8)
- **Security scans pass** (bandit, safety)

### File Structure
```
backend/
├── app/
│   ├── api/routes/          # FastAPI endpoints
│   ├── core/               # Config, database, auth
│   ├── models/             # SQLAlchemy models
│   ├── schemas/            # Pydantic schemas
│   ├── services/           # Business logic
│   └── tests/              # Test suites
├── migrations/             # Alembic migrations
└── scripts/               # Deployment scripts
```

### Naming Conventions
- **Files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Database tables**: `snake_case`

## 🔄 Git Workflow

### Branch Strategy
```
main            # Production-ready code
├── develop     # Integration branch
├── feature/*   # Feature branches
├── hotfix/*    # Critical fixes
└── release/*   # Release preparation
```

### Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
feat(api): add procurement search endpoint
fix(auth): resolve JWT token expiration bug
docs(readme): update deployment instructions
test(analytics): add unit tests for trend analysis
```

### PR Process

#### Before Creating PR
- [ ] All tests pass locally
- [ ] Code coverage ≥80%
- [ ] Pre-commit hooks pass
- [ ] API documentation updated
- [ ] Database migrations tested

#### PR Requirements
- **Title**: `[TICKET-123] Brief description`
- **Size**: ≤300 lines (split larger changes)
- **Description**: Use template below
- **Reviews**: ≥2 approvals for `main`, ≥1 for `develop`

#### PR Template
```markdown
## 🎯 What
Brief description of changes

## 🔧 How
Technical implementation details

## 🧪 Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## 📊 Impact
- Performance impact: None/Positive/Negative
- Breaking changes: Yes/No
- Database changes: Yes/No

## 🔗 Links
- Ticket: [PROJ-123](link)
- Design doc: [link]
- API docs: [link]
```

## 🧪 Testing Standards

### Test Structure
```python
# tests/test_[module].py
import pytest
from fastapi.testclient import TestClient

class TestProcurementAPI:
    """Test procurement endpoints."""
    
    def test_list_procurements_success(self, client: TestClient):
        """Should return paginated procurement list."""
        # Arrange
        # Act
        # Assert
        pass
    
    def test_list_procurements_with_filters(self, client: TestClient):
        """Should filter procurements by date range."""
        pass
```

### Test Categories
- **Unit tests**: `tests/unit/` - Pure logic, no external deps
- **Integration tests**: `tests/integration/` - Database, Redis, external APIs
- **E2E tests**: `tests/e2e/` - Full user workflows
- **Performance tests**: `tests/performance/` - Load testing

### Test Commands
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test types
pytest tests/unit/
pytest tests/integration/ -v
pytest -k "test_procurement" -v

# Performance tests
pytest tests/performance/ --benchmark-only
```

## 📊 Performance Standards

### Response Time Budgets
- **95th percentile**: <150ms
- **99th percentile**: <500ms
- **Health checks**: <50ms

### Database Guidelines
- Use indexes for all filter/sort columns
- Explain query plans for N+1 queries
- Paginate results (max 100 items)
- Use async/await for all DB calls

### API Guidelines
- Follow REST conventions
- Use HTTP status codes correctly
- Include pagination headers
- Validate all inputs
- Return consistent error formats

## 🔒 Security Standards

### Authentication/Authorization
- JWT tokens with 1-hour expiry
- Refresh tokens with 7-day expiry
- Role-based access control (RBAC)
- Rate limiting on all endpoints

### Data Handling
- Validate all inputs with Pydantic
- Sanitize SQL queries (no raw SQL)
- Hash passwords with bcrypt
- Encrypt sensitive data at rest

### Security Checklist
- [ ] No secrets in code
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention
- [ ] CORS properly configured
- [ ] HTTPS in production

## 🚀 Deployment

### Environment Requirements
- **Development**: Docker Compose
- **Staging**: Kubernetes + Helm
- **Production**: Kubernetes + ArgoCD

### Release Process
1. Create release branch from `develop`
2. Update version numbers
3. Run full test suite
4. Deploy to staging
5. QA approval
6. Merge to `main`
7. Auto-deploy to production

## 📈 Monitoring

### Metrics to Track
- API response times
- Error rates
- Database query performance
- Memory/CPU usage
- Active user sessions

### Alerting Thresholds
- **Critical**: Error rate >1%, Response time >1s
- **Warning**: Error rate >0.5%, Response time >500ms
- **Info**: High traffic, deployment events

## 🤝 Code Review Guidelines

### What to Look For
- **Functionality**: Does it work as intended?
- **Performance**: Any potential bottlenecks?
- **Security**: Input validation, SQL injection risks?
- **Maintainability**: Clear, readable code?
- **Tests**: Adequate coverage and quality?

### Review Checklist
- [ ] Code follows style guidelines
- [ ] Tests are comprehensive
- [ ] API changes are documented
- [ ] No hardcoded values
- [ ] Error handling is proper
- [ ] Performance considerations addressed

## 📚 Documentation

### Required Documentation
- **API docs**: Auto-generated from OpenAPI
- **Architecture docs**: High-level system design
- **Runbooks**: Operational procedures
- **Changelog**: User-facing changes

### Documentation Standards
- Keep README up-to-date
- Document all public APIs
- Include examples in docstrings
- Update docs with code changes

## 🐛 Bug Reports

### Bug Report Template
```markdown
## 🐛 Bug Description
Clear description of the issue

## 🔄 Steps to Reproduce
1. Go to...
2. Click on...
3. See error

## 🎯 Expected Behavior
What should happen

## 📱 Environment
- OS: [e.g., macOS 12.0]
- Browser: [e.g., Chrome 96]
- Version: [e.g., 1.2.3]

## 📎 Additional Context
Screenshots, logs, etc.
```

## 💡 Feature Requests

### Feature Request Template
```markdown
## 🎯 Feature Description
Clear description of the proposed feature

## 🔥 Motivation
Why is this feature needed?

## 💡 Proposed Solution
How should this be implemented?

## 🔄 Alternatives Considered
What other approaches were considered?

## 📊 Success Metrics
How will we measure success?
```

---

## 🏆 Definition of Done

A task is only "Done" when:

- [ ] **Code written** and follows all standards
- [ ] **Tests written** with ≥80% coverage
- [ ] **Code reviewed** and approved
- [ ] **Documentation updated**
- [ ] **CI/CD passes** all checks
- [ ] **Deployed to staging** and tested
- [ ] **Product owner** approved

---

**Remember**: We optimize for **long-term maintainability** over short-term velocity. Quality code today saves hours of debugging tomorrow! 🚀 