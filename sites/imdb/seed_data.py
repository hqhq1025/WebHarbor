"""Seed data for IMDb mirror.

Idempotent: re-entry is a no-op once Title rows exist.

The data set covers:
  * 25 movies (mix of all-time Top 250 + recent popular)
  * 5 TV series
  * 13 genres
  * 30 persons (directors, writers, cast)
  * Featured reviews per major title
  * 4 benchmark users with deterministic watchlists, ratings, reviews
  * ~12 news items
"""
import json
from datetime import datetime, timedelta


GENRES = [
    ('Action', 'action'), ('Adventure', 'adventure'), ('Animation', 'animation'),
    ('Biography', 'biography'), ('Comedy', 'comedy'), ('Crime', 'crime'),
    ('Drama', 'drama'), ('Fantasy', 'fantasy'), ('History', 'history'),
    ('Horror', 'horror'), ('Mystery', 'mystery'),
    ('Romance', 'romance'), ('Sci-Fi', 'sci-fi'), ('Thriller', 'thriller'),
    ('War', 'war'), ('Western', 'western'), ('Family', 'family'),
    ('Music', 'music'),
]


# Each person: (nm_id, name, birth_year, death_year, birth_place, profession, bio)
PERSONS = [
    ('nm0000338', 'Francis Ford Coppola', 1939, None, 'Detroit, Michigan, USA',
     'director,producer,writer',
     'American film director, producer and screenwriter, best known for The Godfather trilogy and Apocalypse Now.'),
    ('nm0000008', 'Marlon Brando', 1924, 2004, 'Omaha, Nebraska, USA',
     'actor,producer',
     'Considered one of the greatest and most influential actors of the 20th century.'),
    ('nm0000199', 'Al Pacino', 1940, None, 'East Harlem, New York, USA',
     'actor,producer',
     'American actor with a career spanning over five decades, known for The Godfather and Scarface.'),
    ('nm0000148', 'Harrison Ford', 1942, None, 'Chicago, Illinois, USA',
     'actor,producer',
     'Hollywood leading man known for Indiana Jones, Star Wars and Blade Runner.'),
    ('nm0000704', 'Frank Darabont', 1959, None, 'Montbéliard, France',
     'director,writer,producer',
     'Hungarian-American filmmaker, three-time Academy Award nominee, known for The Shawshank Redemption.'),
    ('nm0000209', 'Tim Robbins', 1958, None, 'West Covina, California, USA',
     'actor,director,writer',
     'American actor and filmmaker, Oscar winner for Mystic River.'),
    ('nm0000151', 'Morgan Freeman', 1937, None, 'Memphis, Tennessee, USA',
     'actor,producer,director',
     'American actor, director, and narrator with a distinctive deep voice.'),
    ('nm0634240', 'Christopher Nolan', 1970, None, 'London, England, UK',
     'director,writer,producer',
     'British-American film director known for Inception, Interstellar, The Dark Knight and Oppenheimer.'),
    ('nm0000288', 'Christian Bale', 1974, None, 'Haverfordwest, Wales, UK',
     'actor,producer',
     'Welsh actor, Academy Award winner, known for Batman Begins and The Dark Knight trilogy.'),
    ('nm0001173', 'Heath Ledger', 1979, 2008, 'Perth, Western Australia',
     'actor,producer,director',
     'Australian actor; posthumous Academy Award winner for his role as the Joker in The Dark Knight.'),
    ('nm0000093', 'Brad Pitt', 1963, None, 'Shawnee, Oklahoma, USA',
     'actor,producer',
     'American actor and producer, Academy Award winner.'),
    ('nm0000233', 'Quentin Tarantino', 1963, None, 'Knoxville, Tennessee, USA',
     'director,writer,producer',
     'American filmmaker known for Pulp Fiction, Kill Bill and Once Upon a Time in Hollywood.'),
    ('nm0000158', 'Tom Hanks', 1956, None, 'Concord, California, USA',
     'actor,producer,director',
     'American actor and filmmaker, two-time Academy Award winner.'),
    ('nm0000229', 'Steven Spielberg', 1946, None, 'Cincinnati, Ohio, USA',
     'director,producer,writer',
     'American filmmaker, one of the founding pioneers of the New Hollywood era.'),
    ('nm0000698', 'Uma Thurman', 1970, None, 'Boston, Massachusetts, USA',
     'actress,producer',
     'American actress known for Pulp Fiction and Kill Bill.'),
    ('nm0001392', 'Peter Jackson', 1961, None, 'Pukerua Bay, New Zealand',
     'director,producer,writer',
     'New Zealand filmmaker who directed The Lord of the Rings and The Hobbit trilogies.'),
    ('nm0000704A', 'Elijah Wood', 1981, None, 'Cedar Rapids, Iowa, USA',
     'actor,producer',
     'American actor known for portraying Frodo Baggins in The Lord of the Rings trilogy.'),
    ('nm0001772', 'Robert Downey Jr.', 1965, None, 'Manhattan, New York, USA',
     'actor,producer',
     'American actor; Academy Award winner for Oppenheimer.'),
    ('nm0000354', 'Leonardo DiCaprio', 1974, None, 'Los Angeles, California, USA',
     'actor,producer',
     'American actor and film producer, Academy Award winner.'),
    ('nm0000168', 'Cillian Murphy', 1976, None, 'Douglas, Cork, Ireland',
     'actor,producer',
     'Irish actor, Academy Award winner for Oppenheimer.'),
    ('nm0000128', 'Bryan Cranston', 1956, None, 'Hollywood, California, USA',
     'actor,producer,director',
     'American actor, best known for Breaking Bad.'),
    ('nm0348152', 'Aaron Paul', 1979, None, 'Emmett, Idaho, USA',
     'actor,producer',
     'American actor, known for Breaking Bad.'),
    ('nm0001401', 'Peter Dinklage', 1969, None, 'Morristown, New Jersey, USA',
     'actor,producer',
     'American actor, Emmy and Golden Globe winner for Game of Thrones.'),
    ('nm0000204', 'Natalie Portman', 1981, None, 'Jerusalem, Israel',
     'actress,producer,director',
     'Israeli-born American actress, Academy Award winner.'),
    ('nm0000206', 'Keanu Reeves', 1964, None, 'Beirut, Lebanon',
     'actor,producer',
     'Canadian actor known for The Matrix and John Wick.'),
    ('nm0905152', 'Lana Wachowski', 1965, None, 'Chicago, Illinois, USA',
     'director,writer,producer',
     'American filmmaker, co-creator of The Matrix franchise.'),
    ('nm0000341', 'Greta Gerwig', 1983, None, 'Sacramento, California, USA',
     'director,writer,actress',
     'American director, writer and actress, known for Lady Bird and Barbie.'),
    ('nm2225369', 'Margot Robbie', 1990, None, 'Dalby, Queensland, Australia',
     'actress,producer',
     'Australian actress and producer.'),
    ('nm0586655', 'Bong Joon-ho', 1969, None, 'Daegu, South Korea',
     'director,writer,producer',
     'South Korean filmmaker, Academy Award winner for Parasite.'),
    ('nm0000497', 'Anthony Hopkins', 1937, None, 'Margam, Wales, UK',
     'actor,producer,director',
     'Welsh actor, two-time Academy Award winner.'),
    ('nm0000164', 'Jodie Foster', 1962, None, 'Los Angeles, California, USA',
     'actress,director,producer',
     'American actress and filmmaker, two-time Academy Award winner.'),
]


