#!/usr/bin/python
"""
Call:
        python pwb.py masti/ms-Andrzei111.py -page:"Wikipedysta:Andrzei111" -outpage:"Wikipedysta:Andrzei111/lista artykułów" -maxlines:10000 -ns:0 -summary:"Bot uaktualnia tabelę"

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

    update_options = {
        'replace': False,  # delete old text and write the new text
        'summary': None,  # your own bot summary
        'text': 'Test',  # add this text from option. 'Test' is default
        'top': False,  # append text on top of the page
        'outpage': 'Wikipedysta:mastiBot/test',  # default output page
        'maxlines': 1000,  # default number of entries per page
        'test': False,  # test options
    }

    def extractsection(self, page, section, level):
        # extract section of page returning it's content
        sectionR = re.compile(
            r'(?s)={' + str(level) + '}\s*?' + section + '\s*?={' + str(level) + '}(?P<text>.*?)\n={' + str(
                level) + '} ')
        if self.opt.test:
            pywikibot.output(
                '(?s)={' + str(level) + '}\s*?' + section + '\s*?={' + str(level) + '}(?P<text>.*?)\n={' + str(
                    level) + '} ')
        return sectionR.search(page.text).group('text')

    def genpages(self, text):
        # generate pages based on wikilinks in text
        titleR = re.compile(r'\[\[(?P<title>[^\|\]]*?)[\|\]]')
        for t in titleR.finditer(text):
            page = pywikibot.Page(pywikibot.Site(), t.group('title'))
            yield page

    def run(self):

        header = "Ta strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|MastiBota]]. Ostatnia aktualizacja ~~~~~. \n"
        header += "Wszelkie uwagi proszę zgłaszać w [[Dyskusja_Wikipedysty:Masti|dyskusji operatora]].\n\n"
        header += '\n{| class="wikitable sortable" style="font-size:85%;"'
        header += '\n|-'
        header += '\n!Nr'
        header += '\n!Artykuł'
        header += '\n!Data utworzenia'
        header += '\n!Autor'
        header += '\n!Data modyfikacji'
        header += '\n!Autor modyfikacji'
        header += '\n!Rozmiar'
        header += '\n!Linkujące'

        reflinks = []  # initiate list
        gencount = 0
        for tpage in self.generator:
            gencount += 1
            if self.opt.test:
                pywikibot.output('Treating #%i: %s' % (gencount, tpage.title()))

            text = self.extractsection(tpage, 'Artykuły zapoczątkowane przeze mnie', 2)
            # if self.opt.test:
            #    pywikibot.output('[%s]L:%s T:%s' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tpage.title(),text ))

            count = 0
            for p in self.genpages(text):
                count += 1
                if self.opt.test:
                    pywikibot.output(
                        '[%s][%i]L:%s' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), count, p.title()))
                refs = self.treat(p)  # get (name, id, creator, lastedit)
                if self.opt.test:
                    pywikibot.output(refs)
                reflinks.append(refs)

        footer = '\n|}'
        # footer += '\n\nPrzetworzono ' + str(counter) + ' stron'

        outputpage = self.opt.outpage

        return self.generateresultspage(reflinks, outputpage, header, footer)

    def generateresultspage(self, redirlist, pagename, header, footer):
        """
        Generates results page from redirlist
        Starting with header, ending with footer
        Output page is pagename
        """
        finalpage = header
        # res = sorted(redirlist, key=redirlist.__getitem__, reverse=False)
        res = sorted(redirlist)
        itemcount = 0
        if self.opt.test:
            pywikibot.output('GENERATING RESULTS')
        for i in res:

            if self.opt.test:
                pywikibot.output(i)
            title, creationdate, creator, lastedit, lasteditor, refscount, size = i

            itemcount += 1

            finalpage += '\n|-\n| %i || [[%s]] || %s || [[Wikipedysta:%s|%s]] || %s || [[Wikipedysta:%s|%s]] || %i || %s' % \
                         (itemcount, title, creationdate, creator, creator, lastedit, lasteditor, lasteditor, size,
                          self.linknumber(title, refscount))

        finalpage += footer

        if self.opt.test:
            pywikibot.output(finalpage)
        success = True
        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        outpage.text = finalpage

        if self.opt.test:
            pywikibot.output(outpage.title())

        outpage.save(summary=self.opt.summary)
        # if not outpage.save(finalpage, outpage, self.summary):
        #   pywikibot.output('Page %s not saved.' % outpage.title(as_link=True))
        #   success = False
        return success

    def treat(self, tpage):
        """
        Creates a tuple (title, creationdate, creator, lastedit, refscount, size)
        """

        sTitle = self.shortTitle(tpage.title())
        if self.opt.test:
            pywikibot.output('sTitle:%s' % sTitle)

        # check for page creator
        # creator, timestamp = tpage.getCreator()
        creator = tpage.oldest_revision.user
        timestamp = tpage.oldest_revision.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        # test
        if self.opt.test:
            pywikibot.output('Creator:%s<<Timestamp %s' % (creator, timestamp))

        # check for last edit
        lastedit = tpage.latest_revision.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        lastEditor = tpage.latest_revision.user
        # get numer of linking pages
        refsCount = self.linking(tpage)
        # get articlke size
        size = len(tpage.text)

        if self.opt.test:
            pywikibot.output('lastedit:%s' % lastedit)
            pywikibot.output('creationDate:%s' % timestamp)
            pywikibot.output('refsCount:%s' % refsCount)
            pywikibot.output('lastEditor:%s' % lastEditor)
            pywikibot.output('size:%s' % size)

        return tpage.title(), timestamp, creator, lastedit, lastEditor, refsCount, size

    def shortTitle(self, t):
        """ return text without part in parentheses"""
        if '(' in t:
            shR = re.compile(r'(?P<short>.*?) \(')
            match = shR.search(t)
            return match.group("short").strip()
        else:
            return t

    def linking(self, page):
        """ get number of references """
        '''
        count = 0
        for i in page.getReferences(namespaces=0):
            count += 1

        if self.opt.test:
            pywikibot.output('RefsCount:%s' % count)
        return count
        '''
        return len(list(page.getReferences(namespaces=0)))

    def linknumber(self, t, i):
        if self.opt.test:
            pywikibot.output('[[Specjalna:Linkujące/' + t + '|' + str(i) + ']]')
        return '[[Specjalna:Linkujące/' + t + '|' + str(i) + ']]'

    def templateArg(self, param):
        """
        return name,value for each template param

        input text in form "name = value"
        @return: a tuple for each param of a template
            named: named (True) or int
            name: name of param or None if numbered
            value: value of param
        @rtype: tuple
        """
        paramR = re.compile(r'(?P<name>.*)=(?P<value>.*)')
        if '=' in param:
            match = paramR.search(param)
            named = True
            name = match.group("name").strip()
            value = match.group("value").strip()
        else:
            named = False
            name = None
            value = param
        # test
        if self.opt.test:
            pywikibot.output('named:%s:name:%s:value:%s' % (named, name, value))
        return named, name, value


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
