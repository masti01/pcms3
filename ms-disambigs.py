#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to list potential disambigs and disambig errors
Call;
python3 pwb.py masti/ms-disambigs.py -start:'!' -outpage:'Wikipedysta:mastiBot/Ujednoznacznienia' -progress -summary:'Bot aktulizuje tabelę ujednoznacznień' -pt:0


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
from pywikibot import pagegenerators, config2
from pywikibot.backports import Tuple
from pywikibot.bot import (
    AutomaticTWSummaryBot,
    ConfigParserBot,
    ExistingPageBot,
    SingleSiteBot,
)
import re
import datetime
import pickle


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

    def __init__(self, generator, **kwargs):
        """
        Constructor.

        @param generator: the page generator that determines on which pages
            to work
        @type generator: generator
        """
        # Add your own options to the bot and set their defaults
        # -always option is predefined by BaseBot class
        self.availableOptions.update({
            'replace': False,  # delete old text and write the new text
            'summary': None,  # your own bot summary
            'text': 'Test',  # add this text from option. 'Test' is default
            'top': False,  # append text on top of the page
            'outpage': 'User:mastiBot/test', #default output page
            'maxlines': 1000, #default number of entries per page
            'test': False, # print testoutput
            'progress': False, # report progress
            'load': False, # load data from file
            'negative': False, #if True negate behavior i.e. mark pages that DO NOT contain search string
        })

        # call constructor of the super class
        super(BasicBot, self).__init__(site=True, **kwargs)

        # assign the generator to the bot
        self.generator = generator

    def run(self):
        """TEST"""
        pywikibot.output('THIS IS A RUN METHOD')
        outputpage = self.opt.outpage
        pywikibot.output('OUTPUTPAGE:%s' % outputpage)

        result = {}
        pagecount = 0

        if self.opt.load:
            try:
                with open('masti/disambigs.dat', 'rb') as datfile:
                    result = pickle.load(datfile)
            except (IOError, EOFError):
                # no saved history exists yet, or history dump broken
                result = {}

        for p in self.generator:
            pagecount += 1
            if self.opt.test or self.opt.progress:
                pywikibot.output('[%s] Treating:[%s] %s' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),pagecount,p.title()))
            basic = self.basicTitle(p.title())

            if basic in result.keys():
                result[basic]['articles'].append(p.title())
                if p.isDisambig():
                    result[basic]['disambig'] = p.title()
            else:
                if p.isDisambig():
                    result[basic] = {'articles':[p.title()], 'disambig':p.title(), 'redir':None}
                else:
                    result[basic] = {'articles':[p.title()], 'disambig':None, 'redir':None}
        if self.opt.test:
            pywikibot.output(result)

        result = self.cleanupList(result)
        result = self.checkExistence(result)
        result = self.solveRedirs(result)
        result = self.solveDisambTargets(result)
        result = self.guessDisambig(result)

        self.save(result)

        self.generateresultspage(result, self.opt.outpage, self.header(), self.footer())

    def save(self,results):
        """Save the .dat file to disk."""
        #test output
        pywikibot.output('PICKLING at %s' % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        with open('masti/disambigs.dat', 'wb') as f:
            pickle.dump(results, f, protocol=config2.pickle_protocol)

    def cleanupList(self,reslist):
        #remove unnecessary records
        #where only 1 article and not disambig
        d = {}
        pagecount = 0
        for p in reslist.keys():
            pagecount += 1
            if self.opt.test or self.opt.progress:
                pywikibot.output('[%s] cleanupList:[%i] %s %s' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),pagecount,p,reslist[p]))
            if reslist[p]['disambig']:
                if  p == reslist[p]['disambig']:
                    if self.opt.test:
                        pywikibot.input('skipped')
                    continue
            else:
                if len(reslist[p]['articles']) == 1 and p == reslist[p]['articles'][0] :
                    if self.opt.test:
                        pywikibot.input('skipped')
                    continue
            if self.opt.test:
                pywikibot.input('P:%s D:%s' % (p,reslist[p]['disambig']))
            d[p] = reslist[p]
            if self.opt.test:
                pywikibot.input('solveRedirs: %s' % d[p])

        return(d)

    def solveRedirs(self,reslist):
        # check if arts are redirs and find targets
        pagecount = 0
        for p in reslist.keys():
            pagecount += 1
            if self.opt.test or self.opt.progress:
                pywikibot.output('[%s] solveRedirs:[%i] %s' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),pagecount,p))
            page = pywikibot.Page(pywikibot.Site(),p)
            if page.isRedirectPage():
                reslist[p]['redir'] = page.getRedirectTarget().title()
                if not reslist[p]['disambig']:
                    reslist[p]['disambig'] = page.getRedirectTarget().title()
        return(reslist)

    def solveDisambTargets(self,reslist):
        # if disambig defined find not listed targets
        pagecount = 0
        for p in reslist.keys():
            pagecount += 1
            if self.opt.test or self.opt.progress:
                pywikibot.output('[%s] getDisambTargets:[%i] %s' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),pagecount,p))
            if reslist[p]['disambig']:
                page = pywikibot.Page(pywikibot.Site(),reslist[p]['disambig'])
                reslist[p]['articles'] = self.getDisambTargets(page,reslist[p]['articles'])

        return(reslist)

    def getDisambTargets(self,page,reslist):
        # get a list of disamb targets and add to article list
        titleR =  re.compile(r'(?m)^\* *\[\[(?P<title>[^\|\]]*)')
      
        for p in titleR.finditer(page.text):
            if p.group('title') not in reslist:
                reslist.append(p.group('title'))
        return(reslist)

    def checkExistence(self,reslist):
        # check if main topic exists
        
        pagecount = 0
        for p in reslist.keys():
            pagecount += 1
            if self.opt.test or self.opt.progress:
                pywikibot.output('[%s] checkExistence:[%i] %s' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),pagecount,p))
            page = pywikibot.Page(pywikibot.Site(),p)
            reslist[p]['exists'] = page.exists()

        return(reslist)

    def guessDisambig(self,reslist):
        # look for possible disambigs if None
        #
        pagecount = 0
        for p in reslist.keys():
            pagecount += 1
            if self.opt.test or self.opt.progress:
                pywikibot.output('[%s] guessDisambig:[%i] %s' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),pagecount,p))
            if not reslist[p]['exists']:
                reslist[p]['disambig'] = p
            elif not reslist[p]['disambig']:
                reslist[p]['disambig'] = p + ' (ujednoznacznienie)'

        return(reslist)

    def basicTitle(self,title):
        #return title without leading parenthesis section
        btR = re.compile(r'(?m)(?P<basictitle>.*?) \(.*?\)(\/.*)?$')
        bt = btR.match(title)
        if bt:
            return(bt.group('basictitle'))
        else:
            return(title)

    def header(self):
        header = u"Ta strona jest okresowo uaktualniana przez [[Wikipedysta:MastiBot|MastiBota]]. Ostatnia aktualizacja '''~~~~~'''."
        header += u"\n\nWszelkie uwagi proszę zgłaszać w [[Dyskusja wikipedysty:Masti|dyskusji operatora]]."
        header += u"\n:<small>ZLista potencjalnie brakujących ujednoznacznień</small>"
        header +='\n\n{| class="wikitable sortable" style="font-size:85%;"'
        header +='\n|-'
        header +='\n!Nr'
        header +='\n!Artykuł'
        header +='\n!Cel'
        header +='\n!Ujednoznacznienie'
        header +='\n!Lista'
        return(header)

    def footer(self):
        footer = '\n|}'
        return(footer)

    def generateresultspage(self, redirlist, pagename, header, footer):
        """
        Generates results page from redirlist
        Starting with header, ending with footer
        Output page is pagename
        """
        maxlines = int(self.opt.maxlines)
        finalpage = header
        #res = sorted(redirlist, key=redirlist.__getitem__, reverse=False)
        res = sorted(redirlist.keys())
        #res = redirlist
        itemcount = 1
        if self.opt.test:
            pywikibot.output('GENERATING RESULTS')
        for i in res:
            disamb = '[[%s]]' % redirlist[i]['disambig'] if redirlist[i]['disambig'] else ''
            redir = '[[%s]]' % redirlist[i]['redir'] if redirlist[i]['redir'] else ''

            if len(redirlist[i]['articles']) > 1:
                line = '\n|-\n| %i || [[%s]] || %s || %s || [[%s]]' % ( itemcount, i, redir, disamb, ']]<br />[['.join(redirlist[i]['articles']) )
            else:
                if redirlist[i]['articles'][0] == i:
                    continue
                else:
                    line = '\n|-\n| %i || [[%s]] || %s || %s || [[%s]]' % ( itemcount, i, redir, disamb, redirlist[i]['articles'][0] )
            itemcount += 1
            finalpage += line

        finalpage += footer 
        
        if self.opt.test:
            pywikibot.output(finalpage)
        success = True
        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        outpage.text = finalpage

        if self.opt.test:
            pywikibot.output(outpage.title())
        
        outpage.save(summary=self.opt.summary)
        #if not outpage.save(finalpage, outpage, self.summary):
        #   pywikibot.output('Page %s not saved.' % outpage.title(asLink=True))
        #   success = False
        return(success)



def main(*args: Tuple[str, ...]) -> None:
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
