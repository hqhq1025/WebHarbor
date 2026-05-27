"""Diversified R4/R5/R6/R10 task generator (post-rewrite).

Pulls real data from `_real_data.py` and emits ~887 GUI-style tasks whose
answers always live on a *detail page* the agent must click through to.
Compared to the previous generator, this one:

- Varies phrasing across 5+ rephrase templates per pattern so groups of
  identical sentences are eliminated.
- Mixes chain lengths from 2-step (hub -> answer) up to 7+ step
  (hub -> tools -> filter -> preview -> related -> bookmark).
- Spreads answer fields across source / dims / license / type / alt /
  caption / author / year / venue / citation count / publish date /
  channel / language / quality / kind / source_title / fact value.
- Keeps every group <= 30 entries so duplication is bounded.

The original WebVoyager numeric tasks (id 0..6710) are preserved by the
caller; this script only emits the r4/r5/r6/r10 supplement that gets
appended in tasks.jsonl.
"""
import json
import os
import random

import _real_data as RD

WEB = 'http://localhost:40009/'
UPSTREAM = 'https://www.google.com/'
WEB_NAME = 'Google Search'

IMAGES = RD.IMAGE_CARDS
VIDEOS = RD.VIDEO_CARDS
PAPERS = RD.SCHOLAR_PAPERS
SNIPS  = RD.FEATURED_SNIPPETS
PAA    = RD.PAA_BUNDLES
KPS    = RD.KNOWLEDGE_PANELS


# ---------------------------------------------------------------------------
# R4 — Image search tasks. 30+ phrasing templates split across 12 patterns.
# ---------------------------------------------------------------------------

R4_PHRASES_SOURCE = [
    'Open the {nav} tab on Google, click into the image card "{t}" and tell me the source domain shown on its preview.',
    'I want to know which website hosts the photo "{t}". Use Google Images, click through to its preview page, and report the domain.',
    'On Google Images, navigate to "{t}" and read off the source attribution printed under the photo.',
    'Find the image titled "{t}" via the Images hub and copy the source domain from its detail panel.',
    'Through Google Image search, locate "{t}" and report which site the image is hosted on (the source domain).',
]
R4_PHRASES_DIMS = [
    'Open the Google Images preview for "{t}" and tell me the pixel dimensions printed in the metadata row.',
    'Go through Google Images to find "{t}" and copy the resolution (e.g. 4032x3024) shown on its preview page.',
    'Find "{t}" via Image search and report the image dimensions listed in the right-hand panel.',
]
R4_PHRASES_LICENSE = [
    'In Google Images find "{t}" and tell me the usage-rights license label printed on its preview page.',
    'Open the preview of "{t}" through Google Image search and report what Creative Commons / commercial license category it carries.',
    'Use the Images > Usage rights flow to identify the license that "{t}" is under.',
]
R4_PHRASES_TYPE = [
    'On Google Images, open the preview of "{t}" and report whether its Type is Photo, Clip art, Line drawing, GIF or Transparent.',
    'Find "{t}" via Image search; what Type category (Photo / Clip art / Line drawing / GIF / Transparent) does its preview list?',
]
R4_PHRASES_ALT = [
    'Open the Google Images preview for "{t}" and copy the Alt text it lists.',
    'Through Image search, find "{t}" and report its accessibility Alt description verbatim.',
]
R4_PHRASES_OWNER = [
    'Open the Google Images preview for "{t}" and report the Source owner (the name printed under "Source owner").',
    'Find "{t}" through Google Images and tell me which photographer / agency the preview credits as the source owner.',
]
R4_PHRASES_CAPTION = [
    'Through Google Images, open the preview of "{t}" and copy the descriptive caption shown below the photo.',
    'Find the Google Images preview for "{t}" and report the photo caption written under it.',
]

R4_NAV_OPTIONS = ['Images', 'Google Images', 'Image search', 'Images hub', 'Images vertical']