# Each title:
# (tt_id, type, primary_title, year, end_year, runtime, mpaa, plot_short, plot,
#  rating_avg, num_votes, metascore, popularity_rank, top_rank,
#  bo_us, bo_world, budget, release_date, country, language, taglines, genres,
#  credits=[(role, nm_id, character, billing_order)])
TITLES = [
    ('tt0111161', 'movie', 'The Shawshank Redemption', 1994, None, 142, 'R',
     'Two imprisoned men bond over a number of years.',
     'Chronicles the experiences of a formerly successful banker as a prisoner in the gloomy sphere of Shawshank State Prison after being found guilty of a crime he did not commit. The film portrays the man\'s unique way of dealing with his new, torturous life; along the way he befriends a number of fellow prisoners, most notably a wise long-term inmate named Red.',
     9.3, 2_900_000, 82, 4, 1,
     28_341_469, 73_341_469, 25_000_000, '1994-10-14', 'United States', 'English',
     ['Fear can hold you prisoner. Hope can set you free.'],
     ['Drama'],
     [('director', 'nm0000704', '', None),
      ('writer', 'nm0000704', '', None),
      ('actor', 'nm0000209', 'Andy Dufresne', 1),
      ('actor', 'nm0000151', 'Ellis Boyd "Red" Redding', 2)]),
    ('tt0068646', 'movie', 'The Godfather', 1972, None, 175, 'R',
     'The aging patriarch of an organized crime dynasty transfers control to his reluctant son.',
     'The Godfather "Don" Vito Corleone is the head of the Corleone mafia family in New York. He is at the event of his daughter\'s wedding. Michael, Vito\'s youngest son and a decorated war hero, is also present at the wedding. Michael seems to be uninterested in being a part of the family business.',
     9.2, 2_050_000, 100, 11, 2,
     136_381_073, 250_341_816, 6_000_000, '1972-03-24', 'United States', 'English',
     ['An offer you can\'t refuse.'],
     ['Crime', 'Drama'],
     [('director', 'nm0000338', '', None),
      ('writer', 'nm0000338', '', None),
      ('actor', 'nm0000008', 'Don Vito Corleone', 1),
      ('actor', 'nm0000199', 'Michael Corleone', 2)]),
    ('tt0468569', 'movie', 'The Dark Knight', 2008, None, 152, 'PG-13',
     'When the menace known as the Joker wreaks havoc and chaos on Gotham, Batman must accept one of the greatest psychological tests.',
     'Set within a year after the events of Batman Begins (2005), Batman, Lieutenant James Gordon, and new District Attorney Harvey Dent successfully begin to round up the criminals that plague Gotham City, until a mysterious and sadistic criminal mastermind known only as "The Joker" appears.',
     9.0, 2_900_000, 84, 23, 3,
     534_858_444, 1_006_102_277, 185_000_000, '2008-07-18', 'United States', 'English',
     ['Why so serious?', 'Welcome to a world without rules.'],
     ['Action', 'Crime', 'Drama', 'Thriller'],
     [('director', 'nm0634240', '', None),
      ('writer', 'nm0634240', '', None),
      ('actor', 'nm0000288', 'Bruce Wayne / Batman', 1),
      ('actor', 'nm0001173', 'The Joker', 2)]),
    ('tt1375666', 'movie', 'Inception', 2010, None, 148, 'PG-13',
     'A thief who steals corporate secrets through dream-sharing technology.',
     'Dom Cobb is a skilled thief, the absolute best in the dangerous art of extraction, stealing valuable secrets from deep within the subconscious during the dream state, when the mind is at its most vulnerable.',
     8.8, 2_600_000, 74, 6, 14,
     292_576_195, 836_836_967, 160_000_000, '2010-07-16', 'United States', 'English',
     ['Your mind is the scene of the crime.'],
     ['Action', 'Adventure', 'Sci-Fi', 'Thriller'],
     [('director', 'nm0634240', '', None),
      ('writer', 'nm0634240', '', None),
      ('actor', 'nm0000354', 'Cobb', 1),
      ('actor', 'nm0000288', 'No', 2)]),
    ('tt0816692', 'movie', 'Interstellar', 2014, None, 169, 'PG-13',
     'A team of explorers travel through a wormhole in space.',
     'When Earth becomes uninhabitable in the future, a farmer and ex-NASA pilot, Joseph Cooper, is tasked to pilot a spacecraft, along with a team of researchers, to find a new planet for humans.',
     8.7, 2_200_000, 74, 8, 30,
     188_020_017, 681_877_724, 165_000_000, '2014-11-07', 'United States', 'English',
     ['Mankind was born on Earth. It was never meant to die here.'],
     ['Adventure', 'Drama', 'Sci-Fi'],
     [('director', 'nm0634240', '', None),
      ('writer', 'nm0634240', '', None)]),
    ('tt0110912', 'movie', 'Pulp Fiction', 1994, None, 154, 'R',
     'The lives of two mob hitmen, a boxer, a gangster and his wife intertwine.',
     'Jules Winnfield and Vincent Vega are two hitmen who are out to retrieve a suitcase stolen from their employer, mob boss Marsellus Wallace. Wallace has also asked Vincent to take his wife Mia out a few days later when Wallace himself will be out of town.',
     8.9, 2_200_000, 95, 31, 8,
     107_928_762, 213_928_762, 8_000_000, '1994-10-14', 'United States', 'English',
     ['Just because you are a character doesn\'t mean you have character.'],
     ['Crime', 'Drama'],
     [('director', 'nm0000233', '', None),
      ('writer', 'nm0000233', '', None),
      ('actor', 'nm0000093', 'Vincent Vega', 2),
      ('actor', 'nm0000698', 'Mia Wallace', 3)]),
    ('tt0167260', 'movie', 'The Lord of the Rings: The Return of the King', 2003, None, 201, 'PG-13',
     'Gandalf and Aragorn lead the World of Men against Sauron\'s army.',
     'The final confrontation between the forces of good and evil fighting for control of the future of Middle-earth. Frodo and Sam reach Mordor in their quest to destroy the "one ring".',
     9.0, 2_000_000, 94, 17, 7,
     379_427_292, 1_146_457_516, 94_000_000, '2003-12-17', 'New Zealand', 'English',
     ['The eye of the enemy is moving.', 'There can be no triumph without loss.'],
     ['Action', 'Adventure', 'Drama', 'Fantasy'],
     [('director', 'nm0001392', '', None),
      ('writer', 'nm0001392', '', None),
      ('actor', 'nm0000704A', 'Frodo', 1)]),
    ('tt0109830', 'movie', 'Forrest Gump', 1994, None, 142, 'PG-13',
     'The history of the United States from the 1950s to the \'70s unfolds from the perspective of an Alabama man.',
     'Forrest Gump, while not intelligent, has accidentally been present at many historic moments, but his true love, Jenny Curran, eludes him.',
     8.8, 2_200_000, 82, 43, 12,
     330_455_270, 678_226_133, 55_000_000, '1994-07-06', 'United States', 'English',
     ['Life is like a box of chocolates...you never know what you\'re gonna get.'],
     ['Drama', 'Romance'],
     [('director', 'nm0000229', '', None),
      ('actor', 'nm0000158', 'Forrest Gump', 1)]),
    ('tt0133093', 'movie', 'The Matrix', 1999, None, 136, 'R',
     'A computer hacker learns about the true nature of reality.',
     'Thomas A. Anderson is a man living two lives. By day he is an average computer programmer; by night a hacker known as Neo. Neo has always questioned his reality, but the truth is far beyond his imagination.',
     8.7, 2_100_000, 73, 56, 17,
     172_076_928, 467_222_728, 63_000_000, '1999-03-31', 'United States', 'English',
     ['The fight for the future begins.', 'Welcome to the Real World.'],
     ['Action', 'Sci-Fi'],
     [('director', 'nm0905152', '', None),
      ('writer', 'nm0905152', '', None),
      ('actor', 'nm0000206', 'Neo', 1)]),
    ('tt0099685', 'movie', 'Goodfellas', 1990, None, 145, 'R',
     'The story of Henry Hill and his life in the mob.',
     'Henry Hill might be a small-time gangster, who may have taken part in a robbery, but the mob, headed by Paul Cicero, considers Henry to be a part of their family.',
     8.7, 1_200_000, 90, 95, 18,
     46_836_394, 47_103_945, 25_000_000, '1990-09-19', 'United States', 'English',
     ['Three decades of life in the Mafia.'],
     ['Biography', 'Crime', 'Drama'],
     [('actor', 'nm0000093', 'Mickey Conway', 7)]),
    ('tt0102926', 'movie', 'The Silence of the Lambs', 1991, None, 118, 'R',
     'A young F.B.I. cadet must receive the help of an incarcerated cannibal killer.',
     'F.B.I. trainee Clarice Starling ventures into a maximum-security asylum to pick the diseased brain of Hannibal Lecter, a psychiatrist turned homicidal cannibal.',
     8.6, 1_500_000, 86, 110, 25,
     130_742_922, 272_742_922, 19_000_000, '1991-02-14', 'United States', 'English',
     ['To enter the mind of a killer she must challenge the mind of a madman.'],
     ['Crime', 'Drama', 'Thriller'],
     [('actor', 'nm0000497', 'Hannibal Lecter', 1),
      ('actor', 'nm0000164', 'Clarice Starling', 2)]),
    ('tt0114369', 'movie', 'Se7en', 1995, None, 127, 'R',
     'Two detectives, a rookie and a veteran, hunt a serial killer who uses the seven deadly sins as his motives.',
     'A film about two homicide detectives\' desperate hunt for a serial killer who justifies his crimes as absolution for the world\'s ignorance of the Seven Deadly Sins.',
     8.6, 1_800_000, 65, 86, 21,
     100_125_643, 327_311_859, 33_000_000, '1995-09-22', 'United States', 'English',
     ['Seven deadly sins. Seven ways to die.'],
     ['Crime', 'Drama', 'Mystery', 'Thriller'],
     [('actor', 'nm0000093', 'Detective David Mills', 1),
      ('actor', 'nm0000151', 'Detective William Somerset', 2)]),
    ('tt0137523', 'movie', 'Fight Club', 1999, None, 139, 'R',
     'An insomniac office worker and a soap maker form an underground fight club.',
     'A nameless first person narrator attends support groups in an attempt to subdue his emotional state and relieve his insomniac state.',
     8.8, 2_400_000, 67, 36, 13,
     37_030_102, 101_209_702, 63_000_000, '1999-10-15', 'United States', 'English',
     ['Mischief. Mayhem. Soap.'],
     ['Drama'],
     [('actor', 'nm0000093', 'Tyler Durden', 1)]),
    ('tt15398776', 'movie', 'Oppenheimer', 2023, None, 180, 'R',
     'The story of American scientist J. Robert Oppenheimer and his role in the development of the atomic bomb.',
     'During World War II, Lt. Gen. Leslie Groves Jr. appoints physicist J. Robert Oppenheimer to work on the top-secret Manhattan Project. Oppenheimer and a team of scientists spend years developing and designing the atomic bomb.',
     8.3, 850_000, 88, 1, 38,
     330_078_895, 974_980_408, 100_000_000, '2023-07-21', 'United States', 'English',
     ['The world forever changes.'],
     ['Biography', 'Drama', 'History'],
     [('director', 'nm0634240', '', None),
      ('writer', 'nm0634240', '', None),
      ('actor', 'nm0000168', 'J. Robert Oppenheimer', 1),
      ('actor', 'nm0001772', 'Lewis Strauss', 2)]),
    ('tt1517268', 'movie', 'Barbie', 2023, None, 114, 'PG-13',
     'Barbie suffers a crisis that leads her to question her world and her existence.',
     'Barbie and Ken are having the time of their lives in the colorful and seemingly perfect world of Barbie Land. However, when they get a chance to go to the real world, they soon discover the joys and perils of living among humans.',
     6.8, 700_000, 80, 2, None,
     636_238_421, 1_445_638_421, 145_000_000, '2023-07-21', 'United States', 'English',
     ['She\'s everything. He\'s just Ken.'],
     ['Adventure', 'Comedy', 'Fantasy'],
     [('director', 'nm0000341', '', None),
      ('writer', 'nm0000341', '', None),
      ('actor', 'nm2225369', 'Barbie', 1)]),
    ('tt6751668', 'movie', 'Parasite', 2019, None, 132, 'R',
     'A poor family schemes to become employed by a wealthy family.',
     'All unemployed, Ki-taek\'s family takes peculiar interest in the wealthy and glamorous Parks for their livelihood until they get entangled in an unexpected incident.',
     8.5, 950_000, 96, 19, 35,
     53_855_206, 263_855_206, 11_400_000, '2019-05-30', 'South Korea', 'Korean',
     ['Act like you own the place.'],
     ['Drama', 'Thriller'],
     [('director', 'nm0586655', '', None),
      ('writer', 'nm0586655', '', None)]),
    ('tt4633694', 'movie', 'Spider-Man: Into the Spider-Verse', 2018, None, 117, 'PG',
     'Teen Miles Morales becomes the Spider-Man of his reality.',
     'Bitten by a radioactive spider in the subway, Brooklyn teenager Miles Morales suddenly develops mysterious powers that transform him into the one and only Spider-Man.',
     8.4, 600_000, 87, 47, 60,
     190_241_310, 384_298_736, 90_000_000, '2018-12-14', 'United States', 'English',
     ['More than one wears the mask.'],
     ['Animation', 'Action', 'Adventure'],
     []),
    ('tt0245429', 'movie', 'Spirited Away', 2001, None, 125, 'PG',
     'During her family\'s move to the suburbs, a sullen 10-year-old girl wanders into a world ruled by gods and witches.',
     'When Chihiro moves with her parents to a new neighborhood, they take a shortcut through what appears to be an abandoned amusement park. As her mother and father go to inspect a curiously fragrant feast, they don\'t notice their daughter\'s mounting unease.',
     8.6, 800_000, 96, 33, 23,
     10_055_859, 395_580_000, 19_000_000, '2001-07-20', 'Japan', 'Japanese',
     ['The tunnel led Chihiro to a mysterious town.'],
     ['Animation', 'Adventure', 'Family'],
     []),
    ('tt0120737', 'movie', 'The Lord of the Rings: The Fellowship of the Ring', 2001, None, 178, 'PG-13',
     'A meek Hobbit and eight companions set out on a journey to destroy the One Ring.',
     'An ancient Ring thought lost for centuries has been found, and through a strange twist of fate has been given to a small Hobbit named Frodo.',
     8.9, 2_050_000, 92, 13, 9,
     316_115_420, 887_871_301, 93_000_000, '2001-12-19', 'New Zealand', 'English',
     ['One ring to rule them all.', 'Power can be held in the smallest of things.'],
     ['Action', 'Adventure', 'Drama', 'Fantasy'],
     [('director', 'nm0001392', '', None),
      ('writer', 'nm0001392', '', None),
      ('actor', 'nm0000704A', 'Frodo', 1)]),
    ('tt0167261', 'movie', 'The Lord of the Rings: The Two Towers', 2002, None, 179, 'PG-13',
     'Frodo and Sam are trekking to Mordor.',
     'While Frodo and Sam edge closer to Mordor with the One Ring, their former companion Aragorn rallies the alliance of Free Peoples of Middle-earth.',
     8.8, 1_800_000, 87, 35, 11,
     342_551_365, 947_445_259, 94_000_000, '2002-12-18', 'New Zealand', 'English',
     ['A new power is rising.'],
     ['Action', 'Adventure', 'Drama', 'Fantasy'],
     [('director', 'nm0001392', '', None),
      ('actor', 'nm0000704A', 'Frodo', 1)]),
    ('tt0050083', 'movie', '12 Angry Men', 1957, None, 96, 'Approved',
     'A jury holdout attempts to prevent a miscarriage of justice.',
     'The defense and the prosecution have rested and the jury is filing into the jury room to decide if a young Spanish-American is guilty or innocent of murdering his father.',
     9.0, 870_000, 96, 240, 5,
     None, 955_000, 350_000, '1957-04-10', 'United States', 'English',
     ['Twelve men, twelve minds, one verdict.'],
     ['Crime', 'Drama'],
     []),
    ('tt0080684', 'movie', 'Star Wars: Episode V - The Empire Strikes Back', 1980, None, 124, 'PG',
     'After the Rebels are overpowered by the Empire, Luke Skywalker begins Jedi training with Yoda.',
     'After the destruction of the Death Star, the rebels, including Luke Skywalker, Han Solo, Chewbacca, Princess Leia, C-3PO, and R2-D2, have set up a new base on the icy planet of Hoth.',
     8.7, 1_400_000, 82, 105, 15,
     209_398_025, 538_375_067, 18_000_000, '1980-05-21', 'United States', 'English',
     ['The Adventure Continues...'],
     ['Action', 'Adventure', 'Fantasy', 'Sci-Fi'],
     [('actor', 'nm0000148', 'Han Solo', 1)]),
    ('tt0078788', 'movie', 'Apocalypse Now', 1979, None, 147, 'R',
     'A U.S. Army officer is sent on a mission into the Cambodian jungle.',
     'During the on-going Vietnam War, Captain Benjamin L. Willard is sent on a dangerous mission that, officially, "does not exist, nor will it ever exist".',
     8.4, 700_000, 94, 240, 50,
     83_471_511, 150_000_000, 31_500_000, '1979-08-15', 'United States', 'English',
     ['The horror... the horror...'],
     ['Drama', 'Mystery', 'War'],
     [('director', 'nm0000338', '', None),
      ('writer', 'nm0000338', '', None),
      ('actor', 'nm0000008', 'Colonel Walter E. Kurtz', 2)]),
    ('tt2382320', 'movie', 'No Time to Die', 2021, None, 163, 'PG-13',
     'James Bond has left active service. His peace is short-lived.',
     'Bond, having left active service, is approached by Felix Leiter, his friend from the CIA, who asks for his help.',
     7.3, 460_000, 68, 80, None,
     160_891_007, 774_153_007, 250_000_000, '2021-09-30', 'United Kingdom', 'English',
     ['The mission that changes everything begins.'],
     ['Action', 'Adventure', 'Thriller'],
     []),
    ('tt5491994', 'tvSeries', 'Planet Earth II', 2016, 2016, 60, 'TV-G',
     'Wildlife documentary series with David Attenborough.',
     'Documentary series exploring how animals meet the challenges of surviving in the most iconic habitats on Earth.',
     9.4, 170_000, None, 250, 4,
     None, None, None, '2016-11-06', 'United Kingdom', 'English',
     ['One planet, six worlds.'],
     ['Animation'],
     []),

    # TV
    ('tt0903747', 'tvSeries', 'Breaking Bad', 2008, 2013, 49, 'TV-MA',
     'A high school chemistry teacher turned methamphetamine producer.',
     'A struggling high school chemistry teacher with terminal lung cancer teams up with a former student to manufacture and sell crystal meth to secure his family\'s financial future before he dies.',
     9.5, 2_100_000, None, 12, 2,
     None, None, None, '2008-01-20', 'United States', 'English',
     ['Remember my name.'],
     ['Crime', 'Drama', 'Thriller'],
     [('actor', 'nm0000128', 'Walter White', 1),
      ('actor', 'nm0348152', 'Jesse Pinkman', 2)]),
    ('tt0944947', 'tvSeries', 'Game of Thrones', 2011, 2019, 57, 'TV-MA',
     'Nine noble families wage war against each other to gain control over the lands of Westeros.',
     'In the mythical continent of Westeros, several powerful families fight for control of the Seven Kingdoms.',
     9.2, 2_400_000, None, 7, 6,
     None, None, None, '2011-04-17', 'United States', 'English',
     ['Winter is coming.', 'You win or you die.'],
     ['Action', 'Adventure', 'Drama', 'Fantasy'],
     [('actor', 'nm0001401', 'Tyrion Lannister', 1)]),
    ('tt4574334', 'tvSeries', 'Stranger Things', 2016, 2025, 51, 'TV-14',
     'When a young boy disappears, his mother, a police chief and his friends must confront terrifying supernatural forces.',
     'In the small town of Hawkins, Indiana, a young boy vanishes into thin air. As friends, family and local police search for answers, they are drawn into an extraordinary mystery.',
     8.6, 1_500_000, None, 14, None,
     None, None, None, '2016-07-15', 'United States', 'English',
     ['One summer can change everything.'],
     ['Drama', 'Fantasy', 'Horror'],
     []),
    ('tt0386676', 'tvSeries', 'The Office', 2005, 2013, 22, 'TV-14',
     'A mockumentary on a group of typical office workers.',
     'Steve Carell stars as Michael Scott, regional manager of the Dunder-Mifflin paper company, who fancies himself as a smart and likable boss but is, in fact, a self-absorbed dweeb.',
     9.0, 720_000, None, 38, 10,
     None, None, None, '2005-03-24', 'United States', 'English',
     ['That\'s what she said.'],
     ['Comedy'],
     []),
    ('tt0185906', 'tvSeries', 'Band of Brothers', 2001, 2001, 70, 'TV-MA',
     'The story of Easy Company, U.S. Army 506th Parachute Infantry Regiment.',
     'Drawn from interviews with survivors of Easy Company, as well as their journals and letters, Band of Brothers chronicles the experiences of these men.',
     9.4, 575_000, None, 240, 3,
     None, None, None, '2001-09-09', 'United States', 'English',
     ['They depended on each other. And the world was depending on them.'],
     ['Drama', 'History', 'War'],
     []),
]


