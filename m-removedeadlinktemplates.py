#!/usr/bin/python
"""
This is a bot to remove {{Martwy link dyskusja}} templates from discussion pages if the link reported no longer exists in the article.
Call:
   python pwb.py masti/m-removedeadlinktemplates.py -cat:"Niezweryfikowane martwe linki" -ns:1 -summary:"Nieaktualna informacja o martwym linku zewnętrznym" -pt:0

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
        'nodelete': False,  # do not delete empty pages
    }

    def run(self):
        counter = 1
        changeCounter = 0
        for page in self.generator:
            pywikibot.output(u'Processing #%i (%i changed):%s' % (counter, changeCounter, page.title(as_link=True)))
            counter += 1
            if self.treat(page):
                changeCounter += 1
        pywikibot.output(u'Statistics: Processed: %i, Removed: %i' % (counter, changeCounter))

    def treat(self, page):
        """
        Loads the given discussion page, verifies if the links in {{Martwy link dyskusja}}
        were removed from article or are a part of {{Cytuj}} template with properly filled archiwum= parameter
        Then removes the template(s) or marks page for deletion
        """

        talktext = page.text
        if not talktext:
            return
        originaltext = talktext
    
        articlepage = page.toggleTalkPage()
        articletext = articlepage.text
        if not articletext:
            return
    
        # test printout
        if self.opt.test:
            pywikibot.output(u'Page: %s' % articlepage.title(as_link=True))
            pywikibot.output(u'Talk: %s' % page.title(as_link=True))
    
        # find dead link templates
        # linkR = re.compile(r'\{\{(?P<infobox>([^\]\n\|}]+?infobox))')
        tempR = re.compile(r'(?P<template>\{\{Martwy link dyskusja[^}]*?}}\n*)')
        weblinkR = re.compile(r'link\s*?=\s*?\*?\s*?(?P<weblink>[^\s][^\n\s]*)')
        links = u''
        changed = False
        templs = tempR.finditer(talktext)
        for link in templs:
            template = link.group('template')
            if self.opt.test:
                pywikibot.output(u'>>%s<<' % template)
            # pywikibot.output(template)
            # check if the template is properly built
            try:
                weblink = re.search(weblinkR, template).group('weblink').strip()
                if weblink in articletext and not self.linkarchived(weblink, articletext):
                    if self.opt.test:
                        pywikibot.output(u'Still there >>%s<<' % weblink)
                    if not self.removelinktemplate(weblink, articletext):
                        if self.opt.test:
                            pywikibot.output(u'Should stay >>%s<<' % weblink)
                    else:
                        pywikibot.output(u'Has to go >>%s<<' % weblink)
                        talktext = re.sub(re.escape(template), u'', talktext)
                        changed = True
                else:
                    if self.opt.test:
                        pywikibot.output(u'Uuups! 404 - link not found >>%s<<' % weblink)
                    talktext = re.sub(re.escape(template), u'', talktext)
                    changed = True
            except:
                pywikibot.output(u'Unrecognized template content in %s' % page.title())
    
        if changed:
            if len(talktext) < 4:
                if self.opt.test:
                    pywikibot.output(u'Deleting {0}.'.format(page))
                if not self.opt.nodelete:
                    talktext = u'{{ek|Nieaktualna informacja o martwym linku zewnętrznym}}\n\n' + talktext
            page.text = talktext
            if self.opt.test:
                pywikibot.output(talktext)
            page.save(summary=self.opt.summary)
            return True
        return False

    def linkarchived(self, link, text):
        """
        build regex for searching for archived link
        """
        link = re.sub("\.", "\.", link)
        link = re.sub("\?", "\?", link)
        linkR = re.compile(f'web\.archive\.org/web/\d*/{link}')
        return linkR.search(text)
    def removelinktemplate(self, link, text):
        """
        check if link is within {{cytuj...}} template with filled archiwum= field or within this field
    conditions on link removal:
        link in url/tytuł field + archiwum not empty
        link in archiwum field
        """
        citetempR = re.compile(r'(?P<citetemplate>\{\{[cC]ytuj.*?\|[^}]*?\}\})')
        urlfieldR = re.compile(r'(url|tytuł)\s*?=(?P<url>[^\|\}]*)')
        archfieldR = re.compile(r'archiwum\s*?=\s*?(?P<arch>[^\|\}]*)')
        result = False
    
        cites = citetempR.finditer(text)
        for c in cites:
            citetemplate = c.group('citetemplate').strip()
            if self.opt.test:
                pywikibot.output(u'Cite:%s' % citetemplate)
            try:
                urlfield = re.search(urlfieldR, citetemplate).group('url').strip()
            except AttributeError:
                if self.opt.test:
                    pywikibot.output(u'No url or tytuł field in Cytuj')
                continue
            # pywikibot.output(u'URL:%s' % urlfield) 
            try:
                archfield = re.search(archfieldR, citetemplate).group('arch').strip()
            except AttributeError:
                if self.opt.test:
                    pywikibot.output(u'No ARCH field')
                continue
            if self.opt.test:
                pywikibot.output(u'URL2:%s' % urlfield)
                pywikibot.output(u'Arch2:%s' % archfield)
            if link in urlfield:
                if self.opt.test:
                    pywikibot.output(u'URL in URL field')
                if len(archfield) > 0:
                    if self.opt.test:
                        pywikibot.output(u'ARCHIVE field filled in')
                    result = True
            else:
                if self.opt.test:
                    pywikibot.output(u'URL not found in template')
    
        return result


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
