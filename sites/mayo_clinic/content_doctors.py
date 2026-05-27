"""Mayo Clinic mirror — doctors + healthy-lifestyle articles + news + patient stories."""

# 110 doctor profiles. (name, specialty_label, dept_slug, locations, languages,
# education[], focus_areas[], research_interests[])
# Education uses real Mayo training pathway names.
EDUCATION_OPTIONS = [
    ["MD - Johns Hopkins University School of Medicine", "Residency - Mayo Clinic, Rochester", "Fellowship - Mayo Clinic, Rochester"],
    ["MD - University of Michigan Medical School", "Residency - Massachusetts General Hospital", "Fellowship - Mayo Clinic, Rochester"],
    ["MD - Harvard Medical School", "Residency - Brigham and Women's Hospital", "Fellowship - Mayo Clinic, Jacksonville"],
    ["MD - Mayo Clinic Alix School of Medicine", "Residency - Mayo Clinic, Rochester", "Fellowship - Memorial Sloan Kettering"],
    ["MD - Stanford University School of Medicine", "Residency - UCSF", "Fellowship - Mayo Clinic, Phoenix"],
    ["MD - Duke University School of Medicine", "Residency - Mayo Clinic, Jacksonville", "Fellowship - Cleveland Clinic"],
    ["MD - Northwestern University Feinberg School of Medicine", "Residency - Mayo Clinic, Rochester"],
    ["MD - University of Pennsylvania Perelman School of Medicine", "Residency - Hospital of the University of Pennsylvania", "Fellowship - Mayo Clinic, Rochester"],
    ["MD - Columbia University Vagelos College of Physicians and Surgeons", "Residency - NewYork-Presbyterian", "Fellowship - Mayo Clinic, Phoenix"],
    ["MD - Yale School of Medicine", "Residency - Yale-New Haven Hospital", "Fellowship - Mayo Clinic, Rochester"],
    ["MD, PhD - Washington University in St. Louis", "Residency - Barnes-Jewish Hospital", "Fellowship - Mayo Clinic, Rochester"],
    ["MD - University of California San Francisco", "Residency - UCSF Medical Center", "Fellowship - Mayo Clinic, Jacksonville"],
    ["MD - University of Chicago Pritzker School of Medicine", "Residency - University of Chicago", "Fellowship - Mayo Clinic, Rochester"],
    ["MD - Vanderbilt University School of Medicine", "Residency - Vanderbilt University Medical Center", "Fellowship - Mayo Clinic, Phoenix"],
    ["MD - Baylor College of Medicine", "Residency - MD Anderson Cancer Center", "Fellowship - Mayo Clinic, Rochester"],
    ["MD - University of Washington School of Medicine", "Residency - University of Washington Medical Center", "Fellowship - Mayo Clinic, Rochester"],
    ["MD - Weill Cornell Medical College", "Residency - NewYork-Presbyterian", "Fellowship - Mayo Clinic, Jacksonville"],
    ["MD - University of Pittsburgh School of Medicine", "Residency - UPMC", "Fellowship - Mayo Clinic, Rochester"],
    ["MD - Emory University School of Medicine", "Residency - Emory University Hospital", "Fellowship - Mayo Clinic, Jacksonville"],
    ["MD - Indiana University School of Medicine", "Residency - Mayo Clinic, Rochester", "Fellowship - Mayo Clinic, Rochester"],
    ["MD - University of North Carolina School of Medicine", "Residency - UNC Hospitals", "Fellowship - Mayo Clinic, Jacksonville"],
    ["MD - Albert Einstein College of Medicine", "Residency - Montefiore Medical Center", "Fellowship - Mayo Clinic, Phoenix"],
    ["MD - University of Texas Southwestern Medical Center", "Residency - UT Southwestern Medical Center", "Fellowship - Mayo Clinic, Rochester"],
    ["MD - Case Western Reserve University", "Residency - University Hospitals Cleveland", "Fellowship - Mayo Clinic, Jacksonville"],
    ["MD - University of Iowa Roy J. and Lucille A. Carver College of Medicine", "Residency - Mayo Clinic, Rochester", "Fellowship - Mayo Clinic, Rochester"],
    ["MD - University of Minnesota Medical School", "Residency - Mayo Clinic, Rochester", "Fellowship - Mayo Clinic, Rochester"],
    ["MD - Tulane University School of Medicine", "Residency - Mayo Clinic, Jacksonville", "Fellowship - Mayo Clinic, Phoenix"],
    ["MD - Boston University School of Medicine", "Residency - Boston Medical Center", "Fellowship - Mayo Clinic, Rochester"],
]

