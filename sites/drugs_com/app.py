"""Drugs.com mirror — Flask app for the WebHarbor benchmark.

Full mirror with drug catalog, A-Z index, drug detail pages, search,
interaction checker, pill identifier, conditions/classes, news, accounts,
reviews, and a "My Med List" save feature.
"""
import os
import json
import re
import string
from datetime import datetime, timedelta
from itertools import combinations
import difflib

from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify,
    abort, session,
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required,
    current_user,
)
from flask_bcrypt import Bcrypt

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)

app = Flask(__name__, instance_path=os.path.join(BASE_DIR, "instance"))
app.config["SECRET_KEY"] = "drugs_com-dev-secret-please-change"
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + os.path.join(BASE_DIR, "instance", "drugs_com.db")
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


@app.before_request
def auto_login():
    """Always serve as alice — no real auth needed in this benchmark environment."""
    if not current_user.is_authenticated:
        alice = User.query.filter_by(email="alice.j@test.com").first()
        if alice:
            login_user(alice)


def slugify(text):
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviews = db.relationship("DrugReview", backref="user", lazy=True)
    saved_drugs = db.relationship("SavedDrug", backref="user", lazy=True)

    def set_password(self, raw):
        self.password_hash = bcrypt.generate_password_hash(raw).decode("utf-8")

    def check_password(self, raw):
        return bcrypt.check_password_hash(self.password_hash, raw)


class DrugClass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text)
    drugs = db.relationship("Drug", backref="drug_class", lazy=True)


