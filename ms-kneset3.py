#!/usr/bin/python
"""
A script by masti for creating statistics/listings pages

This bot creates a pages with links to Kneset members.

Call:
    python pwb.py masti/ms-kneset.py -transcludes:Kneset -outpage:"Wikipedysta:Andrzei111/Izrael/lista" -maxlines:10000 -ns:0 -summary:"Bot uaktualnia tabelę"

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
import re

#
# (C) Pywikibot team, 2006-2021
#
# Distributed under the terms of the MIT license.
#
import pywikibot
from pywikibot import pagegenerators
from pywikibot.backports import Tuple
from pywikibot.bot import (
    SingleSiteBot, ConfigParserBot, ExistingPageBot,
    AutomaticTWSummaryBot)

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

    @ivar summary_key: Edit summary message key. The message that should be
        used is placed on /i18n subdirectory. The file containing these
        messages should have the same name as the caller script (i.e. basic.py
        in this case). Use summary_key to set a default edit summary message.

    @type summary_key: str
    """

    summary_key = 'basic-changing'

    def __init__(self, generator, **kwargs) -> None:
        """
        Initializer.

        @param generator: the page generator that determines on which pages
            to work
        @type generator: generator
        """
        # Add your own options to the bot and set their defaults
        # -always option is predefined by BaseBot class
        self.available_options.update({
            'replace': False,  # delete old text and write the new text
            'summary': None,  # your own bot summary
            'text': 'Test',  # add this text from option. 'Test' is default
            'top': False,  # append text on top of the page
            'outpage': u'Wikipedysta:mastiBot/test',  # default output page
            'maxlines': 1000,  # default number of entries per page
            'test': False,  # test options
        })

        # call initializer of the super class
        super().__init__(site=True, **kwargs)
        # assign the generator to the bot
        self.generator = generator

    def run(self):

        header = u"Ta strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|MastiBota]]. Ostatnia aktualizacja ~~~~~. \n"
        header += u"Wszelkie uwagi proszę zgłaszać w [[Dyskusja_Wikipedysty:Masti|dyskusji operatora]].\n\n"
        header += u'\n{| class="wikitable sortable" style="font-size:85%;"'
        header += u'\n|-'
        header += u'\n!Nr'
        header += u'\n!Id'
        header += u'\n!Polityk'
        header += u'\n!Link Kneset'
        header += u'\n!Rozmiar'
        header += u'\n!Autor'
        header += u'\n!Data modyfikacji'
        header += u'\n!Autor modyfikacji'
        header += u'\n!Linkujące'

        reflinks = []  # initiate list
        licznik = 0
        for tpage in self.generator:
            licznik += 1
            if self.opt.test:
                pywikibot.output(u'Treating #%i: %s' % (licznik, tpage.title()))
            refs = self.treat(tpage)  # get (name, id, creator, lastedit)
            if self.opt.test:
                pywikibot.output(refs)
            reflinks.append(refs)

        footer = u'\n|}'
        footer += u'\n\nPrzetworzono ' + str(licznik) + u' stron'

        outputpage = self.opt.outpage

        result = self.generateresultspage(reflinks, outputpage, header, footer)

    def generateresultspage(self, redirlist, pagename, header, footer):
        """
        Generates results page from redirlist
        Starting with header, ending with footer
        Output page is pagename
        """
        maxlines = int(self.opt.maxlines)
        finalpage = header
        # res = sorted(redirlist, key=redirlist.__getitem__, reverse=False)
        res = sorted(redirlist)
        itemcount = 0
        if self.opt.test:
            pywikibot.output(u'GENERATING RESULTS')
        for i in res:

            if self.opt.test:
                pywikibot.output(i)
            ident, title, name, creator, lastedit, lasteditor, refscount, size = i

            if (not name) or (name == self.shortTitle(title)):
                itemcount += 1

                if ident:
                    finalpage += u'\n|-\n| ' + str(itemcount) + u' || ' + str(ident) + u' || [[' + title + u']] || '
                    finalpage += u'[https://www.knesset.gov.il/mk/eng/mk_eng.asp?mk_individual_id_t=' + str(
                        ident) + u' '
                    if name:
                        finalpage += name
                    else:
                        finalpage += title
                    finalpage += u']'
                    # finalpage += u'{{Kneset|' + str(ident) + u'|name='
                else:
                    finalpage += u'\n|-\n| ' + str(itemcount) + u' || ' + u"'''brak'''" + u' || [[' + title + u']] || '

                finalpage += u' || ' + str(size) + u' || [[Wikipedysta:' + creator + u'|' + creator + u']] || ' + str(
                    lastedit)
                finalpage += u' || [[Wikipedysta:' + lasteditor + u'|' + lasteditor + u']] || ' + self.linknumber(title,
                                                                                                                  refscount) + u'\n'

                if itemcount > maxlines - 1:
                    pywikibot.output(u'*** Breaking output loop ***')
                    break
            else:
                if self.opt.test:
                    pywikibot.output(u'SKIPPING:%s' % title)

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
        #   pywikibot.output(u'Page %s not saved.' % outpage.title(asLink=True))
        #   success = False
        return (success)

    def treat(self, tpage):
        """
        Creates a tuple (id, title, name, creator, lastedit, refscount, size)
        """
        found = False
        rowtext = u''
        ident = None
        name = None
        size = 0
        sTitle = self.shortTitle(tpage.title())
        if self.opt.test:
            pywikibot.output(u'sTitle:%s' % sTitle)

        # check for id & name(optional)
        for t in tpage.templatesWithParams():
            (tTitle, paramList) = t
            # test
            if self.opt.test:
                pywikibot.output(u'Template:%s' % tTitle)
            if tTitle.title().startswith('Szablon:Kneset'):
                name = None
                ident = None
                for p in paramList:
                    if self.opt.test:
                        pywikibot.output(u'param:%s' % p)
                    pnamed, pname, pvalue = self.templateArg(p)
                    if pnamed and pname.startswith('name'):
                        name = pvalue
                    else:
                        try:
                            ident = int(pvalue)
                            if self.opt.test:
                                pywikibot.output(u'ident:%s' % ident)
                        except:
                            ident = 0
                            if self.opt.test:
                                pywikibot.output(u'ERROR: ident is not integer:%s' % ident)

                if not pnamed or (pnamed and name == sTitle):
                    break

        # check for page creator
        # creator, timestamp = tpage.getCreator()
        creator = tpage.oldest_revision.user
        timestamp = tpage.oldest_revision.timestamp.strftime('%Y-%m-%d')
        # test
        if self.opt.test:
            pywikibot.output(u'Creator:%s<<Timestamp %s' % (creator, timestamp))

        # check for last edit
        lastedit = tpage.latest_revision.timestamp.strftime('%Y-%m-%d')
        lastEditor = tpage.latest_revision.user
        # get numer of linking pages
        refsCount = self.linking(tpage)
        # get articlke size
        size = len(tpage.text)

        if self.opt.test:
            pywikibot.output(u'lastedit:%s' % lastedit)
            pywikibot.output(u'ident:%s' % ident)
            pywikibot.output(u'refsCount:%s' % refsCount)
            pywikibot.output(u'lastEditor:%s' % lastEditor)
            pywikibot.output(u'size:%s' % size)

        return (ident, tpage.title(), name, creator, lastedit, lastEditor, refsCount, size)

    def shortTitle(self, t):
        """ return text without part in parentheses"""
        if u'(' in t:
            shR = re.compile(r'(?P<short>.*?) \(')
            match = shR.search(t)
            return (match.group("short").strip())
        else:
            return (t)

    def linking(self, page):
        """ get number of references """
        count = 0
        for i in page.getReferences(namespaces=0):
            count += 1

        if self.opt.test:
            pywikibot.output(u'RefsCount:%s' % count)
        return (count)

    def linknumber(self, t, i):
        if self.opt.test:
            pywikibot.output(u'[[Specjalna:Linkujące/' + t + u'|' + str(i) + u']]')
        return (u'[[Specjalna:Linkujące/' + t + u'|' + str(i) + u']]')

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
            pywikibot.output(u'named:%s:name:%s:value:%s' % (named, name, value))
        return named, name, value


def main(*args: Tuple[str, ...]) -> None:
    """
    Process command line arguments and invoke bot.

    If args is an empty list, sys.argv is used.

    @param args: command line arguments
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
    if gen:
        # pass generator and private options to the bot
        bot = BasicBot(gen, **options)
        bot.run()  # guess what it does
    else:
        pywikibot.bot.suggest_help(missing_generator=True)


if __name__ == '__main__':
    main()
