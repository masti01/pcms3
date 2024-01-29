#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import re
import sys
import pywikibot
import codecs
import urllib.parse
from datetime import datetime
from time import strftime

i18 = {
    'pl': {
        'head': 'pl.wikipedia - Ostatnie nowe artykuły - tools.wikimedia.pl',
        'heading': 'Ostatnie nowe artykuły',
        'line1': 'Strona przedstawia numerację ostatnio utworzonych 100 artykułów z głównej przestrzeni nazw.',
        'legend': 'Rodzaj: <b>A</b> (artykuł), <b>R</b> (przekierowanie), <b>M</b> (przeniesiony)',
        'lastupdate': 'Ostatnia aktualizacja: ',
        'refresh': 'Strona uaktualniana co 5 minut. Wyświetlanie od najnowszych.',
        'hnumber': 'Numer artykułu',
        'htype': 'Rodzaj',
        'hdate': 'Data',
        'htime': 'Czas',
        'htitle': 'Tytuł',
        'htarget': 'Cel'},
    'tr': {
        'head': 'tr.wikipedia - Madde sayacı - son 100 madde',
        'heading': 'Son yeni maddeler',
        'line1': u"Sayfa, belirtilen dil sürümündeki son 100 makalenin makale ID'lerini gösterir",
        'legend': 'Tür: <b>A</b> (madde), <b>R</b> (yönlendirme)',
        'lastupdate': 'Son güncellenme: ',
        'refresh': 'Sayfa 5 dakikada bir yenilenir. En yeni, en başta gösterilir.',
        'hnumber': 'Madde no',
        'htype': 'Tür',
        'hdate': 'Tarih',
        'htime': 'Saat',
        'htitle': 'Başlık',
        'htarget': 'Hedef'},
    'szl': {
        'head': 'szl.wikipedia - Ostatnie nowe artykuły - tools.wikimedia.pl',
        'heading': 'Ostatnie nowe artykuły',
        'line1': 'Strona przedstawia numerację ostatnio utworzonych 100 artykułów z głównej przestrzeni nazw.',
        'legend': 'Rodzaj: <b>A</b> (artykuł), <b>R</b> (przekierowanie), <b>M</b> (przeniesiony)',
        'lastupdate': 'Ostatnia aktualizacja: ',
        'refresh': 'Strona uaktualniana co 5 minut. Wyświetlanie od najnowszych.',
        'hnumber': 'Numer artykułu',
        'htype': 'Rodzaj',
        'hdate': 'Data',
        'htime': 'Czas',
        'htitle': 'Tytuł',
        'htarget': 'Cel'},
    'csb': {
        'head': 'csb.wikipedia - Ostatnie nowe artykuły - tools.wikimedia.pl',
        'heading': 'Ostatnie nowe artykuły',
        'line1': 'Strona przedstawia numerację ostatnio utworzonych 100 artykułów z głównej przestrzeni nazw.',
        'legend': 'Rodzaj: <b>A</b> (artykuł), <b>R</b> (przekierowanie), <b>M</b> (przeniesiony)',
        'lastupdate': 'Ostatnia aktualizacja: ',
        'refresh': 'Strona uaktualniana co 5 minut. Wyświetlanie od najnowszych.',
        'hnumber': 'Numer artykułu',
        'htype': 'Rodzaj',
        'hdate': 'Data',
        'htime': 'Czas',
        'htitle': 'Tytuł',
        'htarget': 'Cel'}
}


def header(lang):
    # generate html file header
    header = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n'
    header += '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="pl" lang="pl" dir="ltr">\n'
    header += '	<head>\n'
    header += '		<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />\n'
    header += '		<meta http-equiv="refresh" content="300">\n'
    header += '		<title>' + i18[lang]['head'] + '</title>\n'
    header += '		<link rel="stylesheet" type="text/css" href="/~masti/modern.css" />\n'
    header += '	</head>\n'
    header += '<body>\n'
    header += '\n'
    header += '	<!-- heading -->\n'
    header += '\n'
    header += '	<div id="mw_header">\n'
    header += '		<h1 id="firstHeading">' + i18[lang]['heading'] + '</h1>\n'
    header += '	</div>\n'
    header += '\n'
    header += '	<div id="mw_main">\n'
    header += '	<div id="mw_contentwrapper">\n'
    header += '\n'
    header += '	<!-- content -->\n'
    header += '	<div id="mw_content">\n'
    header += '\n'
    header += '		<p>' + i18[lang]['line1'] + '<br />\n'
    header += '		<small>' + i18[lang]['legend'] + '</small><br />\n'
    header += '		<small>' + i18[lang]['refresh'] + '</small><br />\n'
    header += '		</p>\n'
    # add creation time
    header += '		<p>' + i18[lang]['lastupdate'] + '<b>' + strftime('%A %d %B %Y %X %Z') + '</b></p>\n'
    header += '\n'
    #
    header += '                <center>\n'
    header += '		<table class="wikitable" style="width:85%">\n'
    header += '			<tr>\n'
    header += '				<th>' + i18[lang]['hnumber'] + '</th>\n'
    header += '				<th>' + i18[lang]['hdate'] + '</th>\n'
    header += '				<th>' + i18[lang]['htime'] + '</th>\n'
    header += '				<th>' + i18[lang]['htype'] + '</th>\n'
    header += '				<th>' + i18[lang]['htitle'] + '</th>\n'
    header += '				<th>' + i18[lang]['htarget'] + '</th>\n'
    header += '			</tr>\n'
    return (header)