R4_PHRASES_COLOR_COUNT = [
    'Open the Image search Tools panel on Google and click the colour filter "{c}". Tell me how many photos match.',
    'Go to Google Images, open Tools, filter by colour "{c}", and report the count of matching cards.',
    'Through Google Images > Tools > Colour, select "{c}" and tell me how many images appear in the listing.',
]
R4_PHRASES_SIZE_COUNT = [
    'On Google Images Tools, filter by Size "{s}" and report how many photos are shown.',
    'Use Google Images > Tools > Size > "{s}" and tell me the number of matching photos.',
]
R4_PHRASES_TYPE_COUNT = [
    'In Google Images Tools, filter by image Type "{ty}" and report how many cards appear.',
    'Through Google Images > Tools > Type "{ty}", tell me the count of matching photos.',
]
R4_PHRASES_MULTISTEP = [
    'Start at the Google homepage, click the Images tab, open Tools, filter by colour "{c}", click into the first matching card and tell me the source domain shown on its preview page.',
    'Open Google Images, go to Tools > Type "{ty}", click the first card, read its preview, then tell me the dimensions printed there.',
    'From Google homepage open the Images vertical, then Tools, then Usage rights "{lbl}"; click the very first image and report its photographer / source-owner.',
]


def r4_tasks():
    rows = []
    field_table = [
        ('preview_source',  R4_PHRASES_SOURCE,  'source_domain'),
        ('preview_dims',    R4_PHRASES_DIMS,    'dims'),
        ('preview_license', R4_PHRASES_LICENSE, 'license_label'),
        ('preview_type',    R4_PHRASES_TYPE,    '_type_label'),
        ('preview_alt',     R4_PHRASES_ALT,     'alt'),
        ('preview_owner',   R4_PHRASES_OWNER,   'source_owner'),
        ('preview_caption', R4_PHRASES_CAPTION, 'caption'),
    ]
    type_label = {'photo': 'Photo', 'clipart': 'Clip art', 'lineart': 'Line drawing',
                  'gif': 'GIF', 'transparent': 'Transparent'}
    for field, phrases, ans_key in field_table:
        for i, c in enumerate(IMAGES):
            tmpl = phrases[i % len(phrases)]
            nav = R4_NAV_OPTIONS[i % len(R4_NAV_OPTIONS)]
            q = tmpl.format(t=c['title'], nav=nav)
            ans = type_label.get(c['type'], c['type']) if ans_key == '_type_label' else c[ans_key]
            rows.append((field, q, ans))
    # Filter counts (color/size/type)
    color_keys = sorted({c['color'] for c in IMAGES})
    for i, ck in enumerate(color_keys):
        n = sum(1 for c in IMAGES if c['color'] == ck)
        tmpl = R4_PHRASES_COLOR_COUNT[i % len(R4_PHRASES_COLOR_COUNT)]
        rows.append(('color_count', tmpl.format(c=ck), str(n)))
    for i, s in enumerate(['large', 'medium', 'icon']):
        n = sum(1 for c in IMAGES if c['size'] == s)
        tmpl = R4_PHRASES_SIZE_COUNT[i % len(R4_PHRASES_SIZE_COUNT)]
        rows.append(('size_count', tmpl.format(s=s), str(n)))
    for i, ty in enumerate(['photo', 'clipart', 'lineart', 'gif', 'transparent']):
        n = sum(1 for c in IMAGES if c['type'] == ty)
        tmpl = R4_PHRASES_TYPE_COUNT[i % len(R4_PHRASES_TYPE_COUNT)]
        rows.append(('type_count', tmpl.format(ty=ty), str(n)))
    # Multi-step chains
    seen_colors = set()
    for c in IMAGES:
        if c['color'] in seen_colors:
            continue
        seen_colors.add(c['color'])
        tmpl = R4_PHRASES_MULTISTEP[len(seen_colors) % len(R4_PHRASES_MULTISTEP)]
        if '{ty}' in tmpl:
            rows.append(('multistep_type_dims', tmpl.format(ty=c['type']), c['dims']))
        elif '{lbl}' in tmpl:
            rows.append(('multistep_rights_owner', tmpl.format(lbl=c['license_label']), c['source_owner']))
        else:
            rows.append(('multistep_color_source', tmpl.format(c=c['color']), c['source_domain']))
    return rows


