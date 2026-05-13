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
    if DrugClass.query.count() > 0:
        return
    for name, desc in DRUG_CLASSES:
        db.session.add(DrugClass(name=name, slug=slugify(name), description=desc))
    db.session.commit()


def seed_conditions():
    if Condition.query.count() > 0:
        return
    for slug, name, desc in CONDITIONS_DATA:
        db.session.add(Condition(name=name, slug=slug, description=desc))
    db.session.commit()


def seed_drugs():
    if Drug.query.count() > 0:
        return
    cls_by_name = {c.name: c.id for c in DrugClass.query.all()}
    featured_targets = {"ibuprofen", "metformin", "lisinopril", "sertraline", "atorvastatin", "semaglutide", "amoxicillin", "levothyroxine"}
    for entry in DRUGS_DATA:
        gname, cname, avail, csa, pron, brands, conds = entry
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
    if DrugCondition.query.count() > 0:
        return
    cond_by_slug = {c.slug: c for c in Condition.query.all()}
    for d in Drug.query.all():
        for c_slug in d.conditions_list:
            c = cond_by_slug.get(c_slug)
            if c:
                db.session.add(DrugCondition(drug_id=d.id, condition_id=c.id))
    db.session.commit()
    # Update denormalized drug_count
    for c in Condition.query.all():
        c.drug_count = DrugCondition.query.filter_by(condition_id=c.id).count()
    db.session.commit()


def seed_pill_images():
    if DrugImage.query.count() > 0:
        return
    drug_by_name = {d.generic_name: d for d in Drug.query.all()}
    for gname, imprint, shape, color, strength, mfg in PILL_IMAGES_DATA:
        d = drug_by_name.get(gname)
        if not d:
            continue
        db.session.add(DrugImage(
            drug_id=d.id, imprint=imprint, shape=shape, color=color,
            strength=strength, manufacturer=mfg,
        ))
    db.session.commit()


def seed_interactions():
    if DrugInteraction.query.count() > 0:
        return
    drug_by_name = {d.generic_name: d for d in Drug.query.all()}
    for a, b, sev, desc in INTERACTIONS_DATA:
        da = drug_by_name.get(a)
        db_ = drug_by_name.get(b)
        if not da or not db_:
            continue
        db.session.add(DrugInteraction(drug_a_id=da.id, drug_b_id=db_.id, severity=sev, description=desc))
    db.session.commit()


def seed_news():
    if NewsArticle.query.count() > 0:
        return
    now = datetime.utcnow()
    for i, (title, cat, body) in enumerate(NEWS_DATA):
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
    if DrugReview.query.count() >= 40:
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
               "semaglutide", "fluoxetine", "amlodipine", "tramadol", "zolpidem"]
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
            if count >= 55:
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
    trending = Drug.query.order_by(Drug.review_count.desc()).limit(10).all()
    news = NewsArticle.query.order_by(NewsArticle.published_at.desc()).limit(6).all()
    classes = DrugClass.query.order_by(DrugClass.name).limit(12).all()
    return render_template("index.html", featured=featured, trending=trending,
                           news=news, classes=classes)


@app.route("/drug_information.html")
@app.route("/drugs-a-to-z.html")
def drug_az():
    letter = (request.args.get("letter") or "A").upper()
    if letter not in string.ascii_uppercase:
        letter = "A"
    drugs = Drug.query.filter(Drug.generic_name.ilike(f"{letter}%")).order_by(Drug.generic_name).all()
    return render_template("drug_az.html", letter=letter, drugs=drugs)


@app.route("/<slug>.html")
def drug_detail(slug):
    drug = Drug.query.filter_by(slug=slug).first()
    if not drug:
        abort(404)
    reviews = DrugReview.query.filter_by(drug_id=drug.id).order_by(DrugReview.helpful_count.desc()).limit(20).all()
    related = Drug.query.filter(Drug.generic_name.in_(drug.related_drugs)).all()
    cond_by_slug = {c.slug: c for c in Condition.query.all()}
    drug_conditions = [cond_by_slug[s] for s in drug.conditions_list if s in cond_by_slug]
    saved = False
    if current_user.is_authenticated:
        saved = SavedDrug.query.filter_by(user_id=current_user.id, drug_id=drug.id).first() is not None
    return render_template("drug_detail.html", drug=drug, reviews=reviews,
                           related=related, drug_conditions=drug_conditions, saved=saved)


