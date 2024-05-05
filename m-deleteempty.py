#!/usr/bin/python
"""
Usage:
python3 pwb.py masti/m-deleteempty.py -start:'Dyskusja:!' -summary:'Pusta strona dyskusji' -pt:0 -always

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
        'summary': "Bot usuwa pustą stronę dyskusji",  # your own bot summary
        'text': 'Test',  # add this text from option. 'Test' is default
        'top': False,  # append text on top of the page
        'test': False,  # print test messages
    }

    def backoff_hdlr(details):
        print("Backing off {wait:0.1f} seconds after {tries} tries "
              "calling function {target} with args {args} and kwargs "
              "{kwargs}".format(**details))
    @backoff.on_exception(
        backoff.expo,
        pywikibot.exceptions.ServerError,
        on_backoff=self.backoff_hdlr,
        max_tries=5
    )
    def treat_page(self) -> None:
        """Load the given page, do some changes, and save it."""

        # if len(self.current_page.text) < 4 :
        #    if self.site.user() is None:
        #       self.site.login()
        szoltysEK = '{{Wikipedysta:Szoltys-bot/EK}}' in self.current_page.text
        martwyEK = '{{ek|nieaktualna' in self.current_page.text
        if len(self.current_page.text) < 4 or szoltysEK or martwyEK:
            try:
                if szoltysEK:
                    self.current_page.delete(f'{self.opt.summary} (Szoltys-bot/EK)',
                                         not self.opt.always,
                                         self.opt.always)
                if martwyEK:
                    self.current_page.delete(f'{self.opt.summary} (nieaktualna informacja o martwym linku)',
                                             not self.opt.always,
                                             self.opt.always)
                else:
                    self.current_page.delete(self.opt.summary,
                                             not self.opt.always,
                                             self.opt.always)
            except pywikibot.exceptions.Error:
                if self.opt.test:
                    pywikibot.output('Page %s does not exist.' % self.current_page.title)


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