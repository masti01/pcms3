#!/usr/bin/python
"""
This bot creates pages listing count of references to article from list:
Wikipedysta:Andrzei111/nazwiska z inicjałem

Call: python3 pwb.py masti/ms-refsnumber.py -page:'Wikipedysta:Andrzei111/nazwiska z inicjałem'        -summary:"Bot aktualizuje stronę" -outpage:'Wikipedysta:Andrzei111/nazwiska z inicjałem/licznik'

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
import re
import datetime
from pywikibot import textlib

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

    use_redirects = False  # treats non-redirects only
    summary_key = 'basic-changing'
    results = {}
    ranges = [(100, '100+'),
              (50, '50-99'),
              (40, '40-49'),
              (30, '30-39'),
              (25, '25-29'),
              (22, '22-24'),
              (20, '20-21'),
              (18, '18-19'),
              (16, '16-17'),
              (15, '15'),
              (14, '14'),
              (13, '13'),
              (12, '12'),
              (11, '11'),
              (10, '10'),
              (5, '5+'),
              ]

    update_options = {
        'replace': False,  # delete old text and write the new text
        'summary': None,  # your own bot summary
        'text': 'Test',  # add this text from option. 'Test' is default
        'top': False,  # append text on top of the page
        'outpage': 'User:mastiBot/test',  # default output page
        'maxlines': 1000,  # default number of entries per page
        'testprint': False,  # print testoutput
        'negative': False,  # if True negate behavior i.e. mark pages that DO NOT contain search string
        'test': False,  # test printouts
        'testlinks': False,  # test printouts
        'progress': False,  # show progress
        'resprogress': False,  # show progress in generating results
        'minlinks': 50,  # print only >minlinks results
        'reset': False,  # reset saved data
    }

    def run(self):
        # prepare new page
        # replace @@ with number of pages
        header = 'Lista linkujących do artykułów z listy na stronie [[Wikipedysta:Andrzei111/nazwiska z inicjałem]].\n\n'
        header += "Ta strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|MastiBota]]. Ostatnia aktualizacja przez bota: '''~~~~~'''. \n\n"
        header += 'Wszelkie uwagi proszę zgłaszać w [[Dyskusja_Wikipedysty:Masti|dyskusji operatora]].\n\n'

        header += '{| class="wikitable sortable"\n|-\n'
        header += '! Nr !! nazwa !! odwołania !! krótka nazwa !! odwołania\n|-\n'
        # footer = '\n\n[[Kategoria:Najbardziej potrzebne strony]]'
        footer = '|}\n'

        counter = 1

        for page in self.generator:
            if self.opt.progress:
                pywikibot.output('%s #%i Treating:%s' % (
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), counter, page.title(as_link=True)))
            refs = self.treat(page)

            counter += 1

        return self.generateresultspage(refs, self.opt.outpage, header, footer)

    def generateresultspage(self, redirlist, pagename, header, footer):
        """
        Generates results page from redirlist
        Starting with header, ending with footer
        Output page is pagename
        """
        finalpage = header
        # res = sorted(redirlist, key=redirlist.__getitem__, reverse=True)
        res = redirlist
        if self.opt.test:
            pywikibot.output('***** INPUT *****')
            pywikibot.output(redirlist)
            pywikibot.output('***** RESULT *****')
            pywikibot.output(res)
        linkcount = 0
        for i in res:
            linkcount += 1
            finalpage += "| %i || [[%s]] || %s || [[%s]] || %s\n|-\n" % (linkcount, i['long'], str(i['refl']) +
                                                                         ' link' + self.suffix(i['refl']), i['short'],
                                                                         str(i['refs']) + ' link' + self.suffix(
                                                                             i['refs']))

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

    def suffix(self, count):
        strcount = str(count)
        if count == 1:
            return ''
        elif strcount[-1] in ('2', '3', '4') and (count > 20 or count < 10):
            return 'i'
        else:
            return 'ów'

    def savepart(self, body, suffix, pagename, header, footer):
        if self.opt.test:
            pywikibot.output('***** FINALPAGE *****')
            pywikibot.output(body)

        outpage = pywikibot.Page(pywikibot.Site(), pagename + '/' + suffix)
        outpage.text = re.sub(r'@@', suffix, header) + body + footer
        outpage.save(summary=self.opt.summary)

        # if self.opt.test:
        #    pywikibot.output(redirlist)
        return

    def treat(self, page):
        # get all linkedPages
        # check for disambigs
        linksR = re.compile('\[\[(?P<short>[^\]]*)\]\] *\|\| *\[\[(?P<long>[^\]]*)\]\]')
        res = []
        counter = 0
        if self.opt.test:
            pywikibot.output('Treat(%s)' % page.title(as_link=True))
        for p in linksR.finditer(textlib.removeDisabledParts(page.text)):
            counter += 1
            longn = p.group('long')
            shortn = p.group('short')
            if self.opt.testlinks:
                pywikibot.output('[%s][#%i] S:%s L:%s' % (
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), counter, shortn, longn))
            rpl = pywikibot.Page(pywikibot.Site(), longn)
            rplcount = len(list(rpl.getReferences(namespaces=0)))
            if self.opt.testlinks:
                pywikibot.output('L:%s #%i In %s checking:%s - referenced by %i' %
                                 (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), counter,
                                  page.title(as_link=True), rpl.title(as_link=True), rplcount))
            rps = pywikibot.Page(pywikibot.Site(), shortn)
            rpscount = len(list(rps.getReferences(namespaces=0)))
            if self.opt.testlinks:
                pywikibot.output('S:%s #%i In %s checking:%s - referenced by %i' %
                                 (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), counter,
                                  page.title(as_link=True), rps.title(as_link=True), rpscount))

            res.append({"long": longn, "refl": rplcount, "short": shortn, "refs": rpscount})

        print(res)
        return res


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
