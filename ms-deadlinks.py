#!/usr/bin/python
"""
This bot creates a pages with links to disambig pages with ref counts.
Wikipedysta:MastiBot/Statystyka martwych linków
Wikipedysta:MastiBot/Statystyka martwych linków/ogólne

Call:
python pwb.py masti/ms-deadlinks.py -cat:"Niezweryfikowane martwe linki" -ns:1 -outpage:"Wikipedysta:MastiBot/Statystyka martwych linków" -summary:"Bot uaktualnia stronę" -maxlines:3000

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
    SingleSiteBot,
)
import re
import datetime
import time
from random import randint

from artnosml import linkcolor

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

    summary_key = 'basic-changing'
    use_redirects = False

    update_options = {
        'replace': False,  # delete old text and write the new text
        'summary': None,  # your own bot summary
        'text': 'Test',  # add this text from option. 'Test' is default
        'top': False,  # append text on top of the page
        'outpage': 'Wikipedysta:mastiBot/test',  # default output page
        'maxlines': 1000,  # default number of entries per page
        'test': False,  # test options
        'progress': False,  # display progress
        'includes': False,  # only include links that include this text
        'delays': False, # test for delays
    }

    def run(self):

        if self.opt.test:
            pywikibot.output(self.opt.includes)

        headerfull = "Poniżej znajduje się lista " + self.opt.maxlines + " martwych linków występujących w największej liczbie artykułów.\n\n"
        headersum = headerfull
        if not self.opt.includes:
            headersum += "Zobacz też: [[" + self.opt.outpage + "|Statystykę szczegółowych linków]]\n\n"
            headerfull += "Zobacz też: [[" + self.opt.outpage + "/ogólne|Statystykę domen z największą liczbą martwych linków]]\n\n"

        headerfull += "Ta strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|MastiBota]]. Ostatnia aktualizacja ~~~~~. \n"
        headerfull += "Wszelkie uwagi proszę zgłaszać w [[Dyskusja_Wikipedysty:Masti|dyskusji operatora]].\n\n"
        headersum += "Ta strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|MastiBota]]. Ostatnia aktualizacja ~~~~~. \n"
        headersum += "Wszelkie uwagi proszę zgłaszać w [[Dyskusja_Wikipedysty:Masti|dyskusji operatora]].\n\n"
        footer = ''

        deadlinksf = {}  # full links
        deadlinkss = {}  # summary links
        deadlinksfuse = {}  # full links
        deadlinkssuse = {}  # summary links
        licznik = 0
        for page in self.generator:
            licznik += 1
            if self.opt.progress:
                pywikibot.output('[%s]Treating #%i: %s' % (
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), licznik, page.title()))
            refs = self.treat(page)  # get list of weblinks
            for ref, rcount in refs:
                # if self.opt.test:
                #    pywikibot.output('REFS: %s' % refs)
                if ref in deadlinksf:
                    deadlinksf[ref] += 1
                    deadlinksfuse[ref] += rcount
                else:
                    deadlinksf[ref] = 1
                    deadlinksfuse[ref] = rcount
                if self.opt.test:
                    pywikibot.output('%s - %i' % (ref, deadlinksf[ref]))

        deadlinkss, deadlinkssuse = self.getDomainStats(deadlinksf, deadlinksfuse)

        footer = 'Przetworzono: ' + str(licznik) + ' stron'

        result = self.generateresultspage(deadlinksf, deadlinksfuse, self.opt.outpage, headerfull, footer)
        # skip domains grouping if looking for specific text
        # if not self.opt.includes:
        result = self.generateresultspage(deadlinkss, deadlinkssuse, self.opt.outpage + '/ogólne', headersum, footer)

        return

    def getDomainStats(self, dl, dluse):
        deadlinksf = {}
        deadlinksfuse = {}
        # domainR = re.compile(r'(?P<domain>https?://[^\/]*)')
        domainR = re.compile(r'https?://(www\.)?(?P<domain>[^/$]*)')

        for l in dl.keys():
            try:
                dom = 'https://{0}'.format(domainR.match(l).group('domain'))
                if self.opt.test:
                    pywikibot.output('Domain:link:%s' % dom)
                if dom in deadlinksf.keys():
                    deadlinksf[dom] += dl[l]
                    deadlinksfuse[dom] += dluse[l]
                else:
                    deadlinksf[dom] = dl[l]
                    deadlinksfuse[dom] = dluse[l]
            except:
                pywikibot.output('Missing domain group in %s' % l)

        return deadlinksf, deadlinksfuse

    def getRefsNumber(self, weblink, text):
        # find how many times link is referenced on the page
        # ref names including group
        # refR = re.compile(r'(?i)<ref (group *?= *?"?(?P<group>[^>"]*)"?)?(name *?= *?"?(?P<name>[^>"]*)"?)?>\.?\[?(?P<url>http[s]?:(\/\/[^:\s\?]+?)(\??[^\s<]*?)[^\]\.])(\]|\]\.)?[ \t]*<\/ref>')
        refR = re.compile(
            r'(?im)<ref (group *?= *?"?(?P<group>[^>"]*)"?)?(name *?= *?"?(?P<name>[^>"]*)"?)?>.*?%s.*?<\/ref>' % re.escape(
                weblink).strip())

        """
        opcje wywołania: <ref name="BVL2006" /> {{u|BVL2006}} {{r|BVL2006}}
        """

        # check if weblink is in named ref
        linkscount = 0
        # for r in refR.finditer(text):
        r = refR.search(text)
        if r:
            if r.group('name'):
                if self.opt.test:
                    pywikibot.output('Treat:NamedRef:%s' % r.group('name'))
                # template to catch note/ref with {{u}} or {{r}}
                ruR = re.compile(
                    r'(?i)(?:{{[ur] *?(?:[^\|}]*\|)*|<ref *?name *?= *?\"?)(%s)(?:[^}\/]*}}|\"? \/>)' % re.escape(
                        r.group('name').strip()))
                if self.opt.test:
                    pywikibot.output(
                        'Treat:Regex:(?i)(?:{{[ur] *?(?:[^\|}]*\|)*|<ref *?name *?= *?\"?)(%s)(?:[^}\/]*}}|\"? \/>)' % re.escape(
                            r.group('name').strip()))
                match = ruR.findall(text)
                linkscount += len(match)
                if self.opt.test:
                    pywikibot.output('Treat:Templates matched:%s' % match)
        if self.opt.test:
            pywikibot.output('Treat:links count:%s' % linkscount)

        # catch unnamed links
        match = re.findall(re.escape(weblink), text)
        linkscount += len(match)
        if self.opt.test:
            pywikibot.output('Treat:Loose links matched:%s' % match)
            pywikibot.output('Treat:links count:%s' % linkscount)

        return linkscount

    def getarttext(self, art):
        while True:
            try:
                arttext = art.text
                break
            except pywikibot.exceptions.ServerError:
                delay = randint(5,100)
                if self.opt.delays:
                    pywikibot.output(f'Delaying {delay}s in [[{art.title()}]]')
                time.sleep(delay)
        return arttext

    def treat(self, page):
        """
        Creates a list of weblinks
        """
        refs = []
        tempR = re.compile(r'(?P<template>\{\{Martwy link dyskusja[^}]*?}}\n*?)')
        # weblinkR = re.compile(r'link\s*?=\s*?\*?\s*?(?P<weblink>[^\n\(]*)')
        weblinkR = re.compile(r'link *?= *?\*? (?P<weblink>[^\n ]*)')
        if self.opt.test:
            pywikibot.output('domains=False')
        links = ''
        art = page.toggleTalkPage()
        # arttext = art.text
        arttext = self.getarttext(art)
        templs = tempR.finditer(page.text)
        for link in templs:
            template = link.group('template').strip()
            if self.opt.test:
                pywikibot.output(template)
            try:
                weblink = re.search(weblinkR, template).group('weblink').strip()
            except:
                continue
            linkscount = self.getRefsNumber(weblink, arttext)
            refs.append((weblink, linkscount))
            if self.opt.test:
                pywikibot.output('Treat Weblink:%s' % weblink)
                pywikibot.output('Treat Usage:%i' % linkscount)
            # except:
            #    pywikibot.output('Error in page %s' % page.title(asLink=True))

        return refs

    def SpamCheck(self, url):
        r = pywikibot.data.api.Request(parameters={'action': 'spamblacklist', 'url': url})
        data = r.submit()
        return data['spamblacklist']['result'] == 'blacklisted'

    def shortenlink(self,link):
        # if link longer than 150 chars
        if len(link) > 150:
            return f'[{link} {link[:50]}...{link[-50:]}]'
        else:
            return link

    def generateresultspage(self, redirlist, redirlistuse, pagename, header, footer):
        """
        Generates results page from redirlist
        Starting with header, ending with footer
        Output page is pagename
        """
        maxlines = int(self.opt.maxlines)
        finalpage = header

        finalpage += '\n{| class="wikitable sortable" style="font-size:85%;"'
        finalpage += '\n|-'
        finalpage += '\n!Nr'
        finalpage += '\n!Link'
        finalpage += '\n!Liczba stron'
        finalpage += '\n!Liczba odnośników'

        res = sorted(redirlist, key=redirlist.__getitem__, reverse=True)
        itemcount = 0
        pywikibot.output('res length:%i' % len(res))
        for i in res[:int(self.opt.maxlines)]:
            # use only links with -includes if specified
            if self.opt.includes:
                if not (self.opt.includes in i):
                    continue

            # check for spamlist entry
            spam = self.SpamCheck(i)

            itemcount += 1
            count = redirlist[i]
            strcount = str(count)
            # suffix = self.declination(count, 'wystąpienie', 'wystąpienia', 'wystąpień')
            suffix = self.declination(count, 'strona', 'strony', 'stron')
            linksuffix = self.declination(redirlistuse[i], 'odnośnik', 'odnośniki', 'odnośników')

            # finalpage += '#' + i + ' ([{{fullurl:Specjalna:Wyszukiwarka linków/|target=' + i + '}} ' + str(count) + ' ' + suffix + '])\n'
            if self.opt.test:
                pywikibot.output('(%d, %d) #%s (%s %s)' % (itemcount, len(finalpage), i, str(count), suffix))
            if spam:
                finalpage += f'\n|-\n| {str(itemcount)} || <nowiki>{self.shortenlink(i)}</nowiki><sup>SPAM</sup> || style="width: 20%; align="center" | [{{{{fullurl:Specjalna:Wyszukiwarka linków/|target={i}}}}} {str(count)} {suffix}]'
            else:
                # finalpage += '\n|-\n| ' + str(
                #     itemcount) + ' || ' + i + ' || style="width: 20%;" align="center" | [{{fullurl:Specjalna:Wyszukiwarka linków/|target=' + i + '}} ' + str(
                #     count) + ' ' + suffix + ']'
                finalpage += f'\n|-\n| {str(itemcount)} || {self.shortenlink(i)} || style="width: 20%; align="center" | [{{{{fullurl:Specjalna:Wyszukiwarka linków/|target={i}}}}} {str(count)} {suffix}]'
            finalpage += f' || {redirlistuse[i]} {linksuffix}'
            # if itemcount >= maxlines:
            #     pywikibot.output('*** Breaking output loop ***')
            #     break

        finalpage += '\n|}\n'
        finalpage += footer

        if self.opt.test:
            pywikibot.output(finalpage)
        success = True
        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        outpage.text = finalpage

        if self.opt.test:
            pywikibot.output(outpage.title())

        outpage.save(summary=self.opt.summary)
        return success

    def declination(self, v, t1, t2, t3):
        if v == 0:
            return (t3)
        elif v == 1:
            return (t1)
        elif v % 10 in (2, 3, 4) and (v < 10 or v > 20):
            return (t2)
        else:
            return (t3)
        # value = int(str(v)[-2:])
        # if value == 0:
        #     return (t3)
        # elif value == 1:
        #     return (t1)
        # elif value < 5:
        #     return (t2)
        # else:
        #     return (t3)


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
        if option in ('summary', 'text', 'outpage', 'maxlines', 'includes'):
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