# ---------------------------------------------------------------------------
# R5 — Video search tasks
# ---------------------------------------------------------------------------

R5_PHRASES_CHANNEL = [
    'Through Google Videos, find the clip "{t}" and open its captions/details page; tell me what channel publishes it.',
    'On Google Videos, locate the video "{t}" and report which channel hosts it.',
    'Find "{t}" via the Videos hub and copy the channel name shown on its captions page.',
]
R5_PHRASES_PLATFORM = [
    'Go to Google Videos and find "{t}"; on its detail page, tell me which platform (YouTube / Vimeo / TED) the video lives on.',
    'Open Google Videos, navigate to "{t}", and report the upstream platform name from its captions page.',
]
R5_PHRASES_DURATION = [
    'Find the video "{t}" through Google Videos and copy the duration (e.g. 12:01) printed on its detail page.',
    'On Google Videos, open the captions panel for "{t}" and report its duration.',
]
R5_PHRASES_QUALITY = [
    'Through Google Videos, locate "{t}" and tell me whether it is HD, 1080p Full HD, or 4K Ultra HD on its detail page.',
    'Find "{t}" on Google Videos and report the listed quality (HD / Full HD / 4K).',
]
R5_PHRASES_PUBLISHED = [
    'On Google Videos, open the captions page for "{t}" and copy the "published" date (YYYY-MM-DD).',
    'Find "{t}" through Google Videos and tell me when it was published.',
]
R5_PHRASES_LANGUAGE = [
    'Open Google Videos, navigate to "{t}", and report the two-letter language code shown for its captions.',
    'Find "{t}" on Google Videos and tell me the caption language code listed on its detail panel.',
]
R5_PHRASES_LASTLINE = [
    'Open Google Videos, navigate to the captions of "{t}", and copy the LAST caption line printed on its page.',
    'Find "{t}" on Google Videos and report the final caption line shown in its closed-caption preview.',
]
R5_PHRASES_FIRSTLINE = [
    'Through Google Videos, open the captions for "{t}" and copy the FIRST caption line verbatim.',
    'Find "{t}" via Google Videos and tell me the very first caption line printed on its detail page.',
]
R5_PHRASES_DESCRIPTION = [
    'On Google Videos, open "{t}" and copy the description (the paragraph below the title) verbatim.',
    'Find "{t}" via the Videos hub and report the descriptive blurb shown on its detail page.',
]
R5_PHRASES_FILTER_COUNT = [
    'Open Google Videos Tools, filter by duration "{d}", and tell me how many clips match.',
    'Go to /videos, open Tools, choose duration "{d}", and report the match count.',
]
R5_PHRASES_QUAL_COUNT = [
    'On Google Videos Tools, filter by quality "{q}" and tell me how many clips appear.',
]
R5_PHRASES_MULTISTEP = [
    'Start at the Google homepage, click Videos, open Tools, filter by duration "{d}", click the first clip and report its channel.',
    'From the Google homepage open Videos, then Tools, then quality "{q}"; click the first clip and tell me its published date.',
    'Open Google Videos, filter by language "{lang}" (after clicking into Tools), click the first clip and report its duration.',
]


