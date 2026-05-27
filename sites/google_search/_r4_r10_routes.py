"""R4 / R5 / R6 / R10 surface routes for Google Search mirror.

Wires the templates created in `templates/r4_*`, `templates/r5_*`,
`templates/r6_*` and `templates/r10_*` to actual Flask routes so the GUI
flows used by the corresponding tasks in `tasks.jsonl` are reachable.

All data is built deterministically from in-module tables so byte-id
reset is preserved.
"""

from flask import render_template, request, redirect, abort, session


# ---------------------------------------------------------------------------
# R4 — Image search Tools / filters / preview / usage rights
# ---------------------------------------------------------------------------

R4_COLORS = [
    ('red',    'Red',    '#ea4335'),
    ('orange', 'Orange', '#fb8c00'),
    ('yellow', 'Yellow', '#fbbc04'),
    ('green',  'Green',  '#34a853'),
    ('teal',   'Teal',   '#00897b'),
    ('blue',   'Blue',   '#4285f4'),
    ('purple', 'Purple', '#8e24aa'),
    ('pink',   'Pink',   '#e91e63'),
    ('white',  'White',  '#ffffff'),
    ('gray',   'Gray',   '#9aa0a6'),
    ('black',  'Black',  '#202124'),
    ('brown',  'Brown',  '#795548'),
]
R4_SIZES = [
    ('large',  'Large',  '2 MP or larger'),
    ('medium', 'Medium', '400px to 2 MP'),
    ('icon',   'Icon',   'thumbnail / icon'),
]
R4_TYPES = [
    ('photo',       'Photo',       'Photographic images.'),
    ('clipart',     'Clip art',    'Stylised illustrations.'),
    ('lineart',     'Line drawing','Sketch / line art.'),
    ('gif',         'GIF',         'Animated GIFs.'),
    ('transparent', 'Transparent', 'PNGs with transparent backgrounds.'),
]
R4_TIMES = [
    ('any',  'Any time',   ''),
    ('d',    'Past 24 hours', 'qdr:d'),
    ('w',    'Past week',  'qdr:w'),
    ('m',    'Past month', 'qdr:m'),
    ('y',    'Past year',  'qdr:y'),
]
R4_RIGHTS = [
    ('cc_by', 'Creative Commons - BY',     'Attribution required.'),
    ('cc_ba', 'Creative Commons - BY-SA',  'Attribution and share-alike.'),
    ('cc_nc', 'Creative Commons - BY-NC',  'Non-commercial use only.'),
    ('cc0',   'Creative Commons - CC0',    'No rights reserved.'),
    ('com',   'Commercial license',        'Licensed for commercial use.'),
]

R4_TITLES = [
    'Aurora over the Norwegian fjords',          # 1
    'Lavender field at sunset in Provence',      # 2
    'Old town square panorama in Prague',        # 3
    'Snow leopard cub in the Hindu Kush',        # 4
    'Cherry blossom canopy in Kyoto',            # 5
    'Patagonia ice trek aerial view',            # 6
    'Macro shot of dragonfly wings',             # 7
    'Vintage train station clock face',          # 8
    'Coffee art latte heart',                    # 9
    'Sahara dunes at golden hour',               # 10
    'Rainforest river canopy reflection',        # 11
    'Italian renaissance ceiling fresco',        # 12
    'Northern lights time-lapse still',          # 13
    'Bonsai forest miniature scene',             # 14
    'Tokyo skyline neon nightscape',             # 15
    'Antarctic emperor penguin colony',          # 16
    'Mountain bike on alpine ridge',             # 17
    'Botanical illustration of dahlia',          # 18
    'Brutalist library reading hall',            # 19
    'Stratocumulus over open ocean',             # 20
    'Glacier-fed turquoise alpine lake',         # 21
    'Hot-air balloons over Cappadocia',          # 22
    'Sequoia trunk close-up bark texture',       # 23
    'Mosaic glass dome ceiling Lisbon',          # 24
]
R4_SOURCES = [
    'nasa.gov', 'unsplash.com', 'wikimedia.org', 'natgeo.com',
    'flickr.com', 'pexels.com', 'gettyimages.com', 'shutterstock.com',
    'pixabay.com', 'imgur.com', 'reddit.com', 'tumblr.com',
]


def _r4_card(i):
    """Build deterministic image card for 1-based index."""
    n = i - 1
    color = R4_COLORS[n % len(R4_COLORS)][0]
    size  = R4_SIZES[n % len(R4_SIZES)][0]
    typ   = R4_TYPES[n % len(R4_TYPES)][0]
    lic   = R4_RIGHTS[n % len(R4_RIGHTS)][0]
    dims_pool = ['4032x3024', '1920x1080', '1280x720', '800x600', '512x512',
                 '2048x1365', '3000x2000', '1600x900']
    dims = dims_pool[n % len(dims_pool)]
    source = R4_SOURCES[n % len(R4_SOURCES)]
    title = R4_TITLES[n % len(R4_TITLES)]
    slug = (title.lower()
                 .replace("'", '')
                 .replace(',', '')
                 .replace('.', '')
                 .replace('-', ' ')
                 .replace('/', ' ')
                 .replace('  ', ' ')
                 .strip()
                 .replace(' ', '_'))[:60]
    alt = 'Photograph: ' + title
    return {
        'id': i,
        'slug': slug,
        'title': title,
        'source': source,
        'dims': dims,
        'thumb': '/static/images/thumb_' + str(i) + '.jpg',
        'color': color,
        'size': size,
        'type': typ,
        'license': lic,
        'alt': alt,
    }


R4_CARDS = [_r4_card(i) for i in range(1, 25)]


