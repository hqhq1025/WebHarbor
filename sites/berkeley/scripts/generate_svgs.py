#!/usr/bin/env python3
"""One-time SVG asset generator for Berkeley deepen.

Writes deterministic placeholder SVGs into static/images/ so templates have
real <img> targets. Use a simple geometric pattern per file so each file's
bytes are unique and stable.
"""
import os
import hashlib
import pathlib

BASE = pathlib.Path(__file__).parent.parent / 'static' / 'images'
BASE.mkdir(parents=True, exist_ok=True)

BLUE = '#003262'
GOLD = '#FDB515'
LIGHT_BLUE = '#3B7EA1'
DARK_GOLD = '#C4820A'
WHITE = '#ffffff'

PALETTES = {
    'campus': [BLUE, LIGHT_BLUE, GOLD, '#4A6FA5', '#5A7FB5', '#6A8FC5'],
    'headshot': ['#8B6F47', '#A47C5C', '#C49A75', '#5F8B7E', '#7A9D8F', '#9CB5A8'],
    'banner': [GOLD, DARK_GOLD, '#E89708', '#FFC533', '#FFE699', '#F5D77A'],
    'fund': ['#1A5490', '#2E6BA8', '#4282BE', BLUE, LIGHT_BLUE],
    'library': ['#2C3E50', '#34495E', '#4A6273', '#5D7387', '#7A8A9C'],
    'sport': ['#003262', '#0057A8', '#1976D2', '#42A5F5', '#90CAF9'],
}

KINDS = {
    'campus': 20,
    'headshot': 20,
    'banner': 12,
    'fund': 10,
    'library': 6,
    'sport': 8,
}

CAPTIONS = {
    'campus': ['Sather Tower', 'Memorial Glade', 'Sproul Plaza', 'Doe Library', 'Greek Theatre',
               'Campanile', 'South Hall', 'Hearst Mining', 'Wheeler Hall', 'Botanical Garden',
               'Strawberry Creek', 'Sather Gate', 'Wellman Quad', 'VLSB Glade', 'Eucalyptus Grove',
               'Faculty Glade', 'Crescent Lawn', 'Founders Rock', 'Senior Hall', 'Ratcliffe Plaza',
               'University Drive', 'Big C Trail', 'Tilden View', 'East Asian Library', 'BAMPFA',
               'Hearst Greek', 'Mining Circle', 'North Gate', 'West Crescent', 'Goldman School'],
    'headshot': ['Professor', 'Researcher', 'Dean', 'Director', 'Associate Professor',
                 'Assistant Professor', 'Lecturer', 'Postdoc', 'Vice Chancellor', 'Chancellor',
                 'Faculty', 'Scholar', 'Investigator', 'Department Chair', 'Senior Scientist',
                 'Distinguished Professor', 'Chair', 'Senior Lecturer', 'Provost', 'Counselor',
                 'Coach', 'Librarian', 'Curator', 'Advisor', 'Coordinator',
                 'Manager', 'Editor', 'Officer', 'Director', 'Scholar'],
    'banner': ['Lecture Series', 'Concert', 'Career Fair', 'Big Game', 'Symposium',
               'Open House', 'Summer Session', 'Welcome Week', 'Commencement', 'Alumni Reunion',
               'Research Showcase', 'Cal Day', 'Homecoming', 'Move-in Day', 'Finals Week',
               'Spring Festival', 'Holiday Concert', 'Town Hall', 'Tour Booking', 'Reception'],
    'fund': ['Endowment', 'Scholarship', 'Research Fund', 'Annual Gift', 'Capital Campaign',
             'Library Fund', 'Athletics', 'Arts Fund', 'Climate Initiative', 'AI Lab',
             'Cancer Research', 'Student Aid', 'Memorial', 'Diversity Fund', 'Public Service'],
    'library': ['Doe Library', 'Moffitt Library', 'Bancroft Library', 'Engineering Library',
                'Music Library', 'Science Library', 'Law Library', 'Business Library',
                'Asian Library', 'Storage Facility'],
    'sport': ['Football', 'Basketball', 'Baseball', 'Soccer', 'Swimming',
              'Volleyball', 'Tennis', 'Track', 'Rowing', 'Rugby'],
}


