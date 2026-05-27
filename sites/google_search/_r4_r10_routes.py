"""R4 / R5 / R6 / R10 surface routes — DB-backed.

All entity data lives in DB tables (ImageCard / VideoCard / ScholarPaper /
ScholarCitation / FeaturedSnippet / PaaBundle / PaaQuestionRow /
KnowledgePanel / KnowledgePanelFact). The source-of-truth is
`_real_data.py` which is read ONLY by `seed_r4_r10_tables()` at seed time.

Runtime route handlers always query the SQLite seed copy. This means
the byte-identical reset check (md5 of instance_seed/google_search.db
before and after rebuild) sees only DB rows, not Python module state.
"""

import json
from flask import render_template, request, redirect, abort, session


# Static filter taxonomies (these are real Google UI controls, not entity data,
# so they stay as Python constants — they never mutate at runtime).

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

R10_SAFESEARCH_LEVELS = [
    ('off',      'Off',      'Show all results, including explicit content.'),
    ('moderate', 'Moderate', 'Filter explicit images, but allow explicit text.'),
    ('strict',   'Strict',   'Filter explicit images, videos and text from results.'),
]


# ---------------------------------------------------------------------------
# DTO helpers — template-friendly view of an ORM row, hiding DB column names.
# ---------------------------------------------------------------------------

def _img_to_card(img, idx_hint=None):
    return {
        'id': img.id,
        'slug': img.slug,
        'query': img.query_text,
        'title': img.title,
        'source': img.source_domain,
        'source_url': img.source_url,
        'source_owner': img.source_owner,
        'dims': img.dims,
        'thumb': '/static/images/thumb_' + str(img.id) + '.jpg',
        'color': img.color,
        'size': img.size,
        'type': img.type,
        'license': img.license,
        'license_label': img.license_label,
        'alt': img.alt,
        'caption': img.caption,
    }


def _video_to_card(v):
    try:
        caption_lines = json.loads(v.captions_json or '[]')
    except Exception:
        caption_lines = []
    return {
        'id': v.id,
        'slug': v.slug,
        'title': v.title,
        'channel': v.channel,
        'source': v.platform,
        'platform_domain': v.platform_domain,
        'upstream_url': v.upstream_url,
        'duration_bucket': v.duration_bucket,
        'duration': v.duration,
        'quality': v.quality,
        'published': v.published,
        'caption_lang': v.language,
        'description': v.description,
        'caption_lines': caption_lines,
    }


def _paper_to_dict(p):
    return {
        'id': p.id,
        'slug': p.slug,
        'title': p.title,
        'authors': [a.strip() for a in p.authors_csv.split(';') if a.strip()],
        'venue': p.venue,
        'year': p.year,
        'citations': p.citations,
        'abstract': p.abstract,
        'pdf_url': p.pdf_url,
    }


# ---------------------------------------------------------------------------
# Route registration — every handler queries the DB via the app's `models`
# dict that is passed in by `register_all(app, models)`.
# ---------------------------------------------------------------------------

