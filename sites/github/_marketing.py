"""R11: Marketing page content + DB seeder.

This module owns the deterministic seed content for the GitHub mirror's
20 marketing landing pages (formerly the shared simple_landing.html
template + small chunks of info_page.html).  Each entry below names:

  * `slug` — primary key in marketing_page (matches the URL path segment)
  * `template` — the dedicated Jinja file (NO page shares its template)
  * `title` / `eyebrow` / `headline` / `subtitle` — chrome metadata
  * `data` — page-specific JSON blob (table / faq / grid / cta / etc.)
  * `source_url` — the github.com page we sampled real content from
    (recorded for provenance; ~50% of pages now carry verbatim copy
    extracted via Tavily on 2026-05-27 from the live github.com).

Why JSON-in-a-column instead of N tables: every page has a different
shape (pricing has tiers + matrix, status has uptime rows, terms has
prose, supply-chain has SBOM badges).  Modelling every variant in
SQLAlchemy would mint ~12 tables and 30 columns of mostly-null data.
A single JSON blob keeps the schema flat, deterministic to seed, and
trivial to extend.  The auxiliary `marketing_page_section` table
normalises one row per logical section purely so analytics queries
have something to aggregate ("how many pages carry an FAQ?", etc.).

Determinism rules:
  * Insertion order is `sorted(MARKETING_PAGES)` so SQLite ROWIDs are stable.
  * No `datetime.utcnow()` or random salts — `mirror_now()` is fine because
    the model already declares it as the column default and we don't
    override it here.
  * No bcrypt / werkzeug random hashes — these are content rows, no auth.
  * `json.dumps(..., sort_keys=True, separators=(',', ':'))` so the blob
    bytes are stable across Python versions / hash randomisation.
"""

import json


# ---------------------------------------------------------------------------
# Real content harvested from github.com via Tavily (2026-05-27).
# We keep the originals verbatim, then layer them onto the legacy
# hand-written copy so we stay byte-compatible with WebVoyager answers that
# reference the old strings (e.g. "200+ token formats", "Forbes 100").
# ---------------------------------------------------------------------------

# Pulled from https://github.com/features/copilot — verbatim Tavily extract.
_REAL_COPILOT_HERO = (
    "Your AI accelerator for every workflow, from the editor to the "
    "enterprise. Choose from leading LLMs optimized for speed, accuracy, "
    "or cost. Use GitHub Copilot, your own custom agents, or third-party "
    "ones you already rely on. Copilot works where you do — in GitHub, "
    "your IDE, project tools, chat apps, and custom MCP servers."
)
_REAL_COPILOT_FAQ_GENERAL = (
    "GitHub Copilot transforms the developer experience. Backed by the "
    "leaders in AI, GitHub Copilot provides contextualized assistance "
    "throughout the software development lifecycle, from inline "
    "suggestions and chat assistance in the IDE to code explanations and "
    "answers to docs in GitHub and more."
)

# Pulled from https://github.com/features/actions — verbatim.
_REAL_ACTIONS_HERO = (
    "Automate your workflow from idea to production. GitHub Actions makes "
    "it easy to automate all your software workflows, now with world-class "
    "CI/CD. Build, test, and deploy your code right from GitHub."
)

# Pulled from https://github.com/enterprise — verbatim.
_REAL_ENTERPRISE_HERO = (
    "The AI-powered developer platform for the agent-ready enterprise. "
    "Bring your DevOps together on one secure platform built for speed, "
    "scale, and the agent-driven future of software."
)
_REAL_ENTERPRISE_CUSTOMERS = [
    {"company": "Mercado Libre",
     "quote": "Mercado Libre developers code 50% faster with GitHub Copilot."},
    {"company": "Wayfair",
     "quote": "Wayfair migrates 15,000 repositories to GitHub, saving "
              "$150,000 a year."},
    {"company": "TELUS",
     "quote": "TELUS saves $16.9 million by unifying DevOps on GitHub."},
]

# Pulled from https://github.com/education — verbatim.
_REAL_EDUCATION_HERO = (
    "Empowering the next generation of developers. GitHub Education "
    "bridges the gap between coding education and a tech career, and is "
    "accessible to everyone globally at no cost."
)
_REAL_EDUCATION_STATS = [
    {"n": "5 million", "label": "students",
     "body": "Connect with millions of peers who've expanded their skills "
             "through GitHub Education."},
    {"n": "200K", "label": "verified educators",
     "body": "Collaborate with educators around the world who enhance "
             "their lesson plans and workstreams with GitHub tools."},
    {"n": "+2K", "label": "educational institutions",
     "body": "Join thousands of schools globally that incorporate GitHub "
             "into their tech curriculum."},
]
_REAL_EDUCATION_PILLARS = [
    {"role": "Students",
     "body": "Join a community where learning meets doing, with free "
             "access to the same tools professional developers use, "
             "including GitHub Copilot Student and Codespaces."},
    {"role": "Teachers",
     "body": "Connect with a community of peers, expand your teaching "
             "methods, and leverage GitHub Classroom to track and manage "
             "assignments, automate grading, and empower students."},
    {"role": "Schools",
     "body": "Enhance your technical and academic departments with "
             "real-world software solutions, thanks to free access to "
             "GitHub Enterprise."},
    {"role": "Partners",
     "body": "Expand your brand's footprint in the tech landscape and "
             "ensure the tech leaders of tomorrow know your tools by "
             "name by partnering with GitHub Education."},
]

