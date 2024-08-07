#!/usr/bin/python
"""
Lista artykułów z uzupełnionym parametrem "Nagrody" bez sekcji "Nagrody", "Nominacje" lub "Nagrody i nominacje"
w artykule. Dotyczycy artykułów w których występuje infobox Szablon:Film infobox.
Call:
    python3 pwb.py masti/ms-nagrody.py -transcludes:"Film infobox" -ns:0 -outpage:"Wikipedysta:mastiBot/Film infobox" \
        -summary:"Bot uaktualnia stronę"

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
        'outpage': 'User:mastiBot/test',  # default output page
        'maxlines': 1000,  # default number of entries per page
        'testprint': False,  # print testoutput
        'negative': False,  # if True negate behavior i.e. mark pages that DO NOT contain search string
        'test': False,  # switch on test functionality
    }

    def run(self):
        # prepare new page with table
        header = "Ta strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|bota]]. Ostatnia aktualizacja ~~~~~."
        header += "\nWszelkie uwagi proszę zgłaszać w [[Dyskusja_Wikipedysty:Masti|dyskusji operatora]]."
        # header += "\n<small>"
        header += "\n*Legenda:"
        header += "\n*:'''Hasło''' - Tytuł hasła"
        header += "\n*:'''Nagrody''' - zawartość pola nagrody"
        # header += "\n</small>\n"
        header += '\n{| class="wikitable" style="font-size:85%;"\n|-\n!Lp.\n!Hasło\n!Nagrody'
    
        results = {}
    
        counter = 0
        marked = 0
        for page in self.generator:
            counter += 1
            # finalpage = finalpage + self.treat(page)
            if self.opt.test:
                pywikibot.output(
                    'Processing page #{:d} ({:d} marked): {}'.format(counter, marked, page.title(as_link=True)))
            result = self.treat(page)
            if result:
                results[page.title(with_ns=False)] = result
                marked += 1
                if self.opt.test:
                    pywikibot.output('Added line #{:d}: {}'.format(marked, page.title(as_link=True)))
    
        footer = '\n|}\n\n'
        footer += 'Przetworzono stron:' + str(counter)
    
        if self.opt.test:
            pywikibot.output(results)
        self.generateresultspage(results, self.opt.outpage, header, footer)
        return
    
    def treat(self, page):
        """
        Loads the given page, looks for sections:
            "Nagrody", "Nominacje" lub "Nagrody i nominacje"
        look for Film infobox with nonempty param: Nagrody
        returns nagrody content
        """

        text = page.text
        # if self.opt.test:
        #    pywikibot.output(text)
        if not text or page.isDisambig():
            return None
    
        awardR = re.compile(r'=+\s*?(nagrody|nominacje|nagrody i nominacje)\s*?=+', re.I)
        award = awardR.search(text)
        if award:
            if self.opt.test:
                pywikibot.output('wynik:{}'.format(award.group(0)))
            return None
        else:
            if self.opt.test:
                pywikibot.output('wynik: BRAK')
    
        # look for film infobox
        for t in page.templatesWithParams():
            tt, arglist = t
            if self.opt.test:
                pywikibot.output('Template:%s' % tt.title())
            if 'Szablon:Film infobox' in tt.title():
                for a in arglist:
                    if self.opt.test:
                        pywikibot.output('Arg:%s' % a)
                    named, name, value = self.templateArg(a)
                    if not named:
                        continue
                    if self.opt.test:
                        pywikibot.output('name:{}; value:{}'.format(name, value))
                    if 'nagrody' in name:
                        if len(value) > 0:
                            result = value
                            return result
                        else:
                            return None
    
        # return None as no filled field found
        return None

    def generateresultspage(self, redirlist, pagename, header, footer):
        """
        Generates results page from redirlist
        Starting with header, ending with footer
        Output page is pagename
        """
        finalpage = header
        lineN = 1
        for i in list(redirlist):
            finalpage += '\n|-\n| ' + str(lineN) + ' || [[' + i + ']] || ' + redirlist[i]
            lineN += 1
    
        finalpage += footer
    
        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        outpage.text = finalpage
        outpage.save(summary=self.opt.summary)
    
        if self.opt.test:
            pywikibot.output(finalpage)
        return redirlist
    
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
            pywikibot.output('name:%s:value:%s' % (name, value))
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