def register_r4(app):
    @app.route('/search/images/tools')
    def r4_image_tools():
        return render_template(
            'r4_image_tools.html',
            q=request.args.get('q', ''),
            colors=R4_COLORS,
            sizes=R4_SIZES,
            types=R4_TYPES,
            times=R4_TIMES,
            rights=R4_RIGHTS,
        )

    @app.route('/search/images/color/<color>')
    def r4_image_color(color):
        if color not in {k for k, _, _ in R4_COLORS}:
            abort(404)
        matches = [c for c in R4_CARDS if c['color'] == color]
        label = next(l for k, l, _ in R4_COLORS if k == color)
        return render_template(
            'r4_image_filter.html',
            kind='color', name=color, label=label, matches=matches,
        )

    @app.route('/search/images/size/<size>')
    def r4_image_size(size):
        if size not in {k for k, _, _ in R4_SIZES}:
            abort(404)
        matches = [c for c in R4_CARDS if c['size'] == size]
        label = next(l for k, l, _ in R4_SIZES if k == size)
        return render_template(
            'r4_image_filter.html',
            kind='size', name=size, label=label, matches=matches,
        )

    @app.route('/search/images/type/<typ>')
    def r4_image_type(typ):
        if typ not in {k for k, _, _ in R4_TYPES}:
            abort(404)
        matches = [c for c in R4_CARDS if c['type'] == typ]
        label = next(l for k, l, _ in R4_TYPES if k == typ)
        return render_template(
            'r4_image_filter.html',
            kind='type', name=typ, label=label, matches=matches,
        )

    @app.route('/search/images/usage-rights')
    def r4_image_usage_rights():
        return render_template(
            'r4_image_usage_rights.html',
            rights=R4_RIGHTS,
            cards=R4_CARDS,
        )

    @app.route('/search/images/preview/<int:img_id>')
    def r4_image_preview(img_id):
        if img_id < 1 or img_id > len(R4_CARDS):
            abort(404)
        card = R4_CARDS[img_id - 1]
        type_index = {k: (k, l, d) for k, l, d in R4_TYPES}
        rights_index = {k: (k, l, d) for k, l, d in R4_RIGHTS}
        return render_template(
            'r4_image_preview.html',
            card=card, type_index=type_index, rights_index=rights_index,
        )


# ---------------------------------------------------------------------------
# R5 — Video search filters + closed captions
# ---------------------------------------------------------------------------

R5_DURATIONS = [
    ('any',    'Any duration', ''),
    ('short',  'Short',  'under 4 minutes'),
    ('medium', 'Medium', '4-20 minutes'),
    ('long',   'Long',   'over 20 minutes'),
    ('film',   'Film',   'feature length'),
]
R5_QUALITIES = [
    ('any', 'Any quality', ''),
    ('hd',  '720p HD',  '720p'),
    ('fhd', '1080p Full HD', '1080p'),
    ('4k',  '4K Ultra HD',   '2160p'),
]
R5_SOURCES = [
    ('youtube', 'YouTube',   'youtube.com'),
    ('vimeo',   'Vimeo',     'vimeo.com'),
    ('dailym',  'Dailymotion','dailymotion.com'),
    ('archive', 'Archive.org','archive.org'),
    ('ted',     'TED',       'ted.com'),
]
R5_AGES = [
    ('any',  'Any time', ''),
    ('d',    'Past 24 hours', 'qdr:d'),
    ('w',    'Past week',  'qdr:w'),
    ('m',    'Past month', 'qdr:m'),
    ('y',    'Past year',  'qdr:y'),
]
R5_LANGUAGES = [
    ('en', 'English'),
    ('es', 'Spanish'),
    ('fr', 'French'),
    ('de', 'German'),
    ('ja', 'Japanese'),
    ('zh', 'Chinese (Simplified)'),
    ('hi', 'Hindi'),
    ('pt', 'Portuguese'),
]

R5_VIDEO_TITLES = [
    'Build a Rust web server in 10 minutes',           # 1 short
    'Photosynthesis explained for beginners',          # 2 medium
    'The history of the silk road (full documentary)', # 3 long
    'Bach Cello Suite No.1 - live performance',        # 4 medium
    'How LLMs really work - 3Blue1Brown overview',     # 5 long
    'Northern lights time-lapse 4K',                   # 6 short
    'TED: A brief history of the universe',            # 7 medium
    'Mount Everest 1996 disaster - feature film',      # 8 film
    'Cooking pasta carbonara the Roman way',           # 9 short
    'How GPS works - animated explainer',              # 10 medium
    'Beethoven symphony 9 - Berlin Philharmonic',      # 11 film
    'Quantum entanglement in 5 minutes',               # 12 short
    'Inside the Hubble Space Telescope',               # 13 long
    'Tokyo street walk - rainy night ASMR',            # 14 long
    'Soldering basics for hobbyists',                  # 15 short
    'AlphaFold and the protein folding revolution',    # 16 medium
    'Climate models 101 - what they predict',          # 17 medium
    'The Apollo 13 mission - full feature',            # 18 film
    'Tigers in the Sundarbans - documentary',          # 19 long
    'Stock market basics in 7 minutes',                # 20 short
    'AI safety panel at NeurIPS 2024',                 # 21 long
    'Aurora chasing in Iceland - cinematic',           # 22 medium
    'Building a chess engine from scratch',            # 23 medium
    'Antarctic expedition diary - feature length',     # 24 film
]
R5_CHANNELS = [
    'Fireship', 'CrashCourse', 'TED-Ed', 'Vsauce', 'Numberphile',
    'Veritasium', 'Smarter Every Day', 'Kurzgesagt', 'PBS Space Time',
    '3Blue1Brown', 'BBC Earth', 'National Geographic', 'NASA', 'MIT OCW',
    'Stanford Online', 'Computerphile',
]


