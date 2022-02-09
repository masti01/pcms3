#!/usr/bin/python
"""
Usage:
python3 pwb.py masti/m-isap.py -page:"Wikipedysta:MastiBot/DU" -summary:"Bot poprawia odwołania do ustawy" -outpage:'Wikipedysta:MastiBot/DU/log' -pt:0

Page should contain a list of {{Dziennik Ustaw}} linking to a new wersion of law.

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
from bs4 import BeautifulSoup
import urllib
import re
from datetime import datetime


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
    WUs = {}  # dict to keep info on processed templates

    update_options = {
        'replace': False,  # delete old text and write the new text
        'summary': None,  # your own bot summary
        'text': 'Test',  # add this text from option. 'Test' is default
        'top': False,  # append text on top of the page
        'outpage': u'User:mastiBot/test',  # default output page
        'maxlines': 10000,  # default number of entries per page
        'test': False,  # print testoutput
        'negative': False,  # if True negate behavior i.e. mark pages that DO NOT contain search string
        'id': '20190000506',  # starting isap page id - for test only
    }

    def run(self):
        """TEST"""
        toReplace = {}
        outputpage = self.opt.outpage
        pywikibot.output(u'OUTPUTPAGE:%s' % outputpage)

        for p in self.generator:
            pywikibot.output(u'Treating: %s' % p.title())
            self.treat(p)

        return

    def createReplaceList(self, docNumber):
        # replace a list of regex for replacement
        repl = []
        for tr in self.toReplaceIDs(docNumber):
            repl.append(self.replEncode(tr))
            repl.append(self.replEncode(tr, labels=True))
        if self.opt.test:
            pywikibot.output(repl)
        if len(repl):
            return (repl)
        else:
            return (None)

    def newTemplate(self, docNumber):
        # encode DU Number in new {{Dziennik Ustaw}}
        year, volume, position = self.decodeDUid(docNumber)
        if year > 2011:
            return ('{{Dziennik Ustaw|%i|%i}}' % (year, position))
        else:
            return ('{{Dziennik Ustaw|%i|%i|%i}}' % (year, volume, position))

    def replEncode(self, docNumber, labels=False):
        # encode docNumber in replacement string
        # with labels: {{Dziennik Ustaw|rok=1997|numer=88|pozycja=553}} {{Dziennik Ustaw|rok=2016|pozycja=1137}}
        # without labels: {{Dziennik Ustaw|1997|88|553}} {{Dziennik Ustaw|2016|1137}}
        year, volume, position = self.decodeDUid(docNumber)

        if labels:
            if year > 2011:
                repl = r'{{Dziennik Ustaw\s*\|\s*rok\s*=\s*%s\s*\|\s*numer\s*=\s*\|\s*pozycja\s*=\s*%s\s*}}' % (
                year, position)
            else:
                repl = r'{{Dziennik Ustaw\s*\|\s*rok\s*=\s*%s\s*\|\s*numer\s*=\s*%s\s*\|\s*pozycja\s*=\s*%s\s*}}' % (
                year, volume, position)
        else:
            if year > 2011:
                repl = r'{{Dziennik Ustaw\s*\|\s*%s\s*\|\s*%s\s*}}' % (year, position)
            else:
                repl = r'{{Dziennik Ustaw\s*\|\s*%s\s*\|\s*%s\s*\|\s*%s\s*}}' % (year, volume, position)
        return (repl)

    def getInitialWebPage(self, docNumber):
        # specify the url
        quote_page = 'http://prawo.sejm.gov.pl/isap.nsf/DocDetails.xsp?id=WDU%s' % docNumber
        if self.opt.test:
            pywikibot.output('getInitialWebPage:%s' % quote_page)
        webpage =  urllib.request.urlopen(quote_page)
        if webpage:
            pywikibot.output("webpage: %s" % webpage)
        else:
            pywikibot.output("NO WEBPAGE")
        if self.opt.test:
            pywikibot.output('webpage:%s' % webpage)
        soup = BeautifulSoup(webpage, 'html.parser')
        if self.opt.test:
            pywikibot.output('Soup:%s' % soup)
            pywikibot.output('Web Page:%s' % quote_page)
            pywikibot.output('Title:%s' % soup.title.string)

        idR = re.compile(r'\/isap\.nsf\/DocDetails\.xsp\?id=WDU(?P<id>.*)')
        ident = idR.search(soup.find(id="collapse_10").find('a').get('href'))

        if self.opt.test:
            pywikibot.output('ID:%s' % ident.group('id'))
        return (ident.group('id'))

    def toReplaceIDs(self, docNumber):
        # yield a list of IDs to be replaced
        quote_page = 'http://prawo.sejm.gov.pl/isap.nsf/DocDetails.xsp?id=WDU%s' % docNumber
        if self.opt.test:
            pywikibot.output('getting target page:%s' % quote_page)
        webpage = urllib.request.urlopen(quote_page)
        soup = BeautifulSoup(webpage, 'html.parser')
        idR = re.compile(r'\/isap\.nsf\/DocDetails\.xsp\?id=WDU(?P<id>.*)')
        first = True
        for t in soup.find(id="collapse_14").find_all('a'):
            if first:
                first = False
            else:
                ident = idR.search(t.get('href'))
                yield (ident.group('id'))

    def decodeDUid(self, ident):
        # convert WDU ID to year,number,position
        dR = re.compile(r'(?P<rok>\d{4})(?P<nr>\d{3})(?P<poz>\d{4})')
        data = dR.match(ident)
        return ((int(data.group('rok')), int(data.group('nr')), int(data.group('poz'))))

    def encodeDUid(self, year, number, position):
        # create WDU ID from year,number,position
        return ('%04i%03i%04i' % (year, number, position))

    def getDUTemplateList(self, text):
        # return list of {{Dziennik Ustaw}} templates from text (page)
        duR = re.compile(r'(?m)^\* \{\{Dziennik Ustaw[^\}]*}}.*$')
        # duR = re.compile(r'\{\{Dziennik Ustaw[^\}]*}}')
        if self.opt.test:
            pywikibot.output('FindAll:%s' % duR.findall(text))
        return (duR.findall(text))

    def WUid(self, templ):
        # return isap WU id from {{Dziennik Ustaw}}
        if self.opt.test:
            pywikibot.output('DU(WUID):%s' % templ)
        duR = re.compile(
            r'\** *\{\{Dziennik Ustaw\s*\|\s*(?P<one>\d*)\s*\|\s*(?P<two>\d*)\s*(\|\s*(?P<three>\d*))?\}\}')
        du = duR.match(templ)
        if du:
            year = int(du.group('one'))
            if year > 2011:
                pos = int(du.group('two'))
                vol = 0
            else:
                pos = int(du.group('three'))
                vol = int(du.group('two'))
            return (self.encodeDUid(year, vol, pos))
        else:
            return (None)

    def fixPage(self, page):
        # get page, do replacements, save
        if self.opt.test:
            pywikibot.output('Fixing page: %s' % page.title(as_link=True))
        text = page.text
        replCount = 0
        for k in self.WUs.keys():
            if self.WUs[k]['toReplace']:
                regex = "|".join(self.WUs[k]['toReplace'])
                #if self.opt.test:
                #    pywikibot.output('Regex:%s New:%s' % (regex, self.WUs[k]['newTemplate']))
                text, count = re.subn(regex, self.WUs[k]['newTemplate'], text)
                if self.opt.test:
                    pywikibot.output('[%s] Relacements:%s' % (k,count))
                if count:
                    self.WUs[k]['replacements'][page.title()] = count
                replCount += count
            else:
                if self.opt.test:
                    pywikibot.output("ERROR: skiping %s due to no replacements for %s" % (page.title(as_link=True), k))

        if page.text != text:
            page.text = text
            try:
                page.save(summary=self.opt.summary)
            except pywikibot.exceptions.EditConflict:
                pywikibot.output('ERROR: EditConflict in %s' % page.title)
        return (replCount)

    def treat(self, page):

        # get templates from page

        text = page.text

        for d in self.getDUTemplateList(text):
            if self.opt.test:
                pywikibot.output('DU:%s' % d)
            # generate list of WU ids self.WUid
            # save for future cleanup {'line':d}
            self.WUs[self.WUid(d)] = {'line': d, 'replacements': {}, 'error': False}

        if self.opt.test:
            pywikibot.output('WUs:%s' % self.WUs)

        # generate replacement dictionary
        for tr in self.WUs.keys():
            self.WUs[tr]['newTemplate'] = self.newTemplate(tr)
            try:
                self.WUs[tr]['toReplace'] = self.createReplaceList(self.getInitialWebPage(tr))
            except urllib.error.HTTPError:
                self.WUs[tr]['toReplace'] = None
                self.WUs[tr]['error'] = 'Brak strony w systemie isap'
            if not self.WUs[tr]['error'] and not self.WUs[tr]['toReplace']:
                self.WUs[tr]['error'] = 'Brak poprzednich wersji tekstu jednolitego'

        if self.opt.test:
            pywikibot.output('toReplace:%s' % self.WUs)
            pywikibot.output('toReplace LEN:%s' % len(self.WUs))

        if len(self.WUs):
            # get pages transcluding {{Dziennik Ustaw}}
            duTemplatePage = pywikibot.Page(pywikibot.Site(), 'Dziennik Ustaw', ns=10)
            count = 0
            rpages = 0  # fixed pages count
            rcount = 0  # replacements done
            for du in duTemplatePage.getReferences(only_template_inclusion=True, namespaces=0):
                count += 1
                if count > int(self.opt.maxlines):
                    break
                if self.opt.test:
                    pywikibot.output(
                        '[%s] Page (%i):%s' % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), count, du.title()))
                # run replacements
                rc = self.fixPage(du)  # count pages and replacements made
                if rc:
                    rpages += 1
                    rcount += rc
                    if self.opt.test:
                        # pywikibot.output('Fixpages WUs:%s' % self.WUs)
                        pywikibot.output('Fixpages WUs:%s' % du.title())
            if self.opt.test:
                pywikibot.output('[%s] %i replacements on %i pages after processing %i pages.' % (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), rcount, rpages, count - 1))
            # generate log
            # cleanup
            self.cleanup(page)
            self.logUpdate()
            # page.text = header
            # page.save(summary='Bot czyści stronę po zakończeniu działania (isap)')
        else:
            pywikibot.output('*** Nothing to do ***')
        return

    def cleanup(self, page):
        # cleanup input page - removig used templates
        text = page.text
        for k in self.WUs.keys():
            if not self.WUs[k]['error'] == 'Brak strony w systemie isap':
                text = text.replace(self.WUs[k]['line'], '')
            else:
                text = self.commentSource(text, self.WUs[k]['line'])
        if self.opt.test:
            pywikibot.output('FINALPAGE:%s' % text)
        page.text = text
        page.save(summary='Bot usuwa wykonane zadania')
        return

    def commentSource(self, text, torepl):
        # replace source line 'text' with updated last check datetime
        toreplR = re.compile(r'(\*.*?}}).*')
        line = toreplR.sub('\\1', torepl) +' <small>(Dokument niedostępny %s)</small>' % datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = re.sub(re.escape(torepl),line,text)
        return(text)

    def logUpdate(self):
        # update log file defined in outpage
        l = []
        pages = 0

        newline = ''
        for k in self.WUs.keys():
            if not self.WUs[k]['error']:
                replacements = 0
                for r in self.WUs[k]['replacements'].keys():
                    replacements += self.WUs[k]['replacements'][r]
                newline += '\n|-\n| %s || %s || %i || %i' % (
                datetime.now().strftime("%Y-%m-%d"), self.WUs[k]['newTemplate'], len(self.WUs[k]['replacements']),
                replacements)
            else:
                newline += '\n|-\n| %s || %s || colspan=2 style="background-color:Yellow"| <small>%s</small>' % (
                datetime.now().strftime("%Y-%m-%d"), self.WUs[k]['newTemplate'], self.WUs[k]['error'])
        pywikibot.output('Added log entries:%s' % newline)
        newline += '\n|}'

        page = pywikibot.Page(pywikibot.Site(), self.opt.outpage)
        page.text = page.text.replace('\n|}', newline)
        if self.opt.test:
            pywikibot.output('LOG FILE:%s' % page.text)
        page.save(summary='Bot uaktualnia log')
        return


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
        if option in ('summary', 'text', 'outpage', 'maxlines', 'id'):
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
