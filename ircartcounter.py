#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
A script that displays the ordinal number of the new articles being created
visible on the Recent Changes list. The script doesn't make any edits, no bot
account needed.

Note: the script requires the Python IRC library
http://python-irclib.sourceforge.net/
"""

# Author: Balasyum
# http://hu.wikipedia.org/wiki/User:Balasyum
# License : LGPL
# from __future__ import absolute_import, unicode_literals

__version__ = '$Id: 229b3e02cf110f5e9d7f8d16c60906ee9769b7af $'

import re
# import threading
# from pywikibot import textlib
import sys
# import ssl
import os

import pywikibot
import requests
from pywikibot.comms.http import request
import datetime, time
# from time import strftime
# import irclib
# from irc.bot import SingleServerIRCBot
import irc.bot
import irc.strings

def getURL(site):
    apiURL = f'https://{site.lang}.{site.family.name}.org/w/api.php?action=query&meta=siteinfo&siprop=statistics&format=xml'
    r = requests.get(apiURL)
    return r.text

class ArtNoDisp(irc.bot.SingleServerIRCBot):

    def __init__(self, site, channel, nickname, server, port=6667):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel
        self.site = site
        # self.lang = site.language()
        self.lang = site.lang
        self.apiURL = f'https://{self.lang}.{site.family.name}.org/w/api.php?action=query&meta=siteinfo&siprop=statistics&format=xml'
        self.logname = f'masti/ircbot/artnos{self.lang}.log'

        ns = []
        # for n in site.namespaces():
        for n in site.namespaces:
            if isinstance(n, tuple):  # I am wondering that this may occur!
                ns += n[0]
            else:
                ns += [n]
        # self.other_ns = re.compile(u'14\[\[07(' + u'|'.join(ns) + u')')
        # self.api_url = self.site.api_address()
        # self.api_url += 'action=query&meta=siteinfo&siprop=statistics&format=xml'
        # self.api_found = re.compile(r'articles="(.*?)"')
        self.re_edit = re.compile(
            r'^C14\[\[^C07(?P<page>.+?)^C14\]\]^C4 (?P<flags>.*?)^C10 ^C02(?P<url>.+?)^C ^C5\*^C ^C03(?P<user>.+?)^C ^C5\*^C \(?^B?(?P<bytes>[+-]?\d+?)^B?\) ^C10(?P<summary>.*)^C'.replace(
                '^B', '\002').replace('^C', '\003').replace('^U', '\037'))
        self.re_move = re.compile(
            r'^C14\[\[^C07(?P<page>.+?)^C14]]^C4 move^C10 ^C02^C ^C5\*^C ^C03(?P<user>.+?)^C ^C5\*^C  ^C10(?P<action>.+?) \[\[^C02(?P<frompage>.+?)^C10]] to \[\[(?P<topage>.+?)]]((?P<summary>.*))?^C'.replace(
                '^C', '\003'))
        self.re_move_redir = re.compile(
            r'^C14\[\[^C07(?P<page>.+?)^C14]]^C4 move_redir^C10 ^C02^C ^C5\*^C ^C03(?P<user>.+?)^C ^C5\*^C  ^C10(?P<action>.+?) \[\[^C02(?P<frompage>.+?)^C10]] to \[\[(?P<topage>.+?)]] over redirect: ((?P<summary>.*))?^C'.replace(
                '^C', '\003'))
        self.re_delete_redir = re.compile(
            r'^C14\[\[^C07(?P<page>.+?)^C14]]^C4 delete_redir^C10 ^C02^C ^C5\*^C ^C03(?P<user>.+?)^C ^C5\*^C  ^C10(?P<action>.+?) \[\[^C02(?P<frompage>.+?)^C10\]\](?P<reason>.*?):(?P<comment>.*?„\[\[(?P<topage>.*?\]\])”)^C'.replace(
                '^C', '\003'))

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_privmsg(self, c, e):
        pass

    def on_pubmsg(self, c, e):
        # pywikibot.output(c)
        # pywikibot.output(e)
        # source = unicode(e.source().split ( '!' ) [ 0 ], 'utf-8')
        # text = unicode(e.arguments [ 0 ], 'utf-8')
        # source = e.source().split('!')[0]
        # text = e.arguments[0]
        # print text
        # pywikibot.output(u'CONNECTION:%s' % unicode(c[ 0 ], 'utf-8'))
        # pywikibot.output(u'SOURCE:%s' % source)
        # if u'move' in text:
        #    pywikibot.output(u'TEXT move:%s' % text)

        edit = False
        move = False
        move_redir = False
        delete_redir = False

        match = self.re_edit.match(e.arguments[0])
        matchmove = self.re_move.match(e.arguments[0])
        matchmoveredir = self.re_move_redir.match(e.arguments[0])
        matchdeleteredir = self.re_delete_redir.match(e.arguments[0])

        if match:
            edit = True
            # pywikibot.output(u'EDIT')
        elif matchmove:
            move = True
            # pywikibot.output(u'MOVE')
        elif matchmoveredir:
            move_redir = True
            matchmove = matchmoveredir
            # pywikibot.output(u'MOVE_REDIR')
        elif matchdeleteredir:
            delete_redir = True
            matchmove = matchdeleteredir
            # pywikibot.output(u'DELETE_REDIR')

        if move or move_redir or delete_redir:
            mvpagefrom = matchmove.group('frompage')
            mvpageto = matchmove.group('topage')
            # mvactionu = unicode(matchmove.group('actionu'), 'utf-8')
            mvaction = matchmove.group('action')
            if matchmove.group('summary'):
                mvsummary = matchmove.group('summary')
            else:
                mvsummary = u''
            mvuser = matchmove.group('user')
            currtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pywikibot.output('MOVE->F:%s:T:%s:AT:%s:S:%s:SU:%s:T:%s' % (
            mvpagefrom, mvpageto, mvaction, mvuser, mvsummary, currtime))
            frompage = pywikibot.Page(self.site, mvpagefrom)
            topage = pywikibot.Page(self.site, mvpageto)
            if topage.namespace() == 0 and not frompage.namespace == 0:
                # NAthread = newArticleThread((topage,))

                # register edit
                # text = self.site.getUrl(self.apiURL)
                text = getURL(site=self.site)
                # print text.encode('UTF-8')
                artsR = re.compile(r'articles="(?P<arts>.*?)"')
                match = artsR.search(text)
                arts = match.group('arts')
                # pywikibot.output(u'Liczba artykułów:%s' % arts)
                logfile = open(self.logname, "a")
                if topage.isRedirectPage():
                    try:
                        # logline = arts + ';' + currtime + ';RM;' + mvpageto + ';' + topage.getRedirectTarget().title() + u'\n'
                        logline = f'{arts};{currtime};RM;{mvpageto};{topage.getRedirectTarget().title()}\n'
                    except pywikibot.exceptions.CircularRedirect:
                        # logline = arts + ';' + currtime + ';R;' + mpage + ';' + mpage + u'\n'
                        logline = f'{arts};{currtime};R;{mpage};{mpage};\n'
                else:
                    # logline = arts + ';' + currtime + ';AM;' + mvpageto + u';\n'
                    logline = f'{arts};{currtime};AM;{mvpageto}\n'
                pywikibot.output(logline)
                logfile.write(logline)
                logfile.close()

        elif edit:
            mflags = match.group('flags')
            # murl = unicode(match.group('url'), 'utf-8')
            # muser = unicode(match.group('user'), 'utf-8')
            # mbytes = unicode(match.group('bytes'), 'utf-8')
            mpage = match.group('page')
            # msummary = unicode(match.group('summary'), 'utf-8')
            currtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # print (u'P:%s:F:%s:U:%s:B:%s:S:%s:U:%s:T:%s' % (mpage,mflags,muser,mbytes,msummary,murl,currtime)).encode('UTF-8')
            newArt = 'N' in mflags
            page = pywikibot.Page(self.site, mpage)
            # print (u'P:%s:F:%s:U:%s:B:%s:S:%s:U:%s:T:%s:NS:%i' % (mpage,mflags,muser,mbytes,msummary,murl,currtime,page.namespace())).encode('UTF-8')

            if newArt and (page.namespace() == 0):
                # try threading
                if not page.isRedirectPage():
                    # NAthread = newArticleThread((page,))
                    pass
                else:
                    pywikibot.output('skipping')

                # print 'new article'
                # currtime = strftime("%Y-%m-%d %H:%M:%S", datetime.datetime.now().time())

                # register edit
                pywikibot.output(f'SITEINFO:{str(self.site.siteinfo)}')
                # text = self.site.getUrl(self.apiURL)
                # print text.encode('UTF-8')
                text = getURL(site=self.site)
                artsR = re.compile(r'articles="(?P<arts>.*?)"')
                match = artsR.search(text)
                arts = match.group('arts')
                # pywikibot.output(u'Liczba artykułów:%s' % arts)
                logfile = open(self.logname, "a")
                if page.isRedirectPage():
                    try:
                        # logline = arts + ';' + currtime + ';R;' + mpage + ';' + page.getRedirectTarget().title() + u'\n'
                        logline = f'{arts};{currtime};R;{mpage};{page.getRedirectTarget().title()}\n'
                    except pywikibot.exceptions.CircularRedirect:
                        # logline = arts + ';' + currtime + ';R;' + mpage + ';' + mpage + u'\n'
                        logline = f'{arts};{currtime};R;{mpage};{mpage}\n'
                else:
                    logline = arts + ';' + currtime + ';A;' + mpage + u';\n'
                pywikibot.output(logline)
                logfile.write(logline)
                logfile.close()
                # print 'look ma, thread is not alive: ', thread.is_alive()
            # elif page.namespace() == 2:
            #    UPthread = userPageThread((page,))
            else:
                pywikibot.output(f'[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Skipping:{page.title()}')

    def on_dccmsg(self, c, e):
        pass

    def on_dccchat(self, c, e):
        pass

    def do_command(self, e, cmd):
        pass

    def on_quit(self, e, cmd):
        pass


def savepid(suffix):
    """ get script name and pid, save it in scriptname.pid"""
    # scrR = r'.*\/(.*?)\.py'
    script = re.sub('.*\/(.*?)\.py', '\1', sys.argv[0])
    pid = os.getpid()
    pidname = f'masti/pid/ircartcounter{suffix}.pid'
    pidfile = open(pidname, "w")
    pidfile.write(f'{str(pid)}\n')
    pidfile.close()
    return


def main():
    botname = 'mastiBotIRC'
    lang = 'pl'
    for arg in sys.argv:
        if arg.startswith('-lang:'):
            lang = arg[6:]
            botname = f'{botname}{lang}'
        if arg.startswith('-name:'):
            botname = arg[6:]
    savepid(u'-' + lang)
    site = pywikibot.Site(lang, fam='wikipedia')
    # site.forceLogin()
    # chan = f'#{site.language()}.{site.family.name}'
    chan = f'#{site.lang}.{site.family}'

    bot = ArtNoDisp(site, chan, botname, "irc.wikimedia.org")
    bot.start()


if __name__ == "__main__":
    main()