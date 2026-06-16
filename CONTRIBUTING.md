# Contributing

Thank you for your interest in contributing to CausalInsight.

## Development Setup

```bash
git clone https://github.com/yourusername/causal-insight.git
cd causal-insight

# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

## Code Style

- **Python**: Follow PEP 8. Run `ruff check` before committing.
- **JavaScript/JSX**: The project uses the default Vite/React conventions.

## Pull Requests

1. Fork the repository.
2. Create a feature branch (`git checkout -b feat/your-feature`).
3. Commit your changes (`git commit -m "feat: description"`).
4. Push to the branch (`git push origin feat/your-feature`).
5. Open a Pull Request.

## Adding a new causal method

1. Add the method to `backend/causal_engine.py` in the appropriate section.
2. Add the call in `full_analysis()`.
3. Add the result key to the methods list in `frontend/src/components/ResultsDashboard.jsx`.
4. Update `frontend/src/components/CausalChart.jsx` if new visualization is needed.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
