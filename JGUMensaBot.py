import copy
import re  # regex
import requests
import telegram.ext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bs4 import BeautifulSoup
from emoji import emojize
import const as c
import meine_token


############################################## Klassen #################################################################
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


############################################## CODE ###################################################################
def get_fleisch_information(div_foodIcon_contents, bezeichnung_in_klammern=False):
    alleFleischEmojis = ""
    if bezeichnung_in_klammern == True:
        string_mit_fleisch = div_foodIcon_contents
        if re.findall(",S,|,S[)]|[(]S,|[(]S[)]", string_mit_fleisch):
            alleFleischEmojis += c.EMOJI_SCHWEIN + " "
        if re.findall(",R,|,R[)]|[(]R,|[(]R[)]", string_mit_fleisch):
            alleFleischEmojis += c.EMOJI_RIND + " "
        if re.findall(",G,|,G[)]|[(]G,|[(]G[)]", string_mit_fleisch):
            alleFleischEmojis += c.EMOJI_HUHN + " "

    else:
        # Fleischbezeichnung ist in DIV
        try:
            text = div_foodIcon_contents[1].attrs['src']
            if "S.png" in text:
                alleFleischEmojis += c.EMOJI_SCHWEIN + " "
            if "R.png" in text:
                alleFleischEmojis += c.EMOJI_RIND + " "
            if "G.png" in text:
                alleFleischEmojis += c.EMOJI_HUHN + " "
            if "W.png" in text:
                alleFleischEmojis += c.EMOJI_WILD + " "
            if "Fi.png" in text:
                alleFleischEmojis += c.EMOJI_FISCH + " "
        except:
            pass

    return alleFleischEmojis


def get_veggi_vegan_information(div_veganIcon_contents):
    veggi_vegan = ""
    try:
        text = div_veganIcon_contents[1].attrs['src']
        if "Veggi.png" in text:
            veggi_vegan = c.VEGGI
        elif "Vegan.png" in text:
            veggi_vegan = c.VEGAN
    except:
        veggi_vegan = ""
    return veggi_vegan


def get_kennzeichnung(*, vegan_div, fleisch_div, fleischbezeichnung_in_klammern=False):
    veg = get_veggi_vegan_information(vegan_div)
    if fleischbezeichnung_in_klammern == True:
        meat = get_fleisch_information(fleisch_div, bezeichnung_in_klammern=True)
    else:
        meat = get_fleisch_information(fleisch_div, bezeichnung_in_klammern=False)
    a = False
    b = False

    if (veg == ""):
        a = True
    if (meat == ""):
        b = True
    if (a and not b) or (not a and b):  # logisches XOR
        return veg + meat
    else:
        # keine Kennzeichnung
        return "Es konnte keine eindeutige Zuordnung gefunden werden (ob vegan, vegetarisch bzw. welches Fleisch)"


def filter_allergikerinformationen(eingabe):
    # filter Allergiker-Information (bzw lösche Inhalt aus 2 Klammern und die 2 Klammern
    ret = re.sub("[\(\[].*?[\)\]]", "", eingabe)
    ret = ret.replace("  ", " ")
    ret = ret.replace(" .", ".")
    ret = ret.replace(" ,", ",")
    return ret


def get_speise_von_div_theke(div):
    # Wenn alles "normal" ist, dann funktioniert das, wenn es aber "Heute keine Ausgabe" gibt, dann wird es einen
    # Attribute Error geben. Den fangen wir im except Teil ab.
    try:
        beschreibung = ""
        kennzeichnung = ""
        preis = ""

        beschreibung = div.find('div', attrs={'class': 'speiseplanname'}).text
        beschreibung = filter_allergikerinformationen(beschreibung).strip()

        # parse den Preis
        preis = div.contents[8].strip()

        # parse Kennzeichnung
        vegan_information = div.find('div', attrs={'class': 'vegan_icon'}).contents
        fleisch_information = div.find('div', attrs={'class': 'food_icon'}).contents
        kennzeichnung = get_kennzeichnung(vegan_div=vegan_information, fleisch_div=fleisch_information)

        return Speise(beschreibung=beschreibung,
                      preis=preis,
                      kennzeichnung=kennzeichnung)

    except AttributeError:
        # Der Fall: "Heute keine Ausgabe"
        return None


def get_speise_von_div_snack(div):
    beschreibung = ""
    kennzeichnung = ""
    preis = ""

    beschreibung = div.find('div', attrs={'class': 'spmenuname'}).text
    # filter_allergiker ist weiter hinten damit man darin eventuelle Fleischinfos (S,R,G) finden kann (bspw. G=Geflügel)
    # parse den Preis
    preis = div.contents[3].text.strip()

    # parse Kennzeichnung wenn vorhanden!
    vegan_information = div.contents[1].contents
    fleisch_information = beschreibung
    kennzeichnung = get_kennzeichnung(vegan_div=vegan_information, fleisch_div=fleisch_information,
                                      fleischbezeichnung_in_klammern=True)

    beschreibung = filter_allergikerinformationen(beschreibung).strip()

    return Speise(beschreibung=beschreibung,
                  preis=preis,
                  kennzeichnung=kennzeichnung)