# Each news item: (headline, summary, source, published_at, category, related_tt)
NEWS = [
    ('Oppenheimer dominates the 96th Academy Awards',
     'Christopher Nolan\'s historical epic took home seven Oscars including Best Picture, Best Director, and Best Actor.',
     'IMDb News', '2024-03-11', 'movie', 'tt15398776'),
    ('Stranger Things Season 5 wraps production',
     'The Duffer Brothers confirm filming has finished ahead of the show\'s final season premiere later this year.',
     'IMDb News', '2025-01-08', 'tv', 'tt4574334'),
    ('Greta Gerwig signs on to direct Narnia adaptations',
     'After the global phenomenon of Barbie, Gerwig will helm at least two Narnia films for Netflix.',
     'Variety', '2024-09-22', 'movie', 'tt1517268'),
    ('Cillian Murphy joins Steve adaptation',
     'Following his Best Actor win, Murphy will star in and produce a Netflix film based on Cormac McCarthy\'s work.',
     'Deadline', '2024-06-30', 'celebrity', 'nm0000168'),
    ('Peter Jackson returns to Middle-earth with The Hunt for Gollum',
     'Warner Bros. confirms Andy Serkis will direct with Jackson producing, slated for 2026.',
     'Hollywood Reporter', '2024-05-09', 'movie', 'tt0167260'),
    ('Tom Hanks reflects on 30 years of Forrest Gump',
     'In a candid interview, Hanks revisits the making of the iconic 1994 drama.',
     'IndieWire', '2024-07-06', 'celebrity', 'tt0109830'),
    ('Bong Joon-ho returns with Mickey 17',
     'The Parasite director\'s sci-fi follow-up starring Robert Pattinson hits theaters in March.',
     'IMDb News', '2025-02-14', 'movie', 'tt6751668'),
    ('Robert Downey Jr. cast in Avengers: Doomsday',
     'In a surprise twist, Marvel announces Downey will return as Doctor Doom in 2026.',
     'Marvel Wire', '2024-07-27', 'celebrity', 'nm0001772'),
    ('Quentin Tarantino\'s final film delayed',
     'Production on The Movie Critic has been put on hold; Tarantino is reconsidering the project.',
     'Deadline', '2024-04-18', 'movie', 'tt0110912'),
    ('Anthony Hopkins begins memoir promotion',
     'The two-time Academy Award winner discusses six decades on screen.',
     'IMDb News', '2024-11-04', 'celebrity', 'nm0000497'),
    ('Breaking Bad turns 17',
     'Looking back at how a chemistry teacher became the most quoted antihero on TV.',
     'AV Club', '2025-01-20', 'tv', 'tt0903747'),
    ('Planet Earth III tops critic best-of lists',
     'Sir David Attenborough\'s latest series scores a 100 Metascore.',
     'IMDb News', '2024-12-29', 'tv', 'tt5491994'),
]