def register_r4(app, M):
    ImageCard = M['ImageCard']
    db = M['db']

    @app.route('/search/images/tools')
    def r4_image_tools():
        return render_template(
            'r4_image_tools.html',
            q=request.args.get('q', ''),
            colors=R4_COLORS, sizes=R4_SIZES, types=R4_TYPES,
            times=R4_TIMES, rights=R4_RIGHTS,
        )

    @app.route('/search/images/color/<color>')
    def r4_image_color(color):
        if color not in {k for k, _, _ in R4_COLORS}:
            abort(404)
        cards = [_img_to_card(c) for c in
                 ImageCard.query.filter_by(color=color).order_by(ImageCard.id).all()]
        label = next(l for k, l, _ in R4_COLORS if k == color)
        return render_template('r4_image_filter.html',
                               kind='color', name=color, label=label, matches=cards)

    @app.route('/search/images/size/<size>')
    def r4_image_size(size):
        if size not in {k for k, _, _ in R4_SIZES}:
            abort(404)
        cards = [_img_to_card(c) for c in
                 ImageCard.query.filter_by(size=size).order_by(ImageCard.id).all()]
        label = next(l for k, l, _ in R4_SIZES if k == size)
        return render_template('r4_image_filter.html',
                               kind='size', name=size, label=label, matches=cards)

    @app.route('/search/images/type/<typ>')
    def r4_image_type(typ):
        if typ not in {k for k, _, _ in R4_TYPES}:
            abort(404)
        cards = [_img_to_card(c) for c in
                 ImageCard.query.filter_by(type=typ).order_by(ImageCard.id).all()]
        label = next(l for k, l, _ in R4_TYPES if k == typ)
        return render_template('r4_image_filter.html',
                               kind='type', name=typ, label=label, matches=cards)

    @app.route('/search/images/usage-rights')
    def r4_image_usage_rights():
        cards = [_img_to_card(c) for c in
                 ImageCard.query.order_by(ImageCard.id).all()]
        return render_template('r4_image_usage_rights.html',
                               rights=R4_RIGHTS, cards=cards)

    @app.route('/search/images/preview/<int:img_id>')
    def r4_image_preview(img_id):
        img = ImageCard.query.get(img_id)
        if not img:
            abort(404)
        card = _img_to_card(img)
        type_index = {k: (k, l, d) for k, l, d in R4_TYPES}
        rights_index = {k: (k, l, d) for k, l, d in R4_RIGHTS}
        return render_template('r4_image_preview.html',
                               card=card, type_index=type_index, rights_index=rights_index)

    # Hub entry — `/images` lands here, with tab bar links to tools / usage-rights
    @app.route('/images')
    def r4_image_hub():
        cards = [_img_to_card(c) for c in
                 ImageCard.query.order_by(ImageCard.id).all()]
        return render_template('r4_image_hub.html',
                               cards=cards, colors=R4_COLORS,
                               sizes=R4_SIZES, types=R4_TYPES, rights=R4_RIGHTS)


def register_r5(app, M):
    VideoCard = M['VideoCard']

    @app.route('/search/videos/filters')
    @app.route('/search/videos/duration/<bucket>')
    def r5_video_filters(bucket=None):
        bucket = bucket or 'any'
        if bucket not in {k for k, _, _ in R5_DURATIONS}:
            abort(404)
        label = next(l for k, l, _ in R5_DURATIONS if k == bucket)
        if bucket == 'any':
            videos = VideoCard.query.order_by(VideoCard.id).all()
        else:
            videos = VideoCard.query.filter_by(duration_bucket=bucket).order_by(VideoCard.id).all()
        return render_template('r5_video_filters.html',
                               bucket=bucket, label=label,
                               matches=[_video_to_card(v) for v in videos],
                               durations=R5_DURATIONS, qualities=R5_QUALITIES,
                               sources=R5_SOURCES, ages=R5_AGES)

    @app.route('/search/videos/quality/<q>')
    def r5_video_quality(q):
        if q not in {k for k, _, _ in R5_QUALITIES}:
            abort(404)
        label = next(l for k, l, _ in R5_QUALITIES if k == q)
        if q == 'any':
            videos = VideoCard.query.order_by(VideoCard.id).all()
        else:
            videos = VideoCard.query.filter_by(quality=q).order_by(VideoCard.id).all()
        return render_template('r5_video_filters.html',
                               bucket=q, label=label,
                               matches=[_video_to_card(v) for v in videos],
                               durations=R5_DURATIONS, qualities=R5_QUALITIES,
                               sources=R5_SOURCES, ages=R5_AGES)

    @app.route('/search/videos/captions/<int:vid>')
    def r5_video_captions(vid):
        v = VideoCard.query.get(vid)
        if not v:
            abort(404)
        return render_template('r5_video_captions.html',
                               v=_video_to_card(v), languages=R5_LANGUAGES)

    # Hub entry — `/videos` lands here, real tabs link to filters
    @app.route('/videos')
    def r5_video_hub():
        videos = [_video_to_card(v) for v in
                  VideoCard.query.order_by(VideoCard.id).all()]
        return render_template('r5_video_hub.html',
                               videos=videos, durations=R5_DURATIONS,
                               qualities=R5_QUALITIES, sources=R5_SOURCES)


