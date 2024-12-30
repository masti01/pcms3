#!/usr/bin/env python3

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
)

import mwparserfromhell
import requests

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

    use_redirects = False  # treats non-redirects only
    summary_key = 'basic-changing'

    update_options = {
        'replace': False,  # delete old text and write the new text
        'summary': None,  # your own bot summary
        'text': 'Test',  # add this text from option. 'Test' is default
        'top': False,  # append text on top of the page
        'outpage': u'User:mastiBot/test',  # default output page
        'maxlines': 1000,  # default number of entries per page
        'testprint': False,  # print testoutput
        'negative': False,  # if True negate behavior i.e. mark pages that DO NOT contain search string
        'test': False,  # test options
        'progress': False  # test option showing bot progress
    }

    def treat_page(self) -> None:

        text = self.current_page.text
        pywikibot.output(f'treating {self.current_page.title()}')

        pywikibot.output('TREATING')
        # Initialize Memento Client
        # mc = MementoClient()

        """Load the given page, do some changes, and save it."""
        text = self.current_page.text
        parsed = mwparserfromhell.parse(text)

        for link in parsed.ifilter_external_links():
            if str(link).startswith('https://natura2000.gdos.gov.pl/files/'):
                pywikibot.output(link)

        # if summary option is None, it takes the default i18n summary from
        # i18n subdirectory with summary_key as summary key.
        # self.put_current(text, summary=self.opt.summary)


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
        if not pywikibot.bot.suggest_help(missing_generator=not gen):
            # pass generator and private options to the bot
            bot = BasicBot(generator=gen, **options)
            bot.run()  # guess what it does

    if __name__ == '__main__':
        main()