# (title_tt, user_name_seed, headline, body, rating, helpful_count)
SEED_REVIEWS = [
    ('tt0111161', 'CinemaPilgrim',
     'A timeless meditation on hope',
     'Frank Darabont turns Stephen King\'s novella into a slow-burning hymn to friendship. Tim Robbins is restrained brilliance; Morgan Freeman\'s narration is the year the prison clock stopped. Watch it once. Then watch it again the next week.',
     10, 2_413),
    ('tt0111161', 'CelluloidDad',
     'Why it\'s perennially #1',
     'No special effects. No twist endings. Just a beautifully shot story of two men becoming each other\'s home. Some movies survive on novelty; this one survives on craft.',
     10, 1_902),
    ('tt0068646', 'NewWaveFan',
     'The blueprint',
     'Every modern crime drama lives inside the shadow of Coppola\'s 1972 masterpiece. Brando\'s growl, Pacino\'s slow burn, Gordon Willis\' caramel-and-shadow cinematography — nothing this complete has been made since.',
     10, 3_120),
    ('tt0468569', 'GothamFan',
     'Heath Ledger\'s Joker is unmatched',
     'Forget the cape. The Joker scenes are some of the finest acting put to film in the 2000s. Nolan\'s realist Gotham makes every other comic-book movie look frivolous.',
     10, 4_002),
    ('tt1375666', 'DreamArchitect',
     'The summer thinker',
     'Inception is the rare blockbuster that asks you to keep up. Five-tier nested dreams, an emotional core, and an ending that has fueled bar arguments for fifteen years now.',
     9, 1_551),
    ('tt0816692', 'DustBowlPilot',
     'Cosmic in the best sense',
     'Interstellar wears its Kubrick on its sleeve and earns the comparison. The docking sequence is the most exhilarating five minutes Nolan has filmed.',
     10, 1_802),
    ('tt0110912', 'ReservoirDad',
     'Pulp, defined',
     'Three years before The Big Lebowski, Tarantino weaponized non-linear narrative for the mainstream. Vincent and Jules\' diner conversation is still a master-class.',
     10, 2_287),
    ('tt0167260', 'HobbitForever',
     'The trilogy ends in glory',
     'Twelve Academy Awards for a reason. Jackson manages to send off every character with dignity, and that quiet shot of Frodo at the Grey Havens earns every tear.',
     10, 1_980),
    ('tt0903747', 'AlbuquerqueDealer',
     'Television\'s greatest pivot',
     'A show that began as a quirky drama about a chemistry teacher with cancer ended as a Greek tragedy of a man who became his own worst fear. Bryan Cranston\'s arc has no equal.',
     10, 3_500),
    ('tt0944947', 'IronThroneWatcher',
     'Eight seasons of grandeur and one of fumble',
     'For seven seasons, the gold standard of TV fantasy. Then the rush job in season eight cost it the all-time crown. Still must-watch.',
     8, 1_320),
    ('tt15398776', 'AtomicFilmgoer',
     'Christopher Nolan\'s most personal film',
     'Three hours, mostly conversations, and not a minute wasted. Cillian Murphy is hauntingly internal; the Trinity sequence is craft beyond superlative.',
     10, 1_710),
    ('tt6751668', 'GenreNomad',
     'A class study in three acts',
     'Bong Joon-ho pivots from satire to thriller to tragedy without missing a beat. The first foreign-language Best Picture winner. Earned, every frame.',
     10, 1_408),
    ('tt1517268', 'PinkPilled',
     'Smarter than its marketing suggested',
     'A studio movie about an existential crisis dressed as a toy commercial — and somehow it works. Margot Robbie carries the film, Gosling steals scenes.',
     8, 905),
]


