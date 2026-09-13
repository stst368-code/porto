# Good Boy Records — GitHub overlay only

This archive is intentionally SAFE to extract into the repository root.

It contains only:
- `.github/workflows/static.yml`
- `.gitignore`
- `good-boy-records/tools/check_github_ready.py`
- this guide

It does **not** contain or overwrite `showcase/`, `content-source/`, `templates/`, `assets/`, `data/`, or any of your written tab content.

Repository layout expected:

```text
porto/
├── .git/
├── .github/
│   └── workflows/
│       └── static.yml
├── .gitignore
└── good-boy-records/
    ├── content-source/
    ├── showcase/
    ├── templates/
    ├── tools/
    └── ...
```

`.git` and `.github` are different things and should coexist. `.git` is Git's private repository metadata. `.github` contains GitHub-specific configuration such as Actions workflows.

Before committing, run from the `porto` repository root:

```powershell
python .\good-boy-records\tools\check_github_ready.py
```