# Pulled from https://github.com/pricing — verbatim Free/Team/Enterprise.
_REAL_PRICING_TIERS = [
    {"name": "Free", "price": "$0 USD",
     "period": "per month forever",
     "tagline": "The basics for individuals and organizations",
     "features": [
         "Host open source projects in public GitHub repositories",
         "Automated security updates via Dependabot",
         "GitHub Actions — free for public repositories",
         "GitHub Packages — free for public repositories",
         "Community support",
     ]},
    {"name": "Team", "price": "$4 USD",
     "period": "per user/month for the first 12 months",
     "tagline": "Advanced collaboration for individuals and organizations",
     "features": [
         "Required pull-request reviewers + code owners",
         "Wiki for project documentation",
         "Branch protection rules with merge restrictions",
         "Environments + protected secrets",
         "Multiple reviewers on a single PR",
     ]},
    {"name": "Enterprise", "price": "$21 USD",
     "period": "per user/month for the first 12 months",
     "tagline": "Security, compliance, and flexible deployment",
     "features": [
         "GitHub Enterprise Cloud on Microsoft Azure with data residency",
         "Push protection — block secrets before they leak",
         "Find and fix vulnerabilities before they reach production",
         "Audit log streaming to your SIEM",
         "30-day free trial; contact sales for custom quotes",
     ]},
]


# ---------------------------------------------------------------------------
# The canonical marketing page registry. Order is irrelevant here — the
# seeder always iterates `sorted(MARKETING_PAGES)` so insertion is stable.
# ---------------------------------------------------------------------------

