#!/usr/bin/python

"""
Call:
	python3 pwb.py masti/wlc3.py -ignore:401 -ignore:403 -ignore:451 -ignore:500 -ignore:503 -ignore:429 -talk -pt:0 -talk -start:'!'

This bot is used for checking external links found at the wiki.

It checks several pages at once, with a limit set by the config variable
max_external_links, which defaults to 50.

The bot won't change any wiki pages, it will only report dead links such that
people can fix or remove the links themselves.

The bot will store all links found dead in a .dat file in the deadlinks
subdirectory. To avoid the removing of links which are only temporarily
unavailable, the bot ONLY reports links which were reported dead at least
two times, with a time lag of at least one week. Such links will be logged to a
.txt file in the deadlinks subdirectory.

The .txt file uses wiki markup and so it may be useful to post it on the
wiki and then exclude that page from subsequent runs. For example if the
page is named Broken Links, exclude it with '-titleregexnot:^Broken Links$'

After running the bot and waiting for at least one week, you can re-check those
pages where dead links were found, using the -repeat parameter.

In addition to the logging step, it is possible to automatically report dead
links to the talk page of the article where the link was found. To use this
feature, set report_dead_links_on_talk = True in your user-config.py, or
specify "-talk" on the command line. Adding "-notalk" switches this off
irrespective of the configuration variable.

When a link is found alive, it will be removed from the .dat file.

These command line parameters can be used to specify which pages to work on:

-repeat      Work on all pages were dead links were found before. This is
             useful to confirm that the links are dead after some time (at
             least one week), which is required before the script will report
             the problem.

-namespace   Only process templates in the namespace with the given number or
             name. This parameter may be used multiple times.

-xml         Should be used instead of a simple page fetching method from
             pagegenerators.py for performance and load issues

-xmlstart    Page to start with when using an XML dump

-ignore      HTTP return codes to ignore. Can be provided several times :
                -ignore:401 -ignore:500

&params;

Furthermore, the following command line parameters are supported:

-talk        Overrides the report_dead_links_on_talk config variable, enabling
             the feature.

-notalk      Overrides the report_dead_links_on_talk config variable, disabling
             the feature.

-day         Do not report broken link if the link is there only since
             x days or less. If not set, the default is 7 days.

The following config variables are supported:

 max_external_links         The maximum number of web pages that should be
                            loaded simultaneously. You should change this
                            according to your Internet connection speed.
                            Be careful: if it is set too high, the script
                            might get socket errors because your network
                            is congested, and will then think that the page
                            is offline.

 report_dead_links_on_talk  If set to true, causes the script to report dead
                            links on the article's talk page if (and ONLY if)
                            the linked page has been unavailable at least two
                            times during a timespan of at least one week.

 weblink_dead_days          sets the timespan (default: one week) after which
                            a dead link will be reported

Examples
--------

Loads all wiki pages in alphabetical order using the Special:Allpages
feature:

    python pwb.py weblinkchecker -start:!

Loads all wiki pages using the Special:Allpages feature, starting at
"Example page":

    python pwb.py weblinkchecker -start:Example_page

Loads all wiki pages that link to www.example.org:

    python pwb.py weblinkchecker -weblink:www.example.org

Only checks links found in the wiki page "Example page":

    python pwb.py weblinkchecker Example page

Loads all wiki pages where dead links were found during a prior run:

    python pwb.py weblinkchecker -repeat
"""
#
# (C) Pywikibot team, 2005-2020
#
# Distributed under the terms of the MIT license.
#
import codecs
import datetime
import pickle
import re
import threading
import time

from contextlib import suppress
from functools import partial

import mwparserfromhell
import requests

import pywikibot

from pywikibot import comms, i18n, pagegenerators, textlib
from pywikibot import config

from pywikibot.bot import ExistingPageBot, SingleSiteBot, suggest_help
from pywikibot.pagegenerators import (
    XMLDumpPageGenerator as _XMLDumpPageGenerator,
)

# from pywikibot.tools.formatter import color_format
from pywikibot.tools.threading import ThreadList

try:
    import memento_client
    from memento_client.memento_client import MementoClientException
except ImportError as e:
    memento_client = e

docuReplacements = {'&params;': pagegenerators.parameterHelp}  # noqa: N816

ignorelist = [
    # Officially reserved for testing, documentation, etc. in
    # https://tools.ietf.org/html/rfc2606#page-2
    # top-level domains:
    re.compile(r'.*[\./@]test(/.*)?'),
    re.compile(r'.*[\./@]example(/.*)?'),
    re.compile(r'.*[\./@]invalid(/.*)?'),
    re.compile(r'.*[\./@]localhost(/.*)?'),
    # second-level domains:
    re.compile(r'.*[\./@]example\.com(/.*)?'),
    re.compile(r'.*[\./@]example\.net(/.*)?'),
    re.compile(r'.*[\./@]example\.org(/.*)?'),

    # Other special cases
    re.compile(r'.*[\./@]berlinonline\.de(/.*)?'),
    # above entry to be manually fixed per request at
    # [[de:Benutzer:BLueFiSH.as/BZ]]
    # bot can't handle their redirects:

    # bot rejected on the site, already archived
    re.compile(r'.*[\./@]web\.archive\.org(/.*)?'),
    re.compile(r'.*[\./@]archive\.is(/.*)?'),
    re.compile(r'.*[\./@]archive\.vn(/.*)?'),
    re.compile(r'.*[\./@]archive.li(/.*)?'),
    re.compile(r'.*[\./@]archive.md(/.*)?'),
    re.compile(r'.*[\./@]archive.today(/.*)?'),

    # ignore links to files like spreadsheets
    re.compile(r'.*[\./@]\.xlsx?(/.*)?'),
    re.compile(r'.*[\./@]\.docx?(/.*)?'),

    # ignore wikimedia projects links
    re.compile(r'.*[\./@]wikipedia\.org(/.*)?'),
    re.compile(r'.*[\./@]wiktionary\.org(/.*)?'),
    re.compile(r'.*[\./@]wikisource\.org(/.*)?'),
    re.compile(r'.*[\./@]wikimedia\.org(/.*)?'),
    re.compile(r'.*[\./@]wikivoyage\.org(/.*)?'),
    re.compile(r'.*[\./@]wikidata\.org(/.*)?'),


    # Ignore links containing * in domain name
    # as they are intentionally fake
    re.compile(r'https?\:\/\/\*(/.*)?'),

    # masti's collected exceptions
    re.compile('.*[\./@]anfp\.cl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]antiqueadvertising\.com/pics/lucky\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bipraciborz\.pl/bip/dokumenty-akcja-wyszukaj-idkategorii-39906'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]brutalism\.com/content/anima-damnata-atrocious-disfigurement-of-the-redeemers-corpse-at-the-graveyard-of-humanity'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]brutalism\.com/content/hyperial-sceptical-vision'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]brutalism\.com/content/welicoruss-and-the-story-behind-skirts-and-make-up'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cavanheritage\.ie/Default\.aspx?StructureID_str=2'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ceausescu\.org/ceausescu_texts/revolution/trial-eng\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cityofandalusia\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ck-czestochowa\.pl/wyszukiwarka-grobow/szukaj'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]ebelchatow\.pl/content/nie-plus-plus-polska-razem'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]europeanvoice\.com/folder/theswedishpresidencyoftheeu/124.aspx?artid=65305'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]federnuoto\.it/federazione/federazione-news/item/40079-barelli-eletto-alla-camera\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]forumakademickie\.pl/aktualnosci/2011/1/5/765/jak-ck-wybierano/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]forumakademickie\.pl/fa/2013/02/chalasinscy/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]forumakademickie\.pl/fa/2015/07-08/kronika-wydarzen/odzew-w-sprawie-bez-odzewu/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]gum\.gov\.pl/ftp'),  # bot rejected on site (masti, Akoshina)
    re.compile('.*[\./@]hej\.mielec\.pl/miasto2/repoe/art548,publiczne-gimnazjum-w-wadowicach-gornych-z-imieniem-leszka-deptuly-ten-dzien-zapisze-sie-w-historii\\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]jablunkov\.cz/ic/index\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lameziainstrada\.com/politica/politiche-2018-matteo-salvini-eletto-senatore-in-calabria-furgiuele-deputato'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]linkedin\.com/in/krzysztof-lisek-7a6259bb/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]linyi\.gov\.cn/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]maius\.uj\.edu\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]monsourdelrosario\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]movimentocinquestelle\.it/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]msp\.gov\.pl/pl/media/aktualnosci/31579,Zmiany-w-kierownictwie-MSP\\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]niccolorinaldi\.it/chi-sono/biografia\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]pip\.gov\.pl/pl/wiadomosci/69784,roman-giedrojc-glownym-inspektorem-pracy\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]pism\.pl/publications/bulletin/no-55-905'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]piw\.pl/indeks-autorow/ferry-luc'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]polishmusic\.ca/skok/cds/polskie/grupy/a/2plus1/2plus1\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]polishmusic\.ca/skok/cds/polskie/grupy/r/roma/roma\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]polishmusic\.ca/skok/cds/polskie/grupy/s/smerfy/smerfy\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]polishmusic\.ca/skok/cds/polskie/grupy/s/szczesni/szczesni\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rezeknesbiblioteka\.lv/index\.php?option=com_content&view=article&id=376:apsveicam-vladimirs-nikonovs&catid=163:par-izstadem-cb&Itemid=104'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]segodnya\.ua/politics/pnews/olga-bogomolec-sobiraetsya-ballotirovatsya-v-prezidenty-ukrainy-505598\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]shellenicparliament\.gr/en/Vouleftes/Diatelesantes-Vouleftes-Apo-Ti-Metapolitefsi-Os-Simera'),  # bot rejected on site (masti, Elfhelm)
