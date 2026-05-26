"""R4 data generator for cambridge_dictionary.

Outputs (all deterministic — every field derived via hashlib.md5 from the
slug, no time, no randomness):

  scraped_data/words_r4.json       — ~6000 new WordNet entries with
                                      register/freq_rank/etymology/
                                      collocations/mistake_note fields.
  scraped_data/mistakes_r4.json    — 60 mistake-corner topics.
  .r4_build/tasks_r4.jsonl         — 450+ new tasks ready to append.

Run once on the build host with NLTK + wordnet present:

  python3 sites/cambridge_dictionary/.r4_build/gen.py
"""
import hashlib
import json
import os
import re
from nltk.corpus import wordnet as wn

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
SCRAPED = os.path.join(SITE, 'scraped_data')

# ─── helpers ────────────────────────────────────────────────────────────────


def slugify(s):
    return re.sub(r'[^a-z0-9-]+', '-', s.lower()).strip('-')


def h(s, mod=None):
    """Stable integer hash from string."""
    n = int(hashlib.md5(s.encode('utf-8')).hexdigest()[:8], 16)
    return n if mod is None else n % mod


def pick(s, options, salt=''):
    return options[h(s + salt, len(options))]


# ─── existing slugs ─────────────────────────────────────────────────────────

existing_slugs = set()
for fname in ['words_existing.json', 'words_fetched.json', 'words_extra.json']:
    with open(os.path.join(SCRAPED, fname)) as f:
        for w in json.load(f):
            existing_slugs.add(w['slug'])

# Also load all existing headwords for tasks.
existing_headwords = []
with open(os.path.join(SCRAPED, 'words_existing.json')) as f:
    for w in json.load(f):
        existing_headwords.append(w['headword'])


# ─── WordNet candidate selection ────────────────────────────────────────────

WN_POS = {'n': 'noun', 'v': 'verb', 'a': 'adjective', 's': 'adjective',
          'r': 'adverb'}

# Pick lemmas: alphabetic only, length 4-18, not in existing.
candidates = []
for lemma in sorted(wn.all_lemma_names()):
    if '_' in lemma or '.' in lemma or "'" in lemma or '-' in lemma:
        continue
    if not lemma.isalpha() or not lemma.islower():
        continue
    if not (4 <= len(lemma) <= 18):
        continue
    sl = slugify(lemma)
    if not sl or sl in existing_slugs:
        continue
    candidates.append(lemma)

print(f'WordNet candidates: {len(candidates)}')

# Take ~5500 deterministic picks. Sort, then keep evenly spaced sample.
TARGET = 5500
if len(candidates) > TARGET:
    step = len(candidates) / TARGET
    picked = [candidates[int(i * step)] for i in range(TARGET)]
else:
    picked = candidates

# De-dup defensively.
seen = set()
picked2 = []
for w in picked:
    sl = slugify(w)
    if sl in seen or sl in existing_slugs:
        continue
    seen.add(sl)
    picked2.append(w)
picked = picked2
print(f'Picked: {len(picked)}')

# ─── word entry builder ────────────────────────────────────────────────────

LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
REGISTERS = ['', '', '', 'formal', 'informal', 'slang', 'archaic',
             'technical', 'literary', 'humorous']
TR_LANGS = ['chinese (traditional)', 'chinese (simplified)', 'spanish',
            'portuguese', 'french', 'italian', 'german', 'japanese', 'chinese']

# Hand-picked etymology root templates (deterministic pick by hash).
ETY_ROOTS = [
    ('Latin', 'Late Latin', '14th century'),
    ('Old French', 'Anglo-French', '12th century'),
    ('Greek', 'Late Greek', 'via Latin'),
    ('Old English', 'Proto-Germanic', 'before 900 AD'),
    ('Middle English', 'Old French', 'late 13th century'),
    ('Latin', 'Vulgar Latin', '15th century'),
    ('Arabic', 'Persian', 'via Spanish'),
    ('German', 'Old High German', '16th century'),
    ('Italian', 'Latin', '17th century'),
    ('Spanish', 'Latin', 'colonial era'),
    ('Sanskrit', 'Indo-European', 'via Greek'),
    ('Norse', 'Old Norse', 'Viking-era England'),
    ('Dutch', 'Middle Dutch', '15th century'),
    ('Celtic', 'Gaulish', 'pre-Roman Britain'),
    ('Yiddish', 'German', '19th century'),
]

# Collocation patterns by POS.
COLLOC_PATTERNS = {
    'noun': [
        ('verb', '{verb} {head}', 'She likes to {verb} the {head} every morning.'),
        ('adj', '{adj} {head}', 'The {adj} {head} was unexpected.'),
        ('prep', '{head} of', '{Head} of opportunity comes once.'),
        ('phrase', 'a {head} of', 'It was just a {head} of luck.'),
    ],
    'verb': [
        ('adv', '{head} {adv}', 'They {head} {adv}.'),
        ('obj', '{head} a {obj}', 'I {head} a {obj} every Sunday.'),
        ('prep', '{head} into', 'She {head}s into the role with energy.'),
    ],
    'adjective': [
        ('noun', '{head} {noun}', 'A {head} {noun} caught his eye.'),
        ('adv', 'extremely {head}', 'He looked extremely {head}.'),
        ('verb', 'feel {head}', 'I feel {head} about the result.'),
    ],
    'adverb': [
        ('verb', 'speak {head}', 'They spoke {head} during the meeting.'),
        ('verb', '{head} done', 'It was {head} done.'),
        ('clause', '{head}, the result was', '{Head}, the result was unclear.'),
    ],
}

VERB_FILL = ['use', 'find', 'see', 'know', 'study', 'follow', 'discuss']
ADJ_FILL = ['real', 'common', 'rare', 'simple', 'classic', 'modern']
ADV_FILL = ['quickly', 'softly', 'clearly', 'subtly']
NOUN_FILL = ['example', 'case', 'idea', 'moment', 'instance']
OBJ_FILL = ['plan', 'choice', 'lesson', 'memory']


def ety_for(slug):
    root, sub, when = ETY_ROOTS[h(slug, len(ETY_ROOTS))]
    surface = pick(slug, ['noun', 'verb', 'adjective', 'state'], salt='surf')
    return (f"From {root} (via {sub}), first attested in English {when}. "
            f"The modern English {surface} sense developed alongside cognates "
            f"in related languages. Compare with parallel forms across the "
            f"{root} family of vocabulary.")


def collocations_for(slug, pos):
    patterns = COLLOC_PATTERNS.get(pos, COLLOC_PATTERNS['noun'])
    out = []
    for i, (label, tmpl, ex_tmpl) in enumerate(patterns[:4]):
        verb = pick(slug + str(i), VERB_FILL)
        adj = pick(slug + str(i), ADJ_FILL)
        adv = pick(slug + str(i), ADV_FILL)
        noun = pick(slug + str(i), NOUN_FILL)
        obj = pick(slug + str(i), OBJ_FILL)
        phrase = tmpl.format(head=slug, verb=verb, adj=adj, adv=adv,
                             noun=noun, obj=obj, prep='of',
                             Head=slug.capitalize())
        ex = ex_tmpl.format(head=slug, verb=verb, adj=adj, adv=adv,
                            noun=noun, obj=obj, Head=slug.capitalize())
        out.append({'type': label, 'phrase': phrase, 'example': ex})
    return out


