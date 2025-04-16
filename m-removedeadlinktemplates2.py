#!/usr/bin/python
"""
This is a bot to remove {{Martwy link dyskusja}} templates from discussion pages if the link reported no longer exists in the article.
Call:
   python pwb.py masti/m-removedeadlinktemplates2.py -cat:"Niezweryfikowane martwe linki" -ns:1 -summary:"Nieaktualna informacja o martwym linku zewnętrznym" -pt:0

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

from urllib.parse import unquote
import mwparserfromhell
import difflib
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
        'test': False,  # switch on test functionality
        'testtmplname': False,  # switch on test functionality
        'testtmpllink': False,  # switch on test functionality - check link with archive
        'testcheck': False,  # switch on test functionality - check links on page
        'nodelete': False,  # do not delete empty pages
    }

    def run(self):
        counter = 0
        changeCounter = 0
        for page in self.generator:
            pywikibot.output(u'Processing #%i (%i changed):%s' % (counter, changeCounter, page.title(as_link=True)))
            counter += 1
            if self.treat(page):
                changeCounter += 1
        pywikibot.output(u'Statistics: Processed: %i, Changed: %i' % (counter, changeCounter))

    def treat(self, page):
        """
        Loads the given discussion page, verifies if the links in {{Martwy link dyskusja}}
        were removed from article or are a part of {{Cytuj}} template with properly filled archiwum= parameter
        Then removes the template(s) or marks page for deletion
        """

        talktext = page.text
        if not talktext:
            return False

        articlepage = page.toggleTalkPage()
        articletext = articlepage.text
        if not articletext:
            return False

        # test printout
        if self.opt.test:
            pywikibot.output(u'Page: %s' % articlepage.title(as_link=True))
            pywikibot.output(u'Talk: %s' % page.title(as_link=True))

        # parse talk page
        parsedtalk = mwparserfromhell.parse(talktext)

        # parse article text
        parsedarticle = mwparserfromhell.parse(articletext)
        # get all weblinks from article
        articlelinks = self.checklinksinpage(parsedarticle)


        # get templates from talk
        templates = parsedtalk.filter_templates(recursive=False)

        # find dead link templates
        changed = False
        tmplcount = 0
        tmplremoved = 0
        for tmpl in templates:
            tmplcount += 1
            if self.opt.testtmplname:
                pywikibot.output(f'Title:{tmpl.name}')
            if tmpl.name.matches("Martwy link dyskusja") and tmpl.has("link"):
                # pywikibot.output(f"Matched:{tmpl['link']}")
                try:
                    linklink = unquote(tmpl['link'].value.filter_external_links()[0].strip())
                    pywikibot.output(f"linktype:{type(linklink)}, link:{linklink}")
                    pywikibot.output(f"articlelinks.keys:{articlelinks.keys()}")
                    try:
                        pywikibot.output(f"articlelinks[linklink]: {articlelinks[linklink]}")
                    except KeyError:
                        pywikibot.output(f"articlelinks[{linklink}]: DO NOT EXISTS")

                    # find linklink in article unquoted content
                    if (linklink in articlelinks.keys() and articlelinks[linklink]) or (linklink not in articlelinks.keys()):
                        parsedtalk.remove(tmpl)
                        changed = True
                        tmplremoved += 1
                        if self.opt.test:
                            pywikibot.output(f'Template #{tmplremoved} removed:{tmpl["link"]}')
                except IndexError:
                    pywikibot.output(f"Link ERROR:{tmpl['link'].value.filter_external_links()}")

        if self.opt.test:
            pywikibot.output(f'TMPL proc:{tmplcount}, tmplrem:{tmplremoved}')

        if changed:
            page.text = re.sub('\n+{{Martwy link', '\n{{Martwy link', str(parsedtalk))
            if self.opt.test:
                # pywikibot.output(f'NEWTALK:{str(parsedtalk)}')
                pywikibot.output(f'DIFF:\n{str(difflib.ndiff(talktext, page.text))}')

            page.save(summary=self.opt.summary)
            return True
        return False

    def checklinksinpage(self, parsedarticle):
        """
        check all links in page,
        verify if they are in cite template with archiwum=  or they are archive links
        if yes set archive:True
        :param parsedarticle:
        :return:
        """

        result = {}
        for l in parsedarticle.filter_external_links():
            ul = unquote(str(l.url))  # unquoted link
            if str(ul) not in result.keys():
                result[str(ul)] = False
            if self.isarchivedlink(ul) or self.islinkwitharchive(parsedarticle, l.url):
                result[str(ul)] = True

        if self.opt.testcheck:
            pywikibot.output(f'RESULT:{result}')
            pywikibot.output(f'Links found:{len(result)}')
        return result


    def isarchivedlink(self, link):
        """
        if link is internet archive link
        :param link: string
        :return: Bool
        """
        return "web.archive.org" in link or "archive.is" in link

    def islinkwitharchive(self, wcode, link):
        """
        check if link is in cite template with archiwum= set
        :param link:
        :param wcode:
        :return:
        """
        if self.opt.testtmpllink:
            pywikibot.output(f'LINK TYPE:{type(link)}')

        try:
            parent2 = wcode.get_ancestors(link)[-2]
            if self.opt.testtmpllink:
                pywikibot.output(f'PARENT2 LINK TYPE:{type(parent2)}')
            if not isinstance(parent2, mwparserfromhell.nodes.template.Template):
                return False

            if self.opt.testtmpllink:
                pywikibot.output(f'NAME:{parent2.name}')
            if parent2.name.lower().startswith("cytuj"):
                if self.opt.testtmpllink:
                    pywikibot.output(f'CITE:{parent2}')
                return parent2.has("archiwum", ignore_empty=True)
        except IndexError:
            pass

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
        arg, _, value = arg.partition(':')
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

    # check if further help is needed
    if not pywikibot.bot.suggest_help(missing_generator=not gen):
        # pass generator and private options to the bot
        bot = BasicBot(generator=gen, **options)
        bot.run()  # guess what it does


if __name__ == '__main__':
    main()
