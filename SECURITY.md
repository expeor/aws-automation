# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.5.x   | :white_check_mark: |
| < 0.5   | :x:                |

## Reporting a Vulnerability

**Please do NOT open a public GitHub issue for security vulnerabilities.**

Instead, report security issues via:
- Email: security@example.com
- Or use GitHub's [private vulnerability reporting](https://github.com/expeor/aws-automation/security/advisories/new)

### What to expect

- **Initial response**: Within 48 hours
- **Status updates**: Every 3-5 business days
- **Resolution timeline**: Varies by severity (critical: 7 days, high: 30 days)

### Recognition

We appreciate your help in keeping this project secure. With your permission,
we'll credit you in the release notes.

## Security Measures

This project implements several security measures:

- **Static Analysis**: Bandit security linter runs on every PR
- **Dependency Scanning**: pip-audit checks for known vulnerabilities
- **SARIF Integration**: Security findings are uploaded to GitHub Security tab
- **Code Review**: All changes require PR review before merging

## Security Best Practices

When contributing to this project:

1. Never hardcode AWS credentials or secrets
2. Validate all user inputs (account IDs, region names, etc.)
3. Avoid logging sensitive information
4. Follow the principle of least privilege for IAM operations