def mistake_note_for(slug, pos):
    templates = [
        f"Don't confuse '{slug}' with similar-sounding words; check the "
        f"definition before using.",
        f"In formal writing, '{slug}' is preferred over its colloquial "
        f"counterpart.",
        f"Note that '{slug}' is sometimes used incorrectly as a {pos} when "
        f"another form is appropriate — always check context.",
        f"Learners often misuse '{slug}' in collocations; see the "
        f"Collocations section for the correct partner words.",
        f"The pronunciation of '{slug}' is a common pitfall: the stress "
        f"falls earlier than many learners expect.",
        '',  # some words just don't have a note
    ]
    return templates[h(slug + 'mistake', len(templates))]


def translations_for(slug):
    bases = {
        'chinese (simplified)': '词',
        'chinese (traditional)': '詞',
        'chinese': '词',
        'spanish': 'palabra',
        'portuguese': 'palavra',
        'french': 'mot',
        'italian': 'parola',
        'german': 'Wort',
        'japanese': '言葉',
    }
    out = {}
    # Pick 4-6 languages deterministically.
    n = 4 + h(slug + 'tr', 3)
    keys = list(bases.keys())
    for i in range(n):
        k = keys[h(slug + str(i) + 'k', len(keys))]
        if k in out:
            continue
        # Append a stable disambiguator to avoid all words mapping to the
        # same base translation.
        suffix = h(slug + k, 999)
        out[k] = {'text': f'{bases[k]}-{suffix}', 'provider': 'Microsoft'}
    return out


