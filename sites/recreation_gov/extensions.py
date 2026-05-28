"""Recreation.gov vanilla-level deepen extensions.

Append-only blueprint per harden-env/gotchas.md §31:
- Models: Lottery / LotteryEntry / Permit / PermitApplication / Tour / TourBooking /
  Destination / SavedDestination / Alert / AlertSubscription / TripPlan /
  TripPlanItem / GearList / GearItem / GroupReservation / ConditionReport /
  CheckIn / TimedEntryReservation / FacilityPhoto.
- GET routes: detail / hub / list pages for the above (≥17 new templates).
- POST routes: ≥14 new mutating endpoints.
- Seed: gated on `Lottery.query.count() > 0` so re-builds are no-ops.
- Late-import per gotcha §32: nothing from app.py is touched at module load.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta
from decimal import Decimal

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required


# ---------------------------------------------------------------------------
# Late-bound symbols (filled by register(app))
# ---------------------------------------------------------------------------
_BOUND: dict[str, object] = {}


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _pin_hash(email: str, password: str) -> str:
    """Deterministic werkzeug-compatible pbkdf2 hash (gotcha §1 Fix B)."""
    salt = hashlib.sha1(f"recgov-salt-{email}".encode()).hexdigest()[:8]
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 1000, dklen=32).hex()
    return f"pbkdf2:sha256:1000${salt}${derived}"


# ---------------------------------------------------------------------------
# Reference data (drives lotteries / permits / tours / destinations etc.)
# ---------------------------------------------------------------------------

# Per-slug real Wikipedia photos (harvested 2026-05-27, see scrape-real-images
# skill). Overlays the placeholder file used in the spec tuples so each
# permit / tour / destination renders a distinct landmark photo instead of
# the same mt-whitney / aquatic-park-cove / desolation-lake reused across rows.
PERMIT_REAL_PHOTOS = {
    "desolation-wilderness-overnight-permit": "wiki-desolation-wilderness.webp",
    "inyo-mt-whitney-trail-permit": "wiki-mt-whitney-trail.webp",
    "yosemite-wilderness-permit": "wiki-yosemite-wilderness.webp",
    "yellowstone-fishing-permit": "wiki-yellowstone-fishing.webp",
    "canyonlands-overnight-permit": "wiki-canyonlands-overnight.webp",
    "aravaipa-canyon-permit": "wiki-aravaipa-canyon.webp",
    "chilkoot-trail-permit": "wiki-chilkoot-trail.webp",
    "apostle-islands-camping-permit": "wiki-apostle-islands.webp",
    "mt-st-helens-climbing-permit": "wiki-mt-st-helens.webp",
    "cumberland-island-camping-permit": "wiki-cumberland-island.webp",
    "mt-whitney-day-permit": "wiki-mt-whitney.webp",
    "paria-canyon-overnight-permit": "wiki-paria-canyon.webp",
    "rock-castle-gorge-permit": "wiki-rock-castle-gorge.webp",
    "fire-island-driving-permit": "wiki-fire-island.webp",
    "subway-zion-canyoneering-permit": "wiki-zion-subway.webp",
    "hunting-okefenokee-permit": "wiki-okefenokee-hunting.webp",
}
TOUR_REAL_PHOTOS = {
    "yosemite-grand-tour-bus": "wiki-yosemite-valley-tour.webp",
    "alcatraz-day-tour": "wiki-alcatraz-day.webp",
    "carlsbad-kings-palace-tour": "wiki-carlsbad-caverns.webp",
    "mesa-verde-balcony-house": "wiki-mesa-verde.webp",
    "wind-cave-fairgrounds-tour": "wiki-wind-cave.webp",
    "sf-maritime-hyde-street-tour": "wiki-sf-maritime.webp",
    "fort-point-history-tour": "wiki-fort-point.webp",
    "voyageurs-day-cruise": "wiki-voyageurs.webp",
    "statue-of-liberty-crown-tour": "wiki-statue-liberty.webp",
    "independence-hall-tour": "wiki-independence-hall.webp",
    "dry-tortugas-ferry-day-trip": "wiki-dry-tortugas.webp",
    "glacier-bay-cruise": "wiki-glacier-bay.webp",
    "jenny-lake-shuttle-boat": "wiki-jenny-lake.webp",
    "channel-islands-island-packers": "wiki-channel-islands.webp",
    "biscayne-heritage-tour": "wiki-biscayne.webp",
    "lewis-clark-caverns-tour": "wiki-lewis-clark-caverns.webp",
    "campbell-creek-science-tour": "wiki-campbell-creek.webp",
    "zion-canyon-shuttle-narrated": "wiki-zion-canyon.webp",
}
DESTINATION_REAL_PHOTOS = {
    "yosemite-national-park": "wiki-yosemite.webp",
    "yellowstone-national-park": "wiki-yellowstone.webp",
    "grand-teton-national-park": "wiki-grand-teton.webp",
    "rocky-mountain-national-park": "wiki-rocky-mountain.webp",
    "zion-national-park": "wiki-zion.webp",
    "grand-canyon-national-park": "wiki-grand-canyon.webp",
    "glacier-national-park": "wiki-glacier.webp",
    "olympic-national-park": "wiki-olympic.webp",
    "acadia-national-park": "wiki-acadia.webp",
    "great-smoky-mountains-national-park": "wiki-great-smoky.webp",
    "joshua-tree-national-park": "wiki-joshua-tree.webp",
    "death-valley-national-park": "wiki-death-valley.webp",
    "arches-national-park": "wiki-arches.webp",
    "bryce-canyon-national-park": "wiki-bryce-canyon.webp",
    "denali-national-park": "wiki-denali.webp",
    "haleakala-national-park": "wiki-haleakala.webp",
    "everglades-national-park": "wiki-everglades.webp",
    "crater-lake-national-park": "wiki-crater-lake.webp",
    "mount-rainier-national-park": "wiki-mt-rainier.webp",
    "vermilion-cliffs-national-monument": "wiki-vermilion-cliffs.webp",
    "muir-woods-national-monument": "wiki-muir-woods.webp",
    "vermilion-bears-ears": "wiki-bears-ears.webp",
    "inyo-national-forest": "wiki-inyo-forest.webp",
    "tongass-national-forest": "wiki-tongass.webp",
    "okefenokee-refuge": "wiki-okefenokee.webp",
}

LOTTERY_SPECS = [
    ("the-wave-coyote-buttes-north-lottery", "The Wave (Coyote Buttes North) Lottery", "BLM", "Vermilion Cliffs National Monument", "AZ", "Kanab", 9, "2026-06-15", "2026-09-15", 0.04, "real-desolation-hero.webp"),
    ("half-dome-cable-route-lottery", "Half Dome Cable Route Preseason Lottery", "NPS", "Yosemite National Park", "CA", "Yosemite Valley", 12, "2026-03-01", "2026-04-30", 0.18, "real-yosemite-site-pass-hero.jpeg"),
    ("enchantments-overnight-lottery", "Enchantments Overnight Permit Lottery", "USFS", "Okanogan-Wenatchee National Forest", "WA", "Leavenworth", 6, "2026-02-15", "2026-03-02", 0.07, "061-preview-photo-of-enchantment-permit-area-advanced-lottery.webp"),
    ("mount-whitney-day-hike-lottery", "Mount Whitney Day Hike Lottery", "USFS", "Inyo National Forest", "CA", "Lone Pine", 15, "2026-02-01", "2026-03-15", 0.21, "060-preview-photo-of-mt-whitney.webp"),
    ("denali-road-lottery", "Denali Park Road Lottery", "NPS", "Denali National Park and Preserve", "AK", "Healy", 25, "2026-05-01", "2026-05-31", 0.11, "real-nav-passes.webp"),
    ("alcatraz-night-tour-lottery", "Alcatraz Night Tour Holiday Lottery", "NPS", "Golden Gate National Recreation Area", "CA", "San Francisco", 45, "2026-10-01", "2026-12-01", 0.32, "real-golden-gate-tours.webp"),
    ("rocky-bear-lake-lottery", "Rocky Mountain Bear Lake Corridor Lottery", "NPS", "Rocky Mountain National Park", "CO", "Estes Park", 2, "2026-04-01", "2026-05-01", 0.45, "real-nav-camping.webp"),
    ("haleakala-sunrise-lottery", "Haleakala Sunrise Vehicle Lottery", "NPS", "Haleakala National Park", "HI", "Kula", 1, "2026-04-15", "2026-05-15", 0.55, "real-nav-passes.webp"),
    ("the-subway-canyoneering-lottery", "The Subway Canyoneering Day Lottery", "NPS", "Zion National Park", "UT", "Springdale", 12, "2026-01-01", "2026-12-31", 0.16, "real-desolation-granite.webp"),
    ("hammerhead-paddle-lottery", "Hammerhead Lake Paddle-In Lottery", "USACE", "Lake Sonoma", "CA", "Geyserville", 8, "2026-06-01", "2026-08-15", 0.38, "real-lake-sonoma-boat-in.webp"),
    ("dry-tortugas-camping-lottery", "Dry Tortugas Backcountry Camping Lottery", "NPS", "Dry Tortugas National Park", "FL", "Key West", 18, "2026-02-15", "2026-04-30", 0.25, "real-aquatic-park-cove.webp"),
    ("paria-canyon-lottery", "Paria Canyon Wilderness Lottery", "BLM", "Vermilion Cliffs National Monument", "UT", "Kanab", 15, "2026-03-15", "2026-05-15", 0.19, "real-desolation-lake.webp"),
]

PERMIT_SPECS = [
    ("desolation-wilderness-overnight-permit", "Desolation Wilderness Overnight Permit", "boating", "USFS", "Eldorado National Forest", "CA", "South Lake Tahoe", 10, "real-desolation-hero.webp", "Quota permit required for overnight backcountry use in Desolation Wilderness."),
    ("inyo-mt-whitney-trail-permit", "Inyo Mt. Whitney Trail Permit", "climbing", "USFS", "Inyo National Forest", "CA", "Lone Pine", 15, "060-preview-photo-of-mt-whitney.webp", "Daily quota permit for the Mt. Whitney Trail covering both day-use and overnight visitors."),
    ("yosemite-wilderness-permit", "Yosemite Wilderness Permit", "backcountry", "NPS", "Yosemite National Park", "CA", "Yosemite Valley", 10, "real-yosemite-site-pass-hero.jpeg", "Trailhead-based wilderness permit covering Half Dome, Clouds Rest, and JMT entries."),
    ("yellowstone-fishing-permit", "Yellowstone National Park Fishing Permit", "fishing", "NPS", "Yellowstone National Park", "WY", "Mammoth Hot Springs", 40, "063-preview-photo-of-yellowstone-national-park-backcountry-permits.webp", "Daily, 3-day, 7-day, and season fishing permits."),
    ("canyonlands-overnight-permit", "Canyonlands Overnight Backcountry Permit", "backcountry", "NPS", "Canyonlands National Park", "UT", "Moab", 36, "064-preview-photo-of-canyonlands-national-park-overnight-backcountry-permi.webp", "Vehicle and overnight backcountry permits within the Maze, Needles, and Island in the Sky."),
    ("aravaipa-canyon-permit", "Aravaipa Canyon Wilderness Permit", "hiking", "BLM", "Aravaipa Canyon Wilderness", "AZ", "Winkelman", 5, "069-preview-photo-of-aravaipa-canyon-wilderness-permits.webp", "Daily-quota wilderness hiking permit; canyoneering and overnight use included."),
    ("chilkoot-trail-permit", "Chilkoot Trail Camping Permit", "backcountry", "NPS", "Klondike Gold Rush National Historical Park", "AK", "Skagway", 12, "043-preview-photo-of-chilkoot-trail-camping-permits.webp", "Cross-border backcountry trail permit for the historic Chilkoot route."),
    ("apostle-islands-camping-permit", "Apostle Islands Camping Permit", "backcountry", "NPS", "Apostle Islands National Lakeshore", "WI", "Bayfield", 15, "039-preview-photo-of-apostle-islands-national-lakeshore-camping-permits.webp", "Island-based wilderness camping permits requiring boat or kayak access."),
    ("mt-st-helens-climbing-permit", "Mt. St. Helens Climbing Permit", "climbing", "USFS", "Gifford Pinchot National Forest", "WA", "Cougar", 22, "068-preview-photo-of-mount-margaret-backcountry.webp", "Climbing permit above 4,800 feet on Mount St. Helens."),
    ("cumberland-island-camping-permit", "Cumberland Island Camping Permit", "backcountry", "NPS", "Cumberland Island National Seashore", "GA", "St Marys", 12, "027-preview-photo-of-cumberland-island-national-seashore-camping-permits.webp", "Ferry-access wilderness and developed camping permits."),
    ("mt-whitney-day-permit", "Mt. Whitney Day Use Permit", "hiking", "USFS", "Inyo National Forest", "CA", "Lone Pine", 6, "060-preview-photo-of-mt-whitney.webp", "Day-use only permit for the Mt. Whitney Trail, separate from overnight allocation."),
    ("paria-canyon-overnight-permit", "Paria Canyon Overnight Permit", "backcountry", "BLM", "Vermilion Cliffs National Monument", "UT", "Kanab", 6, "real-desolation-lake.webp", "Overnight backcountry permit through the Paria slot canyon corridor."),
    ("rock-castle-gorge-permit", "Rock Castle Gorge Backcountry Permit", "backcountry", "NPS", "Blue Ridge Parkway", "VA", "Mabry Mill", 8, "032-preview-photo-of-rock-castle-gorge-backcountry-camping.webp", "Backcountry route permit along the Blue Ridge Parkway corridor."),
    ("fire-island-driving-permit", "Fire Island Off-Road Vehicle Permit", "boating", "NPS", "Fire Island National Seashore", "NY", "Patchogue", 25, "065-preview-photo-of-fire-island-national-seashore-permits.webp", "Seasonal off-road vehicle permit for designated Fire Island routes."),
    ("subway-zion-canyoneering-permit", "Zion Subway Canyoneering Permit", "climbing", "NPS", "Zion National Park", "UT", "Springdale", 15, "real-desolation-granite.webp", "Day-use canyoneering permit for the Left Fork (Subway) route in Zion."),
    ("hunting-okefenokee-permit", "Okefenokee Hunting Permit", "hunting", "FWS", "Okefenokee National Wildlife Refuge", "GA", "Folkston", 14, "041-preview-photo-of-okefenokee-national-wildlife-refuge-overnight-camping.webp", "Seasonal hunting permit for designated Okefenokee zones."),
]

TOUR_SPECS = [
    ("yosemite-grand-tour-bus", "Yosemite Grand Tour Bus", "NPS", "Yosemite National Park", "CA", "Yosemite Valley", 89, "real-yosemite-site-pass-hero.jpeg", "Full-day narrated motor coach tour through Yosemite Valley with stops at Bridalveil Fall and Tunnel View."),
    ("alcatraz-day-tour", "Alcatraz Island Day Tour", "NPS", "Golden Gate National Recreation Area", "CA", "San Francisco", 47, "real-golden-gate-tours.webp", "Self-guided cellhouse audio tour with optional ranger-led programs on Alcatraz Island."),
    ("carlsbad-kings-palace-tour", "Carlsbad Caverns King's Palace Tour", "NPS", "Carlsbad Caverns National Park", "NM", "Carlsbad", 12, "real-desolation-granite.webp", "Ranger-led lantern tour of Carlsbad's King's Palace room."),
    ("mesa-verde-balcony-house", "Mesa Verde Balcony House Cliff Dwelling Tour", "NPS", "Mesa Verde National Park", "CO", "Mesa Verde", 8, "real-desolation-hero.webp", "Strenuous ladder-and-tunnel cliff dwelling tour at Mesa Verde."),
    ("wind-cave-fairgrounds-tour", "Wind Cave Fairgrounds Tour", "NPS", "Wind Cave National Park", "SD", "Hot Springs", 14, "real-desolation-lake.webp", "Guided 90-minute lantern-style cave tour through Wind Cave's Fairgrounds room."),
    ("sf-maritime-hyde-street-tour", "SF Maritime Hyde Street Pier Tour", "NPS", "San Francisco Maritime National Historical Park", "CA", "San Francisco", 15, "real-sf-maritime-tours.webp", "Ranger-led historic ship tour of the Balclutha and the Eureka ferry."),
    ("fort-point-history-tour", "Fort Point History & Architecture Tour", "NPS", "Golden Gate National Recreation Area", "CA", "San Francisco", 12, "real-fort-point-tours.webp", "Ranger-led architecture and Civil War history tour at Fort Point."),
    ("voyageurs-day-cruise", "Voyageurs Day Cruise Tour", "NPS", "Voyageurs National Park", "MN", "International Falls", 42, "028-preview-photo-of-voyageurs-national-park-camping-permits.webp", "Naturalist-narrated boat cruise of Voyageurs' interior lakes."),
    ("statue-of-liberty-crown-tour", "Statue of Liberty Crown Tour", "NPS", "Statue of Liberty National Monument", "NY", "New York", 25, "real-america-250-background.webp", "Limited-availability tour to the crown of the Statue of Liberty."),
    ("independence-hall-tour", "Independence Hall Tour", "NPS", "Independence National Historical Park", "PA", "Philadelphia", 0, "real-a250-fireworks.webp", "Free, timed-entry ranger tour of the Assembly Room and Independence Hall."),
    ("dry-tortugas-ferry-day-trip", "Dry Tortugas Ferry Day Trip", "NPS", "Dry Tortugas National Park", "FL", "Key West", 220, "real-aquatic-park-cove.webp", "Round-trip ferry plus park admission for the Dry Tortugas day trip."),
    ("glacier-bay-cruise", "Glacier Bay Day Cruise", "NPS", "Glacier Bay National Park", "AK", "Gustavus", 250, "real-nav-tickets.webp", "Naturalist-narrated full-day cruise into Glacier Bay's tidewater glaciers."),
    ("jenny-lake-shuttle-boat", "Jenny Lake Shuttle Boat", "NPS", "Grand Teton National Park", "WY", "Moose", 22, "real-pinnacles-national-park.webp", "Cross-lake shuttle linking the Jenny Lake trailhead with Cascade Canyon."),
    ("channel-islands-island-packers", "Channel Islands Boat Transportation", "NPS", "Channel Islands National Park", "CA", "Ventura", 95, "real-aquatic-park-cove.webp", "Concessioner boat transportation between Ventura and Channel Islands."),
    ("biscayne-heritage-tour", "Biscayne Heritage Tour", "NPS", "Biscayne National Park", "FL", "Homestead", 79, "real-nav-fishing.webp", "Half-day boat tour visiting Stiltsville and Boca Chita lighthouse."),
    ("lewis-clark-caverns-tour", "Lewis and Clark Caverns Guided Tour", "USFS", "Beaverhead-Deerlodge National Forest", "MT", "Three Forks", 19, "real-nav-permits.webp", "Two-hour ranger-led cave tour at Lewis and Clark Caverns."),
    ("campbell-creek-science-tour", "Campbell Creek Science Center Tour", "BLM", "Campbell Tract", "AK", "Anchorage", 8, "real-nav-fishing.webp", "Education-focused naturalist tour at the Campbell Creek Science Center."),
    ("zion-canyon-shuttle-narrated", "Zion Canyon Narrated Shuttle Tour", "NPS", "Zion National Park", "UT", "Springdale", 0, "real-nav-passes.webp", "Free Zion Canyon shuttle with optional narrated ranger pop-up programs."),
]

DESTINATION_SPECS = [
    ("yosemite-national-park", "Yosemite National Park", "national-park", "NPS", "CA", "Granite cliffs, giant sequoias, and roaring waterfalls in the central Sierra Nevada.", "real-yosemite-site-pass-hero.jpeg"),
    ("yellowstone-national-park", "Yellowstone National Park", "national-park", "NPS", "WY", "Geyser basins, wildlife valleys, and the Grand Canyon of the Yellowstone.", "063-preview-photo-of-yellowstone-national-park-backcountry-permits.webp"),
    ("grand-teton-national-park", "Grand Teton National Park", "national-park", "NPS", "WY", "Jagged Teton skyline above glacial lakes and the Snake River.", "real-pinnacles-national-park.webp"),
    ("rocky-mountain-national-park", "Rocky Mountain National Park", "national-park", "NPS", "CO", "Alpine tundra, elk meadows, and Trail Ridge Road above 12,000 feet.", "real-nav-camping.webp"),
    ("zion-national-park", "Zion National Park", "national-park", "NPS", "UT", "Slot canyons, river hikes, and 2,000-foot sandstone walls.", "real-desolation-granite.webp"),
    ("grand-canyon-national-park", "Grand Canyon National Park", "national-park", "NPS", "AZ", "Mile-deep canyon, Colorado River rapids, and rim-to-rim trails.", "real-desolation-hero.webp"),
    ("glacier-national-park", "Glacier National Park", "national-park", "NPS", "MT", "Going-to-the-Sun Road, alpine lakes, and remnant glaciers.", "real-desolation-lake.webp"),
    ("olympic-national-park", "Olympic National Park", "national-park", "NPS", "WA", "Rainforests, ocean coast, and a glaciated peak in one park.", "real-point-reyes-seashore.webp"),
    ("acadia-national-park", "Acadia National Park", "national-park", "NPS", "ME", "Atlantic-coast granite headlands, Cadillac Mountain, and carriage roads.", "real-aquatic-park-cove.webp"),
    ("great-smoky-mountains-national-park", "Great Smoky Mountains National Park", "national-park", "NPS", "TN", "Forested Appalachian ridges, wildflower coves, and historic settlements.", "017-home.webp"),
    ("joshua-tree-national-park", "Joshua Tree National Park", "national-park", "NPS", "CA", "High and low desert with monzogranite boulders and Joshua trees.", "002-home.webp"),
    ("death-valley-national-park", "Death Valley National Park", "national-park", "NPS", "CA", "Largest park in the lower 48, with dunes, salt flats, and dark skies.", "052-preview-photo-of-death-valley-backcountry-roadside-camping.webp"),
    ("arches-national-park", "Arches National Park", "national-park", "NPS", "UT", "Over 2,000 natural sandstone arches in the high desert.", "real-desolation-granite.webp"),
    ("bryce-canyon-national-park", "Bryce Canyon National Park", "national-park", "NPS", "UT", "Hoodoo amphitheaters and high-elevation pine forest.", "real-desolation-lake.webp"),
    ("denali-national-park", "Denali National Park and Preserve", "national-park", "NPS", "AK", "Six million acres of subarctic wilderness around North America's tallest peak.", "real-nav-passes.webp"),
    ("haleakala-national-park", "Haleakala National Park", "national-park", "NPS", "HI", "Volcanic summit and Kipahulu coast on Maui.", "real-aquatic-park-cove.webp"),
    ("everglades-national-park", "Everglades National Park", "national-park", "NPS", "FL", "Subtropical wetlands, mangrove estuaries, and the Anhinga Trail.", "real-aquatic-park-cove.webp"),
    ("crater-lake-national-park", "Crater Lake National Park", "national-park", "OR", "OR", "Deepest lake in the United States inside a collapsed volcano.", "real-pinnacles-national-park.webp"),
    ("mount-rainier-national-park", "Mount Rainier National Park", "national-park", "NPS", "WA", "Glaciated stratovolcano above old-growth forest and meadows.", "real-pinnacles-campground.webp"),
    ("vermilion-cliffs-national-monument", "Vermilion Cliffs National Monument", "national-monument", "BLM", "AZ", "Slickrock plateaus including The Wave and Paria Canyon.", "real-desolation-hero.webp"),
    ("muir-woods-national-monument", "Muir Woods National Monument", "national-monument", "NPS", "CA", "Old-growth coast redwoods just north of San Francisco.", "real-point-reyes-seashore.webp"),
    ("vermilion-bears-ears", "Bears Ears National Monument", "national-monument", "BLM", "UT", "1.36-million-acre cultural landscape with ancestral cliff sites.", "real-desolation-lake.webp"),
    ("inyo-national-forest", "Inyo National Forest", "national-forest", "USFS", "CA", "Eastern Sierra ridges, alpine lakes, and Ancient Bristlecone Pine Forest.", "067-preview-photo-of-inyo-national-forest-wilderness-permits.webp"),
    ("tongass-national-forest", "Tongass National Forest", "national-forest", "USFS", "AK", "Largest US national forest covering 16.7 million acres of southeast Alaska.", "056-preview-photo-of-samsing-cove-cabin.webp"),
    ("okefenokee-refuge", "Okefenokee National Wildlife Refuge", "wildlife-refuge", "FWS", "GA", "Blackwater swamp ecosystem with paddle trails and overnight platforms.", "041-preview-photo-of-okefenokee-national-wildlife-refuge-overnight-camping.webp"),
]

ALERT_SPECS = [
    ("yosemite-firefall-window", "Yosemite Firefall Reservation Window", "yosemite-national-park", "NPS", "Reservation required for Yosemite Valley entry during the February Firefall window."),
    ("rocky-bear-lake-corridor", "Rocky Mountain Bear Lake Corridor Pilot", "rocky-mountain-national-park", "NPS", "Bear Lake Corridor timed-entry pilot remains in effect through October."),
    ("glacier-going-to-sun-closure", "Going-to-the-Sun Road Winter Closure", "glacier-national-park", "NPS", "Going-to-the-Sun Road is closed past Lake McDonald until plowing completes."),
    ("zion-angels-landing-quota", "Angels Landing Permit Quota", "zion-national-park", "NPS", "Daily Angels Landing permit lottery has shifted to a seasonal lottery format."),
    ("arches-timed-entry", "Arches Timed Entry Pilot", "arches-national-park", "NPS", "Arches National Park timed-entry pilot continues into 2026."),
    ("yellowstone-bear-jam", "Yellowstone Wildlife Jam Advisory", "yellowstone-national-park", "NPS", "Spring bear activity is causing wildlife jams along the Lamar and Hayden Valleys."),
    ("denali-road-lottery-window", "Denali Road Lottery Window Open", "denali-national-park", "NPS", "Denali Park Road lottery applications are open through the end of May."),
    ("smokies-parking-tag", "Smokies Parking Tag In Effect", "great-smoky-mountains-national-park", "NPS", "All vehicles parked more than 15 minutes require a Park It Forward tag."),
    ("dry-tortugas-ferry-cap", "Dry Tortugas Ferry Capacity Cap", "everglades-national-park", "NPS", "Dry Tortugas day-trip ferry has lowered daily capacity for the spring."),
    ("everglades-shark-valley-trams", "Shark Valley Tram Reservations", "everglades-national-park", "NPS", "Shark Valley tram tours require advance reservations through Memorial Day."),
    ("muir-woods-shuttle", "Muir Woods Shuttle Pilot Continues", "muir-woods-national-monument", "NPS", "Muir Woods reservations and shuttle pilot remain in effect for the 2026 season."),
    ("wave-lottery-window-changes", "Wave Lottery Window Updates", "vermilion-cliffs-national-monument", "BLM", "Daily Wave lottery has shifted to seasonal advance lottery for non-walk-up permits."),
]

TIMED_ENTRY_PARKS = [
    ("rocky-mountain", "Rocky Mountain National Park", "rocky-mountain-national-park", "NPS", "Estes Park, CO", 2, "real-nav-camping.webp"),
    ("arches", "Arches National Park", "arches-national-park", "NPS", "Moab, UT", 2, "real-desolation-granite.webp"),
    ("glacier-gtsr", "Glacier Going-to-the-Sun Road", "glacier-national-park", "NPS", "West Glacier, MT", 2, "real-desolation-lake.webp"),
    ("haleakala-sunrise", "Haleakala Sunrise", "haleakala-national-park", "NPS", "Kula, HI", 1, "real-aquatic-park-cove.webp"),
    ("acadia-cadillac", "Acadia Cadillac Summit Road", "acadia-national-park", "NPS", "Bar Harbor, ME", 6, "real-point-reyes-seashore.webp"),
    ("yosemite-firefall", "Yosemite Firefall Reservation", "yosemite-national-park", "NPS", "Yosemite Valley, CA", 2, "real-yosemite-site-pass-hero.jpeg"),
    ("muir-woods-parking", "Muir Woods Parking & Shuttle", "muir-woods-national-monument", "NPS", "Mill Valley, CA", 9, "real-point-reyes-seashore.webp"),
    ("zion-angels-landing", "Zion Angels Landing", "zion-national-park", "NPS", "Springdale, UT", 6, "real-desolation-granite.webp"),
]

GEAR_LIST_SPECS = [
    ("backpacking", "Backpacking Gear List", "Multi-day overnight backpacking essentials.", "060-preview-photo-of-mt-whitney.webp",
     ["Internal-frame backpack 50-65L", "Sleeping bag rated to 20F", "Inflatable sleeping pad", "Two-person backpacking tent", "Bear-resistant food canister", "Headlamp + extra batteries", "Water filter or purifier", "Trekking poles", "Layered clothing (base / insulating / shell)", "Map, compass, and route notes"]),
    ("car-camping", "Car Camping Gear List", "Reservable campsite weekend basics.", "real-point-reyes-campground.webp",
     ["Family-sized tent", "Sleeping bags rated to 30F", "Self-inflating sleeping pads", "Camp stove + fuel canister", "Cooler with ice packs", "Folding camp chairs", "LED lantern", "Camp kitchen tote", "Firewood (locally sourced)", "Trash and recycling bags"]),
    ("paddling", "Paddling Gear List", "Kayak / canoe / packraft essentials.", "real-lake-sonoma-boat-in.webp",
     ["PFD (Coast Guard approved)", "Spare paddle", "Dry bags", "Bilge pump or sponge", "Whistle and signaling mirror", "Marine-grade chart", "Spray skirt (kayak)", "Wetsuit or paddle pants", "Sun shirt with UPF rating", "Wide-brim hat"]),
    ("winter-camping", "Winter Camping Gear List", "Cold-weather overnight kit.", "057-preview-photo-of-rampart-range-recreation-area-designated-dispersed-ca.webp",
     ["Four-season tent", "Down sleeping bag rated to 0F", "Closed-cell foam pad + insulated pad", "Liquid-fuel stove (rated for cold)", "Vacuum-insulated bottle", "Insulated parka", "Mittens + glove liners", "Snowshoes or skis", "Avalanche beacon and probe", "Ice axe (when relevant)"]),
    ("day-hiking", "Day Hiking Gear List", "Single-day hiking essentials.", "real-pinnacles-national-park.webp",
     ["20-30L daypack", "Reusable water bottles or hydration bladder", "Snack and lunch supplies", "Layered clothing", "Sun hat and sunscreen", "Trail map or downloaded route", "Whistle", "First-aid kit", "Headlamp", "Trekking poles"]),
    ("climbing", "Climbing Gear List", "Sport / trad / multi-pitch essentials.", "069-preview-photo-of-aravaipa-canyon-wilderness-permits.webp",
     ["Climbing harness", "Climbing shoes", "Belay device", "Helmet", "Locking carabiners", "Quickdraws", "Dynamic climbing rope", "Personal anchor system", "Chalk bag", "Approach pack"]),
    ("fishing", "Fishing Gear List", "Cold-water and warm-water fishing essentials.", "066-preview-photo-of-hemlock-cabin.webp",
     ["Fly or spinning rod", "Reel matched to rod weight", "Polarized sunglasses", "Tackle box", "Net (wood or rubber)", "Waders and boots", "Layered fishing shirt", "Cooler (for licensed catch)", "Required state permit", "Pliers and forceps"]),
    ("backcountry-skiing", "Backcountry Skiing Gear List", "Avalanche-aware ski touring essentials.", "061-preview-photo-of-enchantment-permit-area-advanced-lottery.webp",
     ["Backcountry skis with bindings", "Climbing skins", "Ski boots compatible with bindings", "Avalanche beacon", "Probe (240cm+)", "Snow shovel", "Helmet", "Goggles", "Insulated layering kit", "Emergency bivy"]),
]


# ---------------------------------------------------------------------------
# Model definitions (returns module-level handles via _BOUND)
# ---------------------------------------------------------------------------
def _define_models() -> None:
    db = _BOUND["db"]
    User = _BOUND["User"]
    Facility = _BOUND["Facility"]

    class Lottery(db.Model):
        __tablename__ = "lottery"
        id = db.Column(db.Integer, primary_key=True)
        slug = db.Column(db.String(180), unique=True, nullable=False)
        name = db.Column(db.String(220), nullable=False)
        agency = db.Column(db.String(80), nullable=False)
        parent_area = db.Column(db.String(180), default="")
        state = db.Column(db.String(2), nullable=False)
        location = db.Column(db.String(140), default="")
        fee = db.Column(db.Numeric(8, 2), default=0)
        opens = db.Column(db.String(20), nullable=False)
        deadline = db.Column(db.String(20), nullable=False)
        odds = db.Column(db.Float, default=0.1)
        hero_image = db.Column(db.String(220), default="")
        past_winners_json = db.Column(db.Text, default="[]")
        description = db.Column(db.Text, default="")

        @property
        def past_winners(self) -> list[str]:
            return json.loads(self.past_winners_json or "[]")

    class LotteryEntry(db.Model):
        __tablename__ = "lottery_entry"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        lottery_id = db.Column(db.Integer, db.ForeignKey("lottery.id"), nullable=False)
        group_size = db.Column(db.Integer, default=1)
        preferred_date = db.Column(db.String(20), default="")
        alternate_date = db.Column(db.String(20), default="")
        zone = db.Column(db.String(80), default="")
        notes = db.Column(db.Text, default="")
        status = db.Column(db.String(40), default="Entered")
        confirmation_code = db.Column(db.String(40), unique=True, nullable=False)
        created_at = db.Column(db.DateTime, default=lambda: datetime(2026, 5, 12, 12, 0, 0))
        lottery = db.relationship("Lottery")

    class Permit(db.Model):
        __tablename__ = "permit"
        id = db.Column(db.Integer, primary_key=True)
        slug = db.Column(db.String(180), unique=True, nullable=False)
        name = db.Column(db.String(220), nullable=False)
        activity = db.Column(db.String(40), nullable=False)
        agency = db.Column(db.String(80), nullable=False)
        parent_area = db.Column(db.String(180), default="")
        state = db.Column(db.String(2), nullable=False)
        location = db.Column(db.String(140), default="")
        fee = db.Column(db.Numeric(8, 2), default=0)
        hero_image = db.Column(db.String(220), default="")
        description = db.Column(db.Text, default="")
        quota_per_day = db.Column(db.Integer, default=20)
        season_start = db.Column(db.String(20), default="2026-05-01")
        season_end = db.Column(db.String(20), default="2026-10-31")

    class PermitApplication(db.Model):
        __tablename__ = "permit_application"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        permit_id = db.Column(db.Integer, db.ForeignKey("permit.id"), nullable=False)
        party_size = db.Column(db.Integer, default=1)
        entry_date = db.Column(db.String(20), default="")
        exit_date = db.Column(db.String(20), default="")
        trailhead = db.Column(db.String(120), default="")
        emergency_contact = db.Column(db.String(160), default="")
        status = db.Column(db.String(40), default="Submitted")
        confirmation_code = db.Column(db.String(40), unique=True, nullable=False)
        created_at = db.Column(db.DateTime, default=lambda: datetime(2026, 5, 12, 12, 0, 0))
        permit = db.relationship("Permit")

    class Tour(db.Model):
        __tablename__ = "tour"
        id = db.Column(db.Integer, primary_key=True)
        slug = db.Column(db.String(180), unique=True, nullable=False)
        name = db.Column(db.String(220), nullable=False)
        agency = db.Column(db.String(80), nullable=False)
        parent_area = db.Column(db.String(180), default="")
        state = db.Column(db.String(2), nullable=False)
        location = db.Column(db.String(140), default="")
        price = db.Column(db.Numeric(8, 2), default=0)
        hero_image = db.Column(db.String(220), default="")
        description = db.Column(db.Text, default="")
        duration_minutes = db.Column(db.Integer, default=90)
        accessibility = db.Column(db.String(120), default="Accessible Route")
        next_session = db.Column(db.String(40), default="2026-05-15 10:00")

    class TourBooking(db.Model):
        __tablename__ = "tour_booking"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        tour_id = db.Column(db.Integer, db.ForeignKey("tour.id"), nullable=False)
        party_size = db.Column(db.Integer, default=2)
        session_time = db.Column(db.String(40), default="")
        confirmation_code = db.Column(db.String(40), unique=True, nullable=False)
        status = db.Column(db.String(40), default="Booked")
        created_at = db.Column(db.DateTime, default=lambda: datetime(2026, 5, 12, 12, 0, 0))
        tour = db.relationship("Tour")

    class Destination(db.Model):
        __tablename__ = "destination"
        slug = db.Column(db.String(180), primary_key=True)
        name = db.Column(db.String(220), nullable=False)
        kind = db.Column(db.String(60), default="national-park")
        agency = db.Column(db.String(80), nullable=False)
        state = db.Column(db.String(2), nullable=False)
        description = db.Column(db.Text, default="")
        hero_image = db.Column(db.String(220), default="")
        things_to_do_json = db.Column(db.Text, default="[]")

        @property
        def things_to_do(self) -> list[dict]:
            return json.loads(self.things_to_do_json or "[]")

    class SavedDestination(db.Model):
        __tablename__ = "saved_destination"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        destination_slug = db.Column(db.String(180), db.ForeignKey("destination.slug"), nullable=False)
        created_at = db.Column(db.DateTime, default=lambda: datetime(2026, 5, 12, 12, 0, 0))
        destination = db.relationship("Destination")

    class Alert(db.Model):
        __tablename__ = "alert"
        slug = db.Column(db.String(180), primary_key=True)
        title = db.Column(db.String(220), nullable=False)
        destination_slug = db.Column(db.String(180), default="")
        agency = db.Column(db.String(80), nullable=False)
        severity = db.Column(db.String(40), default="advisory")
        posted_date = db.Column(db.String(20), default="2026-04-15")
        body = db.Column(db.Text, default="")

    class AlertSubscription(db.Model):
        __tablename__ = "alert_subscription"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        alert_slug = db.Column(db.String(180), db.ForeignKey("alert.slug"), nullable=False)
        notify_email = db.Column(db.Boolean, default=True)
        notify_sms = db.Column(db.Boolean, default=False)
        created_at = db.Column(db.DateTime, default=lambda: datetime(2026, 5, 12, 12, 0, 0))
        alert = db.relationship("Alert")

    class TripPlan(db.Model):
        __tablename__ = "trip_plan"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        name = db.Column(db.String(160), nullable=False)
        start_date = db.Column(db.String(20), default="2026-06-01")
        end_date = db.Column(db.String(20), default="2026-06-08")
        notes = db.Column(db.Text, default="")
        is_public = db.Column(db.Boolean, default=False)
        share_token = db.Column(db.String(60), default="")
        created_at = db.Column(db.DateTime, default=lambda: datetime(2026, 5, 12, 12, 0, 0))

    class TripPlanItem(db.Model):
        __tablename__ = "trip_plan_item"
        id = db.Column(db.Integer, primary_key=True)
        trip_id = db.Column(db.Integer, db.ForeignKey("trip_plan.id"), nullable=False)
        position = db.Column(db.Integer, default=1)
        kind = db.Column(db.String(40), default="facility")
        ref_slug = db.Column(db.String(180), default="")
        title = db.Column(db.String(220), default="")
        notes = db.Column(db.Text, default="")
        trip = db.relationship("TripPlan", backref="items")

    class GearList(db.Model):
        __tablename__ = "gear_list"
        category = db.Column(db.String(60), primary_key=True)
        name = db.Column(db.String(160), nullable=False)
        description = db.Column(db.Text, default="")
        hero_image = db.Column(db.String(220), default="")

    class GearItem(db.Model):
        __tablename__ = "gear_item"
        id = db.Column(db.Integer, primary_key=True)
        category = db.Column(db.String(60), db.ForeignKey("gear_list.category"), nullable=False)
        position = db.Column(db.Integer, default=1)
        text = db.Column(db.String(220), nullable=False)
        gear_list = db.relationship("GearList", backref="items")

    class GearChecklist(db.Model):
        __tablename__ = "gear_checklist"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        category = db.Column(db.String(60), nullable=False)
        items_json = db.Column(db.Text, default="[]")
        created_at = db.Column(db.DateTime, default=lambda: datetime(2026, 5, 12, 12, 0, 0))

    class GroupReservation(db.Model):
        __tablename__ = "group_reservation"
        id = db.Column(db.Integer, primary_key=True)
        slug = db.Column(db.String(180), unique=True, nullable=False)
        name = db.Column(db.String(220), nullable=False)
        facility_slug = db.Column(db.String(180), default="")
        capacity = db.Column(db.Integer, default=20)
        fee = db.Column(db.Numeric(8, 2), default=120)
        amenities_json = db.Column(db.Text, default="[]")
        hero_image = db.Column(db.String(220), default="")
        location = db.Column(db.String(140), default="")
        state = db.Column(db.String(2), default="")

    class GroupReservationRequest(db.Model):
        __tablename__ = "group_reservation_request"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        group_id = db.Column(db.Integer, db.ForeignKey("group_reservation.id"), nullable=False)
        party_size = db.Column(db.Integer, default=20)
        event_date = db.Column(db.String(20), default="")
        notes = db.Column(db.Text, default="")
        status = db.Column(db.String(40), default="Submitted")
        confirmation_code = db.Column(db.String(40), unique=True, nullable=False)
        created_at = db.Column(db.DateTime, default=lambda: datetime(2026, 5, 12, 12, 0, 0))
        group = db.relationship("GroupReservation")

    class ConditionReport(db.Model):
        __tablename__ = "condition_report"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        facility_id = db.Column(db.Integer, db.ForeignKey("facility.id"), nullable=False)
        category = db.Column(db.String(60), default="trail")
        severity = db.Column(db.String(40), default="advisory")
        body = db.Column(db.Text, nullable=False)
        created_at = db.Column(db.DateTime, default=lambda: datetime(2026, 5, 12, 12, 0, 0))
        facility = db.relationship("Facility")

    class CheckIn(db.Model):
        __tablename__ = "check_in"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        reservation_id = db.Column(db.Integer, db.ForeignKey("reservation.id"), nullable=False)
        checked_in_at = db.Column(db.DateTime, default=lambda: datetime(2026, 5, 12, 12, 0, 0))
        party_count = db.Column(db.Integer, default=2)
        vehicle_plate = db.Column(db.String(20), default="")
        notes = db.Column(db.Text, default="")

    class TimedEntryPark(db.Model):
        __tablename__ = "timed_entry_park"
        slug = db.Column(db.String(60), primary_key=True)
        name = db.Column(db.String(160), nullable=False)
        destination_slug = db.Column(db.String(180), default="")
        agency = db.Column(db.String(80), nullable=False)
        location = db.Column(db.String(140), default="")
        fee = db.Column(db.Numeric(8, 2), default=2)
        hero_image = db.Column(db.String(220), default="")
        window_open = db.Column(db.String(20), default="2026-05-01")
        window_close = db.Column(db.String(20), default="2026-10-31")

    class TimedEntryReservation(db.Model):
        __tablename__ = "timed_entry_reservation"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        park_slug = db.Column(db.String(60), db.ForeignKey("timed_entry_park.slug"), nullable=False)
        entry_date = db.Column(db.String(20), nullable=False)
        entry_window = db.Column(db.String(40), nullable=False)
        vehicle_plate = db.Column(db.String(20), default="")
        party_size = db.Column(db.Integer, default=2)
        confirmation_code = db.Column(db.String(40), unique=True, nullable=False)
        created_at = db.Column(db.DateTime, default=lambda: datetime(2026, 5, 12, 12, 0, 0))
        park = db.relationship("TimedEntryPark")

    class FacilityPhoto(db.Model):
        __tablename__ = "facility_photo"
        id = db.Column(db.Integer, primary_key=True)
        facility_id = db.Column(db.Integer, db.ForeignKey("facility.id"), nullable=False)
        position = db.Column(db.Integer, default=1)
        filename = db.Column(db.String(220), nullable=False)
        caption = db.Column(db.String(220), default="")
        facility = db.relationship("Facility", backref="photos")

    class ReservationModification(db.Model):
        __tablename__ = "reservation_modification"
        id = db.Column(db.Integer, primary_key=True)
        reservation_id = db.Column(db.Integer, db.ForeignKey("reservation.id"), nullable=False)
        user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        previous_start_date = db.Column(db.String(20))
        previous_end_date = db.Column(db.String(20))
        new_start_date = db.Column(db.String(20))
        new_end_date = db.Column(db.String(20))
        reason = db.Column(db.String(220), default="")
        created_at = db.Column(db.DateTime, default=lambda: datetime(2026, 5, 12, 12, 0, 0))

    _BOUND.update({
        "Lottery": Lottery, "LotteryEntry": LotteryEntry,
        "Permit": Permit, "PermitApplication": PermitApplication,
        "Tour": Tour, "TourBooking": TourBooking,
        "Destination": Destination, "SavedDestination": SavedDestination,
        "Alert": Alert, "AlertSubscription": AlertSubscription,
        "TripPlan": TripPlan, "TripPlanItem": TripPlanItem,
        "GearList": GearList, "GearItem": GearItem, "GearChecklist": GearChecklist,
        "GroupReservation": GroupReservation, "GroupReservationRequest": GroupReservationRequest,
        "ConditionReport": ConditionReport, "CheckIn": CheckIn,
        "TimedEntryPark": TimedEntryPark, "TimedEntryReservation": TimedEntryReservation,
        "FacilityPhoto": FacilityPhoto,
        "ReservationModification": ReservationModification,
    })


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
def _register_routes(app) -> None:
    db = _BOUND["db"]
    Facility = _BOUND["Facility"]
    Reservation = _BOUND["Reservation"]
    Lottery = _BOUND["Lottery"]
    LotteryEntry = _BOUND["LotteryEntry"]
    Permit = _BOUND["Permit"]
    PermitApplication = _BOUND["PermitApplication"]
    Tour = _BOUND["Tour"]
    TourBooking = _BOUND["TourBooking"]
    Destination = _BOUND["Destination"]
    SavedDestination = _BOUND["SavedDestination"]
    Alert = _BOUND["Alert"]
    AlertSubscription = _BOUND["AlertSubscription"]
    TripPlan = _BOUND["TripPlan"]
    TripPlanItem = _BOUND["TripPlanItem"]
    GearList = _BOUND["GearList"]
    GearItem = _BOUND["GearItem"]
    GearChecklist = _BOUND["GearChecklist"]
    GroupReservation = _BOUND["GroupReservation"]
    GroupReservationRequest = _BOUND["GroupReservationRequest"]
    ConditionReport = _BOUND["ConditionReport"]
    CheckIn = _BOUND["CheckIn"]
    TimedEntryPark = _BOUND["TimedEntryPark"]
    TimedEntryReservation = _BOUND["TimedEntryReservation"]
    FacilityPhoto = _BOUND["FacilityPhoto"]
    ReservationModification = _BOUND["ReservationModification"]

    # ------- Lotteries -------
    @app.route("/lottery/list")
    def ext_lottery_list():
        items = Lottery.query.order_by(Lottery.deadline).all()
        return render_template("ext/lottery_list.html", lotteries=items)

    @app.route("/lottery/<slug>")
    def ext_lottery_detail(slug):
        lottery = Lottery.query.filter_by(slug=slug).first_or_404()
        return render_template("ext/lottery_detail.html", lottery=lottery)

    @app.route("/lottery/<slug>/enter", methods=["GET", "POST"])
    @login_required
    def ext_lottery_enter(slug):
        lottery = Lottery.query.filter_by(slug=slug).first_or_404()
        if request.method == "POST":
            try:
                group_size = max(1, min(int(request.form.get("group_size") or 1), 12))
            except ValueError:
                group_size = 1
            code = f"LOT-{lottery.id:03d}-{LotteryEntry.query.count() + 1:05d}"
            entry = LotteryEntry(
                user_id=current_user.id,
                lottery_id=lottery.id,
                group_size=group_size,
                preferred_date=request.form.get("preferred_date") or lottery.opens,
                alternate_date=request.form.get("alternate_date") or lottery.deadline,
                zone=request.form.get("zone", "").strip(),
                notes=request.form.get("notes", "").strip(),
                status="Entered",
                confirmation_code=code,
            )
            db.session.add(entry)
            db.session.commit()
            flash(f"Lottery entry submitted. Confirmation code {code}.", "success")
            return redirect(url_for("ext_lottery_detail", slug=slug, _anchor="entries"))
        return render_template("ext/lottery_apply.html", lottery=lottery)

    # ------- Permits -------
    @app.route("/permits/list")
    def ext_permit_list():
        activity = request.args.get("activity", "").strip()
        q = Permit.query
        if activity:
            q = q.filter(Permit.activity == activity)
        items = q.order_by(Permit.name).all()
        activities = sorted({p.activity for p in Permit.query.all()})
        return render_template("ext/permit_list.html", permits=items, activities=activities, current_activity=activity)

    @app.route("/permits/<slug>")
    def ext_permit_detail(slug):
        permit = Permit.query.filter_by(slug=slug).first_or_404()
        return render_template("ext/permit_detail.html", permit=permit)

    @app.route("/permits/<slug>/apply", methods=["GET", "POST"])
    @login_required
    def ext_permit_apply(slug):
        permit = Permit.query.filter_by(slug=slug).first_or_404()
        if request.method == "POST":
            try:
                party = max(1, min(int(request.form.get("party_size") or 1), 12))
            except ValueError:
                party = 1
            code = f"PERMIT-{permit.id:03d}-{PermitApplication.query.count() + 1:05d}"
            app_row = PermitApplication(
                user_id=current_user.id,
                permit_id=permit.id,
                party_size=party,
                entry_date=request.form.get("entry_date") or permit.season_start,
                exit_date=request.form.get("exit_date") or permit.season_end,
                trailhead=request.form.get("trailhead", "").strip(),
                emergency_contact=request.form.get("emergency_contact", "").strip(),
                status="Submitted",
                confirmation_code=code,
            )
            db.session.add(app_row)
            db.session.commit()
            flash(f"Permit application submitted. Confirmation code {code}.", "success")
            return redirect(url_for("ext_myaccount_permits"))
        return render_template("ext/permit_apply.html", permit=permit)

    # ------- Tours -------
    @app.route("/tour/list")
    def ext_tour_list():
        items = Tour.query.order_by(Tour.name).all()
        return render_template("ext/tour_list.html", tours=items)

    @app.route("/tour/<slug>")
    def ext_tour_detail(slug):
        tour = Tour.query.filter_by(slug=slug).first_or_404()
        return render_template("ext/tour_detail.html", tour=tour)

    @app.route("/tour/<slug>/book", methods=["GET", "POST"])
    @login_required
    def ext_tour_book(slug):
        tour = Tour.query.filter_by(slug=slug).first_or_404()
        if request.method == "POST":
            try:
                party = max(1, min(int(request.form.get("party_size") or 2), 12))
            except ValueError:
                party = 2
            code = f"TOUR-{tour.id:03d}-{TourBooking.query.count() + 1:05d}"
            db.session.add(TourBooking(
                user_id=current_user.id,
                tour_id=tour.id,
                party_size=party,
                session_time=request.form.get("session_time") or tour.next_session,
                confirmation_code=code,
                status="Booked",
            ))
            db.session.commit()
            flash(f"Tour booked. Confirmation code {code}.", "success")
            return redirect(url_for("ext_tour_detail", slug=slug))
        return render_template("ext/tour_book.html", tour=tour)

    # ------- Destinations -------
    @app.route("/destination/list")
    def ext_destination_list():
        kind = request.args.get("kind", "").strip()
        q = Destination.query
        if kind:
            q = q.filter(Destination.kind == kind)
        items = q.order_by(Destination.name).all()
        kinds = sorted({d.kind for d in Destination.query.all()})
        return render_template("ext/destination_list.html", destinations=items, kinds=kinds, current_kind=kind)

    @app.route("/destination/<slug>")
    def ext_destination_detail(slug):
        destination = Destination.query.filter_by(slug=slug).first_or_404()
        alerts = Alert.query.filter_by(destination_slug=slug).order_by(Alert.posted_date.desc()).all()
        return render_template("ext/destination_hub.html", destination=destination, alerts=alerts)

    @app.route("/destination/<slug>/things-to-do")
    def ext_destination_things(slug):
        destination = Destination.query.filter_by(slug=slug).first_or_404()
        return render_template("ext/destination_things_to_do.html", destination=destination)

    @app.route("/destination/<slug>/save", methods=["POST"])
    @login_required
    def ext_destination_save(slug):
        destination = Destination.query.filter_by(slug=slug).first_or_404()
        existing = SavedDestination.query.filter_by(user_id=current_user.id, destination_slug=slug).first()
        if existing:
            db.session.delete(existing)
            flash(f"Removed {destination.name} from saved destinations.", "info")
        else:
            db.session.add(SavedDestination(user_id=current_user.id, destination_slug=slug))
            flash(f"Saved {destination.name} to your destinations.", "success")
        db.session.commit()
        return redirect(request.referrer or url_for("ext_destination_detail", slug=slug))

    # ------- Alerts -------
    @app.route("/alerts/list")
    def ext_alerts_list():
        items = Alert.query.order_by(Alert.posted_date.desc()).all()
        return render_template("ext/alerts_list.html", alerts=items)

    @app.route("/alerts/<slug>")
    def ext_alerts_detail(slug):
        alert = Alert.query.filter_by(slug=slug).first_or_404()
        destination = Destination.query.filter_by(slug=alert.destination_slug).first() if alert.destination_slug else None
        return render_template("ext/alerts_detail.html", alert=alert, destination=destination)

    @app.route("/alerts/<slug>/subscribe", methods=["POST"])
    @login_required
    def ext_alerts_subscribe(slug):
        alert = Alert.query.filter_by(slug=slug).first_or_404()
        existing = AlertSubscription.query.filter_by(user_id=current_user.id, alert_slug=slug).first()
        if existing:
            db.session.delete(existing)
            flash("Alert subscription removed.", "info")
        else:
            db.session.add(AlertSubscription(
                user_id=current_user.id,
                alert_slug=slug,
                notify_email=request.form.get("notify_email") != "off",
                notify_sms=request.form.get("notify_sms") == "on",
            ))
            flash(f"Subscribed to alert {alert.title}.", "success")
        db.session.commit()
        return redirect(url_for("ext_alerts_detail", slug=slug))

    # ------- Timed entry -------
    @app.route("/timed-entry/list")
    def ext_timed_entry_list():
        parks = TimedEntryPark.query.order_by(TimedEntryPark.name).all()
        return render_template("ext/timed_entry_list.html", parks=parks)

    @app.route("/timed-entry/<park>")
    def ext_timed_entry_park(park):
        park_row = TimedEntryPark.query.filter_by(slug=park).first_or_404()
        return render_template("ext/timed_entry.html", park=park_row)

    @app.route("/timed-entry/<park>/book", methods=["POST"])
    @login_required
    def ext_timed_entry_book(park):
        park_row = TimedEntryPark.query.filter_by(slug=park).first_or_404()
        code = f"TE-{park_row.slug[:6].upper()}-{TimedEntryReservation.query.count() + 1:05d}"
        try:
            party = max(1, min(int(request.form.get("party_size") or 2), 8))
        except ValueError:
            party = 2
        db.session.add(TimedEntryReservation(
            user_id=current_user.id,
            park_slug=park_row.slug,
            entry_date=request.form.get("entry_date") or park_row.window_open,
            entry_window=request.form.get("entry_window") or "07:00 - 09:00",
            vehicle_plate=request.form.get("vehicle_plate", "").strip(),
            party_size=party,
            confirmation_code=code,
        ))
        db.session.commit()
        flash(f"Timed entry confirmed. Confirmation code {code}.", "success")
        return redirect(url_for("ext_timed_entry_park", park=park))

    # ------- Trip Planner -------
    @app.route("/trip-planner")
    @login_required
    def ext_trip_planner_index():
        plans = TripPlan.query.filter_by(user_id=current_user.id).order_by(TripPlan.created_at.desc()).all()
        return render_template("ext/trip_planner.html", plans=plans)

    @app.route("/trip-planner/<int:plan_id>")
    @login_required
    def ext_trip_planner_detail(plan_id):
        plan = TripPlan.query.filter_by(id=plan_id, user_id=current_user.id).first_or_404()
        items = TripPlanItem.query.filter_by(trip_id=plan.id).order_by(TripPlanItem.position).all()
        return render_template("ext/trip_planner_detail.html", plan=plan, items=items)

    @app.route("/trip-planner/create", methods=["POST"])
    @login_required
    def ext_trip_planner_create():
        name = (request.form.get("name") or "Untitled Trip").strip()
        plan = TripPlan(
            user_id=current_user.id,
            name=name,
            start_date=request.form.get("start_date") or "2026-06-01",
            end_date=request.form.get("end_date") or "2026-06-08",
            notes=request.form.get("notes", "").strip(),
        )
        db.session.add(plan)
        db.session.commit()
        flash(f"Trip plan '{name}' created.", "success")
        return redirect(url_for("ext_trip_planner_detail", plan_id=plan.id))

    @app.route("/trip-planner/<int:plan_id>/add", methods=["POST"])
    @login_required
    def ext_trip_planner_add(plan_id):
        plan = TripPlan.query.filter_by(id=plan_id, user_id=current_user.id).first_or_404()
        position = TripPlanItem.query.filter_by(trip_id=plan.id).count() + 1
        db.session.add(TripPlanItem(
            trip_id=plan.id,
            position=position,
            kind=request.form.get("kind", "facility"),
            ref_slug=request.form.get("ref_slug", "").strip(),
            title=request.form.get("title", "").strip() or "Untitled stop",
            notes=request.form.get("notes", "").strip(),
        ))
        db.session.commit()
        flash("Added to trip plan.", "success")
        return redirect(url_for("ext_trip_planner_detail", plan_id=plan.id))

    @app.route("/trip-planner/<int:plan_id>/share", methods=["POST"])
    @login_required
    def ext_trip_planner_share(plan_id):
        plan = TripPlan.query.filter_by(id=plan_id, user_id=current_user.id).first_or_404()
        plan.is_public = True
        if not plan.share_token:
            plan.share_token = hashlib.sha1(f"{plan.id}-{plan.name}-share".encode()).hexdigest()[:16]
        db.session.commit()
        flash(f"Trip plan share link ready: /trip-planner/shared/{plan.share_token}.", "success")
        return redirect(url_for("ext_trip_planner_detail", plan_id=plan.id))

    # ------- Gear lists -------
    @app.route("/gear-list")
    def ext_gear_list_index():
        gear = GearList.query.order_by(GearList.name).all()
        return render_template("ext/gear_list_index.html", gear_lists=gear)

    @app.route("/gear-list/<category>")
    def ext_gear_list_detail(category):
        gear = GearList.query.filter_by(category=category).first_or_404()
        items = GearItem.query.filter_by(category=category).order_by(GearItem.position).all()
        return render_template("ext/gear_list.html", gear=gear, items=items)

    @app.route("/gear-list/<category>/save", methods=["POST"])
    @login_required
    def ext_gear_list_save(category):
        gear = GearList.query.filter_by(category=category).first_or_404()
        items = request.form.getlist("items")
        db.session.add(GearChecklist(
            user_id=current_user.id,
            category=gear.category,
            items_json=json.dumps(items),
        ))
        db.session.commit()
        flash(f"Saved {gear.name} checklist with {len(items)} items.", "success")
        return redirect(url_for("ext_gear_list_detail", category=category))

    # ------- My account hubs -------
    @app.route("/myaccount")
    @login_required
    def ext_myaccount_dashboard():
        reservations = Reservation.query.filter_by(user_id=current_user.id).order_by(Reservation.start_date.desc()).limit(5).all()
        permits = PermitApplication.query.filter_by(user_id=current_user.id).order_by(PermitApplication.id.desc()).limit(5).all()
        lottery_entries = LotteryEntry.query.filter_by(user_id=current_user.id).order_by(LotteryEntry.id.desc()).limit(5).all()
        plans = TripPlan.query.filter_by(user_id=current_user.id).order_by(TripPlan.id.desc()).limit(5).all()
        return render_template("ext/myaccount_dashboard.html",
                               reservations=reservations, permits=permits,
                               lottery_entries=lottery_entries, plans=plans)

    @app.route("/myaccount/reservations")
    @login_required
    def ext_myaccount_reservations():
        reservations = Reservation.query.filter_by(user_id=current_user.id).order_by(Reservation.start_date.desc()).all()
        return render_template("ext/myaccount_reservations.html", reservations=reservations)

    @app.route("/myaccount/permits")
    @login_required
    def ext_myaccount_permits():
        permits = PermitApplication.query.filter_by(user_id=current_user.id).order_by(PermitApplication.id.desc()).all()
        lottery_entries = LotteryEntry.query.filter_by(user_id=current_user.id).order_by(LotteryEntry.id.desc()).all()
        return render_template("ext/myaccount_permits.html", permits=permits, lottery_entries=lottery_entries)

    @app.route("/myaccount/profile")
    @login_required
    def ext_myaccount_profile():
        return render_template("ext/myaccount_profile.html")

    @app.route("/myaccount/tour-bookings")
    @login_required
    def ext_myaccount_tour_bookings():
        bookings = TourBooking.query.filter_by(user_id=current_user.id).order_by(TourBooking.id.desc()).all()
        return render_template("ext/myaccount_tour_bookings.html", bookings=bookings)

    @app.route("/myaccount/check-ins")
    @login_required
    def ext_myaccount_check_ins():
        checkins = CheckIn.query.filter_by(user_id=current_user.id).order_by(CheckIn.id.desc()).all()
        res_ids = {c.reservation_id for c in checkins}
        reservation_lookup = {
            r.id: r for r in Reservation.query.filter(Reservation.id.in_(res_ids)).all()
        } if res_ids else {}
        return render_template(
            "ext/myaccount_check_ins.html",
            checkins=checkins, reservation_lookup=reservation_lookup,
        )

    @app.route("/myaccount/checklists")
    @login_required
    def ext_myaccount_checklists():
        raw = GearChecklist.query.filter_by(user_id=current_user.id).order_by(GearChecklist.id.desc()).all()
        # Perf: one prefetch keyed by category — replaces N×GearList.query.first()
        # inside the per-row loop. First-match semantics preserved via .first().
        gear_by_cat = {}
        cats_needed = {row.category for row in raw if row.category}
        if cats_needed:
            for g in GearList.query.filter(GearList.category.in_(cats_needed)).all():
                gear_by_cat.setdefault(g.category, g)
        checklists = []
        for row in raw:
            gear = gear_by_cat.get(row.category)
            try:
                items = json.loads(row.items_json or "[]")
            except (ValueError, TypeError):
                items = []
            checklists.append({"row": row, "items": items, "gear": gear})
        return render_template("ext/myaccount_gear_checklists.html", checklists=checklists)

    @app.route("/myaccount/condition-reports")
    @login_required
    def ext_myaccount_condition_reports():
        reports = (
            ConditionReport.query.filter_by(user_id=current_user.id)
            .order_by(ConditionReport.id.desc())
            .all()
        )
        return render_template("ext/myaccount_condition_reports.html", reports=reports)

    @app.route("/myaccount/timed-entry")
    @login_required
    def ext_myaccount_timed_entry():
        entries = (
            TimedEntryReservation.query.filter_by(user_id=current_user.id)
            .order_by(TimedEntryReservation.id.desc())
            .all()
        )
        return render_template("ext/myaccount_timed_entry.html", entries=entries)

    @app.route("/myaccount/alert-subscriptions")
    @login_required
    def ext_myaccount_alert_subscriptions():
        subs = (
            AlertSubscription.query.filter_by(user_id=current_user.id)
            .order_by(AlertSubscription.id.desc())
            .all()
        )
        return render_template("ext/myaccount_alert_subscriptions.html", subs=subs)

    @app.route("/myaccount/modifications")
    @login_required
    def ext_myaccount_modifications():
        mods = (
            ReservationModification.query.filter_by(user_id=current_user.id)
            .order_by(ReservationModification.id.desc())
            .all()
        )
        res_ids = {m.reservation_id for m in mods}
        reservation_lookup = {
            r.id: r for r in Reservation.query.filter(Reservation.id.in_(res_ids)).all()
        } if res_ids else {}
        return render_template(
            "ext/myaccount_modifications.html",
            mods=mods, reservation_lookup=reservation_lookup,
        )

    # ------- Public condition feed -------
    @app.route("/condition-reports")
    def ext_condition_reports_feed():
        category = (request.args.get("category") or "").strip()
        severity = (request.args.get("severity") or "").strip()
        q = ConditionReport.query
        if category:
            q = q.filter(ConditionReport.category == category)
        if severity:
            q = q.filter(ConditionReport.severity == severity)
        reports = q.order_by(ConditionReport.id.desc()).limit(60).all()
        categories = sorted({r.category for r in ConditionReport.query.all()})
        severities = sorted({r.severity for r in ConditionReport.query.all()})
        return render_template(
            "condition_reports.html",
            reports=reports,
            categories=categories, severities=severities,
            current_category=category, current_severity=severity,
        )

    # ------- Reports / check-in -------
    @app.route("/report-condition/<int:facility_id>", methods=["GET", "POST"])
    @login_required
    def ext_report_condition(facility_id):
        facility = Facility.query.get_or_404(facility_id)
        if request.method == "POST":
            body = request.form.get("body", "").strip()
            if len(body) < 10:
                flash("Please include at least a short description of the condition.", "danger")
                return redirect(url_for("ext_report_condition", facility_id=facility_id))
            db.session.add(ConditionReport(
                user_id=current_user.id,
                facility_id=facility.id,
                category=request.form.get("category", "trail"),
                severity=request.form.get("severity", "advisory"),
                body=body,
            ))
            db.session.commit()
            flash("Condition report submitted. Thanks for the heads-up.", "success")
            return redirect(url_for("facility_detail", slug=facility.slug))
        return render_template("ext/report_condition.html", facility=facility)

    @app.route("/reservations/<int:reservation_id>/check-in", methods=["GET", "POST"])
    @login_required
    def ext_check_in(reservation_id):
        reservation = Reservation.query.filter_by(id=reservation_id, user_id=current_user.id).first_or_404()
        if request.method == "POST":
            try:
                party = max(1, min(int(request.form.get("party_count") or reservation.guests), 12))
            except ValueError:
                party = reservation.guests
            db.session.add(CheckIn(
                user_id=current_user.id,
                reservation_id=reservation.id,
                party_count=party,
                vehicle_plate=request.form.get("vehicle_plate", "").strip(),
                notes=request.form.get("notes", "").strip(),
            ))
            reservation.status = "Checked In"
            db.session.commit()
            flash(f"Checked in for {reservation.confirmation_code}.", "success")
            return redirect(url_for("reservations"))
        return render_template("ext/check_in.html", reservation=reservation)

    @app.route("/reservations/<int:reservation_id>/modify", methods=["GET", "POST"])
    @login_required
    def ext_reservation_modify(reservation_id):
        reservation = Reservation.query.filter_by(id=reservation_id, user_id=current_user.id).first_or_404()
        if request.method == "POST":
            db.session.add(ReservationModification(
                reservation_id=reservation.id,
                user_id=current_user.id,
                previous_start_date=reservation.start_date,
                previous_end_date=reservation.end_date,
                new_start_date=request.form.get("new_start_date") or reservation.start_date,
                new_end_date=request.form.get("new_end_date") or reservation.end_date,
                reason=request.form.get("reason", "").strip(),
            ))
            reservation.start_date = request.form.get("new_start_date") or reservation.start_date
            reservation.end_date = request.form.get("new_end_date") or reservation.end_date
            db.session.commit()
            flash(f"Reservation {reservation.confirmation_code} updated.", "success")
            return redirect(url_for("reservations"))
        return render_template("ext/reservation_modify.html", reservation=reservation)

    # ------- Group reservation -------
    @app.route("/group-reservation/list")
    def ext_group_reservation_list():
        items = GroupReservation.query.order_by(GroupReservation.name).all()
        return render_template("ext/group_reservation_list.html", groups=items)

    @app.route("/group-reservation/<slug>")
    def ext_group_reservation_detail(slug):
        group = GroupReservation.query.filter_by(slug=slug).first_or_404()
        return render_template("ext/group_reservation.html", group=group)

    @app.route("/group-reservation/<slug>/request", methods=["POST"])
    @login_required
    def ext_group_reservation_request(slug):
        group = GroupReservation.query.filter_by(slug=slug).first_or_404()
        try:
            party = max(1, min(int(request.form.get("party_size") or group.capacity), 200))
        except ValueError:
            party = group.capacity
        code = f"GROUP-{group.id:03d}-{GroupReservationRequest.query.count() + 1:05d}"
        db.session.add(GroupReservationRequest(
            user_id=current_user.id,
            group_id=group.id,
            party_size=party,
            event_date=request.form.get("event_date") or "2026-07-15",
            notes=request.form.get("notes", "").strip(),
            confirmation_code=code,
        ))
        db.session.commit()
        flash(f"Group reservation request sent. Confirmation code {code}.", "success")
        return redirect(url_for("ext_group_reservation_detail", slug=slug))

    # ------- Site detail (per-campsite child page) -------
    @app.route("/camping/site/<int:site_id>")
    def ext_camping_site(site_id):
        Campsite = _BOUND["Campsite"]
        site = Campsite.query.get_or_404(site_id)
        return render_template("ext/site_detail.html", site=site)

    @app.route("/camping/campgrounds/<int:facility_id>")
    def ext_camping_campground(facility_id):
        facility = Facility.query.get_or_404(facility_id)
        return redirect(url_for("facility_detail", slug=facility.slug))


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------
def seed_extensions() -> None:
    db = _BOUND["db"]
    Facility = _BOUND["Facility"]
    User = _BOUND["User"]
    Lottery = _BOUND["Lottery"]
    Permit = _BOUND["Permit"]
    Tour = _BOUND["Tour"]
    Destination = _BOUND["Destination"]
    Alert = _BOUND["Alert"]
    GearList = _BOUND["GearList"]
    GearItem = _BOUND["GearItem"]
    GroupReservation = _BOUND["GroupReservation"]
    TimedEntryPark = _BOUND["TimedEntryPark"]
    FacilityPhoto = _BOUND["FacilityPhoto"]
    Reservation = _BOUND["Reservation"]
    SavedDestination = _BOUND["SavedDestination"]
    LotteryEntry = _BOUND["LotteryEntry"]
    PermitApplication = _BOUND["PermitApplication"]
    TripPlan = _BOUND["TripPlan"]
    TripPlanItem = _BOUND["TripPlanItem"]

    if Lottery.query.count() == 0:
        for slug, name, agency, parent, state, location, fee, opens, deadline, odds, hero in LOTTERY_SPECS:
            past = [f"2024 — {2400 + i * 137} entries / {int((2400 + i * 137) * odds)} winners" for i in range(3)]
            db.session.add(Lottery(slug=slug, name=name, agency=agency, parent_area=parent, state=state,
                                   location=location, fee=Decimal(str(fee)), opens=opens, deadline=deadline,
                                   odds=odds, hero_image=hero, past_winners_json=json.dumps(past),
                                   description=(f"{name} accepts entries from {opens} through {deadline}. "
                                                f"Historic acceptance rate is roughly {int(odds * 100)}%. "
                                                f"Fee {fee or 'free'} per entry; managed by {agency}.")))
        db.session.commit()

    if Permit.query.count() == 0:
        for slug, name, activity, agency, parent, state, location, fee, hero, desc in PERMIT_SPECS:
            hero = PERMIT_REAL_PHOTOS.get(slug, hero)
            db.session.add(Permit(slug=slug, name=name, activity=activity, agency=agency,
                                  parent_area=parent, state=state, location=location,
                                  fee=Decimal(str(fee)), hero_image=hero, description=desc))
        db.session.commit()

    if Tour.query.count() == 0:
        for idx, (slug, name, agency, parent, state, location, price, hero, desc) in enumerate(TOUR_SPECS):
            hero = TOUR_REAL_PHOTOS.get(slug, hero)
            db.session.add(Tour(slug=slug, name=name, agency=agency, parent_area=parent, state=state,
                                location=location, price=Decimal(str(price)), hero_image=hero,
                                description=desc, duration_minutes=60 + (idx % 5) * 30,
                                accessibility=["Accessible Route", "Limited Mobility", "Stairs / Ladders"][idx % 3],
                                next_session=f"2026-05-{15 + (idx % 12):02d} {8 + (idx % 8):02d}:00"))
        db.session.commit()

    if Destination.query.count() == 0:
        for slug, name, kind, agency, state, desc, hero in DESTINATION_SPECS:
            hero = DESTINATION_REAL_PHOTOS.get(slug, hero)
            things = [
                {"title": "Featured tours", "body": f"Reserve guided tours and ranger programs within {name}."},
                {"title": "Backcountry permits", "body": f"Apply for wilderness and overnight permits inside {name}."},
                {"title": "Day-use access", "body": f"Plan parking, picnic, or shuttle reservations across {name}."},
                {"title": "Lodging & camping", "body": f"Browse campsites and cabins managed by {agency}."},
            ]
            db.session.add(Destination(slug=slug, name=name, kind=kind, agency=agency, state=state,
                                       description=desc, hero_image=hero,
                                       things_to_do_json=json.dumps(things)))
        db.session.commit()

    if Alert.query.count() == 0:
        for slug, title, dest_slug, agency, body in ALERT_SPECS:
            severity = "warning" if "Closure" in title or "Capacity" in title else "advisory"
            db.session.add(Alert(slug=slug, title=title, destination_slug=dest_slug,
                                 agency=agency, severity=severity,
                                 posted_date="2026-04-15", body=body + " Review the official destination page for current details."))
        db.session.commit()

    if TimedEntryPark.query.count() == 0:
        for slug, name, dest_slug, agency, location, fee, hero in TIMED_ENTRY_PARKS:
            db.session.add(TimedEntryPark(slug=slug, name=name, destination_slug=dest_slug,
                                          agency=agency, location=location,
                                          fee=Decimal(str(fee)), hero_image=hero))
        db.session.commit()

    if GearList.query.count() == 0:
        for category, name, desc, hero, items in GEAR_LIST_SPECS:
            db.session.add(GearList(category=category, name=name, description=desc, hero_image=hero))
            db.session.flush()
            for idx, text in enumerate(items, start=1):
                db.session.add(GearItem(category=category, position=idx, text=text))
        db.session.commit()

    if GroupReservation.query.count() == 0:
        group_specs = [
            ("rob-hill-group-campground", "Rob Hill Group Campground", "Presidio of San Francisco", "CA", 50, 165, "real-nav-camping.webp",
             ["Group fire ring", "Restrooms", "Picnic Tables", "Tent Pads", "Vehicle Parking"]),
            ("twin-creek-group-camping", "Twin Creek Group Camping", "Tenkiller Ferry Lake", "OK", 60, 180, "034-preview-photo-of-twin-creek-campground-group-camping-site.webp",
             ["Group Pavilion", "Picnic Tables", "Vault Toilets", "Lake Access"]),
            ("crescent-moon-group-picnic", "Crescent Moon Group Picnic Site", "Coconino National Forest", "AZ", 40, 95, "real-nav-venues.webp",
             ["Picnic Pavilion", "Creek Access", "Grill", "Restrooms"]),
            ("catoctin-mountain-group-pavilion", "Catoctin Mountain Group Pavilion", "Catoctin Mountain Park", "MD", 80, 140, "real-nav-venues.webp",
             ["Pavilion", "Grills", "Picnic Tables", "Restrooms"]),
            ("indiana-dunes-group-area", "Indiana Dunes Group Area", "Indiana Dunes National Park", "IN", 35, 120, "real-aquatic-park-cove.webp",
             ["Group Tent Sites", "Beach Access", "Restrooms"]),
            ("everglades-flamingo-group-site", "Flamingo Group Camping", "Everglades National Park", "FL", 30, 110, "real-aquatic-park-cove.webp",
             ["Tent Pads", "Picnic Pavilion", "Boat Launch"]),
            ("acadia-blackwoods-group-site", "Blackwoods Group Camping", "Acadia National Park", "ME", 25, 130, "real-point-reyes-seashore.webp",
             ["Tent Pads", "Restrooms", "Carriage Road Access"]),
            ("yosemite-bridalveil-group-site", "Bridalveil Creek Group Camping", "Yosemite National Park", "CA", 45, 175, "real-yosemite-site-pass-hero.jpeg",
             ["Tent Pads", "Picnic Tables", "Vault Toilets", "Bear Boxes"]),
            ("rocky-glacier-basin-group-site", "Glacier Basin Group Camping", "Rocky Mountain National Park", "CO", 40, 160, "real-nav-camping.webp",
             ["Tent Pads", "Picnic Tables", "Bear Lockers"]),
            ("smokies-cataloochee-group-site", "Cataloochee Group Camping", "Great Smoky Mountains National Park", "TN", 30, 130, "017-home.webp",
             ["Group Pavilion", "Picnic Tables", "Vault Toilets"]),
        ]
        for slug, name, area, state, cap, fee, hero, amenities in group_specs:
            db.session.add(GroupReservation(slug=slug, name=name, facility_slug=slug, capacity=cap,
                                            fee=Decimal(str(fee)), amenities_json=json.dumps(amenities),
                                            hero_image=hero, location=area, state=state))
        db.session.commit()

    # Facility photos — boost image utilization by attaching 3-5 photos per facility.
    if FacilityPhoto.query.count() == 0:
        all_facilities = Facility.query.order_by(Facility.id).all()
        gallery_pool = [
            "015-point-reyes-national-seashore.webp", "016-pinnacles-national-park.webp",
            "018-preview-photo-of-outflow-camping.webp", "019-preview-photo-of-brooks-camp-camping-permit.webp",
            "020-preview-photo-of-mammoth-cave-backcountry-camping.webp", "022-preview-photo-of-ausable-river-camping.webp",
            "025-preview-photo-of-horsfall-sand-camping.webp", "026-preview-photo-of-bluff-hike-in-camping.webp",
            "029-preview-photo-of-siltcoos-sand-camping.webp", "031-preview-photo-of-dale-hollow-lake-primitive-camping.webp",
            "034-preview-photo-of-twin-creek-campground-group-camping-site.webp", "036-preview-photo-of-sylvania-wilderness-backcountry-camping.webp",
            "037-preview-photo-of-winhall-brook-camping-area.webp", "040-preview-photo-of-calpine-lookout.webp",
            "047-preview-photo-of-manzanita-lake-camping-cabins-ca.webp", "049-preview-photo-of-canning-creek.webp",
            "050-preview-photo-of-lake-powhatan-glamping.webp", "051-preview-photo-of-bumping-lake-campground.webp",
            "054-preview-photo-of-sherando-lake-recreation-area-family-camping.webp", "055-preview-photo-of-katahdin-woods-waters-national-monument-camping.webp",
            "058-preview-photo-of-soda-springs-campground-bumping-river-wa.webp", "060-preview-photo-of-mt-whitney.webp",
            "061-preview-photo-of-enchantment-permit-area-advanced-lottery.webp", "062-preview-photo-of-desolation-wilderness-permit.webp",
            "066-preview-photo-of-hemlock-cabin.webp", "067-preview-photo-of-inyo-national-forest-wilderness-permits.webp",
            "070-preview-photo-of-central-cascades-wilderness-overnight-permits.webp", "072-preview-photo-of-tilly-jane-a-frame.webp",
            "real-point-reyes-gallery-oak.webp", "real-point-reyes-gallery-drakes.webp",
            "real-point-reyes-gallery-campsite.webp", "real-pinnacles-campground.webp",
            "real-oak-knoll-campground.webp", "real-glory-hole.webp",
            "real-lake-sonoma-boat-in.webp", "real-sf-maritime-tours.webp",
            "real-fort-point-tours.webp", "real-aquatic-park-cove.webp",
            "real-point-reyes-seashore.webp", "real-desolation-hero.webp",
            "real-desolation-granite.webp", "real-desolation-lake.webp",
        ]
        caption_templates = [
            "Wide-angle landscape view at {name}",
            "Campsite layout and amenities at {name}",
            "Wildlife and habitat near {name}",
            "Trailhead and entrance signage at {name}",
            "Photographer's view of {name}",
        ]
        for facility in all_facilities:
            seed_int = int(hashlib.md5(facility.slug.encode()).hexdigest()[:6], 16)
            count = 3 + seed_int % 3  # 3-5
            for pos in range(1, count + 1):
                fn = gallery_pool[(seed_int + pos) % len(gallery_pool)]
                if facility.image and pos == 1:
                    fn = facility.image
                db.session.add(FacilityPhoto(
                    facility_id=facility.id,
                    position=pos,
                    filename=fn,
                    caption=caption_templates[(seed_int + pos) % len(caption_templates)].format(name=facility.name),
                ))
        db.session.commit()

    # Benchmark user fixtures: trip plans + saved destinations + lottery entries + permit apps.
    bench_emails = ["alice.j@test.com", "bob.c@test.com", "carol.d@test.com", "david.k@test.com"]
    bench_users = {u.email: u for u in User.query.filter(User.email.in_(bench_emails)).all()}

    if TripPlan.query.count() == 0 and bench_users:
        plan_specs = [
            ("alice.j@test.com", "Sierra Spring Loop", "2026-06-04", "2026-06-09",
             [("facility", "point-reyes-national-seashore-campground", "Point Reyes overnight"),
              ("tour", "alcatraz-day-tour", "Alcatraz day tour"),
              ("destination", "yosemite-national-park", "Yosemite valley swing")]),
            ("alice.j@test.com", "Bay Area Tour Weekend", "2026-07-10", "2026-07-12",
             [("tour", "sf-maritime-hyde-street-tour", "Hyde Street Pier"),
              ("tour", "fort-point-history-tour", "Fort Point history"),
              ("facility", "kirby-cove-campground", "Kirby Cove overnight")]),
            ("bob.c@test.com", "Cascades Backpacking Week", "2026-08-01", "2026-08-08",
             [("permit", "yosemite-wilderness-permit", "Wilderness entry permit"),
              ("facility", "bumping-lake-campground", "Bumping Lake first night"),
              ("lottery", "enchantments-overnight-lottery", "Enchantments entry attempt")]),
            ("carol.d@test.com", "Rocky Mountains Family Trip", "2026-07-20", "2026-07-26",
             [("destination", "rocky-mountain-national-park", "Trail Ridge Road"),
              ("timed_entry", "rocky-mountain", "Bear Lake corridor entry"),
              ("facility", "moraine-park-campground", "Moraine Park overnight")]),
            ("david.k@test.com", "Southern Coast Discovery", "2026-09-12", "2026-09-19",
             [("destination", "everglades-national-park", "Everglades Anhinga trail"),
              ("permit", "cumberland-island-camping-permit", "Cumberland Island camping"),
              ("tour", "biscayne-heritage-tour", "Biscayne heritage tour")]),
        ]
        for email, name, start, end, items in plan_specs:
            user = bench_users.get(email)
            if not user:
                continue
            plan = TripPlan(user_id=user.id, name=name, start_date=start, end_date=end,
                            notes=f"Auto-built trip plan for {name}.", is_public=False)
            db.session.add(plan)
            db.session.flush()
            for idx, (kind, ref_slug, title) in enumerate(items, start=1):
                db.session.add(TripPlanItem(trip_id=plan.id, position=idx, kind=kind, ref_slug=ref_slug,
                                            title=title, notes=""))
        db.session.commit()

    if SavedDestination.query.count() == 0 and bench_users:
        saved_specs = [
            ("alice.j@test.com", ["yosemite-national-park", "muir-woods-national-monument", "rocky-mountain-national-park"]),
            ("bob.c@test.com", ["olympic-national-park", "mount-rainier-national-park", "vermilion-cliffs-national-monument"]),
            ("carol.d@test.com", ["rocky-mountain-national-park", "grand-teton-national-park", "arches-national-park"]),
            ("david.k@test.com", ["everglades-national-park", "great-smoky-mountains-national-park", "acadia-national-park"]),
        ]
        for email, slugs in saved_specs:
            user = bench_users.get(email)
            if not user:
                continue
            for slug in slugs:
                if Destination.query.filter_by(slug=slug).first():
                    db.session.add(SavedDestination(user_id=user.id, destination_slug=slug))
        db.session.commit()

    if LotteryEntry.query.count() == 0 and bench_users:
        entry_specs = [
            ("alice.j@test.com", "half-dome-cable-route-lottery", 2, "2026-07-12"),
            ("bob.c@test.com", "enchantments-overnight-lottery", 4, "2026-08-04"),
            ("bob.c@test.com", "mount-whitney-day-hike-lottery", 3, "2026-08-10"),
            ("carol.d@test.com", "rocky-bear-lake-lottery", 4, "2026-07-22"),
            ("david.k@test.com", "alcatraz-night-tour-lottery", 4, "2026-10-31"),
        ]
        for idx, (email, slug, party, pref) in enumerate(entry_specs, start=1):
            user = bench_users.get(email)
            lottery = Lottery.query.filter_by(slug=slug).first()
            if not (user and lottery):
                continue
            db.session.add(LotteryEntry(
                user_id=user.id, lottery_id=lottery.id, group_size=party,
                preferred_date=pref, alternate_date=lottery.deadline,
                zone="", notes="", status="Entered",
                confirmation_code=f"LOT-{lottery.id:03d}-FIX{idx:03d}"
            ))
        db.session.commit()

    if PermitApplication.query.count() == 0 and bench_users:
        permit_app_specs = [
            ("alice.j@test.com", "yosemite-wilderness-permit", 3, "2026-07-15", "2026-07-18", "Happy Isles"),
            ("bob.c@test.com", "inyo-mt-whitney-trail-permit", 2, "2026-08-04", "2026-08-06", "Whitney Portal"),
            ("carol.d@test.com", "canyonlands-overnight-permit", 2, "2026-09-10", "2026-09-12", "The Maze"),
            ("david.k@test.com", "cumberland-island-camping-permit", 4, "2026-09-17", "2026-09-19", "Sea Camp"),
        ]
        for idx, (email, slug, party, start, end, head) in enumerate(permit_app_specs, start=1):
            user = bench_users.get(email)
            permit = Permit.query.filter_by(slug=slug).first()
            if not (user and permit):
                continue
            db.session.add(PermitApplication(
                user_id=user.id, permit_id=permit.id, party_size=party,
                entry_date=start, exit_date=end, trailhead=head,
                emergency_contact="Trip emergency contact on file",
                status="Submitted",
                confirmation_code=f"PERMIT-{permit.id:03d}-FIX{idx:03d}",
            ))
        db.session.commit()

    # ------------------------------------------------------------------
    # 2026-05-28 priority-deepen seed: tour_booking / check_in /
    # gear_checklist / condition_report / reservation_modification /
    # timed_entry_reservation / alert_subscription / group_reservation_request
    # ------------------------------------------------------------------
    TourBooking = _BOUND["TourBooking"]
    CheckIn = _BOUND["CheckIn"]
    GearChecklist = _BOUND["GearChecklist"]
    ConditionReport = _BOUND["ConditionReport"]
    ReservationModification = _BOUND["ReservationModification"]
    TimedEntryReservation = _BOUND["TimedEntryReservation"]
    AlertSubscription = _BOUND["AlertSubscription"]
    GroupReservationRequest = _BOUND["GroupReservationRequest"]

    if TourBooking.query.count() == 0 and bench_users:
        booking_specs = [
            ("alice.j@test.com", "alcatraz-day-tour", 2, "2026-06-15 10:00"),
            ("alice.j@test.com", "sf-maritime-hyde-street-tour", 3, "2026-07-11 13:00"),
            ("bob.c@test.com", "yosemite-grand-tour-bus", 4, "2026-08-02 09:00"),
            ("carol.d@test.com", "jenny-lake-shuttle-boat", 2, "2026-07-22 10:30"),
            ("carol.d@test.com", "wind-cave-fairgrounds-tour", 3, "2026-07-23 11:00"),
            ("david.k@test.com", "dry-tortugas-ferry-day-trip", 2, "2026-09-18 08:00"),
            ("david.k@test.com", "biscayne-heritage-tour", 4, "2026-09-19 09:30"),
        ]
        for idx, (email, slug, party, when) in enumerate(booking_specs, start=1):
            user = bench_users.get(email)
            tour = Tour.query.filter_by(slug=slug).first()
            if not (user and tour):
                continue
            db.session.add(TourBooking(
                user_id=user.id, tour_id=tour.id, party_size=party,
                session_time=when, status="Booked",
                confirmation_code=f"TOUR-{tour.id:03d}-FIX{idx:03d}",
            ))
        db.session.commit()

    if CheckIn.query.count() == 0 and bench_users:
        checkin_specs = [
            ("RG-2026-AJ01", 2, "RVR-4823", "Arrived 4 PM, set up at site 12 of the Coast Camp loop."),
            ("RG-2026-BC01", 3, "WTH-7188", "Picked up bear canister from ranger station before sundown."),
            ("RG-2026-CD01", 4, "FRD-2210", "Late check-in approved; quiet hours acknowledged."),
            ("RG-2026-DK01", 2, "HND-0331", "Completed stay, returned permit slip on departure."),
        ]
        for code, party, plate, note in checkin_specs:
            reservation = Reservation.query.filter_by(confirmation_code=code).first()
            if not reservation:
                continue
            db.session.add(CheckIn(
                user_id=reservation.user_id, reservation_id=reservation.id,
                party_count=party, vehicle_plate=plate, notes=note,
            ))
        db.session.commit()

    if GearChecklist.query.count() == 0 and bench_users:
        checklist_specs = [
            ("alice.j@test.com", "backpacking",
             ["Internal-frame backpack 50-65L", "Sleeping bag rated to 20F", "Inflatable sleeping pad",
              "Two-person backpacking tent", "Bear-resistant food canister", "Headlamp + extra batteries",
              "Water filter or purifier", "Trekking poles"]),
            ("alice.j@test.com", "day-hiking",
             ["20-30L daypack", "Reusable water bottles or hydration bladder", "Snack and lunch supplies",
              "Layered clothing", "Sun hat and sunscreen", "First-aid kit"]),
            ("bob.c@test.com", "backcountry-skiing",
             ["Backcountry skis with bindings", "Climbing skins", "Avalanche beacon",
              "Probe (240cm+)", "Snow shovel", "Helmet", "Insulated layering kit", "Emergency bivy"]),
            ("carol.d@test.com", "car-camping",
             ["Family-sized tent", "Sleeping bags rated to 30F", "Camp stove + fuel canister",
              "Cooler with ice packs", "Folding camp chairs", "LED lantern", "Camp kitchen tote"]),
            ("david.k@test.com", "paddling",
             ["PFD (Coast Guard approved)", "Spare paddle", "Dry bags", "Bilge pump or sponge",
              "Whistle and signaling mirror", "Sun shirt with UPF rating", "Wide-brim hat"]),
            ("david.k@test.com", "fishing",
             ["Fly or spinning rod", "Reel matched to rod weight", "Polarized sunglasses",
              "Tackle box", "Net (wood or rubber)", "Required state permit"]),
        ]
        for email, category, items in checklist_specs:
            user = bench_users.get(email)
            gear = GearList.query.filter_by(category=category).first()
            if not (user and gear):
                continue
            db.session.add(GearChecklist(
                user_id=user.id, category=gear.category,
                items_json=json.dumps(items),
            ))
        db.session.commit()

    if ConditionReport.query.count() == 0 and bench_users:
        report_specs = [
            ("alice.j@test.com", "point-reyes-national-seashore-campground", "trail", "advisory",
             "Sky Trail is muddy after recent rain; consider trekking poles past the Stewart Trail junction."),
            ("alice.j@test.com", "pinnacles-campground", "wildlife", "advisory",
             "Bobcat sighted near Loop B at dusk. Keep food locked in bear boxes overnight."),
            ("bob.c@test.com", "oak-knoll-campground", "facility", "warning",
             "Vault toilet at site 6 is locked for repairs; portable replacement near the ranger station."),
            ("bob.c@test.com", "lake-sonoma-boat-in-sites", "water", "warning",
             "Lake levels are low; boat launch is steep and rocky. Confirm draft before launching."),
            ("carol.d@test.com", "glory-hole-recreation-area", "access", "advisory",
             "Lower trail from the boat-in sites has a fallen oak blocking the path."),
            ("carol.d@test.com", "aquatic-park-cove-overnight-anchoring", "facility", "advisory",
             "Mooring buoys 3 and 5 are missing tags; verify with harbormaster before tying off."),
            ("david.k@test.com", "pinnacles-campground", "trail", "advisory",
             "Bear Gulch Cave west entrance flooded; expect detour via the Rim Trail."),
        ]
        for email, slug, category, severity, body in report_specs:
            user = bench_users.get(email)
            facility = Facility.query.filter_by(slug=slug).first()
            if not (user and facility):
                continue
            db.session.add(ConditionReport(
                user_id=user.id, facility_id=facility.id,
                category=category, severity=severity, body=body,
            ))
        db.session.commit()

    if ReservationModification.query.count() == 0 and bench_users:
        mod_specs = [
            ("RG-2026-AJ02", "2026-07-03", "2026-07-05", "2026-07-10", "2026-07-12",
             "Extended for an additional family member arriving late."),
            ("RG-2026-BC01", "2026-08-11", "2026-08-14", "2026-08-13", "2026-08-16",
             "Shifted to align with the Cascade backcountry permit window."),
            ("RG-2026-CD01", "2026-05-20", "2026-05-22", "2026-05-21", "2026-05-23",
             "Weather-related single-day shift requested by visitor."),
            ("RG-2026-AJ01", "2026-06-12", "2026-06-14", "2026-06-13", "2026-06-15",
             "Group adjusted arrival because of road closure on Hwy 1."),
        ]
        for code, old_s, old_e, new_s, new_e, reason in mod_specs:
            reservation = Reservation.query.filter_by(confirmation_code=code).first()
            if not reservation:
                continue
            db.session.add(ReservationModification(
                reservation_id=reservation.id, user_id=reservation.user_id,
                previous_start_date=old_s, previous_end_date=old_e,
                new_start_date=new_s, new_end_date=new_e, reason=reason,
            ))
        db.session.commit()

    if TimedEntryReservation.query.count() == 0 and bench_users:
        te_specs = [
            ("alice.j@test.com", "yosemite-firefall", "2026-02-22", "07:00 - 09:00", "8KJL231", 4),
            ("alice.j@test.com", "muir-woods-parking", "2026-06-04", "10:00 - 12:00", "CA-7TR-993", 3),
            ("bob.c@test.com", "rocky-mountain", "2026-07-18", "06:00 - 08:00", "OR-A8821", 3),
            ("bob.c@test.com", "glacier-gtsr", "2026-08-09", "06:00 - 08:00", "MT-G-5512", 2),
            ("carol.d@test.com", "arches", "2026-07-22", "07:00 - 09:00", "CO-NM-9912", 4),
            ("carol.d@test.com", "zion-angels-landing", "2026-07-24", "09:00 - 11:00", "UT-AL-3320", 2),
            ("david.k@test.com", "haleakala-sunrise", "2026-09-15", "03:00 - 07:00", "HI-PLR-3344", 2),
            ("david.k@test.com", "acadia-cadillac", "2026-09-20", "05:30 - 07:30", "ME-AC-4012", 3),
        ]
        for idx, (email, park_slug, when, window, plate, party) in enumerate(te_specs, start=1):
            user = bench_users.get(email)
            park = TimedEntryPark.query.filter_by(slug=park_slug).first()
            if not (user and park):
                continue
            db.session.add(TimedEntryReservation(
                user_id=user.id, park_slug=park.slug,
                entry_date=when, entry_window=window,
                vehicle_plate=plate, party_size=party,
                confirmation_code=f"TE-{park.slug[:6].upper()}-FIX{idx:03d}",
            ))
        db.session.commit()

    if AlertSubscription.query.count() == 0 and bench_users:
        sub_specs = [
            ("alice.j@test.com", "yosemite-firefall-window"),
            ("alice.j@test.com", "muir-woods-shuttle"),
            ("bob.c@test.com", "glacier-going-to-sun-closure"),
            ("bob.c@test.com", "wave-lottery-window-changes"),
            ("carol.d@test.com", "rocky-bear-lake-corridor"),
            ("carol.d@test.com", "arches-timed-entry"),
            ("david.k@test.com", "dry-tortugas-ferry-cap"),
            ("david.k@test.com", "everglades-shark-valley-trams"),
        ]
        for email, slug in sub_specs:
            user = bench_users.get(email)
            alert = Alert.query.filter_by(slug=slug).first()
            if not (user and alert):
                continue
            db.session.add(AlertSubscription(
                user_id=user.id, alert_slug=alert.slug,
                notify_email=True, notify_sms=False,
            ))
        db.session.commit()

    if GroupReservationRequest.query.count() == 0 and bench_users:
        req_specs = [
            ("alice.j@test.com", "rob-hill-group-campground", 28, "2026-08-15",
             "Family reunion overnight stay, requesting fire ring access."),
            ("bob.c@test.com", "twin-creek-group-camping", 42, "2026-09-12",
             "Scout troop weekend, will bring own potable water."),
            ("carol.d@test.com", "catoctin-mountain-group-pavilion", 60, "2026-07-04",
             "Birthday picnic + pavilion booking for extended family."),
            ("david.k@test.com", "everglades-flamingo-group-site", 24, "2026-12-19",
             "Photography club seasonal retreat tied to wildlife migration window."),
        ]
        for idx, (email, slug, party, when, notes) in enumerate(req_specs, start=1):
            user = bench_users.get(email)
            group = GroupReservation.query.filter_by(slug=slug).first()
            if not (user and group):
                continue
            db.session.add(GroupReservationRequest(
                user_id=user.id, group_id=group.id,
                party_size=party, event_date=when,
                notes=notes, status="Submitted",
                confirmation_code=f"GROUP-{group.id:03d}-FIX{idx:03d}",
            ))
        db.session.commit()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def normalize_seed_db_layout() -> None:
    """Re-emit indexes in alpha order + VACUUM (gotcha §2)."""
    from sqlalchemy import text
    db = _BOUND["db"]
    conn = db.engine.connect()
    idx_rows = conn.execute(text(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%'"
    )).fetchall()
    for name, _ in idx_rows:
        conn.execute(text(f"DROP INDEX IF EXISTS {name}"))
    for name, sql in sorted(idx_rows, key=lambda r: r[0]):
        if sql:
            conn.execute(text(sql))
    conn.execute(text("VACUUM"))
    conn.commit()


def register(app) -> None:
    """Late-import everything from app and wire models + routes."""
    from app import (app as host_app, db,
                     User, Facility, Campsite, Review, Address, PaymentMethod,
                     SavedItem, CartItem, Reservation)
    _BOUND.update({
        "app": host_app, "db": db,
        "User": User, "Facility": Facility, "Campsite": Campsite, "Review": Review,
        "Address": Address, "PaymentMethod": PaymentMethod,
        "SavedItem": SavedItem, "CartItem": CartItem, "Reservation": Reservation,
    })
    _define_models()
    _register_routes(app)
