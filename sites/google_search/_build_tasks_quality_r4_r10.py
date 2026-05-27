"""R4 / R5 / R6 / R10 quality task generator — GUI-style.

Produces natural-language tasks (no /api/, no JSON, no URL ?-strings) that
exercise the surfaces wired by _r4_r10_routes.py. Each task's answer lives
on a detail page (preview / paper / cited-by / knowledge panel / PAA /
featured snippet) so the agent must click through, not just read the
listing page.

Layout: 4 themed sections (image, video, scholar, modules) × ~6 patterns
each. Task ids use a `rN_<theme>_<NNN>` naming convention so diversity is
visible from a glance at tasks.jsonl.
"""
import json
import os

# Import the data tables from the routes module via importlib (we cannot
# rely on package import because app.py runs as a script).
import importlib.util as _ilu

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = _ilu.spec_from_file_location(
    '_r4_r10_routes', os.path.join(HERE, '_r4_r10_routes.py'),
)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

R4_CARDS = _mod.R4_CARDS
R4_COLORS = _mod.R4_COLORS
R4_SIZES = _mod.R4_SIZES
R4_TYPES = _mod.R4_TYPES
R4_RIGHTS = _mod.R4_RIGHTS
R5_VIDEOS = _mod.R5_VIDEOS
R5_DURATIONS = _mod.R5_DURATIONS
R5_QUALITIES = _mod.R5_QUALITIES
R6_PAPERS = _mod.R6_PAPERS
R6_VENUES = _mod.R6_VENUES
R6_CITED_BY = _mod.R6_CITED_BY
R10_FEATURED = _mod.R10_FEATURED_SNIPPETS
R10_PAA = _mod.R10_PAA_BUNDLES
R10_KP = _mod.R10_KNOWLEDGE_PANELS
R10_LEVELS = _mod.R10_SAFESEARCH_LEVELS

WEB = 'http://localhost:40009/'
UPSTREAM = 'https://www.google.com/'
WEB_NAME = 'Google Search'


