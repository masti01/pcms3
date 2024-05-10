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
from __future__ import annotations

import re

import pywikibot
from pywikibot import pagegenerators
from pywikibot.bot import (
    AutomaticTWSummaryBot,
    ConfigParserBot,
    ExistingPageBot,
    SingleSiteBot,
)
from pywikibot.textlib import extract_templates_and_params, extract_templates_and_params_regex_simple, glue_template_and_params, replaceExcept


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
    }

    def glue_inline(self, template_and_params) -> str:
        """Return wiki text of template glued from params.

        You can use items from extract_templates_and_params here to get
        an equivalent template wiki text (it may happen that the order
        of the params changes).
        """
        template, params = template_and_params
        text = ''
        pywikibot.output(f'glueT:{template}, glueP:{params}')
        for items in params.items():
            text += '| {}={} '.format(*items)

        return f'{{{{{template} | {text}}}}}' if len(text) > 0 else f'{{{{{template}}}}}'

    def glue(self, template_and_params, inline=True, justify=False) -> str:
        """Return wiki text of template glued from params.

        You can use items from extract_templates_and_params here to get
        an equivalent template wiki text (it may happen that the order
        of the params changes).
        """
        template, params = template_and_params
        text = ''
        pywikibot.output(f'glueT:{template}, glueP:{params}')
        justlen = len(max(params, key=len)) if len(params) else 0
        for items in params.items():
            if inline:
                text += '| {}={} '.format(*items)
            else:
                if justify:
                    k,v = items
                    text += '| {} = {}\n'.format(k.ljust(justlen,' '), v)
                else:
                    text += '| {}={}\n'.format(*items)

        if inline:
            return f'{{{{{template} {text}}}}}' if len(text) > 0 else f'{{{{{template}}}}}'
        else:
            return f'{{{{{template}\n{text}}}}}' if len(text) > 0 else f'{{{{{template}}}}}'

    def treat_page(self) -> None:
        """Load the given page, do some changes, and save it."""
        # tmplR = re.compile(r'{{[^{}]*({{[^{}]*({{[^{}]*}}[^{}]*)*}}[^{}]*)*}}')
        # tmplR = re.compile(r'\{\{[^\{\}]*(?:(\{\{[^\{\}]*(?:(\{\{[^\{\}]*(?:(\{\{[^\{\}]*(?:(\{\{[^\{\}]*(?:(\{\{[^\{\}]*(?:(\{\{[^\{\}]*(?:(\{\{[^\{\}]*(?:(\{\{[^\{\}]*(?:(\{\{[^\{\}]*(?:(\{\{[^\{\}]*?\}\})+?[^\{\}]*)*?\}\})+?[^\{\}]*)*?\}\})+?[^\{\}]*)*?\}\})+?[^\{\}]*)*?\}\})+?[^\{\}]*)*?\}\})+?[^\{\}]*)*?\}\})+?[^\{\}]*)*?\}\})+?[^\{\}]*)*?\}\})+?[^\{\}]*)*?\}\})+?[^\{\}]*)*?\}\}')
        tmplR = re.compile(r'{{[^{}]*(?:({{[^{}]*(?:({{[^{}]*(?:({{[^{}]*(?:({{[^{}]*(?:({{[^{}]*(?:({{[^{}]*(?:({{[^{}]*(?:({{[^{}]*(?:({{[^{}]*(?:({{[^{}]*?}})+?[^{}]*)*?}})+?[^{}]*)*?}})+?[^{}]*)*?}})+?[^{}]*)*?}})+?[^{}]*)*?}})+?[^{}]*)*?}})+?[^{}]*)*?}})+?[^{}]*)*?}})+?[^{}]*)*?}})+?[^{}]*)*?}}')
        text = self.current_page.text

        templatelist = extract_templates_and_params(text, remove_disabled_parts=True, strip=True)
        pywikibot.output(templatelist)
        for t in re.finditer(tmplR, text):
            # pywikibot.output(f'TMPL:{t.group(0)}')
            tmpltxt = t.group(0)
            tmpl = extract_templates_and_params(t.group(0), remove_disabled_parts=True, strip=True)
            # pywikibot.output(f'EXTRACT:{tmpl[0]}')
            title, params = tmpl[0]
            # pywikibot.output(f'TITLE:{title}, PARAMS COUNT:{len(params)}')
            # regentmpl = self.glue_inline(tmpl[0])
            # pywikibot.output(f'REGEN:\n{self.glue(tmpl[0])}')
            # pywikibot.output(f'REGEN2:\n{self.glue(tmpl[0], inline=False)}')
            # pywikibot.output(f'REGENINLINE:\n{self.glue(tmpl[0], inline=False, justify=True)}')
            # self.current_page.text = replaceExcept(
            #     self.current_page.text,
            #     t.group(0),
            #     self.glue(tmpl[0], inline=False),
            #     [],
            #     caseInsensitive=False,
            #     count = 1
            # )
            #self.current_page.text = re.sub(tmpltxt, self.glue(tmpl[0], inline=False), self.current_page.text)
            pywikibot.output(f'pattern:**************\n{tmpltxt}')
            pywikibot.output(f'repl:**************\n{self.glue(tmpl[0])}')
            pywikibot.output(f'page:**************\n{self.current_page.text}')
re.sub
        # self.current_page.save()
        # pywikibot.output(self.current_page.text)


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
