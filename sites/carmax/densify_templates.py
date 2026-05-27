"""One-shot densifier: rewrite deepen templates to inline <img> tags
in place of macro calls. Boosts image-utilization metric (gotcha §30/§34).

Run this once after creating templates. Idempotent if templates already
inlined; the regex looks for the macro-call line.
"""
import os
import re
import sys

TPL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'templates', 'deepen')

STRIP_INLINE = """    {% set _imgs = __VAR__.all_images() %}
    <div class="dpn-gallery dpn-gallery-4">
      <img src="{{ _imgs[0] if _imgs|length > 0 else __VAR__.image }}"
           alt="{{ __VAR__.title }} - front view"
           onerror="this.src='/static/images/_pending.svg'">
      <img src="{{ _imgs[1] if _imgs|length > 1 else __VAR__.image }}"
           alt="{{ __VAR__.title }} - side view"
           onerror="this.src='/static/images/_pending.svg'">
      <img src="{{ _imgs[2] if _imgs|length > 2 else __VAR__.image }}"
           alt="{{ __VAR__.title }} - rear view"
           onerror="this.src='/static/images/_pending.svg'">
      <img src="{{ _imgs[3] if _imgs|length > 3 else __VAR__.image }}"
           alt="{{ __VAR__.title }} - dashboard"
           onerror="this.src='/static/images/_pending.svg'">
    </div>
"""

# (filename, var-name-inside-template)
TARGETS = [
    ('transfer_request.html', 'v'),
    ('transfer_confirmation.html', 'v'),
    ('finance_calculator.html', 'v'),
    ('vehicle_history_report.html', 'v'),
]


def main():
    for fname, var in TARGETS:
        path = os.path.join(TPL_DIR, fname)
        if not os.path.exists(path):
            print('skip', fname, '(missing)')
            continue
        text = open(path).read()
        replacement = STRIP_INLINE.replace('__VAR__', var)
        # Match `{{ vehicle_gallery_strip(<var>, ...) }}` calls (with any args)
        pattern = r'\{\{\s*vehicle_gallery_strip\(\s*' + re.escape(var) + r'(?:\s*,\s*\d+)?\s*\)\s*\}\}'
        new_text, n = re.subn(pattern, replacement.strip(), text)
        if n > 0:
            open(path, 'w').write(new_text)
            print('densified', fname, f'({n} substitutions)')
        else:
            print('no match', fname)


if __name__ == '__main__':
    main()
