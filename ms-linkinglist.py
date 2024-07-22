#!/usr/bin/python
"""
Script by masti for creating list of articles linking to pages referenced by a page

Call: python3 pwb.py masti/ms-linkinglist.py -outpage:"Wikipedysta:Andrzei111/Izrael/linki" -links:"Wikipedysta:Andrzei111/Izrael" -summary:"Bot uaktualnia tabelę" -maxlines:10000 -ns:0 -ascending -negative


Use global -simulate option for test purposes. No changes to live wiki
will be done.


The following parameters are supported:

-always           The bot won't ask for confirmation when putting a page

-text:            Use this text to be added; otherwise 'Test' is used

-replace:         Don't add text but replace it

-top              Place additional text on top of the page

-summary:         Set the action summary message for the edit.

All settings can be made either by giving option with the command line
or with a settings file which is scripts.ini by default. If you don't
want the default values you can add any option you want to change to
that settings file below the [basic] section like:

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
    SingleSiteBot,
)


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
        'testprint': False,  # print testoutput
        'negative': False,  # if True negate behavior i.e. mark pages that DO NOT contain search string
        'ascending': False,  # sort order
        'test': False,  # switch on test functionality
    }

    def run(self):

        # prepare new page
        header = "Poniżej znajduje się lista do " + str(self.opt.maxlines) + " brakujących artykułów.\n\n"
        header += "Ta strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|MastiBota]]. Ostatnia aktualizacja ~~~~~. \n"
        header += "Wszelkie uwagi proszę zgłaszać w [[Dyskusja_Wikipedysty:Masti|dyskusji operatora]].\n\n"
        header += "\n\nBrakujące artykuły"
        # header += "\n<small>"
        header += "\n*Legenda:"
        header += "\n*:'''#''' - Numer"
        header += "\n*:'''Hasło''' - Tytuł hasła"
        header += "\n*:'''Linki''' - Ilość linków do artykuł"
        # header += "\n</small>\n"
        header += '\n{| class="wikitable sortable" style="font-size:85%;"\n|-\n!#\n!Hasło\n!Linki\n'

        reflinks = {}
        licznik = 0
        for page in self.generator:
            licznik += 1
            if self.opt.test:
                pywikibot.output('Treating #%i: %s' % (licznik, page.title()))
            if (self.opt.negative and not page.exists()) or (not self.opt.negative and page.exists()):
                refs = self.treat(page)  # get list of links
                reflinks[page.title()] = refs
                if self.opt.test:
                    pywikibot.output('%s - %i' % (page.title(), reflinks[page.title()]))
            else:
                if self.opt.test:
                    pywikibot.output('SKIPPING Page :%s' % page.title())

        footer = '\n|}\n'
        footer += 'Przetworzono: ' + str(licznik) + ' stron'

        result = self.generateresultspage(reflinks, self.opt.outpage, header, footer)
        return

    def treat(self, page):
        count = 0
        for i in page.getReferences(namespaces=0):
            count += 1

        # test
        # pywikibot.output(count)
        return count

    def linknumber(self, t, i):

        if i == 1:
            suffix = 'linkująca'
        elif i in (2, 3, 4) and (i < 10 or i > 20):
            suffix = 'linkujące'
        else:
            suffix = 'linkujących'

        if self.opt.test:
            pywikibot.output('[[Specjalna:Linkujące/' + t + '|' + str(i) + ' ' + suffix + ']]')
        return '[[Specjalna:Linkujące/' + t + '|' + str(i) + ' ' + suffix + ']]\n'

    def generateresultspage(self, resdict, pagename, header, footer):
        """
        Generates results page from resdict
        Starting with header, ending with footer
        Output page is pagename
        """
        maxlines = int(self.opt.maxlines)
        finalpage = header
        res = sorted(resdict, key=resdict.__getitem__, reverse=not self.opt.ascending)
        # res = sorted(redirlist)
        itemcount = 0
        for t in res:
            finalpage += '\n|-\n| ' + str(itemcount + 1) + ' || [[' + t + ']] || ' + self.linknumber(t, resdict[t])
            itemcount += 1
            if itemcount > maxlines - 1:
                pywikibot.output('*** Breaking output loop ***')
                break

        finalpage += footer

        # pywikibot.output(finalpage)
        success = True
        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        outpage.text = finalpage

        if self.opt.test:
            pywikibot.output(outpage.title())

        outpage.save(summary=self.opt.summary)
        # if not outpage.save(finalpage, outpage, self.summary):
        #   pywikibot.output('Page %s not saved.' % outpage.title(as_link=True))
        #   success = False
        return success


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