# ---------------------------------------------------------------------------
# R4 — Image search (target: 250+)
# ---------------------------------------------------------------------------
def r4_image_tasks():
    rows = []  # list of (theme, ques)
    # P1: preview source (detail-only field)
    for c in R4_CARDS:
        rows.append(('preview_source', (
            "Go to Google's Image search Tools panel, navigate to the image "
            "card titled \"" + c['title'] + "\" and report the source "
            "domain shown on its preview page."
        )))
    # P2: preview alt text
    for c in R4_CARDS:
        rows.append(('preview_alt', (
            "Find the image preview page for \"" + c['title'] + "\" via "
            "Google Images and copy the Alt text it lists."
        )))
    # P3: preview dimensions (detail page Dimensions row)
    for c in R4_CARDS:
        rows.append(('preview_dims', (
            "Open the Google Images preview for \"" + c['title'] + "\" and "
            "tell me the dimensions printed on the metadata table."
        )))
    # P4: preview image type
    for c in R4_CARDS:
        rows.append(('preview_type', (
            "On Google Images, open the preview of \"" + c['title'] + "\" "
            "and report which image Type it falls under (Photo, Clip art, "
            "Line drawing, GIF or Transparent)."
        )))
    # P5: color filter -> count
    for k, lbl, _sw in R4_COLORS:
        count = sum(1 for c in R4_CARDS if c['color'] == k)
        rows.append(('color_count', (
            "On Google Images, open the Tools panel, then click the \"" + lbl +
            "\" color swatch under the Color section and tell me how many "
            "image cards appear on the filtered listing."
        )))
        del count  # answer kept only for reference
    # P6: size filter -> first match title
    for k, lbl, _det in R4_SIZES:
        rows.append(('size_first', (
            "On Google Images, click Tools, expand the Size section and "
            "follow the \"" + lbl + "\" link; report the title of the first "
            "image card on that filtered page."
        )))
    # P7: type filter -> count
    for k, lbl, _det in R4_TYPES:
        rows.append(('type_count', (
            "On Google Images Tools, browse to the Type filter and count how "
            "many cards are listed under \"" + lbl + "\"."
        )))
    # P8: usage rights -> which cards under CC0
    for k, lbl, _det in R4_RIGHTS:
        rows.append(('rights_titles', (
            "On Google Images, open Tools then Usage rights; list the titles "
            "of every image card grouped under \"" + lbl + "\"."
        )))
    # P9: tools-panel walkthrough (multi-step)
    for c in R4_CARDS:
        rows.append(('tools_to_preview', (
            "On Google Images, click Tools, scroll to the Color filter, pick "
            "the swatch for the color " + c['color'] + ", then click the "
            "image titled \"" + c['title'] + "\" and tell me the source "
            "domain on its preview page."
        )))
    # P10: cross-filter (color + size) — list titles that appear in both
    for ci in range(8):
        ck = R4_COLORS[ci][0]
        for sk, slbl, _ in R4_SIZES:
            rows.append(('cross_color_size', (
                "On Google Images, first open the color filter page for " +
                ck + ", then open the size filter page for " + slbl + " — "
                "name the image card (if any) that appears in both filtered "
                "listings."
            )))
    # P11: source attribution
    for c in R4_CARDS[:18]:
        rows.append(('preview_source_owner', (
            "Look up the Google Images preview for \"" + c['title'] +
            "\" and tell me which site the image is credited to."
        )))
    # P12: license per card via Tools
    for c in R4_CARDS:
        rows.append(('preview_license', (
            "Go to Google Images, click Tools then Usage rights, and from "
            "there find the listing entry for \"" + c['title'] + "\"; report "
            "which usage-rights bucket it sits under."
        )))
    # P13: from a color filter -> click card -> read its size bucket
    for c in R4_CARDS[:18]:
        rows.append(('color_to_size', (
            "On Google Images, open the Tools > Color filter for " +
            c['color'] + ", click into \"" + c['title'] + "\", and report "
            "which Size bucket the metadata table shows."
        )))
    # P14: disambiguation — title overlap is intentional ("Northern lights" appears as id 13 and a similar aurora photo as id 1)
    rows.append(('disambig_northern_lights', (
        "On Google Images I see two cards that both relate to the aurora — "
        "one called \"Aurora over the Norwegian fjords\" and another "
        "\"Northern lights time-lapse still\". Open each preview page and "
        "tell me which one is licensed for commercial use."
    )))
    rows.append(('disambig_kyoto_canopy', (
        "I'm comparing two greenery shots on Google Images — \"Cherry blossom "
        "canopy in Kyoto\" and \"Rainforest river canopy reflection\". Open "
        "both image previews and tell me which one has the larger pixel "
        "dimensions."
    )))
    rows.append(('disambig_train_clock', (
        "On Google Images there's a card called \"Vintage train station clock "
        "face\" and another \"Old town square panorama in Prague\". Open "
        "each preview and tell me which one is hosted on wikimedia.org."
    )))
    rows.append(('disambig_penguin_leopard', (
        "Open Google Images, then preview both \"Antarctic emperor penguin "
        "colony\" and \"Snow leopard cub in the Hindu Kush\"; which one is "
        "categorised under Type = Clip art?"
    )))
    rows.append(('disambig_fresco_dome', (
        "From Google Images Tools, open the previews for both \"Italian "
        "renaissance ceiling fresco\" and \"Mosaic glass dome ceiling "
        "Lisbon\" and tell me which one was sourced from natgeo.com."
    )))
    # P15: 5-step trajectory — tools -> rights -> click card -> read alt
    for c in R4_CARDS[:14]:
        rows.append(('rights_to_alt', (
            "Open Google Images Tools, click Usage rights, find the entry "
            "for \"" + c['title'] + "\" under its license group, open its "
            "preview page and tell me the Alt text."
        )))
    # P16: type-filter -> click card -> read source domain
    for c in R4_CARDS:
        rows.append(('type_to_preview_source', (
            "On Google Images, open Tools then the Type filter for " +
            c['type'] + "; click the entry titled \"" + c['title'] +
            "\" and report the source domain on its preview page."
        )))
    return rows