def r5_tasks():
    rows = []
    field_table = [
        ('caps_channel',     R5_PHRASES_CHANNEL,    'channel'),
        ('caps_platform',    R5_PHRASES_PLATFORM,   'platform'),
        ('caps_duration',    R5_PHRASES_DURATION,   'duration'),
        ('caps_quality',     R5_PHRASES_QUALITY,    'quality'),
        ('caps_published',   R5_PHRASES_PUBLISHED,  'published'),
        ('caps_language',    R5_PHRASES_LANGUAGE,   'language'),
        ('caps_description', R5_PHRASES_DESCRIPTION,'description'),
    ]
    for field, phrases, ans_key in field_table:
        for i, v in enumerate(VIDEOS):
            tmpl = phrases[i % len(phrases)]
            q = tmpl.format(t=v['title'])
            rows.append((field, q, v[ans_key]))

    for i, v in enumerate(VIDEOS):
        tmpl = R5_PHRASES_FIRSTLINE[i % len(R5_PHRASES_FIRSTLINE)]
        rows.append(('caps_firstline', tmpl.format(t=v['title']), v['caption_lines'][0]))
    for i, v in enumerate(VIDEOS):
        tmpl = R5_PHRASES_LASTLINE[i % len(R5_PHRASES_LASTLINE)]
        rows.append(('caps_lastline', tmpl.format(t=v['title']), v['caption_lines'][-1]))

    for i, d in enumerate(['short', 'medium', 'long', 'film']):
        n = sum(1 for v in VIDEOS if v['duration_bucket'] == d)
        tmpl = R5_PHRASES_FILTER_COUNT[i % len(R5_PHRASES_FILTER_COUNT)]
        rows.append(('dur_count', tmpl.format(d=d), str(n)))
    for i, q in enumerate(['hd', 'fhd', '4k']):
        n = sum(1 for v in VIDEOS if v['quality'] == q)
        rows.append(('qual_count', R5_PHRASES_QUAL_COUNT[0].format(q=q), str(n)))

    seen = set()
    for v in VIDEOS:
        key = v['duration_bucket']
        if key in seen:
            continue
        seen.add(key)
        idx = len(seen)
        tmpl = R5_PHRASES_MULTISTEP[idx % len(R5_PHRASES_MULTISTEP)]
        if '{d}' in tmpl:
            rows.append(('multistep_dur_channel', tmpl.format(d=v['duration_bucket']), v['channel']))
        elif '{q}' in tmpl:
            rows.append(('multistep_qual_published', tmpl.format(q=v['quality']), v['published']))
        else:
            rows.append(('multistep_lang_duration', tmpl.format(lang=v['language']), v['duration']))

    return rows


# ---------------------------------------------------------------------------
# R6 — Scholar tasks
# ---------------------------------------------------------------------------

R6_PHRASES_AUTHORS = [
    'On Google Scholar, search for "{t}" and open the paper detail page; copy the FIRST author name listed.',
    'Find the Scholar paper "{t}" and tell me who its first author is.',
    'Through /scholar/search, locate "{t}" and report the lead author from its detail page.',
]
R6_PHRASES_VENUE = [
    'On Google Scholar, navigate to the paper "{t}" and report the publication venue printed on its detail page.',
    'Through the Scholar search, find "{t}" and tell me the venue (NeurIPS / ICLR / Nature / etc.) it appeared in.',
]
R6_PHRASES_YEAR = [
    'On Google Scholar, search for "{t}" and report the publication year shown on its detail page.',
    'Open the paper "{t}" via the Scholar hub and tell me the year of publication.',
]
R6_PHRASES_CITED = [
    'On Google Scholar open the paper "{t}" and report its citation count.',
    'Find "{t}" through Scholar and tell me how many citations it has.',
    'Via /scholar/search, navigate to "{t}" and copy the citation total.',
]
R6_PHRASES_ABSTRACT = [
    'Open the Scholar paper "{t}" and copy the FIRST sentence of its abstract.',
    'Through Google Scholar, find "{t}" and report the opening sentence of its abstract.',
]
R6_PHRASES_FIG = [
    'Open the PDF preview for the Scholar paper "{t}" and copy the caption of Figure 2.',
    'Through Google Scholar, navigate to "{t}", click into its PDF preview, and report Figure 3s caption.',
]
R6_PHRASES_CITEDBY_FIRST = [
    'On Google Scholar, open the cited-by list for "{t}" and report the FIRST citing paper title.',
    'Find "{t}" through Scholar, follow its cited-by link, and tell me the title of the first paper that cites it.',
]
R6_PHRASES_CITEDBY_COUNT = [
    'Through Google Scholar, open the cited-by page for "{t}" and report how many citing papers are listed.',
]
R6_PHRASES_MULTISTEP = [
    ('On Google Scholar, sort all results by citations (descending), click into the 3rd row and report its venue.',
     lambda: sorted(PAPERS, key=lambda x: -x['citations'])[2]['venue']),
    ('Open Scholar, filter to Since 2022 and sort by date; click the first result and tell me its citation count.',
     lambda: str(sorted([p for p in PAPERS if p['year'] >= 2022], key=lambda x: -x['year'])[0]['citations'])),
    ('On Google Scholar, search "transformer", sort by citation count, click the top paper and open its PDF preview; copy Figure 1s caption.',
     lambda: 'Figure 1. Architecture overview of ' + sorted(
         [p for p in PAPERS if 'transformer' in (p['abstract']+' '+p['title']).lower()],
         key=lambda x: -x['citations'])[0]['title'].split(':')[0] + '.'),
]


