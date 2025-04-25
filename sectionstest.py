#!/usr/bin/python
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
from pywikibot import textlib
import re
import mwparserfromhell
from urllib.parse import unquote, urlparse

from pywikibot.bot import (
    SingleSiteBot, ConfigParserBot, ExistingPageBot,
    AutomaticTWSummaryBot)


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
    # NoRedirectPageBot,  # CurrentPageBot which only treats non-redirects
    AutomaticTWSummaryBot,  # Automatically defines summary; needs summary_key
):

    """
    An incomplete sample bot.

    @ivar summary_key: Edit summary message key. The message that should be
        used is placed on /i18n subdirectory. The file containing these
        messages should have the same name as the caller script (i.e. basic.py
        in this case). Use summary_key to set a default edit summary message.

    @type summary_key: str
    """

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
            'testtmpllink': False,  # test for link in template
            'negative': False,  # if True negate behavior i.e. mark pages that DO NOT contain search string
            'test': False,  # test options
            'progress': False,  # test option showing bot progress
            'link': '',  # link to search for
            'archivelink': '',  # link to add
            'archivedate': '',  # archive date
        })

        # call initializer of the super class
        super().__init__(site=True, **kwargs)
        # assign the generator to the bot
        self.generator = generator



    def treat_page(self) -> None:
        """Load the given page, do some changes, and save it."""
        pagetext = self.current_page.text
        wcode = mwparserfromhell.parse(pagetext)

        # search for link
        for link in wcode.filter_external_links():
            if link.url == self.opt.link:
                if self.opt.test:
                    pywikibot.output(f'link found:{self.opt.link}')
                try:
                    parent2 = wcode.get_ancestors(link)[-2]
                    parent = wcode.get_ancestors(link)[-1]
                    if self.opt.testtmpllink:
                        pywikibot.output(f'PARENT LINK TYPE:{type(parent)}')
                        pywikibot.output(f'PARENT2 LINK TYPE:{type(parent2)}')
                    if not isinstance(parent, mwparserfromhell.nodes.template.Template):
                        pywikibot.output(f"citeArchivedLink parent is not template:{str(parent2)}")
                        return False

                    if self.opt.testtmpllink:
                        pywikibot.output(f'NAME:{parent.name}')
                    if parent.name.lower().startswith("cytuj"):
                        if self.opt.testtmpllink:
                            pywikibot.output(f'CITE:{parent}')
                        if self.opt.testremove:
                            pywikibot.output(f'Archiwum? {parent.has("archiwum", ignore_empty=True)}')
                        return parent.has("archiwum", ignore_empty=True)
                except IndexError:
                    pass

        return
        # pywikibot.output(parsed.nodes)
        # for n in parsed.nodes:
        #     pywikibot.output(n)

        # lastnode = wc.nodes[-1]
        # pywikibot.output(f'LASTNODE: {lastnode}')

        # firstnode = parsed.nodes[0]
        # pywikibot.output(f'page Tree:\n {[parsed.get_tree()]}')

        # check for templates - move them to the end
        # for t in parsed.filter_templates():
        #     parsed.append('\n')
        #     parsed.append(t)
        #     parsed.remove(t)
            # pywikibot.output(parsed.nodes)

        # add history= param
        for t in parsed.filter_templates():
            pywikibot.output(str(t))
            link = str(t.get('link').value).rstrip() + '\n'
            linkR = re.compile(r'(?si)\*?\s*?(?P<link>http[^\s]*?)( [^\n]*)?\n(?P<history>.*)')
            pywikibot.output(f'LINK:{link}')
            m = re.search(linkR, link)
            try:
                newlink = m.group('link')
            except AttributeError:
                newlink = ''

            if t.has('historia'):
                pywikibot.output(f'historia= param found')
                newhistory = str(t.get('historia').value).rstrip()
                if newhistory[-1] != '\n':
                    newhistory += '\n'
            else:
                try:
                    history = m.group('history')
                    historyR = re.compile(r'\**\s*In\s*?(?P<wikilink>\[\[.*\]\]) on (?P<date>[^,]*),\s*(?P<error>.*)')
                    newhistory = '\n'
                    for h in historyR.finditer(history):
                        wikilink = h.group('wikilink')
                        date = h.group('date')
                        error = h.group('error')
                        newhistory += f'* {wikilink} - {date} - {error}\n'
                except AttributeError:
                    newhistory = ''

            try:
                IA = str(t.get('IA').value).rstrip()
            except ValueError:
                IA = ''

            t2 = f'{{{{Wikipedysta:Masti/mld\n| link = {newlink}\n| IA = {IA}\n| historia ={newhistory}}}}}'
            # t.remove('link')
            # t.remove('IA')
            # t.add('link', link)
            # t.add('IA', IA)
            # t.add('history', history)
            parsed.remove(t)  # remove old template
            parsed.append('\n')  # add newline between templates
            parsed.append(t2)  # append new version of template

            # cleanup page
            text = str(parsed)
            text = re.sub(r'\n{2,}', '\n', text)

        # self.current_page.text = str(parsed)
        # if summary option is None, it takes the default i18n summary from
        # i18n subdirectory with summary_key as summary key.
        self.put_current(text, summary='test')
        pywikibot.output(f'New page:\n{text}')

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
        if option in ('summary', 'text', 'link', 'archivelink', 'archivedate'):
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