# ---------------------------------------------------------------------------
# R5 — Video search (target: 200+)
# ---------------------------------------------------------------------------
def r5_video_tasks():
    rows = []
    # P1: captions language (detail-only)
    for v in R5_VIDEOS:
        rows.append(('captions_lang', (
            "On Google Videos, open the duration filter for " +
            v['duration_bucket'] + ", click the video titled \"" + v['title'] +
            "\", and tell me which language its closed-captions are in."
        )))
    # P2: first caption line
    for v in R5_VIDEOS:
        rows.append(('captions_line1', (
            "Open the closed-captions page for \"" + v['title'] + "\" on "
            "Google Videos and report the very first caption line shown."
        )))
    # P3: channel attribution
    for v in R5_VIDEOS:
        rows.append(('captions_channel', (
            "On Google Videos, find the duration listing that contains \"" +
            v['title'] + "\", click into it, and tell me which channel "
            "uploaded the video."
        )))
    # P4: duration string after clicking through filter
    for v in R5_VIDEOS[:18]:
        rows.append(('captions_duration', (
            "From Google Videos > Tools > Duration = " + v['duration_bucket'] +
            ", click \"" + v['title'] + "\" and tell me the duration "
            "(mm:ss or hh:mm:ss) printed on the captions page."
        )))
    # P5: duration bucket count
    for k, lbl, _det in R5_DURATIONS:
        rows.append(('dur_count', (
            "Open Google Videos, click Tools then set Duration to \"" + lbl +
            "\" and report how many videos match that bucket."
        )))
    # P6: quality bucket count
    for k, lbl, _det in R5_QUALITIES:
        rows.append(('qual_count', (
            "On Google Videos, open Tools and switch the Quality filter to " +
            lbl + "; tell me how many results stay on the page."
        )))
    # P7: published date detail
    for v in R5_VIDEOS:
        rows.append(('captions_published', (
            "Open the captions page for the Google Videos result \"" +
            v['title'] + "\" and tell me the published date."
        )))
    # P8: multi-step — duration -> first video -> caption lang
    for k, lbl, _det in R5_DURATIONS:
        rows.append(('dur_first_caption', (
            "On Google Videos, click Tools > Duration > " + lbl + ". Click "
            "the first video listed, then tell me which language its closed "
            "captions are in."
        )))
    # P9: quality -> first channel
    for k, lbl, _det in R5_QUALITIES:
        rows.append(('qual_first_channel', (
            "On Google Videos, open Tools > Quality > " + lbl + " and tell "
            "me the channel name of the first video on the filtered page."
        )))
    # P10: cross duration + caption languages list size
    for v in R5_VIDEOS[:12]:
        rows.append(('captions_lang_count', (
            "On the captions page for Google Videos result \"" + v['title'] +
            "\", how many caption languages are listed under \"Other "
            "available caption languages\"?"
        )))
    # P11: disambig — two videos with similar topic
    rows.append(('disambig_aurora_videos', (
        "There are two aurora-themed Google Videos results — \"Northern "
        "lights time-lapse 4K\" and \"Aurora chasing in Iceland - cinematic\". "
        "Open each captions page and tell me which one has a longer duration."
    )))
    rows.append(('disambig_ai_videos', (
        "Two Google Videos results discuss large language models: \"How LLMs "
        "really work - 3Blue1Brown overview\" and \"AI safety panel at "
        "NeurIPS 2024\". Open each captions page and report which uploader "
        "(channel) handled the panel."
    )))
    rows.append(('disambig_climate_videos', (
        "On Google Videos there are two climate-related results — \"Climate "
        "models 101 - what they predict\" and \"AlphaFold and the protein "
        "folding revolution\". Click into each captions page and tell me "
        "which one is rated as Medium duration."
    )))
    # P12: source attribution from captions page
    for v in R5_VIDEOS[:16]:
        rows.append(('captions_source', (
            "Open \"" + v['title'] + "\" on Google Videos via the duration "
            "filter and tell me which video source (YouTube, Vimeo, etc.) "
            "the captions page header lists."
        )))
    # P13: full multi-step trajectory
    for v in R5_VIDEOS[:14]:
        rows.append(('full_traj', (
            "Open Google Videos, click Tools, then Duration > " +
            v['duration_bucket'] + ". Find \"" + v['title'] + "\" in the "
            "list, click it to open the captions view, and tell me which "
            "channel published it and how many caption lines appear under "
            "the closed-captions block."
        )))
    # P14: search the captions page via Quality filter chain
    for v in R5_VIDEOS:
        rows.append(('qual_to_captions', (
            "On Google Videos, click Tools then set Quality to " +
            v['quality'] + ", find \"" + v['title'] + "\" and click into "
            "its captions page; report the published date."
        )))
    # P15: captions page back-link target
    for v in R5_VIDEOS[:12]:
        rows.append(('captions_back_target', (
            "Open the captions page for \"" + v['title'] + "\" on Google "
            "Videos and tell me what duration bucket the \"back to ...\" "
            "breadcrumb at the top points to."
        )))
    # P16: captions transcript - last line
    for v in R5_VIDEOS[:16]:
        rows.append(('captions_lastline', (
            "On the captions page for the Google Video \"" + v['title'] +
            "\", scroll to the final caption line and copy its text."
        )))
    return rows