class Drug(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    generic_name = db.Column(db.String(120), unique=True, nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    brand_names_json = db.Column(db.Text, default="[]")
    drug_class_id = db.Column(db.Integer, db.ForeignKey("drug_class.id"))
    availability = db.Column(db.String(40), default="Rx")
    csa_schedule = db.Column(db.String(40), default="Not a controlled drug")
    pregnancy_risk = db.Column(db.String(80), default="Consult your doctor")
    pronunciation = db.Column(db.String(120))
    description = db.Column(db.Text)
    uses = db.Column(db.Text)
    warnings = db.Column(db.Text)
    dosage = db.Column(db.Text)
    side_effects = db.Column(db.Text)
    interactions_text = db.Column(db.Text)
    faq_json = db.Column(db.Text, default="[]")
    avg_rating = db.Column(db.Float, default=0.0)
    review_count = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=False)
    conditions_json = db.Column(db.Text, default="[]")
    related_drugs_json = db.Column(db.Text, default="[]")
    reviewer_name = db.Column(db.String(120), default="Drugs.com editorial team")
    reviewer_credential = db.Column(db.String(120), default="PharmD")
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def brand_names(self):
        try:
            return json.loads(self.brand_names_json or "[]")
        except Exception:
            return []

    @property
    def faq(self):
        try:
            return json.loads(self.faq_json or "[]")
        except Exception:
            return []

    @property
    def conditions_list(self):
        try:
            return json.loads(self.conditions_json or "[]")
        except Exception:
            return []

    @property
    def related_drugs(self):
        try:
            return json.loads(self.related_drugs_json or "[]")
        except Exception:
            return []


class DrugImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    drug_id = db.Column(db.Integer, db.ForeignKey("drug.id"), nullable=False)
    imprint = db.Column(db.String(80))
    shape = db.Column(db.String(40))
    color = db.Column(db.String(40))
    strength = db.Column(db.String(80))
    manufacturer = db.Column(db.String(120))
    drug = db.relationship("Drug", backref="images")


class DrugInteraction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    drug_a_id = db.Column(db.Integer, db.ForeignKey("drug.id"), nullable=False)
    drug_b_id = db.Column(db.Integer, db.ForeignKey("drug.id"), nullable=False)
    severity = db.Column(db.String(20), default="unknown")
    description = db.Column(db.Text)
    drug_a = db.relationship("Drug", foreign_keys=[drug_a_id])
    drug_b = db.relationship("Drug", foreign_keys=[drug_b_id])


class DrugReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    drug_id = db.Column(db.Integer, db.ForeignKey("drug.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200))
    body = db.Column(db.Text)
    condition_treated = db.Column(db.String(120))
    helpful_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    drug = db.relationship("Drug", backref="reviews")


class Condition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text)
    drug_count = db.Column(db.Integer, default=0)


class DrugCondition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    drug_id = db.Column(db.Integer, db.ForeignKey("drug.id"), nullable=False)
    condition_id = db.Column(db.Integer, db.ForeignKey("condition.id"), nullable=False)


class NewsArticle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    body = db.Column(db.Text)
    source = db.Column(db.String(120), default="Drugs.com")
    published_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_featured = db.Column(db.Boolean, default=False)

    @property
    def slug(self):
        s = re.sub(r"[^a-z0-9]+", "-", (self.title or "").lower()).strip("-")
        return s or f"article-{self.id}"


class SavedDrug(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    drug_id = db.Column(db.Integer, db.ForeignKey("drug.id"), nullable=False)
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    drug = db.relationship("Drug")


@login_manager.user_loader
def load_user(uid):
    return User.query.get(int(uid))


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------
DRUG_CLASSES = [
    ("Nonsteroidal anti-inflammatory drugs", "NSAIDs reduce pain, inflammation, and fever by inhibiting cyclooxygenase enzymes."),
    ("Analgesics", "Analgesics relieve pain. They include opioid and non-opioid options."),
    ("Opioids", "Opioids are strong pain relievers that work on opioid receptors in the central nervous system."),
    ("Anticonvulsants", "Anticonvulsants treat seizures and are also used for nerve pain and mood disorders."),
    ("ACE inhibitors", "ACE inhibitors lower blood pressure by blocking the conversion of angiotensin I to angiotensin II."),
    ("Beta blockers", "Beta blockers slow the heart and reduce blood pressure by blocking adrenaline."),
    ("Calcium channel blockers", "Calcium channel blockers relax blood vessels and lower blood pressure."),
    ("Statins", "Statins lower cholesterol by inhibiting HMG-CoA reductase."),
    ("ARBs", "Angiotensin II receptor blockers lower blood pressure by blocking angiotensin II."),
    ("Diuretics", "Diuretics help the body remove excess salt and water through urine."),
    ("Anticoagulants", "Anticoagulants prevent dangerous blood clots."),
    ("Antiplatelet drugs", "Antiplatelet drugs prevent platelets from sticking together."),
    ("Biguanides", "Biguanides reduce glucose production in the liver. Metformin is the most common."),
    ("GLP-1 receptor agonists", "GLP-1 agonists improve blood sugar control and are used for type 2 diabetes and obesity."),
    ("SGLT2 inhibitors", "SGLT2 inhibitors lower blood sugar by causing the kidneys to remove glucose in urine."),
    ("DPP-4 inhibitors", "DPP-4 inhibitors increase insulin release after meals."),
    ("Insulins", "Insulin is a hormone replacement used to control blood glucose in diabetes."),
    ("SSRIs", "Selective serotonin reuptake inhibitors treat depression and anxiety."),
    ("SNRIs", "Serotonin and norepinephrine reuptake inhibitors treat depression, anxiety, and pain."),
    ("Atypical antidepressants", "Atypical antidepressants work via novel mechanisms."),
    ("Benzodiazepines", "Benzodiazepines treat anxiety, seizures, and insomnia."),
    ("Atypical antipsychotics", "Atypical antipsychotics treat schizophrenia, bipolar disorder, and other conditions."),
    ("Mood stabilizers", "Mood stabilizers manage bipolar disorder."),
    ("Tricyclic antidepressants", "TCAs treat depression and certain pain conditions."),
    ("Penicillins", "Penicillins are beta-lactam antibiotics."),
    ("Macrolides", "Macrolide antibiotics treat respiratory and skin infections."),
    ("Fluoroquinolones", "Fluoroquinolones treat a broad range of bacterial infections."),
    ("Tetracyclines", "Tetracyclines treat bacterial infections, acne, and other conditions."),
    ("Cephalosporins", "Cephalosporins are beta-lactam antibiotics related to penicillins."),
    ("Lincosamides", "Lincosamide antibiotics like clindamycin treat anaerobic and gram-positive infections."),
    ("Thyroid hormones", "Thyroid hormone replacements treat hypothyroidism."),
    ("Bronchodilators", "Bronchodilators relax airway muscles, easing breathing."),
    ("Leukotriene modifiers", "Leukotriene modifiers reduce asthma and allergy symptoms."),
    ("Corticosteroids", "Corticosteroids reduce inflammation and suppress the immune system."),
    ("Muscle relaxants", "Muscle relaxants reduce muscle spasms and pain."),
    ("Antiemetics", "Antiemetics prevent and treat nausea and vomiting."),
    ("PDE5 inhibitors", "PDE5 inhibitors treat erectile dysfunction and pulmonary hypertension."),
    ("5-alpha-reductase inhibitors", "5-ARIs treat benign prostatic hyperplasia and male pattern hair loss."),
    ("Alpha blockers", "Alpha blockers relax smooth muscle, helping with BPH and high blood pressure."),
    ("DMARDs", "Disease-modifying antirheumatic drugs slow autoimmune disease progression."),
    ("TNF inhibitors", "TNF inhibitors are biologics that block tumor necrosis factor."),
    ("Triptans", "Triptans treat migraine and cluster headaches."),
    ("Sleep aids", "Sleep aids help with short-term insomnia."),
    ("Opioid antagonists", "Opioid antagonists block opioid receptors; used for overdose reversal."),
    ("Stimulants", "Stimulants treat ADHD and narcolepsy."),
    ("Xanthine oxidase inhibitors", "Xanthine oxidase inhibitors lower uric acid in gout."),
    ("Retinoids", "Retinoids treat severe acne and other skin conditions."),
    ("Antihistamines", "Antihistamines relieve allergy symptoms by blocking histamine."),
    ("Proton pump inhibitors", "PPIs reduce stomach acid production."),
    ("H2 blockers", "H2 blockers reduce stomach acid by blocking histamine H2 receptors."),
    ("Decongestants", "Decongestants relieve nasal congestion."),
    ("Cough suppressants", "Cough suppressants reduce coughing."),
    ("Antimalarials", "Antimalarials treat malaria and certain autoimmune diseases."),
    ("Antimetabolites", "Antimetabolites disrupt cell metabolism; used in cancer and autoimmune diseases."),
    ("Monoclonal antibodies", "Monoclonal antibodies target specific molecules in disease."),
    ("Supplements", "Dietary supplements provide nutrients or substances like melatonin."),
    ("Antivirals", "Antivirals treat viral infections by inhibiting viral replication."),
    ("Antifungals", "Antifungals treat fungal infections."),
    ("Sulfonamides", "Sulfonamide antibiotics inhibit bacterial folate synthesis."),
    ("Nitroimidazoles", "Nitroimidazole antibiotics treat anaerobic bacterial and protozoal infections."),
    ("Immunosuppressants", "Immunosuppressants reduce immune system activity to prevent transplant rejection or treat autoimmune disease."),
    ("Biologics", "Biologic drugs are produced from living cells and target specific immune pathways."),
    ("Cardiac glycosides", "Cardiac glycosides increase cardiac contractility; digoxin is the prototype."),
    ("Nitrates", "Nitrates dilate blood vessels and are used in angina."),
    ("Antiarrhythmics", "Antiarrhythmics treat irregular heart rhythms."),
    ("Inhaled corticosteroids", "Inhaled corticosteroids reduce airway inflammation in asthma and COPD."),
    ("Anticholinergic bronchodilators", "Anticholinergic bronchodilators relax airway smooth muscle in COPD and asthma."),
    ("Nasal corticosteroids", "Nasal corticosteroids reduce nasal inflammation in allergic rhinitis."),
    ("Antidiarrheals", "Antidiarrheals slow intestinal motility and treat diarrhea."),
    ("Laxatives", "Laxatives relieve constipation."),
    ("Prokinetics", "Prokinetics enhance gastrointestinal motility."),
    ("Antacids", "Antacids neutralize stomach acid."),
    ("Anxiolytics", "Anxiolytics relieve anxiety; non-benzodiazepine options include buspirone."),
    ("Bisphosphonates", "Bisphosphonates strengthen bone and treat osteoporosis."),
    ("SERMs", "Selective estrogen receptor modulators act selectively on estrogen receptors."),
    ("Estrogens", "Estrogens are female sex hormones used in hormone therapy and contraception."),
    ("Progestogens", "Progestogens are female sex hormones used in contraception and hormone therapy."),
    ("Androgens", "Androgens are male sex hormones used for hypogonadism."),
    ("Contraceptives", "Contraceptives prevent pregnancy."),
    ("Fertility agents", "Fertility agents stimulate ovulation."),
    ("Prostaglandins", "Prostaglandins are hormone-like substances used in obstetrics and ophthalmology."),
    ("Antithyroid agents", "Antithyroid agents block thyroid hormone synthesis."),
    ("Topical corticosteroids", "Topical corticosteroids reduce skin inflammation."),
    ("Topical antibiotics", "Topical antibiotics treat localized bacterial skin infections."),
    ("Topical retinoids", "Topical retinoids treat acne and photoaging."),
    ("Acne treatments", "Acne treatments include benzoyl peroxide and other topical agents."),
    ("Ophthalmic beta blockers", "Ophthalmic beta blockers lower intraocular pressure in glaucoma."),
    ("Ophthalmic prostaglandins", "Ophthalmic prostaglandin analogues lower intraocular pressure."),
    ("Ophthalmic antibiotics", "Ophthalmic antibiotics treat bacterial eye infections."),
    ("Ophthalmic alpha agonists", "Ophthalmic alpha agonists lower intraocular pressure in glaucoma."),
    ("Hormones", "Hormones regulate physiological processes; includes oxytocin and calcitonin."),
    ("Iron supplements", "Iron supplements treat iron-deficiency anemia."),
    ("Vitamins", "Vitamins treat or prevent vitamin deficiencies."),
    ("ADHD non-stimulants", "Non-stimulant ADHD medications work via norepinephrine modulation."),
    ("Partial opioid agonists", "Partial opioid agonists treat opioid use disorder and pain."),
]


DRUGS_DATA = [
    # (generic_name, class_name, availability, csa, pronunciation, brand_names, conditions)
    ("ibuprofen", "Nonsteroidal anti-inflammatory drugs", "Rx and/or OTC", "Not a controlled drug", "eye-bue-PROE-fen", ["Advil", "Motrin", "Nuprin"], ["pain", "fever", "arthritis", "migraine"]),
    ("naproxen", "Nonsteroidal anti-inflammatory drugs", "Rx and/or OTC", "Not a controlled drug", "na-PROX-en", ["Aleve", "Naprosyn", "Anaprox"], ["pain", "arthritis", "gout"]),
    ("aspirin", "Nonsteroidal anti-inflammatory drugs", "OTC", "Not a controlled drug", "AS-pir-in", ["Bayer", "Bufferin", "Ecotrin"], ["pain", "fever", "heart_disease"]),
    ("meloxicam", "Nonsteroidal anti-inflammatory drugs", "Rx", "Not a controlled drug", "mel-OX-i-kam", ["Mobic", "Vivlodex"], ["arthritis", "pain"]),
    ("celecoxib", "Nonsteroidal anti-inflammatory drugs", "Rx", "Not a controlled drug", "sel-e-KOX-ib", ["Celebrex"], ["arthritis", "pain"]),
    ("acetaminophen", "Analgesics", "OTC", "Not a controlled drug", "a-seet-a-MIN-oh-fen", ["Tylenol", "Panadol"], ["pain", "fever"]),
    ("tramadol", "Opioids", "Rx", "C-IV", "TRAM-a-dol", ["Ultram", "ConZip"], ["pain"]),
    ("oxycodone", "Opioids", "Rx", "C-II", "ox-i-KOE-done", ["OxyContin", "Roxicodone", "Percocet"], ["pain"]),
    ("hydrocodone", "Opioids", "Rx", "C-II", "hye-droe-KOE-done", ["Vicodin", "Norco", "Lortab"], ["pain"]),
    ("gabapentin", "Anticonvulsants", "Rx", "Not a controlled drug", "GA-ba-PEN-tin", ["Neurontin", "Gralise"], ["epilepsy", "pain"]),
    ("pregabalin", "Anticonvulsants", "Rx", "C-V", "pre-GAB-a-lin", ["Lyrica"], ["pain", "epilepsy"]),
    ("lisinopril", "ACE inhibitors", "Rx", "Not a controlled drug", "lyse-IN-oh-pril", ["Zestril", "Prinivil"], ["hypertension", "heart_disease"]),
    ("metoprolol", "Beta blockers", "Rx", "Not a controlled drug", "me-TOE-proe-lol", ["Lopressor", "Toprol XL"], ["hypertension", "heart_disease"]),
    ("amlodipine", "Calcium channel blockers", "Rx", "Not a controlled drug", "am-LOE-di-peen", ["Norvasc"], ["hypertension"]),
    ("atorvastatin", "Statins", "Rx", "Not a controlled drug", "a-TOR-va-sta-tin", ["Lipitor"], ["high_cholesterol", "heart_disease"]),
    ("rosuvastatin", "Statins", "Rx", "Not a controlled drug", "roe-SOO-va-sta-tin", ["Crestor"], ["high_cholesterol"]),
    ("losartan", "ARBs", "Rx", "Not a controlled drug", "loe-SAR-tan", ["Cozaar"], ["hypertension"]),
    ("carvedilol", "Beta blockers", "Rx", "Not a controlled drug", "KAR-ve-dil-ol", ["Coreg"], ["heart_disease", "hypertension"]),
    ("hydrochlorothiazide", "Diuretics", "Rx", "Not a controlled drug", "hye-droe-klor-oh-THYE-a-zide", ["Microzide"], ["hypertension"]),
    ("furosemide", "Diuretics", "Rx", "Not a controlled drug", "fur-OH-se-mide", ["Lasix"], ["heart_disease", "hypertension"]),
    ("warfarin", "Anticoagulants", "Rx", "Not a controlled drug", "WAR-far-in", ["Coumadin", "Jantoven"], ["heart_disease"]),
    ("clopidogrel", "Antiplatelet drugs", "Rx", "Not a controlled drug", "kloh-PID-oh-grel", ["Plavix"], ["heart_disease"]),
    ("spironolactone", "Diuretics", "Rx", "Not a controlled drug", "speer-on-oh-LAK-tone", ["Aldactone"], ["hypertension", "heart_disease"]),
    ("metformin", "Biguanides", "Rx", "Not a controlled drug", "met-FOR-min", ["Glucophage", "Fortamet", "Glumetza"], ["diabetes", "obesity"]),
    ("semaglutide", "GLP-1 receptor agonists", "Rx", "Not a controlled drug", "sem-a-GLOO-tide", ["Ozempic", "Wegovy", "Rybelsus"], ["diabetes", "obesity"]),
    ("tirzepatide", "GLP-1 receptor agonists", "Rx", "Not a controlled drug", "tir-ZEP-a-tide", ["Mounjaro", "Zepbound"], ["diabetes", "obesity"]),
    ("empagliflozin", "SGLT2 inhibitors", "Rx", "Not a controlled drug", "em-pa-gli-FLOE-zin", ["Jardiance"], ["diabetes", "heart_disease"]),
    ("sitagliptin", "DPP-4 inhibitors", "Rx", "Not a controlled drug", "sit-a-GLIP-tin", ["Januvia"], ["diabetes"]),
    ("insulin glargine", "Insulins", "Rx", "Not a controlled drug", "IN-su-lin GLAR-jeen", ["Lantus", "Basaglar", "Toujeo"], ["diabetes"]),
    ("sertraline", "SSRIs", "Rx", "Not a controlled drug", "SER-tra-leen", ["Zoloft"], ["depression", "anxiety"]),
    ("escitalopram", "SSRIs", "Rx", "Not a controlled drug", "es-sye-TAL-oh-pram", ["Lexapro"], ["depression", "anxiety"]),
    ("fluoxetine", "SSRIs", "Rx", "Not a controlled drug", "floo-OX-e-teen", ["Prozac", "Sarafem"], ["depression", "anxiety"]),
    ("duloxetine", "SNRIs", "Rx", "Not a controlled drug", "doo-LOX-e-teen", ["Cymbalta"], ["depression", "pain"]),
    ("bupropion", "Atypical antidepressants", "Rx", "Not a controlled drug", "byoo-PROE-pee-on", ["Wellbutrin", "Zyban"], ["depression"]),
    ("venlafaxine", "SNRIs", "Rx", "Not a controlled drug", "ven-la-FAX-een", ["Effexor"], ["depression", "anxiety"]),
    ("alprazolam", "Benzodiazepines", "Rx", "C-IV", "al-PRAY-zoe-lam", ["Xanax"], ["anxiety"]),
    ("clonazepam", "Benzodiazepines", "Rx", "C-IV", "kloe-NAZ-e-pam", ["Klonopin"], ["anxiety", "epilepsy"]),
    ("lorazepam", "Benzodiazepines", "Rx", "C-IV", "lor-AZ-e-pam", ["Ativan"], ["anxiety"]),
    ("quetiapine", "Atypical antipsychotics", "Rx", "Not a controlled drug", "kwe-TYE-a-peen", ["Seroquel"], ["schizophrenia", "bipolar_disorder"]),
    ("aripiprazole", "Atypical antipsychotics", "Rx", "Not a controlled drug", "ay-ri-PIP-ray-zole", ["Abilify"], ["schizophrenia", "bipolar_disorder", "depression"]),
    ("lithium", "Mood stabilizers", "Rx", "Not a controlled drug", "LITH-ee-um", ["Lithobid", "Eskalith"], ["bipolar_disorder"]),
    ("amitriptyline", "Tricyclic antidepressants", "Rx", "Not a controlled drug", "a-mee-TRIP-ti-leen", ["Elavil"], ["depression", "pain"]),
    ("amoxicillin", "Penicillins", "Rx", "Not a controlled drug", "a-mox-i-SIL-in", ["Amoxil", "Moxatag"], ["bacterial_infections"]),
    ("azithromycin", "Macrolides", "Rx", "Not a controlled drug", "az-ith-roe-MYE-sin", ["Zithromax", "Z-Pak"], ["bacterial_infections"]),
    ("ciprofloxacin", "Fluoroquinolones", "Rx", "Not a controlled drug", "sip-roe-FLOX-a-sin", ["Cipro"], ["bacterial_infections"]),
    ("doxycycline", "Tetracyclines", "Rx", "Not a controlled drug", "dox-i-SYE-kleen", ["Vibramycin", "Doryx"], ["bacterial_infections", "acne"]),
    ("clindamycin", "Lincosamides", "Rx", "Not a controlled drug", "klin-da-MYE-sin", ["Cleocin"], ["bacterial_infections", "acne"]),
    ("cephalexin", "Cephalosporins", "Rx", "Not a controlled drug", "sef-a-LEX-in", ["Keflex"], ["bacterial_infections"]),
    ("levothyroxine", "Thyroid hormones", "Rx", "Not a controlled drug", "lee-voe-thye-ROX-een", ["Synthroid", "Levoxyl"], ["hypothyroidism"]),
    ("albuterol", "Bronchodilators", "Rx", "Not a controlled drug", "al-BUE-ter-ol", ["ProAir", "Ventolin", "Proventil"], ["asthma"]),
    ("montelukast", "Leukotriene modifiers", "Rx", "Not a controlled drug", "mon-te-LOO-kast", ["Singulair"], ["asthma", "allergies"]),
    ("prednisone", "Corticosteroids", "Rx", "Not a controlled drug", "PRED-ni-sone", ["Deltasone", "Rayos"], ["arthritis", "allergies", "lupus"]),
    ("cyclobenzaprine", "Muscle relaxants", "Rx", "Not a controlled drug", "sye-kloe-BEN-za-preen", ["Flexeril", "Amrix"], ["pain"]),
    ("ondansetron", "Antiemetics", "Rx", "Not a controlled drug", "on-DAN-se-tron", ["Zofran"], ["cancer"]),
    ("sildenafil", "PDE5 inhibitors", "Rx", "Not a controlled drug", "sil-DEN-a-fil", ["Viagra", "Revatio"], ["erectile_dysfunction"]),
    ("finasteride", "5-alpha-reductase inhibitors", "Rx", "Not a controlled drug", "fi-NAS-teer-ide", ["Proscar", "Propecia"], ["bph"]),
    ("tamsulosin", "Alpha blockers", "Rx", "Not a controlled drug", "tam-SOO-loe-sin", ["Flomax"], ["bph"]),
    ("hydroxychloroquine", "Antimalarials", "Rx", "Not a controlled drug", "hye-drox-ee-KLOR-oh-kwin", ["Plaquenil"], ["lupus", "arthritis"]),
    ("methotrexate", "Antimetabolites", "Rx", "Not a controlled drug", "meth-oh-TREX-ate", ["Trexall", "Otrexup"], ["arthritis", "psoriasis", "cancer"]),
    ("adalimumab", "TNF inhibitors", "Rx", "Not a controlled drug", "a-da-LIM-ue-mab", ["Humira"], ["arthritis", "crohns_disease", "psoriasis"]),
    ("dupilumab", "Monoclonal antibodies", "Rx", "Not a controlled drug", "doo-PIL-ue-mab", ["Dupixent"], ["eczema", "asthma"]),
    ("sumatriptan", "Triptans", "Rx", "Not a controlled drug", "soo-ma-TRIP-tan", ["Imitrex"], ["migraine"]),
    ("zolpidem", "Sleep aids", "Rx", "C-IV", "zole-PI-dem", ["Ambien"], ["insomnia"]),
    ("naloxone", "Opioid antagonists", "Rx and/or OTC", "Not a controlled drug", "nal-OX-one", ["Narcan", "Evzio"], []),
    ("methylphenidate", "Stimulants", "Rx", "C-II", "meth-il-FEN-i-date", ["Ritalin", "Concerta"], ["adhd"]),
    ("colchicine", "Xanthine oxidase inhibitors", "Rx", "Not a controlled drug", "KOL-chi-seen", ["Colcrys", "Mitigare"], ["gout"]),
    ("allopurinol", "Xanthine oxidase inhibitors", "Rx", "Not a controlled drug", "al-oh-PURE-i-nol", ["Zyloprim"], ["gout"]),
    ("isotretinoin", "Retinoids", "Rx", "Not a controlled drug", "eye-soe-tret-IN-oh-in", ["Accutane", "Claravis"], ["acne"]),
    ("diphenhydramine", "Antihistamines", "OTC", "Not a controlled drug", "dye-fen-HYE-dra-meen", ["Benadryl"], ["allergies", "insomnia"]),
    ("loratadine", "Antihistamines", "OTC", "Not a controlled drug", "lor-AT-a-deen", ["Claritin", "Alavert"], ["allergies"]),
    ("cetirizine", "Antihistamines", "OTC", "Not a controlled drug", "se-TIR-i-zeen", ["Zyrtec"], ["allergies"]),
    ("omeprazole", "Proton pump inhibitors", "Rx and/or OTC", "Not a controlled drug", "oh-MEP-ra-zole", ["Prilosec"], ["acid_reflux"]),
    ("famotidine", "H2 blockers", "Rx and/or OTC", "Not a controlled drug", "fa-MOE-ti-deen", ["Pepcid"], ["acid_reflux"]),
    ("melatonin", "Supplements", "OTC", "Not a controlled drug", "mel-a-TOE-nin", ["Natrol Melatonin"], ["insomnia"]),
    ("pseudoephedrine", "Decongestants", "OTC", "Not a controlled drug", "soo-doe-e-FED-rin", ["Sudafed"], ["allergies"]),
    ("dextromethorphan", "Cough suppressants", "OTC", "Not a controlled drug", "dex-troe-meth-OR-fan", ["Robitussin DM", "Delsym"], []),
    ("citalopram", "SSRIs", "Rx", "Not a controlled drug", "sye-TAL-oh-pram", ["Celexa"], ["depression", "anxiety"]),
    ("trazodone", "Atypical antidepressants", "Rx", "Not a controlled drug", "TRAZ-oh-done", ["Desyrel", "Oleptro"], ["depression", "insomnia"]),
    ("lamotrigine", "Anticonvulsants", "Rx", "Not a controlled drug", "la-MOE-tri-jeen", ["Lamictal"], ["epilepsy", "bipolar_disorder"]),
    ("topiramate", "Anticonvulsants", "Rx", "Not a controlled drug", "toe-PYRE-a-mate", ["Topamax"], ["epilepsy", "migraine"]),
    ("verapamil", "Calcium channel blockers", "Rx", "Not a controlled drug", "ver-AP-a-mil", ["Calan", "Verelan"], ["hypertension", "heart_disease"]),
    # --- Expanded catalog ---
    ("methylprednisolone", "Corticosteroids", "Rx", "Not a controlled drug", "meth-il-pred-NIS-oh-lone", ["Medrol", "Solu-Medrol"], ["arthritis", "allergies", "lupus"]),
    ("dexamethasone", "Corticosteroids", "Rx", "Not a controlled drug", "dex-a-METH-a-sone", ["Decadron", "DexPak"], ["arthritis", "allergies", "cancer"]),
    ("hydrocortisone", "Topical corticosteroids", "Rx and/or OTC", "Not a controlled drug", "hye-droe-KOR-ti-sone", ["Cortizone-10", "Cortaid"], ["eczema", "psoriasis"]),
    ("triamcinolone", "Topical corticosteroids", "Rx", "Not a controlled drug", "trye-am-SIN-oh-lone", ["Kenalog", "Aristocort"], ["eczema", "psoriasis", "allergies"]),
    ("cyclosporine", "Immunosuppressants", "Rx", "Not a controlled drug", "sye-kloe-SPOR-een", ["Neoral", "Sandimmune", "Gengraf"], ["psoriasis", "arthritis"]),
    ("tacrolimus", "Immunosuppressants", "Rx", "Not a controlled drug", "ta-KROE-li-mus", ["Prograf", "Astagraf XL"], ["eczema"]),
    ("mycophenolate", "Immunosuppressants", "Rx", "Not a controlled drug", "mye-koe-FEN-oh-late", ["CellCept", "Myfortic"], ["lupus"]),
    ("rituximab", "Biologics", "Rx", "Not a controlled drug", "ri-TUX-i-mab", ["Rituxan"], ["arthritis", "cancer", "lupus"]),
    ("insulin aspart", "Insulins", "Rx", "Not a controlled drug", "IN-su-lin AS-part", ["NovoLog", "Fiasp"], ["diabetes"]),
    ("insulin lispro", "Insulins", "Rx", "Not a controlled drug", "IN-su-lin LYE-sproe", ["Humalog", "Admelog"], ["diabetes"]),
    ("canagliflozin", "SGLT2 inhibitors", "Rx", "Not a controlled drug", "kan-a-gli-FLOE-zin", ["Invokana"], ["diabetes"]),
    ("dapagliflozin", "SGLT2 inhibitors", "Rx", "Not a controlled drug", "dap-a-gli-FLOE-zin", ["Farxiga"], ["diabetes", "heart_disease"]),
    ("liraglutide", "GLP-1 receptor agonists", "Rx", "Not a controlled drug", "lir-a-GLOO-tide", ["Victoza", "Saxenda"], ["diabetes", "obesity"]),
    ("glipizide", "Sulfonamides", "Rx", "Not a controlled drug", "GLIP-i-zide", ["Glucotrol"], ["diabetes"]),
    ("pravastatin", "Statins", "Rx", "Not a controlled drug", "PRA-va-sta-tin", ["Pravachol"], ["high_cholesterol"]),
    ("simvastatin", "Statins", "Rx", "Not a controlled drug", "SIM-va-sta-tin", ["Zocor"], ["high_cholesterol"]),
    ("ezetimibe", "Statins", "Rx", "Not a controlled drug", "ez-ET-i-mibe", ["Zetia"], ["high_cholesterol"]),
    ("valsartan", "ARBs", "Rx", "Not a controlled drug", "val-SAR-tan", ["Diovan"], ["hypertension", "heart_disease"]),
    ("olmesartan", "ARBs", "Rx", "Not a controlled drug", "ole-me-SAR-tan", ["Benicar"], ["hypertension"]),
    ("irbesartan", "ARBs", "Rx", "Not a controlled drug", "ir-be-SAR-tan", ["Avapro"], ["hypertension"]),
    ("atenolol", "Beta blockers", "Rx", "Not a controlled drug", "a-TEN-oh-lol", ["Tenormin"], ["hypertension", "heart_disease"]),
    ("propranolol", "Beta blockers", "Rx", "Not a controlled drug", "proe-PRAN-oh-lol", ["Inderal"], ["hypertension", "migraine"]),
    ("bisoprolol", "Beta blockers", "Rx", "Not a controlled drug", "bis-OH-proe-lol", ["Zebeta"], ["hypertension", "heart_disease"]),
    ("diltiazem", "Calcium channel blockers", "Rx", "Not a controlled drug", "dil-TYE-a-zem", ["Cardizem", "Tiazac"], ["hypertension", "heart_disease"]),
    ("nifedipine", "Calcium channel blockers", "Rx", "Not a controlled drug", "nye-FED-i-peen", ["Procardia", "Adalat"], ["hypertension"]),
    ("digoxin", "Cardiac glycosides", "Rx", "Not a controlled drug", "di-JOX-in", ["Lanoxin"], ["heart_disease"]),
    ("nitroglycerin", "Nitrates", "Rx", "Not a controlled drug", "nye-troe-GLI-ser-in", ["Nitrostat", "Nitro-Dur", "Nitrolingual"], ["heart_disease"]),
    ("isosorbide", "Nitrates", "Rx", "Not a controlled drug", "eye-soe-SOR-bide", ["Isordil", "Imdur"], ["heart_disease"]),
    ("amiodarone", "Antiarrhythmics", "Rx", "Not a controlled drug", "a-MEE-oh-da-rone", ["Cordarone", "Pacerone"], ["heart_disease"]),
    ("apixaban", "Anticoagulants", "Rx", "Not a controlled drug", "a-PIX-a-ban", ["Eliquis"], ["blood_clots", "heart_disease"]),
    ("rivaroxaban", "Anticoagulants", "Rx", "Not a controlled drug", "riv-a-ROX-a-ban", ["Xarelto"], ["blood_clots"]),
    ("dabigatran", "Anticoagulants", "Rx", "Not a controlled drug", "da-BIG-a-tran", ["Pradaxa"], ["blood_clots"]),
    ("enoxaparin", "Anticoagulants", "Rx", "Not a controlled drug", "ee-nox-a-PA-rin", ["Lovenox"], ["blood_clots"]),
    ("pantoprazole", "Proton pump inhibitors", "Rx", "Not a controlled drug", "pan-TOE-pra-zole", ["Protonix"], ["acid_reflux"]),
    ("esomeprazole", "Proton pump inhibitors", "Rx and/or OTC", "Not a controlled drug", "es-oh-MEP-ra-zole", ["Nexium"], ["acid_reflux"]),
    ("lansoprazole", "Proton pump inhibitors", "Rx and/or OTC", "Not a controlled drug", "lan-SOE-pra-zole", ["Prevacid"], ["acid_reflux"]),
    ("ranitidine", "H2 blockers", "Rx", "Not a controlled drug", "ra-NI-ti-deen", ["Zantac"], ["acid_reflux"]),
    ("metoclopramide", "Prokinetics", "Rx", "Not a controlled drug", "met-oh-kloe-PRA-mide", ["Reglan"], ["acid_reflux", "nausea"]),
    ("loperamide", "Antidiarrheals", "OTC", "Not a controlled drug", "loe-PER-a-mide", ["Imodium"], ["diarrhea"]),
    ("bisacodyl", "Laxatives", "OTC", "Not a controlled drug", "bis-AK-oh-dil", ["Dulcolax"], ["constipation"]),
    ("polyethylene glycol", "Laxatives", "OTC", "Not a controlled drug", "pol-ee-ETH-i-leen GLYE-kol", ["MiraLax"], ["constipation"]),
    ("docusate", "Laxatives", "OTC", "Not a controlled drug", "DOK-yoo-sate", ["Colace"], ["constipation"]),
    ("calcium carbonate", "Antacids", "OTC", "Not a controlled drug", "KAL-see-um KAR-bon-ate", ["Tums", "Caltrate"], ["acid_reflux", "vitamin_deficiency"]),
    ("magnesium oxide", "Supplements", "OTC", "Not a controlled drug", "mag-NEE-zee-um OX-ide", ["Mag-Ox"], ["vitamin_deficiency", "constipation"]),
    ("fexofenadine", "Antihistamines", "OTC", "Not a controlled drug", "fex-oh-FEN-a-deen", ["Allegra"], ["allergies"]),
    ("hydroxyzine", "Antihistamines", "Rx", "Not a controlled drug", "hye-DROX-i-zeen", ["Vistaril", "Atarax"], ["anxiety", "allergies"]),
    ("fluticasone", "Nasal corticosteroids", "Rx and/or OTC", "Not a controlled drug", "floo-TIK-a-sone", ["Flonase", "Flovent"], ["allergies", "asthma"]),
    ("budesonide", "Inhaled corticosteroids", "Rx", "Not a controlled drug", "byoo-DES-oh-nide", ["Pulmicort", "Rhinocort"], ["asthma", "copd"]),
    ("tiotropium", "Anticholinergic bronchodilators", "Rx", "Not a controlled drug", "ty-oh-TROE-pee-um", ["Spiriva"], ["copd", "asthma"]),
    ("ipratropium", "Anticholinergic bronchodilators", "Rx", "Not a controlled drug", "i-pra-TROE-pee-um", ["Atrovent"], ["copd", "asthma"]),
    ("salmeterol", "Bronchodilators", "Rx", "Not a controlled drug", "sal-MEE-ter-ol", ["Serevent"], ["asthma", "copd"]),
    ("levofloxacin", "Fluoroquinolones", "Rx", "Not a controlled drug", "lee-voe-FLOX-a-sin", ["Levaquin"], ["bacterial_infections"]),
    ("moxifloxacin", "Fluoroquinolones", "Rx", "Not a controlled drug", "mox-i-FLOX-a-sin", ["Avelox"], ["bacterial_infections"]),
    ("trimethoprim-sulfamethoxazole", "Sulfonamides", "Rx", "Not a controlled drug", "trye-METH-oh-prim sul-fa-meth-OX-a-zole", ["Bactrim", "Septra"], ["bacterial_infections"]),
    ("metronidazole", "Nitroimidazoles", "Rx", "Not a controlled drug", "me-troe-NI-da-zole", ["Flagyl"], ["bacterial_infections"]),
    ("nitrofurantoin", "Sulfonamides", "Rx", "Not a controlled drug", "nye-troe-fyoor-AN-toyn", ["Macrobid", "Macrodantin"], ["bacterial_infections"]),
    ("penicillin", "Penicillins", "Rx", "Not a controlled drug", "pen-i-SIL-in", ["Penicillin VK"], ["bacterial_infections"]),
    ("ampicillin", "Penicillins", "Rx", "Not a controlled drug", "am-pi-SIL-in", ["Principen"], ["bacterial_infections"]),
    ("amoxicillin-clavulanate", "Penicillins", "Rx", "Not a controlled drug", "a-mox-i-SIL-in klav-yoo-LAN-ate", ["Augmentin"], ["bacterial_infections"]),
    ("ceftriaxone", "Cephalosporins", "Rx", "Not a controlled drug", "sef-trye-AX-one", ["Rocephin"], ["bacterial_infections"]),
    ("vancomycin", "Cephalosporins", "Rx", "Not a controlled drug", "van-koe-MYE-sin", ["Vancocin"], ["bacterial_infections"]),
    ("fluconazole", "Antifungals", "Rx", "Not a controlled drug", "floo-KOE-na-zole", ["Diflucan"], ["fungal_infections"]),
    ("terbinafine", "Antifungals", "Rx and/or OTC", "Not a controlled drug", "ter-BIN-a-feen", ["Lamisil"], ["fungal_infections"]),
    ("ketoconazole", "Antifungals", "Rx and/or OTC", "Not a controlled drug", "kee-toe-KOE-na-zole", ["Nizoral"], ["fungal_infections"]),
    ("nystatin", "Antifungals", "Rx", "Not a controlled drug", "nye-STAT-in", ["Mycostatin"], ["fungal_infections"]),
    ("acyclovir", "Antivirals", "Rx", "Not a controlled drug", "ay-SYE-kloe-veer", ["Zovirax"], ["herpes"]),
    ("valacyclovir", "Antivirals", "Rx", "Not a controlled drug", "val-ay-SYE-kloe-veer", ["Valtrex"], ["herpes"]),
    ("oseltamivir", "Antivirals", "Rx", "Not a controlled drug", "oh-sel-TAM-i-veer", ["Tamiflu"], ["influenza"]),
    ("tenofovir", "Antivirals", "Rx", "Not a controlled drug", "te-NOE-foe-veer", ["Viread"], ["viral_infections"]),
    ("tadalafil", "PDE5 inhibitors", "Rx", "Not a controlled drug", "tah-DAL-a-fil", ["Cialis", "Adcirca"], ["erectile_dysfunction", "bph"]),
    ("vardenafil", "PDE5 inhibitors", "Rx", "Not a controlled drug", "var-DEN-a-fil", ["Levitra"], ["erectile_dysfunction"]),
    ("morphine", "Opioids", "Rx", "C-II", "MOR-feen", ["MS Contin", "Roxanol"], ["pain"]),
    ("fentanyl", "Opioids", "Rx", "C-II", "FEN-ta-nil", ["Duragesic", "Sublimaze"], ["pain"]),
    ("codeine", "Opioids", "Rx", "C-II", "KOE-deen", ["Codeine sulfate"], ["pain"]),
    ("buprenorphine", "Partial opioid agonists", "Rx", "C-III", "byoo-pre-NOR-feen", ["Suboxone", "Subutex"], ["opioid_dependence", "pain"]),
    ("methadone", "Opioids", "Rx", "C-II", "METH-a-done", ["Dolophine", "Methadose"], ["opioid_dependence", "pain"]),
    ("amphetamine-dextroamphetamine", "Stimulants", "Rx", "C-II", "am-FET-a-meen dex-troe-am-FET-a-meen", ["Adderall"], ["adhd"]),
    ("lisdexamfetamine", "Stimulants", "Rx", "C-II", "lis-dex-am-FET-a-meen", ["Vyvanse"], ["adhd"]),
    ("atomoxetine", "ADHD non-stimulants", "Rx", "Not a controlled drug", "at-oh-MOX-e-teen", ["Strattera"], ["adhd"]),
    ("guanfacine", "ADHD non-stimulants", "Rx", "Not a controlled drug", "GWAN-fa-seen", ["Intuniv", "Tenex"], ["adhd", "hypertension"]),
    ("valproic acid", "Anticonvulsants", "Rx", "Not a controlled drug", "val-PROE-ik AS-id", ["Depakote", "Depakene"], ["epilepsy", "bipolar_disorder", "migraine"]),
    ("levetiracetam", "Anticonvulsants", "Rx", "Not a controlled drug", "lee-ve-tye-RA-se-tam", ["Keppra"], ["epilepsy"]),
    ("carbamazepine", "Anticonvulsants", "Rx", "Not a controlled drug", "kar-ba-MAZ-e-peen", ["Tegretol", "Carbatrol"], ["epilepsy", "bipolar_disorder"]),
    ("phenytoin", "Anticonvulsants", "Rx", "Not a controlled drug", "FEN-i-toyn", ["Dilantin"], ["epilepsy"]),
    ("paroxetine", "SSRIs", "Rx", "Not a controlled drug", "pa-ROX-e-teen", ["Paxil"], ["depression", "anxiety"]),
    ("mirtazapine", "Atypical antidepressants", "Rx", "Not a controlled drug", "mir-TAZ-a-peen", ["Remeron"], ["depression"]),
    ("olanzapine", "Atypical antipsychotics", "Rx", "Not a controlled drug", "oh-LAN-za-peen", ["Zyprexa"], ["schizophrenia", "bipolar_disorder"]),
    ("risperidone", "Atypical antipsychotics", "Rx", "Not a controlled drug", "ris-PER-i-done", ["Risperdal"], ["schizophrenia", "bipolar_disorder"]),
    ("haloperidol", "Atypical antipsychotics", "Rx", "Not a controlled drug", "ha-loe-PER-i-dol", ["Haldol"], ["schizophrenia"]),
    ("ziprasidone", "Atypical antipsychotics", "Rx", "Not a controlled drug", "zi-PRAS-i-done", ["Geodon"], ["schizophrenia", "bipolar_disorder"]),
    ("diazepam", "Benzodiazepines", "Rx", "C-IV", "dye-AZ-e-pam", ["Valium"], ["anxiety", "muscle_spasm"]),
    ("temazepam", "Benzodiazepines", "Rx", "C-IV", "tem-AZ-e-pam", ["Restoril"], ["insomnia"]),
    ("buspirone", "Anxiolytics", "Rx", "Not a controlled drug", "byoo-SPYE-rone", ["Buspar"], ["anxiety"]),
    ("eszopiclone", "Sleep aids", "Rx", "C-IV", "es-zoe-PIK-lone", ["Lunesta"], ["insomnia"]),
    ("methocarbamol", "Muscle relaxants", "Rx", "Not a controlled drug", "meth-oh-KAR-ba-mol", ["Robaxin"], ["muscle_spasm", "pain"]),
    ("baclofen", "Muscle relaxants", "Rx", "Not a controlled drug", "BAK-loe-fen", ["Lioresal", "Gablofen"], ["muscle_spasm"]),
    ("tizanidine", "Muscle relaxants", "Rx", "Not a controlled drug", "tye-ZAN-i-deen", ["Zanaflex"], ["muscle_spasm"]),
    ("carisoprodol", "Muscle relaxants", "Rx", "C-IV", "kar-eye-soe-PROE-dol", ["Soma"], ["muscle_spasm", "pain"]),
    ("alendronate", "Bisphosphonates", "Rx", "Not a controlled drug", "a-LEN-droe-nate", ["Fosamax"], ["osteoporosis"]),
    ("risedronate", "Bisphosphonates", "Rx", "Not a controlled drug", "ris-ED-roe-nate", ["Actonel"], ["osteoporosis"]),
    ("zoledronic acid", "Bisphosphonates", "Rx", "Not a controlled drug", "zoe-le-DROE-nik AS-id", ["Reclast", "Zometa"], ["osteoporosis", "cancer"]),
    ("raloxifene", "SERMs", "Rx", "Not a controlled drug", "ral-OX-i-feen", ["Evista"], ["osteoporosis"]),
    ("calcitonin", "Hormones", "Rx", "Not a controlled drug", "kal-si-TOE-nin", ["Miacalcin", "Fortical"], ["osteoporosis"]),
    ("estradiol", "Estrogens", "Rx", "Not a controlled drug", "es-tra-DYE-ol", ["Estrace", "Vivelle-Dot"], ["menopause", "contraception"]),
    ("progesterone", "Progestogens", "Rx", "Not a controlled drug", "proe-JES-ter-one", ["Prometrium"], ["menopause", "contraception"]),
    ("testosterone", "Androgens", "Rx", "C-III", "tes-TOS-ter-one", ["AndroGel", "Testim"], ["low_testosterone"]),
    ("ethinyl estradiol-norethindrone", "Contraceptives", "Rx", "Not a controlled drug", "ETH-in-il es-tra-DYE-ol nor-eth-IN-drone", ["Ortho-Novum", "Loestrin"], ["contraception"]),
    ("levonorgestrel", "Contraceptives", "OTC", "Not a controlled drug", "lee-voe-nor-JES-trel", ["Plan B", "Mirena"], ["contraception"]),
    ("norethindrone", "Progestogens", "Rx", "Not a controlled drug", "nor-eth-IN-drone", ["Aygestin"], ["contraception", "menopause"]),
    ("clomiphene", "Fertility agents", "Rx", "Not a controlled drug", "KLOE-mi-feen", ["Clomid"], []),
    ("misoprostol", "Prostaglandins", "Rx", "Not a controlled drug", "mye-soe-PROST-ole", ["Cytotec"], []),
    ("oxytocin", "Hormones", "Rx", "Not a controlled drug", "ox-i-TOE-sin", ["Pitocin"], []),
    ("methimazole", "Antithyroid agents", "Rx", "Not a controlled drug", "meth-IM-a-zole", ["Tapazole"], ["hyperthyroidism"]),
    ("propylthiouracil", "Antithyroid agents", "Rx", "Not a controlled drug", "proe-pil-thye-oh-YOOR-a-sil", ["PTU"], ["hyperthyroidism"]),
    ("desiccated thyroid", "Thyroid hormones", "Rx", "Not a controlled drug", "DES-i-kay-ted THYE-roid", ["Armour Thyroid", "Nature-Throid"], ["hypothyroidism"]),
    ("mupirocin", "Topical antibiotics", "Rx", "Not a controlled drug", "myoo-PEER-oh-sin", ["Bactroban"], ["bacterial_infections"]),
    ("bacitracin", "Topical antibiotics", "OTC", "Not a controlled drug", "bas-i-TRAY-sin", ["Neosporin"], ["bacterial_infections"]),
    ("tretinoin", "Topical retinoids", "Rx", "Not a controlled drug", "TRET-i-noyn", ["Retin-A", "Renova"], ["acne"]),
    ("adapalene", "Topical retinoids", "Rx and/or OTC", "Not a controlled drug", "a-DAP-a-leen", ["Differin"], ["acne"]),
    ("benzoyl peroxide", "Acne treatments", "OTC", "Not a controlled drug", "BEN-zoe-il per-OX-ide", ["Clearasil", "PanOxyl"], ["acne"]),
    ("timolol", "Ophthalmic beta blockers", "Rx", "Not a controlled drug", "TYE-moe-lol", ["Timoptic", "Istalol"], ["glaucoma"]),
    ("latanoprost", "Ophthalmic prostaglandins", "Rx", "Not a controlled drug", "la-TAN-oh-prost", ["Xalatan"], ["glaucoma"]),
    ("bimatoprost", "Ophthalmic prostaglandins", "Rx", "Not a controlled drug", "bi-MAT-oh-prost", ["Lumigan", "Latisse"], ["glaucoma"]),
    ("brimonidine", "Ophthalmic alpha agonists", "Rx", "Not a controlled drug", "bri-MOE-ni-deen", ["Alphagan"], ["glaucoma"]),
    ("ofloxacin ophthalmic", "Ophthalmic antibiotics", "Rx", "Not a controlled drug", "oh-FLOX-a-sin", ["Ocuflox"], ["bacterial_infections"]),
    ("tobramycin ophthalmic", "Ophthalmic antibiotics", "Rx", "Not a controlled drug", "toe-bra-MYE-sin", ["Tobrex"], ["bacterial_infections"]),
    ("vitamin D3", "Vitamins", "OTC", "Not a controlled drug", "VYE-ta-min D3", ["D-Vi-Sol", "Drisdol"], ["vitamin_deficiency", "osteoporosis"]),
    ("folic acid", "Vitamins", "OTC", "Not a controlled drug", "FOE-lik AS-id", ["Folvite"], ["vitamin_deficiency", "anemia"]),
    ("ferrous sulfate", "Iron supplements", "OTC", "Not a controlled drug", "FER-us SUL-fate", ["Slow FE", "Feosol"], ["anemia"]),
    ("vitamin B12", "Vitamins", "OTC", "Not a controlled drug", "VYE-ta-min B12", ["Cyanoject", "Nascobal"], ["vitamin_deficiency", "anemia"]),
    ("multivitamin", "Vitamins", "OTC", "Not a controlled drug", "mul-tee-VYE-ta-min", ["Centrum", "One A Day"], ["vitamin_deficiency"]),
]


CONDITIONS_DATA = [
    ("pain", "Pain", "Pain is an unpleasant sensory and emotional experience. Many drugs treat acute and chronic pain."),
    ("fever", "Fever", "Fever is a temporary increase in body temperature, often due to illness."),
    ("hypertension", "Hypertension (High Blood Pressure)", "Hypertension is a long-term condition where blood pressure in the arteries is persistently elevated."),
    ("diabetes", "Diabetes (Type 2)", "Type 2 diabetes is a chronic condition that affects how the body metabolizes glucose."),
    ("depression", "Depression", "Depression is a mood disorder causing persistent feelings of sadness and loss of interest."),
    ("anxiety", "Anxiety", "Anxiety disorders involve excessive worry or fear that interferes with daily activities."),
    ("high_cholesterol", "High Cholesterol", "High cholesterol increases the risk of heart disease and stroke."),
    ("heart_disease", "Heart Disease", "Heart disease describes a range of conditions affecting the heart."),
    ("asthma", "Asthma", "Asthma is a condition in which airways narrow and swell, causing breathing difficulty."),
    ("allergies", "Allergies", "Allergies are immune system reactions to substances that are usually harmless."),
    ("arthritis", "Arthritis", "Arthritis is inflammation of one or more joints, causing pain and stiffness."),
    ("adhd", "ADHD", "Attention-deficit/hyperactivity disorder affects attention, impulse control, and activity levels."),
    ("bipolar_disorder", "Bipolar Disorder", "Bipolar disorder causes extreme mood swings including emotional highs and lows."),
    ("schizophrenia", "Schizophrenia", "Schizophrenia is a serious mental disorder affecting thoughts, feelings, and behavior."),
    ("epilepsy", "Epilepsy", "Epilepsy is a neurological disorder marked by recurrent seizures."),
    ("insomnia", "Insomnia", "Insomnia is difficulty falling or staying asleep."),
    ("erectile_dysfunction", "Erectile Dysfunction", "Erectile dysfunction is the inability to achieve or maintain an erection."),
    ("hypothyroidism", "Hypothyroidism", "Hypothyroidism is an underactive thyroid gland producing insufficient hormone."),
    ("bacterial_infections", "Bacterial Infections", "Bacterial infections are illnesses caused by harmful bacteria."),
    ("acne", "Acne", "Acne is a skin condition that occurs when hair follicles become plugged with oil and dead skin cells."),
    ("gout", "Gout", "Gout is a form of inflammatory arthritis caused by uric acid crystals in joints."),
    ("migraine", "Migraine", "Migraine is a neurological condition causing intense headaches."),
    ("acid_reflux", "Acid Reflux (GERD)", "GERD occurs when stomach acid frequently flows back into the esophagus."),
    ("bph", "Benign Prostatic Hyperplasia", "BPH is a noncancerous enlargement of the prostate gland."),
    ("cancer", "Cancer", "Cancer is a disease in which abnormal cells divide uncontrollably and destroy body tissue."),
    ("lupus", "Lupus", "Lupus is a systemic autoimmune disease where the immune system attacks tissues."),
    ("crohns_disease", "Crohn's Disease", "Crohn's disease is a chronic inflammatory bowel disease."),
    ("psoriasis", "Psoriasis", "Psoriasis is a skin disease causing red, itchy, scaly patches."),
    ("eczema", "Eczema", "Eczema is a condition that makes skin red and itchy."),
    ("obesity", "Obesity", "Obesity is a complex disease involving an excessive amount of body fat."),
    ("osteoporosis", "Osteoporosis", "Osteoporosis is a condition that weakens bones, making them fragile and more likely to break."),
    ("glaucoma", "Glaucoma", "Glaucoma is a group of eye conditions that damage the optic nerve, often due to high intraocular pressure."),
    ("copd", "COPD", "Chronic obstructive pulmonary disease is a chronic inflammatory lung disease that causes airflow obstruction."),
    ("hyperthyroidism", "Hyperthyroidism", "Hyperthyroidism is an overactive thyroid gland producing excess thyroid hormone."),
    ("herpes", "Herpes", "Herpes infections are caused by herpes simplex virus and produce painful cold sores or genital lesions."),
    ("influenza", "Influenza (Flu)", "Influenza is a contagious respiratory illness caused by influenza viruses."),
    ("fungal_infections", "Fungal Infections", "Fungal infections are diseases caused by fungi, ranging from superficial skin infections to invasive disease."),
    ("viral_infections", "Viral Infections", "Viral infections are illnesses caused by viruses such as HIV, hepatitis, or herpes."),
    ("constipation", "Constipation", "Constipation is infrequent or difficult bowel movements."),
    ("diarrhea", "Diarrhea", "Diarrhea is the passage of loose or watery stools."),
    ("nausea", "Nausea and Vomiting", "Nausea and vomiting can result from many causes including infections, medications, and motion sickness."),
    ("opioid_dependence", "Opioid Use Disorder", "Opioid use disorder is a chronic medical condition characterized by problematic opioid use."),
    ("contraception", "Contraception", "Contraception refers to methods used to prevent pregnancy."),
    ("menopause", "Menopause", "Menopause is the time that marks the end of a woman's menstrual cycles."),
    ("low_testosterone", "Low Testosterone", "Low testosterone (hypogonadism) is a condition in which the body produces insufficient testosterone."),
    ("muscle_spasm", "Muscle Spasm", "Muscle spasms are involuntary contractions of one or more muscles that can be painful."),
    ("blood_clots", "Blood Clots (Thrombosis)", "Blood clots can block veins or arteries and cause serious complications such as stroke or pulmonary embolism."),
    ("anemia", "Anemia", "Anemia is a condition in which the blood lacks enough healthy red blood cells to carry oxygen."),
    ("vitamin_deficiency", "Vitamin Deficiency", "Vitamin deficiencies occur when the body lacks sufficient amounts of essential vitamins."),
]


PILL_IMAGES_DATA = [
    # (generic_name, imprint, shape, color, strength, manufacturer)
    ("ibuprofen", "I-2", "Round", "White", "200 mg", "Advil"),
    ("ibuprofen", "44-291", "Round", "Brown", "200 mg", "LNK International"),
    ("ibuprofen", "IP 466", "Oval", "White", "800 mg", "Amneal Pharmaceuticals"),
    ("acetaminophen", "TYLENOL 500", "Oblong", "White", "500 mg", "McNeil"),
    ("acetaminophen", "L484", "Oblong", "White", "500 mg", "Kroger"),
    ("metformin", "M 500", "Round", "White", "500 mg", "Mylan"),
    ("metformin", "Z 70", "Oval", "White", "1000 mg", "Zydus"),
    ("lisinopril", "10 MG", "Oval", "White", "10 mg", "Lupin"),
    ("lisinopril", "M L24", "Round", "Pink", "20 mg", "Mylan"),
    ("atorvastatin", "PD 156", "Oval", "White", "20 mg", "Pfizer"),
    ("atorvastatin", "A 10", "Oval", "White", "10 mg", "Apotex"),
    ("amlodipine", "G 1530", "Round", "White", "5 mg", "Greenstone"),
    ("amoxicillin", "AMOX 500", "Capsule", "Pink/Buff", "500 mg", "Sandoz"),
    ("azithromycin", "PLIVA 333", "Round", "Pink", "250 mg", "Pliva"),
    ("ciprofloxacin", "CIPRO 500", "Oblong", "White", "500 mg", "Bayer"),
    ("sertraline", "ZOLOFT 50", "Oblong", "Blue", "50 mg", "Pfizer"),
    ("sertraline", "G 4900", "Oblong", "Blue", "100 mg", "Greenstone"),
    ("fluoxetine", "PROZAC 20", "Capsule", "Green/Yellow", "20 mg", "Eli Lilly"),
    ("alprazolam", "XANAX 0.5", "Oval", "Peach", "0.5 mg", "Pfizer"),
    ("alprazolam", "G 372", "Oval", "Blue", "1 mg", "Greenstone"),
    ("oxycodone", "M 30", "Round", "Blue", "30 mg", "Mallinckrodt"),
    ("hydrocodone", "M367", "Oblong", "White", "10/325 mg", "Mallinckrodt"),
    ("tramadol", "AN 627", "Round", "White", "50 mg", "Amneal"),
    ("gabapentin", "IP 102", "Capsule", "Yellow", "300 mg", "Amneal"),
    ("levothyroxine", "M L 4", "Round", "Yellow", "50 mcg", "Mylan"),
    ("warfarin", "TV 5", "Round", "Pink", "5 mg", "Teva"),
    ("prednisone", "WESTWARD 477", "Round", "White", "20 mg", "West-Ward"),
    ("omeprazole", "57", "Capsule", "Purple", "20 mg", "Dr. Reddy's"),
    ("loratadine", "L612", "Round", "White", "10 mg", "Perrigo"),
    ("cetirizine", "Z 10", "Round", "White", "10 mg", "Zyrtec"),
    ("zolpidem", "TEVA 73", "Round", "Pink", "5 mg", "Teva"),
    ("clonazepam", "C 1", "Round", "Yellow", "0.5 mg", "Accord"),
    ("methylphenidate", "M 5", "Round", "Yellow", "5 mg", "Mallinckrodt"),
    ("warfarin", "COUMADIN 1", "round", "pink", "1mg", "Bristol-Myers Squibb"),
    ("warfarin", "COUMADIN 2", "round", "lavender", "2mg", "Bristol-Myers Squibb"),
    ("warfarin", "COUMADIN 5", "round", "peach", "5mg", "Bristol-Myers Squibb"),
    ("warfarin", "COUMADIN 10", "round", "white", "10mg", "Bristol-Myers Squibb"),
    ("clopidogrel", "75", "round", "pink", "75mg", "Sanofi-Aventis"),
    ("furosemide", "LASIX 40", "round", "white", "40mg", "Sanofi-Aventis"),
    ("furosemide", "LASIX 80", "oval", "white", "80mg", "Sanofi-Aventis"),
    ("prednisone", "DELTASONE 5", "round", "white", "5mg", "Pfizer"),
    ("prednisone", "DELTASONE 20", "round", "peach", "20mg", "Pfizer"),
    ("metformin", "GLUCOPHAGE 500", "oval", "white", "500mg", "Bristol-Myers Squibb"),
    ("rosuvastatin", "CRESTOR 10", "round", "pink", "10mg", "AstraZeneca"),
    ("rosuvastatin", "CRESTOR 20", "round", "pink", "20mg", "AstraZeneca"),
    ("losartan", "COZAAR 50", "oval", "white", "50mg", "Merck"),
    ("metoprolol", "LOPRESSOR 50", "round", "pink", "50mg", "Novartis"),
    ("carvedilol", "COREG 6.25", "oval", "white", "6.25mg", "GlaxoSmithKline"),
    ("amlodipine", "NORVASC 5", "diamond", "white", "5mg", "Pfizer"),
    ("amlodipine", "NORVASC 10", "round", "white", "10mg", "Pfizer"),
    ("hydrochlorothiazide", "HYDRODIURIL 25", "round", "peach", "25mg", "Merck"),
    ("pantoprazole", "PROTONIX 20", "oval", "yellow", "20mg", "Wyeth"),
    ("pantoprazole", "PROTONIX 40", "oval", "yellow", "40mg", "Wyeth"),
    ("famotidine", "PEPCID 20", "oval", "brown", "20mg", "Merck"),
    ("ondansetron", "ZOFRAN 4", "oval", "white", "4mg", "GlaxoSmithKline"),
    ("ondansetron", "ZOFRAN 8", "oval", "yellow", "8mg", "GlaxoSmithKline"),
    ("cetirizine", "ZYRTEC 10", "oval", "white", "10mg", "UCB"),
    ("loratadine", "CLARITIN 10", "round", "white", "10mg", "Bayer"),
    ("montelukast", "SINGULAIR 10", "round", "beige", "10mg", "Merck"),
    ("ciprofloxacin", "CIPRO 500", "oval", "white", "500mg", "Bayer"),
    ("doxycycline", "VIBRAMYCIN 100", "capsule", "blue/white", "100mg", "Pfizer"),
    ("fluconazole", "DIFLUCAN 150", "oval", "pink", "150mg", "Pfizer"),
    ("acyclovir", "ZOVIRAX 400", "oval", "blue", "400mg", "GlaxoSmithKline"),
    ("tamsulosin", "FLOMAX 0.4", "capsule", "olive/orange", "0.4mg", "Boehringer Ingelheim"),
    ("tadalafil", "CIALIS 10", "oval", "yellow", "10mg", "Eli Lilly"),
    ("sildenafil", "VIAGRA 50", "diamond", "blue", "50mg", "Pfizer"),
    ("sildenafil", "VIAGRA 100", "diamond", "blue", "100mg", "Pfizer"),
    ("oxycodone", "OC 10", "round", "white", "10mg", "Purdue Pharma"),
    ("methylphenidate", "RITALIN 10", "round", "white", "10mg", "Novartis"),
    ("amphetamine", "ADDERALL 20", "round", "orange", "20mg", "Teva"),
    ("lithium", "LITHOBID 300", "capsule", "pink", "300mg", "Noven"),
    ("valproic acid", "DEPAKOTE 250", "oval", "salmon", "250mg", "AbbVie"),
    ("lamotrigine", "LAMICTAL 100", "oval", "white", "100mg", "GlaxoSmithKline"),
    ("levetiracetam", "KEPPRA 500", "oval", "yellow", "500mg", "UCB"),
    ("duloxetine", "CYMBALTA 30", "capsule", "white/blue", "30mg", "Eli Lilly"),
    ("venlafaxine", "EFFEXOR 75", "capsule", "peach", "75mg", "Pfizer"),
    ("bupropion", "WELLBUTRIN 150", "round", "purple", "150mg", "GlaxoSmithKline"),
    ("trazodone", "DESYREL 100", "round", "white", "100mg", "Mead Johnson"),
    ("escitalopram", "LEXAPRO 10", "round", "white", "10mg", "Forest Labs"),
    ("quetiapine", "SEROQUEL 100", "round", "yellow", "100mg", "AstraZeneca"),
    ("quetiapine", "SEROQUEL 300", "oval", "white", "300mg", "AstraZeneca"),
    ("olanzapine", "ZYPREXA 5", "round", "white", "5mg", "Eli Lilly"),
    ("aripiprazole", "ABILIFY 10", "round", "pink", "10mg", "Otsuka"),
    ("clonazepam", "KLONOPIN 1", "round", "blue", "1mg", "Roche"),
    ("lorazepam", "ATIVAN 1", "round", "white", "1mg", "Wyeth"),
    ("diazepam", "VALIUM 5", "round", "yellow", "5mg", "Roche"),
    ("buspirone", "BUSPAR 15", "oval", "white", "15mg", "Bristol-Myers Squibb"),
    ("pregabalin", "LYRICA 75", "capsule", "white/orange", "75mg", "Pfizer"),
    ("celecoxib", "CELEBREX 200", "capsule", "white/gold", "200mg", "Pfizer"),
    ("naproxen", "ALEVE 220", "oval", "blue", "220mg", "Bayer"),
    ("cyclobenzaprine", "FLEXERIL 10", "round", "yellow", "10mg", "McNeil"),
    ("colchicine", "COLCRYS 0.6", "oval", "purple", "0.6mg", "Takeda"),
    ("allopurinol", "ZYLOPRIM 300", "round", "white", "300mg", "Aspen"),
    ("alendronate", "FOSAMAX 70", "oval", "white", "70mg", "Merck"),
    ("estradiol", "ESTRACE 1", "round", "pink", "1mg", "Warner Chilcott"),
    ("levothyroxine", "SYNTHROID 100", "oval", "yellow", "100mcg", "AbbVie"),
    ("levothyroxine", "SYNTHROID 50", "oval", "white", "50mcg", "AbbVie"),
    ("methimazole", "TAPAZOLE 10", "round", "white", "10mg", "Monarch"),
    ("finasteride", "PROSCAR 5", "round", "blue", "5mg", "Merck"),
    ("finasteride", "PROPECIA 1", "oval", "tan", "1mg", "Merck"),
    ("spironolactone", "ALDACTONE 25", "round", "white", "25mg", "Pfizer"),
    ("digoxin", "LANOXIN 0.25", "round", "white", "0.25mg", "GlaxoSmithKline"),
    ("lisinopril", "ZESTRIL 10", "round", "pink", "10mg", "AstraZeneca"),
    ("atorvastatin", "LIPITOR 20", "oval", "white", "20mg", "Pfizer"),
    ("atorvastatin", "LIPITOR 40", "oval", "white", "40mg", "Pfizer"),
]


INTERACTIONS_DATA = [
    ("ibuprofen", "warfarin", "major", "Concurrent use of ibuprofen and warfarin significantly increases the risk of serious bleeding. NSAIDs inhibit platelet function and can cause GI ulceration; warfarin already increases bleeding risk."),
    ("ibuprofen", "aspirin", "moderate", "Ibuprofen can interfere with the cardioprotective antiplatelet effect of low-dose aspirin. If both are needed, take ibuprofen at least 8 hours before or 30 minutes after aspirin."),
    ("warfarin", "aspirin", "major", "Combining warfarin with aspirin substantially increases bleeding risk. Concurrent use should only occur under close medical supervision."),
    ("sertraline", "tramadol", "major", "Combining sertraline (SSRI) with tramadol can cause serotonin syndrome — a potentially life-threatening reaction. Symptoms include agitation, hallucinations, rapid heart rate, fever."),
    ("fluoxetine", "tramadol", "major", "Fluoxetine combined with tramadol may cause serotonin syndrome. Also, fluoxetine inhibits CYP2D6, reducing tramadol's analgesic effect."),
    ("alprazolam", "oxycodone", "major", "Combining benzodiazepines with opioids can result in profound sedation, respiratory depression, coma, and death."),
    ("alprazolam", "hydrocodone", "major", "Concurrent use of alprazolam and hydrocodone increases the risk of fatal respiratory depression."),
    ("metoprolol", "verapamil", "major", "Combining a beta blocker with a non-dihydropyridine calcium channel blocker can cause severe bradycardia, hypotension, and heart block."),
    ("ciprofloxacin", "warfarin", "major", "Ciprofloxacin can substantially increase warfarin's anticoagulant effect, raising INR and bleeding risk."),
    ("lithium", "ibuprofen", "major", "NSAIDs reduce renal lithium clearance, potentially leading to lithium toxicity. Monitor lithium levels closely."),
    ("metformin", "ciprofloxacin", "moderate", "Fluoroquinolones may disturb blood glucose, causing either hypo- or hyperglycemia in patients on metformin."),
    ("prednisone", "ibuprofen", "major", "Combining corticosteroids with NSAIDs substantially increases the risk of GI ulceration and bleeding."),
    ("sildenafil", "isosorbide", "major", "Combining PDE5 inhibitors with nitrates can cause severe, potentially fatal hypotension."),
    ("clopidogrel", "omeprazole", "moderate", "Omeprazole inhibits CYP2C19 and can reduce the antiplatelet effect of clopidogrel. Consider pantoprazole instead."),
    ("simvastatin", "amiodarone", "major", "Amiodarone can increase simvastatin levels, raising the risk of severe muscle injury (rhabdomyolysis)."),
    ("escitalopram", "tramadol", "major", "Combining SSRIs with tramadol may precipitate serotonin syndrome."),
    ("duloxetine", "tramadol", "major", "Both drugs increase serotonin levels; concurrent use can cause serotonin syndrome."),
    ("methotrexate", "ibuprofen", "major", "NSAIDs can reduce methotrexate clearance, leading to severe methotrexate toxicity including pancytopenia."),
    ("levothyroxine", "omeprazole", "moderate", "Reduced gastric acidity from PPIs can impair levothyroxine absorption. Separate dosing and monitor TSH."),
    ("amlodipine", "simvastatin", "moderate", "Amlodipine increases simvastatin exposure; limit simvastatin dose to 20 mg when used with amlodipine."),
    ("furosemide", "lisinopril", "moderate", "ACE inhibitors plus diuretics may cause symptomatic hypotension, especially with first doses."),
    ("clonazepam", "hydrocodone", "major", "Benzodiazepine plus opioid combinations carry a serious risk of respiratory depression and death."),
    ("lorazepam", "oxycodone", "major", "Concurrent benzodiazepine and opioid use can cause profound CNS and respiratory depression."),
    ("aripiprazole", "fluoxetine", "moderate", "Fluoxetine inhibits CYP2D6 and may increase aripiprazole levels. Dose adjustments may be needed."),
    ("hydrochlorothiazide", "lithium", "major", "Thiazide diuretics reduce lithium clearance and can cause lithium toxicity."),
    # --- Additional major interactions ---
    ("warfarin", "ibuprofen", "major", "NSAIDs can displace warfarin from plasma proteins and inhibit platelet function, greatly increasing bleeding risk."),
    ("digoxin", "amiodarone", "major", "Amiodarone increases digoxin serum levels by inhibiting P-glycoprotein, raising the risk of digoxin toxicity. Reduce digoxin dose by 30-50%."),
    ("simvastatin", "clarithromycin", "major", "Clarithromycin strongly inhibits CYP3A4, dramatically increasing simvastatin exposure and the risk of severe myopathy and rhabdomyolysis. Avoid combination."),
    ("carbamazepine", "valproic acid", "major", "Carbamazepine induces metabolism of valproic acid, reducing its levels; valproate can also raise carbamazepine's active metabolite. Levels of both require monitoring."),
    ("phenytoin", "warfarin", "major", "Phenytoin and warfarin interact bidirectionally: initial increase in INR followed by reduced anticoagulant effect; phenytoin levels may rise. Monitor closely."),
    ("sertraline", "tryptophan", "major", "Combining SSRIs with tryptophan can precipitate serotonin syndrome with agitation, hyperthermia, and autonomic instability."),
    ("phenelzine", "sertraline", "major", "MAOIs combined with SSRIs can cause life-threatening serotonin syndrome. A 14-day washout is required between agents."),
    ("phenelzine", "fluoxetine", "major", "Combining MAOIs with fluoxetine carries a serious risk of serotonin syndrome. A 5-week washout after fluoxetine is required before starting an MAOI."),
    ("tranylcypromine", "sertraline", "major", "MAOIs combined with SSRIs can precipitate fatal serotonin syndrome. Avoid combination."),
    ("methylphenidate", "phenelzine", "major", "Stimulants combined with MAOIs can trigger hypertensive crisis. Contraindicated."),
    ("amphetamine", "phenelzine", "major", "Amphetamines combined with MAOIs can cause severe hypertensive crisis. Contraindicated."),
    ("bupropion", "tramadol", "major", "Both lower the seizure threshold; concurrent use substantially increases seizure risk."),
    ("buspirone", "phenelzine", "major", "Buspirone with MAOIs can elevate blood pressure dangerously and contribute to serotonin syndrome."),
    ("fluoxetine", "tamoxifen", "major", "Fluoxetine strongly inhibits CYP2D6, reducing conversion of tamoxifen to its active metabolite endoxifen and potentially decreasing efficacy in breast cancer treatment."),
    ("paroxetine", "tamoxifen", "major", "Paroxetine strongly inhibits CYP2D6, reducing tamoxifen's active metabolite and potentially decreasing antineoplastic efficacy."),
    ("pregabalin", "oxycodone", "major", "Gabapentinoids combined with opioids substantially increase the risk of profound sedation and respiratory depression."),
    ("pregabalin", "hydrocodone", "major", "Concurrent pregabalin and opioids can produce severe CNS and respiratory depression."),
    ("alprazolam", "hydromorphone", "major", "Benzodiazepine plus opioid combinations carry a black-box risk of fatal respiratory depression."),
    ("diazepam", "oxycodone", "major", "Concurrent benzodiazepine and opioid use can cause profound CNS depression and death."),
    ("metronidazole", "alcohol", "major", "Metronidazole inhibits aldehyde dehydrogenase; combination with alcohol causes a disulfiram-like reaction (flushing, vomiting, tachycardia)."),
    ("warfarin", "fluconazole", "major", "Fluconazole inhibits CYP2C9, substantially increasing warfarin's anticoagulant effect and bleeding risk."),
    ("simvastatin", "gemfibrozil", "major", "Gemfibrozil dramatically increases simvastatin exposure and the risk of rhabdomyolysis. Avoid combination."),
    ("colchicine", "clarithromycin", "major", "Clarithromycin inhibits CYP3A4 and P-glycoprotein, markedly increasing colchicine levels with potential for fatal toxicity. Avoid combination."),
    ("methotrexate", "trimethoprim", "major", "Trimethoprim potentiates methotrexate's antifolate effect, risking pancytopenia and severe bone marrow suppression."),
    ("tadalafil", "isosorbide", "major", "PDE5 inhibitors combined with nitrates can cause severe, life-threatening hypotension. Contraindicated."),
    ("vardenafil", "isosorbide", "major", "PDE5 inhibitors with any nitrate are contraindicated due to risk of profound hypotension."),

    # --- Moderate interactions ---
    ("metformin", "alcohol", "moderate", "Alcohol increases the risk of lactic acidosis in patients on metformin and can cause hypoglycemia. Limit alcohol intake."),
    ("lisinopril", "potassium", "moderate", "ACE inhibitors raise serum potassium; concurrent potassium supplements can produce dangerous hyperkalemia. Monitor levels."),
    ("atorvastatin", "fluconazole", "moderate", "Fluconazole inhibits CYP3A4, increasing atorvastatin levels and the risk of myopathy."),
    ("sertraline", "alcohol", "moderate", "Combining SSRIs with alcohol enhances CNS depression and may worsen depressive symptoms."),
    ("alprazolam", "alcohol", "moderate", "Concurrent use produces additive CNS depression, impaired coordination, and serious risk of overdose."),
    ("gabapentin", "alcohol", "moderate", "Alcohol enhances gabapentin's sedative effects and risk of psychomotor impairment."),
    ("quetiapine", "alcohol", "moderate", "Quetiapine plus alcohol produces additive sedation and orthostatic hypotension."),
    ("lisinopril", "spironolactone", "moderate", "ACE inhibitors plus potassium-sparing diuretics can cause hyperkalemia. Monitor potassium and renal function."),
    ("levothyroxine", "calcium", "moderate", "Calcium carbonate binds levothyroxine in the gut, reducing absorption. Separate dosing by 4 hours."),
    ("levothyroxine", "iron", "moderate", "Iron supplements impair levothyroxine absorption. Separate by at least 4 hours and monitor TSH."),
    ("doxycycline", "calcium carbonate", "moderate", "Antacids and calcium products chelate doxycycline, reducing oral absorption. Separate by 2-3 hours."),
    ("clindamycin", "rocuronium", "moderate", "Clindamycin can prolong neuromuscular blockade with nondepolarizing agents."),
    ("furosemide", "gentamicin", "moderate", "Loop diuretics combined with aminoglycosides increase the risk of ototoxicity and nephrotoxicity."),
    ("spironolactone", "lisinopril", "moderate", "Combining potassium-sparing diuretics with ACE inhibitors elevates hyperkalemia risk; monitor potassium."),
    ("prednisone", "naproxen", "moderate", "Corticosteroids and NSAIDs together substantially increase GI ulceration and bleeding risk."),
    ("prednisone", "metformin", "moderate", "Corticosteroids elevate blood glucose, potentially reducing the effectiveness of metformin and other diabetes medications."),
    ("prednisone", "insulin", "moderate", "Corticosteroids antagonize insulin's glucose-lowering effect; insulin dose adjustment may be needed."),
    ("hydroxychloroquine", "azithromycin", "moderate", "Both agents prolong the QT interval; concurrent use raises the risk of torsades de pointes."),
    ("tamsulosin", "sildenafil", "moderate", "Combined alpha-blocker and PDE5 inhibitor use can produce symptomatic hypotension. Stagger doses."),
    ("finasteride", "warfarin", "moderate", "Finasteride may modestly affect warfarin's anticoagulant effect; monitor INR after initiation."),
    ("trazodone", "alcohol", "moderate", "Trazodone and alcohol have additive sedative effects and increase orthostatic hypotension risk."),
    ("lithium", "hydrochlorothiazide", "moderate", "Thiazides reduce renal lithium clearance, raising levels into the toxic range. Monitor lithium closely."),
    ("valproic acid", "aspirin", "moderate", "Aspirin displaces valproate from plasma proteins and inhibits its metabolism, raising free valproate levels."),
    ("lamotrigine", "valproic acid", "moderate", "Valproate inhibits lamotrigine glucuronidation, doubling its half-life. Lamotrigine doses must be halved when added to valproate."),
    ("levetiracetam", "alcohol", "moderate", "Alcohol enhances the CNS-depressant effects of levetiracetam."),
    ("celecoxib", "warfarin", "moderate", "Celecoxib inhibits CYP2C9 and platelet-independent bleeding risk; INR may rise. Monitor closely."),
    ("naproxen", "warfarin", "moderate", "Naproxen increases bleeding risk via platelet inhibition and GI irritation in patients on warfarin."),
    ("aspirin", "clopidogrel", "moderate", "Dual antiplatelet therapy increases bleeding risk; combination is often intentional after stenting but requires monitoring."),
    ("metformin", "topiramate", "moderate", "Topiramate's carbonic anhydrase inhibition combined with metformin increases the risk of metabolic acidosis."),
    ("fluoxetine", "alcohol", "moderate", "Alcohol potentiates SSRI sedation and may worsen depressive symptoms."),
    ("escitalopram", "alcohol", "moderate", "Alcohol enhances CNS depressant effects of escitalopram and may aggravate depression."),
    ("citalopram", "azithromycin", "moderate", "Both prolong the QT interval; combination may increase the risk of arrhythmia."),
    ("amiodarone", "warfarin", "moderate", "Amiodarone inhibits CYP2C9, increasing warfarin's effect; warfarin dose typically needs reduction by 30-50%."),
    ("rifampin", "warfarin", "moderate", "Rifampin induces CYP enzymes, reducing warfarin levels and anticoagulant effect; INR may drop."),
    ("rifampin", "oral contraceptives", "moderate", "Rifampin induces hepatic metabolism, reducing oral contraceptive efficacy. Use a backup method."),
    ("phenytoin", "fluconazole", "moderate", "Fluconazole inhibits CYP2C9, increasing phenytoin levels and the risk of toxicity."),
    ("metoprolol", "fluoxetine", "moderate", "Fluoxetine inhibits CYP2D6, raising metoprolol levels and the risk of bradycardia or hypotension."),
    ("propranolol", "verapamil", "moderate", "Beta blocker plus non-dihydropyridine calcium channel blocker can produce bradycardia and AV block."),
    ("diltiazem", "simvastatin", "moderate", "Diltiazem inhibits CYP3A4, increasing simvastatin levels; limit simvastatin to 10 mg/day."),
    ("atorvastatin", "clarithromycin", "moderate", "Clarithromycin can increase atorvastatin levels; consider holding the statin during the antibiotic course."),
    ("omeprazole", "diazepam", "moderate", "Omeprazole inhibits CYP2C19, prolonging diazepam half-life and enhancing sedation."),
    ("sumatriptan", "sertraline", "moderate", "Combination of triptans with SSRIs may increase the risk of serotonin syndrome."),
    ("losartan", "potassium", "moderate", "Angiotensin receptor blockers raise serum potassium; concurrent supplementation may cause hyperkalemia."),
    ("losartan", "spironolactone", "moderate", "ARBs combined with potassium-sparing diuretics increase hyperkalemia risk; monitor potassium."),
    ("digoxin", "verapamil", "moderate", "Verapamil increases digoxin levels by inhibiting P-glycoprotein; reduce digoxin dose and monitor."),
    ("digoxin", "furosemide", "moderate", "Furosemide-induced hypokalemia potentiates digoxin toxicity; monitor potassium."),
    ("warfarin", "amoxicillin", "moderate", "Broad-spectrum antibiotics can disrupt vitamin K-producing gut flora, modestly raising INR."),
    ("warfarin", "acetaminophen", "moderate", "High or sustained acetaminophen doses can increase INR in patients on warfarin."),
    ("hydrochlorothiazide", "ibuprofen", "moderate", "NSAIDs blunt the antihypertensive and diuretic effects of thiazides and may worsen renal function."),
    ("lisinopril", "ibuprofen", "moderate", "NSAIDs reduce the antihypertensive effect of ACE inhibitors and may impair renal function."),
    ("clopidogrel", "esomeprazole", "moderate", "Esomeprazole inhibits CYP2C19 activation of clopidogrel; consider an alternative PPI such as pantoprazole."),
    ("methotrexate", "naproxen", "moderate", "NSAIDs reduce renal clearance of methotrexate; high-dose methotrexate combinations should be avoided."),
    ("levothyroxine", "ferrous sulfate", "moderate", "Iron salts impair levothyroxine absorption; separate dosing by 4 hours."),
    ("ciprofloxacin", "calcium carbonate", "moderate", "Polyvalent cations chelate fluoroquinolones, reducing absorption. Separate by 2 hours before or 6 hours after."),
    ("ciprofloxacin", "tizanidine", "moderate", "Ciprofloxacin inhibits CYP1A2, markedly elevating tizanidine levels with risk of hypotension and somnolence."),

    # --- Minor interactions ---
    ("ibuprofen", "atorvastatin", "minor", "Mild possible elevation of CK; rarely clinically significant. Monitor for muscle symptoms."),
    ("omeprazole", "magnesium hydroxide", "minor", "Long-term PPI use may modestly reduce magnesium absorption; supplementation rarely needed."),
    ("calcium carbonate", "ferrous sulfate", "minor", "Calcium can modestly reduce iron absorption. Separate dosing by 1-2 hours if both are needed."),
    ("acetaminophen", "alcohol", "minor", "Chronic alcohol use combined with regular acetaminophen modestly increases the risk of hepatotoxicity. Limit to recommended doses."),
    ("cetirizine", "alcohol", "minor", "Cetirizine has minimal sedation but alcohol can produce additive drowsiness in sensitive individuals."),
    ("loratadine", "alcohol", "minor", "Loratadine is non-sedating but rare additive drowsiness with alcohol is possible."),
    ("montelukast", "phenobarbital", "minor", "Phenobarbital may modestly induce montelukast metabolism, slightly reducing exposure."),
    ("doxycycline", "calcium", "minor", "Dairy and calcium products can modestly reduce doxycycline absorption when taken simultaneously."),
    ("ciprofloxacin", "caffeine", "minor", "Ciprofloxacin inhibits caffeine metabolism, potentially enhancing caffeine effects such as jitteriness."),
    ("metformin", "cimetidine", "minor", "Cimetidine modestly reduces renal metformin clearance; clinical significance is generally low."),
    ("famotidine", "ketoconazole", "minor", "H2 blockers raise gastric pH, modestly reducing ketoconazole absorption. Separate dosing when possible."),
    ("aspirin", "ibuprofen", "minor", "Ibuprofen taken before low-dose aspirin can blunt antiplatelet effect; usually managed with timing rather than avoidance."),
    ("simvastatin", "grapefruit", "minor", "Grapefruit juice modestly increases simvastatin exposure; limit intake while on the medication."),
    ("naproxen", "caffeine", "minor", "Combination may slightly enhance analgesic effect; clinically minor."),
    ("pseudoephedrine", "caffeine", "minor", "Additive stimulant effects may produce mild jitteriness or increased heart rate."),
    ("diphenhydramine", "alcohol", "minor", "Additive sedation; effect is usually mild at typical OTC doses."),
    ("ranitidine", "iron", "minor", "Reduced gastric acidity may slightly impair iron absorption; clinically minor."),
    ("aluminum hydroxide", "ciprofloxacin", "minor", "Aluminum binds fluoroquinolones; small reductions in absorption are clinically minor with appropriate timing."),
    ("vitamin k", "warfarin", "minor", "Routine dietary vitamin K does not require avoidance; consistency of intake is more important than absolute amount."),
    ("green tea", "warfarin", "minor", "Green tea contains modest vitamin K and may slightly affect INR; keep intake consistent."),
]


NEWS_DATA = [
    ("FDA Approves New GLP-1 Agonist for Weight Management", "New Drug Approvals", "The U.S. Food and Drug Administration today approved a new GLP-1 receptor agonist for chronic weight management in adults with obesity. The approval was based on phase 3 trials showing significant weight reduction compared with placebo."),
    ("FDA Approves Updated Influenza Vaccines for 2025-2026 Season", "New Drug Approvals", "The FDA has approved updated influenza vaccine formulations for the upcoming flu season, targeting circulating H1N1, H3N2, and B-lineage strains."),
    ("FDA Approves First Generic of Popular Migraine Medication", "New Drug Approvals", "The FDA today approved the first generic version of a widely used CGRP inhibitor for the prevention of migraine, expanding access for millions of patients."),
    ("New SGLT2 Inhibitor Approved for Chronic Kidney Disease", "New Drug Approvals", "The FDA has expanded approval of an SGLT2 inhibitor to include adults with chronic kidney disease, based on trial data showing reduced progression to kidney failure."),
    ("FDA Approves Biosimilar for Common Biologic", "New Drug Approvals", "A new biosimilar to a widely prescribed TNF inhibitor has received FDA approval, offering a lower-cost alternative for patients with autoimmune conditions."),
    ("Study: Statins May Reduce Risk of Severe COVID-19", "Medical", "A large observational study published this week suggests that patients on statin therapy may have a reduced risk of severe outcomes from COVID-19 infection."),
    ("Doctors Caution Against Combining NSAIDs With Blood Thinners", "Medical", "Clinicians are reminding patients of the substantial bleeding risk associated with combining NSAIDs such as ibuprofen and naproxen with anticoagulants like warfarin."),
    ("Researchers Identify New Risk Factors for Type 2 Diabetes", "Medical", "A multi-center study has identified previously unrecognized lifestyle and genetic factors that increase the risk of developing type 2 diabetes."),
    ("Long-term SSRI Use Linked to Bone Density Changes", "Medical", "New research indicates a possible association between long-term SSRI use and changes in bone mineral density in older adults."),
    ("Hospital-acquired Infections Decline With Updated Guidelines", "Medical", "Updated infection-control guidelines have contributed to a notable decline in hospital-acquired infections nationwide."),
    ("FDA Issues Safety Alert on Certain Recalled Blood Pressure Medications", "FDA Alerts", "The FDA has announced a voluntary recall of specific lots of valsartan-containing products due to detection of trace impurities."),
    ("FDA Warns About Unapproved Online Sales of Weight-loss Drugs", "FDA Alerts", "The FDA has issued a public health alert about counterfeit and unapproved versions of popular GLP-1 weight-loss medications sold online."),
    ("FDA Strengthens Boxed Warning for Quinolone Antibiotics", "FDA Alerts", "The FDA has updated boxed warnings on fluoroquinolone antibiotics including ciprofloxacin and levofloxacin to highlight risks of aortic dissection."),
    ("FDA Recalls Eye Drops Due to Contamination Concerns", "FDA Alerts", "Several lots of over-the-counter eye drops have been recalled due to possible bacterial contamination."),
    ("FDA Warns of Counterfeit Ozempic in Distribution Channels", "FDA Alerts", "The FDA has identified counterfeit semaglutide injections in the legitimate U.S. drug supply chain and is investigating."),
    ("Phase 3 Trial Begins for Novel Alzheimer's Disease Therapy", "Clinical Trials", "A pharmaceutical company has launched a global phase 3 clinical trial of a new anti-amyloid antibody for early Alzheimer's disease."),
    ("Clinical Trial Shows Promise for New Long-acting Insulin", "Clinical Trials", "A once-weekly insulin formulation has shown comparable efficacy to daily basal insulin in a phase 3 trial of type 2 diabetes patients."),
    ("Cancer Immunotherapy Trial Reports Encouraging Survival Results", "Clinical Trials", "Updated results from an ongoing phase 3 trial show improved overall survival with a combination immunotherapy regimen for advanced melanoma."),
    ("Researchers Begin Trial of Oral GLP-1 for Obesity", "Clinical Trials", "A new phase 3 trial will evaluate the efficacy and safety of a once-daily oral GLP-1 agonist for chronic weight management."),
    ("Trial Investigates Microbiome Therapy for Recurrent C. difficile", "Clinical Trials", "Investigators are enrolling patients in a phase 3 trial of a live microbiome therapeutic for prevention of recurrent C. difficile infection."),

    # --- FDA Alerts (expanded) ---
    ("FDA Issues Safety Communication About Acetaminophen and Liver Risk", "FDA Alerts", "The U.S. Food and Drug Administration today issued a renewed Drug Safety Communication reminding clinicians and consumers about the risk of severe liver injury associated with acetaminophen at doses above 4 grams per day in adults.\n\nThe agency reviewed adverse event reports from the past three years and identified hundreds of cases of acute liver failure, many of which involved unintentional overdose from concurrent use of multiple acetaminophen-containing products. Combination cold-and-flu remedies, prescription opioid-acetaminophen tablets, and over-the-counter pain relievers were frequently implicated.\n\nThe FDA recommends that healthcare providers review a patient's full medication list before prescribing additional acetaminophen products, with particular attention to patients who consume alcohol regularly or who have pre-existing liver disease. Consumers are urged to read the active ingredients panel on every product and to avoid exceeding 3 grams per day without medical supervision.\n\nLabeling updates affecting prescription combination products will be implemented within the next six months. The FDA continues to evaluate whether further regulatory action is warranted."),
    ("FDA Approves New Label Warnings for SGLT2 Inhibitor Class", "FDA Alerts", "The FDA has required updated labeling across the SGLT2 inhibitor class to highlight the risk of euglycemic diabetic ketoacidosis, a condition in which patients develop ketoacidosis despite blood glucose levels that appear near-normal.\n\nThe class, which includes dapagliflozin, empagliflozin, and canagliflozin, has been the subject of mounting postmarket reports describing ketoacidosis presentations that delay diagnosis because patients lack the marked hyperglycemia clinicians expect. Several cases occurred perioperatively or during acute illness.\n\nThe updated Warnings and Precautions section advises clinicians to assess for ketoacidosis in any patient on an SGLT2 inhibitor presenting with nausea, vomiting, abdominal pain, fatigue, or shortness of breath, regardless of glucose level. The label also recommends withholding the medication for at least three days prior to scheduled surgery.\n\nThe FDA emphasized that the cardiovascular and renal benefits of SGLT2 inhibitors continue to outweigh the risks for appropriately selected patients."),
    ("FDA Alerts Providers About Ongoing Shortage of Amoxicillin Oral Suspension", "FDA Alerts", "The FDA has added amoxicillin oral suspension to its drug shortage list, citing supply constraints affecting multiple manufacturers heading into the respiratory illness season.\n\nPediatric formulations are most affected, and the agency is working with manufacturers to expedite production. In the interim, the FDA suggests clinicians consider therapeutic alternatives such as amoxicillin tablets or capsules where appropriate, compounded suspensions from licensed pharmacies, or alternative first-line antibiotics for specific indications.\n\nPharmacists are encouraged to check wholesaler availability daily and to communicate proactively with prescribers when substitutions are required. The FDA reiterated that the shortage does not reflect a safety concern with the drug itself."),
    ("Recall Notice: Multiple Lots of Levothyroxine Recalled Due to Subpotency", "FDA Alerts", "A manufacturer has initiated a voluntary nationwide recall of several lots of levothyroxine sodium tablets after stability testing revealed the product may be subpotent prior to its labeled expiration date.\n\nSubpotent levothyroxine can result in inadequate thyroid hormone replacement, with potential consequences including fatigue, weight gain, cold intolerance, and, in pregnant patients, adverse fetal outcomes. No serious adverse events have been confirmed at this time.\n\nPatients should not stop taking their medication abruptly but should contact their pharmacy to determine whether their supply is affected and to arrange replacement. Healthcare providers are advised to recheck TSH levels in patients who report new or worsening hypothyroid symptoms after using a recalled lot."),
    ("FDA Strengthens Cardiac Warning for Azithromycin", "FDA Alerts", "The FDA has strengthened the cardiac warning on azithromycin labeling following a comprehensive review of QT-interval data and reports of fatal arrhythmias in at-risk patients.\n\nThe updated warning more clearly identifies populations at elevated risk, including patients with known QT prolongation, hypokalemia, hypomagnesemia, clinically significant bradycardia, or concurrent use of Class IA or III antiarrhythmics. Clinicians are urged to consider alternative antibiotics for these patients when feasible.\n\nThe agency stressed that azithromycin remains an important option for many infections and that the absolute risk of serious arrhythmia is low in patients without predisposing conditions."),
    ("Safety Communication: Long-Term Proton Pump Inhibitor Use Linked to Fracture Risk", "FDA Alerts", "The FDA today reiterated its longstanding safety communication regarding the association between long-term, high-dose proton pump inhibitor use and an increased risk of fractures of the hip, wrist, and spine.\n\nReview of additional observational data and meta-analyses continues to support the association, particularly for users of more than one year and those over age 50. The mechanism is not fully established but may involve reduced calcium absorption and altered bone remodeling.\n\nThe agency recommends that clinicians prescribe the lowest effective dose for the shortest duration consistent with the condition being treated and periodically reassess the ongoing need for therapy. Over-the-counter PPI products remain limited to 14-day courses up to three times per year."),
    ("FDA Requires New Boxed Warning for Janus Kinase Inhibitor Class", "FDA Alerts", "The FDA has required a new boxed warning across the Janus kinase (JAK) inhibitor class addressing increased risks of serious cardiovascular events, malignancy, thrombosis, and mortality observed in a large postmarket safety trial.\n\nThe boxed warning applies to tofacitinib, baricitinib, and upadacitinib when used for chronic inflammatory conditions. The FDA also limited certain indications to patients who have had an inadequate response or intolerance to one or more TNF blockers.\n\nProviders should discuss the updated risk profile with patients prior to initiation and document an informed treatment decision. Patients currently on JAK inhibitors should not discontinue therapy without consulting their prescriber."),
    ("MedWatch: Lamotrigine Associated With Severe Skin Reactions Including Stevens-Johnson Syndrome", "FDA Alerts", "The FDA's MedWatch program has issued a reminder regarding the risk of life-threatening cutaneous reactions, including Stevens-Johnson syndrome and toxic epidermal necrolysis, associated with lamotrigine, particularly during the first two to eight weeks of therapy.\n\nRisk is increased with rapid dose titration, concurrent valproate use, and prior history of antiepileptic drug-related rash. Pediatric patients appear to be at higher relative risk than adults.\n\nProviders are reminded to follow the recommended titration schedule precisely, to counsel patients to report any rash immediately, and to discontinue lamotrigine at the first sign of rash unless clearly unrelated to the drug."),
    ("FDA Drug Safety Communication: NSAIDs and Risk of Renal Impairment in Older Adults", "FDA Alerts", "The FDA has issued an updated Drug Safety Communication regarding the risk of acute kidney injury and chronic renal impairment in older adults taking nonsteroidal anti-inflammatory drugs, particularly at higher doses or for prolonged periods.\n\nThe communication highlights additional risk in patients with pre-existing chronic kidney disease, heart failure, cirrhosis, volume depletion, or concomitant use of ACE inhibitors, ARBs, or diuretics-the so-called 'triple whammy' combination.\n\nClinicians are encouraged to consider acetaminophen, topical NSAIDs, or non-pharmacologic strategies where appropriate, and to monitor renal function and blood pressure in patients who require systemic NSAID therapy."),
    ("Postmarket Drug Safety Information: Citalopram and QT Prolongation", "FDA Alerts", "The FDA has reaffirmed prescribing restrictions for citalopram based on continued postmarket evidence of dose-dependent QT-interval prolongation.\n\nThe maximum recommended dose remains 40 mg per day for most adults and 20 mg per day for patients older than 60, those with hepatic impairment, poor CYP2C19 metabolizers, or those taking concurrent CYP2C19 inhibitors. Doses above these limits are not recommended in any population.\n\nProviders should obtain a baseline ECG in patients with cardiovascular risk factors and correct hypokalemia and hypomagnesemia before initiation."),

    # --- New Drug Approvals (expanded) ---
    ("FDA Approves Lecanemab for Early Alzheimer's Disease", "New Drug Approvals", "The FDA has granted traditional approval to lecanemab, an anti-amyloid monoclonal antibody, for the treatment of mild cognitive impairment or mild dementia due to Alzheimer's disease in patients with confirmed amyloid pathology.\n\nApproval was based on a confirmatory phase 3 trial that demonstrated a statistically significant slowing of clinical decline on the Clinical Dementia Rating-Sum of Boxes scale over 18 months. Imaging studies showed substantial reductions in cerebral amyloid plaque burden.\n\nThe label carries a boxed warning for amyloid-related imaging abnormalities (ARIA), and prescribers must enroll in a structured monitoring program that includes serial MRI scans during the initial dosing period."),
    ("FDA Grants Breakthrough Therapy Designation to Novel Gene Therapy for Sickle Cell Disease", "New Drug Approvals", "The FDA has granted Breakthrough Therapy Designation to an investigational gene therapy for severe sickle cell disease, citing preliminary trial data showing a meaningful reduction in vaso-occlusive crises.\n\nThe one-time therapy uses CRISPR-based editing of autologous hematopoietic stem cells to reactivate fetal hemoglobin production. Patients in the lead-in cohort have remained free of severe pain crises for more than two years following infusion.\n\nThe designation will expedite the FDA's review of the eventual Biologics License Application and provides for closer agency engagement during late-stage development."),
    ("FDA Approves First Generic of Suboxone Sublingual Film", "New Drug Approvals", "The FDA has approved the first generic version of buprenorphine/naloxone sublingual film for the maintenance treatment of opioid use disorder, expanding affordable access to a medication central to outpatient addiction care.\n\nThe approval follows a rigorous review of bioequivalence and dissolution data. Public health officials welcomed the expanded supply, citing persistent gaps in medication for opioid use disorder despite the elimination of the X-waiver requirement.\n\nThe generic product is expected to reach pharmacies within the next quarter."),
    ("FDA Approves Adalimumab Biosimilar, Bringing Cost Relief", "New Drug Approvals", "A new adalimumab biosimilar has received FDA approval and is expected to launch later this year, joining a growing market of adalimumab competitors.\n\nThe biosimilar is approved for all indications of the reference product, including rheumatoid arthritis, psoriatic arthritis, ankylosing spondylitis, Crohn's disease, ulcerative colitis, plaque psoriasis, and hidradenitis suppurativa. Interchangeability designation will require additional switching study data currently under review.\n\nPayer formulary placement and rebate dynamics will largely determine the actual savings realized by patients."),
    ("FDA Approves New Indication: Semaglutide for Reduction of Cardiovascular Events", "New Drug Approvals", "The FDA has approved a new indication for semaglutide injection: reduction of major adverse cardiovascular events in adults with established cardiovascular disease and either obesity or overweight.\n\nThe approval is based on a large cardiovascular outcomes trial showing a 20% relative reduction in the composite endpoint of cardiovascular death, nonfatal myocardial infarction, and nonfatal stroke versus placebo over a median follow-up of about three years.\n\nThe new indication marks the first time a weight-management medication has demonstrated and obtained labeling for cardiovascular benefit independent of diabetes status."),
    ("FDA Approves Cystic Fibrosis Triple Combination Therapy for Children Ages 2-5", "New Drug Approvals", "The FDA has approved the elexacaftor/tezacaftor/ivacaftor combination for pediatric patients with cystic fibrosis aged 2 through 5 years who have at least one F508del mutation or another responsive mutation.\n\nThe pediatric approval was supported by safety and pharmacokinetic data from an open-label trial, in which young children showed sweat chloride reductions consistent with those previously observed in older patients.\n\nClinicians emphasize that early initiation of CFTR modulator therapy may meaningfully alter the long-term trajectory of lung disease."),
    ("Accelerated Approval Granted to New Therapy for Duchenne Muscular Dystrophy", "New Drug Approvals", "The FDA has granted accelerated approval to a new exon-skipping therapy for ambulatory pediatric patients with Duchenne muscular dystrophy and a confirmed mutation amenable to exon 53 skipping.\n\nApproval was based on a surrogate endpoint-an increase in dystrophin protein-considered reasonably likely to predict clinical benefit. Continued approval is contingent on results from an ongoing confirmatory trial assessing motor function outcomes.\n\nThe therapy is administered as weekly intravenous infusions and joins a growing class of mutation-specific options for this devastating childhood disease."),
    ("FDA Approves Fixed-Dose Combination of Empagliflozin and Linagliptin", "New Drug Approvals", "The FDA has approved a single-tablet fixed-dose combination of empagliflozin and linagliptin for use as an adjunct to diet and exercise in adults with type 2 diabetes.\n\nThe combination pairs an SGLT2 inhibitor with a DPP-4 inhibitor, providing complementary mechanisms of action and the convenience of once-daily dosing. Approval was supported by trials demonstrating significant A1c reductions versus either component alone.\n\nThe fixed-dose product is not indicated for type 1 diabetes or for treatment of diabetic ketoacidosis."),

    # --- Medical (expanded) ---
    ("Large Trial Finds Empagliflozin Reduces Cardiovascular Events by 14% in High-Risk Patients", "Medical", "A randomized trial of nearly 7,000 patients with type 2 diabetes and established cardiovascular disease has found that empagliflozin reduced the composite endpoint of cardiovascular death, nonfatal myocardial infarction, and nonfatal stroke by 14% compared with placebo over a median 3.1 years of follow-up.\n\nMortality benefits were driven primarily by a 38% reduction in cardiovascular death and a 35% reduction in hospitalization for heart failure. The renal composite endpoint was also improved.\n\nThe results, replicated in subsequent trials of the SGLT2 inhibitor class, have transformed the management of type 2 diabetes in patients with cardiovascular and renal comorbidities."),
    ("Research: Long-Term ACE Inhibitor Use May Affect Kidney Function in Subset of Patients", "Medical", "A large observational cohort study has identified a subset of patients in whom long-term ACE inhibitor use is associated with a gradual decline in estimated glomerular filtration rate, particularly among patients with baseline CKD stage 3b or higher.\n\nThe authors caution that the observational design cannot establish causation and note that the cardioprotective and antiproteinuric benefits of ACE inhibition remain well established for most patients.\n\nClinicians are reminded to monitor renal function and potassium periodically and to individualize therapy in patients with advanced kidney disease."),
    ("Metformin Shows Reduced Cancer Incidence in Large Diabetes Cohort", "Medical", "A pooled analysis of long-term diabetes registry data has found that patients with type 2 diabetes treated with metformin had a modestly lower incidence of several common cancers, including colorectal, breast, and pancreatic cancer, compared with patients on other glucose-lowering therapies.\n\nThe association persisted after adjustment for body mass index, smoking status, and duration of diabetes, though residual confounding cannot be excluded. Several proposed mechanisms, including AMPK activation and reduced insulin/IGF-1 signaling, remain under investigation.\n\nDespite intriguing observational data, metformin is not currently recommended for cancer prevention outside of clinical trials."),
    ("Statin Therapy Reduces Stroke Risk Even Among Patients With Low Baseline LDL", "Medical", "Secondary analyses of a large primary prevention trial suggest that statin therapy reduces ischemic stroke risk even among patients with LDL cholesterol below 100 mg/dL at baseline.\n\nThe benefit was consistent across age groups and was apparent within the first two years of therapy. The authors hypothesize that pleiotropic effects on endothelial function and plaque stabilization may contribute beyond LDL lowering alone.\n\nGuidelines continue to recommend statin therapy decisions based on absolute cardiovascular risk rather than LDL threshold alone."),
    ("GLP-1 Receptor Agonists Show Sustained Weight Loss Benefits at Two Years", "Medical", "Long-term follow-up data from extension studies of GLP-1 receptor agonist trials show that the substantial weight loss observed in initial trials is largely maintained at two years among patients who continue therapy, with mean weight reductions of 12-17% from baseline depending on the agent and dose.\n\nDiscontinuation is associated with substantial regain, underscoring that obesity is a chronic disease requiring chronic management. Common side effects-nausea, vomiting, and diarrhea-tend to diminish over time but may limit tolerability in some patients.\n\nAccess and affordability remain significant barriers for many patients eligible for therapy."),
    ("New Research on Antidepressant Efficacy Across Patient Subgroups", "Medical", "A network meta-analysis encompassing more than 500 trials has provided updated comparative-efficacy estimates for second-generation antidepressants in adults with major depressive disorder.\n\nWhile differences between agents were modest in head-to-head comparisons, escitalopram and sertraline emerged as favorable options in terms of the balance between efficacy and acceptability. Effects in subgroups defined by symptom severity and prior treatment response varied meaningfully.\n\nThe authors emphasize that antidepressant selection should remain individualized based on patient comorbidities, side effect profile, drug interactions, and patient preference."),
    ("Antibiotics and the Gut Microbiome: What Recent Research Shows", "Medical", "A growing body of research has documented that even short courses of broad-spectrum antibiotics can produce lasting changes in the gut microbiome, with full recovery sometimes taking months.\n\nClinical correlates of antibiotic-induced dysbiosis under active investigation include Clostridioides difficile infection, antibiotic-associated diarrhea, and potential downstream effects on immune and metabolic function.\n\nThe findings reinforce stewardship principles: prescribe antibiotics only when indicated, choose the narrowest-spectrum effective agent, and use the shortest duration supported by evidence."),
    ("Opioid Crisis Update: Revised Prescribing Guidelines Aim to Reduce Misuse Without Undertreatment", "Medical", "Updated CDC guidelines for opioid prescribing emphasize a more flexible, individualized approach to pain management compared with earlier iterations, while retaining a strong recommendation to maximize nonopioid and nonpharmacologic therapies first.\n\nThe revisions address concerns that prior numeric thresholds were sometimes applied rigidly, leading to abrupt tapers and inadequately treated pain in patients on stable long-term therapy. Shared decision-making and careful monitoring remain central.\n\nThe guidelines do not apply to active cancer treatment, palliative care, or end-of-life care."),
    ("Cannabis and Drug Interactions: What Patients Should Know", "Medical", "Pharmacologists are increasingly raising awareness of clinically meaningful interactions between cannabis products and prescription medications, particularly those metabolized by CYP3A4, CYP2C9, and CYP2C19.\n\nCannabidiol (CBD) is a notable inhibitor of several CYP enzymes and can elevate concentrations of clobazam, warfarin, tacrolimus, and others. THC may add to sedation from benzodiazepines, opioids, and certain antidepressants.\n\nPatients are encouraged to disclose all cannabis use-medical or recreational-to their prescribers and pharmacists so that interaction risks can be evaluated."),
    ("Proton Pump Inhibitors: Weighing Benefits and Risks for Long-Term Use", "Medical", "Long-term proton pump inhibitor (PPI) therapy provides important benefit for patients with severe reflux, Barrett's esophagus, and risk factors for upper GI bleeding, but observational data have linked extended use to a range of potential harms including B12 deficiency, hypomagnesemia, fractures, and certain infections.\n\nThe absolute increase in risk for any individual outcome is small, but the cumulative effect across millions of long-term users is clinically meaningful. Periodic reassessment of the indication is appropriate.\n\nIn many patients with uncomplicated reflux, dose reduction, on-demand dosing, or transition to H2 blockers may be viable strategies."),
    ("COVID-19 Treatment Updates: Antiviral Effectiveness in 2025", "Medical", "Updated effectiveness data from real-world studies confirm that nirmatrelvir-ritonavir reduces hospitalization and death among high-risk outpatients with COVID-19, though absolute benefit is smaller in vaccinated patients than was observed in the original placebo-controlled trial.\n\nDrug-drug interactions, particularly with statins, antiarrhythmics, and immunosuppressants, continue to require careful review prior to prescribing. Remdesivir remains an option for hospitalized patients and some high-risk outpatients who cannot take nirmatrelvir-ritonavir.\n\nMonoclonal antibody therapies have largely fallen out of use due to loss of activity against currently circulating variants."),
    ("ADHD Medication Shortages: Causes and What Patients Should Do", "Medical", "Persistent shortages of stimulant medications used to treat attention-deficit/hyperactivity disorder continue to disrupt care for many patients, with shortages reflecting a combination of increased demand, manufacturing constraints, and DEA quota limitations on controlled substances.\n\nThe FDA and DEA have taken several steps to expand supply, but patients and prescribers are encouraged to plan ahead, call pharmacies in advance to confirm stock, and discuss alternative formulations or non-stimulant therapies where clinically appropriate.\n\nAbrupt discontinuation of stimulants is generally not associated with physiologic withdrawal, but may produce a return of ADHD symptoms that affect daily functioning."),

    # --- Clinical Trials (expanded) ---
    ("Phase 3 Trial of Tirzepatide Shows Substantial Weight Loss in Patients Without Diabetes", "Clinical Trials", "A 72-week phase 3 trial of tirzepatide in adults with obesity or overweight and at least one weight-related comorbidity has reported mean weight reductions of approximately 20% at the highest dose, with concurrent improvements in cardiometabolic risk factors.\n\nThe most common adverse events were gastrointestinal-nausea, diarrhea, and constipation-which were typically transient and dose-related. Trial discontinuation due to adverse events was modest.\n\nThe results expand the evidence base supporting GIP/GLP-1 dual agonism as a strategy for chronic weight management."),
    ("Combination Therapy Outperforms Standard of Care in Advanced Renal Cell Carcinoma Trial", "Clinical Trials", "A phase 3 trial evaluating a combination of an immune checkpoint inhibitor plus a tyrosine kinase inhibitor has reported improved progression-free survival and overall response rate compared with sunitinib monotherapy in patients with previously untreated advanced renal cell carcinoma.\n\nGrade 3 or higher adverse events were more frequent with the combination, and discontinuation rates were correspondingly higher. Patient selection and toxicity management will be key considerations in adoption.\n\nThe findings are expected to inform updated treatment guidelines for advanced renal cell carcinoma."),
    ("Landmark NEJM Trial Demonstrates Dapagliflozin Benefit in Heart Failure With Preserved Ejection Fraction", "Clinical Trials", "Results published in the New England Journal of Medicine from a large randomized trial show that dapagliflozin reduced the composite primary endpoint of worsening heart failure or cardiovascular death in patients with heart failure and preserved or mildly reduced ejection fraction.\n\nBenefit was consistent across ejection fraction subgroups and irrespective of diabetes status. Renal endpoints and quality-of-life measures also favored dapagliflozin.\n\nThe trial adds to a growing body of evidence supporting SGLT2 inhibitors as foundational therapy across the full spectrum of heart failure."),
    ("Personalized Dosing of Vancomycin Improves Outcomes in Critically Ill Patients", "Clinical Trials", "A pragmatic randomized trial comparing AUC-guided personalized dosing of vancomycin with traditional trough-based dosing in critically ill adults has reported reduced rates of acute kidney injury and improved early target attainment.\n\nThe AUC-guided strategy used Bayesian software-assisted dose adjustment from limited blood samples. Implementation required pharmacy infrastructure and clinician training but did not increase length of stay.\n\nProfessional societies have increasingly endorsed AUC-based monitoring for vancomycin, and this trial provides prospective support for the approach."),
    ("Clinical Data Supports Expanded Use of Direct Oral Anticoagulants in Elderly Patients", "Clinical Trials", "An age-stratified analysis of a large direct oral anticoagulant (DOAC) trial has reported favorable efficacy and safety in patients aged 75 and older with nonvalvular atrial fibrillation, with reduced rates of intracranial hemorrhage compared with warfarin.\n\nThe analysis controlled for baseline frailty, renal function, and concurrent antiplatelet use. The authors note that careful dose selection-particularly accounting for renal impairment and drug interactions-remains essential in older adults.\n\nThe findings support continued use of DOACs as first-line anticoagulants in most elderly patients with atrial fibrillation."),
    ("Gene Therapy Combined With Enzyme Replacement Shows Promise in Pompe Disease Trial", "Clinical Trials", "Interim results from an early-phase trial combining adeno-associated virus-mediated gene therapy with reduced-frequency enzyme replacement therapy in patients with late-onset Pompe disease have reported improvements in respiratory function and biomarkers of disease activity.\n\nThe combination approach is designed to provide sustained enzyme expression while bridging the early treatment period with conventional enzyme replacement. Larger studies are planned to confirm durability and to refine dosing.\n\nThe trial illustrates an emerging trend of combining gene-based therapies with established treatments to optimize patient outcomes."),

    # --- Health (new category) ---
    ("Understanding Your Prescription: What Beta-Blockers Do and How They Work", "Health", "Beta-blockers are a widely prescribed class of medications used to treat conditions including high blood pressure, certain abnormal heart rhythms, heart failure, angina, and migraine prophylaxis.\n\nThe medications work by blocking the action of adrenaline and similar hormones at beta-adrenergic receptors, slowing the heart rate and reducing the force of cardiac contraction. Different beta-blockers have differing selectivity for various receptor subtypes, which affects their side effect profiles and choice for specific conditions.\n\nCommon side effects include fatigue, cold extremities, and, less commonly, depressed mood or sexual dysfunction. Beta-blockers should generally not be stopped abruptly, especially in patients with coronary artery disease, as rebound effects can occur."),
    ("Drug-Food Interactions: Common Combinations to Avoid", "Health", "Many widely used medications can interact meaningfully with foods or beverages, sometimes producing unexpected changes in drug effect or risk of side effects.\n\nGrapefruit juice can elevate blood levels of certain statins, calcium channel blockers, and immunosuppressants by inhibiting intestinal CYP3A4. Leafy greens high in vitamin K can reduce the effectiveness of warfarin if consumed inconsistently. Tyramine-containing foods such as aged cheeses can produce dangerous blood pressure elevations in patients taking MAO inhibitors.\n\nPatients are encouraged to ask their pharmacist about food interactions when starting any new medication, and to maintain consistent dietary patterns when on warfarin or other interaction-prone drugs."),
    ("Medication Adherence: Practical Strategies to Never Miss a Dose", "Health", "Suboptimal medication adherence is among the most common preventable causes of poor outcomes in chronic disease, accounting for substantial avoidable morbidity and healthcare cost.\n\nPractical strategies that have been shown to improve adherence include using pill organizers, setting daily phone reminders, pairing medication doses with established daily routines, consolidating to once-daily formulations when available, and using automatic refill or 90-day mail-order programs.\n\nPatients should communicate openly with their providers about barriers to taking medication-cost, side effects, complexity of the regimen, or doubts about effectiveness-so that adjustments can be made before adherence problems lead to worsening disease."),
    ("Polypharmacy Risks: When Multiple Medications Become Dangerous", "Health", "Polypharmacy, generally defined as the concurrent use of five or more medications, becomes increasingly common with age and the accumulation of chronic conditions. The risk of clinically significant drug-drug interactions, additive side effects, and prescribing cascades rises sharply with each added medication.\n\nPeriodic comprehensive medication reviews-sometimes called 'brown bag' visits when patients bring all of their medications including over-the-counter products and supplements-can identify deprescribing opportunities. Tools such as the Beers Criteria highlight medications that are potentially inappropriate in older adults.\n\nThe goal is not necessarily fewer medications but the right medications, used at the right doses, for the right durations."),
    ("Medication Safety During Pregnancy: What Is Safe and What Is Not", "Health", "Pregnancy creates physiologic changes that can alter drug absorption, distribution, metabolism, and excretion, and many medications cross the placenta and can affect the developing fetus.\n\nSome medications-folic acid, levothyroxine, certain antihypertensives, and many antibiotics-are safe and important during pregnancy. Others-warfarin, ACE inhibitors, ARBs, methotrexate, isotretinoin, and several antiepileptic drugs-are known teratogens and should generally be avoided.\n\nWomen of reproductive age taking chronic medications should discuss preconception planning with their provider, as some medication changes are best made before conception. Decisions during pregnancy should balance the risk of medication exposure against the risk of untreated maternal disease."),
    ("How to Safely Discontinue SSRIs Without Withdrawal Symptoms", "Health", "Abrupt discontinuation of selective serotonin reuptake inhibitors (SSRIs)-particularly paroxetine and venlafaxine-can produce a discontinuation syndrome characterized by flu-like symptoms, sensory disturbances ('brain zaps'), dizziness, irritability, and sleep disturbance.\n\nA gradual taper over several weeks, with smaller dose reductions toward the end of the taper, generally allows discontinuation with minimal symptoms. Hyperbolic tapering using compounded smaller doses or liquid formulations may be appropriate for patients who experience symptoms with conventional tapering.\n\nDiscontinuation should be undertaken in collaboration with the prescriber and ideally with monitoring for return of depressive or anxiety symptoms."),
    ("Generic vs. Brand-Name Drugs: Are They Really the Same?", "Health", "FDA-approved generic medications contain the same active ingredient, strength, dosage form, and route of administration as their brand-name counterparts, and must demonstrate bioequivalence-meaning comparable rate and extent of absorption-within tightly defined statistical limits.\n\nFor the vast majority of medications, generic and brand-name products are clinically interchangeable. A small number of agents with narrow therapeutic indices-such as warfarin, levothyroxine, and certain antiepileptic drugs-warrant additional caution, and some patients may notice differences when switching among products from different manufacturers.\n\nGenerics typically cost 80-85% less than the brand-name equivalent and account for the majority of prescriptions filled in the United States."),
    ("Pill Splitting: Which Medications Can Safely Be Cut in Half?", "Health", "Pill splitting can be a reasonable way to reduce medication cost when prescribers and patients use it appropriately. Tablets that are scored, immediate-release, and not enteric-coated are generally suitable for splitting.\n\nMedications that should not be split include extended- or controlled-release products, enteric-coated tablets, capsules, sublingual products, and many oncology and hormonal therapies, as splitting can alter pharmacokinetics or expose the user to hazardous drug residues.\n\nPatients considering pill splitting should ask their pharmacist for guidance and use a dedicated pill splitter to improve accuracy."),
]


REVIEW_TEMPLATES = [
    ("Worked great for my condition", 9, "I was prescribed this for {cond} and have had excellent results. Minimal side effects so far. Highly recommend talking to your doctor about this option."),
    ("Took a while to kick in", 7, "It took about 4 weeks before I really noticed a difference treating my {cond}. Once it started working, the effect has been consistent. Some mild side effects at first."),
    ("Game changer", 10, "This medication has been a game changer for managing my {cond}. I feel like myself again after years of struggling. The side effects were minimal for me."),
    ("Not for me", 3, "Tried this for {cond} for 6 weeks and the side effects outweighed the benefits. Switched to something else. Everyone reacts differently though."),
    ("Mixed feelings", 5, "Some days it helps with my {cond}, other days less so. Side effects include some drowsiness. Talk with your doctor about whether this fits your situation."),
    ("Effective but watch dosage", 8, "Effective treatment for {cond}, but you really need to follow dosing instructions carefully. I had to adjust mine with my doctor's help."),
    ("Worked for a while", 6, "Helped with my {cond} for about a year, then I felt the effects wear off. Doctor is adjusting my treatment plan."),
    ("Best medication I've tried", 10, "Out of several medications I've tried for {cond}, this has been the most effective with the fewest side effects. Quality of life vastly improved."),
    ("Cautious recommendation", 7, "It works for my {cond} but the cost is significant. Insurance covered most of it. Be sure to discuss generics."),
    ("Side effects too much", 2, "The side effects were too disruptive for my daily life, even though it did help with {cond}. Discontinued after a few weeks."),
    ("Changed my life", 10, "After years of struggling with {cond}, this medication has truly changed my life. I feel like a completely different person and can finally enjoy daily activities again."),
    ("Minimal side effects", 9, "Been taking this for treating {cond} and it works great with very minimal side effects. Much better than the previous medication I was on."),
    ("Gradual improvement", 7, "It took several weeks before I noticed any improvement in my {cond}, but once it kicked in, the difference was noticeable. Staying patient was key."),
    ("Mixed results", 5, "This drug helped somewhat with my {cond} but I'm still experiencing breakthrough symptoms. My doctor and I are still adjusting the dosage."),
    ("Difficult adjustment period", 6, "The first two weeks treating {cond} were rough with side effects, but things settled down and now it seems to be working. Stick with it if you can."),
    ("Better than expected", 8, "I was skeptical but this has exceeded my expectations for managing {cond}. Following up with my doctor regularly has made all the difference."),
    ("Not right for me", 3, "Unfortunately this medication wasn't a good fit for my {cond}. I experienced too many side effects and had to discontinue. Everyone is different."),
    ("Consistent results", 9, "Very reliable medication. My {cond} has been under consistent control since starting this treatment. My doctor is pleased with my lab results."),
    ("Insurance hassle but worth it", 8, "Had some trouble getting this covered for {cond} but my doctor fought for it. Now that I'm on it, I understand why - it works really well."),
    ("Mild but effective", 7, "Nothing dramatic but steadily effective for my {cond}. Fewer side effects than alternatives I've tried. Would recommend discussing with your doctor."),
]


BENCHMARK_USERS = [
    {"email": "alice.j@test.com", "username": "alice_j", "password": "TestPass123!"},
    {"email": "bob.c@test.com", "username": "bob_c", "password": "TestPass123!"},
    {"email": "carol.d@test.com", "username": "carol_d", "password": "TestPass123!"},
    {"email": "david.k@test.com", "username": "david_k", "password": "TestPass123!"},
]


# ---------------------------------------------------------------------------
# OpenFDA fetch
# ---------------------------------------------------------------------------
def fetch_openfda_label(generic):
    """Fetch label info from OpenFDA. Returns dict or None on any failure."""
    if not HAS_REQUESTS:
        return None
    try:
        q = generic.replace(" ", "+")
        url = f"https://api.fda.gov/drug/label.json?search=openfda.generic_name:{q}&limit=1"
        r = requests.get(url, timeout=4)
        if r.status_code != 200:
            return None
        data = r.json()
        results = data.get("results", [])
        if not results:
            return None
        return results[0]
    except Exception:
        return None


def first(text_field):
    if not text_field:
        return None
    if isinstance(text_field, list):
        return text_field[0] if text_field else None
    return str(text_field)


def truncate(text, n=2400):
    if not text:
        return text
    text = str(text).strip()
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + "..."


def synthetic_content(generic, cls_name, conditions):
    """Generate realistic synthetic content when OpenFDA isn't available."""
    cond_text = ", ".join(conditions) if conditions else "various medical conditions"
    return {
        "description": f"{generic.capitalize()} is a {cls_name.lower()} medication used to treat {cond_text}. It works by addressing the underlying biological processes associated with these conditions.",
        "uses": f"{generic.capitalize()} is indicated for the treatment of {cond_text}. Your doctor may prescribe this medication for other purposes not listed here. Always follow your healthcare provider's instructions regarding indications and proper use.",
        "warnings": f"Do not use {generic} if you are allergic to it or to similar medications. Tell your doctor about all your medical conditions, especially kidney or liver problems, heart disease, and any history of allergic reactions. Inform your doctor if you are pregnant or breastfeeding. Stop taking {generic} and contact your doctor immediately if you experience severe allergic reactions, unusual bleeding, severe abdominal pain, or signs of a serious skin reaction.",
        "dosage": f"The dose of {generic} should be individualized based on the patient's condition, age, and response to therapy. Follow the directions on your prescription label. Do not take more or less than prescribed. If you miss a dose, take it as soon as you remember. Do not double up on doses.",
        "side_effects": f"Common side effects of {generic} may include headache, nausea, dizziness, drowsiness, and gastrointestinal upset. Less common but serious side effects include allergic reactions (rash, swelling, difficulty breathing), changes in mood or behavior, and unusual bleeding. Contact your healthcare provider if any side effect persists or worsens.",
        "interactions_text": f"{generic.capitalize()} can interact with many other medications. Tell your doctor about all prescription and over-the-counter medications, vitamins, and herbal supplements you take. Pay particular attention to interactions with anticoagulants, NSAIDs, antidepressants, and certain antibiotics.",
    }


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------
def seed_drug_classes():
    existing = {c.name for c in DrugClass.query.all()}
    for name, desc in DRUG_CLASSES:
        if name in existing:
            continue
        db.session.add(DrugClass(name=name, slug=slugify(name), description=desc))
    db.session.commit()


def seed_conditions():
    existing = {c.slug for c in Condition.query.all()}
    for slug, name, desc in CONDITIONS_DATA:
        if slug in existing:
            continue
        db.session.add(Condition(name=name, slug=slug, description=desc))
    db.session.commit()


def seed_drugs():
    existing = {d.generic_name for d in Drug.query.all()}
    cls_by_name = {c.name: c.id for c in DrugClass.query.all()}
    featured_targets = {"ibuprofen", "metformin", "lisinopril", "sertraline", "atorvastatin", "semaglutide", "amoxicillin", "levothyroxine"}
    for entry in DRUGS_DATA:
        gname, cname, avail, csa, pron, brands, conds = entry
        if gname in existing:
            continue
        # Try OpenFDA first, fall back to synthetic.
        openfda = fetch_openfda_label(gname)
        if openfda:
            uses = truncate(first(openfda.get("indications_and_usage")))
            warn = truncate(first(openfda.get("warnings") or openfda.get("warnings_and_cautions")))
            dose = truncate(first(openfda.get("dosage_and_administration")))
            adv = truncate(first(openfda.get("adverse_reactions")))
            inter = truncate(first(openfda.get("drug_interactions")))
            desc = truncate(first(openfda.get("description")) or first(openfda.get("clinical_pharmacology")))
        else:
            uses = warn = dose = adv = inter = desc = None
        if not any([uses, warn, dose, adv, inter, desc]):
            syn = synthetic_content(gname, cname, conds)
            uses = uses or syn["uses"]
            warn = warn or syn["warnings"]
            dose = dose or syn["dosage"]
            adv = adv or syn["side_effects"]
            inter = inter or syn["interactions_text"]
            desc = desc or syn["description"]

        faq = [
            {"q": f"What is {gname} used for?", "a": (uses or "")[:400] or f"{gname} is used to treat {', '.join(conds) if conds else 'various medical conditions'}."},
            {"q": f"How should I take {gname}?", "a": (dose or "")[:400] or f"Take {gname} exactly as prescribed by your doctor."},
            {"q": f"What are the most common side effects of {gname}?", "a": (adv or "")[:400] or "Common side effects vary; consult the side effects section above."},
            {"q": f"Can I drink alcohol while taking {gname}?", "a": "Talk with your doctor or pharmacist about whether alcohol is safe to consume while on this medication. Alcohol can worsen side effects of many drugs."},
            {"q": f"Is {gname} safe during pregnancy?", "a": "Discuss with your doctor before using this medication if you are pregnant, planning pregnancy, or breastfeeding."},
        ]

        d = Drug(
            generic_name=gname,
            slug=slugify(gname),
            brand_names_json=json.dumps(brands),
            drug_class_id=cls_by_name.get(cname),
            availability=avail,
            csa_schedule=csa,
            pregnancy_risk="Discuss with your doctor",
            pronunciation=pron,
            description=desc,
            uses=uses,
            warnings=warn,
            dosage=dose,
            side_effects=adv,
            interactions_text=inter,
            faq_json=json.dumps(faq),
            conditions_json=json.dumps(conds),
            related_drugs_json=json.dumps([]),
            is_featured=(gname in featured_targets),
            reviewer_name="Drugs.com editorial team",
            reviewer_credential="PharmD",
            last_updated=datetime.utcnow() - timedelta(days=hash(gname) % 365),
        )
        db.session.add(d)
    db.session.commit()

    # Populate related_drugs by class
    all_drugs = Drug.query.all()
    by_class = {}
    for d in all_drugs:
        by_class.setdefault(d.drug_class_id, []).append(d.generic_name)
    for d in all_drugs:
        peers = [n for n in by_class.get(d.drug_class_id, []) if n != d.generic_name][:6]
        d.related_drugs_json = json.dumps(peers)
    db.session.commit()


def seed_drug_conditions():
    cond_by_slug = {c.slug: c for c in Condition.query.all()}
    existing = {(dc.drug_id, dc.condition_id) for dc in DrugCondition.query.all()}
    for d in Drug.query.all():
        for c_slug in d.conditions_list:
            c = cond_by_slug.get(c_slug)
            if c and (d.id, c.id) not in existing:
                db.session.add(DrugCondition(drug_id=d.id, condition_id=c.id))
    db.session.commit()
    # Update denormalized drug_count
    for c in Condition.query.all():
        c.drug_count = DrugCondition.query.filter_by(condition_id=c.id).count()
    db.session.commit()


def seed_pill_images():
    drug_by_name = {d.generic_name: d for d in Drug.query.all()}
    existing = set()
    for pi in DrugImage.query.all():
        existing.add((pi.drug_id, pi.imprint))
    to_add = []
    for gname, imprint, shape, color, strength, mfg in PILL_IMAGES_DATA:
        d = drug_by_name.get(gname)
        if not d:
            continue
        if (d.id, imprint) in existing:
            continue
        to_add.append((d, imprint, shape, color, strength, mfg))
        existing.add((d.id, imprint))
    if not to_add:
        return
    for d, imprint, shape, color, strength, mfg in to_add:
        db.session.add(DrugImage(
            drug_id=d.id, imprint=imprint, shape=shape, color=color,
            strength=strength, manufacturer=mfg,
        ))
    db.session.commit()


def seed_interactions():
    """Add any interactions in INTERACTIONS_DATA that aren't already in the DB.

    Additive: matches on the unordered (drug_a_id, drug_b_id) pair so re-seeding
    won't duplicate rows. Gated as a whole — if every applicable pair is already
    present, returns without touching the session, preserving byte-identical
    reset semantics.
    """
    drug_by_name = {d.generic_name: d for d in Drug.query.all()}
    existing_pairs = set()
    for i in DrugInteraction.query.all():
        existing_pairs.add((i.drug_a_id, i.drug_b_id))
        existing_pairs.add((i.drug_b_id, i.drug_a_id))

    to_add = []
    for a, b, sev, desc in INTERACTIONS_DATA:
        da = drug_by_name.get(a)
        db_ = drug_by_name.get(b)
        if not da or not db_:
            continue
        if (da.id, db_.id) in existing_pairs:
            continue
        to_add.append((da, db_, sev, desc))
        existing_pairs.add((da.id, db_.id))
        existing_pairs.add((db_.id, da.id))

    if not to_add:
        return
    for da, db_, sev, desc in to_add:
        db.session.add(DrugInteraction(
            drug_a_id=da.id, drug_b_id=db_.id, severity=sev, description=desc,
        ))
    db.session.commit()


def seed_news():
    existing = {n.title for n in NewsArticle.query.all()}
    now = datetime.utcnow()
    for i, (title, cat, body) in enumerate(NEWS_DATA):
        if title in existing:
            continue
        db.session.add(NewsArticle(
            title=title, category=cat, body=body, source="Drugs.com Medical News",
            published_at=now - timedelta(days=i * 2),
            is_featured=(i < 4),
        ))
    db.session.commit()


def seed_benchmark_users():
    if User.query.filter_by(email="alice.j@test.com").first():
        return
    drugs = Drug.query.all()
    if not drugs:
        return
    for idx, u in enumerate(BENCHMARK_USERS):
        user = User(username=u["username"], email=u["email"])
        user.set_password(u["password"])
        db.session.add(user)
        db.session.flush()
        # Saved drugs (3+)
        saved_pool = drugs[(idx * 7) % len(drugs):(idx * 7) % len(drugs) + 5]
        if len(saved_pool) < 3:
            saved_pool = drugs[:5]
        for d in saved_pool[:4]:
            db.session.add(SavedDrug(user_id=user.id, drug_id=d.id, notes=f"Tracking for ongoing treatment."))
        # Reviews (2+)
        for j in range(3):
            target = drugs[(idx * 5 + j * 11) % len(drugs)]
            conds = target.conditions_list or ["general use"]
            tmpl = REVIEW_TEMPLATES[(idx + j) % len(REVIEW_TEMPLATES)]
            db.session.add(DrugReview(
                drug_id=target.id, user_id=user.id, rating=tmpl[1],
                title=tmpl[0], body=tmpl[2].format(cond=conds[0]),
                condition_treated=conds[0],
                helpful_count=(idx + j) * 3,
            ))
    db.session.commit()


def seed_extra_reviews():
    """Add ~50 additional reviews across drugs from auto-generated reviewer users."""
    if DrugReview.query.count() >= 100:
        return
    # Create some anonymous reviewer users if not present
    reviewers = []
    for i in range(8):
        email = f"reviewer{i}@example.com"
        u = User.query.filter_by(email=email).first()
        if not u:
            u = User(username=f"reviewer_{i}", email=email)
            u.set_password("review-seed-pw")
            db.session.add(u)
            db.session.flush()
        reviewers.append(u)
    popular = ["ibuprofen", "metformin", "lisinopril", "sertraline", "atorvastatin",
               "amoxicillin", "levothyroxine", "alprazolam", "gabapentin", "omeprazole",
               "semaglutide", "fluoxetine", "amlodipine", "tramadol", "zolpidem",
               "warfarin", "clopidogrel", "furosemide", "prednisone", "rosuvastatin",
               "losartan", "metoprolol", "carvedilol", "hydrochlorothiazide",
               "pantoprazole", "famotidine", "ondansetron", "cetirizine", "loratadine",
               "montelukast", "ciprofloxacin", "doxycycline", "fluconazole", "acyclovir",
               "tamsulosin", "tadalafil", "sildenafil", "oxycodone", "hydrocodone",
               "methylphenidate", "lithium", "valproic acid", "lamotrigine",
               "levetiracetam", "duloxetine", "venlafaxine", "bupropion", "trazodone",
               "escitalopram", "quetiapine", "olanzapine", "aripiprazole", "clonazepam",
               "lorazepam", "diazepam", "buspirone", "pregabalin", "celecoxib",
               "naproxen", "cyclobenzaprine", "colchicine", "allopurinol", "alendronate",
               "estradiol", "methimazole", "finasteride", "spironolactone", "digoxin",
               "citalopram", "paroxetine", "mirtazapine", "risperidone", "topiramate",
               "verapamil", "diltiazem", "valsartan", "atenolol", "propranolol",
               "apixaban", "rivaroxaban", "esomeprazole", "lansoprazole", "azithromycin",
               "fexofenadine", "hydroxyzine", "fluticasone", "tiotropium",
               "valacyclovir", "morphine", "buprenorphine", "atomoxetine",
               "carbamazepine", "haloperidol", "methocarbamol", "baclofen",
               "tizanidine", "risedronate", "raloxifene", "testosterone",
               "isotretinoin", "tretinoin", "timolol", "latanoprost",
               "vitamin D3", "folic acid", "ferrous sulfate", "multivitamin"]
    drug_by_name = {d.generic_name: d for d in Drug.query.all()}
    count = 0
    for i, name in enumerate(popular):
        d = drug_by_name.get(name)
        if not d:
            continue
        conds = d.conditions_list or ["general"]
        for j in range(4):
            tmpl = REVIEW_TEMPLATES[(i + j) % len(REVIEW_TEMPLATES)]
            u = reviewers[(i + j) % len(reviewers)]
            db.session.add(DrugReview(
                drug_id=d.id, user_id=u.id, rating=tmpl[1],
                title=tmpl[0], body=tmpl[2].format(cond=conds[j % len(conds)]),
                condition_treated=conds[j % len(conds)],
                helpful_count=(j + 1) * 4,
                created_at=datetime.utcnow() - timedelta(days=(i * 4 + j)),
            ))
            count += 1
            if count >= 200:
                break
        if count >= 55:
            break
    db.session.commit()


def recompute_drug_ratings():
    for d in Drug.query.all():
        revs = DrugReview.query.filter_by(drug_id=d.id).all()
        if revs:
            d.avg_rating = round(sum(r.rating for r in revs) / len(revs), 1)
            d.review_count = len(revs)
        else:
            d.avg_rating = 0.0
            d.review_count = 0
    db.session.commit()


def seed_database():
    # Gate the entire seeding block: even a no-op commit bumps SQLite metadata
    # and breaks /reset byte-identity. All-or-nothing is the correct invariant.
    if Drug.query.count() > 0:
        return
    seed_drug_classes()
    seed_conditions()
    seed_drugs()
    seed_drug_conditions()
    seed_pill_images()
    seed_interactions()
    seed_news()
    seed_benchmark_users()
    seed_extra_reviews()
    recompute_drug_ratings()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def tokenize(q):
    if not q:
        return []
    return [t.lower() for t in re.split(r"\W+", q) if t]


def score_drug(drug, tokens):
    text = f"{drug.generic_name} {drug.brand_names_json} {drug.description or ''}".lower()
    return sum(1 for t in tokens if t in text)


@app.template_filter('format_drug_text')
def format_drug_text(text):
    """Format raw FDA-label drug text into readable HTML paragraphs.

    Collapses internal newlines, bolds ALL-CAPS section headings like
    'WARNINGS:', sets off numbered list items, and groups sentences into
    paragraphs of roughly three sentences each. Returns an HTML string
    consisting of one or more ``<p>...</p>`` blocks; intended to be
    piped through ``|safe`` in templates.
    """
    if not text:
        return ''
    text = str(text).strip()
    # Collapse internal newlines into spaces.
    text = re.sub(r'\n+', ' ', text)
    # Bold ALL-CAPS section headings like 'WARNINGS:' or 'DOSAGE:'.
    text = re.sub(r'([A-Z]{3,}:)\s*', r'<strong>\1</strong> ', text)
    # Split into sentences at terminal punctuation followed by capital/digit.
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])', text)
    paragraphs = []
    current = []
    for i, sentence in enumerate(sentences):
        if not sentence.strip():
            continue
        current.append(sentence.strip())
        if len(current) >= 3 or i == len(sentences) - 1:
            paragraphs.append(' '.join(current))
            current = []
    if current:
        paragraphs.append(' '.join(current))
    return '<p>' + '</p><p>'.join(p for p in paragraphs if p.strip()) + '</p>'


@app.context_processor
def inject_globals():
    return {
        "site_name": "Drugs.com",
        "site_tagline": "Know More. Be Sure.",
        "current_year": datetime.utcnow().year,
        "all_letters": list(string.ascii_uppercase),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    featured = Drug.query.filter_by(is_featured=True).limit(8).all()
    trending = Drug.query.order_by(Drug.review_count.desc()).limit(12).all()
    news = NewsArticle.query.order_by(NewsArticle.published_at.desc()).limit(6).all()
    classes = DrugClass.query.order_by(DrugClass.name).limit(12).all()
    # Top 12 conditions by drug count (for homepage "Browse by" tabs)
    top_conditions = (Condition.query
                      .order_by(Condition.drug_count.desc(), Condition.name)
                      .limit(12).all())
    # Top 12 drug classes by number of drugs (denormalized count via subquery)
    class_drug_counts = dict(
        db.session.query(Drug.drug_class_id, db.func.count(Drug.id))
        .group_by(Drug.drug_class_id).all()
    )
    all_classes = DrugClass.query.all()
    for c in all_classes:
        c.drug_count_val = class_drug_counts.get(c.id, 0)
    top_drug_classes = sorted(
        all_classes, key=lambda c: (-c.drug_count_val, c.name)
    )[:12]
    # Common symptoms for the "Symptoms" tab (flat list of 12 from body systems)
    top_symptoms = [
        "Headache", "Cough", "Chest pain", "Nausea", "Joint pain", "Rash",
        "Anxiety", "Fatigue", "Shortness of breath", "Abdominal pain",
        "Back pain", "Insomnia",
    ]
    health_topics = Condition.query.filter(
        Condition.slug.in_(['hypertension', 'diabetes', 'depression', 'anxiety', 'pain',
                            'high-cholesterol', 'heart-disease', 'asthma', 'arthritis', 'insomnia'])
    ).all()
    fda_news = NewsArticle.query.filter_by(category="FDA Alerts").order_by(
        NewsArticle.published_at.desc()).limit(3).all()
    new_approvals = NewsArticle.query.filter(
        NewsArticle.category.in_(['New Drug Approvals', 'New Drugs'])
    ).order_by(NewsArticle.published_at.desc()).limit(4).all()
    image_drugs = (Drug.query.join(DrugImage, DrugImage.drug_id == Drug.id)
                   .order_by(db.func.random()).limit(6).all())
    image_samples = [(d, d.images[0]) for d in image_drugs if d.images]
    return render_template("index.html", featured=featured, trending=trending,
                           news=news, classes=classes,
                           health_topics=health_topics, fda_news=fda_news,
                           new_approvals=new_approvals,
                           image_samples=image_samples,
                           top_conditions=top_conditions,
                           top_drug_classes=top_drug_classes,
                           top_symptoms=top_symptoms)


@app.route("/drug_information.html")
@app.route("/drugs-a-to-z.html")
def drug_az():
    letter = (request.args.get("letter") or "A").upper()
    if letter not in string.ascii_uppercase:
        letter = "A"
    drugs = Drug.query.filter(Drug.generic_name.ilike(f"{letter}%")).order_by(Drug.generic_name).all()
    letter_counts = {
        L: Drug.query.filter(Drug.generic_name.ilike(f"{L}%")).count()
        for L in string.ascii_uppercase
    }
    popular_drugs = Drug.query.order_by(Drug.review_count.desc()).limit(10).all()
    return render_template(
        "drug_az.html",
        active_letter=letter,
        all_letters=list(string.ascii_uppercase),
        drugs=drugs,
        letter_counts=letter_counts,
        popular_drugs=popular_drugs,
    )


def _first_sentences(text, n):
    """Return the first n sentences from text as a single string."""
    if not text:
        return ""
    # Strip simple HTML tags that may live in seed content
    plain = re.sub(r"<[^>]+>", " ", text)
    plain = re.sub(r"\s+", " ", plain).strip()
    parts = re.split(r"(?<=[.!?])\s+", plain)
    parts = [p for p in parts if p]
    return " ".join(parts[:n]).strip()


def _build_default_faq(drug):
    """Generate a contextual FAQ from drug fields when faq_json is empty."""
    name = drug.generic_name
    name_cap = name.capitalize() if name else "this medicine"
    items = []

    uses_summary = _first_sentences(drug.uses, 2) or _first_sentences(drug.description, 2)
    if uses_summary:
        items.append({
            "q": f"What is {name} used for?",
            "a": uses_summary,
        })

    items.append({
        "q": f"How does {name} work?",
        "a": (
            f"{name_cap} belongs to the {drug.drug_class.name} class. "
            f"{drug.drug_class.description}"
        ) if drug.drug_class else (
            f"{name_cap} works through its active pharmacological mechanism in the body. "
            f"Talk to your doctor or pharmacist for a detailed explanation of how it works for your condition."
        ),
    })

    se_summary = _first_sentences(drug.side_effects, 3)
    if se_summary:
        items.append({
            "q": f"What are the most common side effects of {name}?",
            "a": se_summary,
        })

    avail = (drug.availability or "").lower()
    if "otc" in avail and "rx" in avail:
        otc_answer = (
            f"{name_cap} is available both over the counter and by prescription, "
            f"depending on the strength and formulation."
        )
    elif "otc" in avail:
        otc_answer = (
            f"Yes. {name_cap} is available over the counter without a prescription. "
            f"Always follow the directions on the label."
        )
    else:
        otc_answer = (
            f"No. {name_cap} is a prescription-only medicine and is not available over the counter. "
            f"You will need a prescription from a licensed healthcare provider."
        )
    items.append({
        "q": f"Is {name} available over the counter?",
        "a": otc_answer,
    })

    preg = (drug.pregnancy_risk or "").strip()
    if preg:
        items.append({
            "q": f"Is {name} safe to take during pregnancy?",
            "a": (
                f"Pregnancy risk for {name}: {preg}. "
                f"Always talk to your doctor before taking any medicine while pregnant or breastfeeding."
            ),
        })

    items.append({
        "q": f"Is there a generic version of {name}?",
        "a": (
            f"{name_cap} is itself a generic name. Generic versions are widely available "
            f"and may be sold under several brand names: "
            f"{', '.join(drug.brand_names) if drug.brand_names else 'see the brand names listed above'}."
        ),
    })

    return items


@app.route("/<slug>.html")
def drug_detail(slug):
    drug = Drug.query.filter_by(slug=slug).first()
    if not drug:
        abort(404)
    # Track recently viewed drugs in session
    viewed = session.get("recently_viewed", [])
    if drug.slug in viewed:
        viewed.remove(drug.slug)
    viewed.insert(0, drug.slug)
    viewed = viewed[:10]
    session["recently_viewed"] = viewed
    session.modified = True
    # Fetch recently viewed Drug rows (excluding current page's drug) in session order
    other_slugs = [s for s in viewed if s != drug.slug]
    recently_viewed = []
    if other_slugs:
        recently_viewed = Drug.query.filter(Drug.slug.in_(other_slugs)).all()
        rv_order = {s: i for i, s in enumerate(other_slugs)}
        recently_viewed.sort(key=lambda d: rv_order.get(d.slug, 99))
    reviews = DrugReview.query.filter_by(drug_id=drug.id).order_by(DrugReview.helpful_count.desc()).limit(20).all()
    related = Drug.query.filter(Drug.generic_name.in_(drug.related_drugs)).all()
    cond_by_slug = {c.slug: c for c in Condition.query.all()}
    drug_conditions = [cond_by_slug[s] for s in drug.conditions_list if s in cond_by_slug]
    saved = False
    if current_user.is_authenticated:
        saved = SavedDrug.query.filter_by(user_id=current_user.id, drug_id=drug.id).first() is not None
    # rating distribution: counts indexed 1..10
    rating_distribution = {i: 0 for i in range(1, 11)}
    for r in DrugReview.query.filter_by(drug_id=drug.id).all():
        if 1 <= (r.rating or 0) <= 10:
            rating_distribution[r.rating] += 1
    user_review = None
    if current_user.is_authenticated:
        user_review = DrugReview.query.filter_by(drug_id=drug.id, user_id=current_user.id).first()
    related_news = NewsArticle.query.filter(
        db.or_(
            NewsArticle.title.ilike(f"%{drug.generic_name}%"),
            NewsArticle.body.ilike(f"%{drug.generic_name}%")
        )
    ).order_by(NewsArticle.published_at.desc()).limit(3).all()

    # Fallback: add brand name matches to fill up to 3
    if len(related_news) < 3 and drug.brand_names:
        seen_ids = {a.id for a in related_news}
        for brand in drug.brand_names[:2]:
            extras = NewsArticle.query.filter(
                db.or_(
                    NewsArticle.title.ilike(f"%{brand}%"),
                    NewsArticle.body.ilike(f"%{brand}%")
                )
            ).order_by(NewsArticle.published_at.desc()).limit(2).all()
            for a in extras:
                if a.id not in seen_ids:
                    related_news.append(a)
                    seen_ids.add(a.id)
                    if len(related_news) >= 3:
                        break

    # Final fallback: just recent news
    if not related_news:
        related_news = NewsArticle.query.order_by(NewsArticle.published_at.desc()).limit(3).all()
    related_drugs = []
    if drug.drug_class_id:
        related_drugs = Drug.query.filter(
            Drug.drug_class_id == drug.drug_class_id,
            Drug.id != drug.id
        ).order_by(db.func.random()).limit(6).all()
    drug_interactions = DrugInteraction.query.filter(
        (DrugInteraction.drug_a_id == drug.id) | (DrugInteraction.drug_b_id == drug.id)
    ).all()
    faq_items = drug.faq or _build_default_faq(drug)
    return render_template("drug_detail.html", drug=drug, reviews=reviews,
                           related=related, drug_conditions=drug_conditions, saved=saved,
                           rating_distribution=rating_distribution, user_review=user_review,
                           related_news=related_news, related_drugs=related_drugs,
                           drug_interactions=drug_interactions,
                           faq_items=faq_items,
                           recently_viewed=recently_viewed)


@app.route("/<slug>/reviews")
def drug_reviews_page(slug):
    drug = Drug.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    condition_filter = request.args.get('condition', '')
    sort = request.args.get('sort', 'recent')

    query = DrugReview.query.filter_by(drug_id=drug.id)
    if condition_filter:
        query = query.filter_by(condition_treated=condition_filter)
    if sort == 'helpful':
        query = query.order_by(DrugReview.helpful_count.desc())
    elif sort == 'highest':
        query = query.order_by(DrugReview.rating.desc())
    elif sort == 'lowest':
        query = query.order_by(DrugReview.rating.asc())
    else:
        query = query.order_by(DrugReview.created_at.desc())

    reviews = query.paginate(page=page, per_page=20, error_out=False)
    conditions = db.session.query(DrugReview.condition_treated).filter_by(drug_id=drug.id).distinct().all()
    conditions = [c[0] for c in conditions if c[0]]
    rating_dist = {i: DrugReview.query.filter_by(drug_id=drug.id, rating=i).count() for i in range(1, 11)}
    return render_template("drug_reviews_page.html", drug=drug, reviews=reviews,
                          conditions=conditions, condition_filter=condition_filter,
                          sort=sort, rating_dist=rating_dist)


@app.route("/<slug>/review", methods=["POST"])
@login_required
def submit_review(slug):
    drug = Drug.query.filter_by(slug=slug).first_or_404()
    try:
        rating = int(request.form.get("rating", 5))
    except (TypeError, ValueError):
        rating = 5
    rating = max(1, min(10, rating))
    title = (request.form.get("title") or "")[:200]
    body = (request.form.get("body") or "")[:2000]
    condition = (request.form.get("condition_treated") or "")[:100]
    existing = DrugReview.query.filter_by(drug_id=drug.id, user_id=current_user.id).first()
    if existing:
        existing.rating = rating
        existing.title = title
        existing.body = body
        existing.condition_treated = condition
    else:
        db.session.add(DrugReview(
            drug_id=drug.id, user_id=current_user.id,
            rating=rating, title=title, body=body, condition_treated=condition,
        ))
    db.session.commit()
    revs = DrugReview.query.filter_by(drug_id=drug.id).all()
    if revs:
        drug.avg_rating = round(sum(r.rating for r in revs) / len(revs), 1)
        drug.review_count = len(revs)
        db.session.commit()
    flash("Your review has been submitted.", "success")
    return redirect(url_for("drug_detail", slug=slug) + "#reviews")


@app.route("/<slug>/review/<int:review_id>/helpful", methods=["POST"])
def review_helpful_vote(slug, review_id):
    drug = Drug.query.filter_by(slug=slug).first_or_404()
    review = DrugReview.query.filter_by(id=review_id, drug_id=drug.id).first_or_404()
    vote = (request.values.get("vote") or "yes").lower()
    delta = -1 if vote == "no" else 1
    review.helpful_count = max(0, (review.helpful_count or 0) + delta)
    db.session.commit()
    return jsonify({"votes": review.helpful_count, "review_id": review.id})


@app.route("/search")
def search():
    q = (request.args.get("q") or "").strip()
    class_slug = request.args.get("class") or ""
    cond_slug = request.args.get("condition") or ""
    avail = request.args.get("availability") or ""
    try:
        page = max(1, int(request.args.get("page") or 1))
    except (TypeError, ValueError):
        page = 1
    per_page = 20

    drugs = Drug.query
    if class_slug:
        cls = DrugClass.query.filter_by(slug=class_slug).first()
        if cls:
            drugs = drugs.filter(Drug.drug_class_id == cls.id)
    if avail:
        drugs = drugs.filter(Drug.availability == avail)
    drugs = drugs.all()

    if cond_slug:
        drugs = [d for d in drugs if cond_slug in d.conditions_list]

    tokens = tokenize(q)
    matched_condition = None
    matched_class = None
    if tokens:
        # Check if query matches a condition or drug class name
        ql = q.lower()
        for c in Condition.query.all():
            if c.name.lower() == ql or c.slug == ql:
                matched_condition = c
                break
        if not matched_condition:
            for cls in DrugClass.query.all():
                if cls.name.lower() == ql or cls.slug == ql:
                    matched_class = cls
                    break

        scored = [(score_drug(d, tokens), d) for d in drugs]
        scored = [(s, d) for s, d in scored if s > 0]
        existing_ids = {d.id for _, d in scored}

        # Explicit brand-name match: include drugs whose brand names contain
        # any query token (and bump the score of already-scored drugs).
        for d in drugs:
            brand_blob = " ".join(d.brand_names).lower() if d.brand_names else ""
            if any(t in brand_blob for t in tokens):
                if d.id in existing_ids:
                    scored = [(s + 2, dd) if dd.id == d.id else (s, dd) for s, dd in scored]
                else:
                    scored.append((2, d))
                    existing_ids.add(d.id)

        # Boost drugs matching the condition/class
        if matched_condition:
            extras = [d for d in drugs if matched_condition.slug in d.conditions_list]
            for d in extras:
                if d.id not in existing_ids:
                    scored.append((1, d))
                    existing_ids.add(d.id)
        if matched_class:
            extras = [d for d in drugs if d.drug_class_id == matched_class.id]
            for d in extras:
                if d.id not in existing_ids:
                    scored.append((1, d))
                    existing_ids.add(d.id)

        scored.sort(key=lambda x: (-x[0], x[1].generic_name))
        results = [d for _, d in scored]
    else:
        # Empty query: show popular drugs (most reviewed)
        if not (class_slug or cond_slug or avail):
            drugs = Drug.query.order_by(Drug.review_count.desc()).all()
        results = sorted(drugs, key=lambda d: -d.review_count) if not q else sorted(drugs, key=lambda d: d.generic_name)

    # Conditions and News result groups (only when there's a query and no
    # restrictive drug-only filters are applied).
    condition_results = []
    news_results = []
    if q:
        ql = q.lower()
        for c in Condition.query.all():
            if ql in c.name.lower() or ql in (c.slug or "").lower() \
               or ql in (c.description or "").lower():
                condition_results.append(c)
        condition_results.sort(key=lambda c: c.name)
        condition_results = condition_results[:10]

        for a in NewsArticle.query.all():
            if ql in a.title.lower() or ql in (a.body or "").lower() \
               or ql in (a.category or "").lower():
                news_results.append(a)
        news_results.sort(key=lambda a: a.published_at or datetime.min, reverse=True)
        news_results = news_results[:10]

    # "Did you mean?" suggestions: 3 closest drug names by edit-distance
    # ratio whenever the query produced zero drug hits.
    suggestions = []
    if q and not results:
        all_names = [d.generic_name for d in Drug.query.all()]
        suggestions = difflib.get_close_matches(q.lower(),
                                                [n.lower() for n in all_names],
                                                n=3, cutoff=0.5)
        # Map back to canonical capitalisation.
        lower_to_orig = {n.lower(): n for n in all_names}
        suggestions = [lower_to_orig.get(s, s) for s in suggestions]

    # "Related searches": fuzzy-near drug names, excluding any name already
    # present in the result set. Only computed when a query is present.
    related_searches = []
    if q:
        result_names_lower = {d.generic_name.lower() for d in results}
        all_names = [d.generic_name for d in Drug.query.all()]
        candidates = [n for n in all_names if n.lower() not in result_names_lower]
        matches = difflib.get_close_matches(q.lower(),
                                            [n.lower() for n in candidates],
                                            n=6, cutoff=0.4)
        lower_to_orig = {n.lower(): n for n in candidates}
        related_searches = [lower_to_orig.get(s, s) for s in matches]

    total = len(results)
    total_all = total + len(condition_results) + len(news_results)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)
    page_results = results[(page - 1) * per_page: page * per_page]

    classes = DrugClass.query.order_by(DrugClass.name).all()
    conditions = Condition.query.order_by(Condition.name).all()
    return render_template("search.html", q=q, results=page_results, total=total,
                           total_all=total_all,
                           condition_results=condition_results,
                           news_results=news_results,
                           classes=classes, conditions=conditions,
                           class_slug=class_slug, cond_slug=cond_slug, avail=avail,
                           page=page, total_pages=total_pages,
                           suggestions=suggestions,
                           related_searches=related_searches,
                           matched_condition=matched_condition,
                           matched_class=matched_class)


@app.route("/api/autocomplete")
def autocomplete():
    q = request.args.get("q", "").strip().lower()
    if len(q) < 2:
        return jsonify([])
    # Search generic names
    drugs = Drug.query.filter(Drug.generic_name.ilike(f"{q}%")).limit(5).all()
    # Also search brand names within the list
    results = []
    for d in drugs:
        results.append({"type": "drug", "name": d.generic_name, "url": f"/{d.slug}.html", "label": d.generic_name.capitalize()})
        for brand in (d.brand_names or [])[:1]:  # only first brand
            if brand.lower().startswith(q):
                results.append({"type": "brand", "name": brand, "url": f"/{d.slug}.html", "label": f"{brand} ({d.generic_name})"})
    # Also search conditions
    conditions = Condition.query.filter(Condition.name.ilike(f"%{q}%")).limit(3).all()
    for c in conditions:
        results.append({"type": "condition", "name": c.name, "url": f"/condition/{c.slug}", "label": c.name})
    return jsonify(results[:8])


@app.route("/drug_interactions.html", methods=["GET", "POST"])
@app.route("/interaction-checker/", methods=["GET", "POST"])
@app.route("/interaction-checker", methods=["GET", "POST"])
def interaction_checker():
    drugs = Drug.query.order_by(Drug.generic_name).all()
    drugs_input = None
    interactions = None
    unrecognized = []
    summary = None
    # Pre-populate from URL param (linked from drug detail pages, e.g. ?drug=ibuprofen)
    prefill_slug = request.args.get("drug", "").strip()
    prefill = ""
    if prefill_slug:
        d = Drug.query.filter_by(slug=prefill_slug).first()
        if not d:
            d = Drug.query.filter(db.func.lower(Drug.generic_name) == prefill_slug.lower()).first()
        prefill = d.generic_name if d else prefill_slug
    if request.method == "POST":
        raw = request.form.getlist("drugs")
        drugs_input = [r.strip() for r in raw if r and r.strip()]
        resolved = []
        seen_ids = set()
        for n in drugs_input:
            low = n.lower()
            d = Drug.query.filter(db.func.lower(Drug.generic_name) == low).first()
            if not d:
                for cand in drugs:
                    if low in [b.lower() for b in cand.brand_names]:
                        d = cand
                        break
            if d and d.id not in seen_ids:
                resolved.append(d)
                seen_ids.add(d.id)
            elif not d:
                unrecognized.append(n)

        interactions = []
        pair_keys = set()
        for a, b in combinations(resolved, 2):
            rec = DrugInteraction.query.filter(
                ((DrugInteraction.drug_a_id == a.id) & (DrugInteraction.drug_b_id == b.id)) |
                ((DrugInteraction.drug_a_id == b.id) & (DrugInteraction.drug_b_id == a.id))
            ).first()
            key = tuple(sorted([a.id, b.id]))
            if key in pair_keys:
                continue
            pair_keys.add(key)
            if rec:
                interactions.append({
                    "drug_a": a,
                    "drug_b": b,
                    "severity": rec.severity,
                    "description": rec.description,
                })
        # Sort major -> moderate -> minor
        order = {"major": 0, "moderate": 1, "minor": 2}
        interactions.sort(key=lambda it: order.get(it["severity"], 99))
        summary = {
            "total": len(interactions),
            "major": sum(1 for it in interactions if it["severity"] == "major"),
            "moderate": sum(1 for it in interactions if it["severity"] == "moderate"),
            "minor": sum(1 for it in interactions if it["severity"] == "minor"),
        }
        food_interactions, alcohol_interactions = _lifestyle_interactions(resolved)
    else:
        food_interactions, alcohol_interactions = [], []
    return render_template(
        "interaction_checker.html",
        drugs=drugs,
        drugs_input=drugs_input,
        interactions=interactions,
        unrecognized=unrecognized,
        summary=summary,
        prefill=prefill,
        food_interactions=food_interactions,
        alcohol_interactions=alcohol_interactions,
    )


# Hardcoded clinical reference data for drug-food / drug-alcohol interactions.
# Keyed by (lowercased) generic name and by (lowercased) drug-class name.
_FOOD_BY_GENERIC = {
    "warfarin": [
        {"item": "Vitamin K-rich foods (kale, spinach, broccoli)", "severity": "moderate",
         "description": "Large or fluctuating intake of leafy greens high in vitamin K can antagonize warfarin's anticoagulant effect and destabilize INR. Keep vitamin K intake consistent rather than eliminating these foods."},
        {"item": "Cranberry juice", "severity": "moderate",
         "description": "Cranberry juice may potentiate warfarin and raise INR, increasing bleeding risk. Limit intake or avoid large quantities while on warfarin."},
    ],
    "ibuprofen": [
        {"item": "High-sodium foods", "severity": "minor",
         "description": "NSAIDs can cause fluid retention and elevate blood pressure; high-sodium meals compound this effect, particularly in patients with hypertension or heart failure."},
    ],
}

_FOOD_BY_CLASS = {
    "nsaids": [
        {"item": "High-sodium foods", "severity": "minor",
         "description": "NSAIDs promote sodium and water retention. Diets high in sodium can amplify blood-pressure increases and edema, especially in older adults or those with cardiac disease."},
    ],
    "statins": [
        {"item": "Grapefruit juice", "severity": "major",
         "description": "Grapefruit inhibits intestinal CYP3A4 and substantially raises serum levels of simvastatin, lovastatin, and atorvastatin. Elevated exposure increases the risk of myopathy and rhabdomyolysis."},
    ],
    "ssris": [
        {"item": "Tyramine-rich foods (aged cheese, cured meats)", "severity": "minor",
         "description": "While SSRIs are safer than MAOIs with tyramine, large tyramine loads can occasionally precipitate hypertensive or serotonergic symptoms in susceptible patients."},
    ],
    "anticoagulants": [
        {"item": "Vitamin K-rich foods (kale, spinach, broccoli)", "severity": "moderate",
         "description": "Vitamin K antagonizes warfarin-type anticoagulants. Keep daily vitamin K intake consistent to maintain stable INR; abrupt changes alter anticoagulant control."},
    ],
    "ace inhibitors": [
        {"item": "Potassium-rich foods (bananas, oranges, salt substitutes)", "severity": "moderate",
         "description": "ACE inhibitors reduce aldosterone-mediated potassium excretion. Excess dietary potassium, especially with salt substitutes, can produce clinically significant hyperkalemia."},
    ],
}

_ALCOHOL_BY_GENERIC = {
    "metronidazole": {"severity": "major",
        "description": "Metronidazole with alcohol can produce a disulfiram-like reaction with flushing, nausea, vomiting, tachycardia, and headache. Avoid alcohol during therapy and for at least 48 hours after the last dose."},
    "warfarin": {"severity": "major",
        "description": "Acute heavy alcohol intake inhibits warfarin metabolism and raises INR with bleeding risk; chronic use induces metabolism and reduces effect. Either pattern destabilizes anticoagulation."},
    "acetaminophen": {"severity": "moderate",
        "description": "Chronic alcohol use induces CYP2E1, increasing formation of acetaminophen's hepatotoxic metabolite (NAPQI). Combination significantly raises the risk of acute liver injury."},
}

_ALCOHOL_BY_CLASS = {
    "nsaids": {"severity": "major",
        "description": "Combining NSAIDs with alcohol substantially increases the risk of gastrointestinal bleeding, ulceration, and renal injury. Avoid or minimize alcohol while taking NSAIDs."},
    "ssris": {"severity": "moderate",
        "description": "SSRIs combined with alcohol increase central nervous system depression, sedation, and impaired judgment. Alcohol may also worsen depressive symptoms and reduce SSRI efficacy."},
    "benzodiazepines": {"severity": "major",
        "description": "Benzodiazepines plus alcohol cause additive CNS and respiratory depression. The combination can produce profound sedation, respiratory arrest, and death."},
    "opioids": {"severity": "major",
        "description": "Opioids and alcohol both depress the CNS and respiratory drive. Concurrent use markedly increases the risk of fatal respiratory depression and overdose."},
    "anticoagulants": {"severity": "major",
        "description": "Alcohol affects both anticoagulant metabolism and platelet function, increasing the risk of major bleeding. Patients should limit intake and discuss safe thresholds with their clinician."},
    "antihistamines": {"severity": "moderate",
        "description": "First-generation antihistamines combined with alcohol produce additive sedation and psychomotor impairment, raising the risk of falls and motor-vehicle accidents."},
    "antidiabetics": {"severity": "moderate",
        "description": "Alcohol can cause hypoglycemia (especially fasting) and impair recognition of warning symptoms. Sulfonylureas and insulin carry the greatest risk."},
}


def _lifestyle_interactions(resolved_drugs):
    """Return (food_interactions, alcohol_interactions) for the given Drug rows.

    Each food entry is {drug, item, severity, description}; each alcohol entry
    is {drug, severity, description}. Lookups are by lowercased generic name
    and drug-class name against hardcoded reference tables; drugs without
    matches contribute nothing. Lists are sorted major -> moderate -> minor,
    deduplicated per (drug, item) for food and one entry per drug for alcohol.
    """
    sev_order = {"major": 0, "moderate": 1, "minor": 2}
    food, alcohol = [], []
    seen_food = set()
    seen_alc = set()
    for d in resolved_drugs:
        gname = (d.generic_name or "").lower()
        cname = (d.drug_class.name or "").lower() if d.drug_class else ""
        candidates = list(_FOOD_BY_GENERIC.get(gname, []))
        candidates.extend(_FOOD_BY_CLASS.get(cname, []))
        for entry in candidates:
            key = (d.id, entry["item"])
            if key in seen_food:
                continue
            seen_food.add(key)
            food.append({"drug": d, **entry})
        alc = _ALCOHOL_BY_GENERIC.get(gname) or _ALCOHOL_BY_CLASS.get(cname)
        if alc and d.id not in seen_alc:
            seen_alc.add(d.id)
            alcohol.append({"drug": d, **alc})
    food.sort(key=lambda x: sev_order.get(x["severity"], 99))
    alcohol.sort(key=lambda x: sev_order.get(x["severity"], 99))
    return food, alcohol


@app.route("/api/interaction-check", methods=["POST"])
def api_interaction_check():
    data = request.get_json(silent=True) or {}
    names = [str(n).strip().lower() for n in data.get("drugs", []) if str(n).strip()]
    # normalize: try matching by generic name or brand
    matched = []
    name_to_drug = {}
    for n in names:
        d = Drug.query.filter(db.func.lower(Drug.generic_name) == n).first()
        if not d:
            # try brand match
            all_drugs = Drug.query.all()
            for cand in all_drugs:
                brands = [b.lower() for b in cand.brand_names]
                if n in brands:
                    d = cand
                    break
        if d:
            matched.append(d)
            name_to_drug[n] = d
    interactions = []
    pair_keys = set()
    no_interaction = []
    for a, b in combinations(matched, 2):
        # Try a-b and b-a
        rec = DrugInteraction.query.filter(
            ((DrugInteraction.drug_a_id == a.id) & (DrugInteraction.drug_b_id == b.id)) |
            ((DrugInteraction.drug_a_id == b.id) & (DrugInteraction.drug_b_id == a.id))
        ).first()
        key = tuple(sorted([a.generic_name, b.generic_name]))
        if key in pair_keys:
            continue
        pair_keys.add(key)
        if rec:
            interactions.append({
                "drug_a": a.generic_name,
                "drug_b": b.generic_name,
                "severity": rec.severity,
                "description": rec.description,
            })
        else:
            no_interaction.append([a.generic_name, b.generic_name])
    return jsonify({
        "interactions": interactions,
        "drugs_checked": [d.generic_name for d in matched],
        "unrecognized": [n for n in names if n not in name_to_drug],
        "no_interaction_pairs": no_interaction,
    })


@app.route("/pill_identification.html")
@app.route("/pill-identifier.html")
def pill_identifier():
    shapes = sorted({i.shape for i in DrugImage.query.all() if i.shape})
    colors = sorted({i.color for i in DrugImage.query.all() if i.color})
    return render_template("pill_identifier.html", shapes=shapes, colors=colors, results=None)


@app.route("/pill-identifier-results")
def pill_identifier_results():
    imprint = (request.args.get("imprint") or "").strip()
    shape = (request.args.get("shape") or "").strip()
    color = (request.args.get("color") or "").strip()
    q = DrugImage.query
    if imprint:
        q = q.filter(DrugImage.imprint.ilike(f"%{imprint}%"))
    if shape:
        q = q.filter(DrugImage.shape == shape)
    if color:
        q = q.filter(DrugImage.color == color)
    results = q.all()
    shapes = sorted({i.shape for i in DrugImage.query.all() if i.shape})
    colors = sorted({i.color for i in DrugImage.query.all() if i.color})
    return render_template("pill_identifier.html", shapes=shapes, colors=colors,
                           results=results, imprint=imprint, shape=shape, color=color)


@app.route("/condition/<slug>")
@app.route("/conditions/<slug>")
def condition_page(slug):
    cond = Condition.query.filter_by(slug=slug).first_or_404()
    links = DrugCondition.query.filter_by(condition_id=cond.id).all()
    drugs = [Drug.query.get(l.drug_id) for l in links]
    drugs = [d for d in drugs if d]
    sort = (request.args.get("sort") or "rating").lower()
    if sort == "name":
        drugs.sort(key=lambda d: d.generic_name)
    else:
        sort = "rating"
        drugs.sort(key=lambda d: (-(d.avg_rating or 0), d.generic_name))
    related = (
        Condition.query.filter(Condition.id != cond.id)
        .order_by(Condition.drug_count.desc())
        .limit(8)
        .all()
    )
    return render_template(
        "condition.html",
        condition=cond,
        drugs=drugs,
        sort=sort,
        related_conditions=related,
    )


CLASS_DESCRIPTIONS = {
    "NSAID": "Nonsteroidal anti-inflammatory drugs (NSAIDs) reduce pain, fever, and inflammation by blocking cyclooxygenase enzymes.",
    "NSAIDs": "Nonsteroidal anti-inflammatory drugs (NSAIDs) reduce pain, fever, and inflammation by blocking cyclooxygenase enzymes.",
    "SSRI": "Selective serotonin reuptake inhibitors (SSRIs) increase serotonin levels in the brain and are used to treat depression and anxiety disorders.",
    "SSRIs": "Selective serotonin reuptake inhibitors (SSRIs) increase serotonin levels in the brain and are used to treat depression and anxiety disorders.",
    "SNRI": "Serotonin-norepinephrine reuptake inhibitors (SNRIs) raise serotonin and norepinephrine levels, used for depression, anxiety, and chronic pain.",
    "ACE Inhibitor": "ACE inhibitors block the angiotensin-converting enzyme to lower blood pressure and treat heart failure.",
    "ACE Inhibitors": "ACE inhibitors block the angiotensin-converting enzyme to lower blood pressure and treat heart failure.",
    "ARB": "Angiotensin II receptor blockers (ARBs) relax blood vessels by blocking angiotensin II, used to treat hypertension and heart failure.",
    "Beta Blocker": "Beta blockers slow the heart rate and lower blood pressure by blocking adrenaline effects on beta receptors.",
    "Beta Blockers": "Beta blockers slow the heart rate and lower blood pressure by blocking adrenaline effects on beta receptors.",
    "Calcium Channel Blocker": "Calcium channel blockers relax blood vessels and reduce the heart's workload by blocking calcium entry into cardiac and smooth muscle cells.",
    "Statin": "Statins lower LDL cholesterol by inhibiting HMG-CoA reductase in the liver, reducing the risk of cardiovascular events.",
    "Statins": "Statins lower LDL cholesterol by inhibiting HMG-CoA reductase in the liver, reducing the risk of cardiovascular events.",
    "PPI": "Proton pump inhibitors (PPIs) suppress stomach acid production by blocking the H+/K+ ATPase pump, used for GERD and ulcers.",
    "Proton Pump Inhibitor": "Proton pump inhibitors (PPIs) suppress stomach acid production by blocking the H+/K+ ATPase pump, used for GERD and ulcers.",
    "Antibiotic": "Antibiotics kill or inhibit bacteria and are used to treat bacterial infections.",
    "Antibiotics": "Antibiotics kill or inhibit bacteria and are used to treat bacterial infections.",
    "Antihistamine": "Antihistamines block histamine receptors to relieve allergy symptoms such as sneezing, itching, and runny nose.",
    "Antihistamines": "Antihistamines block histamine receptors to relieve allergy symptoms such as sneezing, itching, and runny nose.",
    "Benzodiazepine": "Benzodiazepines enhance GABA activity in the brain to produce calming effects, used for anxiety, insomnia, and seizures.",
    "Opioid": "Opioids bind to opioid receptors to relieve moderate to severe pain; they carry risk of dependence and respiratory depression.",
    "Opioids": "Opioids bind to opioid receptors to relieve moderate to severe pain; they carry risk of dependence and respiratory depression.",
    "Corticosteroid": "Corticosteroids reduce inflammation and suppress the immune response, used for asthma, allergies, and autoimmune conditions.",
    "Diuretic": "Diuretics increase urine output to remove excess fluid, used for hypertension, heart failure, and edema.",
    "Biguanide": "Biguanides such as metformin lower blood glucose by reducing hepatic glucose production, used as first-line therapy for type 2 diabetes.",
}


@app.route("/drug-class/<slug>")
def drug_class_page(slug):
    cls = DrugClass.query.filter_by(slug=slug).first_or_404()
    sort = (request.args.get("sort") or "name").lower()
    drugs_q = Drug.query.filter_by(drug_class_id=cls.id)
    if sort == "rating":
        drugs = drugs_q.order_by(Drug.avg_rating.desc(), Drug.generic_name).all()
    elif sort == "reviews":
        drugs = drugs_q.order_by(Drug.review_count.desc(), Drug.generic_name).all()
    else:
        sort = "name"
        drugs = drugs_q.order_by(Drug.generic_name).all()
    related = (
        DrugClass.query.filter(DrugClass.id != cls.id)
        .order_by(DrugClass.name)
        .limit(8)
        .all()
    )

    class_description = cls.description
    if not class_description:
        class_description = (
            CLASS_DESCRIPTIONS.get(cls.name)
            or CLASS_DESCRIPTIONS.get((cls.name or "").rstrip("s"))
        )

    drug_ids = [d.id for d in drugs]
    common_conditions = []
    if drug_ids:
        cond_counts = (
            db.session.query(
                DrugCondition.condition_id,
                db.func.count(DrugCondition.drug_id),
            )
            .filter(DrugCondition.drug_id.in_(drug_ids))
            .group_by(DrugCondition.condition_id)
            .order_by(db.func.count(DrugCondition.drug_id).desc())
            .limit(8)
            .all()
        )
        if cond_counts:
            ids = [cid for cid, _ in cond_counts]
            cond_map = {
                c.id: c
                for c in Condition.query.filter(Condition.id.in_(ids)).all()
            }
            for cid, n in cond_counts:
                c = cond_map.get(cid)
                if c:
                    common_conditions.append({"condition": c, "count": n})

    notable_drugs = sorted(
        drugs,
        key=lambda d: (-(d.avg_rating or 0), -(d.review_count or 0), d.generic_name),
    )[:5]

    return render_template(
        "drug_class.html",
        drug_class=cls,
        drugs=drugs,
        related_classes=related,
        sort=sort,
        drug_count=len(drugs),
        class_description=class_description,
        common_conditions=common_conditions,
        notable_drugs=notable_drugs,
    )


@app.route("/news/")
def news_index():
    cat = request.args.get("cat", "")
    q = request.args.get("q", "")
    query = NewsArticle.query
    if cat:
        query = query.filter_by(category=cat)
    if q:
        query = query.filter(db.or_(
            NewsArticle.title.ilike(f"%{q}%"),
            NewsArticle.body.ilike(f"%{q}%")
        ))
    articles = query.order_by(NewsArticle.published_at.desc()).limit(30).all()
    categories = ["New Drug Approvals", "Medical", "FDA Alerts", "Clinical Trials", "Health"]
    fda_alerts = NewsArticle.query.filter(
        NewsArticle.category.in_(["FDA Alerts", "Safety"])
    ).order_by(NewsArticle.published_at.desc()).limit(4).all()
    return render_template("news.html", articles=articles, active_category=cat, active_cat=cat or None, categories=categories, search_query=q, fda_alerts=fda_alerts)


@app.route("/news/<slug>-<int:article_id>")
def news_article_slug(slug, article_id):
    return news_article(article_id)


@app.route("/news/article/<int:article_id>")
def news_article(article_id):
    article = NewsArticle.query.get_or_404(article_id)
    related = (
        NewsArticle.query.filter(
            NewsArticle.category == article.category,
            NewsArticle.id != article.id,
        )
        .order_by(NewsArticle.published_at.desc())
        .limit(5)
        .all()
    )
    return render_template("news_article.html", article=article, related=related)


@app.route("/news/<category>")
def news_category(category):
    cat_map = {
        "new-drug-approvals": "New Drug Approvals",
        "new drug approvals": "New Drug Approvals",
        "medical": "Medical",
        "fda-alerts": "FDA Alerts",
        "fda alerts": "FDA Alerts",
        "clinical-trials": "Clinical Trials",
        "clinical trials": "Clinical Trials",
        "health": "Health",
    }
    cat = cat_map.get(category.lower()) or (category if category in cat_map.values() else None)
    if not cat:
        abort(404)
    articles = NewsArticle.query.filter_by(category=cat).order_by(NewsArticle.published_at.desc()).all()
    categories = list(cat_map.values())
    fda_alerts = NewsArticle.query.filter(
        NewsArticle.category.in_(["FDA Alerts", "Safety"])
    ).order_by(NewsArticle.published_at.desc()).limit(4).all()
    return render_template("news.html", articles=articles, categories=categories, active_cat=cat, fda_alerts=fda_alerts)


@app.route("/drug-classes")
@app.route("/drug-classes.html")
def drug_classes_list():
    classes = DrugClass.query.order_by(DrugClass.name).all()
    for c in classes:
        c.drug_count_val = Drug.query.filter_by(drug_class_id=c.id).count()
    return render_template("drug_classes.html", classes=classes)


@app.route("/conditions")
@app.route("/conditions.html")
def conditions_list():
    all_conditions = Condition.query.order_by(Condition.name).all()
    condition_drug_counts = dict(
        db.session.query(
            DrugCondition.condition_id, db.func.count(DrugCondition.drug_id)
        )
        .group_by(DrugCondition.condition_id)
        .all()
    )
    for c in all_conditions:
        computed = condition_drug_counts.get(c.id, 0)
        if c.drug_count is None or c.drug_count == 0:
            c.drug_count = computed
    all_letters = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ') + ['0-9']
    active_letter = (request.args.get("letter") or "").upper().strip() or None
    if active_letter == '0-9':
        conditions = [c for c in all_conditions if c.name and not c.name[0].isalpha()]
    elif active_letter:
        conditions = [c for c in all_conditions if c.name and c.name[0].upper() == active_letter]
    else:
        conditions = all_conditions
    top_slugs = ["hypertension", "diabetes", "depression", "asthma", "anxiety",
                 "high_cholesterol", "heart_disease", "migraine", "gerd", "arthritis"]
    by_slug = {c.slug: c for c in all_conditions}
    top_conditions = [by_slug[s] for s in top_slugs if s in by_slug]
    if len(top_conditions) < 6:
        extras = sorted(all_conditions, key=lambda c: -(c.drug_count or 0))
        for c in extras:
            if c not in top_conditions:
                top_conditions.append(c)
            if len(top_conditions) >= 8:
                break
    top_conditions = top_conditions[:8]

    # Featured conditions: those with the most drugs (independent of curated top list).
    featured_conditions = sorted(
        all_conditions, key=lambda c: (-(c.drug_count or 0), c.name)
    )[:8]
    featured_conditions = [c for c in featured_conditions if (c.drug_count or 0) > 0]

    # Group conditions alphabetically for letter section headers.
    grouped_conditions = {}
    for c in conditions:
        if not c.name:
            continue
        first = c.name[0].upper()
        if not first.isalpha():
            first = "0-9"
        grouped_conditions.setdefault(first, []).append(c)
    grouped_keys = sorted(
        grouped_conditions.keys(), key=lambda k: (k == "0-9", k)
    )

    return render_template("conditions.html",
                           conditions=conditions,
                           all_letters=all_letters,
                           active_letter=active_letter,
                           top_conditions=top_conditions,
                           condition_drug_counts=condition_drug_counts,
                           featured_conditions=featured_conditions,
                           grouped_conditions=grouped_conditions,
                           grouped_keys=grouped_keys)


SYMPTOM_BODY_SYSTEMS = [
    ("Head & Neurological", [
        "Headache", "Dizziness", "Fatigue", "Memory problems", "Confusion",
    ]),
    ("Respiratory", [
        "Cough", "Shortness of breath", "Wheezing", "Congestion", "Sore throat",
    ]),
    ("Cardiovascular", [
        "Chest pain", "Rapid heartbeat", "High blood pressure", "Swelling",
    ]),
    ("Digestive", [
        "Nausea", "Vomiting", "Diarrhea", "Constipation", "Abdominal pain", "Heartburn",
    ]),
    ("Musculoskeletal", [
        "Joint pain", "Muscle pain", "Back pain", "Weakness",
    ]),
    ("Skin", [
        "Rash", "Itching", "Hives", "Dry skin",
    ]),
    ("Mental Health", [
        "Anxiety", "Depression", "Insomnia", "Mood changes",
    ]),
]

# Map symptom name -> list of condition slugs that commonly present with it.
SYMPTOM_CONDITION_MAP = {
    "Headache": ["migraine", "hypertension", "anxiety"],
    "Dizziness": ["hypertension", "anemia", "anxiety"],
    "Fatigue": ["hypothyroidism", "anemia", "depression", "diabetes"],
    "Memory problems": ["depression", "anxiety"],
    "Confusion": ["depression", "anemia"],
    "Cough": ["asthma", "copd", "influenza", "bacterial_infections"],
    "Shortness of breath": ["asthma", "copd", "heart_disease", "anemia"],
    "Wheezing": ["asthma", "copd"],
    "Congestion": ["influenza", "viral_infections"],
    "Sore throat": ["influenza", "bacterial_infections", "viral_infections"],
    "Chest pain": ["heart_disease", "acid_reflux", "anxiety"],
    "Rapid heartbeat": ["hyperthyroidism", "anxiety", "heart_disease"],
    "High blood pressure": ["hypertension", "heart_disease"],
    "Swelling": ["heart_disease", "arthritis", "gout"],
    "Nausea": ["nausea", "migraine", "acid_reflux"],
    "Vomiting": ["nausea", "influenza"],
    "Diarrhea": ["diarrhea", "crohns_disease", "bacterial_infections"],
    "Constipation": ["constipation", "hypothyroidism"],
    "Abdominal pain": ["acid_reflux", "crohns_disease", "constipation"],
    "Heartburn": ["acid_reflux"],
    "Joint pain": ["arthritis", "gout", "lupus"],
    "Muscle pain": ["muscle_spasm", "influenza"],
    "Back pain": ["muscle_spasm", "osteoporosis"],
    "Weakness": ["anemia", "hypothyroidism", "vitamin_deficiency"],
    "Rash": ["eczema", "psoriasis", "lupus"],
    "Itching": ["eczema", "psoriasis", "acne"],
    "Hives": ["eczema"],
    "Dry skin": ["eczema", "psoriasis", "hypothyroidism"],
    "Anxiety": ["anxiety", "depression"],
    "Depression": ["depression", "anxiety", "hypothyroidism"],
    "Insomnia": ["anxiety", "depression", "menopause"],
    "Mood changes": ["depression", "anxiety", "menopause"],
}


@app.route("/symptom-checker", methods=["GET", "POST"])
@app.route("/symptom-checker.html", methods=["GET", "POST"])
@app.route("/symptom_checker.html", methods=["GET", "POST"])
def symptom_checker():
    """Symptom checker: pick symptoms grouped by body system, see possible conditions.

    Selected symptoms come in via ``?symptom=X&symptom=Y`` (GET) or a form POST.
    Each symptom maps to a small static list of condition slugs; the union of
    those slugs is resolved against the ``Condition`` table and ranked by how
    many of the chosen symptoms point to each condition.
    """
    if request.method == "POST":
        selected = request.form.getlist("symptom")
    else:
        selected = request.args.getlist("symptom")
    selected_set = {s for s in selected if s in SYMPTOM_CONDITION_MAP}

    # Count how many selected symptoms point to each condition slug.
    slug_hits = {}
    for sym in selected_set:
        for slug in SYMPTOM_CONDITION_MAP.get(sym, []):
            slug_hits[slug] = slug_hits.get(slug, 0) + 1

    possible_conditions = []
    if slug_hits:
        conds = Condition.query.filter(Condition.slug.in_(list(slug_hits.keys()))).all()
        by_slug = {c.slug: c for c in conds}
        for slug, hits in sorted(slug_hits.items(), key=lambda kv: (-kv[1], kv[0])):
            c = by_slug.get(slug)
            if c is not None:
                possible_conditions.append((c, hits))

    return render_template(
        "symptom_checker.html",
        body_systems=SYMPTOM_BODY_SYSTEMS,
        selected=selected_set,
        possible_conditions=possible_conditions,
        total_selected=len(selected_set),
    )


# --- Auth ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        flash("Welcome back!", "success")
        return redirect(request.args.get("next") or url_for("account"))
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        flash("Account created.", "success")
        return redirect(url_for("account"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/my-account.html")
@app.route("/account")
@login_required
def account():
    reviews = DrugReview.query.filter_by(user_id=current_user.id).order_by(DrugReview.created_at.desc()).all()
    saved_count = SavedDrug.query.filter_by(user_id=current_user.id).count()
    recently_viewed_slugs = session.get("recently_viewed", [])
    recently_viewed = []
    if recently_viewed_slugs:
        recently_viewed = Drug.query.filter(Drug.slug.in_(recently_viewed_slugs)).all()
        slug_order = {s: i for i, s in enumerate(recently_viewed_slugs)}
        recently_viewed.sort(key=lambda d: slug_order.get(d.slug, 99))
    return render_template("account.html", reviews=reviews, saved_count=saved_count,
                           recently_viewed=recently_viewed,
                           recently_viewed_count=len(recently_viewed_slugs))


@app.route("/my-med-list.html")
@app.route("/my-med-list")
@login_required
def my_med_list():
    items = SavedDrug.query.filter_by(user_id=current_user.id).order_by(SavedDrug.created_at.desc()).all()
    return render_template("my_med_list.html", items=items)


@app.route("/my-med-list/toggle", methods=["POST"])
@login_required
def my_med_list_toggle():
    data = request.get_json(silent=True) or {}
    slug = data.get("slug") or request.form.get("slug")
    drug = Drug.query.filter_by(slug=slug).first()
    if not drug:
        if request.is_json:
            return jsonify({"ok": False, "error": "drug_not_found"}), 404
        return redirect(url_for("my_med_list"))
    existing = SavedDrug.query.filter_by(user_id=current_user.id, drug_id=drug.id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        if request.is_json:
            return jsonify({"ok": True, "saved": False})
        return redirect(url_for("my_med_list"))
    db.session.add(SavedDrug(user_id=current_user.id, drug_id=drug.id))
    db.session.commit()
    if request.is_json:
        return jsonify({"ok": True, "saved": True})
    return redirect(url_for("my_med_list"))


@app.route("/pro/")
@app.route("/pro")
def pro_edition():
    classes = DrugClass.query.order_by(DrugClass.name).all()
    return render_template("pro_edition.html", classes=classes)


@app.route("/compare/")
@app.route("/compare")
def compare_drugs():
    def _lookup(q):
        if not q:
            return None
        q = q.strip()
        if not q:
            return None
        d = Drug.query.filter(db.func.lower(Drug.slug) == q.lower()).first()
        if d:
            return d
        d = Drug.query.filter(db.func.lower(Drug.generic_name) == q.lower()).first()
        if d:
            return d
        # brand name fallback (substring match against brand_names_json)
        return Drug.query.filter(Drug.brand_names_json.ilike(f"%{q}%")).first()

    def _dosage_forms(drug):
        if not drug:
            return "—"
        shapes = {img.shape for img in drug.images if img.shape}
        return ", ".join(sorted(shapes)) if shapes else "Tablet"

    drug1 = _lookup(request.args.get("drug1", ""))
    drug2 = _lookup(request.args.get("drug2", ""))
    drug3 = _lookup(request.args.get("drug3", ""))
    popular = Drug.query.order_by(Drug.review_count.desc()).limit(20).all()
    dosage_forms = {
        "drug1": _dosage_forms(drug1),
        "drug2": _dosage_forms(drug2),
        "drug3": _dosage_forms(drug3),
    }
    return render_template(
        "compare_drugs.html",
        drug1=drug1,
        drug2=drug2,
        drug3=drug3,
        popular=popular,
        dosage_forms=dosage_forms,
    )


@app.route("/account/reviews")
@login_required
def my_reviews():
    reviews = DrugReview.query.filter_by(user_id=current_user.id).order_by(DrugReview.created_at.desc()).all()
    return render_template("my_reviews.html", reviews=reviews)


@app.route("/account/reviews/<int:review_id>/delete", methods=["POST"])
@login_required
def delete_review(review_id):
    review = DrugReview.query.filter_by(id=review_id, user_id=current_user.id).first_or_404()
    db.session.delete(review)
    db.session.commit()
    return redirect(url_for("my_reviews"))


@app.route("/my-med-list/notes", methods=["POST"])
@login_required
def update_med_notes():
    slug = request.form.get("slug")
    notes = request.form.get("notes", "")
    drug = Drug.query.filter_by(slug=slug).first_or_404()
    item = SavedDrug.query.filter_by(user_id=current_user.id, drug_id=drug.id).first_or_404()
    item.notes = notes[:500]
    db.session.commit()
    return redirect(url_for("my_med_list"))


@app.route("/account/settings")
@login_required
def account_settings():
    return render_template("account_settings.html")


@app.route("/account/settings/save", methods=["POST"])
@login_required
def save_settings():
    flash("Settings saved.", "success")
    return redirect(url_for("account_settings"))


@app.route("/account/subscriptions")
@login_required
def account_subscriptions():
    return render_template("account_subscriptions.html")


@app.route("/account/subscriptions/save", methods=["POST"])
@login_required
def save_subscriptions():
    flash("Email preferences saved.", "success")
    return redirect(url_for("account_subscriptions"))


@app.route("/sitemap")
@app.route("/sitemap.html")
def sitemap():
    classes = DrugClass.query.order_by(DrugClass.name).all()
    conditions = Condition.query.order_by(Condition.name).all()
    return render_template("sitemap.html", classes=classes, conditions=conditions)


SIDE_EFFECTS_AZ = [
    "Abdominal pain", "Acne", "Agitation", "Allergic reaction", "Anemia",
    "Anxiety", "Appetite loss", "Arrhythmia", "Back pain", "Bleeding",
    "Bloating", "Blurred vision", "Bruising", "Chest pain", "Chills",
    "Confusion", "Constipation", "Cough", "Cramps", "Depression",
    "Diarrhea", "Dizziness", "Drowsiness", "Dry mouth", "Edema",
    "Fatigue", "Fever", "Flushing", "Gas", "Hair loss",
    "Headache", "Heartburn", "Hypertension", "Hypotension", "Indigestion",
    "Insomnia", "Itching", "Jaundice", "Joint pain", "Liver damage",
    "Muscle pain", "Nausea", "Nervousness", "Numbness", "Palpitations",
    "Rash", "Restlessness", "Ringing in ears", "Seizures", "Shortness of breath",
    "Skin reaction", "Sore throat", "Stomach upset", "Sweating", "Swelling",
    "Tachycardia", "Tremor", "Vomiting", "Weakness", "Weight gain",
    "Weight loss",
]

MOST_SEARCHED_SIDE_EFFECTS = [
    "Nausea", "Headache", "Dizziness", "Drowsiness", "Fatigue",
    "Diarrhea", "Constipation", "Insomnia", "Weight gain", "Rash",
]


@app.route("/side-effects/")
@app.route("/side-effects")
def side_effects_page():
    """Side Effects A-Z index page.

    Renders an alphabetical directory of common side effect names with an
    A-Z letter navigation, a search box, a "most commonly searched" list,
    and (when ``?q=`` is supplied) drugs whose ``side_effects`` text matches.
    """
    q = (request.args.get("q") or "").strip()
    drugs = []
    if q:
        drugs = Drug.query.filter(Drug.side_effects.ilike(f"%{q}%")).limit(30).all()

    # Group the curated A-Z list by first letter for the directory grid.
    by_letter = {}
    for name in SIDE_EFFECTS_AZ:
        letter = name[0].upper()
        by_letter.setdefault(letter, []).append(name)
    for letter in by_letter:
        by_letter[letter].sort()
    letters = sorted(by_letter.keys())
    all_letters = list(string.ascii_uppercase)

    popular = Drug.query.order_by(Drug.review_count.desc()).limit(10).all()
    return render_template(
        "side_effects.html",
        drugs=drugs, query=q, popular=popular,
        by_letter=by_letter, letters=letters, all_letters=all_letters,
        most_searched=MOST_SEARCHED_SIDE_EFFECTS,
    )


@app.route("/warnings/")
@app.route("/blackbox-warnings")
def warnings_index():
    drugs_with_warnings = Drug.query.filter(Drug.warnings.isnot(None)).order_by(Drug.generic_name).limit(50).all()
    return render_template("warnings_index.html", drugs=drugs_with_warnings)


@app.route("/newsletter")
def newsletter():
    return render_template("newsletter.html")


@app.route("/newsletter/subscribe", methods=["POST"])
def newsletter_subscribe():
    email = request.form.get("email", "")
    flash(f"Thank you! {email} has been subscribed to our newsletter.", "success")
    return redirect(url_for("newsletter"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/<slug>/images")
def drug_images(slug):
    drug = Drug.query.filter_by(slug=slug).first_or_404()
    images = DrugImage.query.filter_by(drug_id=drug.id).all()
    return render_template("drug_images.html", drug=drug, images=images)


def generate_drug_prices(drug):
    """Build a deterministic per-pharmacy price table for a drug.

    Pricing tier is chosen from drug attributes:
      * Controlled substances (`csa_schedule` starts with "Schedule") use a
        mid-to-high band ($40-$220 / 30-day supply).
      * Brand-only drugs (Rx, has brand names, no generic equivalent flag)
        use the brand band ($80-$520 / 30-day supply).
      * OTC drugs use a low band ($4-$25 / 30-day supply).
      * Everything else (generic Rx) uses $6-$45 / 30-day supply.

    A per-drug seed (derived from id + generic_name length) drives small
    deterministic variation across pharmacies so the table looks plausible
    without random noise per request.

    Returns a list of dicts:
        {pharmacy, unit_price, supply_price, coupon, savings_pct}
    plus a `base_retail` value usable as the "average retail" anchor.
    """
    seed = (drug.id * 31 + len(drug.generic_name or "") * 7) % 997
    csa = (drug.csa_schedule or "").lower()
    avail = (drug.availability or "Rx").lower()
    brands = drug.brand_names or []

    if csa.startswith("schedule"):
        base = 40 + (seed % 180)
        tier = "controlled"
    elif "otc" in avail:
        base = 4 + (seed % 22)
        tier = "otc"
    elif brands and "rx" in avail:
        # Brand-name Rx drugs skew expensive.
        base = 80 + (seed % 440)
        tier = "brand"
    else:
        base = 6 + (seed % 40)
        tier = "generic"

    pharmacies = [
        ("CVS Pharmacy",     1.12, True),
        ("Walgreens",        1.15, True),
        ("Walmart Pharmacy", 0.88, False),
        ("Rite Aid",         1.06, True),
        ("Costco Pharmacy",  0.82, False),
        ("GoodRx Price",     0.55, True),
    ]

    rows = []
    for i, (name, mult, coupon) in enumerate(pharmacies):
        # tiny deterministic jitter so prices aren't perfect multiples
        jitter = ((seed + i * 13) % 7) / 100.0  # 0.00 .. 0.06
        supply = round(base * (mult + jitter), 2)
        # Assume 30 tablets/capsules per 30-day supply for unit price.
        unit = round(supply / 30.0, 2)
        savings = max(0, int(round((1 - supply / (base * 1.15)) * 100)))
        rows.append({
            "pharmacy": name,
            "unit_price": unit,
            "supply_price": supply,
            "coupon": coupon,
            "savings_pct": savings,
        })

    return {
        "tier": tier,
        "base_retail": round(base * 1.15, 2),
        "rows": rows,
        "has_generic": bool(brands),  # if it has brand names, a generic equivalent exists too
        "brand_price": round(base * 4.2, 2) if tier == "generic" and brands else None,
        "generic_price": round(base * 0.95, 2) if tier == "brand" else None,
    }


@app.route("/<slug>/prices")
def drug_prices(slug):
    drug = Drug.query.filter_by(slug=slug).first_or_404()
    price_data = generate_drug_prices(drug)
    return render_template("drug_prices.html", drug=drug, price_data=price_data)


@app.route("/<slug>/dosage")
def drug_dosage(slug):
    drug = Drug.query.filter_by(slug=slug).first_or_404()
    return render_template("drug_dosage.html", drug=drug)


@app.route("/<slug>/side-effects")
def drug_side_effects(slug):
    drug = Drug.query.filter_by(slug=slug).first_or_404()
    return render_template("drug_side_effects.html", drug=drug)


@app.route("/<slug>/pregnancy")
def drug_pregnancy(slug):
    drug = Drug.query.filter_by(slug=slug).first_or_404()
    return render_template("drug_pregnancy.html", drug=drug)


@app.route("/<slug>/warnings")
def drug_warnings(slug):
    drug = Drug.query.filter_by(slug=slug).first_or_404()
    text = (drug.warnings or "").strip()
    boxed_warning = None
    lowered = text.lower()
    if "boxed warning" in lowered or "black box" in lowered:
        for para in text.split("\n\n"):
            if "boxed warning" in para.lower() or "black box" in para.lower():
                boxed_warning = para.strip()
                break
        if not boxed_warning:
            boxed_warning = text[:400]
    categories = [
        ("Before taking this medicine",
         ["allerg", "pregnan", "breastfeed", "tell your doctor", "medical history",
          "kidney", "liver", "heart"]),
        ("Serious side effects to watch for",
         ["severe", "stop taking", "emergency", "call your doctor", "seek medical",
          "anaphyla", "bleeding", "skin reaction"]),
        ("Drug and food interactions",
         ["other medic", "interaction", "alcohol", "grapefruit", "food"]),
        ("Special populations",
         ["children", "elderly", "older adults", "pediatric", "geriatric"]),
    ]
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) <= 1 and text:
        # Try sentence-split if no paragraph breaks.
        import re
        paragraphs = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    categorized = {name: [] for name, _ in categories}
    general = []
    for p in paragraphs:
        pl = p.lower()
        if boxed_warning and p in boxed_warning:
            continue
        placed = False
        for name, kws in categories:
            if any(k in pl for k in kws):
                categorized[name].append(p)
                placed = True
                break
        if not placed:
            general.append(p)
    cards = [(name, items) for name, items in categorized.items() if items]
    if general:
        cards.append(("General warnings", general))
    return render_template("drug_warnings.html",
                           drug=drug,
                           boxed_warning=boxed_warning,
                           warning_cards=cards)


@app.route("/<slug>/interactions")
def drug_interactions_page(slug):
    drug = Drug.query.filter_by(slug=slug).first_or_404()
    interactions = DrugInteraction.query.filter(
        db.or_(DrugInteraction.drug_a_id == drug.id, DrugInteraction.drug_b_id == drug.id)
    ).all()
    interaction_details = []
    for i in interactions:
        other_id = i.drug_b_id if i.drug_a_id == drug.id else i.drug_a_id
        other = Drug.query.get(other_id)
        if other is None:
            continue
        interaction_details.append({
            'other_drug': other,
            'severity': i.severity,
            'description': i.description,
        })
    sev_order = {'major': 0, 'moderate': 1, 'minor': 2, 'unknown': 3}
    interaction_details.sort(key=lambda x: sev_order.get(x['severity'], 3))
    summary = {
        'total': len(interaction_details),
        'major': sum(1 for x in interaction_details if x['severity'] == 'major'),
        'moderate': sum(1 for x in interaction_details if x['severity'] == 'moderate'),
        'minor': sum(1 for x in interaction_details if x['severity'] == 'minor'),
    }
    return render_template(
        "drug_interactions_page.html",
        drug=drug,
        interactions=interaction_details,
        summary=summary,
    )


@app.route("/_health")
def health():
    return {"ok": True, "site": "drugs_com"}


@app.errorhandler(404)
def not_found(e):
    return render_template("base.html", not_found=True), 404


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
def init_app():
    with app.app_context():
        db.create_all()
        seed_database()


init_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
