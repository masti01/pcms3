#!/usr/bin/python
"""
call:
    python pwb.py masti/m-check-new-pages.py -ns:0 -newpages -pt:0 -always

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
from datetime import datetime
# import re
# from pywikibot import textlib
from mwparserfromhell import wikicode, parse
from mwparserfromhell.nodes import Wikilink

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
    'kalendaria tematyczne',
}

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
    }

    @staticmethod
    def ek(parsed: wikicode.Wikicode):
        """
        check if page contains Ek template
        :param parsed:
        :return:
        """
        # templaete ek and synonims
        ekname = ("ek", "ekspresowe kasowanko", "usuń", "speedy", "delete")
        for t in parsed.filter_templates():
            if t.name.matches(ekname):
                return True

        return False

    @staticmethod
    def category(wikilink: Wikilink) -> bool:
        return wikilink.name.lower().startswith(("kategoria:", "category:"))

    def treat_page(self):
        """ parse page for checks"""
        parsed = parse(self.current_page.text)

        # refR = re.compile(r'(?P<all><ref[^>]*?>)')
        # clenaupR = re.compile(r'(?i){{dopracować.*?}}')
        # text = self.current_page.text
        tests = dict(links=0, cat=0, template=0, infobox=0, refs=0, clenaup=False)
        cleanup_tmpl = None
        summary = []

        if self.current_page.isRedirectPage():
            pywikibot.output(f'Page {self.current_page.title()} is REDIRECT!')
            return
        if self.current_page.isDisambig():
            pywikibot.output(f'Page {self.current_page.title()} is DISAMBIG!')
            return
        if self.ek(parsed):  # page contains speedy delete template
            pywikibot.output(f'Page {self.current_page.title()} is to be DELETED!')
            return

        if self.opt.test:
            pywikibot.output(u'Title:%s' % self.current_page.title())
            pywikibot.output(u'Depth:%s' % self.current_page.depth)

        # Wikilinks
        wikilinks = parsed.filter_wikilinks()
        tests['links'] = len(wikilinks)
        if self.opt.test:
            pywikibot.output(f'Links to: {wikilinks}')

        # Templates
        for t in parsed.filter_templates():
            if self.opt.test:
                pywikibot.output('Template:[[%s]]' % t)
            # if 'infobox' in t.title.lower():  # check for infobox presence
            #     tests['infobox'] += 1
            # if t.lower() in tmplcat:  # check for category adding templates
            #     tests['cat'] += 1
            # if t.title.matches('dopracować'):
            #     cleanup_tmpl = t
            #     tests['clenaup'] = True

            # infobox
            tests['infobox'] = len(parsed.filter_templates(matches=lambda tmpl: tmpl.name.lower().endswith("infobox")))
            # References
            tests['refs'] = len(parsed.filter_tags(matches=lambda tag: tag.tag.lower() == "ref"))

            # Categories
            tests['cat'] = len(parsed.filter_wikilinks(matches=lambda link: self.category(link)))
            # for c in wikilinks:
            #     if self.category(c):
            #         tests['cat'] += 1

        if self.opt.test:
            pywikibot.output(f"Tests:{tests}")

        # if tests['clenaup']:
        #     if self.opt.test:
        #         pywikibot.output(f'Cleanup Tmpl FOUND: {cleanup_tmpl}')
        # else:
        #     # add {{Dopracować}}
        #     t = 'Dopracować'  # template title
        #     p = {}  # template params
        #     today = datetime.now()
        #     datestr = today.strftime('%Y-%m')
        #     if self.opt.test:
        #         pywikibot.output('Date:%s' % datestr)
        #     if not (tests['links'] and tests['cat']):
        #         if not tests['links']:
        #             p['linki'] = datestr
        #             summary.append('linki')
        #         if not tests['cat']:
        #             p['kategoria'] = datestr
        #             summary.append('kategorie')
        #         if not tests['refs']:
        #            p['przypisy'] = datestr
        #            summary.append('przypisy')
        #     # cleanup_tmpl = (t, p)
        #
        #     if not p:
        #         if self.opt.test:
        #             pywikibot.output('Nothing to add')
        #         return
        #
        #     if self.opt.test:
        #         pywikibot.output('Cleanup Tmpl TO ADD')
        #         pywikibot.output(f'summary:{summary}')
        #         pywikibot.output(f'params:{p}')
        #     # text = re.sub('\n', '', textlib.glue_template_and_params(cleanupTmpl)) + '\n' + text
        #
        #     # if summary option is None, it takes the default i18n summary from
        #     # i18n subdirectory with summary_key as summary key.
        #     self.put_current(str(parsed), summary=f"Sprawdzanie nowych stron, w artykule należy dopracować: {','.join(summary)}")


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
