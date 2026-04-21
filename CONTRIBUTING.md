# Contributing to MemFree

Thank you for your interest in MemFree! Here's how to contribute effectively.

---

## 🐛 Bug Reports

1. Check existing issues first
2. Include: Python version, OS, error trace, minimal reproduction
3. Use the bug report template

---

## 💡 Feature Requests

1. Explain the problem you're solving, not just the solution
2. Consider: Is this general enough for all users, or specific to your setup?
3. Reference existing architecture decisions in `DECISIONS.md` if relevant

---

## 🔧 Code Contributions

### Setup

```bash
git clone https://github.com/yul0101/memfree.git
cd memfree
cp -r * ~/.memfree/
```

### Running Tests

```bash
python3 ~/.memfree/test_mem0_facts.py
```

### Code Style

- Python: `black` formatting, `ruff` linting
- Configs are in `pyproject.toml`
- Run `black .` before submitting

### Pull Request Process

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Add tests for new functionality
4. Ensure all tests pass
5. Update docs if needed
6. Open PR with clear description

---

## 📖 Documentation

- Core docs: `docs/` directory
- API reference: inline docstrings
- Architecture decisions: `DECISIONS.md`

---

## 🧪 Testing Strategy

- Unit tests for each CLI command
- Integration tests for the REST API
- Manual testing checklist for Web UI

---

## ❓ Questions?

Open a Discussion or ping via GitHub Issues.