def makeurl(mensa="url", tag=None):
    if (tag == c.DIESE_WOCHE):
        return (mensa + c.DIESE_WOCHE)
    elif (tag == c.NAECHSTE_WOCHE):
        return (mensa + c.NAECHSTE_WOCHE)
    else:
        return (mensa + c.HEUTE)


# -------------------------------------------------- COMMANDS --------------------------------------------------
def command_start(bot, update):
    start_message = "Das ist ein Mensabot der JGU Mainz. Das Projekt ist nicht offiziell und ich bin nur ein Student. " \
                    "Um anzufangen rate ich dir einmal den /zentralmensa Befehl zu probieren. Viel Spaß!"
    bot.send_message(chat_id=update.message.chat_id, text=start_message)


def command_zentralmensa(bot, update):
    button_list = [
        [InlineKeyboardButton("Alle Gerichte", callback_data="gerichteauswahl_alles_zentralmensa")],
        [InlineKeyboardButton(c.VEGGI, callback_data="gerichteauswahl_veggi_zentralmensa")],
        [InlineKeyboardButton(c.VEGAN, callback_data="gerichteauswahl_vegan_zentralmensa")],

    ]
    markup = InlineKeyboardMarkup(button_list)
    bot.send_message(chat_id=update.message.chat_id, text="Wähle deine Gerichte:", reply_markup=markup)


def parse_mensa(bot, update, url, gerichteauswahl):
    # <editor-fold desc="init">
    # init
    theke1 = Theke(theke="1", speisenliste=[], keine_ausgabe=False)
    theke2 = Theke(theke="2", speisenliste=[], keine_ausgabe=False)
    theke3 = Theke(theke="Snack", speisenliste=[], keine_ausgabe=False)
    alle_theken = [theke1, theke2, theke3]
    speisen = []

    page = requests.get(url)
    if page.status_code != 200:
        text = "Die Homepage\n" + c.URL_SPEISEPLAN + "\n ist nicht erreichbar " + c.EMOJI_SOB
        bot.edit_message_text(text=text,
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id)
        return
    soup = BeautifulSoup(page.text, 'html.parser')
    counterboxes = soup.find_all('div', attrs={'class': 'counter_box'})
    # </editor-fold>

    # <editor-fold desc="Parse das gesamte Essen">
    # Wenn es kein Essen gibt
    if len(counterboxes) == 0:
        for theke in alle_theken:
            theke.keine_ausgabe = True
    # parse alle Speisen von allen (meistens 2) Theken
    for i in range(len(counterboxes)):
        speisen = counterboxes[i].find_all('div', attrs={'class': 'menuspeise'})

        # pro Theke jede Speise
        for speise in speisen:
            erhaltene_speise = get_speise_von_div_theke(speise)
            if erhaltene_speise is not None:
                alle_theken[i].speisenliste.append(erhaltene_speise)
            elif erhaltene_speise is None:
                alle_theken[i].keine_ausgabe = True

    # parse alle Speisen aus "Snack"-Bereich
    try:  # wird gebraucht, falls Mensa zu hat, dann skip einfach
        snackplan = soup.find_all('div', attrs={'class': 'specialbox'})
        speisen = snackplan[0].find_all('div', attrs={'class': 'special_menu'})
    except:
        pass

    for speise in speisen:
        erhaltene_speise = get_speise_von_div_snack(speise)
        if erhaltene_speise is not None:
            alle_theken[2].speisenliste.append(erhaltene_speise)
        elif erhaltene_speise is None:
            alle_theken[2].keine_ausgabe = True
    # </editor-fold>

    # <editor-fold desc="Filtere ungewünschte Speisen">
    # Filter alle ungewünschten Speisen
    if gerichteauswahl != "alles":
        for i in range(len(alle_theken)):
            if gerichteauswahl == "veggi":
                alle_theken[i].entferneFleisch()
            elif gerichteauswahl == "vegan":
                alle_theken[i].entferneTierprodukte()
            # hier noch erweiterbar, z.b. mit "custom"
    # </editor-fold>

    # <editor-fold desc="Sende Nachrichten">
    # Sende Nachrichten und bearbeite die Nachricht mit den InlineKeyboards "alles", "vegetarisch", "vegan"
    edit_text = "Ihre Auswahl war: "
    if gerichteauswahl == "alles":
        edit_text += "Alle Gerichte"
    elif gerichteauswahl == "veggi":
        edit_text += c.VEGGI
    elif gerichteauswahl == "vegan":
        edit_text += c.VEGAN
    else:
        edit_text += c.ERROR
    bot.edit_message_text(text=edit_text,
                          chat_id=update.callback_query.message.chat_id,
                          message_id=update.callback_query.message.message_id)
    for theke in alle_theken:
        bot.send_message(chat_id=update.effective_message.chat_id, text=theke.getNachrichtZumSenden())
    # </editor-fold>


def command_mensaria(bot, update):
    button_list = [
        [InlineKeyboardButton("Alle Gerichte", callback_data="gerichteauswahl_alles_mensaria")],
        [InlineKeyboardButton(c.VEGGI, callback_data="gerichteauswahl_veggi_mensaria")],
        [InlineKeyboardButton(c.VEGAN, callback_data="gerichteauswahl_vegan_mensaria")],

    ]
    markup = InlineKeyboardMarkup(button_list)
    bot.send_message(chat_id=update.message.chat_id, text="Wähle deine Gerichte:", reply_markup=markup)


