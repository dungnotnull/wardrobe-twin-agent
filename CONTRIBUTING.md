# Contributing to wardrobe-twin-agent

Thank you for your interest in contributing! Here's how to get started:

## Development Setup

1. **Python Backend**
   ```bash
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1  # Windows
   pip install -e ".[gpu]"       # With CUDA, or just pip install -e .
   ```

2. **UI (Electron + React)**
   ```bash
   cd ui
   npm install
   npm run dev
   ```

3. **Browser Extension**
   - Open Chrome → `chrome://extensions`
   - Enable Developer mode
   - Load unpacked → select the `extension/` folder

4. **Start the backend**
   ```bash
   python -m backend.api.server
   ```

## Code Style

- Python: PEP 8, type hints required, docstrings for public functions
- TypeScript/React: ESLint + Prettier, functional components with hooks
- Commit messages: Conventional Commits (`feat:`, `fix:`, `docs:`, etc.)

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Add your changes with clear commit messages
4. Ensure no breaking changes to existing APIs
5. Submit a PR with a description of what and why

## Reporting Issues

- Use GitHub Issues for bugs, feature requests, and questions
- Include steps to reproduce, expected behavior, and actual behavior
- Tag with appropriate labels

## Privacy & Security

- **Never commit API keys** — use `.env` for secrets
- All body scan data must remain local (AES-256 encrypted)
- Do not add any telemetry or cloud upload features without explicit opt-in

## Adding New Features

### New ML Model
1. Add the model ID to `config/settings.py`
2. Create a pipeline file under `backend/ml/<category>/`
3. Implement lazy loading with graceful fallback
4. Add endpoint(s) in `backend/api/server.py`
5. Add UI components in `ui/src/pages/` or `ui/src/components/`

### New E-commerce Site Support
1. Add site config to `extension/src/content.js`
2. Add host permission to `extension/manifest.json`

### New LLM Provider
1. Add advisor class in `backend/advisors/llm_advisor.py`
2. Add it to the fallback chain in `LLMAdvisor.__init__`
3. Add config key to `config/settings.py`