# Ze słownikiem Kopalińskiego podobna sytuacja jak z Gcatholikiem, tzn\. część linków zgłoszona prawidłowo, część nieprawidłowo\. Nieprawidłowe zgłoszenia to:
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/02162EB3B37F6455412565B70004B0F9\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/0CE83B0EDC7B72F2C12565DB0064BCBF\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/18D2145DAFA7FBD3C12565BE001644D4\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/21BBD727783F862B412565CD0051A57E\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/246F68861BD49548412565BA003434EE\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/255DF08B813660F5412565BA0036F441\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/27192AAB9A0B2452412565B70039BB8A\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/27DC83AA85CAF6D5C125656F001C75B0\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/286890E66B322A6B412565BA0022F4CB\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/2D64302975D79C3AC125658C005F8974\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/2E48A299DC6EB482C125658B0074E140\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/2ED46894AB6C6A27C12565E70063258C\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/2FD5655E3C91FBCD412565D30056733A\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/2FFEDBF26AC72CCF412565B60051565A\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/33EF8940386A2E0AC12565EE005AE531\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/3BD9AF807D7613D2412565BA0022CCA0\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/3E3CFA773D4AABF3C12565BD006673CB\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/40650EF20C762479412565BF00294622\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/489E074C12B30A35412565CD004BECDB\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/4AB76064E593F011C125658C0063B83F\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/4AB9FF36C825C18FC125657C0081D067\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/4AD308518E458BA8412565B8001C110B\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/55ADB4D52C9A3ECBC12565BE0043D580\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/5774F597D0942D31412565CB0059A735\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/578F60BA759FF4A4412565BA002D82B8\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/650218F9F3D03517412565CB0072C82A\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/6DEC11B84950D1F9412565BA0021C94C\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/6FCBE3EE599F3EC3C12565B60006269D\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/7290491D99D06D0A412565D3004C6CD1\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/73D68C65F2C33E6BC12565BD003BCD92\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/7A9AECCA5EC4A591C12565BD0057FAD5\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/8061E4B2EE139D5AC12565EE006E6A0A\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/844BEF3539CCC370C12565EF0046B5C6\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/84C8DEF5AB6694F2412565CD005DB310\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/93E2A52FDA53B491C12565BD003B5FB3\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/944B03D3BB6696F6C12565BD00540FE8\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/97EC1A11607283AE412565CC004763B7\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/994E28BF6FC733A9412565BA00289ACA\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/9BB6A4284E15C4EEC12565E700674E8B\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/9CC69A2A9E99A48CC12565B5007CD020\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/ADE096011D04FB9DC12565BD0057383C\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/AE5ABDF9E893388EC12565EE005D855D\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/B9A4FD7AD8EC09F5412565BA002D5036\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/BB932EB1B605294A412565B80010EED6\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/C1489C254BDB29D1412565B800092026\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/C9CF9AFC8175D311412565CC007B6AE5\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/CEA41203C7084B3BC12565BE0039CDBC\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/D0EEBBD933631C13C12565D800472319\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/D14910AA76E13D8A412565D4004AEEE8\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/D6420FD8CDF9C6AF412565AF0078C733\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/DCC4BF7D21C6A5D3412565B8001B743A\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/DF34B55637518E1D412565B7003E98AD\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/E8B75264E4BDA91E412565CD004B610F\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/F9267F8EF0DE1437C12565DA00556B95\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slownik-online\.pl/kopalinski/FB880FDFC5A8A9A0412565BD0035BFA4\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]songfacts\.com/detail\.php?id='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]stowarzyszeniekongreskobiet\.pl/pl-PL/text/o_nas/rada_programowa'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]swr\.de/report/presse/-/id=1197424/nid=1197424/did=2918594/1wxuzhj/index\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]swr\.de/swraktuell/rp/ludwigshafen/entscheidung-in-ludwigshafen-spd-frau-jutta-steinruck-gewinnt-ob-wahl/-/id=1652/did=20434688/nid=1652/elild0/index\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]the-athenaeum\.org/art/by_artist\.php?Artist_ID=426'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]the-athenaeum\.org/art/detail\.php?ID= +wszystkie ID'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]the-athenaeum\.org/art/list\.php?m=a&s=tu&aid='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]the-athenaeum\.org/art/list\.php?m=o&s=du&oid=1\.&f=a&fa=11380'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]the-athenaeum\.org/art/list\.php?m=o&s=du&oid=1\.&f=a&fa=3453'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]the-athenaeum\.org/art/list\.php?s=tu&m=a&aid=428&p=3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]the-athenaeum\.org/people/detail\.php?ID='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ujfeherto\.hu/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]vaulnaveys-le-bas\.fr/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]vilalba\.gal/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]vilani\.lv/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]villefort-cevennes\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]vismaskiclassics\.com/standings_total?personID=3421292'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]vysna-jedlova\.sk/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wloclawek\.info\.pl/nowosci,wiadomosci_wloclawek_i_region,1,1,tadeusz_dubicki_nowym_rektorem_p,16036\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]13grudnia81\.pl/portal/sw/wolnytekst/9499'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]13grudnia81\.pl/sw/wolnytekst/9499,dok\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]2lo\.traugutt\.net(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]academic\.oup\.com/aob/article-abstract/72/6/607/2769155'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]academic\.oup\.com/bioscience/article/53/4/421/250384'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]academic\.oup\.com/bioscience/article/57/3/227/268444'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]academic\.oup\.com/bioscience/article/62/1/67/295711'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]academic\.oup\.com/ijnp/article/15/6/825/761323'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]academic\.oup\.com/ijnp/article/18/11/pyv060/2910020]'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]academic\.oup\.com/ijnp/article/19/2/pyv076/2910032'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]academic\.oup\.com/ijnp/article/19/4/pyv124/2910122'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]academic\.oup\.com/jid/article/186/Supplement_1/S91/838964'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]actmedia\.eu/daily/cristian-diaconescu-was-appointment-as-foreign-affairs-minister/37811'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]aei\.org'),  # bot rejected on site (masti)
    re.compile('.*[\./@]age.ne\.jp/x/sas/96th_alljapan_j_nh-l2018results.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]age.ne\.jp/x/sas/96th_alljapan_j_nh-m2018results.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]age.ne\.jp/x/sas/alljapan_jump_lh_men_results20171105.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]age\.ne\.jp/x/sas'),  # bot rejected on site (masti, Snoflaxe)
    re.compile('.*[\./@]age\.ne\.jp/x/sas/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ak\.org\.pl/download/zywoty_swietych\.pdf(/.*)?'),  # well known missing doc  (masti)
    re.compile('.*[\./@]allaboutmusic\.pl'),  # bot rejected on site (masti, edk)
    re.compile('.*[\./@]allafrica\.com(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]allmusic\.com/album/r146898'),  # bot rejected on site (masti, Janusz61)
    re.compile('.*[\./@]alpha\.bn\.org\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]americanskijumping\.com/hof\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]amt-franzburg-richtenberg\.de'),  # bot rejected on site (masti)
    re.compile('.*[\./@]amt-jarmen-tutow\.de'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]annalubanska\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]anonimagroup\.org/index\.php'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]anst.gov\.ro/documente/documente/0993-1016%20National%20Federations%20-%20Ski%20-%20Biathlon%20.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]antibr\.ru'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]antiqueadvertising\.com/price-guide/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]apa\.org'),  # redirect loop (masti)
    re.compile('.*[\./@]archinea\.pl/biblioteka-uniwersytetu-warszawskiego-marek-budzynski-zbigniew-badowski/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]archinea\.pl/sad-najwyzszy-w-warszawie-marek-budzynski-zbigniew-badowski/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]archinform\.net'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]architektura\.um\.warszawa\.pl/ekofizjografia-zakola-wawerskiego'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]architektura\.um\.warszawa\.pl/ekofizjografia'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]architektura\.um\.warszawa\.pl/hydrografia'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]architektura\.um\.warszawa\.pl/plany_uchwalone_ochota]'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]architektura\.um\.warszawa\.pl/sites/default/files/files/Ekofizjografia_tekst\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]architektura\.um\.warszawa\.pl/sites/default/files/files/Zakole_Wawerskie_1_wstep_1\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]architektura\.um\.warszawa\.pl/sites/default/files/files/Zakole_Wawerskie_2\.1_geologia_0\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]architektura\.um\.warszawa\.pl/sites/default/files/files/Zakole_Wawerskie_2\.4_wody\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]architektura\.um\.warszawa\.pl/sites/default/files/files/Zakole_Wawerskie_2\.5-2\.7_gleby_roslinnosc_fauna\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]architektura\.um\.warszawa\.pl/wisla'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]archive\.fo'),  # redirect t archive.is (masti)
    re.compile('.*[\./@]archive\.is(/.*)?'),  # bot rejected on the site (masti)
    re.compile('.*[\./@]archive\.org(/.*)?'),  # bot rejected on the site (masti)
    re.compile('.*[\./@]archive\.today(/.*)?'),  # bot rejected on the site  (masti)
    re.compile('.*[\./@]arquidiocesisdesucre\.org\.bo'),  # bot rejected on site (masti)
    re.compile('.*[\./@]artrenewal\.org/pages/artist\.php?artistid=1857&page=1'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]artrenewal\.org/pages/artist\.php?artistid=305&page=1'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]artrenewal\.org/pages/artist\.php?artistid=5317&page=1'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]astronomynow\.com/news'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]atlaspsow\.online'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]atlasryb\.online/opis_ryby.php?id= (wszystkie numery po "id")'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]atlasryb\.online/opis_ryby\.php\?id='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]auerbach-erzgebirge\.de'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]automobile-catalog\.com(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]automobile-catalog\.com(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]bank\.gov\.ua/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]basketball-players\.pointafter\.com(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]bbc\.co\.uk/radio3/world/onyourstreet/dholhistory.shtml '),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]berlinonline\.de(/.*)?'),  # a de: user wants to fix them by hand and doesn't want them to be deleted, see [[de:Benutzer:BLueFiSH.as/BZ]].
    re.compile('.*[\./@]biancofiore\.pl '),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]biblioteka\.nama-hatta\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]biblioteka\.zagorz\.pl/texts/view/2'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bielskpodlaski\.pl/asp/pl_start\.asp?typ=14&sub=3&menu=15&strona=1'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]bielskpodlaski\.pl/asp/pl_start\.asp?typ=14&sub=3&menu=15&strona=1'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]bielskpodlaski\.pl/asp/pl_start\.asp?typ=14&sub=3&menu=15&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bielskpodlaski\.pl/asp/pl_start\.asp\?typ=14&sub=3&menu=15&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bielskpodlaski\.pl/asp/pl_start\.asp\?typ=14&sub=3&menu=15&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bierutow\.pl/asp/pl_start\.asp\?typ=14&menu=28&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bilkent\.edu\.tr/bilkent/bilkent-mourns-the-loss-of-janusz-szprot-former-instructor-at-the-faculty-of-music-and-performing-arts'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]biodiversitylibrary\.org'),  # bot rejected on site (masti)
    re.compile('.*[\./@]bip\.bytow\.com\.pl/m,420,solectwa\.html'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]bip\.czersk\.pl/2112\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bip\.gminaolawa\.pl/Article/get/id,14856\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bip\.gminastarytarg\.pl/archiwum/www\.bip\.gminastarytarg\.pl/userfiles/PONZ%20Stary%20Targ%20binarny_na%20lata%202016_2019_AKTUALIZACJA\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bip\.jaworzno\.pl/Article/id,18060\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]bip\.mazovia\.pl/samorzad/zarzad/uchwaly-zarzadu/uchwala,40669,15948319\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]bip\.miekinia\.pl/Article/get/id,17673\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bip\.powiatboleslawiecki\.pl/oswiadczenia'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]bip\.sobkow\.pl/\?bip=1&cid=51&bsc=N'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bip\.umwp\.wrotapodlasia\.pl/wojewodztwo/oswiadczenia/oswiad_majo/oswiadczenia_majatkowe_od_2009/oswiadczenie-majatkowe-anna-naszkiewicz-4\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]biuletyn\.net/nt-bin/_private/biskupiec/1209\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biuletyn\.net/nt-bin/_private/dubiecko/3618\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biuletyn\.net/nt-bin/_private/radomysl/8911\.pdf'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]biuletyn\.net/nt-bin/start\.asp?podmiot=kazimierzawielka/&strona=14&typ=podmenu&menu=128&id=170&str=8'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biuletyn\.net/nt-bin/start\.asp?podmiot=kazimierzawielka/&strona=14&typ=submenu&typmenu=14&id=135&str=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biuletyn\.net/nt-bin/start\.asp?podmiot=kazimierzawielka/&strona=14&typ=submenu&typmenu=14&id=228&str=5'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biuletyn\.net/nt-bin/start\.asp?podmiot=zaklikow/&strona=14&typ=podmenu&typmenu=14&menu=7&id=31&str=1'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]biuletyn\.net/nt-bin/start\.asp\?podmiot=wartkowice/&strona=14&typ=podmenu&typmenu=14&menu=34&id=34&str=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]blasonariosubalpino\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bobruisk\.hram\.by'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bodo\.kommune\.no(/.*)?'),  # bot can't handle their redirects
    re.compile('.*[\./@]boxrec\.com'),  # bot rejected on site (masti)
    re.compile('.*[\./@]bpi.co.uk/award/ - wszystkie podstrony'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bpi\.co\.uk/bpi-awards/'),  # bot rejected on site (masti)
    re.compile('.*[\./@]bpi\.co\.uk/brit-certified/'),  # bot rejected on site (masti)
    re.compile('.*[\./@]britannica\.com(/.*)?'),  # HTTP redirect loop
    re.compile('.*[\./@]brzostek\.pl/asp/pl_start\.asp?typ=14&menu=289&strona=1&sub=278#strona'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]brzostek\.pl/asp/pl_start\.asp\?typ=14&menu=289&strona=1&sub=278'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bs\.sejm\.gov\.pl'),  # slow response (masti)
    re.compile('.*[\./@]cafonline\.com/en-us/competitions/31theditionofafricancupofnationtotal,gabon2017'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/en-us/competitions/32ndeditionoftotalafricacupofnations'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/en-us/competitions/32ndeditionoftotalafricacupofnations/MatchDetails?MatchId=c8WFJCFnBOuM7mR%2feYEFkCmdq3y59q4uIqqQwH7I4XBdCUMKpVuT5gHSHovlxfKL'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/en-us/competitions/africanwomenchampionship,cameroon2016'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/en-us/competitions/allafricagamesmencongo2015'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/en-us/competitions/orangeafricacupofnations,equatorialguinea2015.aspx'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/en-us/competitions/orangeafricacupofnations,equatorialguinea2015'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/en-us/competitions/qcan2017.aspx'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/en-us/competitions/qcan2017'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/en-us/competitions/tn9thafricanwomenchampionship-namibia/news.aspx/NewsDetails?id=FiwOlHoESQWLBCXDsqhA7w%3D%3D'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/en-us/memberassociations/f%C3%A9d%C3%A9rationgabonaisedefootball'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/en-US/NewsCenter/News/NewsDetails?id=7hxNqK1bVNLnCtOlOfU1ZA%3D%3D'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/en-US/NewsCenter/News/NewsDetails?id=7Q1Us%2BTZ%2Bi03aalfg76fmw%3D%3D'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/en-US/NewsCenter/News/NewsDetails?id=8OD0yxG/y9dts7Ih8e/JqA%3D%3D'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/en-US/NewsCenter/News/NewsDetails?id=auMqtAj3SdstqcMlrNnjPQ%3D%3D'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/en-US/NewsCenter/News/NewsDetails?id=KXDfhHRQfmo848MmjaimQA%3D%3D'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/en-US/NewsCenter/News/NewsDetails?id=PEhc3UzJyA5sc0oWvJWcag%3D%3D'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/en-US/NewsCenter/News/NewsDetails?id=rHQkXwbJ/qnlkT0kYVKcMg%3D%3D'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/en-US/NewsCenter/News/NewsDetails?id=tjUi4YBkLWPBNKHA%2B7kBJg%3D%3D'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/en-US/NewsCenter/News/NewsDetails?id=vHiSLG/k2NKtlLQi4VfGCA%3D%3D'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/Portals/0/glo%20caf%202014/Draw%20Procedure%20-%20FT%20AFCON%202017%20---.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/Portals/0/glo%20caf%202014/Final%20Ranking%20AFCON%20FT,%20Gabon%202017%20FT%20FT.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/Portals/0/President/ranking%20tirage%20PDF%20English.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/Portals/0/President/ranking%20tirage%20PDF%20English.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/Portals/0/Total%20AFCON%202016/Qualifiers%20CAN%202019%20-%20matches.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\.com/Portals/0/Total%20AFCON%202016/Qualifiers%20CAN%202019%20-%20matches.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cafonline\\.com/en-us/competitions/32ndeditionoftotalafricacupofnations/MatchDetails?MatchId=c8WFJCFnBOuM7mR%2feYEFkCmdq3y59q4uIqqQwH7I4XBdCUMKpVuT5gHSHovlxfKL'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]canadianpoetry\.org/2016/06/28/widow-of-the-rock/#thewidowoftherock'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]canicattiweb\.com/2009/05/18/nuovo-cda-della-banca-san-francesco-di-canicatti/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]canmore\.org\.uk'),  # bot rejected on site (masti, Four.mg)
    re.compile('.*[\./@]canna\.pl/tuszyn/index\.php\?page=historia_kalendarium'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]cantat\.amu\.edu\.pl:80/pl/universitas-cantat-2015/konkurs-kompozytorski-na-dzielo-finalowe '),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]carfolio\.com(/.*)?'),  # site very slow timeouts  (masti)
    re.compile('.*[\./@]cars\.com/articles/lamborghini-urus-concept-at-the-beijing-motor-show-1420663120980/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]catholic-hierarchy\.org/'),  # bot rejected on site (masti)
    re.compile('.*[\./@]catholic-hierarchy\.org/bishop'),  # bot rejected on site (masti)
    re.compile('.*[\./@]catholic-hierarchy\.org/diocese'),  # bot rejected on site (masti)
    re.compile('.*[\./@]caudetedelasfuentes\.es'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]cbc\.ca/news/entertainment/vancouver-actor-nabs-csi-role-1\.680212'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]cbc\.ca/sports/olympics-winter/1956-cortina-d-ampezzo-italy-1\.864041'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cbc\.ca/world/story/2006/06/07/france-pay\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]cbssy.sy/new%20web%20site/General_census/census_2004/NH/'),  # bot rejected on site (masti)
    re.compile('.*[\./@]ceciliabartolionline\.com '),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]census\.gov(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]cev\.lu(/.*)?'),  # bot rejected on the site
    re.compile('.*[\./@]chor\.umed\.wroc\.pl '),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]chybie\.pl/asp/pl_start\.asp\?typ=14&sub=2&menu=4&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ciaaw\.org/atomic-weights\.htm'),  # bot rejected on site (masti, CiaPan)
    re.compile('.*[\./@]cieplodlatrojmiasta\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cityofshoreacres.us'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ck-czestochowa\.pl/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]climatebase\.ru/station'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]clubz\.bg/4341-kogo_prashtame_v_evropejskiq_parlament'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]cmi2\.yale\.edu/ym/archive/artists/jamespeale/artist\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]coiu\.pl/media/download/Obywatelskie_inicjatywy_ustawodawcze_Solidarnosci_1980-1990\.pdf'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]comune\.sora\.fr\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]concertorganists\.com/site2009/artist2\.aspx?id=67'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]contraloria\.gob\.pa'),  # bot rejected on site (masti)
    re.compile('.*[\./@]cotes\.es/'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]cruxgaliciae\.org'),  # bot rejected on site (masti)
    re.compile('.*[\./@]cvk\.gov\.ua/pls/vnd2006/w6p001\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]cvk\.gov\.ua/pls/vnd2007/w6p001\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]cvk\.gov\.ua/pls/vnd2012/wp001\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]cvk\.gov\.ua/pls/vnd2012/wp001\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]cvk\.gov\.ua/pls/vnd2012/wp001\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cvk\.gov\.ua/pls/vnd2014/wp001\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]cvk\.gov\.ua/pls/vnd2014/wp001\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]cvk\.gov\.ua/pls/vnd2014/wp001\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]cvk\.gov\.ua/pls/vnd2019/wp001\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]cvk\.gov\.ua/pls/vnd2019/wp001\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]cvk\.gov\.ua/pls/vp2014/wp001\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]cvk\.gov\.ua/pls/vp2014/wp001\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]cvk\.gov\.ua/pls/vp2019/wp001\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]czd\.pl/index\.php\?option=com_content&view=article&id=3131:koncert-podsumowujcy-obchody-40-lecia-ipczd&catid=27:wane&Itemid=420'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]czyczy\.pl/2012/jadrowa/litwa-energetyka-jadrowa-polegla-w-referendum'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]czyczy\.pl/2014/jadrowa/wlk-brytania-sellafield-troche-rzeczywistych-danych-kosztach-rozbiorki-elektrowni-jadrowej'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]czyczy\.pl/mapa'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]d-nb\.info(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]da\.katowice\.pl/lux-ex-silesia'),  # bot rejected on site (masti)
    re.compile('.*[\./@]daniiltrifonov\.com '),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]db\.ipc-services\.org/sdms/hira/web/competition/code/PG1994'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]db\.ipc-services\.org/sdms/hira/web/country/code'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]delibra\.bg\.polsl\.pl/Content/24007/BCPS_25841_1927_Polskie-Towarzystwo-\.pdf'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]delibra\.bg\.polsl\.pl/Content/25374/BCPS_28917_1927_Podrecznik-inzyniers\.pdf'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]delipark\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]demografia\.stat\.gov\.pl/bazademografia/Tables\.aspx'),  # bot rejected on site (masti)
    re.compile('.*[\./@]demographia\.com/db-worldua.pdf(/.*)?'),  # well known missing doc  (masti)
    re.compile('.*[\./@]deon\.pl(/.*)?'),  # bot rejected on the site  (masti)
    re.compile('.*[\./@]depatisnet\.dpma\.de(/.*)?'),  # bot rejected on the site  (masti)
    re.compile('.*[\./@]deu\.archinform\.net'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]diecezja\.rzeszow\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]diecezja\.wloclawek\.pl'),  # bot rejected on site (masti, Wiktoryn)
    re.compile('.*[\./@]dioceseofscranton\.org'),  # bot rejected on site (masti)
    re.compile('.*[\./@]discogs\.com(/.*)?'),  # bot rejected on the site  (masti)
    re.compile('.*[\./@]dlastudenta\.pl(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]dlastudenta\.pl(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]dlibra\.bg\.ajd\.czest\.pl:8080/Content/855/Kultura_fizyczna_9\.-57\.pdf'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]dlibra\.umcs\.lublin\.pl/dlibra/plain-content?id=3251'),  # bot rejected on site (masti)
    re.compile('.*[\./@]dlibra\.umcs\.lublin\.pl/dlibra/plain-content\?id=3251'),  # bot rejected on site (masti)
    re.compile('.*[\./@]doi\.org'),  # false positive (masti)
    re.compile('.*[\./@]dovidka\.com\.ua'),  # bot rejected on site (masti)
    re.compile('.*[\./@]dre\.pt/application/dir/pdf1sdip/2013/01/01901/0000200147\.pdf'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]dre\.pt/pdf2sdip/2009/02/040000000/0769107691\.pdf'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]drelow\.pl/asp/pl_start\.asp\?typ=14&sub=2&menu=20&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dsm.psychiatryonline\.org//book.aspx?bookid=22'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]duwo\.opole\.uw\.gov\.pl/WDU_O/2019/1695/akt\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dzieje\.pl(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]dzieje\.pl(/.*)?'),  # bot rejected on the site  (masti)
    re.compile('.*[\./@]dziennikustaw\.gov\.pl/DU'),  # bot rejected on site (masti)    http://dziennikustaw.gov.pl/du
    re.compile('.*[\./@]dziennikustaw\.gov\.pl/du'),  # bot rejected on site (masti)    http://dziennikustaw.gov.pl/du
    re.compile('.*[\./@]dziennikzbrojny\.pl/aktualnosci/news,1,2155,aktualnosci-z-polski,robert-kupiecki-wiceministrem-on'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]earlparkindiana\.com'),  # bot rejected on site (masti)
    re.compile('.*[\./@]eco\.gov\.az/en/67-hydrometeorology'),  # bot rejected on site (masti)
    re.compile('.*[\./@]edziennik\.poznan\.uw\.gov\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]eksploratorzy\.com\.pl/viewtopic\.php?p=153649#p153649'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]elk\.gmina\.pl/nauczmy-sie-na-pamiec-tego-kraju-gminne-obchody-2-i-3-maja'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]emmelle\.it'),  # bot rejected on site (masti)
    re.compile('.*[\./@]emporis\.com/buildings'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]emporis\.com/city'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]emporis\.com/complex/100329/world-trade-center-new-york-city-ny-usa'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]emporis\.com/statistics/tallest-buildings/country/100156/spain'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]encyklopedia\.pwn\.pl/haslo/sredniowiecze-Muzyka;4019677.html '),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]encysol\.pl'),  # wrong URLs (masti)
    re.compile('.*[\./@]entsyklopeedia\.ee'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]eosielsko\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]epolotsk\.com'),  # bot rejected on site (masti)
    re.compile('.*[\./@]erc24\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]erc24\.com/archives/16292'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]eredivisiestats\.nl/topscorers.php'),  # bot rejected on site (masti)
    re.compile('.*[\./@]esbl\.ee/biograafia'),  # bot rejected on site (masti)
    re.compile('.*[\./@]ethnologue\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]euroferroviarios\.net'),  # bot rejected on site (masti)
    re.compile('.*[\./@]europarl\.europa\.eu/meps(/.*)?'),  # links redirected  (masti)
    re.compile('.*[\./@]europe-politique\.eu'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]europe-politique\.eu/union-pour-l-europe\.htm'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]europeanvoice\.com/folder/theswedishpresidencyoftheeu/124\.aspx\?artid=65305'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]ewrc-results\.com/season/\d{4}/6-erc'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]fcgoverla\.uz\.ua/index\.php\?page=history'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fenditton\.org'),  # bot rejected on site (masti)
    re.compile('.*[\./@]file\.scirp\.org/Html'),  # bot rejected on site (masti, Wiklol)
    re.compile('.*[\./@]flutopedia\.com'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]flutopedia\.com/ '),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]formula3\.co'),  # bot rejected on site (masti)
    re.compile('.*[\./@]forumakademickie\.pl/fa/2013/02/chalasinscy'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]fra\.archinform\.net'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]frazettaartmuseum\.com'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]frontnational\.com'),  # bot rejected on site (masti)
    re.compile('.*[\./@]ft\.dk(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]galeriabwa.bydgoszcz\.pl/wystawa/milosz-matwijewicz-moj-malowany-swiat'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]galewice\.pl/asp/pliki/Gmina_Galewice/Charakterystyka_gminy_Galewice\.pdf'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gamespot\.com(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]gazeta-mlawska\.pl/aktualnosc-2186-wybory_do_rady_powiatu_mlawskiego__psl_ma_wiekszosc_\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]gazetagazeta\.com'),  # bot rejected on site (masti)
    re.compile('.*[\./@]gazetapolska\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]gcatholic\.org/dioceses/conference/018\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/country'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/country/AR-province\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/country/CN\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/country/CR-province\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/country/CU-province\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/country/IE\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/country/PY-province\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/country/SS\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/country/UA-province\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/data/rite-Rt\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/agan0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/algi0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/amad0\.htm#3222'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/amma0\.htm '),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/angr0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/angr0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/anta0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/anti0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/anto0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/antw0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/areq0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/ayac0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/bang2\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/bans0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/barq0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/barr0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/bele0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/bere0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/bogo0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/buca0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/cala1\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/caph0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/cara0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/caro1\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/cart0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/casc0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/cast0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/celj0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/chan0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/cili0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/ciud0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/coch0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/coro0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/cuma0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/curi0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/cuzc0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/cypr0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/done0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/falk0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/falk0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/funa0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/goaa0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/goaa0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/guay0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/hany0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/hels0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/honi0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/honi0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/huan0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/ibag0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/ivan0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/king1\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/koln0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/koln0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/kolo0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/kyrg0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/lase0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/lisb0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/lisb0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/ljub0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/ljub0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/loya0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/luts0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/luts0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/luts1\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/lviv1\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/lviv1\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/maca1\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/malt0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/mani0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/mani1\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/mara0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/mars2\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/mars2\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/melf0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/meri0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/moun0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/muka0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/nass0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/ndja0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/ndja0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/neth0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/neth0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/nico0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/npam0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/odes1\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/pana0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/pape0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/pari2\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/paup0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/phil1\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/phno0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/pmor0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/popa0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/port0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/priz0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/priz0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/priz0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/pvil0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/pyon0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/pyon0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/quit0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/raba0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/raro0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/rome0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/soka0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/sucr0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/suva0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/taio0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/taio0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/tara2\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/tern1\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/tong0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/tong0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/truj0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/tsin0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/tuba0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/tunj0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/utre0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/vale1\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/vill3\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/viln0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/wall0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/wanh0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/winn0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/wloc0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/yamo0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/yamo0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/yoko0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/yung3\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/zcru0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/zdom0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/zfed0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/zjos7\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/zjua1\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/zpau0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/ztia1\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/ztia3\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0136\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0895\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1090\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1091\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1093\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1094\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1095\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1108\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1109\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1110\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1111\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1113\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1686\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t2060\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/vlad0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/nunciature/nunc034\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/nunciature/org220\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/organizations/card\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-MAS\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-ST\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-X\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/cardL13-5\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/officials-B\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/officials-M\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/pope/G13\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/orders/018\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/orders/019\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/orders/053\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/orders/index\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/toronto/pr-we\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]genealogics\.org/getperson\.php'),  # bot rejected on site (masti)
    re.compile('.*[\./@]geojournals\.pgi\.gov\.pl/agp/article/view'),  # bot rejected on site (masti, Wiklol)
    re.compile('.*[\./@]geojournals\.pgi\.gov\.pl/pg/article/viewFile/16266/13503'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]geojournals\.pgi\.gov\.pl/pg/article/viewFile/16266/13503'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]geonames\.usgs\.gov(/.*)?'),  # site very slow timeouts  (masti)
    re.compile('.*[\./@]geoportal\.cuzk\.cz/mapycuzk'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]get-ligaen\.stats\.pointstreak\.com/scoreboard.html'),  # bot rejected on site (masti)
    re.compile('.*[\./@]gimnazjum\.bystrzyca\.eu'),  # bot rejected on site (masti)
    re.compile('.*[\./@]glencteresa.pl/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]gminaczarna\.pl/asp/pliki/download/statystyka_ludnosci_31-12-2017\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gminajozefow\.pl/soltysi-2/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gminajozefow\.pl/wyniki-konsultacji-spolecznych/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gminajozefow\.pl/zapraszamy-do-udzialu-w-konsultacjach-spolecznych/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gminajozefow\.pl/zawiadomienie-o-sesji-rady-gminy-2/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gminalancut\.pl/asp/pl_start\.asp\?typ=14&menu=28&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gminalancut\.pl/asp/pl_start\.asp\?typ=14&menu=475&strona=1&sub=425'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gminalancut\.pl/asp/pl_start\.asp\?typ=14&menu=87&strona=1&prywatnosc=tak'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gminalancut\.pl/asp/pl_start\.asp\?typ=14&menu=93&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gminawilkow\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]gniezno\.eu/cms/20189/nagroda_kulturalna_miasta_gniezna'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gniezno\.eu/cms/20276/miasto_w_liczbach'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gniezno\.eu/cms/20285/ambasadorzy'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gniezno\.eu/cms/20542/vii_pustachowakokoszki_'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gniezno\.eu/cms/25147/trakt_krolewski_w_gnieznie'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gniezno\.eu/katalog/2290/szkola_podstawowa__nr_1_im_zjazdu_gnieznienskiego'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gniezno\.eu/wiadomosci/1/wiadomosc/111630/projekty_22_nowych_posagow_wybrane'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gniezno\.eu/wiadomosci/1/wiadomosc/126702/trakt_krolewski_w_ostatnim_etapie_realizacji'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]goranbregovic\.co\.rs '),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]gorzowianin\.com/wiadomosc/10529-tvp-wybuduje-w-koncu-siedzibe\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gorzowianin\.com/wiadomosc/10584-zamiast-kary-dwa-nowe-linki\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gorzowianin\.com/wiadomosc/11301-powstanie-przystanek-kolejowy-gorzow-zachod-zdjecia\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gorzowianin\.com/wiadomosc/7775-radio-go-juz-ruszylo-w-rytmie-hitow-tylko-na-1017-fm\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gorzowianin\.com/wiadomosc/9607-z-centrum-na-zawarcie-to-bedzie-wielki-korek\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gorzowianin\.com/wiadomosc/9746-pociag-do-berlina-coraz-bardziej-popularny\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]granowo\.pl/asp/pl_start\.asp?typ=14&sub=14&menu=114&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]granowo\.pl/asp/pl_start\.asp?typ=14&sub=14&menu=29&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]granowo\.pl/asp/pl_start\.asp?typ=14&sub=14&menu=30&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]granowo\.pl/asp/pl_start\.asp\?typ=14&sub=14&menu=114&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]grapplerinfo\.pl/amatorski-puchar-ksw'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]greghancock\.com'),  # bot rejected on site (masti, Klima)
    re.compile('.*[\./@]grodziczno\.pl/asp/pl_start\.asp?typ=14&sub=12&menu=26&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]grodziczno\.pl/asp/pl_start\.asp\?typ=14&sub=12&menu=26&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]grodziczno\.pl/asp/pl_start\.asp\?typ=14&sub=12&menu=26&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]groupofsevenart\.com/ '),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]gryfice\.eu/gryfice\.eu-strona-archiwalna/zabytki\.html'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gsemilia\.it/index\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gso\.gbv\.de(/.*)?'),  # bot somehow can't handle their redirects
    re.compile('.*[\./@]gutenberg\.org(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]gwz.bielsko\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]halama\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]hanba1926\.pl '),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]harku\.ee'),  # bot rejected on site (masti)
    re.compile('.*[\./@]heilsbronn\.de(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]heimenkirch\.de(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]heraldry\.com\.ua/index\.php3?lang=U&context=info&id=920'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hertfordshiremercury\.co\.uk'),  # bot rejected on site (masti)
    re.compile('.*[\./@]hfhr\.org\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]hfhrpol\.waw\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]hipic\.jp '),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]historialomzy\.pl/orzel-kolno/'),  # bot rejected on site (masti)
    re.compile('.*[\./@]history\.house\.gov/Institution/Party-Divisions/Party-Divisions'),  # (masti, Ptjackyll)
    re.compile('.*[\./@]historyofpainters\.com/ralph_blakelock\.htm'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]histpol.pl.ua/ru/biblioteka/ukazatel-po-nazvaniyam?id=491'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]histpol.pl.ua/ru/gosudarstvennoe-upravlenie/sudebnye-i-pravookhranitelnye-organy-pravo?id=1759'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]histpol.pl.ua/ru/kultura/pechatnye-izdaniya/gazety?id=2366'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]horneburg\.de'),  # bot rejected on site (masti)
    re.compile('.*[\./@]horodlo\.pl/asp/pl_start\.asp\?typ=14&menu=22&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]horodlo\.pl/asp/pl_start\.asp\?typ=14&menu=24&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hrubieszow-gmina\.pl/gmina/solectwa-soltysi'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]ibdb\.com(/.*)?'),  # redirect  (masti)
    re.compile('.*[\./@]ibiblio\.org/lighthouse/tallest\.htm ten'),  # bot rejected on site (masti, Janusz61)
    re.compile('.*[\./@]iep\.utm\.edu'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]ifpicr\.cz'),  # false positive (masti)
    re.compile('.*[\./@]inafed\.gob\.mx/work/enciclopedia/EMM27tabasco/index\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]independent\.co\.uk'),  # bot rejected on site (masti, Wikipek)
    re.compile('.*[\./@]independent\.ie(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]inews\.co\.uk/news/politics/who-my-mp-won-constituency-area-general-election-2019-results-full-list-mps-1340769'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]inserbia\.info'),  # bot rejected on site (masti)
    re.compile('.*[\./@]insidehoops\.com/blog/?p='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]interlude\.hk'),  # timeouts (masti)
    re.compile('.*[\./@]ipn\.gov\.pl/pl/aktualnosci/44090,Uroczystosc-wreczenia-odznaczen-panstwowych-Warszawa-13-grudnia-2017\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]ira\.art\.pl'),  # false positive (masti)
    re.compile('.*[\./@]irishcharts\.ie/search/placement'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]itis\.gov(/.*)?'),  # bot rejected on the site
    re.compile('.*[\./@]iz\.poznan\.pl/aktualnosci/wydarzenia/nowa-rada-instytutu-zachodniego'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]iz\.poznan\.pl/aktualnosci/wydarzenia/nowa-rada-instytutu-zachodniego'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]jamanetwork\.com/journals/archneurpsyc/article-abstract/642767'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jama/fullarticle/1104423'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jama/fullarticle/198487'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jamaotolaryngology/article-abstract/2681628?widget=personalizedcontent&previousarticle=2685259'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jamapsychiatry/article-abstract/209616'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jamapsychiatry/fullarticle/2517515'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jamapsychiatry/fullarticle/2599177'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jamapsychiatry/fullarticle/2604310'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jaskinia\.pl/jaskinia_pl\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jedlnia\.biuletyn\.net/\?bip=1&cid=1155'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jerzymalecki\.pl'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]jezowe\.biuletyn\.net/?bip=1&cid=143'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]journals\.indexcopernicus\.com'),  # slow site (masti)
    re.compile('.*[\./@]journals\.indexcopernicus\.com/search/details\?id=16423'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]journals\.indexcopernicus\.com/search/details\?id=3495'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jpl\.nasa\.gov(/.*)?'),  # bot rejected on the site
    re.compile('.*[\./@]jura-pilica\.com/?rezerwat-ruskie-gory-,388'),  # bot rejected on site (masti)
    re.compile('.*[\./@]jusbrasil\.com\.br'),  # bot rejected on site (masti)
    re.compile('.*[\./@]justallstar\.com/contests/discontinued/legends'),  # bot rejected on site (masti, B-X)
    re.compile('.*[\./@]justallstar\.com/nba-all-star-game/coaches'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]juwra\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kadra\.pl(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]kameralisci\.pl/ '),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]kanalbydgoski\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]karczew\.pl/asp/pl_start\.asp?typ=14&menu=89&strona=1&sub=21&subsub=32'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]karlovaves\.sk/samosprava/starostka/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]katalog\.bip\.ipn\.gov\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]keanemusic\.com'),  # bot rejected on site (masti)
    re.compile('.*[\./@]kedzierzynkozle\.pl/portal/index\.php\?t=200&id=35673'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]kelseyserwa\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kettererkunst\.com/bio/LyonelFeininger-1871-1956\.shtml'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]kinakh\.com\.ua/bio'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]kloczew\.eurzad\.eu'),  # bot rejected on site (masti)
    re.compile('.*[\./@]koeppen-geiger\.vu-wien\.ac\.at/'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]kolejpiaskowa\.pl/index\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kopernik\.net\.pl/imprezy-i-festiwale/swietojanski-festiwal-organowy '),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]kosmonauta\.net'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]krakowskascenamuzyczna\.pl/artykuly/the-toobes-dla-nich-najwazniejsza-jest-komercja-wywiad'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]krakowskascenamuzyczna\.pl/zespoly/hanba/ '),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]krknews\.pl/zobaczyc-caly-swiat-swietna-akcja-krakowem-barany-wytepione-ruchu-wideo/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]krs-online\.com\.pl(/.*)?'),  # bot rejected on the site  (masti)
    re.compile('.*[\./@]ksi.home\.pl/archiwaprzelomu/obrazy/AP-6-1-1-42_23\.PDF'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]ksi.home\.pl/archiwaprzelomu/obrazy/AP-6-1-1-44_39\.PDF'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]ksi.home\.pl/archiwaprzelomu/obrazy/AP-6-1-1-44_40\.PDF'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]kszosiatkowka\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]kulturalna\.warszawa\.pl/kapuscinski,1,2794\.html\?locale=pl_PL'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]kulturalna\.warszawa\.pl/osoby,1,11053,0,Mindaugas_Kvietkauskas\.html\?locale=pl_PL'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]kuriergalicyjski\.com/actualnosci/polska/1487-adam-rotfeld-we-lwowie\?showall=1&limitstart='),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]kuriergalicyjski\.com/actualnosci/report/6631-nagroda-specjalna-ministra-kultury-i-dziedzictwa-narodowego-rp-dla-kuriera-galicyjskiego'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kuriergalicyjski\.com/historia/zabytki/3123-tajna-apteka'),  # bot rejected on site (masti)
    re.compile('.*[\./@]kuriergalicyjski\.com/kultura/film/7201-produkcja-kuriera-galicyjskiego-wyrozniona-na-vi-festiwalu-filmowym-emigra'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kyivpost\.com'),  # bot rejected on site (masti)
    re.compile('.*[\./@]lallameryemtennis\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lazarus\.elte\.hu/hun/digkonyv/topo/3felmeres\.htm'),  # bot rejected on site (masti)
    re.compile('.*[\./@]lazarz\.pl'),  # bot rejected on site (masti, Four.mg)
    re.compile('.*[\./@]lead\.org\.au/lanv1n2/lanv1n2-8\.html'),  # bot rejected on site (masti, CiaPan)
    re.compile('.*[\./@]leparisien\.fr'),  # bot rejected on site (masti)
    re.compile('.*[\./@]leyendablanca\.galeon\.com'),  # bot rejected on site (masti)
    re.compile('.*[\./@]liceum1\.bystrzyca\.eu'),  # bot rejected on site (masti)
    re.compile('.*[\./@]lietuvosdiena\.lrytas\.lt/aktualijos/seimo-pirmininku-isrinktas-viktoras-pranckietis-20161114033033\.htm'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]ligocka\.wydawnictwoliterackie\.pl'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]listaptakow\.eko\.uj\.edu\.pl/nonpasserines1\.html'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]listaptakow\.eko\.uj\.edu\.pl/passerines1\.html'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]listaptakow\.eko\.uj\.edu\.pl/passerines2\.html'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]lobzenica\.pl/asp/pl_start\.asp?typ=14&menu=10&strona=1&sub=139&subsub=141&subsubsub=142'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]lobzenica\.pl/asp/pl_start\.asp\?typ=14&menu=10&strona=1&sub=139&subsub=141&subsubsub=142'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lobzenica\.pl/asp/pl_start\.asp\?typ=14&menu=10&strona=1&sub=139&subsub=141&subsubsub=142'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lowell\.edu/staff-member/emeritus-astronomers'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]lrs\.lt/datos/kovo11/signatarai/www_lrs\.signataras-p_asm_id=8\.htm'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]lrs\.lt/sip/portal\.show\?p_r=119&p_k=1&p_t=167698'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]lrs\.lt/sip/portal\.show\?p_r=35299&p_k=1&p_a=498&p_asm_id=47839'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]mae\.ro'),  # bot rejected on site (masti)
    re.compile('.*[\./@]majdankrolewski\.pl/asp/pl_start\.asp\?typ=14&menu=6&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mandolinluthier\.com'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]mapy\.zabytek\.gov\.pl/nid'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mareksierocki\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]matica\.hr/knjige/autor/576/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]matriculasdelmundo\.com/gibraltar\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mazovia\.pl'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]media\.metro\.net/riding_metro/bus_overview/images/803\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]metacritic\.com'),  # false positive (masti)
    re.compile('.*[\./@]metro\.gov\.az'),  # bot rejected on site (masti)
    re.compile('.*[\./@]michal_wasilewicz\.users\.sggw\.pl/Inz_rzeczna/wyklady/Wyklad_9\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]miedzyrzecgmina\.pl/solectwa-2'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]mieszkaniegepperta\.pl/dwurnik\.php'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]military-prints\.com/caton_woodville\.htm'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]militaryarchitecture\.com'),  # bot rejected on site (masti)
    re.compile('.*[\./@]mini\.sl\.se/sv/travelplanner'),  # bot rejected on site (masti)
    re.compile('.*[\./@]minorplanetcenter\.net'),  # bot rejected on site (masti)
    re.compile('.*[\./@]minorplanetcenter\.org'),  # bot rejected on site (masti)
    re.compile('.*[\./@]mirassolandia\.sp\.gov\.br'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mks-mos\.bedzin\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mmanews\.pl'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]mogiel\.net/POL/history/polhist.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]monitorkonstytucyjny\.eu/archiwa'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]monitorpolski\.gov.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]movie-censorship\.com'),  # bot rejected on site (masti, ptjackyll)
    re.compile('.*[\./@]mpkolsztyn\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]mpu\.bydgoszcz\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]mrkoll\.se/person'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]msz\.gov\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]mtr\.com\.hk/en/customer/services/system_map.html'),  # bot rejected on site (masti)
    re.compile('.*[\./@]murki\.pl/ppm\.skaly\.Mirachowo\.acs'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]musixmatch\.com'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]muzeumgdansk\.pl/o-muzeum-gdanska/zarzad-i-rada-muzeum-gdanska'),  # bot rejected on site (masti)
    re.compile('.*[\./@]muzeumtg\.pl'),  # bot rejected on site (masti, Gabriel3)
    re.compile('.*[\./@]nasipolitici\.cz'),  # slow site (masti)
    re.compile('.*[\./@]nature\.com(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]nba\.com(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]neb\.de'),  # bot rejected on site (masti, Michozord)
    re.compile('.*[\./@]neonmuzeum\.org'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nga\.gov/collection/gallery/gg60b/gg60b-main1\.html'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]nicesport\.pl/sportyzimowe/105016/mitz-mistrzem-szwecji'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]nicesport\.pl/sportyzimowe/109610/ps-w-planicy-214-metrow-muellera'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nicesport\.pl/sportyzimowe/138514/pk-w-engelbergu-schmitt-wygrywa-serie-probna-nowy-rekord-grecji'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]nicesport\.pl/sportyzimowe/140101/fc-w-rasnovie-znamy-liste-uczestnikow'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]nicesport\.pl/sportyzimowe/142712/ps-w-oberstdorfie-seria-probna-dla-kranjca-kolejny-rekord-bulgarii'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]niezalezna\.pl'),  # false positive (masti)
    re.compile('.*[\./@]nike\.org\.pl/strona\.php\?p='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]norden\.org'),  # slow site (masti)
    re.compile('.*[\./@]norfolkchurches\.co\.uk'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]nowadekada\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]noweskalmierzyce\.pl/pl/strona/parki-krajobrazowe'),  # bot rejected on site (masti)
    re.compile('.*[\./@]nra\.lv/politika/128301-12-saeima-apstiprinata\.htm'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]nssdc\.gsfc\.nasa\.gov/nmc/spacecraft/display\.action?id='),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]nssdc\.gsfc\.nasa\.gov/nmc/spacecraft/display\.action?id='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nssdc\.gsfc\.nasa\.gov/nmc/spacecraft/display\.action\?id='),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]nssdc\.gsfc\.nasa\.gov/planetary/factsheet/earthfact\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nssdc\.gsfc\.nasa\.gov/planetary/factsheet/neptuniansatfact\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nssdc\.gsfc\.nasa\.gov/planetary/factsheet/sunfact\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nssdc\.gsfc\.nasa\.gov/planetary/gemini_4_eva\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nztop40\.co\.nz/index.php/chart/singles'),  # bot rejected on site (masti)
    re.compile('.*[\./@]obc\.opole\.pl/dlibra/publication/edition/1076?id=1076'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]obc\.opole\.pl/dlibra/publication/edition/6609?id=6609'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]obc\.opole\.pl/dlibra/publication/edition/6661?id=6661'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]obywatelenauki\.pl/2014/02/wiecej-dobrej-nauki-nowa-akcja-prof-janusza-bujnickiego'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]ochtrup\.de'),  # bot rejected on site (masti)
    re.compile('.*[\./@]old\.iupac\.org/publications/books/rbook/Red_Book_2005\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]omulecki\.com'),  # bot rejected on site (masti, Cloefor)
    re.compile('.*[\./@]operakrolewska\.pl/artysci-2 '),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]operone\.de/komponist/stefanijo\.html'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]opowiecie\.info/regionalna-mniejszosc-wiekszoscia-nowa-partia-lada-dzien/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]orzeczenia\.nsa\.gov\.pl/doc/'),  # bot rejected on site (masti)
    re.compile('.*[\./@]osnews\.pl(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]ossolineum\.pl/index\.php/aktualnosci/historia-znio/dyrektorzy-znio'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ossolineum\.pl/index\.php/aktualnosci/zbiory-lwowskie'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ostpommern\.de/kr-regenwalde.php'),  # bot rejected on site (masti)
    re.compile('.*[\./@]ostpommern\.de/kr-schlawe.php'),  # bot rejected on site (masti)
    re.compile('.*[\./@]ostrorog\.pl/asp/pl_start\.asp\?typ=14&menu=16&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ostrzeszow\.pl/asp/pl_start\.asp\?typ=14&menu=63&strona=1&prywatnosc=tak'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ostrzeszow\.pl/asp/pl_start\.asp\?typ=14&menu=89&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]other\.birge\.ru'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]otz\.de/web/zgt/politik/detail/-/specific/Fusionen-im-Altenburger-Land-Kreis-Greiz-und-Saalfeld-Rudolstadt-nun-moeglich-1908536788'),  # false positive (masti)
    re.compile('.*[\./@]oxfordmusiconline\.com\/subscriber/(/.*)?'),  # paywall  (masti)
    re.compile('.*[\./@]panstwo\.net'),  # bot rejected on site (masti)
    re.compile('.*[\./@]parafiapcim\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]parlament2015\.pkw\.gov\.pl'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]parlamentarny\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]parlamento\.pt(/.*)?'),  # slow response  (masti)
    re.compile('.*[\./@]partitodemocratico\.it/profile/stefano-bonaccini/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]pbn\.nauka\.gov\.pl/sedno-webapp/persons/969455/Tomasz_Maszczyk'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pbn\.nauka\.gov\.pl/sedno-webapp/search'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pcworld\.com'),  # bot rejected on site (masti)
    re.compile('.*[\./@]pe2014\.pkw\.gov\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]perseus\.tufts\.edu/hopper/text?doc=Perseus%3Atext%3A1999\.04\.0057%3Aentry%3De%29ruqro%2Fs'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pgeenergiaciepla\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pingzhen\.tycg\.gov\.tw'),  # bot rejected on site (masti)
    re.compile('.*[\./@]piotrdlubak\.com'),  # bot rejected on site (masti, Cloefor)
    re.compile('.*[\./@]pl.linkedin\.com/pub/sabina-nowosielska/51/308/5a7'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]planespotters\.net'),  # bot rejected on site (masti)
    re.compile('.*[\./@]plantes-botanique\.org'),  # false positive (masti)
    re.compile('.*[\./@]plymouthherald\.co\.uk'),  # bot rejected on site (masti)
    re.compile('.*[\./@]pmaa\.pl/uczestnicy-2014 '),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]pnf\.pl'),  # false positive (masti)
    re.compile('.*[\./@]pod-semaforkiem\.aplus\.pl/gt-chelmno\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]poesies\.net/henrideregnier\.html'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]pointstreak\.com'),  # false positive (masti)
    re.compile('.*[\./@]polkiwravensbruck\.pl/zofii-pocilowska-kann/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]polski-dubbing\.pl/forum/viewtopic\.php?p=12114'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]polsteam\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]polsteam\.com'),  # bot rejected on site (masti, Wiklol)
    re.compile('.*[\./@]portalpasazera\.pl/Plakaty'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]portalsamorzadowy\.pl'),  # false positive (masti)
    re.compile('.*[\./@]portugal\.gov\.pt/pt/gc21/comunicacao/noticia\?i=elenco-completo-do-novo-governo'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]postal-codes\.findthedata\.com'),  # false positive (masti)
    re.compile('.*[\./@]powiatwlodawski\.pl/c/document_library/get_file\?p_l_id=26096&folderId=34447&name=DLFE-1403\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pracownia52\.pl/www/?p=7072 '),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]prawo\.sejm\.gov\.pl/isap\.nsf/DocDetails\.xsp?id=WDU20120000124'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]president\.ee/en/estonia/decorations/bearers\.php\?id=1749'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]president\.gov\.ua(/.*)?'),  # redirect loop  (masti)
    re.compile('.*[\./@]pressto\.amu\.edu\.pl'),  # bot rejected on site (masti, Four.mg)
    re.compile('.*[\./@]proszynski\.pl/Historia-a-11-4-\.html'),  # bot rejected on site (masti, Zwistun2010)
    re.compile('.*[\./@]przegladlubartowski\.pl/informacje/6762/wybory-2014-wyniki-wyborow-wojtow-i-radnych'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]przewodnik-katolicki\.pl(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]przystanekplanszowka\.pl/2012/09/k2-wyrok.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]przystanekplanszowka\.pl/2012/10/dominion-rozdarte-krolewstwo-wyrok.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]przystanekplanszowka\.pl/2015/07/instrukcja-neuroshima-epub-mobi.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pttk.gubin.com\.pl/luz/wycieczki.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pwm\.com\.pl/pl/kompozytorzy_i_autorzy/5103/andrzej-nikodemowicz/index.html '),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]pzbs\.pl/regulaminy-stale/137-regulamin-klasyfikacyjny'),  # bot rejected on site (masti)
    re.compile('.*[\./@]pzd-srem\.pl/asp'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pzhl\.org\.pl/files/absolwencisms\.doc'),  # slow response (masti)
    re.compile('.*[\./@]raciborz\.com\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]raciborz\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]rada\.gov\.ua(/.*)?'),  # bot rejected on the site  (masti)
    re.compile('.*[\./@]radawarszawy\.um\.warszawa.pl'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]radioartnet\.net/11/2015/11/01/robert-adrian-smith-1935-2015-the-artist-and-the-media-condition'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]radomysl\.pl/asp'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]radzymin\.pl/asp/pliki/0000_Aktualnosci_2016/program_rewitalizacji_gminy_radzymin_24-04-2017\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]raimondspauls\.lv/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]rain-tree\.com'),  # bot rejected on site (masti)
    re.compile('.*[\./@]rallye-info\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rateyourmusic\.com'),  # false positive (masti)
    re.compile('.*[\./@]rcin\.org\.pl/dlibra/publication/15454'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rcin\.org\.pl/dlibra/publication/edition/2236?id=2236&from=publication'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rcin\.org\.pl/dlibra/publication/edition/2236?id=2236&from=publication'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rcin\.org\.pl/dlibra/publication/edition/2236\?id=2236&from=publication'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rcin\.org\.pl/dlibra/show-content/publication/edition/31639?id=31639'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rcin\.org\.pl/dlibra/show-content/publication/edition/31639\?id=31639'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rcin\.org\.pl/dlibra/show-content/publication/edition/5969?id=5969'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]redemptor\.pl'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]rehden\.de'),  # bot rejected on site (masti)
    re.compile('.*[\./@]rejestry-notarialne\.pl/37'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]rektor\.us\.edu\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]relacjebiograficzne\.pl'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]researchgate\.net'),  # bot rejected on site (masti)
    re.compile('.*[\./@]researchgate\.net/publication'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]ringostarr\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rj\.metropoliaztm\.pl/przystanki/tarnowskie-gory'),  # bot rejected on site (masti, Gabriel3)
    re.compile('.*[\./@]rogowo\.paluki\.pl/asp/pliki/aktualnosci/ewidencja_pomnikow_przyrody\.pdf'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]rottentomatoes\.com(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]rozklad\.zdkium\.walbrzych\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]rsssf\.com'),  # bot rejected on site (masti)
    re.compile('.*[\./@]rus\.delfi\.ee/daily/estonia/centristskaya-frakciya-v-parlamente-po-chislennosti-teper-lish-tretya\.d\?id=64222901'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]russiavolley\.com'),  # bot rejected on site (masti)
    re.compile('.*[\./@]rymanow\.pl/asp'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/berdyczow0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/bychow0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/czerkasy0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/czortkow\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/dorpat0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/halicz0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/kamieniec-litewski0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/kamieniec0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/kijow0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/lojow0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/miadziol\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/mitawa0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/polock0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/ponary\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/pop-iwan0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/rewel0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/rowne0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/ryga0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/siebiez0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/trubczewsk0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/tuhanowicze0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/winnica0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/wornie0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/zabie0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzecz-pospolita\.com/zielence0\.php3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rzeszow-news\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]rzezawa\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]saeima\.lv/lv/aktualitates/saeimas-zinas/21757-saeima-apstiprina-deputata-pilnvaras-un-atjauno-mandatu-sesiem-deputatiem'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]samborzec\.pl/asp/_pdf\.asp\?typ=14&sub=2&subsub=72&menu=87&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]samborzec\.pl/asp/pl_start\.asp\?typ=14&sub=2&subsub=72&menu=80&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]samborzec\.pl/asp/pl_start\.asp\?typ=14&sub=31&subsub=121&menu=162&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]samborzec\.pl/asp/pliki/pobierz/LPR_Samborzec_281008\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]samorzad2014\.pkw\.gov\.pl'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]sanockabibliotekacyfrowa\.pl'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]sanockabibliotekacyfrowa\.pl/dlibra/docmetadata\?id=56'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sanockabibliotekacyfrowa\.pl/publication/1000'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sanockabibliotekacyfrowa\.pl/publication/1011'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sanockabibliotekacyfrowa\.pl/publication/1015'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sanockabibliotekacyfrowa\.pl/publication/1030'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sanockabibliotekacyfrowa\.pl/publication/1031'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sanockabibliotekacyfrowa\.pl/publication/1032'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sanockabibliotekacyfrowa\.pl/publication/1033'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sanockabibliotekacyfrowa\.pl/publication/1034'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sanockabibliotekacyfrowa\.pl/publication/1047'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sanockabibliotekacyfrowa\.pl/publication/1067'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sanockabibliotekacyfrowa\.pl/publication/1070'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sanockabibliotekacyfrowa\.pl/publication/350'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sanockabibliotekacyfrowa\.pl/publication/351'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sanockabibliotekacyfrowa\.pl/publication/408'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]savatage\.com/newsavatage/discography/albums/edgeofthorns/info\.html'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]savatage\.com/newsavatage/discography/albums/edgeofthorns/info\.html'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]sbc\.org\.pl/dlibra'),  # bot rejected on site (masti)
    re.compile('.*[\./@]sbc\.org\.pl/publication/11793'),  # bot rejected on site (masti)
    re.compile('.*[\./@]scholar\.google\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]science\.ksc\.nasa\.gov(/.*)?'),  # very slow response resulting in bot error
    re.compile('.*[\./@]sdlp\.ie'),  # bot rejected on site (masti)
    re.compile('.*[\./@]senat\.ro'),  # slow site (masti)
    re.compile('.*[\./@]senate\.gov'),  # bot rejected on site (masti)
    re.compile('.*[\./@]seriea\.pl(/.*)?'),  # slow response  (masti)
    re.compile('.*[\./@]setkab\.go\.id/11-duta-besar-negara-sahabat-serahkan-surat-kepercayaan-kepada-presiden-jokowi'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]shantymen\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]shmetro\.com(/.*)?'),  # slow response  (masti)
    re.compile('.*[\./@]sittensen\.de'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sjdz\.jlu\.edu\.cn/CN/abstract/abstract8427\.shtml'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sjdz\.jlu\.edu\.cn/CN/abstract/abstract8427\.shtml'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sjp\.pwn\.pl/zasady/Transliteracja-i-transkrypcja-wspolczesnego-alfabetu-macedonskiego;629733\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]skisprungschanzen\.com'),  # bot rejected on site (masti)
    re.compile('.*[\./@]sl\.se/ficktid/vinter/h22ny\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sledzinska-katarasinska\.pl/o-mnie'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]snooker\.org/res/index\.asp?event=281 -> http://www\.snooker\.org/res/index\.asp?event=281'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sns\.org\.rs'),  # bot rejected on site (masti)
    re.compile('.*[\./@]soccerbase\.com'),  # bot rejected on site (masti)
    re.compile('.*[\./@]sosnowka\.pl/asp/pl_start\.asp\?typ=14&menu=11&strona=1&sub=10'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sothebys\.com/es/auctions/ecatalogue/2014/medieval-renaissance-manuscripts-l14241/lot\.32\.html'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]speedwayresults\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]spoilertv\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]spsarnow\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]sputniknews\.com/society/201803251062883119-israel-sculptor-death-meisler'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ssweb\.seap\.minhap\.es'),  # slow site (masti)
    re.compile('.*[\./@]stadtlohn\.de'),  # bot rejected on site (masti)
    re.compile('.*[\./@]stare-babice\.pl/sites/default/files/attachment/ludnosc_w_podziale_na_miejscowosci_2010_2015.pdf'),  # bot rejected on site (masti)
    re.compile('.*[\./@]stat\.gov\.pl/broker/access'),  # bot rejected on site (masti, Stok)
    re.compile('.*[\./@]stat\.gov\.pl/cps/rde/xbcr/gus/LU_ludnosc_stan_struktura_31_12_2012\.pdf'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]stat\.gov\.pl/download/gfx/portalinformacyjny/pl/defaultaktualnosci/5488/2/15/1/szkoly_wyzsze_i_ich_finanse_w_2018\.pdf'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]stat\.gov\.pl/download/gfx/portalinformacyjny/pl/defaultaktualnosci/5670/21/1/1/1_miejscowosci_ludnosc_nsp2011\.xlsx'),  # bot rejected on site (masti)
    re.compile('.*[\./@]stat\.gov\.pl/obszary-tematyczne/ludnosc/ludnosc/ludnosc-stan-i-struktura-ludnosci-oraz-ruch-naturalny-w-przekroju-terytorialnym-stan-w-dniu-31-12-2019,6,27\.html'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]stat\.gov\.pl/obszary-tematyczne/ludnosc/ludnosc/ludnosc-stan-i-struktura-w-przekroju-terytorialnym-stan-w-dniu-30-06-2019,6,26\.html'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]stat\.gov\.pl/obszary-tematyczne/ludnosc/ludnosc/powierzchnia-i-ludnosc-w-przekroju-terytorialnym-w-2019-roku,7,16\.html'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]statistics\.gr/documents/20181/1210503/resident_population_census2011rev\.xls/956f8949-513b-45b3-8c02-74f5e8ff0230'),  # file exists (masti)
    re.compile('.*[\./@]stratigraphy\.org(/.*)?'),  # site very slow timeouts  (masti)
    re.compile('.*[\./@]structurae\.net'),  # bot rejected on site (masti, Four.mg)
    re.compile('.*[\./@]suraz\.pl/asp/pl_start\.asp?typ=14&sub=7&menu=45&strona=1'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]svencionys\.lt/index.php?3819840680'),  # bot rejected on site (masti)
    re.compile('.*[\./@]swaid\.stat\.gov\.pl/Dashboards/Dane%20dla%20jednostki%20podzia%C5%82u%20terytorialnego\.aspx'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]swiatowedziedzictwo\.nid\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]switzenhausen\.eu'),  # bot rejected on site (masti)
    re.compile('.*[\./@]sztetl\.org\.pl/pl/miejscowosci/l/497-lodz/112-synagogi-domy-modlitwy-i-inne/86846-szczegolowy-spis-domow-modlitwy-w-lodzi'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]szukajwarchiwach\.pl'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]tablicerejestracyjne\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]teamusa\.org/USA-Wrestling/Features/2019/April/18/Coon-Nowry-Perkins-win-gold-at-Pan-Am-Championships-in-Buenos-Aires'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]teamusa\.org/USA-Wrestling/Team-USA/World-Team-History'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ted\.europa\.eu(/.*)?'),  # bot rejected on the site  (masti)
    re.compile('.*[\./@]tel-aviv\.millenium\.org\.il'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tenisista\.com\.pl/ciekawostki-tenisowe\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tenisista\.com\.pl/ewolucja-sprzetu-tenisowego\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tenisista\.com\.pl/historia-tenisa\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tenisista\.com\.pl/suzanne-lenglen\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tenisista\.com\.pl/zasady-gry-w-tenisa\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]the-athenaeum\.org'),  # bot rejected on site (masti)
    re.compile('.*[\./@]the-athenaeum\.org/art/by_artist\.php?id=421'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]the-athenaeum\.org/art/list\.php?m=a&s=du&aid=1722'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]the-athenaeum\.org/art/list\.php?m=a&s=du&aid=551'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]the-athenaeum\.org/art/list\.php?m=a&s=du&aid=586'),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]the-sports\.org(/.*)?'),  # slow response  (masti)
    re.compile('.*[\./@]theplantlist\.org'),  # bot rejected on site (masti, Wiklol)
    re.compile('.*[\./@]tiger\.edu\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]tokarczuk\.wydawnictwoliterackie\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]torun\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]transport\.gov\.mg'),  # bot rejected on site (masti)
    re.compile('.*[\./@]trm\.md'),  # bot rejected on site (masti)
    re.compile('.*[\./@]trybunal\.gov\.pl/o-trybunale/sedziowie-trybunalu-konstytucyjnego/art/2440-slawomira-wronkowska-jaskiewicz/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]trzebiatow\.pl/asp/pl_start\.asp\?typ=14&sub=5&menu=49&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]trzebiatow\.pl/asp/pl_start\.asp\?typ=14&sub=9&menu=177&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]trzebiatow\.pl/asp/pl_start\.asp\?typ=14&sub=9&menu=63&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tulospalvelu\.vaalit\.fi'),  # slow site (masti)
    re.compile('.*[\./@]tygodnikpowszechny\.pl(/.*)?'),  # bot redirect loop  (masti)
    re.compile('.*[\./@]udlaspalmas\.es/jugador/alvaro-lemos'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]udlaspalmas\.es/jugador/aythami-artiles-1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]udlaspalmas\.es/jugador/de-la-bella'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]udlaspalmas\.es/jugador/raul-fernandez'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]udlaspalmas\.es/jugador/ruiz-de-galarreta'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]udlaspalmas\.es/noticias/noticia/el-presidente-confirma-el-pago-a-boca-por-araujo]'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]udlaspalmas\.es/noticias/noticia/marko-livaja-cedido-al-aek-atenas'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ugcycow\.pl/asp/pl_start\.asp\?typ=13&sub=5&menu=6&artykul=2872&akcja=artykul'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ugcycow\.pl/asp/pl_start\.asp\?typ=14&sub=19&menu=35&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ugsiedliszcze\.bip\.e-zeto\.eu/index\.php?type%3D4%26name%3Dbt46%26func%3Dselectsite%26value%255B0%255D%3Dmnu11%26value%255B1%255D%3D6'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]um\.warszawa\.pl/aktualnosci/kolekcja-ludwiga-zimmerera-juz-w-muzeum-etnograficznym'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]um\.zabrze\.pl/mieszkancy/miasto/historia/wladze-lokalne'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]um\.zabrze\.pl/mieszkancy/miasto/historia/wladze-lokalne'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]uniaeuropejska.org/antysemickie-hasa-w-wgierskim-parlamencie/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]uniaeuropejska.org/marek-safjan-ponownie-sedzia-tsue/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]uniwersytetradom\.pl/art/display_article\.php'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]upjp2\.edu\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]usnews\.com'),  # bot rejected on site (masti)
    re.compile('.*[\./@]usopen\.org/en_US/visit/history/mschamps\.html'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]usopen\.org/index\.html'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]usosweb\.amu\.edu\.pl(/.*)?'),  # HTTP redirect loop on site  (masti)
    re.compile('.*[\./@]usps\.com'),  # bot rejected on site (masti)
    re.compile('.*[\./@]villaeva\.pl/villa-eva/historia'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]villargordodelcabriel\.es'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]vled\.co\.il'),  # bot rejected on site (masti)
    re.compile('.*[\./@]vreme\.com/cms/view\.php\?id=346508'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]waganiec\.biuletyn\.net/?bip=2&cid=37&id=36'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wawer\.warszawa\.pl/pl/kurier-wawerski'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wawer\.warszawa\.pl/pl/news/mapa-wawerskich-szlakow-rowerowych'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wawer\.warszawa\.pl/pl/news/otwarcie-szlaku-rowerowego-mtb'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wawer\.warszawa\.pl/sites/default/files/field/attachments/LAS%20PROGNOZA%20%C5%9ARODOWISKOWA%2004%202014\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wawer\.warszawa\.pl/sites/default/files/field/attachments/Mapki%20szlak%C3%B3w\.jpg'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wawer\.warszawa\.pl/sites/default/files/field/attachments/Opisy%20tras%20rowerowych\.doc]'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wawer\.warszawa\.pl/sites/default/files/field/attachments/Wawer%20szlaki%201x1%2C4\.jpg'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wawer\.warszawa\.pl/sites/default/files/kw_nr_05_2016_n_3\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wawer\.warszawa\.pl/sites/default/files/nr_15_2012\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wawer\.warszawa\.pl/sites/default/files/nr_20_2012\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wawer\.warszawa\.pl/sites/default/files/nr_5_2012\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wawer\.warszawa\.pl/sites/default/files/nr_6_2011\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wawer\.warszawa\.pl/sites/default/files/nr_7_2012\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wbc\.macbre\.net'),  # bot rejected on site (masti, Four.mg)
    re.compile('.*[\./@]wcsp\.science\.kew\.org'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wcsp\.science\.kew\.org/prepareChecklist\.do?checklist=selected_families%40%40222100820181252697'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]web\.archive\.org/web/20090805065419/http://www\.the-afc\.com/en/afc-u19-womens-championship-2009-schedule-a-results'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]website\.musikhochschule-muenchen\.de/de/index.php?option=com_content&task=view&id=636 '),  # bot rejected on site (masti, Fiszka)
    re.compile('.*[\./@]widawa\.pl/asp/pl_start\.asp?typ=13&menu=1&artykul=231&akcja=artykul'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]widawa\.pl/asp/pl_start\.asp?typ=13&menu=1&artykul=231&akcja=artykul'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]widawa\.pl/asp/pl_start\.asp\?typ=13&menu=1&artykul=231&akcja=artykul'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wielcy\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]wielkopolanie\.zhr\.pl/rozkazy/L4_2010\.pdf'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]wiki-de\.genealogy\.net/GOV:AUSERKJO72RN'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wiki-de\.genealogy\.net/GOV:KLEHOFJO82RV'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wiki-de\.genealogy\.net/GOV:KRIIELJO72QK'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wiki-de\.genealogy\.net/GOV:MEIITZKO03AH'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wiki-de\.genealogy\.net/GOV:VORSENJO72RM]'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wiki-de\.genealogy\.net/Gutt_%28Familienname%29'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wrecksite\.eu'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wupperverband\.de'),  # bot rejected on site (masti, Four.mg)
    re.compile('.*[\./@]bipraciborz\.pl/bip/dokumenty-akcja-wyszukaj-idkategorii-39906'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]ebelchatow\.pl/content/nie-plus-plus-polska-razem'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]europeanvoice\.com/folder/theswedishpresidencyoftheeu/124.aspx?artid=65305'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]federnuoto\.it/federazione/federazione-news/item/40079-barelli-eletto-alla-camera.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]forumakademickie\.pl/aktualnosci/2011/1/5/765/jak-ck-wybierano/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]forumakademickie\.pl/fa/2015/07-08/kronika-wydarzen/odzew-w-sprawie-bez-odzewu/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]gopsusports.com/sports/m-fenc/spec-rel/032402aaa.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]independent\.co\.uk/news/world/europe/mariano-rajoy-latest-spain-election-pedro-sanchez-premier-basque-national-party-a8378101.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]independent\.co\.uk/news/world/europe/mariano-rajoy-latest-spain-election-pedro-sanchez-premier-basque-national-party-a8378101.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]independent\.co\.uk/news/world/europe/silvio-berlusconis-heir-angelino-alfano-forms-new-party-in-italy-8943520.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]independent\.co\.uk/opinion/commentators/denis-macshane-britain-can-help-to-shape-a-new-europe-481214.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]leggiperme.it/?p=495'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]matica\.hr/knjige/autor/369/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]mojabibliotekamazurska\.pl/biblioteka/ukazaly_sie_02_03.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]msp\.gov\.pl/pl/media/aktualnosci/31579,Zmiany-w-kierownictwie-MSP.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]ordynacka\.pl/2017/04/22/zakonczyl-sie-vii-kongres-ordynackiej/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]pip\.gov\.pl/pl/wiadomosci/69784,roman-giedrojc-glownym-inspektorem-pracy.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]pism\.pl/publications/bulletin/no-55-905'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]ptp\.org\.pl/modules.php?name=News&file=article&sid=25'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]segodnya\.ua/politics/pnews/olga-bogomolec-sobiraetsya-ballotirovatsya-v-prezidenty-ukrainy-505598.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]wloclawek\.info.pl/nowosci,wiadomosci_wloclawek_i_region,1,1,tadeusz_dubicki_nowym_rektorem_p,16036.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]bielecki\.pl'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]businesseurope\.eu/history-organisation'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]faktyoswiecim\.pl/fakty/aktualnosci/15778-oswiecim-to-pewne-janusz-chwierut-wygral-w-pierwszej-turze'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]fiedler\.pl'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]fiedler\.pl/sub,pl,arkady-radoslaw-fiedler\.html'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]forumakademickie\.pl/fa/2014/04/kurczewscy'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]forumakademickie\.pl/fa/2015/06/jak-stracic-prestiz'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]frithjof-schmidt\.de'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]ft\.dk/Folketinget/findMedlem(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]gcatholic\.org/churches/'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/conference/'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/diocese/'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former//t1946\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/bagn0\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/iles0\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/micr0\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0036\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0037\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0038\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0039\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0040\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0041\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0042\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0045\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0047\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0049\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0050\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0059\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0060\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0061\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0150\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0156\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0164\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0166\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0167\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0170\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0171\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0174\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0181\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0187\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0212\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0216\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0219\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0221\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0229\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0239\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0241\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0248\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0255\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0256\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0267\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0270\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0273\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0279\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0283\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0284\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0287\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0291\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0296\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0305\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0308\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0311\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0312\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0315\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0316\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0317\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0318\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0320\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0323\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0324\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0328\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0338\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0340\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0341\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0344\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0351\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0352\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0355\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0356\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0406\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0476\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0666\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0670\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0672\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0682\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0688\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0805\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0806\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0869\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0872\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0874\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0875\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0876\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0878\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0879\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0880\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0881\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0885\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0887\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0888\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0892\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0896\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0899\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0901\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0902\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0906\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0907\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0909\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0943\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t0944\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1040\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1302\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1418\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1419\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1425\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1428\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1433\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1434\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1435\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1437\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1438\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1439\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1441\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1445\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1447\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1449\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1450\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1451\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1452\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1453\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1454\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1577\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1578\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1585\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1589\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1597\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1602\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1605\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1606\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1609\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1617\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1622\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1623\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1627\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1632\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1633\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1635\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1641\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1644\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1647\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1651\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1652\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1679\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1682\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1683\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1690\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1691\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1693\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1694\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1696\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1703\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1704\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1706\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1710\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1712\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1716\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1718\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1719\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1723\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1724\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1725\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1727\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1733\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1738\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1799\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1826\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1831\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1833\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1835\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1836\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1838\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1839\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1893\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1895\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1896\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1897\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1900\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1901\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1902\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1903\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1904\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1905\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1906\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1907\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1908\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1910\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1911\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1923\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1926\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1928\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1931\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1934\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1935\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1936\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1937\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1938\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1940\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1941\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1943\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1945\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1947\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1949\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1951\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1952\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1956\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1957\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1958\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1959\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1960\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1962\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1964\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1965\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1966\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1967\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1969\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1970\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1971\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1974\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1975\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1976\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1977\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1978\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1979\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1980\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1981\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1984\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t1987\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t2022\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t2063\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t2065\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t2075\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t3381\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t3383\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/t3398\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/nunciature/nunc017\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/nunciature/nunc076\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/nunciature/org202\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/nunciature/org204\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/nunciature/org207\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/nunciature/org210\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/romancuria/'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/cardinals-title-c2\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/cardinals-title-c3\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-BAR\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-BR\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-BU\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-CR\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-DEC\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-DEM\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-DI\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-FI\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-GL\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-GR\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-H\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-K\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-KI\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-KR\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-L\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-LO\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-N\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-O\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-P\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-PE\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-PF\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-PL\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-PR\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-RO\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-SH\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-SK\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-SU\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-TI\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-VONH\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-VONS\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-W\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-WI\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-X\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops-Z\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/card'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/officials-C\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/officials-S\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/orders/006\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/orders/009\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/orders/040\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gcatholic\.org/orders/237\.htm'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]ibdb\.com(/.*)?'),  #site automatically redirectong (masti)
    re.compile('.*[\./@]ireneuszras\.pl'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]jacektomczak\.pl'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]jadwigarotnicka\.pl'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]jerzymaslowski\.pl'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]jerzymaslowski\.pl/wp-content/uploads/2009/02/jmm5\.jpg'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]kedzierzynkozle\.pl/portal/index\.php?t=200&id=35673'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]kulanu-party\.co\.il/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kulturalna\.warszawa\.pl/nagroda-literacka,1,10564\.html?locale=pl_PL'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]lincolnshire\.org/lincolnshire-sausage/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]maltauncovered\.com/valletta-capital-city/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mfa\.gov\.pl/pl/aktualnosci/wiadomosci/nominacje_dla_nowych_ambasadorow_rp'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]mojamongolia\.com/moj-zyciorys'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]muzeumsg\.pl/images/Publikacje_1918_1939/70\.J\.Prochwicz\.pdf(/.*)?'),  # false postive  (masti)
    re.compile('.*[\./@]nba-allstar\.com/legends/rosters\.htm '),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]netcarshow\.com/ford/2017-fiesta/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]netcarshow\.com/opel/2018-crossland_x/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]netcarshow\.com/volkswagen/2018-tiguan_allspace/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]newyorktheatreguide\.com/news/jl09/bacchae555183\.htm'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]odg\.mi\.it/node/30222'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]pcworld\.com/article/253200/googles_project_glass_teases_augmented_reality_glasses\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]prowincja\.com\.pl/autorzy/Jerzy-Wcisla,25'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]terzobinario\.it/elezioni-alessandro-battilocchio-eletto-alla-camera/131593'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]tubawyszkowa\.pl/aktualnosci/czytaj/4863/Kandydaci-KWW-Kukiz-15-pod-szczesliwa-siodemka'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]uj\.edu\.pl/documents/10172/24c02901-aecc-4d79-b067-6ab2fa71fb00'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]uniaeuropejska\.org/nominacje-do-nagrod-mep-awards'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]wrp\.pl/prof-dr-hab-eberhard-makosz-1932-2018'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]zbigniewkonwinski\.pl'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]www3.put.poznan\.pl/jubileusz/honoriscausa'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wybory\.gov\.pl/pe2019'),  # temporary (masti, Elfhelm)
    re.compile('.*[\./@]wysokosc\.mapa\.info\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]yg-life\.com/archives'),  # bot rejected on site (masti)
    re.compile('.*[\./@]ygfamily\.com'),  # bot rejected on site (masti, Camomilla)
    re.compile('.*[\./@]yivo\.org/yiddishland-topo'),  # Err 201, bot rejected on site (masti, Maitake)
    re.compile('.*[\./@]youtube\.com/(/.*)?'),  # bot rejected on site  (masti)
    re.compile('.*[\./@]zagnansk\.pl/asp/pl_start\.asp\?typ=14&menu=174'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zagraevsky\.com/democracy_engl.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zagraevsky\.com/sloboda_book1.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zagraevsky\.com/vsmz11.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zagraevsky\.com/vsmz2.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zagraevsky\.com/vsmz5.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zagraevsky\.com/vsmz7.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zalesie\.pl/asp/pl_start\.asp\?typ=14&menu=31&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zaleszany\.pl/asp/pl_start\.asp\?typ=14&menu=239&strona=1&sub=6'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zbigniewloskot\.pl'),  # bot rejected on site (masti, Ysska)
    re.compile('.*[\./@]zbp\.pl/wydarzenia/archiwum/wydarzenia/2016/marzec/medale-kopernika-dla-srodowiska-naukowego'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]zdw\.lublin\.pl'),  # bot rejected on site (masti)
    re.compile('.*[\./@]zeglarski.info/artykuly/zmarl-kapitan-zygrfyd-zyga-perlicki/'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]zgryglas\.pl/o-mnie'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]zso\.bystrzyca\.eu'),  # bot rejected on site (masti)
    re.compile('.*[\./@]zulawy\.infopl\.info/index\.php/pndg/gstegna/drewnica'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zwierzyniec\.e-biuletyn\.pl/index\.php?id=131'),  # bot rejected on site (masti, szoltys)
    re.compile('\.*[\./@]assaeroporti\.com/statistiche'),  # bot rejected on site (masti, szoltys)
    re.compile('\.*[\./@]en\.jerusalem-patriarchate\.info/apostolic-succession'),  # bot rejected on site (masti, szoltys)
    re.compile('\.*[\./@]geonames\.nga\.mil/gns/html'),  # bot rejected on site (masti, szoltys)
    re.compile('\.*[\./@]iwf.net/results/athletes/?athlete=artykov-izzat-1993-09-08&id=2770'),  # bot rejected on site (masti, BrakPomysłuNaNazwę)
    re.compile('\.*[\./@]lizakowski-photo\.art\.pl'),  # bot rejected on site (masti, Cloefor)
    re.compile('\.*[\./@]s2\.fbcdn\.pl/5/clubs/40695/data/docs/pomorzanka-statystyka-1955-2011\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('\.*[\./@]stat\.gov\.pl/spisy-powszechne/nsp-2011/nsp-2011-wyniki/ludnosc-w-miejscowosciach-statystycznych-wedlug-ekonomicznych-grup-wieku-stan-w-dniu-31-03-2011-r-,21,1\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('\.*[\./@]www\.biuletyn\.net/nt-bin/start\.asp\\?podmiot=zaklikow/&strona=14&typ=podmenu&typmenu=14&menu=7&id=31&str=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kpbc\.umk\.pl'),  # bot rejected on site (masti, Four.mg)
    re.compile('.*[\./@]friedensfahrt-museum\.de'),  # bot rejected on site (masti, Four.mg)
    re.compile('.*[\./@]opera\.lv'),  # bot rejected on site (masti, Four.mg)
    re.compile('.*[\./@]museum\.gov\.rw'),  # bot rejected on site (masti, Four.mg)
    re.compile('.*[\./@]reh4mat\.com/cbr/historia-zaopatrzenia-ortotycznego'),  # bot rejected on site (masti, Four.mg)
    re.compile('.*[\./@]structurae\.net/de'),  # bot rejected on site (masti, Four.mg)
    re.compile('.*[\./@]thames\.me\.uk/s00820\.htm'),  # bot rejected on site (masti, Four.mg)
    re.compile('.*[\./@]forecki\.pl'),  # bot rejected on site (masti, Cloefor)
    re.compile('.*[\./@]olimpijski\.pl'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]globalsecurity\.org/military/systems'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]e-dziennik\.mswia\.gov\.pl/DUM_MSW'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]sport24\.ee'),  # bot rejected on site (masti, Barcival)
    re.compile('.*[\./@]biodiversitylibrary\.org'),  # bot rejected on site (masti, Pikador)
    re.compile('.*[\./@]przemyska\.pl'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]strata\.geology\.wisc\.edu/jack/showgenera.php\?taxon=231&rank=class'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]strata\.geology\.wisc\.edu / jack / showgenera.php\?taxon=307&rank=class'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]diecezja\.opole\.pl/index\.php/parafie/alfabetycznie'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]gugik\.gov\.pl'),  # bot rejected on site (masti, Stok)
    re.compile('.*[\./@]eu-football\.info'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]stadiumguide\.com'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]esbl\.ee/biograafia'),  # bot rejected on site (masti, Szoltys)
    re.compile('.*[\./@]e-dziennik\.msw\.gov\.pl'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]rtvslo\.si'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]elperiodico\.com'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]ouest-france\.fr'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]cyprus-mail\.com'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]lrs\.lt'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]olsztyn24\.com'),  # bot rejected on site (masti, Elfhelm)
    re.compile('.*[\./@]sciencedaily\.com/releases'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]artonline\.ru/encyclopedia'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]geojournals\.pgi\.gov\.pl/pg/article'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bip\.wejherowo\.pl/strony/4054\.dhtml'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bip\.wejherowo\.pl/strony/6343\.dhtml'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bip\.wejherowo\.pl/strony/8154\.dhtml'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slovak-republic\.org/history/communism'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slovak-republic\.org/citizenship'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slovak-republic\.org/food/drinks'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]slovak-republic\.org/symbols/honours'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]osiek\.gda\.pl/asp/pl_start.asp?typ=14&sub=6&menu=46&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hannapakarinen\.fi'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rermegacorp\.com/mm5/merchant\.mvc?Store_Code=RM'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zabierzow\.org\.pl/wp-content/uploads/2013/05/monografia\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]diecezja\.opole\.pl/index.php/parafie/wg-dekanatow'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dsb\.dk'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tygodnikpowszechny\.pl/najwazniejsi-28374'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tygodnikpowszechny\.pl/aniol-w-spodnicy-26201'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tygodnikpowszechny\.pl/cala-wladza-w-rece-rodzicow-15583'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tygodnikpowszechny\.pl/ekonomia-ksiedza-stryczka-32929'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tygodnikpowszechny\.pl/homofobia-zabija-29013'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tygodnikpowszechny\.pl/kultura-w-skrocie-30900'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tygodnikpowszechny\.pl/mala-rzesza-w-sercu-rosji-16518'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tygodnikpowszechny\.pl/polski-maleter-129549'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tygodnikpowszechny\.pl/redakcja-25447'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tygodnikpowszechny\.pl/sad-nad-kapuscinskim-28527'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tygodnikpowszechny\.pl/sceny-z-zycia-plciownika-28362'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tygodnikpowszechny\.pl/wiemy-bo-to-przeszlismy-29737'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tygodnikpowszechny\.pl/wyprawa-nie-wyprawka-24942'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rcin\.org\.pl/dlibra/show-content/publication/edition/5969?id=5969'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]amt-lauenburgische-seen\.de/index.php/startseite.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kremlincup\.ru'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tswisla\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]amt-eider\.de'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kakamega\.go\.ke'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mandera\.go\.ke'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/nunciature'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/bishops'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data/officials'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/orders'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fmg\.ac/Projects/MedLands'),  # bot rejected on site (masti, Ptjackyll)
    re.compile('.*[\./@]academic\.oup\.com/sysbio/article/61/3/490/1674014'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jstor\.org/stable/25065646'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jstor\.org/stable/10.1086/432631'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jstor\.org/stable/10.1086/521066'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]skiinghistory\.org/history/women%E2%80%99s-ski-jumping-takes-aim-winter-olympics'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]academic\.oup\.com'),   # bot rejected on site (masti, Salicyna)
    re.compile('.*[\./@]na-svyazi\.ru'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ethnologue\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]metroweb\.cz/metro'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lib\.cas\.cz/space\.40'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]globalsecurity\.org/military/world'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fis-ski\.com/DB/freestyle-skiing/cup-standings\.html?'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]eventselection=&place=&sectorcode=FS'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jstor\.org/stable/1899474'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]allseanpaul\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]paintedbird\.net'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nowaruda\.info/136\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]paralympic\.org/rio-2016'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]uipmworld\.org/event/olympic-games'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dpsu\.gov\.ua'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nv\.ua/ukr/ukraine/events/jevstratij-zorja-pered-objednavchim-soborom-upts-kp-ta-uapts-oholosili-samorozpusk-2513666\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nv\.ua/ukraine/events/umer-znamenityj-ukrainskij-khudozhnik-multiplikator-david-cherkasskij-2503665\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nv\.ua/ukraine/events/v-ofise-poltavskoy-yacheyki-opzzh-proizoshel-vzryv-novosti-ukrainy-50097850\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nv\.ua/ukraine/politics/rabinovich-parad-9-maya-v-moskve-video-novosti-ukrainy-50070656\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hamodia\.com/2020/05/14/minister-rafi-peretz-leaves-yamina-join-new-government'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hamodia\.com/2018/12/16/knesset-advances-bill-legalize-outposts-attorney-generals-opposition'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hamodia\.com/columns/day-history-14-iyarmay-10'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hamodia\.com/columns/day-history-26-tamuzaugust-1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]geojournals\.pgi\.gov\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]spaceflight101\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]diecezja\.siedlce\.pl/parafie'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]globalsecurity\.org/wmd'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]environment\.gov\.au/cgi-bin/sprat/public/publicspecies.pl?taxon_id='),    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]environment\.gov\.au/cgi-bin/ahdb/search.pl?mode=place_detail;place_id='),    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biuletyn\.net/nt-bin/start.asp\?podmiot='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]historicspeedway\.co\.nz'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]diseasesdatabase\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fmg\.ac/Projects/MedLands'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sciencedaily\.com/releases'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sztetl\.org\.pl/pl/biogramy'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]genius\.com/artists'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nssdc\.gsfc\.nas\.gov/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ilikezaglebie\.pl/korona-gor-sosnowca/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linux\.gda\.pl/archiwum/tlug/2000-10/001701\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jaroslawkaczynski\.info/poparcie/Warszawski_spoleczny_komitet_poparcia'),    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gopr\.pl/aktualnosci/zmarl-janusz-siematkowski'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]paralympic\.org/oksana-masters'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]galeriafundamenty\.pl/linia-kolejowa-turza-wielka-samborowo/'),    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wuwr\.pl/plit/article/view/3336'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cybinka\.pl/asp/pl_start\.asp\?typ=14&sub=1&menu=7&strona=1'),    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cybinka\.pl/asp/pl_start\.asp\?typ=14&sub=20&menu=7&strona=1'),    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jstor\.org/stable/106542'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jstor\.org/stable/106717'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jstor\.org/stable/106823'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rcin\.org\.pl/dlibra/publication/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]demo\.istat\.it/pop\d{4}/index1_e\.html'),  # bot rejected on site (masti)
    re.compile('.*[\./@]swimrankings\.net/index\.php\?page=athleteDetail&athleteId='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]results\.gc2018\.com/en'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bpi\.co\.uk/award'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wpk\.katowice\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jstor\.org/stable'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]departments\.bucknell\.edu/biology/resources/msw3/browse\.asp\?id='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]enotes\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]repository\.si\.edu/handle'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]repository\.si\.edu/bitstream/handle'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]obrzycko\.pl/asp/pl_start\.asp\?typ=14'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]digi\.ub\.uni-heidelberg\.de/diglit'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tourism\.cz/encyklopedie'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]genius\.com/Katy-perry-swish-swish-lyrics'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sana\.sy/en/\?page_id=1900'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sana\.sy/en/\?p=130030'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sana\.sy/en/\?p=178438'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/world/asia/unified-korea-athletes-asian-games-opening-ceremony-north-south-kim-jong-un-a8497521\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biodiversitylibrary\.org/page/39462291#page/37/mode/1up'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ivpp\.cas\.cn/cbw/gjzdwxb/xbwzxz/201202/t20120209_3438263\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pozeska-biskupija\.hr/2017/08/03/arhidakonati-i-dekanati-2/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]greatbedwyn\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]olympia-lexikon\.de/Nordische_Kombination'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]chmielnik\.com/asp/pl_start\.asp\?typ=14&menu=26&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]chmielnik\.com/asp/pl_start\.asp\?typ=14&menu=29&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]chmielnik\.com/asp/pl_start\.asp\?typ=14&menu=480&strona=1&sub=318&subsub=475'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]trinityhouse\.co\.uk'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]infolotnicze\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ck\.gov\.pl/promotion'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]globalsecurity\.org/military'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]google\.pl/search\?hl=pl&tbo=p&tbm=bks&q=inauthor'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]google\.pl/search\?tbm=bks&hl=pl&q='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]prudnik24\.pl/index\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]oneartyminute\.com/lexique-artistique/academie-julian'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]google\.pl/search\?sa=G&hl=pl&tbm=bks&tbm=bks&q=inauthor:%22J%C3%B3zef+Premik%22&ei=5_u2U7aHBouS7AbdlIGoDw&ved=0CDYQ9AgwAw'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]naval-technology\.com/projects/littoral/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]amw\.gdynia\.pl/index\.php/o-nas/historia#poczet-komendantow'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]amw\.gdynia\.pl/index\.php/uczelnia/wladze-uczelni/item/1128-wladze-rektor-komendant'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]amw\.gdynia\.pl/images/AMW/Menu-zakladki/Nauka/Zeszyty_naukowe/Numery_archiwalne/2009/Nawrot_D2\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biodiversitylibrary\.org/page/32271873#page/434/mode/1up'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dpsceilings\.com/kontakt/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]aldi\.com/impressum\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ipfs\.io/ipfs/QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco/wiki/List_of_music_recording_certifications\.html#cite_ref-International_Certification_Award_levels_\.E2\.80\.93_2013_6-0'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hydra\.hull\.ac\.uk/assets/hull:9375/content'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]portalgorski\.pl/images/images_arch/topo/mirow_topo/mirow_topo_mg\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]portalgorski\.pl/images/content/2013/07/topo_pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pulskosmosu\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rt100\.ro/top-100-edition\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]eurovisionworld\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]petanque\.pl/asp/pl_start\.asp'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]genealogy\.euweb\.cz/ zakończone na \.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pacodelucia\.org/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]teatrwybrzeze\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]portalpasazera\.pl/ poza https://portalpasazera\.pl/Plakaty/PobierzPlakat\?id=8259049&aft=fba8f051&tlo=true'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bikiniatoll\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]stat\.gov\.pl/obszary-tematyczne/ludnosc/ludnosc/ludnosc-stan-i-struktura-oraz-ruch-naturalny-w-przekroju-terytorialnym-w-2018-r-stan-w-dniu-31-xii,6,25\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bip\.wuoz\.olsztyn\.pl/phocadownload/rejestr/HTML/WUOZ%20Olsztyn%20-%20Rejestr%20zabytkow%20nieruchomych\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]yivo\.org/yiddishland-topo'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]maps\.mapywig\.org/m/WIG_maps/various/Small_scale_maps/MAPA_POLSKI_1945\.jpg'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]maps\.mapywig\.org/m/WIG_maps/various/Small_scale_maps/POLSKA_MAPA_SAMOCHODOWA_WIG_1947_2\.jpg'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]discoverlife\.org/mp/20q'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]apps\.dtic\.mil/dtic/tr/fulltext/u2/a327986\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]petanque\.net\.pl/asp/pl_start\.asp\?typ=14&sub=51&menu=55&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dmcs\.p\.lodz\.pl/wladze-katedry'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dmcs\.p\.lodz\.pl/web/anders/strona-pracownika'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zspbaczal\.com\.pl/pl/o-szkole'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]muzeumtreblinka\.eu/informacje/rodzina-kasprzakow/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ausrosterese\.lt/en/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kampinoski-pn\.gov\.pl/aktualnosci/w-przyrodzie/611-nie-taka-zima-straszna'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biodiversitylibrary\.org/part/226634'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fondationprincessecharlene\.mc/en/the-foundation/governance'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pracownia52\.pl/www/\?page_id=568'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pracownia52\.pl/www/\?page_id=2189'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gg\.ca/en/governor-general/former-governors-general/edward-richard-schreyer'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]parafiapniow\.pl/index\.php/historiaparafii#'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hockeydb\.com/ihdb/stats/leagues/241\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hockeydb\.com/ihdb/stats/pdisplay\.php\?pid=18751'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hockeydb\.com/ihdb/stats/pdisplay\.php\?pid=3883'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hockeydb\.com/ihdb/stats/pdisplay\.php\?pid=45383'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hockeydb\.com/ihdb/stats/pdisplay\.php\?pid=45384'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hockeydb\.com/ihdb/stats/pdisplay\.php\?pid=45390'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hockeydb\.com/ihdb/stats/pdisplay\.php\?pid=59815'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hockeydb\.com/stte/d-team-jyvaskyla-10479\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wtp\.waw\.pl/rozklady-jazdy/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]eparhia\.kz/node/8'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]iaf\.org\.il'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kino-teatr\.ru'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]araceum\.abrimaal\.pro-e\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]archeologia\.com\.pl/\w'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]teamusa\.org/us'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]teamusa\.org/Athletes'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]diecezjasandomierska\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]images\.sport\.org\.cn/File'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]westhighlandpeninsulas\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]inwentarz\.ipn\.gov\.pl/showDetails\?id='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]www\.wlen\.org\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]www\.aeroklub\.suwalki\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]www\.rpo-unesco\.zamosc\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]www\.dubiecko\.pl/asp/pl_start\.asp'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]polona\.pl/archive\?uid='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]atptour\.com/en/players'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]magyarfutball\.hu/hu/stadionok'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]magyarfutball\.hu/hu/szemelyek'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]magyarfutball\.hu/hu/csapat'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]magyarfutball\.hu/hu/stadion'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]villageinfo\.in'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]plato\.stanford\.edu/entries'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]aleaguestats\.com/ALeagueStats'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ipn\.gov\.pl/pl/aktualnosci/\d'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ipn\.gov\.pl/pl/aktualnosci/konkursy-i-nagrody'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]historyspeedway\.nstrefa\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tram\.rusign\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]aeroklub\.olsztyn\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fis-ski\.com/DB/freestyle-skiing/calendar-results\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wegenwiki\.nl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]byodoin\.or\.jp'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]britishmuseum\.org/collection'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gminadabie\.pl/asp/pl_start\.asp'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kurylowka\.pl/asp'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cso\.ie/en/census/census2011reports/census2011populationclassifiedbyareaformerlyvolumeone/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bontonland\.cz/berezin-xm2012/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]stat\.gov\.pl/obszary-tematyczne/srodowisko-energia/srodowisko/ochrona-srodowiska-2019,1,20\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/arts-entertainment/music/reviews/christina-aguilera-liberation-review-album-chromeo-mike-shinoda-a8397131\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wpolomne\.org/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biodiversitylibrary\.org/item/42805#page/107/mode/1up'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]eswc\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]apl\.geology\.sk/gm50js/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]apl\.geology\.sk/mapportal/img/pdf/tm19a\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]visitcumbria\.com/pen/mungrisdale/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wikipasy\.pl/%C5%9Awi%C4%99ta_Wojna_%28historia%29'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wikipasy\.pl/1983/84_III_liga_grupa_VIII_(Cracovia_II)'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wikipasy\.pl/Hokej_m%C4%99%C5%BCczyzn_1927/28'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bnc\.cat/eng/About-us/Chronology'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pajeczno\.pl/poznaj-miasto/historia-pajeczna/z-przeszlosci-miejscowosci-i-parafii-pajeczno/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]usosweb\.uth\.edu\.pl/kontroler\.php\?_action=katalog2/osoby/pokazOsobe&os_id=17842'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nppshamli\.in/statis\.aspx'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biodiversitylibrary\.org/item/23715'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]groby\.cui\.wroclaw\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]paralympic\.org/news/list-opening-ceremony-flag-bearers'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]paralympic\.org/oksana-masters'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cidades\.ibge\.gov\.br/brasil/ma/bom-jesus-das-selvas/panorama'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cidades\.ibge\.gov\.br/brasil/pe/calumbi/panorama'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]arabakolautada\.eus/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]atptour\.com/en/tournaments/kitzbuhel/319/overview'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dosaguasayuntamiento\.es/es/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]severina\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]otterbach-otterberg\.de/vg_otterbach_otterberg/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]liturgia\.cerkiew\.pl/texty\.php\?id_n=128&id=114'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bkvelore\.hu/stadion/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]austria-salzburg\.at/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wieliczka\.eu/pl/201263/0/miasta-partnerskie\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wieliczka\.eu/pl/201266/0/strefa-platnego-parkowania\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]strzelce\.pl/nasze-strzelce/wspolpraca-zagraniczna/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fotopolska\.eu/Niwnice_Dwor'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fotopolska\.eu/Torun/b33528,Gazownia_Miejska\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fotopolska\.eu/Wroclaw/u149195,ul_Jozefa_sw\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rsssfbrasil\.com/miscellaneous/artbrclubs\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]praterservice\.at/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]theplantlist\.org/tpl1\.1/search\?q=Glomera'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lonelyplanet\.com/equatorial-guinea'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]spaceobs\.org/en/2011/03/07/vliyanie-planet-gigantov-na-orbitu-komety-c2010-x1-elenin/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]spaceobs\.org/en/2011/10/06/comet-elenin-disintegrated/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fcdac1904\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pilsudski\.org/pl/88-zbiory/zasoby/356-zespol-133'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pilsudski\.org/pl/88-zbiory/zasoby/227-zespol-004'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pilsudski\.org/pl/zbiory-instytutu/galeria/obrazy/164-jozef-chelmonski---czworka'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pilsudski\.org/pl/zbiory-instytutu/katalogarchiwum-2/308-zespol-085'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fis-ski\.com/DB/freestyle-skiing/cup-standings\.html\?eventselection=&place=&sectorcode=SB&seasoncode=2019&categorycode=NAC&disciplinecode=&gendercode=&racedate=&racecodex=&nationcode=&seasonmonth=X-2019&saveselection=-1&seasonselection='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]snim\.rami\.gob\.mx/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]routes\.fandom\.com/wiki/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lloydslist\.maritimeintelligence\.informa\.com/one-hundred-container-ports-2018/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]teki\.bkpan\.poznan\.pl/index_regesty\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]teki\.bkpan\.poznan\.pl/index_monografie\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]histmag\.org/Co-po-Hitlerze-skrajna-prawica-w-powojennych-Niemczech-14802'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gminadabie\.pl/asp/pl_start\.asp\?typ=13&menu=416&sub=460&subsub=283&pol=1&dzialy=416&akcja=artykul&artykul=533&schemat=2'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bpi\.co\.uk/about-bpi\.aspx'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]katalog\.bip\.ipn\.gov\.pl/informacje/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biodiversitylibrary\.org/item/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]atptour\.com/en/tournaments/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]presidency\.gov\.lb/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]data\.fei\.org/Person/Detail\.aspx\?p='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]data\.fei\.org/Horse/Detail\.aspx\?p='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]data\.fei\.org/Horse/Performance\.aspx\?p='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]data\.fei\.org/Person/Performance\.aspx\?p='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]data\.fei\.org/Result/ResultList\.aspx\?p='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]przeworsk\.net\.pl/asp/pl_start\.asp'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]genius\.com/albums/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]poranny\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]studiojg\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]autocade\.net/index\.php/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]spirit-of-metal\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tapology\.com/fightcenter/fighters/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]academic\.oup\.com/zoolinnean/article/159/2/435/2622978'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]poszukiwania\.ipn\.gov\.pl/bbp/aktualnosci/7303,Odnalezieni-i-Zidentyfikowani\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]poszukiwania\.ipn\.gov\.pl/bbp/odnalezieni/482,Stanislaw-Kutryb\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fpiw\.pl/pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]meden\.com\.pl/baza-wiedzy'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]familek\.pl/atrakcja/muzeum-mineralow-skarby-ziemi'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rlfoot\.fr/index\.php\?page=http://rlfoot\.fr/Joueurs/DIABY_Abou\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gal-ed\.co\.il/etzel/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fis-ski\.com/DB/DB/cross-country/calendar-results\.html\?eventselection=&place=&sectorcode=CC&seasoncode=2019&categorycode=UST&disciplinecode=&gendercode=&racedate=&racecodex=&nationcode=&seasonmonth=X-2019&saveselection=-1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fis-ski\.com/DB/DB/cross-country/calendar-results\.html\?eventselection=&place=&sectorcode=CC&seasoncode=2020&categorycode=UST&disciplinecode=&gendercode=&racedate=&racecodex=&nationcode=&seasonmonth=X-2020&saveselection=-1&seasonselection='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]soccerpunter\.com/players/98386-Veronica-Boquete-Giadans'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]katalog\.bip\.ipn\.gov\.pl/funkcjonariusze/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ma\.linkedin\.com/in/nawal-slaoui-b5609aba'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]teamusa\.org/Hall-of-Fame/Hall-of-Fame-Members/Ray-Ewry'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]antiochpatriarchate\.org'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]globalsecurity\.org/intell/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dic\.academic\.ru/dic\.nsf/biograf2/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dic\.academic\.ru/dic\.nsf/bse/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dic\.academic\.ru/dic\.nsf/brokgauz_efron/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dic\.academic\.ru/dic\.nsf/dic_synonims/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dic\.academic\.ru/dic\.nsf/enc'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dic\.academic\.ru/dic\.nsf/es'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dic\.academic\.ru/dic\.nsf/sie'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dic\.academic\.ru/dic\.nsf/vasmer/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]collinsdictionary\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]walesonline\.co\.uk'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]db\.japan-wrestling\.jp/player/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nowehoryzonty\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]14mff\.nowehoryzonty\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]15mff\.nowehoryzonty\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]magazyngitarzysta\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]plants\.jstor\.org/stable/10\.5555/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ipsb\.nina\.gov\.pl/a/biografia/aleksander-jaroslaw-rymkiewicz'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dic\.academic\.ru/dic\.nsf/ushakov/907214'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dic\.academic\.ru/dic\.nsf/stroitel/1632'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]klimontow\.pl/kosciol-p-w-sw-jacka-oraz-podominikanski-zespol-klasztorny/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]motovoyager\.net/najnowsze/nadjezdza-predator-pierwszy-w-polsce-test-kawasaki-versys-650-tylko-u-nas/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cometography\.com/lcomets/2011l4\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]calc\.beltoll\.by'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hockey\.no'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]viafrancigena\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]16mff\.nowehoryzonty\.pl/film\.do\?typOpisu=1&id=7921&ind=typ=cykl&idCyklu=561'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]myspace\.com/fulldiesel'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cbc\.ca/news/canada/government-s-recent-labour-interventions-highly-unusual-experts-say-1\.977658'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]digital\.la84\.org/digital/collection/p17103coll8'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]szklanydom\.maslow\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]backstage\.com/magazine/article/frida-premieres-venice-festival-32514/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biathlon\.com\.pl/biathlon/olimpijczycy/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]simon-b-k\.com/index\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]10mff\.nowehoryzonty\.pl/artykul\.do\?id=511'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rymanow\.pl/asp/pl_start\.asp\?typ=14&sub=9&subsub=27&menu=67&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bielskpodlaski\.pl/asp/pl_start\.asp\?typ=13&sub=4&menu=66&artykul=1150&akcja=artykul'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bielskpodlaski\.pl/asp/pl_start\.asp\?typ=13&sub=4&menu=66&artykul=1047&akcja=artykul'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bielskpodlaski\.pl/asp/pl_start\.asp\?typ=13&sub=4&subsub=0&menu=66&artykul=931&akcja=artykul'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mundoascensonline\.com\.ar'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]8ff\.nowehoryzonty\.pl/lista\.do\?edycjaFest=8&typ=cykl&dzien=&indeksAZ=%E2%80%93&rodzajTytulu=2&idCyklu=124&tytul=las+meninas'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ligaprimera\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]academic\.oup\.com/botlinnean/article-abstract/57/369/1/2883056'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kirgizfilm\.ru'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lodzkiedziewuchy\.org\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]scientificamerican\.com/article'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]anzrankings\.org\.nz/site/results_con'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]anzrankings\.org\.nz/site/records_con/get_records'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]imslp\.org/wiki/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]premierleague\.com/players/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]scsuhuskies\.com/news/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sarp\.krakow\.pl/sd/om/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]google\.pl/search\?hl=pl&tbm=bks&tbm=bks&q=inauthor'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sabre-roads\.org\.uk/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hawkwind\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]horodlo\.biuletyn\.net/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]karczew\.biuletyn\.net/fls/bip_pliki/2017_04/BIPF54E3923EE299CZ/12\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]klodawa\.biuletyn\.net/fls/bip_pliki/2018_03/BIPF5684BB14266DCZ/2018-03-19_278\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]klodawa\.biuletyn\.net/fls/bip_pliki/2020_05/BIPF5A55A2DC38B16Z/2020_RAPORT_O_STANIE_GMINY\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lipka\.biuletyn\.net/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nowaruda\.biuletyn\.net/fls/bip_pliki/2017_03/BIPF54B660A833020Z/NRM_zm_Studium_tekst_zal_zabytki_2017-03-15-wylozenie\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rakszawa\.biuletyn\.net/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sierakowice\.biuletyn\.net/fls/bip_pliki/2015_02/BIPF5100C964BD685Z/strategia2014p\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sobkow\.biuletyn\.net/fls/bip_pliki/2013_03/BIPF4D7CA4112D892Z/stan\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biuletyn\.net/nt-bin/start\.asp\?podmiot=rzeczniow/&strona=14&typ=podmenu&typmenu=14&menu=18&id=20&str=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]warszawa\.stat\.gov\.pl/vademecum/vademecum_mazowieckie/portrety_gmin/radomski/1425062_jedlnia-letnisko\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tuszownarodowy\.biuletyn\.net/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biuletyn\.net/lipusz/fls/bip_pliki/2016_09/BIPF53D8B89C4070FZ/XXXV1942013_z_dnia__2013\.10\.24\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biuletyn\.net/pilawagorna/archiwum/pilawagorna\.bip\.ornak\.pl/pl/bip/prawo_lokalne/uchwaly_rady_miejskiej/2009/26_08_2009/177_xxxiv_2009/px_u_177_xxxiv_2009\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biuletyn\.net/powiat-gdanski/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bierutow\.biuletyn\.net/\?bip=1&cid=173'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bukowsko\.biuletyn\.net/fls/bip_pliki/2021_06/BIPF5C4C9E1E205CDZ/RAPORT_O_STANIE_GMINY_BUKOWSKO_ZA_ROK_2020\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gminaskorcz\.biuletyn\.net/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tuszownarodowy\.biuletyn\.net/\?bip=2&cid=234&id=1007'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]chkrootkit\.org/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]detektywi-na-kolkach\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]buffalopittsburghdiocesepncc\.org/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zheldor-city\.ru/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]stat\.gov\.pl/obszary-tematyczne/roczniki-statystyczne/roczniki-statystyczne/rocznik-demograficzny-2019,3,13\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]muzeumfarmacji\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cbnt\.collegium\.edu\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ecb\.co\.uk/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]vysnykazimir\.eu/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nfas\.org\.sz/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]goslawski\.art\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mikulas\.sk/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]samorin\.sk/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]obecdanisovce\.eu/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]academic\.oup\.com/occmed/article/67/4/251/3858154'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cochranelibrary\.com/cdsr/doi/10\.1002/14651858\.CD010922\.pub2/full'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]metrolisboa\.pt/viajar/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]olimpbase\.org/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mbc\.cyfrowemazowsze\.pl/dlibra/plain-content\?id='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mbc\.malopolska\.pl/dlibra/plain-content\?id='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dlibra\.umcs\.lublin\.pl/dlibra/plain-content\?id='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kulturalnemedia\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]thecatlady\.co\.uk/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dziennikiurzedowe\.rcl\.gov\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]eto\.hu/stadionrol/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]capcom\.fandom\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]crescentbloom\.com/plants/genus/c/a/cannabis\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]crescentbloom\.com/plants/genus/c/o/cocos\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]crescentbloom\.com/plants/ordo/ranunculales\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]file-extension\.org/pl/extensions/lrc'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]web\.archive\.org/web/20120306062250/http://www\.president\.gov\.ua/documents/4871\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ldoceonline\.com/dictionary/cf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nagrzyby\.pl/atlas\?id=5010'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]riley-smith\.net/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zawadzka\.eu/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]liturgia\.cerkiew\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]theplantlist\.org'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mat\.umk\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]polcul\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]navypedia\.org/ships'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]newsbeezer\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]journals\.lww\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]arthur-conan-doyle\.com/index\.php\?title='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]academic\.oup\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bloodhorse\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ultimateracinghistory\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]news\.softpedia\.com/news'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]11v11\.com/players'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/data'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/hierarchy/data'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fabrykaslow\.com\.pl/autorzy'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]princevault\.com/index\.php\?title='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wiki\.bugwood\.org'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sezonoj\.ru'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jezowe24\.pl/wiki'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jbc\.bj\.uj\.edu\.pl/publication'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]faktyoswiecim\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dlibra\.bg\.ajd\.czest\.pl:8080/Content'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dlibra\.bg\.ajd\.czest\.pl:8080/publication'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ouest-france\.fr/pays-de-la-loire'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ouest-france\.fr/sport'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ouest-france\.fr/normandie'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]guinnessworldrecords\.com/world-records'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]web\.diecezja\.wloclawek\.pl/parafia'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dlibra\.bg\.ajd\.czest\.pl:8080/dlibra/doccontent\?id=2502'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dlibra\.bg\.ajd\.czest\.pl:8080/dlibra/docmetadata\?id=2504&from=publication'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jbc\.bj\.uj\.edu\.pl/dlibra/publication/152129#structure'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rockerek\.hu/zenekarok/%C1rnyak'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]whatisfear\.com/#/en/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kameralisci\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pusoksa\.buddhism\.org/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hami\.gov\.cn/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]macedonia\.sp\.gov\.br/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pure-romania\.com/phoenix-band/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]no\.unionpedia\.org/i/Stabekk'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pl\.unionpedia\.org/Rejon_samborski'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pl\.unionpedia\.org/i/Micha%C5%82_W%C5%82adys%C5%82aw_Sobolewski'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wombatmaksymilian\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]scopecalc\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ouest-france\.fr/societe/police/deces-de-roger-borniche-flic-et-romancier-succes-6871346'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]redemptor\.pl/historia/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]redemptor\.pl/redemptorysci-w-polsce/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]medieval\.eu/aggersborg-viking-age-settlement-and-fortress/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/organizations/a04\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/organizations/v2c2\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/former/mohi0\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/dioceses/types\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/orders/007\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gcatholic\.org/saints/fr1-blesseds6\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]myvimu\.com/exhibit/47683217-karabin-maszynowy-mg-81'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cloudflare\.com/learning/bots/what-is-click-fraud/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cloudflare\.com/learning/ddos/http-flood-ddos-attack/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cloudflare\.com/learning/ddos/syn-flood-ddos-attack/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]millercenter\.org/president/thomas-jefferson/key-events'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]millercenter\.org/president/lbjohnson/essays/gronouski-1963-postmaster-general'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]buildandfly\.shop/product/j2-polonez/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]foxsports\.com\.au/football/a-league/melbourne-city-v-wellington-phoenix-at-aami-park-score-highlights-video-statistics/news-story/1797a97125becdc5dfe42aac0ca38bf5'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]matamaladealmazan\.es/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mypoeticside\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dictionary\.cambridge\.org/dictionary	'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]genius\.com/S'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]genius\.com/T'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bpwola\.waw\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]whosampled\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ville-bourges\.fr'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]genius\.com/Vnm-zagusz-mnie-lyrics'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]genius\.com/Bad-religion-flat-earth-society-lyrics'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://pther\.net/PDF/Szlachta%20ziemianie/02%20%C5%9Alusarek%20Krzysztof%20W%20przededniu%20autonomii\.%20W%C5%82asno%C5%9B%C4%87%20ziemska%20i%20ziemia%C5%84stwo%20zachodniej%20Galicji%20w%20po%C5%82owie%20XIX%20wieku\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://pther\.net/PDF/Rocznik_PTHer/Rocznik_PTHer_tom12%20ISSN%201230-803X\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://zawisza1946\.pl/zawodnik_razem\.php\?id_zawodnika=241&imie_nazwisko=Miros%B3aw%20Milewski'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]eol\.org/pages/793463'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]eol\.org/pages/1252905'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://floradobrasil\.jbrj\.gov\.br/jabot/FichaPublicaTaxonUC/FichaPublicaTaxonUC\.do\?id=FB14362'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://floradobrasil\.jbrj\.gov\.br/jabot/FichaPublicaTaxonUC/FichaPublicaTaxonUC\.do\?id=FB14367'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://floradobrasil\.jbrj\.gov\.br/jabot/FichaPublicaTaxonUC/FichaPublicaTaxonUC\.do\?id=FB117251'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bbn\.gov\.pl/pl/wydarzenia/6588,Jacek-Kitlinski-generalem-Sluzby-Wieziennej\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bbn\.gov\.pl/download/1/15274/99-120selzbietaposluszna\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bbn\.gov\.pl/download/1/24951/08Czlowiekowski\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bbn\.gov\.pl/pl/wydarzenia/309,Spotkanie-prezydenta-RP-z-Batalionem-Polsko-Ukrainskim-w-Kosowie\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bbn\.gov\.pl/pl/wydarzenia/3825,Nominacje-generalskie-i-odznaczenia-dla-funkcjonariuszy-Panstwowej-Strazy-Pozarn\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bbn\.gov\.pl/pl/wydarzenia/5216,183-lata-temu-Sejm-Krolestwa-Polskiego-przyjal-uchwale-o-fladze-Polski\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bbn\.gov\.pl/pl/wydarzenia/4773,Pozegnanie-attach-obrony-Niemiec\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bbn\.gov\.pl/pl/wydarzenia/7731,Prezydent-RP-quotPo-27-latach-zaniedban-i-niedoinwestowania-MW-RP-czas-na-zmiany\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bbn\.gov\.pl/pl/wydarzenia/8572,Nominacje-i-odznaczenia-z-okazji-Swieta-Wojska-Polskiego\.html\?search=6062800228'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wiadomosci\.wp\.pl/obudz-sie-polsko-relacja-na-zywo-z-marszu-pis-w-warszawie-6031535103181441a'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pigc\.org\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]shift\.org\.pl/zabytkowe-pojazdy/wraki'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wrota-swietokrzyskie\.pl/transport-kolejowy'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]checiny\.e-mapa\.net/\?userview=146'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wrota-swietokrzyskie\.pl/407/-/asset_publisher/tvK0/content/wojewodzki-dom-kultury-w-kielcach-2\?redirect=https%3A%2F%2Fwww\.wrota-swietokrzyskie\.pl%2F407%3Fp_p_id%3D101_INSTANCE_tvK0%26p_p_lifecycle%3D0%26p_p_state%3Dnormal%26p_p_mode%3Dview%26p_p_col_id%3Dcolumn-2%26p_p_col_count%3D1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wrota-swietokrzyskie\.pl/411/-/asset_publisher/M5hu/content/hebdow-sanktuarium-matki-boskiej-hebdowskiej\?redirect=https%3A%2F%2Fwww\.wrota-swietokrzyskie\.pl%2F411%3Fp_p_id%3D101_INSTANCE_M5hu%26p_p_lifecycle%3D0%26p_p_state%3Dnormal%26p_p_mode%3Dview%26p_p_col_id%3Dcolumn-2%26p_p_col_count%3D1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]katyn\.wrota-swietokrzyskie\.pl/deby-pamieci'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]katyn\.wrota-swietokrzyskie\.pl/main/-/asset_publisher/4WCw/content/kwesta-na-rozbudowe-pomnika-katynskiego\?redirect=https://katyn\.wrota-swietokrzyskie\.pl/main\?p_p_id=101_INSTANCE_4WCw&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&p_p_col_id=column-2&p_p_col_count=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dir\.icm\.edu\.pl/pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]grywald\.podhale\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cbj\.jhi\.pl/documents'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rhs\.org\.uk/plants'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]poemhunter\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pw\.ipn\.gov\.pl/pwi'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]amudanan\.co\.il/\?lon'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lancut\.pl/asp/pl_start\.asp'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gac\.pl/asp/pl_start\.asp'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sla\.polonistyka\.uj\.edu\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lutnia-strumien\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]skiboardmagazine\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kwidzyn\.pl/krwawa-sobota-14-sierpnia-1982-roku-pacyfikacja-internowanych-w-osrodku-odosobnienia-w-kwidzynie-4112/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sodbtn\.sk/obce/index_kraje\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]google\.com/search\?tbm=bks&q=Tadeusz+Antoni+Mostowski'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sylwekszweda\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zajecar\.info/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]morentin\.es/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]twitter\.com/Udhaystalin_FC'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]episcopia\.ca/index\.php/en/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]episcopia\.ca/index\.php/ro/structura/director-parohii'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]web\.archive\.org/web/20070518191639/http://www\.mayones\.pl/katalog\.html\?nazwa=Skawi%F1ski+Regius-7&menu=2'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bakalarzewo\.pl/asp/pl_start\.asp\?typ=13&menu=101&dzialy=101&akcja=artykul&artykul=2495'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bakalarzewo\.pl/asp/pl_start\.asp\?typ=13&menu=85&artykul=894&akcja=artykul'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fotopolis\.pl/tagi/5852-fotografia-analogowa'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]swietokrzyskisztetl\.pl/asp/pl_start\.asp\?typ=14&menu=39&strona=1&sub=9&schemat=2'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fotopolis\.pl/newsy-sprzetowe/branza/9024-przyznano-odznaczenia-mkidn-dla-czlonkow-zpaf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fotopolis\.pl/newsy-sprzetowe/aparaty-fotograficzne/29796-blindtouch-polacy-stworzyli-pierwszy-aparat-fotograficzny-dla-niewidomych'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rsssf\.no/2010/Premier\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rsssf\.no/2010/Cup\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]graastenslot\.dk/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ansichtskarten-lexikon\.de/ak-97135\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]spirit-of-rock\.com/pl/band/The_Adolescents'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]spirit-of-rock\.com/pl/album/Live_at_the_House_of_Blues/51870'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]synonim\.net/synonim/germanizacja'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]synonim\.net/synonim/obierki'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]spr-chrobry\.glogow\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lubelskiedworce\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lingvaria\.polonistyka\.uj\.edu\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gbl\.waw\.pl/p/informacje-ogolne#historia'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]vaaju.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]orthodoxwiki.org'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gbu.gl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]handballkorea.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]swimsa.org/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gibraltar.gov.gi/statistics/census/gibraltar-census-history'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]usawaterpolo.org/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kobo.com/ca/en/ebook/sapiens-2'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]revuckalehota.sk/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]renatogamba.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]skiinghistory.org/history/100-years-rossignol'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]changjiang.hainan.gov.cn/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]onlinelibrary.wiley.com/doi/book/10.1002/9783527619115'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]orthodoxcanada.ca/Archbishop_Victorin_(Ursache)'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]orthodoxcanada.ca/Bishop_Andrei_(Moldovan)'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mitropolia.us/index.php/en/structure/canadian-diocese'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wmo.asu.edu/content/antarctica-highest-temperature'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]valenzueladecalatrava.es/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]archive.ph/xvqtj'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]archive.ph/OGY29'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]arfik.art.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ministranci.katowice.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]grkatpo.sk/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]aacz.czestochowa.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]blog.wikimapia.org/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kishkhodro.ir/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lorinser.com.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]turgenev.org.ru/en/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cornellbigred.com/sports/wrestling/roster/coaches/clint-wattenberg/312'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]autotrader.com/car-news/chrysler-conquest-only-model-name-sold-three-different-brands-262368'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]autotrader.com/car-news/saturn-vue-red-line-was-high-performance-saturn-suv-281474979933211'),  # bot rejected on site (masti, szoltys)

    re.compile('.*[\./@]fundacjawagnera\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hltv\.org'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]teatrtv\.vod\.tvp\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ruj\.uj\.edu\.pl/xmlui/handle/item/22093'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zwiazekgmin\.eu/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nlomov\.net/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]carabobo\.gob\.ve/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]forza-fiume\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]harsany\.hu/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rsa\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ui\.adsabs\.harvard\.edu/abs/1976Natur\.261\.\.459M/abstract'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]szupermodern\.hu/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nationalparkgemeinde-buhlenberg\.de/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.albareto\.pr\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]chiltoncountychamber\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]omega\.hu/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wadirum\.jo/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]obc\.opole\.pl/dlibra/publication/edition/6609\?id=6609'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]texassports\.com/hof\.aspx\?hof=88'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]researchgate\.net/profile/Adam_Fronczak'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]newscientist\.com/article/2365363-mathematicians-discover-shape-that-can-tile-a-wall-and-never-repeat/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/arts-entertainment/music/news/jill-janus-dead-dies-huntress-singer-heavy-metal-age-how-cause-a8495566\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/sport/football-leighton-saves-the-day-1351758\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/world/middle-east/yemen-food-supplies-two-months-charity-warns-a8551481\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/world/middle-east/yemen-war-saudi-arabia-children-deaths-famine-disease-latest-figures-a8057441\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/world/middle-east/saudi-arabia-s-bombing-of-yemeni-farmland-is-a-disgraceful-breach-of-the-geneva-conventions-a7376576\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/world/middle-east/un-saudi-arabia-yemen-air-strikes-violated-international-law-a7372936\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/business/analysis-and-features/the-big-question-what-is-short-selling-and-is-it-a-practice-that-should-be-stamped-out-874717\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/business/analysis-and-features'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/media/press/evening-standard-wins-top-awards-2120509\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/sport/football/premier-league/manchester-united-clinch-record-19th-english-title-2284086\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/sport/tennis/us-open-simona-halep-grand-slam-kaia-kanepi-out-report-latest-a8510126\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/people/obituary-luis-rosales-1559684\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/obituaries/nelson-bond-423513\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/arts-entertainment/music/news/metro-boomin-retires-rap-producer-instagram-drake-future-kanye-migos-a8302806\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/people/news/the-ios-pink-list-2012-8216187\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/arts-entertainment/music/reviews/lily-allen-sheezus-album-review-lily-takes-no-prisoners-in-return-to-the-spotlight-9294354\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/world/middle-east/socotra-yemen-civil-war-uae-miltary-base-island-life-emirates-a8342621\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/arts-entertainment/music/reviews/lily-allen-new-album-no-shame-review-lyrics-release-date-a8386156\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/obituaries/barry-foster-9133062\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/world/europe/suruc-bombing-is-it-safe-to-travel-in-turkey-10403122\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/arts-entertainment/music/reviews/ariana-grande-sweetener-review-tracks-pete-davidson-manchester-a8494496\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/arts-entertainment/theatre-dance/features/will-spice-girls-inspired-musical-viva-forever-spice-up-my-life-again-8386944\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/sport/general/wwe-mma-wrestling/wwe-network-everything-you-need-to-know-9150052\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/life-style/health-and-families/healthy-living/zumba-you-get-fit-they-get-rich-8106992\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/obituaries/alberto-de-lacerda-5329171\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/people/rio-2016-olympic-gymnastics-mexico-alexa-moreno-twitter-supports-body-shaming-a7182641\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/obituaries/barbara-piasecka-johnson-heiress-to-a-disputed-fortune-8560682\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/obituaries/mortimer-planno-6102816\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/media/yawns-greet-bbc-millennium-lineup-738983\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/arts-entertainment/films/news/bud-luckey-woody-toy-story-dead-age-andy-pixar-sesame-street-a8229121\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/obituaries/judy-lewis-actress-eventually-revealed-as-the-love-child-of-clark-gable-and-loretta-young-6275575\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/uk/politics/david-lidington-lgbt-rights-gay-marriage-theresa-may-justice-secretary-a7786751\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/life-style/health-and-families/health-news/residents-at-richard-attenborough-s-care-home-given-wrong-drug-doses-9845014\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/world/americas/guatemala-volcano-live-latest-updates-eruption-death-toll-rescue-travel-warning-de-fuego-a8382426\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/incoming/2010-fifa-world-cup-south-africa-stadium-guide-1838530\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/sport/football/scottish/scottish-premier-league-celtic-clinch-spl-title-8581759\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/sport/football/premier-league/former-spurs-defender-bunjevcevic-dies-at-at-the-age-of-45-a8422226\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/arts-entertainment/music/reviews/manic-street-preachers-album-review-eels-kylie-minogue-today-listen-a8288586\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/arts-entertainment/music/reviews/harry-styles-album-review-debut-singles-sign-of-the-times-sweet-creature-two-ghosts-lyrics-a7729891\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/obituaries/hiroshi-yamauchi-computing-pioneer-who-turned-nintendo-into-a-global-gaming-giant-8832956\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/people/profiles/my-secret-life-james-may-tv-presenter-age-45-943442\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/life-style/the-draughty-state-of-e-lasker-1254486\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/uk/politics/queen-s-speech-six-antiquated-customs-of-the-monarch-s-address-to-parliament-a7034591\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/arts-entertainment/music/news/keith-flint-dead-prodigy-cause-age-firestarter-a8806456\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/uk/home-news/bottle-flipping-trick-videos-youtube-banned-in-schools-a7346131\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/travel/news-and-advice/coventry-airport-shuts-down-1836481\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/people/obituary-alan-booth-1470999\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/world/europe/yellow-vest-protests-man-killed-perpignan-france-gilets-jaunes-roundabout-a8696021\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/obituaries/rolando-ugolini-goalkeeper-adored-by-fans-of-middlesbrough-for-his-flamboyant-acrobatics-allied-to-a-fearless-reliability-9503057\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/world/parents-on-trial-for-cancer-treatment-refusal-1357672\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/obituaries/mona-inglesby-419831\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/arts-entertainment/tv/news/great-british-bake-off-2014-viewers-complain-about-smutty-innuendos-as-we-pick-the-best-9752461\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/arts-entertainment/tv/news/the-great-british-bake-off-rocked-by-baked-alaska-sabotage-scandal-9695831\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/arts-entertainment/tv/news/great-british-bake-off-review-channel-4-noel-fielding-paul-hollywood-sandi-toksvig-prue-bbc-a7906051\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/arts-entertainment/tv/news/great-british-bake-off-2018-gbbo-start-air-date-contestants-channel-4-presenters-a8494066\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/arts-entertainment/tv/news/the-great-british-bake-off-2016-start-date-bbc-one-show-delayed-thanks-to-the-rio-olympics-a7174311\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/uk/home-news/is-this-the-bella-in-the-wych-elm-unravelling-the-mystery-of-the-skull-found-in-a-tree-trunk-8546497\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/news/obituaries/metropolitan-vitaly-ustinov-417796\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]independent\.co\.uk/arts-entertainment/music/reviews/5sos-new-album-review-bebe-rexha-nine-inch-nails-kamasi-washington-a8408281\.html'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]teatrwkrakowie\.pl'),   # bot rejected on site (masti, MiniMiniBomba)
    re.compile('.*[\./@]daao\.org\.au/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wff\.pl/pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dic\.academic\.ru/dic\.nsf/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]debowe\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]browar-moczybroda\.eatbu\.com/\?lang=pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mwananchi\.co\.tz/habari/Kitaifa/Askofu-mstaafu-Mmole-afariki-dunia--kuzikwa-Mei-21/1597296-5116652-kuy3hmz/index\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]thecitizen\.co\.tz/news/Sports/Okwi-saga-takes-new-twist--Yanga-protest-ruling-/1840572-2446584-12xukjfz/index\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]data\.worldbank\.org/indicator/ST\.INT\.ARVL\?locations=KE'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]data\.worldbank\.org/indicator/NY\.GDP\.MKTP\.CD\?locations=CF'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]estradaistudio\.pl/mieszanka/30113-z-mikrofonem-w-swiat-field-recording'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]henrykow\.ziebice\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]femminile\.football\.it//schedagiocatore\.php\?id_giocatore=5986'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]archidiecezja\.wroc\.pl/parafia\.php\?id_dek=34&id_par=4'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]archidiecezja\.wroc\.pl/parafia\.php\?id_dek=45&id_par=8'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]archidiecezja\.wroc\.pl/parafia\.php\?id_dek=4&id_par=4'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]archidiecezja\.wroc\.pl/parafia\.php\?id_dek=3&id_par=7'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]archidiecezja\.wroc\.pl/parafia\.php\?id_dek=27&id_par=6'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]elijahmessage\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]darwinproject\.ac\.uk/conrad-martens'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]iuhoosiers\.com/sports/mens-basketball/roster/juwan-morgan/10999'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]iovs\.arvojournals\.org/article\.aspx\?articleid=2182695'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gocards\.com/sports/womens-volleyball/roster/lecia-brown/4756'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gocards\.com/sports/womens-volleyball/roster/justine-landi/4765'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]karate\.suwalki\.pl/wyniki-sportowe/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]osir\.suwalki\.pl/rozpoczela-sie-budowa-hali-sportowej-suwalki-arena/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]osir\.suwalki\.pl/nasze-obiekty/suwalki-arena-2/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]russian_geography\.academic\.ru/3102/Усвяты'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]border\.academic\.ru/500/%D0%9A%D0%BE%D0%BD%D1%82%D1%80%D0%BE%D0%BB%D1%8C%D0%BD%D0%BE-%D1%81%D0%BB%D0%B5%D0%B4%D0%BE%D0%B2%D0%B0%D1%8F_%D0%BF%D0%BE%D0%BB%D0%BE%D1%81%D0%B0'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]books\.academic\.ru/book\.nsf/60614285/%D0%94%D0%B8%D0%B0%D0%BB%D0%BE%D0%B3+%D1%81+%D0%B0%D0%BA%D1%82%D0%B5%D1%80%D0%BE%D0%BC'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]eponym\.academic\.ru/142/%D0%9B%D0%B0%D0%BD%D0%B4%D1%80%D0%B8%D0%BD'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]agricultural_dictionary\.academic\.ru/1477/АМУ-БУХАРСКИЙ_КАНАЛ#sel=3:47,3:94'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jbc\.bj\.uj\.edu\.pl/dlibra/publication/290337/edition/277213'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jbc\.bj\.uj\.edu\.pl/dlibra/publication/5929'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]brevets-patents\.ic\.gc\.ca/opic-cipo/cpd/eng/patent/1288559/summary\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]merckmillipore\.com/INTERSHOP/web/WFS/Merck-DE-Site/de_DE/-/EUR/ShowDocument-File\?ProductSKU=MDA_CHEM-814254&DocumentId=814254_SDS_DE_DE\.PDF&DocumentType=MSD&Language=DE&Country=DE'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]esaso\.org/team/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]geni\.com/people/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lwow\.info/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pzdw\.bialystok\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dakar\.com/fr/concurrent/247'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dakar\.com/en/competitor/8'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]frank-turner\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]celebretainment\.com/music/demi-lovato-inspired-by-christina-aguilera/article_25df5d90-d398-524a-8ee6-6c1484b2a425\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]atptour\.com/en/tournaments/laver-cup/9210/overview'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ilisimatusarfik\.gl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]porcys\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]satbayev\.university/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]circuitcat\.com/en/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]vec\.wikipedia\.org/wiki/Pajina_prinsipa'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]luban\.luteranie\.pl/kosciol-ewangelicki-marii-panny-w-lubaniu-z-xiv-wieku/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wolczyn\.luteranie\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lask\.luteranie\.pl/\?D=1/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]litclub\.com/library/bg/kanon\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]skofjaloka\.si/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]beskidmaly\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gnomonika\.pl/katalog\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zdw\.olsztyn\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biathlon\.com\.ua/en/calendar\.php\?id=30'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biathlon\.com\.ua/calendar\.php\?id=29'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biodiversitylibrary\.org/page/3887548#page/165/mode/1up'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]voleiromania\.ro/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]perlabaroku\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wbc\.macbre\.net/document/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]invasiveplantatlas\.org/subject\.html\?sub='),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]codaworx\.com/projects/podlasie-opera-and-philharmonic-european-art-centre-in-bialystok-podlaskie-voivodeship-marshal-s-office/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]landeskirche-anhalts\.de/landeskirche/leitung'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]landeskirche-anhalts\.de/service/information-in-english'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]landeskirche-anhalts\.de/projekte/kirchen-im-gartenreich/evangelische-kirche-riesigk'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]timesmachine\.nytimes\.com/timesmachine/1922/04/29/103588246\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biblia\.info\.pl/slownik/eliab/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biblia\.info\.pl/slownik/eliakim/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]waterford-cathedral\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]torlengua\.es/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]filmweb\.pl/film/LEGO%C2%AE+PRZYGODA+2-2019-709802'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pzrugby\.pl/download/34'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]autoevolution\.com/cars/dodge-charger-1983\.html#aeng_dodge-charger-1983-16-4mt-62-hp'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pzss\.org\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]aytobembibre\.es/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]histmag\.org/Cmentarz-zydowski-na-gdanskim-Chelmie-4677/1/1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]histmag\.org/Pojedynki-sadowe-w-Polsce-sredniowiecznej-8620;1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wbc\.macbre\.net/api/v1/documents/5725\.txt'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]naqu\.gov\.cn/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/mlachowicz/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/sebastian-grochala-b414a6106/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/dariusz-zawadka-b6584372/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/jakub-jaworowski-cfa-9762343/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/jurand-drop-167438/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/marcin-czech-23604774/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/witold-dro%C5%BCd%C5%BC-22499aba/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/anna-wypych-namiotko-17704520/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/company/indahash/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/boguslaw-nadolnik-02966276/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/beata-jaczewska-752588/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/karol-okonski-2002901/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/wanda-buk-2a349385/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/john-tamny-2698b56/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/alicja-omi%C4%99cka-96b396b2/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/leszekskiba/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/s%C5%82awomir-mazurek-08536090/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/andrzejjacaszek/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/jpawlowski/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/michael-hoge-919499103/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/piotr-otawski-ab26351/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/przemyslawmorysiak/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/witoldjablonski/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/arkadiusz-huzarek-3498665b/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/travis-geiselbrecht-507ba7/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/david-w-panuelo-9ab0726/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/lpwaterfront/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/mariella-mularoni-2585a5a1/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/mariusz-furmanek-54a65338/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/liwiusz-laska-221138152/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/eugeniusz-jakubaszek-7006a466/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/alexander-glogowski-57b3bb6/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/zuzanna-radzik-746367143/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/john-stubbington-4291823/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/suzanne-dekker-96526a21/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/waldemar-szajewski-baa018115/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/aleksandra-janusz-kami%C5%84ska-68705464/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/albert-borowski-9800017/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/dulnik-dariusz-743b9056/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/jerzy-cukierski-12b625104/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/marclgreenberg/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/truepiotrnowicki/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]eurovoix\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]spoilertv\.pl/aktualnosci/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]glamrap\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fembio\.org/biographie\.php/frau/biographie/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]forebears\.io/surnames/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cwkopole\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]karate-opole\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]podlaskie\.tv/sensacyjne-odkrycie-w-puszczy-knyszynskiej-o-zelaznej-zabie-na-podlasiu-juz-zapomnieli/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]www2\.arnes\.si/~gljsentvid10/Praga_prestolnica_zgodovine_casa2013\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jstor\.org/journal/mycologia'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fiaworldrallycross\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bilet\.kolejeslaskie\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]automatykab2b\.pl/kalendarium/48213-nowoczesne-roboty-przejmuja-coraz-wiecej-zadan'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tychy\.pl/2018/09/05/krzysztof-sitko-nie-zyje/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cyclones\.com/sports/mens-basketball/roster/matt-thomas/8161'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]koelleda\.de/index\.php/startseite\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jamainternalmedicine/fullarticle/414643'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jama/fullarticle/187347'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jamainternalmedicine/fullarticle/1106080'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jama/fullarticle/2524189'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jamaophthalmology/fullarticle/424640'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]konkurs-zurowski\.pl/portrety-krytykow'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]acropolis-en\.skakistikiakadimia\.gr'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]adventskalenderkopen\.nl/wat-is-een-adventskalender'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wh-trc\.org'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kuriles\.ru'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]data\.aad\.gov\.au/aadc/gaz'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sztetl\.org\.pl/pl/slownik'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sztetl\.org\.pl/pl/miejscowosci'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pomeranica\.pl/wiki'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ninjatune\.net/artist'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ninjatune\.net/release'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gopsusports\.com/sports'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]coursera\.org/courses'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]adria-mobil-cycling\.com/sl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]snowpatrol\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mbst-terapia\.pl/osteoporoza'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]frontflieger\.de/2-js01\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gismap\.by'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]catalog\.afi\.com/Film/51494-THE-FARCOUNTRY\?sid=1c536d70-721a-4581-af30-4cf94d37a058&sr=8\.377865&cp=1&pos=0'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jama/fullarticle/182920'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jamapediatrics/fullarticle/384214'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jamaophthalmology/fullarticle/412728'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jama/fullarticle/184015'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jamaophthalmology/article-abstract/618305'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jamaophthalmology'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jamapediatrics/fullarticle/2091622'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jama/fullarticle/184014'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jamanetwork\.com/journals/jamapsychiatry/fullarticle/481868'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]developer\.nvidia\.com/opencl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]roxymusic\.co\.uk'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]grunwald600\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zerkow\.pl/asp/pl_start\.asp\?typ=13&sub=6&menu=43&artykul=1115&akcja=artykul'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sztetl\.org\.pl/pl/media/45478-kamionka-cmentarz-zydowski-macewa-fajgi-corki-jechiela'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cgm\.pl/felietony/10-najbardziej-oniryczne-plyty-wszech-czasow'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fashionista\.com'),  # bot rejected on site (masti)
    re.compile('.*[\./@]redemptor\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fjc\.gov'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dwory\.cal24\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sbc\.org\.pl/publication'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]anidb\.net/perl-bin/animedb\.pl\?show'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jstor\.org/journal/polisciequar'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tourdurwanda\.rw'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]similarweb\.com/corp/about'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wsd\.redemptor\.pl/formacja'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wody\.gov\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zoeblen\.tirol\.gv\.at'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]usosweb\.uni\.wroc\.pl/kontroler\.php\?_action=actionx%3Akatalog2%2Fosoby%2FpokazOsobe\(os_id%3A118930\)&lang=2'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]perseus\.tufts\.edu/hopper/text\?doc=Perseus%3Atext%3A1999\.04\.0057%3Aentry%3De\(%2Fsperos\)'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]perseus\.tufts\.edu/hopper/text\?doc=Perseus%3Atext%3A1999\.04\.0057%3Aalphabetic+letter%3D*e%3Aentry+group%3D303%3Aentry%3D*eu%29%3Dros'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]perseus\.tufts\.edu/hopper/text\?doc=Perseus%3Atext%3A1999\.04\.0059%3Aentry%3Dgeminatio'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]perseus\.tufts\.edu/hopper/text\?doc=Perseus%3Atext%3A1999\.04\.0057%3Aentry%3Da\)posiw%2Fphsis'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]perseus\.tufts\.edu/hopper/text\?doc=Perseus%3Atext%3A1999\.04\.0057%3Aentry%3De%29kfw%2Fnhsis'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]worldcpday\.org'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]castlebar\.ie'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pielgrzymka\.diecezjatorun\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kir\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pkoziol\.cal24\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.riccione\.rn\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]it\.cathopedia\.org'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comuneditarvisio\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]parafianmp\.cal24\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]vuzenica\.si'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cm-coimbra\.pt'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]audioriver\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]laheda\.ee'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]stadtpfarrfriedhof-baden\.at'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]trieben\.net'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]alvsbyn\.se'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mlb\.com/mets/video/cano-s-clutch-rbi-single'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mlb\.com/video/robinson-cano-homers-1-on-a-fly-ball-to-center-field'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]liezen\.at'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]friedberg\.de'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mestojablonec\.cz/cs/magistrat/informace/zpravy/aktualni-zpravy/novym-primatorem-jablonce-nad-nisou-se-stal-jiri-cerovsky\.html'),  # bot rejected on site (masti, szoltys)

    re.compile('.*[\./@]kampinoski-pn\.gov\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]atptour\.com/en/scores/archive'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cec\.org\.co/episcopado'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]katalog\.czasopism\.pl/index\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]techinasia\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kvr\.kpd\.lt/#/static-heritage-detail/4ffd98b9-dc7b-4a81-b330-80f787c5fae3'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.flussio\.or\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]12thman\.com/news/2017/8/4/womens-basketball-danielle-adams-named-to-texas-am-athletic-hall-of-fame\.aspx'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]parrocchiasancamillo\.net/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ildivomovie\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]santandrea\.teatinos\.org/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mosonmagyarovar\.hu/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]santiago-ixcuintla\.gob\.mx/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]klana\.hr/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]saultstemarie\.ca/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]google\.pl/search\?hl=pl&biw=1280&bih=684&tbm=bks&tbm=bks&q=inauthor:%22Mieczys%C5%82aw+Bilek%22&sa=X&ei=9_GyU9baNczZ4QT-soHwDQ&ved=0CCwQ9AgwAg#hl=pl&q=inauthor:%22Mieczys%C5%82aw+Bilek%22&tbm=bks'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]newsweek\.com/2019/04/05/10-best-hospitals-world-1368512\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]newsweek\.com/houses-hidden-100621'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]newsweek\.com/scutoid-scientists-discover-entirely-new-shape-and-its-been-hiding-inside-1045097'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]newsweek\.com/stanford-prison-experiment-age-justice-reform-359247'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]newsweek\.com/total-free-fall-195938'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]newsweek\.com/ukraine-two-russian-spies-arrested-double-agents-inside-kievs-own-ranks-755504'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]newsweek\.com/worlds-healthiest-cities-ranked-1062277'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]newsweek\.com/wwe-crown-jewel-hulk-hogan-video-1199206'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]instagram\.com/armani/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]instagram\.com/mocni_w_duchu/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bigband\.palac\.bydgoszcz\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]eurowizja\.tvp\.pl/27311750/2016-margaret-cool-me-down-elephant'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]plock\.luteranie\.pl/index\.php\?r=pages/view&id=4'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pmi\.org/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]usosweb\.uw\.edu\.pl/kontroler\.php\?_action=actionx:katalog2/przedmioty/pokazPrzedmiot\(prz_kod:3502-529'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]usosweb\.uw\.edu\.pl/kontroler\.php\?_action=actionx:katalog2/przedmioty/pokazZajecia\(zaj_cyk_id:219631;gr_nr:1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]usosweb\.uw\.edu\.pl/kontroler\.php\?_action=actionx:katalog2/osoby/pokazOsobe\(os_id:13184'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]owsiaknet\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]city\.sunagawa\.hokkaido\.jp/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]reims\.fr/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]santanadavargem\.mg\.gov\.br/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ville-rochefort\.fr/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gopurpleaces\.com/news/2018/3/22/ue-agrees-to-terms-with-walter-mccarty-to-become-head-mens-basketball-coach\.aspx'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.villanova-mondovi\.cn\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.vicari\.pa\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.casalvieri\.fr\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.casalnuovo\.na\.it/hh/index\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.careri\.rc\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.capodimonte\.vt\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.campodimele\.lt\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comunecampodigiove\.it/it-it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.brittoli\.pe\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.agropoli\.sa\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.castelforte\.lt\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.chieve\.cr\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.colledimacine\.ch\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comunedicoreno\.eu/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.cusano-milanino\.mi\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.trequanda\.si\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.torrile\.pr\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.torrice\.fr\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.tarantapeligna\.ch\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.settimosanpietro\.ca\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.selargius\.ca\.it/sitoistituzionale/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.deliceto\.fg\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.ruda\.ud\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.rozzano\.mi\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.roccabianca\.pr\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.ripaltacremasca\.cr\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.prignano\.mo\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.pralboino\.bs\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fonte-nuova\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sarpsborg\.com/kultur-og-fritid/idrettsanlegg/#heading-h2-6'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.brandico\.bs\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]newsweek\.com/denny-hamlin-wins-daytona-500-results-2020-daytona-500-big-crash-15-laps-go-1487698'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]noir\.pl/autorzy/128'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pubs\.geoscienceworld\.org/gsa/gsabulletin/article-abstract/100/9/1400/182200/Anomalously-young-volcanoes-on-old-hot-spot-traces'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pubs\.geoscienceworld\.org/gsa/geology/article/44/10/847/195063/Extensive-Noachian-fluvial-systems-in-Arabia-Terra'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]codaworx\.com/projects/glass-sphere-the-united-earth-in-the-european-parliament-building-lower-silesian-chamber-of-commerce/'),   # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]yanbian\.gov\.cn/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jti\.com/pl/europe/poland'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kolbiel\.pl/asp/pl_start\.asp\?typ=14&sub=3&subsub=43&menu=80&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]region\.krasu\.ru/cities'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kvr\.kpd\.lt/#static-heritage'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]retropress\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]buin\.cl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]concellodefriol\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.sannicolaarcella\.cs\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]trbovlje\.si'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pontedipiave\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]villanueva\.gob\.ar/web'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.pescantina\.vr\.it/hh/index\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.formia\.lt\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.formigine\.mo\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.pauliarbarei\.su\.it/it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.pau\.or\.it/it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.pandino\.cr\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.frassinoro\.mo\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.pancarana\.pv\.it/portal'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.palagano\.mo\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comunediortucchio\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.novara\.it/it/home'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.catania\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]miradordelriovictoria\.com\.ar/web'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.gorgoglione\.mt\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comuneguiglia\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.mosciano\.te\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.longhena\.bs\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.montegrino-valtravaglia\.va\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.montefiorino\.mo\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comunedicanicattinibagni\.it/web'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]comune\.capaccio\.sa\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]curtatone\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]prope\.jp'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]buffalony\.gov'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]web\.molina\.cl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ntagil\.org'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]urbanet\.info/kampala-local-economic-development'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]samokov\.bg'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]alpharetta\.ga\.us'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sfscon\.it/speakers/arno-kompatscher'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cittametropolitana\.ba\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]baltimorecity\.gov'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]res\.krasu\.ru/exlibris/hist/hist5\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]vereya\.ru'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dalnegorsk\.ru'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mairie-panazol\.fr'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]saintmauricedrome\.fr'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ksiazkoweklimaty\.pl/author/71/max-blecher'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ksiazkoweklimaty\.pl/author/42/monika-kompan%C3%ADkov%C3%A1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]koscian\.net/Fenomen_regionalizmu,32933\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]roanoke\.com/hokies/sidney-cook-of-virginia-tech-perseveres-in-her-college-career/article_a2ef0fbd-e547-501e-8040-343afb260e2c\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lekarzepowstania\.pl/osoba/zygmunt-gilewicz-narkotyk'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sbj6\.com\.br'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mairie-altkirch\.fr'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]timesmachine\.nytimes\.com/timesmachine/1922/01/31/109336514\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]timesmachine\.nytimes\.com/timesmachine/1922/12/06/98793891\.pdf'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gamesfanatic\.pl/2016/01/21/tajniacy'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gamesfanatic\.pl/2016/10/29/dominion-rog-obfitosci'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gamesfanatic\.pl/category/gra-roku/edycja-2016'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gamesfanatic\.pl/2010/12/16/gamedec-czyli-cyberpunkowa-gra-planszowa'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]generaltoshevo\.bg'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]varshets\.info'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]townsville-port\.com\.au'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]aquaparkelsurillal\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]buenafe\.gob\.ec'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]admmaloyaroslavec\.ru/en'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ku96\.ru'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cityofwashougal\.us'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tualatinoregon\.gov'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wici\.info'),  # bot rejected on site (masti, Kynikos)
    re.compile('.*[\./@]musixmatch\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wattpad\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dts24\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fchd\.info'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]divers24\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]aviafrance\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]encyklopedia\.warmia\.mazury\.pl/index\.php'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ladek\.pl/gmina/solectwa'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ruj\.uj\.edu\.pl/xmlui/handle/item/49688'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]krd\.edu\.pl/projekty/prodok-propan/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]utahutes\.com/news/2017/3/6/mens-basketball-kuzma-named-to-all-pac-12-first-team\.aspx'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]misja\.org\.pl/o-nas/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hirm\.gv\.at/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]msuspartans\.com/sports/mens-soccer/roster/ken-krolicki/3368'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]naia\.org/schools/index'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]naia\.org/sports/mwrest/index'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]liverpoolecho\.co\.uk/all-about/hillsborough'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]liverpoolecho\.co\.uk/news/liverpool-news/pope-francis-deeply-moved-death-14588600'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]liverpoolecho\.co\.uk/news/tv/coronation-street-star-helen-flanagan-14821354'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]liverpoolecho\.co\.uk/news/tv/little-mix-star-jesy-nelsons-17646363'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]liverpoolecho\.co\.uk/sport/football/football-news/amazing-statistics-prove-nicolas-pepe-16448598'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]liverpoolecho\.co\.uk/sport/football/football-news/ian-st-john-liverpool-breaking-19944559'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]invaluable\.com/artist/doncker-hendrick-aw324xu2ns/sold-at-auction-prices/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]invaluable\.com/auction-lot/carsten-henrichsen-danish,-1824-1897-view-of-no-247-c-a054142544'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]invaluable\.com/auction-lot/mateusz-gawrys-1926-2003-landscape-1999-44-c-62948ec9a0'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]muzeum\.tarnow\.pl/zwiedzanie/oddzialy/siedziba/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]stmartin\.at/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]odusports\.com/sports/2019/9/16/208424706\.aspx'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lakeway-tx\.gov/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nashville\.gov/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]expedia\.co\.uk/Anacaona-Park-Constanza\.d553248621579693577\.Attraction'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wattpad\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]news\.lockheedmartin\.com/2018-03-28-Lockheed-Martin-Poland-Sign-Agreement-for-Hit-to-Kill-PAC-3-MSE-Missile'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rep\.adw-goe\.de/bitstream/handle/11858/00-001S-0000-0023-9B0C-3/WOB%206%20Die%20Ortsnamen%20des%20Hochsauerlandkreises\.pdf\?sequence=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bible-history\.com/map-israel-joshua/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]harpercollins\.com/blogs/authors/katherine-applegate'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fightingillini\.com/news/2017/6/9/former-illini-mike-poeta-named-assistant-wrestling-coach\.aspx\?path=wrestling'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fightingillini\.com/news/2018/3/26/wrestling-isaiah-martinez-named-to-usa-world-cup-team\.aspx\?path=wrestling'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hailstate\.com/sports/mens-basketball/roster/malik-newman/3354'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pulaskitown\.org/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rockwall\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]springfieldmo\.gov/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sgcity\.org/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]binhphuoc\.gov\.vn/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bursa-kerja\.ptkpt\.net/id4/112-1/I-Turn-To-You_244078_stikom-bali_bursa-kerja-ptkpt\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]izardcountyar\.org/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]madisonco\.virginia\.gov/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ongov\.net/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cityofmanistique\.org/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]co\.somerset\.pa\.us/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]quangtri\.gov\.vn/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cmentarzcentralny\.szczecin\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jizzine\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]chonburicity\.go\.th/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mytyshi\.ru/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cabanatuancity\.gov\.ph/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hasbayya\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rashaya\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]secowarwick\.com/pl/ospolce/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]stanislawdeja\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]snsinfo\.ifpan\.edu\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]village\.homewood\.il\.us/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lakebarrington\.org/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]villagemedina\.org/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]oakwoodvillageoh\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]villageofstevensville\.us/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]westmont\.illinois\.gov/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]marekszyszko\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ppr\.pl/wiadomosci/aktualnosci/nowy-podsekretarz-stanu-w-mrirw-122950'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lsusports\.net/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bankizywnosci\.pl/kontakt/banki-zywnosci/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]read\.dukeupress\.edu/eighteenth-century-life/article-abstract/34/3/51/721/Rousseau-and-Feminist-Revision'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]read\.dukeupress\.edu/environmental-humanities/article/6/1/159/8110/Anthropocene-Capitalocene-Plantationocene'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]read\.dukeupress\.edu/hope/article-abstract/41/2/271/92483/Charles-Dunoyer-and-the-Emergence-of-the-Idea-of'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]read\.dukeupress\.edu/tsq/article/3/1-2/5/91824/IntroductionTrans-Feminisms'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]beskid-maly\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bvbinfo\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]carrowkeel\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wuac\.info/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bramtankink\.nl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zydowskicmentarzdzierzoniow\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kwidzynopedia\.pl/index\.php\?title=Brachlewo'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]xjblk\.gov\.cn/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bobrzany\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]brudzen\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]es\.athlet\.org/futbol/copa-del-caribe/1989/clasificacion/grupo-a'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]es\.athlet\.org/futbol/copa-del-caribe/1989/clasificacion/grupo-b'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]es\.athlet\.org/futbol/copa-del-caribe/1989/clasificacion/grupo-c'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]works\.doklad\.ru/view/bBLUCdOQu-w/all\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]battleships-cruisers\.co\.uk/habsburg_class\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lehighsports\.com/sports/wrestling/roster/coaches/steve-mocco/1276'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cefaly\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]street-viewer\.ru/tula/street/rudneva-ulica/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zbigniewloskot\.pl/pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lazarica\.rs/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nachtkabarett\.com/AlchemyAndKabbalah/ZimZum'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]skk\.pzkregl\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]harrypotter\.fandom\.com/pl/wiki/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pcn\.minambiente\.it/viewer/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rcin\.org\.pl/publication/21101'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rcin\.org\.pl/dlibra/publication/36703'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rcin\.org\.pl/dlibra/publication/39990'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gomitaro\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]teologia\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cass\.net\.cn/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]altanen\.dk/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hannieschaft\.nl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]trumphotels\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hanasakuiroha\.jp/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jirnsum\.com/atje-keulen-deelstra-74-overleden/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]allmusic\.com/album/pleasures-pave-sewers-mw0000054662'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]allmusic\.com/album/private-audition-mw0000650244'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]allmusic\.com/album/the-lexicon-of-love-mw0000649803w'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]olsztyn24\.com/news'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]acad\.ro/bdar'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]altierospinelli\.org'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]terebess\.hu'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kristall-saratov\.ru'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://parafia-panienka\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://wiki\.meteoritica\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://chelm\.mojeosiedle\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://polaneis\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]daviscup\.com/en/draws-results/tie\.aspx\?id=M-DC'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]usopen\.org/en_US/scores/stats/54101\.html\?promo=matchchanger'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]daviscup\.com/en/draws-results/group-iii/americas/2018\.aspx'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]trbovlje\.si/'),  # bot rejected on site (masti, szoltys)
    re.compile(
        '.*[\./@]ubitennis\.net/2017/12/roof-roland-garros-stadium-court-phillippe-chatrier-plans-motion-video/'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]esri\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile(
        '.*[\./@]dalmacijadanas\.hr/nova-hit-rekreativna-zona-splicana-setnica-uz-rijeku-zrnovnicu-do-usca-u-stobrecu/'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sherlockian\.net/hounds-summary/blan-hounds/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mixmag\.net/read/tokimonsta-jon-hopkins-and-justice-nominated-for-grammy-awards-news'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]oetker\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]redstormsports\.com/sports/mens-basketball/roster/tariq-owens/375'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]crittersbuggin\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]johanniskirchturm\.de/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]en\.tengrinews\.kz/people/24-year-old-gets-into-the-forbes-list-of-100-richest-people-23871/'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tengrinews\.kz/sports/skonchalsya-izvestnyiy-kazahstanskiy-jurnalist-i-kommentator-407310/'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tengrinews\.kz/kazakhstan_news/umer-byivshiy-predsedatel-kgb-kazahskoy-ssr-zakash-317619/'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]www2\.fbi\.gov/wanted/topten/fugitives/bulger\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cambridge-news\.co\.uk/news/uk-world-news/bernard-giles-serial-killer-crimes-15798955'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lhf\.lv/lv/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lincolnshirelive\.co\.uk/sport/other-sport/golden-girl-georgie-twigg-announces-1852795'),
    # bot rejected on site (masti, szoltys)
    re.compile(
        '.*[\./@]newsweek\.com/who-was-elisa-leonida-zamfirescu-facts-and-quotes-one-worlds-first-women-1210496'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bioguideretro\.congress\.gov/Home/MemberDetails\?memIndex=t000057'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]linkedin\.com/in/krzysztof-landa-%C5%82anda-03727515a/'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ec\.bialystok\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]indiapost\.gov\.in/vas/pages/findpincode\.aspx'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://tarnopol\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]esm\.rochester\.edu/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zspryglice\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]collegeslam\.com/2019Results'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hockeycanada\.ca/en-ca/news/tsn-rds-to-remain-hockey-canada-home'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hokej-bialystok\.pl/druzyna-adh/aktualnosci/92-pierwsze-ligowe-punkty-w-sezonie-2012-13'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]cska-hockey\.ru/club/rukovodstvo/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hcmvd\.ru/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]katalog\.rajska\.info/0631900294031/ksiazka/encyklopedia-pedagogiczna-xxi-wieku'),
    # bot rejected on site (masti, szoltys)
    re.compile(
        '.*[\./@]katalog\.rajska\.info/search/description\?q=Nowak%2C+Ewa+%281941-+%29&index=7&rp=50&f4%5B0%5D=1&s=author_asc'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://niedzwiedzie\.sanok\.pl/aktualnosci/6-turniej-w-sanoku'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hockeydb\.com/ihdb/draft/nhl2000e\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://orlikopole\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile(
        '.*[\./@]# http://easternhockey\.stats\.pointstreak\.com/playerpage\.html\?playerid=712406&seasonid=2025'),
    # bot rejected on site (masti, szoltys)
    re.compile(
        '.*[\./@]# http://eihcpolesie\.stats\.pointstreak\.com/en/playerpage\.html\?playerid=3490460&seasonid=4928'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://rebase\.neb\.com/rebase/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]motorsport\.hyundai\.com/ott-signs-for-two-years/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]journals\.lib\.unb\.ca/index\.php/scl/article/view/8114/9171'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]miegon\.tokraw\.pl/zyciorys\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]seminarium\.wloclawek\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]modbee\.com/news/local/article231678328\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pinczow\.com/turystyka/slawne-znane-postacie-zwiazane-ziemia-pinczowska/'),
    # bot rejected on site (masti, szoltys)
    re.compile(
        '.*[\./@]radiowarszawa\.com\.pl/ks-stanislaw-jurczuk-posmiertnie-odznaczony-krzyzem-kawalerskim-orderu-odrodzenia-polski/'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]duch\.koszalin\.opoka\.org\.pl/gazetka/naszezycie65/skrzatusz\.html'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]karmelwadowice\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wioskaindianska\.eu/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sbdiocese\.org/bishops/delriego\.cfm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://diocesedecaxiasdomaranhao\.org/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]parafiarozborz\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://hiroshima\.catholic\.jp/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://czernichow\.duszpasterstwa\.bielsko\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]parafiawolkapanienska\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]changbai\.gov\.cn/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]diocesistabasco\.org\.mx/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]chiesasavona\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://mbozejlubartow\.pl/duszpasterze/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]obispadorqta\.org\.ar/v3/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zorymb\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sacredheartdanbury\.org/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]narodzenianmp\.wloclawek\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]parafiaoleszyce\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://kresowe\.pl/wpieramy-polski-kosciol-w-stryju/'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nurt\.kck\.com\.pl/index\.php/jury/komisja-artystyczna/280-maria-malatyska'),
    # bot rejected on site (masti, szoltys)
    re.compile(
        '.*[\./@]nurt\.kck\.com\.pl/index\.php\?option=com_content&view=article&id=124:informacja-o-przyznanych-nagrodach-2010&catid=35:2010&Itemid=58&lang=pl'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]chelm\.mojeosiedle\.pl/fakt\.php\?fid=283&spi=2'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://bc\.wbp\.lublin\.pl/dlibra/docmetadata\?id=21371&from=publication'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://bc\.wbp\.lublin\.pl/dlibra/docmetadata\?id=3218&from=publication'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]edvinohrstrom\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://nplit\.ru/books/item/f00/s00/z0000040/index\.shtml'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]krzyz-zawada\.katowice\.opoka\.org\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]parafia-piatnica\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://parafiaswietejtrojcy\.boguszow-gorce\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]oczamiduszy\.pl/stygmaty-sw-franciszka/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://parafiachwarstnica\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kozalwagrowiec\.pl/nasz-kosciol/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://antoni-reda\.pl/wp/istotne-daty/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://mikolaj\.siedliska\.info/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://strumien\.duszpasterstwa\.bielsko\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]parafiachotow\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]syriac-catholic\.org/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://roczyny\.duszpasterstwa\.bielsko\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]arytmia\.eu/niezwykle-zwykle-zycie-w-swiecie-wedlug-ludwiczka/'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]arytmia\.eu/mad-men-serial-ktory-szanuje-widza/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://wolarusinowska\.cba\.pl/parafia/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://sosnicowice\.opw\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://parafia\.elacko\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://parafiastaryzmigrod\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]parswkazimierzaleszno\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]turbia\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile(
        '.*[\./@]powiat-plonski\.pl/pl/prezentacjapowiatu/turystykawpowiecie/najciekawsze-koscioly-powiatu-plonskiego\.html'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]maksymilian\.eu/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pisarzowice\.duszpasterstwa\.bielsko\.pl/historia\.php'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]parafia\.czerwonka\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]# http://parafia\.dolsk\.info\.pl/asp/pl_start\.asp\?typ=14&menu=77&strona=1'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]poddebicki\.pl/asp/zabytki,264,,1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]parafiaswstanislawa\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]regestry\.lubgens\.eu/viewpage\.php\?page_id=1052&par=395'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]parafiabiedrusko\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]krosnowojciech\.przemyska\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jstage\.jst\.go\.jp'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]satkurier\.pl/news'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]istoriya-kino\.ru/kinematograf/item'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bip\.pomorskie\.eu'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]legislacja\.rcl\.gov\.pl/projekt'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]adf-gallery\.com\.au'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]archiwum\.sky-watcher\.pl/content'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]opowiecie\.info'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wikizaglebie\.pl/wiki'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wow\.gm/africa/gambia/article'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]digital\.library\.unt\.edu'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nrc\.gov'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]interq\.or\.jp'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]movieway\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]visual-memory\.co\.uk'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]thelyricarchive\.com'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]galeria\.mojeosiedle\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gingergeneration\.it'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gdynia-oksywie\.mojeosiedle\.pl'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hrfilm\.hr'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ptakiegzotyczne\.net'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]actupny\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]campionatoprimavera\.com/giocatori/derossi/derossi/derossi\.html'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]na\.icreb\.org/2006-argiope-brunnich-spider-description-of-a-yellow-blac\.html'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]haf\.gr/en/history/historical-aircraft/fairey-battle-b-1/'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gdansk-orunia\.mojeosiedle\.pl/\?gdansk-orunia=gdansk-orunia'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]morena\.mojeosiedle\.pl/gal\.php\?&g=5&m=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gdansk-nowy-port\.mojeosiedle\.pl/viewtopic\.php\?t=39585'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gdansk-lostowice\.mojeosiedle\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gdansk-ujescisko\.mojeosiedle\.pl/viewtopic\.php\?t=17500'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]info\.filg\.uj\.edu\.pl/ifk/knfkuj/\?page_id=75'),  # bot rejected on site (masti, szoltys)
    re.compile(
        '.*[\./@]foxsports\.com\.au/football/a-league/roy-krishna-and-christine-nairn-were-the-big-winners-at-the-dolan-warren-awards-in-sydney/news-story/c6dcdbc125f7986e59676d24c24e0ef8'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rodionova\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]worldathletics\.org/athletes/biographies/letter=v/country=cze/athcode=240921/index\.html'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]microsoft\.com/pl-pl/useterms'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]romanianliteraturenow\.com/authors/adriana-bittel/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mnlr\.ro/case-memoriale/casa-memoriala-george-si-agatha-bacovia/'),
    # bot rejected on site (masti, szoltys)
    re.compile(
        '.*[\./@]independent\.co\.uk/arts-entertainment/music/reviews/album-reviews-wilco-wilco-schmilco-jack-white-acoustic-recordings-mia-aim-and-more-a7232056\.html'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]reliefweb\.int/report/japan/japan-prefectures-open-shelters-tsunami-survivors'),
    # bot rejected on site (masti, szoltys)
    re.compile(
        '.*[\./@]measuringworth\.com/calculators/exchange/result_exchall\.php\?action=&iyear=1931&dyear=2014&ivalue=115&itype=pound'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]films-sans-frontieres\.fr/laviesansprincipe/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]namu\.wiki/w/%EB%A1%9C%EB%B3%B4%ED%8A%B8%20%ED%82%B9'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]truetears\.jp/index\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lesne-zacisze\.net/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]thekitchn\.com/when-healthy-eating-becomes-a-bad-thing-orthorexia-254259'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]glartent\.com/PL/Katowice/124535997641054/Galeria-Pi%C4%99tro-Wy%C5%BCej'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rs-online\.com/designspark/running-george-3-on-a-raspberry-pi'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]eintracht-trier\.com/stadion/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]eintracht-trier\.com/geschichte/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]backstage\.com/resources/detail/productionlisting/the-laundromat-86794/'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]backstage\.com/uk/magazine/article/netflix-stranger-kadiff-kirwan-70153/'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]janosik\.terchova-info\.sk/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]doyouknowturkey\.com/soz-the-oath-series-special-forces-of-turkish-television/'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]sincity-2\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]glartent\.com/PL/Gliwice/1688978184651818/Rockin%27-Silesia'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]steeton\.net/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]teatrtv\.vod\.tvp\.pl/594085/samolot-do-londynu'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]stengazeta\.net/\?p=10002396'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]manana\.pl/pl/component/k2/72-nieulotne\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tvdrama-db\.com/drama_info/p/id-39512'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]femmefatalethemovie\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]whoscored\.com/Players/77056/Show/Alban-Pnishi'),  # bot rejected on site (masti, szoltys)
    re.compile(
        '.*[\./@]dziennikpolski24\.pl/potomek-rodziny-buchalow-z-wysokiej-ktora-ocalila-romana-polanskiego-podczas-okupacji-otrzymal-medal-od-izraela/ar/c13-15236717'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]soundcloud\.com/micrec-publishing/fomins-kleins-dziesma-par-1/sets'),
    # bot rejected on site (masti, szoltys)
    re.compile(
        '.*[\./@]radioradicale\.it/scheda/528218/intervista-a-gabriele-panizzi-gia-presidente-della-regione-lazio-sulla-sua-iscrizione\?i=3791862'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]francescosalvi\.it/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]swiatmlodych\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile(
        '.*[\./@]semanticscholar\.org/paper/An-updated-classification-of-Orchidaceae-Chase-Chase/a0d6040ee391286d94cf594ffa4edb2b343838b1'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]deathmagnetic\.pl/naszym-zdaniem/recenzje/decapitated-recenzja-albumu-anticult/'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rtvslo\.si/slovenija/marjan-sarec-v-vladni-palaci-ze-prevzel-premierske-posle/465770'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biol-chem\.uwb\.edu\.pl/aktualnosci/jak-ustalic-tozsamosc-dzieciola-339/'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]steamdb\.info/app/324160/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]monsoongroup\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]dinosaur-world\.com/feathered_dinosaurs/dromaeosaurus_albertensis\.htm'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]taxonsearch\.uchicago\.edu/\?exe=browse&ke=key'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jboyd\.net/Taxo/List22\.html#cettiidae'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]jboyd\.net/Taxo/List29\.html#fringillidae'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]birdinfo\.co\.uk/sites/Mules_Hybrids/goldfinch_crosses\.htm'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]wingspan\.co\.nz/birds_of_prey_new_zealand_falcon\.html'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]arthurgrosset\.com/sabirds/sharpbill\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pl\.russellhobbs\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]guess\.eu/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]znakitowarowe-blog\.pl/uniewazniono-znak-towarowy-szachownicy-louis-vuitton/'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kaefer-der-welt\.de/lycus_trabeatus\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]motyle-motyle\.pl/index\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]biocontrol\.entomology\.cornell\.edu/predators/Phalangium\.php'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ape-o-naut\.org/famous/famous/reallife\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]departments\.bucknell\.edu/biology/resources/msw3/browse\.asp\?s=y&id=13100002'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]zuzelend\.com/stadion\.php\?id=92'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]peoples\.ru/tv/kevin_s__bright/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]peoples\.ru/sport/trainer/vladimir_alikin/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rymanow\.pl/asp/pl_start\.asp\?typ=13&sub=0&subsub=0&menu=8&artykul=3714&akcja=artykul'),
    # bot rejected on site (masti, szoltys)
    re.compile(
        '.*[\./@]fis-ski\.com/DB/DB/cross-country/calendar-results\.html\?eventselection=&place=&sectorcode=CC&seasoncode=2020&categorycode=SCAN&disciplinecode=&gendercode=&racedate=&racecodex=&nationcode=&seasonmonth=X-2020&saveselection=-1&seasonselection='),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]nabiegowkach\.pl/Sprzet/index\.php\?option=com_k2&view=item&id=40&Itemid=3'),
    # bot rejected on site (masti, szoltys)
    re.compile(
        '.*[\./@]wiesentbote\.de/2018/07/25/neue-gegentribuene-im-bayreuther-hans-walter-wild-stadion-die-arbeiten-beginnen-frueher/'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]bibliographie\.uni-tuebingen\.de/xmlui/handle/10900/37173'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]lengvoji\.lt/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]instagram\.com/p/BbUQvkSj-np/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]hardingsports\.com/news/2006/3/9/Track%20regional%20awards\.aspx\?path=mtrack'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]blog\.pgd\.pl/historia-shelby-droga-carrolla-shelbyego-przez-ciernie-do-chwaly/'),
    # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]whiplash.net/materias'),  # bot rejected on site (masti, Revsson)
    re.compile('.*[\./@]eddies.it/'),  # bot rejected on site (masti, Revsson)
    re.compile('.*[\./@]belfastlive.co.uk/news/tv/belsonic-ticket-warning-summer-shows-17809395'),  # bot rejected on site (masti, Revsson)
    re.compile('.*[\./@]allmusic\.com/album/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]allmusic\.com/artist/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]um\.poniatowa\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]obserwatoriumedukacji\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]interfacebus\.com/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]solofutbol\.cl/seleccion%20chilena/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]am-sur\.com/am-sur/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ipn\.gov\.pl/pl/publikacje/periodyki-ipn/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ndrugs\.com/\?s=simfibrate'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fscimage\.fishersci\.com/msds/01139\.htm'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]szps\.pl/historia/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]um\.poniatowa\.pl/asp/pl_start\.asp\?typ=14&sub=16&menu=29&strona=1'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]must-see\.top/reki-kurskoy-oblasti/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]docplayer\.pl/7826029-Hale-o-konstrukcji-slupowo-ryglowej\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]diginole\.lib\.fsu\.edu/islandora/object/fsu%3A274058'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]rotbewegt\.at/#/epoche/1889-1918/artikel/emma-adler'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fujian\.gov\.cn/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]fusong\.gov\.cn/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]parafiagabon\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]pricemole\.io/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]kop\.ipn\.gov\.pl/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]filmfestivals\.com/blog/awardswatch/winners_golden_calves_netherlands_film_festival_2017_announced'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]www1\.wdr\.de/radio/cosmo/programm/sendungen/radio-po-polsku/polska-muzyka-w-niemczech-madlen-100\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]krakowski-kazimierz\.pl/majer_balaban_18771942/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]tawernaskipperow\.pl/czytelnia/slownik/majtek-czyli-specjalista-od-tentegowania/5846'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]newsweek\.com/watercolor-painting-adolf-hitler-sells-161000-286414'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]thesac\.com/sports/msoc/2012-13/players/makonnanclarelqgd'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]if-pan\.krakow\.pl/pl/aktualnosci/aktualnosci/Prof-dr-hab-Malgorzata-Filip-oraz-prof-dr-hab-Ryszard-Przewlocki-wybrani-na-czlonkow-korespondentow-Polskiej-Akademii-Nauk-prof-dr-hab-Edmund-Przegalinski-laureatem-nagrody-naukowej-Prezesa-PAN/387/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]xvlo\.lodz\.pl/absolwenci\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mannadey\.in/index2\.html'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]geniuscreations\.pl/ksiazki/okup-krwi-marcin-jamiolkowski/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]gluseum\.com/PL/B%C5%82onie/140950746521639/Muzeum-Ziemi-B%C5%82o%C5%84skiej'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]foxsports\.com\.au/tennis/australian-tennis-legend-margaret-court-protests-against-qantas-for-promoting-for-samesex-marriage/news-story/c0573fe58324203a4b57d8f2d0a1fa16'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mujeresbacanas\.com/la-gran-piloto-chilena-margot-duhalde-1920-las/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]ev-akademie-tutzing\.de/'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]mariomerola\.it/ricordo\.asp'),  # bot rejected on site (masti, szoltys)
    re.compile('.*[\./@]salonliteracki\.pl'),  # bot rejected on site (masti, Revsson)
    re.compile('.*[\./@]jeuxvideo\.com'),  # bot rejected on site (masti, Revsson)
    re.compile('.*[\./@]audio\.art\.pl/2013/index.php'),  # bot rejected on site (masti, Revsson)
    re.compile('.*[\./@]bfm\.ru'),  # bot rejected on site (masti, NiktWażny)
    re.compile('.*[./@]lccn.loc.gov'),  # bot rejected on site (masti, Revsson)
    re.compile('.*[./@]svs.stat.gov.pl'),  # bot rejected on site (masti)
]