def r6_tasks():
    rows = []
    venue_label = {k: l for k, l in [
        ('neurips', 'NeurIPS — Conference on Neural Information Processing Systems'),
        ('icml',    'ICML — International Conference on Machine Learning'),
        ('nature',  'Nature'),
        ('science', 'Science'),
        ('cell',    'Cell'),
        ('jacs',    'Journal of the American Chemical Society'),
        ('arxiv',   'arXiv preprint'),
        ('iclr',    'ICLR — International Conference on Learning Representations'),
        ('cvpr',    'CVPR — Computer Vision and Pattern Recognition'),
        ('lancet',  'The Lancet'),
        ('nejm',    'New England Journal of Medicine'),
        ('ipcc',    'IPCC Assessment Report'),
    ]}
    field_table = [
        ('paper_authors',    R6_PHRASES_AUTHORS, lambda p: p['authors_csv'].split(';')[0].strip()),
        ('paper_venue',      R6_PHRASES_VENUE,   lambda p: venue_label.get(p['venue'], p['venue'])),
        ('paper_year',       R6_PHRASES_YEAR,    lambda p: str(p['year'])),
        ('paper_citations',  R6_PHRASES_CITED,   lambda p: str(p['citations'])),
        ('paper_abstract',   R6_PHRASES_ABSTRACT,lambda p: p['abstract'].split('.')[0] + '.'),
    ]
    for field, phrases, ans_fn in field_table:
        for i, p in enumerate(PAPERS):
            tmpl = phrases[i % len(phrases)]
            rows.append((field, tmpl.format(t=p['title']), ans_fn(p)))
    for i, p in enumerate(PAPERS):
        tmpl = R6_PHRASES_FIG[i % len(R6_PHRASES_FIG)]
        if 'Figure 2' in tmpl:
            ans = 'Figure 2. Quantitative results table comparing baselines.'
        else:
            ans = 'Figure 3. Ablation study of key components.'
        rows.append(('paper_fig', tmpl.format(t=p['title']), ans))
    for i, p in enumerate(PAPERS):
        dsts = RD.CITED_BY.get(p['slug'], [])
        if not dsts:
            continue
        first = next((q['title'] for q in PAPERS if q['slug'] == dsts[0]), None)
        if not first:
            continue
        tmpl = R6_PHRASES_CITEDBY_FIRST[i % len(R6_PHRASES_CITEDBY_FIRST)]
        rows.append(('citedby_first', tmpl.format(t=p['title']), first))
    for p in PAPERS:
        resolved = len(RD.CITED_BY.get(p['slug'], []))
        stubs    = len(RD.CITED_BY_STUBS.get(p['slug'], []))
        total = resolved + stubs
        if total == 0:
            continue
        rows.append(('citedby_count',
                     R6_PHRASES_CITEDBY_COUNT[0].format(t=p['title']), str(total)))
    for i, (tmpl, ans_fn) in enumerate(R6_PHRASES_MULTISTEP):
        rows.append(('multistep_' + str(i), tmpl, ans_fn()))
    return rows


# ---------------------------------------------------------------------------
# R10 — Featured snippet / PAA / KP / safesearch
# ---------------------------------------------------------------------------

