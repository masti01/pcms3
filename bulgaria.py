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

This sample script is a
:py:obj:`ConfigParserBot <pywikibot.bot.ConfigParserBot>`. All settings can be
made either by giving option with the command line or with a settings file
which is scripts.ini by default. If you don't want the default values you can
add any option you want to change to that settings file below the [basic]
section like:

    [basic] ; inline comments starts with colon
    # This is a comment line. Assignments may be done with '=' or ':'
    text: A text with line break and
        continuing on next line to be put
    replace: yes ; yes/no, on/off, true/false and 1/0 is also valid
    summary = Bot: My first test edit with pywikibot

Every script has its own section with the script name as header.

In addition the following generators and filters are supported but
cannot be set by settings file:

&params;
"""
import re
from urllib.request import Request, urlopen

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

# This is required for the text that is shown when you run this script
# with the parameter -help.
docuReplacements = {'&params;': pagegenerators.parameterHelp}  # noqa: N816

ekatte = {}
ekatte_list = {}


class Demography():
    def __init__(self, name=None, ekatteid=None, opt=False):
        """Initializer."""

        self.name = name
        self.ekatte_id = ekatteid
        self.search_id = self._search_page(self.ekatte_id)
        self.demo_data = self._demo_data(self.search_id)
        self.opt = opt

    def __str__(self):
        return '[[{self.name}]]: EKATTE:{self.ekatte_id} SID:{self.search_id} -> {self.demo_data}'.format(self=self)

    def _search_page(self, ekatteid):
        quote_page = 'https://nsi.bg/nrnm/index.php?ezik=en&f=9&search=%s' % ekatteid
        web = Request(quote_page, headers={'User-Agent': 'Mozilla/5.0'})
        webpage = urlopen(web, timeout=10).read()

        sidR = re.compile(r"<a href=\"show9\.php\?sid=(?P<sid>\d+)")
        sid = sidR.search(str(webpage)).group('sid')
        pywikibot.output('SID:{}'.format(sid))

        return sid

    def _demo_data(self, sid):
        data = []
        quote_page = 'https://nsi.bg/nrnm/show9.php?sid=%s&ezik=en' % sid
        web = Request(quote_page, headers={'User-Agent': 'Mozilla/5.0'})
        webpage = urlopen(web, timeout=10).read()

        drowR = re.compile(r'(?is)<tr>\\n(?P<table>.*?)\\n</tr>')
        datesR = re.compile(r'(?i).*?(?P<year>\d{4})</td>\\n.*?(?P<population>\d*)</td>\\n.*?Census')
        for dr in drowR.finditer(str(webpage)):
            # pywikibot.output('DR:%s' % dr.group('table'))
            dates = datesR.search(dr.group('table'))
            if dates:
                # pywikibot.output('Dates::%s' % str(dates))
                data.append((dates.group('year'), dates.group('population')))

        return (data)

    @property
    def demo_template(self):
        text = '\n== Demografia =='
        text += '\n{{Wykres demograficzny'
        text += '\n| tytuł = Liczba ludności według danych ze spisów powszechnych'

        count = 0
        for year, pop in self.demo_data:
            count += 1
            text += '\n | rok{} = {} || pop{} = {}'.format(count, year, count, pop)

        text += '\n| źródło = Narodowy Instytut Statystyczny<ref>{{Cytuj stronę | url = ' \
                'https://www.nsi.bg/nrnm/show9.php?sid=%s&ezik=en | tytuł = NATIONAL REGISTER OF POPULATED PLACES | ' \
                'opublikowany = Narodowy Instytut Statystyczny Bułgarii | język = en | data dostępu = ' \
                '2021-12-28}}</ref>' % self.search_id
        text += '\n}}'

        return text


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
        'outpage': u'User:mastiBot/test',  # default output page
        'maxlines': 10000,  # default number of entries per page
        'test': False,  # print testoutput
    }

    def run(self):
        """TEST"""
        outputpage = self.opt.outpage
        if self.opt.test:
            pywikibot.output(u'OUTPUTPAGE:%s' % outputpage)

        for p in self.generator:
            pywikibot.output(u'Treating: %s' % p.title())
            self.treat(p)

        page = pywikibot.Page(pywikibot.Site(), self.opt.outpage)
        page.text = 'Dane statystyczne: {{państwo|BUL}}\n\n'
        for p in ekatte_list:
            pywikibot.output(ekatte_list[p])
            page.text += ekatte_list[p].demo_template
            page.text += '\n* {ekatte_list[p]}'

        page.save(summary=self.opt.summary)
        return

    def ekatte_id(self, page):  # get EKATTE ID from WikiData
        wd = page.data_item()

        wd.get()

        ekatteR = re.compile('\d+?')  # new EKATTE is digits only
        try:
            claims3990 = wd.claims['P3990']  # get EKATTE ID
            for c in claims3990:
                value = c.getTarget()
                if ekatteR.match(value):
                    if self.opt.test:
                        pywikibot.output("Page {}, value:{}".format(page.title(as_link=True), value))
                    return value
                else:
                    if page.title() not in ekatte.keys():
                        if self.opt.test:
                            pywikibot.output("Page {}, WRONG value:{}".format(page.title(as_link=True), value))
                        return None
        except:
            if self.opt.test:
                pywikibot.output("Page {}, no EKATTE".format(page.title(as_link=True)))
            return None

    def treat(self, page) -> None:
        """Load the given page, do some changes, and save it."""

        ekatte[page.title()] = self.ekatte_id(page)

        demo = Demography(page.title(), ekatte[page.title()], opt=True)

        if self.opt.test:
            pywikibot.output("Demo:{}".format(demo))
        ekatte_list[page.title()] = demo

        return  # remove after preparing to update each page
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
        arg, sep, value = arg.partition(':')
        option = arg[1:]
        if option in ('summary', 'text', 'outpage'):
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
