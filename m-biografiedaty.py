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
# (C) masti, 2022
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
from tools.biography import Biography
from tools.results import Results

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
        'progress': False,  # report script progress
    }

    def run(self):

        footer = '\n|}\n'

        # finalpage =  "{}\n{{{{Wikipedysta:MastiBot/Nawigacja}}}}\n\n{}".format(self.header(1), self.header(2))
        pagecounter = 0
        rowcounter = 0

        pywikibot.output('outpage:{}'.format(self.opt.outpage))
        res = Results(self.opt.outpage, self.header(1), self.header(2), footer, '', self.opt.summary, int(self.opt.maxlines))
        if self.opt.test:
            res.testenable()

        for page in self.generator:
            pagecounter += 1
            if self.opt.test or self.opt.progress:
                pywikibot.output(
                    'Processing page #%s (%s marked): %s' % (str(pagecounter), str(rowcounter), page.title(as_link=True)))
            if page.isRedirectPage() or page.isDisambig():
                continue
            result = self.treat(page)
            if result:
                rowcounter += 1
                res.add('\n|-\n| {} || {} {}'.format(rowcounter, page.title(as_link=True), result))
                # finalpage += '\n|-\n| {} || {} {}'.format(rowcounter, page.title(as_link=True), result)
                if self.opt.test:
                    pywikibot.output('Added line #%i (#%i): %s' % (
                        rowcounter, res.lines, '\n|-\n| {} || {} || {}'.format(rowcounter, page.title(as_link=True), result)))

        # finalpage += footer
        # finalpage += '\nPrzetworzono stron: ' + str(pagecounter)
        res.footer1 += '\nPrzetworzono stron: {:d}'.format(pagecounter)

        #finalpage += self.przypisy(finalpage)

        # Save page
        res.saveresults()

        # pywikibot.output(finalpage)
        # outpage = pywikibot.Page(pywikibot.Site(), self.opt.outpage)
        # outpage.text = finalpage
        # outpage.save(summary=self.opt.summary)

    @staticmethod
    def header(index):
        # prepare new page with table
        if index == 1:
            return (
                "\nTa strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|bota]]. Ostatnia aktualizacja '''~~~~~''' "
                "\nWszelkie uwagi proszę zgłaszać w [[Dyskusja_Wikipedysty:Masti|dyskusji operatora]]."
                "\n"
                "\nStrona zawiera artykuły, w których wykryto niezgodność nazwisk lub lat urodzenia/śmierci."
            )
        elif index == 2:
            return (
                "\n{{Wikipedysta:MastiBot/legendy/problemy w biogramach}}"
                "\n"
                '\n{| class="wikitable" style="font-size:85%; text-align:center; vertical-align:middle; margin: auto;"'
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


    def treat(self, page) -> str:
        """
        Loads the given page, performs action
        """

        bc = Biography(page)

        if self.opt.test:
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
            ibox='{{{{s|{}}}}}'.format(bc.infoboxtitle) if bc.infoboxtitle else '')

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
