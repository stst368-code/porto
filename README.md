# Porto multi-site GitHub Pages

This package changes deployment from GBR occupying `/porto/` to sibling routes:

```text
/porto/cv/
/porto/good-boy-records/
/porto/blabla/
```

Merge these into the existing repository:

```text
porto/
├── .github/
│   ├── scripts/
│   │   └── stage_portfolio.py
│   └── workflows/
│       └── portfolio-pages.yml
├── cv/
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   ├── CV_SimonTaylor.pdf
│   └── certs/
├── gbr/
└── good-boy-records/
```

The existing GBR build still creates:

```text
good-boy-records/_site/
```

The new staging script creates the actual GitHub Pages artifact:

```text
_pages/
├── cv/
└── good-boy-records/
```

Any other root-level folder containing `index.html` is also copied automatically,
so `blabla/index.html` becomes `/porto/blabla/`.

The CV package has already been rewritten for its new location:
- `CV_SimonTaylor.pdf`
- `certs/...`
- `../good-boy-records/`
- `../good-boy-records/#how-it-works`

Important: disable/remove the old Pages deployment workflow after installing
`portfolio-pages.yml`, otherwise both workflows may attempt to deploy Pages.