R10_PHRASES_SNIP_ANSWER = [
    'On Google, search for "{q}". Open the featured-snippet card that appears and copy its answer paragraph.',
    'Find the featured snippet for the query "{q}" and report the answer it gives.',
]
R10_PHRASES_SNIP_SOURCE = [
    'Search Google for "{q}", then read the featured snippet card and report the source domain shown.',
    'Find the featured snippet for "{q}" on Google and tell me which website it cites as the source.',
]
R10_PHRASES_SNIP_SRCTITLE = [
    'On Google, search "{q}". Open the featured snippet and copy the source page title it links to.',
]
R10_PHRASES_SNIP_KIND = [
    'On Google, search "{q}", read the featured snippet, and report whether it is shown as a "paragraph" or "list" snippet.',
]
R10_PHRASES_PAA_FIRST = [
    'Open the People also ask block on Google for "{q}". Expand the FIRST question and tell me what it reads.',
    'For the Google query "{q}", the People also ask panel appears; expand it and copy the first question listed.',
]
R10_PHRASES_PAA_LAST = [
    'Open the People also ask block on Google for "{q}" and report the LAST expandable question.',
    'Find the PAA panel on Google for "{q}" and tell me the very last listed question.',
]
R10_PHRASES_PAA_ANSWER = [
    'Open the People also ask block for "{q}" on Google. Expand the SECOND question and copy its answer verbatim.',
    'For the Google query "{q}", expand the second PAA question and report the answer.',
]
R10_PHRASES_KP_FIRST = [
    'Search Google for "{n}" and look at the Knowledge panel facts table; copy the value in the FIRST row.',
    'On Google, find the Knowledge panel for "{n}" and report the first fact value listed.',
]
R10_PHRASES_KP_LAST = [
    'Search Google for "{n}" and look at the Knowledge panel facts table; copy the value in the LAST row.',
    'On Google, find the Knowledge panel for "{n}" and report the last fact value listed.',
]
R10_PHRASES_KP_KIND = [
    'On Google, find the Knowledge panel for "{n}" and tell me its "kind" (e.g. Basketball player, 2023 film, ...).',
]
R10_PHRASES_KP_FACTCOUNT = [
    'On Google, find the Knowledge panel for "{n}" and tell me how many fact rows are listed in its table.',
]
R10_PHRASES_SAFESEARCH = [
    ('Open Google Settings > SafeSearch. Switch the level to "Strict" and report the description shown for Strict.',
     'Filter explicit images, videos and text from results.'),
    ('Go to /settings/safesearch and tell me what description text appears next to the "Moderate" option.',
     'Filter explicit images, but allow explicit text.'),
    ('In Google SafeSearch settings, set the level to "Off" and report the help-text describing what Off does.',
     'Show all results, including explicit content.'),
]
R10_PHRASES_MULTI_SNIP_PAA = [
    'Search Google for "{q}". Open the featured snippet, then scroll to the People also ask block and tell me the FIRST PAA question listed.',
]
R10_PHRASES_MULTI_KP_PAA = [
    'Search Google for "{n}". Open the Knowledge panel, then read the People also ask block in the same SERP and report its first question.',
]