def _r5_video(i):
    n = i - 1
    bucket_pool = ['short', 'medium', 'long', 'short', 'medium', 'long',
                   'medium', 'film', 'short', 'medium', 'film', 'short',
                   'long', 'long', 'short', 'medium', 'medium', 'film',
                   'long', 'short', 'long', 'medium', 'medium', 'film']
    quality_pool = ['hd', 'fhd', '4k']
    durstr_pool = {
        'short':  ['1:42', '2:13', '3:01', '3:48'],
        'medium': ['5:30', '8:14', '12:01', '17:42'],
        'long':   ['24:08', '32:14', '47:55', '58:30'],
        'film':   ['1:32:14', '1:48:00', '2:01:55', '2:15:08'],
    }
    bucket = bucket_pool[n]
    return {
        'id': i,
        'title': R5_VIDEO_TITLES[n],
        'channel': R5_CHANNELS[n % len(R5_CHANNELS)],
        'source': R5_SOURCES[n % len(R5_SOURCES)][1],
        'duration_bucket': bucket,
        'duration': durstr_pool[bucket][n % 4],
        'quality': quality_pool[n % len(quality_pool)],
        'published': '2024-' + str(((n * 7) % 12) + 1).zfill(2) + '-' + str(((n * 3) % 27) + 1).zfill(2),
        'caption_lang': R5_LANGUAGES[n % len(R5_LANGUAGES)][0],
        'caption_lines': [
            'Line ' + str(j + 1) + ' of captions for: ' + R5_VIDEO_TITLES[n][:32]
            for j in range(6)
        ],
    }


R5_VIDEOS = [_r5_video(i) for i in range(1, 25)]


def register_r5(app):
    @app.route('/search/videos/filters')
    @app.route('/search/videos/duration/<bucket>')
    def r5_video_filters(bucket=None):
        bucket = bucket or 'any'
        if bucket not in {k for k, _, _ in R5_DURATIONS}:
            abort(404)
        label = next(l for k, l, _ in R5_DURATIONS if k == bucket)
        if bucket == 'any':
            matches = R5_VIDEOS
        else:
            matches = [v for v in R5_VIDEOS if v['duration_bucket'] == bucket]
        return render_template(
            'r5_video_filters.html',
            bucket=bucket, label=label, matches=matches,
            durations=R5_DURATIONS, qualities=R5_QUALITIES,
            sources=R5_SOURCES, ages=R5_AGES,
        )

    @app.route('/search/videos/quality/<q>')
    def r5_video_quality(q):
        if q not in {k for k, _, _ in R5_QUALITIES}:
            abort(404)
        label = next(l for k, l, _ in R5_QUALITIES if k == q)
        if q == 'any':
            matches = R5_VIDEOS
        else:
            matches = [v for v in R5_VIDEOS if v['quality'] == q]
        return render_template(
            'r5_video_filters.html',
            bucket=q, label=label, matches=matches,
            durations=R5_DURATIONS, qualities=R5_QUALITIES,
            sources=R5_SOURCES, ages=R5_AGES,
        )

    @app.route('/search/videos/captions/<int:vid>')
    def r5_video_captions(vid):
        if vid < 1 or vid > len(R5_VIDEOS):
            abort(404)
        v = R5_VIDEOS[vid - 1]
        return render_template(
            'r5_video_captions.html', v=v, languages=R5_LANGUAGES,
        )


# ---------------------------------------------------------------------------
# R6 — Google Scholar sub-tab + paper detail + cited-by + PDF preview
# ---------------------------------------------------------------------------

R6_VENUES = [
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
]
R6_YEARS = [
    ('any',  'Any time'),
    ('2024', 'Since 2024'),
    ('2022', 'Since 2022'),
    ('2020', 'Since 2020'),
    ('2018', 'Since 2018'),
]
R6_SORTS = [
    ('relevance', 'Sort by relevance'),
    ('date',      'Sort by date'),
    ('cited',     'Sort by citation count'),
]

