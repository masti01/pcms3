#!/usr/bin/python
"""
Article to find miisng/potential doubled articles with or without dicatrical chararcters in title

Call:
    python pwb.py masti/ms-nodiactrics.py -catr:"Sportowcy" -summary:"Bot uaktualnia tabelę" -outpage:"Wikipedysta:MastiBot/Przekierowania bez diaktryków" -skippl
    python pwb.py masti/ms-nodiactrics.py -catr:"Sportowcy" -summary:"Bot uaktualnia tabelę" -outpage:"Wikipedysta:MastiBot/Przekierowania bez diaktryków/duble" -skippl -doubles

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
import unicodedata


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
        'test': False,  # switch on test functionality
        'outpage': 'User:mastiBot/test',  # default output page
        'maxlines': 1000,  # default number of entries per page
        'testprint': False,  # print testoutput
        'negative': False,  # if True negate behavior i.e. mark pages that DO NOT contain search string
        'skippl': False,  # try to assume if the title is polish based on chars used
        'doubles': False,  # find when articles with and without diactrics exist
    }

    def run(self):

        results = {}
        processed = {}

        # prepare new page with table

        header = "Ta strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|bota]]. Ostatnia aktualizacja ~~~~~. \nWszelkie uwagi proszę zgłaszać w [[Dyskusja_Wikipedysty:Masti|dyskusji operatora]]."
        # header += "\n<small>"
        header += "\n*Legenda:"
        header += "\n*:'''Hasło''' - Tytuł hasła"
        header += "\n*:'''Przekierowanie''' - Brakujące przekierowanie"
        # header += "\n</small>\n"
        header += '\n{| class="wikitable" style="font-size:85%;"\n|-\n!Lp.\n!Hasło\n!Przekierowanie'
    
        footer = '\n|}'
    
        counter = 1
        marked = 0
        skipped = 0
        for page in self.generator:
            if self.opt.test:
                pywikibot.output(
                    'Processing #%i (%i marked, %i skipped):%s' % (counter, marked, skipped, page.title(as_link=True)))
            counter += 1
            if page.title() in processed.keys():
                if self.opt.test:
                    pywikibot.output('Already done...')
                skipped += 1
                processed[page.title()] += 1
                continue
            processed[page.title()] = 1
            res = self.treat(page)
            if res:
                marked += 1
                results[page.title()] = res
    
        self.generateresultspage(results, self.opt.outpage, header, footer)
        if self.opt.test:
            pywikibot.output(processed)
            pywikibot.output('Processed #%i (%i marked, %i skipped)' % (counter, marked, skipped))

        return
    
    
    def treat(self, page):
        """
        Check if page with .title() without diactrics exist
        If no: return title without diactrics
        If yes: return None
        """
        title = self.noDisambig(page.title())
    
        if self.opt.skippl:
            if self.assumedPolish(title):
                if self.opt.test:
                    pywikibot.output('Assumed polish name:%s' % title)
                return None
    
        noDiactricsTitle = self.strip_accents(title)
        if self.opt.test:
            pywikibot.output('Diactrics stripped:%s' % noDiactricsTitle)
        if noDiactricsTitle == title:
            if self.opt.test:
                pywikibot.output('No diactrics found:%s' % title)
            return None
    
        noDPage = pywikibot.Page(pywikibot.Site(), noDiactricsTitle)
        if not self.opt.doubles and not noDPage.exists():
            return noDiactricsTitle
        elif self.opt.doubles and noDPage.exists() and not noDPage.isRedirectPage():
            return noDiactricsTitle
        else:
            if self.opt.test:
                pywikibot.output('Diactrics page exists:%s' % noDiactricsTitle)
            return None
    
    
    def noDisambig(self, text):
        if self.opt.test:
            pywikibot.output('%s-->%s' % (text, re.sub(r' \(.*?\)', '', text)))
        return re.sub(r' \(.*?\)', '', text)
    
    
    def strip_accents(self, text):
        """
        Strip accents from input String.
    
        :param text: The input string.
        :type text: String.
    
        :returns: The processed String.
        :rtype: String.
        """
        # try:
        #    text = unicode(text, 'utf-8')
        # except NameError: # unicode is a default on python 3 
        #    pass
    
        # text = unicodedata.normalize('NFD', text)
        # text = text.encode('ascii', 'ignore')
        # text = text.decode("utf-8")
        trans = [
            ('Đ', 'D'),
            ('đ', 'd'),
            ('ð', 'd'),
            ('Ł', 'L'),
            ('ł', 'l'),
            ('ß', 'ss'),
            ('ñ', 'n'),
            ('Ä', 'Ae'),
            ('ä', 'ae'),
            ('Ö', 'Oe'),
            ('ö', 'oe'),
            ('Ü', 'Ue'),
            ('ü', 'ue'),
            ('Å', 'Aa'),
            ('å', 'aa'),
            ('Ø', 'Oe'),
            ('ø', 'oe'),
            ('Æ', 'Ae'),
            ('æ', 'ae'),
            ('Œ', 'Oe'),
            ('œ', 'oe'),
        ]
    
        text = self.multisub(trans, text)
        if self.opt.test:
            pywikibot.output(text)
            pywikibot.input('Waiting...')
        return str(''.join((c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')))
    
    
    def assumedPolish(self, text):
        """
        Try to verify if the text is in Polish
        """
        polishChars = ['ą', 'ć', 'ę', 'ń', 'ó', 'ś', 'ź', 'ż', 'Ą', 'Ć', 'Ę', 'Ń', 'Ó', 'Ś', 'Ź', 'Ż']
        for c in polishChars:
            if c in text:
                return True
        return False
    
    
    def generateresultspage(self, rlist, pagename, header, footer):
        """
        Generates results page from rlist
        Starting with header, ending with footer
        Output page is pagename
        """
        finalpage = header
        # res = sorted(redirlist, key=redirlist.__getitem__, reverse=True)
        res = rlist
        linkcount = 1
        for i in res:
            finalpage += '\n|-\n| ' + str(linkcount) + ' || [[' + i + ']] || [[' + rlist[i] + ']]'
            linkcount += 1
        finalpage += footer
    
        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        outpage.text = finalpage
        outpage.save(summary=self.opt.summary)
    
        if self.opt.test:
            pywikibot.output(rlist)
        return res
    
    
    def multisub(self, subs, subject):
        "Simultaneously perform all substitutions on the subject string."
        pattern = '|'.join('(%s)' % re.escape(p) for p, s in subs)
        substs = [s for p, s in subs]
        replace = lambda m: substs[m.lastindex - 1]
        return re.sub(pattern, replace, subject)


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
