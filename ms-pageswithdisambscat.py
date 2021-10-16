#!/usr/bin/python
"""
This bot creates a page with list of pages with most linked disambigs:
Wikiprojekt:Strony ujednoznaczniające z linkami/Wiele linków z pojedynczych artykułów

Call:
    python3 pwb.py masti/ms-pageswithdisambscat.py -cat:'Strony ujednoznaczniające' -summary:"Bot aktualizuje
        stronę" -outpage:'Wikiprojekt:Strony ujednoznaczniające z linkami/Wiele linków z pojedynczych artykułów'

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
import datetime

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
    results = {}

    update_options = {
        'replace': False,  # delete old text and write the new text
        'summary': None,  # your own bot summary
        'text': 'Test',  # add this text from option. 'Test' is default
        'top': False,  # append text on top of the page
        'outpage': u'User:mastiBot/test',  # default output page
        'maxlines': 1000,  # default number of entries per page
        'testprint': False,  # print testoutput
        'negative': False,  # if True negate behavior i.e. mark pages that DO NOT contain search string
        'test': False,  # test printouts
        'testlinks': False,  # test printouts
        'progress': False,  # show progress
        'resprogress': False,  # show progress in generating results
        'minlinks': 50,  # print only >minlinks results
    }

    def run(self):
        # prepare new page
        header = u'Poniżej znajduje się lista artykułów linkujących do conajmniej %s [[:Kategoria:Strony ujednoznaczniające|stron ujednoznaczniających]].\n\n' % self.getOption(
            'minlinks')

        # header += u':<small>Pominięto strony z szablonem {{s|Inne znaczenia}}</small>\n\n'
        header += u"Ta strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|MastiBota]]. Ostatnia aktualizacja przez bota: '''~~~~~'''. \n"
        header += u'Wszelkie uwagi proszę zgłaszać w [[Dyskusja_Wikipedysty:Masti|dyskusji operatora]].\n\n'
        footer = u'\n\n[[Kategoria:Wikiprojekt Strony ujednoznaczniające z linkami]]'

        counter = 1
        refscounter = 0

        for page in self.generator:
            if self.opt.progress:
                pywikibot.output(
                    u'{} #{:d} ({:d}) Treating:{}'.format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                                          counter, refscounter, page.title(asLink=True)))
            refs = self.treat(page)
            if self.opt.progress:
                pywikibot.output(
                    '{} #{:d} refs found:{:d}'.format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), counter,
                                                      refs))
            counter += 1

        return self.generateresultspage(self.results, self.opt.outpage, header, footer)

    def redirCount(self, article):
        # return number of linkined redirs
        return article['count']

    def generateresultspage(self, redirlist, pagename, header, footer):
        """
        Generates results page from redirlist
        Starting with header, ending with footer
        Output page is pagename
        """
        finalpage = header
        res = sorted(redirlist, key=redirlist.__getitem__, reverse=True)
        if self.opt.test:
            pywikibot.output('***** INPUT *****')
            pywikibot.output(redirlist)
            pywikibot.output('***** RESULT *****')
            pywikibot.output(res)
        for i in res:
            count = self.redirCount(redirlist[i])
            l = redirlist[i]['list']
            if self.opt.resprogress:
                pywikibot.output('i:[[{}]], count:{:d}, l:{}'.format(i, count, l))

            if count < int(self.opt.minlinks):
                continue
            strcount = str(count)
            if count == 1:
                suffix = u''
            elif strcount[len(strcount) - 1] in (u'2', u'3', u'4') and count > 20:
                suffix = u'i'
            else:
                suffix = u'ów'
            finalpage += u'\n# [[{}]] ([[Specjalna:Linkujące/{}|{} link{}]])  &rarr; [[{}]]'.format(i, i, str(count),
                                                                                                    suffix,
                                                                                                    ']], [['.join(l))

        finalpage += footer

        if self.opt.test:
            pywikibot.output('***** FINALPAGE *****')
            pywikibot.output(finalpage)

        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        outpage.text = finalpage
        outpage.save(summary=self.opt.summary)

        # if self.opt.test:
        #    pywikibot.output(redirlist)
        return res


    def addResult(self, what, where):
        if where not in self.results.keys():
            self.results[where] = {'count': 0, 'list': []}
        self.results[where]['count'] += 1
        self.results[where]['list'].append(what)
        return

    def treat(self, page):
        # get all linkedPages
        # check for disambigs
        counter = 0
        disambcounter = 0
        for p in page.getReferences(namespaces=0):
            counter += 1
            if self.opt.testlinks:
                pywikibot.output(
                    u'{} #{:d} ({:d}) In {} checking:{}'.format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                                                counter, disambcounter, page.title(as_link=True),
                                                                p.title(as_link=True)))
            self.addResult(page.title(), p.title())
        return counter


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
        if option in ('summary', 'text', 'outpage', 'maxlines', 'minlinks'):
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
