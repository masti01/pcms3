#!/usr/bin/python
"""
Creates a list of articles without interwiki
Call:
    python3 pwb.py masti/ms-nointerwiki.py -catr:"Hasła kanonu polskiej Wikipedii" -outpage:"Wikiprojekt:Polski kanon Wikipedii/bez interwiki" -summary:"Bot aktualizuje listę"

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
# (C) masti, 2021
#
# Distributed under the terms of the MIT license.
#
import pywikibot
from pywikibot import pagegenerators, exceptions
from pywikibot.bot import (
    AutomaticTWSummaryBot,
    ConfigParserBot,
    ExistingPageBot,
    SingleSiteBot,
)
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
    use_redirects = False

    update_options = {
        'replace': False,  # delete old text and write the new text
        'summary': None,  # your own bot summary
        'text': 'Test',  # add this text from option. 'Test' is default
        'top': False,  # append text on top of the page
        'outpage': u'User:mastiBot/test',  # default output page
        'maxlines': 1000,  # default number of entries per page
        'test': False,  # print testoutput
        'progress': False,  # report progress

    }

    def run(self):
        """TEST"""
        result = []

        count = 0
        marked = 0
        for p in self.generator:
            count += 1
            if self.opt.test or self.opt.progress:
                pywikibot.output(u'[%s] [%i/%i] Treating: %s' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), marked, count, p.title()))
            if self.treat(p):
                marked += 1
                if self.opt.test:
                    pywikibot.output(u'[%s] [%i/%i] Marking: %s' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), marked, count, p.title()))
                result.append(p.title(as_link=True))

        header = 'Artykuły [[Wikiprojekt:Polski kanon Wikipedii|polskiego kanonu Wikipedii]] bez żadnych odpowiedników w innych Wikipediach\n\n'
        header += 'Ta strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|bota]].\n\n'
        header += "Ostatnia aktualizacja: '''" + datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S (CEST)") + "'''.\n\n"
        header += 'Wszelkie uwagi proszę zgłaszać w [[Dyskusja_Wikipedysty:Masti|dyskusji operatora]].\n\n'
        footer = '\n\nPrzetworzono stron:' + str(count)

        self.generateresultspage(result, self.opt.outpage, header, footer)
        return

    def generateresultspage(self, redirlist, pagename, header, footer):
        """
        Generates results page from redirlist
        Starting with header, ending with footer
        Output page is pagename
        """
        finalpage = header
        res = sorted(redirlist)
        itemcount = 0
        for i in res:
            finalpage += u'\n# %s' % i

        finalpage += footer

        success = True
        #outpage = pywikibot.Page(pywikibot.Site(), pagename, ns='Wikiprojekt')
        if self.opt.test:
            pywikibot.output("Page: %s" % pagename)
        outpage = pywikibot.Page(pywikibot.Link(pagename))
        outpage.text = finalpage

        if self.opt.test:
            pywikibot.output(outpage.title())

        outpage.save(summary=self.opt.summary)
        # if not outpage.save(finalpage, outpage, self.summary):
        #   pywikibot.output(u'Page %s not saved.' % outpage.title(as_link=True))
        #   success = False
        return success

    def checkInterwiki(self, interwikis, lang):
        """Check if there are interwikis except lang"""
        for iw in interwikis:
            if iw.endswith('wiki') and iw != lang:
                return False
        return True

    def treat(self, page):
        #
        try:
            wd = pywikibot.ItemPage.fromPage(page)
            wdcontent = wd.get()
            if self.opt.test:
                pywikibot.output(wdcontent['sitelinks'].keys())
        except exceptions.NoPageError:
            pywikibot.output('WikiData page for %s do not exists' % page.title(as_link=True))
            return None
        # except NotImplementedError:
        #    pywikibot.output('Skipped: WikiData page for %s returns erros' % page.title(as_link=True))
        #    return(None)

        return self.checkInterwiki(wdcontent['sitelinks'].keys(), 'plwiki')


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