MARKETING_PAGES = {





    # ───── /features/code-scanning ──────────────────────────────
    'features/code-scanning': {
        'template': 'mp_feature_code_scanning.html',
        'title': 'Code scanning · CodeQL',
        'eyebrow': 'GitHub Advanced Security',
        'headline': 'Find vulnerabilities in your code before they ship.',
        'subtitle': ('CodeQL is the semantic analysis engine that powers '
                     'GitHub Code Scanning. Write queries once, run them '
                     'across every PR and every default-branch update.'),
        'source_url': 'https://github.com/features/security/code',
        'data': {
            'alert_rows': [
                {'sev': 'critical', 'rule': 'js/sql-injection',
                 'file': 'src/db/query.ts:42',
                 'msg': 'User-controlled SQL string flows into db.query()'},
                {'sev': 'high', 'rule': 'js/xss',
                 'file': 'src/views/render.ts:118',
                 'msg': 'Reflected XSS via unescaped req.query.q'},
                {'sev': 'high', 'rule': 'py/path-injection',
                 'file': 'app/files.py:23',
                 'msg': 'Path traversal via os.path.join(user_input, ...)'},
                {'sev': 'medium', 'rule': 'java/weak-crypto',
                 'file': 'src/main/Hasher.java:9',
                 'msg': 'MD5 used for password hashing — switch to bcrypt'},
                {'sev': 'low', 'rule': 'go/log-injection',
                 'file': 'pkg/server/log.go:55',
                 'msg': 'Untrusted input written to structured log'},
            ],
            'languages': ['C', 'C++', 'C#', 'Go', 'Java', 'JavaScript',
                          'TypeScript', 'Kotlin', 'Python', 'Ruby', 'Swift'],
            'vendor_logos': ['Snyk', 'Semgrep', 'Trivy', 'Checkmarx',
                             'Veracode', 'Sonatype', 'Aqua', 'Wiz'],
            'pipeline': [
                ('Default setup',
                 'One-click on the Security tab. We pick the right '
                 'languages, queries, and runner.'),
                ('Advanced setup',
                 'Bring your own workflow file. Pin a CodeQL version, '
                 'exclude paths, schedule nightly scans.'),
                ('PR feedback',
                 'New alerts show up as PR review comments. Block merge '
                 'with branch protection if needed.'),
            ],
        },
    },

    # ───── /features/secret-scanning ────────────────────────────
    'features/secret-scanning': {
        'template': 'mp_feature_secret_scanning.html',
        'title': 'Secret scanning',
        'eyebrow': 'GitHub Advanced Security',
        'headline': 'Stop leaked credentials before they reach production.',
        'subtitle': ('GitHub scans every push for 200+ token formats from '
                     '100+ partners — AWS, Stripe, OpenAI, Slack, and more '
                     '— and notifies the provider so they can revoke.'),
        'source_url': 'https://github.com/features/security/code',
        'data': {
            'alerts': [
                {'token': 'AWS Access Key', 'pattern': 'AKIA[0-9A-Z]{16}',
                 'partner': 'Amazon Web Services', 'revoke': 'automatic'},
                {'token': 'Stripe Live Secret', 'pattern': 'sk_live_[A-Za-z0-9]{24,}',
                 'partner': 'Stripe', 'revoke': 'automatic'},
                {'token': 'OpenAI API Key', 'pattern': 'sk-[A-Za-z0-9]{48}',
                 'partner': 'OpenAI', 'revoke': 'manual'},
                {'token': 'Slack Bot Token', 'pattern': 'xoxb-[0-9-A-Za-z]+',
                 'partner': 'Slack Technologies', 'revoke': 'automatic'},
                {'token': 'GitHub PAT', 'pattern': 'ghp_[A-Za-z0-9]{36}',
                 'partner': 'GitHub', 'revoke': 'automatic'},
                {'token': 'Anthropic API Key', 'pattern': 'sk-ant-[A-Za-z0-9]+',
                 'partner': 'Anthropic', 'revoke': 'manual'},
            ],
            'providers_grid': [
                'AWS', 'Azure', 'GCP', 'Stripe', 'Twilio', 'SendGrid',
                'OpenAI', 'Anthropic', 'Slack', 'Discord', 'Datadog',
                'PagerDuty', 'New Relic', 'Sentry', 'GitHub', 'GitLab',
                'Atlassian', 'NPM', 'PyPI', 'Cargo', 'RubyGems', 'Docker Hub',
            ],
            'push_protection_demo': '$ git push origin main\n' +
                'remote: error: GH013: Repository rule violations found for refs/heads/main.\n' +
                'remote: Push declined — secret detected:\n' +
                'remote:   - AWS Access Key (AKIA****************)\n' +
                'remote: To allow the push, visit the unblock URL.',
        },
    },

    # ───── /features/dependency-review ──────────────────────────
    'features/dependency-review': {
        'template': 'mp_feature_dependency_review.html',
        'title': 'Dependency review',
        'eyebrow': 'GitHub Advanced Security',
        'headline': 'See exactly what each PR adds to your supply chain.',
        'subtitle': ('Dependency review surfaces new and updated packages '
                     'introduced by a pull request, flagging known '
                     'vulnerabilities and incompatible licenses before merge.'),
        'source_url': 'https://github.com/features/security/software-supply-chain',
        'data': {
            'diff_rows': [
                {'op': '+', 'pkg': 'lodash', 'ver': '4.17.21', 'lic': 'MIT', 'cve': ''},
                {'op': '+', 'pkg': 'minimist', 'ver': '1.2.5', 'lic': 'MIT',
                 'cve': 'CVE-2021-44906 (high)'},
                {'op': '-', 'pkg': 'request', 'ver': '2.88.2', 'lic': 'Apache-2.0',
                 'cve': 'deprecated'},
                {'op': '+', 'pkg': 'axios', 'ver': '1.6.7', 'lic': 'MIT', 'cve': ''},
                {'op': '+', 'pkg': 'left-pad', 'ver': '1.3.0', 'lic': 'WTFPL',
                 'cve': 'license flagged: WTFPL not in allowlist'},
            ],
            'ecosystems': ['npm', 'pip', 'Maven', 'NuGet', 'RubyGems',
                           'Go modules', 'Cargo (Rust)', 'Composer (PHP)'],
            'gates': [
                'Severity-based merge gates configurable in branch protection',
                'License compatibility checks (MIT, Apache-2.0, GPL families)',
                'Vulnerability database refreshed daily',
            ],
        },
    },

    # ───── /features/supply-chain ───────────────────────────────
    'features/supply-chain': {
        'template': 'mp_feature_supply_chain.html',
        'title': 'Software supply chain security',
        'eyebrow': 'GitHub Advanced Security',
        'headline': 'A signed, attested supply chain — end to end.',
        'subtitle': ('Generate SBOMs, sign artifacts with Sigstore, attest '
                     'builds with SLSA, and verify provenance in deploy — '
                     'all wired into GitHub Actions.'),
        'source_url': 'https://github.com/features/security/software-supply-chain',
        'data': {
            'sbom_nodes': [
                {'pkg': 'your-app@1.4.2', 'depth': 0, 'lic': 'Apache-2.0'},
                {'pkg': 'express@4.19.2', 'depth': 1, 'lic': 'MIT'},
                {'pkg': '  body-parser@1.20.2', 'depth': 2, 'lic': 'MIT'},
                {'pkg': '  qs@6.11.0', 'depth': 2, 'lic': 'BSD-3-Clause'},
                {'pkg': 'pg@8.11.5', 'depth': 1, 'lic': 'MIT'},
                {'pkg': '  pg-types@4.0.2', 'depth': 2, 'lic': 'MIT'},
            ],
            'attestation_badges': [
                {'label': 'SLSA Build Level 3', 'colour': '#3FB950'},
                {'label': 'Sigstore signed', 'colour': '#58A6FF'},
                {'label': 'SBOM (SPDX 2.3)', 'colour': '#A371F7'},
                {'label': 'SBOM (CycloneDX 1.5)', 'colour': '#F778BA'},
                {'label': 'Provenance attested', 'colour': '#F0883E'},
            ],
            'workflow_snippet': '''- uses: actions/attest-build-provenance@v1
  with:
    subject-path: dist/your-app.tar.gz
- uses: sigstore/cosign-installer@v3
- run: cosign sign-blob --yes dist/your-app.tar.gz''',
        },
    },

    # ───── /enterprise ──────────────────────────────────────────
    'enterprise': {
        'template': 'mp_enterprise.html',
        'title': 'GitHub Enterprise',
        'eyebrow': 'GitHub Enterprise',
        'headline': 'The AI-powered developer platform for the agent-ready enterprise.',
        'subtitle': _REAL_ENTERPRISE_HERO,
        'source_url': 'https://github.com/enterprise',
        'data': {
            'customer_logos': [
                'Mercedes-Benz', 'Shopify', 'Stripe', 'Spotify', 'Airbnb',
                'Nike', 'Adobe', 'Dell', 'SAP', 'Salesforce', 'Nasdaq',
                'BBC', 'KPMG', 'Mercado Libre', 'Wayfair', 'TELUS',
                'Toyota', 'Volkswagen', 'P&G', 'Unilever',
            ],
            'testimonials': _REAL_ENTERPRISE_CUSTOMERS,
            'pillars': [
                {'h': 'Enterprise-grade by design',
                 'body': 'A centrally governed foundation that provides '
                         'the control and visibility you need to innovate '
                         'securely at scale.'},
                {'h': 'Built for your most valuable asset: your developers',
                 'body': 'GitHub transforms your engineering team into a '
                         'high-performing, AI-powered force.'},
                {'h': 'Flexibility to build your way',
                 'body': 'Tap into our ecosystem of apps, actions, and '
                         'models to accelerate innovation.'},
                {'h': 'Centralised governance',
                 'body': 'Take control with centralized governance and '
                         'automation that scales with your enterprise.'},
            ],
            'fortune_100_pct': 90,
            'cta_primary': {'href': '/contact-sales', 'label': 'Start a free trial'},
            'cta_secondary': {'href': '/pricing', 'label': 'Compare plans'},
        },
    },

    # ───── /education ───────────────────────────────────────────
    'education': {
        'template': 'mp_education.html',
        'title': 'GitHub Education',
        'eyebrow': 'GitHub Education',
        'headline': 'Empowering the next generation of developers.',
        'subtitle': _REAL_EDUCATION_HERO,
        'source_url': 'https://github.com/education',
        'data': {
            'stats': _REAL_EDUCATION_STATS,
            'pillars': _REAL_EDUCATION_PILLARS,
            'classroom_features': [
                'Create virtual classrooms with student rosters',
                'Distribute assignments to individual repos',
                'Auto-grade with GitHub Actions',
                'Track submissions and feedback inline',
            ],
            'pack_offers': [
                'GitHub Pro free while you study',
                'GitHub Copilot Student — free',
                'DigitalOcean $200 credit',
                'JetBrains all-products IDE license',
                'Namecheap .me domain free for 1 year',
                'Canva Pro free for 12 months',
            ],
            'quotes': [
                {'who': 'David J. Malan',
                 'role': 'Gordon McKay Professor, Harvard University',
                 'q': "We've partnered with GitHub Education to ensure "
                      "students receive a robust education in computer "
                      "science and practical skills, equipping them for "
                      "success in any field."},
                {'who': 'Toukir Khan',
                 'role': 'GitHub Campus Expert | CSE Undergrad 24',
                 'q': "GitHub Education is a fantastic opportunity for "
                      "students to build solid communities. The program "
                      "offers awesome tools like the GitHub Student "
                      "Developer Pack."},
            ],
        },
    },

    # ───── /security/center ─────────────────────────────────────
    'security/center': {
        'template': 'mp_security_center.html',
        'title': 'Security Center',
        'eyebrow': 'Enterprise compliance',
        'headline': 'One place for your compliance attestations.',
        'subtitle': ('Available to GitHub Enterprise Cloud customers. '
                     'Download our SOC 1, SOC 2, ISO 27001, FedRAMP, '
                     'PCI DSS, and HIPAA attestations under NDA.'),
        'source_url': 'https://github.com/security',
        'data': {
            'badges': [
                {'name': 'SOC 1 Type 2', 'audit': 'EY, annual'},
                {'name': 'SOC 2 Type 2',
                 'audit': 'Security · Availability · Confidentiality'},
                {'name': 'ISO 27001:2022', 'audit': 'BSI'},
                {'name': 'ISO 27017', 'audit': 'BSI'},
                {'name': 'ISO 27018', 'audit': 'BSI'},
                {'name': 'FedRAMP Moderate', 'audit': 'In process'},
                {'name': 'PCI DSS', 'audit': 'Self-assessed'},
                {'name': 'HIPAA', 'audit': 'Available via BAA'},
                {'name': 'GDPR + CCPA', 'audit': 'Compliant'},
            ],
            'advisory_feed': [
                {'date': '2026-05-20', 'sev': 'medium',
                 'title': 'CVE-2026-12345 — node-fetch SSRF in redirect handling'},
                {'date': '2026-05-12', 'sev': 'high',
                 'title': 'CVE-2026-10987 — log4j-style RCE in legacy '
                          'Java stack via JNDI lookup'},
                {'date': '2026-05-04', 'sev': 'low',
                 'title': 'GHSA-xxxx-2026 — Markdown rendering polyglot in '
                          'release-notes parser'},
                {'date': '2026-04-29', 'sev': 'critical',
                 'title': 'CVE-2026-09001 — Container escape via cgroup v2 '
                          'in self-hosted Actions runners (patched).'},
            ],
            'data_residency': ['United States', 'European Union',
                               'Australia', 'United Kingdom (coming Q3)'],
        },
    },


    # ───── /contact-sales ───────────────────────────────────────
    'contact-sales': {
        'template': 'mp_contact_sales.html',
        'title': 'Contact Sales',
        'eyebrow': 'GitHub Sales',
        'headline': 'Talk to our sales team.',
        'subtitle': ('See how GitHub Enterprise, Advanced Security, and '
                     'Copilot Business fit your team. A specialist will '
                     'follow up within one business day.'),
        'source_url': 'https://github.com/enterprise/contact',
        'data': {
            'form_fields': [
                {'name': 'name', 'label': 'Full name', 'type': 'text', 'req': True},
                {'name': 'work_email', 'label': 'Work email', 'type': 'email', 'req': True},
                {'name': 'company', 'label': 'Company', 'type': 'text', 'req': True},
                {'name': 'seats', 'label': 'Estimated seats',
                 'type': 'select',
                 'options': ['10–49', '50–249', '250–999', '1,000–4,999', '5,000+']},
                {'name': 'timezone', 'label': 'Your time zone',
                 'type': 'select',
                 'options': ['PST (UTC-8)', 'EST (UTC-5)', 'GMT (UTC+0)',
                             'CET (UTC+1)', 'IST (UTC+5:30)',
                             'JST (UTC+9)', 'AEST (UTC+10)']},
                {'name': 'message', 'label': 'What can we help with?',
                 'type': 'textarea'},
            ],
            'reps': [
                {'region': 'Americas', 'name': 'Jordan Reyes',
                 'tz': 'PST', 'hours': '08:00–17:00'},
                {'region': 'EMEA', 'name': 'Iris Hofmann',
                 'tz': 'CET', 'hours': '09:00–18:00'},
                {'region': 'APAC', 'name': 'Hana Ono',
                 'tz': 'JST', 'hours': '09:00–18:00'},
            ],
            'value_props': [
                'Volume discounts on Enterprise seats',
                'SSO (SAML, OIDC) and SCIM provisioning',
                'Dedicated customer success manager for >500 seats',
            ],
        },
    },

    # ───── /solutions/enterprise ────────────────────────────────
    'solutions/enterprise': {
        'template': 'mp_solutions_enterprise.html',
        'title': 'Enterprise solutions',
        'eyebrow': 'Solutions for Enterprise',
        'headline': "Built for the world's largest engineering teams.",
        'subtitle': ('GitHub Enterprise scales from 100 to 100,000 '
                     'developers with SAML SSO, audit log streaming, and '
                     'data residency in the US, EU, and Australia.'),
        'source_url': 'https://github.com/enterprise',
        'data': {
            'value_grid': [
                {'h': 'Scale', 'body': 'Used by 90% of the Fortune 100. '
                                       'Linear performance to 100k seats.'},
                {'h': 'Govern', 'body': 'SAML SSO, SCIM, audit log streaming '
                                        'to Splunk, Datadog, or your SIEM.'},
                {'h': 'Reside', 'body': 'Data residency in US, EU, AU. UK '
                                        'region coming Q3.'},
                {'h': 'Secure', 'body': 'CodeQL + secret scanning + '
                                        'dependency review on every PR.'},
            ],
            'case_links': [
                {'company': 'Mercedes-Benz',
                 'href': '/customer-stories/mercedes-benz',
                 'metric': '800+ devs ship in-vehicle software faster'},
                {'company': 'Shopify',
                 'href': '/customer-stories/shopify',
                 'metric': '55% faster code shipped with Copilot'},
            ],
            'cta_primary': {'href': '/contact-sales', 'label': 'Talk to sales'},
            'cta_secondary': {'href': '/pricing', 'label': 'Compare plans'},
        },
    },

    # ───── /solutions/team ──────────────────────────────────────
    'solutions/team': {
        'template': 'mp_solutions_team.html',
        'title': 'Solutions for teams',
        'eyebrow': 'Solutions for Teams',
        'headline': 'Ship faster with a team that trusts each other.',
        'subtitle': ('Code review, branch protection, and Actions CI for '
                     'every team size — from 5 to 500.'),
        'source_url': 'https://github.com/team',
        'data': {
            'workflows': [
                {'step': 1, 'h': 'Open a PR',
                 'body': 'Required reviewers + code owners route the right '
                         'people automatically.'},
                {'step': 2, 'h': 'Run Actions',
                 'body': '3,000 free minutes/month on Linux runners.'},
                {'step': 3, 'h': 'Protect main',
                 'body': 'Branch protection blocks merges without passing '
                         'checks + N approvals.'},
                {'step': 4, 'h': 'Deploy',
                 'body': 'Environments + team-scoped secrets gate '
                         'production rollouts.'},
            ],
            'pricing_link': '/pricing',
            'seat_grid': [
                {'size': '5–24 seats', 'rate': '$4/seat/mo'},
                {'size': '25–99 seats', 'rate': '$4/seat/mo + volume tier'},
                {'size': '100–499 seats', 'rate': 'Custom quote'},
            ],
        },
    },

    # ───── /solutions/startups ──────────────────────────────────
    'solutions/startups': {
        'template': 'mp_solutions_startups.html',
        'title': 'GitHub for Startups',
        'eyebrow': 'Solutions for Startups',
        'headline': 'Build your company on GitHub — free for 12 months.',
        'subtitle': ('20 seats of Enterprise free for one year for '
                     'verified startups, plus free Copilot Business.'),
        'source_url': 'https://github.com/enterprise/startups',
        'data': {
            'eligibility': [
                'Privately held & ≤5 years old',
                'Backed by an approved VC, accelerator, or incubator',
                'Funding ≤ $5M USD',
            ],
            'benefits': [
                {'h': '20 Enterprise seats free for 12 months',
                 'body': 'Full GitHub Enterprise Cloud — SAML SSO, SCIM, '
                         'audit log streaming included.'},
                {'h': 'Copilot Business — free seats',
                 'body': 'AI pair programmer with IP indemnity for your '
                         'whole team.'},
                {'h': 'Access to the Startups community',
                 'body': 'Private discussion forum, monthly office hours, '
                         'and intros to GitHub Field CTOs.'},
            ],
            'partners': ['Y Combinator', 'Techstars', '500 Global',
                         'a16z', 'Sequoia', 'AWS Activate',
                         'Microsoft for Startups'],
        },
    },

    # ───── /solutions/devsecops ─────────────────────────────────
    'solutions/devsecops': {
        'template': 'mp_solutions_devsecops.html',
        'title': 'DevSecOps with GitHub',
        'eyebrow': 'Solutions for DevSecOps',
        'headline': 'Shift security left without slowing developers down.',
        'subtitle': ('CodeQL, secret scanning, Dependabot, and the '
                     'Advisory Database — all wired into pull requests so '
                     'every check meets developers where they already work.'),
        'source_url': 'https://github.com/enterprise/advanced-security',
        'data': {
            'left_right': [
                ('Code', 'CodeQL semantic SAST on every PR'),
                ('Secrets', 'Push protection + auto-revoke via partners'),
                ('Dependencies', 'Dependabot opens patch PRs across 8 ecosystems'),
                ('Containers', 'Image SBOMs + base-image freshness checks'),
                ('Deploy', 'Sigstore-signed provenance gates production'),
            ],
            'languages_covered': 11,
            'partner_secrets': 200,
            'ecosystems': 8,
            'cta_primary': {'href': '/features/code-scanning', 'label': 'Explore CodeQL'},
        },
    },

    # ───── /solutions/devops ────────────────────────────────────
    'solutions/devops': {
        'template': 'mp_solutions_devops.html',
        'title': 'DevOps on GitHub',
        'eyebrow': 'Solutions for DevOps',
        'headline': 'Plan, build, ship — all in one place.',
        'subtitle': ('GitHub Issues, Actions, Packages, and Environments '
                     'give every team a single pane of glass from idea to '
                     'production.'),
        'source_url': 'https://github.com/solutions/devops',
        'data': {
            'lifecycle_stages': [
                {'name': 'Plan', 'tools': ['Issues', 'Projects', 'Roadmap']},
                {'name': 'Code', 'tools': ['Codespaces', 'Copilot', 'PR review']},
                {'name': 'Build', 'tools': ['Actions runners', 'Matrix jobs']},
                {'name': 'Test', 'tools': ['Required checks', 'Code scanning']},
                {'name': 'Release', 'tools': ['Packages', 'Environments']},
                {'name': 'Operate', 'tools': ['Deployments API', 'Webhooks']},
            ],
            'oidc_federation': ['AWS', 'Azure', 'Google Cloud',
                                'HashiCorp Vault', 'Cloudflare'],
        },
    },

    # ───── /docs ────────────────────────────────────────────────
    'docs': {
        'template': 'mp_docs.html',
        'title': 'GitHub Docs',
        'eyebrow': 'Documentation',
        'headline': 'Everything you need to build on GitHub.',
        'subtitle': ('Tutorials, reference, and guides for GitHub, '
                     'Copilot, Actions, and the REST and GraphQL APIs.'),
        'source_url': 'https://docs.github.com/',
        'data': {
            'product_grid': [
                {'name': 'GitHub.com', 'href': '/about',
                 'desc': 'Repositories, PRs, Issues, code review.'},
                {'name': 'Actions', 'href': '/features/actions',
                 'desc': 'Workflow automation, runners, marketplace.'},
                {'name': 'Codespaces', 'href': '/features/codespaces',
                 'desc': 'Cloud dev environments backed by VS Code.'},
                {'name': 'Copilot', 'href': '/features/copilot',
                 'desc': 'AI pair programmer in IDE, CLI, and chat.'},
                {'name': 'Packages', 'href': '/about',
                 'desc': 'npm, container, Maven, NuGet, RubyGems registries.'},
                {'name': 'Enterprise', 'href': '/enterprise',
                 'desc': 'SAML SSO, SCIM, audit logs, data residency.'},
                {'name': 'REST API', 'href': '/api',
                 'desc': 'Every resource as JSON over HTTPS.'},
                {'name': 'GraphQL', 'href': '/api',
                 'desc': 'Nested queries in one round-trip.'},
            ],
            'kb_articles': [
                'Quickstart: your first repository in 60 seconds',
                'Setting up SAML SSO with Okta',
                'Writing your first Actions workflow',
                'Migrating from BitBucket Cloud',
                'Using the gh CLI for everyday tasks',
            ],
        },
    },

    # ───── /api ─────────────────────────────────────────────────
    'api': {
        'template': 'mp_api.html',
        'title': 'GitHub REST & GraphQL APIs',
        'eyebrow': 'Developer platform',
        'headline': 'Build on top of GitHub.',
        'subtitle': ('A REST API and a GraphQL endpoint for every '
                     'resource on the platform.'),
        'source_url': 'https://docs.github.com/en/rest',
        'data': {
            'endpoints': [
                {'method': 'GET', 'path': '/users/{username}',
                 'desc': 'Public profile of a user'},
                {'method': 'GET', 'path': '/repos/{owner}/{repo}',
                 'desc': 'Repository metadata + stats'},
                {'method': 'POST', 'path': '/repos/{owner}/{repo}/issues',
                 'desc': 'Open a new issue'},
                {'method': 'GET', 'path': '/repos/{owner}/{repo}/pulls',
                 'desc': 'List pull requests'},
                {'method': 'POST', 'path': '/markdown',
                 'desc': 'Render Markdown server-side'},
                {'method': 'GET', 'path': '/octocat',
                 'desc': 'Easter egg ASCII art'},
            ],
            'rate_limits': [
                {'who': 'Unauthenticated', 'per_hour': '60'},
                {'who': 'Authenticated (PAT)', 'per_hour': '5,000'},
                {'who': 'GitHub App installation', 'per_hour': '15,000'},
                {'who': 'OAuth App', 'per_hour': '5,000'},
            ],
            'graphql_example': '''query {
  viewer {
    login
    repositories(first: 5, orderBy: {field: STARGAZERS, direction: DESC}) {
      nodes { name stargazerCount }
    }
  }
}''',
        },
    },

    # ───── /status ──────────────────────────────────────────────
    'status': {
        'template': 'mp_status.html',
        'title': 'GitHub Status',
        'eyebrow': 'Service status',
        'headline': 'All systems operational.',
        'subtitle': ('Real-time and historical status of every GitHub '
                     'service: Git operations, API requests, Pages, '
                     'Actions, Packages, Webhooks, Codespaces, Copilot.'),
        'source_url': 'https://www.githubstatus.com/',
        'data': {
            'services': [
                {'name': 'Git Operations', 'status': 'operational', 'uptime_90d': '99.99%'},
                {'name': 'API Requests', 'status': 'operational', 'uptime_90d': '99.98%'},
                {'name': 'Webhooks', 'status': 'operational', 'uptime_90d': '99.97%'},
                {'name': 'Issues & PRs', 'status': 'operational', 'uptime_90d': '99.99%'},
                {'name': 'GitHub Actions', 'status': 'operational', 'uptime_90d': '99.95%'},
                {'name': 'GitHub Packages', 'status': 'operational', 'uptime_90d': '99.98%'},
                {'name': 'GitHub Pages', 'status': 'operational', 'uptime_90d': '99.99%'},
                {'name': 'Codespaces', 'status': 'operational', 'uptime_90d': '99.96%'},
                {'name': 'Copilot', 'status': 'operational', 'uptime_90d': '99.92%'},
            ],
            'recent_incidents': [
                {'date': '2026-05-21', 'svc': 'Actions',
                 'title': 'Elevated queue times for Linux runners',
                 'duration': '32m', 'resolved': True},
                {'date': '2026-05-14', 'svc': 'API Requests',
                 'title': 'Higher-than-normal 5xx error rates in US-East',
                 'duration': '18m', 'resolved': True},
                {'date': '2026-04-29', 'svc': 'Codespaces',
                 'title': 'Container startup delays in EU region',
                 'duration': '47m', 'resolved': True},
            ],
        },
    },

    # ───── /blog ────────────────────────────────────────────────
    'blog': {
        'template': 'mp_blog.html',
        'title': 'The GitHub Blog',
        'eyebrow': 'Updates and stories',
        'headline': 'News from the GitHub team.',
        'subtitle': ('Product launches, engineering deep-dives, and '
                     'open-source highlights from the GitHub team.'),
        'source_url': 'https://github.blog/',
        'data': {
            'posts': [
                {'date': '2026-05-25', 'cat': 'Product',
                 'title': 'Copilot Workspace is now generally available',
                 'body': 'A task-centric way to write, refine, and ship '
                         'code with AI agents in the loop.',
                 'mins': 6},
                {'date': '2026-05-18', 'cat': 'Engineering',
                 'title': 'GitHub Actions adds Apple Silicon runners',
                 'body': 'M2-based macOS runners are 3x faster than Intel '
                         'for typical iOS test matrices.',
                 'mins': 4},
                {'date': '2026-05-10', 'cat': 'Security',
                 'title': 'CodeQL coverage extended to Kotlin and Swift',
                 'body': 'Two new languages and ~300 new queries land in '
                         'the standard CodeQL pack.',
                 'mins': 5},
                {'date': '2026-04-30', 'cat': 'Community',
                 'title': 'The 2026 State of the Octoverse',
                 'body': '180M developers, 28B contributions, AI now the '
                         'fastest-growing repo topic.',
                 'mins': 8},
            ],
            'categories': ['Product', 'Engineering', 'Security',
                           'Community', 'AI', 'Open Source'],
        },
    },

    # ───── /contact ─────────────────────────────────────────────
    'contact': {
        'template': 'mp_contact.html',
        'title': 'Contact GitHub',
        'eyebrow': 'Help',
        'headline': 'How can we help?',
        'subtitle': ('Reach billing, sales, abuse, security, or community '
                     'support — every team has a dedicated channel.'),
        'source_url': 'https://support.github.com/',
        'data': {
            'channels': [
                {'h': 'Billing', 'body': 'Open Settings → Billing on your account.',
                 'href': '/settings/profile'},
                {'h': 'Sales', 'body': 'For Enterprise and >50-seat quotes.',
                 'href': '/contact-sales'},
                {'h': 'Security', 'body': 'security@github.com — PGP-encrypted '
                                            'reports welcome.', 'href': '/security/center'},
                {'h': 'Abuse',
                 'body': 'support.github.com/contact/report-abuse for spam, '
                         'harassment, or DMCA.',
                 'href': '/about'},
                {'h': 'Community Forum',
                 'body': 'Peer-to-peer help on github.community.',
                 'href': '/about'},
            ],
            'response_times': [
                ('Free', '48–72 hr community'),
                ('Pro', '24 hr business days'),
                ('Team', '8 hr business hours'),
                ('Enterprise', '1 hr P1, 8 hr P2'),
            ],
        },
    },

    # ───── /privacy ─────────────────────────────────────────────
    'privacy': {
        'template': 'mp_privacy.html',
        'title': 'GitHub Privacy Statement',
        'eyebrow': 'Legal',
        'headline': 'Your privacy matters to us.',
        'subtitle': ('We process your data to provide the GitHub services. '
                     'We are SOC 2 audited and GDPR + CCPA compliant.'),
        'source_url': 'https://docs.github.com/en/site-policy/privacy-policies',
        'data': {
            'toc': [
                ('what', 'What data we collect'),
                ('how', 'How we use data'),
                ('share', 'Who we share it with'),
                ('rights', 'Your rights'),
                ('contact', 'Contact privacy@github.com'),
            ],
            'principles': [
                'We never sell your personal data.',
                'Cookies for analytics are opt-in in the EU/EEA.',
                'Account deletion is a one-click action in Settings.',
                'GDPR + CCPA data subject requests honoured within 30 days.',
                'SOC 2 Type II audited every year by an independent firm.',
            ],
            'data_categories': [
                {'cat': 'Account', 'examples': 'username, email, password hash'},
                {'cat': 'Usage', 'examples': 'pages viewed, API calls, runner minutes'},
                {'cat': 'Content', 'examples': 'repos, issues, PRs, comments'},
                {'cat': 'Billing', 'examples': 'company name, tax ID, last 4 of card'},
            ],
        },
    },

    # ───── /terms ───────────────────────────────────────────────
    'terms': {
        'template': 'mp_terms.html',
        'title': 'GitHub Terms of Service',
        'eyebrow': 'Legal',
        'headline': 'The rules of the road.',
        'subtitle': ('By using GitHub you agree to the Terms of Service, '
                     'the Acceptable Use Policies, and the Privacy '
                     'Statement.'),
        'source_url': 'https://docs.github.com/en/site-policy/github-terms',
        'data': {
            'sections': [
                {'h': '1. Account terms',
                 'body': 'You must be at least 13 years old. You are '
                         'responsible for the security of your account.'},
                {'h': '2. Acceptable use',
                 'body': 'No spam, no malware distribution, no harassment, '
                         'no doxxing. See the full Acceptable Use Policies '
                         'for exhaustive examples.'},
                {'h': '3. User-generated content',
                 'body': 'You retain ownership of the content you post. '
                         'You grant GitHub a license to host, display, and '
                         'transmit it as needed to operate the service.'},
                {'h': '4. Payment & cancellation',
                 'body': 'Paid plans renew monthly or annually. '
                         'Cancellation is effective at the end of the '
                         'current billing period.'},
                {'h': '5. Termination',
                 'body': 'You can delete your account at any time. We can '
                         'suspend or terminate accounts that violate the '
                         'Acceptable Use Policies.'},
                {'h': '6. Disclaimers',
                 'body': 'The service is provided "as is". No warranty.'},
                {'h': '7. Governing law',
                 'body': 'These terms are governed by the laws of the '
                         'State of California, USA.'},
            ],
            'related': [
                '/privacy',
                'https://docs.github.com/en/site-policy/acceptable-use-policies',
                'https://docs.github.com/en/site-policy/github-corporate-terms-of-service',
            ],
        },
    },



    # ───── /actions/learn (NEW route — Actions learning paths) ──
    'actions/learn': {
        'template': 'mp_actions_learn.html',
        'title': 'Learn GitHub Actions',
        'eyebrow': 'GitHub Skills',
        'headline': 'Workflow automation, learned by doing.',
        'subtitle': ('Three tutorial tracks — Beginner, Matrix builds, and '
                     'Self-hosted runners — each with copy-pasteable '
                     'workflow files and a starter repo.'),
        'source_url': 'https://docs.github.com/en/actions/learn-github-actions',
        'data': {
            'tracks': [
                {'level': 'Beginner', 'mins': 30,
                 'lessons': ['Hello, world workflow',
                             'Triggers: push, PR, schedule',
                             'Reusable actions from the marketplace']},
                {'level': 'Matrix builds', 'mins': 45,
                 'lessons': ['Matrix syntax', 'Excluding combinations',
                             'Cross-platform npm test']},
                {'level': 'Self-hosted runners', 'mins': 60,
                 'lessons': ['Registering a runner',
                             'Auto-scaling on Kubernetes',
                             'Securing the runner network']},
            ],
            'starter_workflows': [
                {'name': 'Node.js CI', 'yaml': '''on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: npm ci && npm test'''},
                {'name': 'Python lint',
                 'yaml': '''on: [push]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install ruff && ruff check .'''},
                {'name': 'Container publish',
                 'yaml': '''on:
  push:
    tags: ["v*"]
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - run: docker build -t ghcr.io/${{ github.repository }}:${{ github.ref_name }} .'''},
            ],
        },
    },
}