def command_gfg(bot, update):
    button_list = [
        [InlineKeyboardButton("Alle Gerichte", callback_data="gerichteauswahl_alles_gfg")],
        [InlineKeyboardButton(c.VEGGI, callback_data="gerichteauswahl_veggi_gfg")],
        [InlineKeyboardButton(c.VEGAN, callback_data="gerichteauswahl_vegan_gfg")],

    ]
    markup = InlineKeyboardMarkup(button_list)
    bot.send_message(chat_id=update.message.chat_id, text="Wähle deine Gerichte:", reply_markup=markup)


def command_rewi(bot, update):
    button_list = [
        [InlineKeyboardButton("Alle Gerichte", callback_data="gerichteauswahl_alles_rewi")],
        [InlineKeyboardButton(c.VEGGI, callback_data="gerichteauswahl_veggi_rewi")],
        [InlineKeyboardButton(c.VEGAN, callback_data="gerichteauswahl_vegan_rewi")],

    ]
    markup = InlineKeyboardMarkup(button_list)
    bot.send_message(chat_id=update.message.chat_id, text="Wähle deine Gerichte:", reply_markup=markup)


def command_oeffnungszeiten(bot, update):
    button_list = [
        [InlineKeyboardButton("Alle (dauert einen Moment)", callback_data="oz_alle")],
        [InlineKeyboardButton("GFG", callback_data="oz_gfg")],
        [InlineKeyboardButton("Ins Grüne", callback_data="oz_insgruene")],
        [InlineKeyboardButton("Mensaria", callback_data="oz_mensaria")],
        [InlineKeyboardButton("Rewi", callback_data="oz_rewi")],
        [InlineKeyboardButton("Zentralmensa", callback_data="oz_zentralmensa")]
    ]
    markup = InlineKeyboardMarkup(button_list)
    bot.send_message(chat_id=update.message.chat_id, text="Wähle deine Mensa:", reply_markup=markup)


def command_help(bot, update):
    ret = "Das ist der JGUMensaBot. Ich rate dir folgende Funktionen zu verwenden: \n \n"
    ret += "/help - zeigt dir diese Nachricht\n"
    ret += "/zentralmensa - damit bekommst du das Essen der Zentralmensa\n"
    ret += "/mensaria - damit bekommst du das Essen der mensaria\n"
    ret += "/gfg - damit bekommst du das Essen der GFG-Mensa\n"
    ret += "/rewi - damit bekommst du das Essen der Rewi Cafeteria\n"
    ret += "/oeffnungszeiten - wähle danach eine Mensa aus und die Öffnungszeiten werden angezeigt\n"
    ret += "/feedback - damit kannst du mir Feedback geben\n"
    ret += "/featurerequest - damit könnt ihr einen Verbesserungsvorschlag einreichen oder euch eine neue" \
           "Funktionalität wünschen\n"
    ret += "/curly_fries - dieser Command war der wunsch eines Kommilitonen von euch. Hiermit erfährt ihr ob es in" \
           "der Zentralmensa heute Curly Fries gibt oder nicht " + c.EMOJI_WINK + "\n"
    ret += "\n\nIch bin selbst nur ein Student und habe dieses Projekt ins leben gerufen um einfacher den Speiseplan " \
           "zu erhalten. Die Informationen stammen immer direkt von der Homepage des Studierendenwerks.\n"
    ret += "\nPS: Ich speichere keine Daten, lediglich deine TelegramID wenn du mir ein Feedback hinterlässt, damit " \
           "ich dir antworten kann. Bald werde ich den Code auf Github veröffentlichen, dann kannst du dir den Code " \
           "ansehen, kopieren oder deinen eigenen Bot hosten!\n"
    ret += "Ich wünsche dir noch viel spaß mit dem Bot, und guten Appetit! " + c.EMOJI_PARTYING_FACE + "\n"
    bot.send_message(chat_id=update.message.chat_id, text=ret)


def command_feedback(bot, update, args):
    feedback(bot, update, args, "Feedback")


def command_featurerequest(bot, update, args):
    feedback(bot, update, args, "Featurerequest")


def feedback(bot, update, args, befehl):  # befehl ist entweder "feedback" oder "featurerequest"
    if update.message.text.lower() == ("/" + befehl.lower()) or update.message.text.lower() == (
            "/" + befehl.lower() + "@jgumensabot"):
        msg = "Um ein " + befehl + " abzugeben, solltest du diese Syntax verwenden:\n"
        msg += "\"/" + befehl + " blablabla\""
        bot.send_message(chat_id=update.message.chat_id, text=msg)
    else:
        bot.send_message(chat_id=update.message.chat_id, text="Danke für dein " + befehl + "!")
        feedback = befehl + " von: " + update.message.from_user.full_name + "\n"
        feedback += "Telegram ID: " + str(update.message.from_user.id) + "\n"
        feedback += "\n" + update.message.text  # /feedback has 9 chars
        bot.send_message(chat_id=, text=feedback)  # TODO: replace ID with YOUR ID


