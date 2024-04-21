#!/usr/bin/python
"""
A script by masti for creating statistics/listings pages

Use global -simulate option for test purposes. No changes to live wiki
will be done.

This bot creates a pages with links to tennis players.

Call:
        python3 pwb.py masti/ms-kneset.py -transcludes:Kneset -outpage:"Wikipedysta:Andrzei111/Izrael/lista" -maxlines:10000 -ns:0 -summary:"Bot uaktualnia tabelę"

The following parameters are supported:

&params;

-always           If used, the bot won't ask if it should file the message
                  onto user talk page.   

-outpage          Results page; otherwise "Wikipedysta:mastiBot/test" is used

-maxlines         Max number of entries before new subpage is created; default 1000

-text:            Use this text to be added; otherwise 'Test' is used

-replace:         Dont add text but replace it

-top              Place additional text on top of the page

-summary:         Set the action summary message for the edit.
"""
#
# (C) Pywikibot team, 2006-2021
#
# Distributed under the terms of the MIT license.
#
import pywikibot

from pywikibot import pagegenerators

from pywikibot.bot import (
    SingleSiteBot, ConfigParserBot, ExistingPageBot,
    AutomaticTWSummaryBot)

import re

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

    @ivar summary_key: Edit summary message key. The message that should be
        used is placed on /i18n subdirectory. The file containing these
        messages should have the same name as the caller script (i.e. basic.py
        in this case). Use summary_key to set a default edit summary message.

    @type summary_key: str
    """
    use_redirects = False  # treats non-redirects only
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
            'outpage': 'User:mastiBot/test',  # default output page
            'maxlines': 1000,  # default number of entries per page
            'testprint': False,  # print testoutput
            'negative': False,  # if True negate behavior i.e. mark pages that DO NOT contain search string
            'test': False,  # test options
            'progress': False  # test option showing bot progress
        })

        # call initializer of the super class
        super().__init__(site=True, **kwargs)
        # assign the generator to the bot
        self.generator = generator

    def run(self):

        header = "Ta strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|MastiBota]]. Ostatnia aktualizacja ~~~~~. \n"
        header += "Wszelkie uwagi proszę zgłaszać w [[Dyskusja_Wikipedysty:Masti|dyskusji operatora]].\n\n"
        header += '\n{| class="wikitable sortable" style="font-size:85%;"'
        header += '\n|-'
        header += '\n!Nr'
        header += '\n!Id'
        header += '\n!Polityk'
        header += '\n!Link Kneset'
        header += '\n!Rozmiar'
        header += '\n!Autor'
        header += '\n!Data modyfikacji'
        header += '\n!Autor modyfikacji'
        header += '\n!Linkujące'

        reflinks = []  # initiate list
        licznik = 0
        for tpage in self.generator:
            licznik += 1
            if self.opt.test:
                pywikibot.output('Treating #%i: %s' % (licznik, tpage.title()))
            refs = self.treat(tpage)  # get (name, id, creator, lastedit)
            if self.opt.test:
                pywikibot.output(refs)
            reflinks.append(refs)

        footer = '\n|}'
        footer += f'\n\nPrzetworzono {str(licznik)} stron.'

        outputpage = self.opt.outpage

        return self.generateresultspage(reflinks, outputpage, header, footer)

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
            pywikibot.output('GENERATING RESULTS')
        for i in res:

            if self.opt.test:
                pywikibot.output(i)
            ident, title, name, creator, lastedit, lasteditor, refscount, size = i

            if (not name) or (name == self.short_title(title)):
                itemcount += 1

                if ident:
                    finalpage += f'\n|-\n| {str(itemcount)} || {str(ident)} || [[{title}]] || '
                    finalpage += f'[https://www.knesset.gov.il/mk/eng/mk_eng.asp?mk_individual_id_t={str(ident)} '
                    if name:
                        finalpage += name
                    else:
                        finalpage += title
                    finalpage += ']'
                    # finalpage += '{{Kneset|' + str(ident) + '|name='
                else:
                    finalpage += f"\n|-\n| {str(itemcount)} || '''brak''' || [[{title}]] || "

                finalpage += f' || {str(size)} || [[Wikipedysta:{creator}|{creator}]] || {str(lastedit)}'
                finalpage += f' || [[Wikipedysta:{lasteditor}|{lasteditor}]] || {self.linknumber(title, refscount)}\n'

                if itemcount > maxlines - 1:
                    pywikibot.output('*** Breaking output loop ***')
                    break
            else:
                if self.opt.test:
                    pywikibot.output('SKIPPING:%s' % title)

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

    def treat(self, tpage):
        """
        Creates a tuple (id, title, name, creator, lastedit, refscount, size)
        """
        ident = None
        name = None
        sTitle = self.short_title(tpage.title())
        if self.opt.test:
            pywikibot.output(f'sTitle:{sTitle}')

        # check for id & name(optional)
        for t in tpage.templatesWithParams():
            (tTitle, paramList) = t
            # test
            if self.opt.test:
                pywikibot.output(f'Template:{tTitle}')
            if tTitle.title().startswith('Szablon:Kneset'):
                name = None
                ident = None
                for p in paramList:
                    if self.opt.test:
                        pywikibot.output('param:%s' % p)
                    pnamed, pname, pvalue = self.template_arg(p)
                    if pnamed and pname.startswith('name'):
                        name = pvalue
                    else:
                        try:
                            ident = int(pvalue)
                            if self.opt.test:
                                pywikibot.output(f'ident:{ident}')
                        except:
                            ident = 0
                            if self.opt.test:
                                pywikibot.output(f'ERROR: ident is not integer:{ident})

                if not pnamed or (pnamed and name == sTitle):
                    break

        # check for page creator
        # creator, timestamp = tpage.getCreator()
        creator = tpage.oldest_revision.user
        timestamp = tpage.oldest_revision.timestamp.strftime('%Y-%m-%d')
        # test
        if self.opt.test:
            pywikibot.output(f'Creator:{creator}<<Timestamp {timestamp}')

        # check for last edit
        lastedit = tpage.latest_revision.timestamp.strftime('%Y-%m-%d')
        lastEditor = tpage.latest_revision.user
        # get numer of linking pages
        refsCount = self.linking_count(tpage)
        # get article size
        size = len(tpage.text)

        if self.opt.test:
            pywikibot.output(f'lastedit:{lastedit}')
            pywikibot.output(f'ident:{ident}')
            pywikibot.output(f'refsCount:{refsCount}')
            pywikibot.output(f'lastEditor:{lastEditor}')
            pywikibot.output(f'size:{size}')

        return ident, tpage.title(), name, creator, lastedit, lastEditor, refsCount, size

    def short_title(self, t):
        """ return text without part in parentheses"""
        if '(' in t:
            shR = re.compile(r'(?P<short>.*?) \(')
            match = shR.search(t)
            return match.group("short").strip()
        else:
            return t

    def linking_count(self, page):
        """ get number of references """
        if self.opt.test:
            pywikibot.output(f'RefsCount:{len(list(page.getReferences(namespaces=0)))})
        return len(list(page.getReferences(namespaces=0)))


    def linknumber(self, t, i):
        if self.opt.test:
            pywikibot.output(f'[[Specjalna:Linkujące/{t}|{str(i)}]]')
        return f'[[Specjalna:Linkujące//{t}|{str(i)}]]'

    def template_arg(self, param):
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
            pywikibot.output(f'named:{named}:name:{name}:value:{value}')
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
        arg, _, value = arg.partition(':')
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

        # check if further help is needed
        if not pywikibot.bot.suggest_help(missing_generator=not gen):
            # pass generator and private options to the bot
            bot = BasicBot(generator=gen, **options)
            bot.run()  # guess what it does

    if __name__ == '__main__':
        main()
