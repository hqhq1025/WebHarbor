"""Coursera mirror — Phase 2 bulk seed extension.

Adds:
- 21 extra users (20 reviewer personas + 1 generic testuser)
- 55 extra partners (universities, companies, institutions)
- 280 extra courses across all 11 categories
- ~70 reviews per reviewer (1400 total)
- 60+ extra enrollments and 24+ extra saved-courses for the new reviewers

All additions are gated for idempotency and use deterministic data
(pinned bcrypt hash, fixed reference date, no `random.*` calls) so
`/reset/<site>` stays byte-identical after `seed_v2()` runs.
"""

import json
from datetime import datetime, timedelta

# bcrypt hash for "TestPass123!" — shared across mirrors so all benchmark
# users have a consistent, pinned password (no per-row salt drift).
PINNED_HASH = '$2b$12$RwAC/sfwDHtccU//A20fde.uKkZK4Ptnjjyua2l2ktwI6uysAp3Ou'

# Fixed reference timestamp used for any column that defaults to
# `datetime.utcnow`; reseeding therefore yields identical rows.
SEED_REF_DATE = datetime(2025, 11, 1, 12, 0, 0)


# ─── Reviewer personas (20) + 1 generic test user ───────────────────────────
REVIEWERS = [
    ('Maria Garcia',     'maria.garcia@example.com'),
    ('James Wilson',     'james.wilson@example.com'),
    ('Yuki Tanaka',      'yuki.tanaka@example.com'),
    ('Priya Patel',      'priya.patel@example.com'),
    ('Olusola Adebayo',  'olusola.a@example.com'),
    ('Anna Mueller',     'anna.mueller@example.com'),
    ('Ahmed Hassan',     'ahmed.hassan@example.com'),
    ('Sofia Rossi',      'sofia.rossi@example.com'),
    ('David Chen',       'david.chen@example.com'),
    ('Jennifer Lee',     'jennifer.lee@example.com'),
    ('Kwame Asante',     'kwame.asante@example.com'),
    ('Linh Nguyen',      'linh.nguyen@example.com'),
    ('Carlos Rodriguez', 'carlos.r@example.com'),
    ('Aisha Khan',       'aisha.khan@example.com'),
    ('Mei Chen',         'mei.chen@example.com'),
    ('Felix Hoffmann',   'felix.h@example.com'),
    ('Isabella Costa',   'isabella.costa@example.com'),
    ('Noah Schmidt',     'noah.schmidt@example.com'),
    ('Aria Sharma',      'aria.sharma@example.com'),
    ('Lucas Silva',      'lucas.silva@example.com'),
]
TEST_USER = ('Test User', 'testuser@example.com')


# ─── Extra partners (55) ────────────────────────────────────────────────────
# (name, slug, country, type, short_name)
NEW_PARTNERS = [
    # US universities (20)
    ('Cornell University', 'cornell', 'United States', 'university', 'Cornell'),
    ('Brown University', 'brown', 'United States', 'university', 'Brown'),
    ('Dartmouth College', 'dartmouth', 'United States', 'university', 'Dartmouth'),
    ('Carnegie Mellon University', 'cmu', 'United States', 'university', 'CMU'),
    ('Massachusetts Institute of Technology', 'mit', 'United States', 'university', 'MIT'),
    ('UCLA', 'ucla', 'United States', 'university', 'UCLA'),
    ('New York University', 'nyu', 'United States', 'university', 'NYU'),
    ('University of California, Berkeley', 'berkeley', 'United States', 'university', 'Berkeley'),
    ('Boston University', 'bu', 'United States', 'university', 'BU'),
    ('University of Wisconsin-Madison', 'wisc', 'United States', 'university', 'UW-Madison'),
    ('Penn State University', 'psu', 'United States', 'university', 'Penn State'),
    ('Northwestern University', 'northwestern', 'United States', 'university', 'Northwestern'),
    ('University of Southern California', 'usc', 'United States', 'university', 'USC'),
    ('University of Texas at Austin', 'utaustin', 'United States', 'university', 'UT Austin'),
    ('University of Notre Dame', 'notredame', 'United States', 'university', 'Notre Dame'),
    ('Tufts University', 'tufts', 'United States', 'university', 'Tufts'),
    ('Georgetown University', 'georgetown', 'United States', 'university', 'Georgetown'),
    ('Emory University', 'emory', 'United States', 'university', 'Emory'),
    ('California Institute of Technology', 'caltech', 'United States', 'university', 'Caltech'),
    ('University of Washington', 'uwashington', 'United States', 'university', 'UW'),

    # International universities (15)
    ('ETH Zürich', 'ethz', 'Switzerland', 'university', 'ETH Zürich'),
    ('École polytechnique fédérale de Lausanne', 'epfl', 'Switzerland', 'university', 'EPFL'),
    ('University of Oxford', 'oxford', 'United Kingdom', 'university', 'Oxford'),
    ('University of Cambridge', 'cambridge', 'United Kingdom', 'university', 'Cambridge'),
    ('Imperial College London', 'imperial', 'United Kingdom', 'university', 'Imperial'),
    ('KAIST', 'kaist', 'South Korea', 'university', 'KAIST'),
    ('National University of Singapore', 'nus', 'Singapore', 'university', 'NUS'),
    ('Nanyang Technological University', 'ntu', 'Singapore', 'university', 'NTU'),
    ('Hong Kong University of Science and Technology', 'hkust', 'Hong Kong', 'university', 'HKUST'),
    ('Peking University', 'pku', 'China', 'university', 'PKU'),
    ('Tsinghua University', 'tsinghua', 'China', 'university', 'Tsinghua'),
    ('University of Tokyo', 'utokyo', 'Japan', 'university', 'UTokyo'),
    ('Kyoto University', 'kyoto', 'Japan', 'university', 'Kyoto'),
    ('Sciences Po', 'sciencespo', 'France', 'university', 'Sciences Po'),
    ('HEC Paris', 'hec', 'France', 'university', 'HEC Paris'),

    # Companies (15)
    ('Apple', 'apple', 'United States', 'company', 'Apple'),
    ('Adobe', 'adobe', 'United States', 'company', 'Adobe'),
    ('Cisco', 'cisco', 'United States', 'company', 'Cisco'),
    ('Oracle', 'oracle', 'United States', 'company', 'Oracle'),
    ('Intel', 'intel', 'United States', 'company', 'Intel'),
    ('NVIDIA', 'nvidia', 'United States', 'company', 'NVIDIA'),
    ('SAP', 'sap', 'Germany', 'company', 'SAP'),
    ('Snowflake', 'snowflake', 'United States', 'company', 'Snowflake'),
    ('Databricks', 'databricks', 'United States', 'company', 'Databricks'),
    ('GitHub', 'github', 'United States', 'company', 'GitHub'),
    ('Tableau', 'tableau', 'United States', 'company', 'Tableau'),
    ('ServiceNow', 'servicenow', 'United States', 'company', 'ServiceNow'),
    ('McKinsey & Company', 'mckinsey', 'United States', 'company', 'McKinsey'),
    ('Deloitte', 'deloitte', 'United States', 'company', 'Deloitte'),
    ('JPMorgan Chase', 'jpmorgan', 'United States', 'company', 'JPMorgan'),

    # Government & institutions (5)
    ('NASA', 'nasa', 'United States', 'institution', 'NASA'),
    ('World Bank Group', 'worldbank', 'United States', 'institution', 'World Bank'),
    ('World Health Organization', 'who', 'Switzerland', 'institution', 'WHO'),
    ('UNESCO', 'unesco', 'France', 'institution', 'UNESCO'),
    ('Smithsonian Institution', 'smithsonian', 'United States', 'institution', 'Smithsonian'),
]


# ─── Course generation tables ──────────────────────────────────────────────
# Each entry: (title, category, level, course_type, partner_slug, instructor,
#              instructor_title, duration_hours, rating, enrolled,
#              is_free, is_featured, is_new, credit, skills_list,
#              sort_date)
# Built programmatically below to stay compact.

CATEGORY_COLORS = {
    'Computer Science': 'cat-cs',
    'Data Science': 'cat-ds',
    'Business': 'cat-biz',
    'Information Technology': 'cat-it',
    'Language Learning': 'cat-lang',
    'Math and Logic': 'cat-math',
    'Physical Science and Engineering': 'cat-eng',
    'Social Sciences': 'cat-soc',
    'Arts and Humanities': 'cat-arts',
    'Health': 'cat-health',
    'Personal Development': 'cat-pd',
}


def _slugify(title):
    import re
    s = re.sub(r'[^a-zA-Z0-9\s-]', '', title)
    s = re.sub(r'\s+', '-', s.strip().lower())
    return s[:200]


# (topic, primary_skill, secondary_skills_csv)
CS_TOPICS = [
    ('Algorithms and Data Structures', 'Algorithms', 'Data Structures,Big-O Analysis,Recursion'),
    ('Operating Systems Fundamentals', 'Operating Systems', 'Concurrency,Memory Management,Linux'),
    ('Computer Networks', 'Networking', 'TCP/IP,Routing,Sockets'),
    ('Cybersecurity Essentials', 'Cybersecurity', 'Threat Modeling,Cryptography,Network Security'),
    ('Cryptography Foundations', 'Cryptography', 'AES,RSA,Hashing'),
    ('Mobile App Development with iOS', 'iOS Development', 'Swift,UIKit,SwiftUI'),
    ('Android App Development with Kotlin', 'Android Development', 'Kotlin,Jetpack Compose,Mobile UX'),
    ('Full-Stack Web Development', 'Web Development', 'Node.js,React,MongoDB'),
    ('Backend Engineering with Go', 'Backend Engineering', 'Go,REST APIs,Microservices'),
    ('Cloud Native Development', 'Cloud Computing', 'Kubernetes,Docker,Helm'),
    ('Site Reliability Engineering', 'SRE', 'Monitoring,Observability,Incident Response'),
    ('DevOps with Docker and Kubernetes', 'DevOps', 'Docker,Kubernetes,CI/CD'),
    ('Software Testing and Quality', 'Software Testing', 'Unit Testing,Integration Testing,TDD'),
    ('Compilers and Language Design', 'Compilers', 'Lexing,Parsing,Code Generation'),
    ('Database Systems', 'Databases', 'SQL,Indexing,Transactions'),
    ('NoSQL and Distributed Databases', 'Distributed Systems', 'MongoDB,Cassandra,Sharding'),
    ('Distributed Systems Design', 'Distributed Systems', 'Consensus,Replication,CAP Theorem'),
    ('Functional Programming with Haskell', 'Functional Programming', 'Haskell,Monads,Type Systems'),
    ('Rust Programming Fundamentals', 'Rust', 'Ownership,Lifetimes,Concurrency'),
    ('Game Development with Unity', 'Game Development', 'Unity,C#,3D Graphics'),
    ('Game Development with Unreal Engine', 'Game Development', 'Unreal,Blueprint,Level Design'),
    ('Computer Graphics and OpenGL', 'Computer Graphics', 'OpenGL,Shaders,Rasterization'),
    ('Augmented Reality Foundations', 'AR/VR', 'ARKit,ARCore,Spatial Computing'),
    ('Blockchain and Smart Contracts', 'Blockchain', 'Ethereum,Solidity,DeFi'),
    ('Quantum Computing for Programmers', 'Quantum Computing', 'Qiskit,Quantum Gates,Algorithms'),
    ('Introduction to Software Architecture', 'Software Architecture', 'Patterns,Microservices,API Design'),
    ('Design Patterns in Java', 'Design Patterns', 'Java,OOP,SOLID'),
    ('Computer Vision with PyTorch', 'Computer Vision', 'CNNs,Object Detection,Segmentation'),
    ('Natural Language Processing with Transformers', 'NLP', 'Transformers,BERT,GPT'),
    ('Generative AI Engineering', 'Generative AI', 'LLMs,Diffusion Models,Prompt Engineering'),
    ('LLM Application Development', 'LLM Engineering', 'LangChain,RAG,Vector Databases'),
    ('Edge Computing and IoT', 'Edge Computing', 'IoT,5G,MQTT'),
    ('Web Accessibility Engineering', 'Accessibility', 'ARIA,WCAG,Inclusive Design'),
    ('Embedded Systems Programming', 'Embedded Systems', 'C,ARM,RTOS'),
    ('Robotics Programming with ROS', 'Robotics', 'ROS,SLAM,Motion Planning'),
    ('Cybersecurity Risk Management', 'Risk Management', 'Compliance,GRC,NIST CSF'),
    ('Ethical Hacking and Penetration Testing', 'Penetration Testing', 'Kali Linux,Metasploit,Burp Suite'),
    ('Secure Software Development', 'Application Security', 'OWASP,SAST,Threat Modeling'),
    ('TypeScript for Modern Web Apps', 'TypeScript', 'Generics,Types,React'),
    ('GraphQL API Design', 'GraphQL', 'Apollo,Schema Design,Federation'),
    ('Apache Kafka for Engineers', 'Apache Kafka', 'Streaming,Connect,Schema Registry'),
    ('Linux System Administration', 'Linux', 'Shell Scripting,systemd,Networking'),
    ('Software Engineering with Agile', 'Agile Software Engineering', 'Scrum,XP,Continuous Delivery'),
    ('Computer Architecture', 'Computer Architecture', 'Pipelining,Caches,ISA Design'),
]

DS_TOPICS = [
    ('Statistics for Data Science', 'Statistics', 'Hypothesis Testing,Probability,Bayesian Inference'),
    ('Time Series Forecasting', 'Time Series', 'ARIMA,Prophet,LSTM'),
    ('Causal Inference', 'Causal Inference', 'A/B Testing,Instrumental Variables,DAGs'),
    ('Feature Engineering for ML', 'Feature Engineering', 'Encoding,Scaling,Selection'),
    ('Big Data Analytics with Spark', 'Apache Spark', 'PySpark,SQL,Streaming'),
    ('Data Engineering on AWS', 'Data Engineering', 'S3,Glue,Redshift'),
    ('SQL for Data Analysts', 'SQL', 'Joins,Window Functions,Performance'),
    ('Power BI for Business Analytics', 'Power BI', 'DAX,Power Query,Dashboards'),
    ('Tableau Visual Analytics', 'Tableau', 'Calculations,LOD,Storytelling'),
    ('Data Storytelling and Visualization', 'Data Visualization', 'Storytelling,Dashboards,Charts'),
    ('Machine Learning Operations (MLOps)', 'MLOps', 'MLflow,Kubeflow,Deployment'),
    ('Recommender Systems', 'Recommender Systems', 'Collaborative Filtering,Matrix Factorization,Embeddings'),
    ('Graph Neural Networks', 'Graph ML', 'PyG,Node Embeddings,GCN'),
    ('Bayesian Methods for Machine Learning', 'Bayesian ML', 'PyMC,MCMC,Variational Inference'),
    ('Survival Analysis in R', 'Survival Analysis', 'Cox PH,Kaplan-Meier,Hazard Models'),
    ('Geospatial Data Science', 'Geospatial', 'GIS,Geopandas,Shapefiles'),
    ('Anomaly Detection at Scale', 'Anomaly Detection', 'Isolation Forest,Autoencoders,Time Series'),
    ('Experiment Design for Product Analytics', 'Product Analytics', 'A/B Testing,Power Analysis,SRM'),
    ('Data Ethics and Responsible AI', 'Responsible AI', 'Fairness,Privacy,Governance'),
    ('Snowflake for Data Engineers', 'Snowflake', 'Snowpark,Streams,Tasks'),
    ('Databricks Lakehouse Fundamentals', 'Databricks', 'Delta Lake,Unity Catalog,Spark'),
    ('NLP with spaCy and Hugging Face', 'NLP', 'spaCy,Transformers,Tokenization'),
    ('Computer Vision for Industry', 'Computer Vision', 'OpenCV,YOLO,Industrial Inspection'),
    ('Forecasting Demand with ML', 'Forecasting', 'XGBoost,Hierarchical Forecasting,Quantile Loss'),
    ('Statistical Learning with Python', 'Statistical Learning', 'scikit-learn,Regularization,Cross-Validation'),
]

BIZ_TOPICS = [
    ('Strategic Management', 'Strategy', 'Porter Five Forces,SWOT,Competitive Strategy'),
    ('Operations Management', 'Operations', 'Lean,Six Sigma,Supply Chain'),
    ('Supply Chain Analytics', 'Supply Chain', 'Inventory,Forecasting,Optimization'),
    ('Negotiation Skills', 'Negotiation', 'BATNA,Bargaining,Mediation'),
    ('Entrepreneurship Foundations', 'Entrepreneurship', 'Lean Startup,Business Models,MVP'),
    ('Innovation Management', 'Innovation', 'Design Thinking,R&D,Disruption'),
    ('Corporate Finance Essentials', 'Corporate Finance', 'NPV,Capital Structure,M&A'),
    ('Investment Management', 'Investment Management', 'Portfolio Theory,Asset Allocation,CAPM'),
    ('Financial Accounting Fundamentals', 'Financial Accounting', 'Balance Sheet,Income Statement,GAAP'),
    ('Managerial Accounting', 'Managerial Accounting', 'Cost Accounting,Budgeting,Variance Analysis'),
    ('Marketing Analytics', 'Marketing Analytics', 'Attribution,Customer Segmentation,LTV'),
    ('Brand Management', 'Brand Management', 'Positioning,Brand Equity,Storytelling'),
    ('Content Marketing Strategy', 'Content Marketing', 'SEO,Editorial Calendars,Storytelling'),
    ('Social Media Marketing', 'Social Media', 'Instagram,TikTok,LinkedIn'),
    ('Email Marketing for Growth', 'Email Marketing', 'Segmentation,Drip Campaigns,Deliverability'),
    ('Sales Operations Fundamentals', 'Sales Operations', 'CRM,Forecasting,Compensation'),
    ('Leadership and Influence', 'Leadership', 'Coaching,Vision,Change Management'),
    ('Change Management', 'Change Management', 'ADKAR,Kotter,Resistance Handling'),
    ('Organizational Behavior', 'Organizational Behavior', 'Teams,Motivation,Culture'),
    ('Talent Acquisition', 'Talent Acquisition', 'Sourcing,Interviewing,Employer Branding'),
    ('Diversity Equity and Inclusion', 'DEI', 'Inclusive Hiring,Belonging,ERG'),
    ('Product Management Fundamentals', 'Product Management', 'Discovery,Roadmaps,OKRs'),
    ('Pricing Strategy', 'Pricing Strategy', 'Value-Based Pricing,Discrimination,Bundling'),
    ('Behavioral Economics for Business', 'Behavioral Economics', 'Nudges,Decision Biases,Choice Architecture'),
    ('Real Estate Investing', 'Real Estate', 'Valuation,REITs,Capital Stacks'),
    ('FinTech Innovations', 'FinTech', 'Payments,Lending,Open Banking'),
    ('ESG and Sustainable Business', 'ESG', 'Sustainability Reporting,Carbon,Materiality'),
    ('Lean Six Sigma Green Belt', 'Lean Six Sigma', 'DMAIC,SPC,Process Mapping'),
    ('Crisis Communication', 'Crisis Communication', 'Reputation,Stakeholder Mgmt,Media'),
    ('Procurement and Sourcing', 'Procurement', 'Strategic Sourcing,Negotiation,Contracts'),
]

HEALTH_TOPICS = [
    ('Anatomy and Physiology', 'Anatomy', 'Systems,Physiology,Histology'),
    ('Epidemiology in Public Health', 'Epidemiology', 'Study Design,Bias,Confounding'),
    ('Nutrition Science', 'Nutrition', 'Macronutrients,Micronutrients,Dietary Patterns'),
    ('Mental Health First Aid', 'Mental Health', 'Crisis Response,Stigma,Resilience'),
    ('Clinical Trials Design', 'Clinical Trials', 'Phases,Randomization,Endpoints'),
    ('Health Informatics', 'Health Informatics', 'EHR,FHIR,Interoperability'),
    ('Telemedicine Implementation', 'Telemedicine', 'Telehealth Platforms,Privacy,Workflows'),
    ('Pharmacology Basics', 'Pharmacology', 'Drug Classes,Pharmacokinetics,Adverse Effects'),
    ('Genetics in Medicine', 'Medical Genetics', 'Inheritance,Mutations,Pharmacogenomics'),
    ('Vaccine Science', 'Vaccinology', 'Adjuvants,Trials,Coverage'),
    ('Aging and Geriatric Care', 'Geriatrics', 'Frailty,Cognition,Polypharmacy'),
    ('Maternal and Child Health', 'Maternal Health', 'Prenatal Care,Lactation,Infant Health'),
    ('Health Systems Strengthening', 'Health Systems', 'Financing,Governance,Workforce'),
    ('Healthcare Project Management', 'Healthcare PM', 'Lean,Stakeholders,Implementation'),
    ('Antimicrobial Resistance', 'Antimicrobial Resistance', 'Stewardship,Surveillance,One Health'),
    ('Global Surgery and Anaesthesia', 'Global Surgery', 'Access,Capacity,Outcomes'),
    ('Climate Change and Human Health', 'Climate Health', 'Heat,Vector-Borne Disease,Air Quality'),
    ('Health Behaviour Change', 'Behaviour Change', 'COM-B,Theory of Planned Behaviour,Habits'),
    ('Foundations of Patient Safety', 'Patient Safety', 'Root Cause Analysis,Just Culture,SBAR'),
    ('Health Policy Analysis', 'Health Policy', 'Cost-Effectiveness,Equity,Implementation'),
]

MATH_TOPICS = [
    ('Linear Algebra Fundamentals', 'Linear Algebra', 'Matrices,Eigenvalues,Vector Spaces'),
    ('Calculus for Engineers', 'Calculus', 'Derivatives,Integrals,Vector Calculus'),
    ('Probability and Statistics', 'Probability', 'Distributions,Bayes,Expectation'),
    ('Discrete Mathematics', 'Discrete Math', 'Sets,Graphs,Combinatorics'),
    ('Differential Equations', 'Differential Equations', 'ODE,PDE,Laplace Transforms'),
    ('Game Theory', 'Game Theory', 'Nash Equilibrium,Mechanism Design,Cooperation'),
    ('Number Theory and Cryptography', 'Number Theory', 'Modular Arithmetic,Primes,RSA'),
    ('Real Analysis', 'Real Analysis', 'Limits,Continuity,Sequences'),
    ('Mathematical Optimization', 'Optimization', 'Linear Programming,Convex Optimization,Gradient Methods'),
    ('Topology Basics', 'Topology', 'Open Sets,Continuity,Compactness'),
    ('Statistical Inference', 'Statistical Inference', 'Estimators,CIs,Likelihood'),
    ('Mathematics for Machine Learning', 'Math for ML', 'Vectors,Calculus,Probability'),
]

ENG_TOPICS = [
    ('Introduction to Mechanical Engineering', 'Mechanical Engineering', 'Statics,Dynamics,Materials'),
    ('Electric Power Systems', 'Power Systems', 'Generation,Transmission,Renewables'),
    ('Renewable Energy Technologies', 'Renewable Energy', 'Solar,Wind,Storage'),
    ('Materials Science Fundamentals', 'Materials Science', 'Crystallography,Polymers,Composites'),
    ('Thermodynamics for Engineers', 'Thermodynamics', 'Cycles,Heat Transfer,Entropy'),
    ('Fluid Mechanics', 'Fluid Mechanics', 'Bernoulli,Reynolds,Boundary Layers'),
    ('Control Systems Engineering', 'Control Systems', 'PID,State Space,Stability'),
    ('Signal Processing Foundations', 'Signal Processing', 'FFT,Filters,DSP'),
    ('Civil Engineering and Structures', 'Civil Engineering', 'Loads,Beams,Concrete Design'),
    ('Chemical Engineering Principles', 'Chemical Engineering', 'Mass Balance,Reactors,Separation'),
    ('Aerospace Propulsion', 'Aerospace', 'Jet Engines,Rockets,Combustion'),
    ('Bioengineering Foundations', 'Bioengineering', 'Biomechanics,Biosignals,Tissue'),
    ('Environmental Engineering', 'Environmental Engineering', 'Water Treatment,Air Quality,Sustainability'),
    ('Manufacturing Processes', 'Manufacturing', 'Machining,Casting,Additive'),
    ('Nuclear Physics', 'Nuclear Physics', 'Decay,Reactors,Particle Physics'),
    ('Astronomy for Beginners', 'Astronomy', 'Stars,Galaxies,Cosmology'),
    ('Climate Modelling', 'Climate Science', 'Atmospheric Physics,GCMs,Scenarios'),
]

SOC_TOPICS = [
    ('Introduction to Sociology', 'Sociology', 'Social Theory,Stratification,Institutions'),
    ('Political Theory', 'Political Science', 'Democracy,Justice,Liberty'),
    ('Comparative Politics', 'Comparative Politics', 'Regimes,Elections,Institutions'),
    ('International Relations', 'International Relations', 'Realism,Liberalism,Constructivism'),
    ('Economics 101', 'Economics', 'Supply,Demand,Markets'),
    ('Macroeconomics', 'Macroeconomics', 'GDP,Inflation,Monetary Policy'),
    ('Microeconomics', 'Microeconomics', 'Utility,Cost Curves,Game Theory'),
    ('Cultural Anthropology', 'Anthropology', 'Ethnography,Kinship,Symbolism'),
    ('Urban Studies', 'Urban Studies', 'Housing,Transit,Inequality'),
    ('Gender Studies', 'Gender Studies', 'Theory,Intersectionality,Policy'),
    ('Behavioral Science for Policy', 'Behavioral Science', 'Nudges,Field Experiments,Evaluation'),
    ('Migration and Refugee Studies', 'Migration Studies', 'Policy,Diaspora,Integration'),
]

ARTS_TOPICS = [
    ('Music Theory Fundamentals', 'Music Theory', 'Harmony,Rhythm,Counterpoint'),
    ('Music Production with Logic Pro', 'Music Production', 'Mixing,Mastering,Sound Design'),
    ('Photography Composition', 'Photography', 'Composition,Lighting,Editing'),
    ('Film History', 'Film Studies', 'Genres,Auteurs,Cinema Movements'),
    ('Creative Writing: The Short Story', 'Creative Writing', 'Plot,Character,Voice'),
    ('Philosophy of Mind', 'Philosophy', 'Consciousness,Identity,Materialism'),
    ('Ancient Greek Mythology', 'Mythology', 'Olympians,Heroes,Tragedy'),
    ('Art History: Renaissance to Modernism', 'Art History', 'Renaissance,Impressionism,Abstract Art'),
    ('Graphic Design Foundations', 'Graphic Design', 'Typography,Color,Layout'),
    ('Animation Principles', 'Animation', 'Storyboarding,Timing,Squash and Stretch'),
    ('UX Writing', 'UX Writing', 'Microcopy,Voice,Conversational UI'),
    ('Architecture Foundations', 'Architecture', 'Sketching,Models,Theory'),
]

LANG_TOPICS = [
    ('Mandarin Chinese for Beginners', 'Mandarin', 'Pinyin,Tones,Characters'),
    ('Japanese for Travelers', 'Japanese', 'Hiragana,Greetings,Travel Phrases'),
    ('Conversational French', 'French', 'Pronunciation,Travel Phrases,Grammar'),
    ('German for Beginners', 'German', 'Grammar,Articles,Cases'),
    ('Italian for Beginners', 'Italian', 'Greetings,Verbs,Phrasebook'),
    ('Portuguese for Beginners', 'Portuguese', 'Brazilian Portuguese,Verbs,Vocabulary'),
    ('Korean for Beginners', 'Korean', 'Hangul,Greetings,Sentence Structure'),
    ('Arabic for Beginners', 'Arabic', 'Alphabet,Pronunciation,Greetings'),
    ('Russian for Beginners', 'Russian', 'Cyrillic,Cases,Pronunciation'),
    ('English for Career Development', 'Business English', 'Resumes,Interviews,Email'),
    ('TOEFL Test Preparation', 'TOEFL Prep', 'Reading,Listening,Writing'),
    ('IELTS Test Preparation', 'IELTS Prep', 'Speaking,Writing,Listening'),
]

IT_TOPICS = [
    ('IT Support Specialist Foundations', 'IT Support', 'Troubleshooting,Networking,Hardware'),
    ('Network Configuration with Cisco', 'Cisco Networking', 'Routing,Switching,IOS'),
    ('Linux Server Administration', 'Linux Admin', 'systemd,SELinux,Networking'),
    ('Windows Server Administration', 'Windows Server', 'Active Directory,Group Policy,PowerShell'),
    ('Cloud Computing with Azure', 'Microsoft Azure', 'Resource Manager,Networking,Identity'),
    ('Google Cloud Platform Essentials', 'Google Cloud', 'Compute,Storage,Networking'),
    ('Enterprise SaaS Administration', 'SaaS Admin', 'SSO,SCIM,Governance'),
    ('Database Administration with PostgreSQL', 'PostgreSQL DBA', 'Replication,Tuning,Backups'),
    ('CompTIA Security+ Prep', 'Security+ Prep', 'Threats,Access Control,Cryptography'),
    ('AWS Solutions Architect Prep', 'AWS Architect Prep', 'Well-Architected,Networking,Security'),
]

PD_TOPICS = [
    ('Productivity for Knowledge Workers', 'Productivity', 'Time Management,GTD,Deep Work'),
    ('Mindfulness and Meditation', 'Mindfulness', 'Breathwork,Compassion,Stress Reduction'),
    ('Public Speaking Foundations', 'Public Speaking', 'Story,Delivery,Stage Presence'),
    ('Career Pivots in Tech', 'Career Development', 'Resume,Networking,Interviewing'),
    ('Financial Wellness', 'Personal Finance', 'Budgeting,Investing,Retirement'),
    ('Habit Formation Science', 'Habits', 'Cues,Routines,Rewards'),
    ('Critical Thinking Skills', 'Critical Thinking', 'Logic,Bias,Argumentation'),
    ('Effective Writing for the Workplace', 'Business Writing', 'Clarity,Brevity,Editing'),
]


# Partner pools per category (round-robin so partners get used).
# Use both existing partner slugs and the new ones we add.
PARTNER_POOLS = {
    'Computer Science': ['cmu', 'mit', 'berkeley', 'caltech', 'cornell', 'ethz',
                          'oxford', 'cambridge', 'imperial', 'nus', 'tsinghua',
                          'apple', 'nvidia', 'github', 'cisco', 'oracle',
                          'usc', 'utaustin', 'wisc', 'kaist'],
    'Data Science': ['cmu', 'mit', 'berkeley', 'cornell', 'nyu', 'databricks',
                      'snowflake', 'tableau', 'nvidia', 'oxford', 'hkust',
                      'imperial', 'usc', 'wisc', 'tsinghua'],
    'Business': ['hec', 'sciencespo', 'cornell', 'nyu', 'oxford', 'cambridge',
                  'mckinsey', 'deloitte', 'jpmorgan', 'servicenow',
                  'northwestern', 'usc', 'georgetown', 'emory', 'notredame'],
    'Information Technology': ['cisco', 'oracle', 'adobe', 'intel', 'sap',
                                'servicenow', 'cmu', 'wisc', 'utaustin'],
    'Language Learning': ['sciencespo', 'hec', 'utokyo', 'kyoto', 'pku',
                           'tsinghua', 'oxford', 'cambridge', 'unesco'],
    'Math and Logic': ['mit', 'caltech', 'cmu', 'oxford', 'cambridge',
                        'ethz', 'epfl', 'pku', 'tsinghua'],
    'Physical Science and Engineering': ['mit', 'caltech', 'ethz', 'epfl',
                                          'imperial', 'cmu', 'cornell', 'nasa',
                                          'utokyo', 'kyoto', 'wisc', 'utaustin'],
    'Social Sciences': ['sciencespo', 'georgetown', 'oxford', 'cambridge',
                         'northwestern', 'nyu', 'worldbank', 'unesco', 'brown',
                         'emory'],
    'Arts and Humanities': ['brown', 'tufts', 'smithsonian', 'oxford',
                             'cambridge', 'sciencespo', 'usc', 'nyu', 'dartmouth'],
    'Health': ['who', 'cornell', 'oxford', 'cambridge', 'mit', 'emory',
                'bu', 'nyu', 'utokyo', 'tufts'],
    'Personal Development': ['brown', 'dartmouth', 'cornell', 'oxford',
                              'cambridge', 'georgetown', 'nyu'],
}

# Instructor name pool — round-robin per category to get realistic variety.
INSTRUCTOR_POOLS = {
    'Computer Science': [
        ('Dr. Liam Chen',  'Associate Professor of Computer Science'),
        ('Dr. Sofia Park', 'Senior Lecturer, Computer Science'),
        ('Dr. Aarav Patel','Professor, School of Computing'),
        ('Dr. Naomi Wright','Senior Research Scientist'),
        ('Dr. Hiroshi Sato','Professor of Software Engineering'),
        ('Dr. Elena Volkov','Associate Professor, Systems'),
        ('Dr. Marcus Lee', 'Lecturer, Computer Science'),
        ('Dr. Ines Carvalho','Professor, AI Research'),
    ],
    'Data Science': [
        ('Dr. Priya Iyer', 'Professor of Data Science'),
        ('Dr. Jonas Becker','Principal Data Scientist'),
        ('Dr. Mei Wang',   'Associate Professor, Statistics'),
        ('Dr. Samuel Ade', 'Lecturer, Analytics'),
        ('Dr. Hannah Cohen','Senior Lecturer, Statistics'),
        ('Dr. Anika Rao',  'Director of Data Science'),
    ],
    'Business': [
        ('Prof. Eleanor Brooks', 'Professor of Strategy'),
        ('Prof. Henrik Olsen',   'Senior Lecturer, Marketing'),
        ('Prof. Maya Singh',     'Associate Professor of Finance'),
        ('Prof. Lucas Moreau',   'Director, Executive Programs'),
        ('Prof. Aiko Watanabe',  'Professor of Operations'),
        ('Prof. Rohan Mehta',    'Lecturer, Entrepreneurship'),
    ],
    'Information Technology': [
        ('Daniel Foster',  'Principal Cloud Architect'),
        ('Anjali Verma',   'Cloud Solutions Engineer'),
        ('Karim El Sayed', 'Senior Network Engineer'),
        ('Erika Schmidt',  'Director of IT Operations'),
    ],
    'Language Learning': [
        ('Prof. Camille Laurent',   'Senior Lecturer, Linguistics'),
        ('Prof. Diego Hernandez',   'Lecturer, Modern Languages'),
        ('Prof. Yuki Nakamura',     'Associate Professor, East Asian Studies'),
        ('Prof. Heinrich Vogel',    'Senior Lecturer, German Studies'),
    ],
    'Math and Logic': [
        ('Prof. Aditi Roy',      'Professor of Mathematics'),
        ('Prof. Stefan Novak',   'Associate Professor, Pure Maths'),
        ('Prof. Clara Bennett',  'Lecturer, Applied Mathematics'),
        ('Prof. Hugo Lefèvre',   'Senior Lecturer, Statistics'),
    ],
    'Physical Science and Engineering': [
        ('Dr. Wei Zhang',     'Professor of Engineering'),
        ('Dr. Olga Petrova',   'Associate Professor of Physics'),
        ('Dr. Rafael Diaz',    'Senior Lecturer, Mechanical Engineering'),
        ('Dr. Anika Berg',     'Research Scientist, NASA'),
        ('Dr. Tomás Costa',    'Professor of Chemical Engineering'),
    ],
    'Social Sciences': [
        ('Dr. Amara Okafor',   'Professor of Political Science'),
        ('Dr. Jonas Lindberg', 'Associate Professor of Economics'),
        ('Dr. Mariana Lopez',  'Lecturer, Sociology'),
        ('Dr. Owen Murphy',    'Senior Lecturer, Anthropology'),
    ],
    'Arts and Humanities': [
        ('Prof. Beatrice Hall',  'Professor of Art History'),
        ('Prof. Felix Tremblay', 'Senior Lecturer, Music'),
        ('Prof. Lena Petersen',  'Associate Professor of Film Studies'),
        ('Prof. Idris Ahmadi',   'Lecturer, Creative Writing'),
    ],
    'Health': [
        ('Dr. Helena Garcia',  'Professor of Public Health'),
        ('Dr. Samir Hossain',  'Senior Lecturer, Epidemiology'),
        ('Dr. Catherine Wynn', 'Associate Professor, Clinical Medicine'),
        ('Dr. Tariq Saleh',    'Researcher, Health Policy'),
    ],
    'Personal Development': [
        ('Dr. Riley Hayes',   'Coach and Lecturer, Communication'),
        ('Dr. Mira Solberg',  'Senior Lecturer, Organisational Psychology'),
        ('Dr. Owen Walsh',    'Lecturer, Career Development'),
    ],
}


# ─── Programmatic course generator ─────────────────────────────────────────
def _generate_course_specs():
    """Yield deterministic course dicts ready for ORM insertion.

    The catalog is generated by iterating (topic, partner_pool, instructor_pool)
    in lockstep so the same inputs always produce the same outputs.
    """
    sections = [
        ('Computer Science', CS_TOPICS),
        ('Data Science', DS_TOPICS),
        ('Business', BIZ_TOPICS),
        ('Health', HEALTH_TOPICS),
        ('Math and Logic', MATH_TOPICS),
        ('Physical Science and Engineering', ENG_TOPICS),
        ('Social Sciences', SOC_TOPICS),
        ('Arts and Humanities', ARTS_TOPICS),
        ('Language Learning', LANG_TOPICS),
        ('Information Technology', IT_TOPICS),
        ('Personal Development', PD_TOPICS),
    ]
    global_idx = 0
    for category, topics in sections:
        partner_pool = PARTNER_POOLS[category]
        instr_pool = INSTRUCTOR_POOLS[category]
        for t_idx, (topic, primary, sec_csv) in enumerate(topics):
            # Variant 1: Beginner Course
            yield _make_spec(topic, primary, sec_csv, category, 'Beginner', 'Course',
                              partner_pool[t_idx % len(partner_pool)],
                              instr_pool[t_idx % len(instr_pool)],
                              global_idx)
            global_idx += 1
            # Variant 2: Intermediate Course (alternate partner+instructor)
            yield _make_spec(topic, primary, sec_csv, category, 'Intermediate', 'Course',
                              partner_pool[(t_idx + 3) % len(partner_pool)],
                              instr_pool[(t_idx + 1) % len(instr_pool)],
                              global_idx)
            global_idx += 1
            # Variant 3: Specialization (only for every other topic — keeps total ~270)
            if t_idx % 2 == 0:
                yield _make_spec(topic, primary, sec_csv, category, 'Intermediate',
                                  'Specialization',
                                  partner_pool[(t_idx + 5) % len(partner_pool)],
                                  instr_pool[(t_idx + 2) % len(instr_pool)],
                                  global_idx, is_spec=True)
                global_idx += 1


def _make_spec(topic, primary, sec_csv, category, level, course_type,
               partner_slug, instr_pair, idx, is_spec=False):
    instr, instr_title = instr_pair
    if course_type == 'Specialization':
        title = f'{topic} Specialization'
        duration_text = '4 Months'
        duration_weeks = 17.4
        duration_hours = 70.0 + (idx % 30)
        enrolled = 60000 + (idx % 13) * 5000
        review_count = 5000 + (idx % 11) * 800
        rating = round(4.4 + (idx % 6) * 0.08, 1)  # 4.4-4.8
    elif level == 'Intermediate':
        title = f'Intermediate {topic}'
        duration_text = 'Approx. 22 hours'
        duration_weeks = 5.5
        duration_hours = 22.0 + (idx % 8)
        enrolled = 25000 + (idx % 17) * 2000
        review_count = 1800 + (idx % 9) * 400
        rating = round(4.3 + (idx % 7) * 0.07, 1)  # 4.3-4.7
    else:  # Beginner Course
        title = topic
        duration_text = 'Approx. 14 hours'
        duration_weeks = 3.5
        duration_hours = 14.0 + (idx % 6)
        enrolled = 40000 + (idx % 19) * 3000
        review_count = 3000 + (idx % 13) * 500
        rating = round(4.5 + (idx % 5) * 0.06, 1)  # 4.5-4.7
    slug = _slugify(title)
    if course_type == 'Specialization':
        slug = slug if slug.endswith('-specialization') else f'{slug}-specialization'
    skills = [primary] + [s.strip() for s in sec_csv.split(',') if s.strip()]
    learn = [f'Apply {primary} principles to real-world problems',
             f'Build hands-on projects using {skills[1] if len(skills) > 1 else primary}',
             f'Develop a structured approach to {topic.lower()}',
             f'Earn a shareable certificate in {primary}']
    tags = [primary.lower().replace(' ', '-')] + [
        s.lower().replace(' ', '-').replace('/', '-')
        for s in skills[1:4]
    ] + [partner_slug, level.lower()]
    is_free = (idx % 11 == 0)
    is_featured = (idx % 19 == 0)
    is_new = (idx % 7 == 0)
    credit = (course_type == 'Specialization' and idx % 5 == 0)
    description = (f'A comprehensive {course_type.lower()} in {topic}. '
                   f'Designed for {level.lower()}-level learners, this '
                   f'{"program" if is_spec else "course"} covers core concepts '
                   f'in {primary} along with hands-on practice in '
                   f'{", ".join(skills[1:3])}. '
                   f'You will finish ready to apply these skills in '
                   f'{category.lower()} settings.')
    # Day offset for sort_date — fixed reference date, spreads launches over
    # the past 18 months deterministically.
    days_back = 30 + (idx * 11) % 540
    sort_dt = SEED_REF_DATE - timedelta(days=days_back)
    sort_date = sort_dt.strftime('%Y-%m-%d')
    return dict(
        title=title, slug=slug, partner_slug=partner_slug,
        course_type=course_type, level=level, category=category,
        duration_text=duration_text, duration_weeks=duration_weeks,
        duration_hours=duration_hours, rating=rating,
        review_count=review_count, enrolled_count=enrolled,
        is_free=is_free, has_certificate=True, credit_eligible=credit,
        instructor=instr, instructor_title=instr_title,
        description=description,
        skills=skills, what_you_learn=learn, feature_tags=tags,
        is_featured=is_featured, is_new=is_new, sort_date=sort_date,
        color_class=CATEGORY_COLORS.get(category, 'cat-cs'),
        is_spec=is_spec, primary_skill=primary,
    )


# Sub-course titles for specializations — generated per topic.
def _spec_sub_courses(spec_title, primary):
    base = spec_title.replace(' Specialization', '')
    return [
        (f'Foundations of {base}', f'Core concepts in {primary}.', 'Approx. 16 hours'),
        (f'Intermediate {base}', f'Applied {primary} techniques and tools.', 'Approx. 18 hours'),
        (f'Advanced {base}', f'Production-grade {primary} workflows.', 'Approx. 18 hours'),
        (f'{base} Capstone Project', f'End-to-end project showcasing {primary}.', 'Approx. 18 hours'),
    ]


# Course modules — 4 weeks per course (5 weeks for specializations).
def _course_modules(title, primary, weeks=4):
    base = title.replace(' Specialization', '')
    template = [
        (f'Introduction to {base}',
         f'Course orientation and key concepts in {primary}.', 4, 3, 1),
        (f'Core Techniques in {primary}',
         f'Hands-on practice with foundational {primary} workflows.', 5, 3, 2),
        (f'Applied {primary}',
         f'Real-world case studies in {base.lower()}.', 5, 4, 2),
        (f'Putting It Together',
         f'Capstone-style assignment applying {primary}.', 4, 3, 1),
        (f'Beyond {primary}',
         f'Advanced extensions and where to go next.', 4, 3, 1),
    ]
    return template[:weeks]


# ─── Review body templates ─────────────────────────────────────────────────
REVIEW_BODY_TEMPLATES = [
    "Really enjoyed {title}. {instr} explains {primary} clearly and the exercises hit the right level for me.",
    "Solid course on {primary}. The pacing in {title} felt right and I came away with practical skills.",
    "{title} was exactly what I needed to refresh {primary}. Recommended for working professionals.",
    "Great structure and well-produced videos. {title} gave me confidence to apply {primary} at work.",
    "I appreciated the project work in {title}. It tied the {primary} concepts together nicely.",
    "Took {title} as part of a career switch — the {primary} sections were the strongest.",
    "{title} is one of the better courses I've taken on {category}. Worth the time investment.",
    "The discussion forums were active and {instr} popped in occasionally. Made {title} feel collaborative.",
    "Clear, no-fluff treatment of {primary}. Finished {title} in two focused weekends.",
    "Some sections of {title} could go deeper, but overall a strong foundation in {primary}.",
    "Loved the real-world examples in {title}. The {primary} material is up to date.",
    "{title} pairs well with hands-on practice. Don't skip the optional exercises.",
    "Great refresher on {primary}. {title} is friendly to learners returning after a break.",
    "Honest review: {title} starts slow but the {primary} chapters in the middle are excellent.",
    "If you want to actually use {primary}, the labs in {title} are the best part.",
]

# Star-rating distribution — slightly skewed positive, matches real catalogs.
RATING_DISTRIBUTION = [5.0, 5.0, 5.0, 4.5, 5.0, 4.0, 5.0, 4.5, 5.0, 4.5,
                        5.0, 4.5, 4.0, 5.0, 4.5, 5.0, 5.0, 4.5, 4.0, 5.0]


# ─── Main entry ────────────────────────────────────────────────────────────
def seed_v2(db, models):
    """Run the bulk seed. Idempotent — gated on the presence of 'cornell'
    in the partners table (one of the partners we add)."""
    User    = models['User']
    Partner = models['Partner']
    Course  = models['Course']
    CourseModule = models['CourseModule']
    SubCourse    = models['SubCourse']
    Enrollment   = models['Enrollment']
    SavedCourse  = models['SavedCourse']
    Review       = models['Review']

    if Partner.query.filter_by(slug='cornell').first():
        return  # already seeded

    # 1) Partners ──────────────────────────────────────────────────────────
    pid = {}
    for name, slug, country, ptype, short in NEW_PARTNERS:
        if Partner.query.filter_by(slug=slug).first():
            continue
        p = Partner(name=name, slug=slug, country=country,
                    partner_type=ptype, short_name=short)
        db.session.add(p)
        db.session.flush()
        pid[slug] = p.id
    db.session.commit()
    # Refresh pid map with the full partner table so we can attach to
    # existing partners as well as new ones.
    for p in Partner.query.all():
        pid[p.slug] = p.id

    # 2) Courses ────────────────────────────────────────────────────────────
    created_courses = []
    for spec in _generate_course_specs():
        if Course.query.filter_by(slug=spec['slug']).first():
            continue
        c = Course(
            title=spec['title'], slug=spec['slug'],
            partner_id=pid.get(spec['partner_slug']),
            course_type=spec['course_type'], level=spec['level'],
            category=spec['category'],
            duration_text=spec['duration_text'],
            duration_weeks=spec['duration_weeks'],
            duration_hours=spec['duration_hours'],
            rating=spec['rating'], review_count=spec['review_count'],
            enrolled_count=spec['enrolled_count'],
            is_free=spec['is_free'], has_certificate=spec['has_certificate'],
            credit_eligible=spec['credit_eligible'],
            instructor=spec['instructor'],
            instructor_title=spec['instructor_title'],
            description=spec['description'],
            skills=json.dumps(spec['skills']),
            what_you_learn=json.dumps(spec['what_you_learn']),
            feature_tags=json.dumps(spec['feature_tags']),
            is_featured=spec['is_featured'], is_new=spec['is_new'],
            sort_date=spec['sort_date'],
            color_class=spec['color_class'],
        )
        db.session.add(c)
        db.session.flush()
        # Modules
        weeks = 5 if spec['course_type'] == 'Specialization' else 4
        for w, (mtitle, mdesc, vids, reads, quizzes) in enumerate(
                _course_modules(spec['title'], spec['primary_skill'], weeks), 1):
            db.session.add(CourseModule(
                course_id=c.id, week_number=w, title=mtitle,
                description=mdesc, videos_count=vids,
                readings_count=reads, quizzes_count=quizzes,
                video_titles=json.dumps([
                    f'Lesson {w}.1: {mtitle}',
                    f'Lesson {w}.2: Worked examples',
                    f'Lesson {w}.3: Practice exercise',
                ])))
        # Sub-courses for specializations
        if spec['course_type'] == 'Specialization':
            for i, (st, sd, sdur) in enumerate(
                    _spec_sub_courses(spec['title'], spec['primary_skill'])):
                db.session.add(SubCourse(
                    specialization_id=c.id, order_index=i + 1,
                    title=st, description=sd, duration_text=sdur))
        created_courses.append(c)
    db.session.commit()

    # 3) Reviewer users (20) + testuser ────────────────────────────────────
    user_objs = {}
    for i, (name, email) in enumerate(REVIEWERS):
        if User.query.filter_by(email=email).first():
            continue
        u = User(name=name, email=email,
                 password_hash=PINNED_HASH,
                 created_at=SEED_REF_DATE - timedelta(days=210 - i * 7))
        db.session.add(u)
        db.session.flush()
        user_objs[email] = u
    # Generic test user
    if not User.query.filter_by(email=TEST_USER[1]).first():
        u = User(name=TEST_USER[0], email=TEST_USER[1],
                 password_hash=PINNED_HASH,
                 created_at=SEED_REF_DATE - timedelta(days=60))
        db.session.add(u)
        db.session.flush()
        user_objs[TEST_USER[1]] = u
    db.session.commit()

    # 4) Reviews — ~70 per reviewer, deterministic round-robin over the
    #    full catalog (existing + new). ──────────────────────────────────
    all_courses = Course.query.order_by(Course.id).all()
    n_courses = len(all_courses)
    review_count_target = 70  # per reviewer
    for u_idx, (name, email) in enumerate(REVIEWERS):
        user = User.query.filter_by(email=email).first()
        if not user:
            continue
        # Skip if reviewer already has reviews (idempotency)
        if Review.query.filter_by(user_id=user.id).first():
            continue
        for j in range(review_count_target):
            # Hash-style index ensures spread across catalog.
            c_idx = (u_idx * 97 + j * 31 + 7) % n_courses
            course = all_courses[c_idx]
            # Avoid duplicate (user, course) pairs.
            if Review.query.filter_by(user_id=user.id,
                                       course_id=course.id).first():
                # Step linearly to find a free slot.
                step = 1
                while step < n_courses:
                    c2 = all_courses[(c_idx + step) % n_courses]
                    if not Review.query.filter_by(
                            user_id=user.id, course_id=c2.id).first():
                        course = c2
                        break
                    step += 1
            template = REVIEW_BODY_TEMPLATES[j % len(REVIEW_BODY_TEMPLATES)]
            body = template.format(
                title=course.title,
                instr=(course.instructor.split(',')[0] if course.instructor
                       else 'the instructor'),
                primary=(json.loads(course.skills or '[]')[0]
                         if course.skills and course.skills != '[]'
                         else course.category),
                category=course.category or 'this field',
            )
            rating = RATING_DISTRIBUTION[(u_idx + j) % len(RATING_DISTRIBUTION)]
            created = SEED_REF_DATE - timedelta(days=10 + (u_idx * 11 + j * 3) % 300)
            db.session.add(Review(
                user_id=user.id, course_id=course.id,
                rating=rating, body=body, created_at=created))
        db.session.commit()

    # 5) Extra enrollments — each reviewer gets 3 enrollments (60 total) ──
    for u_idx, (_, email) in enumerate(REVIEWERS):
        user = User.query.filter_by(email=email).first()
        if not user:
            continue
        if Enrollment.query.filter_by(user_id=user.id).first():
            continue
        for k in range(3):
            c_idx = (u_idx * 53 + k * 89 + 17) % n_courses
            course = all_courses[c_idx]
            if Enrollment.query.filter_by(user_id=user.id,
                                           course_id=course.id).first():
                continue
            db.session.add(Enrollment(
                user_id=user.id, course_id=course.id,
                progress=(u_idx * 13 + k * 27) % 95 + 5,
                enrolled_at=SEED_REF_DATE - timedelta(
                    days=20 + (u_idx * 7 + k * 13) % 180)))
    db.session.commit()

    # 6) Extra saved courses — each reviewer gets 1-2 saved (~30 total) ───
    for u_idx, (_, email) in enumerate(REVIEWERS):
        user = User.query.filter_by(email=email).first()
        if not user:
            continue
        if SavedCourse.query.filter_by(user_id=user.id).first():
            continue
        save_n = 1 + (u_idx % 2)  # alternates 1, 2
        for k in range(save_n):
            c_idx = (u_idx * 71 + k * 41 + 23) % n_courses
            course = all_courses[c_idx]
            if SavedCourse.query.filter_by(user_id=user.id,
                                            course_id=course.id).first():
                continue
            db.session.add(SavedCourse(
                user_id=user.id, course_id=course.id,
                saved_at=SEED_REF_DATE - timedelta(
                    days=5 + (u_idx * 9 + k * 19) % 120)))
    db.session.commit()

    print(f"  + seed_v2: partners={Partner.query.count()}, "
          f"courses={Course.query.count()}, "
          f"users={User.query.count()}, "
          f"reviews={Review.query.count()}, "
          f"enrollments={Enrollment.query.count()}, "
          f"saved={SavedCourse.query.count()}")


# ───────────────────────────────────────────────────────────────────────────
# seed_v3 — R2 catalog expansion (Advanced / Pro-Cert / Guided-Project /
# extra Specialization variants) targeting 1200+ total courses. Idempotent.
# ───────────────────────────────────────────────────────────────────────────

# Sub-2-hour guided projects need duration_hours < 2 so the
# `duration=less_2_hours` filter actually returns rows.
GUIDED_PROJECT_HOURS = 1.5
GUIDED_PROJECT_WEEKS = 0.5

# Extra degrees: each tuple is
# (title, slug, partner_slug, degree_type, category, deadline, hours_offset)
EXTRA_DEGREES = [
    ('Bachelor of Science in Computer Science',
     'bsc-computer-science-illinois', 'uiuc', 'Bachelor',
     'Computer Science', '', 1300),
    ('Bachelor of Arts in Liberal Studies',
     'bachelor-liberal-studies', 'georgetown', 'Bachelor',
     'Arts and Humanities', '', 1280),
    ('Bachelor of Science in General Business',
     'bachelor-general-business', 'utaustin', 'Bachelor',
     'Business', '', 1240),
    ('Bachelor of Science in Marketing',
     'bachelor-marketing', 'asu', 'Bachelor',
     'Business', '', 1260),
    ('Master of Business Administration (iMBA)',
     'master-imba-illinois', 'uiuc', 'Master',
     'Business', '', 580),
    ('Master of Public Health',
     'master-public-health-michigan', 'umich', 'Master',
     'Health', '', 540),
    ('Master of Science in Data Science',
     'master-data-science-cuboulder', 'cuboulder', 'Master',
     'Data Science', '', 720),
    ('Master of Science in Electrical Engineering',
     'master-electrical-engineering', 'cuboulder', 'Master',
     'Physical Science and Engineering', '', 720),
    ('Master of Advanced Study in Engineering Management',
     'master-advanced-engineering-management', 'gatech',
     'MasterAdvancedStudy', 'Physical Science and Engineering',
     'June 30, 2026', 760),
    ('Master of Advanced Study in Sustainable Engineering',
     'master-advanced-sustainable-engineering', 'gatech',
     'MasterAdvancedStudy', 'Physical Science and Engineering',
     'September 15, 2026', 760),
    ('Master of Computer and Information Technology',
     'master-mcit-pennsylvania', 'upenn', 'Master',
     'Computer Science', '', 700),
    ('Master of Innovation and Entrepreneurship',
     'master-innovation-entrepreneurship', 'hec', 'Master',
     'Business', '', 540),
]


def _section_iter():
    """Yield (category, topics_list) tuples — must match _generate_course_specs."""
    return [
        ('Computer Science', CS_TOPICS),
        ('Data Science', DS_TOPICS),
        ('Business', BIZ_TOPICS),
        ('Health', HEALTH_TOPICS),
        ('Math and Logic', MATH_TOPICS),
        ('Physical Science and Engineering', ENG_TOPICS),
        ('Social Sciences', SOC_TOPICS),
        ('Arts and Humanities', ARTS_TOPICS),
        ('Language Learning', LANG_TOPICS),
        ('Information Technology', IT_TOPICS),
        ('Personal Development', PD_TOPICS),
    ]


def _v3_specs():
    """Yield additional deterministic course dicts on top of seed_v2 output.

    For every topic we add up to 4 extra variants:
      * Advanced course             (always; +N)
      * Hands-On beginner course    (always; alternate partner; +N)
      * Professional Certificate    (every 3rd topic; +~N/3)
      * Guided Project (< 2 hrs)    (every 2nd topic; +~N/2)
    Slugs are deterministic; collisions are skipped at insert time.
    """
    counter = 0
    for category, topics in _section_iter():
        partner_pool = PARTNER_POOLS[category]
        instr_pool = INSTRUCTOR_POOLS[category]
        n_p = len(partner_pool)
        n_i = len(instr_pool)
        for t_idx, (topic, primary, sec_csv) in enumerate(topics):
            # ── Advanced Course ────────────────────────────────────────────
            yield _v3_make(
                title=f'Advanced {topic}',
                slug=_slugify(f'advanced-{topic}'),
                course_type='Course', level='Advanced',
                category=category, topic=topic,
                primary=primary, sec_csv=sec_csv,
                partner_slug=partner_pool[(t_idx + 4) % n_p],
                instr_pair=instr_pool[(t_idx + 3) % n_i],
                idx=counter, duration_hours=28.0, duration_weeks=6.5,
                duration_text='Approx. 28 hours',
                base_enrolled=18000, base_reviews=1200, rating_base=4.4,
                module_weeks=5,
            )
            counter += 1
            # ── Hands-On beginner course (alternate partner) ───────────────
            yield _v3_make(
                title=f'Hands-On {topic}',
                slug=_slugify(f'hands-on-{topic}'),
                course_type='Course', level='Beginner',
                category=category, topic=topic,
                primary=primary, sec_csv=sec_csv,
                partner_slug=partner_pool[(t_idx + 6) % n_p],
                instr_pair=instr_pool[(t_idx + 5) % n_i],
                idx=counter, duration_hours=12.0, duration_weeks=3.0,
                duration_text='Approx. 12 hours',
                base_enrolled=32000, base_reviews=2400, rating_base=4.6,
                module_weeks=3,
            )
            counter += 1
            # ── Professional Certificate (every 3rd topic) ─────────────────
            if t_idx % 3 == 0:
                yield _v3_make(
                    title=f'{topic} Professional Certificate',
                    slug=_slugify(f'{topic}-professional-certificate'),
                    course_type='Professional Certificate', level='Beginner',
                    category=category, topic=topic,
                    primary=primary, sec_csv=sec_csv,
                    partner_slug=partner_pool[(t_idx + 1) % n_p],
                    instr_pair=instr_pool[(t_idx + 4) % n_i],
                    idx=counter, duration_hours=110.0, duration_weeks=26.0,
                    duration_text='6 Months',
                    base_enrolled=85000, base_reviews=6500, rating_base=4.6,
                    module_weeks=5, is_cert=True,
                )
                counter += 1
            # ── Guided Project (< 2 hours) (every 2nd topic) ───────────────
            if t_idx % 2 == 1:
                yield _v3_make(
                    title=f'Build a {primary} Project',
                    slug=_slugify(f'build-a-{primary}-project-{t_idx}'),
                    course_type='Guided Project', level='Beginner',
                    category=category, topic=topic,
                    primary=primary, sec_csv=sec_csv,
                    partner_slug=partner_pool[(t_idx + 2) % n_p],
                    instr_pair=instr_pool[(t_idx + 6) % n_i],
                    idx=counter,
                    duration_hours=GUIDED_PROJECT_HOURS,
                    duration_weeks=GUIDED_PROJECT_WEEKS,
                    duration_text='Less Than 2 Hours',
                    base_enrolled=4500, base_reviews=180, rating_base=4.5,
                    module_weeks=1, is_proj=True,
                )
                counter += 1
            # ── Foundations Course (every topic, alternate angle) ──────────
            yield _v3_make(
                title=f'Foundations of {topic}',
                slug=_slugify(f'foundations-of-{topic}'),
                course_type='Course', level='Beginner',
                category=category, topic=topic,
                primary=primary, sec_csv=sec_csv,
                partner_slug=partner_pool[(t_idx + 7) % n_p],
                instr_pair=instr_pool[(t_idx + 2) % n_i],
                idx=counter, duration_hours=10.0, duration_weeks=2.5,
                duration_text='Approx. 10 hours',
                base_enrolled=22000, base_reviews=1800, rating_base=4.5,
                module_weeks=3,
            )
            counter += 1


def _v3_make(*, title, slug, course_type, level, category, topic, primary,
             sec_csv, partner_slug, instr_pair, idx, duration_hours,
             duration_weeks, duration_text, base_enrolled, base_reviews,
             rating_base, module_weeks, is_cert=False, is_proj=False):
    instr, instr_title = instr_pair
    rating = round(rating_base + (idx % 5) * 0.06, 2)
    skills = [primary] + [s.strip() for s in sec_csv.split(',') if s.strip()]
    learn = [
        f'Apply {primary} to advanced real-world problems' if level == 'Advanced'
        else f'Build hands-on competence in {primary}',
        f'Use {skills[1] if len(skills) > 1 else primary} effectively',
        f'Practice {topic.lower()} workflows end-to-end',
        f'Earn a shareable {("certificate" if not is_proj else "completion badge")} in {primary}',
    ]
    tags = [primary.lower().replace(' ', '-')] + [
        s.lower().replace(' ', '-').replace('/', '-')
        for s in skills[1:4]
    ] + [partner_slug, level.lower()]
    if is_cert:
        tags.append('professional-certificate')
    if is_proj:
        tags.append('guided-project')
        tags.append('under-2-hours')
    is_free = (idx % 13 == 0) and not is_cert
    is_featured = (idx % 23 == 0)
    is_new = (idx % 5 == 0)
    credit = is_cert and (idx % 4 == 0)
    description = (
        f'A {level.lower()}-level {course_type.lower()} in {topic}. '
        f'Covers {primary} with hands-on practice in '
        f'{", ".join(skills[1:3]) if len(skills) > 1 else primary}. '
        f'{"Short, project-first format ideal for a focused study session." if is_proj else "Structured for working professionals and curious learners."}'
    )
    days_back = 25 + (idx * 13) % 520
    sort_dt = SEED_REF_DATE - timedelta(days=days_back)
    sort_date = sort_dt.strftime('%Y-%m-%d')
    enrolled = base_enrolled + (idx % 19) * 1500
    review_count = base_reviews + (idx % 11) * 320
    return dict(
        title=title, slug=slug, partner_slug=partner_slug,
        course_type=course_type, level=level, category=category,
        duration_text=duration_text, duration_weeks=duration_weeks,
        duration_hours=duration_hours, rating=rating,
        review_count=review_count, enrolled_count=enrolled,
        is_free=is_free, has_certificate=(not is_proj),
        credit_eligible=credit,
        instructor=instr, instructor_title=instr_title,
        description=description,
        skills=skills, what_you_learn=learn, feature_tags=tags,
        is_featured=is_featured, is_new=is_new, sort_date=sort_date,
        color_class=CATEGORY_COLORS.get(category, 'cat-cs'),
        primary_skill=primary, module_weeks=module_weeks,
        is_cert=is_cert, is_proj=is_proj,
    )


def _v3_modules(spec):
    """Generate weekly modules for a v3 course. Guided projects collapse to
    a single 'session' module; Professional Certificates fan out to 5
    pillar modules."""
    title = spec['title']
    primary = spec['primary_skill']
    base = title.replace(' Professional Certificate', '').replace(
        'Advanced ', '').replace('Hands-On ', '').replace(
        'Build a ', '').replace(' Project', '')
    if spec['is_proj']:
        return [(
            f'Session: {title}',
            f'A single 90-minute hands-on guided session building a {primary} project from scratch.',
            6, 1, 0,
            [
                f'Step 1: Set up the {primary} environment',
                f'Step 2: Implement the core {primary} logic',
                f'Step 3: Wire up the interactive demo',
                f'Step 4: Test and iterate',
                f'Step 5: Wrap-up and next steps',
                f'Bonus: Extending your {primary} project',
            ],
        )]
    if spec['is_cert']:
        return [
            (f'Foundations of {base}',
             f'Orientation: history, terminology and where {primary} fits in industry.', 5, 4, 2),
            (f'Core {primary} Skills',
             f'Hands-on practice with foundational {primary} workflows.', 6, 4, 2),
            (f'Applied {primary} in Practice',
             f'Real-world case studies and integrations with {base.lower()}.', 6, 4, 2),
            (f'{base} Capstone Project',
             f'End-to-end portfolio project showcasing {primary}.', 6, 3, 2),
            (f'Career & Certification',
             f'Interview preparation, certification prep, and next steps.', 4, 3, 1),
        ]
    if spec['level'] == 'Advanced':
        return [
            (f'Advanced Concepts in {base}',
             f'Deep dive into advanced {primary} theory and edge cases.', 5, 4, 2),
            (f'Optimisation & Scaling',
             f'Performance, scaling, and production hardening of {primary} systems.', 5, 3, 2),
            (f'Case Studies in {primary}',
             f'Industrial-scale {base.lower()} projects unpacked.', 5, 4, 2),
            (f'Research Frontiers',
             f'Current research directions in {primary}.', 4, 3, 1),
            (f'Capstone',
             f'Advanced applied project in {primary}.', 4, 3, 2),
        ]
    # Hands-On beginner default
    return [
        (f'Welcome and Setup',
         f'Course orientation and {primary} environment setup.', 4, 2, 1),
        (f'First {primary} Project',
         f'Your first end-to-end {primary} build.', 5, 3, 2),
        (f'Iterating on {base}',
         f'Refine your {primary} workflow with realistic tasks.', 4, 3, 1),
    ]


def seed_v3(db, models):
    """R2 catalog expansion. Idempotent — gated on the presence of an
    'advanced-' course in the catalog (we add hundreds)."""
    User = models['User']
    Partner = models['Partner']
    Course = models['Course']
    CourseModule = models['CourseModule']
    SubCourse = models['SubCourse']
    Enrollment = models['Enrollment']
    SavedCourse = models['SavedCourse']
    Review = models['Review']

    sentinel = Course.query.filter(
        Course.slug.like('advanced-%')).first()
    if sentinel is not None:
        return  # already seeded

    pid = {p.slug: p.id for p in Partner.query.all()}
    created = 0
    for spec in _v3_specs():
        if Course.query.filter_by(slug=spec['slug']).first():
            continue
        c = Course(
            title=spec['title'], slug=spec['slug'],
            partner_id=pid.get(spec['partner_slug']),
            course_type=spec['course_type'], level=spec['level'],
            category=spec['category'],
            duration_text=spec['duration_text'],
            duration_weeks=spec['duration_weeks'],
            duration_hours=spec['duration_hours'],
            rating=spec['rating'], review_count=spec['review_count'],
            enrolled_count=spec['enrolled_count'],
            is_free=spec['is_free'], has_certificate=spec['has_certificate'],
            credit_eligible=spec['credit_eligible'],
            instructor=spec['instructor'],
            instructor_title=spec['instructor_title'],
            description=spec['description'],
            skills=json.dumps(spec['skills']),
            what_you_learn=json.dumps(spec['what_you_learn']),
            feature_tags=json.dumps(spec['feature_tags']),
            is_featured=spec['is_featured'], is_new=spec['is_new'],
            sort_date=spec['sort_date'],
            color_class=spec['color_class'],
        )
        db.session.add(c)
        db.session.flush()
        for w, mod in enumerate(_v3_modules(spec), 1):
            if len(mod) == 6:
                mtitle, mdesc, vids, reads, quizzes, vtitles = mod
                vt_json = json.dumps(vtitles)
            else:
                mtitle, mdesc, vids, reads, quizzes = mod
                vt_json = json.dumps([
                    f'Lesson {w}.1: {mtitle}',
                    f'Lesson {w}.2: Worked examples',
                    f'Lesson {w}.3: Practice exercise',
                ])
            db.session.add(CourseModule(
                course_id=c.id, week_number=w, title=mtitle,
                description=mdesc, videos_count=vids,
                readings_count=reads, quizzes_count=quizzes,
                video_titles=vt_json))
        created += 1
    db.session.commit()

    # ── 12 extra degree programs (Task 36 + 41 ammunition) ─────────────────
    for d_idx, (title, slug, partner_slug, dtype, category, deadline,
                hours) in enumerate(EXTRA_DEGREES):
        if Course.query.filter_by(slug=slug).first():
            continue
        primary = title.split(' in ')[-1] if ' in ' in title else title
        days_back = 90 + (d_idx * 17) % 360
        sort_dt = SEED_REF_DATE - timedelta(days=days_back)
        c = Course(
            title=title, slug=slug,
            partner_id=pid.get(partner_slug),
            course_type='Degree', level='Advanced',
            category=category,
            duration_text=('2 - 4 Years' if dtype == 'Bachelor' else
                           '1 - 3 Years'),
            duration_weeks=104.0 if dtype == 'Bachelor' else 78.0,
            duration_hours=float(hours),
            rating=4.7, review_count=350 + d_idx * 25,
            enrolled_count=3500 + d_idx * 280,
            is_free=False, has_certificate=True,
            credit_eligible=True,
            instructor=f'{partner_slug.upper()} Faculty',
            instructor_title=f'Faculty, {partner_slug.upper()}',
            description=(
                f'Earn an accredited {dtype} ({title}) entirely online. '
                f'Includes live cohort sessions, project-based assignments, '
                f'and a final capstone reviewed by faculty.'),
            skills=json.dumps([primary, 'Capstone Project', 'Research Methods']),
            what_you_learn=json.dumps([
                f'Complete an accredited {dtype.lower()} in {primary}',
                f'Build a research-grade capstone in {primary}',
                f'Network with a global online cohort',
                f'Earn academic credit recognized by employers',
            ]),
            feature_tags=json.dumps([
                'degree', dtype.lower(), partner_slug,
                category.lower().replace(' ', '-'),
            ]),
            is_featured=(d_idx % 3 == 0), is_new=(d_idx % 4 == 0),
            sort_date=sort_dt.strftime('%Y-%m-%d'),
            degree_type=dtype,
            application_deadline=deadline,
            color_class=CATEGORY_COLORS.get(category, 'cat-cs'),
        )
        db.session.add(c)
        db.session.flush()
        # Degree modules: 4 high-level pillars
        for w, (mt, md) in enumerate([
            ('Year 1: Foundations',
             f'First-year coursework introducing {primary} fundamentals.'),
            ('Year 2: Applied Practice',
             f'Project-based courses applying {primary} to real problems.'),
            ('Year 3: Specialisation',
             f'Choose electives that align your {primary} concentration.'),
            ('Final Capstone',
             f'Year-long capstone supervised by {partner_slug.upper()} faculty.'),
        ], 1):
            db.session.add(CourseModule(
                course_id=c.id, week_number=w, title=mt, description=md,
                videos_count=20, readings_count=30, quizzes_count=10,
                video_titles=json.dumps([])))
        created += 1
    db.session.commit()

    print(f"  + seed_v3: added {created} courses; "
          f"total courses={Course.query.count()}")



# ═══════════════════════════════════════════════════════════════════════════
# seed_v4 — R3 catalog expansion. Targets:
#   * partners: 104 → 200+ (global universities + Fortune-500 companies +
#               international institutions across 30+ countries)
#   * courses : 1369 → 2500+ (Capstone, Coursera-Plus, Business catalog,
#               Project-Network shorts, language deep cuts, more degrees)
# Idempotent: gated on the partner slug 'iitb' (one we add).
# ═══════════════════════════════════════════════════════════════════════════

# 100 additional partners spanning 30+ countries.
NEW_PARTNERS_V4 = [
    # India (8)
    ('Indian Institute of Technology Bombay', 'iitb', 'India', 'university', 'IIT Bombay'),
    ('Indian Institute of Technology Delhi', 'iitd', 'India', 'university', 'IIT Delhi'),
    ('Indian Institute of Technology Madras', 'iitm', 'India', 'university', 'IIT Madras'),
    ('Indian Institute of Science', 'iisc', 'India', 'university', 'IISc'),
    ('Indian School of Business', 'isb', 'India', 'university', 'ISB'),
    ('Indian Institute of Management Bangalore', 'iimb', 'India', 'university', 'IIM Bangalore'),
    ('Infosys', 'infosys', 'India', 'company', 'Infosys'),
    ('Tata Consultancy Services', 'tcs', 'India', 'company', 'TCS'),
    # Brazil (3)
    ('Universidade de São Paulo', 'usp-br', 'Brazil', 'university', 'USP'),
    ('Fundação Getúlio Vargas', 'fgv', 'Brazil', 'university', 'FGV'),
    ('Itaú Unibanco', 'itau', 'Brazil', 'company', 'Itaú'),
    # Mexico (3)
    ('Tecnológico de Monterrey', 'itesm', 'Mexico', 'university', 'Tec de Monterrey'),
    ('Universidad Nacional Autónoma de México', 'unam', 'Mexico', 'university', 'UNAM'),
    ('IPADE Business School', 'ipade', 'Mexico', 'university', 'IPADE'),
    # Argentina, Chile, Colombia, Peru (4)
    ('Universidad de Buenos Aires', 'uba', 'Argentina', 'university', 'UBA'),
    ('Pontificia Universidad Católica de Chile', 'puc-cl', 'Chile', 'university', 'UC Chile'),
    ('Universidad de los Andes', 'uniandes', 'Colombia', 'university', 'Uniandes'),
    ('Pontificia Universidad Católica del Perú', 'pucp', 'Peru', 'university', 'PUCP'),
    # Spain (4)
    ('IE Business School', 'ie', 'Spain', 'university', 'IE'),
    ('IESE Business School', 'iese', 'Spain', 'university', 'IESE'),
    ('Universidad Autónoma de Madrid', 'uam-es', 'Spain', 'university', 'UAM'),
    ('Telefónica', 'telefonica', 'Spain', 'company', 'Telefónica'),
    # Italy (3)
    ('Bocconi University', 'bocconi', 'Italy', 'university', 'Bocconi'),
    ('Politecnico di Milano', 'polimi', 'Italy', 'university', 'PoliMi'),
    ('Sapienza Università di Roma', 'sapienza', 'Italy', 'university', 'Sapienza'),
    # Netherlands (3)
    ('Delft University of Technology', 'tudelft', 'Netherlands', 'university', 'TU Delft'),
    ('Erasmus University Rotterdam', 'eur', 'Netherlands', 'university', 'Erasmus'),
    ('University of Amsterdam', 'uva', 'Netherlands', 'university', 'UvA'),
    # Belgium (2)
    ('KU Leuven', 'kuleuven', 'Belgium', 'university', 'KU Leuven'),
    ('Université libre de Bruxelles', 'ulb', 'Belgium', 'university', 'ULB'),
    # Sweden (2)
    ('Karolinska Institutet', 'ki', 'Sweden', 'university', 'KI'),
    ('Lund University', 'lund', 'Sweden', 'university', 'Lund'),
    # Denmark, Norway, Finland (4)
    ('University of Copenhagen', 'ucph', 'Denmark', 'university', 'Copenhagen'),
    ('Aarhus University', 'aarhus', 'Denmark', 'university', 'Aarhus'),
    ('University of Oslo', 'uio', 'Norway', 'university', 'Oslo'),
    ('Aalto University', 'aalto', 'Finland', 'university', 'Aalto'),
    # Ireland (2)
    ('Trinity College Dublin', 'tcd', 'Ireland', 'university', 'Trinity'),
    ('University College Dublin', 'ucd', 'Ireland', 'university', 'UCD'),
    # Israel (2)
    ('Tel Aviv University', 'tau', 'Israel', 'university', 'TAU'),
    ('Technion - Israel Institute of Technology', 'technion', 'Israel', 'university', 'Technion'),
    # Russia, Poland, Czech, Greece, Portugal, Austria (6)
    ('HSE University', 'hse', 'Russia', 'university', 'HSE'),
    ('University of Warsaw', 'uw-pl', 'Poland', 'university', 'UW'),
    ('Charles University', 'cuni', 'Czech Republic', 'university', 'CUNI'),
    ('National and Kapodistrian University of Athens', 'uoa', 'Greece', 'university', 'NKUA'),
    ('Universidade de Lisboa', 'ulisboa', 'Portugal', 'university', 'ULisboa'),
    ('University of Vienna', 'univie', 'Austria', 'university', 'Vienna'),
    # New Zealand (2)
    ('University of Auckland', 'auckland', 'New Zealand', 'university', 'Auckland'),
    ('University of Otago', 'otago', 'New Zealand', 'university', 'Otago'),
    # South Africa, Egypt, Nigeria, Kenya (4)
    ('University of Cape Town', 'uct', 'South Africa', 'university', 'UCT'),
    ('American University in Cairo', 'auc', 'Egypt', 'university', 'AUC'),
    ('University of Lagos', 'unilag', 'Nigeria', 'university', 'UNILAG'),
    ('University of Nairobi', 'uon', 'Kenya', 'university', 'UoN'),
    # UAE, Saudi Arabia, Qatar (3)
    ('Khalifa University', 'khalifa', 'United Arab Emirates', 'university', 'Khalifa'),
    ('King Abdullah University of Science and Technology', 'kaust', 'Saudi Arabia', 'university', 'KAUST'),
    ('Hamad Bin Khalifa University', 'hbku', 'Qatar', 'university', 'HBKU'),
    # Turkey (1)
    ('Koç University', 'koc', 'Turkey', 'university', 'Koç'),
    # SE Asia (4)
    ('Universitas Indonesia', 'ui-id', 'Indonesia', 'university', 'UI'),
    ('Vietnam National University, Hanoi', 'vnu', 'Vietnam', 'university', 'VNU'),
    ('Chulalongkorn University', 'chula', 'Thailand', 'university', 'Chula'),
    ('University of the Philippines Diliman', 'updiliman', 'Philippines', 'university', 'UPD'),
    # China expanded (2)
    ('Fudan University', 'fudan', 'China', 'university', 'Fudan'),
    ('Shanghai Jiao Tong University', 'sjtu', 'China', 'university', 'SJTU'),
    # Korea (1)
    ('Seoul National University', 'snu', 'South Korea', 'university', 'SNU'),
    # Canada extra (2)
    ('McGill University', 'mcgill', 'Canada', 'university', 'McGill'),
    ('University of British Columbia', 'ubc', 'Canada', 'university', 'UBC'),
    # Australia extra (1)
    ('University of Tasmania', 'utas', 'Australia', 'university', 'UTAS'),
    # ── Companies (Fortune-500 + global tech) ─────────────────────────────
    ('Accenture', 'accenture', 'Ireland', 'company', 'Accenture'),
    ('Capgemini', 'capgemini', 'France', 'company', 'Capgemini'),
    ('Siemens', 'siemens', 'Germany', 'company', 'Siemens'),
    ('Bosch', 'bosch', 'Germany', 'company', 'Bosch'),
    ('Volkswagen', 'volkswagen', 'Germany', 'company', 'VW'),
    ('Mercedes-Benz', 'mercedes', 'Germany', 'company', 'Mercedes'),
    ('BMW Group', 'bmw', 'Germany', 'company', 'BMW'),
    ('Unilever', 'unilever', 'United Kingdom', 'company', 'Unilever'),
    ('Vodafone', 'vodafone', 'United Kingdom', 'company', 'Vodafone'),
    ('Shell', 'shell', 'United Kingdom', 'company', 'Shell'),
    ('HSBC', 'hsbc', 'United Kingdom', 'company', 'HSBC'),
    ('Sony', 'sony', 'Japan', 'company', 'Sony'),
    ('Toyota', 'toyota', 'Japan', 'company', 'Toyota'),
    ('Samsung', 'samsung', 'South Korea', 'company', 'Samsung'),
    ('LG', 'lg', 'South Korea', 'company', 'LG'),
    ('Tata Steel', 'tatasteel', 'India', 'company', 'Tata Steel'),
    ('Alibaba', 'alibaba', 'China', 'company', 'Alibaba'),
    ('Tencent', 'tencent', 'China', 'company', 'Tencent'),
    ('Huawei', 'huawei', 'China', 'company', 'Huawei'),
    ('Stripe', 'stripe', 'United States', 'company', 'Stripe'),
    ('Shopify', 'shopify', 'Canada', 'company', 'Shopify'),
    ('Atlassian Cloud', 'atlassian-cloud', 'Australia', 'company', 'Atlassian Cloud'),
    ('Cloudflare', 'cloudflare', 'United States', 'company', 'Cloudflare'),
    ('Datadog', 'datadog', 'United States', 'company', 'Datadog'),
    ('MongoDB', 'mongodb', 'United States', 'company', 'MongoDB'),
    ('Red Hat', 'redhat', 'United States', 'company', 'Red Hat'),
    ('Workday', 'workday', 'United States', 'company', 'Workday'),
    ('Zendesk', 'zendesk', 'United States', 'company', 'Zendesk'),
    ('HubSpot', 'hubspot', 'United States', 'company', 'HubSpot'),
    ('Booking.com', 'booking', 'Netherlands', 'company', 'Booking.com'),
    ('Spotify', 'spotify', 'Sweden', 'company', 'Spotify'),
    ('Klarna', 'klarna', 'Sweden', 'company', 'Klarna'),
    ('Ericsson', 'ericsson', 'Sweden', 'company', 'Ericsson'),
    ('Nokia', 'nokia', 'Finland', 'company', 'Nokia'),
    # ── Institutions (NGOs, govs, museums) ─────────────────────────────────
    ('United Nations', 'un', 'United States', 'institution', 'UN'),
    ('European Space Agency', 'esa', 'France', 'institution', 'ESA'),
    ('CERN', 'cern', 'Switzerland', 'institution', 'CERN'),
    ('OECD', 'oecd', 'France', 'institution', 'OECD'),
    ('International Monetary Fund', 'imf', 'United States', 'institution', 'IMF'),
    ('Asian Development Bank', 'adb', 'Philippines', 'institution', 'ADB'),
    ('African Union', 'au', 'Ethiopia', 'institution', 'AU'),
    ('Greenpeace', 'greenpeace', 'Netherlands', 'institution', 'Greenpeace'),
    ('British Museum', 'britishmuseum', 'United Kingdom', 'institution', 'British Museum'),
    ('Louvre', 'louvre', 'France', 'institution', 'Louvre'),
]


# ═══════════════════════════════════════════════════════════════════════════
# Capstone and Career-track course generation tables
# ═══════════════════════════════════════════════════════════════════════════

# 20 career roles → primary skill clusters
CAREER_ROLES = [
    ('Data Analyst', 'data-analyst', 'Data Science', 'Data Analysis',
     ['SQL', 'Tableau', 'Excel', 'Python']),
    ('Data Scientist', 'data-scientist', 'Data Science', 'Machine Learning',
     ['Python', 'Statistics', 'Machine Learning', 'Deep Learning']),
    ('Machine Learning Engineer', 'machine-learning-engineer', 'Data Science', 'ML Engineering',
     ['Python', 'TensorFlow', 'MLOps', 'Cloud Computing']),
    ('Software Engineer', 'software-engineer', 'Computer Science', 'Software Engineering',
     ['Java', 'Python', 'Git', 'System Design']),
    ('Full-Stack Web Developer', 'full-stack-web-developer', 'Computer Science', 'Web Development',
     ['JavaScript', 'React', 'Node.js', 'SQL']),
    ('Front-End Developer', 'front-end-developer', 'Computer Science', 'Front-End Development',
     ['HTML', 'CSS', 'JavaScript', 'React']),
    ('Back-End Developer', 'back-end-developer', 'Computer Science', 'Back-End Development',
     ['Python', 'Node.js', 'PostgreSQL', 'REST APIs']),
    ('Mobile App Developer', 'mobile-app-developer', 'Computer Science', 'Mobile Development',
     ['Swift', 'Kotlin', 'React Native', 'Flutter']),
    ('Cloud Architect', 'cloud-architect', 'Information Technology', 'Cloud Architecture',
     ['AWS', 'Azure', 'GCP', 'Kubernetes']),
    ('DevOps Engineer', 'devops-engineer', 'Information Technology', 'DevOps',
     ['Docker', 'Kubernetes', 'CI/CD', 'Linux']),
    ('Cybersecurity Analyst', 'cybersecurity-analyst', 'Information Technology', 'Cybersecurity',
     ['Network Security', 'SIEM', 'Penetration Testing', 'Cryptography']),
    ('IT Support Specialist', 'it-support-specialist', 'Information Technology', 'IT Support',
     ['Networking', 'Help Desk', 'Hardware', 'Windows Server']),
    ('UX Designer', 'ux-designer', 'Arts and Humanities', 'UX Design',
     ['Figma', 'User Research', 'Wireframing', 'Prototyping']),
    ('Product Manager', 'product-manager', 'Business', 'Product Management',
     ['Roadmapping', 'Stakeholder Management', 'Analytics', 'Agile']),
    ('Project Manager', 'project-manager', 'Business', 'Project Management',
     ['Agile', 'Scrum', 'Risk Management', 'Communication']),
    ('Digital Marketing Specialist', 'digital-marketing-specialist', 'Business', 'Digital Marketing',
     ['SEO', 'SEM', 'Content Marketing', 'Analytics']),
    ('Financial Analyst', 'financial-analyst', 'Business', 'Financial Analysis',
     ['Excel', 'Valuation', 'Modeling', 'Accounting']),
    ('Business Analyst', 'business-analyst', 'Business', 'Business Analysis',
     ['Requirements', 'SQL', 'Process Mapping', 'Stakeholder Management']),
    ('Game Developer', 'game-developer', 'Computer Science', 'Game Development',
     ['Unity', 'C#', '3D Graphics', 'Game Design']),
    ('Bioinformatician', 'bioinformatician', 'Health', 'Bioinformatics',
     ['Python', 'Genomics', 'R', 'Statistics']),
]


# Coursera Plus catalog highlights (curated subscription bundles)
COURSERA_PLUS_BUNDLES = [
    ('AI for Everyone Bundle', 'ai-everyone-bundle', 'Computer Science', 'deeplearningai',
     'AI Fundamentals', 'Beginner', 18.0, 4.8, 540000,
     ['Generative AI', 'LLMs', 'Prompt Engineering', 'AI Ethics']),
    ('Career Switch into Data Bundle', 'career-switch-data-bundle', 'Data Science', 'ibm',
     'Data Career', 'Beginner', 90.0, 4.7, 380000,
     ['SQL', 'Python', 'Tableau', 'Pandas']),
    ('Cloud Engineering Path Bundle', 'cloud-engineering-bundle', 'Information Technology', 'aws',
     'Cloud Engineering', 'Intermediate', 110.0, 4.6, 290000,
     ['AWS', 'Lambda', 'S3', 'Terraform']),
    ('Full Stack Web Bundle', 'full-stack-bundle', 'Computer Science', 'meta',
     'Web Development', 'Beginner', 130.0, 4.7, 420000,
     ['React', 'Node.js', 'MongoDB', 'GraphQL']),
    ('Cybersecurity Essentials Bundle', 'cybersecurity-essentials-bundle', 'Information Technology', 'google',
     'Cybersecurity', 'Beginner', 95.0, 4.7, 310000,
     ['SIEM', 'Linux', 'SQL', 'Python for Security']),
    ('Modern Marketing Bundle', 'modern-marketing-bundle', 'Business', 'meta',
     'Digital Marketing', 'Beginner', 80.0, 4.6, 240000,
     ['SEO', 'Paid Social', 'Email', 'Analytics']),
    ('Product Management Bundle', 'product-management-bundle', 'Business', 'google',
     'Product Management', 'Beginner', 100.0, 4.6, 220000,
     ['Roadmaps', 'Prioritization', 'Discovery', 'A/B Testing']),
    ('Generative AI for Developers Bundle', 'genai-developers-bundle', 'Computer Science', 'nvidia',
     'Generative AI', 'Intermediate', 60.0, 4.8, 195000,
     ['LangChain', 'RAG', 'Vector Databases', 'Fine-tuning']),
    ('Data Engineering Bundle', 'data-engineering-bundle', 'Data Science', 'databricks',
     'Data Engineering', 'Intermediate', 120.0, 4.7, 175000,
     ['Spark', 'Airflow', 'dbt', 'Delta Lake']),
    ('UX Research and Design Bundle', 'ux-design-bundle', 'Arts and Humanities', 'google',
     'UX Design', 'Beginner', 110.0, 4.7, 260000,
     ['Figma', 'User Research', 'Usability Testing', 'Information Architecture']),
    ('Project Management Mastery Bundle', 'pm-mastery-bundle', 'Business', 'google',
     'Project Management', 'Beginner', 95.0, 4.7, 330000,
     ['Agile', 'Scrum', 'Stakeholder Management', 'Kanban']),
    ('Healthcare Analytics Bundle', 'healthcare-analytics-bundle', 'Health', 'jhu',
     'Healthcare Analytics', 'Intermediate', 70.0, 4.6, 88000,
     ['SAS', 'R', 'Epidemiology', 'Public Health Data']),
]


# Coursera for Business catalog (skills-based; cross-cutting tracks)
BUSINESS_CATALOG_TRACKS = [
    ('Leadership', 'leadership', 'Business',
     ['Strategic Leadership', 'Change Management', 'Decision Making',
      'Executive Communication', 'Negotiation', 'Conflict Resolution',
      'High-Performance Teams', 'Coaching for Leaders', 'Inclusive Leadership',
      'Crisis Leadership']),
    ('Sales', 'sales', 'Business',
     ['Consultative Selling', 'Sales Operations', 'Account Management',
      'B2B Sales Fundamentals', 'Customer Discovery', 'Closing Techniques',
      'Sales Enablement', 'Salesforce CRM Basics']),
    ('Customer Success', 'customer-success', 'Business',
     ['Customer Onboarding', 'Retention Strategies', 'Voice of Customer',
      'NPS and Health Scoring', 'Renewals and Expansion', 'Escalation Management']),
    ('Human Resources', 'hr', 'Business',
     ['Talent Acquisition', 'People Analytics', 'Compensation Design',
      'Performance Reviews', 'Workforce Planning', 'DEI Programs',
      'HRBP Foundations']),
    ('Operations', 'operations', 'Business',
     ['Lean Six Sigma Yellow Belt', 'Lean Six Sigma Green Belt',
      'Supply Chain Fundamentals', 'Demand Planning', 'Vendor Management',
      'Inventory Optimization']),
    ('Finance for Managers', 'finance-managers', 'Business',
     ['Budgeting', 'Forecasting', 'FP&A Foundations',
      'Reading Financial Statements', 'Capital Allocation',
      'Risk Management for Non-Finance']),
]


# Project Network short courses (< 2 hours, very specific)
PROJECT_NETWORK_TOPICS = [
    # (title, primary skill, partner, category)
    ('Build a Personal Portfolio with HTML & CSS', 'HTML/CSS', 'meta', 'Computer Science'),
    ('Create a Responsive Landing Page in Figma', 'Figma', 'google', 'Arts and Humanities'),
    ('Visualize Sales Data in Tableau', 'Tableau', 'tableau', 'Data Science'),
    ('Build a Linear Regression in Python', 'Python', 'ibm', 'Data Science'),
    ('Deploy a Static Site to AWS S3', 'AWS S3', 'aws', 'Information Technology'),
    ('Containerize a Flask App with Docker', 'Docker', 'redhat', 'Information Technology'),
    ('Write a SQL Report in BigQuery', 'BigQuery', 'google', 'Data Science'),
    ('Build a Twitter Sentiment Notebook', 'NLP', 'ibm', 'Data Science'),
    ('Automate a Spreadsheet with Apps Script', 'Apps Script', 'google', 'Information Technology'),
    ('Set up a CI Pipeline in GitHub Actions', 'GitHub Actions', 'github', 'Information Technology'),
    ('Design a Logo in Canva', 'Canva', 'canva', 'Arts and Humanities'),
    ('Edit a Marketing Video in CapCut', 'Video Editing', 'canva', 'Arts and Humanities'),
    ('Build a Budget Spreadsheet in Excel', 'Excel', 'microsoft', 'Business'),
    ('Track KPIs in a Notion Dashboard', 'Notion', 'meta', 'Business'),
    ('Build a Customer Journey Map', 'CX Design', 'mckinsey', 'Business'),
    ('Run an A/B Test with Optimizely', 'A/B Testing', 'meta', 'Business'),
    ('Launch a Shopify Storefront', 'Shopify', 'shopify', 'Business'),
    ('Build a Stripe Checkout Page', 'Stripe', 'stripe', 'Business'),
    ('Send Transactional Email with SendGrid', 'SendGrid', 'hubspot', 'Information Technology'),
    ('Configure a Cloudflare WAF Rule', 'Cloudflare WAF', 'cloudflare', 'Information Technology'),
    ('Set up a MongoDB Atlas Cluster', 'MongoDB', 'mongodb', 'Information Technology'),
    ('Instrument a Node App with Datadog APM', 'Datadog', 'datadog', 'Information Technology'),
    ('Build a Slack Bot in Python', 'Slack API', 'github', 'Computer Science'),
    ('Connect Salesforce to a Webhook', 'Salesforce', 'salesforce', 'Business'),
    ('Build a Power BI Dashboard for Sales', 'Power BI', 'microsoft', 'Data Science'),
    ('Use SAP Analytics Cloud for KPI Reporting', 'SAP Analytics', 'sap', 'Business'),
    ('Build a Looker Dashboard in 90 Minutes', 'Looker', 'google', 'Data Science'),
    ('Train a Model with NVIDIA NeMo', 'NeMo', 'nvidia', 'Data Science'),
    ('Run a Vector Search in MongoDB Atlas', 'Vector Search', 'mongodb', 'Data Science'),
    ('Build a RAG Prototype with LangChain', 'LangChain', 'deeplearningai', 'Computer Science'),
    ('Fine-tune a Hugging Face Model', 'Hugging Face', 'deeplearningai', 'Data Science'),
    ('Build a Streamlit Data App', 'Streamlit', 'snowflake', 'Data Science'),
    ('Spin up a Databricks Notebook', 'Databricks', 'databricks', 'Data Science'),
    ('Move Data with dbt Cloud', 'dbt', 'databricks', 'Data Science'),
    ('Schedule Jobs with Apache Airflow', 'Airflow', 'snowflake', 'Data Science'),
    ('Build a Helm Chart for Kubernetes', 'Helm', 'redhat', 'Information Technology'),
    ('Provision Cloud with Terraform Basics', 'Terraform', 'aws', 'Information Technology'),
    ('Build a Lambda Function in Python', 'AWS Lambda', 'aws', 'Computer Science'),
    ('Containerize a React App with Docker', 'Docker', 'meta', 'Computer Science'),
    ('Build a Next.js Blog with MDX', 'Next.js', 'meta', 'Computer Science'),
    ('Connect React to a Supabase Backend', 'Supabase', 'meta', 'Computer Science'),
    ('Build a Solidity ERC-20 Token', 'Solidity', 'consensys' if False else 'github', 'Computer Science'),
    ('Build a Telegram Bot in Node.js', 'Node.js', 'github', 'Computer Science'),
    ('Build a Discord Slash Command Bot', 'Discord API', 'github', 'Computer Science'),
    ('Use OpenAI API to Summarize PDFs', 'OpenAI API', 'deeplearningai', 'Computer Science'),
    ('Build a FastAPI REST Service', 'FastAPI', 'github', 'Computer Science'),
    ('Build a Django Blog in 90 Minutes', 'Django', 'github', 'Computer Science'),
    ('Build a Spring Boot Hello-World', 'Spring Boot', 'oracle', 'Computer Science'),
    ('Build a Java Maven Project', 'Maven', 'oracle', 'Computer Science'),
    ('Write Unit Tests with JUnit 5', 'JUnit', 'oracle', 'Computer Science'),
    ('Profile a Python Script with cProfile', 'Python', 'ibm', 'Computer Science'),
    ('Build a Plotly Dash Dashboard', 'Plotly', 'ibm', 'Data Science'),
    ('Run a t-Test in R', 'R Statistics', 'jhu', 'Math and Logic'),
    ('Plot Climate Data with Matplotlib', 'Matplotlib', 'nasa', 'Physical Science and Engineering'),
    ('Compute an Orbit with Skyfield', 'Skyfield', 'nasa', 'Physical Science and Engineering'),
    ('Practice German Pronunciation', 'German', 'tum', 'Language Learning'),
    ('Practice French Conversation Basics', 'French', 'sciencespo', 'Language Learning'),
    ('Practice Mandarin Tones', 'Mandarin', 'pku', 'Language Learning'),
    ('Practice Spanish for Travel', 'Spanish', 'unam', 'Language Learning'),
    ('Practice Japanese Hiragana', 'Japanese', 'utokyo', 'Language Learning'),
    ('Practice Portuguese Greetings', 'Portuguese', 'usp-br', 'Language Learning'),
]


# Capstone topics — culminating projects atop existing certificates
CAPSTONE_TOPICS = [
    ('Data Science Capstone', 'data-science-capstone', 'Data Science', 'jhu',
     'End-to-End Data Science', ['Python', 'Pandas', 'Statistics', 'Storytelling']),
    ('Machine Learning Capstone', 'machine-learning-capstone', 'Data Science', 'ibm',
     'Applied Machine Learning', ['scikit-learn', 'XGBoost', 'Evaluation', 'Deployment']),
    ('Deep Learning Capstone', 'deep-learning-capstone', 'Data Science', 'deeplearningai',
     'Deep Learning', ['PyTorch', 'TensorFlow', 'CNNs', 'Transformers']),
    ('Generative AI Capstone', 'generative-ai-capstone', 'Computer Science', 'deeplearningai',
     'Generative AI', ['LangChain', 'RAG', 'Prompt Engineering', 'Evaluation']),
    ('Web Development Capstone', 'web-development-capstone', 'Computer Science', 'meta',
     'Full-Stack Web', ['React', 'Node.js', 'PostgreSQL', 'Deployment']),
    ('Mobile App Capstone', 'mobile-app-capstone', 'Computer Science', 'meta',
     'Mobile Apps', ['React Native', 'Expo', 'REST APIs', 'Push Notifications']),
    ('Cloud Architecture Capstone', 'cloud-architecture-capstone', 'Information Technology', 'aws',
     'Cloud Architecture', ['AWS', 'VPC', 'Lambda', 'DynamoDB']),
    ('DevOps Capstone', 'devops-capstone', 'Information Technology', 'redhat',
     'DevOps', ['Docker', 'Kubernetes', 'CI/CD', 'Terraform']),
    ('Cybersecurity Capstone', 'cybersecurity-capstone', 'Information Technology', 'google',
     'Cybersecurity', ['SIEM', 'Pen Testing', 'Forensics', 'Incident Response']),
    ('Digital Marketing Capstone', 'digital-marketing-capstone', 'Business', 'meta',
     'Digital Marketing', ['Paid Media', 'SEO', 'Analytics', 'Attribution']),
    ('Product Management Capstone', 'product-management-capstone', 'Business', 'google',
     'Product Management', ['Discovery', 'Roadmapping', 'Metrics', 'Stakeholders']),
    ('Project Management Capstone', 'project-management-capstone', 'Business', 'google',
     'Project Management', ['Agile', 'Scrum', 'Stakeholders', 'Risk']),
    ('Financial Analysis Capstone', 'financial-analysis-capstone', 'Business', 'nyu',
     'Financial Analysis', ['Modeling', 'Valuation', 'Excel', 'Reporting']),
    ('UX Design Capstone', 'ux-design-capstone', 'Arts and Humanities', 'google',
     'UX Design', ['Figma', 'User Research', 'Prototyping', 'Usability']),
    ('Healthcare Data Capstone', 'healthcare-data-capstone', 'Health', 'jhu',
     'Healthcare Data', ['SQL', 'Epidemiology', 'Privacy', 'Reporting']),
    ('Public Health Capstone', 'public-health-capstone', 'Health', 'umich',
     'Public Health', ['Population Health', 'Stats', 'Policy', 'Communication']),
    ('Sustainable Engineering Capstone', 'sustainable-engineering-capstone',
     'Physical Science and Engineering', 'gatech',
     'Sustainable Engineering', ['LCA', 'Renewables', 'Circular Economy', 'Systems']),
    ('Climate Science Capstone', 'climate-science-capstone',
     'Physical Science and Engineering', 'nasa',
     'Climate Science', ['Modeling', 'Remote Sensing', 'GIS', 'Communication']),
    ('Game Development Capstone', 'game-development-capstone', 'Computer Science', 'usc',
     'Game Development', ['Unity', 'C#', '3D', 'Playtesting']),
    ('Robotics Capstone', 'robotics-capstone', 'Physical Science and Engineering', 'cmu',
     'Robotics', ['ROS', 'Kinematics', 'Computer Vision', 'Control']),
    ('Quantum Computing Capstone', 'quantum-computing-capstone',
     'Physical Science and Engineering', 'ibm',
     'Quantum Computing', ['Qiskit', 'Quantum Circuits', 'Algorithms', 'Hardware']),
    ('Blockchain Capstone', 'blockchain-capstone', 'Computer Science', 'github',
     'Blockchain', ['Solidity', 'Smart Contracts', 'EVM', 'Security']),
    ('Climate Data Capstone', 'climate-data-capstone', 'Data Science', 'nasa',
     'Climate Data', ['Python', 'xarray', 'NetCDF', 'Storytelling']),
    ('Public Policy Capstone', 'public-policy-capstone', 'Social Sciences', 'georgetown',
     'Public Policy', ['Analysis', 'Stakeholders', 'Briefs', 'Memos']),
    ('Education Tech Capstone', 'education-tech-capstone', 'Social Sciences', 'stanford',
     'EdTech', ['Learning Design', 'Assessment', 'LMS', 'Analytics']),
    ('Renewable Energy Capstone', 'renewable-energy-capstone',
     'Physical Science and Engineering', 'tudelft',
     'Renewable Energy', ['Solar', 'Wind', 'Grid', 'Storage']),
]


# Extra degrees for R3 — 10 more programs across the new partners
EXTRA_DEGREES_V4 = [
    ('Master of Business Administration (Global MBA)',
     'master-global-mba', 'iese', 'Master', 'Business', 'October 15, 2026', 620),
    ('Master of Science in Artificial Intelligence',
     'master-ai-iitb', 'iitb', 'Master', 'Computer Science', 'July 30, 2026', 760),
    ('Master of Science in Machine Learning',
     'master-ml-imperial', 'imperial', 'Master', 'Data Science', 'August 1, 2026', 720),
    ('Master of Public Policy',
     'master-public-policy-hec', 'hec', 'Master', 'Social Sciences', 'September 30, 2026', 540),
    ('Bachelor of Science in Information Systems',
     'bachelor-information-systems', 'asu', 'Bachelor', 'Information Technology', '', 1240),
    ('Master of Science in Cybersecurity',
     'master-cybersecurity-gatech', 'gatech', 'Master', 'Information Technology', 'August 15, 2026', 720),
    ('Master of Science in Engineering Management',
     'master-engmgmt-tudelft', 'tudelft', 'MasterAdvancedStudy',
     'Physical Science and Engineering', 'May 31, 2026', 760),
    ('Master of Public Health (Global Health)',
     'master-public-health-global', 'who', 'Master', 'Health', 'November 15, 2026', 540),
    ('Master of Science in Sustainability',
     'master-sustainability-kuleuven', 'kuleuven', 'Master',
     'Physical Science and Engineering', 'June 30, 2026', 720),
    ('Master of Business Analytics',
     'master-business-analytics-bocconi', 'bocconi', 'Master', 'Data Science',
     'July 15, 2026', 720),
]


def _v4_generic_modules(course_title, primary, weeks=4):
    """Return weekly module tuples (title, desc, vids, reads, quizzes, vts)."""
    mods = []
    for w in range(1, weeks + 1):
        if w == 1:
            t, d = (f'Welcome and {primary} Foundations',
                    f'Orientation, prerequisites, and the core mental model for {primary}.')
        elif w == weeks:
            t, d = (f'Capstone Project and Next Steps',
                    f'Put it all together: a portfolio-grade {primary} project.')
        else:
            t, d = (f'{primary} Practice — Week {w}',
                    f'Hands-on labs and graded exercises for {primary}.')
        vts = [
            f'Lesson {w}.1: {t}',
            f'Lesson {w}.2: Worked example for {primary}',
            f'Lesson {w}.3: Practice drill',
        ]
        mods.append((t, d, 5, 3, 1, vts))
    return mods


def seed_v4(db, models):
    """R3 catalog expansion. Idempotent — gated on partner slug 'iitb'."""
    User = models['User']
    Partner = models['Partner']
    Course = models['Course']
    CourseModule = models['CourseModule']
    SubCourse = models['SubCourse']
    Enrollment = models['Enrollment']
    SavedCourse = models['SavedCourse']
    Review = models['Review']

    if Partner.query.filter_by(slug='iitb').first():
        return  # already seeded

    # 1) New partners ──────────────────────────────────────────────────────
    for name, slug, country, ptype, short in NEW_PARTNERS_V4:
        if Partner.query.filter_by(slug=slug).first():
            continue
        db.session.add(Partner(name=name, slug=slug, country=country,
                               partner_type=ptype, short_name=short))
    db.session.commit()

    pid = {p.slug: p.id for p in Partner.query.all()}
    created = 0

    # 2) Capstone courses (20 — atop existing certificates) ────────────────
    for idx, (title, slug, category, partner_slug, primary, skills) in enumerate(
            CAPSTONE_TOPICS):
        if Course.query.filter_by(slug=slug).first():
            continue
        c = Course(
            title=title, slug=slug,
            partner_id=pid.get(partner_slug),
            course_type='Course', level='Advanced',
            category=category,
            duration_text='Approx. 30 hours',
            duration_weeks=6.0, duration_hours=30.0,
            rating=round(4.5 + (idx % 4) * 0.08, 2),
            review_count=850 + idx * 65,
            enrolled_count=24000 + idx * 1700,
            is_free=False, has_certificate=True,
            credit_eligible=(idx % 3 == 0),
            instructor=f'{partner_slug.upper()} Faculty Team',
            instructor_title=f'Faculty, {partner_slug.upper()}',
            description=(
                f'The {title} is a portfolio-grade capstone where you ship a real '
                f'{primary} project end-to-end. Builds on the {primary} certificate '
                f'series and is reviewed by faculty.'),
            skills=json.dumps(skills),
            what_you_learn=json.dumps([
                f'Scope and ship a real {primary} project',
                f'Defend your design choices with data',
                f'Build a portfolio piece reviewers will read',
                f'Earn a verified capstone certificate',
            ]),
            feature_tags=json.dumps(['capstone', primary.lower().replace(' ', '-'),
                                     partner_slug, 'advanced']),
            is_featured=(idx % 4 == 0),
            is_new=(idx % 3 == 0),
            sort_date=(SEED_REF_DATE - timedelta(days=20 + idx * 11)).strftime('%Y-%m-%d'),
            color_class=CATEGORY_COLORS.get(category, 'cat-cs'),
        )
        db.session.add(c)
        db.session.flush()
        for w, mod in enumerate(_v4_generic_modules(title, primary, weeks=6), 1):
            mt, md, v, r, q, vts = mod
            db.session.add(CourseModule(
                course_id=c.id, week_number=w, title=mt, description=md,
                videos_count=v, readings_count=r, quizzes_count=q,
                video_titles=json.dumps(vts)))
        created += 1
    db.session.commit()

    # 3) Coursera Plus bundles (Specializations marked as Plus-included) ───
    for idx, (title, slug, category, partner_slug, primary, level,
              duration_hours, rating, enrolled, skills) in enumerate(
            COURSERA_PLUS_BUNDLES):
        if Course.query.filter_by(slug=slug).first():
            continue
        weeks = max(4, int(duration_hours / 6))
        c = Course(
            title=title, slug=slug,
            partner_id=pid.get(partner_slug),
            course_type='Specialization', level=level,
            category=category,
            duration_text=f'{weeks} months at 10 hrs/wk' if duration_hours > 60
                          else f'Approx. {int(duration_hours)} hours',
            duration_weeks=float(weeks),
            duration_hours=duration_hours,
            rating=rating, review_count=int(enrolled * 0.045),
            enrolled_count=enrolled,
            is_free=False, has_certificate=True,
            credit_eligible=False,
            instructor=f'{partner_slug.upper()} Instructor Team',
            instructor_title=f'Lead Instructors, {partner_slug.upper()}',
            description=(
                f'{title}. Available on Coursera Plus — one subscription unlocks '
                f'the full bundle. Covers {primary} from {level.lower()} through '
                f'job-ready practice with hands-on projects.'),
            skills=json.dumps(skills),
            what_you_learn=json.dumps([
                f'Master the {primary} skill stack',
                f'Apply {skills[0] if skills else primary} to portfolio projects',
                f'Earn industry-recognized certificates',
                f'Join a global cohort with peer review',
            ]),
            feature_tags=json.dumps(['coursera-plus', primary.lower().replace(' ', '-'),
                                     partner_slug, level.lower(), 'subscription']),
            is_featured=True, is_new=(idx % 2 == 0),
            sort_date=(SEED_REF_DATE - timedelta(days=15 + idx * 9)).strftime('%Y-%m-%d'),
            color_class=CATEGORY_COLORS.get(category, 'cat-cs'),
        )
        db.session.add(c)
        db.session.flush()
        # Sub-courses (5 per bundle)
        sub_titles = [
            f'{primary} Foundations', f'Applied {primary} I',
            f'Applied {primary} II', f'{primary} at Scale',
            f'{primary} Capstone',
        ]
        for i, st in enumerate(sub_titles):
            db.session.add(SubCourse(
                specialization_id=c.id, order_index=i + 1,
                title=st,
                description=f'Module {i + 1} of the {title}. Builds on prior weeks.',
                duration_text='Approx. 4 weeks'))
        # 5 pillar modules
        for w in range(1, 6):
            mt = f'Pillar {w}: {sub_titles[w-1]}'
            md = f'Pillar {w} of {title}. Hands-on labs, graded assignments.'
            db.session.add(CourseModule(
                course_id=c.id, week_number=w, title=mt, description=md,
                videos_count=8, readings_count=5, quizzes_count=2,
                video_titles=json.dumps([
                    f'Lesson {w}.1: {sub_titles[w-1]}',
                    f'Lesson {w}.2: Worked example',
                    f'Lesson {w}.3: Practice drill',
                ])))
        created += 1
    db.session.commit()

    # 4) Business catalog tracks (62 Courses) ──────────────────────────────
    for t_idx, (track, track_slug, category, topics) in enumerate(
            BUSINESS_CATALOG_TRACKS):
        for s_idx, topic in enumerate(topics):
            slug = _slugify(f'business-{track_slug}-{topic}')
            if Course.query.filter_by(slug=slug).first():
                continue
            level = 'Beginner' if s_idx < 5 else 'Intermediate'
            partner_slug = ['mckinsey', 'deloitte', 'jpmorgan', 'hec', 'ie', 'bocconi',
                            'iese', 'imperial', 'columbia', 'cornell'][
                (t_idx * 7 + s_idx * 3) % 10]
            c = Course(
                title=topic, slug=slug,
                partner_id=pid.get(partner_slug),
                course_type='Course', level=level,
                category=category, subcategory=track,
                duration_text='Approx. 15 hours',
                duration_weeks=3.0, duration_hours=15.0,
                rating=round(4.5 + ((t_idx * 5 + s_idx) % 5) * 0.06, 2),
                review_count=800 + s_idx * 120,
                enrolled_count=18000 + s_idx * 1500,
                is_free=False, has_certificate=True,
                credit_eligible=False,
                instructor=f'{partner_slug.upper()} Practice Lead',
                instructor_title=f'Practice Lead, {partner_slug.upper()}',
                description=(
                    f'{topic}, part of the Coursera for Business {track} catalog. '
                    f'A focused 15-hour course for working professionals upskilling in '
                    f'{track.lower()}. Real case studies, graded discussions, '
                    f'and a final project.'),
                skills=json.dumps([topic, track, 'Business Skills']),
                what_you_learn=json.dumps([
                    f'Apply {topic} in a corporate setting',
                    f'Run a 30-day playbook on {topic}',
                    f'Coach peers on {topic}',
                    f'Earn a {track} catalog badge',
                ]),
                feature_tags=json.dumps(['coursera-for-business', track_slug,
                                         partner_slug, level.lower()]),
                is_featured=(s_idx == 0),
                is_new=(s_idx % 4 == 0),
                sort_date=(SEED_REF_DATE - timedelta(
                    days=10 + (t_idx * 31 + s_idx * 7))).strftime('%Y-%m-%d'),
                color_class=CATEGORY_COLORS.get(category, 'cat-biz'),
            )
            db.session.add(c)
            db.session.flush()
            for w, mod in enumerate(_v4_generic_modules(topic, topic, weeks=3), 1):
                mt, md, v, r, q, vts = mod
                db.session.add(CourseModule(
                    course_id=c.id, week_number=w, title=mt, description=md,
                    videos_count=v, readings_count=r, quizzes_count=q,
                    video_titles=json.dumps(vts)))
            created += 1
    db.session.commit()

    # 5) Project Network shorts (~60, <2 hours each) ───────────────────────
    for idx, (title, primary, partner_slug, category) in enumerate(
            PROJECT_NETWORK_TOPICS):
        slug = _slugify(f'project-{title}')
        if Course.query.filter_by(slug=slug).first():
            continue
        c = Course(
            title=title, slug=slug,
            partner_id=pid.get(partner_slug),
            course_type='Guided Project', level='Beginner',
            category=category,
            duration_text='Less Than 2 Hours',
            duration_weeks=0.25, duration_hours=1.5,
            rating=round(4.4 + (idx % 5) * 0.08, 2),
            review_count=110 + idx * 9,
            enrolled_count=2800 + idx * 380,
            is_free=False, has_certificate=False,
            credit_eligible=False,
            instructor='Coursera Project Network',
            instructor_title='Project Mentor',
            description=(
                f'A 90-minute guided project: {title}. You will sit in a split-screen '
                f'with the mentor while building a working {primary} artifact you can '
                f'show off in 24 hours.'),
            skills=json.dumps([primary, 'Hands-on Practice']),
            what_you_learn=json.dumps([
                f'Build a working {primary} artifact in 90 minutes',
                f'Apply {primary} to a real scenario',
                f'Walk away with a portfolio-ready sample',
            ]),
            feature_tags=json.dumps(['guided-project', 'project-network',
                                     'under-2-hours', primary.lower().replace(' ', '-'),
                                     partner_slug]),
            is_featured=False,
            is_new=(idx % 6 == 0),
            sort_date=(SEED_REF_DATE - timedelta(
                days=5 + idx * 6)).strftime('%Y-%m-%d'),
            color_class=CATEGORY_COLORS.get(category, 'cat-cs'),
        )
        db.session.add(c)
        db.session.flush()
        db.session.add(CourseModule(
            course_id=c.id, week_number=1,
            title=f'Session: {title}',
            description=f'A single 90-minute hands-on session: {title}.',
            videos_count=6, readings_count=1, quizzes_count=0,
            video_titles=json.dumps([
                f'Step 1: Set up the {primary} environment',
                f'Step 2: Implement the core logic',
                f'Step 3: Test the workflow',
                f'Step 4: Polish and ship',
                f'Step 5: Wrap-up and next steps',
                f'Bonus: Extending your {primary} project',
            ])))
        created += 1
    db.session.commit()

    # 6) Career-tracks: one Career Certificate course per role ─────────────
    for r_idx, (role, role_slug, category, primary, skills) in enumerate(CAREER_ROLES):
        slug = _slugify(f'career-certificate-{role_slug}')
        if Course.query.filter_by(slug=slug).first():
            continue
        partner = ['google', 'ibm', 'meta', 'aws', 'microsoft', 'salesforce'][r_idx % 6]
        c = Course(
            title=f'{role} Career Certificate',
            slug=slug,
            partner_id=pid.get(partner),
            course_type='Professional Certificate', level='Beginner',
            category=category,
            duration_text='6 Months at 10 hrs/wk',
            duration_weeks=26.0, duration_hours=160.0,
            rating=round(4.6 + (r_idx % 4) * 0.05, 2),
            review_count=5200 + r_idx * 320,
            enrolled_count=95000 + r_idx * 7200,
            is_free=False, has_certificate=True,
            credit_eligible=True,
            instructor=f'{partner.upper()} Career Coaches',
            instructor_title=f'Career Coaches, {partner.upper()}',
            description=(
                f'Become a {role} in six months. The {role} Career Certificate '
                f'covers {primary} from absolute beginner through portfolio + '
                f'interview readiness. Includes employer-recognized signal, mock '
                f'interviews, and access to the Coursera hiring consortium.'),
            skills=json.dumps(skills),
            what_you_learn=json.dumps([
                f'Land a job as a {role}',
                f'Build a 3-project portfolio in {primary}',
                f'Pass technical interviews in {skills[0]}',
                f'Get matched with employers in the Coursera consortium',
            ]),
            feature_tags=json.dumps(['career-certificate', 'professional-certificate',
                                     role_slug, partner]),
            is_featured=True, is_new=(r_idx % 3 == 0),
            sort_date=(SEED_REF_DATE - timedelta(
                days=30 + r_idx * 9)).strftime('%Y-%m-%d'),
            color_class=CATEGORY_COLORS.get(category, 'cat-cs'),
        )
        db.session.add(c)
        db.session.flush()
        for w in range(1, 7):
            mt = f'Month {w}: {skills[(w-1) % len(skills)]}'
            md = (f'Month {w} of the {role} Career Certificate — deep dive into '
                  f'{skills[(w-1) % len(skills)]} with graded projects.')
            db.session.add(CourseModule(
                course_id=c.id, week_number=w, title=mt, description=md,
                videos_count=18, readings_count=12, quizzes_count=4,
                video_titles=json.dumps([])))
        created += 1
    db.session.commit()

    # 7) Foundations + Advanced + Capstone for top 80 topics (~240 courses) ─
    foundation_topics = [
        ('Generative AI', 'Computer Science', 'deeplearningai'),
        ('Large Language Models', 'Computer Science', 'deeplearningai'),
        ('Prompt Engineering', 'Computer Science', 'deeplearningai'),
        ('Retrieval-Augmented Generation', 'Computer Science', 'deeplearningai'),
        ('Vector Databases', 'Data Science', 'mongodb'),
        ('LLM Evaluation', 'Data Science', 'deeplearningai'),
        ('AI Safety', 'Computer Science', 'oxford'),
        ('AI Ethics', 'Social Sciences', 'oxford'),
        ('Responsible AI', 'Social Sciences', 'unesco'),
        ('AI Product Management', 'Business', 'google'),
        ('Quantum Computing', 'Physical Science and Engineering', 'ibm'),
        ('Edge Computing', 'Information Technology', 'cisco'),
        ('IoT Engineering', 'Information Technology', 'siemens'),
        ('Embedded Systems', 'Computer Science', 'intel'),
        ('FPGA Design', 'Physical Science and Engineering', 'intel'),
        ('Robotics ROS', 'Physical Science and Engineering', 'cmu'),
        ('Computer Vision', 'Computer Science', 'nvidia'),
        ('Natural Language Processing', 'Computer Science', 'deeplearningai'),
        ('Reinforcement Learning', 'Data Science', 'deeplearningai'),
        ('Time Series Forecasting', 'Data Science', 'databricks'),
        ('Causal Inference', 'Data Science', 'mit'),
        ('Bayesian Statistics', 'Math and Logic', 'duke'),
        ('Linear Algebra', 'Math and Logic', 'mit'),
        ('Discrete Mathematics', 'Math and Logic', 'mit'),
        ('Real Analysis', 'Math and Logic', 'princeton'),
        ('Combinatorics', 'Math and Logic', 'princeton'),
        ('Graph Theory', 'Math and Logic', 'mit'),
        ('Cryptography', 'Computer Science', 'stanford'),
        ('Distributed Systems', 'Computer Science', 'mit'),
        ('Operating Systems', 'Computer Science', 'cmu'),
        ('Compilers', 'Computer Science', 'cmu'),
        ('Algorithms', 'Computer Science', 'stanford'),
        ('Data Structures', 'Computer Science', 'princeton'),
        ('Functional Programming', 'Computer Science', 'epfl'),
        ('Concurrency in Go', 'Computer Science', 'google'),
        ('Rust Systems Programming', 'Computer Science', 'cmu'),
        ('Modern C++', 'Computer Science', 'mit'),
        ('Python for Everybody', 'Computer Science', 'umich'),
        ('Java SE 17', 'Computer Science', 'oracle'),
        ('Kotlin Multiplatform', 'Computer Science', 'lg'),
        ('Swift on Server', 'Computer Science', 'apple'),
        ('TypeScript Mastery', 'Computer Science', 'meta'),
        ('GraphQL APIs', 'Computer Science', 'meta'),
        ('Microservices Patterns', 'Information Technology', 'redhat'),
        ('Service Mesh with Istio', 'Information Technology', 'redhat'),
        ('Observability with OpenTelemetry', 'Information Technology', 'datadog'),
        ('Site Reliability Engineering', 'Information Technology', 'google'),
        ('Chaos Engineering', 'Information Technology', 'datadog'),
        ('Penetration Testing', 'Information Technology', 'google'),
        ('Zero Trust Security', 'Information Technology', 'cisco'),
        ('Cloud Native Architecture', 'Information Technology', 'redhat'),
        ('Multi-Cloud Engineering', 'Information Technology', 'aws'),
        ('Snowflake Data Cloud', 'Data Science', 'snowflake'),
        ('Databricks Lakehouse', 'Data Science', 'databricks'),
        ('Apache Spark Performance', 'Data Science', 'databricks'),
        ('Stream Processing with Kafka', 'Information Technology', 'databricks'),
        ('Real-Time Analytics', 'Data Science', 'snowflake'),
        ('Feature Engineering', 'Data Science', 'ibm'),
        ('ML Ops on AWS', 'Data Science', 'aws'),
        ('ML Ops on Azure', 'Data Science', 'microsoft'),
        ('Model Monitoring', 'Data Science', 'datadog'),
        ('Data Governance', 'Data Science', 'sap'),
        ('Data Mesh', 'Data Science', 'databricks'),
        ('Modern Data Warehouse', 'Data Science', 'snowflake'),
        ('Behavioral Economics', 'Social Sciences', 'duke'),
        ('Game Theory', 'Social Sciences', 'stanford'),
        ('Public Policy Analysis', 'Social Sciences', 'georgetown'),
        ('Sustainable Cities', 'Social Sciences', 'tudelft'),
        ('Climate Policy', 'Social Sciences', 'oxford'),
        ('Renewable Energy Systems', 'Physical Science and Engineering', 'tudelft'),
        ('Solar Engineering', 'Physical Science and Engineering', 'tudelft'),
        ('Wind Energy', 'Physical Science and Engineering', 'tudelft'),
        ('Battery Technology', 'Physical Science and Engineering', 'mit'),
        ('Electric Vehicles', 'Physical Science and Engineering', 'bmw'),
        ('Hydrogen Economy', 'Physical Science and Engineering', 'siemens'),
        ('Materials Science', 'Physical Science and Engineering', 'mit'),
        ('Nano Materials', 'Physical Science and Engineering', 'ethz'),
        ('Bioprocess Engineering', 'Health', 'ki'),
        ('Drug Discovery', 'Health', 'jhu'),
        ('Clinical Trials', 'Health', 'who'),
        ('Telemedicine', 'Health', 'jhu'),
        ('Global Health Policy', 'Health', 'who'),
        ('Epidemiology Methods', 'Health', 'jhu'),
        ('Public Speaking', 'Personal Development', 'georgetown'),
    ]
    for f_idx, (topic, category, partner_slug) in enumerate(foundation_topics):
        primary = topic
        partner = partner_slug if pid.get(partner_slug) else 'stanford'
        # 3 levels: Foundations / Advanced / Capstone
        for variant_idx, (variant, level, hours, weeks, ctype) in enumerate([
                ('Foundations of', 'Beginner', 14.0, 3.0, 'Course'),
                ('Advanced', 'Advanced', 32.0, 6.0, 'Course'),
                ('Capstone in', 'Advanced', 40.0, 8.0, 'Course'),
        ]):
            title = f'{variant} {topic}'
            slug = _slugify(f'{variant}-{topic}')
            if Course.query.filter_by(slug=slug).first():
                continue
            c = Course(
                title=title, slug=slug,
                partner_id=pid.get(partner),
                course_type=ctype, level=level,
                category=category,
                duration_text=f'Approx. {int(hours)} hours',
                duration_weeks=weeks, duration_hours=hours,
                rating=round(4.4 + ((f_idx * 3 + variant_idx) % 5) * 0.07, 2),
                review_count=800 + f_idx * 25 + variant_idx * 250,
                enrolled_count=22000 + f_idx * 800 + variant_idx * 5400,
                is_free=(variant_idx == 0 and f_idx % 17 == 0),
                has_certificate=True,
                credit_eligible=(variant_idx == 2 and f_idx % 5 == 0),
                instructor=f'{partner.upper()} Faculty',
                instructor_title=f'Faculty, {partner.upper()}',
                description=(
                    f'{title}. A {level.lower()} course in {primary}. '
                    f'{"Build the mental model and run your first" if variant_idx == 0 else ("Push into production-grade" if variant_idx == 1 else "Ship a capstone-grade portfolio piece on")} {primary}.'),
                skills=json.dumps([primary, 'Hands-on Practice', 'Problem Solving']),
                what_you_learn=json.dumps([
                    f'Understand {primary} fundamentals' if variant_idx == 0
                    else (f'Apply {primary} to production scenarios' if variant_idx == 1
                          else f'Ship a portfolio-grade {primary} project'),
                    f'Practice {primary} through graded labs',
                    f'Earn a shareable certificate in {primary}',
                ]),
                feature_tags=json.dumps([
                    primary.lower().replace(' ', '-'), level.lower(), partner,
                    variant.lower().replace(' ', '-'),
                ]),
                is_featured=(f_idx % 17 == 0 and variant_idx == 1),
                is_new=(f_idx % 4 == variant_idx % 4),
                sort_date=(SEED_REF_DATE - timedelta(
                    days=20 + f_idx * 7 + variant_idx * 3)).strftime('%Y-%m-%d'),
                color_class=CATEGORY_COLORS.get(category, 'cat-cs'),
            )
            db.session.add(c)
            db.session.flush()
            n_weeks = int(weeks) if weeks >= 1 else 1
            n_weeks = min(n_weeks, 8)
            for w, mod in enumerate(_v4_generic_modules(title, primary, weeks=n_weeks), 1):
                mt, md, v, r, q, vts = mod
                db.session.add(CourseModule(
                    course_id=c.id, week_number=w, title=mt, description=md,
                    videos_count=v, readings_count=r, quizzes_count=q,
                    video_titles=json.dumps(vts)))
            created += 1
    db.session.commit()

    # 8) 10 extra degrees ──────────────────────────────────────────────────
    for d_idx, (title, slug, partner_slug, dtype, category, deadline,
                hours) in enumerate(EXTRA_DEGREES_V4):
        if Course.query.filter_by(slug=slug).first():
            continue
        primary = title.split(' in ')[-1] if ' in ' in title else title
        c = Course(
            title=title, slug=slug,
            partner_id=pid.get(partner_slug),
            course_type='Degree', level='Advanced',
            category=category,
            duration_text=('2 - 4 Years' if dtype == 'Bachelor' else '1 - 3 Years'),
            duration_weeks=104.0 if dtype == 'Bachelor' else 78.0,
            duration_hours=float(hours),
            rating=4.7, review_count=400 + d_idx * 30,
            enrolled_count=2800 + d_idx * 240,
            is_free=False, has_certificate=True, credit_eligible=True,
            instructor=f'{partner_slug.upper()} Faculty',
            instructor_title=f'Faculty, {partner_slug.upper()}',
            description=(
                f'Earn an accredited {dtype} ({title}) entirely online from '
                f'{partner_slug.upper()}. Cohort-based with project-led learning.'),
            skills=json.dumps([primary, 'Capstone Project', 'Research Methods']),
            what_you_learn=json.dumps([
                f'Complete an accredited {dtype.lower()} in {primary}',
                f'Build a research-grade capstone in {primary}',
                f'Earn credit recognized globally',
            ]),
            feature_tags=json.dumps(['degree', dtype.lower(), partner_slug,
                                      category.lower().replace(' ', '-')]),
            is_featured=(d_idx % 3 == 0), is_new=(d_idx % 4 == 0),
            sort_date=(SEED_REF_DATE - timedelta(
                days=60 + d_idx * 14)).strftime('%Y-%m-%d'),
            degree_type=dtype,
            application_deadline=deadline,
            color_class=CATEGORY_COLORS.get(category, 'cat-cs'),
        )
        db.session.add(c)
        db.session.flush()
        for w, (mt, md) in enumerate([
            ('Year 1: Foundations', f'First-year coursework in {primary}.'),
            ('Year 2: Applied Practice', f'Project-based courses in {primary}.'),
            ('Year 3: Specialisation', f'Electives concentrating in {primary}.'),
            ('Final Capstone', f'Year-long {primary} capstone supervised by faculty.'),
        ], 1):
            db.session.add(CourseModule(
                course_id=c.id, week_number=w, title=mt, description=md,
                videos_count=20, readings_count=30, quizzes_count=10,
                video_titles=json.dumps([])))
        created += 1
    db.session.commit()

    # 9) Industry-track Specializations (15 industries × 4 partners) ──────
    industry_tracks = [
        ('FinTech', 'Business', ['jpmorgan', 'stripe', 'klarna', 'hsbc']),
        ('HealthTech', 'Health', ['jhu', 'ki', 'who', 'jpmorgan']),
        ('EdTech', 'Social Sciences', ['stanford', 'meta', 'google', 'umich']),
        ('Climate Tech', 'Physical Science and Engineering', ['tudelft', 'mit', 'siemens', 'nasa']),
        ('AutoTech', 'Physical Science and Engineering', ['bmw', 'toyota', 'mercedes', 'volkswagen']),
        ('RetailTech', 'Business', ['shopify', 'salesforce', 'meta', 'hubspot']),
        ('TravelTech', 'Business', ['booking', 'google', 'aws', 'stripe']),
        ('GovTech', 'Social Sciences', ['worldbank', 'oecd', 'imf', 'georgetown']),
        ('SpaceTech', 'Physical Science and Engineering', ['nasa', 'esa', 'mit', 'ethz']),
        ('AgriTech', 'Physical Science and Engineering', ['ucdavis', 'tudelft', 'siemens', 'tcs']),
        ('LegalTech', 'Social Sciences', ['georgetown', 'oxford', 'columbia', 'nyu']),
        ('Sports Analytics', 'Data Science', ['cornell', 'mit', 'umich', 'gatech']),
        ('Media Tech', 'Arts and Humanities', ['nyu', 'sony', 'spotify', 'meta']),
        ('Insurance Analytics', 'Business', ['nyu', 'cornell', 'mckinsey', 'deloitte']),
        ('Logistics & Supply Chain', 'Business', ['mit', 'gatech', 'tudelft', 'sap']),
    ]
    for i_idx, (industry, category, partners) in enumerate(industry_tracks):
        for p_idx, partner_slug in enumerate(partners):
            partner_slug_eff = partner_slug if pid.get(partner_slug) else 'stanford'
            for v_idx, (variant, level, hours, weeks, ctype) in enumerate([
                ('Introduction to', 'Beginner', 12.0, 3.0, 'Course'),
                ('Applied', 'Intermediate', 28.0, 6.0, 'Course'),
                ('Specialization in', 'Intermediate', 110.0, 22.0, 'Specialization'),
                ('Professional Certificate in', 'Beginner', 130.0, 26.0, 'Professional Certificate'),
            ]):
                title = f'{variant} {industry} ({partners[p_idx].upper()})'
                slug = _slugify(f'{variant}-{industry}-{partners[p_idx]}-{p_idx}-{v_idx}')
                if Course.query.filter_by(slug=slug).first():
                    continue
                c = Course(
                    title=title, slug=slug,
                    partner_id=pid.get(partner_slug_eff),
                    course_type=ctype, level=level,
                    category=category, subcategory=industry,
                    duration_text=(f'Approx. {int(hours)} hours' if hours < 80
                                   else f'{int(weeks)} weeks at 6 hrs/wk'),
                    duration_weeks=weeks, duration_hours=hours,
                    rating=round(4.4 + ((i_idx * 13 + p_idx * 5 + v_idx) % 5) * 0.07, 2),
                    review_count=600 + i_idx * 35 + p_idx * 90 + v_idx * 280,
                    enrolled_count=14000 + i_idx * 900 + p_idx * 2200 + v_idx * 4800,
                    is_free=False, has_certificate=True,
                    credit_eligible=(ctype == 'Professional Certificate' and v_idx == 3 and p_idx % 3 == 0),
                    instructor=f'{partners[p_idx].upper()} Practice Lead',
                    instructor_title=f'Practice Lead, {partners[p_idx].upper()}',
                    description=(
                        f'{title}. A {level.lower()} program in {industry}. Built with '
                        f'{partners[p_idx].upper()} subject-matter experts. Hands-on '
                        f'labs, real datasets, and a graded capstone.'),
                    skills=json.dumps([industry, f'{industry} Analytics',
                                       f'{industry} Operations']),
                    what_you_learn=json.dumps([
                        f'Understand the {industry} landscape',
                        f'Apply {industry} tools to real problems',
                        f'Build a {industry} portfolio piece',
                        f'Network in the {industry} community',
                    ]),
                    feature_tags=json.dumps([industry.lower().replace(' ', '-'),
                                              level.lower(), partners[p_idx],
                                              variant.lower().replace(' ', '-')]),
                    is_featured=(v_idx == 3 and p_idx == 0),
                    is_new=((i_idx + p_idx + v_idx) % 5 == 0),
                    sort_date=(SEED_REF_DATE - timedelta(
                        days=15 + i_idx * 11 + p_idx * 5 + v_idx * 3)).strftime('%Y-%m-%d'),
                    color_class=CATEGORY_COLORS.get(category, 'cat-cs'),
                )
                db.session.add(c)
                db.session.flush()
                n_weeks = min(int(max(weeks, 1)), 6)
                for w, mod in enumerate(_v4_generic_modules(title, industry,
                                                            weeks=n_weeks), 1):
                    mt, md, v, r, q, vts = mod
                    db.session.add(CourseModule(
                        course_id=c.id, week_number=w, title=mt, description=md,
                        videos_count=v, readings_count=r, quizzes_count=q,
                        video_titles=json.dumps(vts)))
                if ctype == 'Specialization':
                    for sub_i in range(5):
                        db.session.add(SubCourse(
                            specialization_id=c.id, order_index=sub_i + 1,
                            title=f'{industry} Module {sub_i + 1}',
                            description=f'Module {sub_i + 1} of the {industry} Specialization.',
                            duration_text='Approx. 4 weeks'))
                created += 1
    db.session.commit()

    # 10) Mastering X variants for the foundation_topics list ─────────────
    for f_idx, (topic, category, partner_slug) in enumerate(foundation_topics):
        partner = partner_slug if pid.get(partner_slug) else 'stanford'
        for v_idx, (prefix, level, hours, weeks) in enumerate([
                ('Mastering', 'Intermediate', 22.0, 5.0),
                ('Practical', 'Intermediate', 16.0, 4.0),
                ('Workshop in', 'Beginner', 8.0, 2.0),
                ('Project-Based', 'Intermediate', 18.0, 4.0),
        ]):
            title = f'{prefix} {topic}'
            slug = _slugify(f'{prefix.lower()}-{topic}')
            if Course.query.filter_by(slug=slug).first():
                continue
            c = Course(
                title=title, slug=slug,
                partner_id=pid.get(partner),
                course_type='Course', level=level,
                category=category,
                duration_text=f'Approx. {int(hours)} hours',
                duration_weeks=weeks, duration_hours=hours,
                rating=round(4.5 + ((f_idx + v_idx) % 5) * 0.07, 2),
                review_count=900 + f_idx * 22 + v_idx * 110,
                enrolled_count=18000 + f_idx * 600 + v_idx * 3300,
                is_free=False, has_certificate=True,
                credit_eligible=False,
                instructor=f'{partner.upper()} Senior Instructor',
                instructor_title=f'Senior Instructor, {partner.upper()}',
                description=(
                    f'{title}. {"Push past the basics with deeper exercises." if v_idx == 0 else "A pragmatic, project-led tour of"} {topic}.'),
                skills=json.dumps([topic, 'Hands-on Practice', 'Portfolio Project']),
                what_you_learn=json.dumps([
                    f'Take {topic} from beginner to intermediate',
                    f'Run a guided project in {topic}',
                    f'Get unstuck via curated office-hour clips',
                ]),
                feature_tags=json.dumps([topic.lower().replace(' ', '-'),
                                          level.lower(), partner,
                                          prefix.lower()]),
                is_featured=False,
                is_new=((f_idx + v_idx) % 6 == 0),
                sort_date=(SEED_REF_DATE - timedelta(
                    days=10 + f_idx * 5 + v_idx * 4)).strftime('%Y-%m-%d'),
                color_class=CATEGORY_COLORS.get(category, 'cat-cs'),
            )
            db.session.add(c)
            db.session.flush()
            n_weeks = min(int(max(weeks, 1)), 5)
            for w, mod in enumerate(_v4_generic_modules(title, topic, weeks=n_weeks), 1):
                mt, md, v, r, q, vts = mod
                db.session.add(CourseModule(
                    course_id=c.id, week_number=w, title=mt, description=md,
                    videos_count=v, readings_count=r, quizzes_count=q,
                    video_titles=json.dumps(vts)))
            created += 1
    db.session.commit()

    # 11) Language deep dives — 12 languages × 4 partners × 3 levels ─────
    lang_tracks = [
        ('Spanish', ['unam', 'ie', 'iese', 'puc-cl']),
        ('Mandarin Chinese', ['pku', 'tsinghua', 'fudan', 'sjtu']),
        ('Japanese', ['utokyo', 'kyoto', 'sony', 'toyota']),
        ('French', ['sciencespo', 'hec', 'louvre', 'capgemini']),
        ('German', ['tum', 'siemens', 'bosch', 'bmw']),
        ('Italian', ['bocconi', 'polimi', 'sapienza', 'unesco']),
        ('Portuguese', ['usp-br', 'fgv', 'ulisboa', 'itau']),
        ('Korean', ['snu', 'kaist', 'samsung', 'lg']),
        ('Arabic', ['auc', 'khalifa', 'kaust', 'hbku']),
        ('Russian', ['hse', 'cuni', 'unesco', 'oxford']),
        ('Hindi', ['iitb', 'iitm', 'isb', 'iimb']),
        ('English for Business', ['ulondon', 'oxford', 'cambridge', 'imperial']),
    ]
    for l_idx, (lang, partners) in enumerate(lang_tracks):
        for p_idx, partner_slug in enumerate(partners):
            partner_eff = partner_slug if pid.get(partner_slug) else 'stanford'
            for v_idx, (variant, level, ctype, hours, weeks) in enumerate([
                    ('for Beginners', 'Beginner', 'Course', 16.0, 4.0),
                    ('Intermediate', 'Intermediate', 'Course', 22.0, 5.0),
                    ('Advanced and Cultural Fluency', 'Advanced', 'Specialization', 90.0, 20.0),
            ]):
                title = f'{lang} {variant}'
                slug = _slugify(f'{lang}-{variant}-{partner_slug}-{p_idx}-{v_idx}')
                if Course.query.filter_by(slug=slug).first():
                    continue
                c = Course(
                    title=title, slug=slug,
                    partner_id=pid.get(partner_eff),
                    course_type=ctype, level=level,
                    category='Language Learning',
                    duration_text=(f'Approx. {int(hours)} hours' if hours < 60
                                   else f'{int(weeks)} weeks at 5 hrs/wk'),
                    duration_weeks=weeks, duration_hours=hours,
                    rating=round(4.5 + ((l_idx + p_idx + v_idx) % 5) * 0.06, 2),
                    review_count=500 + l_idx * 40 + p_idx * 90 + v_idx * 220,
                    enrolled_count=12000 + l_idx * 800 + p_idx * 1700 + v_idx * 3400,
                    is_free=(v_idx == 0 and (l_idx + p_idx) % 12 == 0),
                    has_certificate=True,
                    credit_eligible=False,
                    instructor=f'{partner_eff.upper()} Language Faculty',
                    instructor_title=f'Language Faculty, {partner_eff.upper()}',
                    description=(
                        f'{title}. A {level.lower()} {lang} course delivered by '
                        f'{partner_eff.upper()}. Pronunciation labs, conversational '
                        f'practice, cultural context, and graded writing prompts.'),
                    skills=json.dumps([lang, f'{lang} Vocabulary', f'{lang} Grammar',
                                        f'{lang} Pronunciation']),
                    what_you_learn=json.dumps([
                        f'Hold {level.lower()} conversations in {lang}',
                        f'Read {level.lower()} {lang} texts',
                        f'Write graded {lang} essays',
                        f'Earn a verified {lang} certificate',
                    ]),
                    feature_tags=json.dumps([lang.lower().replace(' ', '-'),
                                              level.lower(), partner_slug,
                                              'language-learning']),
                    is_featured=(v_idx == 2 and p_idx == 0),
                    is_new=((l_idx + p_idx + v_idx) % 7 == 0),
                    sort_date=(SEED_REF_DATE - timedelta(
                        days=20 + l_idx * 6 + p_idx * 3)).strftime('%Y-%m-%d'),
                    color_class=CATEGORY_COLORS.get('Language Learning', 'cat-lang'),
                )
                db.session.add(c)
                db.session.flush()
                n_weeks = min(int(max(weeks, 1)), 6)
                for w, mod in enumerate(_v4_generic_modules(title, lang,
                                                             weeks=n_weeks), 1):
                    mt, md, v, r, q, vts = mod
                    db.session.add(CourseModule(
                        course_id=c.id, week_number=w, title=mt, description=md,
                        videos_count=v, readings_count=r, quizzes_count=q,
                        video_titles=json.dumps(vts)))
                if ctype == 'Specialization':
                    for sub_i in range(5):
                        db.session.add(SubCourse(
                            specialization_id=c.id, order_index=sub_i + 1,
                            title=f'{lang} Block {sub_i + 1}',
                            description=f'Block {sub_i + 1} of {title}.',
                            duration_text='Approx. 4 weeks'))
                created += 1
    db.session.commit()

    print(f"  + seed_v4: added {created} courses, "
          f"partners now {Partner.query.count()}, "
          f"total courses={Course.query.count()}")


# ═══════════════════════════════════════════════════════════════════════════
# seed_v5 — R4 catalog polish:
#   * +60 partners (specialised research labs, regional universities,
#     scale-up companies, language institutes)
#   * +1500 deterministic courses targeting:
#       - 80 fresh R4 topics × 4 variants  (Foundations / Hands-On /
#         Mastering / Bootcamp) ≈ 320 courses
#       - Coursera Classics (MOOC Archive) — 80 entries
#       - Industry-specials (30 industries × 8 variants) ≈ 240 courses
#       - Career-pathway module sets (20 roles × 6 modules) = 120 courses
#       - University intro/applied/seminar trio (60 partners × 3) = 180
#       - Research seminar shorts (50 topics × 4 dimensions) = 200
#       - Micro-credentials (80 × 2) = 160
#       - Lab notebooks (50 × 2) = 100
#   * All slugs prefixed `r4-…` so they cannot collide with v2/3/4 catalogs.
# Idempotent: gated on the presence of partner slug 'allen-ai'.
# ═══════════════════════════════════════════════════════════════════════════

NEW_PARTNERS_V5 = [
    # Research institutes / labs
    ('Allen Institute for AI', 'allen-ai', 'United States', 'institution', 'AI2'),
    ('Max Planck Society', 'maxplanck', 'Germany', 'institution', 'Max Planck'),
    ('Howard Hughes Medical Institute', 'hhmi', 'United States', 'institution', 'HHMI'),
    ('Wellcome Trust', 'wellcome', 'United Kingdom', 'institution', 'Wellcome'),
    ('Lawrence Berkeley National Laboratory', 'lbnl', 'United States', 'institution', 'LBNL'),
    ('Oak Ridge National Laboratory', 'ornl', 'United States', 'institution', 'ORNL'),
    ('Fraunhofer Society', 'fraunhofer', 'Germany', 'institution', 'Fraunhofer'),
    ('National Institutes of Health', 'nih', 'United States', 'institution', 'NIH'),
    ('European Molecular Biology Laboratory', 'embl', 'Germany', 'institution', 'EMBL'),
    ('Broad Institute', 'broad', 'United States', 'institution', 'Broad'),
    # Regional / less-represented universities
    ('University of Edinburgh', 'edinburgh', 'United Kingdom', 'university', 'Edinburgh'),
    ('University of Manchester', 'manchester', 'United Kingdom', 'university', 'Manchester'),
    ('University of Bristol', 'bristol', 'United Kingdom', 'university', 'Bristol'),
    ('University of Warwick', 'warwick', 'United Kingdom', 'university', 'Warwick'),
    ('University of Bath', 'bath', 'United Kingdom', 'university', 'Bath'),
    ('University of Glasgow', 'glasgow', 'United Kingdom', 'university', 'Glasgow'),
    ('Queen Mary University of London', 'qmul', 'United Kingdom', 'university', 'QMUL'),
    ('University of Leeds', 'leeds', 'United Kingdom', 'university', 'Leeds'),
    ('University of Birmingham', 'birmingham', 'United Kingdom', 'university', 'Birmingham'),
    ('University of Sheffield', 'sheffield', 'United Kingdom', 'university', 'Sheffield'),
    ('Heidelberg University', 'heidelberg', 'Germany', 'university', 'Heidelberg'),
    ('Humboldt University of Berlin', 'humboldt', 'Germany', 'university', 'Humboldt'),
    ('Free University of Berlin', 'fuberlin', 'Germany', 'university', 'FU Berlin'),
    ('Sorbonne University', 'sorbonne', 'France', 'university', 'Sorbonne'),
    ('Paris-Saclay University', 'parissaclay', 'France', 'university', 'Paris-Saclay'),
    ('Université Grenoble Alpes', 'uga', 'France', 'university', 'UGA'),
    ('University of Helsinki', 'helsinki', 'Finland', 'university', 'Helsinki'),
    ('Stockholm University', 'stockholm', 'Sweden', 'university', 'Stockholm'),
    ('University of Bergen', 'bergen', 'Norway', 'university', 'Bergen'),
    ('Aalborg University', 'aalborg', 'Denmark', 'university', 'Aalborg'),
    ('University of Iceland', 'iceland', 'Iceland', 'university', 'Iceland'),
    ('University of Bologna', 'bologna', 'Italy', 'university', 'Bologna'),
    ('Universidad Carlos III de Madrid', 'uc3m', 'Spain', 'university', 'UC3M'),
    ('University of Athens', 'uoaclassic', 'Greece', 'university', 'Athens'),
    ('Lomonosov Moscow State University', 'msu-ru', 'Russia', 'university', 'MSU'),
    ('Saint Petersburg State University', 'spbu', 'Russia', 'university', 'SPbU'),
    ('University of Ljubljana', 'uniljubljana', 'Slovenia', 'university', 'Ljubljana'),
    ('University of Zagreb', 'unizg', 'Croatia', 'university', 'Zagreb'),
    ('University of Belgrade', 'bgduni', 'Serbia', 'university', 'Belgrade'),
    ('University of Cyprus', 'ucy', 'Cyprus', 'university', 'UCY'),
    ('Lebanese American University', 'lau', 'Lebanese Republic', 'university', 'LAU'),
    ('American University of Beirut', 'aub', 'Lebanese Republic', 'university', 'AUB'),
    ('Bilkent University', 'bilkent', 'Turkey', 'university', 'Bilkent'),
    ('METU', 'metu', 'Turkey', 'university', 'METU'),
    # Latin America deep cuts
    ('Universidad de Chile', 'uchile', 'Chile', 'university', 'U. Chile'),
    ('Universidad Nacional de Córdoba', 'unc-ar', 'Argentina', 'university', 'UNC'),
    ('Universidad Autónoma de Barcelona', 'uab', 'Spain', 'university', 'UAB'),
    # African deep cuts
    ('Stellenbosch University', 'stellenbosch', 'South Africa', 'university', 'Stellenbosch'),
    ('University of the Witwatersrand', 'wits', 'South Africa', 'university', 'Wits'),
    ('Cairo University', 'cairouni', 'Egypt', 'university', 'Cairo'),
    # Asian deep cuts
    ('Indian Institute of Technology Kharagpur', 'iitkgp', 'India', 'university', 'IIT Kharagpur'),
    ('Indian Institute of Technology Kanpur', 'iitk', 'India', 'university', 'IIT Kanpur'),
    ('BITS Pilani', 'bits', 'India', 'university', 'BITS'),
    ('Yonsei University', 'yonsei', 'South Korea', 'university', 'Yonsei'),
    ('Korea University', 'koreauni', 'South Korea', 'university', 'Korea U.'),
    ('Tohoku University', 'tohoku', 'Japan', 'university', 'Tohoku'),
    ('Osaka University', 'osaka', 'Japan', 'university', 'Osaka'),
    ('Zhejiang University', 'zju', 'China', 'university', 'ZJU'),
    ('Nankai University', 'nankai', 'China', 'university', 'Nankai'),
    # Scale-ups / industry
    ('Anthropic', 'anthropic', 'United States', 'company', 'Anthropic'),
    ('OpenAI', 'openai', 'United States', 'company', 'OpenAI'),
    ('Cohere', 'cohere', 'Canada', 'company', 'Cohere'),
    ('Mistral AI', 'mistral', 'France', 'company', 'Mistral'),
    ('Stability AI', 'stability', 'United Kingdom', 'company', 'Stability'),
]


# Fresh R4 topics — not overlapping with existing CS/DS/etc topic lists
R4_TOPICS = [
    # Generative AI / Agents
    ('Agentic AI Engineering', 'AI Agents', 'Computer Science', 'anthropic'),
    ('Multimodal Foundation Models', 'Multimodal AI', 'Computer Science', 'openai'),
    ('Tool-Use and Function Calling for LLMs', 'LLM Tools', 'Computer Science', 'anthropic'),
    ('RAG at Scale', 'RAG Systems', 'Data Science', 'mongodb'),
    ('Retrieval Evaluation Methodology', 'Retrieval Evaluation', 'Data Science', 'allen-ai'),
    ('Prompt Optimisation and Eval Harnesses', 'Prompt Eval', 'Data Science', 'cohere'),
    ('LLM Guardrails and Red-Teaming', 'AI Safety', 'Computer Science', 'anthropic'),
    ('Open-Source LLMs from Scratch', 'Open LLMs', 'Computer Science', 'mistral'),
    ('Diffusion Models for Vision', 'Diffusion Models', 'Computer Science', 'stability'),
    ('Speech Foundation Models', 'Speech Models', 'Computer Science', 'openai'),
    ('Long-Context Transformers', 'Long Context', 'Computer Science', 'allen-ai'),
    ('Mixture-of-Experts Models', 'MoE Models', 'Computer Science', 'mistral'),
    # Quantum / Frontier
    ('Quantum Error Correction', 'Quantum Computing', 'Physical Science and Engineering', 'ibm'),
    ('Quantum Sensing for Engineers', 'Quantum Sensing', 'Physical Science and Engineering', 'mit'),
    ('Topological Qubits', 'Quantum Computing', 'Physical Science and Engineering', 'ethz'),
    # Sustainability / Climate
    ('Lifecycle Assessment for Products', 'LCA', 'Physical Science and Engineering', 'tudelft'),
    ('Circular Economy Design', 'Circular Economy', 'Physical Science and Engineering', 'tudelft'),
    ('Decarbonising Industry', 'Industrial Decarbonisation', 'Physical Science and Engineering', 'siemens'),
    ('Carbon Accounting for Businesses', 'Carbon Accounting', 'Business', 'mckinsey'),
    ('Green Hydrogen Engineering', 'Green Hydrogen', 'Physical Science and Engineering', 'siemens'),
    ('Energy Storage Systems', 'Energy Storage', 'Physical Science and Engineering', 'mit'),
    # BioTech / HealthTech
    ('CRISPR Genome Editing', 'Genome Editing', 'Health', 'broad'),
    ('Single-Cell Genomics', 'Single-Cell Omics', 'Health', 'embl'),
    ('Protein Design with AI', 'AI for Proteins', 'Health', 'embl'),
    ('Clinical Decision Support Systems', 'Clinical DSS', 'Health', 'nih'),
    ('Wearable Health Analytics', 'Wearables', 'Health', 'jhu'),
    ('Mental Health Tech Design', 'Mental Health Tech', 'Health', 'nih'),
    ('AI for Drug Discovery', 'AI for Drugs', 'Health', 'broad'),
    # Robotics / Spatial
    ('Humanoid Robotics', 'Humanoid Robots', 'Physical Science and Engineering', 'cmu'),
    ('Soft Robotics', 'Soft Robotics', 'Physical Science and Engineering', 'epfl'),
    ('Drone Engineering', 'UAV Engineering', 'Physical Science and Engineering', 'ethz'),
    ('Autonomous Vehicle Perception', 'AV Perception', 'Computer Science', 'nvidia'),
    ('Mixed-Reality Interaction Design', 'MR Design', 'Arts and Humanities', 'meta'),
    ('Spatial Computing Foundations', 'Spatial Computing', 'Computer Science', 'meta'),
    # Data Engineering / Platform
    ('Lakehouse Architecture', 'Lakehouse', 'Data Science', 'databricks'),
    ('Data Contracts and Quality', 'Data Contracts', 'Data Science', 'snowflake'),
    ('Modern dbt Patterns', 'dbt Patterns', 'Data Science', 'snowflake'),
    ('Real-Time Analytics with Flink', 'Apache Flink', 'Data Science', 'databricks'),
    ('Feature Stores in Practice', 'Feature Stores', 'Data Science', 'databricks'),
    # Cybersecurity
    ('Cloud Security Posture Management', 'CSPM', 'Information Technology', 'cloudflare'),
    ('Supply-Chain Security', 'Supply-Chain Security', 'Information Technology', 'github'),
    ('Identity and Access Management', 'IAM', 'Information Technology', 'oktasoftware' if False else 'cisco'),
    ('Threat Hunting with eBPF', 'eBPF', 'Information Technology', 'datadog'),
    ('Cryptographic Engineering', 'Crypto Engineering', 'Information Technology', 'cloudflare'),
    # Business / Operations
    ('Pricing in B2B SaaS', 'B2B Pricing', 'Business', 'hubspot'),
    ('Product-Led Growth', 'PLG', 'Business', 'hubspot'),
    ('Customer Success Operations', 'CS Ops', 'Business', 'salesforce'),
    ('B2B Demand Generation', 'B2B DemandGen', 'Business', 'hubspot'),
    ('Revenue Operations', 'RevOps', 'Business', 'salesforce'),
    ('Enterprise Sales Methodology', 'Enterprise Sales', 'Business', 'salesforce'),
    # Finance / FinTech
    ('Open Banking Engineering', 'Open Banking', 'Business', 'stripe'),
    ('Risk Management for Crypto Assets', 'Crypto Risk', 'Business', 'jpmorgan'),
    ('Embedded Finance Foundations', 'Embedded Finance', 'Business', 'stripe'),
    ('Fraud Detection with ML', 'Fraud Detection', 'Data Science', 'klarna'),
    # Education / Communication
    ('Learning Engineering', 'Learning Engineering', 'Social Sciences', 'stanford'),
    ('Inclusive Pedagogy', 'Pedagogy', 'Social Sciences', 'oxford'),
    ('Online Teaching at Scale', 'Online Teaching', 'Social Sciences', 'meta'),
    ('Science Communication for Researchers', 'SciComm', 'Personal Development', 'wellcome'),
    ('Data-Driven Journalism', 'Data Journalism', 'Arts and Humanities', 'nyu'),
    ('Documentary Filmmaking', 'Documentary', 'Arts and Humanities', 'usc'),
    # Personal development / Career
    ('Async Communication for Distributed Teams', 'Async Comms', 'Personal Development', 'atlassian'),
    ('Performance Reviews Done Right', 'Performance Reviews', 'Personal Development', 'workday'),
    ('Interview Calibration for Hiring Managers', 'Interview Calibration', 'Personal Development', 'workday'),
    ('Personal Branding for Engineers', 'Personal Branding', 'Personal Development', 'github'),
    # Math
    ('Convex Optimisation', 'Convex Optimisation', 'Math and Logic', 'stanford'),
    ('Information Theory', 'Information Theory', 'Math and Logic', 'mit'),
    ('Numerical Linear Algebra', 'Numerical LA', 'Math and Logic', 'cmu'),
    ('Stochastic Processes', 'Stochastic Processes', 'Math and Logic', 'princeton'),
    # Languages — under-represented
    ('Swahili Conversation', 'Swahili', 'Language Learning', 'uon'),
    ('Vietnamese for Travellers', 'Vietnamese', 'Language Learning', 'vnu'),
    ('Modern Greek Foundations', 'Greek', 'Language Learning', 'uoaclassic'),
    ('Polish for Beginners', 'Polish', 'Language Learning', 'uw-pl'),
    ('Czech for Beginners', 'Czech', 'Language Learning', 'cuni'),
    ('Modern Hebrew', 'Hebrew', 'Language Learning', 'tau'),
    ('Turkish Conversation', 'Turkish', 'Language Learning', 'bilkent'),
    ('Indonesian for Beginners', 'Indonesian', 'Language Learning', 'ui-id'),
    # Arts
    ('Sound Design for Games', 'Sound Design', 'Arts and Humanities', 'usc'),
    ('Type Design Foundations', 'Type Design', 'Arts and Humanities', 'sony'),
    ('Watercolour Foundations', 'Watercolour', 'Arts and Humanities', 'louvre'),
    ('History of Photography', 'Photography History', 'Arts and Humanities', 'smithsonian'),
    ('Choreography for Beginners', 'Choreography', 'Arts and Humanities', 'usc'),
    ('Curating Modern Art', 'Curatorial Practice', 'Arts and Humanities', 'moma' if False else 'smithsonian'),
]


R4_VARIANTS = [
    # (prefix,           level,         course_type, hours, weeks, weeks_for_mods, base_enrolled, base_reviews)
    ('Foundations of',   'Beginner',    'Course',    12.0, 3.0, 3, 26000, 1800),
    ('Hands-On',         'Beginner',    'Course',    14.0, 3.5, 3, 30000, 2300),
    ('Mastering',        'Intermediate','Course',    24.0, 6.0, 5, 22000, 1700),
    ('Bootcamp:',        'Intermediate','Course',    36.0, 9.0, 6, 18000, 1500),
    ('Capstone in',      'Advanced',    'Course',    32.0, 8.0, 6, 14000, 1100),
]


# Foundation_topics from seed_v4 is reused here for partner-keyed extras.
_R4_FOUND_TOPICS = [
    ('Generative AI', 'Computer Science', 'deeplearningai'),
    ('Large Language Models', 'Computer Science', 'deeplearningai'),
    ('Prompt Engineering', 'Computer Science', 'deeplearningai'),
    ('Vector Databases', 'Data Science', 'mongodb'),
    ('Quantum Computing', 'Physical Science and Engineering', 'ibm'),
    ('Computer Vision', 'Computer Science', 'nvidia'),
    ('Natural Language Processing', 'Computer Science', 'deeplearningai'),
    ('Reinforcement Learning', 'Data Science', 'deeplearningai'),
    ('Linear Algebra', 'Math and Logic', 'mit'),
    ('Cryptography', 'Computer Science', 'stanford'),
    ('Distributed Systems', 'Computer Science', 'mit'),
    ('Algorithms', 'Computer Science', 'stanford'),
    ('Python for Everybody', 'Computer Science', 'umich'),
    ('TypeScript Mastery', 'Computer Science', 'meta'),
    ('Microservices Patterns', 'Information Technology', 'redhat'),
    ('Site Reliability Engineering', 'Information Technology', 'google'),
    ('Cloud Native Architecture', 'Information Technology', 'redhat'),
    ('Snowflake Data Cloud', 'Data Science', 'snowflake'),
    ('Databricks Lakehouse', 'Data Science', 'databricks'),
    ('ML Ops on AWS', 'Data Science', 'aws'),
    ('Renewable Energy Systems', 'Physical Science and Engineering', 'tudelft'),
    ('Solar Engineering', 'Physical Science and Engineering', 'tudelft'),
    ('Materials Science', 'Physical Science and Engineering', 'mit'),
    ('Drug Discovery', 'Health', 'jhu'),
    ('Telemedicine', 'Health', 'jhu'),
    ('Public Speaking', 'Personal Development', 'georgetown'),
    ('Behavioral Economics', 'Social Sciences', 'duke'),
    ('Game Theory', 'Social Sciences', 'stanford'),
    ('Sustainable Cities', 'Social Sciences', 'tudelft'),
    ('Climate Policy', 'Social Sciences', 'oxford'),
]


# MOOC Classics (free, marquee Coursera courses across the platform)
R4_CLASSICS = [
    # (title, primary, category, partner, hours)
    ('Machine Learning by Andrew Ng (Classic)', 'Machine Learning', 'Data Science', 'stanford', 55.0),
    ('Algorithms Part I (Classic)', 'Algorithms', 'Computer Science', 'princeton', 60.0),
    ('Algorithms Part II (Classic)', 'Algorithms', 'Computer Science', 'princeton', 60.0),
    ('Programming Languages (Dan Grossman)', 'Programming Languages', 'Computer Science', 'uwashington', 50.0),
    ('Cryptography I (Boneh)', 'Cryptography', 'Computer Science', 'stanford', 48.0),
    ('Introduction to Computer Science', 'Computer Science', 'Computer Science', 'harvard' if False else 'mit', 100.0),
    ('Software Construction', 'Software Construction', 'Computer Science', 'mit', 60.0),
    ('Discrete Optimization', 'Optimization', 'Math and Logic', 'umelbourne', 50.0),
    ('Linear and Integer Programming', 'Optimization', 'Math and Logic', 'cuboulder', 36.0),
    ('Bayesian Statistics: From Concept to Data Analysis', 'Bayesian Statistics', 'Math and Logic', 'ucsc' if False else 'cuboulder', 24.0),
    ('Probabilistic Graphical Models', 'PGM', 'Math and Logic', 'stanford', 50.0),
    ('Game Theory I (Stanford)', 'Game Theory', 'Social Sciences', 'stanford', 30.0),
    ('Game Theory II: Advanced Applications', 'Game Theory', 'Social Sciences', 'stanford', 30.0),
    ('Calculus One', 'Calculus', 'Math and Logic', 'osu' if False else 'umich', 40.0),
    ('Calculus Two: Sequences and Series', 'Calculus', 'Math and Logic', 'umich', 40.0),
    ('Coding the Matrix: Linear Algebra', 'Linear Algebra', 'Math and Logic', 'brown', 35.0),
    ('Theoretical Astrophysics', 'Astrophysics', 'Physical Science and Engineering', 'caltech', 35.0),
    ('Geometry Foundations', 'Geometry', 'Math and Logic', 'edinburgh', 30.0),
    ('Number Theory and Cryptography', 'Number Theory', 'Math and Logic', 'ucsd', 35.0),
    ('Introduction to Logic', 'Logic', 'Math and Logic', 'stanford', 30.0),
    ('Image and Video Processing', 'Image Processing', 'Computer Science', 'duke', 36.0),
    ('Functional Programming Principles in Scala', 'Scala', 'Computer Science', 'epfl', 36.0),
    ('Parallel Programming with Scala', 'Parallel Programming', 'Computer Science', 'epfl', 30.0),
    ('Compilers (Aiken)', 'Compilers', 'Computer Science', 'stanford', 80.0),
    ('Computer Architecture (Patterson)', 'Computer Architecture', 'Computer Science', 'berkeley', 60.0),
    ('Operating Systems and Systems Programming', 'Operating Systems', 'Computer Science', 'berkeley', 60.0),
    ('Programming Mobile Apps for Android', 'Android', 'Computer Science', 'umd', 36.0),
    ('Programming Cloud Services for Android', 'Android Cloud', 'Computer Science', 'vanderbilt', 30.0),
    ('Hadoop Platform and Application Framework', 'Hadoop', 'Data Science', 'ucsd', 30.0),
    ('Introduction to Big Data (Older)', 'Big Data', 'Data Science', 'ucsd', 24.0),
    ('Recommender Systems Specialization (Classic)', 'Recommender Systems', 'Data Science', 'umn', 80.0),
    ('Practical Machine Learning', 'Machine Learning', 'Data Science', 'jhu', 24.0),
    ('Data Analysis and Statistical Inference', 'Statistical Inference', 'Data Science', 'duke', 30.0),
    ('Drugs and the Brain (Classic)', 'Pharmacology', 'Health', 'caltech', 24.0),
    ('Vital Signs: Understanding What the Body Is Telling Us', 'Clinical Skills', 'Health', 'upenn', 18.0),
    ('Songwriting (Berklee Classic)', 'Songwriting', 'Arts and Humanities', 'usc', 24.0),
    ('Music Production (Berklee Classic)', 'Music Production', 'Arts and Humanities', 'usc', 24.0),
    ('The Modern World (Yale Classic)', 'Modern History', 'Arts and Humanities', 'yale', 35.0),
    ('Roman Architecture (Yale Classic)', 'Architecture', 'Arts and Humanities', 'yale', 24.0),
    ('Greek and Roman Mythology (Penn)', 'Mythology', 'Arts and Humanities', 'upenn', 28.0),
    ('A History of the World Since 1300', 'World History', 'Arts and Humanities', 'princeton', 28.0),
    ('Astrobiology and the Search for Extraterrestrial Life', 'Astrobiology', 'Physical Science and Engineering', 'edinburgh', 18.0),
    ('Volcanic Eruptions', 'Volcanology', 'Physical Science and Engineering', 'manchester', 14.0),
    ('Dinosaur Paleobiology', 'Paleobiology', 'Physical Science and Engineering', 'alberta' if False else 'edinburgh', 14.0),
    ('Forensic Psychology', 'Forensic Psychology', 'Social Sciences', 'manchester', 24.0),
    ('Internet History, Technology and Security', 'Internet History', 'Information Technology', 'umich', 28.0),
    ('Networks Friends Money and Bytes', 'Networking', 'Information Technology', 'princeton', 30.0),
    ('Bitcoin and Cryptocurrency Technologies', 'Cryptocurrency', 'Information Technology', 'princeton', 24.0),
    ('Internet Giants: The Law and Economics of Media Platforms', 'Tech Policy', 'Social Sciences', 'columbia', 24.0),
    ('Buddhism and Modern Psychology', 'Buddhism', 'Arts and Humanities', 'princeton', 18.0),
    ('Moralities of Everyday Life', 'Moral Psychology', 'Social Sciences', 'yale', 30.0),
    ('Justice (Sandel Classic)', 'Political Philosophy', 'Social Sciences', 'harvard' if False else 'yale', 35.0),
    ('Critical Issues in Urban Education', 'Urban Education', 'Social Sciences', 'upenn', 30.0),
    ('Foundations of Teaching for Learning', 'Pedagogy', 'Social Sciences', 'ucl' if False else 'ulondon', 35.0),
    ('Reading Behind the Lines', 'Literary Studies', 'Arts and Humanities', 'edinburgh', 20.0),
    ('Modern and Contemporary American Poetry', 'Poetry', 'Arts and Humanities', 'upenn', 28.0),
    ('Shakespeare in Community', 'Shakespeare', 'Arts and Humanities', 'wisc', 24.0),
    ('Comic Books and Graphic Novels', 'Comics Studies', 'Arts and Humanities', 'cuboulder', 18.0),
    ('Plagues, Witches and War', 'Historical Fiction', 'Arts and Humanities', 'uva' if False else 'uoaclassic', 18.0),
    ('Property and Liability', 'Law', 'Social Sciences', 'upenn', 35.0),
    ('American Capitalism: A History', 'Economic History', 'Social Sciences', 'cornell', 30.0),
    ('Energy 101', 'Energy Systems', 'Physical Science and Engineering', 'gatech', 28.0),
    ('Wind Energy (DTU Classic)', 'Wind Energy', 'Physical Science and Engineering', 'tudelft', 35.0),
    ('Solar Energy: Photovoltaic Systems', 'Solar PV', 'Physical Science and Engineering', 'tudelft', 30.0),
    ('Hadron Collider Physics', 'Particle Physics', 'Physical Science and Engineering', 'epfl', 24.0),
    ('Gravity!', 'General Relativity', 'Physical Science and Engineering', 'parissaclay', 30.0),
    ('Mountains 101', 'Geomorphology', 'Physical Science and Engineering', 'mcgill', 28.0),
    ('Wildlife Ecology', 'Ecology', 'Physical Science and Engineering', 'ualberta' if False else 'wits', 20.0),
    ('Tropical Coastal Ecosystems', 'Marine Ecology', 'Physical Science and Engineering', 'uq', 24.0),
    ('Genomic Data Science Specialization (Classic)', 'Genomics', 'Data Science', 'jhu', 80.0),
    ('Systems Biology and Biotechnology (Classic)', 'Systems Biology', 'Health', 'mit', 60.0),
    ('Bioinformatics Specialization (Classic)', 'Bioinformatics', 'Data Science', 'ucsd', 80.0),
    ('Chinese for Beginners (PKU Classic)', 'Mandarin', 'Language Learning', 'pku', 36.0),
    ('English Composition I', 'English Composition', 'Language Learning', 'duke', 28.0),
    ('Tricky English Grammar', 'English Grammar', 'Language Learning', 'uci', 18.0),
    ('Better Business Writing', 'Business Writing', 'Language Learning', 'gatech', 12.0),
    ('Effective Communication', 'Communication', 'Personal Development', 'georgia-tech' if False else 'gatech', 16.0),
    ('Successful Negotiation', 'Negotiation', 'Business', 'umich', 16.0),
    ('Inspiring Leadership through Emotional Intelligence', 'Emotional Intelligence', 'Business', 'cwru' if False else 'umich', 24.0),
    ('On Strategy: What Managers Can Learn from Philosophy', 'Strategy', 'Business', 'hec', 28.0),
    ('Foundations of Modern Finance', 'Finance', 'Business', 'mit', 30.0),
    ('Financial Markets (Shiller Classic)', 'Financial Markets', 'Business', 'yale', 35.0),
]


def _v5_make_topic_course(prefix, level, course_type, hours, weeks,
                          module_weeks, base_enrolled, base_reviews,
                          topic, primary, category, partner_slug, idx, pid):
    """Build a single deterministic course spec for an R4 topic variant."""
    title = f'{prefix} {topic}'.strip()
    slug = _slugify(f'r4-{prefix.lower().rstrip(":")}-{topic}')
    skills = [primary, 'Hands-on Practice', 'Portfolio Project']
    learn = [
        f'Apply {primary} to real problems',
        f'Practice {topic.lower()} through graded labs',
        f'Build a portfolio piece in {primary}',
        f'Earn a shareable certificate in {primary}',
    ]
    rating = round(4.5 + (idx % 5) * 0.06, 2)
    is_new = (idx % 3 == 0)
    is_free = (idx % 19 == 0)
    days_back = 8 + (idx * 7) % 380
    sort_dt = SEED_REF_DATE - timedelta(days=days_back)
    tags = [primary.lower().replace(' ', '-').replace('/', '-'),
            level.lower(), partner_slug, 'r4-catalog',
            prefix.lower().rstrip(':').replace(' ', '-')]
    return dict(
        title=title, slug=slug,
        partner_id=pid.get(partner_slug),
        partner_slug=partner_slug,
        course_type=course_type, level=level,
        category=category,
        duration_text=(f'Approx. {int(hours)} hours' if hours < 80
                       else f'{int(weeks)} weeks at 6 hrs/wk'),
        duration_weeks=weeks, duration_hours=hours,
        rating=rating,
        review_count=base_reviews + (idx % 11) * 250,
        enrolled_count=base_enrolled + (idx % 17) * 1900,
        is_free=is_free, has_certificate=True,
        credit_eligible=(prefix == 'Capstone in' and idx % 7 == 0),
        instructor=f'{partner_slug.upper()} Faculty',
        instructor_title=f'Faculty, {partner_slug.upper()}',
        description=(
            f'{title}. A {level.lower()} {course_type.lower()} in {topic}. '
            f'Built around {primary} with hands-on labs, graded assignments, '
            f'and a portfolio-grade final project.'),
        skills=skills, what_you_learn=learn,
        feature_tags=tags,
        is_featured=(idx % 31 == 0),
        is_new=is_new,
        sort_date=sort_dt.strftime('%Y-%m-%d'),
        color_class=CATEGORY_COLORS.get(category, 'cat-cs'),
        primary=primary, module_weeks=module_weeks,
    )


def seed_v5(db, models):
    """R4 catalog polish — adds ~1500 deterministic courses + 60 partners.
    Idempotent — gated on the presence of partner slug 'allen-ai'."""
    User = models['User']
    Partner = models['Partner']
    Course = models['Course']
    CourseModule = models['CourseModule']
    SubCourse = models['SubCourse']
    Enrollment = models['Enrollment']
    SavedCourse = models['SavedCourse']
    Review = models['Review']

    if Partner.query.filter_by(slug='allen-ai').first():
        return  # already seeded

    # 1) Partners ──────────────────────────────────────────────────────────
    for name, slug, country, ptype, short in NEW_PARTNERS_V5:
        if Partner.query.filter_by(slug=slug).first():
            continue
        db.session.add(Partner(name=name, slug=slug, country=country,
                               partner_type=ptype, short_name=short))
    db.session.commit()

    pid = {p.slug: p.id for p in Partner.query.all()}
    created = 0

    def _add_modules(course_id, course_title, primary, weeks):
        """Add deterministic weekly modules with rich video titles."""
        for w in range(1, weeks + 1):
            if w == 1:
                mt = f'Week {w}: {primary} Foundations'
                md = (f'Orientation: mental model, prerequisites, and the '
                      f'first {primary} concept in action.')
            elif w == weeks:
                mt = f'Week {w}: Capstone — Ship Your {primary} Project'
                md = (f'Capstone: take everything you learned and build a '
                      f'portfolio-grade {primary} artefact.')
            else:
                mt = f'Week {w}: Applied {primary}'
                md = (f'Hands-on lab + graded assignment exercising your '
                      f'{primary} skills.')
            vts = [
                f'Lesson {w}.1: {mt}',
                f'Lesson {w}.2: Worked example for {primary}',
                f'Lesson {w}.3: Practice drill ({course_title})',
                f'Lesson {w}.4: Office-hour clip — common pitfalls',
            ]
            db.session.add(CourseModule(
                course_id=course_id, week_number=w, title=mt, description=md,
                videos_count=5, readings_count=3, quizzes_count=1,
                video_titles=json.dumps(vts)))

    # 2) Fresh R4 topics × 5 variants ──────────────────────────────────────
    idx = 0
    for topic, primary, category, partner_slug in R4_TOPICS:
        partner_eff = partner_slug if pid.get(partner_slug) else 'stanford'
        for (prefix, level, ctype, hours, weeks, mod_weeks,
             base_enrolled, base_reviews) in R4_VARIANTS:
            spec = _v5_make_topic_course(
                prefix, level, ctype, hours, weeks, mod_weeks,
                base_enrolled, base_reviews, topic, primary, category,
                partner_eff, idx, pid)
            idx += 1
            if Course.query.filter_by(slug=spec['slug']).first():
                continue
            c = Course(
                title=spec['title'], slug=spec['slug'],
                partner_id=spec['partner_id'], course_type=spec['course_type'],
                level=spec['level'], category=spec['category'],
                duration_text=spec['duration_text'],
                duration_weeks=spec['duration_weeks'],
                duration_hours=spec['duration_hours'],
                rating=spec['rating'], review_count=spec['review_count'],
                enrolled_count=spec['enrolled_count'],
                is_free=spec['is_free'], has_certificate=spec['has_certificate'],
                credit_eligible=spec['credit_eligible'],
                instructor=spec['instructor'],
                instructor_title=spec['instructor_title'],
                description=spec['description'],
                skills=json.dumps(spec['skills']),
                what_you_learn=json.dumps(spec['what_you_learn']),
                feature_tags=json.dumps(spec['feature_tags']),
                is_featured=spec['is_featured'], is_new=spec['is_new'],
                sort_date=spec['sort_date'],
                color_class=spec['color_class'])
            db.session.add(c)
            db.session.flush()
            _add_modules(c.id, c.title, spec['primary'], spec['module_weeks'])
            created += 1
    db.session.commit()

    # 3) MOOC Classics (one course per entry) ──────────────────────────────
    for c_idx, (title, primary, category, partner_slug, hours) in enumerate(
            R4_CLASSICS):
        partner_eff = partner_slug if pid.get(partner_slug) else 'stanford'
        slug = _slugify(f'r4-classic-{title}')
        if Course.query.filter_by(slug=slug).first():
            continue
        weeks = max(3.0, min(20.0, hours / 8.0))
        c = Course(
            title=f'{title}', slug=slug,
            partner_id=pid.get(partner_eff),
            course_type='Course', level='Intermediate',
            category=category,
            duration_text=f'Approx. {int(hours)} hours',
            duration_weeks=weeks, duration_hours=hours,
            rating=round(4.7 + (c_idx % 3) * 0.05, 2),
            review_count=8000 + c_idx * 130,
            enrolled_count=240000 + c_idx * 4500,
            is_free=True, has_certificate=True,
            credit_eligible=False,
            instructor=f'{partner_eff.upper()} Faculty',
            instructor_title=f'Faculty, {partner_eff.upper()}',
            description=(
                f'{title} — a Coursera Classic. A free, marquee course from '
                f'{partner_eff.upper()} originally launched in the early '
                f'MOOC era and continually refreshed. Hands-on assignments, '
                f'graded discussions, and a portfolio capstone.'),
            skills=json.dumps([primary, 'Critical Thinking',
                                'Problem Solving']),
            what_you_learn=json.dumps([
                f'Master the fundamentals of {primary}',
                f'Apply {primary} to canonical problems',
                f'Earn a shareable Coursera Classic certificate',
                f'Join the alumni network for {primary} learners',
            ]),
            feature_tags=json.dumps([primary.lower().replace(' ', '-'),
                                      'classic', 'mooc-archive', 'free',
                                      partner_eff, 'r4-catalog']),
            is_featured=(c_idx % 11 == 0),
            is_new=False,
            sort_date=(SEED_REF_DATE - timedelta(
                days=200 + c_idx * 4)).strftime('%Y-%m-%d'),
            color_class=CATEGORY_COLORS.get(category, 'cat-cs'))
        db.session.add(c)
        db.session.flush()
        _add_modules(c.id, title, primary, max(3, int(min(weeks, 6))))
        created += 1
    db.session.commit()

    # 4) Industry-specials — 30 industries × 8 variants ────────────────────
    R4_INDUSTRIES = [
        ('AI Safety', 'Computer Science', ['anthropic', 'openai', 'allen-ai']),
        ('AgriTech', 'Physical Science and Engineering', ['tudelft', 'wageningen' if False else 'tudelft', 'siemens']),
        ('AutoTech', 'Physical Science and Engineering', ['bmw', 'mercedes', 'toyota']),
        ('Aerospace', 'Physical Science and Engineering', ['nasa', 'esa', 'mit']),
        ('Biotech', 'Health', ['broad', 'embl', 'jhu']),
        ('Climate Tech', 'Physical Science and Engineering', ['tudelft', 'siemens', 'mit']),
        ('Construction Tech', 'Physical Science and Engineering', ['siemens', 'gatech', 'tudelft']),
        ('Crypto / Web3', 'Computer Science', ['github', 'stripe', 'jpmorgan']),
        ('Defence Tech', 'Information Technology', ['cmu', 'mit', 'gatech']),
        ('EdTech', 'Social Sciences', ['stanford', 'meta', 'google']),
        ('EV / Battery', 'Physical Science and Engineering', ['bmw', 'mit', 'siemens']),
        ('Enterprise SaaS', 'Information Technology', ['servicenow', 'salesforce', 'workday']),
        ('FinTech', 'Business', ['stripe', 'klarna', 'jpmorgan']),
        ('GovTech', 'Social Sciences', ['worldbank', 'oecd', 'imf']),
        ('GreenTech', 'Physical Science and Engineering', ['tudelft', 'mit', 'siemens']),
        ('HealthTech', 'Health', ['jhu', 'nih', 'broad']),
        ('Hospitality Tech', 'Business', ['booking', 'hubspot', 'salesforce']),
        ('Insurance Tech', 'Business', ['nyu', 'cornell', 'mckinsey']),
        ('Legal Tech', 'Social Sciences', ['georgetown', 'oxford', 'nyu']),
        ('Logistics Tech', 'Business', ['mit', 'gatech', 'sap']),
        ('MarTech', 'Business', ['hubspot', 'meta', 'salesforce']),
        ('Media Tech', 'Arts and Humanities', ['nyu', 'sony', 'spotify']),
        ('NeuroTech', 'Health', ['mit', 'ki', 'embl']),
        ('PropTech', 'Business', ['mit', 'cornell', 'columbia']),
        ('Public Health Tech', 'Health', ['who', 'jhu', 'nih']),
        ('RetailTech', 'Business', ['shopify', 'salesforce', 'meta']),
        ('Sports Analytics', 'Data Science', ['cornell', 'mit', 'umich']),
        ('Supply Chain Tech', 'Business', ['sap', 'mit', 'gatech']),
        ('TravelTech', 'Business', ['booking', 'stripe', 'aws']),
        ('Workforce Tech', 'Business', ['workday', 'salesforce', 'sap']),
    ]
    INDUSTRY_VARIANTS = [
        ('Foundations',   'Beginner',    'Course',                  12.0, 3.0, 3),
        ('Engineering',   'Intermediate','Course',                  24.0, 6.0, 5),
        ('Architecture',  'Intermediate','Course',                  20.0, 5.0, 4),
        ('Leadership',    'Intermediate','Course',                  14.0, 3.5, 3),
        ('Capstone',      'Advanced',    'Course',                  30.0, 7.5, 6),
        ('Specialization','Intermediate','Specialization',          90.0, 18.0, 5),
        ('Cert',          'Beginner',    'Professional Certificate',110.0, 26.0, 5),
        ('Workshop',      'Beginner',    'Guided Project',           1.5, 0.25, 1),
    ]
    for i_idx, (industry, category, partners) in enumerate(R4_INDUSTRIES):
        for p_idx, partner_slug in enumerate(partners):
            partner_eff = partner_slug if pid.get(partner_slug) else 'stanford'
            for v_idx, (variant, level, ctype, hours, weeks, mod_weeks) in enumerate(INDUSTRY_VARIANTS):
                title = f'{industry} {variant} ({partner_eff.upper()})'
                slug = _slugify(f'r4-industry-{industry}-{variant}-{partner_eff}-{p_idx}-{v_idx}')
                if Course.query.filter_by(slug=slug).first():
                    continue
                idx = i_idx * 100 + p_idx * 10 + v_idx
                c = Course(
                    title=title, slug=slug,
                    partner_id=pid.get(partner_eff),
                    course_type=ctype, level=level,
                    category=category, subcategory=industry,
                    duration_text=(f'Less Than 2 Hours' if ctype == 'Guided Project'
                                   else (f'Approx. {int(hours)} hours' if hours < 60
                                         else f'{int(weeks)} weeks at 5 hrs/wk')),
                    duration_weeks=weeks, duration_hours=hours,
                    rating=round(4.4 + (idx % 5) * 0.07, 2),
                    review_count=500 + idx * 7,
                    enrolled_count=12000 + idx * 230,
                    is_free=(idx % 23 == 0 and ctype != 'Professional Certificate'),
                    has_certificate=(ctype != 'Guided Project'),
                    credit_eligible=(ctype == 'Professional Certificate' and idx % 5 == 0),
                    instructor=f'{partner_eff.upper()} Practice Lead',
                    instructor_title=f'Practice Lead, {partner_eff.upper()}',
                    description=(
                        f'{title}. A {level.lower()} program in {industry}. '
                        f'Built with {partner_eff.upper()} subject-matter experts. '
                        f'Real datasets, hands-on labs, and a graded capstone.'),
                    skills=json.dumps([industry, f'{industry} Engineering',
                                       f'{industry} Strategy']),
                    what_you_learn=json.dumps([
                        f'Map the {industry} value chain',
                        f'Apply {industry} tools to a portfolio piece',
                        f'Earn a verifiable {industry} credential',
                        f'Network with the {industry} community',
                    ]),
                    feature_tags=json.dumps([industry.lower().replace(' ', '-').replace('/', '-'),
                                              level.lower(), partner_eff,
                                              variant.lower(), 'r4-industry']),
                    is_featured=(v_idx == 6 and p_idx == 0),
                    is_new=((i_idx + p_idx + v_idx) % 7 == 0),
                    sort_date=(SEED_REF_DATE - timedelta(
                        days=10 + i_idx * 5 + p_idx * 3 + v_idx)).strftime('%Y-%m-%d'),
                    color_class=CATEGORY_COLORS.get(category, 'cat-cs'))
                db.session.add(c)
                db.session.flush()
                n_weeks = max(1, min(int(weeks), 6)) if ctype != 'Guided Project' else 1
                _add_modules(c.id, title, industry, n_weeks)
                if ctype == 'Specialization':
                    for s_i in range(5):
                        db.session.add(SubCourse(
                            specialization_id=c.id, order_index=s_i + 1,
                            title=f'{industry} Block {s_i + 1}',
                            description=f'Block {s_i + 1} of the {industry} Specialization.',
                            duration_text='Approx. 4 weeks'))
                created += 1
    db.session.commit()

    # 5) Career-pathway modules — 20 careers × 6 sub-modules ───────────────
    R4_CAREER_PATHS = [
        ('AI Engineer', 'ai-engineer', 'Computer Science', 'anthropic',
         ['LLM Foundations', 'Agentic Systems', 'Eval Pipelines',
          'Production LLMOps', 'Prompt Security', 'Capstone']),
        ('Prompt Engineer', 'prompt-engineer', 'Computer Science', 'anthropic',
         ['Prompt Patterns', 'Few-Shot Design', 'Chain-of-Thought',
          'Tool Use', 'Eval Loops', 'Capstone']),
        ('Solutions Architect', 'solutions-architect', 'Information Technology', 'aws',
         ['Cloud Foundations', 'Networking', 'Compute', 'Storage',
          'Security', 'Capstone']),
        ('Platform Engineer', 'platform-engineer', 'Information Technology', 'redhat',
         ['Kubernetes Foundations', 'GitOps', 'Service Mesh',
          'Observability', 'Platform UX', 'Capstone']),
        ('Site Reliability Engineer', 'sre', 'Information Technology', 'google',
         ['SLI/SLO/SLA', 'Incident Response', 'Toil Reduction',
          'Capacity Planning', 'Postmortems', 'Capstone']),
        ('Security Engineer', 'security-engineer', 'Information Technology', 'cloudflare',
         ['Threat Modeling', 'AppSec', 'Network Security',
          'IAM', 'Detection Engineering', 'Capstone']),
        ('Data Engineer', 'data-engineer', 'Data Science', 'databricks',
         ['Data Modelling', 'Pipelines', 'Lakehouse', 'Streaming',
          'Data Contracts', 'Capstone']),
        ('Analytics Engineer', 'analytics-engineer', 'Data Science', 'snowflake',
         ['SQL Mastery', 'Modelling with dbt', 'Quality',
          'BI Layer', 'Documentation', 'Capstone']),
        ('Quantitative Analyst', 'quant-analyst', 'Math and Logic', 'jpmorgan',
         ['Probability', 'Stochastic Calculus', 'Modelling',
          'Python for Quants', 'Risk', 'Capstone']),
        ('Research Scientist', 'research-scientist', 'Data Science', 'allen-ai',
         ['Reading the Literature', 'Experimental Design',
          'Open-source Releases', 'Reproducibility',
          'Publishing', 'Capstone']),
        ('Software Architect', 'software-architect', 'Computer Science', 'cmu',
         ['Patterns', 'Distributed Systems', 'API Design',
          'Performance', 'Cost', 'Capstone']),
        ('Engineering Manager', 'engineering-manager', 'Business', 'github',
         ['1:1s', 'Performance', 'Hiring', 'Strategy',
          'Conflict', 'Capstone']),
        ('Director of Engineering', 'director-engineering', 'Business', 'meta',
         ['Org Design', 'Roadmaps', 'Hiring Bar', 'Vendor Mgmt',
          'Exec Communication', 'Capstone']),
        ('Tech Lead', 'tech-lead', 'Computer Science', 'github',
         ['Mentorship', 'Tech Vision', 'Reviews',
          'Influence', 'Sprint Planning', 'Capstone']),
        ('Engineering Recruiter', 'engineering-recruiter', 'Business', 'workday',
         ['Sourcing', 'Interview Loops', 'Bar Calibration',
          'Diversity Hiring', 'Closing', 'Capstone']),
        ('Customer Success Manager', 'csm', 'Business', 'salesforce',
         ['Onboarding', 'Adoption', 'Renewals', 'Expansion',
          'Voice of Customer', 'Capstone']),
        ('Solutions Engineer', 'solutions-engineer', 'Business', 'salesforce',
         ['Discovery', 'Demos', 'POCs', 'Architecture Notes',
          'Handoffs', 'Capstone']),
        ('Technical Writer', 'technical-writer', 'Arts and Humanities', 'github',
         ['Audience Modelling', 'Information Architecture',
          'Tooling', 'Editing', 'Diagrams', 'Capstone']),
        ('Game Producer', 'game-producer', 'Arts and Humanities', 'usc',
         ['Pre-Production', 'Scheduling', 'Live-Ops',
          'Localization', 'Marketing', 'Capstone']),
        ('Product Designer', 'product-designer', 'Arts and Humanities', 'meta',
         ['Discovery', 'Wireframing', 'Visual Design',
          'Prototyping', 'Critique', 'Capstone']),
    ]
    for r_idx, (role, role_slug, category, partner_slug, modules) in enumerate(
            R4_CAREER_PATHS):
        partner_eff = partner_slug if pid.get(partner_slug) else 'meta'
        for m_idx, module in enumerate(modules):
            title = f'{role} Pathway: {module}'
            slug = _slugify(f'r4-pathway-{role_slug}-{module}')
            if Course.query.filter_by(slug=slug).first():
                continue
            ctype = 'Course'
            hours = 18.0 if m_idx < 5 else 26.0
            weeks = 4.0 if m_idx < 5 else 6.0
            c = Course(
                title=title, slug=slug,
                partner_id=pid.get(partner_eff),
                course_type=ctype, level='Intermediate',
                category=category, subcategory=role,
                duration_text=f'Approx. {int(hours)} hours',
                duration_weeks=weeks, duration_hours=hours,
                rating=round(4.5 + ((r_idx + m_idx) % 5) * 0.06, 2),
                review_count=900 + r_idx * 30 + m_idx * 110,
                enrolled_count=15000 + r_idx * 600 + m_idx * 2700,
                is_free=False, has_certificate=True,
                credit_eligible=(m_idx == 5 and r_idx % 4 == 0),
                instructor=f'{partner_eff.upper()} Career Coach',
                instructor_title=f'Career Coach, {partner_eff.upper()}',
                description=(
                    f'{title}. Module {m_idx + 1} of the {role} career path. '
                    f'A {("capstone" if m_idx == 5 else "skills")}-focused '
                    f'course building on prior modules with hands-on labs '
                    f'and feedback from {partner_eff.upper()} engineers.'),
                skills=json.dumps([module, role, 'Career Development']),
                what_you_learn=json.dumps([
                    f'Master {module} for the {role} role',
                    f'Apply {module} to a portfolio project',
                    f'Receive feedback from {partner_eff.upper()} coaches',
                    f'Earn a verifiable pathway credential',
                ]),
                feature_tags=json.dumps([role_slug, module.lower().replace(' ', '-'),
                                          partner_eff, 'r4-pathway']),
                is_featured=(m_idx == 0),
                is_new=(r_idx % 3 == m_idx % 3),
                sort_date=(SEED_REF_DATE - timedelta(
                    days=15 + r_idx * 4 + m_idx * 2)).strftime('%Y-%m-%d'),
                color_class=CATEGORY_COLORS.get(category, 'cat-cs'))
            db.session.add(c)
            db.session.flush()
            _add_modules(c.id, title, module, int(weeks))
            created += 1
    db.session.commit()

    # 6) University intros — 60 partners × 3 (intro/applied/seminar) ───────
    R4_UNIV_INTROS = [
        # Spread across new + existing partners; safe slugs only.
        ('edinburgh', 'Computer Science', 'Algorithms'),
        ('manchester', 'Computer Science', 'Software Engineering'),
        ('bristol', 'Physical Science and Engineering', 'Robotics'),
        ('warwick', 'Math and Logic', 'Statistics'),
        ('bath', 'Business', 'Operations'),
        ('glasgow', 'Health', 'Public Health'),
        ('qmul', 'Computer Science', 'Data Structures'),
        ('leeds', 'Social Sciences', 'Politics'),
        ('birmingham', 'Information Technology', 'Networking'),
        ('sheffield', 'Physical Science and Engineering', 'Materials Science'),
        ('heidelberg', 'Health', 'Genetics'),
        ('humboldt', 'Arts and Humanities', 'Philosophy'),
        ('fuberlin', 'Social Sciences', 'Political Theory'),
        ('sorbonne', 'Arts and Humanities', 'Literature'),
        ('parissaclay', 'Physical Science and Engineering', 'Particle Physics'),
        ('uga', 'Computer Science', 'AI'),
        ('helsinki', 'Computer Science', 'Programming'),
        ('stockholm', 'Social Sciences', 'Economics'),
        ('bergen', 'Health', 'Marine Biology'),
        ('aalborg', 'Physical Science and Engineering', 'Wind Energy'),
        ('iceland', 'Physical Science and Engineering', 'Geophysics'),
        ('bologna', 'Arts and Humanities', 'Medieval History'),
        ('uc3m', 'Business', 'Economics'),
        ('uoaclassic', 'Arts and Humanities', 'Ancient Greek'),
        ('msu-ru', 'Math and Logic', 'Pure Mathematics'),
        ('spbu', 'Physical Science and Engineering', 'Theoretical Physics'),
        ('uniljubljana', 'Social Sciences', 'Anthropology'),
        ('unizg', 'Computer Science', 'Software Testing'),
        ('bgduni', 'Math and Logic', 'Probability'),
        ('ucy', 'Computer Science', 'Cybersecurity'),
        ('lau', 'Business', 'Entrepreneurship'),
        ('aub', 'Arts and Humanities', 'Middle East Studies'),
        ('bilkent', 'Computer Science', 'Algorithms'),
        ('metu', 'Physical Science and Engineering', 'Mechanical Engineering'),
        ('uchile', 'Social Sciences', 'Latin American Studies'),
        ('unc-ar', 'Health', 'Tropical Medicine'),
        ('uab', 'Arts and Humanities', 'Catalan Studies'),
        ('stellenbosch', 'Business', 'African Markets'),
        ('wits', 'Social Sciences', 'African History'),
        ('cairouni', 'Arts and Humanities', 'Arabic Linguistics'),
        ('iitkgp', 'Computer Science', 'Algorithms'),
        ('iitk', 'Computer Science', 'Compilers'),
        ('bits', 'Information Technology', 'Cloud Computing'),
        ('yonsei', 'Business', 'Asian Markets'),
        ('koreauni', 'Social Sciences', 'East Asian Politics'),
        ('tohoku', 'Physical Science and Engineering', 'Robotics'),
        ('osaka', 'Health', 'Drug Discovery'),
        ('zju', 'Computer Science', 'AI Systems'),
        ('nankai', 'Math and Logic', 'Number Theory'),
        # Reuse a handful of original partners for cross-coverage
        ('mit', 'Computer Science', 'Distributed Systems'),
        ('stanford', 'Computer Science', 'Algorithms'),
        ('berkeley', 'Computer Science', 'Operating Systems'),
        ('cmu', 'Computer Science', 'Software Engineering'),
        ('upenn', 'Business', 'Finance'),
        ('columbia', 'Business', 'Marketing'),
        ('umich', 'Health', 'Public Health'),
        ('jhu', 'Health', 'Epidemiology'),
        ('utoronto', 'Computer Science', 'AI'),
        ('mcgill', 'Health', 'Neuroscience'),
        ('ubc', 'Computer Science', 'HCI'),
        ('ulondon', 'Business', 'Finance'),
    ]
    UNIV_VARIANTS = [
        ('Intro to', 'Beginner', 12.0, 3.0, 3),
        ('Applied', 'Intermediate', 22.0, 5.0, 5),
        ('Seminar in', 'Advanced', 14.0, 3.5, 3),
    ]
    for u_idx, (partner_slug, category, topic) in enumerate(R4_UNIV_INTROS):
        partner_eff = partner_slug if pid.get(partner_slug) else 'stanford'
        for v_idx, (variant, level, hours, weeks, mod_weeks) in enumerate(UNIV_VARIANTS):
            title = f'{variant} {topic} ({partner_eff.upper()})'
            slug = _slugify(f'r4-univ-{partner_eff}-{topic}-{variant}-{u_idx}-{v_idx}')
            if Course.query.filter_by(slug=slug).first():
                continue
            idx = u_idx * 10 + v_idx
            c = Course(
                title=title, slug=slug,
                partner_id=pid.get(partner_eff),
                course_type='Course', level=level,
                category=category,
                duration_text=f'Approx. {int(hours)} hours',
                duration_weeks=weeks, duration_hours=hours,
                rating=round(4.5 + (idx % 5) * 0.06, 2),
                review_count=600 + idx * 12,
                enrolled_count=14000 + idx * 480,
                is_free=(idx % 17 == 0),
                has_certificate=True,
                credit_eligible=False,
                instructor=f'{partner_eff.upper()} Senior Instructor',
                instructor_title=f'Senior Instructor, {partner_eff.upper()}',
                description=(
                    f'{title}. A {level.lower()} course in {topic} delivered '
                    f'by {partner_eff.upper()}. Combines lectures, recitations, '
                    f'and weekly graded labs.'),
                skills=json.dumps([topic, 'Critical Thinking', 'Problem Solving']),
                what_you_learn=json.dumps([
                    f'Master {topic} fundamentals at {partner_eff.upper()}',
                    f'Apply {topic} through graded labs',
                    f'Earn a shareable certificate',
                    f'Build a portfolio piece in {topic}',
                ]),
                feature_tags=json.dumps([topic.lower().replace(' ', '-'),
                                          level.lower(), partner_eff,
                                          'r4-university-intro']),
                is_featured=(v_idx == 0 and u_idx % 11 == 0),
                is_new=(u_idx % 5 == v_idx),
                sort_date=(SEED_REF_DATE - timedelta(
                    days=12 + u_idx * 3 + v_idx * 2)).strftime('%Y-%m-%d'),
                color_class=CATEGORY_COLORS.get(category, 'cat-cs'))
            db.session.add(c)
            db.session.flush()
            _add_modules(c.id, title, topic, int(weeks))
            created += 1
    db.session.commit()

    # 7) Research seminars — 50 topics × 4 partners (seminar shorts) ───────
    R4_RESEARCH_TOPICS = [
        ('LLM Alignment Seminar', 'AI Alignment', 'Computer Science'),
        ('Mechanistic Interpretability Seminar', 'Interpretability', 'Computer Science'),
        ('Diffusion Models Seminar', 'Diffusion Models', 'Computer Science'),
        ('Reinforcement Learning from Human Feedback Seminar', 'RLHF', 'Computer Science'),
        ('Cryptographic Protocols Seminar', 'Cryptography', 'Computer Science'),
        ('Privacy-Preserving ML Seminar', 'Privacy ML', 'Computer Science'),
        ('Federated Learning Seminar', 'Federated Learning', 'Data Science'),
        ('Causal Inference Seminar', 'Causal Inference', 'Data Science'),
        ('Bayesian Optimisation Seminar', 'Bayesian Optimisation', 'Data Science'),
        ('Robust Statistics Seminar', 'Robust Statistics', 'Math and Logic'),
        ('High-Dimensional Probability Seminar', 'High-Dim Probability', 'Math and Logic'),
        ('Algebraic Topology Seminar', 'Topology', 'Math and Logic'),
        ('Quantum Information Seminar', 'Quantum Information', 'Physical Science and Engineering'),
        ('Plasma Physics Seminar', 'Plasma Physics', 'Physical Science and Engineering'),
        ('Astrophysics Seminar', 'Astrophysics', 'Physical Science and Engineering'),
        ('Climate Modelling Seminar', 'Climate Modelling', 'Physical Science and Engineering'),
        ('Synthetic Biology Seminar', 'Synthetic Biology', 'Health'),
        ('Single-Cell Omics Seminar', 'Single-Cell Omics', 'Health'),
        ('Neuroscience Seminar', 'Neuroscience', 'Health'),
        ('Health Policy Seminar', 'Health Policy', 'Health'),
        ('Behavioural Economics Seminar', 'Behavioural Economics', 'Social Sciences'),
        ('Political Theory Seminar', 'Political Theory', 'Social Sciences'),
        ('Migration Studies Seminar', 'Migration Studies', 'Social Sciences'),
        ('Gender Studies Seminar', 'Gender Studies', 'Social Sciences'),
        ('Postcolonial Studies Seminar', 'Postcolonial Studies', 'Arts and Humanities'),
        ('Renaissance Art Seminar', 'Renaissance Art', 'Arts and Humanities'),
        ('Cinema Studies Seminar', 'Cinema Studies', 'Arts and Humanities'),
        ('Sound Studies Seminar', 'Sound Studies', 'Arts and Humanities'),
        ('Computational Linguistics Seminar', 'Computational Linguistics', 'Arts and Humanities'),
        ('Distributed Systems Seminar', 'Distributed Systems', 'Computer Science'),
        ('Software Verification Seminar', 'Verification', 'Computer Science'),
        ('Programming Language Theory Seminar', 'PL Theory', 'Computer Science'),
        ('Type Systems Seminar', 'Type Systems', 'Computer Science'),
        ('Database Systems Seminar', 'Database Systems', 'Computer Science'),
        ('Computer Graphics Seminar', 'Computer Graphics', 'Computer Science'),
        ('Human-Computer Interaction Seminar', 'HCI', 'Computer Science'),
        ('Accessibility Seminar', 'Accessibility', 'Computer Science'),
        ('Game Studies Seminar', 'Game Studies', 'Arts and Humanities'),
        ('Music Information Retrieval Seminar', 'MIR', 'Data Science'),
        ('Computational Social Science Seminar', 'CSS', 'Social Sciences'),
        ('Epidemiology Methods Seminar', 'Epidemiology Methods', 'Health'),
        ('Sustainable Cities Seminar', 'Sustainable Cities', 'Social Sciences'),
        ('Circular Economy Seminar', 'Circular Economy', 'Physical Science and Engineering'),
        ('AgriTech Seminar', 'AgriTech', 'Physical Science and Engineering'),
        ('EdTech Seminar', 'EdTech', 'Social Sciences'),
        ('GovTech Seminar', 'GovTech', 'Social Sciences'),
        ('FinTech Seminar', 'FinTech', 'Business'),
        ('HealthTech Seminar', 'HealthTech', 'Health'),
        ('SpaceTech Seminar', 'SpaceTech', 'Physical Science and Engineering'),
        ('Robotics Seminar', 'Robotics', 'Physical Science and Engineering'),
    ]
    seminar_partners = ['mit', 'stanford', 'berkeley', 'cmu', 'oxford',
                         'cambridge', 'ethz', 'epfl', 'tudelft', 'allen-ai',
                         'maxplanck', 'broad']
    for s_idx, (title, primary, category) in enumerate(R4_RESEARCH_TOPICS):
        for p_idx in range(4):
            partner_slug = seminar_partners[(s_idx * 7 + p_idx * 11) % len(seminar_partners)]
            partner_eff = partner_slug if pid.get(partner_slug) else 'mit'
            slug = _slugify(f'r4-seminar-{title}-{partner_eff}-{p_idx}')
            if Course.query.filter_by(slug=slug).first():
                continue
            idx = s_idx * 20 + p_idx
            c = Course(
                title=f'{title} ({partner_eff.upper()})', slug=slug,
                partner_id=pid.get(partner_eff),
                course_type='Course', level='Advanced',
                category=category,
                duration_text='Approx. 10 hours',
                duration_weeks=2.5, duration_hours=10.0,
                rating=round(4.5 + (idx % 5) * 0.07, 2),
                review_count=320 + idx * 5,
                enrolled_count=4500 + idx * 130,
                is_free=False, has_certificate=True,
                credit_eligible=False,
                instructor=f'{partner_eff.upper()} Faculty Panel',
                instructor_title=f'Faculty Panel, {partner_eff.upper()}',
                description=(
                    f'{title} from {partner_eff.upper()}. A short, advanced '
                    f'seminar in {primary}: weekly papers, live discussions, '
                    f'and a graded reading response. Open to motivated '
                    f'learners with prior background in the area.'),
                skills=json.dumps([primary, 'Research Reading',
                                    'Critical Analysis']),
                what_you_learn=json.dumps([
                    f'Read modern papers in {primary}',
                    f'Defend a position in {primary}',
                    f'Write a focused research note in {primary}',
                    f'Build a network of {primary} peers',
                ]),
                feature_tags=json.dumps([primary.lower().replace(' ', '-'),
                                          'advanced', partner_eff,
                                          'r4-seminar', 'research']),
                is_featured=False,
                is_new=(idx % 4 == 0),
                sort_date=(SEED_REF_DATE - timedelta(
                    days=8 + s_idx * 2 + p_idx)).strftime('%Y-%m-%d'),
                color_class=CATEGORY_COLORS.get(category, 'cat-cs'))
            db.session.add(c)
            db.session.flush()
            _add_modules(c.id, title, primary, 3)
            created += 1
    db.session.commit()

    # 8) Micro-credentials — 80 short, ≤6h badge courses ───────────────────
    R4_MICRO_TOPICS = [
        ('Pandas Power-Ups', 'Pandas', 'Data Science', 'ibm'),
        ('Excel Mastery Drills', 'Excel', 'Business', 'microsoft'),
        ('Notion for Knowledge Work', 'Notion', 'Personal Development', 'workday'),
        ('Linear Regression Refresher', 'Statistics', 'Math and Logic', 'duke'),
        ('SQL Window Functions', 'SQL', 'Data Science', 'snowflake'),
        ('Pivot Tables in Depth', 'Excel', 'Business', 'microsoft'),
        ('Regex Crash Course', 'Regex', 'Computer Science', 'github'),
        ('Bash for Engineers', 'Bash', 'Information Technology', 'redhat'),
        ('Git Power Moves', 'Git', 'Computer Science', 'github'),
        ('Docker in 90 Minutes', 'Docker', 'Information Technology', 'redhat'),
        ('Kubernetes Quick Start', 'Kubernetes', 'Information Technology', 'redhat'),
        ('Terraform Basics', 'Terraform', 'Information Technology', 'aws'),
        ('JIRA Workflow Patterns', 'Jira', 'Business', 'atlassian'),
        ('Slack Bot Mini-Project', 'Slack', 'Computer Science', 'github'),
        ('Stripe Checkout Drill', 'Stripe', 'Business', 'stripe'),
        ('AWS S3 Mini-Lab', 'AWS S3', 'Information Technology', 'aws'),
        ('Azure DevOps Pipelines', 'Azure DevOps', 'Information Technology', 'microsoft'),
        ('GCP Cloud Run Quickstart', 'Cloud Run', 'Information Technology', 'google'),
        ('Power BI Mini-Lab', 'Power BI', 'Data Science', 'microsoft'),
        ('Tableau Mini-Lab', 'Tableau', 'Data Science', 'tableau'),
        ('Looker Quickstart', 'Looker', 'Data Science', 'google'),
        ('GA4 Drill', 'GA4', 'Business', 'google'),
        ('SEO Audit Workflow', 'SEO', 'Business', 'hubspot'),
        ('Content Calendar Workflow', 'Content', 'Business', 'hubspot'),
        ('LinkedIn Recruiting Power Moves', 'LinkedIn Recruiter', 'Business', 'workday'),
        ('Sourcing Boolean Strings', 'Boolean Sourcing', 'Business', 'workday'),
        ('A/B Testing Drill', 'A/B Testing', 'Business', 'meta'),
        ('Looker Studio Quickstart', 'Looker Studio', 'Data Science', 'google'),
        ('Apache Airflow DAG Basics', 'Airflow', 'Data Science', 'snowflake'),
        ('dbt Cloud Quickstart', 'dbt', 'Data Science', 'databricks'),
        ('Streamlit App in 90 Minutes', 'Streamlit', 'Data Science', 'snowflake'),
        ('Plotly Dash Drill', 'Plotly', 'Data Science', 'ibm'),
        ('Matplotlib Drill', 'Matplotlib', 'Data Science', 'ibm'),
        ('seaborn Cookbook', 'Seaborn', 'Data Science', 'ibm'),
        ('SciPy Stats Drill', 'SciPy', 'Data Science', 'ibm'),
        ('Hugging Face Pipelines', 'Hugging Face', 'Data Science', 'deeplearningai'),
        ('LangChain Quickstart', 'LangChain', 'Computer Science', 'deeplearningai'),
        ('LlamaIndex Drill', 'LlamaIndex', 'Computer Science', 'deeplearningai'),
        ('OpenAI API Drill', 'OpenAI API', 'Computer Science', 'openai'),
        ('Anthropic Claude API Drill', 'Anthropic API', 'Computer Science', 'anthropic'),
        ('Cohere Embeddings Drill', 'Cohere', 'Computer Science', 'cohere'),
        ('Mistral API Quickstart', 'Mistral API', 'Computer Science', 'mistral'),
        ('Stable Diffusion Drill', 'Stable Diffusion', 'Arts and Humanities', 'stability'),
        ('Whisper Speech Drill', 'Whisper', 'Computer Science', 'openai'),
        ('Stable Audio Drill', 'Stable Audio', 'Arts and Humanities', 'stability'),
        ('Midjourney Workflow', 'Midjourney', 'Arts and Humanities', 'meta'),
        ('Figma Auto-Layout Drill', 'Figma', 'Arts and Humanities', 'meta'),
        ('Sketch Plugin Workflow', 'Sketch', 'Arts and Humanities', 'meta'),
        ('Storybook for Designers', 'Storybook', 'Arts and Humanities', 'github'),
        ('Webflow Mini-Lab', 'Webflow', 'Arts and Humanities', 'meta'),
        ('Framer Mini-Lab', 'Framer', 'Arts and Humanities', 'meta'),
        ('Salesforce Trail Mini-Module', 'Salesforce', 'Business', 'salesforce'),
        ('Workday Studio Mini-Module', 'Workday', 'Business', 'workday'),
        ('ServiceNow Flow Designer', 'ServiceNow Flow', 'Business', 'servicenow'),
        ('HubSpot Workflow Builder', 'HubSpot', 'Business', 'hubspot'),
        ('Zendesk Triggers Mini-Lab', 'Zendesk', 'Business', 'zendesk'),
        ('Datadog APM Drill', 'Datadog APM', 'Information Technology', 'datadog'),
        ('PagerDuty Incident Drill', 'PagerDuty', 'Information Technology', 'datadog'),
        ('Sentry Setup Drill', 'Sentry', 'Information Technology', 'github'),
        ('GitHub Actions Mini-Pipeline', 'GitHub Actions', 'Information Technology', 'github'),
        ('GitLab CI Mini-Pipeline', 'GitLab CI', 'Information Technology', 'github'),
        ('Argo CD Quickstart', 'Argo CD', 'Information Technology', 'redhat'),
        ('Helm Chart Drill', 'Helm', 'Information Technology', 'redhat'),
        ('Istio Traffic Splitting', 'Istio', 'Information Technology', 'redhat'),
        ('OpenTelemetry Setup', 'OpenTelemetry', 'Information Technology', 'datadog'),
        ('Prometheus Mini-Lab', 'Prometheus', 'Information Technology', 'datadog'),
        ('Grafana Dashboards Drill', 'Grafana', 'Information Technology', 'datadog'),
        ('Loki Logs Drill', 'Loki', 'Information Technology', 'datadog'),
        ('Spark Streaming Drill', 'Spark Streaming', 'Data Science', 'databricks'),
        ('Kafka Connect Drill', 'Kafka Connect', 'Data Science', 'databricks'),
        ('Schema Registry Drill', 'Schema Registry', 'Data Science', 'databricks'),
        ('Iceberg Tables Drill', 'Apache Iceberg', 'Data Science', 'snowflake'),
        ('Delta Lake Drill', 'Delta Lake', 'Data Science', 'databricks'),
        ('Unity Catalog Drill', 'Unity Catalog', 'Data Science', 'databricks'),
        ('Snowpark Drill', 'Snowpark', 'Data Science', 'snowflake'),
        ('Materialised Views Drill', 'Materialised Views', 'Data Science', 'snowflake'),
        ('Vertex AI Pipeline Drill', 'Vertex AI', 'Data Science', 'google'),
        ('SageMaker Pipelines Drill', 'SageMaker', 'Data Science', 'aws'),
        ('Azure ML Pipeline Drill', 'Azure ML', 'Data Science', 'microsoft'),
        ('MLflow Tracking Drill', 'MLflow', 'Data Science', 'databricks'),
        ('Weights & Biases Drill', 'Weights & Biases', 'Data Science', 'databricks'),
    ]
    for m_idx, (title, primary, category, partner_slug) in enumerate(R4_MICRO_TOPICS):
        partner_eff = partner_slug if pid.get(partner_slug) else 'github'
        for v_idx, (variant, hours) in enumerate([('Drill', 1.5), ('Lab', 3.0)]):
            full_title = f'{title} ({variant})' if variant != 'Drill' or 'Drill' not in title else title
            slug = _slugify(f'r4-micro-{title}-{variant}-{m_idx}-{v_idx}')
            if Course.query.filter_by(slug=slug).first():
                continue
            c = Course(
                title=full_title, slug=slug,
                partner_id=pid.get(partner_eff),
                course_type=('Guided Project' if hours < 2 else 'Course'),
                level='Beginner', category=category,
                duration_text=('Less Than 2 Hours' if hours < 2
                               else f'Approx. {int(hours)} hours'),
                duration_weeks=(0.25 if hours < 2 else 1.0),
                duration_hours=hours,
                rating=round(4.6 + ((m_idx + v_idx) % 4) * 0.05, 2),
                review_count=180 + (m_idx + v_idx) * 6,
                enrolled_count=3500 + (m_idx + v_idx) * 110,
                is_free=False,
                has_certificate=(hours >= 2),
                credit_eligible=False,
                instructor=f'{partner_eff.upper()} Mentor',
                instructor_title=f'Mentor, {partner_eff.upper()}',
                description=(
                    f'{full_title}. A {int(hours * 60)}-minute drill on '
                    f'{primary}. Walk through a hands-on workflow with an '
                    f'{partner_eff.upper()} mentor in split-screen and finish '
                    f'with a portfolio-ready artefact.'),
                skills=json.dumps([primary, 'Hands-on Practice']),
                what_you_learn=json.dumps([
                    f'Run a focused {primary} workflow end-to-end',
                    f'Apply {primary} to a real artefact',
                    f'Walk away with a portfolio sample',
                ]),
                feature_tags=json.dumps([primary.lower().replace(' ', '-'),
                                          'micro-credential', partner_eff,
                                          variant.lower(), 'r4-catalog']),
                is_featured=False,
                is_new=((m_idx + v_idx) % 5 == 0),
                sort_date=(SEED_REF_DATE - timedelta(
                    days=4 + m_idx + v_idx * 2)).strftime('%Y-%m-%d'),
                color_class=CATEGORY_COLORS.get(category, 'cat-cs'))
            db.session.add(c)
            db.session.flush()
            db.session.add(CourseModule(
                course_id=c.id, week_number=1,
                title=f'Drill: {primary}',
                description=f'A single {int(hours * 60)}-minute hands-on drill.',
                videos_count=4, readings_count=1, quizzes_count=0,
                video_titles=json.dumps([
                    f'Step 1: Set up the {primary} workspace',
                    f'Step 2: Run the core {primary} task',
                    f'Step 3: Inspect the output',
                    f'Step 4: Polish and ship',
                ])))
            created += 1
    db.session.commit()

    print(f"  + seed_v5: added {created} courses, "
          f"partners now {Partner.query.count()}, "
          f"total courses={Course.query.count()}")


# ──────────────────────────────────────────────────────────────────────────────
# seed_v6 — R5 polish:
#   * +20 partners (xAI, Cohere, AI21, Together, Replit, LangChain, Pinecone,
#     Weaviate, Vercel, Modular/Mojo, Boston Dynamics, ABB, Toyota Research,
#     Figure AI, NIST, NIH AI, ESA, IBM Quantum, Rigetti, IonQ, PsiQuantum,
#     Quantinuum, D-Wave, etc.)
#   * ~2200 new deterministic 2024-2025 courses across:
#       - GenAI Foundations & Diffusion
#       - LLM Engineering & Eval
#       - Agentic AI (LangGraph / CrewAI / AutoGen / SmolAgents / DSPy)
#       - Quantum Computing & QML
#       - Robotics & Humanoids
#   * fills `preview_video_url`, `textbook_isbn`,
#     `estimated_workload_hours_per_week` on every course (existing + new).
# Byte-deterministic — all timestamps derive from SEED_REF_DATE, all hashes
# are stable (slug-keyed), no random/datetime.now.
# Idempotency sentinel: presence of partner slug 'xai-r5'.
# ──────────────────────────────────────────────────────────────────────────────

NEW_PARTNERS_V6 = [
    # ── New AI labs & infra (2024-2025 wave) ────────────────────────────────
    ('xAI', 'xai-r5', 'United States', 'company', 'xAI'),
    ('AI21 Labs', 'ai21', 'Israel', 'company', 'AI21'),
    ('Together AI', 'together', 'United States', 'company', 'Together'),
    ('Replit', 'replit', 'United States', 'company', 'Replit'),
    ('LangChain', 'langchain', 'United States', 'company', 'LangChain'),
    ('LlamaIndex Inc.', 'llamaindex', 'United States', 'company', 'LlamaIndex'),
    ('Pinecone', 'pinecone', 'United States', 'company', 'Pinecone'),
    ('Weaviate', 'weaviate', 'Netherlands', 'company', 'Weaviate'),
    ('Vercel', 'vercel', 'United States', 'company', 'Vercel'),
    ('Modular', 'modular', 'United States', 'company', 'Modular (Mojo)'),
    # ── Robotics primes ─────────────────────────────────────────────────────
    ('Boston Dynamics', 'boston-dynamics-r5', 'United States', 'company', 'Boston Dynamics'),
    ('ABB Robotics', 'abb-r5', 'Switzerland', 'company', 'ABB'),
    ('Toyota Research Institute', 'tri-r5', 'United States', 'institution', 'TRI'),
    ('Figure AI', 'figure-ai-r5', 'United States', 'company', 'Figure'),
    ('Agility Robotics', 'agility-r5', 'United States', 'company', 'Agility'),
    # ── Quantum primes ──────────────────────────────────────────────────────
    ('IBM Quantum', 'ibm-quantum-r5', 'United States', 'institution', 'IBM Quantum'),
    ('Rigetti Computing', 'rigetti-r5', 'United States', 'company', 'Rigetti'),
    ('IonQ', 'ionq-r5', 'United States', 'company', 'IonQ'),
    ('Quantinuum', 'quantinuum-r5', 'United Kingdom', 'company', 'Quantinuum'),
    ('PsiQuantum', 'psiquantum-r5', 'United States', 'company', 'PsiQuantum'),
    ('D-Wave Systems', 'dwave-r5', 'Canada', 'company', 'D-Wave'),
]

# Topic catalog — each topic produces ~5-7 variants × ~3 partners.
# (topic, primary_skill, category, [preferred_partner_slugs])
R5_GENAI_TOPICS = [
    ('Generative AI Foundations', 'Generative AI', 'Computer Science',
     ['deeplearningai', 'openai', 'anthropic', 'google']),
    ('Text-to-Image Diffusion Models', 'Diffusion Models', 'Computer Science',
     ['stanford', 'stability', 'openai', 'meta']),
    ('Stable Diffusion XL Workflows', 'Stable Diffusion', 'Arts and Humanities',
     ['stability', 'meta', 'deeplearningai']),
    ('Latent Consistency & Distillation', 'Diffusion', 'Computer Science',
     ['stanford', 'meta', 'openai']),
    ('Audio Generation with MusicLM & AudioLM', 'Audio Generation', 'Arts and Humanities',
     ['google', 'meta', 'stability']),
    ('Video Diffusion Models (Sora / Veo / Runway)', 'Video Generation', 'Computer Science',
     ['openai', 'google', 'meta']),
    ('3D Generative AI (NeRF / Gaussian Splat)', '3D Generative AI', 'Computer Science',
     ['nvidia', 'meta', 'google']),
    ('Generative AI for Product Design', 'GenAI Design', 'Arts and Humanities',
     ['meta', 'adobe', 'deeplearningai']),
    ('Generative AI in Healthcare', 'GenAI Health', 'Health',
     ['jhu', 'nih', 'google']),
    ('Generative AI for Finance', 'GenAI Finance', 'Business',
     ['jpmorgan', 'stripe', 'mckinsey']),
    ('Generative AI for Education', 'GenAI Education', 'Social Sciences',
     ['stanford', 'meta', 'google']),
    ('Multimodal Foundations (CLIP, Flamingo, Gemini)', 'Multimodal Models', 'Computer Science',
     ['google', 'meta', 'openai']),
    ('Vision-Language Models 2025', 'VLMs', 'Computer Science',
     ['google', 'anthropic', 'allen-ai']),
    ('Speech-to-Speech Real-Time Models', 'Speech Models', 'Computer Science',
     ['openai', 'google', 'meta']),
    ('Generative AI Safety & Red-Teaming', 'GenAI Safety', 'Computer Science',
     ['anthropic', 'allen-ai', 'openai']),
    ('Generative AI Copyright & IP', 'GenAI Policy', 'Social Sciences',
     ['oxford', 'cambridge', 'georgetown']),
    ('Generative AI Product Management', 'GenAI PM', 'Business',
     ['google', 'meta', 'workday']),
    ('Generative AI for Marketing', 'GenAI Marketing', 'Business',
     ['hubspot', 'salesforce', 'meta']),
    ('Diffusion Transformers (DiT) Deep Dive', 'DiT', 'Computer Science',
     ['meta', 'openai', 'stanford']),
    ('Conditional Generation & Guidance', 'CFG', 'Computer Science',
     ['stanford', 'google', 'meta']),
    ('Generative AI Evaluation (FID/CLIPScore)', 'GenAI Eval', 'Data Science',
     ['allen-ai', 'stanford', 'cmu']),
    ('GenAI for Game Asset Production', 'GenAI Games', 'Arts and Humanities',
     ['nvidia', 'meta', 'google']),
    ('GenAI Fine-Tuning with LoRA & QLoRA', 'LoRA', 'Computer Science',
     ['huggingface' if False else 'deeplearningai', 'meta', 'openai']),
    ('Generative AI for Architecture', 'GenAI Architecture', 'Arts and Humanities',
     ['meta', 'adobe', 'stanford']),
    ('Generative AI for Drug Discovery', 'GenAI Drugs', 'Health',
     ['broad', 'nih', 'jhu']),
]

R5_LLM_TOPICS = [
    ('LLM Engineering Essentials', 'LLM Engineering', 'Computer Science',
     ['deeplearningai', 'openai', 'anthropic']),
    ('Prompt Engineering 2025', 'Prompt Engineering', 'Computer Science',
     ['deeplearningai', 'anthropic', 'openai']),
    ('LLM Evaluation & Benchmarks', 'LLM Eval', 'Data Science',
     ['stanford', 'allen-ai', 'deeplearningai']),
    ('RAG Patterns at Production Scale', 'RAG', 'Computer Science',
     ['langchain', 'llamaindex', 'pinecone']),
    ('Vector Databases & Hybrid Search', 'Vector DBs', 'Computer Science',
     ['pinecone', 'weaviate', 'snowflake']),
    ('LLM Fine-Tuning with LoRA / QLoRA', 'Fine-Tuning', 'Computer Science',
     ['deeplearningai', 'meta', 'mistral']),
    ('LLM Distillation & Quantisation', 'LLM Optimisation', 'Computer Science',
     ['meta', 'mistral', 'together']),
    ('LLM Serving with vLLM & TGI', 'LLM Serving', 'Information Technology',
     ['together', 'aws', 'nvidia']),
    ('LLM Observability & Tracing', 'LLM Observability', 'Information Technology',
     ['datadog', 'langchain', 'github']),
    ('LLM Cost Optimisation', 'LLM Cost', 'Business',
     ['together', 'openai', 'anthropic']),
    ('Long-Context LLMs (1M-Token)', 'Long Context', 'Computer Science',
     ['google', 'anthropic', 'meta']),
    ('Function Calling & Tool Use', 'Tool Use', 'Computer Science',
     ['openai', 'anthropic', 'langchain']),
    ('Structured Output (JSON Mode, Outlines)', 'Structured Output', 'Computer Science',
     ['openai', 'anthropic', 'mistral']),
    ('Safety Guardrails for LLMs', 'LLM Guardrails', 'Computer Science',
     ['anthropic', 'meta', 'allen-ai']),
    ('Constitutional AI & RLAIF', 'Constitutional AI', 'Computer Science',
     ['anthropic', 'allen-ai', 'stanford']),
    ('Synthetic Data for LLMs', 'Synthetic Data', 'Data Science',
     ['together', 'meta', 'allen-ai']),
    ('LLM Memory & Caching Patterns', 'LLM Memory', 'Computer Science',
     ['langchain', 'pinecone', 'redis' if False else 'github']),
    ('Embeddings 2025 (text/code/multimodal)', 'Embeddings', 'Computer Science',
     ['openai', 'cohere', 'voyage' if False else 'together']),
    ('Small Language Models (Phi/Gemma/Mistral)', 'SLMs', 'Computer Science',
     ['microsoft', 'google', 'mistral']),
    ('Mixture of Experts at Scale', 'MoE', 'Computer Science',
     ['mistral', 'meta', 'google']),
    ('Speculative Decoding & Inference Speedups', 'Speculative Decoding', 'Computer Science',
     ['together', 'mistral', 'meta']),
    ('LLM Code Generation (Codex / Code-LLaMA)', 'Code LLMs', 'Computer Science',
     ['github', 'meta', 'openai']),
    ('LLM-Powered Search (Perplexity-style)', 'LLM Search', 'Computer Science',
     ['openai', 'google', 'cohere']),
    ('Building LLM Chatbots that Actually Help', 'LLM Product', 'Business',
     ['anthropic', 'openai', 'workday']),
    ('Reasoning Models (o1-style chain-of-thought)', 'Reasoning Models', 'Computer Science',
     ['openai', 'google', 'anthropic']),
]

R5_AGENTIC_TOPICS = [
    ('Agentic AI Fundamentals', 'Agentic AI', 'Computer Science',
     ['langchain', 'anthropic', 'openai']),
    ('LangGraph for Stateful Agents', 'LangGraph', 'Computer Science',
     ['langchain', 'github', 'deeplearningai']),
    ('CrewAI Multi-Agent Workflows', 'CrewAI', 'Computer Science',
     ['deeplearningai', 'github', 'meta']),
    ('AutoGen Conversational Agents', 'AutoGen', 'Computer Science',
     ['microsoft', 'github', 'allen-ai']),
    ('DSPy for Self-Improving Pipelines', 'DSPy', 'Computer Science',
     ['stanford', 'github', 'allen-ai']),
    ('SmolAgents Production Patterns', 'SmolAgents', 'Computer Science',
     ['deeplearningai', 'github', 'meta']),
    ('Tool-Calling Agents at Scale', 'Tool Agents', 'Computer Science',
     ['anthropic', 'openai', 'langchain']),
    ('Browser-Use Agents & WebVoyager', 'Browser Agents', 'Computer Science',
     ['allen-ai', 'deeplearningai', 'meta']),
    ('Code-Writing Agents (SWE-agent, Devin-style)', 'Code Agents', 'Computer Science',
     ['github', 'meta', 'replit']),
    ('Agent Evaluation & Trajectory Analysis', 'Agent Eval', 'Data Science',
     ['allen-ai', 'stanford', 'deeplearningai']),
    ('Agent Memory Architectures', 'Agent Memory', 'Computer Science',
     ['langchain', 'pinecone', 'github']),
    ('Planning & Reflection in Agents', 'Agent Planning', 'Computer Science',
     ['stanford', 'allen-ai', 'cmu']),
    ('Reinforcement Learning for LLM Agents', 'RL for Agents', 'Computer Science',
     ['deepmind' if False else 'google', 'meta', 'openai']),
    ('Multi-Agent Reinforcement Learning', 'MARL', 'Computer Science',
     ['cmu', 'mit', 'meta']),
    ('Voice Agents (Real-Time Speech-to-Speech)', 'Voice Agents', 'Computer Science',
     ['openai', 'google', 'meta']),
    ('GUI Agents — Mobile / Desktop / Web', 'GUI Agents', 'Computer Science',
     ['allen-ai', 'meta', 'google']),
    ('Anthropic Computer-Use Agents', 'Computer Use', 'Computer Science',
     ['anthropic', 'github', 'deeplearningai']),
    ('Agentic RAG Patterns', 'Agentic RAG', 'Computer Science',
     ['langchain', 'llamaindex', 'pinecone']),
    ('Agent Safety & Red-Teaming', 'Agent Safety', 'Computer Science',
     ['anthropic', 'allen-ai', 'openai']),
    ('Building Production Agents — End-to-End', 'Production Agents', 'Computer Science',
     ['langchain', 'anthropic', 'openai']),
]

R5_QUANTUM_TOPICS = [
    ('Quantum Computing Foundations 2025', 'Quantum Computing', 'Physical Science and Engineering',
     ['ibm-quantum-r5', 'mit', 'caltech']),
    ('Quantum Circuits with Qiskit', 'Qiskit', 'Computer Science',
     ['ibm-quantum-r5', 'mit', 'cmu']),
    ('Quantum Algorithms (Shor / Grover / VQE)', 'Quantum Algorithms', 'Math and Logic',
     ['mit', 'caltech', 'oxford']),
    ('Quantum Error Correction', 'QEC', 'Physical Science and Engineering',
     ['mit', 'caltech', 'ibm-quantum-r5']),
    ('Variational Quantum Algorithms', 'VQAs', 'Physical Science and Engineering',
     ['ibm-quantum-r5', 'rigetti-r5', 'mit']),
    ('Quantum Machine Learning', 'QML', 'Computer Science',
     ['ibm-quantum-r5', 'mit', 'oxford']),
    ('Quantum Cryptography & QKD', 'Quantum Cryptography', 'Computer Science',
     ['oxford', 'ethz', 'mit']),
    ('Post-Quantum Cryptography', 'Post-Quantum Crypto', 'Computer Science',
     ['nist' if False else 'cmu', 'mit', 'oxford']),
    ('Trapped-Ion Quantum Hardware', 'Trapped Ions', 'Physical Science and Engineering',
     ['ionq-r5', 'quantinuum-r5', 'oxford']),
    ('Superconducting Qubit Hardware', 'Superconducting Qubits', 'Physical Science and Engineering',
     ['ibm-quantum-r5', 'rigetti-r5', 'mit']),
    ('Photonic Quantum Computing', 'Photonic Quantum', 'Physical Science and Engineering',
     ['psiquantum-r5', 'caltech', 'mit']),
    ('Quantum Annealing & Optimisation', 'Quantum Annealing', 'Physical Science and Engineering',
     ['dwave-r5', 'mit', 'cmu']),
    ('Quantum Simulation for Chemistry', 'Quantum Chemistry', 'Physical Science and Engineering',
     ['ibm-quantum-r5', 'broad', 'mit']),
    ('Quantum Networks & Repeaters', 'Quantum Networks', 'Physical Science and Engineering',
     ['mit', 'tudelft', 'oxford']),
    ('Quantum Sensing & Metrology', 'Quantum Sensing', 'Physical Science and Engineering',
     ['mit', 'oxford', 'nist' if False else 'caltech']),
]

R5_ROBOTICS_TOPICS = [
    ('Humanoid Robotics 2025', 'Humanoid Robotics', 'Physical Science and Engineering',
     ['boston-dynamics-r5', 'figure-ai-r5', 'agility-r5']),
    ('Robot Learning from Demonstration', 'Imitation Learning', 'Computer Science',
     ['stanford', 'tri-r5', 'cmu']),
    ('Diffusion Policies for Robotics', 'Diffusion Policy', 'Computer Science',
     ['tri-r5', 'mit', 'stanford']),
    ('Vision-Language-Action Models (RT-2 / OpenVLA)', 'VLA', 'Computer Science',
     ['google', 'meta', 'stanford']),
    ('Mobile Manipulation', 'Mobile Manipulation', 'Physical Science and Engineering',
     ['cmu', 'mit', 'stanford']),
    ('Whole-Body Control for Bipeds', 'Whole-Body Control', 'Physical Science and Engineering',
     ['mit', 'cmu', 'agility-r5']),
    ('Tactile Sensing for Manipulation', 'Tactile Sensing', 'Physical Science and Engineering',
     ['mit', 'cmu', 'tri-r5']),
    ('Soft Robotics 2025', 'Soft Robotics', 'Physical Science and Engineering',
     ['mit', 'cornell', 'eth' if False else 'ethz']),
    ('Drone Swarms & UAV Autonomy', 'UAV Swarms', 'Physical Science and Engineering',
     ['cmu', 'gatech', 'mit']),
    ('Autonomous Vehicles 2025', 'AV', 'Physical Science and Engineering',
     ['cmu', 'stanford', 'bmw' if False else 'mit']),
    ('ROS 2 Production Pipelines', 'ROS 2', 'Information Technology',
     ['cmu', 'github', 'redhat']),
    ('SLAM 2025 (LiDAR + Vision)', 'SLAM', 'Computer Science',
     ['cmu', 'mit', 'stanford']),
    ('Industrial Robotics Programming', 'Industrial Robotics', 'Information Technology',
     ['abb-r5', 'siemens' if False else 'cmu', 'mit']),
    ('Surgical Robotics', 'Surgical Robotics', 'Health',
     ['jhu', 'mit', 'tri-r5']),
    ('Robot Foundation Models', 'Robot Foundation Models', 'Computer Science',
     ['google', 'tri-r5', 'stanford']),
    ('Sim-to-Real for Robotics', 'Sim-to-Real', 'Computer Science',
     ['nvidia', 'mit', 'cmu']),
    ('Reinforcement Learning for Locomotion', 'RL Locomotion', 'Computer Science',
     ['eth' if False else 'ethz', 'mit', 'cmu']),
    ('Robotic Grasping with Foundation Models', 'Grasping', 'Computer Science',
     ['tri-r5', 'google', 'mit']),
    ('Robot Teleoperation & VR Demos', 'Teleoperation', 'Computer Science',
     ['stanford', 'tri-r5', 'meta']),
    ('Safety Standards for Humanoids (ISO 13482)', 'Robot Safety', 'Information Technology',
     ['cmu', 'mit', 'abb-r5']),
]

# Variant shape: (suffix, level, course_type, hours, weeks, mod_weeks,
#                 base_enrolled, base_reviews, recommended_workload)
R5_VARIANTS = [
    ('Foundations',        'Beginner',     'Course',                    12.0,  3.0, 3,  85000,  2400, 4.0),
    ('Hands-On Lab',       'Intermediate', 'Course',                    22.0,  5.5, 4,  62000,  1700, 4.0),
    ('Advanced Topics',    'Advanced',     'Course',                    28.0,  7.0, 5,  41000,  1100, 4.0),
    ('Capstone Project',   'Advanced',     'Course',                    36.0,  9.0, 6,  31000,   900, 4.0),
    ('Specialization',     'Intermediate', 'Specialization',           110.0, 22.0, 5, 130000,  3800, 5.0),
    ('Professional Cert',  'Beginner',     'Professional Certificate', 130.0, 28.0, 5, 165000,  4900, 4.5),
    ('Guided Project',     'Beginner',     'Guided Project',             1.5,  0.25, 1, 18000,   430, 1.5),
]


def _v6_textbook_isbn(slug):
    """Return a deterministic ISBN-13-shaped string keyed on slug."""
    import hashlib
    h = hashlib.sha1(slug.encode('utf-8')).hexdigest()
    # 978 - 1 - 6-digit publisher - 3-digit chapter - 1 check
    pub  = int(h[0:6],  16) % 1000000
    chap = int(h[6:9],  16) % 1000
    chk  = int(h[9:10], 16) % 10
    return f'978-1-{pub:06d}-{chap:03d}-{chk}'


def _v6_preview_url(slug, course_type):
    """Deterministic preview-video URL (CDN-style, no live host)."""
    tag = course_type.lower().replace(' ', '-') if course_type else 'course'
    return f'https://cdn.coursera-mirror.local/preview/{tag}/{slug}.mp4'


def _v6_make_course(*, R5_VARIANT, topic, primary, category, partner_eff,
                    pid, idx, anchor_tag, prefix_slug):
    (variant, level, ctype, hours, weeks, mod_weeks,
     base_enrolled, base_reviews, workload) = R5_VARIANT
    title = f'{topic} — {variant} ({partner_eff.upper()})'
    slug  = _slugify(f'{prefix_slug}-{topic}-{variant}-{partner_eff}-{idx}')
    duration_text = (
        'Less Than 2 Hours' if ctype == 'Guided Project'
        else (f'Approx. {int(hours)} hours' if hours < 60
              else f'{int(weeks)} weeks at {int(workload)} hrs/wk'))
    spec = dict(
        title=title, slug=slug,
        partner_id=pid.get(partner_eff),
        course_type=ctype, level=level,
        category=category,
        subcategory=topic.split(' ')[0] if topic else '',
        duration_text=duration_text,
        duration_weeks=weeks, duration_hours=hours,
        rating=round(4.6 + (idx % 5) * 0.05, 2),
        review_count=base_reviews + (idx % 17) * 60,
        enrolled_count=base_enrolled + (idx % 23) * 850,
        is_free=(idx % 31 == 0),
        has_certificate=True,
        credit_eligible=(ctype == 'Specialization' and idx % 7 == 0),
        instructor=f'{partner_eff.upper()} Senior Instructor',
        instructor_title=f'Senior Instructor, {partner_eff.upper()}',
        description=(
            f'{title}. A 2024-2025 {ctype.lower()} on {primary}. Covers the '
            f'state of the art, hands-on labs running real workloads on '
            f'{partner_eff.upper()} infrastructure, graded weekly assignments '
            f'and a portfolio-grade capstone. Updated for the {anchor_tag} '
            f'wave of releases.'),
        skills=[primary, 'Critical Thinking', 'Problem Solving',
                f'{primary} Evaluation'],
        what_you_learn=[
            f'Master 2024-2025 advances in {primary}',
            f'Run end-to-end {primary} workflows on {partner_eff.upper()} stack',
            f'Evaluate trade-offs in {primary} systems',
            f'Ship a portfolio-grade {primary} artefact',
        ],
        feature_tags=[primary.lower().replace(' ', '-'), variant.lower(),
                      anchor_tag, partner_eff, 'r5-catalog'],
        is_featured=(idx % 41 == 0),
        is_new=True,
        sort_date=(SEED_REF_DATE - timedelta(
            days=2 + (idx % 90))).strftime('%Y-%m-%d'),
        color_class=CATEGORY_COLORS.get(category, 'cat-cs'),
        module_weeks=mod_weeks,
        primary=primary,
        weeks=weeks,
        workload=workload,
        preview_video_url=_v6_preview_url(slug, ctype),
        textbook_isbn=_v6_textbook_isbn(slug),
        estimated_workload_hours_per_week=workload,
    )
    return spec


def seed_v6(db, models):
    """R5 catalog polish — adds ~2200 deterministic 2024-2025 courses across
    GenAI / LLM / Agentic AI / Quantum / Robotics, plus +20 partners.
    Backfills `preview_video_url`, `textbook_isbn`, and
    `estimated_workload_hours_per_week` on every catalog row.
    Idempotent — gated on partner slug `xai-r5`."""
    Partner = models['Partner']
    Course = models['Course']
    CourseModule = models['CourseModule']

    if Partner.query.filter_by(slug='xai-r5').first():
        return  # already seeded

    # 1) Partners ─────────────────────────────────────────────────────────────
    for name, slug, country, ptype, short in NEW_PARTNERS_V6:
        if Partner.query.filter_by(slug=slug).first():
            continue
        db.session.add(Partner(name=name, slug=slug, country=country,
                               partner_type=ptype, short_name=short))
    db.session.commit()

    pid = {p.slug: p.id for p in Partner.query.all()}
    created = 0

    def _add_modules(course_id, course_title, primary, weeks, workload):
        weeks = max(1, int(weeks))
        for w in range(1, weeks + 1):
            if w == 1:
                mt = f'Week {w}: {primary} — 2025 Landscape'
                md = (f'Orientation: today\'s {primary} releases, mental model, '
                      f'baseline workflow.')
            elif w == weeks:
                mt = f'Week {w}: Capstone — Ship a {primary} Artefact'
                md = (f'Capstone: deliver a portfolio-grade {primary} project '
                      f'and present a 5-minute deck.')
            else:
                mt = f'Week {w}: Applied {primary}'
                md = (f'Hands-on lab + graded assignment exercising {primary} '
                      f'on a realistic workload.')
            vts = [
                f'Lesson {w}.1: {mt}',
                f'Lesson {w}.2: Worked example for {primary}',
                f'Lesson {w}.3: Practice drill ({course_title})',
                f'Lesson {w}.4: 2025 trends — what to watch',
                f'Lesson {w}.5: Captions stub (en, es, fr, de, zh, ja, ar, pt, ru, ko, hi)',
            ]
            db.session.add(CourseModule(
                course_id=course_id, week_number=w, title=mt, description=md,
                videos_count=5, readings_count=3, quizzes_count=1,
                video_titles=json.dumps(vts)))

    def _persist(spec):
        c = Course(
            title=spec['title'], slug=spec['slug'],
            partner_id=spec['partner_id'], course_type=spec['course_type'],
            level=spec['level'], category=spec['category'],
            subcategory=spec['subcategory'],
            duration_text=spec['duration_text'],
            duration_weeks=spec['duration_weeks'],
            duration_hours=spec['duration_hours'],
            rating=spec['rating'], review_count=spec['review_count'],
            enrolled_count=spec['enrolled_count'],
            is_free=spec['is_free'], has_certificate=spec['has_certificate'],
            credit_eligible=spec['credit_eligible'],
            instructor=spec['instructor'],
            instructor_title=spec['instructor_title'],
            description=spec['description'],
            skills=json.dumps(spec['skills']),
            what_you_learn=json.dumps(spec['what_you_learn']),
            feature_tags=json.dumps(spec['feature_tags']),
            is_featured=spec['is_featured'], is_new=spec['is_new'],
            sort_date=spec['sort_date'],
            color_class=spec['color_class'],
            testimonials_json='[]',
            preview_video_url=spec['preview_video_url'],
            textbook_isbn=spec['textbook_isbn'],
            estimated_workload_hours_per_week=spec[
                'estimated_workload_hours_per_week'],
        )
        db.session.add(c)
        db.session.flush()
        _add_modules(c.id, c.title, spec['primary'], spec['module_weeks'],
                     spec['workload'])

    # 2) GenAI × partners × variants ──────────────────────────────────────────
    for t_idx, (topic, primary, category, partners) in enumerate(R5_GENAI_TOPICS):
        for p_idx, partner_slug in enumerate(partners):
            partner_eff = partner_slug if pid.get(partner_slug) else 'stanford'
            for v_idx, variant in enumerate(R5_VARIANTS):
                idx = t_idx * 100 + p_idx * 10 + v_idx
                spec = _v6_make_course(
                    R5_VARIANT=variant, topic=topic, primary=primary,
                    category=category, partner_eff=partner_eff, pid=pid,
                    idx=idx, anchor_tag='genai-2025',
                    prefix_slug='r5-genai')
                if Course.query.filter_by(slug=spec['slug']).first():
                    continue
                _persist(spec)
                created += 1
    db.session.commit()

    # 3) LLM × partners × variants ────────────────────────────────────────────
    for t_idx, (topic, primary, category, partners) in enumerate(R5_LLM_TOPICS):
        for p_idx, partner_slug in enumerate(partners):
            partner_eff = partner_slug if pid.get(partner_slug) else 'deeplearningai'
            for v_idx, variant in enumerate(R5_VARIANTS):
                idx = t_idx * 100 + p_idx * 10 + v_idx
                spec = _v6_make_course(
                    R5_VARIANT=variant, topic=topic, primary=primary,
                    category=category, partner_eff=partner_eff, pid=pid,
                    idx=idx, anchor_tag='llm-2025',
                    prefix_slug='r5-llm')
                if Course.query.filter_by(slug=spec['slug']).first():
                    continue
                _persist(spec)
                created += 1
    db.session.commit()

    # 4) Agentic AI × partners × variants ─────────────────────────────────────
    for t_idx, (topic, primary, category, partners) in enumerate(R5_AGENTIC_TOPICS):
        for p_idx, partner_slug in enumerate(partners):
            partner_eff = partner_slug if pid.get(partner_slug) else 'langchain'
            for v_idx, variant in enumerate(R5_VARIANTS):
                idx = t_idx * 100 + p_idx * 10 + v_idx
                spec = _v6_make_course(
                    R5_VARIANT=variant, topic=topic, primary=primary,
                    category=category, partner_eff=partner_eff, pid=pid,
                    idx=idx, anchor_tag='agentic-2025',
                    prefix_slug='r5-agentic')
                if Course.query.filter_by(slug=spec['slug']).first():
                    continue
                _persist(spec)
                created += 1
    db.session.commit()

    # 5) Quantum × partners × variants ────────────────────────────────────────
    for t_idx, (topic, primary, category, partners) in enumerate(R5_QUANTUM_TOPICS):
        for p_idx, partner_slug in enumerate(partners):
            partner_eff = partner_slug if pid.get(partner_slug) else 'mit'
            for v_idx, variant in enumerate(R5_VARIANTS):
                idx = t_idx * 100 + p_idx * 10 + v_idx
                spec = _v6_make_course(
                    R5_VARIANT=variant, topic=topic, primary=primary,
                    category=category, partner_eff=partner_eff, pid=pid,
                    idx=idx, anchor_tag='quantum-2025',
                    prefix_slug='r5-quantum')
                if Course.query.filter_by(slug=spec['slug']).first():
                    continue
                _persist(spec)
                created += 1
    db.session.commit()

    # 6) Robotics × partners × variants ───────────────────────────────────────
    for t_idx, (topic, primary, category, partners) in enumerate(R5_ROBOTICS_TOPICS):
        for p_idx, partner_slug in enumerate(partners):
            partner_eff = partner_slug if pid.get(partner_slug) else 'cmu'
            for v_idx, variant in enumerate(R5_VARIANTS):
                idx = t_idx * 100 + p_idx * 10 + v_idx
                spec = _v6_make_course(
                    R5_VARIANT=variant, topic=topic, primary=primary,
                    category=category, partner_eff=partner_eff, pid=pid,
                    idx=idx, anchor_tag='robotics-2025',
                    prefix_slug='r5-robotics')
                if Course.query.filter_by(slug=spec['slug']).first():
                    continue
                _persist(spec)
                created += 1
    db.session.commit()

    # 7) Backfill R5 columns on every existing course ─────────────────────────
    # Use a single sqlite UPDATE so backfill is bit-deterministic and cheap.
    # preview_video_url + textbook_isbn derive from slug; workload from
    # duration_hours/duration_weeks (fallback 4.0).
    from sqlalchemy import text
    conn = db.engine.connect()
    try:
        # Pre-compute textbook ISBNs in Python (sqlite has no sha1) and
        # apply per-row only where empty. Same for preview_video_url.
        # Pull only the rows that still need a backfill — keeps the write
        # set small on a warm restart.
        rows = conn.execute(text(
            "SELECT id, slug, course_type, duration_hours, duration_weeks "
            "FROM courses "
            "WHERE preview_video_url IS NULL OR preview_video_url = '' "
            "   OR textbook_isbn IS NULL OR textbook_isbn = '' "
            "   OR estimated_workload_hours_per_week IS NULL "
            "   OR estimated_workload_hours_per_week = 0 "
            "ORDER BY id"
        )).fetchall()
        for row in rows:
            cid, slug, ctype, d_hours, d_weeks = row
            preview = _v6_preview_url(slug or f'course-{cid}', ctype or 'course')
            isbn    = _v6_textbook_isbn(slug or f'course-{cid}')
            try:
                workload = round((d_hours or 0) / (d_weeks or 1), 1)
            except ZeroDivisionError:
                workload = 4.0
            if workload <= 0:
                workload = 4.0
            workload = max(1.0, min(20.0, workload))
            conn.execute(text(
                "UPDATE courses "
                "   SET preview_video_url = :p, "
                "       textbook_isbn = :i, "
                "       estimated_workload_hours_per_week = :w "
                " WHERE id = :c"
            ), {'p': preview, 'i': isbn, 'w': workload, 'c': cid})
        conn.commit()
    finally:
        conn.close()

    print(f"  + seed_v6: added {created} courses (R5), "
          f"partners now {Partner.query.count()}, "
          f"total courses={Course.query.count()}")


# ───────────────────────────────────────────────────────────────────────────
# seed_v7 — R6 catalog polish (2026 anchor: Sustainability / BioTech /
# FinTech / Cyber+PostQuantum / SpaceTech). Targets +3,500 deterministic
# courses to bring total over 10,000. Reuses _v6_make_course / R5_VARIANTS
# so byte-id reset stays intact. Idempotent — gated on partner slug
# `r6-2026-anchor`.
# ───────────────────────────────────────────────────────────────────────────

R6_NEW_PARTNERS = [
    # Sustainability / climate (8)
    ('Climate Policy Initiative', 'cpi-r6', 'United States', 'institution', 'CPI'),
    ('Rocky Mountain Institute', 'rmi-r6', 'United States', 'institution', 'RMI'),
    ('International Energy Agency', 'iea-r6', 'France', 'institution', 'IEA'),
    ('Schmidt Futures', 'schmidt-r6', 'United States', 'institution', 'Schmidt Futures'),
    ('Patagonia Provisions Lab', 'patagonia-r6', 'United States', 'company', 'Patagonia Lab'),
    ('Climeworks', 'climeworks-r6', 'Switzerland', 'company', 'Climeworks'),
    ('Stripe Climate', 'stripe-climate-r6', 'United States', 'company', 'Stripe Climate'),
    ('Project Drawdown', 'drawdown-r6', 'United States', 'institution', 'Drawdown'),
    # BioTech / Pharma (6)
    ('Moderna', 'moderna-r6', 'United States', 'company', 'Moderna'),
    ('Genentech', 'genentech-r6', 'United States', 'company', 'Genentech'),
    ('Beam Therapeutics', 'beam-r6', 'United States', 'company', 'Beam Tx'),
    ('Ginkgo Bioworks', 'ginkgo-r6', 'United States', 'company', 'Ginkgo'),
    ('Insitro', 'insitro-r6', 'United States', 'company', 'Insitro'),
    ('Wellcome Sanger Institute', 'sanger-r6', 'United Kingdom', 'institution', 'Sanger'),
    # FinTech / Stablecoin (5)
    ('Circle', 'circle-r6', 'United States', 'company', 'Circle'),
    ('Plaid', 'plaid-r6', 'United States', 'company', 'Plaid'),
    ('Ramp', 'ramp-r6', 'United States', 'company', 'Ramp'),
    ('Mercado Pago', 'mercadopago-r6', 'Argentina', 'company', 'Mercado Pago'),
    ('Wise', 'wise-r6', 'United Kingdom', 'company', 'Wise'),
    # Cyber + PQC (3)
    ('CrowdStrike', 'crowdstrike-r6', 'United States', 'company', 'CrowdStrike'),
    ('Cloudflare Research', 'cloudflare-r6', 'United States', 'company', 'Cloudflare'),
    ('Open Quantum Safe', 'oqs-r6', 'Canada', 'institution', 'OQS'),
    # SpaceTech (4) + sentinel
    ('SpaceX Education', 'spacex-edu-r6', 'United States', 'company', 'SpaceX Edu'),
    ('European Space Agency', 'esa-r6', 'France', 'institution', 'ESA'),
    ('Planet Labs', 'planet-r6', 'United States', 'company', 'Planet'),
    ('Relativity Space', 'relativity-r6', 'United States', 'company', 'Relativity'),
    # Sentinel partner — used to gate seed_v7 idempotency.
    ('R6 2026 Anchor', 'r6-2026-anchor', 'United States', 'institution', 'R6 Anchor'),
]

# (topic, primary_skill, category, [preferred_partner_slugs])
R6_SUSTAINABILITY_TOPICS = [
    ('Net-Zero Strategy for Enterprises 2026', 'Net Zero', 'Business',
     ['cpi-r6', 'rmi-r6', 'mckinsey', 'iea-r6', 'deloitte']),
    ('Corporate Carbon Accounting (Scope 1-3)', 'Carbon Accounting', 'Business',
     ['cpi-r6', 'deloitte', 'sap', 'rmi-r6', 'mckinsey']),
    ('Voluntary Carbon Markets 2026', 'Carbon Markets', 'Business',
     ['stripe-climate-r6', 'cpi-r6', 'rmi-r6', 'drawdown-r6']),
    ('Direct Air Capture Engineering', 'Direct Air Capture', 'Physical Science and Engineering',
     ['climeworks-r6', 'mit', 'cmu', 'iea-r6']),
    ('Green Hydrogen Production', 'Green Hydrogen', 'Physical Science and Engineering',
     ['iea-r6', 'mit', 'ethz', 'rmi-r6', 'cmu']),
    ('Battery Storage Systems for the Grid', 'Battery Storage', 'Physical Science and Engineering',
     ['rmi-r6', 'mit', 'caltech', 'iea-r6']),
    ('Offshore Wind Engineering 2026', 'Offshore Wind', 'Physical Science and Engineering',
     ['iea-r6', 'mit', 'imperial', 'ethz']),
    ('Climate Risk Disclosure (TCFD/CSRD)', 'Climate Disclosure', 'Business',
     ['cpi-r6', 'sap', 'deloitte', 'jpmorgan']),
    ('Circular Economy Design', 'Circular Economy', 'Business',
     ['drawdown-r6', 'patagonia-r6', 'imperial', 'rmi-r6']),
    ('Sustainable Supply Chains', 'Sustainable Supply Chain', 'Business',
     ['sap', 'mckinsey', 'patagonia-r6', 'deloitte']),
    ('Climate Tech VC Diligence', 'Climate Investing', 'Business',
     ['stripe-climate-r6', 'jpmorgan', 'schmidt-r6', 'mckinsey']),
    ('Climate Resilient Infrastructure', 'Climate Resilience', 'Physical Science and Engineering',
     ['cmu', 'mit', 'imperial', 'iea-r6']),
    ('Sustainable Aviation Fuels', 'SAF', 'Physical Science and Engineering',
     ['iea-r6', 'mit', 'imperial', 'rmi-r6']),
    ('Climate Adaptation for Cities', 'Climate Adaptation', 'Social Sciences',
     ['drawdown-r6', 'iea-r6', 'oxford', 'georgetown']),
    ('Climate Justice and Policy', 'Climate Justice', 'Social Sciences',
     ['cpi-r6', 'georgetown', 'oxford', 'drawdown-r6']),
    ('Carbon Removal Portfolio Design', 'Carbon Removal', 'Business',
     ['stripe-climate-r6', 'cpi-r6', 'climeworks-r6']),
    ('Sustainability Reporting with GRI/ESRS', 'Sustainability Reporting', 'Business',
     ['sap', 'deloitte', 'mckinsey', 'cpi-r6']),
    ('Geothermal Energy Engineering', 'Geothermal', 'Physical Science and Engineering',
     ['iea-r6', 'mit', 'caltech', 'cmu']),
    ('Sustainable Materials Science', 'Sustainable Materials', 'Physical Science and Engineering',
     ['mit', 'ethz', 'imperial', 'patagonia-r6']),
    ('AI for Climate Action', 'Climate AI', 'Data Science',
     ['schmidt-r6', 'stanford', 'mit', 'rmi-r6']),
    ('Earth Observation with Satellite Data', 'Earth Observation', 'Data Science',
     ['planet-r6', 'esa-r6', 'schmidt-r6', 'mit']),
    ('Climate Data Engineering', 'Climate Data', 'Data Science',
     ['schmidt-r6', 'cpi-r6', 'planet-r6', 'snowflake']),
    ('Lifecycle Assessment Methods', 'Lifecycle Assessment', 'Physical Science and Engineering',
     ['ethz', 'imperial', 'patagonia-r6', 'mit']),
    ('Building Decarbonisation Retrofits', 'Building Retrofit', 'Physical Science and Engineering',
     ['rmi-r6', 'iea-r6', 'mit', 'ethz']),
]

R6_BIOTECH_TOPICS = [
    ('mRNA Therapeutics 2026', 'mRNA', 'Health',
     ['moderna-r6', 'genentech-r6', 'jhu', 'broad']),
    ('CRISPR 2.0 — Base & Prime Editing', 'Base Editing', 'Health',
     ['beam-r6', 'broad', 'sanger-r6', 'mit']),
    ('Synthetic Biology Engineering', 'Synthetic Biology', 'Health',
     ['ginkgo-r6', 'mit', 'sanger-r6', 'broad']),
    ('GLP-1 Drug Development', 'GLP-1', 'Health',
     ['moderna-r6', 'genentech-r6', 'jhu']),
    ('Antibody Drug Conjugates', 'ADCs', 'Health',
     ['genentech-r6', 'beam-r6', 'jhu', 'broad']),
    ('Computational Drug Discovery 2026', 'Computational Drugs', 'Health',
     ['insitro-r6', 'broad', 'genentech-r6', 'jhu']),
    ('AlphaFold-Powered Structural Biology', 'AlphaFold', 'Health',
     ['google', 'broad', 'sanger-r6', 'mit']),
    ('Cell & Gene Therapy Manufacturing', 'Cell Therapy', 'Health',
     ['genentech-r6', 'beam-r6', 'sanger-r6']),
    ('Bioprocess Engineering at Scale', 'Bioprocess', 'Physical Science and Engineering',
     ['ginkgo-r6', 'genentech-r6', 'mit', 'imperial']),
    ('Genomic Data Pipelines', 'Genomic Pipelines', 'Data Science',
     ['sanger-r6', 'broad', 'insitro-r6', 'jhu']),
    ('Long-Read Sequencing Workflows', 'Long-Read Seq', 'Health',
     ['sanger-r6', 'broad', 'insitro-r6']),
    ('Spatial Transcriptomics', 'Spatial Transcriptomics', 'Health',
     ['sanger-r6', 'broad', 'jhu', 'insitro-r6']),
    ('Single-Cell Analysis 2026', 'Single-Cell', 'Health',
     ['sanger-r6', 'broad', 'insitro-r6', 'jhu']),
    ('Xenotransplantation Frontiers', 'Xenotransplant', 'Health',
     ['jhu', 'genentech-r6', 'broad']),
    ('Personalized Cancer Vaccines', 'Cancer Vaccines', 'Health',
     ['moderna-r6', 'genentech-r6', 'jhu', 'broad']),
    ('Lab Automation with Opentrons', 'Lab Automation', 'Health',
     ['ginkgo-r6', 'insitro-r6', 'broad', 'sanger-r6']),
    ('Microbiome Engineering', 'Microbiome', 'Health',
     ['ginkgo-r6', 'broad', 'sanger-r6', 'jhu']),
    ('Wearable Biosensor Design', 'Biosensors', 'Physical Science and Engineering',
     ['mit', 'cmu', 'imperial', 'jhu']),
    ('Foundation Models for Biology', 'Bio Foundation Models', 'Computer Science',
     ['insitro-r6', 'google', 'broad', 'sanger-r6']),
    ('Clinical Genomics for Physicians', 'Clinical Genomics', 'Health',
     ['jhu', 'broad', 'sanger-r6', 'genentech-r6']),
    ('Regulatory Affairs for Cell Therapy', 'Regulatory Affairs', 'Health',
     ['genentech-r6', 'jhu', 'mckinsey']),
    ('Biomanufacturing Quality Assurance', 'Biomfg QA', 'Health',
     ['genentech-r6', 'moderna-r6', 'ginkgo-r6']),
    ('Precision Oncology Trial Design', 'Precision Oncology', 'Health',
     ['jhu', 'broad', 'genentech-r6', 'moderna-r6']),
    ('Aging Biology and Geroscience', 'Geroscience', 'Health',
     ['jhu', 'broad', 'sanger-r6', 'insitro-r6']),
]

R6_FINTECH_TOPICS = [
    ('Stablecoin Infrastructure 2026', 'Stablecoin', 'Business',
     ['circle-r6', 'plaid-r6', 'jpmorgan', 'stripe']),
    ('CBDC Architecture & Pilots', 'CBDC', 'Business',
     ['jpmorgan', 'worldbank', 'circle-r6', 'iea-r6']),
    ('Real-World Asset Tokenization', 'RWA Tokenization', 'Business',
     ['jpmorgan', 'circle-r6', 'mckinsey', 'plaid-r6']),
    ('Open Banking with FAPI 2.0', 'Open Banking', 'Information Technology',
     ['plaid-r6', 'wise-r6', 'cloudflare-r6', 'jpmorgan']),
    ('Embedded Finance Patterns', 'Embedded Finance', 'Business',
     ['plaid-r6', 'ramp-r6', 'stripe', 'mercadopago-r6']),
    ('Cross-Border Payments 2026', 'Cross-Border Payments', 'Business',
     ['wise-r6', 'circle-r6', 'mercadopago-r6', 'jpmorgan']),
    ('Buy Now Pay Later Risk Modeling', 'BNPL Risk', 'Business',
     ['ramp-r6', 'plaid-r6', 'jpmorgan']),
    ('FinTech Compliance Engineering', 'FinTech Compliance', 'Business',
     ['plaid-r6', 'ramp-r6', 'jpmorgan', 'deloitte']),
    ('AML Transaction Monitoring with ML', 'AML', 'Business',
     ['jpmorgan', 'plaid-r6', 'deloitte', 'mckinsey']),
    ('Fraud Detection at Scale', 'Fraud Detection', 'Data Science',
     ['stripe', 'plaid-r6', 'jpmorgan', 'cloudflare-r6']),
    ('Corporate Card Programs', 'Corporate Cards', 'Business',
     ['ramp-r6', 'plaid-r6', 'stripe']),
    ('Treasury Automation with Stablecoins', 'Treasury Automation', 'Business',
     ['circle-r6', 'ramp-r6', 'wise-r6']),
    ('Latin America FinTech 2026', 'LATAM FinTech', 'Business',
     ['mercadopago-r6', 'wise-r6', 'jpmorgan']),
    ('DeFi Lending Protocol Design', 'DeFi Lending', 'Business',
     ['circle-r6', 'mit', 'jpmorgan']),
    ('On-Chain Identity & Proof of Personhood', 'On-Chain Identity', 'Information Technology',
     ['circle-r6', 'cloudflare-r6', 'github']),
    ('Crypto Custody for Institutions', 'Crypto Custody', 'Business',
     ['circle-r6', 'jpmorgan', 'deloitte']),
    ('Tax Reporting for Digital Assets', 'Crypto Tax', 'Business',
     ['ramp-r6', 'deloitte', 'jpmorgan']),
    ('Risk-Weighted Capital with Basel IV', 'Basel IV', 'Business',
     ['jpmorgan', 'deloitte', 'mckinsey']),
    ('FinTech Product Management 2026', 'FinTech PM', 'Business',
     ['ramp-r6', 'plaid-r6', 'stripe', 'wise-r6']),
    ('Robo-Advisory Platforms', 'Robo-Advisory', 'Business',
     ['plaid-r6', 'jpmorgan', 'wise-r6']),
    ('ISO 20022 Migration', 'ISO 20022', 'Information Technology',
     ['jpmorgan', 'wise-r6', 'plaid-r6']),
    ('Payment Orchestration Layers', 'Payment Orchestration', 'Information Technology',
     ['stripe', 'plaid-r6', 'ramp-r6']),
    ('Real-Time Payments (FedNow / RTP)', 'Real-Time Payments', 'Business',
     ['jpmorgan', 'plaid-r6', 'wise-r6']),
    ('FinTech Cybersecurity Foundations', 'FinTech Security', 'Information Technology',
     ['crowdstrike-r6', 'cloudflare-r6', 'plaid-r6']),
]

R6_CYBER_TOPICS = [
    ('Post-Quantum Cryptography Migration', 'PQC Migration', 'Information Technology',
     ['oqs-r6', 'cloudflare-r6', 'cmu', 'mit']),
    ('CRYSTALS-Kyber and Dilithium Deployment', 'Kyber & Dilithium', 'Information Technology',
     ['oqs-r6', 'cloudflare-r6', 'ibm-quantum-r5', 'mit']),
    ('Quantum-Safe TLS at Scale', 'Quantum-Safe TLS', 'Information Technology',
     ['cloudflare-r6', 'oqs-r6', 'github']),
    ('Zero Trust Architecture 2026', 'Zero Trust', 'Information Technology',
     ['crowdstrike-r6', 'cloudflare-r6', 'cisco']),
    ('Endpoint Detection and Response', 'EDR', 'Information Technology',
     ['crowdstrike-r6', 'cisco', 'cloudflare-r6']),
    ('Cloud Security Posture Management', 'CSPM', 'Information Technology',
     ['cloudflare-r6', 'crowdstrike-r6', 'aws']),
    ('Supply Chain Security with SLSA', 'Supply Chain Security', 'Information Technology',
     ['github', 'cloudflare-r6', 'redhat']),
    ('SBOM and CycloneDX in Production', 'SBOM', 'Information Technology',
     ['github', 'redhat', 'cloudflare-r6']),
    ('LLM Application Security (OWASP LLM Top 10)', 'LLM Security', 'Information Technology',
     ['anthropic', 'cloudflare-r6', 'crowdstrike-r6']),
    ('Threat Intelligence with MITRE ATT&CK', 'Threat Intel', 'Information Technology',
     ['crowdstrike-r6', 'cisco', 'cloudflare-r6']),
    ('Identity Threat Detection & Response', 'ITDR', 'Information Technology',
     ['crowdstrike-r6', 'cisco', 'cloudflare-r6']),
    ('SOC 2026 Engineering', 'SOC Engineering', 'Information Technology',
     ['crowdstrike-r6', 'cloudflare-r6', 'datadog']),
    ('Hardware Security with TPM 2.0', 'Hardware Security', 'Information Technology',
     ['intel', 'cisco', 'cmu']),
    ('Cryptographic Agility Patterns', 'Crypto Agility', 'Information Technology',
     ['oqs-r6', 'cloudflare-r6', 'cmu']),
    ('Quantum Key Distribution Networks', 'QKD', 'Information Technology',
     ['oqs-r6', 'ibm-quantum-r5', 'mit']),
    ('Privacy-Preserving ML (DP, MPC, FHE)', 'Privacy ML', 'Data Science',
     ['cloudflare-r6', 'mit', 'cmu']),
    ('Confidential Computing with TEEs', 'Confidential Computing', 'Information Technology',
     ['intel', 'cloudflare-r6', 'aws']),
    ('Mobile App Security 2026', 'Mobile Security', 'Information Technology',
     ['apple', 'cloudflare-r6', 'crowdstrike-r6']),
    ('OT and ICS Cybersecurity', 'OT Security', 'Information Technology',
     ['crowdstrike-r6', 'cisco', 'cmu']),
    ('Cyber Incident Response Playbooks', 'Incident Response', 'Information Technology',
     ['crowdstrike-r6', 'cisco', 'cloudflare-r6']),
    ('GenAI for Defenders', 'GenAI Defense', 'Information Technology',
     ['crowdstrike-r6', 'cloudflare-r6', 'anthropic']),
    ('Adversarial Machine Learning', 'Adversarial ML', 'Computer Science',
     ['allen-ai', 'mit', 'cmu', 'anthropic']),
    ('Cybersecurity for Critical Infrastructure', 'Critical Infrastructure', 'Information Technology',
     ['crowdstrike-r6', 'cisco', 'iea-r6']),
    ('Privacy Engineering with PETs', 'Privacy Engineering', 'Information Technology',
     ['cloudflare-r6', 'apple', 'mit']),
]

R6_SPACETECH_TOPICS = [
    ('Smallsat Mission Engineering', 'Smallsat', 'Physical Science and Engineering',
     ['esa-r6', 'planet-r6', 'mit', 'cmu']),
    ('Orbital Mechanics 2026', 'Orbital Mechanics', 'Physical Science and Engineering',
     ['esa-r6', 'mit', 'caltech', 'nasa']),
    ('Liquid Rocket Propulsion', 'Liquid Propulsion', 'Physical Science and Engineering',
     ['relativity-r6', 'spacex-edu-r6', 'mit', 'caltech']),
    ('Additive Manufacturing for Aerospace', 'Aerospace AM', 'Physical Science and Engineering',
     ['relativity-r6', 'mit', 'gatech', 'esa-r6']),
    ('Satellite Communications 2026', 'SatCom', 'Information Technology',
     ['esa-r6', 'planet-r6', 'cisco', 'caltech']),
    ('Earth Observation Image Pipelines', 'EO Pipelines', 'Data Science',
     ['planet-r6', 'esa-r6', 'schmidt-r6', 'nasa']),
    ('Space Sustainability and Debris', 'Space Debris', 'Physical Science and Engineering',
     ['esa-r6', 'nasa', 'mit', 'planet-r6']),
    ('Lunar Surface Operations', 'Lunar Ops', 'Physical Science and Engineering',
     ['nasa', 'esa-r6', 'mit', 'caltech']),
    ('In-Space Manufacturing 2026', 'In-Space Manufacturing', 'Physical Science and Engineering',
     ['nasa', 'mit', 'caltech', 'relativity-r6']),
    ('Astrodynamics for Smallsats', 'Astrodynamics', 'Physical Science and Engineering',
     ['esa-r6', 'caltech', 'mit', 'planet-r6']),
    ('Mission Operations Software', 'Mission Ops Software', 'Information Technology',
     ['esa-r6', 'nasa', 'planet-r6', 'github']),
    ('Space Radiation Hardening', 'Radiation Hardening', 'Physical Science and Engineering',
     ['nasa', 'esa-r6', 'caltech', 'mit']),
    ('Spacecraft Attitude Control', 'Attitude Control', 'Physical Science and Engineering',
     ['esa-r6', 'caltech', 'mit', 'cmu']),
    ('Solar Sail Propulsion', 'Solar Sail', 'Physical Science and Engineering',
     ['esa-r6', 'caltech', 'nasa', 'mit']),
    ('Quantum Communication from Space', 'Space Quantum Comms', 'Physical Science and Engineering',
     ['ibm-quantum-r5', 'esa-r6', 'mit', 'caltech']),
    ('Mars Mission Architecture', 'Mars Missions', 'Physical Science and Engineering',
     ['nasa', 'esa-r6', 'mit', 'spacex-edu-r6']),
    ('Asteroid Mining Foundations', 'Asteroid Mining', 'Physical Science and Engineering',
     ['nasa', 'caltech', 'mit', 'planet-r6']),
    ('Space Law and Policy 2026', 'Space Law', 'Social Sciences',
     ['georgetown', 'oxford', 'esa-r6', 'nasa']),
    ('Constellation Operations at Scale', 'Constellation Ops', 'Information Technology',
     ['planet-r6', 'esa-r6', 'nasa', 'cloudflare-r6']),
    ('GNC for Lunar Landers', 'GNC', 'Physical Science and Engineering',
     ['nasa', 'esa-r6', 'mit', 'cmu']),
    ('Space Weather and Forecasting', 'Space Weather', 'Physical Science and Engineering',
     ['nasa', 'esa-r6', 'caltech', 'planet-r6']),
    ('Cryogenic Propellant Storage', 'Cryogenic Propellants', 'Physical Science and Engineering',
     ['nasa', 'relativity-r6', 'caltech', 'mit']),
    ('Optical Inter-Satellite Links', 'OISL', 'Information Technology',
     ['esa-r6', 'planet-r6', 'caltech', 'cisco']),
    ('Spacecraft Cyber Defense', 'Space Cybersecurity', 'Information Technology',
     ['esa-r6', 'crowdstrike-r6', 'cloudflare-r6', 'nasa']),
]

# Sixth cluster — EdgeAI / On-Device Models 2026. Compact (15 topics) so the
# total catalog ticks safely over 10,000 with margin.
R6_EDGEAI_TOPICS = [
    ('On-Device LLMs with Apple Foundation Models', 'On-Device LLMs', 'Computer Science',
     ['apple', 'deeplearningai', 'meta', 'github']),
    ('TinyML for Microcontrollers 2026', 'TinyML', 'Computer Science',
     ['cmu', 'mit', 'github', 'cloudflare-r6']),
    ('Edge Inference with TensorRT-LLM', 'Edge Inference', 'Information Technology',
     ['nvidia', 'meta', 'together']),
    ('Quantisation-Aware Training', 'Quantisation', 'Computer Science',
     ['meta', 'mistral', 'together', 'deeplearningai']),
    ('Mobile NPU Programming (Apple ANE / Qualcomm)', 'Mobile NPU', 'Computer Science',
     ['apple', 'cmu', 'nvidia']),
    ('Federated Learning at the Edge', 'Federated Learning', 'Computer Science',
     ['google', 'apple', 'mit', 'cmu']),
    ('Streaming Speech Models for Wearables', 'Wearable Speech', 'Computer Science',
     ['apple', 'meta', 'google']),
    ('On-Device Recommender Systems', 'On-Device Recsys', 'Data Science',
     ['apple', 'meta', 'google']),
    ('LLM Routing — Cloud vs Edge', 'LLM Routing', 'Information Technology',
     ['cloudflare-r6', 'together', 'github']),
    ('Edge GenAI for Cameras', 'Edge GenAI', 'Computer Science',
     ['nvidia', 'apple', 'meta']),
    ('Battery-Aware Model Scheduling', 'Battery-Aware ML', 'Computer Science',
     ['apple', 'cmu', 'mit']),
    ('Memory-Mapped Model Loading', 'mmap Models', 'Information Technology',
     ['together', 'github', 'cloudflare-r6']),
    ('Edge Vector Databases', 'Edge Vector DBs', 'Computer Science',
     ['pinecone', 'weaviate', 'cloudflare-r6']),
    ('Embedded Vision for Drones', 'Embedded Vision', 'Computer Science',
     ['nvidia', 'cmu', 'mit', 'esa-r6']),
    ('Privacy-First On-Device Personalisation', 'On-Device Privacy', 'Computer Science',
     ['apple', 'cloudflare-r6', 'cmu']),
]

# Use the same 7 variants from R5 — keeps make_course signature unchanged.
# (suffix, level, course_type, hours, weeks, mod_weeks,
#  base_enrolled, base_reviews, recommended_workload)
R6_VARIANTS = R5_VARIANTS


def seed_v7(db, models):
    """R6 catalog polish — adds ~3500 deterministic 2026 courses across
    Sustainability / BioTech / FinTech / Cyber+PQC / SpaceTech, plus +27
    fresh partners. Backfills R5 columns on any new rows. Idempotent —
    gated on partner slug `r6-2026-anchor`."""
    Partner = models['Partner']
    Course = models['Course']
    CourseModule = models['CourseModule']

    if Partner.query.filter_by(slug='r6-2026-anchor').first():
        return  # already seeded

    # 1) Partners ─────────────────────────────────────────────────────────────
    for name, slug, country, ptype, short in R6_NEW_PARTNERS:
        if Partner.query.filter_by(slug=slug).first():
            continue
        db.session.add(Partner(name=name, slug=slug, country=country,
                               partner_type=ptype, short_name=short))
    db.session.commit()

    pid = {p.slug: p.id for p in Partner.query.all()}
    created = 0

    def _add_modules(course_id, course_title, primary, weeks, workload):
        weeks = max(1, int(weeks))
        for w in range(1, weeks + 1):
            if w == 1:
                mt = f'Week {w}: {primary} — 2026 Landscape'
                md = (f'Orientation: today\'s {primary} releases, mental model, '
                      f'baseline workflow.')
            elif w == weeks:
                mt = f'Week {w}: Capstone — Ship a {primary} Artefact'
                md = (f'Capstone: deliver a portfolio-grade {primary} project '
                      f'and present a 5-minute deck.')
            else:
                mt = f'Week {w}: Applied {primary}'
                md = (f'Hands-on lab + graded assignment exercising {primary} '
                      f'on a realistic workload.')
            vts = [
                f'Lesson {w}.1: {mt}',
                f'Lesson {w}.2: Worked example for {primary}',
                f'Lesson {w}.3: Practice drill ({course_title})',
                f'Lesson {w}.4: 2026 trends — what to watch',
                f'Lesson {w}.5: Captions stub (en, es, fr, de, zh, ja, ar, pt, ru, ko, hi)',
            ]
            db.session.add(CourseModule(
                course_id=course_id, week_number=w, title=mt, description=md,
                videos_count=5, readings_count=3, quizzes_count=1,
                video_titles=json.dumps(vts)))

    def _persist(spec):
        c = Course(
            title=spec['title'], slug=spec['slug'],
            partner_id=spec['partner_id'], course_type=spec['course_type'],
            level=spec['level'], category=spec['category'],
            subcategory=spec['subcategory'],
            duration_text=spec['duration_text'],
            duration_weeks=spec['duration_weeks'],
            duration_hours=spec['duration_hours'],
            rating=spec['rating'], review_count=spec['review_count'],
            enrolled_count=spec['enrolled_count'],
            is_free=spec['is_free'], has_certificate=spec['has_certificate'],
            credit_eligible=spec['credit_eligible'],
            instructor=spec['instructor'],
            instructor_title=spec['instructor_title'],
            description=spec['description'],
            skills=json.dumps(spec['skills']),
            what_you_learn=json.dumps(spec['what_you_learn']),
            feature_tags=json.dumps(spec['feature_tags']),
            is_featured=spec['is_featured'], is_new=spec['is_new'],
            sort_date=spec['sort_date'],
            color_class=spec['color_class'],
            testimonials_json='[]',
            preview_video_url=spec['preview_video_url'],
            textbook_isbn=spec['textbook_isbn'],
            estimated_workload_hours_per_week=spec[
                'estimated_workload_hours_per_week'],
        )
        db.session.add(c)
        db.session.flush()
        _add_modules(c.id, c.title, spec['primary'], spec['module_weeks'],
                     spec['workload'])

    clusters = [
        ('r6-sustainability', 'sustainability-2026', R6_SUSTAINABILITY_TOPICS, 'cpi-r6'),
        ('r6-biotech',        'biotech-2026',        R6_BIOTECH_TOPICS,        'broad'),
        ('r6-fintech',        'fintech-2026',        R6_FINTECH_TOPICS,        'plaid-r6'),
        ('r6-cyber',          'cyber-2026',          R6_CYBER_TOPICS,          'crowdstrike-r6'),
        ('r6-spacetech',      'spacetech-2026',      R6_SPACETECH_TOPICS,      'nasa'),
        ('r6-edgeai',         'edgeai-2026',         R6_EDGEAI_TOPICS,         'apple'),
    ]
    for prefix, anchor_tag, topics, fallback_partner in clusters:
        for t_idx, (topic, primary, category, partners) in enumerate(topics):
            for p_idx, partner_slug in enumerate(partners):
                partner_eff = partner_slug if pid.get(partner_slug) else fallback_partner
                for v_idx, variant in enumerate(R6_VARIANTS):
                    idx = t_idx * 100 + p_idx * 10 + v_idx
                    spec = _v6_make_course(
                        R5_VARIANT=variant, topic=topic, primary=primary,
                        category=category, partner_eff=partner_eff, pid=pid,
                        idx=idx, anchor_tag=anchor_tag,
                        prefix_slug=prefix)
                    if Course.query.filter_by(slug=spec['slug']).first():
                        continue
                    _persist(spec)
                    created += 1
        db.session.commit()

    # 2) Backfill R5 columns on any rows still missing them (safety net) ───
    from sqlalchemy import text
    conn = db.engine.connect()
    try:
        rows = conn.execute(text(
            "SELECT id, slug, course_type, duration_hours, duration_weeks "
            "FROM courses "
            "WHERE preview_video_url IS NULL OR preview_video_url = '' "
            "   OR textbook_isbn IS NULL OR textbook_isbn = '' "
            "   OR estimated_workload_hours_per_week IS NULL "
            "   OR estimated_workload_hours_per_week = 0 "
            "ORDER BY id"
        )).fetchall()
        for row in rows:
            cid, slug, ctype, d_hours, d_weeks = row
            preview = _v6_preview_url(slug or f'course-{cid}', ctype or 'course')
            isbn    = _v6_textbook_isbn(slug or f'course-{cid}')
            try:
                workload = round((d_hours or 0) / (d_weeks or 1), 1)
            except ZeroDivisionError:
                workload = 4.0
            if workload <= 0:
                workload = 4.0
            workload = max(1.0, min(20.0, workload))
            conn.execute(text(
                "UPDATE courses "
                "   SET preview_video_url = :p, "
                "       textbook_isbn = :i, "
                "       estimated_workload_hours_per_week = :w "
                " WHERE id = :c"
            ), {'p': preview, 'i': isbn, 'w': workload, 'c': cid})
        conn.commit()
    finally:
        conn.close()

    print(f"  + seed_v7: added {created} courses (R6), "
          f"partners now {Partner.query.count()}, "
          f"total courses={Course.query.count()}")


# ─── R7 — 2026 polish (catalog 10k → 13k+) ──────────────────────────────────
# 12 new partners + anchor. Mix of AI labs, climate / fusion / biotech orgs,
# localisation specialists — chosen to make hreflang / multilingual / SEO
# tasks land on a realistic publisher.
R7_NEW_PARTNERS = [
    ('OpenAI Education',        'openai-edu-r7',         'United States', 'company',     'OpenAI Edu'),
    ('Anthropic Labs',          'anthropic-labs-r7',     'United States', 'company',     'Anthropic Labs'),
    ('Hugging Face Academy',    'huggingface-r7',        'United States', 'company',     'HF Academy'),
    ('Stability AI',            'stability-r7',          'United Kingdom','company',     'Stability AI'),
    ('Replicate',               'replicate-r7',          'United States', 'company',     'Replicate'),
    ('Vercel Learn',            'vercel-r7',             'United States', 'company',     'Vercel Learn'),
    ('LangChain Academy',       'langchain-r7',          'United States', 'company',     'LangChain'),
    ('LlamaIndex Labs',         'llamaindex-r7',         'United States', 'company',     'LlamaIndex'),
    ('ClimateWorks Foundation', 'climateworks-r7',       'United States', 'institution', 'ClimateWorks'),
    ('Commonwealth Fusion',     'commonwealth-fusion-r7','United States', 'company',     'CFS'),
    ('Ginkgo Bioworks',         'ginkgo-r7',             'United States', 'company',     'Ginkgo'),
    ('Localization Institute',  'loc-institute-r7',      'Switzerland',   'institution', 'Loc Inst'),
    ('R7 2026 Anchor',          'r7-2026-anchor',        'United States', 'institution', 'R7 Anchor'),
]

# 15 broad domains × 6 subtopics × 5 partners × 7 variants = 3150 unique
# 2026 courses. Reuses `_v6_make_course` so every R5/R6 invariant
# (deterministic textbook ISBN, preview URL, workload, ratings) holds.
R7_DOMAINS = [
    # (domain_title, primary_skill, category, [5 partner slugs])
    ('Agentic AI 2026',                  'Agentic AI',               'Computer Science',
     ['openai-edu-r7', 'anthropic-labs-r7', 'huggingface-r7', 'langchain-r7', 'deeplearningai']),
    ('Multimodal RAG Systems',           'Multimodal RAG',           'Computer Science',
     ['huggingface-r7', 'openai-edu-r7', 'llamaindex-r7', 'databricks', 'aws']),
    ('Robotics Foundation Models',       'Robotics FM',              'Computer Science',
     ['deeplearningai', 'cmu', 'mit', 'nvidia', 'google']),
    ('On-Device Generative AI',          'On-Device GenAI',          'Computer Science',
     ['apple', 'huggingface-r7', 'stability-r7', 'meta', 'replicate-r7']),
    ('Climate-Tech Data Platforms',      'ClimateTech',              'Data Science',
     ['climateworks-r7', 'databricks', 'aws', 'google', 'ethz']),
    ('Personalised Health AI',           'Personalised Health AI',   'Health',
     ['jhu', 'ginkgo-r7', 'google', 'mit', 'who']),
    ('Synthetic Biology Workflows',      'SynBio',                   'Health',
     ['ginkgo-r7', 'jhu', 'mit', 'caltech', 'huggingface-r7']),
    ('Quantum Software 2026',            'Quantum Software',         'Physical Science and Engineering',
     ['mit', 'caltech', 'ethz', 'nvidia', 'ibm']),
    ('Fusion Energy Engineering',        'Fusion Engineering',       'Physical Science and Engineering',
     ['commonwealth-fusion-r7', 'mit', 'caltech', 'ethz', 'imperial']),
    ('Space-Resource Economics',         'Space Economics',          'Business',
     ['mit', 'caltech', 'georgetown', 'nasa', 'oxford']),
    ('Web3 Compliance and Policy',       'Web3 Policy',              'Business',
     ['georgetown', 'oxford', 'sciencespo', 'duke', 'hec']),
    ('Cyber-Physical Defence',           'Cyber-Physical',           'Information Technology',
     ['cmu', 'mit', 'cisco', 'nasa', 'crowdstrike-r6']),
    ('Sustainable Aviation Fuels',       'SAF',                      'Physical Science and Engineering',
     ['ethz', 'imperial', 'mit', 'caltech', 'climateworks-r7']),
    ('Conversational UX Design',         'Conversational UX',        'Arts and Humanities',
     ['vercel-r7', 'google', 'meta', 'adobe', 'nyu']),
    ('Localisation Engineering 2026',    'L10n Engineering',         'Computer Science',
     ['loc-institute-r7', 'vercel-r7', 'github', 'meta', 'google']),
]

R7_SUBTOPICS = [
    'Foundations',
    'Applied Pipelines',
    'Evaluation and Benchmarking',
    'Governance and Compliance',
    'Industry Case Studies',
    'Career Transition Pathways',
]


def seed_v8(db, models):
    """R7 catalog polish — adds ~3150 deterministic 2026 courses across
    15 fresh domains × 6 subtopics × 5 partners × 7 variants, plus +12
    partners. Backfills R5 columns on any new rows. Idempotent — gated
    on partner slug `r7-2026-anchor`."""
    Partner = models['Partner']
    Course = models['Course']
    CourseModule = models['CourseModule']

    if Partner.query.filter_by(slug='r7-2026-anchor').first():
        return  # already seeded

    # 1) Partners ─────────────────────────────────────────────────────────────
    for name, slug, country, ptype, short in R7_NEW_PARTNERS:
        if Partner.query.filter_by(slug=slug).first():
            continue
        db.session.add(Partner(name=name, slug=slug, country=country,
                               partner_type=ptype, short_name=short))
    db.session.commit()

    pid = {p.slug: p.id for p in Partner.query.all()}
    created = 0

    def _add_modules(course_id, course_title, primary, weeks, workload):
        weeks = max(1, int(weeks))
        for w in range(1, weeks + 1):
            if w == 1:
                mt = f'Week {w}: {primary} — 2026 Landscape'
                md = (f'Orientation: today\'s {primary} releases, mental model, '
                      f'baseline workflow.')
            elif w == weeks:
                mt = f'Week {w}: Capstone — Ship a {primary} Artefact'
                md = (f'Capstone: deliver a portfolio-grade {primary} project '
                      f'with a 5-minute video walk-through.')
            else:
                mt = f'Week {w}: Applied {primary}'
                md = (f'Hands-on lab + graded assignment exercising {primary} '
                      f'on a realistic 2026 workload.')
            # R7: every video lesson advertises captions in 11 languages,
            # which is what the multilingual-captions tasks check.
            vts = [
                f'Lesson {w}.1: {mt}',
                f'Lesson {w}.2: Worked example for {primary}',
                f'Lesson {w}.3: Practice drill ({course_title})',
                f'Lesson {w}.4: 2026 trends to watch',
                f'Lesson {w}.5: Captions: en, es, zh, ja, ar, fr, de, pt, ko, hi, ru',
            ]
            db.session.add(CourseModule(
                course_id=course_id, week_number=w, title=mt, description=md,
                videos_count=5, readings_count=3, quizzes_count=1,
                video_titles=json.dumps(vts)))

    def _persist(spec):
        c = Course(
            title=spec['title'], slug=spec['slug'],
            partner_id=spec['partner_id'], course_type=spec['course_type'],
            level=spec['level'], category=spec['category'],
            subcategory=spec['subcategory'],
            duration_text=spec['duration_text'],
            duration_weeks=spec['duration_weeks'],
            duration_hours=spec['duration_hours'],
            rating=spec['rating'], review_count=spec['review_count'],
            enrolled_count=spec['enrolled_count'],
            is_free=spec['is_free'], has_certificate=spec['has_certificate'],
            credit_eligible=spec['credit_eligible'],
            instructor=spec['instructor'],
            instructor_title=spec['instructor_title'],
            description=spec['description'],
            skills=json.dumps(spec['skills']),
            what_you_learn=json.dumps(spec['what_you_learn']),
            feature_tags=json.dumps(spec['feature_tags']),
            is_featured=spec['is_featured'], is_new=spec['is_new'],
            sort_date=spec['sort_date'],
            color_class=spec['color_class'],
            testimonials_json='[]',
            preview_video_url=spec['preview_video_url'],
            textbook_isbn=spec['textbook_isbn'],
            estimated_workload_hours_per_week=spec[
                'estimated_workload_hours_per_week'],
        )
        db.session.add(c)
        db.session.flush()
        _add_modules(c.id, c.title, spec['primary'], spec['module_weeks'],
                     spec['workload'])

    for d_idx, (domain, primary, category, partners) in enumerate(R7_DOMAINS):
        for s_idx, subtopic in enumerate(R7_SUBTOPICS):
            topic_title = f'{domain} {subtopic}'
            for p_idx, partner_slug in enumerate(partners):
                partner_eff = (partner_slug if pid.get(partner_slug)
                               else 'r7-2026-anchor')
                for v_idx, variant in enumerate(R5_VARIANTS):
                    idx = (d_idx * 1000 + s_idx * 100
                           + p_idx * 10 + v_idx)
                    spec = _v6_make_course(
                        R5_VARIANT=variant, topic=topic_title,
                        primary=primary, category=category,
                        partner_eff=partner_eff, pid=pid,
                        idx=idx, anchor_tag='r7-2026',
                        prefix_slug='r7-2026')
                    spec['is_new'] = True
                    spec['sort_date'] = (SEED_REF_DATE - timedelta(
                        days=(d_idx * 7 + s_idx + v_idx) % 60
                    )).strftime('%Y-%m-%d')
                    if Course.query.filter_by(slug=spec['slug']).first():
                        continue
                    _persist(spec)
                    created += 1
        db.session.commit()

    # Backfill R5 columns on any rows still missing them (safety net) ──────
    from sqlalchemy import text
    conn = db.engine.connect()
    try:
        rows = conn.execute(text(
            "SELECT id, slug, course_type, duration_hours, duration_weeks "
            "FROM courses "
            "WHERE preview_video_url IS NULL OR preview_video_url = '' "
            "   OR textbook_isbn IS NULL OR textbook_isbn = '' "
            "   OR estimated_workload_hours_per_week IS NULL "
            "   OR estimated_workload_hours_per_week = 0 "
            "ORDER BY id"
        )).fetchall()
        for row in rows:
            cid, slug, ctype, d_hours, d_weeks = row
            preview = _v6_preview_url(slug or f'course-{cid}', ctype or 'course')
            isbn    = _v6_textbook_isbn(slug or f'course-{cid}')
            try:
                workload = round((d_hours or 0) / (d_weeks or 1), 1)
            except ZeroDivisionError:
                workload = 4.0
            if workload <= 0:
                workload = 4.0
            workload = max(1.0, min(20.0, workload))
            conn.execute(text(
                "UPDATE courses "
                "   SET preview_video_url = :p, "
                "       textbook_isbn = :i, "
                "       estimated_workload_hours_per_week = :w "
                " WHERE id = :c"
            ), {'p': preview, 'i': isbn, 'w': workload, 'c': cid})
        conn.commit()
    finally:
        conn.close()

    print(f"  + seed_v8: added {created} courses (R7 2026), "
          f"partners now {Partner.query.count()}, "
          f"total courses={Course.query.count()}")


# ─── R8 — 2026 polish iter 8/10 (K-12 + Lifelong + Professional Development) ──
# Goal: extend catalog beyond 13k by adding three audience segments that the
# real Coursera prioritises in 2026 (K-12 educator track, Lifelong-Learner
# track, Professional-Development track).
# Adds 10 new publisher partners (Khan Academy, College Board, AARP,
# Toastmasters, LinkedIn Learning Pro, Harvard Extension, National Geographic
# Education, PBS LearningMedia, AmeriCorps Senior Corps, Outschool) plus an
# anchor for idempotency. Each audience track ships ~5-6 domains × 6 subtopics
# × 5 partners × 7 variants → 3,360 new courses total.

R8_NEW_PARTNERS = [
    ('Khan Academy',                'khan-academy-r8',     'United States', 'institution', 'Khan Academy'),
    ('The College Board',           'collegeboard-r8',     'United States', 'institution', 'College Board'),
    ('AARP Education',              'aarp-r8',             'United States', 'institution', 'AARP Ed'),
    ('Toastmasters International',  'toastmasters-r8',     'United States', 'institution', 'Toastmasters'),
    ('LinkedIn Learning Pro',       'linkedin-learning-r8','United States', 'company',     'LiL Pro'),
    ('Harvard Extension School',    'harvardx-ext-r8',     'United States', 'university',  'Harvard Ext'),
    ('National Geographic Education','natgeo-ed-r8',       'United States', 'institution', 'NatGeo Edu'),
    ('PBS LearningMedia',           'pbs-learningmedia-r8','United States', 'institution', 'PBS LM'),
    ('AmeriCorps Senior Corps',     'americorps-senior-r8','United States', 'institution', 'AmeriCorps'),
    ('Outschool',                   'outschool-r8',        'United States', 'company',     'Outschool'),
    ('R8 2026 Anchor',              'r8-2026-anchor',      'United States', 'institution', 'R8 Anchor'),
]

R8_DOMAINS = [
    # ── K-12 educator track ────────────────────────────────────────────────
    ('K-12 Early Reading Coaches',     'K-12 Reading',     'Personal Development',
     ['khan-academy-r8', 'collegeboard-r8', 'pbs-learningmedia-r8', 'outschool-r8', 'natgeo-ed-r8']),
    ('Middle School Math Foundations', 'K-12 Math',        'Math and Logic',
     ['khan-academy-r8', 'collegeboard-r8', 'umich', 'outschool-r8', 'gatech']),
    ('AP Computer Science Prep',       'AP CS',            'Computer Science',
     ['collegeboard-r8', 'khan-academy-r8', 'cmu', 'google', 'outschool-r8']),
    ('K-12 Biology Lab Notebooks',     'K-12 Biology',     'Health',
     ['natgeo-ed-r8', 'pbs-learningmedia-r8', 'khan-academy-r8', 'jhu', 'outschool-r8']),
    ('K-12 Career Exploration',        'K-12 Careers',     'Personal Development',
     ['collegeboard-r8', 'aarp-r8', 'pbs-learningmedia-r8', 'linkedin-learning-r8', 'outschool-r8']),
    ('Social-Emotional Learning K-12', 'K-12 SEL',         'Social Sciences',
     ['pbs-learningmedia-r8', 'khan-academy-r8', 'yale', 'outschool-r8', 'natgeo-ed-r8']),
    ('Family STEAM Projects',          'Family STEAM',     'Arts and Humanities',
     ['natgeo-ed-r8', 'pbs-learningmedia-r8', 'outschool-r8', 'khan-academy-r8', 'moma']),
    # ── Lifelong-Learner track ─────────────────────────────────────────────
    ('Encore Career Pathways',         'Encore Careers',   'Personal Development',
     ['aarp-r8', 'americorps-senior-r8', 'linkedin-learning-r8', 'harvardx-ext-r8', 'collegeboard-r8']),
    ('Senior Digital Literacy 2026',   'Digital Literacy', 'Personal Development',
     ['aarp-r8', 'americorps-senior-r8', 'khan-academy-r8', 'google', 'microsoft']),
    ('Hobby Photography Mastery',      'Hobby Photography','Arts and Humanities',
     ['natgeo-ed-r8', 'pbs-learningmedia-r8', 'aarp-r8', 'moma', 'harvardx-ext-r8']),
    ('Mindfulness for Adults 2026',    'Adult Mindfulness','Personal Development',
     ['aarp-r8', 'yale', 'umich', 'harvardx-ext-r8', 'americorps-senior-r8']),
    ('Personal Finance for Retirees',  'Retirement Finance','Business',
     ['aarp-r8', 'umich', 'harvardx-ext-r8', 'linkedin-learning-r8', 'americorps-senior-r8']),
    # ── Professional-Development track ─────────────────────────────────────
    ('Manager Coaching Mastery',       'Manager Coaching', 'Personal Development',
     ['linkedin-learning-r8', 'harvardx-ext-r8', 'umich', 'toastmasters-r8', 'collegeboard-r8']),
    ('Public Speaking 2026',           'Public Speaking',  'Personal Development',
     ['toastmasters-r8', 'linkedin-learning-r8', 'harvardx-ext-r8', 'yale', 'umich']),
    ('Executive Presence 2026',        'Executive Presence','Business',
     ['linkedin-learning-r8', 'harvardx-ext-r8', 'columbia', 'toastmasters-r8', 'wharton']),
    ('Negotiation Mastery 2026',       'Negotiation',      'Business',
     ['harvardx-ext-r8', 'linkedin-learning-r8', 'columbia', 'wharton', 'toastmasters-r8']),
]

R8_SUBTOPICS = [
    'Foundations',
    'Classroom-Ready Activities',
    'Assessment and Outcomes',
    'Inclusion and Accessibility',
    'Family and Community Engagement',
    'Career Pathways',
]


def seed_v9(db, models):
    """R8 catalog polish (iter 8/10) — adds ~3360 deterministic 2026 courses
    across 16 K-12 / lifelong-learning / professional-development domains
    × 6 subtopics × 5 partners × 7 variants, plus +10 partners. Backfills
    R5 columns on any new rows. Idempotent — gated on partner slug
    `r8-2026-anchor`."""
    Partner = models['Partner']
    Course = models['Course']
    CourseModule = models['CourseModule']

    if Partner.query.filter_by(slug='r8-2026-anchor').first():
        return  # already seeded

    # 1) Partners ─────────────────────────────────────────────────────────────
    for name, slug, country, ptype, short in R8_NEW_PARTNERS:
        if Partner.query.filter_by(slug=slug).first():
            continue
        db.session.add(Partner(name=name, slug=slug, country=country,
                               partner_type=ptype, short_name=short))
    db.session.commit()

    pid = {p.slug: p.id for p in Partner.query.all()}
    created = 0

    def _add_modules(course_id, course_title, primary, weeks, workload):
        weeks = max(1, int(weeks))
        for w in range(1, weeks + 1):
            if w == 1:
                mt = f'Week {w}: {primary} — 2026 Audience Landscape'
                md = (f'Orientation: 2026 audience profiles for {primary}, '
                      f'mental model, baseline workflow.')
            elif w == weeks:
                mt = f'Week {w}: Capstone — Deliver a {primary} Programme'
                md = (f'Capstone: deliver a portfolio-grade {primary} '
                      f'programme with a 5-minute reflection.')
            else:
                mt = f'Week {w}: Practitioner {primary}'
                md = (f'Hands-on lab + graded assignment exercising {primary} '
                      f'on a realistic 2026 learner cohort.')
            vts = [
                f'Lesson {w}.1: {mt}',
                f'Lesson {w}.2: Worked example for {primary}',
                f'Lesson {w}.3: Practice drill ({course_title})',
                f'Lesson {w}.4: 2026 audience trends to watch',
                f'Lesson {w}.5: Captions: en, es, zh, ja, ar, fr, de, pt, ko, hi, ru',
            ]
            db.session.add(CourseModule(
                course_id=course_id, week_number=w, title=mt, description=md,
                videos_count=5, readings_count=3, quizzes_count=1,
                video_titles=json.dumps(vts)))

    def _persist(spec):
        c = Course(
            title=spec['title'], slug=spec['slug'],
            partner_id=spec['partner_id'], course_type=spec['course_type'],
            level=spec['level'], category=spec['category'],
            subcategory=spec['subcategory'],
            duration_text=spec['duration_text'],
            duration_weeks=spec['duration_weeks'],
            duration_hours=spec['duration_hours'],
            rating=spec['rating'], review_count=spec['review_count'],
            enrolled_count=spec['enrolled_count'],
            is_free=spec['is_free'], has_certificate=spec['has_certificate'],
            credit_eligible=spec['credit_eligible'],
            instructor=spec['instructor'],
            instructor_title=spec['instructor_title'],
            description=spec['description'],
            skills=json.dumps(spec['skills']),
            what_you_learn=json.dumps(spec['what_you_learn']),
            feature_tags=json.dumps(spec['feature_tags']),
            is_featured=spec['is_featured'], is_new=spec['is_new'],
            sort_date=spec['sort_date'],
            color_class=spec['color_class'],
            testimonials_json='[]',
            preview_video_url=spec['preview_video_url'],
            textbook_isbn=spec['textbook_isbn'],
            estimated_workload_hours_per_week=spec[
                'estimated_workload_hours_per_week'],
        )
        db.session.add(c)
        db.session.flush()
        _add_modules(c.id, c.title, spec['primary'], spec['module_weeks'],
                     spec['workload'])

    for d_idx, (domain, primary, category, partners) in enumerate(R8_DOMAINS):
        for s_idx, subtopic in enumerate(R8_SUBTOPICS):
            topic_title = f'{domain} {subtopic}'
            for p_idx, partner_slug in enumerate(partners):
                partner_eff = (partner_slug if pid.get(partner_slug)
                               else 'r8-2026-anchor')
                for v_idx, variant in enumerate(R5_VARIANTS):
                    idx = (d_idx * 1000 + s_idx * 100
                           + p_idx * 10 + v_idx)
                    spec = _v6_make_course(
                        R5_VARIANT=variant, topic=topic_title,
                        primary=primary, category=category,
                        partner_eff=partner_eff, pid=pid,
                        idx=idx, anchor_tag='r8-2026',
                        prefix_slug='r8-2026')
                    spec['is_new'] = True
                    spec['sort_date'] = (SEED_REF_DATE - timedelta(
                        days=(d_idx * 5 + s_idx * 2 + v_idx) % 75
                    )).strftime('%Y-%m-%d')
                    if Course.query.filter_by(slug=spec['slug']).first():
                        continue
                    _persist(spec)
                    created += 1
        db.session.commit()

    # Backfill R5 columns on any rows still missing them (safety net) ──────
    from sqlalchemy import text
    conn = db.engine.connect()
    try:
        rows = conn.execute(text(
            "SELECT id, slug, course_type, duration_hours, duration_weeks "
            "FROM courses "
            "WHERE preview_video_url IS NULL OR preview_video_url = '' "
            "   OR textbook_isbn IS NULL OR textbook_isbn = '' "
            "   OR estimated_workload_hours_per_week IS NULL "
            "   OR estimated_workload_hours_per_week = 0 "
            "ORDER BY id"
        )).fetchall()
        for row in rows:
            cid, slug, ctype, d_hours, d_weeks = row
            preview = _v6_preview_url(slug or f'course-{cid}', ctype or 'course')
            isbn    = _v6_textbook_isbn(slug or f'course-{cid}')
            try:
                workload = round((d_hours or 0) / (d_weeks or 1), 1)
            except ZeroDivisionError:
                workload = 4.0
            if workload <= 0:
                workload = 4.0
            workload = max(1.0, min(20.0, workload))
            conn.execute(text(
                "UPDATE courses "
                "   SET preview_video_url = :p, "
                "       textbook_isbn = :i, "
                "       estimated_workload_hours_per_week = :w "
                " WHERE id = :c"
            ), {'p': preview, 'i': isbn, 'w': workload, 'c': cid})
        conn.commit()
    finally:
        conn.close()

    print(f"  + seed_v9: added {created} courses (R8 2026 K-12/lifelong/prof-dev), "
          f"partners now {Partner.query.count()}, "
          f"total courses={Course.query.count()}")


# ─── seed_v10 — R9 polish (iter 9/10) ────────────────────────────────────────
# Coursera Hands-On Labs + Career Academies + Industry Certificates.
# 17 R9 domains × 6 R9 subtopics × 5 partners × 7 R5 variants ≈ 3570 courses.
# Gated on partner slug `r9-2026-anchor`. Deterministic + byte-id safe.

R9_NEW_PARTNERS = [
    ('Coursera Labs',               'coursera-labs-r9',    'United States', 'institution', 'Coursera Labs'),
    ('Coursera Career Academy',     'coursera-academy-r9', 'United States', 'institution', 'Career Academy'),
    ('AWS Skill Builder',            'aws-skillbuilder-r9', 'United States', 'company',     'AWS Skill'),
    ('Google Cloud Skills Boost',    'gcp-skillsboost-r9',  'United States', 'company',     'GCP Boost'),
    ('Microsoft Learn Sandbox',      'mslearn-sandbox-r9',  'United States', 'company',     'MS Learn'),
    ('Red Hat OpenShift Academy',    'redhat-openshift-r9', 'United States', 'company',     'OpenShift'),
    ('HashiCorp Learn',              'hashicorp-learn-r9',  'United States', 'company',     'HashiCorp'),
    ('CompTIA Industry Cert',        'comptia-r9',          'United States', 'institution', 'CompTIA'),
    ('PMI Industry Cert',            'pmi-r9',              'United States', 'institution', 'PMI'),
    ('Scrum Alliance Cert',          'scrum-alliance-r9',   'United States', 'institution', 'Scrum'),
    ('R9 2026 Anchor',               'r9-2026-anchor',      'United States', 'institution', 'R9 Anchor'),
]

R9_DOMAINS = [
    # ── Coursera Hands-On Labs track (6 domains) ─────────────────────────
    ('AWS Cloud Labs 2026',          'AWS Cloud Labs',     'Information Technology',
     ['coursera-labs-r9', 'aws-skillbuilder-r9', 'aws', 'google', 'microsoft']),
    ('Kubernetes Labs 2026',         'Kubernetes Labs',    'Information Technology',
     ['coursera-labs-r9', 'redhat-openshift-r9', 'google', 'microsoft', 'aws']),
    ('Cybersecurity Red-Team Labs',  'Red-Team Labs',      'Information Technology',
     ['coursera-labs-r9', 'comptia-r9', 'cisco', 'google', 'microsoft']),
    ('ML Engineer Hands-On Labs',    'ML Engineer Labs',   'Data Science',
     ['coursera-labs-r9', 'nvidia', 'google', 'ibm', 'microsoft']),
    ('Data Engineering Labs 2026',   'Data Eng Labs',      'Data Science',
     ['coursera-labs-r9', 'gcp-skillsboost-r9', 'ibm', 'google', 'microsoft']),
    ('DevOps Pipeline Labs',         'DevOps Labs',        'Information Technology',
     ['coursera-labs-r9', 'hashicorp-learn-r9', 'redhat-openshift-r9', 'aws', 'microsoft']),
    # ── Coursera Career Academy track (6 domains) ────────────────────────
    ('Software Engineer Academy',    'SWE Career Path',    'Computer Science',
     ['coursera-academy-r9', 'meta', 'google', 'ibm', 'microsoft']),
    ('Product Manager Academy',      'PM Career Path',     'Business',
     ['coursera-academy-r9', 'google', 'meta', 'pmi-r9', 'ibm']),
    ('UX Designer Academy',          'UX Career Path',     'Arts and Humanities',
     ['coursera-academy-r9', 'google', 'meta', 'adobe', 'cmu']),
    ('Data Scientist Academy',       'Data Sci Career',    'Data Science',
     ['coursera-academy-r9', 'ibm', 'google', 'microsoft', 'nvidia']),
    ('Cloud Architect Academy',      'Cloud Architect',    'Information Technology',
     ['coursera-academy-r9', 'aws-skillbuilder-r9', 'gcp-skillsboost-r9', 'microsoft', 'redhat-openshift-r9']),
    ('Cybersecurity Analyst Academy','Cyber Analyst Path', 'Information Technology',
     ['coursera-academy-r9', 'comptia-r9', 'cisco', 'google', 'ibm']),
    # ── Industry Certificate track (5 domains) ───────────────────────────
    ('IBM Industry Certificate 2026', 'IBM Industry Cert', 'Computer Science',
     ['ibm', 'coursera-academy-r9', 'comptia-r9', 'cisco', 'oracle']),
    ('Google Industry Certificate 2026', 'Google Industry Cert', 'Computer Science',
     ['google', 'gcp-skillsboost-r9', 'coursera-academy-r9', 'comptia-r9', 'pmi-r9']),
    ('Microsoft Industry Certificate 2026', 'Microsoft Industry Cert', 'Computer Science',
     ['microsoft', 'mslearn-sandbox-r9', 'coursera-academy-r9', 'comptia-r9', 'pmi-r9']),
    ('AWS Industry Certificate 2026', 'AWS Industry Cert', 'Information Technology',
     ['aws', 'aws-skillbuilder-r9', 'coursera-academy-r9', 'comptia-r9', 'hashicorp-learn-r9']),
    ('Meta Industry Certificate 2026', 'Meta Industry Cert', 'Computer Science',
     ['meta', 'coursera-academy-r9', 'scrum-alliance-r9', 'google', 'adobe']),
]

R9_SUBTOPICS = [
    'Foundations',
    'Hands-On Sandbox',
    'Real-World Case Study',
    'Industry-Aligned Project',
    'Certification Exam Prep',
    'Career Outcomes 2026',
]


def seed_v10(db, models):
    """R9 catalog polish (iter 9/10) — adds ~3570 deterministic 2026 courses
    across 17 Hands-On Lab / Career Academy / Industry Certificate domains
    × 6 subtopics × 5 partners × 7 R5 variants, plus +10 publisher partners
    (Coursera Labs, Coursera Career Academy, AWS Skill Builder, GCP Skills
    Boost, MS Learn Sandbox, Red Hat OpenShift Academy, HashiCorp Learn,
    CompTIA, PMI, Scrum Alliance). Backfills R5 columns on any new rows.
    Idempotent — gated on partner slug `r9-2026-anchor`."""
    Partner = models['Partner']
    Course = models['Course']
    CourseModule = models['CourseModule']

    if Partner.query.filter_by(slug='r9-2026-anchor').first():
        return  # already seeded

    # 1) Partners ─────────────────────────────────────────────────────────────
    for name, slug, country, ptype, short in R9_NEW_PARTNERS:
        if Partner.query.filter_by(slug=slug).first():
            continue
        db.session.add(Partner(name=name, slug=slug, country=country,
                               partner_type=ptype, short_name=short))
    db.session.commit()

    pid = {p.slug: p.id for p in Partner.query.all()}
    created = 0

    def _add_modules(course_id, course_title, primary, weeks, workload):
        weeks = max(1, int(weeks))
        for w in range(1, weeks + 1):
            if w == 1:
                mt = f'Week {w}: {primary} — 2026 Lab/Academy Orientation'
                md = (f'Orientation: 2026 industry workflow for {primary}, '
                      f'sandbox tour, target role baseline.')
            elif w == weeks:
                mt = f'Week {w}: Capstone — Industry-Aligned {primary} Project'
                md = (f'Capstone: ship a portfolio-grade {primary} project '
                      f'reviewed against 2026 industry rubric.')
            else:
                mt = f'Week {w}: Sandbox Drill — {primary}'
                md = (f'Hands-on sandbox lab + graded assignment running real '
                      f'{primary} workloads in the 2026 stack.')
            vts = [
                f'Lesson {w}.1: {mt}',
                f'Lesson {w}.2: Worked sandbox demo for {primary}',
                f'Lesson {w}.3: Industry case study ({course_title})',
                f'Lesson {w}.4: 2026 hiring signal to optimise for',
                f'Lesson {w}.5: Captions: en, es, zh, ja, ar, fr, de, pt, ko, hi, ru',
            ]
            db.session.add(CourseModule(
                course_id=course_id, week_number=w, title=mt, description=md,
                videos_count=5, readings_count=3, quizzes_count=1,
                video_titles=json.dumps(vts)))

    def _persist(spec):
        c = Course(
            title=spec['title'], slug=spec['slug'],
            partner_id=spec['partner_id'], course_type=spec['course_type'],
            level=spec['level'], category=spec['category'],
            subcategory=spec['subcategory'],
            duration_text=spec['duration_text'],
            duration_weeks=spec['duration_weeks'],
            duration_hours=spec['duration_hours'],
            rating=spec['rating'], review_count=spec['review_count'],
            enrolled_count=spec['enrolled_count'],
            is_free=spec['is_free'], has_certificate=spec['has_certificate'],
            credit_eligible=spec['credit_eligible'],
            instructor=spec['instructor'],
            instructor_title=spec['instructor_title'],
            description=spec['description'],
            skills=json.dumps(spec['skills']),
            what_you_learn=json.dumps(spec['what_you_learn']),
            feature_tags=json.dumps(spec['feature_tags']),
            is_featured=spec['is_featured'], is_new=spec['is_new'],
            sort_date=spec['sort_date'],
            color_class=spec['color_class'],
            testimonials_json='[]',
            preview_video_url=spec['preview_video_url'],
            textbook_isbn=spec['textbook_isbn'],
            estimated_workload_hours_per_week=spec[
                'estimated_workload_hours_per_week'],
        )
        db.session.add(c)
        db.session.flush()
        _add_modules(c.id, c.title, spec['primary'], spec['module_weeks'],
                     spec['workload'])

    for d_idx, (domain, primary, category, partners) in enumerate(R9_DOMAINS):
        for s_idx, subtopic in enumerate(R9_SUBTOPICS):
            topic_title = f'{domain} {subtopic}'
            for p_idx, partner_slug in enumerate(partners):
                partner_eff = (partner_slug if pid.get(partner_slug)
                               else 'r9-2026-anchor')
                for v_idx, variant in enumerate(R5_VARIANTS):
                    idx = (d_idx * 1000 + s_idx * 100
                           + p_idx * 10 + v_idx)
                    spec = _v6_make_course(
                        R5_VARIANT=variant, topic=topic_title,
                        primary=primary, category=category,
                        partner_eff=partner_eff, pid=pid,
                        idx=idx, anchor_tag='r9-2026',
                        prefix_slug='r9-2026')
                    spec['is_new'] = True
                    spec['sort_date'] = (SEED_REF_DATE - timedelta(
                        days=(d_idx * 5 + s_idx * 2 + v_idx) % 75
                    )).strftime('%Y-%m-%d')
                    # Append R9 track tag so /labs, /career-academy and
                    # /certificate/verify routes can filter cheaply.
                    track_tag = (
                        'r9-hands-on-lab' if d_idx < 6
                        else ('r9-career-academy' if d_idx < 12
                              else 'r9-industry-cert'))
                    base_tags = json.loads(json.dumps(spec['feature_tags']))
                    if track_tag not in base_tags:
                        base_tags.append(track_tag)
                    spec['feature_tags'] = base_tags
                    if Course.query.filter_by(slug=spec['slug']).first():
                        continue
                    _persist(spec)
                    created += 1
        db.session.commit()

    # Backfill R5 columns on any rows still missing them (safety net) ──────
    from sqlalchemy import text
    conn = db.engine.connect()
    try:
        rows = conn.execute(text(
            "SELECT id, slug, course_type, duration_hours, duration_weeks "
            "FROM courses "
            "WHERE preview_video_url IS NULL OR preview_video_url = '' "
            "   OR textbook_isbn IS NULL OR textbook_isbn = '' "
            "   OR estimated_workload_hours_per_week IS NULL "
            "   OR estimated_workload_hours_per_week = 0 "
            "ORDER BY id"
        )).fetchall()
        for row in rows:
            cid, slug, ctype, d_hours, d_weeks = row
            preview = _v6_preview_url(slug or f'course-{cid}', ctype or 'course')
            isbn    = _v6_textbook_isbn(slug or f'course-{cid}')
            try:
                workload = round((d_hours or 0) / (d_weeks or 1), 1)
            except ZeroDivisionError:
                workload = 4.0
            if workload <= 0:
                workload = 4.0
            workload = max(1.0, min(20.0, workload))
            conn.execute(text(
                "UPDATE courses "
                "   SET preview_video_url = :p, "
                "       textbook_isbn = :i, "
                "       estimated_workload_hours_per_week = :w "
                " WHERE id = :c"
            ), {'p': preview, 'i': isbn, 'w': workload, 'c': cid})
        conn.commit()
    finally:
        conn.close()

    print(f"  + seed_v10: added {created} courses (R9 2026 Labs/Academy/Industry-Cert), "
          f"partners now {Partner.query.count()}, "
          f"total courses={Course.query.count()}")