def command_answer(bot, update, args):
    if update.message.chat_id == :  # die Nachricht ist von mir  # TODO: replace ID with YOUR ID
        if update.message.text == "/answer" or update.message.text == "/answer@JGUMensaBot" or update.message.text == "/answer@Daboss_bot":
            bot.send_message(chat_id=update.message.chat_id, text="Syntax: \n/answer TelegramID blablabla")
        else:
            recipient_id = update.message.text.split(" ")[1]
            message_to_recipient = ' '.join(update.message.text.split(" ")[2:])
            message_to_me = "Die Nachricht wurde an " + recipient_id + " gesendet \n \n" + message_to_recipient

            bot.send_message(chat_id=update.message.chat_id, text=message_to_me)
            try:
                bot.send_message(chat_id=recipient_id, text=message_to_recipient)
            except:  # Wenn die Nachricht nicht gesendet werden konnte, antworte mir, dass es nicht ging
                msg = "Die Nachricht konnte nicht gesendet werden " + emojize(":sob:", use_aliases=True)
                bot.send_message(chat_id=update.message.chat_id, text=msg)
    else:
        bot.send_message(chat_id=update.message.chat_id, text="Du bist nicht authorisiert")


def parse_gerichte_zentralmensa(bot, update, url, gerichteauswahl):
    # init
    theke1 = Theke(theke="1", speisenliste=[], keine_ausgabe=False)
    theke2 = Theke(theke="2", speisenliste=[], keine_ausgabe=False)
    theke3 = Theke(theke="3", speisenliste=[], keine_ausgabe=False)
    theke4 = Theke(theke="4", speisenliste=[], keine_ausgabe=False)
    alle_theken = [theke1, theke2, theke3, theke4]
    speisen = []

    page = requests.get(url)
    if page.status_code != 200:
        text = "Die Homepage\n" + c.URL_SPEISEPLAN + "\n ist nicht erreichbar " + c.EMOJI_SOB
        bot.edit_message_text(text=text,
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id)
        return
    soup = BeautifulSoup(page.text, 'html.parser')
    counterboxes = soup.find_all('div', attrs={'class': 'counter_box'})

    # Wenn es kein Essen gibt
    if len(counterboxes) == 0:
        for theke in alle_theken:
            theke.keine_ausgabe = True
    # parse alle Speisen von allen Theken
    for i in range(len(counterboxes)):
        speisen = counterboxes[i].find_all('div', attrs={'class': 'menuspeise'})

        # Theken 1, 3 und 4, da Theke 2 die Menütheke ist und anders geparsed wird, weil es z.b. nur einen Preis gibt
        if (i != 1):
            # pro Theke jede Speise
            for speise in speisen:
                erhaltene_speise = get_speise_von_div_theke(speise)
                if erhaltene_speise is not None:
                    alle_theken[i].speisenliste.append(erhaltene_speise)
                elif erhaltene_speise is None:
                    alle_theken[i].keine_ausgabe = True

        # Theke2 (theke, soup)
        else:
            for j in range(len(speisen)):
                # parse Tagessuppe
                if j == 0:
                    tagessuppe = speisen[j].find('div', attrs={'class': 'speiseplanname'}).text
                    tagessuppe = filter_allergikerinformationen(tagessuppe)

                    suppen_objekt = soup.find_all('div', attrs={'class': 'special_box'})[0]. \
                        contents[1].contents[1].contents
                    genaue_suppe = filter_allergikerinformationen(suppen_objekt[0]).strip()  # z.b. Tomatensuppe
                    kennzeichnung = get_veggi__information(suppen_objekt)
                    beschreibung = tagessuppe + " (" + genaue_suppe + ")"  # "Tagessuppe (Tomatensuppe)"

                    # erzeuge Speisenobjekt
                    theke2.speisenliste.append(Speise(beschreibung=beschreibung,
                                                      preis="",
                                                      kennzeichnung=kennzeichnung))

                elif j == 1:  # parse Hauptgericht
                    beschreibung = speisen[j].find('div', attrs={'class': 'speiseplanname'}).text
                    beschreibung = filter_allergikerinformationen(beschreibung)

                    # parse Kennzeichnung
                    vegan_information = speisen[i].find('div', attrs={'class': 'vegan_icon'}).contents
                    fleisch_information = speisen[i].find('div', attrs={'class': 'food_icon'}).contents
                    kennzeichnung = get_kennzeichnung(vegan_div=vegan_information, fleisch_div=fleisch_information)

                    # erzeuge Speisenobjekt
                    theke2.speisenliste.append(Speise(beschreibung=beschreibung,
                                                      preis="",
                                                      kennzeichnung=kennzeichnung))

                elif j == 2:  # parse Tagesdessert
                    beschreibung = speisen[j].find('div', attrs={'class': 'speiseplanname'}).text
                    beschreibung = filter_allergikerinformationen(beschreibung)

                    # erzeuge zwei Speisenobjekte, 1. ist das Dessert
                    theke2.speisenliste.append(Speise(beschreibung=beschreibung,
                                                      preis="",
                                                      kennzeichnung=""))

                    # 2. ist nur der Preis (für eine schöne Formatierung)
                    preis = speisen[j].contents[3].text.strip()
                    theke2.speisenliste.append(Speise(beschreibung="",
                                                      preis=preis,
                                                      kennzeichnung=""))

    edit_text = "Ihre Auswahl war: "
    # Filter alle ungewünschten Speisen
    if gerichteauswahl != "alles":
        # lösche alle Fleischgerichte (Spezialfall Theke2)!
        for i in range(len(alle_theken)):
            if i != 1:
                if gerichteauswahl == "veggi":
                    alle_theken[i].entferneFleisch()
                elif gerichteauswahl == "vegan":
                    alle_theken[i].entferneTierprodukte()
                # hier noch erweiterbar, z.b. mit "custom"

            else:  # SPEZIALFALL THEKE2
                try:  # try wird nur gebraucht falls Mensa zu hat!
                    # Es muss geprüft werden ob irgend ein Gericht entfernt wurde (z.b. Hauptgericht is mit Fleisch,
                    # aber Suppe is Veggi. Dann wird nur das Hauptgericht gefiltert. Es muss aber alles weg, Menütheke!!
                    temp = copy.deepcopy(alle_theken[i])  # temp = theke2

                    # dirty part 1, ich weiß, sehr dirty... damit das Tagesdessert und der Preis nicht gelöscht wird.
                    # habe dafür entschieden, alles als eine sepparate Speise zu erzeugen, damit die Ausgabefunktion
                    # einen schönen Text erzeugt und man keine Extrawurst braucht.
                    alle_theken[i].speisenliste[-1].kennzeichnung = "vegan"
                    alle_theken[i].speisenliste[-2].kennzeichnung = "vegan"

                    # filter wird angewendet
                    if gerichteauswahl == "veggi":
                        alle_theken[i].entferneFleisch()
                    elif gerichteauswahl == "vegan":
                        alle_theken[i].entferneTierprodukte()

                    # dirty part 2
                    alle_theken[i].speisenliste[-1].kennzeichnung = ""
                    alle_theken[i].speisenliste[-2].kennzeichnung = ""

                    if len(alle_theken[i].speisenliste) != len(temp.speisenliste):  # es wurde ein Gericht entfernt
                        alle_theken[i].speisenliste = []
                        alle_theken[i].keine_ausgabe_mit_filter = True
                except IndexError:
                    # Grund ist, es gibt kein Essen -> Mensa hat zu
                    pass

    # Sende Nachrichten und bearbeite die Nachricht mit den InlineKeyboards "alles", "vegetarisch", "vegan"
    edit_text = "Ihre Auswahl war: "
    if gerichteauswahl == "alles":
        edit_text += "Alle Gerichte"
    elif gerichteauswahl == "veggi":
        edit_text += c.VEGGI
    elif gerichteauswahl == "vegan":
        edit_text += c.VEGAN
    else:
        edit_text += c.ERROR
    bot.edit_message_text(text=edit_text,
                          chat_id=update.callback_query.message.chat_id,
                          message_id=update.callback_query.message.message_id)
    for theke in alle_theken:
        bot.send_message(chat_id=update.effective_message.chat_id, text=theke.getNachrichtZumSenden())