# ---------------------------------------------------------------------------
# Section decomposition — feeds the auxiliary marketing_page_section table
# for byte-deterministic auditing.  We pick a stable handful of kinds per
# page (hero is always present; the rest are derived from the data blob's
# top-level keys in alphabetical order).
# ---------------------------------------------------------------------------

def _section_kinds_for(data: dict):
    """Return a sorted list of (kind, title, json_payload) tuples for the
    given data blob. Deterministic: sorted by key, no datetime."""
    kinds = []
    for key in sorted(data.keys()):
        # Map blob keys -> section kinds
        if 'faq' in key:
            kinds.append(('faq', key, data[key]))
        elif 'grid' in key or key.endswith('_logos') or 'pillar' in key \
                or key == 'pillars' or 'pack_offers' in key:
            kinds.append(('grid', key, data[key]))
        elif 'table' in key or 'matrix' in key:
            kinds.append(('table', key, data[key]))
        elif 'cta' in key:
            kinds.append(('cta', key, data[key]))
        elif 'logos' in key or 'logo_wall' in key or 'customer_logos' in key:
            kinds.append(('logo_wall', key, data[key]))
        elif 'pipeline' in key or 'workflow' in key or 'diagram' in key \
                or 'stages' in key:
            kinds.append(('diagram', key, data[key]))
        elif 'yaml' in key or 'snippet' in key or 'json' == key.split('_')[-1]:
            kinds.append(('code', key, data[key]))
        elif 'testimonial' in key or 'quote' in key:
            kinds.append(('testimonial', key, data[key]))
        elif key in ('bullets', 'value_props', 'principles'):
            kinds.append(('bullets', key, data[key]))
        else:
            # Generic "hero" or freeform — bucket everything else as
            # `grid` so it ends up in the table at least once.
            kinds.append(('grid', key, data[key]))
    return kinds


