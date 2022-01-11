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


# This is required for the text that is shown when you run this script
# with the parameter -help.
docuReplacements = {'&params;': pagegenerators.parameterHelp}  # noqa: N816


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

        footer = u'\n|}\n'

        finalpage = self.prepareheader()
        licznik = 0
        wiersz = 0
        # pagelist = [page for page in self.generator]

        # pagelist.sort()
        # for page in pagelist:
        for page in self.generator:
            licznik += 1
            # finalpage = finalpage + self.treat(page)
            pywikibot.output(u'Processing page #%s (%s marked): %s' % (str(licznik), str(wiersz), page.title(as_link=True)))
            result = self.treat(page)
            if not result == u'':
                wiersz += 1
                finalpage += u'\n|-\n| ' + str(wiersz) + u' || ' + result
                pywikibot.output(u'Added line #%i: %s' % (wiersz, u'\n|-\n| ' + str(wiersz) + u' || ' + result))
            # pywikibot.output(finalpage)
        finalpage += footer
        finalpage += u'\nPrzetworzono stron: ' + str(licznik)
    
        finalpage = self.przypisy(finalpage)
    
        # Save page
        # pywikibot.output(finalpage)
        outpage = pywikibot.Page(pywikibot.Site(), self.opt.outpage)
        outpage.text = finalpage
        outpage.save(summary=self.opt.summary)
        

    def prepareheader(self):
        # prepare new page with table
        header = u"Ta strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|bota]]. Ostatnia aktualizacja ~~~~~. \nWszelkie uwagi proszę zgłaszać w [[Dyskusja_Wikipedysty:Masti|dyskusji operatora]]."
        header += u"\n\nStrona zawiera artykuły, w których wykryto niezgodność nazwisk lub lat urodzenia/śmierci."
        header += u"\n<small>"
        header += u"\n*Legenda:"
        header += u"\n*:'''Hasło''' - Tytuł hasła"
        header += u"\n*:'''Nagłówek''' - Nazwa wyróżniona"
        header += u"\n*:'''Data urodzenia''' - Data urodzenia w nagłówku"
        header += u"\n*:'''Data śmierci''' - Data śmierci w nagłówku"
        header += u"\n*:'''Kategoria Urodzeni w''' - Rok w kategorii urodzonych"
        header += u"\n*:'''Kategoria zmarli w''' - Rok w kategorii zmarłych"
        header += u"\n*:'''Infoboksy''' - liczba infoboksów"
        header += u"\n*:'''Infobox''' - tytuł infoboksu"
        header += u"\n*:'''Nazwisko w infoboksie'''"
        header += u"\n*:'''Data urodzenia w infoboksie'''"
        header += u"\n*:'''Data śmierci w infoboksie'''"
        header += u"\n</small>\n"
        header += u'{| class="wikitable" style="font-size:85%;"\n|-\n!Lp.\n!Hasło\n!Nagłówek\n!Data urodzenia\n!Data śmierci\n'
        header += u'!Kategoria<br />Urodzeni w\n!Kategoria<br />zmarli w\n!Infoboksy\n!Infobox\n!Nazwisko<br />w infoboksie\n!Data urodzenia<br />w infoboksie\n!Data śmierci<br />w infoboksie'
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
            text += u'\n\n{{Przypisy}}'
            return (text)
    
    
    def refremove(self, intext):
        """
        remove references from text
        """
        refR = re.compile(r'(<ref.*?<\/ref>|\{\{r\|.*?\}\}|\{\{u\|.*?\}\})')
        output = re.sub(refR, u'', intext)
        # pywikibot.output(output)
        return (output)
    
    
    def treat(self, page):
        """
        Loads the given page, looks for interwikis
        """
        found = False
        rowtext = u''
        textload = self.load(page)
        if not textload:
            return (u'')
    
        text = self.refremove(textload)
        # pywikibot.output(text)

        # First paragraph
        firstparR = re.compile(r"(^|\n)(?P<firstpar>'''.*\n)")
        firstpars = u''
        firstline = True
        linki = firstparR.finditer(text)
        for firstpar in linki:
            found = True
            pywikibot.output(u'Firstpar: %s' % firstpar.group('firstpar'))
            break
        if found:
            firstpars = firstpar.group('firstpar')
        
        # page title no disambig
        ptitleR = re.compile(r'(?P<ptitle>.*?) \(')
        pagetitle = page.title()
        if u'(' in pagetitle:
            ptitle = ptitleR.search(pagetitle).group('ptitle')
        else:
            ptitle = pagetitle
        pywikibot.output(u'PTitle (no disambig): %s' % ptitle)
        
        # bolded header
        bheaderR = re.compile(r"(^|\n)'''(?P<header>.*?)'''", flags=re.I)
        bheaders = u''
        firstline = True
        linki = bheaderR.finditer(firstpars)
        for bheader in linki:
            found = True
            pywikibot.output(u'Header: %s' % bheader.group('header'))
            if firstline:
                firstline = False
                bheaders += bheader.group('header')
            else:
                bheaders += u'<br />' + bheader.group('header')
            break
        
        # bolded birthday  ur\.\s*(\[\[)?\d*\s*\w*(\]\])?\s*(\[\[)?\d*
        bbdayR = re.compile(
            r"ur\.(\s*w)?(\s*(\[{2})?(?P<bbd>\d{1,2} [\wśńź]{4,12})(\]{2})?)?\s*?(\[{2})?(?P<bby>\d{4})(\]{2})?", flags=re.I)
        bbd = u''
        bby = u''
        firstline = True
        linki = bbdayR.finditer(firstpars)
        for bday in linki:
            found = True
            pywikibot.output(u'BDAY: %s %s' % (bday.group('bbd'), bday.group('bby')))
            if not bday.group('bbd') == None:
                bbd = bday.group('bbd')
            if not bday.group('bby') == None:
                bby = bday.group('bby')
                pywikibot.output(u'BDAY set: %s %s' % (bbd, bby))
                break
        
        # bolded death
        bddayR = re.compile(
            r"zm\.(\s*w)?(\s*(\[{2})?(?P<bdd>\d{1,2} [\wśńź]{4,12})(\]{2})?)?\s*?(\[{2})?(?P<bdy>\d{4})(\]{2})?", flags=re.I)
        bdd = u''
        bdy = u''
        firstline = True
        linki = bddayR.finditer(firstpars)
        for dday in linki:
            found = True
            pywikibot.output(u'DDAY: %s %s' % (dday.group('bdd'), dday.group('bdy')))
            if not dday.group('bdd') == None:
                bdd = dday.group('bdd')
            if not dday.group('bdy') == None:
                bdy = dday.group('bdy')
                pywikibot.output(u'DDAY set: %s %s' % (bdd, bdy))
                break
        
        # Category birthyear
        cbyearR = re.compile(r"\[\[Kategoria:Urodzeni w (?P<cby>.*?)[\|\]]")
        cby = u''
        firstline = True
        linki = cbyearR.finditer(text)
        for cbyear in linki:
            found = True
            # pywikibot.output(u'CATBYEAR: %s' % cbyear.group('cby'))
            cby = cbyear.group('cby')
            pywikibot.output(u'CATBYEAR: %s' % cby)
            break
        
        # Category deathyear
        cdyearR = re.compile(r"\[\[Kategoria:Zmarli w (?P<cdy>.*?)[\|\]]")
        cdy = u''
        firstline = True
        linki = cdyearR.finditer(text)
        for cdyear in linki:
            found = True
            # pywikibot.output(u'CATDYEAR: %s' % cdyear.group('cdy'))
            cdy = cdyear.group('cdy')
            pywikibot.output(u'CATDYEAR: %s' % cdy)
            break
        
        # infobox name & title
        firstline = True
        infoboxs = u''
        iboxname = u''
        iboxbd = u''
        iboxby = u''
        iboxdd = u''
        iboxdy = u''
        infoboxtitle = u''
        infoboxtR = re.compile(r"\{\{(?P<iboxtitle>.*) infobox", flags=re.I)
        infoboxnR = re.compile(
            r"^(Imię i nazwisko|Imię|polityk|imięinazwisko|imię i nazwisko|imięnazwisko)\s*=\s*(?P<iboxname>.*)", flags=re.I)
        infoboxbdR = re.compile(
            r"^(data urodzenia|dataurodzenia|data i miejsce urodzenia)\s*=(\s*(\[{2})?(?P<iboxbd>\d{1,2} [\wśńź]{4,12})(\]{2})?)?\s*?(\[{2})?(?P<iboxby>\d{4})(\]{2})?",
            flags=re.I)
        infoboxddR = re.compile(
            r"^(data śmierci|dataśmierci|data i miejsce śmierci)\s*=(\s*(\[{2})?(?P<iboxdd>\d{1,2} [\wśńź]{4,12})(\]{2})?)?\s*?(\[{2})?(?P<iboxdy>\d{4})(\]{2})?",
            flags=re.I)
        infoboxnumber = 0
        infoboxskip = False
        for (t, args) in page.templatesWithParams():
            if u'infobox' in t and not u'/' in t:
                iboxname = u''
                iboxbd = u''
                iboxby = u''
                iboxdd = u''
                iboxdy = u''
                infoboxnumber += 1
                if infoboxskip:
                    break
                for p in args:
                    p = self.refremove(p)
                pywikibot.output(p)
                # name in infobox
                arglist = infoboxnR.finditer(p)
        for arg in arglist:
            pywikibot.output(u'ARG: %s' % arg.group('iboxname'))
            iboxname = arg.group('iboxname')
            # birthdate and year in infobox
            arglist = infoboxbdR.finditer(p)
        for arg in arglist:
            pywikibot.output(u'ARG: %s %s' % (arg.group('iboxbd'), arg.group('iboxby')))
            if not arg.group('iboxbd') == None:
                iboxbd = arg.group('iboxbd')
            if not arg.group('iboxby') == None:
                iboxby = arg.group('iboxby')
                # deathdate and year in infobox
            arglist = infoboxddR.finditer(p)
        for arg in arglist:
            pywikibot.output(u'ARG: %s %s' % (arg.group('iboxdd'), arg.group('iboxdy')))
            if not arg.group('iboxdd') == None:
                iboxdd = arg.group('iboxdd')
            if not arg.group('iboxdy') == None:
                iboxdy = arg.group('iboxdy')
        pywikibot.output(u'iboxname: %s' % iboxname)
        pywikibot.output(u'iboxbd: %s' % iboxbd)
        pywikibot.output(u'iboxby: %s' % iboxby)
        pywikibot.output(u'iboxdd: %s' % iboxdd)
        pywikibot.output(u'iboxdy: %s' % iboxdy)
        
        # if firstline:
        #   firstline = False
        # else:
        #   infoboxs += u'<br />'
        # infoboxs += t + u'=>' + iboxname + u'=>' + iboxbd + u' ' + iboxby + u'=>' + iboxdd + u' ' + iboxdy
        infoboxs += t + u' || ' + iboxname + u' || ' + iboxbd + u' ' + iboxby + u' || ' + iboxdd + u' ' + iboxdy
        infoboxtitle = t
        infoboxskip = True
        
        # write result
        ToBeMarked = False
        pywikibot.output(u'ptitle: %s' % ptitle)
        pywikibot.output(u'bheaders: %s' % bheaders)
        pywikibot.output(u'infoboxskip: %s' % infoboxskip)
        if not iboxname == ptitle or not iboxname == bheaders:
            cond1 = True
        else:
            cond1 = False
        pywikibot.output(u'Condition1: %s' % cond1)
        pywikibot.output(u'Condition2: %s' % (infoboxskip and cond1))
        if not ptitle == bheaders or (infoboxskip and (not iboxname == ptitle or not iboxname == bheaders)):
            ToBeMarked = True
            pywikibot.output(u'ToBeMarked: title vs bolded header')
            ptitle = u'style="background-color:PowderBlue" | ' + ptitle
            bheaders = u'style="background-color:PowderBlue" | ' + bheaders
            iboxname = u'style="background-color:PowderBlue" | ' + iboxname
        if not bby == cby or (infoboxskip and (not iboxby == bby or not iboxby == cby)):
            ToBeMarked = True
            pywikibot.output(u'ToBeMarked: Bolded BY vs cat BY')
            bby = u'style="background-color:Lime" | ' + bby
            cby = u'style="background-color:Lime" | ' + cby
            iboxbd = u'style="background-color:Lime" | ' + iboxbd
        if not bdy == cdy or (infoboxskip and (not iboxdy == bdy or not iboxdy == cdy)):
            ToBeMarked = True
            pywikibot.output(u'ToBeMarked: Bolded DY vs cat DY')
            bdy = u'style="background-color:Orange" | ' + bdy
            cdy = u'style="background-color:Orange" | ' + cdy
            iboxdd = u'style="background-color:Orange" | ' + iboxdd
        if ToBeMarked:
            pageiw = u'[[:' + page.title() + u']] || ' + bheaders + u' || ' + bbd + u' ' + bby + u' || ' + bdd + u' ' + bdy + u' || ' + cby + u' || ' + cdy + u' || ' + str(
                infoboxnumber) + u' || ' + infoboxtitle + u' || ' + iboxname + u' || ' + iboxbd + u' ' + iboxby + u' || ' + iboxdd + u' ' + iboxdy
        else:
            pageiw = u''
        
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
            pagetext = u''
            if text != pagetext:
                # Show the title of the page we're working on.
                # Highlight the title in purple.
                pywikibot.output(u"\n\n>>> \03{lightpurple}%s\03{default} <<<"
                                 % page.title())
                # show what was changed
                pywikibot.showDiff(pagetext, text)
                pywikibot.output(u'Comment: %s' % comment)
                # choice = pywikibot.inputChoice(
                #    u'Do you want to accept these changes?',
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
                        u'Skipping %s because of edit conflict'
                        % (page.title()))
                except pywikibot.exceptions.SpamblacklistError as error:
                    pywikibot.output(u'Cannot change %s because of spam blacklist entry %s'
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
