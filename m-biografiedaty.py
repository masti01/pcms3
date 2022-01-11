#!/usr/bin/python3
"""

Use global -simulate option for test purposes. No changes to live wiki
will be done.


The following parameters are supported:

-always           The bot won't ask for confirmation when putting a page

-text:            Use this text to be added; otherwise 'Test' is used

-replace:         Don't add text but replace it

-top              Place additional text on top of the page

-summary:         Set the action summary message for the edit.

This sample script is a
:py:obj:`ConfigParserBot <pywikibot.bot.ConfigParserBot>`. All settings can be
made either by giving option with the command line or with a settings file
which is scripts.ini by default. If you don't want the default values you can
add any option you want to change to that settings file below the [basic]
section like:

    [basic] ; inline comments starts with colon
    # This is a commend line. Assignments may be done with '=' or ':'
    text: A text with line break and
        continuing on next line to be put
    replace: yes ; yes/no, on/off, true/false and 1/0 is also valid
    summary = Bot: My first test edit with pywikibot

Every script has its own section with the script name as header.

In addition the following generators and filters are supported but
cannot be set by settings file:

&params;
"""
#
# (C) Pywikibot team, 2006-2021
#
# Distributed under the terms of the MIT license.
#
import pywikibot
from pywikibot import pagegenerators
from pywikibot.bot import (
    AutomaticTWSummaryBot,
    ConfigParserBot,
    ExistingPageBot,
    NoRedirectPageBot,
    SingleSiteBot,
)
import re
from collections import OrderedDict

# This is required for the text that is shown when you run this script
# with the parameter -help.
docuReplacements = {'&params;': pagegenerators.parameterHelp}  # noqa: N816

class BioInfobox():
    def __init__(self,page):
        self.dateR = re.compile(
            r'(?i)((\[{2})?(?P<day>\d{1,2} [\wśńź]{4,12})(\]{2})?)?\s*?(\[{2})?(?P<year>\d{1,4})(\]{2})?')
        self.infoboxtitle, self.infoboxparams = self._listinfoboxes(page)
        self.infoboxbday = self._infoboxbday()
        self.infoboxbyear = self._infoboxbyear()
        self.infoboxdday =  self._infoboxdday()
        self.infoboxdyear = self._infoboxdyear()

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    @staticmethod
    def _refremove(text):
        """
        remove references from text
        """
        return re.sub("<ref.*?<\/ref>|\{\{r\|.*?\}\}|\{\{u\|.*?\}\}", '', text)

    def _listinfoboxes(self,page):
        par = OrderedDict()
        for t, p in page.templatesWithParams():
            if 'infobox' in t.title().lower():
                pcount = 0
                for pv in p:
                    if '=' in pv:
                        par[(pv.split('=', 1))[0]] = pv.split('=', 1)[1]
                    else:
                        par[str(pcount)] = pv
                    pcount += 1

                return t.title(with_ns=False), par
        return None

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

