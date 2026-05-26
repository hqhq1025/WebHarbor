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