LANGUAGE_OPTIONS = ["English", "Spanish", "French", "German", "Mandarin", "Cantonese", "Arabic", "Hindi", "Vietnamese", "Russian", "Portuguese", "Italian", "Korean", "Japanese", "Tagalog", "Polish"]

# Build 110 deterministic profiles.
FIRST = ["Aaron","Adam","Adriana","Akemi","Alan","Alicia","Allison","Amir","Amy","Andrew","Anjali","Anna","Anthony","April","Arjun","Arthur","Aubrey","Ava","Benjamin","Bianca","Bradley","Brandon","Brenda","Brian","Caleb","Camila","Carla","Carlos","Carolina","Catherine","Charles","Chelsea","Chen","Christopher","Claire","Daniel","David","Deepa","Diana","Diego","Dmitri","Donna","Edward","Eleanor","Elena","Eli","Elizabeth","Emma","Erica","Eric","Ethan","Eva","Faith","Fatima","Felipe","Fiona","Frank","Gabriel","George","Gloria","Grace","Hadley","Hannah","Hassan","Heather","Helena","Henry","Hiroshi","Hugo","Ian","Imani","Irene","Isabella","Jacob","Jane","Jasmin","Javier","Jennifer","Jeremy","Joel","John","Jonathan","Joseph","Joshua","Julian","Karen","Kavya","Keiko","Kenneth","Kevin","Kimberly","Laila","Laura","Leah","Leon","Lina","Linda","Lisa","Lucas","Luis","Madeline","Marcus","Maria","Marlon","Martin","Mateo","Megan","Melissa","Michael","Miguel","Nadia","Natalie","Nathaniel"]
LAST = ["Adams","Aguilar","Anderson","Bell","Bennett","Bishop","Brown","Carter","Chen","Choi","Clark","Cohen","Cooper","Daniels","Davis","Diaz","Edwards","Evans","Fernandez","Fisher","Flores","Foster","Garcia","Gomez","Gonzalez","Graham","Green","Hall","Hamilton","Harper","Harris","Hayes","Henderson","Hernandez","Hill","Howard","Hughes","Iqbal","Jackson","James","Jenkins","Johnson","Jones","Kapoor","Kelly","Kennedy","Khan","Kim","King","Lawrence","Lee","Lewis","Long","Lopez","Martinez","Miller","Mitchell","Moore","Morgan","Morris","Murphy","Nakamura","Nelson","Nguyen","O'Brien","Olsen","Park","Patel","Perez","Peterson","Phillips","Powell","Price","Ramirez","Reed","Reyes","Reynolds","Richardson","Rivera","Roberts","Robinson","Rodriguez","Rogers","Rossi","Russell","Ryan","Sanchez","Sato","Schmidt","Scott","Sharma","Singh","Smith","Stewart","Stone","Sullivan","Tanaka","Taylor","Thompson","Torres","Tran","Turner","Vargas","Vasquez","Wagner","Walker","Wang","Washington","Watson","White","Williams","Wilson","Wong","Wood","Wright","Yamamoto","Young","Zhang","Zhou"]