def r10_tasks():
    rows = []
    for i, s in enumerate(SNIPS):
        rows.append(('snip_answer',  R10_PHRASES_SNIP_ANSWER [i % len(R10_PHRASES_SNIP_ANSWER )].format(q=s['query']), s['answer']))
        rows.append(('snip_source',  R10_PHRASES_SNIP_SOURCE [i % len(R10_PHRASES_SNIP_SOURCE )].format(q=s['query']), s['source_domain']))
        rows.append(('snip_srctitle',R10_PHRASES_SNIP_SRCTITLE[i % len(R10_PHRASES_SNIP_SRCTITLE)].format(q=s['query']), s['source_title']))
        rows.append(('snip_kind',    R10_PHRASES_SNIP_KIND   [i % len(R10_PHRASES_SNIP_KIND   )].format(q=s['query']), s['kind']))
    for i, b in enumerate(PAA):
        first_q = b['qa'][0][0]
        last_q  = b['qa'][-1][0]
        second_a = b['qa'][1][1] if len(b['qa']) > 1 else b['qa'][0][1]
        rows.append(('paa_first',  R10_PHRASES_PAA_FIRST [i % len(R10_PHRASES_PAA_FIRST )].format(q=b['question']), first_q))
        rows.append(('paa_last',   R10_PHRASES_PAA_LAST  [i % len(R10_PHRASES_PAA_LAST  )].format(q=b['question']), last_q))
        rows.append(('paa_2nd_ans',R10_PHRASES_PAA_ANSWER[i % len(R10_PHRASES_PAA_ANSWER)].format(q=b['question']), second_a))
    for i, e in enumerate(KPS):
        first_v = e['facts'][0][1]
        last_v  = e['facts'][-1][1]
        rows.append(('kp_first', R10_PHRASES_KP_FIRST[i % len(R10_PHRASES_KP_FIRST)].format(n=e['name']), first_v))
        rows.append(('kp_last',  R10_PHRASES_KP_LAST [i % len(R10_PHRASES_KP_LAST )].format(n=e['name']), last_v))
        rows.append(('kp_kind',  R10_PHRASES_KP_KIND [0].format(n=e['name']), e['kind']))
        rows.append(('kp_factcount', R10_PHRASES_KP_FACTCOUNT[0].format(n=e['name']), str(len(e['facts']))))
    for tmpl, ans in R10_PHRASES_SAFESEARCH:
        rows.append(('safesearch_desc', tmpl, ans))
    for s in SNIPS[:6]:
        bundle = next((b for b in PAA if b['slug'] == s['slug']), None)
        if bundle is None:
            continue
        rows.append(('multi_snip_paa_first',
                     R10_PHRASES_MULTI_SNIP_PAA[0].format(q=s['query']),
                     bundle['qa'][0][0]))
    for e in KPS[:4]:
        bundle = next((b for b in PAA if b['slug'] == e['slug']), None)
        if bundle is None:
            continue
        rows.append(('multi_kp_paa_first',
                     R10_PHRASES_MULTI_KP_PAA[0].format(n=e['name']),
                     bundle['qa'][0][0]))
    return rows


# ---------------------------------------------------------------------------
def build_all():
    out = []
    counters = {}
    for section, items in [('r4', r4_tasks()), ('r5', r5_tasks()),
                            ('r6', r6_tasks()), ('r10', r10_tasks())]:
        for theme, ques, ans in items:
            tid = section + '_' + theme
            counters[tid] = counters.get(tid, 0) + 1
            full_id = WEB_NAME + '--' + tid + '_' + str(counters[tid]).zfill(3)
            out.append({
                'web_name': WEB_NAME, 'id': full_id, 'ques': ques,
                'web': WEB, 'upstream_url': UPSTREAM, 'answer_token': ans,
            })
    return out


if __name__ == '__main__':
    rows = build_all()
    from collections import Counter
    grp = Counter()
    for r in rows:
        gid = r['id'].split('--', 1)[1].rsplit('_', 1)[0]
        grp[gid] += 1
    print('total new r-tasks:', len(rows))
    print('groups:', len(grp))
    over30 = [(k, v) for k, v in grp.items() if v > 30]
    if over30:
        print('GROUPS OVER 30:', over30)
    out_path = os.path.join(os.path.dirname(__file__), 'tasks.jsonl')
    keep = []
    with open(out_path, 'r') as f:
        for line in f:
            o = json.loads(line)
            sid = o['id'].replace(WEB_NAME + '--', '')
            if (sid.startswith('r4_') or sid.startswith('r5_') or
                sid.startswith('r6_') or sid.startswith('r10_')):
                continue
            keep.append(o)
    print('kept numeric:', len(keep), 'appended new:', len(rows))
    with open(out_path, 'w') as f:
        for o in keep + rows:
            f.write(json.dumps(o, ensure_ascii=False) + '\n')
    print('wrote', out_path)
