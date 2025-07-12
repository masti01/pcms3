#!/usr/bin/python
"""
This bot lists pages without images
Call:
    python pwb.py masti/ms-noimage.py -catr:Sportowcy -outpage:"Wikipedysta:Szoltys/skoczkowie bez zdjęć" -maxlines:10000 -ns:0 -summary:"Bot uaktualnia tabelę"

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
#
# (C) Pywikibot team, 2006-2024
#
# Distributed under the terms of the MIT license.
#
from __future__ import annotations

import pywikibot
from pywikibot import pagegenerators
from pywikibot.bot import (
    AutomaticTWSummaryBot,
    ConfigParserBot,
    ExistingPageBot,
    SingleSiteBot,
    Bot,
)


# This is required for the text that is shown when you run this script
# with the parameter -help.
docuReplacements = {'&params;': pagegenerators.parameterHelp}  # noqa: N816


class BasicBot(
    # Refer pywikibot.bot for generic bot classes
    # SingleSiteBot,  # A bot only working on one site
    Bot,
    # MultipleSitesBot,  # A bot class working on multiple sites
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

    use_redirects = False  # treats non-redirects only
    summary_key = 'basic-changing'

    update_options = {
        'replace': False,  # delete old text and write the new text
        'summary': None,  # your own bot summary
        'text': 'Test',  # add this text from option. 'Test' is default
        'top': False,  # append text on top of the page
        'outpage': 'User:mastiBot/test',  # default output page
        'maxlines': 1000,  # default number of entries per page
        'test': False,  # print testoutput
        'negative': False,  # if True negate behavior i.e. mark pages that DO NOT contain search string
    }

    def run(self):
        pywikibot.output("Running")
        header = f'Ta strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|MastiBota]]. Ostatnia aktualizacja ~~~~~. \n'
        header += f'Wszelkie uwagi proszę zgłaszać w [[Dyskusja_Wikipedysty:Masti|dyskusji operatora]].\n\n'
        header += f'{self.opt.text}\n\n'

        reflinks = []  # initiate list
        counter = 0
        marked = 0
        for tpage in self.generator:
            counter += 1
            if self.opt.test:
                # pywikibot.output('Treating #%i (%i marked): %s' % (counter, marked, tpage.title()))
                pywikibot.output(f'Treating #{counter} (%{marked} marked): {tpage.title()}')
            refs = self.treat(tpage)  # get (name)
            # if self.opt.test:
            # pywikibot.output('%s' % refs)
            if refs:
                reflinks.append(tpage.title(as_link=True))
                marked += 1

        footer = f'\n\nPrzetworzono {counter} stron.'

        outputpage = self.opt.outpage

        return self.generateresultspage(reflinks, outputpage, header, footer)

    def treat(self, page):
        # search for imagelinks in page
        # quit after first one
        found = False
        for i in page.imagelinks():
            if self.opt.test:
                pywikibot.output(i.title())
            if not self.excludedImage(i.title()):
                found = True
                break
        if found:
            return None
        else:
            return page.title

    def excludedImage(self, title):
        exclusions = ('flag', 'map', 'stamp', 'pictogram', 'ensign', 'medal', 'logo')
        for e in exclusions:
            if e in title.lower():
                return True
        return False

    def generateresultspage(self, redirlist, pagename, header, footer):
        """
        Generates results page from redirlist
        Starting with header, ending with footer
        Output page is pagename
        """
        maxlines = int(self.opt.maxlines)
        linecount = 0
        finalpage = header
        if self.opt.test:
            pywikibot.output('GENERATING RESULTS')
        for p in redirlist:
            if self.opt.test:
                pywikibot.output(p)
            finalpage += '\n# ' + p
            linecount += 1
            if linecount >= maxlines:
                break

        finalpage += footer
        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        outpage.text = finalpage
        if self.opt.test:
            pywikibot.output(outpage.title())

        outpage.save(summary=self.opt.summary)
        return


def main(*args: str) -> None:
    """Process command line arguments and invoke bot.

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
        arg, _, value = arg.partition(':')
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

        # check if further help is needed
        # if not pywikibot.bot.suggest_help(missing_generator=not gen):
            # pass generator and private options to the bot
        bot = BasicBot(generator=gen, **options)
        bot.run()  # guess what it does

    if __name__ == '__main__':
        main()