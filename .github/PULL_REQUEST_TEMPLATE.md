# Pull Request Template

## 📋 Description
Brief description of changes and their purpose.

## 🔄 Type of Change
- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update
- [ ] 🔧 Refactoring (no functional changes)
- [ ] ⚡ Performance improvement
- [ ] 🧪 Tests addition/update
- [ ] 🔒 Security enhancement

## ✅ Code Quality Checklist

### Naming & Documentation
- [ ] Functions use snake_case naming
- [ ] Variables use descriptive names (no abbreviations)
- [ ] Classes use PascalCase
- [ ] Constants use UPPER_SNAKE_CASE
- [ ] All functions have comprehensive docstrings
- [ ] Docstrings include Args, Returns, Raises sections
- [ ] Complex logic has inline comments

### Python Standards
- [ ] All functions have type hints
- [ ] Using f-strings for string formatting
- [ ] Context managers for resource management
- [ ] Proper exception handling (specific exceptions)
- [ ] No hardcoded values (using constants)
- [ ] Following asyncio patterns for I/O operations

### Database & Security
- [ ] Using SQLAlchemy ORM (no raw SQL)
- [ ] Database queries are parameterized
- [ ] No hardcoded secrets or API keys
- [ ] Input validation implemented
- [ ] Authentication/authorization checks added
- [ ] Using Decimal for financial calculations

### Frontend/React (if applicable)
- [ ] Functional components with hooks
- [ ] Proper dependency arrays in useEffect
- [ ] React.memo for performance optimization
- [ ] Accessibility attributes added (ARIA labels)
- [ ] Responsive design implemented
- [ ] Loading and error states handled

### Testing & Performance
- [ ] Unit tests added/updated
- [ ] Test coverage ≥ 80%
- [ ] Integration tests for API changes
- [ ] Performance optimizations implemented
- [ ] Memory leaks prevented
- [ ] Database queries optimized

### Financial/Trading Specific
- [ ] Decimal precision for monetary values
- [ ] Market hours validation
- [ ] Risk management checks
- [ ] Audit trails for transactions
- [ ] Regulatory compliance considered

## 🧪 Testing
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Edge cases tested
- [ ] Performance tests run (if applicable)
- [ ] Manual testing completed

## 🔍 Code Review
- [ ] Self-reviewed the code
- [ ] Followed SOLID principles
- [ ] Applied clean code principles (DRY, KISS, YAGNI)
- [ ] Separation of concerns maintained
- [ ] Code is production-ready
- [ ] No security vulnerabilities introduced

## 📊 Performance Impact
- [ ] No performance degradation
- [ ] Database queries optimized
- [ ] Bundle size impact assessed (frontend)
- [ ] Memory usage acceptable
- [ ] Response times within SLA

## 🔒 Security Review
- [ ] No sensitive data exposed in logs
- [ ] API endpoints secured
- [ ] Input validation implemented
- [ ] XSS/CSRF protection in place
- [ ] Encryption used for sensitive data

## 📚 Documentation
- [ ] README updated (if needed)
- [ ] API documentation updated
- [ ] Code comments added for complex logic
- [ ] Migration guide provided (if breaking changes)

## 🚀 Deployment Readiness
- [ ] Environment variables documented
- [ ] Database migrations created
- [ ] Configuration changes documented
- [ ] Rollback plan considered
- [ ] Monitoring/alerting updated

## 📸 Screenshots (if UI changes)
<!-- Add before/after screenshots for UI changes -->

## 🔗 Related Issues
<!-- Link to related issues -->
Closes #

## 🧑‍💻 Reviewer Notes
<!-- Any specific areas you want reviewers to focus on -->

---

**By submitting this PR, I confirm that:**
- [ ] My code follows the project's coding standards (CLAUDE.md)
- [ ] I have performed a self-review of my code
- [ ] I have commented my code where necessary
- [ ] I have made corresponding changes to documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix/feature works
- [ ] New and existing unit tests pass locally