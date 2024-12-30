#!/usr/bin/env python3
"""
An incomplete sample script.

This is not a complete bot; rather, it is a template from which simple
bots can be made. You can rename it to mybot.py, then edit it in
whatever way you want.

Use global -simulate option for test purposes. No changes to live wiki
will be done.


The following parameters are supported:

-always           The bot won't ask for confirmation when putting a page

-text:            Use this text to be added; otherwise 'Test' is used

-replace:         Don't add text but replace it

-top              Place additional text on top of the page

-summary:         Set the action summary message for the edit.

This sample script is a
:py:obj:`ConfigParserBot <bot.ConfigParserBot>`. All settings can be
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
# (C) Pywikibot team, 2006-2022
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
import re
from memento_client import MementoClient



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

    use_redirects = False  # treats non-redirects only
    summary_key = 'basic-changing'

    def __init__(self, generator, **kwargs) -> None:
        """
        Initializer.

        @param generator: the page generator that determines on which pages
            to work
        @type generator: generator
        """
        # Add your own options to the bot and set their defaults
        # -always option is predefined by BaseBot class
        self.available_options.update({
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
        })

        # call initializer of the super class
        super().__init__(site=True, **kwargs)
        # assign the generator to the bot
        self.generator = generator

    # Function to get archived URL using Memento Client
    def get_memento_url(url):
        try:
            # Request the closest Memento
            memento = mc.get_memento(url)
            return memento.uri if memento else None
        except Exception as e:
            print(f"Error fetching memento for {url}: {e}")
            return None

    def treat_page(self) -> None:

        pywikibot.output('TREATING')
        # Initialize Memento Client
        mc = MementoClient()

        """Load the given page, do some changes, and save it."""
        text = self.current_page.text
        parsed = mwparserfromhell.parse(text)

        for link in parsed.ifilter_external_links():
            if 'natura2000.gdos.gov.pl' in link:
                pywikibot.output(link)

        # if summary option is None, it takes the default i18n summary from
        # i18n subdirectory with summary_key as summary key.
        # self.put_current(text, summary=self.opt.summary)


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