def command_curly_fries(bot, update):
    page = requests.get(makeurl(c.URL_ZENTRALMENSA, c.HEUTE))
    if page.status_code != 200:
        text = "Die Homepage\n" + c.URL_SPEISEPLAN + "\n ist nicht erreichbar " + c.EMOJI_SOB
        bot.edit_message_text(text=text,
                              chat_id=update.callback_query.message.chat_id,
                              message_id=update.callback_query.message.message_id)
        return
    soup = BeautifulSoup(page.text, 'html.parser')
    curly_fries = True if "Curly fries" in soup.get_text() else False

    if curly_fries:
        text = "YEAH HEUTE GIBT ES CURLY FRIES " + c.EMOJI_PARTYING_FACE + c.EMOJI_PARTYING_POOPER
        text += "\n in der Zentralmensa"
        bot.send_message(chat_id=update.message.chat_id, text=text)
        bot.send_sticker(chat_id=update.message.chat_id, sticker='CAADAgADTAMAAkcVaAkmOU8hWPR0YhYE')
    else:
        text = "DAMN heute gibt es keine curly fries... " + c.EMOJI_SOB + c.EMOJI_SOB
        text += "\n in der Zentralmensa"
        bot.send_message(chat_id=update.message.chat_id, text=text)
        bot.send_sticker(chat_id=update.message.chat_id, sticker='CAADAgADhwMAAkcVaAkSOJvCwDti1RYE')


