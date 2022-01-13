"""
Class to parse biogrpahy articles on pl.wiki
"""
#
# (C) masti, 2022
#
# Distributed under the terms of the MIT license.
#

import re
import pywikibot
from pywikibot import textlib

class Biography:
    bbdayR = re.compile(
        r'(?i)ur\.\s*((\[{2})?(?P<bbd>\d{1,2} [\wśńź]{4,12})(\]{2})?)?\s*?(\[{2})?(?P<bby>\d{1,4})(\]{2})?')
    bddayR = re.compile(
        r"(?i)zm\.(\s*w)?(\s*(\[{2})?(?P<bdd>\d{1,2} [\wśńź]{4,12})(\]{2})?)?\s*?(\[{2})?(?P<bdy>\d{4})(\]{2})?")
    dateR = re.compile(
        r'(?i)((\[{2})?(?P<day>\d{1,2} [\wśńź]{4,12})(\]{2})?)?\s*?(\[{2})?(?P<year>\d{1,4})(\]{2})?')

    def __init__(self, page: pywikibot.Page):

        # general
        self.shorttitle = page.title(without_brackets=True)
        self.norefstext = self._refremove(page.text)

        # first paragraph (lead) info
        self.firstpar = self._firstpar(self.norefstext)
        self.leadname = self._leadname(self.firstpar) if self.firstpar else None
        self.leadbday = self._leadbday() if self._leadbday() else None
        self.leadbyear = self._leadbyear() if self._leadbyear() else None
        self.leadbdate = ' '.join(item or '' for item in (self.leadbday, self.leadbyear))
        self.leaddday = self._leaddday()
        self.leaddyear = self._leaddyear()
        self.leadddate = ' '.join(item or '' for item in (self.leaddday, self.leaddyear))

        # categories info
        self.catbyear = self._catbyear(self.norefstext)
        self.catdyear = self._catdyear(self.norefstext)

        # infobox info
        self.infoboxtitle, self.infoboxparams = self._listinfoboxes(self.norefstext)
        self.infoboxbday = self._infoboxbday() if self.infoboxparams else None
        self.infoboxbyear = self._infoboxbyear() if self.infoboxparams else None
        self.infoboxbdate = ' '.join(item or '' for item in (self.infoboxbday, self.infoboxbyear))
        self.infoboxdday = self._infoboxdday() if self.infoboxparams else None
        self.infoboxdyear = self._infoboxdyear() if self.infoboxparams else None
        self.infoboxddate = ' '.join(item or '' for item in (self.infoboxdday, self.infoboxdyear))
        self.infoboxname = self._infoboxname() if self.infoboxparams else None

        # results
        self.isconflicted = self.nameconflict or self.birthdayconflict or self.deathdayconflict

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    def __str__(self):
        r = "Class:%s" % self.__class__
        for a in self.__dict__:
            r += '\n%s:%s' % (a, self.__dict__[a])
        return r

    # article lead methods

    @staticmethod
    def _firstpar(text):
        """
        return first paragraf (lead) of page
        """
        match = re.search("(^|\n)(?P<firstpar>'''.*\n)", text)
        return match.group('firstpar') if match else None

    @staticmethod
    def _leadname(text):
        """
        generate person name from lead paragraph
        """
        match = re.search("'''(?P<header>.*?)'''", text)
        return match.group('header') if match else None

    @staticmethod
    def _refremove(text):
        """
        remove references from text
        """
        return re.sub("<ref.*?<\/ref>|\{\{r\|.*?\}\}|\{\{u\|.*?\}\}", '', text)

    def _leadbday(self):
        bdd = self.bbdayR.search(self.firstpar) if self.firstpar else None
        return bdd.group('bbd') if bdd else None

    def _leadbyear(self):
        bdy = self.bbdayR.search(self.firstpar) if self.firstpar else None
        return bdy.group('bby') if bdy else None

    def _leaddday(self):
        bdd = self.bddayR.search(self.firstpar) if self.firstpar else None
        return bdd.group('bdd') if bdd else None

    def _leaddyear(self):
        bdy = self.bddayR.search(self.firstpar) if self.firstpar else None
        return bdy.group('bdy') if bdy else None

    @staticmethod
    def _catbyear(text):
        cby = re.search(r"(?i)\[\[Kategoria:Urodzeni w (?P<cby>.*?)[\|\]]", text)
        return re.sub('wieku', 'wiek', cby.group('cby')) if cby else None

    @staticmethod
    def _catdyear(text):
        cdy = re.search(r"(?i)\[\[Kategoria:Zmarli w (?P<cdy>.*?)[\|\]]", text)
        return re.sub('wieku', 'wiek', cdy.group('cdy')) if cdy else None

    # Infobox methods

    @staticmethod
    def _listinfoboxes(text):
        for t, p in textlib.extract_templates_and_params(text, remove_disabled_parts=True, strip=True):
            pywikibot.output('IBoxTitle:%s' % t)
            pywikibot.output('IBoxParams:%s' % p)
            if 'infobox' in t.lower():
                return t,p
        pywikibot.output('IBoxExists:%s' % False)
        return (None, None)

    @property
    def infoboxexists(self):
        # If the infobox has been found
        return self.infoboxtitle is not None

    def _infoboxbday(self):
        if 'data urodzenia' in self.infoboxparams:
            by = self.dateR.search(self._refremove(self.infoboxparams['data urodzenia']))
            return by.group('day') if by else None
        else:
            return None

    def _infoboxbyear(self):
        if 'data urodzenia' in self.infoboxparams:
            by = self.dateR.search(self._refremove(self.infoboxparams['data urodzenia']))
            return by.group('year') if by else None
        else:
            return None

    def _infoboxdday(self):
        if 'data śmierci' in self.infoboxparams:
            dy = self.dateR.search(self._refremove(self.infoboxparams['data śmierci']))
            return dy.group('day') if dy else None
        else:
            return None

    def _infoboxdyear(self):
        if 'data śmierci' in self.infoboxparams:
            dy = self.dateR.search(self._refremove(self.infoboxparams['data śmierci']))
            return dy.group('year') if dy else None
        else:
            return None

    def _infoboxname(self):
        fields = ['imię i nazwisko', 'Imię i nazwisko']
        for p in self.infoboxparams.keys():
            pywikibot.output('IBoxParamKey: {}'.format(p))
            if p in fields:
                pywikibot.output('IBoxParamValue: {}'.format(self.infoboxparams[p]))
                return self._refremove(self.infoboxparams[p])

    # conflict methods

    @staticmethod
    def conflict(values):
        # return not (o1 == o2 == o3)
        return not all(v == values[0] for v in values)

    @property
    def nameconflict(self):
        return self.conflict((self.shorttitle, self.leadname, self.infoboxname)) if self.infoboxexists else \
            self.conflict((self.shorttitle, self.leadname))

    @property
    def birthdayconflict(self):
        return self.conflict((self.leadbyear, self.catbyear, self.infoboxbyear)) if self.infoboxexists else \
            self.conflict((self.leadbyear, self.catbyear))

    @property
    def deathdayconflict(self):
        return self.conflict((self.leaddyear, self.catdyear, self.infoboxdyear)) if self.infoboxexists else \
            self.conflict((self.leaddyear, self.catdyear))

    # table row methods

    @staticmethod
    def paramrow(conflict, color, values):
        separator = ' || style="background-color:{}" | '.format(color) if conflict else ' || '
        return separator + separator.join(item or '' for item in values)

    def namerow(self):
        return self.paramrow(self.nameconflict, '#cff', (self.shorttitle, self.leadname, self.infoboxname))

    def bdaterow(self):
        return self.paramrow(self.birthdayconflict, '#6fc', (self.leadbdate, self.catbyear, self.infoboxbdate))

    def ddaterow(self):
        return self.paramrow(self.deathdayconflict, '#ffc', (self.leadddate, self.catdyear, self.infoboxddate))

