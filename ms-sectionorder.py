#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
An incomplete sample script by masti for creating statistics/listings pages

Bot creates a list of pages where final sections are in the wrong order.
Correct section order:
*Zobacz też
*Uwagi
*Przypisy
*Bibliografia
*Linki zewnętrzne

Call:
python pwb.py masti/ms-sectionorder.py -start:'!' -outpage:'Wikipedia:Sprzątanie Wikipedii/Artykuły ze złą kolejnością sekcji końcowych' -maxlines:10000 -pt:0 -summary:"Bot aktualizuje tabelę"


Use global -simulate option for test purposes. No changes to live wiki
will be done.

The following parameters are supported:

&params;

-always           If used, the bot won't ask if it should file the message
                  onto user talk page.

-outpage          Results page; otherwise "Wikipedysta:mastiBot/test" is used

-maxlines         Max number of entries before new subpage is created; default 1000

-text:            Use this text to be added; otherwise 'Test' is used

-replace:         Dont add text but replace it

-top              Place additional text on top of the page

-summary:         Set the action summary message for the edit.

-negative:        mark if text not in page
"""
#
# (C) Pywikibot team, 2006-2016
#
# Distributed under the terms of the MIT license.
#
from __future__ import absolute_import, unicode_literals

__version__ = '$Id: c1795dd2fb2de670c0b4bddb289ea9d13b1e9b3f $'

#

import pywikibot
from pywikibot import pagegenerators, textlib

from pywikibot.bot import (
    SingleSiteBot, ExistingPageBot, AutomaticTWSummaryBot)

import re

# This is required for the text that is shown when you run this script
# with the parameter -help.
docuReplacements = {
    '&params;': pagegenerators.parameterHelp
}


class BasicBot(
    # Refer pywikobot.bot for generic bot classes
    SingleSiteBot,  # A bot only working on one site
    # CurrentPageBot,  # Sets 'current_page'. Process it in treat_page method.
    #                  # Not needed here because we have subclasses
    ExistingPageBot,  # CurrentPageBot which only treats existing pages
    AutomaticTWSummaryBot,  # Automatically defines summary; needs summary_key
):
    """
    An incomplete sample bot.

    @ivar summary_key: Edit summary message key. The message that should be used
        is placed on /i18n subdirectory. The file containing these messages
        should have the same name as the caller script (i.e. basic.py in this
        case). Use summary_key to set a default edit summary message.
    @type summary_key: str
    """

    summary_key = 'basic-changing'
    update_options = {
        'replace': False,  # delete old text and write the new text
        'summary': None,  # your own bot summary
        'text': 'Test',  # add this text from option. 'Test' is default
        'top': False,  # append text on top of the page
        'outpage': u'User:mastiBot/test',  # default output page
        'maxlines': 1000,  # default number of entries per page
        'test': False,  # print testoutput
        'negative': False,  # if True negate behavior i.e. mark pages that DO NOT contain search string
        'append': False,  # append results to page
        'section': None,  # section title
    }

    sectionOrder = ['zobacz też', 'uwagi', 'przypisy', 'bibliografia', 'linki zewnętrzne']

    def run(self):
        """TEST"""
        pywikibot.output(u'THIS IS A RUN METHOD')
        outputpage = self.opt.outpage
        pywikibot.output(u'OUTPUTPAGE:%s' % outputpage)

        if not self.opt.append:
            header = u'Strona zawiera listę pierwszych %s stron z błędną kolejnością sekcji końcowych.\n\n' % self.opt.maxlines
            header += u'<small>Prawidłowa kolejność sekcji (za [[Pomoc:Jak napisać doskonały artykuł#Kolejność i wymagalność sekcji końcowych]]):\n'
            header += u'*Zobacz też\n'
            header += u'*Uwagi\n'
            header += u'*Przypisy\n'
            header += u'*Bibliografia\n'
            header += u'*Linki zewnętrzne</small>\n\n'
            header += u"Ostatnia aktualizacja przez bota: '''~~~~~'''.\n\n"
            header += u"Wszelkie uwagi proszę zgłaszać w [[User talk:masti|dyskusji operatora]].\n\n"
        else:
            header = ''

        reflinks = {}  # initiate list
        counter = 0
        marked = 0

        for page in self.generator:
            counter += 1
            # if self.opt.test:
            pywikibot.output(u'Treating #%i (marked:%i): %s' % (counter, marked, page.title()))
            t = self.treat(page)
            if t:
                marked += 1
                reflinks[page.title()] = t
                if self.opt.test:
                    pywikibot.output(t)
                if not (marked < int(self.opt.maxlines)):
                    break
            else:
                if self.opt.test:
                    pywikibot.output('OK')

        footer = u'\n\nPrzetworzono ' + str(counter) + u' stron.'

        # print reflinks
        self.generateresultspage(reflinks, self.opt.outpage, header, footer)

    def sectionList(self, page):
        sections = []
        sectionR = re.compile(r'(?im)^=+(?P<section>[^<]*?)(<ref.*?)?=+$')

        text = page.text

        # expand templates
        etext = page.expand_text()
        etext = textlib.removeDisabledParts(etext)

        # if self.opt.test:
        #    pywikibot.output(etext)
        for s in sectionR.finditer(etext):
            if self.opt.test:
                pywikibot.output(u'>>>%s<<<' % s.group('section').strip())
            sections.append(s.group('section').strip())

        return (sections)

    def compareSections(self, slist, required):
        # compare list to find if they are in the roght orders
        order = []
        index = 0
        wrongOrder = False

        for l in slist:
            if self.opt.test:
                pywikibot.output(u'Section: %s' % l)
            if wrongOrder:
                order.append(l)
                continue
            if l.lower() in required:
                order.append(l)
                if required.index(l.lower()) < index:
                    wrongOrder = True
                else:
                    index = required.index(l.lower())

            if self.opt.test:
                pywikibot.output('i:%i -->%s' % (index, order))

        if wrongOrder:
            return (order)
        else:
            return (None)

    def treat(self, page):
        """Load the given page, do some changes, and save it."""
        sl = self.sectionList(page)
        return (self.compareSections(sl, self.sectionOrder))

    def generateresultspage(self, redirlist, pagename, header, footer):
        """
        Generates results page from redirlist
        Starting with header, ending with footer
        Output page is pagename
        """
        finalpage = ''
        if not self.opt.append:
            finalpage = header
        for i in sorted(redirlist.keys()):
            sections = redirlist[i]
            finalpage += u'\n# [[%s]] ==> ' % i
            for s in sections:
                finalpage += s + u', '

        finalpage += footer

        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        if self.opt.append:
            outpage.text += finalpage
        else:
            outpage.text = finalpage

        outpage.save(summary=self.opt.summary)

        if self.opt.test:
            pywikibot.output(finalpage)
        return (redirlist)


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