R6_PAPERS = [
    {
        'slug': 'attention_is_all_you_need',
        'title': 'Attention Is All You Need',
        'authors': ['Vaswani, A.', 'Shazeer, N.', 'Parmar, N.', 'Uszkoreit, J.', 'Jones, L.'],
        'venue': 'neurips', 'year': 2017, 'citations': 121043,
        'abstract': 'We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.',
        'pdf_url': 'https://arxiv.org/pdf/1706.03762.pdf',
    },
    {
        'slug': 'bert_pretraining',
        'title': 'BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding',
        'authors': ['Devlin, J.', 'Chang, M.', 'Lee, K.', 'Toutanova, K.'],
        'venue': 'arxiv', 'year': 2018, 'citations': 96214,
        'abstract': 'We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers.',
        'pdf_url': 'https://arxiv.org/pdf/1810.04805.pdf',
    },
    {
        'slug': 'gpt3_paper',
        'title': 'Language Models are Few-Shot Learners',
        'authors': ['Brown, T.', 'Mann, B.', 'Ryder, N.'],
        'venue': 'neurips', 'year': 2020, 'citations': 41882,
        'abstract': 'GPT-3, an autoregressive language model with 175 billion parameters, achieves strong performance on many NLP tasks in a few-shot setting.',
        'pdf_url': 'https://arxiv.org/pdf/2005.14165.pdf',
    },
    {
        'slug': 'chinchilla_scaling',
        'title': 'Training Compute-Optimal Large Language Models',
        'authors': ['Hoffmann, J.', 'Borgeaud, S.', 'Mensch, A.'],
        'venue': 'neurips', 'year': 2022, 'citations': 4612,
        'abstract': 'We investigate the optimal model size and number of tokens for training a transformer language model under a given compute budget.',
        'pdf_url': 'https://arxiv.org/pdf/2203.15556.pdf',
    },
    {
        'slug': 'palm_pathways',
        'title': 'PaLM: Scaling Language Modeling with Pathways',
        'authors': ['Chowdhery, A.', 'Narang, S.', 'Devlin, J.'],
        'venue': 'arxiv', 'year': 2022, 'citations': 6204,
        'abstract': 'We trained a 540-billion parameter, densely activated Transformer language model and call it PaLM (Pathways Language Model).',
        'pdf_url': 'https://arxiv.org/pdf/2204.02311.pdf',
    },
    {
        'slug': 'vit_image_is_worth',
        'title': 'An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale',
        'authors': ['Dosovitskiy, A.', 'Beyer, L.', 'Kolesnikov, A.'],
        'venue': 'iclr', 'year': 2021, 'citations': 38911,
        'abstract': 'We show that a pure transformer applied directly to sequences of image patches can perform very well on image classification tasks.',
        'pdf_url': 'https://arxiv.org/pdf/2010.11929.pdf',
    },
    {
        'slug': 'clip_paper',
        'title': 'Learning Transferable Visual Models From Natural Language Supervision',
        'authors': ['Radford, A.', 'Kim, J. W.', 'Hallacy, C.'],
        'venue': 'icml', 'year': 2021, 'citations': 21347,
        'abstract': 'We demonstrate that contrastive pre-training on (image, text) pairs scales to learn state-of-the-art image representations from scratch.',
        'pdf_url': 'https://arxiv.org/pdf/2103.00020.pdf',
    },
    {
        'slug': 'alphafold2',
        'title': 'Highly accurate protein structure prediction with AlphaFold',
        'authors': ['Jumper, J.', 'Evans, R.', 'Pritzel, A.'],
        'venue': 'nature', 'year': 2021, 'citations': 28911,
        'abstract': 'We present AlphaFold, a computational method that predicts protein structures with atomic accuracy even where no similar structure is known.',
        'pdf_url': 'https://www.nature.com/articles/s41586-021-03819-2.pdf',
    },
    {
        'slug': 'med_diet_predimed',
        'title': 'Primary Prevention of Cardiovascular Disease with a Mediterranean Diet (PREDIMED)',
        'authors': ['Estruch, R.', 'Ros, E.', 'Salas-Salvado, J.'],
        'venue': 'nejm', 'year': 2018, 'citations': 6731,
        'abstract': 'A Mediterranean diet supplemented with extra-virgin olive oil or mixed nuts reduced the incidence of major cardiovascular events.',
        'pdf_url': 'https://www.nejm.org/doi/pdf/10.1056/NEJMoa1800389',
    },
    {
        'slug': 'event_horizon_m87',
        'title': 'First M87 Event Horizon Telescope Results - The Shadow of the Supermassive Black Hole',
        'authors': ['EHT Collaboration'],
        'venue': 'science', 'year': 2019, 'citations': 4912,
        'abstract': 'We present the first image of the shadow of the supermassive black hole at the centre of the galaxy M87.',
        'pdf_url': 'https://arxiv.org/pdf/1906.11238.pdf',
    },
    {
        'slug': 'ipcc_ar6_wg1',
        'title': 'IPCC AR6 Working Group I: The Physical Science Basis',
        'authors': ['IPCC'],
        'venue': 'ipcc', 'year': 2021, 'citations': 13288,
        'abstract': 'Human influence has unequivocally warmed the climate; widespread changes in the atmosphere, ocean, cryosphere and biosphere have occurred.',
        'pdf_url': 'https://www.ipcc.ch/report/ar6/wg1/downloads/report/IPCC_AR6_WGI_FullReport.pdf',
    },
    {
        'slug': 'photosynthesis_zscheme',
        'title': 'Revisiting the Z-Scheme of Oxygenic Photosynthesis',
        'authors': ['Govindjee, R.', 'Shevela, D.'],
        'venue': 'cell', 'year': 2019, 'citations': 882,
        'abstract': 'We revisit the canonical Z-scheme and incorporate recent kinetic and structural data on the photosynthetic electron transport chain.',
        'pdf_url': 'https://www.cell.com/photosynth-zscheme.pdf',
    },
    {
        'slug': 'llama2_paper',
        'title': 'Llama 2: Open Foundation and Fine-Tuned Chat Models',
        'authors': ['Touvron, H.', 'Martin, L.', 'Stone, K.'],
        'venue': 'arxiv', 'year': 2023, 'citations': 12842,
        'abstract': 'We release Llama 2, a collection of pretrained and fine-tuned LLMs ranging from 7B to 70B parameters.',
        'pdf_url': 'https://arxiv.org/pdf/2307.09288.pdf',
    },
    {
        'slug': 'gpt4_tech_report',
        'title': 'GPT-4 Technical Report',
        'authors': ['OpenAI'],
        'venue': 'arxiv', 'year': 2023, 'citations': 18044,
        'abstract': 'GPT-4 is a large-scale, multimodal model which can accept image and text inputs and produce text outputs.',
        'pdf_url': 'https://arxiv.org/pdf/2303.08774.pdf',
    },
    {
        'slug': 'instructgpt',
        'title': 'Training Language Models to Follow Instructions with Human Feedback',
        'authors': ['Ouyang, L.', 'Wu, J.', 'Jiang, X.'],
        'venue': 'neurips', 'year': 2022, 'citations': 9123,
        'abstract': 'We show an avenue for aligning language models with user intent by fine-tuning with human feedback (RLHF).',
        'pdf_url': 'https://arxiv.org/pdf/2203.02155.pdf',
    },
    {
        'slug': 'dpo_paper',
        'title': 'Direct Preference Optimization: Your Language Model is Secretly a Reward Model',
        'authors': ['Rafailov, R.', 'Sharma, A.', 'Mitchell, E.'],
        'venue': 'neurips', 'year': 2023, 'citations': 3128,
        'abstract': 'DPO is a stable, performant and computationally lightweight algorithm that eliminates the need for a separate reward model in RLHF.',
        'pdf_url': 'https://arxiv.org/pdf/2305.18290.pdf',
    },
]

