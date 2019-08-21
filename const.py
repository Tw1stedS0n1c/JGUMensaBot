from emoji import emojize

URL_SPEISEPLAN = "https://www.studierendenwerk-mainz.de/essentrinken/speiseplan/"
URL_ZENTRALMENSA = "https://www.studierendenwerk-mainz.de/speiseplan/frontend/index.php?building_id=1"
URL_GFG = "https://www.studierendenwerk-mainz.de/speiseplan/frontend/index.php?building_id=2"
URL_REWI = "https://www.studierendenwerk-mainz.de/speiseplan/frontend/index.php?building_id=3"
URL_MENSARIA = "https://www.studierendenwerk-mainz.de/speiseplan/frontend/index.php?building_id=7"
URL_OEFFNUNGSZEITEN_ZENTRALMENSA = "https://www.studierendenwerk-mainz.de/essentrinken/universitaetscampus/zentralmensa/"
URL_OEFFNUNGSZEITEN_MENSARIA = "https://www.studierendenwerk-mainz.de/essentrinken/universitaetscampus/mensaria/"
URL_OEFFNUNGSZEITEN_GFG = "https://www.studierendenwerk-mainz.de/essentrinken/universitaetscampus/mensa-georg-forster-gebaeude-gfg/"
URL_OEFFNUNGSZEITEN_INSGRUENE = "https://www.studierendenwerk-mainz.de/essentrinken/universitaetscampus/insgruene/"
URL_OEFFNUNGSZEITEN_REWI = "https://www.studierendenwerk-mainz.de/essentrinken/universitaetscampus/cafe-rewi/"

HEUTE = "&display_type=1"
DIESE_WOCHE = "&display_type=2"
NAECHSTE_WOCHE = "&display_type=3"

EMOJI_FISCH = emojize(":tropical_fish:", use_aliases=True)
EMOJI_HUHN = emojize(":chicken:", use_aliases=True)
EMOJI_RIND = emojize(":cow:", use_aliases=True)
EMOJI_SCHWEIN = emojize(":pig:", use_aliases=True)
EMOJI_WILD = emojize(":deer:", use_aliases=True)

EMOJI_WINK = emojize(":wink:", use_aliases=True)
EMOJI_MAN_SHRUGGING = emojize(":man_shrugging:", use_aliases=True)
EMOJI_BLUSH = emojize(":blush:", use_aliases=True)
EMOJI_SEEDLING = emojize(":seedling:", use_aliases=True)
EMOJI_PARTYING_POOPER = emojize(":tada:", use_aliases=True)  # anstatt tada geht auch "party_popper"
EMOJI_PARTYING_FACE = emojize("\U0001F973",
                              use_aliases=True)  # "partying_face" hat nicht funktioniert, deswegen unicode
EMOJI_SOB = emojize(":sob:", use_aliases=True)

VEGGI = "veggi " + EMOJI_SEEDLING
VEGAN = "vegan " + EMOJI_SEEDLING + EMOJI_SEEDLING

ERROR = "Das hätte nicht passieren dürfen! " + EMOJI_MAN_SHRUGGING + "\nBitte sag mir mit /feedback, was du gemacht " \
                                                                     "hast, damit ich den Fehler beheben kann!"
