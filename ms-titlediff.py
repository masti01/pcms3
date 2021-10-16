#!/usr/bin/python
"""
Script find articles where first paragraph bolded header differs from article title except parenthesis part
Call:
	python3 pwb.py masti/ms-contains.py -catr:"Posłowie do Knesetu" -outpage:"Wikipedysta:Andrzei111/Izrael/bez Kneset" \
		-summary:"Bot uaktualnia tabelę" -text:"{{Kneset" -negative
	python3 pwb.py masti/ms-contains.py -weblink:'isap.sejm.gov.pl' -outpage:"Wikipedysta:mastiBot/isap" \
		-summary:"Bot uaktualnia tabelę" -text:"http://isap\.sejm\.gov\.pl/Download\?id=WD[^\s\]\|]*" -ns:0 -regex
	python3 pwb.py masti/ms-contains.py -weblink:'isap.sejm.gov.pl' -outpage:"Wikipedysta:mastiBot/isap" \
		-summary:"Bot uaktualnia tabelę" -text:"(?P<result>http://isap\.sejm\.gov\.pl/Download\?id=WD[^\s\]\|]*)" -ns:0 -regex

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

    update_options = {
        'replace': False,  # delete old text and write the new text
        'summary': None,  # your own bot summary
        'text': 'Test',  # add this text from option. 'Test' is default
        'top': False,  # append text on top of the page
        'outpage': 'Wikipedysta:mastiBot/test',  # default output page
        'maxlines': 1000,  # default number of entries per page
        'negative': False,  # if True mark pages that DO NOT contain search string
        'test': False,  # switch on test functionality
        'regex': False,  # use text as regex
        'as_link': False,  # put links as wikilinks
        'append': False,  # append results to page
        'section': None,  # section title
        'title': False,  # check in title not text
        'multi': False,  # '^' and '$' will now match begin and end of each line.
        'flags': None,  # list of regex flags
        'edit': False,  # link thru template:edytuj instead of wikilink
        'cite': False,  # cite search results
        'nowiki': False,  # put citation in <nowiki> tags
        'count': False,  # count pages only
        'navi': False,  # add navigation template
        'progress': False,  # report progress
    }

    def run(self):

        if not self.opt.append:
            # header = "Ta strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|MastiBota]]. Ostatnia aktualizacja ~~~~~. \n"
            header = "Ostatnia aktualizacja: '''~~~~~'''.\n\n"
            header += "Wszelkie uwagi proszę zgłaszać w [[User talk:masti|dyskusji operatora]].\n\n"
        else:
            header = '\n\n'

        reflinks = []  # initiate list
        pagecounter = 0
        duplicates = 0
        marked = 0
        for page in self.generator:
            pagecounter += 1
            if self.opt.test or self.opt.progress:
                pywikibot.output('[%s] Treating #%i (marked:%i, duplicates:%i): %s' % (
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pagecounter, marked, duplicates, page.title()))
            refs = self.treat(page)  # get (name)
            if refs:
                if not refs in reflinks:
                    # test
                    if self.opt.test:
                        pywikibot.output(refs)
                    reflinks.append(refs)
                    marked += 1
                else:
                    # test
                    if self.opt.test:
                        pywikibot.output('Already marked')
                        duplicates += 1


        footer = '\n\nPrzetworzono ' + str(pagecounter) + ' stron.'
    
        outputpage = self.opt.outpage
    
        result = self.generateresultspage(reflinks, outputpage, header, footer)


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
        res = sorted(redirlist)
        itemcount = 0
        totalcount = len(res)
        pagecount = 0

        if self.opt.count:
            self.savepart(finalpage, pagename, pagecount, header,
                          self.generateprefooter(pagename, totalcount, pagecount) + footer)
            return (1)

        for i in res:
            if self.opt.cite or (self.opt.regex and not self.opt.negative):
                title, link = i
            else:
                title = i
            # finalpage += '\n# [[' + title + ']]'
            linenumber = str(pagecount * int(self.opt.maxlines) + itemcount + 1) + '.'
            if self.opt.edit:
                nakedtitle = re.sub(r'\[\[|\]\]', '', title)
                finalpage += '\n:' + linenumber + ' {{Edytuj|' + nakedtitle + '|' + nakedtitle + '}}'
            else:
                finalpage += '\n:' + linenumber + ' ' + re.sub(r'\[\[', '[[:', title, count=1)
            if self.opt.nowiki:
                finalpage += ' - <nowiki>' + link + '</nowiki>'
            else:
                finalpage += " - '''" + link + "'''"
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
        result = ''

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
            numberedpage = pagename + ' ' + str(pagecount)
        else:
            numberedpage = pagename

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
        #   pywikibot.output('Page %s not saved.' % outpage.title(as_link=True))
        #   success = False
        return (success)


    def treat(self, page):
        """
        Returns page title if param 'text' not in page
        """

        source = page.text

        firstparR = re.compile(
            r"^({{[^{}]*({{[^{}]*({{[^{}]*}}[^{}]*)*}}[^{}]*)*}}[ \t]*\n*)+'''(?P<firstpar>[^'<]*?)(<ref[^']*)*'''")
        nopartitleR = re.compile(r'(?P<npt>.[^\(]*)')

        fp = firstparR.match(source)
        npt = nopartitleR.match(page.title())

        if fp and npt:
            if self.opt.test:
                pywikibot.output('fp:%s npt:%s' % (fp.group('firstpar'), npt.group('npt').strip()))
            if npt.group('npt').strip() != fp.group('firstpar'):
                if self.opt.text:
                    if not re.search(self.opt.text, source):
                        return (page.title(as_link=True), fp.group('firstpar'))
                    else:
                        if self.opt.test:
                            pywikibot.output('SKIPPING: regex matched')
                else:
                    return (page.title(as_link=True), fp.group('firstpar'))
        return (None)


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
        if option in ('summary', 'text', 'outpage', 'maxlines', 'section','flags'):
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