# Benchmark users:
# Each entry: (email, name, password, watchlist tts, ratings [(tt, score)],
#              reviews [(tt, headline, body, rating)])
BENCH_USERS = [
    {
        'email': 'alice.j@test.com', 'name': 'Alice Johnson',
        'password': 'TestPass123!',
        'watchlist': ['tt15398776', 'tt6751668', 'tt0245429', 'tt5491994'],
        'ratings': [('tt0111161', 10), ('tt0068646', 10), ('tt0468569', 9),
                    ('tt1375666', 9), ('tt15398776', 10)],
        'reviews': [
            ('tt0245429', 'Miyazaki at his most generous',
             'Spirited Away is a film that gives more on every rewatch. The bathhouse is a character of its own.', 10),
        ],
    },
    {
        'email': 'bob.c@test.com', 'name': 'Bob Chen',
        'password': 'TestPass123!',
        'watchlist': ['tt0903747', 'tt0944947', 'tt4574334', 'tt0386676'],
        'ratings': [('tt0903747', 10), ('tt0944947', 9), ('tt0386676', 9),
                    ('tt0167260', 10)],
        'reviews': [
            ('tt0386676', 'Comfort TV for the ages',
             'Twenty seasons in and The Office still makes me laugh out loud at the cold opens. Pam and Jim forever.', 9),
        ],
    },
    {
        'email': 'carol.d@test.com', 'name': 'Carol Diaz',
        'password': 'TestPass123!',
        'watchlist': ['tt0102926', 'tt0114369', 'tt0137523', 'tt0099685'],
        'ratings': [('tt0102926', 9), ('tt0114369', 8), ('tt0137523', 9),
                    ('tt0110912', 10)],
        'reviews': [
            ('tt0137523', 'A movie that grows up with you',
             'I rolled my eyes at Fight Club at 16, fell in love at 22, and at 40 I appreciate it as a tragicomic indictment of consumerism. Few movies wear that many hats.', 9),
        ],
    },
    {
        'email': 'dan.k@test.com', 'name': 'Dan Kim',
        'password': 'TestPass123!',
        'watchlist': ['tt0080684', 'tt0078788', 'tt2382320', 'tt0050083'],
        'ratings': [('tt0080684', 10), ('tt0078788', 9), ('tt0050083', 10)],
        'reviews': [],
    },
]


