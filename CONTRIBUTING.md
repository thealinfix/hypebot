# Contributing to HypeBot

Thank you for your interest in contributing to HypeBot! 

## How to Contribute

### Reporting Bugs
1. Check if the bug is already reported in Issues
2. Create a new issue with:
  - Clear title and description
  - Steps to reproduce
  - Expected vs actual behavior
  - System information

### Suggesting Features
1. Check existing issues and roadmap
2. Create a feature request with:
  - Use case description
  - Proposed solution
  - Alternative solutions considered

### Code Contributions

#### Setup
1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/hypebot.git`
3. Create branch: `git checkout -b feature/your-feature-name`
4. Install dependencies: `pip install -r requirements.txt`

#### Code Style
- Follow PEP 8
- Use type hints where possible
- Add docstrings to all functions
- Keep functions small and focused
- Use meaningful variable names

#### Testing
- Test your changes thoroughly
- Add logging for debugging
- Handle errors gracefully
- Test with different timezones

#### Commit Guidelines
- Use clear commit messages
- Reference issues: `Fix #123: Description`
- Keep commits atomic

#### Pull Request Process
1. Update documentation if needed
2. Update CHANGELOG.md
3. Ensure all checks pass
4. Request review from maintainers

### Architecture Guidelines
- Follow existing patterns
- Keep modules independent
- Use dependency injection
- Maintain async/await consistency
- Add to appropriate module:
 - `handlers/` - User interactions
 - `services/` - Business logic
 - `utils/` - Shared utilities
 - `models/` - Data structures

## Code of Conduct
- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive criticism
- Help others learn

## Questions?
Feel free to open an issue for any questions!
