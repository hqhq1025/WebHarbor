"""Seed data for the Recreation.gov mirror.

The seed functions are deliberately gated at the function level. Re-running
them against a populated DB must be a no-op so /reset/recreation_gov remains
byte-identical to instance_seed/recreation_gov.db.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal

PASSWORD = "TestPass123!"

IMAGE_POOL = [
    "015-point-reyes-national-seashore.webp",
    "016-pinnacles-national-park.webp",
    "018-preview-photo-of-outflow-camping.webp",
    "019-preview-photo-of-brooks-camp-camping-permit.webp",
    "020-preview-photo-of-mammoth-cave-backcountry-camping.webp",
    "021-preview-photo-of-spinreel-sand-camping.webp",
    "022-preview-photo-of-ausable-river-camping.webp",
    "023-preview-photo-of-umpqua-sand-camping.webp",
    "024-preview-photo-of-basin-cove-backcountry-camping.webp",
    "025-preview-photo-of-horsfall-sand-camping.webp",
    "026-preview-photo-of-bluff-hike-in-camping.webp",
    "027-preview-photo-of-cumberland-island-national-seashore-camping-permits.webp",
    "028-preview-photo-of-voyageurs-national-park-camping-permits.webp",
    "029-preview-photo-of-siltcoos-sand-camping.webp",
    "030-preview-photo-of-hauser-sand-camping.webp",
    "031-preview-photo-of-dale-hollow-lake-primitive-camping.webp",
    "032-preview-photo-of-rock-castle-gorge-backcountry-camping.webp",
    "033-preview-photo-of-johns-river-road-backcountry-camping.webp",
    "034-preview-photo-of-twin-creek-campground-group-camping-site.webp",
    "035-preview-photo-of-big-bend-backcountry-camping.webp",
    "036-preview-photo-of-sylvania-wilderness-backcountry-camping.webp",
    "037-preview-photo-of-winhall-brook-camping-area.webp",
    "038-preview-photo-of-santa-rosa-island-backcountry-beach-camping.webp",
    "039-preview-photo-of-apostle-islands-national-lakeshore-camping-permits.webp",
    "040-preview-photo-of-calpine-lookout.webp",
    "041-preview-photo-of-okefenokee-national-wildlife-refuge-overnight-camping.webp",
    "042-preview-photo-of-chopawamsic-backcountry-camping-permits.webp",
    "043-preview-photo-of-chilkoot-trail-camping-permits.webp",
    "044-preview-photo-of-delta-national-forest-camping.webp",
    "045-preview-photo-of-south-jetty-sand-camping.webp",
    "046-preview-photo-of-pictured-rocks-national-lakeshore-backcountry-camping.webp",
    "047-preview-photo-of-manzanita-lake-camping-cabins-ca.webp",
    "048-preview-photo-of-center-hill-lake-primitive-camping-areas.webp",
    "049-preview-photo-of-canning-creek.webp",
    "050-preview-photo-of-lake-powhatan-glamping.webp",
    "051-preview-photo-of-bumping-lake-campground.webp",
    "052-preview-photo-of-death-valley-backcountry-roadside-camping.webp",
    "053-preview-photo-of-mill-creek-camping-berlin-lake.webp",
    "054-preview-photo-of-sherando-lake-recreation-area-family-camping.webp",
    "055-preview-photo-of-katahdin-woods-waters-national-monument-camping.webp",
    "056-preview-photo-of-samsing-cove-cabin.webp",
    "057-preview-photo-of-rampart-range-recreation-area-designated-dispersed-ca.webp",
    "058-preview-photo-of-soda-springs-campground-bumping-river-wa.webp",
    "059-preview-photo-of-cedro-peak-camping-sites-robin-and-jay.webp",
    "060-preview-photo-of-mt-whitney.webp",
    "061-preview-photo-of-enchantment-permit-area-advanced-lottery.webp",
    "062-preview-photo-of-desolation-wilderness-permit.webp",
    "063-preview-photo-of-yellowstone-national-park-backcountry-permits.webp",
    "064-preview-photo-of-canyonlands-national-park-overnight-backcountry-permi.webp",
    "065-preview-photo-of-fire-island-national-seashore-permits.webp",
    "066-preview-photo-of-hemlock-cabin.webp",
    "067-preview-photo-of-inyo-national-forest-wilderness-permits.webp",
    "068-preview-photo-of-mount-margaret-backcountry.webp",
    "069-preview-photo-of-aravaipa-canyon-wilderness-permits.webp",
    "070-preview-photo-of-central-cascades-wilderness-overnight-permits.webp",
    "071-preview-photo-of-charon-s-garden.webp",
    "072-preview-photo-of-tilly-jane-a-frame.webp",
]

IMAGE_OVERRIDES = {
    "Aquatic Park Cove Overnight Anchoring": "real-aquatic-park-cove.webp",
    "Point Reyes National Seashore Campground": "real-point-reyes-campground.webp",
    "Pinnacles Campground": "real-pinnacles-campground.webp",
    "Oak Knoll Campground": "real-oak-knoll-campground.webp",
    "Glory Hole Recreation Area": "real-glory-hole.webp",
    "Lake Sonoma Boat-In Sites": "real-lake-sonoma-boat-in.webp",
    "San Francisco Maritime Historic Park Tours": "real-sf-maritime-tours.webp",
    "Fort Point National Historic Site Tours": "real-fort-point-tours.webp",
}

BASE_FACILITIES = [
    ("Point Reyes National Seashore Campground", "camping", "NPS", "Point Reyes National Seashore", "Olema", "CA", 37, 30, "night", 4.8, 1175, True, True, ["Camping", "Hiking", "Wildlife Viewing"], ["Accessible Sites", "Tent Pads", "Drinking Water"]),
    ("Pinnacles Campground", "camping", "NPS", "Pinnacles National Park", "Paicines", "CA", 72, 39, "night", 4.7, 3682, True, True, ["Camping", "Stargazing", "Climbing"], ["Accessible Sites", "RV Hookups", "Showers"]),
    ("Kirby Cove Campground", "camping", "NPS", "Golden Gate National Recreation Area", "Sausalito", "CA", 43, 50, "night", 4.6, 612, True, False, ["Camping", "Beach", "Photography"], ["Tent Pads", "Picnic Tables", "Vault Toilets"]),
    ("Rob Hill Group Campground", "camping", "Presidio Trust", "Presidio of San Francisco", "San Francisco", "CA", 42, 105, "night", 4.5, 28, True, True, ["Group Camping", "Urban Parks", "Hiking"], ["Accessible Sites", "Group Fire Ring", "Restrooms"]),
    ("Aquatic Park Cove Overnight Anchoring", "camping", "NPS", "San Francisco Maritime National Historical Park", "San Francisco", "CA", 41, 10, "night", 4.2, 55, True, False, ["Boating", "Sailing", "Historic Sites"], ["Anchoring Permit", "Waterfront Access"]),
    ("Arroyo Seco", "camping", "USFS", "Los Padres National Forest", "Greenfield", "CA", 112, 35, "night", 4.4, 234, True, False, ["Camping", "Swimming", "Hiking"], ["River Access", "Picnic Tables", "Vault Toilets"]),
    ("Oak Knoll Campground", "camping", "USACE", "New Hogan Lake", "Valley Springs", "CA", 94, 28, "night", 4.1, 59, True, False, ["Camping", "Boating", "Fishing"], ["Boat Ramp", "Picnic Tables", "Dump Station"]),
    ("Glory Hole Recreation Area", "camping", "USACE", "New Melones Lake", "Angels Camp", "CA", 118, 34, "night", 4.4, 437, True, True, ["Camping", "Fishing", "Boating"], ["Accessible Sites", "Marina", "Showers"]),
    ("Yosemite Creek Campground", "camping", "NPS", "Yosemite National Park", "Yosemite National Park", "CA", 2, 24, "night", 4.6, 811, True, False, ["Camping", "Waterfalls", "Hiking"], ["Creek Access", "Tent Pads", "Vault Toilets"]),
    ("Porcupine Flat Campground", "camping", "NPS", "Yosemite National Park", "Yosemite National Park", "CA", 16, 20, "night", 4.3, 267, False, False, ["Camping", "Hiking", "Scenic Drives"], ["Tent Pads", "Vault Toilets"]),
    ("Manzanita Lake Camping Cabins", "camping", "NPS", "Lassen Volcanic National Park", "Mineral", "CA", 204, 76, "night", 4.8, 512, True, True, ["Cabins", "Lake", "Volcanoes"], ["Accessible Cabins", "Camp Store", "Showers"]),
    ("Lake Powhatan Glamping", "camping", "USFS", "National Forests in North Carolina", "Asheville", "NC", 2510, 99, "night", 4.7, 180, True, True, ["Glamping", "Mountain Biking", "Lake"], ["Canvas Tents", "Accessible Sites", "Showers"]),
    ("Mammoth Cave Backcountry Camping", "camping", "NPS", "Mammoth Cave National Park", "Mammoth Cave", "KY", 2280, 10, "permit", 4.6, 422, True, False, ["Backcountry Camping", "Caves", "Hiking"], ["Permit Required", "Primitive Sites"]),
    ("Big Bend Backcountry Camping", "camping", "NPS", "Big Bend National Park", "Big Bend National Park", "TX", 1650, 16, "permit", 4.5, 650, True, False, ["Backcountry Camping", "Desert", "Stargazing"], ["Permit Required", "Primitive Sites"]),
    ("Death Valley Backcountry Roadside Camping", "camping", "NPS", "Death Valley National Park", "Death Valley", "CA", 505, 0, "permit", 4.3, 344, True, False, ["Backcountry Camping", "Desert", "Scenic Drives"], ["Free Permit", "High Clearance Routes"]),
    ("Sherando Lake Family Camping", "camping", "USFS", "George Washington and Jefferson National Forests", "Lyndhurst", "VA", 2670, 32, "night", 4.7, 495, True, True, ["Camping", "Swimming", "Hiking"], ["Accessible Sites", "Beach", "Showers"]),
    ("Tilly Jane A-Frame", "camping", "USFS", "Mt. Hood National Forest", "Parkdale", "OR", 620, 90, "night", 4.9, 91, True, False, ["Cabins", "Skiing", "Hiking"], ["Wood Stove", "Bunk Beds", "Trail Access"]),
    ("Hemlock Cabin", "camping", "USFS", "Tongass National Forest", "Sitka", "AK", 1750, 65, "night", 4.8, 64, True, False, ["Cabins", "Fishing", "Wildlife Viewing"], ["Cabin", "Boat Access", "Wood Stove"]),
    ("Yosemite National Park Wilderness Permits", "permits", "NPS", "Yosemite National Park", "Yosemite National Park", "CA", 2, 10, "permit", 4.7, 1047, True, False, ["Wilderness", "Backpacking", "Half Dome"], ["Quota Permit", "Bear Canister Required"]),
    ("Mt. Whitney", "permits", "USFS", "Inyo National Forest", "Lone Pine", "CA", 331, 15, "permit", 4.8, 891, True, False, ["Hiking", "Wilderness", "Summit"], ["Lottery", "Quota Permit", "Day Use"]),
    ("Enchantment Permit Area Advanced Lottery", "lottery", "USFS", "Okanogan-Wenatchee National Forest", "Leavenworth", "WA", 835, 6, "permit", 4.9, 763, True, False, ["Lottery", "Backpacking", "Alpine Lakes"], ["Advanced Lottery", "Quota Permit"]),
    ("Desolation Wilderness Permit", "permits", "USFS", "Eldorado National Forest", "South Lake Tahoe", "CA", 214, 10, "permit", 4.7, 386, True, False, ["Wilderness", "Backpacking", "Lakes"], ["Quota Permit", "Overnight Permit"]),
    ("Yellowstone National Park Backcountry Permits", "permits", "NPS", "Yellowstone National Park", "Yellowstone National Park", "WY", 0, 10, "permit", 4.6, 253, True, False, ["Backcountry", "Wildlife Viewing", "Fishing"], ["Bear Safety", "Permit Required"]),
    ("Canyonlands Overnight Backcountry Permits", "permits", "NPS", "Canyonlands National Park", "Moab", "UT", 780, 36, "permit", 4.8, 318, True, False, ["Backcountry", "Canyons", "4x4"], ["Vehicle Permit", "Overnight Permit"]),
    ("Fire Island National Seashore Permits", "permits", "NPS", "Fire Island National Seashore", "Patchogue", "NY", 2980, 25, "permit", 4.4, 88, True, False, ["Beach", "Permits", "Wildlife Viewing"], ["Driving Permit", "Seasonal Rules"]),
    ("Inyo National Forest Wilderness Permits", "permits", "USFS", "Inyo National Forest", "Bishop", "CA", 340, 6, "permit", 4.7, 912, True, False, ["Wilderness", "Backpacking", "Fishing"], ["Quota Permit", "Trailhead Entry"]),
    ("Aravaipa Canyon Wilderness Permits", "permits", "BLM", "Aravaipa Canyon Wilderness", "Winkelman", "AZ", 742, 5, "permit", 4.6, 179, True, False, ["Canyons", "Hiking", "Wildlife Viewing"], ["Day Use Permit", "Overnight Permit"]),
    ("Central Cascades Wilderness Overnight Permits", "permits", "USFS", "Willamette National Forest", "Bend", "OR", 590, 6, "permit", 4.5, 248, True, False, ["Wilderness", "Backpacking", "Lakes"], ["Quota Permit", "Trailhead Entry"]),
    ("Voyageurs National Park Tours", "tickets", "NPS", "Voyageurs National Park", "International Falls", "MN", 0, 40, "ticket", 4.8, 522, True, True, ["Tours", "Boating", "Wildlife Viewing"], ["Accessible Seating", "Ranger Program"]),
    ("Mariposa Grove Commercial Bus Parking", "tickets", "NPS", "Yosemite National Park", "Fish Camp", "CA", 24, 25, "ticket", 4.2, 8, True, True, ["Timed Entry", "Shuttles", "Giant Sequoias"], ["Timed Entry", "Commercial Vehicle"]),
    ("San Francisco Maritime Historic Park Tours", "tickets", "NPS", "San Francisco Maritime National Historical Park", "San Francisco", "CA", 42, 15, "ticket", 4.5, 133, True, True, ["Tours", "Historic Ships", "Waterfront"], ["Accessible Route", "Ranger Program"]),
    ("Fort Point National Historic Site Tours", "tickets", "NPS", "Golden Gate National Recreation Area", "San Francisco", "CA", 45, 12, "ticket", 4.4, 96, True, True, ["Tours", "History", "Photography"], ["Accessible Route", "Timed Entry"]),
    ("Voyageurs Winter Equipment Rentals", "tickets", "NPS", "Voyageurs National Park", "Kabetogama", "MN", 0, 20, "ticket", 4.1, 6, True, False, ["Equipment Rentals", "Skiing", "Snowshoeing"], ["Rental Window", "Winter Access"]),
    ("Campbell Creek Science Center Public Programs", "tickets", "BLM", "Campbell Tract", "Anchorage", "AK", 3110, 8, "ticket", 4.4, 42, True, True, ["Education", "Wildlife Viewing", "Family Programs"], ["Accessible Route", "Indoor Program"]),
    ("Yellowstone National Park Fishing Permit", "passes", "NPS", "Yellowstone National Park", "Yellowstone National Park", "WY", 0, 20, "pass", 4.7, 637, True, False, ["Fishing", "Activity Pass", "Rivers"], ["Digital Pass", "Seasonal Rules"]),
    ("Denali National Park Site Pass", "passes", "NPS", "Denali National Park and Preserve", "Healy", "AK", 0, 15, "pass", 4.6, 501, True, True, ["Site Pass", "Scenic Drives", "Wildlife Viewing"], ["Digital Pass", "Accessible Visitor Center"]),
    ("Yosemite National Park Site Pass", "passes", "NPS", "Yosemite National Park", "Yosemite National Park", "CA", 0, 35, "pass", 4.8, 2410, True, True, ["Site Pass", "Waterfalls", "Hiking"], ["Digital Pass", "Entrance Station"]),
    ("Grand Teton National Park Site Pass", "passes", "NPS", "Grand Teton National Park", "Moose", "WY", 7, 35, "pass", 4.8, 1312, True, True, ["Site Pass", "Mountains", "Wildlife Viewing"], ["Digital Pass", "Entrance Station"]),
    ("Rocky Mountain National Park Timed Entry", "passes", "NPS", "Rocky Mountain National Park", "Estes Park", "CO", 1010, 2, "pass", 4.6, 1852, True, True, ["Timed Entry", "Scenic Drives", "Hiking"], ["Timed Entry", "Park Access"]),
    ("Zion Canyon Shuttle Tickets", "tickets", "NPS", "Zion National Park", "Springdale", "UT", 690, 1, "ticket", 4.5, 830, False, True, ["Shuttle", "Canyons", "Hiking"], ["Timed Entry", "Accessible Seating"]),
    ("Muir Woods Parking and Shuttle", "day_use", "NPS", "Muir Woods National Monument", "Mill Valley", "CA", 32, 9, "ticket", 4.6, 2094, True, True, ["Day Use", "Redwoods", "Shuttle"], ["Parking Reservation", "Accessible Parking"]),
    ("Crescent Moon Picnic Site", "day_use", "USFS", "Coconino National Forest", "Sedona", "AZ", 790, 12, "day", 4.5, 420, True, True, ["Day Use", "Picnicking", "Photography"], ["Picnic Tables", "Creek Access"]),
    ("Lake Sonoma Boat-In Sites", "camping", "USACE", "Lake Sonoma", "Geyserville", "CA", 97, 20, "night", 4.5, 133, True, False, ["Boat-In Camping", "Fishing", "Boating"], ["Boat Access", "Primitive Sites"]),
    ("Cumberland Island Camping Permits", "permits", "NPS", "Cumberland Island National Seashore", "St Marys", "GA", 2830, 12, "permit", 4.8, 412, True, False, ["Beach Camping", "Wilderness", "Wildlife Viewing"], ["Ferry Access", "Permit Required"]),
    ("Apostle Islands Camping Permits", "permits", "NPS", "Apostle Islands National Lakeshore", "Bayfield", "WI", 2160, 15, "permit", 4.7, 289, True, False, ["Island Camping", "Kayaking", "Lakes"], ["Permit Required", "Primitive Sites"]),
]

EXTRA_NAMES = [
    ("Bumping Lake Campground", "camping", "USFS", "Okanogan-Wenatchee National Forest", "Naches", "WA", ["Camping", "Lake", "Fishing"]),
    ("Soda Springs Campground", "camping", "USFS", "Bumping River", "Naches", "WA", ["Camping", "River", "Hiking"]),
    ("Rampart Range Designated Dispersed Camping", "camping", "USFS", "Pike-San Isabel National Forest", "Woodland Park", "CO", ["Camping", "OHV", "Forest"]),
    ("Cedro Peak Robin and Jay Sites", "camping", "USFS", "Cibola National Forest", "Tijeras", "NM", ["Camping", "Mountain Biking", "Forest"]),
    ("Okefenokee Overnight Camping Permit", "permits", "FWS", "Okefenokee National Wildlife Refuge", "Folkston", "GA", ["Permits", "Paddling", "Wildlife Viewing"]),
    ("Chilkoot Trail Camping Permits", "permits", "NPS", "Klondike Gold Rush National Historical Park", "Skagway", "AK", ["Permits", "Backpacking", "History"]),
    ("Calpine Lookout", "camping", "USFS", "Tahoe National Forest", "Calpine", "CA", ["Cabins", "Lookout", "Stargazing"]),
    ("Samsing Cove Cabin", "camping", "USFS", "Tongass National Forest", "Petersburg", "AK", ["Cabins", "Fishing", "Boat Access"]),
    ("Chopawamsic Backcountry Permits", "permits", "NPS", "Prince William Forest Park", "Triangle", "VA", ["Permits", "Backcountry", "Hiking"]),
    ("Mount Margaret Backcountry", "permits", "USFS", "Gifford Pinchot National Forest", "Toutle", "WA", ["Permits", "Volcanoes", "Backpacking"]),
    ("Charon's Garden Wilderness Permit", "permits", "FWS", "Wichita Mountains Wildlife Refuge", "Cache", "OK", ["Permits", "Climbing", "Wildlife Viewing"]),
    ("South Jetty Sand Camping", "camping", "USFS", "Siuslaw National Forest", "Florence", "OR", ["Camping", "Sand Dunes", "OHV"]),
    ("Delta National Forest Camping", "camping", "USFS", "Delta National Forest", "Rolling Fork", "MS", ["Camping", "Hunting", "Fishing"]),
    ("Center Hill Primitive Camping Areas", "camping", "USACE", "Center Hill Lake", "Lancaster", "TN", ["Camping", "Lake", "Boating"]),
    ("Canning Creek", "camping", "USACE", "Council Grove Lake", "Council Grove", "KS", ["Camping", "Fishing", "Boating"]),
    ("Mill Creek Camping", "camping", "USACE", "Berlin Lake", "Berlin Center", "OH", ["Camping", "Lake", "Family"]),
    ("Santa Rosa Island Backcountry Beach Camping", "camping", "NPS", "Channel Islands National Park", "Ventura", "CA", ["Camping", "Beach", "Island"]),
    ("Sylvania Wilderness Backcountry Camping", "camping", "USFS", "Ottawa National Forest", "Watersmeet", "MI", ["Camping", "Canoeing", "Wilderness"]),
    ("Brooks Camp Camping Permit", "camping", "NPS", "Katmai National Park & Preserve", "King Salmon", "AK", ["Camping", "Bear Viewing", "Fishing"]),
    ("Umpqua Sand Camping", "camping", "USFS", "Siuslaw National Forest", "Reedsport", "OR", ["Camping", "Sand Dunes", "OHV"]),
    ("Siltcoos Sand Camping", "camping", "USFS", "Oregon Dunes National Recreation Area", "Florence", "OR", ["Camping", "Sand Dunes", "ATV"]),
    ("Hauser Sand Camping", "camping", "USFS", "Oregon Dunes National Recreation Area", "North Bend", "OR", ["Camping", "OHV", "Beach"]),
    ("Horsfall Sand Camping", "camping", "USFS", "Oregon Dunes National Recreation Area", "North Bend", "OR", ["Camping", "Sand Dunes", "Beach"]),
    ("Bluff Hike-In Camping", "camping", "NPS", "Cumberland Island National Seashore", "St Marys", "GA", ["Camping", "Beach", "Hiking"]),
    ("Pictured Rocks Backcountry Camping", "camping", "NPS", "Pictured Rocks National Lakeshore", "Munising", "MI", ["Camping", "Kayaking", "Hiking"]),
    ("Katahdin Woods Waters Monument Camping", "camping", "NPS", "Katahdin Woods and Waters National Monument", "Patten", "ME", ["Camping", "Stargazing", "Paddling"]),
    ("Berlin Lake Shoreline Camping", "camping", "USACE", "Berlin Lake", "Berlin Center", "OH", ["Camping", "Fishing", "Family"]),
    ("Ausable River Camping", "camping", "NPS", "Pictured Rocks National Lakeshore", "Grand Marais", "MI", ["Camping", "River", "Hiking"]),
    ("Rock Castle Gorge Backcountry Camping", "permits", "NPS", "Blue Ridge Parkway", "Mabry Mill", "VA", ["Backpacking", "Waterfalls", "Hiking"]),
    ("Johns River Road Backcountry Camping", "permits", "NPS", "Blue Ridge Parkway", "Blowing Rock", "NC", ["Backpacking", "Forest", "Hiking"]),
    ("Voyageurs Island Campsites", "camping", "NPS", "Voyageurs National Park", "International Falls", "MN", ["Boat-In Camping", "Fishing", "Paddling"]),
    ("Okefenokee Canal Run Camping", "permits", "FWS", "Okefenokee National Wildlife Refuge", "Folkston", "GA", ["Paddling", "Wildlife Viewing", "Camping"]),
    ("Basin Cove Backcountry Camping", "camping", "NPS", "Acadia National Park", "Bar Harbor", "ME", ["Camping", "Island", "Hiking"]),
    ("Dale Hollow Primitive Camping", "camping", "USACE", "Dale Hollow Lake", "Celina", "TN", ["Camping", "Boating", "Fishing"]),
    ("Twin Creek Group Camping", "camping", "USACE", "Tenkiller Ferry Lake", "Vian", "OK", ["Group Camping", "Lake", "Boating"]),
    ("Chilkoot Trail Campgrounds", "permits", "NPS", "Klondike Gold Rush National Historical Park", "Skagway", "AK", ["Backpacking", "History", "Camping"]),
    ("Apostle Islands Kayak Camping", "permits", "NPS", "Apostle Islands National Lakeshore", "Bayfield", "WI", ["Kayaking", "Camping", "Lakes"]),
    ("Firehole Canyon Picnic Area", "day_use", "NPS", "Yellowstone National Park", "Madison", "WY", ["Day Use", "Picnicking", "Scenic Drives"]),
    ("Jenny Lake Shuttle Boat Tickets", "tickets", "NPS", "Grand Teton National Park", "Moose", "WY", ["Boating", "Hiking", "Scenic Views"]),
    ("Mesa Verde Cliff Dwelling Tours", "tickets", "NPS", "Mesa Verde National Park", "Mesa Verde", "CO", ["Tours", "History", "Archeology"]),
    ("Arches Scenic Drive Timed Entry", "passes", "NPS", "Arches National Park", "Moab", "UT", ["Timed Entry", "Scenic Drives", "Photography"]),
    ("Biscayne National Park Heritage Tours", "tickets", "NPS", "Biscayne National Park", "Homestead", "FL", ["Tours", "Boating", "Snorkeling"]),
]

# v2 catalogue expansion: a broader set of real-world facilities sourced from
# public Recreation.gov / NPS / USFS / USACE / BLM / FWS inventory listings.
# Predominantly camping to lift the per-facility campsite count alongside the
# overall facility count. Tuple shape matches EXTRA_NAMES.
EXTRA_NAMES_V2 = [
    # --- Camping: West / Pacific ---
    ("Upper Pines Campground", "camping", "NPS", "Yosemite National Park", "Yosemite Valley", "CA", ["Camping", "Waterfalls", "Hiking"]),
    ("Lower Pines Campground", "camping", "NPS", "Yosemite National Park", "Yosemite Valley", "CA", ["Camping", "River Access", "Hiking"]),
    ("North Pines Campground", "camping", "NPS", "Yosemite National Park", "Yosemite Valley", "CA", ["Camping", "River Access", "Photography"]),
    ("Wawona Campground", "camping", "NPS", "Yosemite National Park", "Wawona", "CA", ["Camping", "Hiking", "Giant Sequoias"]),
    ("Hodgdon Meadow Campground", "camping", "NPS", "Yosemite National Park", "Big Oak Flat", "CA", ["Camping", "Hiking", "Forest"]),
    ("Crane Flat Campground", "camping", "NPS", "Yosemite National Park", "Crane Flat", "CA", ["Camping", "Stargazing", "Forest"]),
    ("Tuolumne Meadows Campground", "camping", "NPS", "Yosemite National Park", "Tuolumne Meadows", "CA", ["Camping", "Wildflowers", "Hiking"]),
    ("Devils Postpile Campground", "camping", "USFS", "Inyo National Forest", "Mammoth Lakes", "CA", ["Camping", "Waterfalls", "Hiking"]),
    ("Convict Lake Campground", "camping", "USFS", "Inyo National Forest", "Mammoth Lakes", "CA", ["Camping", "Fishing", "Lake"]),
    ("Lone Rock Beach Campground", "camping", "NPS", "Glen Canyon National Recreation Area", "Page", "AZ", ["Camping", "Beach", "Boating"]),
    ("Wahweap Campground", "camping", "NPS", "Glen Canyon National Recreation Area", "Page", "AZ", ["Camping", "Boating", "Fishing"]),
    ("Mather Campground", "camping", "NPS", "Grand Canyon National Park", "Grand Canyon Village", "AZ", ["Camping", "Canyon Views", "Hiking"]),
    ("Desert View Campground", "camping", "NPS", "Grand Canyon National Park", "Desert View", "AZ", ["Camping", "Stargazing", "Canyon Views"]),
    ("North Rim Campground", "camping", "NPS", "Grand Canyon National Park", "North Rim", "AZ", ["Camping", "Forest", "Canyon Views"]),
    ("Watchman Campground", "camping", "NPS", "Zion National Park", "Springdale", "UT", ["Camping", "Canyons", "Shuttle Access"]),
    ("South Campground", "camping", "NPS", "Zion National Park", "Springdale", "UT", ["Camping", "River Access", "Canyons"]),
    ("Bridge Bay Campground", "camping", "NPS", "Yellowstone National Park", "Lake Village", "WY", ["Camping", "Lake", "Wildlife Viewing"]),
    ("Madison Campground", "camping", "NPS", "Yellowstone National Park", "Madison", "WY", ["Camping", "Geysers", "Fishing"]),
    ("Grant Village Campground", "camping", "NPS", "Yellowstone National Park", "Grant Village", "WY", ["Camping", "Lake", "Geysers"]),
    ("Canyon Campground", "camping", "NPS", "Yellowstone National Park", "Canyon Village", "WY", ["Camping", "Canyons", "Wildlife Viewing"]),
    ("Fishing Bridge RV Park", "camping", "NPS", "Yellowstone National Park", "Lake Village", "WY", ["Camping", "RV Hookups", "Lake"]),
    ("Slough Creek Campground", "camping", "NPS", "Yellowstone National Park", "Tower Junction", "WY", ["Camping", "Fishing", "Wildlife Viewing"]),
    ("Colter Bay Campground", "camping", "NPS", "Grand Teton National Park", "Colter Bay Village", "WY", ["Camping", "Lake", "Boating"]),
    ("Jenny Lake Campground", "camping", "NPS", "Grand Teton National Park", "Moose", "WY", ["Camping", "Mountains", "Hiking"]),
    ("Signal Mountain Campground", "camping", "NPS", "Grand Teton National Park", "Moran", "WY", ["Camping", "Lake", "Scenic Views"]),
    ("Aspenglen Campground", "camping", "NPS", "Rocky Mountain National Park", "Estes Park", "CO", ["Camping", "Mountains", "Wildlife Viewing"]),
    ("Moraine Park Campground", "camping", "NPS", "Rocky Mountain National Park", "Estes Park", "CO", ["Camping", "Elk Viewing", "Hiking"]),
    ("Timber Creek Campground", "camping", "NPS", "Rocky Mountain National Park", "Grand Lake", "CO", ["Camping", "River Access", "Wildlife Viewing"]),
    ("Glacier Basin Campground", "camping", "NPS", "Rocky Mountain National Park", "Estes Park", "CO", ["Camping", "Mountains", "Hiking"]),
    ("Apgar Campground", "camping", "NPS", "Glacier National Park", "West Glacier", "MT", ["Camping", "Lake", "Hiking"]),
    ("Fish Creek Campground", "camping", "NPS", "Glacier National Park", "West Glacier", "MT", ["Camping", "Forest", "Lake"]),
    ("Many Glacier Campground", "camping", "NPS", "Glacier National Park", "Babb", "MT", ["Camping", "Mountains", "Wildlife Viewing"]),
    ("Two Medicine Campground", "camping", "NPS", "Glacier National Park", "East Glacier Park", "MT", ["Camping", "Lake", "Hiking"]),
    ("St. Mary Campground", "camping", "NPS", "Glacier National Park", "St. Mary", "MT", ["Camping", "Lake", "Scenic Drives"]),
    ("Riley Creek Campground", "camping", "NPS", "Denali National Park and Preserve", "Healy", "AK", ["Camping", "Wildlife Viewing", "Forest"]),
    ("Savage River Campground", "camping", "NPS", "Denali National Park and Preserve", "Healy", "AK", ["Camping", "Wildlife Viewing", "Hiking"]),
    ("Teklanika River Campground", "camping", "NPS", "Denali National Park and Preserve", "Healy", "AK", ["Camping", "Wildlife Viewing", "River Access"]),
    ("Wonder Lake Campground", "camping", "NPS", "Denali National Park and Preserve", "Kantishna", "AK", ["Camping", "Mountains", "Photography"]),
    ("Ohanapecosh Campground", "camping", "NPS", "Mount Rainier National Park", "Packwood", "WA", ["Camping", "Forest", "Hot Springs"]),
    ("Cougar Rock Campground", "camping", "NPS", "Mount Rainier National Park", "Ashford", "WA", ["Camping", "Forest", "Hiking"]),
    ("White River Campground", "camping", "NPS", "Mount Rainier National Park", "Enumclaw", "WA", ["Camping", "Glaciers", "Hiking"]),
    ("Mora Campground", "camping", "NPS", "Olympic National Park", "Forks", "WA", ["Camping", "Beach", "Rainforest"]),
    ("Kalaloch Campground", "camping", "NPS", "Olympic National Park", "Forks", "WA", ["Camping", "Beach", "Tidepools"]),
    ("Hoh Campground", "camping", "NPS", "Olympic National Park", "Forks", "WA", ["Camping", "Rainforest", "Hiking"]),
    ("Sol Duc Hot Springs Campground", "camping", "NPS", "Olympic National Park", "Port Angeles", "WA", ["Camping", "Hot Springs", "Hiking"]),
    ("Heart O' the Hills Campground", "camping", "NPS", "Olympic National Park", "Port Angeles", "WA", ["Camping", "Forest", "Hiking"]),
    ("Lost Creek Campground", "camping", "NPS", "Crater Lake National Park", "Crater Lake", "OR", ["Camping", "Forest", "Lake"]),
    ("Mazama Campground", "camping", "NPS", "Crater Lake National Park", "Crater Lake", "OR", ["Camping", "Lake", "Stargazing"]),

    # --- Camping: Mountain / Desert / Southwest ---
    ("Furnace Creek Campground", "camping", "NPS", "Death Valley National Park", "Death Valley", "CA", ["Camping", "Desert", "Stargazing"]),
    ("Mesquite Spring Campground", "camping", "NPS", "Death Valley National Park", "Death Valley", "CA", ["Camping", "Desert", "Hiking"]),
    ("Texas Spring Campground", "camping", "NPS", "Death Valley National Park", "Death Valley", "CA", ["Camping", "Desert", "Wildflowers"]),
    ("Black Rock Campground", "camping", "NPS", "Joshua Tree National Park", "Yucca Valley", "CA", ["Camping", "Desert", "Rock Climbing"]),
    ("Cottonwood Campground", "camping", "NPS", "Joshua Tree National Park", "Twentynine Palms", "CA", ["Camping", "Desert", "Stargazing"]),
    ("Jumbo Rocks Campground", "camping", "NPS", "Joshua Tree National Park", "Twentynine Palms", "CA", ["Camping", "Rock Climbing", "Stargazing"]),
    ("Indian Cove Campground", "camping", "NPS", "Joshua Tree National Park", "Twentynine Palms", "CA", ["Camping", "Rock Climbing", "Hiking"]),
    ("Devils Garden Campground", "camping", "NPS", "Arches National Park", "Moab", "UT", ["Camping", "Canyons", "Photography"]),
    ("Squaw Flat Campground", "camping", "NPS", "Canyonlands National Park", "Monticello", "UT", ["Camping", "Canyons", "Hiking"]),
    ("Willow Flat Campground", "camping", "NPS", "Canyonlands National Park", "Moab", "UT", ["Camping", "Canyons", "Stargazing"]),
    ("Fruita Campground", "camping", "NPS", "Capitol Reef National Park", "Torrey", "UT", ["Camping", "Orchards", "Canyons"]),
    ("Sunset Campground", "camping", "NPS", "Bryce Canyon National Park", "Bryce", "UT", ["Camping", "Canyons", "Stargazing"]),
    ("North Campground", "camping", "NPS", "Bryce Canyon National Park", "Bryce", "UT", ["Camping", "Canyons", "Hiking"]),
    ("Chisos Basin Campground", "camping", "NPS", "Big Bend National Park", "Big Bend National Park", "TX", ["Camping", "Mountains", "Stargazing"]),
    ("Rio Grande Village Campground", "camping", "NPS", "Big Bend National Park", "Big Bend National Park", "TX", ["Camping", "Desert", "Birding"]),
    ("Gulpha Gorge Campground", "camping", "NPS", "Hot Springs National Park", "Hot Springs", "AR", ["Camping", "Forest", "Hot Springs"]),
    ("Pinyon Flats Campground", "camping", "NPS", "Great Sand Dunes National Park and Preserve", "Mosca", "CO", ["Camping", "Sand Dunes", "Stargazing"]),

    # --- Camping: USFS / USACE Lakes ---
    ("Holiday Park Campground", "camping", "USACE", "Lake Sonoma", "Geyserville", "CA", ["Camping", "Lake", "Boating"]),
    ("Pleasant Cove Campground", "camping", "USACE", "Center Hill Lake", "Smithville", "TN", ["Camping", "Lake", "Fishing"]),
    ("Floating Mill Campground", "camping", "USACE", "Center Hill Lake", "Silver Point", "TN", ["Camping", "Lake", "Boating"]),
    ("Lillydale Campground", "camping", "USACE", "Dale Hollow Lake", "Allons", "TN", ["Camping", "Lake", "Fishing"]),
    ("Willow Grove Campground", "camping", "USACE", "Dale Hollow Lake", "Allons", "TN", ["Camping", "Lake", "Boating"]),
    ("Long Branch Campground", "camping", "USACE", "Lake Cumberland", "Albany", "KY", ["Camping", "Lake", "Boating"]),
    ("Kendall Campground", "camping", "USACE", "Lake Cumberland", "Burnside", "KY", ["Camping", "Lake", "Fishing"]),
    ("Salt Creek Campground", "camping", "USACE", "Lake Cumberland", "Russell Springs", "KY", ["Camping", "Lake", "Boating"]),
    ("Bluestem Point Campground", "camping", "USACE", "El Dorado Lake", "El Dorado", "KS", ["Camping", "Lake", "Hiking"]),
    ("Walnut River Campground", "camping", "USACE", "El Dorado Lake", "El Dorado", "KS", ["Camping", "Lake", "Boating"]),
    ("Outlet Park Campground", "camping", "USACE", "Council Grove Lake", "Council Grove", "KS", ["Camping", "Lake", "Fishing"]),
    ("Mill Creek Park Campground", "camping", "USACE", "Tuttle Creek Lake", "Manhattan", "KS", ["Camping", "Lake", "Boating"]),
    ("Spillway Campground", "camping", "USACE", "Tuttle Creek Lake", "Manhattan", "KS", ["Camping", "Lake", "Fishing"]),
    ("Tailwater Campground", "camping", "USACE", "Berlin Lake", "Berlin Center", "OH", ["Camping", "Lake", "Fishing"]),
    ("Lakeside Campground", "camping", "USACE", "Berlin Lake", "Deerfield", "OH", ["Camping", "Lake", "Boating"]),
    ("Sims Flat Campground", "camping", "USFS", "Shasta-Trinity National Forest", "Castella", "CA", ["Camping", "River Access", "Fishing"]),
    ("Castle Lake Campground", "camping", "USFS", "Shasta-Trinity National Forest", "Mount Shasta", "CA", ["Camping", "Lake", "Hiking"]),
    ("Panther Meadows Campground", "camping", "USFS", "Shasta-Trinity National Forest", "Mount Shasta", "CA", ["Camping", "Wildflowers", "Hiking"]),
    ("Ackerman Campground", "camping", "USFS", "Shasta-Trinity National Forest", "Trinity Center", "CA", ["Camping", "River Access", "Fishing"]),
    ("Pinecrest Campground", "camping", "USFS", "Stanislaus National Forest", "Pinecrest", "CA", ["Camping", "Lake", "Swimming"]),
    ("Lodgepole Campground", "camping", "USFS", "Stanislaus National Forest", "Pinecrest", "CA", ["Camping", "Forest", "Hiking"]),
    ("Sweetwater Campground", "camping", "USFS", "Stanislaus National Forest", "Groveland", "CA", ["Camping", "River Access", "Fishing"]),
    ("Lake Alpine Campground", "camping", "USFS", "Stanislaus National Forest", "Bear Valley", "CA", ["Camping", "Lake", "Boating"]),
    ("Big Meadows Campground", "camping", "USFS", "Sequoia National Forest", "Hume", "CA", ["Camping", "Forest", "Hiking"]),
    ("Hume Lake Campground", "camping", "USFS", "Sequoia National Forest", "Hume", "CA", ["Camping", "Lake", "Swimming"]),
    ("Princess Campground", "camping", "USFS", "Sequoia National Forest", "Hume", "CA", ["Camping", "Forest", "Wildflowers"]),
    ("Cold Springs Campground", "camping", "USFS", "Sequoia National Forest", "Mineral King", "CA", ["Camping", "Mountains", "Hiking"]),
    ("Three Creek Lake Campground", "camping", "USFS", "Deschutes National Forest", "Sisters", "OR", ["Camping", "Lake", "Fishing"]),
    ("Tumalo Falls Campground", "camping", "USFS", "Deschutes National Forest", "Bend", "OR", ["Camping", "Waterfalls", "Hiking"]),
    ("Lava Lake Campground", "camping", "USFS", "Deschutes National Forest", "Bend", "OR", ["Camping", "Lake", "Fishing"]),
    ("Elk Lake Campground", "camping", "USFS", "Deschutes National Forest", "Bend", "OR", ["Camping", "Lake", "Sailing"]),
    ("Sherman Pass Campground", "camping", "USFS", "Colville National Forest", "Republic", "WA", ["Camping", "Mountains", "Hiking"]),
    ("Sullivan Lake Campground", "camping", "USFS", "Colville National Forest", "Metaline Falls", "WA", ["Camping", "Lake", "Swimming"]),
    ("Lakeshore Campground", "camping", "USFS", "Wenatchee National Forest", "Chelan", "WA", ["Camping", "Lake", "Boating"]),

    # --- Camping: Midwest / South / East ---
    ("Devils Lake Campground", "camping", "USFS", "Hoosier National Forest", "Bedford", "IN", ["Camping", "Lake", "Hiking"]),
    ("Indian Boundary Campground", "camping", "USFS", "Cherokee National Forest", "Tellico Plains", "TN", ["Camping", "Lake", "Hiking"]),
    ("Cosby Campground", "camping", "NPS", "Great Smoky Mountains National Park", "Cosby", "TN", ["Camping", "Forest", "Hiking"]),
    ("Cades Cove Campground", "camping", "NPS", "Great Smoky Mountains National Park", "Townsend", "TN", ["Camping", "Wildlife Viewing", "History"]),
    ("Elkmont Campground", "camping", "NPS", "Great Smoky Mountains National Park", "Gatlinburg", "TN", ["Camping", "River Access", "Hiking"]),
    ("Smokemont Campground", "camping", "NPS", "Great Smoky Mountains National Park", "Cherokee", "NC", ["Camping", "River Access", "Hiking"]),
    ("Linville Falls Campground", "camping", "NPS", "Blue Ridge Parkway", "Spruce Pine", "NC", ["Camping", "Waterfalls", "Hiking"]),
    ("Julian Price Campground", "camping", "NPS", "Blue Ridge Parkway", "Blowing Rock", "NC", ["Camping", "Lake", "Hiking"]),
    ("Mt. Pisgah Campground", "camping", "NPS", "Blue Ridge Parkway", "Canton", "NC", ["Camping", "Mountains", "Hiking"]),
    ("Big Meadows Campground (Shenandoah)", "camping", "NPS", "Shenandoah National Park", "Stanley", "VA", ["Camping", "Wildflowers", "Wildlife Viewing"]),
    ("Lewis Mountain Campground", "camping", "NPS", "Shenandoah National Park", "Stanardsville", "VA", ["Camping", "Forest", "Hiking"]),
    ("Loft Mountain Campground", "camping", "NPS", "Shenandoah National Park", "Crozet", "VA", ["Camping", "Forest", "Hiking"]),
    ("Mathews Arm Campground", "camping", "NPS", "Shenandoah National Park", "Luray", "VA", ["Camping", "Forest", "Hiking"]),
    ("Black Woods Campground", "camping", "NPS", "Acadia National Park", "Otter Creek", "ME", ["Camping", "Forest", "Beach"]),
    ("Seawall Campground", "camping", "NPS", "Acadia National Park", "Southwest Harbor", "ME", ["Camping", "Forest", "Tidepools"]),
    ("Schoodic Woods Campground", "camping", "NPS", "Acadia National Park", "Winter Harbor", "ME", ["Camping", "Forest", "Biking"]),
    ("Wright Brothers Park Campground", "camping", "NPS", "Cape Hatteras National Seashore", "Nags Head", "NC", ["Camping", "Beach", "History"]),
    ("Oregon Inlet Campground", "camping", "NPS", "Cape Hatteras National Seashore", "Nags Head", "NC", ["Camping", "Beach", "Fishing"]),
    ("Cape Point Campground", "camping", "NPS", "Cape Hatteras National Seashore", "Buxton", "NC", ["Camping", "Beach", "Lighthouses"]),
    ("Frisco Campground", "camping", "NPS", "Cape Hatteras National Seashore", "Frisco", "NC", ["Camping", "Beach", "Fishing"]),
    ("Long Pine Key Campground", "camping", "NPS", "Everglades National Park", "Homestead", "FL", ["Camping", "Wildlife Viewing", "Birding"]),
    ("Flamingo Campground", "camping", "NPS", "Everglades National Park", "Flamingo", "FL", ["Camping", "Wildlife Viewing", "Paddling"]),
    ("Bear Lake Campground", "camping", "USFS", "Chippewa National Forest", "Cass Lake", "MN", ["Camping", "Lake", "Fishing"]),
    ("Norway Beach Campground", "camping", "USFS", "Chippewa National Forest", "Cass Lake", "MN", ["Camping", "Beach", "Swimming"]),
    ("Twin Lakes Campground", "camping", "USFS", "Superior National Forest", "Ely", "MN", ["Camping", "Lake", "Canoeing"]),
    ("Sawbill Lake Campground", "camping", "USFS", "Superior National Forest", "Tofte", "MN", ["Camping", "Lake", "Canoeing"]),
    ("Fall River Campground", "camping", "USFS", "Black Hills National Forest", "Hot Springs", "SD", ["Camping", "Forest", "History"]),

    # --- Permits / Tickets / Passes / Day Use mix ---
    ("Half Dome Cables Permit", "permits", "NPS", "Yosemite National Park", "Yosemite Valley", "CA", ["Climbing", "Wilderness", "Day Use"]),
    ("Angels Landing Permit", "permits", "NPS", "Zion National Park", "Springdale", "UT", ["Hiking", "Canyons", "Day Use Permit"]),
    ("The Wave Lottery", "lottery", "BLM", "Vermilion Cliffs National Monument", "Kanab", "UT", ["Lottery", "Hiking", "Photography"]),
    ("Coyote Buttes South Permit", "permits", "BLM", "Vermilion Cliffs National Monument", "Kanab", "AZ", ["Lottery", "Hiking", "Photography"]),
    ("Subway Slot Canyon Permit", "permits", "NPS", "Zion National Park", "Springdale", "UT", ["Canyoneering", "Permits", "Wilderness"]),
    ("Cedar Mesa Backcountry Permit", "permits", "BLM", "Bears Ears National Monument", "Blanding", "UT", ["Backpacking", "Archeology", "Wilderness"]),
    ("Paria Canyon Permit", "permits", "BLM", "Vermilion Cliffs National Monument", "Kanab", "UT", ["Backpacking", "Canyons", "Wilderness"]),
    ("Mt. St. Helens Climbing Permit", "permits", "USFS", "Gifford Pinchot National Forest", "Cougar", "WA", ["Climbing", "Volcanoes", "Permits"]),
    ("Alcatraz Island Tour Tickets", "tickets", "NPS", "Golden Gate National Recreation Area", "San Francisco", "CA", ["Tours", "History", "Ferries"]),
    ("Statue of Liberty Pedestal Tickets", "tickets", "NPS", "Statue of Liberty National Monument", "New York", "NY", ["Tours", "History", "Ferries"]),
    ("Independence Hall Tour Tickets", "tickets", "NPS", "Independence National Historical Park", "Philadelphia", "PA", ["Tours", "History"]),
    ("Carlsbad Caverns Guided Tour Tickets", "tickets", "NPS", "Carlsbad Caverns National Park", "Carlsbad", "NM", ["Tours", "Caves", "Ranger Program"]),
    ("Wind Cave Tour Tickets", "tickets", "NPS", "Wind Cave National Park", "Hot Springs", "SD", ["Tours", "Caves", "Ranger Program"]),
    ("Lewis and Clark Caverns Tours", "tickets", "USFS", "Beaverhead-Deerlodge National Forest", "Three Forks", "MT", ["Tours", "Caves", "History"]),
    ("Haleakala Summit Sunrise Reservation", "passes", "NPS", "Haleakala National Park", "Kula", "HI", ["Timed Entry", "Volcanoes", "Sunrise"]),
    ("Acadia Cadillac Summit Vehicle Reservation", "passes", "NPS", "Acadia National Park", "Bar Harbor", "ME", ["Timed Entry", "Mountains", "Sunrise"]),
    ("Glacier Going-to-the-Sun Vehicle Pass", "passes", "NPS", "Glacier National Park", "West Glacier", "MT", ["Timed Entry", "Scenic Drives", "Mountains"]),
    ("Arches Timed Entry Vehicle Pass", "passes", "NPS", "Arches National Park", "Moab", "UT", ["Timed Entry", "Canyons", "Photography"]),
    ("Lake Mead Day Use Pass", "passes", "NPS", "Lake Mead National Recreation Area", "Boulder City", "NV", ["Day Use", "Boating", "Swimming"]),
    ("Cape Lookout Ferry Tickets", "tickets", "NPS", "Cape Lookout National Seashore", "Harkers Island", "NC", ["Ferries", "Beach", "Lighthouses"]),
    ("Channel Islands Boat Transportation", "tickets", "NPS", "Channel Islands National Park", "Ventura", "CA", ["Ferries", "Island", "Wildlife Viewing"]),
    ("Dry Tortugas Ferry Tickets", "tickets", "NPS", "Dry Tortugas National Park", "Key West", "FL", ["Ferries", "Snorkeling", "History"]),
    ("Glacier Bay Day Cruise Tickets", "tickets", "NPS", "Glacier Bay National Park", "Gustavus", "AK", ["Tours", "Wildlife Viewing", "Glaciers"]),
    ("Sleeping Bear Dunes Day Use Pass", "day_use", "NPS", "Sleeping Bear Dunes National Lakeshore", "Empire", "MI", ["Day Use", "Beach", "Scenic Drives"]),
    ("Indiana Dunes Beach Parking Pass", "day_use", "NPS", "Indiana Dunes National Park", "Porter", "IN", ["Day Use", "Beach", "Parking Reservation"]),
    ("Assateague Island Beach Parking", "day_use", "NPS", "Assateague Island National Seashore", "Berlin", "MD", ["Day Use", "Beach", "Wildlife Viewing"]),
    ("Catoctin Mountain Picnic Pavilion", "day_use", "NPS", "Catoctin Mountain Park", "Thurmont", "MD", ["Day Use", "Picnicking", "Forest"]),
    ("Prince William Forest Picnic Pavilion", "day_use", "NPS", "Prince William Forest Park", "Triangle", "VA", ["Day Use", "Picnicking", "Forest"]),
    ("Lake Mead Boulder Beach Parking", "day_use", "NPS", "Lake Mead National Recreation Area", "Boulder City", "NV", ["Day Use", "Beach", "Parking Reservation"]),
    ("San Juan Wilderness Permits", "permits", "USFS", "San Juan National Forest", "Durango", "CO", ["Wilderness", "Backpacking", "Mountains"]),
    ("Pecos Wilderness Permits", "permits", "USFS", "Santa Fe National Forest", "Pecos", "NM", ["Wilderness", "Backpacking", "Mountains"]),
    ("Three Sisters Wilderness Permits", "permits", "USFS", "Willamette National Forest", "Sisters", "OR", ["Wilderness", "Backpacking", "Mountains"]),
    ("Alpine Lakes Wilderness Permits", "permits", "USFS", "Mount Baker-Snoqualmie National Forest", "Skykomish", "WA", ["Wilderness", "Backpacking", "Lakes"]),
    ("Olympic Wilderness Coast Permit", "permits", "NPS", "Olympic National Park", "Forks", "WA", ["Wilderness", "Beach", "Backpacking"]),
    ("Lake Chelan Stehekin Boat Tickets", "tickets", "NPS", "Lake Chelan National Recreation Area", "Chelan", "WA", ["Ferries", "Lake", "Hiking"]),
    ("Cuyahoga Valley Scenic Railroad Tickets", "tickets", "NPS", "Cuyahoga Valley National Park", "Peninsula", "OH", ["Tours", "Train", "Scenic"]),
]

REVIEW_AUTHORS = [
    "Maya R.", "Jordan P.", "Sam K.", "Taylor M.", "Avery L.", "Cameron J.",
    "Riley S.", "Logan W.", "Harper T.", "Casey N.", "Morgan E.", "Dakota F.",
    "Jamie C.", "Skyler A.", "Quinn B.", "Parker D.", "Emerson H.", "Rowan G.",
]

REVIEW_VISIT_DATES = [
    "January 2026", "February 2026", "March 2026", "April 2026",
    "May 2026", "June 2026", "July 2026", "August 2026",
    "September 2025", "October 2025", "November 2025", "December 2025",
]

REVIEW_OPENERS = [
    "The reservation details lined up with what we found on arrival.",
    "This was one of the smoother Recreation.gov bookings we've used recently.",
    "We compared several nearby options before settling on this listing and were glad we did.",
    "The listing was detailed enough that we could plan arrival and gear without guessing.",
    "This spot worked well for a trip where timing and access rules mattered.",
    "The page made it easier to understand what was included and what still needed planning.",
    "This location felt close to the real experience described in the listing.",
    "We booked this after reviewing a few near-miss alternatives and it held up well.",
]

REVIEW_CLOSERS = [
    "We would book it again for a similar itinerary.",
    "It is worth checking nearby alternatives too, but this one delivered on the basics.",
    "The key rules were accurate and easy to confirm before departure.",
    "The reservation flow and on-site expectations were more straightforward than expected.",
    "This is a strong option if you want the same activity mix shown on the page.",
    "The arrival guidance helped avoid last-minute confusion.",
    "For a return trip, we would save this alongside one backup option nearby.",
    "The listing gave us a realistic sense of the tradeoffs before checkout.",
]

RATING_OFFSETS = [0, 0, 0, -1, 0, 0, -1, 0, -2, 0, 0, -1, 0, 0, -1, 0, 0, 0]


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _description(name: str, parent: str, activities: list[str], amenities: list[str]) -> tuple[str, str]:
    activity_text = ", ".join(activities[:3]).lower()
    amenity_text = ", ".join(amenities[:3]).lower()
    short = f"{name} offers {activity_text} within {parent}."
    long = (
        f"{name} is seeded from real Recreation.gov search patterns and mirrors the booking "
        f"details agents need to inspect: agency ownership, location, availability windows, "
        f"fees, accessible options, activities, and facility rules. Visitors should compare "
        f"{activity_text} opportunities with nearby alternatives before reserving. Key "
        f"amenities include {amenity_text}."
    )
    return short, long


def _facility_dict(row: tuple, idx: int) -> dict:
    name, inventory_type, agency, parent, city, state, distance, price, unit, rating, reviews, available, accessible, activities, amenities = row
    rules = ["Carry confirmation details", "Check local alerts before arrival", "Follow posted quiet hours and wildlife guidance"]
    short, long = _description(name, parent, activities, amenities)
    return {
        "slug": _slugify(name),
        "name": name,
        "inventory_type": inventory_type,
        "agency": agency,
        "parent_area": parent,
        "location": city,
        "state": state,
        "distance_miles": distance,
        "price": Decimal(str(price)),
        "price_unit": unit,
        "rating": rating,
        "review_count": reviews,
        "available": available,
        "accessible": accessible,
        "reservable": inventory_type not in {"day_use"} or "Parking" in name or "Picnic" in name,
        "image": IMAGE_OVERRIDES.get(name, IMAGE_POOL[idx % len(IMAGE_POOL)]),
        "short_description": short,
        "long_description": long,
        "amenities_json": json.dumps(amenities),
        "activities_json": json.dumps(activities),
        "rules_json": json.dumps(rules),
        "checkin_date": "2026-05-15",
        "checkout_date": "2026-05-17",
        "capacity": 8 if "Group" in name else 4,
        "tags": " ".join([inventory_type, agency, parent, city, state] + activities + amenities),
    }


def _extra_facilities() -> list[tuple]:
    rows = []
    for idx, (name, inventory_type, agency, parent, city, state, activities) in enumerate(EXTRA_NAMES):
        price = [18, 22, 28, 35, 45, 60][idx % 6]
        unit = "permit" if inventory_type == "permits" else "night"
        amenities = ["Reservable", "Map View", "Mobile Confirmation"]
        if inventory_type == "camping":
            amenities += ["Picnic Tables", "Vault Toilets"]
        else:
            amenities += ["Quota Details", "Date Entry"]
        rows.append((name, inventory_type, agency, parent, city, state, 70 + idx * 43, price, unit, 4.1 + (idx % 8) / 10, 40 + idx * 23, idx % 5 != 0, idx % 4 == 0, activities, amenities))
    # v2 expansion: deterministic numeric fields based on index so the resulting
    # rows are stable across rebuilds and produce a byte-identical seed DB.
    for idx, (name, inventory_type, agency, parent, city, state, activities) in enumerate(EXTRA_NAMES_V2):
        unit_map = {"permits": "permit", "tickets": "ticket", "passes": "pass", "day_use": "day", "lottery": "permit", "camping": "night"}
        unit = unit_map.get(inventory_type, "night")
        if inventory_type == "camping":
            price = [22, 28, 32, 38, 45, 55, 65][idx % 7]
        elif inventory_type == "tickets":
            price = [12, 18, 25, 32, 40][idx % 5]
        elif inventory_type == "permits":
            price = [6, 10, 15, 20, 25][idx % 5]
        elif inventory_type == "passes":
            price = [15, 25, 35, 45][idx % 4]
        elif inventory_type == "day_use":
            price = [5, 8, 10, 12][idx % 4]
        else:
            price = 10
        amenities = ["Reservable", "Map View", "Mobile Confirmation"]
        if inventory_type == "camping":
            amenities += ["Picnic Tables", "Drinking Water", "Vault Toilets"]
        elif inventory_type == "permits":
            amenities += ["Quota Details", "Date Entry", "Printable Permit"]
        elif inventory_type == "tickets":
            amenities += ["Timed Entry", "Accessible Seating"]
        elif inventory_type == "passes":
            amenities += ["Digital Pass", "Entrance Station"]
        elif inventory_type == "day_use":
            amenities += ["Parking Reservation", "Picnic Tables"]
        else:
            amenities += ["Date Entry"]
        distance = 60 + idx * 31
        rating = round(4.0 + (idx % 9) / 10, 1)
        review_count = 35 + idx * 19
        available = idx % 6 != 0
        accessible = idx % 3 == 0
        rows.append((name, inventory_type, agency, parent, city, state, distance, price, unit, rating, review_count, available, accessible, activities, amenities))
    return rows


def seed_database(db, Facility, Campsite, Review):
    if Facility.query.count() > 0:
        return

    facilities = []
    for idx, row in enumerate(BASE_FACILITIES + _extra_facilities()):
        facility = Facility(**_facility_dict(row, idx))
        db.session.add(facility)
        facilities.append(facility)
    db.session.flush()

    for idx, facility in enumerate(facilities):
        if facility.inventory_type == "camping":
            for site_no in range(1, 4):
                db.session.add(Campsite(
                    facility_id=facility.id,
                    name=f"{facility.name.split()[0]} Site {site_no}",
                    site_type=["Standard", "Tent Only", "RV / Trailer"][site_no - 1],
                    nightly_rate=facility.price + Decimal(site_no * 4),
                    capacity=facility.capacity + site_no,
                    accessible=facility.accessible and site_no == 1,
                    available_dates="2026-05-15,2026-05-16,2026-05-17,2026-06-01,2026-06-02",
                ))
        if facility.review_count >= 1000:
            review_target = 42
        elif facility.review_count >= 250:
            review_target = 34
        elif facility.review_count >= 80:
            review_target = 26
        else:
            review_target = 18
        if facility.inventory_type in {"tickets", "day_use"}:
            review_target = max(review_target - 4, 16)
        if facility.inventory_type == "passes":
            review_target = max(review_target, 30)

        for review_no in range(review_target):
            activity = facility.activities[review_no % len(facility.activities)] if facility.activities else facility.label
            amenity = facility.amenities[review_no % len(facility.amenities)] if facility.amenities else "arrival details"
            author = REVIEW_AUTHORS[(idx + review_no) % len(REVIEW_AUTHORS)]
            visit_date = REVIEW_VISIT_DATES[(idx + review_no) % len(REVIEW_VISIT_DATES)]
            rating = max(1, min(5, int(round(facility.rating)) + RATING_OFFSETS[review_no % len(RATING_OFFSETS)]))
            body = (
                f"{REVIEW_OPENERS[(idx + review_no) % len(REVIEW_OPENERS)]} "
                f"The {activity.lower()} component stood out, and the {amenity.lower()} details matched the listing. "
                f"{REVIEW_CLOSERS[(idx + review_no) % len(REVIEW_CLOSERS)]}"
            )
            db.session.add(Review(
                facility_id=facility.id,
                author=author,
                rating=rating,
                body=body,
                visit_date=visit_date,
            ))
    db.session.commit()


def seed_benchmark_users(db, User, Address, PaymentMethod, SavedItem, CartItem, Reservation, Facility, Campsite):
    if User.query.filter_by(email="alice.j@test.com").first():
        return

    users = [
        ("alice_j", "alice.j@test.com", "Alice Johnson", "San Jose"),
        ("bob_c", "bob.c@test.com", "Bob Chen", "Seattle"),
        ("carol_d", "carol.d@test.com", "Carol Davis", "Denver"),
        ("david_k", "david.k@test.com", "David Kim", "Atlanta"),
    ]
    created = {}
    for idx, (username, email, display_name, city) in enumerate(users):
        user = User(username=username, email=email, display_name=display_name, phone=f"555-010{idx}", home_city=city)
        user.set_password(PASSWORD)
        db.session.add(user)
        db.session.flush()
        db.session.add(Address(user_id=user.id, label="Home", street=f"{100 + idx} Trailhead Ave", city=city, state=["CA", "WA", "CO", "GA"][idx], zip_code=["95113", "98101", "80202", "30303"][idx], is_default=True))
        db.session.add(PaymentMethod(user_id=user.id, card_type=["Visa", "Mastercard", "Amex", "Visa"][idx], last4=["4242", "1881", "3005", "9191"][idx], expiry="12/28", is_default=True))
        created[email] = user

    def facility(slug: str):
        return Facility.query.filter_by(slug=slug).first()

    alice = created["alice.j@test.com"]
    bob = created["bob.c@test.com"]
    carol = created["carol.d@test.com"]
    david = created["david.k@test.com"]

    for user, slugs in [
        (alice, ["point-reyes-national-seashore-campground", "yosemite-national-park-wilderness-permits", "muir-woods-parking-and-shuttle"]),
        (bob, ["enchantment-permit-area-advanced-lottery", "bumping-lake-campground", "voyageurs-national-park-tours"]),
        (carol, ["rocky-mountain-national-park-timed-entry", "grand-teton-national-park-site-pass", "canyonlands-overnight-backcountry-permits"]),
        (david, ["cumberland-island-camping-permits", "okefenokee-overnight-camping-permit", "sherando-lake-family-camping"]),
    ]:
        for slug in slugs:
            f = facility(slug)
            if f:
                db.session.add(SavedItem(user_id=user.id, facility_id=f.id))

    for user, slug in [(alice, "pinnacles-campground"), (bob, "lake-powhatan-glamping"), (carol, "denali-national-park-site-pass"), (david, "voyageurs-national-park-tours")]:
        f = facility(slug)
        site = f.campsites[0] if f and f.campsites else None
        if f:
            db.session.add(CartItem(user_id=user.id, facility_id=f.id, campsite_id=site.id if site else None, start_date="2026-05-15", end_date="2026-05-17", guests=2, quantity=1))

    reservations = [
        (alice, "kirby-cove-campground", "Kirby Site 1", "2026-06-12", "2026-06-14", "RG-2026-AJ01", "Upcoming", 108),
        (alice, "yellowstone-national-park-fishing-permit", "Activity Pass", "2026-07-03", "2026-07-03", "RG-2026-AJ02", "Upcoming", 20),
        (bob, "mt-whitney", "Day Use Permit", "2026-08-11", "2026-08-11", "RG-2026-BC01", "Upcoming", 15),
        (carol, "yosemite-national-park-site-pass", "Site Pass", "2026-05-20", "2026-05-20", "RG-2026-CD01", "Upcoming", 35),
        (david, "fort-point-national-historic-site-tours", "Timed Ticket", "2026-04-19", "2026-04-19", "RG-2026-DK01", "Completed", 12),
    ]
    for user, slug, campsite_name, start, end, code, status, total in reservations:
        f = facility(slug)
        if f:
            db.session.add(Reservation(user_id=user.id, facility_id=f.id, campsite_name=campsite_name, start_date=start, end_date=end, guests=2, total_cost=Decimal(str(total)), status=status, confirmation_code=code))

    db.session.commit()