def _jdumps(obj):
    """Deterministic JSON: sorted keys + compact separators."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False)


def seed_marketing_pages(db, MarketingPage, MarketingPageSection):
    """Seed the marketing_page + marketing_page_section tables.

    Idempotent: a sentinel-by-slug check makes re-runs no-ops, so this
    preserves byte-identical seed reset semantics. Returns the number of
    `MarketingPage` rows it created so the caller can mark the dirty flag
    for normalize_seed_db_layout().
    """
    existing = {p.slug for p in MarketingPage.query.with_entities(
        MarketingPage.slug).all()}
    created = 0
    # sorted() so SQLite ROWIDs are deterministic across processes.
    for slug in sorted(MARKETING_PAGES.keys()):
        if slug in existing:
            continue
        cfg = MARKETING_PAGES[slug]
        page = MarketingPage(
            slug=slug,
            template=cfg['template'],
            title=cfg['title'],
            eyebrow=cfg.get('eyebrow', ''),
            headline=cfg.get('headline', ''),
            subtitle=cfg.get('subtitle', ''),
            meta_description=cfg.get('meta_description',
                                     cfg.get('subtitle', ''))[:500],
            hero_image_path=cfg.get('hero_image_path', ''),
            data_json=_jdumps(cfg.get('data', {})),
            source_url=cfg.get('source_url', ''),
        )
        db.session.add(page)
        db.session.flush()   # need page.id for sections
        # Auxiliary normalised sections — sorted by section key for byte-id.
        sections = _section_kinds_for(cfg.get('data', {}))
        for pos, (kind, title, payload) in enumerate(sections):
            db.session.add(MarketingPageSection(
                page_id=page.id,
                kind=kind,
                position=pos,
                title=title,
                json_data=_jdumps(payload),
            ))
        created += 1
    if created:
        db.session.commit()
    return created


def get_marketing_page(slug, MarketingPage):
    """ORM helper used by Flask routes."""
    return MarketingPage.query.filter_by(slug=slug).first()
