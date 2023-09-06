#!/usr/bin/env python3
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
import pywikibot
from pywikibot import pagegenerators
from pywikibot.bot import (
    AutomaticTWSummaryBot,
    ConfigParserBot,
    ExistingPageBot,
    SingleSiteBot,
)
from pywikibot import textlib
import re
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
        'outpage': 'Wikipedysta:mastiBot/test',  # default output page
        'maxlines': 1000,  # default number of entries per page
        'maxresults': 100,  # default number of results
        'test': False,  # test options
        'progress': False,  # display progress
        'append': False,  # append results to page
        'section': None,  # section title
        'title': False,  # check in title not text
        'includes': False,  # only include links that include this text
        'edit': False,  # link thru template:edytuj instead of wikilink
        'cite': False,  # cite search results
        'nowiki': False,  # put citation in <nowiki> tags
        'count': False,  # count pages only
        'navi': False,  # add navigation template
        'progress': False,  # report progress
        'wikipedia': False,  # report only wikipedia links
        'noimages': False,  # do not include image links
    }

    def run(self):

        if not self.opt.append:
            # header = "Ta strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|MastiBota]]. Ostatnia aktualizacja ~~~~~. \n"
            # header = "Ostatnia aktualizacja: '''<onlyinclude>{{#time: Y-m-d H:i|{{REVISIONTIMESTAMP}}}}</onlyinclude>'''.\n\n"
            header = "Ostatnia aktualizacja: '''~~~~~'''."
            header += "\n\nWszelkie uwagi proszę zgłaszać w [[User talk:masti|dyskusji operatora]]."
            header += "\n:Lista stron zawierających linki do innych Wikipedii w postaci linku webowego - często uzywane jako nieprawidłowe źródło."
            if self.opt.noimages:
                header += "\n:Pominięto linki do grafik."
            header += "\n\n{{Wikiprojekt:Strony zawierające linki webowe do innych Wikipedii/Nagłówek}}"

        header += '\n\n{| class="wikitable sortable" style="text-align:center"'
        header += '\n! Lp.'
        header += '\n! Link'
        header += '\n! Stron'
        header += '\n! Artykuły'

        reflinks = {}  # initiate list
        pagecounter = 0
        duplicates = 0
        marked = 0
        for page in self.generator:
            pagecounter += 1
            if self.opt.test or self.opt.progress:
                # pywikibot.output('[%s] Treating #%i (marked:%i, duplicates:%i): %s' % (
                #     datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pagecounter, marked, duplicates,
                #     page.title()))
                pywikibot.output(f'[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Treating #{pagecounter} (marked:{marked}): {page.title()}')
            # if page.title() in reflinks:
            #     duplicates += 1
            #     continue
            refs = self.treat(page)  # get (name)

            for r in refs:
                if r.get("links") in reflinks.keys():
                    reflinks[r.get("links")].append(page.title())
                    marked += 1
                else:
                    reflinks[r.get("links")] = [page.title()]

            if len(refs):
                marked += 1

            if marked > int(self.opt.maxresults) - 1:
                pywikibot.output('MAXRESULTS limit reached')
                break

        footer = '\n\nPrzetworzono ' + str(pagecounter) + ' stron.'
        footer += '\n\n[[Kategoria:Wikiprojekt Strony zawierające linki webowe do innych Wikipedii]]'

        outputpage = self.opt.outpage

        pywikibot.output(str(reflinks))
        return self.generateresultspage(reflinks, outputpage, header, footer)

    def generateresultspage(self, redirlist, pagename, header, footer):
        """
        Generates results page from redirlist
        Starting with header, ending with footer
        Output page is pagename + pagenumber split at maxlines rows
        """
        # finalpage = header
        finalpage = ''
        if self.opt.section:
            finalpage += '== ' + self.opt.section + ' ==\n'
        # res = sorted(redirlist, key=redirlist.__getitem__, reverse=False)
        res = sorted(redirlist.keys())
        itemcount = 0
        totalcount = len(res)
        pagecount = 0

        if self.opt.count:
            self.savepart(finalpage, pagename, pagecount, header,
                          self.generateprefooter(pagename, totalcount, pagecount) + footer)
            return (1)

        for link in res:


            #link = redirlist[i]

            # finalpage += '\n# [[' + title + ']]'
            linenumber = pagecount * int(self.opt.maxlines) + itemcount + 1
            if self.opt.edit:
                # finalpage += '\n|-\n| %i || {{Edytuj| %s | %s }} || %i || ' % (linenumber, title, title, len(link))
                finalpage += f'\n|-\n| {linenumber} || {link} || {len(redirlist[link])} || {{Edytuj| %s | %s }} || %i || ' % (linenumber, title, title, len(link))
            else:
                # finalpage += '\n|-\n| %i || {{Edytuj| %s | %s }} || %i || ' % (linenumber, title, title, len(link))
                finalpage += f'\n|-\n| {linenumber} || {link} || {len(redirlist[link])} || [[{"]], [[".join(redirlist[link])}]]'

            if self.opt.cite and not self.opt.negative:
                # results are list
                if self.opt.nowiki:
                    finalpage += ' - <nowiki>'
                firstlink = True
                for r in link:
                    if not firstlink:
                        finalpage += '<br />'
                    finalpage += r['link']
                    firstlink = False
                if self.opt.nowiki:
                    finalpage += '</nowiki>'

            itemcount += 1

            if itemcount > int(self.opt.maxlines) - 1:
                pywikibot.output('***** saving partial results *****')
                self.savepart(finalpage, pagename, pagecount, header,
                              self.generateprefooter(pagename, totalcount, pagecount) + footer)
                finalpage = ''
                itemcount = 0
                pagecount += 1

        # save remaining results
        pywikibot.output('***** saving remaining results *****')
        self.savepart(finalpage, pagename, pagecount, header,
                      self.generateprefooter(pagename, totalcount, pagecount) + footer)

        return (pagecount)

    def generateprefooter(self, pagename, totalcount, pagecount):
        # generate text to appear before footer

        if self.opt.test:
            pywikibot.output('***** GENERATING PREFOOTER page ' + pagename + ' ' + str(pagecount) + ' *****')
        result = '\n|}'

        # if no results found to be reported
        if not totalcount:
            result += "\n\n'''Brak wyników'''\n\n"
        elif self.opt.count:
            result += "\n\n'''Liczba stron spełniających warunki: " + str(totalcount) + "'''"
        else:
            result += "\n\n"

        return (result)

    def navigation(self, pagename, pagecount):
        # generate navigation template
        if pagecount > 1:
            result = '\n\n{{User:mastiBot/Nawigacja|' + pagename + ' ' + str(
                pagecount - 1) + '|' + pagename + ' ' + str(pagecount + 1) + '}}\n\n'
        elif pagecount:
            result = '\n\n{{User:mastiBot/Nawigacja|' + pagename + '|' + pagename + ' ' + str(pagecount + 1) + '}}\n\n'
        else:
            result = '\n\n{{User:mastiBot/Nawigacja|' + pagename + '|' + pagename + ' ' + str(pagecount + 1) + '}}\n\n'
        return (result)

    def savepart(self, pagepart, pagename, pagecount, header, footer):
        # generate resulting page
        if self.opt.test:
            pywikibot.output('***** SAVING PAGE #%i' % pagecount)
            # pywikibot.output(finalpage)

        if self.opt.navi:
            finalpage = header + self.navigation(pagename, pagecount) + pagepart + footer + self.navigation(pagename,
                                                                                                            pagecount)
        else:
            finalpage = header + pagepart + footer

        if pagecount:
            numberedpage = pagename + '/' + str(pagecount + 1)
        else:
            numberedpage = pagename + '/1'

        outpage = pywikibot.Page(pywikibot.Site(), numberedpage)

        if self.opt.append:
            outpage.text += finalpage
        else:
            outpage.text = finalpage

        if self.opt.test:
            pywikibot.output(outpage.title())
            pywikibot.output(outpage.text)

        success = outpage.save(summary=self.opt.summary)
        # if not outpage.save(finalpage, outpage, self.summary):
        #   pywikibot.output('Page %s not saved.' % outpage.title(asLink=True))
        #   success = False
        return (success)

    def treat(self, page):
        """
        Returns page title if param 'text' not in page
        """

        if self.opt.wikipedia:
            resultR = re.compile(
                '(?i)(?P<result>https?://(?P<lang>[^\.]*?)\.(?P<project>wikipedia)\.org/wiki/[^\s\|<\]\}]*)')
        else:
            resultR = re.compile(
                '(?i)(?P<result>https?://(?P<lang>[^\.]*?)\.(?P<project>wikipedia|wikisource|wiktionary|wikivoyage|wikimedia)\.org/wiki/[^\s\|<\]\}]*)')
        # allowed filtypes: svg, png, jpeg, tiff, gif, xcf
        #imageR = re.compile('(?i).*\.(svg|png|jpeg|jpg|tiff|tif|gif|xcf)$')

        source = textlib.removeDisabledParts(page.text)

        # return all found results
        resultslist = []

        for r in re.finditer(resultR, source):
            if self.opt.test:
                pywikibot.output('R:%s' % r.group('result'))
            # img = imageR.search(r.group('result'))
            # if not img:
            #     resultslist.append({'link': r.group('result'), 'lang': r.group('lang'), 'project': r.group('project')})
            resultslist.append({'link': r.group('result'), 'lang': r.group('lang'), 'project': r.group('project')})

        pywikibot.output(f'RESULT: {resultslist}')
        return (resultslist)

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