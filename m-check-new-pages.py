#!/usr/bin/python
"""
call:
    python3 pwb.py masti/m-check-new-pages.py -ns:0 -newpages -pt:0 -always

This is a bot to check new articles:
* if no categories: add {{Dopracowac|kategoria=YYYY-MM}}
* if no wikilinks: add {{Dopracować|linki=YYYY-MM}}
# * if no refs: add {{Dopracować|przypisy=YYYY-MM}}

{{Dopracować}} has to be once per page: combine with already existing

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
from datetime import datetime
import re
from pywikibot import textlib

# This is required for the text that is shown when you run this script
# with the parameter -help.
docuReplacements = {'&params;': pagegenerators.parameterHelp}  # noqa: N816

# list of category adding templates
tmplcat = {
    'aktualne wydarzenie sportowe',
    'animanga infobox/anime',
    'animanga infobox/druk',
    'animanga infobox/film',
    'animanga infobox/ova',
    'klasyfikacja atc',
    'euronext',
    'gpw',
    'london stock exchange',
    'nyse',
    'six swiss exchange',
    'tyo',
}

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
        'test': False,  # switch on test functionality
    }

    def treat_page(self):
        """Load the given page, do some changes, and save it."""
        refR = re.compile(r'(?P<all><ref.*?</ref>)')
        # clenaupR = re.compile(r'(?i){{dopracować.*?}}')
        text = self.current_page.text
        links = {'links': 0,
                 'cat': 0,
                 'template': 0,
                 'infobox': 0,
                 'refs': 0,
                 'dopracować': False
                 }
        # cleanupTmpl = False
        summary = []

        if self.current_page.isRedirectPage():
            pywikibot.output(u'Page %s is REDIRECT!' % self.current_page.title())
            return
        elif self.current_page.isDisambig():
            pywikibot.output(u'Page %s is DISAMBIG!' % self.current_page.title())
            return
        else:
            if self.opt.test:
                pywikibot.output(u'Title:%s' % self.current_page.title())
                pywikibot.output(u'Depth:%s' % self.current_page.depth)
            for l in self.current_page.linkedPages(namespaces=0):
                if self.opt.test:
                    pywikibot.output(u'Links to:[[%s]]' % l.title())
                links['links'] += 1
                # pywikibot.output(u'Links:%s' % len(list(self.current_page.linkedPages(namespaces=0))))
            for t, p in textlib.extract_templates_and_params(text, remove_disabled_parts=True):
                if self.opt.test:
                    pywikibot.output('Template:[[%s]]' % t)
                links['template'] += 1
                if 'infobox' in t:
                    links['infobox'] += 1
                if 'dopracować' in t.lower():
                    links['dopracować'] = True
                if t.lower() in tmplcat: #  check for category adding templates
                    links['cat'] += 1
                    if self.opt.test:
                        pywikibot.output('Current cat#%i' % links['cat'])
                    # cleanupTmpl = (t, p)
                # if 'rok w' in t or 'Rok w' in t:
                #     links['cat'] += 1

            for c in textlib.getCategoryLinks(text):
                if self.opt.test:
                    pywikibot.output('Category:%s' % c)
                links['cat'] += 1
                if self.opt.test:
                    pywikibot.output('Current cat#%i' % links['cat'])
            for r in refR.finditer(text):
                if self.opt.test:
                    pywikibot.output('Ref:%s' % r.group('all'))
                links['refs'] += 1
            if self.opt.test:
                pywikibot.output('Links=%s' % links)
                # pywikibot.output('Cleanup=%s' % re.sub('\n','',textlib.glue_template_and_params(cleanupTmpl)))

        if links['dopracować']:
            if self.opt.test:
                pywikibot.output('Cleanup Tmpl FOUND')
        else:
            # add {{Dopracować}}
            t = 'Dopracować'  # template title
            p = {}  # template params
            today = datetime.now()
            datestr = today.strftime('%Y-%m')
            if self.opt.test:
                pywikibot.output('Date:%s' % datestr)
            if not (links['links'] and links['cat']):
                if not links['links']:
                    p['linki'] = datestr
                    summary.append('linki')
                if not links['cat']:
                    p['kategoria'] = datestr
                    summary.append('kategorie')
                # if not links['refs']:
                #    p['przypisy'] = datestr
                #    summary.append('przypisy')
            cleanupTmpl = (t, p)

            if not p:
                if self.opt.test:
                    pywikibot.output('Nothing to add')
                return

            if self.opt.test:
                pywikibot.output('Cleanup Tmpl TO ADD')
                pywikibot.output('summary:%s' % summary)
                pywikibot.output('params:%s' % p)
            text = re.sub('\n', '', textlib.glue_template_and_params(cleanupTmpl)) + '\n' + text

            # if summary option is None, it takes the default i18n summary from
            # i18n subdirectory with summary_key as summary key.
            self.put_current(text, summary='Sprawdzanie nowych stron, w artykule należy dopracować: %s' % ','.join(summary))


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
        bot = BasicBot(generator=gen, **options)
        bot.run()  # guess what it does
    else:
        pywikibot.bot.suggest_help(missing_generator=True)


if __name__ == '__main__':
    main()