def _get_closest_memento_url(url, when=None, timegate_uri=None):
    """Get most recent memento for url."""
    if isinstance(memento_client, ImportError):
        raise memento_client

    if not when:
        when = datetime.datetime.now()

    mc = memento_client.MementoClient()
    if timegate_uri:
        mc.timegate_uri = timegate_uri

    retry_count = 0
    while retry_count <= config.max_retries:
        try:
            memento_info = mc.get_memento_info(url, when)
            break
        except (requests.exceptions.ConnectionError, MementoClientException) as e:
            error = e
            retry_count += 1
            pywikibot.sleep(config.retry_wait)
    else:
        raise error

    mementos = memento_info.get('mementos')
    if not mementos:
        raise Exception(
            'mementos not found for {0} via {1}'.format(url, timegate_uri))
    if 'closest' not in mementos:
        raise Exception(
            'closest memento not found for {0} via {1}'.format(
                url, timegate_uri))
    if 'uri' not in mementos['closest']:
        raise Exception(
            'closest memento uri not found for {0} via {1}'.format(
                url, timegate_uri))
    return mementos['closest']['uri'][0]


def get_archive_url(url):
    """Get archive URL."""
    try:
        archive = _get_closest_memento_url(
            url,
            timegate_uri='http://web.archive.org/web/')
    except Exception:
        archive = _get_closest_memento_url(
            url,
            timegate_uri='http://timetravel.mementoweb.org/webcite/timegate/')

    # FIXME: Hack for T167463: Use https instead of http for archive.org links
    if archive.startswith('http://web.archive.org'):
        archive = archive.replace('http://', 'https://', 1)
    return archive

