#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
AThis bot creates a pages with article reviewer's statistics on pl.wikipedia

Call: time python pwb.py masti/ms-deletestats.py -page:'!' -outpage:'deletes.html' -days:30; cp ~/pw/compat/masti/html/deletes.html ~/public_html/deletes.html


Use global -simulate option for test purposes. No changes to live wiki
will be done.

The following parameters are supported:

&params;

-always           If used, the bot won't ask if it should file the message
                  onto user talk page.   

-outpage          Results page; otherwise "Wikipedysta:mastiBot/test" is used

-maxlines         Max number of entries before new subpage is created; default 1000

-text:            Use this text to be added; otherwise 'Test' is used

-replace:         Dont add text but replace it

-top              Place additional text on top of the page

-summary:         Set the action summary message for the edit.

-negative:        mark if text not in page
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

import urllib.parse
import datetime
from time import strftime


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

    @ivar summary_key: Edit summary message key. The message that should be used
        is placed on /i18n subdirectory. The file containing these messages
        should have the same name as the caller script (i.e. basic.py in this
        case). Use summary_key to set a default edit summary message.
    @type summary_key: str
    """

    use_redirects = False  # treats non-redirects only
    summary_key = 'basic-changing'

    update_options = {
        'replace': False,  # delete old text and write the new text
        'summary': None,  # your own bot summary
        'text': 'Test',  # add this text from option. 'Test' is default
        'top': False,  # append text on top of the page
        'outpage': u'User:mastiBot/test',  # default output page
        'maxlines': 1000,  # default number of entries per page
        'test': False,  # print testoutput
        'negative': False,  # if True negate behavior i.e. mark pages that DO NOT contain search string
        'automatic': False,  # include automatic reviews in stats
        'days': '30',  # number of days to calculate statistics
    }

    def _handle_dry_param(self, **kwargs):
        """
        Read the dry parameter and set the simulate variable instead.

        This is a private method. It prints a deprecation warning for old
        -dry paramter and sets the global simulate variable and informs
        the user about this setting.

        The constuctor of the super class ignores it because it is not
        part of self.availableOptions.

        @note: You should ommit this method in your own application.

        @keyword dry: deprecated option to prevent changes on live wiki.
            Use -simulate instead.
        @type dry: bool
        """
        if 'dry' in kwargs:
            issue_deprecation_warning('dry argument',
                                      'pywikibot.config.simulate', 1)
            # use simulate variable instead
            pywikibot.config.simulate = True
            pywikibot.output('config.simulate was set to True')

    def run(self):

        # Dict of tuples (review total, initial, other, unreview)
        deletereasons = {}
        deleteadmins = {}

        currtime = datetime.datetime.now()
        starttime = currtime - datetime.timedelta(hours=4)

        deletereasons = self.deleteReasons(currtime,int(self.opt.days))
        deleteadmins = self.deleteStats(currtime,int(self.opt.days))

        if self.opt.test:
            pywikibot.output(u'Delete Reasons: %s' % deletereasons)
            pywikibot.output(u'Delete Stats: %s' % deleteadmins)

        self.generateresultspage(deletereasons,deleteadmins)

    def deleteReasons(self,starttime, days):

        if self.opt.test:
            pywikibot.output(u'Analyzing delete log last %i days.' % days)

        # Dict of tuples (delete reason, number)
        deletes = {}
        count = 0

        for le in self.site.logevents(end=starttime, start=starttime-datetime.timedelta(days=days), reverse=True, logtype='delete'):
            count += 1
            try:
                comment = le.comment()
            except KeyError:
                comment = u''
            if self.opt.test:
                try:
                    pywikibot.output(u'REAS:%i>>%s>>%s>>%s>>%s>>%s>>%s' % (count, le.type(), le.logid(),le.timestamp(),le.action(),le.user(),comment))
                except KeyError:
                    pywikibot.output(u'REAS:%i:CANNOT READ DATA' % count)
            if comment in deletes.keys():
                deletes[comment] += 1
            else:
                deletes[comment] = 1

        return(deletes)

    def deleteStats(self,starttime, days):
        #calculate delete stats per admin
        if self.opt.test:
            pywikibot.output(u'Analyzing delete log last %i days.' % days)
        # Dict of tuples (admin, number)
        deletes = {}
        count = 0

        for le in self.site.logevents(end=starttime, start=starttime-datetime.timedelta(days=days), reverse=True, logtype='delete'):
            count += 1
            try:
                comment = le.comment()
            except KeyError:
                comment = u''
            if self.opt.test:
                try:
                    pywikibot.output(u'STAT:%i>>%s>>%s>>%s>>%s>>%s>>%s' % (count, le.type(), le.logid(),le.timestamp(),le.action(),le.user(),comment))
                except KeyError:
                    pywikibot.output(u'REAS:%i:CANNOT READ DATA' % count)
            #b = self.addreview(reviews,le.user(),le.action())
            try:
                if le.user() in deletes.keys():
                    deletes[le.user()] += 1
                else:
                    deletes[le.user()] = 1
            except:
                if u'BŁĄD DANYCH' in deletes.keys():
                    deletes[u'BŁĄD DANYCH'] += 1
                else:
                    deletes[u'BŁĄD DANYCH'] = 1
                continue

        return(deletes)

    def addreview(self, dictionary, user, action):
        #tuple (review total, initial, other, unreview)

        if user in dictionary.keys():
            total, initial, other, unreview = dictionary[user]
        else:
            total = 0
            initial = 0 
            other = 0
            unreview = 0
        if self.opt.test:
            pywikibot.output(u'IN:%s>>%s>>%i>>%i>>%i>>%i' % (action, user, total, initial, other, unreview))
        # distinguish automatic review
        if self.opt.automatic or not action.endswith('a'):
            total += 1
            if action.startswith('unapprove'):
                unreview += 1
            elif '-i' in action:
                initial += 1
            else:
                other += 1
        else:
            if self.opt.test:
                pywikibot.output(u'Skipped automatic review')
        if self.opt.test:
            pywikibot.output(u'OUT:%s>>%s>>%i>>%i>>%i>>%i' % (action, user, total, initial, other, unreview))
        return (total, initial, other, unreview)

    def mainheader(self):
        # create main header
        header =u'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n'
        header +=u'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="pl" lang="pl" dir="ltr">\n'
        header +=u'        <head>\n'
        header +=u'                <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />\n'
        header +=u'                <title>Statystyki usunięć - ostatnie ' + self.opt.days + u'dni  - tools.wikimedia.pl</title>\n'
        header +=u'                <link rel="stylesheet" type="text/css" href="/~masti/modern.css" />\n'
        header +=u'        </head>\n'
        header +=u'<body>\n'
        header +=u'\n'
        header +=u'        <!-- heading -->\n'
        header +=u'        <div id="mw_header">\n'
        header +=u'                <h1 id="firstHeading">Statystyki usunięć - ostatnie ' + self.opt.days + u' dni</h1>\n'
        header +=u'        </div>\n'
        header +=u'\n'
        header +=u'        <div id="mw_main">\n'
        header +=u'        <div id="mw_contentwrapper">\n'
        header +=u'\n'
        header +=u'        <!-- content -->\n'
        header +=u'        <div id="mw_content">\n'
        header +=u'\n'
        header +=u'                <table class="infobox">\n'
        header +=u'                        <tr><th>Statystyki</th></tr>\n'
        header +=u'                        <tr><td><a href="#deletereason">Usunięcia - uzasadnienia</a></td></tr>\n'
        header +=u'                        <tr><td><a href="#deleteadmins">Usunięcia - administratorzy</a></td></tr>\n'
        header +=u'                </table>\n'
        header +=u'                <p>Strona przedstawia statystykiusunięć stron. Podsumowanie jest generowane na podstawie danych z ostatnich ' + self.opt.days + u' dni. Strona jest aktualizowana raz dziennie (04:00).</p>\n'
        # add creation time
        header += u'        <p>Ostatnia aktualizacja: <b>' + strftime('%A %d %B %Y %X %Z') + u'</b></p>\n'
        header += u'\n'
        header += u'<center><b><a class="external text" href="http://tools.wikimedia.pl/~masti/deletes.html">ODŚWIEŻ</a></b></center>\n'
        return(header)

    def mainfooter(self):
        # create main footer
        footer = u'                </table>\n'
        footer +=u'\n'
        footer +=u'        </div><!-- mw_content -->\n'
        footer +=u'        </div><!-- mw_contentwrapper -->\n'
        footer +=u'\n'
        footer +=u'        </div><!-- main -->\n'
        footer +=u'\n'
        footer +=u'        <div class="mw_clear"></div>\n'
        footer +=u'\n'
        footer +=u'        <!-- personal portlet -->\n'
        footer +=u'        <div class="portlet" id="p-personal">\n'
        footer +=u'                <div class="pBody">\n'
        footer +=u'                        <ul>\n'
        footer +=u'                                <li><a href="//pl.wikipedia.org">wiki</a></li>\n'
        footer +=u'                                <li><a href="/">tools</a></li>\n'
        footer +=u'                                <li><a href="/~masti/">masti</a></li>\n'
        footer +=u'</ul>\n'
        footer +=u'                </div>\n'
        footer +=u'        </div>\n'
        footer +=u'<div class="stopka">layout by <a href="../~beau/">Beau</a></div>\n'
        footer +=u'</body></html>\n'
        footer +=u'\n'
        return(footer)

    def deletereasonheader(self,days):
        #create section header
        header  =u'                <h2><a name="deletereason"></a>Usunięcia - uzasadnienia - ostatnie '+ str(days) + u' dni</h2>\n'
        header +=u'                <table class="wikitable sortable" >\n'
        header +=u'                        <colgroup span="1" style="width: 5%"></colgroup>\n'
        header +=u'                        <colgroup span="1" style="text-align: left"></colgroup>\n'
        header +=u'                        <tr>\n'
        header +=u'                                <th>Liczba</th>\n'
        header +=u'                                <th>Powód</th>\n'        
        header +=u'                        </tr>\n'
        return(header)

    def deletereasonfooter(self):
        footer  = u'                </table>\n'
        footer += u'                <p>Jednorazowe uzasadnienia nie zostały pokazane.</p>\n'
        return(footer)


    def generatedeletereasonsection(self, deletes, days):
        # generate one section with stats i.e.24h, 168h
        output = self.deletereasonheader(days)

        res = sorted(deletes, key=deletes.__getitem__, reverse=True)
        for i in res:
            if self.opt.test:
                pywikibot.output(u'%s->%s' % (i, deletes[i]))
            # skip single entries
            if deletes[i] < 2:
                break
            output += u'\t\t\t<tr>\n'
            output += u'\t\t\t\t<td>' + u'{:6d}'.format(deletes[i]) + u'</td><td>' + i + u'</td>\n'
            output += u'\t\t\t</tr>\n'
        output += self.deletereasonfooter()
        return(output)

    def deletestatheader(self,days):
        #create section header
        header  =u'                <h2><a name="deleteadmins"></a>Usunięcia - administratorzy - ostatnie '+ str(days) + u' dni</h2>\n'
        header +=u'                <table class="stats">\n'
        header +=u'                        <colgroup>\n'
        header +=u'                                <col style="width: 15%"/>\n'
        header +=u'                                <col style="width: 5%"/>\n'
        header +=u'                        </colgroup>\n'
        header +=u'                        <tr>\n'
        header +=u'                                <th>Administrator</th>\n'
        header +=u'                                <th>Liczba</th>\n'
        header +=u'                                <th>Udział</th>\n'        
        header +=u'                        </tr>\n'
        return(header)

    def deletestatfooter(self):
        footer  = u'                </table>\n'
        footer += u'                <p>Jednorazowe działania nie zostały pokazane.</p>\n'
        return(footer)

    def generatedeletestatsection(self, deletes, days):
        # generate one section with stats i.e.24h, 168h
        output = self.deletestatheader(days)

        #count total number of actions
        total = 0
        for a in deletes:
            total += deletes[a]

        res = sorted(deletes, key=deletes.__getitem__, reverse=True)
        for i in res:
            if self.opt.test:
                pywikibot.output(u'%s->%s' % (i, deletes[i]))
            # skip single entries
            if deletes[i] < 2:
                break
            output += u'                        <tr>\n'
            link = u'//pl.wikipedia.org/wiki/Wikipedysta:' + urllib.parse.quote(i)
            output += u'                                <td><a href="' + link + u'">' + i + u'</a></td>\n'
            output += u'                                <td>' + str(deletes[i]) + u'</td>\n'
            percentage = u'{:3.4f}%'.format(deletes[i]/float(total)*100)
            output += u'                                <td><div style="width: ' + percentage + u';">' + percentage + u'</div></td>\n'
            output += u'                        </tr>\n'
        output += self.deletereasonfooter()
        return(output)


    def generateresultspage(self,delete1, delete2):

        output = self.mainheader()

        output += self.generatedeletereasonsection(delete1,int(self.opt.days))
        output += self.generatedeletestatsection(delete2,int(self.opt.days))

        output += self.mainfooter()

        # write ready file
        #test
        #pywikibot.output(u'Writing file: %s' % self.opt.outpage)
        rf= open(u'masti/html/'+self.opt.outpage,'wb')
        rf.write(bytes(output, 'UTF-8'))
        rf.close()
        return

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
    # local_args = gen_factory.handle_args(local_args)
    local_args = gen_factory.handle_args(local_args)

    # Parse your own command line arguments
    for arg in local_args:
        arg, _, value = arg.partition(':')
        option = arg[1:]
        if option in ('summary', 'text', 'outpage', 'maxlines', 'days'):
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
