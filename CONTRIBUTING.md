# Contributing to the OCR-Devnagari Project

Welcome to the OCR-Devnagari project! We appreciate your interest in contributing to our production-grade Python OCR solution. This guide will help you get started with the contribution process.

## Project Overview
The OCR-Devnagari project aims to provide robust optical character recognition capabilities for the Devanagari script, enabling various applications in text recognition and processing.

## Development Setup
1. **Python Version**: Ensure you have Python 3.8 or higher installed.
2. **Virtual Environment**:
   - Create a virtual environment:
     ```bash
     python -m venv venv
     ```
   - Activate the virtual environment:
     - On Windows: `venv\Scripts\activate`
     - On macOS/Linux: `source venv/bin/activate`
3. **Install Dependencies**: Use the following command to install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Code Style
We follow PEP 8 guidelines for Python code. To maintain code quality, we use:
- **Black** for automatic formatting.
- **isort** for import sorting.
- **ruff** for linting.
- **mypy** for type checking.

## Testing
Testing is crucial for maintaining code quality. We use:
- **pytest**: A framework for writing simple and scalable test cases.
- **coverage**: To measure code coverage.

Run tests with the following command:
```bash
pytest --cov
```

## Dataset Handling Guidance
- **Do not include large datasets in Git**: Use DVC (Data Version Control) or Git LFS (Large File Storage) for handling datasets.
- Ensure compliance with privacy regulations when using public datasets.

## Model Training/Evaluation Notes
- Follow the training pipeline documented in the `train.py` file.
- Make sure to evaluate the model thoroughly before submitting any changes.

## Documentation Updates
- Keep the documentation updated with your changes. Use Markdown syntax for clarity.
- Documentation can be found in the `docs` directory.

## Issue and PR Workflow
1. Open an issue to discuss your proposed changes.
2. Fork the repository and clone your fork.
3. Create a new branch for your changes.
4. Open a pull request against the `main` branch.

## Commit Message Convention
- Use the following format for commit messages:
  - `type: subject`
  - Example: `fix: corrected OCR bug`
- Types include: `feat` (feature), `fix` (bug fix), `docs` (documentation), `style` (formatting), `refactor`, `test`, `chore`.

## Security Policy
We adhere to a responsible disclosure policy. Please report any security vulnerabilities privately to the maintainers.

## Licensing Note
This project is licensed under the MIT License. See the `LICENSE` file for details.

## Multi-Agent Orchestration/Google Agent Development Kit Integration Guidelines
- If applicable, refer to the `docs/integration.md` file for guidelines on integrating with multi-agent orchestration or Google Agent Development Kit.

Thank you for considering contributing to the OCR-Devnagari project! We look forward to your contributions!