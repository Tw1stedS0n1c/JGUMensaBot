class Speise:
    """
    :param beschreibung = Beschreibung des Gerichts (z.B. Nudeln mit Pesto)
    :param preis = Preis für Studierende und nicht Studierende getrennt mit "/"
    :param kennzeichnung = Ein Emoji der beschreibt welches Fleisch in diesem Gericht ist bzw "veggi" oder "vegan"
    """

    beschreibung = None
    preis = None
    kennzeichnung = None

    def __init__(self, *, beschreibung=None, preis=None, kennzeichnung=None):
        self.beschreibung = beschreibung
        self.preis = preis
        self.kennzeichnung = kennzeichnung.strip()

    def getSpeisenNachricht(self):
        ret = self.beschreibung.strip()
        ret += "\n" + self.preis
        ret = ret.strip()
        ret += "\n" + self.kennzeichnung
        ret = ret.strip()
        return ret