@app.route("/search")
def search():
    q = (request.args.get("q") or "").strip()
    class_slug = request.args.get("class") or ""
    cond_slug = request.args.get("condition") or ""
    avail = request.args.get("availability") or ""

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
    if tokens:
        scored = [(score_drug(d, tokens), d) for d in drugs]
        scored = [(s, d) for s, d in scored if s > 0]
        scored.sort(key=lambda x: (-x[0], x[1].generic_name))
        results = [d for _, d in scored]
    else:
        results = sorted(drugs, key=lambda d: d.generic_name)

    classes = DrugClass.query.order_by(DrugClass.name).all()
    conditions = Condition.query.order_by(Condition.name).all()
    return render_template("search.html", q=q, results=results,
                           classes=classes, conditions=conditions,
                           class_slug=class_slug, cond_slug=cond_slug, avail=avail)


@app.route("/drug_interactions.html")
@app.route("/interaction-checker/")
@app.route("/interaction-checker")
def interaction_checker():
    drugs = Drug.query.order_by(Drug.generic_name).all()
    return render_template("interaction_checker.html", drugs=drugs)


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
def condition_page(slug):
    cond = Condition.query.filter_by(slug=slug).first_or_404()
    links = DrugCondition.query.filter_by(condition_id=cond.id).all()
    drugs = [Drug.query.get(l.drug_id) for l in links]
    drugs = [d for d in drugs if d]
    drugs.sort(key=lambda d: -d.avg_rating)
    return render_template("condition.html", condition=cond, drugs=drugs)


@app.route("/drug-class/<slug>")
def drug_class_page(slug):
    cls = DrugClass.query.filter_by(slug=slug).first_or_404()
    drugs = Drug.query.filter_by(drug_class_id=cls.id).order_by(Drug.generic_name).all()
    return render_template("drug_class.html", drug_class=cls, drugs=drugs)


@app.route("/news/")
def news_index():
    articles = NewsArticle.query.order_by(NewsArticle.published_at.desc()).all()
    categories = ["New Drug Approvals", "Medical", "FDA Alerts", "Clinical Trials"]
    return render_template("news.html", articles=articles, categories=categories, active_cat=None)


@app.route("/news/article/<int:article_id>")
def news_article(article_id):
    article = NewsArticle.query.get_or_404(article_id)
    return render_template("news_article.html", article=article)


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
    }
    cat = cat_map.get(category.lower()) or (category if category in cat_map.values() else None)
    if not cat:
        abort(404)
    articles = NewsArticle.query.filter_by(category=cat).order_by(NewsArticle.published_at.desc()).all()
    categories = list(cat_map.values())
    return render_template("news.html", articles=articles, categories=categories, active_cat=cat)


@app.route("/drug-classes")
@app.route("/drug-classes.html")
def drug_classes_list():
    classes = DrugClass.query.order_by(DrugClass.name).all()
    return render_template("drug_class.html", drug_class=None, drugs=None, all_classes=classes)


@app.route("/conditions")
@app.route("/conditions.html")
def conditions_list():
    conditions = Condition.query.order_by(Condition.name).all()
    return render_template("condition.html", condition=None, drugs=None, all_conditions=conditions)


# --- Auth ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter(db.func.lower(User.email) == email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Welcome back!", "success")
            return redirect(request.args.get("next") or url_for("account"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not email or not username or not password:
            flash("All fields are required.", "error")
            return render_template("register.html")
        if User.query.filter(db.func.lower(User.email) == email).first():
            flash("Email already registered.", "error")
            return render_template("register.html")
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "error")
            return render_template("register.html")
        user = User(email=email, username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Account created.", "success")
        return redirect(url_for("account"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/account")
@login_required
def account():
    reviews = DrugReview.query.filter_by(user_id=current_user.id).order_by(DrugReview.created_at.desc()).all()
    saved_count = SavedDrug.query.filter_by(user_id=current_user.id).count()
    return render_template("account.html", reviews=reviews, saved_count=saved_count)


@app.route("/my-med-list")
@login_required
def my_med_list():
    items = SavedDrug.query.filter_by(user_id=current_user.id).order_by(SavedDrug.created_at.desc()).all()
    return render_template("my_med_list.html", items=items)


@app.route("/my-med-list/toggle", methods=["POST"])
@login_required
def my_med_list_toggle():
    data = request.get_json(silent=True) or {}
    slug = data.get("slug")
    drug = Drug.query.filter_by(slug=slug).first()
    if not drug:
        return jsonify({"ok": False, "error": "drug_not_found"}), 404
    existing = SavedDrug.query.filter_by(user_id=current_user.id, drug_id=drug.id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"ok": True, "saved": False})
    db.session.add(SavedDrug(user_id=current_user.id, drug_id=drug.id))
    db.session.commit()
    return jsonify({"ok": True, "saved": True})


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