# -------------------------------------------------- QUERYS OEFFNUNGSZEITEN --------------------------------------------
def parse_oz_zentralmensa(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'html.parser')
    richtigesDIV = soup.find('div', attrs={'id': 'c436'})

    # Zeiten im Semester
    oz_object_im_semester = richtigesDIV.contents[11].contents
    oeffnungszeiten_im_semester = str(oz_object_im_semester[0]).strip()  # String "Speisenausgabe"
    uhrzeit_im_semester = ' ' + str(oz_object_im_semester[2]).strip() + "\n"  # erst Tage (mo-fr)
    uhrzeit_im_semester += '  ' + str(oz_object_im_semester[4]).strip() + "\n"  # dann die Uhrzeit
    uhrzeit_im_semester += ' ' + str(oz_object_im_semester[6]).strip() + "\n"  # dann Tag (sa)
    uhrzeit_im_semester += '  ' + str(oz_object_im_semester[8]).strip()  # dann die Uhrzeit

    # Zeiten in VL-freie Zeit
    oz_object_vlfreie_zeit = richtigesDIV.contents[13].contents
    oeffnungszeiten_vl_freie_zeit = str(oz_object_vlfreie_zeit[0]).strip()  # String "Vorlesungsfreie Zeit"
    uhrzeit_vlfreie_zeit = ' ' + str(oz_object_im_semester[2]).strip() + "\n"  # erst Tage (mo-fr)
    uhrzeit_vlfreie_zeit += '  ' + str(oz_object_im_semester[4]).strip() + "\n"  # dann die Uhrzeit
    uhrzeit_vlfreie_zeit += ' ' + str(oz_object_im_semester[-3]).strip() + "\n"  # dann Tag (sa)
    uhrzeit_vlfreie_zeit += '  ' + str(oz_object_im_semester[-1]).strip()  # dann die Uhrzeit

    ret = oeffnungszeiten_im_semester + "\n"
    ret += uhrzeit_im_semester + "\n\n"
    ret += oeffnungszeiten_vl_freie_zeit + "\n"
    ret += uhrzeit_vlfreie_zeit

    return ret


def parse_oz_mensaria(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'html.parser')
    richtigesDIV = soup.find_all('div', attrs={'id': 'c78'})[0]

    # Zeiten im Semester
    oz_object_im_semester = richtigesDIV.contents[9].contents
    oeffnungszeiten_im_semester = str(oz_object_im_semester[0]).strip()  # String "Öffnungszeiten"
    uhrzeit_im_semester = ' ' + str(oz_object_im_semester[4]).strip() + "\n"  # erst Tage (mo-do)
    uhrzeit_im_semester += '  ' + str(oz_object_im_semester[6]).strip() + "\n"  # dann die Uhrzeit
    uhrzeit_im_semester += ' ' + str(oz_object_im_semester[8]).strip() + "\n"  # dann Tag (fr)
    uhrzeit_im_semester += '  ' + str(oz_object_im_semester[10]).strip()  # dann die Uhrzeit

    # Zeiten in VL-freie Zeit
    oz_object_vlfreie_zeit = richtigesDIV.contents[9].contents  # Hier ist es dasselbe wie "im semester"
    oeffnungszeiten_vl_freie_zeit = str(oz_object_vlfreie_zeit[14]).strip()  # String "Vorlesungsfreie Zeit"
    uhrzeit_vlfreie_zeit = ' ' + str(oz_object_im_semester[16]).strip() + "\n"  # erst Tage (mo-do)
    uhrzeit_vlfreie_zeit += '  ' + str(oz_object_im_semester[18]).strip() + "\n"  # dann die Uhrzeit
    uhrzeit_vlfreie_zeit += ' ' + str(oz_object_im_semester[20]).strip() + "\n"  # dann Tag (sa)
    uhrzeit_vlfreie_zeit += '  ' + str(oz_object_im_semester[22]).strip()  # dann die Uhrzeit

    ret = oeffnungszeiten_im_semester + "\n"
    ret += uhrzeit_im_semester + "\n\n"
    ret += oeffnungszeiten_vl_freie_zeit + "\n"
    ret += uhrzeit_vlfreie_zeit

    return ret


def parse_oz_gfg(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'html.parser')
    richtigesDIV = soup.find_all('div', attrs={'id': 'c6367'})[0].contents

    # Zeiten im Semester
    oz_object_im_semester = richtigesDIV[9].contents
    oeffnungszeiten_im_semester = str(oz_object_im_semester[11].text).strip()  # String "Öffnungszeiten"
    uhrzeit_im_semester = ' ' + str(oz_object_im_semester[15]).strip() + "\n"  # erst Tage (mo-fr)
    uhrzeit_im_semester += '  ' + str(oz_object_im_semester[17]).strip()  # dann die Uhrzeit

    # Zeiten in VL-freie Zeit
    oeffnungszeiten_vl_freie_zeit = str(richtigesDIV[11].text)  # hier ein Spezialfall

    # Speisenausgabe
    speisenausgabe = str(oz_object_im_semester[6]).strip().split(' ')[0] + "\n"  # String "Speisenausgabe"
    speisenausgabe += ' ' + ' '.join(str(oz_object_im_semester[6]).strip().split(' ')[1:])  # bis 30 min vor Schließung

    ret = oeffnungszeiten_im_semester + "\n"
    ret += uhrzeit_im_semester + "\n"
    ret += oeffnungszeiten_vl_freie_zeit + "\n\n"
    ret += speisenausgabe

    return ret