# Hard-coded resolved follow-ups (use real slugs from R6_PAPERS where possible)
R6_CITED_BY = {
    'attention_is_all_you_need': ['bert_pretraining', 'gpt3_paper', 'vit_image_is_worth', 'palm_pathways', 'llama2_paper'],
    'bert_pretraining':          ['gpt3_paper', 'instructgpt', 'palm_pathways'],
    'gpt3_paper':                ['palm_pathways', 'instructgpt', 'llama2_paper', 'gpt4_tech_report'],
    'chinchilla_scaling':        ['llama2_paper', 'gpt4_tech_report'],
    'palm_pathways':             ['llama2_paper', 'gpt4_tech_report'],
    'vit_image_is_worth':        ['clip_paper'],
    'clip_paper':                ['vit_image_is_worth'],
    'alphafold2':                [],
    'med_diet_predimed':         [],
    'event_horizon_m87':         [],
    'ipcc_ar6_wg1':              [],
    'photosynthesis_zscheme':    [],
    'llama2_paper':              ['gpt4_tech_report', 'dpo_paper'],
    'gpt4_tech_report':          ['dpo_paper'],
    'instructgpt':               ['llama2_paper', 'dpo_paper'],
    'dpo_paper':                 [],
}
# Stub citations (unresolved external papers)
R6_CITED_BY_STUBS = {
    'attention_is_all_you_need': [
        ('Transformer-XL: Attentive Language Models Beyond a Fixed-Length Context', 'transformer_xl'),
        ('Reformer: The Efficient Transformer', 'reformer'),
    ],
    'alphafold2': [
        ('ESMFold: Atomic-resolution protein structure with a language model', 'esmfold'),
        ('OmegaFold: High-accuracy protein structure from a single sequence', 'omegafold'),
    ],
    'event_horizon_m87': [
        ('Sagittarius A* shadow imaging', 'sgr_a_star'),
    ],
    'med_diet_predimed': [
        ('Adherence to Mediterranean diet and longevity', 'med_diet_longevity'),
    ],
    'ipcc_ar6_wg1': [
        ('Regional climate projections in CMIP6', 'cmip6_regional'),
        ('Sea-level rise scenarios to 2100', 'slr_2100'),
    ],
}


def _r6_lookup(slug):
    for p in R6_PAPERS:
        if p['slug'] == slug:
            return p
    return None


def _r6_figures(p):
    base = [
        'Figure 1. Architecture overview of ' + p['title'].split(':')[0] + '.',
        'Figure 2. Quantitative results table comparing baselines.',
        'Figure 3. Ablation study of key components.',
    ]
    return [{'caption': c} for c in base]


def register_r6(app):
    @app.route('/scholar/results')
    def r6_scholar_results():
        q = (request.args.get('q') or '').strip()
        yr = request.args.get('as_ylo', 'any')
        sort = request.args.get('sort', 'relevance')
        items = list(R6_PAPERS)
        if q:
            ql = q.lower()
            items = [p for p in items if ql in p['title'].lower() or ql in p['abstract'].lower()]
        if yr != 'any':
            try:
                yi = int(yr)
                items = [p for p in items if p['year'] >= yi]
            except ValueError:
                pass
        if sort == 'date':
            items = sorted(items, key=lambda p: -p['year'])
        elif sort == 'cited':
            items = sorted(items, key=lambda p: -p['citations'])
        venue_index = {k: (k, l) for k, l in R6_VENUES}
        return render_template(
            'r6_scholar_results.html',
            q=q, yr=yr, sort=sort, items=items,
            years=R6_YEARS, sorts=R6_SORTS, venue_index=venue_index,
        )

    @app.route('/scholar/paper/<slug>')
    def r6_scholar_paper(slug):
        p = _r6_lookup(slug)
        if not p:
            abort(404)
        venue_index = {k: (k, l) for k, l in R6_VENUES}
        venue = venue_index.get(p['venue'])
        resolved = [_r6_lookup(s) for s in R6_CITED_BY.get(slug, []) if _r6_lookup(s)]
        cited_by = resolved[:5]
        return render_template(
            'r6_scholar_paper.html', p=p, venue=venue, cited_by=cited_by,
        )

    @app.route('/scholar/cited-by/<slug>')
    def r6_scholar_cited_by(slug):
        p = _r6_lookup(slug)
        if not p:
            abort(404)
        rows = []
        for s in R6_CITED_BY.get(slug, []):
            sub = _r6_lookup(s)
            if sub:
                rows.append({
                    'resolved': True, 'slug': sub['slug'], 'title': sub['title'],
                    'year': sub['year'], 'citations': sub['citations'],
                })
        for title, sslug in R6_CITED_BY_STUBS.get(slug, []):
            rows.append({'resolved': False, 'slug': sslug, 'title': title})
        return render_template('r6_scholar_cited_by.html', p=p, rows=rows)

    @app.route('/scholar/pdf-preview/<slug>')
    def r6_scholar_pdf_preview(slug):
        p = _r6_lookup(slug)
        if not p:
            abort(404)
        return render_template(
            'r6_scholar_pdf_preview.html', p=p, figures=_r6_figures(p),
        )


