#!/usr/bin/python
"""
Creates a list of articles from featured list
Call:
    python pwb.py masti/ms-featured.py -page:"Kategoria:Artykuły na Medal" -outpage:"Wikipedia:Brakujące artykuły na medal z innych Wikipedii" -summary:"Bot aktualizuje listę"
    python pwb.py masti/ms-featured.py -page:"Kategoria:Dobre artykuły" -good -outpage:"Wikipedia:Brakujące dobre artykuły z innych Wikipedii" -summary:"Bot aktualizuje listę"
    python pwb.py masti/ms-featured.py -page:"Kategoria:Listy na Medal" -lists -outpage:"Wikipedia:Brakujące listy na medal z innych Wikipedii" -summary:"Bot aktualizuje listę"


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
from pywikibot.exceptions import NoPageError

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
        'outpage': 'User:mastiBot/test',  # default output page
        'maxlines': 1000,  # default number of entries per page
        'test': False,  # print testoutput
        'short': False,  # print testoutput
        'test3': False,  # print testoutput
        'test4': False,  # print testoutput
        'test5': False,  # print testoutput
        'negative': False,  # if True negate behavior i.e. mark pages that DO NOT contain search string
        'good': False,  # work on good articles
        'lists': False,  # work on featured lists
        'testinterwiki': False,  # make verbose output for interwiki
    }

    def run(self):
        """TEST"""
        result = {}

        outputpage = self.opt.outpage
        # pywikibot.output('OUTPUTPAGE:%s' % outputpage)
        for p in self.generator:
            if self.opt.test:
                pywikibot.output('Treating: %s' % p.title())
            result = self.treat(p)

        header = '{{Wikipedia:Brakujące artykuły/Nagłówek}}\n\n'
        if self.opt.good:
            header += 'Dobre Artykuły'
        elif self.opt.lists:
            header += 'Listy na Medal'
        else:
            header += 'Artykuły na Medal'

        header += ' w innych Wikipediach, które nie mają odpowiednika w polskiej Wikipedii\n\n'
        header += 'Ta strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|bota]].\n\n'
        header += "Ostatnia aktualizacja: '''" + datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S (CEST)") + "'''.\n\n"
        header += 'Wszelkie uwagi proszę zgłaszać w [[Dyskusja_Wikipedysty:Masti|dyskusji operatora]].\n\n'
        footer = ''

        self.generateresultspage(result, self.opt.outpage, header, footer)
        return

    def generateresultspage(self, redirlist, pagename, header, footer):
        """
        Generates results page from redirlist
        Starting with header, ending with footer
        Output page is pagename
        """
        finalpage = header
        res = sorted(redirlist.keys())
        itemcount = 0
        for i in res:
            if i in ('pl'):
                continue
            itemcount += 1
            # section header == aa.wikipedia (x z y)
            finalpage += '\n\n== %s.wikipedia (%i z %i) ==' % (i, redirlist[i]['marked'], redirlist[i]['count'])
            # items
            for a in sorted(redirlist[i]['result']):
                finalpage += '\n# [[:%s:%s]]' % (i, a)

        finalpage += footer

        success = True
        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        outpage.text = finalpage

        if self.opt.test:
            pywikibot.output(outpage.title())

        outpage.save(summary=self.opt.summary)
        # if not outpage.save(finalpage, outpage, self.summary):
        #   pywikibot.output('Page %s not saved.' % outpage.title(as_link=True))
        #   success = False
        return (success)

    def interwikiGenerator(self, page):
        # yield interwiki sites generator
        for s in page.iterlanglinks():
            if self.opt.testinterwiki:
                pywikibot.output('SL iw: %s' % s)
            try:
                spage = pywikibot.Category(s)
            except Exception as e:
                pywikibot.output('Category page EXCEPTION %s' % str(e))
                continue
            if self.opt.testinterwiki:
                pywikibot.output('SL spage')
                pywikibot.output('gI Page: %s' % spage.title(force_interwiki=True))
            yield spage

    '''
    def interwikiGenerator(self,wdpage,namespace=0):
        # yield a list of categories based on wikidata sitelinks
        for i in wdpage['sitelinks']:
            if i.endswith('wiki'):
                lang = self.wikiLangTranslate(i[:-4])
                try:
                    if namespace == 14:
                        yield pywikibot.Category(pywikibot.Site(lang,'wikipedia'), wdpage['sitelinks'][i])
                    else:
                        yield pywikibot.Page(pywikibot.Site(lang,'wikipedia'), wdpage['sitelinks'][i])
                except:
                    pywikibot.output('ERROR: site %s does not exist!' % lang)
    '''

    def checkInterwiki(self, page, lang):
        """Check if lang is in list of interwikis"""
        if self.opt.test3:
            pywikibot.output('[%s] Treating (checkInterwiki): %s' % (
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), page.title()))
        try:
            wd = pywikibot.ItemPage.fromPage(page)
            wdcontent = wd.get()
            if self.opt.test3:
                pywikibot.output('[%s] checkInterwiki: %s' % (
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), wdcontent['sitelinks'].keys()))
            return lang in wdcontent['sitelinks'].keys()
        except NoPageError:
            return False

    def wikiLangTranslate(self, lang):
        # change lang in case of common errors, renames etc.
        translateTable = {
            'dk': 'da',  # Wikipedia, Wikibooks and Wiktionary only.
            'jp': 'ja',
            'nb': 'no',  # T86924
            'minnan': 'zh-min-nan',
            'nan': 'zh-min-nan',
            'zh-tw': 'zh',
            'zh-cn': 'zh',
            'nl_nds': 'nl-nds',
            'be-x-old': 'be-tarask',
            'be_x_old': 'be-tarask',
        }

        if lang in translateTable.keys():
            pywikibot.output('Translated [%s] -> [%s]' % (lang, translateTable[lang]))
            return translateTable[lang]
        else:
            pywikibot.output('unTranslated [%s]' % lang)
            return lang

    def treat(self, page):
        result = {}

        '''
        try:
            wd = pywikibot.ItemPage.fromPage(page)
            wdcontent = wd.get()
            if self.opt.test:
                pywikibot.output(wdcontent['sitelinks'].keys())
        except:
            pywikibot.output('WikiData page for %s do not exists' % page.title(as_link=True))
            return(None)
        '''

        count = 0
        for c in self.interwikiGenerator(page):
            if self.opt.test:
                pywikibot.output(c.title())
            code = c.site.code
            count += 1
            if self.opt.short:
                pywikibot.output('Code:%s' % c.site.code)
                # if lang not in ('be-tarask','tt'):
                if code not in 'de':
                    continue
            if self.opt.test:
                pywikibot.output('[%i] P:%s' % (count, c.title(as_link=True, force_interwiki=True)))
                # pywikibot.output('SI:%s' % c.site.siteinfo)

            result[code] = self.getArticles(c)
        if self.opt.test4:
            pywikibot.output(result)
        return result

    def getArticles(self, cat):
        # return a list of article titles without pl.interwiki
        if self.opt.test5:
            pywikibot.output("get articles")
        count = 0
        marked = 0
        result = []
        lang = cat.site.code
        for a in cat.articles():
            if self.opt.test:
                pywikibot.output('[%s] %s.wiki: [%i of %i] %s' % (
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), lang, marked, count,
                a.title(as_link=True, force_interwiki=True)))
            count += 1
            if a.namespace() == 1:
                a = a.toggleTalkPage()
            if a.namespace() != 0:
                # skip non main articles
                continue
            if not self.checkInterwiki(a, 'plwiki'):
                result.append(a.title())
                marked += 1
                if self.opt.test3:
                    pywikibot.output('[%s] appended: %s' % (
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), a.title(as_link=True, force_interwiki=True)))
        return {'count': count, 'marked': marked, 'result': result}


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
    if gen:
        # pass generator and private options to the bot
        bot = BasicBot(generator=gen, **options)
        bot.run()  # guess what it does
    else:
        pywikibot.bot.suggest_help(missing_generator=True)


if __name__ == '__main__':
    main()