def register_r6(app, M):
    ScholarPaper = M['ScholarPaper']
    ScholarCitation = M['ScholarCitation']

    def _lookup(slug):
        p = ScholarPaper.query.filter_by(slug=slug).first()
        return _paper_to_dict(p) if p else None

    @app.route('/scholar/results')
    @app.route('/scholar/search')  # alias for the canonical entry the user expects
    def r6_scholar_results():
        q = (request.args.get('q') or '').strip()
        yr = request.args.get('as_ylo', 'any')
        sort = request.args.get('sort', 'relevance')
        query = ScholarPaper.query
        if q:
            ql = '%' + q.lower() + '%'
            from sqlalchemy import or_, func as sqlf
            query = query.filter(or_(sqlf.lower(ScholarPaper.title).like(ql),
                                     sqlf.lower(ScholarPaper.abstract).like(ql)))
        if yr != 'any':
            try:
                yi = int(yr)
                query = query.filter(ScholarPaper.year >= yi)
            except ValueError:
                pass
        if sort == 'date':
            query = query.order_by(ScholarPaper.year.desc(), ScholarPaper.id)
        elif sort == 'cited':
            query = query.order_by(ScholarPaper.citations.desc(), ScholarPaper.id)
        else:
            query = query.order_by(ScholarPaper.id)
        items = [_paper_to_dict(p) for p in query.all()]
        venue_index = {k: (k, l) for k, l in R6_VENUES}
        return render_template('r6_scholar_results.html',
                               q=q, yr=yr, sort=sort, items=items,
                               years=R6_YEARS, sorts=R6_SORTS, venue_index=venue_index)

    @app.route('/scholar/paper/<slug>')
    def r6_scholar_paper(slug):
        p = _lookup(slug)
        if not p:
            abort(404)
        venue_index = {k: (k, l) for k, l in R6_VENUES}
        venue = venue_index.get(p['venue'])
        cited_rows = (ScholarCitation.query
                      .filter_by(src_slug=slug, resolved=True)
                      .order_by(ScholarCitation.rank).limit(5).all())
        cited_by = [_lookup(r.dst_slug) for r in cited_rows]
        cited_by = [c for c in cited_by if c]
        return render_template('r6_scholar_paper.html',
                               p=p, venue=venue, cited_by=cited_by)

    @app.route('/scholar/cited-by/<slug>')
    def r6_scholar_cited_by(slug):
        p = _lookup(slug)
        if not p:
            abort(404)
        rows = []
        for r in (ScholarCitation.query
                  .filter_by(src_slug=slug)
                  .order_by(ScholarCitation.rank).all()):
            if r.resolved:
                sub = _lookup(r.dst_slug)
                if sub:
                    rows.append({'resolved': True, 'slug': sub['slug'],
                                 'title': sub['title'], 'year': sub['year'],
                                 'citations': sub['citations']})
            else:
                rows.append({'resolved': False, 'slug': r.dst_slug, 'title': r.dst_title})
        return render_template('r6_scholar_cited_by.html', p=p, rows=rows)

    @app.route('/scholar/pdf-preview/<slug>')
    def r6_scholar_pdf_preview(slug):
        p = _lookup(slug)
        if not p:
            abort(404)
        figures = [
            {'caption': 'Figure 1. Architecture overview of ' + p['title'].split(':')[0] + '.'},
            {'caption': 'Figure 2. Quantitative results table comparing baselines.'},
            {'caption': 'Figure 3. Ablation study of key components.'},
        ]
        return render_template('r6_scholar_pdf_preview.html', p=p, figures=figures)