# ---------------------------------------------------------------------------
# R10 — SafeSearch + featured snippet + PAA + knowledge panel
# ---------------------------------------------------------------------------

R10_SAFESEARCH_LEVELS = [
    ('off',      'Off',      'Show all results, including explicit content.'),
    ('moderate', 'Moderate', 'Filter explicit images, but allow explicit text.'),
    ('strict',   'Strict',   'Filter explicit images, videos and text from results.'),
]

R10_FEATURED_SNIPPETS = [
    {
        'slug': 'photosynthesis',
        'query': 'What is photosynthesis?',
        'answer': 'Photosynthesis is the biochemical process by which green plants convert light energy, water and carbon dioxide into glucose and oxygen.',
        'kind': 'paragraph', 'source_domain': 'britannica.com',
        'source_url': 'https://www.britannica.com/science/photosynthesis',
        'source_title': 'Photosynthesis - Definition, Diagram, & Facts',
    },
    {
        'slug': 'large_language_model',
        'query': 'What is a large language model?',
        'answer': 'A large language model (LLM) is a deep-learning model trained on massive text corpora to predict and generate human-like text.',
        'kind': 'paragraph', 'source_domain': 'nvidia.com',
        'source_url': 'https://www.nvidia.com/llm', 'source_title': 'Large Language Models - NVIDIA',
    },
    {
        'slug': 'black_hole',
        'query': 'How is a black hole formed?',
        'answer': 'A stellar-mass black hole forms when a massive star (>20 solar masses) exhausts its nuclear fuel and its core collapses under gravity.',
        'kind': 'paragraph', 'source_domain': 'nasa.gov',
        'source_url': 'https://www.nasa.gov/black-holes',
        'source_title': 'What Is a Black Hole? - NASA',
    },
    {
        'slug': 'mediterranean_diet',
        'query': 'What foods are in the Mediterranean diet?',
        'answer': 'The Mediterranean diet emphasises olive oil, fresh vegetables, legumes, whole grains, fish, nuts and moderate red wine.',
        'kind': 'list', 'source_domain': 'mayoclinic.org',
        'source_url': 'https://www.mayoclinic.org/mediterranean-diet',
        'source_title': 'Mediterranean Diet - Mayo Clinic',
    },
    {
        'slug': 'climate_change_causes',
        'query': 'What causes climate change?',
        'answer': 'Climate change is driven primarily by the burning of fossil fuels, deforestation, agriculture and industrial emissions of greenhouse gases.',
        'kind': 'paragraph', 'source_domain': 'un.org',
        'source_url': 'https://www.un.org/climatechange-causes',
        'source_title': 'Causes and Effects of Climate Change - UN',
    },
    {
        'slug': 'quantum_entanglement',
        'query': 'What is quantum entanglement?',
        'answer': 'Quantum entanglement is a phenomenon in which two or more particles share a quantum state such that measurement of one instantly affects the other.',
        'kind': 'paragraph', 'source_domain': 'caltech.edu',
        'source_url': 'https://www.caltech.edu/entanglement',
        'source_title': 'Quantum Entanglement Explained - Caltech',
    },
    {
        'slug': 'super_bowl_lviii',
        'query': 'Who won Super Bowl LVIII?',
        'answer': 'The Kansas City Chiefs defeated the San Francisco 49ers 25-22 in overtime to win Super Bowl LVIII on 11 February 2024.',
        'kind': 'paragraph', 'source_domain': 'nfl.com',
        'source_url': 'https://www.nfl.com/super-bowl-lviii',
        'source_title': 'Super Bowl LVIII - NFL.com',
    },
    {
        'slug': 'wimbledon_2024',
        'query': 'Who won Wimbledon 2024 mens singles?',
        'answer': 'Carlos Alcaraz defeated Novak Djokovic in straight sets to win the 2024 Wimbledon mens singles title.',
        'kind': 'paragraph', 'source_domain': 'wimbledon.com',
        'source_url': 'https://www.wimbledon.com/2024',
        'source_title': 'Wimbledon 2024 Champions',
    },
    {
        'slug': 'olympic_games_2026',
        'query': 'Where are the 2026 Winter Olympics?',
        'answer': 'The 2026 Winter Olympics are scheduled to be held in Milan and Cortina dAmpezzo, Italy, from 6 to 22 February 2026.',
        'kind': 'paragraph', 'source_domain': 'olympics.com',
        'source_url': 'https://www.olympics.com/milano-cortina-2026',
        'source_title': 'Milano Cortina 2026',
    },
    {
        'slug': 'oppenheimer',
        'query': 'Who directed Oppenheimer?',
        'answer': 'Oppenheimer (2023) was directed by Christopher Nolan and starred Cillian Murphy in the title role.',
        'kind': 'paragraph', 'source_domain': 'imdb.com',
        'source_url': 'https://www.imdb.com/title/tt15398776/',
        'source_title': 'Oppenheimer (2023) - IMDb',
    },
    {
        'slug': 'barbie',
        'query': 'Who directed Barbie movie?',
        'answer': 'Barbie (2023) was directed by Greta Gerwig and starred Margot Robbie and Ryan Gosling.',
        'kind': 'paragraph', 'source_domain': 'imdb.com',
        'source_url': 'https://www.imdb.com/title/tt1517268/',
        'source_title': 'Barbie (2023) - IMDb',
    },
    {
        'slug': 'dune_part_two',
        'query': 'When was Dune Part Two released?',
        'answer': 'Dune: Part Two was released in cinemas on 1 March 2024 and was directed by Denis Villeneuve.',
        'kind': 'paragraph', 'source_domain': 'imdb.com',
        'source_url': 'https://www.imdb.com/title/tt15239678/',
        'source_title': 'Dune: Part Two (2024) - IMDb',
    },
]