# ---------------------------------------------------------------------------
# R6 — Scholar (target: 200+)
# ---------------------------------------------------------------------------
def r6_scholar_tasks():
    rows = []
    # P1: paper detail - venue
    for p in R6_PAPERS:
        rows.append(('paper_venue', (
            "On Google Scholar, search for \"" + p['title'][:40] + "\" and "
            "open the paper page; report the venue label printed below the "
            "title."
        )))
    # P2: paper detail - citation count (also on listing but we ask after click)
    for p in R6_PAPERS:
        rows.append(('paper_year', (
            "Go to Google Scholar and open the paper titled \"" + p['title'] +
            "\". What publication year is printed on its paper detail page?"
        )))
    # P3: paper abstract opener
    for p in R6_PAPERS:
        rows.append(('paper_abstract', (
            "On Google Scholar, search for \"" + p['title'] + "\", click "
            "into the paper, and copy the first sentence of the Abstract."
        )))
    # P4: cited-by resolved list — show first follow-up title
    for slug, lst in R6_CITED_BY.items():
        if not lst:
            continue
        p = next(pp for pp in R6_PAPERS if pp['slug'] == slug)
        rows.append(('citedby_first', (
            "On Google Scholar, open the paper \"" + p['title'] + "\" and "
            "click the \"View cited-by list\" link; report the title of the "
            "first resolved follow-up paper listed there."
        )))
    # P5: cited-by counts
    for slug, lst in R6_CITED_BY.items():
        p = next(pp for pp in R6_PAPERS if pp['slug'] == slug)
        rows.append(('citedby_count', (
            "On Google Scholar, open the cited-by page for \"" + p['title'] +
            "\" and tell me how many resolved follow-up papers it lists "
            "(do not count entries marked as stubs)."
        )))
    # P6: PDF preview - figure captions
    for p in R6_PAPERS:
        rows.append(('pdf_figure1', (
            "On Google Scholar, open the paper \"" + p['title'] + "\" and "
            "follow the \"PDF preview\" link; copy the caption of Figure 1."
        )))
    # P7: PDF preview - count figures
    for p in R6_PAPERS:
        rows.append(('pdf_figcount', (
            "Open the Google Scholar PDF preview for \"" + p['title'] +
            "\" and tell me how many figure captions are listed on the "
            "synthetic page-1 mockup."
        )))
    # P8: results listing sort by date — first paper title
    rows.append(('sort_date', (
        "On Google Scholar results, change the sort dropdown to \"Sort by "
        "date\" and click Apply. Tell me the title of the first paper on "
        "the listing."
    )))
    rows.append(('sort_cited', (
        "On Google Scholar results, change the sort dropdown to \"Sort by "
        "citation count\" and apply. Report the title of the most-cited "
        "paper at the top of the list."
    )))
    # P9: year filter
    for yr in ['2024', '2022', '2020', '2018']:
        rows.append(('year_filter_count', (
            "On Google Scholar results, change the year dropdown to \"Since "
            + yr + "\" and click Apply; how many papers remain in the list?"
        )))
    # P10: multi-step — results -> paper -> cited-by -> first follow-up year
    for slug, lst in R6_CITED_BY.items():
        if not lst:
            continue
        p = next(pp for pp in R6_PAPERS if pp['slug'] == slug)
        rows.append(('results_to_citedby_year', (
            "From Google Scholar results, open \"" + p['title'] + "\", click "
            "\"View cited-by list\", and report the publication year shown "
            "next to the first resolved follow-up."
        )))
    # P11: 5-step — results -> paper -> pdf preview -> figure 3 caption
    for p in R6_PAPERS[:10]:
        rows.append(('paper_to_pdf_fig3', (
            "Open Google Scholar results, click into the paper \"" +
            p['title'] + "\", then follow \"PDF preview\", and copy the "
            "caption that appears as Figure 3."
        )))
    # P12: search-query filter
    for q in ['transformer', 'climate', 'photosynthesis', 'protein',
              'language model', 'black hole', 'Mediterranean', 'GPT',
              'BERT', 'Llama']:
        rows.append(('search_query_first', (
            "On Google Scholar, type \"" + q + "\" into the search box, "
            "press Apply, and report the title of the first paper on the "
            "results page."
        )))
    # P13: disambiguation
    rows.append(('disambig_gpt_papers', (
        "On Google Scholar there are two GPT-related entries — \"Language "
        "Models are Few-Shot Learners\" and \"GPT-4 Technical Report\". "
        "Open each paper page and tell me which has a higher citation "
        "count."
    )))
    rows.append(('disambig_protein_papers', (
        "Google Scholar surfaces both \"Highly accurate protein structure "
        "prediction with AlphaFold\" and \"Revisiting the Z-Scheme of "
        "Oxygenic Photosynthesis\". Open each paper page and tell me which "
        "is published in a journal named Nature."
    )))
    rows.append(('disambig_climate_papers', (
        "On Google Scholar I see \"IPCC AR6 Working Group I: The Physical "
        "Science Basis\" and \"Primary Prevention of Cardiovascular Disease "
        "with a Mediterranean Diet (PREDIMED)\". Open the paper pages and "
        "tell me which one has more than 10,000 citations."
    )))
    rows.append(('disambig_llm_papers', (
        "Two LLM alignment papers show up on Google Scholar — \"Training "
        "Language Models to Follow Instructions with Human Feedback\" and "
        "\"Direct Preference Optimization: Your Language Model is Secretly "
        "a Reward Model\". Open both paper detail pages and tell me which "
        "one was published more recently."
    )))
    # P14: cited-by stub recognition
    rows.append(('citedby_stub', (
        "Open the Google Scholar paper \"Attention Is All You Need\" and "
        "click View cited-by list. Some entries are marked as \"(stub)\"; "
        "name one of those unresolved stub titles."
    )))
    rows.append(('citedby_stub_alphafold', (
        "On Google Scholar, open AlphaFold's cited-by page and report the "
        "slug of any cited-by entry that is rendered as a stub rather than "
        "a clickable paper link."
    )))
    # P15: results -> filter by year -> open paper
    rows.append(('year_filter_to_paper', (
        "On Google Scholar, set the year filter to \"Since 2022\" and "
        "apply. From the filtered listing, open the paper \"Llama 2: Open "
        "Foundation and Fine-Tuned Chat Models\" and tell me how many "
        "citations the detail page reports."
    )))
    rows.append(('cited_sort_to_authors', (
        "On Google Scholar, sort the results by citation count and click "
        "into the top entry; copy the full list of authors from its paper "
        "detail page."
    )))
    # P16: paper authors list
    for p in R6_PAPERS:
        rows.append(('paper_authors', (
            "On Google Scholar, search for \"" + p['title'][:36] + "\" and "
            "open the paper page; copy the complete authors line as printed "
            "under the title."
        )))
    # P17: cited-by - resolved follow-ups names
    for slug, lst in R6_CITED_BY.items():
        if len(lst) < 2:
            continue
        p = next(pp for pp in R6_PAPERS if pp['slug'] == slug)
        rows.append(('citedby_secondresolved', (
            "Open Google Scholar's cited-by page for \"" + p['title'] +
            "\" and report the title of the SECOND resolved follow-up "
            "(skip stubs)."
        )))
    # P18: paper -> pdf preview -> abstract first words
    for p in R6_PAPERS:
        rows.append(('pdf_abstract_first', (
            "Open the Google Scholar PDF preview for \"" + p['title'] +
            "\" and copy the first 12 words of the Abstract block printed "
            "inside the synthetic page-1 mockup."
        )))
    # P19: results listing card - "Cited by N" link
    for p in R6_PAPERS:
        rows.append(('paper_cited_link', (
            "On Google Scholar, click into the paper \"" + p['title'] +
            "\" and follow the \"View cited-by list\" link. What number "
            "appears next to \"Cited by\" in the header of that page?"
        )))
    # P20: full multi-step (results -> sort cited -> paper -> pdf preview)
    rows.append(('multi_sort_pdf_fig2', (
        "On Google Scholar results, sort by citation count, click into the "
        "top paper, then follow PDF preview and copy the caption of Figure 2."
    )))
    rows.append(('multi_sort_pdf_authors', (
        "On Google Scholar, sort the listing by date, open the most recent "
        "paper, click PDF preview, and tell me the year printed under the "
        "authors line on the synthetic page-1 mockup."
    )))
    # P21: paper -> follow-ups -> open follow-up -> read its year
    for slug, lst in R6_CITED_BY.items():
        if not lst:
            continue
        p = next(pp for pp in R6_PAPERS if pp['slug'] == slug)
        rows.append(('followup_year', (
            "From Google Scholar, open the paper \"" + p['title'] + "\". "
            "It lists Highly-cited follow-ups; click the first follow-up "
            "and tell me the publication year shown on that follow-up's "
            "paper detail page."
        )))
    # P22: cited-by header citation count
    for p in R6_PAPERS[:12]:
        rows.append(('citedby_header_count', (
            "Open the Google Scholar cited-by page for \"" + p['title'] +
            "\" and report the citation count printed in the page header."
        )))
    return rows


