#!/usr/bin/python
"""
This bot creates a pages with links to disambig pages with ref counts in main.
Wikiprojekt:Strony ujednoznaczniające z linkami/50+
Wikiprojekt:Strony ujednoznaczniające z linkami/10-49
Wikiprojekt:Strony ujednoznaczniające z linkami/5-9

Call: python3 pwb.py masti/ms-disambrefslist.py cat:"Strony ujednoznaczniające" -summary:"Bot aktualizuje stronę"

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
import backoff


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
    use_redirects = False
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
        'test': False,  # test printouts
    }

    def run(self):
        # prepare new page
        header = '{{Wikiprojekt:Strony ujednoznaczniające z linkami/Nagłówek}}\n\n'
        header += 'Poniżej znajduje się lista [[:Kategoria:Strony ujednoznaczniające|stron ujednoznaczniających]], do których wiodą linki z innych artykułów.\n\n'
        header += ':<small>Pominięto strony z szablonem {{s|Inne znaczenia}}</small>\n\n'
        header += 'Ta strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|MastiBota]]. Ostatnia aktualizacja ~~~~~. \n'
        header += 'Wszelkie uwagi proszę zgłaszać w [[Dyskusja_Wikipedysty:Masti|dyskusji operatora]].\n\n'
        footer = '\n[[Kategoria:Wikiprojekt Strony ujednoznaczniające z linkami]]'

        redir50 = {}
        redir1049 = {}
        redir59 = {}

        counter = 1
        refscounter = 0

        for page in self.generator:
            if self.opt.test:
                pywikibot.output('# %i (%i) Treating:%s' % (counter, refscounter, page.title(as_link=True)))
            @backoff.on_exception(
                backoff.expo,
                pywikibot.exceptions.ServerError,
                max_tries=5
            )
            refs = self.treat(page)

            counter += 1
            if refs:
                refscounter += 1
                if refs > 49:
                    redir50[page.title()] = refs
                elif refs > 9 and refs < 50:
                    redir1049[page.title()] = refs
                elif refs > 4 and refs < 10:
                    redir59[page.title()] = refs
        result = self.generateresultspage(redir50, 'Wikiprojekt:Strony ujednoznaczniające z linkami/50+', header, footer)
        result = self.generateresultspage(redir1049, 'Wikiprojekt:Strony ujednoznaczniające z linkami/10-49', header,
                                          footer)
        result = self.generateresultspage(redir59, 'Wikiprojekt:Strony ujednoznaczniające z linkami/5-9', header, footer)

        return


    def generateresultspage(self, redirlist, pagename, header, footer):
        """
        Generates results page from redirlist
        Starting with header, ending with footer
        Output page is pagename
        """
        finalpage = header
        res = sorted(redirlist, key=redirlist.__getitem__, reverse=True)
        linkcount = 0
        for i in res:
            count = redirlist[i]
            if count == 1:
                suffix = ''
            elif count % 10 in (2, 3, 4) and (count < 10 or count > 20):
                suffix = 'i'
            else:
                suffix = 'ów'
            # finalpage += '# [[' + i + u']] ([[Specjalna:Linkujące/' + i + '|' + str(count) + ' link' + suffix + ']])\n'
            finalpage += f'# [[{i}]] ([[Specjalna:Linkujące/{i}|{count} link{suffix}]])\n'

        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        outpage.text = finalpage
        outpage.save(summary=self.opt.summary)

        if self.opt.test:
            pywikibot.output(redirlist)
        return res


    def treat(self, page):
        # check for real disambig - exclude {{Inne znaczenia
        if '{{Inne znaczenia' in page.text:
            return None

        return len(list(page.getReferences(namespaces=0)))


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