R10_PAA_BUNDLES = [
    {
        'slug': 'photosynthesis',
        'question': 'How does photosynthesis work?',
        'questions': [
            {'q': 'What are the inputs of photosynthesis?',
             'a': 'Carbon dioxide, water and light energy.'},
            {'q': 'What are the outputs of photosynthesis?',
             'a': 'Glucose and oxygen.'},
            {'q': 'Where does photosynthesis happen in a plant cell?',
             'a': 'In the chloroplasts, specifically inside the thylakoid membranes.'},
            {'q': 'What is the Z-scheme in photosynthesis?',
             'a': 'It is the diagram describing electron flow through Photosystem II and Photosystem I.'},
        ],
    },
    {
        'slug': 'large_language_model',
        'question': 'How does a large language model work?',
        'questions': [
            {'q': 'What is a token?', 'a': 'A token is a sub-word unit produced by a tokenizer.'},
            {'q': 'What is RLHF?', 'a': 'Reinforcement Learning from Human Feedback fine-tunes a model with human preference data.'},
            {'q': 'What is a transformer?', 'a': 'A neural architecture based on self-attention.'},
        ],
    },
    {
        'slug': 'black_hole',
        'question': 'What happens inside a black hole?',
        'questions': [
            {'q': 'What is the event horizon?',
             'a': 'The boundary beyond which nothing can escape, not even light.'},
            {'q': 'What is Hawking radiation?',
             'a': 'Theoretical thermal radiation predicted to be emitted from black-hole horizons.'},
            {'q': 'How are black holes detected?',
             'a': 'Via X-ray emissions from accretion disks, gravitational lensing or gravitational-wave signatures.'},
        ],
    },
    {
        'slug': 'mediterranean_diet',
        'question': 'Is the Mediterranean diet healthy?',
        'questions': [
            {'q': 'What does PREDIMED say?',
             'a': 'PREDIMED showed reduced major cardiovascular events with EVOO or nut supplementation.'},
            {'q': 'Is red wine recommended?',
             'a': 'Moderate red wine with meals is part of the traditional pattern.'},
            {'q': 'Does the diet help with weight loss?',
             'a': 'It can support modest weight loss when combined with calorie awareness.'},
        ],
    },
    {
        'slug': 'climate_change_causes',
        'question': 'What is the biggest cause of climate change?',
        'questions': [
            {'q': 'How much warming is from CO2?',
             'a': 'Roughly two-thirds of observed warming since 1850 is attributable to CO2.'},
            {'q': 'What about methane?',
             'a': 'Methane is the second-largest contributor and has a higher short-term warming potential.'},
            {'q': 'Does deforestation matter?',
             'a': 'Yes, both as a CO2 source and a sink reduction.'},
            {'q': 'What does the IPCC AR6 conclude?',
             'a': 'Human influence has unequivocally warmed the climate.'},
        ],
    },
    {
        'slug': 'quantum_entanglement',
        'question': 'Why is quantum entanglement spooky?',
        'questions': [
            {'q': 'Does it allow faster-than-light signalling?',
             'a': 'No, no usable information is transmitted.'},
            {'q': 'What is Bells theorem?',
             'a': 'It shows no local hidden-variable theory can reproduce all quantum predictions.'},
            {'q': 'How is entanglement used in computing?',
             'a': 'It is a core resource in quantum algorithms and quantum teleportation.'},
        ],
    },
    {
        'slug': 'lebron_james',
        'question': 'How tall is LeBron James?',
        'questions': [
            {'q': 'How many NBA titles does LeBron have?',
             'a': 'Four NBA championships (2012, 2013, 2016, 2020).'},
            {'q': 'When did LeBron join the Lakers?',
             'a': 'July 2018.'},
            {'q': 'Who is LeBrons agent?',
             'a': 'Rich Paul of Klutch Sports Group.'},
        ],
    },
    {
        'slug': 'oppenheimer',
        'question': 'How long is Oppenheimer the movie?',
        'questions': [
            {'q': 'How many Oscars did Oppenheimer win?',
             'a': 'Seven Academy Awards including Best Picture and Best Director.'},
            {'q': 'Is Oppenheimer based on a book?',
             'a': 'Yes, on American Prometheus by Kai Bird and Martin J. Sherwin.'},
            {'q': 'What is Oppenheimer rated?',
             'a': 'R for some sexuality, nudity and language.'},
        ],
    },
    {
        'slug': 'dune_part_two',
        'question': 'Will there be a Dune part three?',
        'questions': [
            {'q': 'Who plays Paul Atreides?',
             'a': 'Timothée Chalamet.'},
            {'q': 'Is Dune Part Two on streaming?',
             'a': 'It is available on Max in many regions.'},
            {'q': 'What is Arrakis?',
             'a': 'A desert planet and the only source of the spice melange.'},
        ],
    },
    {
        'slug': 'tesla_model_s',
        'question': 'What is the range of a Tesla Model S?',
        'questions': [
            {'q': 'What is the 0-60 time of a Model S Plaid?',
             'a': '1.99 seconds with rollout (Tesla figures).'},
            {'q': 'How much does a Model S cost?',
             'a': 'Starting around 79,990 USD for the Long Range trim.'},
            {'q': 'Does Model S have Autopilot?',
             'a': 'Yes, with optional Full Self-Driving capability.'},
        ],
    },
]