class Biography:
    bbdayR = re.compile(
        r'(?i)ur\.\s*((\[{2})?(?P<bbd>\d{1,2} [\wśńź]{4,12})(\]{2})?)?\s*?(\[{2})?(?P<bby>\d{1,4})(\]{2})?')
    bddayR = re.compile(
        r"(?i)zm\.(\s*w)?(\s*(\[{2})?(?P<bdd>\d{1,2} [\wśńź]{4,12})(\]{2})?)?\s*?(\[{2})?(?P<bdy>\d{4})(\]{2})?")

    def __init__(self, page: pywikibot.Page):

        # general
        self.shorttitle = page.title(without_brackets=True)
        self.norefstext = self._refremove(page.text)
        # first paragraph (lead) info
        self.firstpar = self._firstpar(page)
        self.leadname = self._leadname(self.firstpar)
        self.leadbday = self._leadbday() if self._leadbday() else ''
        self.leadbyear = self._leadbyear() if self._leadbyear() else ''
        self.leadbdate = ('%s %s' % (self.leadbday, self.leadbyear)).strip()
        # self.leaddday = self._leaddday() if self._leaddday() else ''
        self.leaddday = self._leaddday()
        self.leaddyear = self._leaddyear()
        # self.leaddyear = self._leaddyear() if self._leaddyear() else ''
        self.leadddate = ('%s %s' % (self.leaddday, self.leaddyear)).strip()
        # categories info
        self.catbyear = self._catbyear(self.norefstext)
        self.catdyear = self._catdyear(self.norefstext)

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    def __str__(self):
        r = "Class:%s" % self.__class__
        for a in self.__dict__:
            r += '\n%s:%s' % (a, self.__dict__[a])
        return r

    @staticmethod
    def _firstpar(page):
        """
        return first paragraf (lead) of page
        """
        return re.search("(^|\n)(?P<firstpar>'''.*\n)", page.text).group('firstpar')

    @staticmethod
    def _leadname(text):
        """
        generate person name from lead paragraph
        """
        return re.search("'''(?P<header>.*?)'''", text).group('header')

    @staticmethod
    def _refremove(text):
        """
        remove references from text
        """
        return re.sub("<ref.*?<\/ref>|\{\{r\|.*?\}\}|\{\{u\|.*?\}\}", '', text)

    def _leadbday(self):
        bdd = self.bbdayR.search(self.firstpar)
        return bdd.group('bbd') if bdd else None

    def _leadbyear(self):
        bdy = self.bbdayR.search(self.firstpar)
        return bdy.group('bby') if bdy else None

    def _leaddday(self):
        bdd = self.bddayR.search(self.firstpar)
        return bdd.group('bdd') if bdd else None

    def _leaddyear(self):
        bdy = self.bddayR.search(self.firstpar)
        return bdy.group('bdy') if bdy else None

    @staticmethod
    def _catbyear(text):
        cby = re.search(r"(?i)\[\[Kategoria:Urodzeni w (?P<cby>.*?)[\|\]]", text)
        return cby.group('cby') if cby else None

    @staticmethod
    def _catdyear(text):
        cdy = re.search(r"(?i)\[\[Kategoria:Zmarli w (?P<cdy>.*?)[\|\]]", text)
        return cdy.group('cdy') if cdy else None



