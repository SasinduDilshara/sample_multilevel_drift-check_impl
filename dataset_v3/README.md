
# Multi-Level Documentation Drift Detection Dataset v3

This dataset contains 5 samples across different domains for testing the
Multi-Level Documentation Drift Detection System.

Each sample includes:
- Source-code with realistic microservices
- Organization-level documentation
- Project-level documentation
- Component-level documentation

Folder structure:
```
sampleX/
├── source-code/
│   └── <microservice>/  # contains 3+ files per service
├── org-level-documentations/
├── project-level-documentation/
└── component-level-documentation/
```

Usage:
- Feed the dataset into the drift detection system
- Validate detection of missing/outdated/conflicting documentation