def register_r10(app, M):
    FeaturedSnippet = M['FeaturedSnippet']
    PaaBundle = M['PaaBundle']
    PaaQuestionRow = M['PaaQuestionRow']
    KnowledgePanel = M['KnowledgePanel']
    KnowledgePanelFact = M['KnowledgePanelFact']

    @app.route('/settings/safesearch', methods=['GET', 'POST'])
    def r10_safesearch_settings():
        if request.method == 'POST':
            level = request.form.get('level', 'moderate')
            if level not in {k for k, _, _ in R10_SAFESEARCH_LEVELS}:
                level = 'moderate'
            session['safesearch'] = level
            return redirect('/settings/safesearch')
        current = session.get('safesearch', 'moderate')
        return render_template('r10_safesearch_settings.html',
                               current=current, levels=R10_SAFESEARCH_LEVELS)

    def _snippet_dict(s):
        return {'slug': s.slug, 'query': s.query_text, 'answer': s.answer,
                'kind': s.kind, 'source_domain': s.source_domain,
                'source_url': s.source_url, 'source_title': s.source_title}

    @app.route('/search/featured-snippet/<slug>')
    def r10_featured_snippet(slug):
        s = FeaturedSnippet.query.filter_by(slug=slug).first()
        if not s:
            abort(404)
        all_snippets = [_snippet_dict(x) for x in
                        FeaturedSnippet.query.order_by(FeaturedSnippet.id).all()]
        return render_template('r10_featured_snippet.html',
                               s=_snippet_dict(s), all_snippets=all_snippets)

    @app.route('/search/people-also-ask/<slug>')
    def r10_paa(slug):
        b = PaaBundle.query.filter_by(slug=slug).first()
        if not b:
            abort(404)
        rows = (PaaQuestionRow.query.filter_by(bundle_slug=slug)
                .order_by(PaaQuestionRow.rank).all())
        bundle = {'slug': b.slug, 'question': b.question,
                  'questions': [{'q': r.question, 'a': r.answer} for r in rows]}
        all_bundles = []
        for bb in PaaBundle.query.order_by(PaaBundle.id).all():
            rr = (PaaQuestionRow.query.filter_by(bundle_slug=bb.slug)
                  .order_by(PaaQuestionRow.rank).all())
            all_bundles.append({'slug': bb.slug, 'question': bb.question,
                                'questions': [{'q': r.question, 'a': r.answer} for r in rr]})
        return render_template('r10_paa.html', b=bundle, all_bundles=all_bundles)

    @app.route('/knowledge-panel/<slug>')
    def r10_knowledge_panel(slug):
        e = KnowledgePanel.query.filter_by(slug=slug).first()
        if not e:
            abort(404)
        facts = (KnowledgePanelFact.query.filter_by(panel_slug=slug)
                 .order_by(KnowledgePanelFact.rank).all())
        entity = {'slug': e.slug, 'name': e.name, 'kind': e.kind,
                  'facts': [(f.label, f.value) for f in facts]}
        all_entities = []
        for ee in KnowledgePanel.query.order_by(KnowledgePanel.id).all():
            ff = (KnowledgePanelFact.query.filter_by(panel_slug=ee.slug)
                  .order_by(KnowledgePanelFact.rank).all())
            all_entities.append({'slug': ee.slug, 'name': ee.name, 'kind': ee.kind,
                                 'facts': [(f.label, f.value) for f in ff]})
        return render_template('r10_knowledge_panel.html',
                               e=entity, all_entities=all_entities)


def register_all(app, models):
    """Register all R4-R10 routes against the Flask `app`.

    `models` is a dict of SQLAlchemy classes + db handle, e.g.:
        {'db': db, 'ImageCard': ImageCard, ...}
    """
    register_r4(app, models)
    register_r5(app, models)
    register_r6(app, models)
    register_r10(app, models)