def make_svg(kind, idx, palette, caption):
    """Generate a deterministic but visually distinct SVG."""
    # Color choice from index
    c1 = palette[idx % len(palette)]
    c2 = palette[(idx * 3 + 1) % len(palette)]
    c3 = palette[(idx * 7 + 2) % len(palette)]

    # Deterministic small details
    h = hashlib.md5(f"{kind}_{idx}".encode()).hexdigest()
    angle = int(h[0:2], 16) % 90 - 45
    cx = 100 + (int(h[2:4], 16) % 200)
    cy = 100 + (int(h[4:6], 16) % 100)
    r = 30 + int(h[6:8], 16) % 60

    if kind == 'headshot':
        # Portrait silhouette
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">
  <rect width="400" height="400" fill="{c1}"/>
  <circle cx="200" cy="160" r="70" fill="{c2}"/>
  <path d="M80 400 Q80 280 200 280 Q320 280 320 400 Z" fill="{c2}"/>
  <text x="200" y="370" font-family="Georgia" font-size="18" fill="{WHITE}" text-anchor="middle" opacity="0.85">{caption}</text>
</svg>'''
    elif kind == 'banner':
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 320" width="1200" height="320">
  <defs>
    <linearGradient id="bg{idx}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="{c2}"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="320" fill="url(#bg{idx})"/>
  <circle cx="{cx + 600}" cy="{cy}" r="{r}" fill="{c3}" opacity="0.5"/>
  <rect x="50" y="240" width="400" height="6" fill="{WHITE}" opacity="0.7"/>
  <text x="60" y="220" font-family="Georgia" font-size="44" fill="{WHITE}">{caption}</text>
  <text x="60" y="280" font-family="Arial" font-size="16" fill="{WHITE}" opacity="0.85">UC Berkeley · 2026-27 Series</text>
</svg>'''
    elif kind == 'campus':
        # Architectural silhouette
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" width="800" height="500">
  <rect width="800" height="500" fill="{c1}"/>
  <rect y="380" width="800" height="120" fill="{c2}"/>
  <rect x="300" y="120" width="80" height="260" fill="{c3}"/>
  <polygon points="290,120 340,60 390,120" fill="{c3}"/>
  <rect x="450" y="220" width="180" height="160" fill="{c3}" opacity="0.8"/>
  <rect x="160" y="280" width="120" height="100" fill="{c3}" opacity="0.7"/>
  <circle cx="{cx}" cy="80" r="30" fill="{GOLD}" opacity="0.7"/>
  <text x="400" y="470" font-family="Georgia" font-size="22" fill="{WHITE}" text-anchor="middle">{caption}</text>
</svg>'''
    elif kind == 'library':
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" width="800" height="500">
  <rect width="800" height="500" fill="{c1}"/>
  <rect x="100" y="150" width="600" height="280" fill="{c2}"/>
  <rect x="120" y="180" width="60" height="220" fill="{c3}"/>
  <rect x="190" y="180" width="60" height="220" fill="{c3}" opacity="0.8"/>
  <rect x="260" y="180" width="60" height="220" fill="{c3}" opacity="0.6"/>
  <rect x="330" y="180" width="60" height="220" fill="{c3}"/>
  <rect x="400" y="180" width="60" height="220" fill="{c3}" opacity="0.8"/>
  <rect x="470" y="180" width="60" height="220" fill="{c3}" opacity="0.6"/>
  <rect x="540" y="180" width="60" height="220" fill="{c3}"/>
  <text x="400" y="470" font-family="Georgia" font-size="22" fill="{WHITE}" text-anchor="middle">{caption}</text>
</svg>'''
    elif kind == 'fund':
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400" width="600" height="400">
  <rect width="600" height="400" fill="{c1}"/>
  <circle cx="300" cy="180" r="100" fill="{c2}"/>
  <circle cx="300" cy="180" r="60" fill="{GOLD}"/>
  <text x="300" y="195" font-family="Georgia" font-size="34" fill="{c1}" text-anchor="middle" font-weight="bold">$</text>
  <text x="300" y="350" font-family="Georgia" font-size="20" fill="{WHITE}" text-anchor="middle">{caption}</text>
</svg>'''
    elif kind == 'sport':
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 400" width="800" height="400">
  <rect width="800" height="400" fill="{c1}"/>
  <rect y="280" width="800" height="120" fill="{c2}"/>
  <circle cx="400" cy="180" r="80" fill="{GOLD}"/>
  <text x="400" y="195" font-family="Georgia" font-size="28" fill="{c1}" text-anchor="middle" font-weight="bold">CAL</text>
  <text x="400" y="370" font-family="Georgia" font-size="22" fill="{WHITE}" text-anchor="middle">{caption}</text>
</svg>'''


def main():
    total = 0
    for kind, count in KINDS.items():
        palette = PALETTES[kind]
        captions = CAPTIONS[kind]
        for i in range(1, count + 1):
            cap = captions[(i - 1) % len(captions)]
            svg = make_svg(kind, i - 1, palette, cap)
            path = BASE / f"{kind}_{i:03d}.svg"
            path.write_text(svg)
            total += 1
    print(f'Wrote {total} SVGs to {BASE}')


if __name__ == '__main__':
    main()