class BasicBot(
    # Refer pywikobot.bot for generic bot classes
    SingleSiteBot,  # A bot only working on one site
    ConfigParserBot,  # A bot which reads options from scripts.ini setting file
    # CurrentPageBot,  # Sets 'current_page'. Process it in treat_page method.
    #                  # Not needed here because we have subclasses
    ExistingPageBot,  # CurrentPageBot which only treats existing pages
    NoRedirectPageBot,  # CurrentPageBot which only treats non-redirects
    AutomaticTWSummaryBot,  # Automatically defines summary; needs summary_key
):
    """
    An incomplete sample bot.

    :ivar summary_key: Edit summary message key. The message that should be
        used is placed on /i18n subdirectory. The file containing these
        messages should have the same name as the caller script (i.e. basic.py
        in this case). Use summary_key to set a default edit summary message.

    :type summary_key: str
    """

    summary_key = 'basic-changing'

    update_options = {
        'replace': False,  # delete old text and write the new text
        'summary': None,  # your own bot summary
        'text': 'Test',  # add this text from option. 'Test' is default
        'top': False,  # append text on top of the page
        'outpage': 'User:mastiBot/test',  # default output page
        'maxlines': 1000,  # default number of entries per page
        'test': False,  # switch on test functionality
    }

    def run(self):

        footer = '\n|}\n'

        finalpage = self.header()
        licznik = 0
        wiersz = 0
        # pagelist = [page for page in self.generator]

        # pagelist.sort()
        # for page in pagelist:
        for page in self.generator:
            licznik += 1
            # finalpage = finalpage + self.treat(page)
            pywikibot.output(
                'Processing page #%s (%s marked): %s' % (str(licznik), str(wiersz), page.title(as_link=True)))
            result = self.treat(page)
            if not result == '':
                wiersz += 1
                finalpage += '\n|-\n| ' + str(wiersz) + ' || ' + result
                pywikibot.output('Added line #%i: %s' % (wiersz, '\n|-\n| ' + str(wiersz) + ' || ' + result))
            # pywikibot.output(finalpage)
        finalpage += footer
        finalpage += '\nPrzetworzono stron: ' + str(licznik)

        finalpage = self.przypisy(finalpage)

        # Save page
        # pywikibot.output(finalpage)
        outpage = pywikibot.Page(pywikibot.Site(), self.opt.outpage)
        outpage.text = finalpage
        outpage.save(summary=self.opt.summary)

    def header(self):
        # prepare new page with table
        header = (
            "Ta strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|bota]]. Ostatnia aktualizacja ~~~~~. "
            "Wszelkie uwagi proszę zgłaszać w [[Dyskusja_Wikipedysty:Masti|dyskusji operatora]]."
            ""
            "Strona zawiera artykuły, w których wykryto niezgodność nazwisk lub lat urodzenia/śmierci."
            "<small>"
            "; Legenda:"
            ":; Nazwisko"
            ":: - '''Tytuł''' - tytuł artykułu bez wyróżników w nawiasie"
            ":: - '''Nagłówek''' - nazwisko w pierwszym akapicie artykułu"
            ":: - '''Infobox''' - nazwisko w infoboksie"
            ":; Data urodzenia"
            ":: - '''Nagłówek''' - data urodzenia w pierwszym akapicie artykułu"
            ":: - '''Kategoria''' - data urodzenia w kategori Urodzeni w ..."
            ":: - '''Infobox''' - data urodzenia w infoboksie"
            ":; Data śmierci"
            ":: - '''Nagłówek''' - data śmierci w pierwszym akapicie artykułu"
            ":: - '''Kategoria''' - data śmierci w kategori Urodzeni w ..."
            ":: - '''Infobox''' - data śmierci w infoboksie"
            ": '''Infobox''' - infobox, z którego pobrano dane"
            "</small>"
            '{| class="wikitable" style="font-size:85%;"'
            "|-"
            "! rowspan=2 | Lp."
            "! colspan=3 | Nazwisko"
            "! colspan=3 | Data urodzenia"
            "! colspan=3 | Data śmierci"
            "! rowspan=2 | Infobox"
            "|-"
            "!Tytuł"
            "!Nagłówek"
            "!Infobox"
            "!Nagłówek"
            "!Kategoria"
            "!Infobox"
            "!Nagłówek"
            "!Kategoria"
            "!Infobox"
        )

        return (header)

    def przypisy(self, text):
        """
        Searches text for references, adds {{Przypisy}} if found.
        """

        # przypisy?
        refR = re.compile(r'(?P<ref>(<ref|\{\{r))', flags=re.I)
        refs = refR.finditer(text)  # ptitleR.search(pagetitle).group('ptitle')
        reffound = False
        for ref in refs:
            reffound = True
            break
        if reffound:
            text += '\n\n{{Przypisy}}'
            return (text)

    def treat(self, page):
        """
        Loads the given page, looks for interwikis
        """
        found = False
        rowtext = ''

        bc = Biography(page)
        # pywikibot.output(bc)
        pywikibot.output('*************************************')
        pywikibot.output('ShortTitle:%s' % bc.shorttitle)
        pywikibot.output('LeadName:%s' % bc.leadname)
        pywikibot.output('*************************************')
        pywikibot.output('LeadBDay:%s' % bc.leadbday)
        pywikibot.output('LeadBYear:%s' % bc.leadbyear)
        pywikibot.output('LeadBDate:%s' % bc.leadbdate)
        pywikibot.output('*************************************')
        pywikibot.output('LeadDDay:%s' % bc.leaddday)
        pywikibot.output('LeadDYear:%s' % bc.leaddyear)
        pywikibot.output('LeadDDate:%s' % bc.leadddate)
        pywikibot.output('*************************************')
        pywikibot.output('CatBYear:%s' % bc.catbyear)
        pywikibot.output('CatDYear:%s' % bc.catdyear)
        pywikibot.output('*************************************')

        bi = BioInfobox(page)
        pywikibot.output('*************************************')
        pywikibot.output('BioInfobox:%s' % bi.__repr__())
        pywikibot.output('*************************************')
        pywikibot.output('BioInfobox:%s' % bi.infoboxtitle)
        pywikibot.output('BioInfobox:%s' % bi.infoboxparams.keys())
        pywikibot.output('*************************************')
        pywikibot.output('BioIboxBDay:%s' % bi.infoboxbday)
        pywikibot.output('BioIboxBYear:%s' % bi.infoboxbyear)
        pywikibot.output('BioIboxDDay:%s' % bi.infoboxdday)
        pywikibot.output('BioIboxDYear:%s' % bi.infoboxdyear)
        pywikibot.output('*************************************')

        return '' # temporary

        text = self.refremove(page.text)

        firstpars = self.firstpar(page)

        # page title no disambig
        """
        ptitleR = re.compile(r'(?P<ptitle>.*?) \(')
        pagetitle = page.title()
        if '(' in pagetitle:
            ptitle = ptitleR.search(pagetitle).group('ptitle')
        else:
            ptitle = pagetitle
        """
        ptitle = page.title(without_brackets=True)
        pywikibot.output('PTitle (no disambig): %s' % ptitle)

        # bolded header
        bheaderR = re.compile(r"(^|\n)'''(?P<header>.*?)'''", flags=re.I)
        bheaders = ''
        firstline = True
        linki = bheaderR.finditer(firstpars)
        for bheader in linki:
            found = True
            pywikibot.output('Header: %s' % bheader.group('header'))
            if firstline:
                firstline = False
                bheaders += bheader.group('header')
            else:
                bheaders += '<br />' + bheader.group('header')
            break

        # bolded birthday  ur\.\s*(\[\[)?\d*\s*\w*(\]\])?\s*(\[\[)?\d*
        bbdayR = re.compile(
            r"ur\.(\s*w)?(\s*(\[{2})?(?P<bbd>\d{1,2} [\wśńź]{4,12})(\]{2})?)?\s*?(\[{2})?(?P<bby>\d{4})(\]{2})?",
            flags=re.I)
        bbd = ''
        bby = ''
        firstline = True
        linki = bbdayR.finditer(firstpars)
        for bday in linki:
            found = True
            pywikibot.output('BDAY: %s %s' % (bday.group('bbd'), bday.group('bby')))
            if not bday.group('bbd') == None:
                bbd = bday.group('bbd')
            if not bday.group('bby') == None:
                bby = bday.group('bby')
                pywikibot.output('BDAY set: %s %s' % (bbd, bby))
                break

        # bolded death
        bddayR = re.compile(
            r"zm\.(\s*w)?(\s*(\[{2})?(?P<bdd>\d{1,2} [\wśńź]{4,12})(\]{2})?)?\s*?(\[{2})?(?P<bdy>\d{4})(\]{2})?",
            flags=re.I)
        bdd = ''
        bdy = ''
        firstline = True
        linki = bddayR.finditer(firstpars)
        for dday in linki:
            found = True
            pywikibot.output('DDAY: %s %s' % (dday.group('bdd'), dday.group('bdy')))
            if not dday.group('bdd') == None:
                bdd = dday.group('bdd')
            if not dday.group('bdy') == None:
                bdy = dday.group('bdy')
                pywikibot.output('DDAY set: %s %s' % (bdd, bdy))
                break

        # Category birthyear
        cbyearR = re.compile(r"\[\[Kategoria:Urodzeni w (?P<cby>.*?)[\|\]]")
        cby = ''
        firstline = True
        linki = cbyearR.finditer(text)
        for cbyear in linki:
            found = True
            # pywikibot.output('CATBYEAR: %s' % cbyear.group('cby'))
            cby = cbyear.group('cby')
            pywikibot.output('CATBYEAR: %s' % cby)
            break

        # Category deathyear
        cdyearR = re.compile(r"\[\[Kategoria:Zmarli w (?P<cdy>.*?)[\|\]]")
        cdy = ''
        firstline = True
        linki = cdyearR.finditer(text)
        for cdyear in linki:
            found = True
            # pywikibot.output('CATDYEAR: %s' % cdyear.group('cdy'))
            cdy = cdyear.group('cdy')
            pywikibot.output('CATDYEAR: %s' % cdy)
            break

        # infobox name & title
        firstline = True
        infoboxs = ''
        iboxname = ''
        iboxbd = ''
        iboxby = ''
        iboxdd = ''
        iboxdy = ''
        infoboxtitle = ''
        infoboxtR = re.compile(r"\{\{(?P<iboxtitle>.*) infobox", flags=re.I)
        infoboxnR = re.compile(
            r"^(Imię i nazwisko|Imię|polityk|imięinazwisko|imię i nazwisko|imięnazwisko)\s*=\s*(?P<iboxname>.*)",
            flags=re.I)
        infoboxbdR = re.compile(
            r"^(data urodzenia|dataurodzenia|data i miejsce urodzenia)\s*=(\s*(\[{2})?(?P<iboxbd>\d{1,2} [\wśńź]{4,12})(\]{2})?)?\s*?(\[{2})?(?P<iboxby>\d{4})(\]{2})?",
            flags=re.I)
        infoboxddR = re.compile(
            r"^(data śmierci|dataśmierci|data i miejsce śmierci)\s*=(\s*(\[{2})?(?P<iboxdd>\d{1,2} [\wśńź]{4,12})(\]{2})?)?\s*?(\[{2})?(?P<iboxdy>\d{4})(\]{2})?",
            flags=re.I)
        infoboxnumber = 0
        infoboxskip = False
        for t, args in page.templatesWithParams():
            pywikibot.output('Template: %s' % t.title())
            if 'infobox' in t.title(with_ns=False) and '/' not in t.title(with_ns=False):
                iboxname = ''
                iboxbd = ''
                iboxby = ''
                iboxdd = ''
                iboxdy = ''
                infoboxnumber += 1
                if infoboxskip:
                    break
                for p in args:
                    p = self.refremove(p)
                pywikibot.output(p)
                # name in infobox
                arglist = infoboxnR.finditer(p)
                for arg in arglist:
                    pywikibot.output('ARG: %s' % arg.group('iboxname'))
                    iboxname = arg.group('iboxname')
                    # birthdate and year in infobox
                    arglist = infoboxbdR.finditer(p)
                for arg in arglist:
                    pywikibot.output('ARG: %s %s' % (arg.group('iboxbd'), arg.group('iboxby')))
                    if not arg.group('iboxbd') == None:
                        iboxbd = arg.group('iboxbd')
                    if not arg.group('iboxby') == None:
                        iboxby = arg.group('iboxby')
                        # deathdate and year in infobox
                    arglist = infoboxddR.finditer(p)
                for arg in arglist:
                    pywikibot.output('ARG: %s %s' % (arg.group('iboxdd'), arg.group('iboxdy')))
                    if not arg.group('iboxdd') == None:
                        iboxdd = arg.group('iboxdd')
                    if not arg.group('iboxdy') == None:
                        iboxdy = arg.group('iboxdy')
                pywikibot.output('iboxname: %s' % iboxname)
                pywikibot.output('iboxbd: %s' % iboxbd)
                pywikibot.output('iboxby: %s' % iboxby)
                pywikibot.output('iboxdd: %s' % iboxdd)
                pywikibot.output('iboxdy: %s' % iboxdy)

        # if firstline:
        #   firstline = False
        # else:
        #   infoboxs += '<br />'
        # infoboxs += t + '=>' + iboxname + '=>' + iboxbd + ' ' + iboxby + '=>' + iboxdd + ' ' + iboxdy
        infoboxs += t.title(
            with_ns=False) + ' || ' + iboxname + ' || ' + iboxbd + ' ' + iboxby + ' || ' + iboxdd + ' ' + iboxdy
        infoboxtitle = t.title(with_ns=False)
        infoboxskip = True

        # write result
        ToBeMarked = False
        pywikibot.output('ptitle: %s' % ptitle)
        pywikibot.output('bheaders: %s' % bheaders)
        pywikibot.output('infoboxskip: %s' % infoboxskip)
        if not iboxname == ptitle or not iboxname == bheaders:
            cond1 = True
        else:
            cond1 = False
        pywikibot.output('Condition1: %s' % cond1)
        pywikibot.output('Condition2: %s' % (infoboxskip and cond1))
        if not ptitle == bheaders or (infoboxskip and (not iboxname == ptitle or not iboxname == bheaders)):
            ToBeMarked = True
            pywikibot.output('ToBeMarked: title vs bolded header')
            ptitle = 'style="background-color:PowderBlue" | ' + ptitle
            bheaders = 'style="background-color:PowderBlue" | ' + bheaders
            iboxname = 'style="background-color:PowderBlue" | ' + iboxname
        if not bby == cby or (infoboxskip and (not iboxby == bby or not iboxby == cby)):
            ToBeMarked = True
            pywikibot.output('ToBeMarked: Bolded BY vs cat BY')
            bby = 'style="background-color:Lime" | ' + bby
            cby = 'style="background-color:Lime" | ' + cby
            iboxbd = 'style="background-color:Lime" | ' + iboxbd
        if not bdy == cdy or (infoboxskip and (not iboxdy == bdy or not iboxdy == cdy)):
            ToBeMarked = True
            pywikibot.output('ToBeMarked: Bolded DY vs cat DY')
            bdy = 'style="background-color:Orange" | ' + bdy
            cdy = 'style="background-color:Orange" | ' + cdy
            iboxdd = 'style="background-color:Orange" | ' + iboxdd
        if ToBeMarked:
            pageiw = '[[:' + page.title(
                with_ns=False) + ']] || ' + bheaders + ' || ' + bbd + ' ' + bby + ' || ' + bdd + ' ' + bdy + ' || ' + cby + ' || ' + cdy + ' || ' + \
                     str(infoboxnumber) + ' || ' + infoboxtitle + ' || ' + iboxname + ' || ' + iboxbd + ' ' + iboxby + ' || ' + iboxdd + ' ' + iboxdy
        else:
            pageiw = ''

            # test print
            pywikibot.output(u"%s" % pageiw)

        return (pageiw)

    def load(self, page):
        """
        Loads the given page, does some changes, and saves it.
        """
        try:
            # Load the page
            text = page.get()
        except pywikibot.exceptions.NoPageError:
            pywikibot.output(u"Page %s does not exist; skipping."
                             % page.title(as_link=True))
        except pywikibot.exceptions.IsRedirectPageError:
            pywikibot.output(u"Page %s is a redirect; skipping."
                             % page.title(as_link=True))
        else:
            return text
        return None

    def save(self, text, page, comment=None, minorEdit=True,
             botflag=True):
        # only save if something was changed
        try:
            pagetext = page.get()
        except:
            pagetext = ''
            if text != pagetext:
                # Show the title of the page we're working on.
                # Highlight the title in purple.
                pywikibot.output(u"\n\n>>> \03{lightpurple}%s\03{default} <<<"
                                 % page.title())
                # show what was changed
                pywikibot.showDiff(pagetext, text)
                pywikibot.output('Comment: %s' % comment)
                # choice = pywikibot.inputChoice(
                #    'Do you want to accept these changes?',
                #    ['Yes', 'No'], ['y', 'N'], 'N')
                try:
                    # Save the page
                    page.put(text, comment=comment or self.comment,
                             minorEdit=minorEdit, botflag=botflag)
                except pywikibot.exceptions.LockedPageError:
                    pywikibot.output(u"Page %s is locked; skipping."
                                     % page.title(as_link=True))
                except pywikibot.exceptions.EditConflictError:
                    pywikibot.output(
                        'Skipping %s because of edit conflict'
                        % (page.title()))
                except pywikibot.exceptions.SpamblacklistError as error:
                    pywikibot.output('Cannot change %s because of spam blacklist entry %s'
                                     % (page.title(), error.url))
                else:
                    return True
        return False