# ---------------------------------------------------------------------------
# R10 — SafeSearch + AI/PAA/Knowledge/Featured (target: 150+, GUI-only)
# ---------------------------------------------------------------------------
def r10_module_tasks():
    rows = []
    # P1: SafeSearch — set then read current
    for k, lbl, _desc in R10_LEVELS:
        rows.append(('safesearch_set', (
            "Open Google's /settings/safesearch page, pick the \"" + lbl +
            "\" radio option and click Save; after the redirect, tell me "
            "which level the page lists as Current."
        )))
    rows.append(('safesearch_desc_strict', (
        "Visit Google's SafeSearch settings page and report the description "
        "shown for the \"Strict\" option."
    )))
    rows.append(('safesearch_desc_moderate', (
        "On Google's SafeSearch settings page, copy the description shown "
        "below the \"Moderate\" radio button."
    )))
    rows.append(('safesearch_default', (
        "Open Google's SafeSearch settings page without changing anything "
        "and tell me which level is shown as Current by default."
    )))
    # P2: featured snippet — source domain
    for s in R10_FEATURED:
        rows.append(('featured_source', (
            "On Google, search for \"" + s['query'] + "\" and look at the "
            "featured snippet that appears; report the source domain printed "
            "above the answer."
        )))
    # P3: featured snippet — source title
    for s in R10_FEATURED:
        rows.append(('featured_srctitle', (
            "When Google shows a featured snippet for \"" + s['query'] +
            "\", what is the source title linked at the top of the snippet "
            "card?"
        )))
    # P4: featured snippet — kind (paragraph/list)
    for s in R10_FEATURED:
        rows.append(('featured_kind', (
            "Search Google for \"" + s['query'] + "\" and open the featured "
            "snippet; tell me what \"kind\" label it shows (paragraph, "
            "list, etc.)."
        )))
    # P5: featured snippet — answer text
    for s in R10_FEATURED:
        rows.append(('featured_answer', (
            "On Google, run the query \"" + s['query'] + "\" and copy the "
            "answer text printed inside the featured snippet card."
        )))
    # P6: PAA — number of expandable rows
    for b in R10_PAA:
        rows.append(('paa_count', (
            "On Google, search for \"" + b['question'] + "\" and look at "
            "the People also ask block; expand each row and tell me how "
            "many questions are inside it."
        )))
    # P7: PAA — Nth question
    for b in R10_PAA:
        rows.append(('paa_q2', (
            "Open the People also ask panel for \"" + b['question'] + "\" "
            "on Google. What is the second question listed?"
        )))
    # P8: PAA — answer text for a specific Q
    for b in R10_PAA[:8]:
        first_q = b['questions'][0]['q']
        rows.append(('paa_q_a', (
            "On Google's People also ask block for \"" + b['question'] +
            "\", expand the question \"" + first_q + "\" and copy the answer."
        )))
    # P9: Knowledge panel — first fact
    for e in R10_KP:
        rows.append(('kp_first_fact', (
            "On Google, search for \"" + e['name'] + "\". A Knowledge panel "
            "appears on the right — tell me the value in the first row of "
            "the facts table."
        )))
    # P10: KP — kind label
    for e in R10_KP:
        rows.append(('kp_kind', (
            "Search Google for \"" + e['name'] + "\" and look at the "
            "Knowledge panel header; what kind of entity is it labelled as?"
        )))
    # P11: KP — specific field
    rows.append(('kp_lebron_height', (
        "On Google, look up LeBron James and read the Knowledge panel; what "
        "is his height?"
    )))
    rows.append(('kp_curry_titles', (
        "Search Google for Stephen Curry and check the Knowledge panel; how "
        "many NBA titles does it list?"
    )))
    rows.append(('kp_oppenheimer_box', (
        "Look up Oppenheimer the 2023 film on Google and report the box "
        "office figure printed in the Knowledge panel."
    )))
    rows.append(('kp_barbie_director', (
        "Search Google for the Barbie movie and report the director listed "
        "in the Knowledge panel."
    )))
    rows.append(('kp_apple_m4_process', (
        "Search Google for the Apple M4 chip and report the process node "
        "shown in the Knowledge panel."
    )))
    rows.append(('kp_tesla_range', (
        "Look up the Tesla Model S on Google and tell me the EPA range "
        "stated in the Knowledge panel."
    )))
    rows.append(('kp_everest_elevation', (
        "Search Google for Mount Everest and report the elevation listed "
        "in the Knowledge panel."
    )))
    rows.append(('kp_canyon_visitors', (
        "On Google, look up the Grand Canyon and report the annual visitor "
        "count printed in the Knowledge panel."
    )))
    # P12: multi-step trajectories — featured -> back to SERP -> PAA
    for s in R10_FEATURED[:8]:
        # pick a PAA with matching slug if available
        paa_slug = next(
            (b['slug'] for b in R10_PAA if b['slug'] == s['slug']),
            R10_PAA[0]['slug'],
        )
        paa_question = next(b['question'] for b in R10_PAA if b['slug'] == paa_slug)
        rows.append(('featured_to_paa', (
            "On Google, search for \"" + s['query'] + "\". Read the featured "
            "snippet card, then scroll to the People also ask block for the "
            "topic \"" + paa_question + "\" and tell me what its very first "
            "expandable question asks."
        )))
    # P13: SafeSearch -> back to search -> featured snippet still renders
    rows.append(('safesearch_then_featured', (
        "Open Google's SafeSearch settings and set the level to Strict and "
        "save. Then go back and search for \"What is photosynthesis?\" — "
        "does the featured snippet still appear, and if so, what source "
        "domain does it cite?"
    )))
    rows.append(('safesearch_then_kp', (
        "Set SafeSearch to Moderate on Google's settings page, then look up "
        "Mount Everest and report the elevation row in the Knowledge panel."
    )))
    # P14: disambiguation
    rows.append(('disambig_two_2023_films', (
        "Two 2023 films show Knowledge panels on Google — Oppenheimer and "
        "Barbie. Open each panel and tell me which one had a higher box "
        "office gross."
    )))
    rows.append(('disambig_two_athletes', (
        "On Google, both LeBron James and Stephen Curry have Knowledge "
        "panels. Open each and tell me which one currently plays for the "
        "Golden State Warriors."
    )))
    rows.append(('disambig_paa_diet', (
        "Google has People also ask blocks for both \"How does "
        "photosynthesis work?\" and \"Is the Mediterranean diet healthy?\". "
        "Open the latter and tell me what PREDIMED concluded according to "
        "the first expandable answer."
    )))
    # P15: multi-step PAA -> related KP
    rows.append(('paa_kp_lebron', (
        "On Google, open the People also ask block for \"How tall is LeBron "
        "James?\". After reading the entries, navigate to the LeBron James "
        "Knowledge panel and report his weight."
    )))
    rows.append(('paa_kp_tesla', (
        "From the People also ask block for \"What is the range of a Tesla "
        "Model S?\" on Google, jump to the Tesla Model S Knowledge panel "
        "and tell me its starting price."
    )))
    # P16: SafeSearch description ordering
    rows.append(('safesearch_three_options', (
        "On Google's SafeSearch settings page, list the three radio "
        "options shown — in the exact order they appear top to bottom."
    )))
    # P17: knowledge panel — facts table row count
    for e in R10_KP:
        rows.append(('kp_factcount', (
            "Search Google for \"" + e['name'] + "\" and open the Knowledge "
            "panel; how many rows does its facts table have?"
        )))
    # P18: featured snippet -> related PAA topic
    rows.append(('featured_paa_climate', (
        "Search Google for \"What causes climate change?\" and read the "
        "featured snippet. Then scroll to the People also ask block titled "
        "\"What is the biggest cause of climate change?\" and report the "
        "answer about methane."
    )))
    rows.append(('featured_paa_lm', (
        "On Google search \"What is a large language model?\", view the "
        "featured snippet, then expand the People also ask question \"What "
        "is RLHF?\" and copy the answer."
    )))
    # P19: PAA - all answers concatenation
    for b in R10_PAA:
        rows.append(('paa_last_q', (
            "Open the People also ask block on Google for \"" +
            b['question'] + "\" and tell me what the LAST expandable "
            "question reads."
        )))
    # P20: KP — last fact
    for e in R10_KP:
        rows.append(('kp_last_fact', (
            "Search Google for \"" + e['name'] + "\" and look at the "
            "Knowledge panel facts table; copy the value in the very "
            "LAST row."
        )))
    # P21: featured snippet -> jump to listing of pinned snippets
    for s in R10_FEATURED[:6]:
        rows.append(('featured_pinned_list', (
            "Search Google for \"" + s['query'] + "\". Open the featured "
            "snippet card, then scroll to \"All pinned featured snippets\" "
            "and tell me how many entries are listed there."
        )))
    return rows


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
TASKS_PATH = os.path.join(HERE, 'tasks.jsonl')
# IDs that previously used the sequential 'Google Search--N' pattern stop
# at 6710. New tasks use a themed id format so diversity is visible.