def parse_oz_insgruene(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'html.parser')
    richtigesDIV = soup.find_all('div', attrs={'id': 'c148'})[
        1]  # wird nur gebraucht damit code schoener ist zum parsen

    # Zeiten im Semester
    oz_object_im_semester = richtigesDIV.contents[11].contents
    oeffnungszeiten_im_semester = str(oz_object_im_semester[0]).strip()  # String "Öffnungszeiten"
    uhrzeit_im_semester = ' ' + str(oz_object_im_semester[2]).strip() + "\n"  # erst Tage (mo-do)
    uhrzeit_im_semester += '  ' + str(oz_object_im_semester[4]).strip() + "\n"  # dann die Uhrzeit
    uhrzeit_im_semester += ' ' + str(oz_object_im_semester[6]).strip() + "\n"  # dann Tag (fr)
    uhrzeit_im_semester += '  ' + str(oz_object_im_semester[8]).strip()  # dann die Uhrzeit

    # Zeiten in VL-freie Zeit
    oz_object_vlfreie_zeit = richtigesDIV.contents[13].contents
    oeffnungszeiten_vl_freie_zeit = str(oz_object_vlfreie_zeit[0].text).strip()  # String "Vorlesungsfreie Zeit"
    uhrzeit_vlfreie_zeit = ' ' + str(oz_object_im_semester[2]).strip() + "\n"  # erst Tage (mo-do)
    uhrzeit_vlfreie_zeit += '  ' + str(oz_object_im_semester[4]).strip() + "\n"  # dann die Uhrzeit
    uhrzeit_vlfreie_zeit += ' ' + str(oz_object_im_semester[6]).strip() + "\n"  # dann Tag (sa)
    uhrzeit_vlfreie_zeit += '  ' + str(oz_object_im_semester[8]).strip()  # dann die Uhrzeit

    ret = oeffnungszeiten_im_semester + "\n"
    ret += uhrzeit_im_semester + "\n\n"
    ret += oeffnungszeiten_vl_freie_zeit + "\n"
    ret += uhrzeit_vlfreie_zeit

    return ret


def parse_oz_rewi(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'html.parser')
    richtigesDIV = soup.find_all('div', attrs={'id': 'c94'})[0]  # wird nur gebraucht damit code schoener ist zum parsen

    # Zeiten im Semester
    oz_object_im_semester = richtigesDIV.contents[11].contents
    oeffnungszeiten_im_semester = str(oz_object_im_semester[0]).strip()  # String "Öffnungszeiten"
    uhrzeit_im_semester = ' ' + str(oz_object_im_semester[2]).strip() + "\n"  # erst Tage (mo-do)
    uhrzeit_im_semester += '  ' + str(oz_object_im_semester[4]).strip() + "\n"  # dann die Uhrzeit
    uhrzeit_im_semester += ' ' + str(oz_object_im_semester[6]).strip() + "\n"  # dann Tag (fr)
    uhrzeit_im_semester += '  ' + str(oz_object_im_semester[8]).strip()  # dann die Uhrzeit

    # Zeiten in VL-freie Zeit
    oz_object_vlfreie_zeit = richtigesDIV.contents[13].contents
    oeffnungszeiten_vl_freie_zeit = str(oz_object_vlfreie_zeit[0]).strip()  # String "Vorlesungsfreie Zeit"
    uhrzeit_vlfreie_zeit = ' ' + str(oz_object_im_semester[2]).strip() + "\n"  # erst Tage (mo-do)
    uhrzeit_vlfreie_zeit += '  ' + str(oz_object_im_semester[4]).strip() + "\n"  # dann die Uhrzeit
    uhrzeit_vlfreie_zeit += ' ' + str(oz_object_im_semester[6]).strip() + "\n"  # dann Tag (sa)
    uhrzeit_vlfreie_zeit += '  ' + str(oz_object_im_semester[8]).strip()  # dann die Uhrzeit

    ret = oeffnungszeiten_im_semester + "\n"
    ret += uhrzeit_im_semester + "\n\n"
    ret += oeffnungszeiten_vl_freie_zeit + "\n"
    ret += uhrzeit_vlfreie_zeit

    return ret


# -------------------------------------------------- QUERY HANDLER -----------------------------------------------------
def query_handler_default(bot, update):
    data = update.callback_query.data
    if "oz_" in data:
        query_oeffnungszeiten(bot, update)
    elif "gerichteauswahl_" in data:
        query_gerichteauswahl(bot, update)

    else:
        bot.send_message(chat_id=update.callback_query.message.chat_id,
                         text="Es ist ein etwas komisches passiert, bitte sag mir was du gemacht hast (mit /feedback),"
                              "damit ich den Fehler beheben kann.")


def query_oeffnungszeiten(bot, update):
    # Es gibt für jede Mensa eine eigene Homepage, somit sind die URL jeweils notwendig. Da die Mensen NICHT dasselbe
    # Template verwenden und somit unterschiedlich strukturiert sind, habe ich dafür eigene Funktionen geschrieben.
    # Dazu kommt, dass jediglich Rewi und InsGrüne denselben Code verwenden. Deswegen habe ich mich für jeweils
    # FAST identische eigene Funktionen entschieden.

    data = update.callback_query.data
    if data == "oz_zentralmensa":
        ret = "Zentralmensa:\n"
        ret += parse_oz_zentralmensa(c.URL_OEFFNUNGSZEITEN_ZENTRALMENSA)
    elif data == "oz_mensaria":
        ret = "Mensaria:\n"
        ret += parse_oz_mensaria(c.URL_OEFFNUNGSZEITEN_MENSARIA)
    elif data == "oz_gfg":
        ret = "GFG:\n"
        ret += parse_oz_gfg(c.URL_OEFFNUNGSZEITEN_GFG)
    elif data == "oz_insgruene":
        ret = "Ins Grüne:\n"
        ret += parse_oz_insgruene(c.URL_OEFFNUNGSZEITEN_INSGRUENE)
    elif data == "oz_rewi":
        ret = "Rewi:\n"
        ret += parse_oz_rewi(c.URL_OEFFNUNGSZEITEN_REWI)
    elif data == "oz_alle":
        ret = "Zentralmensa:\n"
        ret += parse_oz_zentralmensa(c.URL_OEFFNUNGSZEITEN_ZENTRALMENSA)
        ret += "\n\n --- \nMensaria:\n"
        ret += parse_oz_mensaria(c.URL_OEFFNUNGSZEITEN_MENSARIA)
        ret += "\n\n --- \nGFG:\n"
        ret += parse_oz_gfg(c.URL_OEFFNUNGSZEITEN_GFG)
        ret += "\n\n --- \nIns Grüne:\n"
        ret += parse_oz_insgruene(c.URL_OEFFNUNGSZEITEN_INSGRUENE)
        ret += "\n\n --- \nRewi:\n"
        ret += parse_oz_rewi(c.URL_OEFFNUNGSZEITEN_REWI)
    else:
        ret = "Es ist ein Fehler aufgetreten, bitte versuchen Sie es nochmal."

    bot.edit_message_text(text=ret,
                          chat_id=update.callback_query.message.chat_id,
                          message_id=update.callback_query.message.message_id)


