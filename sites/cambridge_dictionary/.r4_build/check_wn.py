"""Quick check what we can pull from WordNet that's NOT already in db."""
import json, re
from nltk.corpus import wordnet as wn

slugs = set()
for fname in ['words_existing.json','words_fetched.json','words_extra.json']:
    with open('scraped_data/'+fname) as f:
        for w in json.load(f):
            slugs.add(w['slug'])

# Lemmas we don't already have. Prefer single-word lemmas with at least one synset.
def slugify(s):
    return re.sub(r'[^a-z0-9-]+','-', s.lower()).strip('-')

candidates = []
for lemma in wn.all_lemma_names():
    if '_' in lemma or '.' in lemma or "'" in lemma:
        continue
    sl = slugify(lemma)
    if not sl or len(sl) < 2 or len(sl) > 30 or sl in slugs:
        continue
    candidates.append(lemma)
print('NEW candidates from WN:', len(candidates))
print(candidates[:10])