# Department -> specialty title mappings
DEPT_SPECIALTY = {
    "cardiology": ["Cardiologist", "Heart Failure Cardiologist", "Electrophysiologist", "Interventional Cardiologist"],
    "neurology": ["Neurologist", "Epileptologist", "Movement Disorders Neurologist", "Stroke Neurologist", "Headache Neurologist"],
    "neurosurgery": ["Neurosurgeon", "Skull Base Neurosurgeon", "Spine Neurosurgeon"],
    "oncology": ["Medical Oncologist", "Surgical Oncologist", "Hematologist-Oncologist", "Gynecologic Oncologist"],
    "orthopedics": ["Orthopedic Surgeon", "Sports Medicine Surgeon", "Joint Replacement Surgeon", "Hand Surgeon"],
    "gastroenterology": ["Gastroenterologist", "Hepatologist", "Advanced Endoscopist"],
    "endocrinology": ["Endocrinologist", "Diabetes Specialist", "Thyroid Specialist"],
    "pulmonary": ["Pulmonologist", "Critical Care Specialist", "Sleep Medicine Specialist"],
    "nephrology": ["Nephrologist", "Transplant Nephrologist"],
    "urology": ["Urologist", "Urologic Oncologist"],
    "obgyn": ["Obstetrician-Gynecologist", "Maternal-Fetal Medicine Specialist", "Gynecologic Surgeon"],
    "dermatology": ["Dermatologist", "Mohs Surgeon", "Pediatric Dermatologist"],
    "ophthalmology": ["Ophthalmologist", "Retina Specialist", "Glaucoma Specialist"],
    "ent": ["Otolaryngologist", "Head and Neck Surgeon", "Otologist"],
    "psychiatry": ["Psychiatrist", "Child & Adolescent Psychiatrist", "Addiction Psychiatrist"],
    "pediatrics": ["Pediatrician", "Pediatric Cardiologist", "Pediatric Hematologist-Oncologist"],
    "family-medicine": ["Family Medicine Physician"],
    "internal-medicine": ["Internist", "Hospitalist", "Geriatrician"],
    "rheumatology": ["Rheumatologist"],
    "hematology": ["Hematologist", "Bone Marrow Transplant Specialist"],
    "infectious-diseases": ["Infectious Diseases Physician", "Transplant Infectious Diseases Physician", "HIV Specialist"],
    "general-surgery": ["General Surgeon", "Colorectal Surgeon", "Bariatric Surgeon"],
    "bariatric": ["Bariatric Surgeon", "Obesity Medicine Specialist"],
    "transplant": ["Transplant Surgeon", "Transplant Hepatologist"],
    "radiation-oncology": ["Radiation Oncologist"],
    "anesthesiology": ["Anesthesiologist", "Pain Specialist"],
    "emergency-medicine": ["Emergency Medicine Physician"],
    "radiology": ["Radiologist", "Interventional Radiologist", "Neuroradiologist"],
    "pain-medicine": ["Pain Medicine Specialist"],
    "rehabilitation": ["Physiatrist"],
}