def make_phonetic(word, region='uk'):
    # Simple deterministic IPA-like transcription. Real IPA would need a
    # phonemiser; this is good enough for "looks like IPA" rendering.
    # Pattern: insert primary-stress mark before second-to-last syllable.
    body = word.lower()
    # Pseudo IPA mapping
    rep = {'ch': 'tʃ', 'sh': 'ʃ', 'th': 'θ', 'ph': 'f', 'ng': 'ŋ',
           'a': 'æ' if region == 'us' else 'ɑː' if len(word) > 6 else 'æ',
           'e': 'e', 'i': 'ɪ', 'o': 'ɒ' if region == 'uk' else 'ɑː', 'u': 'ʌ',
           'y': 'i'}
    out = []
    i = 0
    while i < len(body):
        if i + 1 < len(body) and body[i:i+2] in rep:
            out.append(rep[body[i:i+2]])
            i += 2
        elif body[i] in rep:
            out.append(rep[body[i]])
            i += 1
        else:
            out.append(body[i])
            i += 1
    s = ''.join(out)
    # Insert stress mark at quarter-point.
    mid = max(1, len(word) // 3)
    return f"/{s[:mid]}ˈ{s[mid:]}/"


def definitions_for(slug, pos, synset):
    """Multi-sense definitions for a WordNet lemma, using up to 3 synsets."""
    synsets = wn.synsets(slug)[:3] or [synset]
    out = []
    for i, ss in enumerate(synsets):
        try:
            df = ss.definition()
        except Exception:
            df = f'A meaning of {slug}.'
        examples = list(ss.examples())[:2]
        if not examples:
            examples = [
                f"The word '{slug}' is commonly used in everyday English.",
                f"Researchers continue to study the use of '{slug}' across many contexts.",
            ]
        reg = REGISTERS[h(slug + str(i) + 'reg', len(REGISTERS))]
        grammar_note = ''
        if pos == 'noun':
            grammar_note = pick(slug + str(i), ['[C]', '[U]', '[C, U]'])
        elif pos == 'verb':
            grammar_note = pick(slug + str(i), ['[T]', '[I]', '[I, T]'])
        out.append({
            'sense_num': i + 1,
            'grammar_note': grammar_note,
            'definition': df[0].upper() + df[1:] if df else 'A meaning.',
            'examples': examples,
            'register': reg,
        })
    return out


# ─── build new word entries ────────────────────────────────────────────────

new_words = []
for lemma in picked:
    sl = slugify(lemma)
    synsets = wn.synsets(lemma)
    if not synsets:
        continue
    ss = synsets[0]
    pos_letter = ss.pos()
    pos = WN_POS.get(pos_letter, 'noun')
    guide = ss.definition()[:80].rstrip('.')
    p_uk = make_phonetic(lemma, 'uk')
    p_us = make_phonetic(lemma, 'us')
    level = LEVELS[h(sl + 'lvl', len(LEVELS))]
    register = REGISTERS[h(sl + 'wreg', len(REGISTERS))]
    # Frequency rank: deterministic 1..50000, but biased by level (A1 → low rank).
    base_rank = (LEVELS.index(level) + 1) * 5000
    freq_rank = base_rank - h(sl + 'fr', 4000)
    if freq_rank < 1:
        freq_rank = 1
    ety = ety_for(sl)
    coll = collocations_for(sl, pos)
    mistake = mistake_note_for(sl, pos)
    defs = definitions_for(lemma, pos, ss)
    tr = translations_for(sl)
    new_words.append({
        'headword': lemma,
        'slug': sl,
        'pos': pos,
        'guide_word': guide,
        'phonetic_uk': p_uk,
        'phonetic_us': p_us,
        'pronunciation_ipa': p_uk,
        'audio_uk_path': f'/static/audio/uk/{sl}.mp3',
        'audio_us_path': f'/static/audio/us/{sl}.mp3',
        'level': level,
        'definitions': defs,
        'translations': tr,
        'related': [],
        'synonyms': [s.name() for s in ss.lemmas() if s.name() != lemma][:8],
        'is_thesaurus_phrase': False,
        # R4 fields
        'register': register,
        'frequency_rank': freq_rank,
        'etymology': ety,
        'collocations': coll,
        'mistake_note': mistake,
    })

print(f'New words built: {len(new_words)}')

# Write words_r4.json
with open(os.path.join(SCRAPED, 'words_r4.json'), 'w', encoding='utf-8') as f:
    json.dump(new_words, f, ensure_ascii=False, sort_keys=True, indent=1)
print(f'Wrote scraped_data/words_r4.json')


# ─── mistake corner ─────────────────────────────────────────────────────────

MISTAKE_TOPICS = [
    ('affect-vs-effect', 'Affect vs effect', 'Grammar',
     "'Affect' is usually a verb meaning to influence; 'effect' is usually "
     "a noun meaning the result. The noun 'affect' (emotional state) and "
     "the verb 'effect' (to bring about) do exist but are rare.",
     [('The new policy will effect change.', 'The new policy will affect students.',
       "Use 'effect' as a verb only when you mean 'bring about'."),
      ('The effect of the rain was severe.', None,
       "Here 'effect' is a noun — correct."),
      ('I was affected by the news.', None,
       "Verb form — correct.")]),
    ('fewer-vs-less', 'Fewer vs less', 'Grammar',
     "Use 'fewer' with countable nouns and 'less' with uncountable ones.",
     [('There are less people here.', 'There are fewer people here.', 'People is countable.'),
      ('I have less time today.', None, 'Time is uncountable — correct.')]),
    ('who-vs-whom', 'Who vs whom', 'Grammar',
     "'Who' is a subject; 'whom' is an object. If you can replace it with "
     "'he/she', use 'who'; if 'him/her', use 'whom'.",
     [('Whom is calling?', 'Who is calling?', 'Subject.'),
      ('To who should I address this?', 'To whom should I address this?',
       'Object of preposition.')]),
    ('lie-vs-lay', 'Lie vs lay', 'Grammar',
     "'Lie' is intransitive (you lie down); 'lay' is transitive (you lay "
     "something down).",
     [('I need to lay down.', 'I need to lie down.', "No direct object."),
      ('She lay the book on the table.', None, "Direct object 'book' — correct.")]),
    ('its-vs-its', "Its vs it's", 'Punctuation',
     "'Its' is possessive; 'it's' is the contraction of 'it is' or 'it has'.",
     [("Its raining.", "It's raining.", "Contraction needed."),
      ("The dog wagged it's tail.", "The dog wagged its tail.", "Possessive — no apostrophe.")]),
    ('there-their-theyre', "There, their, they're", 'Spelling',
     "'There' = location; 'their' = belonging to them; 'they're' = they are.",
     [("Their going to the park.", "They're going to the park.", "Contraction."),
      ("There house is blue.", "Their house is blue.", "Possessive.")]),
    ('your-vs-youre', "Your vs you're", 'Spelling',
     "'Your' is possessive; 'you're' is the contraction of 'you are'.",
     [("Your welcome.", "You're welcome.", "Contraction."),
      ("Is this you're book?", "Is this your book?", "Possessive.")]),
    ('me-vs-i', "Me vs I", 'Pronouns',
     "'I' is a subject; 'me' is an object. Test by dropping the other person.",
     [("Sam and me went to the store.", "Sam and I went to the store.", "Subject."),
      ("Give it to Sam and I.", "Give it to Sam and me.", "Object.")]),
    ('which-vs-that', 'Which vs that', 'Grammar',
     "'That' introduces restrictive clauses (essential info); 'which' "
     "introduces non-restrictive ones (extra info, with commas).",
     [("The car which I bought is red.", "The car that I bought is red.",
       "Restrictive."),
      ("My car, that is red, is in the shop.", "My car, which is red, is in the shop.",
       "Non-restrictive.")]),
    ('compliment-vs-complement', 'Compliment vs complement', 'Spelling',
     "'Compliment' = praise; 'complement' = something that completes.",
     [("Her dress was a perfect compliment to her shoes.",
       "Her dress was a perfect complement to her shoes.",
       "Completes the outfit."),
      ("He paid me a nice complement.", "He paid me a nice compliment.",
       "Praise.")]),
    ('principal-vs-principle', 'Principal vs principle', 'Spelling',
     "'Principal' = main/head (adjective or person); 'principle' = a rule "
     "or belief.",
     [("The school principle gave a speech.", "The school principal gave a speech.",
       "The head of the school."),
      ("It's a matter of principal.", "It's a matter of principle.",
       "A belief.")]),
    ('past-vs-passed', 'Past vs passed', 'Spelling',
     "'Passed' is the past tense of 'pass'; 'past' is a noun/adjective/"
     "preposition meaning earlier in time.",
     [("I past my exam.", "I passed my exam.", "Verb."),
      ("In the passed, we did it differently.", "In the past, we did it differently.",
       "Noun.")]),
    ('lose-vs-loose', 'Lose vs loose', 'Spelling',
     "'Lose' (verb) = fail to keep; 'loose' (adj.) = not tight.",
     [("Don't loose your keys.", "Don't lose your keys.", "Verb."),
      ("My belt is lose.", "My belt is loose.", "Adjective.")]),
    ('then-vs-than', 'Then vs than', 'Spelling',
     "'Then' = at that time / next; 'than' = used in comparisons.",
     [("She is taller then me.", "She is taller than me.", "Comparison."),
      ("We ate, than left.", "We ate, then left.", "Sequence.")]),
    ('e-g-vs-i-e', 'e.g. vs i.e.', 'Style',
     "'e.g.' (exempli gratia) = for example; 'i.e.' (id est) = that is, in "
     "other words.",
     [("Bring tools, i.e. a hammer and a screwdriver.",
       "Bring tools, e.g. a hammer and a screwdriver.",
       "You're giving examples, not defining."),
      ("Animals, e.g. mammals, lay eggs.", "Animals, e.g. some animals like mammals, lay eggs.",
       "Often 'i.e.' is better when narrowing.")]),
    ('between-vs-among', 'Between vs among', 'Prepositions',
     "Use 'between' for two (or specific items); 'among' for groups of "
     "three or more.",
     [("Choose among the two options.", "Choose between the two options.",
       "Two options."),
      ("She walked between the trees.", "She walked among the trees.",
       "Many trees.")]),
    ('imply-vs-infer', 'Imply vs infer', 'Vocabulary',
     "The speaker implies; the listener infers.",
     [("Are you inferring that I'm lying?",
       "Are you implying that I'm lying?", "Speaker implies."),
      ("From her tone I implied she was upset.",
       "From her tone I inferred she was upset.", "Listener infers.")]),
    ('disinterested-vs-uninterested', 'Disinterested vs uninterested',
     'Vocabulary',
     "'Disinterested' = impartial; 'uninterested' = not interested.",
     [("The judge looked uninterested in the case.",
       "The judge looked disinterested in the case.", "Impartial."),
      ("He seemed disinterested in football.",
       "He seemed uninterested in football.", "Not interested.")]),
    ('practice-vs-practise', 'Practice vs practise', 'Spelling (UK/US)',
     "In British English, 'practice' is a noun and 'practise' is a verb. "
     "In American English, 'practice' covers both.",
     [("She practiced piano daily.", None, "American usage — correct."),
      ("She practised piano daily.", None, "British usage — correct."),
      ("I have a doctor's practise at noon.", "I have a doctor's practice at noon.",
       "Noun.")]),
    ('advice-vs-advise', 'Advice vs advise', 'Spelling',
     "'Advice' is a noun; 'advise' is a verb.",
     [("He gave me good advise.", "He gave me good advice.", "Noun."),
      ("Please advice me on this.", "Please advise me on this.", "Verb.")]),
    ('continual-vs-continuous', 'Continual vs continuous', 'Vocabulary',
     "'Continual' = recurring frequently with breaks; 'continuous' = "
     "without any break.",
     [("The continual rain ruined the picnic (it rained nonstop).",
       "The continuous rain ruined the picnic (it rained nonstop).",
       "Use 'continuous' for unbroken."),
      ("Continual interruptions made it hard to focus.", None,
       "Recurring — correct.")]),
    ('historic-vs-historical', 'Historic vs historical', 'Vocabulary',
     "'Historic' = important in history; 'historical' = relating to "
     "history.",
     [("A historical moment for the country.",
       "A historic moment for the country.", "Importance."),
      ("A historic novel set in 1850.", "A historical novel set in 1850.",
       "Relating to history.")]),
    ('emigrate-vs-immigrate', 'Emigrate vs immigrate', 'Vocabulary',
     "'Emigrate' = leave a country; 'immigrate' = enter a country.",
     [("She immigrated from Italy in 1950.",
       "She emigrated from Italy in 1950.", "Leaving Italy."),
      ("She emigrated to the US.", "She immigrated to the US.",
       "Entering the US.")]),
    ('lend-vs-borrow', 'Lend vs borrow', 'Vocabulary',
     "'Lend' = give temporarily; 'borrow' = take temporarily.",
     [("Can you borrow me a pen?", "Can you lend me a pen?",
       "The other person gives."),
      ("I lent his pen.", "I borrowed his pen.", "I took.")]),
    ('bring-vs-take', 'Bring vs take', 'Vocabulary',
     "'Bring' = movement toward speaker; 'take' = movement away.",
     [("Take this present to me.", "Bring this present to me.",
       "Toward speaker."),
      ("Bring it to the office tomorrow (I won't be there).",
       "Take it to the office tomorrow (I won't be there).",
       "Away from speaker.")]),
    ('rise-vs-raise', 'Rise vs raise', 'Verbs',
     "'Rise' is intransitive; 'raise' is transitive.",
     [("Raise early on weekends.", "Rise early on weekends.", "No object."),
      ("She rose her hand.", "She raised her hand.", "With object.")]),
    ('sit-vs-set', 'Sit vs set', 'Verbs',
     "'Sit' is usually intransitive; 'set' is transitive.",
     [("Set down, please.", "Sit down, please.", "Intransitive."),
      ("Please sit the books here.", "Please set the books here.",
       "With object.")]),
    ('amount-vs-number', 'Amount vs number', 'Vocabulary',
     "'Amount' for uncountable; 'number' for countable.",
     [("A large amount of people.", "A large number of people.",
       "People is countable."),
      ("A large number of water.", "A large amount of water.",
       "Water is uncountable.")]),
    ('like-vs-as', 'Like vs as', 'Comparison',
     "'Like' compares nouns; 'as' introduces a clause.",
     [("Do like I do.", "Do as I do.", "Clause."),
      ("He fights as a lion.", "He fights like a lion.", "Noun.")]),
    ('every-day-vs-everyday', 'Every day vs everyday', 'Spelling',
     "'Every day' (two words) = each day; 'everyday' (one word) = "
     "ordinary, daily.",
     [("She walks her dog everyday.", "She walks her dog every day.",
       "Time expression."),
      ("These are my every day shoes.", "These are my everyday shoes.",
       "Adjective.")]),
    # Pronunciation-focused.
    ('schedule-uk-vs-us', "'Schedule' UK vs US", 'Pronunciation',
     "UK speakers often pronounce 'schedule' /ˈʃedjuːl/ (SHED-yool); US "
     "speakers say /ˈskedʒuːl/ (SKED-jool).",
     [("Saying 'SKED-jool' in London.", None, "Marks the speaker as American."),
      ("Saying 'SHED-yool' in Boston.", None, "Marks the speaker as British.")]),
    ('aluminium-vs-aluminum', "'Aluminium' vs 'aluminum'", 'Pronunciation',
     "British 'aluminium' (al-yoo-MIN-ee-um, 5 syllables) vs American "
     "'aluminum' (a-LOO-min-um, 4 syllables) — both are correct in their "
     "own dialect.",
     [("Calling it 'aluminum' in a UK chemistry exam.",
       "Use 'aluminium' in UK academic contexts.",
       "Dialect mismatch.")]),
    ('comfortable-syllables', "'Comfortable' syllable count", 'Pronunciation',
     "Native English speakers normally compress 'comfortable' to 3 "
     "syllables: /ˈkʌmftəbl/. Don't say all 4.",
     [("'com-fort-a-ble' (4 syllables, careful)",
       "'COMF-ta-ble' (3 syllables, natural)",
       "4 syllables sounds over-careful.")]),
    ('wednesday-silent', "'Wednesday' silent letters", 'Pronunciation',
     "The 'd' in Wednesday is silent: /ˈwenzdeɪ/.",
     [("Saying 'Wed-NEZ-day' with the 'd'.", "Say 'WENZ-day'.",
       "Silent 'd'.")]),
    # Register pitfalls.
    ('cool-register', "'Cool' across registers", 'Register',
     "'Cool' is informal. In formal writing, use 'excellent', 'admirable', "
     "or 'impressive' instead.",
     [("In a cover letter: 'I had a cool internship at NASA.'",
       "I had an excellent internship at NASA.",
       "Use formal register.")]),
    ('gonna-wanna', "'Gonna' / 'wanna' in writing", 'Register',
     "'Gonna', 'wanna', and 'gotta' are spoken contractions. Avoid them in "
     "formal writing.",
     [("In an essay: 'I'm gonna argue that...'",
       "I will argue that...", "Use full form.")]),
    ('whilst-vs-while', "'Whilst' vs 'while'", 'Register',
     "'Whilst' sounds dated or overly formal in American English; "
     "'while' is preferred everywhere.",
     [("Whilst studying for exams I worked part-time.",
       "While studying for exams I worked part-time.",
       "'While' is more natural.")]),
    ('amongst-vs-among', "'Amongst' vs 'among'", 'Register',
     "Both are correct; 'among' is more common, especially in the US.",
     [("Amongst the trees stood a cabin.", "Among the trees stood a cabin.",
       "More natural.")]),
    # False friends.
    ('actually-false-friend', "'Actually' for non-native speakers",
     'False friend',
     "In English, 'actually' means 'in fact', NOT 'currently'. Compare "
     "Spanish 'actualmente' = currently.",
     [("Actually I am working at Google.", "I am currently working at Google.",
       "If you mean 'now', use 'currently'.")]),
    ('sensible-vs-sensitive', "'Sensible' vs 'sensitive'", 'False friend',
     "'Sensible' = practical, wise. 'Sensitive' = emotionally responsive. "
     "French 'sensible' actually means 'sensitive'.",
     [("She's very sensible to criticism.", "She's very sensitive to criticism.",
       "Emotionally responsive.")]),
    ('library-vs-bookshop', "'Library' vs 'bookshop'", 'False friend',
     "'Library' = place to borrow books (free). 'Bookshop'/'bookstore' = "
     "place to buy books. French 'librairie' is the bookshop.",
     [("I bought a novel at the library.", "I bought a novel at the bookshop.",
       "Libraries lend, bookshops sell.")]),
    ('eventually-vs-possibly', "'Eventually' vs 'possibly'", 'False friend',
     "English 'eventually' means 'in the end'. Compare German "
     "'eventuell' = possibly.",
     [("Eventually I will come to your party.",
       "I might come to your party.", "If you mean 'possibly', say so.")]),
    ('sympathetic-vs-nice', "'Sympathetic' vs 'nice/likeable'", 'False friend',
     "'Sympathetic' = showing understanding of someone's suffering. It is "
     "NOT a general word for 'pleasant', as French/German/Spanish cognates "
     "are.",
     [("My new colleague is very sympathetic.",
       "My new colleague is very likeable.", "Pleasant company.")]),
    # Word-formation.
    ('un-vs-dis', "Un- vs dis-", 'Prefixes',
     "Both negate, but 'un-' typically reverses a state ('unfold', "
     "'undress') while 'dis-' often expresses absence or opposite "
     "('disagree', 'dishonest'). Memorise common pairs.",
     [("She undisagreed with the plan.",
       "She disagreed with the plan.", "Negation prefix."),
      ("He unliked his ex-friend's post.",
       "He disliked his ex-friend's post.", "Standard prefix.")]),
    ('ize-vs-ise', '-ize vs -ise', 'Spelling (UK/US)',
     "American English prefers -ize (organize, realize); British English "
     "accepts both, with -ise widely used.",
     [("In a UK essay: 'organize'", "Use 'organise' in British English.",
       "Dialect consistency.")]),
    ('ee-vs-er', '-ee vs -er suffix', 'Word formation',
     "'-er' typically marks the agent (the one who does); '-ee' marks the "
     "patient (the one who receives the action).",
     [("The interviewee asked the first question.",
       "The interviewer asked the first question.",
       "Interviewer = the one asking.")]),
    # Plurals and irregular forms.
    ('children-plural', "'Childs' is not a word", 'Plurals',
     "The plural of 'child' is 'children', not 'childs'.",
     [("Three childs ran past.", "Three children ran past.",
       "Irregular plural.")]),
    ('media-singular', "'Media' singular vs plural", 'Plurals',
     "Strictly, 'media' is the plural of 'medium'. In modern usage, 'the "
     "media' often takes a singular verb when treated as a collective.",
     [("The medias are reporting.", "The media is/are reporting.",
       "No 's' on media.")]),
    ('criteria-vs-criterion', "'Criteria' vs 'criterion'", 'Plurals',
     "'Criterion' is singular, 'criteria' is plural.",
     [("One criteria is missing.", "One criterion is missing.", "Singular."),
      ("Two criterions remain.", "Two criteria remain.", "Plural.")]),
    ('data-singular-plural', "'Data' singular vs plural", 'Plurals',
     "Originally plural ('this datum, these data'), 'data' is widely used "
     "as a singular mass noun in modern English. Pick one and be "
     "consistent within a document.",
     [("The data are clear.", None, "Traditional usage — correct in academic writing."),
      ("The data is clear.", None, "Modern usage — correct in journalism.")]),
    # Spelling pairs.
    ('stationary-vs-stationery', "'Stationary' vs 'stationery'", 'Spelling',
     "'Stationary' (with 'a') = not moving. 'Stationery' (with 'e') = "
     "writing supplies.",
     [("She bought office stationary.", "She bought office stationery.",
       "Supplies."),
      ("The car was stationery.", "The car was stationary.", "Not moving.")]),
    ('peek-vs-peak-vs-pique', "'Peek' vs 'peak' vs 'pique'", 'Spelling',
     "'Peek' = a quick look. 'Peak' = the top. 'Pique' = arouse interest "
     "or take offence.",
     [("That peaked my interest.", "That piqued my interest.",
       "Aroused interest.")]),
    ('alot-vs-a-lot', "'Alot' is not a word", 'Spelling',
     "Always spell as 'a lot' (two words).",
     [("I learned alot from this course.", "I learned a lot from this course.",
       "Two words.")]),
    ('discrete-vs-discreet', "'Discrete' vs 'discreet'", 'Spelling',
     "'Discrete' = separate, distinct. 'Discreet' = careful not to attract "
     "attention.",
     [("Please be discrete about the surprise party.",
       "Please be discreet about the surprise party.",
       "Don't attract attention.")]),
    ('whose-vs-whos', "'Whose' vs 'who's'", 'Spelling',
     "'Whose' = possessive. 'Who's' = 'who is' or 'who has'.",
     [("Who's car is this?", "Whose car is this?", "Possessive."),
      ("Whose been calling?", "Who's been calling?", "Contraction.")]),
    # Punctuation.
    ('oxford-comma', 'Oxford comma', 'Punctuation',
     "The Oxford comma is the final comma before 'and' in a list. It can "
     "prevent ambiguity but is optional in many style guides.",
     [("I love my parents, Lady Gaga and Humpty Dumpty.",
       "I love my parents, Lady Gaga, and Humpty Dumpty.",
       "Without the Oxford comma it sounds like your parents ARE Lady Gaga and Humpty Dumpty.")]),
    ('semicolon-use', 'When to use a semicolon', 'Punctuation',
     "A semicolon joins two independent clauses without a conjunction. "
     "Don't use it where a comma or full stop would do.",
     [("I love coffee; and tea.", "I love coffee and tea.", "No semicolon with 'and'."),
      ("It's raining; bring an umbrella.", None, "Two independent clauses — correct.")]),
    ('em-dash-en-dash', 'Em dash vs en dash', 'Punctuation',
     "Em dash (—) is for breaks in thought. En dash (–) is for ranges "
     "('pages 10–15'). Hyphen (-) is for compounds.",
     [("Pages 10—15", "Pages 10–15", "Use en dash for ranges."),
      ("She said-'I will not go.'", "She said—'I will not go.'", "Em dash.")]),
]

mistakes = []
for i, (slug, topic, cat, body, examples) in enumerate(MISTAKE_TOPICS):
    ex_list = []
    for wrong, right, note in examples:
        ex_list.append({'wrong': wrong, 'right': right, 'note': note})
    mistakes.append({
        'slug': slug,
        'topic': topic,
        'category': cat,
        'body': body,
        'examples': ex_list,
        'sort_order': i,
    })

with open(os.path.join(SCRAPED, 'mistakes_r4.json'), 'w', encoding='utf-8') as f:
    json.dump(mistakes, f, ensure_ascii=False, sort_keys=True, indent=1)
print(f'Wrote scraped_data/mistakes_r4.json ({len(mistakes)} entries)')


# ─── curated patch: add R4 fields to CURATED slugs that already exist ──────

CURATED_HEADWORDS = {
    'serendipity': ('formal',
                    "From Persian 'Serendip' (the old name for Sri Lanka). "
                    "Coined by Horace Walpole in 1754 in a letter, inspired by "
                    "the fairy tale 'The Three Princes of Serendip', whose "
                    "heroes were always making fortunate discoveries by "
                    "accident. First written use in the modern sense: late "
                    "18th century."),
    'ubiquitous': ('formal',
                   "From Latin 'ubique' (everywhere), formed with the "
                   "suffix -ous in early 19th-century English. Compare "
                   "ecclesiastical Latin 'ubiquitas', a 16th-century "
                   "theological term for divine omnipresence."),
    'zeitgeist': ('formal',
                  "From German 'Zeit' (time) + 'Geist' (spirit). Borrowed "
                  "into English in the mid-19th century via Hegelian "
                  "philosophy; retained the German spelling and capital "
                  "letter in formal use."),
    'innovate': ('',
                 "From Latin 'innovare' (to renew, alter), from 'in-' "
                 "(into) + 'novare' (to make new), from 'novus' (new). "
                 "First English attestation around 1540."),
    'procrastination': ('formal',
                        "From Latin 'procrastinatio', from 'procrastinare' "
                        "(to put off until tomorrow), from 'pro-' "
                        "(forward) + 'crastinus' (of tomorrow), from "
                        "'cras' (tomorrow). Entered English in the late "
                        "16th century."),
    'gestalt': ('technical',
                "From German 'Gestalt' (shape, form), from Old High "
                "German 'gistalt'. Borrowed into English in the early "
                "20th century via Gestalt psychology."),
    'euphoria': ('formal',
                 "From Greek 'euphoria' (power of bearing easily), "
                 "from 'eu-' (well) + 'pherein' (to bear). Originally a "
                 "medical term in 18th-century English meaning 'feeling "
                 "of well-being', generalised to extreme happiness in the "
                 "19th century."),
    'impeccable': ('formal',
                   "From Late Latin 'impeccabilis' (not capable of sin), "
                   "from 'in-' (not) + 'peccare' (to sin). Originally a "
                   "theological term in 16th-century English; secular "
                   "sense of 'faultless' from the early 19th century."),
    'ameliorate': ('formal',
                   "From Latin 'melior' (better), via French 'améliorer'. "
                   "Entered English in the mid-18th century; an alteration "
                   "of the earlier 'meliorate' (1540s) under French "
                   "influence."),
    'resilience': ('',
                   "From Latin 'resilire' (to leap back), from 're-' "
                   "(back) + 'salire' (to jump). First used in English in "
                   "the 1620s for the act of rebounding; psychological "
                   "sense from the early 20th century."),
    'concatenate': ('technical',
                    "From Late Latin 'concatenatus', past participle of "
                    "'concatenare' (to link together), from 'com-' "
                    "(together) + 'catena' (chain). 17th-century "
                    "English borrowing, today especially common in "
                    "programming."),
    'sustainability': ('formal',
                       "From 'sustain' + '-ability'. 'Sustain' from Old "
                       "French 'sustenir', from Latin 'sustinere' (to "
                       "hold up, endure), from 'sub-' (up from below) + "
                       "'tenere' (to hold). Modern environmental sense "
                       "documented from the 1970s."),
    'altruism': ('formal',
                 "Coined by Auguste Comte in 1851 as French 'altruisme', "
                 "from Italian 'altrui' (someone else, of others), "
                 "ultimately from Latin 'alter' (other). Adopted in "
                 "English the same decade."),
    'meticulous': ('formal',
                   "From Latin 'meticulosus' (fearful), from 'metus' "
                   "(fear). Originally meant 'timid' in 16th-century "
                   "English; sense shift to 'painstakingly careful' "
                   "occurred in the 19th century."),
    'ephemeral': ('literary',
                  "From Greek 'ephemeros' (lasting only a day), from "
                  "'epi-' (on) + 'hemera' (day). Used in English from "
                  "the late 16th century, originally of fevers and "
                  "insects that lived only one day."),
    'pandemic': ('formal',
                 "From Greek 'pandemos' (pertaining to all people), "
                 "from 'pan-' (all) + 'demos' (people). Medical English "
                 "term from the mid-17th century."),
    'cryptocurrency': ('technical',
                       "Compound of 'crypto-' (from Greek 'kryptos', "
                       "hidden) + 'currency'. Coined in the 2010s; "
                       "popularised by the rise of Bitcoin from 2009 "
                       "onward."),
    'eloquent': ('formal',
                 "From Latin 'eloquens', present participle of 'eloqui' "
                 "(to speak out), from 'e-' (out) + 'loqui' (to speak). "
                 "Entered English in the late 14th century via Old "
                 "French."),
    'unblemished': ('',
                    "From 'un-' (not) + 'blemished', past participle of "
                    "'blemish'. 'Blemish' from Old French 'blesmir' (to "
                    "make pale, injure). Middle English compound, late "
                    "14th century."),
    'quintessential': ('formal',
                       "From Medieval Latin 'quinta essentia' (fifth "
                       "essence) — the substance medieval philosophers "
                       "thought made up the heavens, distinct from the "
                       "four classical elements. Adjective form in "
                       "English from the 16th century."),
    'reverie': ('literary',
                "From Old French 'reverie' (delirium, raving), from "
                "'rever' (to dream). 14th-century borrowing; modern "
                "'daydream' sense from the 17th century."),
    'mitigate': ('formal',
                 "From Latin 'mitigatus', past participle of 'mitigare' "
                 "(to soften, alleviate), from 'mitis' (gentle) + "
                 "'agere' (to drive). 15th-century English."),
    'ambiguous': ('formal',
                  "From Latin 'ambiguus' (having double meaning, "
                  "shifting), from 'ambigere' (to dispute about), from "
                  "'ambi-' (about, around) + 'agere' (to drive, lead). "
                  "Entered English in the late 15th century."),
    'tenacious': ('formal',
                  "From Latin 'tenax' (holding fast), from 'tenere' (to "
                  "hold). English adjective form from the mid-17th "
                  "century."),
    'dog': ('',
            "From Old English 'docga' (a powerful breed of dog), of "
            "uncertain origin. The word displaced the earlier Old "
            "English 'hund' (which survives as 'hound') as the generic "
            "term during the Middle English period."),
}

curated_patch = {}
for slug, (reg, ety) in CURATED_HEADWORDS.items():
    coll = collocations_for(slug, 'noun')  # use noun patterns broadly
    rank = h(slug + 'rank', 5000) + 1  # curated words tend to be common, 1-5000
    curated_patch[slug] = {
        'register': reg,
        'frequency_rank': rank,
        'etymology': ety,
        'collocations': coll,
        'mistake_note': mistake_note_for(slug, 'noun'),
    }

with open(os.path.join(SCRAPED, 'curated_patch_r4.json'), 'w', encoding='utf-8') as f:
    json.dump(curated_patch, f, ensure_ascii=False, sort_keys=True, indent=1)
print(f'Wrote scraped_data/curated_patch_r4.json ({len(curated_patch)} patches)')


# ─── tasks_r4 ──────────────────────────────────────────────────────────────

# Pick stable curated slugs to reference in tasks.
CURATED = ['serendipity', 'ubiquitous', 'zeitgeist', 'innovate',
           'procrastination', 'gestalt', 'euphoria', 'impeccable',
           'ameliorate', 'resilience', 'concatenate', 'sustainability',
           'altruism', 'meticulous', 'ephemeral', 'pandemic',
           'cryptocurrency', 'eloquent', 'unblemished', 'quintessential',
           'reverie', 'mitigate', 'ambiguous', 'tenacious']

# Newly added words for variety.
sample_new = [w['slug'] for w in new_words[::200]][:20]

tasks_r4 = []
next_id = 454

# Type 1 — IPA-decode (60 tasks)
for slug in (CURATED + sample_new)[:30]:
    tasks_r4.append({
        'ques': (f"On the Cambridge Dictionary, open the entry for \"{slug}\" "
                 f"and report the UK IPA transcription exactly as shown in the "
                 f"pronunciation block."),
    })
for slug in (CURATED + sample_new)[:30]:
    tasks_r4.append({
        'ques': (f"Compare the UK and US IPA for \"{slug}\" on Cambridge "
                 f"Dictionary. Report both transcriptions and whether they "
                 f"differ."),
    })

# Type 2 — pronunciation-quiz (50 tasks via /pronunciation/<slug>)
for slug in CURATED:
    tasks_r4.append({
        'ques': (f"Visit /pronunciation/{slug} on the Cambridge Dictionary "
                 f"and confirm both UK and US audio buttons appear with the "
                 f"correct IPA labels."),
    })
for slug in CURATED:
    tasks_r4.append({
        'ques': (f"On the Cambridge Dictionary pronunciation page for "
                 f"\"{slug}\", list which side (UK or US) shows the longer "
                 f"phonetic transcription."),
    })

# Type 3 — word-formation/affix (40 tasks)
for prefix in ['un-', 'dis-', 'pre-', 're-', 'sub-', 'over-', 'under-',
               'mis-', 'inter-', 'trans-']:
    tasks_r4.append({
        'ques': (f"Search the Cambridge Dictionary for words starting with "
                 f"the prefix \"{prefix.rstrip('-')}\" and list three results "
                 f"with their definitions."),
    })
for suffix in ['-tion', '-ness', '-able', '-ly', '-er', '-ee', '-ize', '-ise',
               '-ment', '-ity']:
    tasks_r4.append({
        'ques': (f"Find three words on the Cambridge Dictionary that end "
                 f"with \"{suffix}\" and identify what part of speech each "
                 f"is."),
    })
# Affix mistake-corner-driven (10)
for mt in ['un-vs-dis', 'ize-vs-ise', 'ee-vs-er']:
    tasks_r4.append({
        'ques': (f"Open /mistake/{mt} on the Cambridge Dictionary and report "
                 f"the correct distinction between the two forms with one "
                 f"example each."),
    })
# 7 more affix tasks to fill out 40
for prefix in ['anti-', 'co-', 'ex-', 'non-', 'post-', 'semi-', 'tri-']:
    tasks_r4.append({
        'ques': (f"Search for words beginning with \"{prefix.rstrip('-')}\" "
                 f"and find one with CEFR level B2 or higher."),
    })

# Type 4 — etymology-trace (45 tasks)
for slug in CURATED:
    tasks_r4.append({
        'ques': (f"Open /etymology/{slug} on the Cambridge Dictionary and "
                 f"report the root language and the century of first English "
                 f"attestation as shown."),
    })
for slug in sample_new[:15]:
    tasks_r4.append({
        'ques': (f"Visit the etymology page for \"{slug}\" on Cambridge "
                 f"Dictionary and quote one sentence from the etymology "
                 f"section."),
    })
tasks_r4.append({
    'ques': ("Open the Cambridge Dictionary etymology index at /etymology "
             "and identify which root language has the most entries listed.")
})
tasks_r4.append({
    'ques': ("Browse /etymology on the Cambridge Dictionary and find one "
             "word whose etymology mentions 'Greek'.")
})
tasks_r4.append({
    'ques': ("On the Cambridge Dictionary, find a word with an Old English "
             "etymology and report its current CEFR level.")
})
tasks_r4.append({
    'ques': ("Open the Cambridge Dictionary etymology page for 'serendipity' "
             "and report when the word entered English.")
})
tasks_r4.append({
    'ques': ("Find an entry on Cambridge Dictionary whose etymology cites "
             "Arabic and quote the etymology sentence verbatim.")
})

# Type 5 — false-friend-warn (15 tasks)
ff_mistakes = ['actually-false-friend', 'sensible-vs-sensitive',
               'library-vs-bookshop', 'eventually-vs-possibly',
               'sympathetic-vs-nice']
for ms in ff_mistakes:
    tasks_r4.append({
        'ques': (f"Open /mistake/{ms} on the Cambridge Dictionary and explain "
                 f"the false-friend trap in your own words, citing one "
                 f"example."),
    })
for ms in ff_mistakes:
    tasks_r4.append({
        'ques': (f"On the Cambridge Dictionary mistake corner page for "
                 f"\"{ms}\", report which language is the source of the "
                 f"interference."),
    })
for w in ['actual', 'sensible', 'library', 'eventual', 'sympathetic']:
    tasks_r4.append({
        'ques': (f"Look up \"{w}\" on the Cambridge Dictionary and confirm "
                 f"whether the English meaning differs from the cognate in "
                 f"another European language."),
    })

# Type 6 — register-context-pick (40 tasks)
for slug in CURATED + sample_new[:16]:
    tasks_r4.append({
        'ques': (f"Open the entry for \"{slug}\" on the Cambridge Dictionary "
                 f"and report the register tag (formal / informal / slang / "
                 f"archaic / etc.) shown next to one of the senses."),
    })

# Type 7 — dictionary-shootout vs Oxford/Merriam (20 tasks)
for slug in CURATED[:10]:
    tasks_r4.append({
        'ques': (f"Compare the Cambridge Dictionary definition of \"{slug}\" "
                 f"with what you would expect to find in Oxford or "
                 f"Merriam-Webster. State whether Cambridge labels the word "
                 f"as formal/informal."),
    })
for slug in CURATED[10:20]:
    tasks_r4.append({
        'ques': (f"On the Cambridge Dictionary entry for \"{slug}\", check "
                 f"how many senses are listed and compare with the count you "
                 f"would expect from a major American dictionary."),
    })

# Type 8 — collocations (35 tasks)
for slug in CURATED:
    tasks_r4.append({
        'ques': (f"Visit /collocation/{slug} on the Cambridge Dictionary and "
                 f"list two common collocations shown for the word."),
    })
for slug in sample_new[:11]:
    tasks_r4.append({
        'ques': (f"Open the collocation page for \"{slug}\" on Cambridge "
                 f"Dictionary and copy out one example sentence."),
    })

# Type 9 — mistake-corner topic (40 tasks)
mc_slugs = [m['slug'] for m in mistakes]
for ms in mc_slugs[:20]:
    tasks_r4.append({
        'ques': (f"Open /mistake/{ms} on the Cambridge Dictionary mistake "
                 f"corner and summarise the rule in one sentence."),
    })
for ms in mc_slugs[20:40]:
    tasks_r4.append({
        'ques': (f"On the Cambridge Dictionary, open the mistake-corner page "
                 f"for \"{ms}\" and report the first wrong→right example "
                 f"pair shown."),
    })

# Type 10 — multi-step composed (35 tasks)
multi = [
    ("Search Cambridge Dictionary for \"resilience\", then open its "
     "etymology page and report the root language."),
    ("Find the Cambridge Dictionary word of the day for 2026-03-15, then "
     "open its pronunciation page and report whether both UK and US IPA "
     "are shown."),
    ("Open /mistake (mistake corner index) on Cambridge Dictionary, pick "
     "the first 'Spelling' category entry, and quote one example."),
    ("Sign in as alice.j@test.com / TestPass123!, save the word "
     "\"ameliorate\" to your word list, then open its etymology page."),
    ("On the Cambridge Dictionary, open /word-of-the-day/archive/2026 and "
     "report how many archive entries it lists."),
    ("Search for \"serendipity\", click through to the collocation page, "
     "and copy out one collocation example."),
    ("Open the Cambridge Dictionary entry for \"euphoria\", note its "
     "register tag, then open the mistake-corner index and find any topic "
     "that discusses register."),
    ("Look up \"impeccable\" on Cambridge Dictionary, then open its "
     "pronunciation page, then return and save it (sign in as "
     "carol.d@test.com / TestPass123! first)."),
    ("Find a B2-level adjective on the Cambridge Dictionary and check "
     "whether its etymology page mentions Old French."),
    ("On the Cambridge Dictionary mistake corner index page, count how "
     "many topics are in the Pronunciation category."),
    ("Open the Cambridge Dictionary, search for \"data\", look at the "
     "mistake-corner topic about data singular/plural, and report the "
     "modern usage example."),
    ("Open /etymology on Cambridge Dictionary and report the total number "
     "of entries listed."),
    ("Sign in as david.k@test.com / TestPass123!, open the mistake corner "
     "topic 'affect-vs-effect', and explain the rule."),
    ("On the Cambridge Dictionary, find a word with both UK and US "
     "pronunciation that differ (e.g. 'schedule'). Open its pronunciation "
     "page and compare."),
    ("Open /word-of-the-day/archive/2025 on the Cambridge Dictionary and "
     "report the first three words listed."),
    ("Visit the Cambridge Dictionary collocation page for "
     "\"sustainability\" and identify which collocation appears first."),
    ("On the Cambridge Dictionary mistake corner, find the topic about "
     "'Oxford comma' and state when to use it."),
    ("Search the Cambridge Dictionary for \"gestalt\", then open its "
     "etymology page and report when it entered English."),
    ("Open /etymology/zeitgeist on the Cambridge Dictionary and report "
     "the source language."),
    ("On the Cambridge Dictionary, open the pronunciation page for "
     "\"comfortable\" and report the natural syllable count."),
    ("Open the Cambridge Dictionary, navigate to /mistake/ize-vs-ise, "
     "and explain the UK vs US convention."),
    ("Browse the Cambridge Dictionary mistake corner and find a topic "
     "with 'Plurals' as its category. Report the rule."),
    ("On the Cambridge Dictionary, open the etymology page for "
     "\"procrastination\" and report when it entered English."),
    ("Find a C2-level word on Cambridge Dictionary with an etymology "
     "tracing to Latin and report its slug."),
    ("Open the Cambridge Dictionary mistake corner, find a topic about "
     "false friends, and report one example."),
    ("On the Cambridge Dictionary, search for \"continuous\" and open "
     "the mistake-corner topic that contrasts it with \"continual\"."),
    ("Open /collocation/euphoria on the Cambridge Dictionary and quote "
     "one example collocation."),
    ("Sign in as bob.c@test.com / TestPass123!, save the word "
     "\"resilience\", and confirm a success message."),
    ("On the Cambridge Dictionary, find the word of the day for "
     "2026-05-01 and report the IPA."),
    ("Open the Cambridge Dictionary, find a verb with register tag "
     "'formal', and quote one example sentence."),
    ("On the Cambridge Dictionary, find any word whose register is "
     "marked 'archaic' and report its definition."),
    ("Visit /pronunciation/serendipity on the Cambridge Dictionary and "
     "report whether the syllable count matches the IPA shown."),
    ("Open the Cambridge Dictionary mistake-corner topic about Oxford "
     "comma and explain why omitting it can cause ambiguity."),
    ("On the Cambridge Dictionary, search for \"medium\" and confirm "
     "that the plural is \"media\" by checking the mistake corner."),
    ("Open the Cambridge Dictionary etymology index, scroll to the "
     "second page if present, and report any one entry."),
]
for q in multi:
    tasks_r4.append({'ques': q})

# Type 11 — IPA-decode (drill) (20 tasks)
ipa_drills = [
    ("/səˌsteɪnəˈbɪlɪti/", "sustainability"),
    ("/ˌserənˈdɪpɪti/", "serendipity"),
    ("/juːˈbɪkwɪtəs/", "ubiquitous"),
    ("/ˈzaɪtɡaɪst/", "zeitgeist"),
    ("/ˈɪnəveɪt/", "innovate"),
    ("/prəˌkræstɪˈneɪʃən/", "procrastination"),
    ("/ɡəˈʃtælt/", "gestalt"),
    ("/juːˈfɔːriə/", "euphoria"),
    ("/ɪmˈpekəbəl/", "impeccable"),
    ("/əˈmiːliəreɪt/", "ameliorate"),
]
for ipa, word in ipa_drills:
    tasks_r4.append({
        'ques': (f"On the Cambridge Dictionary, find the entry whose UK IPA "
                 f"is {ipa}. Report the headword."),
    })
for ipa, word in ipa_drills:
    tasks_r4.append({
        'ques': (f"Look up \"{word}\" on the Cambridge Dictionary and verify "
                 f"that the IPA matches {ipa}."),
    })

# Type 12 — WOTD archive (20 tasks)
for year in ['2024', '2025', '2026']:
    for month in ['01', '04', '07', '10']:
        tasks_r4.append({
            'ques': (f"On the Cambridge Dictionary, open "
                     f"/word-of-the-day/archive/{year} and confirm an entry "
                     f"for the month {year}-{month}."),
        })
# 8 more
for d in ['2026-01-01', '2026-02-14', '2026-03-15', '2026-04-15',
          '2026-05-01', '2026-06-21', '2026-07-04', '2026-12-25']:
    tasks_r4.append({
        'ques': (f"Open /word-of-the-day?date={d} on the Cambridge Dictionary "
                 f"and report the word picked for that date."),
    })

# Type 13 — IPA hover popup / visual checks (15 tasks)
for slug in CURATED[:15]:
    tasks_r4.append({
        'ques': (f"Hover over the IPA for \"{slug}\" on the Cambridge "
                 f"Dictionary entry page and report whether a tooltip popup "
                 f"appears explaining the phonetic symbols."),
    })

# Type 14 — CEFR colored chip / side-by-side toggle visual (15 tasks)
for slug in CURATED[:15]:
    tasks_r4.append({
        'ques': (f"On the Cambridge Dictionary entry for \"{slug}\", check "
                 f"the CEFR colored chip next to the part-of-speech label "
                 f"and report which level it shows."),
    })

# Type 15 — frequency rank (15 tasks)
for slug in CURATED[:15]:
    tasks_r4.append({
        'ques': (f"On the Cambridge Dictionary entry for \"{slug}\", find "
                 f"the frequency-rank indicator and report whether the word "
                 f"is in the top 10,000 most frequent English words."),
    })

print(f'Tasks built: {len(tasks_r4)}')

# Write tasks_r4 to a separate file; will be appended to tasks.jsonl by a
# manual step.
with open(os.path.join(HERE, 'tasks_r4.jsonl'), 'w', encoding='utf-8') as f:
    for i, t in enumerate(tasks_r4):
        rec = {
            'web_name': 'Cambridge Dictionary',
            'id': f'Cambridge Dictionary--{next_id + i}',
            'ques': t['ques'],
            'web': 'http://localhost:40012/',
            'upstream_url': 'https://dictionary.cambridge.org/',
        }
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
print(f'Wrote .r4_build/tasks_r4.jsonl ({len(tasks_r4)} tasks, ids '
      f'{next_id}..{next_id + len(tasks_r4) - 1})')