R10_KNOWLEDGE_PANELS = [
    {
        'slug': 'lebron_james', 'name': 'LeBron James', 'kind': 'Basketball player',
        'facts': [
            ('Born', '30 December 1984 (age 41)'),
            ('Height', '6 ft 9 in (2.06 m)'),
            ('Weight', '250 lb (113 kg)'),
            ('Team', 'Los Angeles Lakers (#23)'),
            ('Position', 'Small forward'),
            ('Career points', 'over 40,000'),
            ('Spouse', 'Savannah Brinson (m. 2013)'),
        ],
    },
    {
        'slug': 'stephen_curry', 'name': 'Stephen Curry', 'kind': 'Basketball player',
        'facts': [
            ('Born', '14 March 1988 (age 38)'),
            ('Height', '6 ft 2 in (1.88 m)'),
            ('Team', 'Golden State Warriors (#30)'),
            ('Position', 'Point guard'),
            ('NBA titles', '4 (2015, 2017, 2018, 2022)'),
            ('Spouse', 'Ayesha Curry (m. 2011)'),
        ],
    },
    {
        'slug': 'oppenheimer_movie', 'name': 'Oppenheimer', 'kind': '2023 film',
        'facts': [
            ('Director', 'Christopher Nolan'),
            ('Release date', '21 July 2023'),
            ('Runtime', '180 minutes'),
            ('Box office', '975.8 million USD'),
            ('Studio', 'Universal Pictures'),
            ('Rating', 'R'),
        ],
    },
    {
        'slug': 'barbie_movie', 'name': 'Barbie', 'kind': '2023 film',
        'facts': [
            ('Director', 'Greta Gerwig'),
            ('Release date', '21 July 2023'),
            ('Runtime', '114 minutes'),
            ('Box office', '1.446 billion USD'),
            ('Studio', 'Warner Bros. Pictures'),
            ('Rating', 'PG-13'),
        ],
    },
    {
        'slug': 'apple_m4', 'name': 'Apple M4', 'kind': 'System on a chip',
        'facts': [
            ('Manufacturer', 'Apple Inc.'),
            ('Launched', '7 May 2024'),
            ('Process', 'TSMC N3E (3 nm)'),
            ('CPU cores', 'up to 10'),
            ('GPU cores', 'up to 10'),
            ('Memory', 'up to 32 GB unified'),
        ],
    },
    {
        'slug': 'tesla_model_s', 'name': 'Tesla Model S', 'kind': 'Electric car',
        'facts': [
            ('Manufacturer', 'Tesla, Inc.'),
            ('Production', 'since 2012'),
            ('Range (EPA)', 'up to 402 mi (Long Range)'),
            ('0-60 mph', '1.99 s (Plaid)'),
            ('Body style', 'liftback sedan'),
            ('Starting price', '79,990 USD'),
        ],
    },
    {
        'slug': 'mount_everest', 'name': 'Mount Everest', 'kind': 'Mountain',
        'facts': [
            ('Elevation', '8,848.86 m (29,031.7 ft)'),
            ('Location', 'Mahalangur Himal, Nepal / China border'),
            ('First ascent', '29 May 1953'),
            ('First climbers', 'Edmund Hillary and Tenzing Norgay'),
            ('Parent peak', 'none (highest above sea level)'),
        ],
    },
    {
        'slug': 'grand_canyon', 'name': 'Grand Canyon', 'kind': 'Canyon',
        'facts': [
            ('Location', 'Arizona, United States'),
            ('Length', '446 km (277 mi)'),
            ('Width', 'up to 29 km (18 mi)'),
            ('Depth', 'over 1,800 m (6,000 ft)'),
            ('Status', 'UNESCO World Heritage Site (1979)'),
            ('Visitors', 'about 4.9 million per year'),
        ],
    },
]


def register_r10(app):
    @app.route('/settings/safesearch', methods=['GET', 'POST'])
    def r10_safesearch_settings():
        if request.method == 'POST':
            level = request.form.get('level', 'moderate')
            if level not in {k for k, _, _ in R10_SAFESEARCH_LEVELS}:
                level = 'moderate'
            session['safesearch'] = level
            return redirect('/settings/safesearch')
        current = session.get('safesearch', 'moderate')
        return render_template(
            'r10_safesearch_settings.html',
            current=current, levels=R10_SAFESEARCH_LEVELS,
        )

    @app.route('/search/featured-snippet/<slug>')
    def r10_featured_snippet(slug):
        s = next((x for x in R10_FEATURED_SNIPPETS if x['slug'] == slug), None)
        if not s:
            abort(404)
        return render_template(
            'r10_featured_snippet.html', s=s, all_snippets=R10_FEATURED_SNIPPETS,
        )

    @app.route('/search/people-also-ask/<slug>')
    def r10_paa(slug):
        b = next((x for x in R10_PAA_BUNDLES if x['slug'] == slug), None)
        if not b:
            abort(404)
        return render_template(
            'r10_paa.html', b=b, all_bundles=R10_PAA_BUNDLES,
        )

    @app.route('/knowledge-panel/<slug>')
    def r10_knowledge_panel(slug):
        e = next((x for x in R10_KNOWLEDGE_PANELS if x['slug'] == slug), None)
        if not e:
            abort(404)
        return render_template(
            'r10_knowledge_panel.html', e=e, all_entities=R10_KNOWLEDGE_PANELS,
        )


def register_all(app):
    register_r4(app)
    register_r5(app)
    register_r6(app)
    register_r10(app)