def query_gerichteauswahl(bot, update):
    data = update.callback_query.data

    # Zentralmensa
    if "gerichteauswahl_alles_zentralmensa" == data:
        parse_gerichte_zentralmensa(bot, update, makeurl(c.URL_ZENTRALMENSA, c.HEUTE), "alles")
    elif "gerichteauswahl_veggi_zentralmensa" == data:
        parse_gerichte_zentralmensa(bot, update, makeurl(c.URL_ZENTRALMENSA, c.HEUTE), "veggi")
    elif "gerichteauswahl_vegan_zentralmensa" == data:
        parse_gerichte_zentralmensa(bot, update, makeurl(c.URL_ZENTRALMENSA, c.HEUTE), "vegan")

    # Mensaria
    elif "gerichteauswahl_alles_mensaria" == data:
        parse_mensa(bot, update, makeurl(c.URL_MENSARIA, c.HEUTE), "alles")
    elif "gerichteauswahl_veggi_mensaria" == data:
        parse_mensa(bot, update, makeurl(c.URL_MENSARIA, c.HEUTE), "veggi")
    elif "gerichteauswahl_vegan_mensaria" == data:
        parse_mensa(bot, update, makeurl(c.URL_MENSARIA, c.HEUTE), "vegan")

    # GFG
    elif "gerichteauswahl_alles_gfg" == data:
        parse_mensa(bot, update, makeurl(c.URL_GFG, c.HEUTE), "alles")
    elif "gerichteauswahl_veggi_gfg" == data:
        parse_mensa(bot, update, makeurl(c.URL_GFG, c.HEUTE), "veggi")
    elif "gerichteauswahl_vegan_gfg" == data:
        parse_mensa(bot, update, makeurl(c.URL_GFG, c.HEUTE), "vegan")

    # Rewi
    elif "gerichteauswahl_alles_gfg" == data:
        parse_mensa(bot, update, makeurl(c.URL_REWI, c.HEUTE), "alles")
    elif "gerichteauswahl_veggi_gfg" == data:
        parse_mensa(bot, update, makeurl(c.URL_REWI, c.HEUTE), "veggi")
    elif "gerichteauswahl_vegan_gfg" == data:
        parse_mensa(bot, update, makeurl(c.URL_REWI, c.HEUTE), "vegan")

    else:
        bot.send_message(chat_id=update.callback_query.message.chat_id,
                         text="Es ist ein etwas komisches passiert, bitte sag mir was du gemacht hast (mit /feedback),"
                              "damit ich den Fehler beheben kann.")


############################################## essenzielles polling und dispatcher #####################################
myupdater = telegram.ext.Updater(token=meine_token.TOKEN)
dispatcher = myupdater.dispatcher

# handler erzeugen und hinzufügen für alle Commands. Diese sind im Bot mit bspw. "/help" aufzurufen
dispatcher.add_handler(telegram.ext.CommandHandler('start', command_start))
dispatcher.add_handler(telegram.ext.CommandHandler('help', command_help))
dispatcher.add_handler(telegram.ext.CommandHandler('zentralmensa', command_zentralmensa))
dispatcher.add_handler(telegram.ext.CommandHandler('mensaria', command_mensaria))
dispatcher.add_handler(telegram.ext.CommandHandler('gfg', command_gfg))
dispatcher.add_handler(telegram.ext.CommandHandler('rewi', command_gfg))
dispatcher.add_handler(telegram.ext.CommandHandler('feedback', command_feedback, pass_args=True))
dispatcher.add_handler(telegram.ext.CommandHandler('oeffnungszeiten', command_oeffnungszeiten))
dispatcher.add_handler(telegram.ext.CommandHandler('answer', command_answer, pass_args=True))
dispatcher.add_handler(telegram.ext.CommandHandler('featurerequest', command_featurerequest, pass_args=True))
dispatcher.add_handler(telegram.ext.CommandHandler('curly_fries', command_curly_fries))

# CallbackQueryHandler for InlineKeyboardQueries
dispatcher.add_handler(telegram.ext.CallbackQueryHandler(query_handler_default))

# START PROGRAMM
myupdater.start_polling()
myupdater.idle()