def main(*args: str) -> None:
    """
    Process command line arguments and invoke bot.

    If args is an empty list, sys.argv is used.

    :param args: command line arguments
    """
    options = {}
    # Process global arguments to determine desired site
    local_args = pywikibot.handle_args(args)

    # This factory is responsible for processing command line arguments
    # that are also used by other scripts and that determine on which pages
    # to work on.
    gen_factory = pagegenerators.GeneratorFactory()

    # Process pagegenerators arguments
    local_args = gen_factory.handle_args(local_args)

    # Parse your own command line arguments
    for arg in local_args:
        arg, sep, value = arg.partition(':')
        option = arg[1:]
        if option in ('summary', 'text', 'outpage', 'maxlines'):
            if not value:
                pywikibot.input('Please enter a value for ' + arg)
            options[option] = value
        # take the remaining options as booleans.
        # You will get a hint if they aren't pre-defined in your bot class
        else:
            options[option] = True

    # The preloading option is responsible for downloading multiple
    # pages from the wiki simultaneously.
    gen = gen_factory.getCombinedGenerator(preload=True)
    if gen:
        # pass generator and private options to the bot
        bot = BasicBot(generator=gen, **options)
        bot.run()  # guess what it does
    else:
        pywikibot.bot.suggest_help(missing_generator=True)


if __name__ == '__main__':
    main()