def isarchivedlink(link):
    """
    if link is internet archive link
    :param link: string
    :return: Bool
    """
    archiveservices = [
        'archive.today',
        'archive.fo',
        'archive.is',
        'archive.li',
        'archive.md',
        'archive.ph',
        'archive.vn',
        'webcitation.org'
    ]

    pywikibot.output(f"isarchivedlink looking for {link.lower()}")
    for arch in archiveservices:
        if arch in link.lower():
            return True
    return False

def citeArchivedLink(link, wcode):
    # look if link is in cite template with non empty archive param within parsedtext (wcode)
    # or link itself is an archive
    # return True in this cases
    pywikibot.output(f"citeArchivedLink looking for {link}")
    # wcode = mwparserfromhell.parse(text)

    try:
        parent2 = wcode.get_ancestors(link)[-2]

        if not isinstance(parent2, mwparserfromhell.nodes.template.Template):
            return False

        if parent2.name.lower().startswith("cytuj"):
            return parent2.has("archiwum", ignore_empty=True)

    except IndexError:
        return False

    return False

def weblinksIn(text, withoutBracketed=False, onlyBracketed=False):
    """
    Yield web links from text.

    TODO: move to mwparserfromhell
    """
    text = textlib.removeDisabledParts(text)
    parsed = mwparserfromhell.parse(text)
    for link in parsed.ifilter_external_links():
        if not isarchivedlink(link.url) and not citeArchivedLink(link, parsed):  # check if link is archived
            yield str(link.url)

    """
    # Ignore links in fullurl template
    text = re.sub(r'{{\s?fullurl:.[^}]*}}', '', text)

    # MediaWiki parses templates before parsing external links. Thus, there
    # might be a | or a } directly after a URL which does not belong to
    # the URL itself.

    # First, remove the curly braces of inner templates:
    nestedTemplateR = re.compile(r'{{([^}]*?){{(.*?)}}(.*?)}}')
    while nestedTemplateR.search(text):
        text = nestedTemplateR.sub(r'{{\1 \2 \3}}', text)

    # Then blow up the templates with spaces so that the | and }} will not
    # be regarded as part of the link:.
    templateWithParamsR = re.compile(r'{{([^}]*?[^ ])\|([^ ][^}]*?)}}',
                                     re.DOTALL)
    while templateWithParamsR.search(text):
        text = templateWithParamsR.sub(r'{{ \1 | \2 }}', text)

    # Add <blank> at the end of a template
    # URL as last param of multiline template would not be correct
    text = text.replace('}}', ' }}')

    # Remove HTML comments in URLs as well as URLs in HTML comments.
    # Also remove text inside nowiki links etc.
    text = textlib.removeDisabledParts(text)
    linkR = textlib.compileLinkR(withoutBracketed, onlyBracketed)
    for m in linkR.finditer(text):
        if m.group('url'):
            # pywikibot.output('URL to YIELD:%s' % m.group('url'))
            if not citeArchivedLink(m.group('url'), text):
                yield m.group('url')
            else:
                # test output
                # pywikibot.output('[%s] WebLinksIn: link skipped:%s' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),m.group('url')))
                pass
        else:
            yield m.group('urlb')
    """