def seed_all(db, Title, Person, Genre, Credit, Review, UserRating,
             WatchlistItem, User, NewsItem):
    """Idempotent. Returns silently if already populated."""
    if db.session.query(Title).count() > 0:
        return

    # 1. Genres ------------------------------------------------------------
    slug_to_genre = {}
    for name, slug in GENRES:
        g = Genre(name=name, slug=slug)
        db.session.add(g)
        slug_to_genre[slug] = g
    db.session.flush()
    name_to_genre = {g.name: g for g in slug_to_genre.values()}

    # 2. Persons -----------------------------------------------------------
    nm_to_person = {}
    for nm_id, name, by, dy, bp, prof, bio in PERSONS:
        p = Person(nm_id=nm_id, name=name, birth_year=by, death_year=dy,
                   birth_place=bp, primary_profession=prof, bio=bio,
                   known_for_json='[]')
        db.session.add(p)
        nm_to_person[nm_id] = p
    db.session.flush()

    # 3. Titles + credits --------------------------------------------------
    tt_to_title = {}
    for row in TITLES:
        (tt_id, ttype, ptitle, year, end_y, runtime, mpaa, plot_short, plot,
         rating, votes, meta, pop_rank, top_rank,
         bo_us, bo_world, budget, rdate, country, lang, taglines,
         genre_names, credits) = row
        t = Title(
            tt_id=tt_id, title_type=ttype, primary_title=ptitle,
            year=year, end_year=end_y, runtime_min=runtime, mpaa_rating=mpaa,
            plot_short=plot_short, plot=plot,
            rating_avg=rating, num_votes=votes, metascore=meta,
            popularity_rank=pop_rank, top_rank=top_rank,
            box_office_us=bo_us, box_office_world=bo_world, budget=budget,
            release_date=rdate, country=country, language=lang,
            taglines_json=json.dumps(taglines),
        )
        for gname in genre_names:
            g = name_to_genre.get(gname)
            if g:
                t.genres.append(g)
        db.session.add(t)
        tt_to_title[tt_id] = (t, credits)
    db.session.flush()

    for tt_id, (t, credits) in tt_to_title.items():
        for role, nm_id, character, billing in credits:
            p = nm_to_person.get(nm_id)
            if not p:
                continue
            db.session.add(Credit(title_id=t.id, person_id=p.id,
                                  role=role, character=character,
                                  billing_order=billing))

    # 4. Known-for per person: pick their top 3 titles by votes ------------
    for nm_id, p in nm_to_person.items():
        their_credits = [(c, tt_to_title[k][0])
                         for k in tt_to_title
                         for c in tt_to_title[k][1]
                         if c[1] == nm_id]
        unique_titles = list({t.tt_id: t for _, t in their_credits}.values())
        unique_titles.sort(key=lambda t: -(t.num_votes or 0))
        p.known_for_json = json.dumps([t.tt_id for t in unique_titles[:4]])

    # 5. Users -------------------------------------------------------------
    nm_to_user = {}
    for u_spec in BENCH_USERS:
        u = User(email=u_spec['email'], name=u_spec['name'])
        u.set_password(u_spec['password'])
        db.session.add(u)
        nm_to_user[u_spec['email']] = (u, u_spec)
    db.session.flush()

    # Extra "review author" users for seeded featured reviews
    review_authors = {name for _, name, *_ in SEED_REVIEWS}
    nm_to_review_author = {}
    for n in review_authors:
        u = User(email=f'{n.lower()}@imdb-mirror.test', name=n)
        u.set_password('seeded-anon-' + n)
        db.session.add(u)
        nm_to_review_author[n] = u
    db.session.flush()

    # 6. Featured reviews --------------------------------------------------
    for tt_id, author, headline, body, rating, helpful in SEED_REVIEWS:
        title_entry = tt_to_title.get(tt_id)
        if not title_entry:
            continue
        t = title_entry[0]
        u = nm_to_review_author[author]
        r = Review(title_id=t.id, user_id=u.id, rating=rating,
                   headline=headline, body=body, helpful_count=helpful,
                   is_seed=True,
                   created_at=datetime(2024, 6, 1))
        db.session.add(r)

    # 7. Benchmark watchlists / ratings / reviews --------------------------
    for email, (u, spec) in nm_to_user.items():
        for tt_id in spec['watchlist']:
            entry = tt_to_title.get(tt_id)
            if not entry:
                continue
            db.session.add(WatchlistItem(user_id=u.id, title_id=entry[0].id,
                                         added_at=datetime(2024, 5, 1)))
        for tt_id, score in spec['ratings']:
            entry = tt_to_title.get(tt_id)
            if not entry:
                continue
            db.session.add(UserRating(user_id=u.id, title_id=entry[0].id,
                                      rating=score,
                                      created_at=datetime(2024, 5, 5)))
        for tt_id, headline, body, rating in spec['reviews']:
            entry = tt_to_title.get(tt_id)
            if not entry:
                continue
            db.session.add(Review(title_id=entry[0].id, user_id=u.id,
                                  rating=rating, headline=headline, body=body,
                                  helpful_count=42, is_seed=False,
                                  created_at=datetime(2024, 5, 10)))

    # 8. News --------------------------------------------------------------
    for headline, summary, source, pub, cat, related in NEWS:
        db.session.add(NewsItem(headline=headline, summary=summary,
                                source=source, published_at=pub,
                                category=cat, related_tt=related))

    db.session.commit()
