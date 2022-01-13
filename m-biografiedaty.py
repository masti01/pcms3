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
        self.firstpar = self._firstpar(page)
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
        self.infoboxtitle, self.infoboxparams = self._listinfoboxes(page)
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
    def _firstpar(page):
        """
        return first paragraf (lead) of page
        """
        match = re.search("(^|\n)(?P<firstpar>'''.*\n)", page.text)
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
        return cby.group('cby') if cby else None

    @staticmethod
    def _catdyear(text):
        cdy = re.search(r"(?i)\[\[Kategoria:Zmarli w (?P<cdy>.*?)[\|\]]", text)
        return cdy.group('cdy') if cdy else None

    # Infobox methods

    @staticmethod
    def _listinfoboxes(page):
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
        return (None, None)

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
        if 'imię i nazwisko' in self.infoboxparams:
            return self._refremove(self.infoboxparams['imię i nazwisko']).strip()

    # conflict methods

    def conflict(self, values):
        # return not (o1 == o2 == o3)
        return not all(v == values[0] for v in values)

    @property
    def nameconflict(self):
        return self.conflict((self.shorttitle, self.leadname, self.infoboxname))

    @property
    def birthdayconflict(self):
        return self.conflict((self.leadbyear, self.catbyear, self.infoboxbyear))

    @property
    def deathdayconflict(self):
        return self.conflict((self.leaddyear, self.catdyear, self.infoboxdyear))

    # table row methods

    @staticmethod
    def paramrow(conflict, color, values):
        separator = f' || style="background-color:{color}" | ' if conflict else ' || '
        return separator + separator.join(item or '' for item in values)

    def namerow(self):
        return self.paramrow(self.nameconflict, '#6cf', (self.shorttitle, self.leadname, self.infoboxname))

    def bdaterow(self):
        return self.paramrow(self.birthdayconflict, '#6fc', (self.leadbdate, self.catbyear, self.infoboxbdate))

    def ddaterow(self):
        return self.paramrow(self.deathdayconflict, '#ffc', (self.leadddate, self.catdyear, self.infoboxddate))

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
        pagecounter = 0
        rowcounter = 0
        # pagelist = [page for page in self.generator]

        # pagelist.sort()
        # for page in pagelist:
        for page in self.generator:
            pagecounter += 1
            # finalpage = finalpage + self.treat(page)
            pywikibot.output(
                'Processing page #%s (%s marked): %s' % (str(pagecounter), str(rowcounter), page.title(as_link=True)))
            if page.isRedirectPage() or page.isDisambig():
                continue
            result = self.treat(page)
            if result:
                rowcounter += 1
                finalpage += '\n|-\n| {} || {} {}'.format(rowcounter, page.title(as_link=True), result)
                pywikibot.output('Added line #%i: %s' % (rowcounter, '\n|-\n| {} || {} || {}'.format(rowcounter, page.title(as_link=True), result)))
                # pywikibot.output('Added line #%i: %s' % (rowcounter, '\n|-\n| ' + str(rowcounter) + ' || ' + result))

        finalpage += footer
        finalpage += '\nPrzetworzono stron: ' + str(pagecounter)

        finalpage += self.przypisy(finalpage)

        # Save page
        # pywikibot.output(finalpage)
        outpage = pywikibot.Page(pywikibot.Site(), self.opt.outpage)
        outpage.text = finalpage
        outpage.save(summary=self.opt.summary)

    def header(self):
        # prepare new page with table
        return (
            "\nTa strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|bota]]. Ostatnia aktualizacja ~~~~~. "
            "\nWszelkie uwagi proszę zgłaszać w [[Dyskusja_Wikipedysty:Masti|dyskusji operatora]]."
            "\n"
            "\nStrona zawiera artykuły, w których wykryto niezgodność nazwisk lub lat urodzenia/śmierci."
            "\n<small>"
            "\n; Legenda:"
            "\n:; Nazwisko"
            "\n:: - '''Tytuł''' - tytuł artykułu bez wyróżników w nawiasie"
            "\n:: - '''Nagłówek''' - nazwisko w pierwszym akapicie artykułu"
            "\n:: - '''Infobox''' - nazwisko w infoboksie"
            "\n:; Data urodzenia"
            "\n:: - '''Nagłówek''' - data urodzenia w pierwszym akapicie artykułu"
            "\n:: - '''Kategoria''' - data urodzenia w kategori Urodzeni w ..."
            "\n:: - '''Infobox''' - data urodzenia w infoboksie"
            "\n:; Data śmierci"
            "\n:: - '''Nagłówek''' - data śmierci w pierwszym akapicie artykułu"
            "\n:: - '''Kategoria''' - data śmierci w kategori Urodzeni w ..."
            "\n:: - '''Infobox''' - data śmierci w infoboksie"
            "\n: '''Infobox''' - infobox, z którego pobrano dane"
            "\n</small>"
            '\n{| class="wikitable" style="font-size:85%; text-align:center; vertical-align:middle; "'
            "\n|-"
            "\n! rowspan=2 | Lp."
            "\n! rowspan=2 | Artykuł"
            "\n! colspan=3 | Nazwisko"
            "\n! colspan=3 | Data urodzenia"
            "\n! colspan=3 | Data śmierci"
            "\n! rowspan=2 | Infobox"
            "\n|-"
            "\n!Tytuł"
            "\n!Nagłówek"
            "\n!Infobox"
            "\n!Nagłówek"
            "\n!Kategoria"
            "\n!Infobox"
            "\n!Nagłówek"
            "\n!Kategoria"
            "\n!Infobox"
        )


    @staticmethod
    def przypisy(text) -> str:
        """
        Searches text for references, adds {{Przypisy}} if found.
        """
        return '\n\n== Przypisy ==\n{{Przypisy}}' if re.search(r'(?i)<ref|\{\{(r|u)', text) else ''

    def treat(self, page) -> str:
        """
        Loads the given page, performs action
        """
        found = False
        rowtext = ''

        bc = Biography(page)

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

        pywikibot.output('BioInfobox:%s' % bc.infoboxtitle)
        pywikibot.output('BioInfobox:%s' % bc.infoboxparams.keys() if bc.infoboxparams else None)
        pywikibot.output('*************************************')
        pywikibot.output('BioIboxName:%s' % bc.infoboxname)
        pywikibot.output('BioIboxBDay:%s' % bc.infoboxbday)
        pywikibot.output('BioIboxBYear:%s' % bc.infoboxbyear)
        pywikibot.output('BioIboxDDay:%s' % bc.infoboxdday)
        pywikibot.output('BioIboxDYear:%s' % bc.infoboxdyear)
        pywikibot.output('*************************************')
        pywikibot.output('name Conflict:%s' % bc.nameconflict)
        pywikibot.output('bday Conflict:%s' % bc.birthdayconflict)
        pywikibot.output('dday Conflict:%s' % bc.deathdayconflict)
        pywikibot.output('*************************************')
        pywikibot.output('row test name:%s' % bc.namerow())
        pywikibot.output('row test bdate:%s' % bc.bdaterow())
        pywikibot.output('row test ddate:%s' % bc.ddaterow())
        pywikibot.output('*************************************')

        return None if not bc.isconflicted else "{names}{bdate}{ddate} || {ibox}".format(
            names=bc.namerow(),
            bdate=bc.bdaterow(),
            ddate=bc.ddaterow(),
            ibox= '{{{{s|{}}}}}'.format(bc.infoboxtitle) if bc.infoboxtitle else '' )


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