XmlDumpPageGenerator = partial(
    _XMLDumpPageGenerator, text_predicate=weblinksIn)


class NotAnURLError(BaseException):
    """The link is not an URL."""


class LinkCheckThread(threading.Thread):
    """A thread responsible for checking one URL.

    After checking the page, it will die.
    """

    def __init__(self, page, url, history, HTTPignore, day):
        """Initializer."""
        super().__init__()
        self.page = page
        self.url = url
        self.history = history
        self.header = {
            'Accept': 'text/xml,application/xml,application/xhtml+xml,'
                      'text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5',
            'Accept-Language': 'de-de,de;q=0.8,en-us;q=0.5,en;q=0.3',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
            'Keep-Alive': '30',
            'Connection': 'keep-alive',
        }
        # identification for debugging purposes
        # DeprecationWarning: setName() is deprecated, set the name attribute instead
        # self.setName(('{0} - {1}'.format(page.title(),
        #                                  url.encode('utf-8', 'replace'))))
        self.name = f'{page.title()} - {url.encode('utf-8', 'replace')}'
        self.HTTPignore = HTTPignore
        self._use_fake_user_agent = config.fake_user_agent_default.get(
            'weblinkchecker', False)
        self.day = day

    def run(self):
        """Run the bot."""
        ok = False
        exception = False
        ignore = False
        pywikibot.output('[{}] :Processing URL {} in page [[{}]]'
                         .format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.url,
                                 self.page.title()))
        try:
            header = self.header
            r = comms.http.fetch(
                self.url, headers=header,
                use_fake_user_agent=self._use_fake_user_agent)
        except requests.exceptions.InvalidURL:
            exception = True
            message = i18n.twtranslate(self.page.site,
                                       'weblinkchecker-badurl_msg',
                                       {'URL': self.url})
        except (pywikibot.exceptions.FatalServerError, requests.exceptions.ConnectionError, requests.exceptions.SSLError, pywikibot.exceptions.ServerError, Exception):
            exception = True
            message = 'Exception while connecting.'
            pywikibot.output('[{}] Exception while processing URL {} in page [[{}]]'
                             .format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.url,
                                     self.page.title()))
            raise
        if not exception:
            if (r.status_code != requests.codes.ok) or (r.status_code in self.HTTPignore):
                ok = True
            else:
                message = str(r.status_code)

        if (r.status_code != requests.codes.ok) and (r.status_code not in self.HTTPignore):
            message = str(r.status_code)
            pywikibot.output('*[{}]:{} links to {} - {}.'
                             .format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                     self.page.title(as_link=True), self.url,
                                     message))
            self.history.setLinkDead(self.url, message, self.page,
                                     config.weblink_dead_days)
        elif self.history.setLinkAlive(self.url):
            pywikibot.output(
                '*[{}]:Link to {} in {} is back alive.'
                    .format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.url,
                            self.page.title(as_link=True)))