# Focus area dictionary by department (each doctor gets 3 random-ish picks)
FOCUS_BY_DEPT = {
    "cardiology": ["Coronary artery disease", "Heart failure", "Atrial fibrillation", "Aortic stenosis", "Hypertrophic cardiomyopathy", "Cardiac amyloidosis", "Cardio-oncology", "Pulmonary hypertension", "Adult congenital heart disease", "Cardiac imaging"],
    "neurology": ["Multiple sclerosis", "Parkinson's disease", "Epilepsy", "Stroke", "Headache and migraine", "Alzheimer's disease", "Sleep disorders", "Neuromuscular disorders", "Movement disorders"],
    "neurosurgery": ["Brain tumor", "Spinal cord tumor", "Awake brain surgery", "Deep brain stimulation", "Cerebrovascular disease", "Complex spine reconstruction"],
    "oncology": ["Breast cancer", "Lung cancer", "Colorectal cancer", "Pancreatic cancer", "Melanoma", "Prostate cancer", "Lymphoma", "Multiple myeloma", "Immunotherapy", "Targeted therapy"],
    "orthopedics": ["Total knee replacement", "Hip arthroplasty", "Sports medicine", "Spine surgery", "Hand and wrist surgery", "Shoulder surgery", "Foot and ankle surgery"],
    "gastroenterology": ["Inflammatory bowel disease", "Liver disease", "Hepatitis C", "Advanced endoscopy", "Esophageal disease", "Pancreatic disease", "GI motility disorders"],
    "endocrinology": ["Type 1 diabetes", "Type 2 diabetes", "Thyroid cancer", "Adrenal disorders", "Pituitary disorders", "Osteoporosis", "Lipid disorders"],
    "pulmonary": ["COPD", "Interstitial lung disease", "Severe asthma", "Sleep apnea", "Lung transplantation", "Pulmonary hypertension", "Cystic fibrosis"],
    "nephrology": ["Chronic kidney disease", "Glomerular disease", "Polycystic kidney disease", "Transplant nephrology", "Kidney stones", "Hypertension"],
    "urology": ["Prostate cancer", "Kidney cancer", "Bladder cancer", "Male infertility", "Urinary incontinence", "Erectile dysfunction", "Stone disease"],
    "obgyn": ["Gynecologic surgery", "Endometriosis", "Fertility", "High-risk pregnancy", "Menopause", "Pelvic floor disorders", "Fibroids"],
    "dermatology": ["Melanoma", "Psoriasis", "Atopic dermatitis", "Mohs surgery", "Hair disorders", "Autoimmune skin disease"],
    "ophthalmology": ["Cataract", "Glaucoma", "Macular degeneration", "Diabetic retinopathy", "Corneal disease", "Pediatric ophthalmology"],
    "ent": ["Head and neck cancer", "Hearing loss", "Voice disorders", "Sinus disease", "Sleep surgery", "Skull base surgery"],
    "psychiatry": ["Depression", "Bipolar disorder", "Anxiety disorders", "Addiction", "ADHD", "Schizophrenia", "Eating disorders", "Transcranial magnetic stimulation"],
    "pediatrics": ["General pediatrics", "Pediatric cardiology", "Pediatric oncology", "Pediatric neurology", "Adolescent medicine"],
    "family-medicine": ["Primary care", "Preventive medicine", "Women's health", "Sports medicine", "Geriatric care"],
    "internal-medicine": ["General internal medicine", "Preventive medicine", "Hospital medicine", "Geriatrics", "Executive health"],
    "rheumatology": ["Rheumatoid arthritis", "Lupus", "Vasculitis", "Gout", "Spondyloarthritis", "Scleroderma"],
    "hematology": ["Leukemia", "Lymphoma", "Multiple myeloma", "Sickle cell disease", "Hemophilia", "Bone marrow transplant"],
    "infectious-diseases": ["HIV care", "Travel medicine", "Antimicrobial stewardship", "Transplant infectious diseases", "Tuberculosis"],
    "general-surgery": ["Robotic surgery", "Colorectal surgery", "Hernia repair", "Foregut surgery", "Endocrine surgery"],
    "bariatric": ["Gastric bypass", "Sleeve gastrectomy", "Medical weight management", "Adolescent bariatrics"],
    "transplant": ["Kidney transplant", "Liver transplant", "Heart transplant", "Lung transplant", "Living donor"],
    "radiation-oncology": ["Proton beam therapy", "Stereotactic radiosurgery", "IMRT", "Brachytherapy", "Pediatric radiation oncology"],
    "anesthesiology": ["Cardiac anesthesia", "Regional anesthesia", "Obstetric anesthesia", "Chronic pain"],
    "emergency-medicine": ["Trauma", "Resuscitation", "Pediatric emergency", "Critical care"],
    "radiology": ["Neuroradiology", "Body imaging", "Breast imaging", "Interventional radiology", "Cardiac imaging"],
    "pain-medicine": ["Chronic pain", "Spine pain", "Cancer pain", "Headache", "Interventional procedures"],
    "rehabilitation": ["Stroke rehabilitation", "Spinal cord injury", "Brain injury", "Sports medicine"],
}

LOCATIONS = ["Rochester", "Jacksonville", "Phoenix"]