def main():
    sections = [
        ('r4_image', r4_image_tasks()),
        ('r5_video', r5_video_tasks()),
        ('r6_scholar', r6_scholar_tasks()),
        ('r10_modules', r10_module_tasks()),
    ]

    existing_ids = set()
    if os.path.exists(TASKS_PATH):
        with open(TASKS_PATH) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    existing_ids.add(json.loads(line).get('id'))
                except Exception:
                    pass

    new_lines = []
    counts = {}
    pattern_counts = {}
    for section_name, rows in sections:
        c = 0
        per_theme = {}
        for theme, ques in rows:
            seq = per_theme.get(theme, 0) + 1
            per_theme[theme] = seq
            tid = 'Google Search--' + section_name + '_' + theme + '_' + str(seq).zfill(3)
            if tid in existing_ids:
                continue
            row = {
                'web_name': WEB_NAME,
                'web': WEB,
                'upstream_url': UPSTREAM,
                'id': tid,
                'ques': ques,
            }
            new_lines.append(json.dumps(row, ensure_ascii=False))
            c += 1
        counts[section_name] = c
        pattern_counts[section_name] = per_theme

    if not new_lines:
        print('[gen-r4-r10] nothing to append (all ids already present)')
        return

    with open(TASKS_PATH, 'a') as fh:
        for line in new_lines:
            fh.write(line + '\n')
    print('[gen-r4-r10] appended ' + str(len(new_lines)) + ' tasks')
    for k, v in counts.items():
        print('[gen-r4-r10]   ' + k + ': ' + str(v) + ' tasks')
        for theme, n in sorted(pattern_counts[k].items()):
            print('[gen-r4-r10]     - ' + theme + ': ' + str(n))


if __name__ == '__main__':
    main()