class History:
    """
    Store previously found dead links.

    The URLs are dictionary keys, and
    values are lists of tuples where each tuple represents one time the URL was
    found dead. Tuples have the form (title, date, error) where title is the
    wiki page where the URL was found, date is an instance of time, and error
    is a string with error code and message.

    We assume that the first element in the list represents the first time we
    found this dead link, and the last element represents the last time.

    Example::

     dict = {
         'https://www.example.org/page': [
             ('WikiPageTitle', DATE, '404: File not found'),
             ('WikiPageName2', DATE, '404: File not found'),
         ]
     }
    """

    def __init__(self, reportThread, site=None):
        """Initializer."""
        self.reportThread = reportThread
        if not site:
            self.site = pywikibot.Site()
        else:
            self.site = site
        self.semaphore = threading.Semaphore()
        # self.datfilename = pywikibot.config.datafilepath(
        #     'deadlinks', 'deadlinks-{0}-{1}.dat'.format(self.site.family.name,
        #                                                 self.site.code))
        self.datfilename = pywikibot.config.datafilepath(
            'deadlinks', f'wlc4.deadlinks-{self.site.family.name}-{self.site.code}.dat')
        # Count the number of logged links, so that we can insert captions
        # from time to time
        self.logCount = 0
        try:
            with open(self.datfilename, 'rb') as datfile:
                self.historyDict = pickle.load(datfile)
            pywikibot.output('DICTIONARY LOADED: %i elements' % len(self.historyDict.keys()))
        except (IOError, EOFError):
            # no saved history exists yet, or history dump broken
            self.historyDict = {}
            pywikibot.output('SKIPPING INITIAL LOAD OF DATA')

    def log(self, url, error, containingPage, archiveURL):
        """Log an error report to a text file in the deadlinks subdirectory."""
        if archiveURL:
            errorReport = '* {0} ([{1} archiwum])\n'.format(url, archiveURL)
        else:
            errorReport = '* {0}\n'.format(url)
        for (pageTitle, date, error) in self.historyDict[url]:
            # ISO 8601 formulation
            isoDate = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(date))
            errorReport += '** In [[{0}]] on {1}, {2}\n'.format(
                pageTitle, isoDate, error)
        pywikibot.output('** Logging link for deletion.')
        txtfilename = pywikibot.config.datafilepath('deadlinks',
                                                    'results-{0}-{1}.txt'
                                                    .format(
                                                        self.site.family.name,
                                                        self.site.lang))
        with codecs.open(txtfilename, 'a', 'utf-8') as txtfile:
            self.logCount += 1
            if self.logCount % 30 == 0:
                # insert a caption
                txtfile.write('=== {} ===\n'
                              .format(containingPage.title()[:3]))
            txtfile.write(errorReport)

        if self.reportThread and not containingPage.isTalkPage():
            self.reportThread.report(url, errorReport, containingPage,
                                     archiveURL)

    def setLinkDead(self, url, error, page, weblink_dead_days):
        """Add the fact that the link was found dead to the .dat file."""
        with self.semaphore:
            now = time.time()
            if url in self.historyDict:
                timeSinceFirstFound = now - self.historyDict[url][0][1]
                timeSinceLastFound = now - self.historyDict[url][-1][1]
                # if the last time we found this dead link is less than an hour
                # ago, we won't save it in the history this time.
                if timeSinceLastFound > 60 * 60:
                    self.historyDict[url].append((page.title(), now, error))
                # if the first time we found this link longer than x day ago
                # (default is a week), it should probably be fixed or removed.
                # We'll list it in a file so that it can be removed manually.
                if timeSinceFirstFound > 60 * 60 * 24 * weblink_dead_days:
                    # search for archived page
                    try:
                        archiveURL = get_archive_url(url)
                    except Exception as e:
                        pywikibot.warning(
                            'get_closest_memento_url({0}) failed: {1}'.format(
                                url, e))
                        archiveURL = None
                    self.log(url, error, page, archiveURL)
            else:
                self.historyDict[url] = [(page.title(), now, error)]

    def setLinkAlive(self, url):
        """
        Record that the link is now alive.

        If link was previously found dead, remove it from the .dat file.

        @return: True if previously found dead, else returns False.
        """
        if url in self.historyDict:
            with self.semaphore, suppress(KeyError):
                del self.historyDict[url]
            return True

        return False

    def save(self):
        """Save the .dat file to disk."""
        # test output
        pywikibot.output('PICKLING %s records at %s' % (
        len(self.historyDict), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        with open(self.datfilename, 'wb') as f:
            pickle.dump(self.historyDict, f, protocol=config.pickle_protocol)


class DeadLinkReportThread(threading.Thread):
    """
    A Thread that is responsible for posting error reports on talk pages.

    There is only one DeadLinkReportThread, and it is using a semaphore to make
    sure that two LinkCheckerThreads can not access the queue at the same time.
    """

    def __init__(self):
        """Initializer."""
        super().__init__()
        self.semaphore = threading.Semaphore()
        self.queue = []
        self.finishing = False
        self.killed = False

    def report(self, url, errorReport, containingPage, archiveURL):
        """Report error on talk page of the page containing the dead link."""
        with self.semaphore:
            self.queue.append((url, errorReport, containingPage, archiveURL))

    def shutdown(self):
        """Finish thread."""
        self.finishing = True

    def kill(self):
        """Kill thread."""
        # TODO: remove if unneeded
        self.killed = True

    def run(self):
        """Run thread."""
        while not self.killed:
            if len(self.queue) == 0:
                if self.finishing:
                    break
                else:
                    time.sleep(0.1)
                    continue

            with self.semaphore:
                url, errorReport, containingPage, archiveURL = self.queue[0]
                self.queue = self.queue[1:]
                talkPage = containingPage.toggleTalkPage()
                pywikibot.output(f' Reporting dead link on {talkPage}...')
                try:
                    content = talkPage.get() + '\n'
                    if url in content:
                        pywikibot.output(f'** Dead link seems to have already been reported on {talkPage}')
                        continue
                except (pywikibot.exceptions.NoPageError, pywikibot.exceptions.IsRedirectPageError):
                    content = ''

                if archiveURL:
                    archiveMsg = archiveURL
                else:
                    archiveMsg = ''

                # new code: use polish template
                # content += u'{{Martwy link dyskusja\n | link=' + errorReport + u' | IA=' + archiveMsg + u'\n}}'
                content += f'{{{{Martwy link dyskusja\n | link={errorReport} | IA={archiveMsg}\n}}}}'

                comment = f'[[{talkPage.title()}]] Robot zgłasza niedostępny link zewnętrzny: {url}'

                try:
                    talkPage.put(content, comment)
                except pywikibot.exceptions.SpamblacklistError as error:
                    pywikibot.output(f'** SpamblacklistError while trying to change {talkPage}: {error.url}')


class WeblinkCheckerRobot(SingleSiteBot, ExistingPageBot):
    """
    Bot which will search for dead weblinks.

    It uses several LinkCheckThreads at once to process pages from generator.
    """

    def __init__(self, generator, HTTPignore=None, day=7, site=True):
        """Initializer."""
        super().__init__(generator=generator, site=site)

        if config.report_dead_links_on_talk:
            pywikibot.log('Starting talk page thread')
            reportThread = DeadLinkReportThread()
            # thread dies when program terminates
            # reportThread.setDaemon(True)
            reportThread.start()
        else:
            reportThread = None
        self.history = History(reportThread, site=self.site)
        self.HTTPignore = HTTPignore or []

        self.day = day

        # Limit the number of threads started at the same time
        self.threads = ThreadList(limit=config.max_external_links,
                                  wait_time=config.retry_wait)

    def ignored(self, url):
        for ignoreR in ignorelist:
            if ignoreR.match(url):
                return True  # url in ingnore list
        return False

    def treat_page(self):
        """Process one page."""
        page = self.current_page
        """report  page.title and time"""
        try:
            pywikibot.output(f'P:{page.title()} >>>{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
            with open("masti/pid/wlclast.log", "w") as logfile:
                logfile.write(page.title())
        except:
            pass

        for url in weblinksIn(page.text):
            if not self.ignored(url):
                pywikibot.output(f'Link [{url}]: processing')
                # Each thread will check one page, then die.
                thread = LinkCheckThread(page, url, self.history,
                                         self.HTTPignore, self.day)
                # thread dies when program terminates
                # thread.setDaemon(True)
                thread.daemon = True
                self.threads.append(thread)
            else:
                pywikibot.output(f'Link [{url}]: ignored from exception list')

def RepeatPageGenerator():
    """Generator for pages in History."""
    history = History(None)
    pageTitles = set()
    for value in history.historyDict.values():
        for entry in value:
            pageTitles.add(entry[0])
    for pageTitle in sorted(pageTitles):
        page = pywikibot.Page(pywikibot.Site(), pageTitle)
        yield page


def countLinkCheckThreads() -> int:
    """
    Count LinkCheckThread threads.

    @return: number of LinkCheckThread threads
    """
    i = 0
    for thread in threading.enumerate():
        if isinstance(thread, LinkCheckThread):
            i += 1
    return i


def main(*args):
    """
    Process command line arguments and invoke bot.

    If args is an empty list, sys.argv is used.

    @param args: command line arguments
    @type args: str
    """
    gen = None
    xmlFilename = None
    HTTPignore = []

    # Process global args and prepare generator args parser
    local_args = pywikibot.handle_args(args)
    genFactory = pagegenerators.GeneratorFactory()

    for arg in local_args:
        if arg == '-talk':
            config.report_dead_links_on_talk = True
        elif arg == '-notalk':
            config.report_dead_links_on_talk = False
        elif arg == '-repeat':
            gen = RepeatPageGenerator()
        elif arg.startswith('-ignore:'):
            HTTPignore.append(int(arg[8:]))
        elif arg.startswith('-day:'):
            config.weblink_dead_days = int(arg[5:])
        elif arg.startswith('-xmlstart'):
            if len(arg) == 9:
                xmlStart = pywikibot.input(
                    'Please enter the dumped article to start with:')
            else:
                xmlStart = arg[10:]
        elif arg.startswith('-xml'):
            if len(arg) == 4:
                xmlFilename = i18n.input('pywikibot-enter-xml-filename')
            else:
                xmlFilename = arg[5:]
        else:
            genFactory.handle_arg(arg)

    if xmlFilename:
        try:
            xmlStart
        except NameError:
            xmlStart = None
        gen = XmlDumpPageGenerator(xmlFilename, xmlStart,
                                   genFactory.namespaces)

    if not gen:
        gen = genFactory.getCombinedGenerator()
    if gen:
        if not genFactory.nopreload:
            # fetch at least 240 pages simultaneously from the wiki, but more
            # if a high thread number is set.
            pageNumber = max(20, config.max_external_links * 2)
            pywikibot.output("Fetch %i pages." % pageNumber)
            gen = pagegenerators.PreloadingGenerator(gen, groupsize=pageNumber)
        gen = pagegenerators.RedirectFilterPageGenerator(gen)
        bot = WeblinkCheckerRobot(gen, HTTPignore, config.weblink_dead_days)
        try:
            bot.run()
        except ImportError:
            suggest_help(missing_dependencies=('memento_client',))
            return False
        finally:
            waitTime = 0
            # Don't wait longer than 30 seconds for threads to finish.
            while countLinkCheckThreads() > 0 and waitTime < 30:
                try:
                    pywikibot.output('Waiting for remaining {0} threads to '
                                     'finish, please wait...'
                                     .format(countLinkCheckThreads()))
                    # wait 1 second
                    time.sleep(1)
                    waitTime += 1
                except KeyboardInterrupt:
                    pywikibot.output('Interrupted.')
                    break
            if countLinkCheckThreads() > 0:
                pywikibot.output('Remaining {0} threads will be killed.'
                                 .format(countLinkCheckThreads()))
                # Threads will die automatically because they are daemonic.
            if bot.history.reportThread:
                bot.history.reportThread.shutdown()
                # wait until the report thread is shut down; the user can
                # interrupt it by pressing CTRL-C.
                try:
                    while bot.history.reportThread.is_alive():
                        time.sleep(0.1)
                except KeyboardInterrupt:
                    pywikibot.output('Report thread interrupted.')
                    bot.history.reportThread.kill()
            pywikibot.output('Saving history...')
            bot.history.save()
    else:
        suggest_help(missing_generator=True)


if __name__ == '__main__':
    main()
