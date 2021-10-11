#!/usr/bin/python
"""
An incomplete sample script.

Call:
        python pwb.py masti/m-tematicweek.py -page:"Wikiprojekt:Tygodnie tematyczne/Tydzień Artykułu Bhutańskiego" -pt:0 -log:"Tydzień Artykułu Bhutańskiego"

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
        'outpage': u'User:mastiBot/test', #default output page
        'maxlines': 1000, #default number of entries per page
        'testprint': False, # print testoutput
        'negative': False, #if True negate behavior i.e. mark pages that DO NOT contain search string
        'test': False, #switch on test functionality
    }

    def run(self):

        # set up log page and load
        logpage = pywikibot.Page(pywikibot.Site(), u'Wikipedysta:MastiBot/Tygodnie Tematyczne/zrobione')
        if not logpage.text:
            return

        for page in self.generator:
            if self.treat_page(page):
                logpage.text += u'\n# [[' + page.title() + u']] --~~~~~'

        logpage.save(summary=u'Tygodnie Tematyczne: log')

    def treat_page(self, page):
        """Load the given page, retrieve links to updated pages. Add template to talkpage if necessary"""

        text = page.text
        # get template for marking articles
        t = re.search(r'(?P<templatename>\{\{Wikiprojekt:Tygodnie tematyczne\/info.*?\}\})', text)
        g = re.search(
            r'\{\{Tydzień tematyczny\/szablony.*?grafika tygodnia\s*?=\s*?(?P<iconname>[^\|\n]*).*?\[\[Wikiprojekt:Tygodnie tematyczne\/(?P<weekname>[^\|]*).*?}}',
            text, flags=re.S)
        if self.getOption('test'):
            pywikibot.output(u't:%s' % t)
            pywikibot.output(u'g:%s' % g)
        if not t and not g:
            pywikibot.output(u'Template not found!')
            return (False)

        if t:
            templatename = t.group('templatename')
        if g:
            templatename = u'{{Wikiprojekt:Tygodnie tematyczne/info|' + g.group('weekname') + '|' + g.group(
                'iconname') + u'}}'
        if self.getOption('test'):
            pywikibot.output(u'templatename:%s' % templatename)

        pywikibot.output(u'Template:%s' % templatename)

        # set summary for edits
        summary = u'Bot dodaje szablon ' + templatename

        # get articlenames to work on
        # get article section
        t = re.search(r'(?P<articlesection>=== Lista alfabetyczna.*?)== ', text, re.DOTALL)
        articlesection = t.group('articlesection')
        # pywikibot.output(u'Articles:%s' % articlesection)

        Rlink = re.compile(r'\[\[(?P<title>[^\]\|\[]*)(\|[^\]]*)?\]\]')

        for match in Rlink.finditer(articlesection):
            try:
                title = match.group('title')
                title = title.replace("_", " ").strip(" ")
            except:
                continue
            # pywikibot.output(u'Art:[[%s]]' % title)
            artpage = pywikibot.Page(pywikibot.Site(), title)

            # follow redirects
            try:
                while artpage.isRedirectPage():
                    oldtitle = artpage.title()
                    artpage = artpage.getRedirectTarget()
                    pywikibot.output(u'Art:[[%s]] FOLLOWING REDIR TO:%s' % (oldtitle, artpage.title()))
            except:
                continue

            # check if article exists
            if not (artpage.namespace() in [0, 10, 14]):
                pywikibot.output(u'Art:[[%s]] SKIPPED:wrong namespace' % artpage.title())
                continue
            elif artpage.exists():
                workpage = artpage.toggleTalkPage()
            else:
                pywikibot.output(u'Art:[[%s]] DOES NOT EXIST' % artpage.title())
                continue
            # pywikibot.output(u'Art:[[%s]]>>>[[%s]]' % (title,workpage.title()))
            # load discussion Page
            worktext = workpage.text
            if worktext:
                # check if template exists
                if u'{{Wikiprojekt:Tygodnie tematyczne/info' in worktext or u'{{Wikiprojekt:Tygodnie tematyczne/info' in worktext:
                    pywikibot.output(u'Art:[[%s]] not changed: template found' % workpage.title())
                    continue
                else:
                    pywikibot.output(u'Art:[[%s]] changed: template added' % workpage.title())
                    worktext = templatename + u'\n' + worktext
            else:
                pywikibot.output(u'Art:[[%s]] created' % workpage.title())
                worktext = templatename

            workpage.text = worktext
            workpage.save(summary=summary)
        return(True)


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
        if option in ('summary', 'text'):
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
