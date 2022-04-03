class Theke:
    """
    :param theke = Nummer der Theke (bspw. "1", "3") oder "Außerdem gibt es noch"
    :param speisenliste = An einer Theke gibt es viele Speisen. Jedes Element ist von der Klasse "Speise"
    :param keine_ausgabe = Ist "True" wenn es dort heute keine Ausgabe gibt
    """

    theke = None
    speisenliste = []
    keine_ausgabe = False
    keine_ausgabe_mit_filter = False

    def __init__(self, *, theke=None, speisenliste=[], keine_ausgabe=False):
        if speisenliste is None:
            speisenliste = []
        self.theke = theke
        self.speisenliste = speisenliste
        self.keine_ausgabe = keine_ausgabe

    def entferneFleisch(self):
        """
        Entfernt alle Produkte die NICHT vegetarisch sind, da diese Fleisch enthalten.
        """
        result = []
        for i in range(len(self.speisenliste)):
            if ("veggi" in self.speisenliste[i].kennzeichnung) or ("vegan" in self.speisenliste[i].kennzeichnung):
                result.append(self.speisenliste[i])
        self.speisenliste = result

        if len(self.speisenliste) == 0:  # wenn alle Gerichte entfernt wurden
            self.keine_ausgabe_mit_filter = True

    def entferneTierprodukte(self):
        """
        Entfernt alle Produkte die NICHT vegan sind, da diese Tierprodulkte enthalfen.
        """
        result = []
        for i in range(len(self.speisenliste)):
            if "vegan" in self.speisenliste[i].kennzeichnung:
                result.append(self.speisenliste[i])
        self.speisenliste = result

        if len(self.speisenliste) == 0:  # wenn alle Gerichte entfernt wurden
            self.keine_ausgabe_mit_filter = True

    def getNachrichtZumSenden(self):
        """
        Gibt einen String zurück der vom Bot direkt gesendet werden kann, ohne ihn weiter modifizieren zu müssen.
        :return: String
        """

        # Es gibt keine Gericht
        if self.keine_ausgabe == True:
            return "An Theke " + self.theke + " gibt es heute keine Ausgabe."
        elif self.keine_ausgabe_mit_filter == True:
            return "An Theke " + self.theke + " gibt es heute keine Gerichte mit deinem gewählten Filter."

        # Beschreibung, welche Theke gemeint ist
        if len(self.theke) == 1:  # es handelt sich um Theke 1, 2, 3 oder 4
            ret = "An Theke " + self.theke + " gibt es heute:\n"
        else:
            ret = "Außerdem gibt es noch:\n"

        # Alle Gerichte zusammenschreiben"
        for i in range(0, len(self.speisenliste)):
            ret += self.speisenliste[i].getSpeisenNachricht()
            if i < len(self.speisenliste) - 1:
                ret += "\n---\n"
        return ret