def footer(lang):
    # generate html file footer
    footer = '		</table>\n'
    footer += '                </center> \n'
    footer += '\n'
    footer += '	</div><!-- mw_content -->\n'
    footer += '	</div><!-- mw_contentwrapper -->\n'
    footer += '\n'
    footer += '	</div><!-- main -->\n'
    footer += '\n'
    footer += '	<div class="mw_clear"></div>\n'
    footer += '\n'
    footer += '	<!-- personal portlet -->\n'
    footer += '	<div class="portlet" id="p-personal">\n'
    footer += '		<div class="pBody">\n'
    footer += '			<ul>\n'
    footer += '				<li><a href="http://pl.wikipedia.org">wiki</a></li>\n'
    footer += '				<li><a href="/">tools</a></li>\n'
    footer += '				<li><a href="/~masti/">masti</a></li>\n'
    footer += '			</ul>\n'
    footer += '		</div>\n'
    footer += '		</div>\n'
    footer += '<div class="stopka">layout by <a href="../~beau/">Beau</a></div>\n'
    footer += '<!-- Matomo -->\n'
    footer += '<script type="text/javascript">\n'
    footer += '  var _paq = _paq || [];\n'
    footer += '  /* tracker methods like "setCustomDimension" should be called before "trackPageView" */\n'
    footer += u"  _paq.push(['trackPageView']);\n"
    footer += u"  _paq.push(['enableLinkTracking']);\n"
    footer += '  (function() {\n'
    footer += '    var u="//s.wikimedia.pl/";\n'
    footer += u"    _paq.push(['setTrackerUrl', u+'piwik.php']);\n"
    footer += u"    _paq.push(['setSiteId', '5']);\n"
    footer += u"    var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];\n"
    footer += u"    g.type='text/javascript'; g.async=true; g.defer=true; g.src=u+'piwik.js'; s.parentNode.insertBefore(g,s);\n"
    footer += '  })();\n'
    footer += '</script>\n'
    footer += '<noscript><p><img src="//s.wikimedia.pl/piwik.php?idsite=5&rec=1" style="border:0;" alt="" /></p></noscript>\n'
    footer += '<!-- End Matomo Code -->\n'
    footer += '</body></html>'
    return (footer)


def outputRow(logline, lang):
    # creates one output row
    s = re.sub(u'\n', '', logline)
    # print s
    try:
        anum, adtime, atype, atitle, atarget = s.split(u';')
        adate, atime = adtime.split()
    except:
        return (None)
    # encode URLs for title and target
    utitle = 'https://' + lang + '.wikipedia.org/wiki/' + urllib.parse.quote(atitle)
    # print utitle
    if atarget == '':
        utarget = ''
    else:
        utarget = 'https://' + lang + '.wikipedia.org/wiki/' + urllib.parse.quote(atarget)
    # create output
    result = '\t\t\t<tr>\n'
    result += '\t\t\t\t<td>' + anum + '</td>\n'
    result += '\t\t\t\t<td>' + adate + '</td>\n'
    result += '\t\t\t\t<td>' + atime + '</td>\n'
    result += '\t\t\t\t<td>' + atype + '</td>\n'
    site = pywikibot.Site(lang, fam='wikipedia')
    page = pywikibot.Page(site, atitle)

    result += '\t\t\t\t<td>' + linkcolor(page, lang) + '</td>\n'
    if page.exists():
        if page.isRedirectPage():
            try:
                tpage = page.getRedirectTarget()
                result += '\t\t\t\t<td>' + linkcolor(tpage, lang) + '</td>\n'
            except pywikibot.exceptions.CircularRedirect:
                tpage = None
                result += '\t\t\t\t<td></td>\n'
        else:
            result += '\t\t\t\t<td></td>\n'
    else:
        result += '\t\t\t\t<td></td>\n'
    result += '\t\t\t</tr>\n'

    # pywikibot.output(result)
    return (result)


def linkcolor(page, lang):
    # return html link for page
    # <a href="PAGE TITLE URL" style="color:#308050">' + PAGE TITLE + '</a>

    if page.exists():
        if page.isRedirectPage():
            return (u'<a href="https://' + lang + '.wikipedia.org/wiki/' + urllib.parse.quote(
                page.title()) + '" style="color:#308050">' + page.title() + '</a>')
        elif page.isDisambig():
            return (u'<a href="https://' + lang + '.wikipedia.org/wiki/' + urllib.parse.quote(
                page.title()) + '" style="color:#800000">' + page.title() + '</a>')
        else:
            return (u'<a href="https://' + lang + '.wikipedia.org/wiki/' + urllib.parse.quote(
                page.title()) + '">' + page.title() + '</a>')
    else:
        return (u'<a href="https://' + lang + '.wikipedia.org/w/index.php?title=' + urllib.parse.quote(
            page.title()) + '&action=edit&redlink=1" style="color:#CC2200">' + page.title() + '</a>')


def main(*args):
    for arg in sys.argv:
        if arg.startswith('-lang:'):
            lang = arg[6:]
    site = pywikibot.Site(lang, fam='wikipedia')

    artlist = []
    result = ''

    logfile = 'ircbot/artnos' + lang + '.log'
    resultfile = 'masti/artykuly' + lang + '.html'

    file = codecs.open(logfile, "r", "utf-8")
    artlist = file.readlines()
    file.close()
    arts = artlist[-100:]

    # print artlist

    result = header(lang)
    for a in reversed(arts):
        r = outputRow(a, lang)
        if r:
            result += r
    result += footer(lang)
    file = codecs.open(resultfile, 'w', 'utf-8')
    # printout log
    # pywikibot.output(result)
    file.write(result)
    file.close()


if __name__ == '__main__':
    main()