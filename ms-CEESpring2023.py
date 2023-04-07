#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Call:
    python pwb.py masti/ms-CEESpring2023.py -page:"Szablon:CEE Spring 2023" -outpage:"meta:Wikimedia CEE Spring 2023/Statistics" -summary:"Bot updates statistics" -reset -progress -pt:0
    python pwb.py masti/ms-CEESpring2023.py -page:"Szablon:CEE Spring 2023" -outpage:"Wikipedysta:Masti/CEE Spring 2023" -summary:"Bot updates statistics" -reset -progress -pt:0


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

-v:               make verbose output
-vv:              make even more verbose output

"""
#
# (C) Pywikibot team, 2006-2016
#
# Distributed under the terms of the MIT license.
#
from __future__ import absolute_import, unicode_literals

__version__ = '$Id: c1795dd2fb2de670c0b4bddb289ea9d13b1e9b3f $'

#

import pywikibot
from pywikibot.backports import Tuple
from pywikibot import pagegenerators

import re
from pywikibot import textlib
from datetime import datetime
import pickle
from pywikibot import config

from pywikibot.bot import (
    Bot, MultipleSitesBot, ConfigParserBot, ExistingPageBot, NoRedirectPageBot,
    AutomaticTWSummaryBot)

# This is required for the text that is shown when you run this script
# with the parameter -help.
docuReplacements = {
    '&params;': pagegenerators.parameterHelp
}

SpringStart = datetime.strptime("2023-03-20T23:59:59Z", "%Y-%m-%dT%H:%M:%SZ")
SpringEnd = datetime.strptime("2023-06-01T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
newbieLimit = datetime.strptime("2023-12-20T12:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
allowedFamilies = ['wikipedia', 'wikivoyage']

CEEtemplates = {'pl': 'Szablon:CEE Spring 2023', 'az': 'Şablon:Vikibahar 2023', 'ba': 'Ҡалып:Вики-яҙ 2023',
                'be': 'Шаблон:CEE Spring 2023', 'be-tarask': 'Шаблён:Артыкул ВікіВясны-2023',
                'bg': 'Шаблон:CEE Spring 2023', 'de': 'Vorlage:CEE Spring 2023', 'eo': 'Ŝablono:VikiPrintempo COE 2023',
                'el': 'Πρότυπο:CEE Spring 2023', 'et': 'Mall:CEE Spring 2023', 'hr': 'Predložak:CEE proljeće 2023.',
                'hu': 'Sablon:CEE Tavasz 2023', 'hy': 'Կաղապար:CEE Spring 2023', 'ka': 'თარგი:ვიკიგაზაფხული 2023',
                'lv': 'Veidne:CEE Spring 2023', 'lt': 'Šablonas:VRE 2023', 'mk': 'Шаблон:СИЕ Пролет 2023',
                'myk': 'Шаблон:СИЕ Пролет 2023', 'ro': 'Format:Wikimedia CEE Spring 2023',
                'roa-rup': 'Format:EMD Primveara 2023', 'ru': 'Шаблон:Вики-весна 2023',
                'sah': 'Халыып:Биики-саас 2023', 'sr': 'Шаблон:ЦЕЕ пролеће 2023', 'tr': 'Şablon:Vikibahar 2023',
                'uk': 'Шаблон:CEE Spring 2023', 'en': 'Template:CEE Spring 2023'}
countryList = ['Albania', 'Armenia', 'Aromanian', 'Austria', 'Azerbaijan', 'Bashkortostan', 'Belarus',
               'Bosnia and Herzegovina', 'Bulgaria', 'Crimean Tatars', 'Croatia', 'Cyprus', 'Czechia', 'Don', 'Erzia',
               'Esperanto', 'Estonia', 'Georgia', 'Greece', 'Hungary', 'Kazakhstan', 'Kosovo', 'Latvia',
               'Lithuania', 'Malta', 'Montenegro', 'North Macedonia', 'Poland', 'Republic of Srpska', 'Roma',
               'Romania and Moldova', 'Russia', 'Sakha', 'Serbia', 'Slovakia', 'Slovenia', 'Sorbia', 'Tatarstan',
               'Turkey', 'Ukraine', 'Võro', 'Western Armenian', 'Other', 'Empty', 'International']
languageCountry = {'el': ['Greece'], 'eo': ['Esperanto'], 'myv': ['Erzia'], 'bg': ['Bulgaria'],
                   'et': ['Estonia', 'Võro'],
                   'az': ['Azerbaijan'], 'ru': ['Russia', 'Don'], 'tt': ['Tatarstan'], 'tr': ['Turkey'],
                   'lv': ['Latvia'],
                   'ro': ['Romania and Moldova'], 'pl': ['Poland'], 'hy': ['Armenia'], 'ba': ['Bashkortostan'],
                   'hr': ['Croatia'], 'de': ['Germany'], 'hu': ['Hungary'], 'kk': ['Kazakhstan'], 'sr': ['Serbia'],
                   'sq': ['Albania'], 'mk': ['North Macedonia'], 'sk': ['Slovakia'], 'mt': ['Malta'],
                   'be-tarask': ['Belarus'], 'uk': ['Ukraine'], 'sl': ['Slovenia'],
                   'bs': ['Bosnia and Herzegovina', 'Republic of Srpska'], 'fiu-vro': ['Võro'], }
countryNames = {
    # pl countries
    'pl': {'Albania': 'Albania', 'Austria': 'Austria', 'Azerbejdżan': 'Azerbaijan', 'Baszkortostan': 'Bashkortostan',
           'Białoruś': 'Belarus', 'Bułgaria': 'Bulgaria', 'Armenia': 'Armenia', 'Cypr': 'Cyprus',
           'Bośnia i Hercegowina': 'Bosnia and Herzegovina', 'Czarnogóra': 'Montenegro', 'Erzja': 'Erzia',
           'Esperanto': 'Esperanto', 'Estonia': 'Estonia', 'Gruzja': 'Georgia', 'Czechy': 'Czechia',
           'Chorwacja': 'Croatia', 'Kosowo': 'Kosovo', 'Tatarzy krymscy': 'Crimean Tatars', 'Litwa': 'Lithuania',
           'Łotwa': 'Latvia', 'Łużyce': 'Sorbia', 'Malta': 'Malta', 'Węgry': 'Hungary',
           'Macedonia Północna': 'North Macedonia', 'Macedonia': 'North Macedonia', 'Mołdawia': 'Romania and Moldova',
           'Polska': 'Poland', 'Region doński': 'Don', 'Romowie': 'Roma', 'Rosja': 'Russia',
           'Rumunia': 'Romania and Moldova', 'Tatarzy': 'Crimean Tatars',
           'Rumunia i Mołdawia': 'Romania and Moldova', 'Republika Serbska': 'Republic of Srpska', 'Serbia': 'Serbia',
           'Serbołużyczanie': 'Sorbia', 'Słowacja': 'Slovakia', 'Słowenia': 'Slovenia', 'Turcja': 'Turkey',
           'Ukraina': 'Ukraine', 'Grecja': 'Greece', 'Kazachstan': 'Kazakhstan', 'Tatarstan': 'Tatarstan',
           'język Võro': 'Võro', 'Język voro': 'Võro', 'Võro': 'Võro', 'Tatarzy Krymscy': 'Crimean Tatars',
           'Języki łużyckie': 'Sorbia', 'Region Donu': 'Don', 'Międzynarodowy': 'International',
           'International': 'International',},
    # az countries
    'az': {'Albaniya': 'Albania', 'Avstriya': 'Austria', 'Azərbaycan': 'Azerbaijan', 'Başqırdıstan': 'Bashkortostan',
           'Belarus': 'Belarus', 'Bolqarıstan': 'Bulgaria', 'Ermənistan': 'Armenia',
           'Bosniya və Herseqovina': 'Bosnia and Herzegovina', 'Erzya': 'Erzia', 'Esperantida': 'Esperanto',
           'Estoniya': 'Estonia', 'Gürcüstan': 'Georgia', 'Çexiya': 'Czechia', 'Xorvatiya': 'Croatia',
           'Kosovo': 'Kosovo', 'Krımtatar': 'Crimean Tatars', 'Krım tatarları': 'Crimean Tatars',
           'Krım-Tatar': 'Crimean Tatars', 'Litva': 'Lithuania', 'Latviya': 'Latvia', 'Macarıstan': 'Hungary',
           'Şimali Makedoniya': 'North Macedonia', 'Makedoniya': 'North Macedonia', 'Malta': 'Malta',
           'Monteneqro': 'Montenegro', 'Moldova': 'Romania and Moldova', 'Polşa': 'Poland', 'Rusiya': 'Russia',
           'Rumıniya': 'Romania and Moldova', 'Serb Respublikası': 'Republic of Srpska', 'Serbiya': 'Serbia',
           'Slovakiya': 'Slovakia', 'Sloveniya': 'Slovenia', 'Tatarıstan': 'Tatarstan', 'Türkiyə': 'Turkey',
           'Ukrayna': 'Ukraine', 'Yunanıstan': 'Greece', 'Qazaxıstan': 'Kazakhstan', 'Krım-tatarlar': 'Crimean Tatars',
           'Don regionu': 'Don', 'Sorblar': 'Sorbia', 'Esperanto': 'Esperanto',
           'Rumıniya və Moldova': 'Romania and Moldova', 'Kipr': 'Cyprus', 'Don vilayəti': 'Don',
           'Tatarstan': 'Tatarstan', 'Krım Tatar': 'Crimean Tatars', 'Bosniya-Herseqovina': 'Bosnia and Herzegovina', },
    # ba countries
    'ba': {'Албания': 'Albania', 'Австрия': 'Austria', 'Әзербайжан': 'Azerbaijan', 'Башҡортостан': 'Bashkortostan',
           'Белоруслаштырыу': 'Belarus', 'Белоруссия': 'Belarus', 'Беларусь': 'Belarus', 'Белорусь': 'Belarus',
           'Болгария': 'Bulgaria', 'Әрмәнстан': 'Armenia', 'Босния һәм Герцоговина': 'Bosnia and Herzegovina',
           'Босния һәм Герцеговина': 'Bosnia and Herzegovina', 'Дон': 'Don', 'Эрзя теле': 'Erzia', 'Эрзя': 'Erzia',
           'Эсперантида': 'Esperanto', 'Эсперанто теле': 'Esperanto', 'Эстония': 'Estonia', 'Грузия': 'Georgia',
           'Чехия': 'Czechia', 'Чех Республикаһы': 'Czechia', 'Хорватия': 'Croatia', 'Косово': 'Kosovo',
           'Ҡырым татар теле': 'Crimean Tatars', 'Ҡырым Республикаһы': 'Crimean Tatars',
           'Ҡырым татарҙары': 'Crimean Tatars', 'Литва': 'Lithuania', 'Латвия': 'Latvia', 'Венгрия': 'Hungary',
           'Черногория': 'Montenegro', 'Төньяҡ Македония': 'North Macedonia', 'Македония': 'North Macedonia',
           'Молдавия': 'Romania and Moldova', 'Бессарабия': 'Romania and Moldova',
           'Румыния һәм Молдова‎': 'Romania and Moldova', 'Польша': 'Poland', 'Рәсәй': 'Russia',
           'Рәсәй Федерацияһы': 'Russia', 'Молдова': 'Romania and Moldova',
           'Румыния һәм Молдова': 'Romania and Moldova', 'Румыния': 'Romania and Moldova', 'Лужи теле': 'Sorbia',
           'Серб Республикаһы': 'Republic of Srpska', 'Сербия': 'Serbia', 'Словакия': 'Slovakia',
           'Словак социалистик республикаһы': 'Slovakia', 'Словения': 'Slovenia', 'Татарстан': 'Tatarstan',
           'Төркиә': 'Turkey', 'Украина': 'Ukraine', 'Греция': 'Greece', 'Ҡаҙағстан': 'Kazakhstan', 'Мальта': 'Malta',
           'Ҡырым': 'Crimean Tatars', 'Эсперанто': 'Esperanto', 'Сиғандар': 'Roma', 'Татар Республикаһы': 'Tatarstan',
           'Әзербайжанн': 'Azerbaijan', 'Кипр': 'Cyprus', 'Ҡаҙаҡстан': 'Kazakhstan', 'Мальта Республикаһы': 'Malta',
           'Босния': 'Bosnia and Herzegovina', 'Россия': 'Russia', 'Выру': 'Võro', 'РСФСР': 'Russia',  },
    # be countries
    'be': {'Албанія': 'Albania', 'Аўстрыя': 'Austria', 'Азербайджан': 'Azerbaijan', 'Башкартастан': 'Bashkortostan',
           'Беларусь': 'Belarus', 'Балгарыя': 'Bulgaria', 'Арменія': 'Armenia',
           'Боснія і Герцагавіна': 'Bosnia and Herzegovina', 'Чарнагорыя': 'Montenegro', 'Эрзя': 'Erzia',
           'Эсперанта': 'Esperanto', 'Эстонія': 'Estonia', 'Грузія': 'Georgia', 'Чэхія': 'Czechia',
           'Харватыя': 'Croatia', 'Рэспубліка Косава': 'Kosovo', 'Крымскія татары': 'Crimean Tatars',
           'Літва': 'Lithuania', 'Латвія': 'Latvia', 'Венгрыя': 'Hungary', 'Македонія': 'North Macedonia',
           'Малдова': 'Romania and Moldova', 'Польшча': 'Poland', 'Расія': 'Russia', 'Румынія': 'Romania and Moldova',
           'Рэспубліка Сербская': 'Republic of Srpska', 'Сербія': 'Serbia', 'Лужычане': 'Sorbia',
           'Славакія': 'Slovakia', 'Татарстан': 'Tatarstan', 'Турцыя': 'Turkey', 'Украіна': 'Ukraine',
           'Грэцыя': 'Greece', 'Казахстан': 'Kazakhstan', },
    # be-tarask countries
    'be-tarask': {'Альбанія': 'Albania', 'Аўстрыя': 'Austria', 'Азэрбайджан': 'Azerbaijan',
                  'Башкартастан': 'Bashkortostan', 'Беларусь': 'Belarus', 'Баўгарыя': 'Bulgaria', 'Армэнія': 'Armenia',
                  'Босьнія і Герцагавіна': 'Bosnia and Herzegovina', 'Дон': 'Don', 'Эрзя': 'Erzia',
                  'Эспэранта': 'Esperanto', 'Эстонія': 'Estonia', 'Грузія': 'Georgia', 'Чэхія': 'Czechia',
                  'Харватыя': 'Croatia', 'Косава': 'Kosovo', 'крымскія татары': 'Crimean Tatars',
                  'Крымскія татары': 'Crimean Tatars', 'Летува': 'Lithuania', 'Латвія': 'Latvia',
                  'Вугоршчына': 'Hungary', 'Паўночная Македонія': 'North Macedonia', 'Македонія': 'North Macedonia',
                  'Северна Македония': 'North Macedonia', 'Малдова': 'Romania and Moldova', 'Чарнагорыя': 'Montenegro',
                  'Польшча': 'Poland', 'Расея': 'Russia', 'Румынія': 'Romania and Moldova',
                  'Малодва': 'Romania and Moldova', 'Рэспубліка Сэрбская': 'Republic of Srpska', 'Сэрбія': 'Serbia',
                  'Славакія': 'Slovakia', 'татары': 'Crimean Tatars',
                  'Славаччына': 'Slovakia', 'Славенія': 'Slovenia', 'Нямеччына (лужычане)': 'Sorbia',
                  'Лужычане': 'Sorbia', 'Расея (Татарстан)': 'Tatarstan', 'Татарстан': 'Tatarstan',
                  'Турэччына': 'Turkey', 'Украіна': 'Ukraine', 'Грэцыя': 'Greece', 'Казахстан': 'Kazakhstan',
                  'Мальта': 'Malta', 'эспэранта': 'Esperanto', 'Republika srbská': 'Republic of Srpska',
                  'Tatársko': 'Tatarstan', 'эрзя': 'Erzia', 'Цыганы': 'Roma', 'цыганы': 'Roma', 'Кіпр': 'Cyprus',
                  'лужычане': 'Sorbia', 'Міжнародны': 'International', 'Літва': 'Lithuania',  },
    # bg countries
    'bg': {'Албания': 'Albania', 'Австрия': 'Austria', 'Азербайджан': 'Azerbaijan', 'Башкортостан': 'Bashkortostan',
           'Беларус': 'Belarus', 'България': 'Bulgaria', 'Армения': 'Armenia',
           'Босна и Херцеговина': 'Bosnia and Herzegovina', 'кримските татари': 'Crimean Tatars',
           'Донски регион': 'Don', 'Ерзяни': 'Erzia', 'ерзяни': 'Erzia', 'Эрзя': 'Erzia', 'Eсперанто': 'Esperanto',
           'Есперанто': 'Esperanto', 'Естония': 'Estonia', 'Грузия': 'Georgia', 'Чехия': 'Czechia',
           'Хърватия': 'Croatia', 'Косово': 'Kosovo', 'кримски татари': 'Crimean Tatars',
           'Кримски татари': 'Crimean Tatars', 'Литва': 'Lithuania', 'Латвия': 'Latvia', 'Унгария': 'Hungary',
           'Република Македония': 'North Macedonia', 'Македония': 'North Macedonia',
           'Северна Македония': 'North Macedonia', 'Молдова': 'Romania and Moldova', 'Полша': 'Poland',
           'Русия': 'Russia', 'Румъния и Молдова': 'Romania and Moldova', 'Румъния': 'Romania and Moldova',
           'Черна гора': 'Montenegro', 'Република Сръбска': 'Republic of Srpska', 'Сърбия': 'Serbia',
           'Словакия': 'Slovakia', 'Словения': 'Slovenia', 'Лужичани (сорби)': 'Sorbia', 'Турция': 'Turkey',
           'Украйна': 'Ukraine', 'Гърция': 'Greece', 'Казахстан': 'Kazakhstan', 'Татарстан': 'Tatarstan',
           'Азербайджан‎': 'Azerbaijan', 'лужичаните': 'Sorbia', 'Малта': 'Malta', 'ерзяните': 'Erzia',
           'есперанто': 'Esperanto', 'Кипър': 'Cyprus', 'циганите': 'Roma', 'Въро': 'Võro', 'въру': 'Võro', },
    # de countries
    'de': {'Albanien': 'Albania', 'Österreich': 'Austria', 'Aserbaidschan': 'Azerbaijan',
           'Baschkortostan': 'Bashkortostan', 'Weißrussland': 'Belarus', 'Bulgarien': 'Bulgaria', 'Armenien': 'Armenia',
           'Bosnien und Herzegowina': 'Bosnia and Herzegovina', 'Don-Region': 'Don', 'Ersja': 'Erzia',
           'Esperanto': 'Esperanto', 'Estland': 'Estonia', 'Georgien': 'Georgia', 'Tschechien': 'Czechia',
           'Kroatien': 'Croatia', 'Kosovo': 'Kosovo', 'Krimtataren': 'Crimean Tatars', 'Litauen': 'Lithuania',
           'Lettland': 'Latvia', 'Ungarn': 'Hungary', 'Mazedonien': 'North Macedonia', 'Montenegro': 'Montenegro',
           'Moldau': 'Romania and Moldova', 'Moldawien': 'Romania and Moldova', 'Polen': 'Poland', 'Russland': 'Russia',
           'Rumänien': 'Romania and Moldova', 'Republik Moldau': 'Romania and Moldova',
           'Republika Srpska': 'Republic of Srpska', 'Serbien': 'Serbia', 'Slowakei': 'Slovakia',
           'Slowenien': 'Slovenia', 'Türkei': 'Turkey', 'Ukraine': 'Ukraine', 'Griechenland': 'Greece',
           'Kasachstan': 'Kazakhstan', 'Malta': 'Malta', 'Sorbisches Siedlungsgebiet': 'Sorbia',
           'Nordmazedonien': 'North Macedonia', 'Tatarstan': 'Tatarstan', 'Zypern': 'Cyprus',
           'die Republik Moldau': 'Romania and Moldova', 'die Türkei': 'Turkey', 'Sorbisch': 'Sorbia',
           'Sorben': 'Sorbia', 'Belarus': 'Belarus', },
    # bs countries
    'bs': {'Albanija': 'Albania', 'Austrija': 'Austria', 'Azerbejdžan': 'Azerbaijan', 'Baškortostan': 'Bashkortostan',
           'Bjelorusija': 'Belarus', 'Bosna i Hercegovina': 'Bosnia and Herzegovina', 'Bugarska': 'Bulgaria',
           'Češka': 'Czechia', 'Armenija': 'Armenia', 'Esperanto': 'Esperanto', 'Estonija': 'Estonia',
           'Gruzija': 'Georgia', 'Grčka': 'Greece', 'Hrvatska': 'Croatia', 'Kazahstan': 'Kazakhstan',
           'Kosovo': 'Kosovo', 'Latvija': 'Latvia', 'Litvanija': 'Lithuania', 'Mađarska': 'Hungary',
           'Makedonija': 'North Macedonia', 'Moldavija': 'Romania and Moldova', 'Poljska': 'Poland',
           'Republika Srpska': 'Republic of Srpska', 'Rumunija': 'Romania and Moldova', 'Rusija': 'Russia',
           'Slovačka': 'Slovakia', 'Srbija': 'Serbia', 'Turska': 'Turkey', 'Ukrajina': 'Ukraine',
           'Slovenija': 'Slovenia', 'Romi': 'Roma', 'Crna Gora': 'Montenegro', 'Virosi': 'Võro',
           'Krimski Tatari': 'Crimean Tatars', 'Kipar': 'Cyprus', 'Sjeverna Makedonija': 'North Macedonia',
           'Don': 'Don',
           'Erzja': 'Erzia', 'Malta': 'Malta', 'Rumunija i Moldavija': 'Romania and Moldova', 'Lužički Srbi': 'Sorbia',
           'Tatarstan': 'Tatarstan', 'Sorbisch': 'Sorbia', 'Krimeanski Tatari': 'Crimean Tatars',
           'Međunarodne teme': 'International', 'Međunarodni': 'International', 'Krimski tatari': 'Crimean Tatars',
           'Lužički srbi': 'Sorbia', 'Arumuni': 'Aromanian', 'Tatari': 'Crimean Tatars', 'Republika Saha': 'Sakha',
           'Võro (jezik)': 'Võro', },
    # crh countries
    'crh': {'Arnavutlıq': 'Albania', 'Avstriya': 'Austria', 'Azerbaycan': 'Azerbaijan', 'Başqırtistan': 'Bashkortostan',
            'Belarus': 'Belarus', 'Bulğaristan': 'Bulgaria', 'Ermenistan': 'Armenia',
            'Bosna ve Hersek': 'Bosnia and Herzegovina', 'Esperanto': 'Esperanto', 'Estoniya': 'Estonia',
            'Gürcistan': 'Georgia', 'Çehiya': 'Czechia', 'Hırvatistan': 'Croatia', 'Kosovo': 'Kosovo',
            'Qırımtatarlar': 'Crimean Tatars', 'Litvaniya': 'Lithuania', 'Latviya': 'Latvia', 'Macaristan': 'Hungary',
            'Makedoniya': 'North Macedonia', 'Moldova': 'Romania and Moldova', 'Lehistan': 'Poland', 'Rusiye': 'Russia',
            'Romaniya': 'Romania and Moldova', 'Sırb Cumhuriyeti': 'Republic of Srpska', 'Sırbistan': 'Serbia',
            'Slovakiya': 'Slovakia', 'Türkiye': 'Turkey', 'Ukraina': 'Ukraine', 'Yunanistan': 'Greece',
            'Qazahistan': 'Kazakhstan', },
    # el countries
    'el': {'Αλβανία': 'Albania', 'Αυστρία': 'Austria', 'Αζερμπαϊτζάν': 'Azerbaijan', 'Μπασκορτοστάν': 'Bashkortostan',
           'Λευκορωσία': 'Belarus', 'Βουλγαρία': 'Bulgaria', 'Αρμενία': 'Armenia', 'Βοσνία': 'Bosnia and Herzegovina',
           'Βοσνία-Ερζεγοβίνη': 'Bosnia and Herzegovina', 'Βοσνία Ερζεγοβίνη': 'Bosnia and Herzegovina',
           'Βοσνία και Ερζεγοβίνη': 'Bosnia and Herzegovina', 'Έρζυα': 'Erzia', 'Εσπεράντο': 'Esperanto',
           'Εσθονία': 'Estonia', 'Γεωργία': 'Georgia', 'Τσεχία': 'Czechia', 'Κροατία': 'Croatia',
           'Περιοχή του Ντον': 'Don', 'Κοσσυφοπέδιο': 'Kosovo', 'Κόσοβο': 'Kosovo',
           'Τατάροι Κριμαίας': 'Crimean Tatars', 'Λιθουανία': 'Lithuania', 'Λετονία': 'Latvia', 'Ουγγαρία': 'Hungary',
           'Μαυροβούνιο': 'Montenegro', 'πΓΔΜ': 'North Macedonia', 'Βόρεια Μακεδονία': 'North Macedonia',
           'Ρουμανία & Μολδαβία': 'Romania and Moldova', 'Μολδαβία': 'Romania and Moldova', 'Πολωνία': 'Poland',
           'Ρωσική Ομοσπονδία': 'Russia', 'Ρωσία': 'Russia', 'Ρουμανία-Μολδαβία': 'Romania and Moldova',
           'Ρουμανία': 'Romania and Moldova', 'Δημοκρατία της Σερβίας': 'Republic of Srpska',
           'Σερβική Δημοκρατία': 'Republic of Srpska', 'Σερβία': 'Serbia', 'Σορβικά': 'Sorbia', 'Σορβία': 'Sorbia',
           'Σλοβακία': 'Slovakia', 'Σλοβενία': 'Slovenia', 'Ταταρστάν': 'Tatarstan', 'Τουρκία': 'Turkey',
           'Ουκρανία': 'Ukraine', 'Ελλάδα': 'Greece', 'Καζακστάν': 'Kazakhstan', 'Μάλτα': 'Malta',
           'Ταταρικά Κριμαίας': 'Crimean Tatars', 'Σερβική Δημοκρατία της Βοσνίας': 'Republic of Srpska',
           'Σλοβενία χώρα': 'Slovenia', 'Croatia': 'Croatia', 'Albania': 'Albania', 'Κύπρος': 'Cyprus',
           'Latvia': 'Latvia',
           'Βόρου': 'Võro', 'Επαρχία Βόρου': 'Võro', 'Ρουμανία και Μολδαβία': 'Romania and Moldova', 'Ρομά': 'Roma',
           'γλώσσα Εσπεράντο': 'Esperanto', 'Τάταροι της Κριμαίας': 'Crimean Tatars', 'Έρζια': 'Erzia',
           'Ογγαρία': 'Hungary', 'Ρωσική ομοσπονδία': 'Russia', },
    # myv countries
    'myv': {'Албания': 'Albania', 'Албания Мастор': 'Albania', 'Австрия Мастор': 'Austria', 'Австрия': 'Austria',
            'Азербайджан Республикась': 'Azerbaijan', 'Азербайджан': 'Azerbaijan',
            'Башкирия Республикась': 'Bashkortostan', 'Башкирия Мастор': 'Bashkortostan',
            'Белорузия Республикась': 'Belarus', 'Белорузия Мастор': 'Belarus', 'Болгария Мастор': 'Bulgaria',
            'Армения Мастор': 'Armenia', 'Босния ды Герцеговина Мастор': 'Bosnia and Herzegovina',
            'Босния ды Герцеговина': 'Bosnia and Herzegovina', 'Эрзянь Мастор': 'Erzia', 'Эрзя Мастор': 'Erzia',
            'Эсперанто': 'Esperanto', 'Эстэнь Мастор': 'Estonia',
            'Грузия Мастор': 'Georgia', 'Чехия Мастор': 'Czechia', 'Хорватия Мастор': 'Croatia', 'Хорватия': 'Croatia',
            'Косово Мастор': 'Kosovo', 'Литва Мастор': 'Lithuania', 'Литва': 'Lithuania', 'Латвия Мастор': 'Latvia',
            'Мадяронь Мастор': 'Hungary', 'Мадьяронь Мастор': 'Hungary', 'Македония Мастор': 'North Macedonia',
            'Македония': 'North Macedonia', 'Молдавия': 'Romania and Moldova',
            'Польша Мастор': 'Poland', 'Польша': 'Poland', 'Россия': 'Russia', 'Россия Мастор': 'Russia',
            'Румыния Мастор': 'Romania and Moldova', 'Сербань Республикась': 'Republic of Srpska',
            'Сербия Мастор': 'Serbia', 'Сербия': 'Serbia', 'Словакия Мастор': 'Slovakia', 'Словакия': 'Slovakia',
            'Татаронь Республикась': 'Tatarstan', 'Турция Мастор': 'Turkey', 'Украина': 'Ukraine',
            'Украина Мастор': 'Ukraine', 'Греция Мастор': 'Greece', 'Казахстан Мастор': 'Kazakhstan',
            'Словения Мастор': 'Slovenia', 'Мальта Мастор': 'Malta', 'Молдавия Мастор': 'Romania and Moldova',
            'Казахстан': 'Kazakhstan', '{{Цыганонь коцтось}}': 'Roma', 'Татарстан': 'Tatarstan',
            'Кипр Республикась': 'Cyprus', 'Крым Республикась': 'Crimean Tatars', 'International': 'International',
            'Ukraine': 'Ukraine', },
    # eo countries
    'eo': {'Albanio': 'Albania', 'Aŭstrio': 'Austria', 'Azerbajĝano': 'Azerbaijan', 'Baŝkirio': 'Bashkortostan',
           'Belorusio': 'Belarus', 'Bulgario': 'Bulgaria', 'Armenio': 'Armenia',
           'Bosnio kaj Hercegovino': 'Bosnia and Herzegovina', 'Erzja': 'Erzia', 'Esperantujo': 'Esperanto',
           'Esperanto': 'Esperanto', 'Estonio': 'Estonia', 'Kartvelio': 'Georgia', 'Ĉeĥio': 'Czechia',
           'Kroatio': 'Croatia', 'Kosovo': 'Kosovo', 'Krimeo': 'Crimean Tatars', 'Krime-tataroj': 'Crimean Tatars',
           'Litovio': 'Lithuania', 'Latvio': 'Latvia', 'Hungario': 'Hungary', 'Makedonio': 'North Macedonia',
           'Moldava': 'Romania and Moldova', 'Montenegro': 'Montenegro', 'Pollando': 'Poland', 'Rusio': 'Russia',
           'Rumanio': 'Romania and Moldova', 'Serba Respubliko': 'Republic of Srpska', 'Serbio': 'Serbia',
           'Slovakio': 'Slovakia', 'Turkio': 'Turkey', 'Ukrainio': 'Ukraine', 'Grekio': 'Greece',
           'Kazaĥio': 'Kazakhstan', 'Moldavio': 'Romania and Moldova', 'Ukraino': 'Ukraine', 'Slovenio': 'Slovenia',
           'Rumanio kaj Moldavio': 'Romania and Moldova', 'Malto': 'Malta', 'Nord-Makedonio': 'North Macedonia', },
    # hy countries
    'hy': {'Ալբանիա': 'Albania', 'Ավստրիա': 'Austria', 'Ադրբեջան': 'Azerbaijan',
           'Ադրբեջանական Հանրապետություն': 'Azerbaijan', 'Բաշկորտոստան': 'Bashkortostan', 'Բելառուս': 'Belarus',
           'Բուլղարիա': 'Bulgaria', 'Հայաստան': 'Armenia', 'Բոսնիա և Հերցեգովինա': 'Bosnia and Herzegovina',
           'Դոնի շրջան': 'Don', 'Էսպերանտո': 'Esperanto', 'Էստոնիա': 'Estonia', 'Էրզիա': 'Erzia', 'Վրաստան': 'Georgia',
           'Չեխիա': 'Czechia', 'Խորվաթիա': 'Croatia', 'Կոսովո': 'Kosovo', 'Ղրիմի թաթարներ': 'Crimean Tatars',
           'Լիտվա': 'Lithuania', 'Լատվիա': 'Latvia', 'Հունգարիա': 'Hungary', 'Հյուսիսային Մակեդոնիա': 'North Macedonia',
           'Մակեդոնիա': 'North Macedonia', 'Մակեդոնիայի Հանրապետություն': 'North Macedonia',
           'Մոլդովա': 'Romania and Moldova', 'Չեռնոգորիա': 'Montenegro', 'Լեհաստան': 'Poland', 'Ռուսաստան': 'Russia',
           'Ռումինիա և Մոլդովա': 'Romania and Moldova', 'Ռումինիա/Մոլդովա': 'Romania and Moldova',
           'Ռումինիա': 'Romania and Moldova', 'Սերբիայի Հանրապետություն': 'Serbia', 'Սերբիա': 'Serbia',
           'Սլովակիա': 'Slovakia', 'Թաթարստան': 'Tatarstan', 'Թուրքիա': 'Turkey', 'Ուկրաինա': 'Ukraine',
           'Հունաստան': 'Greece', 'Ղազախստան': 'Kazakhstan', 'Սլովենիա': 'Slovenia', 'Մալթա': 'Malta',
           'Լեհատան': 'Poland', 'Հունաստամ': 'Greece', 'Ալբանիաիա': 'Albania',
           'Սերբական Հանրապետություն': 'Republic of Srpska', 'Կիպրոս': 'Cyprus', 'էստոնիա': 'Estonia',
           'Գնչուներ': 'Roma', 'Վիրուերեն': 'Võro', 'Լուժիկերեն': 'Sorbia', 'Առումիներեն': 'Armenia', },
    # hyw countries
    'hyw': {
    },
    # ka countries
    'ka': {'ალბანეთი': 'Albania', 'ავსტრია': 'Austria', 'აზერბაიჯანი': 'Azerbaijan', 'ბაშკირეთი': 'Bashkortostan',
           'ბელარუსი': 'Belarus', 'ბულგარეთი': 'Bulgaria', 'სომხეთი': 'Armenia',
           'ბოსნია და ჰერცოგოვინა': 'Bosnia and Herzegovina', 'ბოსნია და ჰერცეგოვინა': 'Bosnia and Herzegovina',
           'ესპერანტო': 'Esperanto', 'ესტონეთი': 'Estonia', 'ერზია': 'Erzia', 'საქართველო': 'Georgia',
           'ჩეხეთი': 'Czechia', 'ხორვატია': 'Croatia', 'კოსოვო': 'Kosovo', 'ყირიმელი თათრები': 'Crimean Tatars',
           'დონის რეგიონი': 'Don', 'ლიტვა': 'Lithuania', 'ლატვია': 'Latvia', 'უნგრეთი': 'Hungary',
           'ჩრდილოეთი მაკედონია': 'North Macedonia', 'ჩრდილოეთ მაკედონია': 'North Macedonia',
           'მაკედონია': 'North Macedonia', 'მოლდოვა': 'Romania and Moldova',
           'რუმინეთი და მოლდოვა': 'Romania and Moldova', 'პოლონეთი': 'Poland', 'რუსეთის ფედერაცია': 'Russia',
           'რუსეთი': 'Russia', 'რუმინეთი': 'Romania and Moldova', 'სერბთა რესპუბლიკა': 'Republic of Srpska',
           'სერბეთი': 'Serbia', 'სლოვაკეთი': 'Slovakia', 'თურქეთი': 'Turkey', 'უკრაინა': 'Ukraine',
           'საბერძნეთი': 'Greece', 'ყაზახეთი': 'Kazakhstan', },
    # lv countries
    'lv': {'Albānija': 'Albania', 'Austrija': 'Austria', 'Azerbaidžāna': 'Azerbaijan',
           'Baškortostāna‎': 'Bashkortostan', 'Baškortostāna': 'Bashkortostan', 'Baltkrievija': 'Belarus',
           'Bulgārija': 'Bulgaria', 'Armēnija': 'Armenia', 'Bosnija un Hercegovina': 'Bosnia and Herzegovina',
           'Donas reģions': 'Don', 'erzji': 'Erzia', 'Erzju': 'Erzia', 'esperanto': 'Esperanto',
           'Esperanto': 'Esperanto', 'Igaunija': 'Estonia', 'Gruzija': 'Georgia', 'Čehija': 'Czechia',
           'Horvātija': 'Croatia', 'Kosova': 'Kosovo', 'Krimas tatāri': 'Crimean Tatars', 'Lietuva': 'Lithuania',
           'Latvija': 'Latvia', 'Ungārija': 'Hungary', 'Ziemeļmaķedonija': 'North Macedonia',
           'Maķedonija': 'North Macedonia', 'Moldova': 'Romania and Moldova', 'Melnkalne': 'Montenegro',
           'Polija': 'Poland', 'Krievija': 'Russia', 'Rumānija': 'Romania and Moldova',
           'Serbu Republika': 'Republic of Srpska', 'Serbija': 'Serbia', 'Slovākija': 'Slovakia',
           'Slovēnija': 'Slovenia', 'Tatarstāna': 'Tatarstan', 'Turcija': 'Turkey', 'Ukraina': 'Ukraine',
           'Grieķija': 'Greece', 'Kazahstāna': 'Kazakhstan', 'Sorbi': 'Sorbia', 'rumāņi': 'Romania and Moldova',
           'Malta': 'Malta', 'sorbi': 'Sorbia', 'Kipra': 'Cyprus', 'veru valoda': 'Võro', 'čigāni': 'Roma',
           'Erzji': 'Erzia', },
    # lt countries
    'lt': {'Albanija': 'Albania', 'Austrija': 'Austria', 'Azerbaidžanas': 'Azerbaijan', 'Baškirija': 'Bashkortostan',
           'Baltarusija': 'Belarus', 'Bulgarija': 'Bulgaria', 'Armėnija': 'Armenia',
           'Bosnija ir Hercegovina': 'Bosnia and Herzegovina', 'Erzija': 'Erzia', 'Erzių': 'Erzia',
           'Esperanto': 'Esperanto', 'Estija': 'Estonia', 'Gruzija': 'Georgia', 'Čekija': 'Czechia',
           'Kroatija': 'Croatia', 'Kosovas': 'Kosovo', 'Krymas': 'Crimean Tatars', 'Krymo totoriai': 'Crimean Tatars',
           'Lietuva': 'Lithuania', 'Latvija': 'Latvia', 'Vengrija': 'Hungary', 'Šiaurės Makedonija': 'North Macedonia',
           'Makedonija': 'North Macedonia', 'Moldavija': 'Romania and Moldova', 'Lenkija': 'Poland', 'Rusija': 'Russia',
           'Rumunija': 'Romania and Moldova', 'Serbų Respublika': 'Republic of Srpska',
           'Serbų respublika': 'Republic of Srpska', 'Serbija': 'Serbia', 'Serbijos respublika': 'Serbia',
           'Slovakija': 'Slovakia', 'Slovėnija': 'Slovenia', 'Lužica': 'Sorbia', 'Turkija': 'Turkey',
           'Ukraina': 'Ukraine', 'Graikija': 'Greece', 'Kazachstanas': 'Kazakhstan', 'Tatarstanas': 'Tatarstan'},
    # mk countries
    'mk': {'Албанија': 'Albania', 'Австрија': 'Austria', 'Азербејџан': 'Azerbaijan', 'Башкортостан': 'Bashkortostan',
           'Bashkortostani': 'Bashkortostan', 'Белорусија': 'Belarus', 'Бугарија': 'Bulgaria', 'Ерменија': 'Armenia',
           'Црна Гора': 'Montenegro', 'Босна и Херцеговина': 'Bosnia and Herzegovina', 'Донбас': 'Don',
           'Ерзја': 'Erzia', 'есперанто': 'Esperanto', 'Есперанто': 'Esperanto', 'Естонија': 'Estonia',
           'Грузија': 'Georgia', 'Чешка': 'Czechia', 'Хрватска': 'Croatia', 'Косово': 'Kosovo',
           'Република Косово': 'Kosovo', 'Крим': 'Crimean Tatars', 'Кримски Татари': 'Crimean Tatars',
           'Кримските Татари': 'Crimean Tatars', 'Литванија': 'Lithuania', 'Латвија': 'Latvia', 'Унгарија': 'Hungary',
           'Македонија': 'North Macedonia', 'Молдавија': 'Romania and Moldova', 'Полска': 'Poland', 'Русија': 'Russia',
           'Романија': 'Romania and Moldova', 'Романија и Молдавија': 'Romania and Moldova',
           'Република Српска': 'Republic of Srpska', 'Србија': 'Serbia', 'Словачка': 'Slovakia',
           'Словенија': 'Slovenia', 'Лужица': 'Sorbia', 'Турција': 'Turkey', 'Украина': 'Ukraine', 'Грција': 'Greece',
           'Казахстан': 'Kazakhstan', 'Татарстан': 'Tatarstan', 'Хрватса': 'Croatia', 'Донечка област': 'Don',
           'Малта': 'Malta', 'Донскиот регион': 'Don', 'Кипар': 'Cyprus', 'Мордовија': 'Erzia',
           'Казакстан': 'Kazakhstan',
           'Виру': 'Võro', 'Роми': 'Roma', 'Донски Регион': 'Don', 'Донски регион': 'Don', },
    # ro countries
    'ro': {'Albania': 'Albania', 'Austria': 'Austria', 'Azerbaidjan': 'Azerbaijan', 'Bașkortostan': 'Bashkortostan',
           'Bașchiria': 'Bashkortostan', 'Belarus': 'Belarus', 'Bulgaria': 'Bulgaria', 'Armenia': 'Armenia',
           'Bosnia și Herțegovina': 'Bosnia and Herzegovina', 'tătarii crimeeni': 'Crimean tatars',
           'Regiunea Donului': 'Don', 'Don': 'Don', 'Esperanto': 'Esperanto', 'Estonia': 'Estonia',
           'Georgia': 'Georgia', 'Cehia': 'Czechia', 'Croația': 'Croatia', 'Kosovo': 'Kosovo',
           'Crimeea': 'Crimean Tatars', 'Lituania': 'Lithuania', 'Letonia': 'Latvia', 'Ungaria': 'Hungary',
           'Muntenegru': 'Montenegro', 'Macedonia de Nord': 'North Macedonia', 'Macedonia': 'North Macedonia',
           'Republica Moldova': 'Romania and Moldova', 'Polonia': 'Poland', 'Rusia': 'Russia',
           'România': 'Romania and Moldova', 'Sorabi': 'Sorbia', 'Republika Srpska': 'Republic of Srpska',
           'Serbia': 'Serbia', 'Slovacia': 'Slovakia', 'Slovenia': 'Slovenia', 'Tatarstan': 'Tatarstan',
           'Turcia': 'Turkey', 'Ucraina': 'Ukraine', 'Grecia': 'Greece', 'Kazahstan': 'Kazakhstan', 'Erzia': 'Erzia',
           'Malta': 'Malta', 'Tătari crimeeni': 'Crimean tatars', 'Tătarii din Crimeea': 'Crimean tatars',
           'sorabi': 'Sorbia',
           'Tătarii crimeeni': 'Crimean Tatars', 'Republica Cehă': 'Czechia', 'Mișcarea esperantistă': 'Esperanto',
           'Cipru': 'Cyprus', 'Romi': 'Roma', 'Võro': 'Võro', 'Federația Rusă': 'Russia', },
    # roa-rup countries
    'roa-rup': {
            },
    # ru countries
    'ru': {'Албания': 'Albania', 'Австрия': 'Austria', 'Азербайджан': 'Azerbaijan', 'Башкортостан': 'Bashkortostan',
           'Беларусь': 'Belarus', 'Белоруссия': 'Belarus', 'Болгария': 'Bulgaria', 'Армения': 'Armenia',
           'Босния и Герцеговина': 'Bosnia and Herzegovina', 'Эрзя': 'Erzia', 'Эсперантида': 'Esperanto',
           'Эсперанто': 'Esperanto', 'Эстония': 'Estonia', 'Грузия': 'Georgia', 'Чехия': 'Czechia',
           'Хорватия': 'Croatia', 'Косово': 'Kosovo', 'Крымские татары': 'Crimean Tatars', 'Литва': 'Lithuania',
           'Латвия': 'Latvia', 'Венгрия': 'Hungary', 'Республика Македония': 'North Macedonia',
           'Македония': 'North Macedonia', 'Северная Македония': 'North Macedonia', 'Молдавия': 'Romania and Moldova',
           'Черногория': 'Montenegro', 'Польша': 'Poland', 'Россия': 'Russia', 'Румыния': 'Romania and Moldova',
           'Сербская Республика': 'Republic of Srpska', 'Республика Сербская': 'Republic of Srpska', 'Сербия': 'Serbia',
           'Лужичане': 'Sorbia', 'Словакия': 'Slovakia', 'Словения': 'Slovenia', 'Татарстан': 'Tatarstan',
           'Турция': 'Turkey', 'Украина': 'Ukraine', 'Греция': 'Greece', 'Казахстан': 'Kazakhstan',
           'Мальта': 'Malta', 'Кипр': 'Cyprus', 'Крым': 'Crimean Tatars', 'Цыгане': 'Roma', 'Лужица': 'Sorbia',
           'Выру': 'Võro', 'Румыния и Молдавия': 'Romania and Moldova', },
    # sah countries
    'sah': {
    },
    # sq countries
    'sq': {'Shqipëria': 'Albania', 'Shqipërisë': 'Albania', 'Armenia': 'Armenia',
           'Armenisë': 'Armenia', 'Armeni': 'Armenia', 'Austria': 'Austria', 'Austri': 'Austria',
           'Azerbajxhani': 'Azerbaijan', 'Azerbajxhanit': 'Azerbaijan', 'Azerbajxhan': 'Azerbaijan',
           'Bashkortostani': 'Bashkortostan', 'Bjellorusi': 'Belarus', 'Bjellorusia': 'Belarus',
           'Bosnja dhe Hercegovina': 'Bosnia and Herzegovina', 'Bullgaria': 'Bulgaria', 'Kroaci': 'Croatia',
           'Kroacia': 'Croatia', 'Kroacisë': 'Croatia', 'Republika Çeke': 'Czechia', 'Esperanto': 'Esperanto',
           'Gjuha esperanto': 'Esperanto', 'Estoni': 'Estonia', 'Estonia': 'Estonia', 'Gjeorgjia': 'Georgia',
           'Gjeorgjisë': 'Georgia', 'Greqi': 'Greece', 'Greqia': 'Greece', 'Greqisë': 'Greece', 'Hungaria': 'Hungary',
           'Hungari': 'Hungary', 'Kazakistan': 'Kazakhstan', 'Kazakistani': 'Kazakhstan', 'Kazakistanin': 'Kazakhstan',
           'Kosovë': 'Kosovo', 'Kosova': 'Kosovo', 'Kosovës': 'Kosovo', 'Letoni': 'Latvia', 'Letonia': 'Latvia',
           'Lituania': 'Lithuania', 'Maltë': 'Malta', 'Maqedonisë': 'North Macedonia',
           'Maqedoni e Veriut': 'North Macedonia', 'Polonia': 'Poland', 'Polonisë': 'Poland', 'Poloni': 'Poland',
           'Moldavia': 'Romania and Moldova', 'Moldavinë': 'Romania and Moldova', 'Rumania': 'Romania and Moldova',
           'Moldavi': 'Romania and Moldova', 'Rumani': 'Romania and Moldova', 'Rusia': 'Russia', 'Rusisë': 'Russia',
           'Rusi': 'Russia', 'Serbia': 'Serbia', 'Serbi': 'Serbia', 'Sllovakia': 'Slovakia', 'Sllovaki': 'Slovakia',
           'Slloveni': 'Slovenia', 'Turqia': 'Turkey', 'Turqisë': 'Turkey', 'Turqi': 'Turkey', 'Ukraina': 'Ukraine',
           'Ukrainë': 'Ukraine', 'Erzya': 'Erzia', 'Bullgari': 'Bulgaria',
           'Bosnje dhe Hercegovinë': 'Bosnia and Herzegovina', 'Bashkortostan': 'Bashkortostan',
           'Tatarstan': 'Tatarstan', 'Bosnjë dhe Hercegovinë': 'Bosnia and Herzegovina', 'Shqipëri': 'Albania',
           'Çeki': 'Czechia', 'gjuhën Esperanto': 'Esperanto', },
    # sr countries
    'sr': {'Албанија': 'Albania', 'Аустрија': 'Austria', 'Атербејџан': 'Azerbaijan', 'Азербејџан': 'Azerbaijan',
           'Башкортостан': 'Bashkortostan', 'Белорусија': 'Belarus', 'Бугарска': 'Bulgaria', 'Јерменија': 'Armenia',
           'Босна': 'Bosnia and Herzegovina', 'Босна и Херцеговина': 'Bosnia and Herzegovina',
           'Црна Гора': 'Montenegro', 'Ерзја': 'Erzia', 'Есперанто': 'Esperanto', 'Естонија': 'Estonia',
           'Грузија': 'Georgia', 'Чешка': 'Czechia', 'Hrvatska': 'Croatia', 'Хрватска': 'Croatia',
           'Република Косово': 'Kosovo', 'Кримски Татари': 'Crimean Tatars', 'Литванија': 'Lithuania',
           'Летонија': 'Latvia', 'Мађарска': 'Hungary', 'Северна Македонија': 'North Macedonia',
           'Македонија': 'North Macedonia', 'Република Македонија': 'North Macedonia',
           'Молдавија': 'Romania and Moldova', 'Пољска': 'Poland', 'Руска Империја': 'Russia', 'Rusija': 'Russia',
           'Русија': 'Russia', 'Румунија': 'Romania and Moldova', 'Република Српска': 'Republic of Srpska',
           'Србија': 'Serbia', 'Словачка': 'Slovakia', 'Словенија': 'Slovenia', 'Турска': 'Turkey',
           'Украјина': 'Ukraine', 'грчка': 'Greece', 'Грчка': 'Greece', 'Казахстан': 'Kazakhstan', 'Grčka': 'Greece',
           'Малта': 'Malta', 'Võrumaa': 'Võro', 'Кипар': 'Cyprus', 'БиХ': 'Bosnia and Herzegovina',
           'Лeтoнија': 'Latvia', 'Пољскаа': 'Poland', 'Српска': 'Republic of Srpska', 'Маđарска': 'Hungary', },
    # tt countries
    'tt': {'Албания': 'Albania', 'Австрия': 'Austria', 'Әзербайҗан': 'Azerbaijan', 'Азәрбайҗан': 'Azerbaijan',
           'Башкортстан': 'Bashkortostan', 'Белорусия': 'Belarus', 'Беларусия': 'Belarus', 'Болгария': 'Bulgaria',
           'Әрмәнстан': 'Armenia', 'Босния һәм Герцоговина': 'Bosnia and Herzegovina',
           'Босния һәм Герцеговина': 'Bosnia and Herzegovina', 'Эрзя': 'Erzia', 'Эрзә': 'Erzia', 'Ирзә': 'Erzia',
           'Эсперанто': 'Esperanto', 'Эстония': 'Estonia', 'Гөрҗистан': 'Georgia', 'Чехия': 'Czechia',
           'Хорватия': 'Croatia', 'Косово Җөмһүрияте': 'Kosovo', 'Кырым татарлары': 'Crimean Tatars',
           'Литва': 'Lithuania', 'Latviä': 'Latvia', 'Маҗарстан': 'Hungary', 'Македония Җөмһүрияте': 'North Macedonia',
           'Македония': 'North Macedonia', 'Молдавия': 'Romania and Moldova', 'Молдова': 'Romania and Moldova',
           'Польша': 'Poland', 'РФ': 'Russia', 'Русия': 'Russia', 'Румыния': 'Romania and Moldova', 'Сербия': 'Serbia',
           'Словакия': 'Slovakia', 'Лужица': 'Sorbia', 'Төркия': 'Turkey', 'Украина': 'Ukraine', 'Греция': 'Greece',
           'Казакъстан': 'Kazakhstan', 'Латвия': 'Latvia', 'Aвстрия': 'Austria', 'Грузия': 'Georgia',
           'Tөркия': 'Turkey', 'Kосово': 'Kosovo', 'Косово': 'Kosovo', 'Төньяк Македония': 'North Macedonia',
           'Румыния һәм Moлдова': 'Romania and Moldova', 'Словения': 'Slovenia', 'Кырым-татар': 'Crimean Tatars',
           'Кырымтатарлары': 'Crimean Tatars', 'Румыния һәм Молдова': 'Romania and Moldova', 'Дон төбәге': 'Don',
           'Башкортостан': 'Bashkortostan', 'Черногория': 'Montenegro', 'Беларусь': 'Belarus', 'Венгрия': 'Hungary',
           'Мальта': 'Malta', 'Монтенегро': 'Montenegro', 'Белоруссия': 'Belarus', 'Россия': 'Russia',
           'Moлдова': 'Moldova', 'Россия Федерациясе': 'Russia', },
    # tr countries
    'tr': {'Arnavutluk': 'Albania', 'Avusturya': 'Austria', 'Azerbaycan': 'Azerbaijan', 'Başkurdistan': 'Bashkortostan',
           'Beyaz Rusya': 'Belarus', 'Bulgaristan': 'Bulgaria', 'Ermenistan': 'Armenia',
           'Bosna Hersek': 'Bosnia and Herzegovina', 'Bosna-Hersek': 'Bosnia and Herzegovina', 'Erzyanca': 'Erzia',
           'Erzya': 'Erzia', 'Esperanto': 'Esperanto', 'Estonya': 'Estonia', 'Gürcistan': 'Georgia',
           'Çek Cumhuriyeti': 'Czechia', 'Hırvatistan': 'Croatia', 'Don Bölgesi': 'Don', 'Kosova': 'Kosovo',
           'Kırım': 'Crimean Tatars', 'Kırım Tatar': 'Crimean Tatars', 'Kırım Tatarları': 'Crimean Tatars',
           'Litvanya': 'Lithuania', 'Letonya': 'Latvia', 'Macaristan': 'Hungary', 'Malta': 'Malta',
           'Kuzey Makedonya': 'North Macedonia', 'Makedonya Cumhuriyeti': 'North Macedonia',
           'Makedonya': 'North Macedonia', 'Karadağ': 'Montenegro', 'Moldova': 'Romania and Moldova',
           'Polonya': 'Poland', 'Rusya': 'Russia', 'СРСР': 'Russia', 'Romanya': 'Romania and Moldova',
           'Sırp Cumhuriyeti': 'Republic of Srpska', 'Sırbistan': 'Serbia', 'Sorblar': 'Sorbia', 'Slovakya': 'Slovakia',
           'Slovenya': 'Slovenia', 'Türkiye': 'Turkey', 'Ukrayna': 'Ukraine', 'Yunanistan': 'Greece',
           'Kazakistan': 'Kazakhstan', 'Tataristan': 'Tatarstan', 'Sırbistan Cumhuriyeti': 'Republic of Srpska',
           'Sıbistan': 'Serbia', 'Võro dili': 'Võro', 'Çingeneler': 'Roma', 'Kıbrıs': 'Cyprus', 'Çekya': 'Czechia',
           'Belarus': 'Belarus', 'Kırımçaklar': 'Crimean Tatars', 'Saha Cumhuriyeti': 'Sakha',  },
    # uk countries
    'uk': {'Албанія': 'Albania', 'Австрія': 'Austria', 'Азербайджан': 'Azerbaijan', 'Башкортостан': 'Bashkortostan',
           'Білорусія': 'Belarus', 'Білорусь': 'Belarus', 'Болгарія': 'Bulgaria', 'Вірменія': 'Armenia',
           'Боснія': 'Bosnia and Herzegovina',
           'Боснія і Герцеговина': 'Bosnia and Herzegovina', 'Боснія і Герцоговина': 'Bosnia and Herzegovina',
           'Боснія та Герцеговина': 'Bosnia and Herzegovina', 'Дон': 'Don', 'Ерзя': 'Erzia', 'Есперантида': 'Esperanto',
           'Есперанто': 'Esperanto', 'есперанто': 'Esperanto', 'Естонія': 'Estonia', 'Грузія': 'Georgia',
           'Чехія': 'Czechia', 'Хорватія': 'Croatia', 'Косово': 'Kosovo', 'Кримські Татари': 'Crimean Tatars',
           'Кримські татари': 'Crimean Tatars', 'Литва': 'Lithuania', 'Латвія': 'Latvia', 'Угорщина': 'Hungary',
           'Македонія': 'North Macedonia', 'Північна Македонія': 'North Macedonia',
           'Румунія, Молдова': 'Romania and Moldova', 'Молдова': 'Romania and Moldova', 'Чорногорія': 'Montenegro',
           'Польша': 'Poland', 'Польща': 'Poland', 'Російська Федерація': 'Russia', 'СРСР': 'Russia', 'Росія': 'Russia',
           'Румунія': 'Romania and Moldova', 'Румунія і Молдова': 'Romania and Moldova',
           'Республіка Сербська': 'Republic of Srpska', 'Сербія': 'Serbia', 'Словакія': 'Slovakia',
           'Словаччина': 'Slovakia', 'Словенія': 'Slovenia', 'Лужичани': 'Sorbia', 'лужичани': 'Sorbia',
           'Татарстан': 'Tatarstan', 'Туреччина': 'Turkey', 'Туречинна': 'Turkey', 'Україна': 'Ukraine',
           'Греція': 'Greece', 'Казахстан': 'Kazakhstan', 'Мальта': 'Malta', 'Виро': 'Võro', 'Роми': 'Roma',
           'Кіпр': 'Cyprus', },
    # hu countries
    'hu': {'Albánia': 'Albania', 'Ausztria': 'Austria', 'Azerbajdzsán': 'Azerbaijan', 'Baskíria': 'Bashkortostan',
           'Baskirföld': 'Bashkortostan', 'Fehéroroszország': 'Belarus', 'Belorusz': 'Belarus', 'Bulgária': 'Bulgaria',
           'Örményország': 'Armenia', 'Bosznia-Hercegovina': 'Bosnia and Herzegovina',
           'Bosznia és Hercegovina': 'Bosnia and Herzegovina', 'Doni régió': 'Don', 'Erzia': 'Erzia',
           'Eszperantó': 'Esperanto', 'Észtország': 'Estonia', 'Grúzia': 'Georgia', 'Csehország': 'Czechia',
           'Horvátország': 'Croatia', 'Koszovó': 'Kosovo', 'Koszovo': 'Kosovo', 'Krími tatárok': 'Crimean Tatars',
           'Litvánia': 'Lithuania', 'Lettország': 'Latvia', 'Magyarország': 'Hungary', 'Montenegró': 'Montenegro',
           'Macedónia': 'North Macedonia', 'Észak-Macedónia': 'North Macedonia', 'Moldávia': 'Romania and Moldova',
           'Lengyelország': 'Poland', 'Moldova': 'Romania and Moldova', 'Oroszország': 'Russia',
           'Románia': 'Romania and Moldova', 'Boszniai Szerb Köztársaság': 'Republic of Srpska', 'Szerbia': 'Serbia',
           'Szlovákia': 'Slovakia', 'Szlovénia': 'Slovenia', 'Tatárföld': 'Tatarstan', 'Törökország': 'Turkey',
           'Ukrajna': 'Ukraine', 'Görögország': 'Greece', 'Kazahsztán': 'Kazakhstan', 'Málta': 'Malta',
           'Szorbok': 'Sorbia', 'Belarusz': 'Belarus', 'Ciprusi Köztársaság': 'Cyprus', 'Ciprus': 'Cyprus',
           'cigány': 'Roma', 'Cigányok': 'Roma', 'Võro': 'Võro', 'Arománok': 'Aromanian', 'Erza nyelv': 'Erzya', },
    # kk countries
    'kk': {'Албания': 'Albania', 'Аустрия': 'Austria', 'Әзірбайжан': 'Azerbaijan', 'Башқұртстан': 'Bashkortostan',
           'Беларусь': 'Belarus', 'Болгария': 'Bulgaria', 'Армения': 'Armenia',
           'Босния және Герцеговина': 'Bosnia and Herzegovina', 'Эсперанто': 'Esperanto', 'Эстония': 'Estonia',
           'Грузия': 'Georgia', 'Чехия': 'Czechia', 'Хорватия': 'Croatia', 'Косово': 'Kosovo',
           'Қырым татарлары': 'Crimean Tatars', 'Литва': 'Lithuania', 'Латвия': 'Latvia', 'Мажарстан': 'Hungary',
           'Македония': 'North Macedonia', 'Молдова': 'Romania and Moldova', 'Польша': 'Poland', 'Ресей': 'Russia',
           'Румыния': 'Romania and Moldova', 'Сербия': 'Serbia', 'Словакия': 'Slovakia', 'Түркия': 'Turkey',
           'Украина': 'Ukraine', 'Грекия': 'Greece', 'Қазақстан': 'Kazakhstan', 'Татарстан': 'Tatarstan', },
    # et countries
    'et': {'Albaania': 'Albania', 'Austria': 'Austria', 'Aserbaidžaan': 'Azerbaijan', 'Baškortostanu': 'Bashkortostan',
           'Baškortostan': 'Bashkortostan', 'Valgevene': 'Belarus', 'Bulgaaria': 'Bulgaria', 'Armeenia': 'Armenia',
           'Bosnia ja Hertsegoviina': 'Bosnia and Herzegovina', 'Doni piirkond': 'Don', 'Esperanto': 'Esperanto',
           'Eesti': 'Estonia', 'Gruusia': 'Georgia', 'Tšehhi Vabariik': 'Czechia', 'Tšehhi': 'Czechia',
           'Horvaatia': 'Croatia', 'Kosovo': 'Kosovo', 'Krimski Tatari': 'Crimean Tatars', 'Leedu': 'Lithuania',
           'Läti': 'Latvia', 'Ungari': 'Hungary', 'Montenegro': 'Montenegro', 'Põhja-Makedoonia': 'North Macedonia',
           'Makedoonia': 'North Macedonia', 'Moldova': 'Romania and Moldova', 'Poola': 'Poland', 'Venemaa': 'Russia',
           'Rumeenia': 'Romania and Moldova', 'Serblaste Vabariik': 'Republic of Srpska',
           'Republika Srpska': 'Republic of Srpska', 'Serbia': 'Serbia', 'Sorbimaa': 'Sorbia', 'Slovakkia': 'Slovakia',
           'Sloveenia': 'Slovenia', 'Tatarstan': 'Tatarstan', 'Türgi': 'Turkey', 'Ukraina': 'Ukraine',
           'Kreeka': 'Greece', 'Kasahstan': 'Kazakhstan', 'Ersa': 'Erzia', 'Malta': 'Malta',
           'Krimmitatari': 'Crimean Tatars', 'esperanto': 'Esperanto', 'Sorbi': 'Sorbia', 'Doni regioon': 'Don',
           'Roma': 'Roma', 'Küpros': 'Cyprus', 'Cyprus': 'Cyprus', 'Crimean Tatars': 'Crimean Tatars', 'Donimaa': 'Don',
           'Don': 'Don', 'sorbid': 'Sorbia', 'Sorbia': 'Sorbia', 'Võro': 'Võro', 'Erzya': 'Erzia',
           'Georgia': 'Georgia', },
    # hr countries
    'hr': {'Albaniji': 'Albania', 'Albanija': 'Albania', 'Austriji': 'Austria', 'Austrija': 'Austria',
           'Azerbajdžanu': 'Azerbaijan', 'Azerbajdžan': 'Azerbaijan', 'Baškortostanu (Bashkortostan)': 'Bashkortostan',
           'Baškirska': 'Bashkortostan', 'Bjelorusiji': 'Belarus', 'Bjelorusija': 'Belarus', 'Bugarskoj': 'Bulgaria',
           'Bugarska': 'Bulgaria', 'Armeniji': 'Armenia', 'Armenija': 'Armenia',
           'Bosni i Hercegovini': 'Bosnia and Herzegovina', 'Bosne i Hercegovine': 'Bosnia and Herzegovina',
           'Bosna i Hercegovina': 'Bosnia and Herzegovina', 'Crnoj Gori': 'Montenegro', 'esperantu': 'Esperanto',
           'Esperanto': 'Esperanto', 'Estoniji': 'Estonia', 'Estonija': 'Estonia', 'Gruziji': 'Georgia',
           'Gruziji (Georgia)': 'Georgia', 'Gruzija': 'Georgia', 'Mađarske': 'Hungary', 'Češkoj (Czech)': 'Czechia',
           'Češkoj': 'Czechia', 'Češka': 'Czechia', 'Hrvatskoj': 'Croatia', 'Hrvatska': 'Croatia', 'Kosovo': 'Kosovo',
           'Kosovu': 'Kosovo', 'Krimskih Tatara': 'Crimean Tatars', 'Krim (Krimski Tatari)': 'Crimean Tatars',
           'Krimu (Krimski Tatari)': 'Crimean Tatars', 'Krimski Tatari': 'Crimean Tatars', 'Litvi': 'Lithuania',
           'Litva': 'Lithuania', 'Latviji': 'Latvia', 'Latvija': 'Latvia', 'Mađarskoj': 'Hungary',
           'Mađarska': 'Hungary', 'Makedoniji': 'North Macedonia', 'Makedonija': 'North Macedonia',
           'Moldaviji': 'Romania and Moldova', 'Moldavija': 'Romania and Moldova', 'Poljskoj': 'Poland',
           'Poljska': 'Poland', 'Rusiji': 'Russia', 'Rusija': 'Russia', 'Rumunjskoj (Romania)': 'Romania and Moldova',
           'Rumunjskoj': 'Romania and Moldova', 'Rumunjska': 'Romania and Moldova',
           'Republici Srpskoj': 'Republic of Srpska', 'Republika Srpska': 'Republic of Srpska', 'Srbiji': 'Serbia',
           'Srbije': 'Serbia', 'Srbija': 'Serbia', 'Slovačkoj': 'Slovakia', 'Slovačkoj (Slovakia)': 'Slovakia',
           'Slovačka': 'Slovakia', 'Sloveniji': 'Slovenia', 'Turskoj': 'Turkey', 'Turska': 'Turkey',
           'Ukrajini': 'Ukraine', 'Ukrajina': 'Ukraine', 'Grčkoj': 'Greece', 'Grčka': 'Greece',
           'Kazahstanu': 'Kazakhstan', 'Kazahstan': 'Kazakhstan', 'Erziji (Erzya)': 'Erzia', 'Erziji': 'Erzia',
           'Erzya': 'Erzia', 'Erzji': 'Erzia', 'BiH': 'Bosnia and Herzegovina', 'Malti': 'Malta',
           'Bugarske': 'Bulgaria', 'Lužički Srbi': 'Sorbia', 'Sjevernoj Makedoniji': 'North Macedonia',
           'Slovenija': 'Slovenia', 'Donu': 'Don', 'Kazahstana': 'Kazakhstan', 'Tatarstana': 'Tatarstan',
           'Rusije': 'Russia', 'Tatarstanu': 'Tatarstan', 'Baškirskoj': 'Bashkortostan', 'Esperantu': 'Esperanto',
           'Lužičkih Srba': 'Sorbia', 'Romi': 'Roma', 'Azerbejdžanu': 'Azerbaijan', 'Cipru': 'Cyprus',
           'Esperanta': 'Esperanto', 'Krimu': 'Crimean Tatars', 'Võru': 'Võro', 'Lužici': 'Sorbia', 'Malte': 'Malta',
           'Cipra': 'Cyprus', 'Grčke': 'Greece', },
    # sl countries
    'sl': {'Albanija': 'Albania', 'Armenija': 'Armenia', 'Avstrija': 'Austria', 'Azerbajdžan': 'Azerbaijan',
           'Baškortostan': 'Bashkortostan', 'Belorusija': 'Belarus', 'Bolgarija': 'Bulgaria',
           'Bosna in Hercegovina': 'Bosnia and Herzegovina', 'Češka': 'Czechia', 'Črna gora': 'Montenegro',
           'Donska republika': 'Don', 'Erzja': 'Erzia', 'Esperanto': 'Esperanto', 'Estonija': 'Estonia',
           'Grčija': 'Greece', 'Gruzija': 'Georgia', 'Hrvaška': 'Croatia', 'Kazahstan': 'Kazakhstan',
           'Kosovo': 'Kosovo', 'Krimski Tatar': 'Crimean Tatars', 'Latvija': 'Latvia', 'Litva': 'Lithuania',
           'Lužiška Srbija': 'Sorbia', 'Madžarska': 'Hungary', 'Malta': 'Malta', 'Poljska': 'Poland',
           'Romunija': 'Romania and Moldova', 'Rusija': 'Russia', 'Severna Makedonija': 'North Macedonia',
           'Slovaška': 'Slovakia', 'Srbija': 'Serbia', 'Tatarstan': 'Tatarstan', 'Turčija': 'Turkey',
           'Ukrajina': 'Ukraine', 'Donska regija': 'Don', 'Romunija in Moldavija': 'Romania and Moldova',
           'Republika srbska': 'Republic of Srpska', 'Moldavija': 'Romania and Moldova', 'Romi': 'Roma',
           'Ciper': 'Cyprus', 'Võrumaa': 'Võro', 'Lužiška srbija': 'Sorbia', 'Lužiški Srbi': 'Sorbia',
           'Tatari': 'Crimean Tatars', 'mednarodno': 'International', 'Ruska federacija': 'Russia',
           },
    # mt countries
    'mt': {'Awstrija': 'Austria', 'Slovakja': 'Slovakia', 'Ċekja': 'Czechia',
           'Bożnija u Ħerżegovina': 'Bosnia and Herzegovina', 'Greċja': 'Greece', 'Polonja': 'Poland',
           'Albania': 'Albania', 'Tararstan': 'Tatarstan', 'Armenia': 'Armenia', 'Azerbajġan': 'Azerbaijan',
           'Baxkortostan': 'Bashkortostan', 'Malta': 'Malta', 'Belarus': 'Belarus',
           'Bożnija-Ħerzegovina': 'Bosnia and Herzegovina', 'Sorbi': 'Sorbia', 'Bulgarija': 'Bulgaria',
           'Tatar tal-Krimea': 'Crimean Tatars', 'Maċedonja ta': 'North Macedonia', 'Kosovo': 'Kosovo',
           'Albanija': 'Albania', 'Serbja': 'Serbia', 'Montenegro': 'Montenegro',
           'BUlgarija': 'Bulgaria', 'Ungerija': 'Hungary', 'Latvja': 'Latvia',
           'Litwanja': 'Lithuania', 'Rumanija': 'Romania and Moldova', 'Slovakkja': 'Slovakia', 'Slovenja': 'Slovenia',
           'Kroazja': 'Croatia', 'Don region': 'Don', 'Erzya': 'Erzia', 'Esperanto': 'Esperanto', 'Estonja': 'Estonia',
           'Turkija': 'Turkey', 'Ġeorġja': 'Georgia', 'Każakistan': 'Kazakhstan',
           'Macedonja tat-Tramuntana': 'North Macedonia', 'Ir-Repubblika ta’ Srpska': 'Republic of Srpska',
           'Rumanija u Moldova': 'Romania and Moldova', 'Sorb': 'Sorbia', 'Tatarstan': 'Tatarstan',
           'Ukrajna': 'Ukraine', 'Federazzjoni Russa': 'Russia', 'Armenja': 'Armenia', 'Ażerbajġan': 'Azerbaijan',
           'Reġjun Don': 'Don', 'Erżja': 'Erzia', 'Repubblika Srpska': 'Republic of Srpska',
           'Repubblika Ċeka': 'Czechia',
           'Russja': 'Russia', 'Belarussja': 'Belarus', 'Ċipru': 'Cyprus', 'Tatari tal-Krimea': 'Crimean Tatars',
           'Võro': 'Võro', 'Ażerbaiġan': 'Azerbaijan', 'Don-Region': 'Don', 'Georgia': 'Georgia', 'Rom': 'Roma',
           'Roma': 'Roma', 'Baxkorstostan': 'Bashkortostan', },
    # sh countries
    'sh': {'Austriji': 'Austria', 'Albaniji': 'Albania', 'Kosovu': 'Kosovo', 'Hrvatskoj': 'Croatia',
           'Bosni i Hercegovini': 'Bosnia and Herzegovina', 'Grčkoj': 'Greece', 'Rumunjskoj': 'Romania and Moldova',
           'Estoniji': 'Estonia', 'Ukrajini': 'Ukraine', 'Poljskoj': 'Poland', 'Sloveniji': 'Slovenia',
           'Kipru': 'Cyprus',
           'Rusiji': 'Russia', 'Češkoj': 'Czechia', 'Gruziji': 'Georgia', 'Hrvatska': 'Croatia',
           'Srbiji': 'Serbia', 'Estonija': 'Estonia', 'Bosna i Hercegovina': 'Bosnia and Herzegovina',
           'Srbija': 'Serbia', 'Kosovo': 'Kosovo', 'Litva': 'Lithuania', 'Mađarska': 'Hungary', 'Poljska': 'Poland',
           'Crnoj Gori': 'Montenegro', },
    # sk countries
    'sk': {'Slovinsko': 'Slovenia', 'Maďarsko': 'Hungary', 'Rakúsko': 'Austria', 'Rumunsko': 'Romania and Moldova',
           'Bosna a Hercegovina': 'Bosnia and Herzegovina', 'Gruzínsko': 'Georgia', 'Chorvátsko': 'Croatia',
           'Kazachstan': 'Kazakhstan', 'Česko': 'Czechia', 'Estónsko': 'Estonia', 'Grécko': 'Greece',
           'Severné Macedónsko': 'North Macedonia', 'Lotyšsko': 'Latvia', 'Rusko': 'Russia', 'Uhorsko': 'Hungary',
           'Moldavsko': 'Romania and Moldova', 'Malta': 'Malta', 'Esperanto': 'Esperanto', 'Srbsko': 'Serbia',
           'Litva': 'Lithuania', 'Ukrajina': 'Ukraine', 'Bulharsko': 'Bulgaria', 'Albánsko': 'Albania',
           'Poľsko': 'Poland', 'Lužickí Srbi': 'Sorbia', 'Kosovo': 'Kosovo', 'Azerbajdžan': 'Azerbaijan',
           'Turecko': 'Turkey', 'Baškirsko': 'Bashkortostan', 'Arménsko': 'Armenia', 'Bielorusko': 'Belarus',
           'Republika Srpska': 'Republic of Srpska', 'Donský región': 'Don', 'Krymskí Tatári': 'Crimean Tatars',
           'Čierna Hora': 'Montenegro', 'Montenegro': 'Montenegro', 'Erzia': 'Erzia', 'Erzya': 'Erzia',
           'Tatarstan': 'Tatarstan', 'Tatársko': 'Tatarstan', 'Sorbia': 'Sorbia', 'Kipru': 'Cyprus', },
    'en': {'Montenegro': 'Montenegro', 'Belarus': 'Belarus', 'Erzya': 'Erzia', 'Serbia': 'Serbia', 'Poland': 'Poland',
           'Croatia': 'Croatia', 'Bosnia & Herzegovina': 'Bosnia and Herzegovina', 'Austria': 'Austria',
           'Slovenia': 'Slovenia', 'Turkey': 'Turkey', 'Ukraine': 'Ukraine', 'Czechia': 'Czechia',
           'Czech Republic': 'Czechia', 'Georgia': 'Georgia', 'Albania': 'Albania', 'Hungary': 'Hungary',
           'Lithuania': 'Lithuania', 'Azerbaijan': 'Azerbaijan', 'North Macedonia': 'North Macedonia',
           'Malta': 'Malta', 'Greece': 'Greece', 'Latvia': 'Latvia', 'Slovakia': 'Slovakia',
           'Romania and Moldova': 'Romania and Moldova', 'Bulgaria': 'Bulgaria',
           'Bosnia and Herzegovina': 'Bosnia and Herzegovina', 'Romania': 'Romania', 'Estonia': 'Estonia',
           'Crimean Tatars': 'Crimean Tatars', 'Bashkortostan': 'Bashkortostan', 'Cyprus': 'Cyprus',
           },

}


class BasicBot(
    # Refer pywikibot.bot for generic bot classes
    # SingleSiteBot,  # A bot only working on one site
    Bot,
    # MultipleSitesBot,  # A bot class working on multiple sites
    # CurrentPageBot,  # Sets 'current_page'. Process it in treat_page method.
    #                  # Not needed here because we have subclasses
    ExistingPageBot,  # CurrentPageBot which only treats existing pages
    NoRedirectPageBot,  # CurrentPageBot which only treats non-redirects
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

    summary_key = 'basic-changing'
    springList = {}
    templatesList = {}

    authors = {}
    authorsData = {}
    authorsArticles = {}
    authorsArticlesDE = {}
    missingCount = {}
    pagesCount = {}
    countryTable = {}
    lengthTable = {}
    lengthTablePL = {}
    womenAuthors = {}  # authors of articles about women k:author v; (count,[list])
    hrightsAuthors = {}  # authors of articles about Human Rights k:author v; (count,[list])
    otherCountriesList = {'pl': [], 'az': [], 'ba': [], 'be': [], 'be-tarask': [], 'bg': [], 'bs': [], 'de': [],
                          'crh': [], 'el': [], 'et': [], 'hyv': [], 'myv': [], 'eo': [], 'hr': [], 'hy': [], 'ka': [],
                          'kk': [], 'lv': [], 'lt': [], 'mk': [], 'mt': [], 'ro': [], 'roa-rup': [], 'ru': [],
                          'sah': [], 'sh': [], 'sk': [], 'sl': [], 'sq': [], 'sr': [], 'tt': [], 'tr': [], 'uk': [],
                          'hu': [], 'fiu-vro': [], 'en': [], }
    women = {'pl': 0, 'az': 0, 'ba': 0, 'be': 0, 'be-tarask': 0, 'bg': 0, 'bs': 0, 'de': 0, 'crh': 0, 'el': 0, 'et': 0,
             'myv': 0, 'eo': 0, 'hr': 0, 'hy': 0, 'hyv': 0, 'ka': 0, 'kk': 0, 'lv': 0, 'lt': 0, 'mk': 0, 'mt': 0,
             'ro': 0, 'roa-rup':0, 'ru': 0, 'sah': 0, 'sh': 0, 'sk': 0, 'sl': 0, 'sq': 0, 'sr': 0, 'tt': 0, 'tr': 0,
             'uk': 0, 'hu': 0, 'fiu-vro': 0, 'en': 0 }
    hrights = {'pl': 0, 'az': 0, 'ba': 0, 'be': 0, 'be-tarask': 0, 'bg': 0, 'bs': 0, 'de': 0, 'crh': 0, 'el': 0, 'et': 0,
             'myv': 0, 'eo': 0, 'hr': 0, 'hy': 0, 'hyv': 0, 'ka': 0, 'kk': 0, 'lv': 0, 'lt': 0, 'mk': 0, 'mt': 0,
             'ro': 0, 'roa-rup':0, 'ru': 0, 'sah': 0, 'sh': 0, 'sk': 0, 'sl': 0, 'sq': 0, 'sr': 0, 'tt': 0, 'tr': 0,
             'uk': 0, 'hu': 0, 'fiu-vro': 0, 'en': 0 }
    # local name for coutry parameter
    countryp = {'pl': 'kraj', 'az': 'ölkə', 'ba': 'ил', 'be': 'краіна', 'be-tarask': 'краіна', 'bg': 'държава',
                'bs': 'država',
                'de': 'land', 'crh': 'memleket', 'eo': 'lando', 'el': 'country', 'et': 'maa', 'hu': 'ország',
                'ka': 'ქვეყანა', 'lv': 'valsts', 'lt': 'šalis', 'mk': 'земја', 'mt': 'pajjiż',
                'myv': 'мастор', 'ro': 'țară', 'roa-rup': 'земја', 'ru': 'страна', 'sah': 'дойду', 'sh': 'zemlja', 'sl': 'država', 'sk': 'Krajina',
                'sq': 'country',
                'sr': 'држава', 'tt': 'ил', 'tr': 'ülke', 'uk': 'країна', 'hr': 'zemlja', 'hy': 'երկիր', 'kk': 'ел',
                'en': 'country', }
    # local name for topic parameter
    topicp = {'pl': 'parametr', 'az': 'qadınlar', 'ba': 'тема', 'be': 'тэма', 'be-tarask': 'тэма', 'bg': 'тема',
              'bs': 'tema',
              'de': 'thema', 'crh': 'mevzu', 'el': 'topic', 'et': 'teema', 'eo': 'temo', 'hu': 'téma', 'ka': 'თემა',
              'lv': 'tēma', 'lt': 'tema', 'mk': 'тема', 'myv': 'тема',
              'ro': 'secțiune', 'roa-rup': 'тема', 'ru': 'тема', 'sah': 'тиэмэ', 'sh': 'tema', 'sl': 'tema', 'sk': 'Parameter', 'sq': 'topic',
              'sr': 'тема',
              'tt': 'тема', 'tr': 'konu', 'uk': 'тема', 'hr': 'tema', 'hy': 'Թուրքիա|թեմա', 'kk': 'тақырып',
              'en': 'topic', }
    # local name for parameter value for: women
    womenp = {'pl': 'kobiety', 'az': 'qadınlar', 'ba': 'Ҡатын-ҡыҙҙар', 'be': 'Жанчыны', 'be-tarask': 'жанчыны',
              'bg': 'жени', 'bs': 'žena', 'de': 'Frauen', 'el': 'γυναίκες', 'et': 'naised', 'ka': 'ქალები',
              'lv': 'Sievietes',
              'mk': 'Жени', 'ro': 'Femei', 'ru': 'женщины', 'sh': 'Žene', 'sl': 'Ženske', 'mt': 'nisa',
              'sk': 'Žena', 'sq': 'Gratë', 'sr': 'Жене', 'tt': 'Хатын-кызлар', 'tr': 'Kadın', 'uk': 'жінки',
              'hu': 'nők', 'hr': 'Žene', 'hy': 'Կանայք', 'en': 'Women', }
    # local name for parameter value for: human rights
    hrightsp = {
            'pl': 'prawa człowieka', 'sq': 'Të drejtat e njeriut', 'hy': 'Մարդու իրավունքներ', 'az': 'İnsan hüquqları',
            'ba': 'Кеше хоҡуҡтары', 'be': 'Правы чалавека', 'be-tarask': 'Правы чалавека', 'sh': 'Ljudska prava',
            'bs': 'Ljudska prava', 'hr': 'Ljudska prava', 'sr': 'Људска права', 'myv': 'Ломанень прават', 'et': 'Inimõigused',
            'ge': 'ადამიანის უფლებები', 'de': 'Menschenrechte', 'el': 'νθρώπινα δικαιώματα', 'hu': 'Emberi jogok',
            'lv': 'Cilvēktiesības', 'mk': 'Човекови права', 'mt': 'Drittijiet umani', 'pl': 'Prawa człowieka',
            'ru': 'Права человека', 'sk': 'Ľudské práva', 'sl': 'Človekove pravice', 'tt': 'Кеше хокуклары',
            'tr': 'İnsan hakları, '

    }
    # local name for user parameter
    userp = {'pl': 'autor', 'az': 'istifadəçi', 'ba': 'ҡатнашыусы', 'be': 'удзельнік', 'be-tarask': 'удзельнік',
             'bg': 'потребител', 'bs': 'korisnik', 'de': 'benutzer', 'crh': 'qullanıcı', 'el': 'user', 'et': 'kasutaja',
             'hu': 'szerkesztő', 'eo': 'uzanto',
             'ka': 'მომხმარებელი', 'lv': 'dalībnieks', 'lt': 'naudotojas', 'mk': 'корисник', 'mt': 'utent',
             'myv': 'сёрмадыця', 'ro': 'utilizator', 'roa-rup': 'корисник', 'ru': 'участник', 'sah': 'кыттааччы', 'sh': 'user',
             'sl': 'uporabnik', 'sk': 'Redaktor', 'sq': 'user', 'sr': 'корисник', 'tt': 'кулланучы', 'tr': 'kullanıcı',
             'uk': 'користувач', 'hr': 'suradnik', 'hy': 'մասնակից', 'kk': 'қатысушы', 'en': 'user', }

    update_options = {
        'replace': False,  # delete old text and write the new text
        'summary': None,  # your own bot summary
        'text': 'Test',  # add this text from option. 'Test' is default
        'top': False,  # append text on top of the page
        'outpage': 'User:mastiBot/test',  # default output page
        'maxlines': 1000,  # default number of entries per page
        'testprint': False,  # print testoutput
        'negative': False,  # if True negate behavior i.e. mark pages that DO NOT contain search string
        'test': False,  # make verbose output
        'test2': False,  # make verbose output
        'test3': False,  # make verbose output
        'test4': False,  # make verbose output
        'test5': False,  # make verbose output
        'testartinfo': False,  # make verbose output
        'testgetart': False,  # make verbose output
        'testwomen': False,  # make verbose output for women table
        'testwomenauthors': False,  # make verbose output for women authors table
        'testnewbie': False,  # make verbose output for newbies
        'testlength': False,  # make verbose output for article length
        'testpickle': False,  # make verbose output for article list load/save
        'testusername': False,  # make verbose output for username found in template
        'testauthorwiki': False,  # make verbose output for author/wiki
        'testinterwiki': False,  # make verbose output for interwiki
        'testtemplatearg': False,  # make verbose output for interwiki
        'short': False,  # make short run
        'append': False,
        'reset': False,  # rebuild database from scratch
        'progress': False,  # report progress
        'testde': False,  # testprint for de.wiki stats
        'testhrightsauthors': False,
        'testhrights': False,

    }

    def articleexists(self, art):
        # check if article already in springList
        result = False
        lang = art.site.code
        title = art.title()
        if self.opt.testpickle:
            pywikibot.output('testing existence: [%s:%s]' % (lang, title))
        if lang in self.springList.keys():
            for a in self.springList[lang]:
                if self.opt.testpickle:
                    pywikibot.output('checking existence: [%s:%s]==%s' % (lang, title, a['title']))
                if a['title'] == title:
                    result = True
                    return result
        return result

    def run(self):

        # load springList from previous run
        self.springList = self.loadArticleList()

        # generate dictionary of articles
        # article[pl:title] = pageobject
        ceeArticles = self.getArticleList()
        self.printArtList(ceeArticles)

        # if self.opt.testpickle:
        #    return

        pywikibot.output('ART INFO')
        count = 0
        for a in ceeArticles:
            count += 1
            if self.articleexists(a):
                if self.opt.testpickle:
                    pywikibot.output('[%s][%i] SKIPPING: [%s:%s]' % (
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), count, a.site.code, a.title()))
            else:
                aInfo = self.getArtInfo(a)
                if self.opt.test:
                    pywikibot.output(aInfo)
                if self.opt.progress and not count % 20:
                    pywikibot.output('[%s][%i] Lang:%s Article:%s' % \
                                     (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), count, aInfo['lang'],
                                      aInfo['title']))
                # populate article list per language
                if aInfo['lang'] not in self.springList.keys():
                    self.springList[aInfo['lang']] = []
                self.springList[aInfo['lang']].append(aInfo)
                # populate authors list
                user = aInfo['creator']
                if self.opt.testnewbie:
                    pywikibot.output('NEWBIE CREATOR:%s' % user)
                if aInfo['creator'] not in self.authors.keys():
                    self.authors[aInfo['creator']] = 1
                else:
                    self.authors[aInfo['creator']] += 1
                self.newbie(aInfo['lang'], user)

        self.printArtInfo(self.springList)

        # save list for the future
        self.saveArticleList(self.springList)

        self.createCountryTable(self.springList)  # generate results for pages about countries
        self.createWomenTable(self.springList)  # generate results for pages about women
        self.createWomenAuthorsTable(self.springList)  # generate results for pages about women
        self.createHrightsTable(self.springList)  # generate results for pages about human rights
        self.createHrightsAuthorsTable(self.springList)  # generate results for pages about human rights
        self.createLengthTable(self.springList)  # generate results for pages length
        self.createLengthTablePL(self.springList)  # generate results for pages length pl.wiki
        self.createAuthorsArticles(self.springList)  # generate list of articles per author/wiki

        header = '{{TNT|Wikimedia CEE Spring 2023 navbar}}\n\n'
        header += '{{Wikimedia CEE Spring 2023/Statistics/Header}}\n\n'
        # header += "Last update: '''<onlyinclude>{{#time: Y-m-d H:i|{{REVISIONTIMESTAMP}}}} UTC</onlyinclude>'''.\n\n"
        header += "Last update: '''%s CEST'''.\n\n" % datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        footer = ''

        self.generateOtherCountriesTable(self.otherCountriesList, self.opt.outpage + '/Other countries',
                                         header, footer)
        self.generateResultCountryTable(self.countryTable, self.opt.outpage, header, footer)
        self.generateResultArticleList(self.springList, self.opt.outpage + '/Article list', header, footer)
        self.generateResultAuthorsPage(self.authors, self.opt.outpage + '/Authors list', header, footer)
        self.generateAuthorsCountryTable(self.authorsArticles, self.opt.outpage + '/Authors list/per wiki',
                                         header, footer)
        self.generateResultWomenPage(self.women, self.opt.outpage + '/Articles about women', header, footer)
        self.generateResultWomenAuthorsTable(self.womenAuthors,
                                             self.opt.outpage + '/Articles about women/Authors', header,
                                             footer)  # generate results for pages about women
        self.generateResultHrightsPage(self.hrights, self.opt.outpage + '/Articles about Human Rights', header, footer)
        self.generateResultHrightsAuthorsTable(self.hrightsAuthors,
                                             self.opt.outpage + '/Articles about Human Rights/Authors', header,
                                             footer)  # generate results for pages about women
        self.generateResultLengthPage(self.lengthTable, self.opt.outpage + '/Article length', header, footer)
        self.generateResultLengthAuthorsPage(self.lengthTable, self.opt.outpage + '/Authors list over 2kB',
                                             header, footer)
        self.generateResultLengthAuthorsPage(self.lengthTablePL, self.opt.outpage + '/Authors list over 2kB/Poland',
                                             header, footer)

        # special needs
        if 'de' in self.springList.keys():
            self.createStatsDe(self.springList['de'])  # generate list for stats on de.wiki
            self.generateResultAuthorsPageDE(self.authorsArticlesDE, 'Wikipedia:Wikimedia CEE Spring 2023/Punktestand',
                                             '', '')

        return

    def newbie(self, lang, user):
        # check if user is a newbie
        if not user:
            return False
        # newbieLimit = datetime.strptime("2019-12-20T12:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
        if self.opt.testnewbie:
            pywikibot.output('NEWBIE:%s' % self.authorsData)
        if user in self.authorsData.keys():
            if lang not in self.authorsData[user]['wikis']:
                self.authorsData[user]['wikis'].append(lang)
            if self.authorsData[user]['anon']:
                return False
            if not self.authorsData[user]['newbie']:
                return False
        else:
            self.authorsData[user] = {'newbie': True, 'wikis': [lang], 'anon': False, 'gender': 'unknown'}
        userpage = 'user:' + user
        site = pywikibot.Site(lang, fam='wikipedia')
        # page = pywikibot.Page(site,userpage)
        if self.opt.testnewbie:
            pywikibot.output('GETTING USER DATA:[[:%s:%s]]' % (lang, userpage))
        try:
            userdata = pywikibot.User(site, userpage)
        except:
            pywikibot.output('NEWBIE Exception: [[%s:user:%s]]' % (lang, user))
            return False
        self.authorsData[user]['anon'] = userdata.isAnonymous()
        if self.authorsData[user]['anon']:
            return False
        usergender = userdata.gender()
        if not self.authorsData[user]['gender'] == 'female':
            self.authorsData[user]['gender'] = usergender
        if self.authorsData[user]['newbie']:
            reg = userdata.registration()
            if reg:
                register = datetime.strptime(str(reg), "%Y-%m-%dT%H:%M:%SZ")
                if register < newbieLimit:
                    self.authorsData[user]['newbie'] = False
            else:
                self.authorsData[user]['newbie'] = False
            if self.opt.testnewbie:
                pywikibot.output('NEWBIE [%s]:%s' % (user, self.authorsData[user]))
                pywikibot.output('registration:%s' % reg)

        return self.authorsData[user]['newbie']

    def createCountryTable(self, aList):
        # creat dictionary with la:country article counts
        if self.opt.test2:
            pywikibot.output('createCountryTable')
        artCount = 0
        countryCount = 0
        for l in aList.keys():
            for a in aList[l]:
                # print a
                artCount += 1
                lang = a['lang']  # source language
                tmpl = a['template']  # template data {country:[clist], women:T/F, nocountry:T/F}
                if self.opt.test2:
                    pywikibot.output('tmpl:%s' % tmpl)
                if 'country' in tmpl.keys():
                    cList = tmpl['country']
                else:
                    continue
                if lang not in self.countryTable.keys():
                    self.countryTable[lang] = {}
                if tmpl['nocountry']:
                    if 'Empty' in self.countryTable[lang].keys():
                        self.countryTable[lang]['Empty'] += 1
                    else:
                        self.countryTable[lang]['Empty'] = 1
                else:
                    for c in cList:
                        if c not in self.countryTable[lang].keys():
                            self.countryTable[lang][c] = 0
                        self.countryTable[lang][c] += 1
                        countryCount += 1
                        if self.opt.test2:
                            pywikibot.output(
                                'art:%i coutry:%i, [[%s:%s]]' % (artCount, countryCount, lang, a['title']))
        return

    def createWomenTable(self, aList):
        # creat dictionary with la:country article counts
        if self.opt.test or self.opt.testwomen:
            pywikibot.output('createWomenTable')
            pywikibot.output(self.women)
        artCount = 0
        countryCount = 0
        for l in aList.keys():
            for a in aList[l]:
                # print a
                artCount += 1
                lang = a['lang']  # source language
                tmpl = a['template']  # template data {country:[clist], women:T/F}
                if 'woman' in tmpl.keys():
                    if not tmpl['woman']:
                        continue
                else:
                    continue
                if self.opt.testwomen:
                    pywikibot.output('tmpl:%s' % tmpl)
                if lang not in self.women.keys():
                    self.women[lang] = 1
                else:
                    self.women[lang] += 1
                if self.opt.testwomen:
                    pywikibot.output('self.women[%s]:%i' % (lang, self.women[lang]))
                countryCount += 1
                if self.opt.test or self.opt.testwomen:
                    pywikibot.output('art:%i Women:True [[%s:%s]]' % (artCount, lang, a['title']))
        if self.opt.testwomen:
            pywikibot.output('**********')
            pywikibot.output('self.women')
            pywikibot.output('**********')
            pywikibot.output(self.women)
        return

    def createWomenAuthorsTable(self, aList):
        # creat dictionary with la:country article counts
        if self.opt.test or self.opt.testwomenauthors:
            pywikibot.output('createWomenAuthorsTable')
            pywikibot.output(self.womenAuthors)
        artCount = 0
        countryCount = 0
        for l in aList.keys():
            for a in aList[l]:
                # print a
                artCount += 1

                if self.opt.testwomenauthors:
                    pywikibot.output('article:%s' % a)

                lang = a['lang']  # source language
                fam = a['family']
                tmpl = a['template']  # template data {country:[clist], women:T/F}
                newart = a['newarticle']
                womanart = tmpl['woman']
                if not newart:
                    if self.opt.test or self.opt.testwomenauthors:
                        pywikibot.output('Skipping updated [%i]: [[%s:%s]]' % (artCount, lang, a['title']))
                    continue
                if not womanart:
                    if self.opt.test or self.opt.testwomenauthors:
                        pywikibot.output('Skipping NOT WOMAN [%i]: [[%s:%s]]' % (artCount, lang, a['title']))
                    continue
                user = a['creator']
                if user in self.womenAuthors.keys():
                    self.womenAuthors[user]['count'] += 1
                    self.womenAuthors[user]['list'].append(
                        (fam + ':' if fam != 'wikipedia' else '') + lang + ':' + a['title'])
                else:
                    self.womenAuthors[user] = {'count': 1, 'list': [
                        (fam + ':' if fam != 'wikipedia' else '') + lang + ':' + a['title']]}

        if self.opt.testwomenauthors:
            pywikibot.output('**********')
            pywikibot.output('self.women.authors')
            pywikibot.output('**********')
            pywikibot.output(self.womenAuthors)
        return

    def createHrightsTable(self, aList):
        # creat dictionary with la:country article counts
        if self.opt.test or self.opt.testwomen:
            pywikibot.output('createHRightsTable')
            pywikibot.output(self.hrights)
        artCount = 0
        countryCount = 0
        for l in aList.keys():
            for a in aList[l]:
                # print a
                artCount += 1
                lang = a['lang']  # source language
                tmpl = a['template']  # template data {country:[clist], women:T/F}
                if 'hrights' in tmpl.keys():
                    if not tmpl['hrights']:
                        continue
                else:
                    continue
                if self.opt.testhrights:
                    pywikibot.output('tmpl:%s' % tmpl)
                if lang not in self.hrights.keys():
                    self.hrights[lang] = 1
                else:
                    self.hrights[lang] += 1
                if self.opt.testhrights:
                    pywikibot.output('self.hrights[%s]:%i' % (lang, self.hrights[lang]))
                countryCount += 1
                if self.opt.test or self.opt.testhrights:
                    pywikibot.output('art:%i HRights:True [[%s:%s]]' % (artCount, lang, a['title']))
        if self.opt.testhrights:
            pywikibot.output('**********')
            pywikibot.output('self.hrights')
            pywikibot.output('**********')
            pywikibot.output(self.hrights)
        return

    def createHrightsAuthorsTable(self, aList):
        # creat dictionary with la:country article counts
        if self.opt.test or self.opt.testhrightsauthors:
            pywikibot.output('createHRightsAuthorsTable')
            pywikibot.output(self.hrightsAuthors)
        artCount = 0
        countryCount = 0
        for l in aList.keys():
            for a in aList[l]:
                # print a
                artCount += 1

                if self.opt.testhrightsauthors:
                    pywikibot.output('article:%s' % a)

                lang = a['lang']  # source language
                fam = a['family']
                tmpl = a['template']  # template data {country:[clist], women:T/F}
                newart = a['newarticle']
                hrightsart = tmpl['hrights']
                if not newart:
                    if self.opt.test or self.opt.testhrightsauthors:
                        pywikibot.output('Skipping updated [%i]: [[%s:%s]]' % (artCount, lang, a['title']))
                    continue
                if not hrightsart:
                    if self.opt.test or self.opt.testhrightsauthors:
                        pywikibot.output('Skipping NOT HRIGHTS [%i]: [[%s:%s]]' % (artCount, lang, a['title']))
                    continue
                user = a['creator']
                if user in self.hrightsAuthors.keys():
                    self.hrightsAuthors[user]['count'] += 1
                    self.hrightsAuthors[user]['list'].append(
                        (fam + ':' if fam != 'wikipedia' else '') + lang + ':' + a['title'])
                else:
                    self.hrightsAuthors[user] = {'count': 1, 'list': [
                        (fam + ':' if fam != 'wikipedia' else '') + lang + ':' + a['title']]}

        if self.opt.testhrightsauthors:
            pywikibot.output('**********')
            pywikibot.output('self.hrights.authors')
            pywikibot.output('**********')
            pywikibot.output(self.hrightsAuthors)
        return

    def createLengthTable(self, aList):
        # creat dictionary with la:country article counts
        if self.opt.test or self.opt.testwomen or self.opt.testlength:
            pywikibot.output('createLengthTable')
            pywikibot.output(self.lengthTable)
        artCount = 0
        countryCount = 0
        for l in aList.keys():
            for a in aList[l]:
                if a['newarticle']:
                    artCount += 1
                    lang = a['lang']  # source language
                    fam = a['family']
                    title = (fam + ':' if fam != 'wikipedia' else '') + lang + ':' + a['title']  # art title

                    if self.opt.testlength:
                        pywikibot.output('Title:%s' % title)
                    self.lengthTable[title] = {'char': a['charcount'], 'word': a['wordcount'], 'creator': a['creator']}
                    if self.opt.testlength:
                        pywikibot.output('self.lengthtable[%s]:%s' % (title, self.lengthTable[title]))

        if self.opt.testlength:
            pywikibot.output('**********')
            pywikibot.output('self.lengthTable')
            pywikibot.output('**********')
            pywikibot.output(self.lengthTable)
        return

    def createLengthTablePL(self, aList):
        # creat dictionary with la:country article counts
        if self.opt.test or self.opt.testwomen or self.opt.testlength:
            pywikibot.output('createLengthTable')
            pywikibot.output(self.lengthTable)
        artCount = 0
        countryCount = 0
        for l in aList.keys():
            for a in aList[l]:
                if a['lang'] == 'pl':
                    if a['newarticle']:
                        lang = a['lang']  # source language
                        fam = a['family']
                        title = (fam + ':' if fam != 'wikipedia' else '') + lang + ':' + a['title']  # art title
                        artCount += 1
                        if self.opt.testlength:
                            pywikibot.output('Title:%s' % title)
                        self.lengthTablePL[title] = {'char': a['charcount'], 'word': a['wordcount'],
                                                     'creator': a['creator']}
                        if self.opt.testlength:
                            pywikibot.output('self.lengthtablePL[%s]:%s' % (title, self.lengthTablePL[title]))

        if self.opt.testlength:
            pywikibot.output('**********')
            pywikibot.output('self.lengthTablePL')
            pywikibot.output('**********')
            pywikibot.output(self.lengthTablePL)
        return

    def createAuthorsArticles(self, aList):
        # creat dictionary with author:wiki:{count,[artlist]} in self.authorsArticles
        if self.opt.test or self.opt.testauthorwiki:
            pywikibot.output('createAuthorsArticles')

        wikilist = list(aList.keys())

        artCount = 0
        countryCount = 0
        for l in aList.keys():
            for a in aList[l]:
                author = a['creator']
                if author not in self.authorsArticles.keys():
                    self.authorsArticles[author] = {}
                    for lang in wikilist:
                        self.authorsArticles[author][lang] = {'count': 0, 'list': []}

                self.authorsArticles[author][l]['count'] += 1
                self.authorsArticles[author][l]['list'].append(a['title'])

        if self.opt.testauthorwiki:
            pywikibot.output('**********')
            pywikibot.output('createAuthorsArticles')
            pywikibot.output('**********')
            pywikibot.output(self.authorsArticles)
        return

    def dePoints(self, artlen):
        kB = 1000
        if artlen > 6 * kB:
            return 5
        elif artlen > 2 * kB:
            return 1
        return 0

    def createStatsDe(self, aList):
        # create dictionary with author:wiki:{count,[artlist]} in self.authorsArticlesDE
        if self.opt.test or self.opt.testde:
            pywikibot.output('createStatDE')

        for a in aList:
            author = a['template']['user']

            if author not in self.authorsArticlesDE.keys():
                self.authorsArticlesDE[author] = {'total': 0, 'articles': []}

            if a['newarticle']:
                self.authorsArticlesDE[author]['total'] += self.dePoints(a['charcount'])
                self.authorsArticlesDE[author]['articles'].append(
                    {'title': a['title'], 'points': self.dePoints(a['charcount'])})
            else:
                self.authorsArticlesDE[author]['total'] += self.dePoints(a['diff'])
                self.authorsArticlesDE[author]['articles'].append(
                    {'title': a['title'], 'points': self.dePoints(a['diff'])})

        if self.opt.testde:
            pywikibot.output('**********')
            pywikibot.output('createStatsDe')
            pywikibot.output('**********')
            pywikibot.output(self.authorsArticlesDE)
        return

    def loadArticleList(self):
        # load article list form pickled dictionary
        result = {}
        if self.opt.reset:
            if self.opt.testpickle:
                pywikibot.output('PICKLING SKIPPED at %s' % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        else:
            if self.opt.testpickle:
                pywikibot.output('PICKLING LOAD at %s' % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            try:
                with open('masti/CEESpring2023.dat', 'rb') as datfile:
                    result = pickle.load(datfile)
            except (IOError, EOFError):
                # no saved history exists yet, or history dump broken
                if self.opt.testpickle:
                    pywikibot.output('PICKLING FILE NOT FOUND')
                result = {}
        if self.opt.testpickle:
            pywikibot.output('PICKLING LOADED LANGUAGES: %i' % len(result))
            pywikibot.output('PICKLING RESULT:%s' % result)
        return (result)

    def saveArticleList(self, artList):
        # save list as pickle file
        if self.opt.testpickle:
            pywikibot.output(
                'PICKLING SAVE at %s ARTICLE count %i' % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), len(artList)))
        with open('masti/CEESpring2023.dat', 'wb') as f:
            pickle.dump(artList, f, protocol=config.pickle_protocol)

    def getArticleList(self):
        # generate article list
        artList = []
        pywikibot.output('GETARTICLELIST artList:%s' % artList)
        # use pagegenerator to get articles linking to CEE templates
        # plwiki = pywikibot.Site('pl',fam='wikipedia')
        # p = pywikibot.Page( plwiki, "Szablon:CEE Spring 2023" )
        # while True:
        for p in self.generator:
            # p = t.toggleTalkPage()
            pywikibot.output('Treating: %s' % p.title())
            d = p.data_item()
            pywikibot.output('WD: %s' % d.title())
            # dataItem = d.get()
            count = 0
            for i in self.genInterwiki(p):
                if self.opt.test:
                    pywikibot.output('Searching for interwiki. Page:%s, Type:%s' % (i, type(i)))
                # lang = self.lang(i.title(as_link=True, force_interwiki=True))
                lang = i.site.code
                fam = i.site.family
                if self.opt.test:
                    pywikibot.output('Searching for interwiki. Lang:%s Family:%s' % (lang, fam))

                # test switch
                if self.opt.short:
                    if lang not in ('de'):
                        continue

                self.templatesList[lang] = [i.title()]
                pywikibot.output(
                    'Getting template redirs to %s Lang:%s' % (i.title(as_link=True, force_interwiki=True), lang))
                for p in i.getReferences(namespaces=10, filter_redirects=True):
                    self.templatesList[lang].append(p.title())
                    if self.opt.test2:
                        pywikibot.output('REDIR TEMPLATE:%s' % p.title(as_link=True, force_interwiki=True))

                pywikibot.output(
                    'Getting references to %s Lang:%s Fam:%s' % (
                    i.title(as_link=True, force_interwiki=True), lang, fam))
                if self.opt.test2:
                    pywikibot.output('REDIR TEMPLATE LIST:%s' % self.templatesList[lang])
                countlang = 0
                for p in i.getReferences(namespaces=1):
                    artParams = {}
                    art = p.toggleTalkPage()
                    if art.exists():
                        countlang += 1
                        artList.append(art)
                        if self.opt.testgetart:
                            pywikibot.output(
                                'getArticleList #%i/%i:%s:%s:%s' % (count, countlang, fam, lang, art.title()))
                        count += 1
            # break
        # get sk.wiki article list
        return (artList)

    def printArtList(self, artList):
        for p in artList:
            s = p.site
            l = s.code
            if self.opt.test:
                pywikibot.output('Page lang:%s : %s' % (l, p.title(as_link=True, force_interwiki=True)))
        return

    def printArtInfo(self, artInfo):
        # test print of article list result
        # if self.opt.testartinfo:
        #    pywikibot.output('***************************************')
        #    pywikibot.output('**            artInfo                **')
        #    pywikibot.output('***************************************')
        for l in artInfo.keys():
            for a in artInfo[l]:
                if self.opt.testartinfo:
                    pywikibot.output(a)
        return

    def cleanText(self, text):
        # remove unnecessary parts of wikitext
        text = textlib.removeDisabledParts(text)
        text = textlib.removeLanguageLinks(text)
        text = textlib.removeCategoryLinks(text)
        return (text)

    def getWordCount(self, text):
        # get a word count for text
        return (len(text.split()))

    def getArtLength(self, text):
        # get article length
        return (len(text))

    def cleanUsername(self, user):
        # remove lang> from username
        if '>' in user:
            user = re.sub(r'.*\>', '', user)
        return (user)

    def getDiffSize(self, art, user):
        # get diff size in art by user
        # artsize = len(self.cleanText(art.text))
        lastsize = 0
        startsize = 0
        found = False
        imported = False
        for r in art.revisions():
            if self.opt.testde:
                pywikibot.output(
                    'REVISION: size:{}, user:{}, timestamp:{}, comment:{}'.format(r.size, r.user, r.timestamp,
                                                                                  r.comment))
            if 'importiert:' in r.comment:
                imported = True
            if not found and r.user == user:
                lastsize = r.size
                found = True
            if r.timestamp < SpringStart:
                startsize = r.size
                break
        if self.opt.testde:
            pywikibot.output(
                '[[{}]]: last({}) - start({}) = {}'.format(art.title(), lastsize, startsize, lastsize - startsize))
        if imported:
            return lastsize
        else:
            return lastsize - startsize

    def getArtInfo(self, art):
        # get article language, creator, creation date
        artParams = {}
        talk = art.toggleTalkPage()
        if art.exists():
            creator, creationDate = self.getUpdater(art)
            creator = self.cleanUsername(creator)
            lang = art.site.code
            fam = art.site.family.name

            woman = self.checkWomen(art)
            # woman = False
            hrights = False
            artParams['title'] = art.title()
            artParams['lang'] = lang
            artParams['family'] = fam
            artParams['creator'] = creator
            artParams['creationDate'] = creationDate
            artParams['newarticle'] = self.newArticle(art)
            cleantext = self.cleanText(art.text)
            artParams['charcount'] = self.getArtLength(cleantext)
            artParams['wordcount'] = self.getWordCount(cleantext)

            if self.opt.test2:
                pywikibot.output('artParams[ArtInfo]:%s' % artParams)

            artParams['template'] = {'country': [], 'user': creator, 'woman': woman, 'hrights': hrights, 'nocountry': False}

            if lang in self.templatesList.keys() and talk.exists():
                TmplInfo = self.getTemplateInfo(talk, self.templatesList[lang], lang)
                artParams['template'] = TmplInfo
            if not artParams['template']['woman']:
                artParams['template']['woman'] = woman
            if not artParams['template']['hrights']:
                artParams['template']['hrights'] = hrights
            if not len(artParams['template']['country']):
                artParams['template']['nocountry'] = True
            # if artParams['template']['user']:
            #    creator = artParams['template']['user']
            if artParams['creator'] == "'''UNKNOWN USER'''":
                artParams['creator'] = artParams['template']['user']

            if not artParams['newarticle'] and artParams['lang'] == 'de':
                artParams['diff'] = self.getDiffSize(art, artParams['template']['user'])

            # print artParams
            if self.opt.test2:
                pywikibot.output('artParams:%s' % artParams)
        return (artParams)

    def checkWomen(self, art):
        # check if the article is about woman
        # using WikiData
        try:
            d = art.data_item()
            if self.opt.test4:
                pywikibot.output('WD: %s (checkWomen)' % d.title())
            dataItem = d.get()
            # pywikibot.output('DataItem:%s' % dataItem.keys()  )
            claims = dataItem['claims']
        except:
            return (False)
        try:
            gender = claims["P21"]
        except:
            return (False)
        for c in gender:
            cjson = c.toJSON()
            genderclaim = cjson['mainsnak']['datavalue']['value']['numeric-id']
            if '6581072' == str(genderclaim):
                if self.opt.test4:
                    pywikibot.output('%s:Woman' % art.title())
                return (True)
            else:
                if self.opt.test4:
                    pywikibot.output('%s:Man' % art.title())
                return (False)
        return (False)

    def getUpdater(self, art):
        # find author and update datetime of the biggest update within CEESpring
        try:
            # initrev = art.oldest_revision
            # if self.opt.test3:
            #    pywikibot.output(initrev)
            # creator, creationDate = art.oldest_revision()
            creator = art.oldest_revision.user
            creationDate = art.oldest_revision.timestamp
        except:
            pywikibot.output('EXCEPTION: oldest_revision')
            return ("'''UNKNOWN USER'''", "'''UNKNOWN DATE'''")
        # SpringStart = datetime.strptime("2023-03-20T12:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
        if self.newArticle(art):
            if self.opt.test3:
                pywikibot.output('New art creator %s:%s (T:%s)' % (
                    art.title(as_link=True, force_interwiki=True), creator, creationDate))
            return (creator, creationDate)
        else:
            # for rv in art.revisions(reverse=True,starttime="2017-03-20T12:00:00Z",endtime="2017-06-01T00:00:00Z"):
            for rv in art.revisions(reverse=True, starttime=datetime.strftime(SpringStart, "%Y-%m-%dT%H:%M:%SZ")):
                if self.opt.test3:
                    pywikibot.output('updated art editor %s:%s (T:%s)' % (
                        art.title(as_link=True, force_interwiki=True), rv.user, rv.timestamp))
                if datetime.strptime(str(rv.timestamp), "%Y-%m-%dT%H:%M:%SZ") > SpringStart:
                    if self.opt.test3:
                        pywikibot.output('returning art editor %s:%s (T:%s)' % (
                            art.title(as_link=True, force_interwiki=True), rv.user, rv.timestamp))
                    return (rv.user, rv.timestamp)
                else:
                    if self.opt.test3:
                        pywikibot.output('Skipped returning art editor %s:%s (T:%s)' % (
                            art.title(as_link=True, force_interwiki=True), rv.user, rv.timestamp))
                # if self.opt.test3:
                #    pywikibot.output('updated art editor %s:%s (T:%s)' % (art.title(as_link=True,force_interwiki=True),rv['user'],rv['timestamp']))
            #    return(rv['user'],rv['timestamp'])
            return ("'''UNKNOWN USER'''", creationDate)

    def newArticle(self, art):
        # check if the article was created within CEE Spring
        try:
            # initrev = art.oldest_revision
            # if self.opt.test3:
            #    pywikibot.output(initrev)
            # creationDate = art.oldest_revision().timestamp
            # creator = initrev.user
            creationDate = art.oldest_revision.timestamp
        except:
            pywikibot.output('EXCEPTION: newArticle: {}'.format(art.title()))
            return (False)
        # SpringStart = datetime.strptime("2023-03-20T12:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
        # SpringEnd = datetime.strptime("2023-06-01T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
        # return (datetime.strptime(creationDate, "%Y-%m-%dT%H:%M:%SZ") > SpringStart)
        return (creationDate > SpringStart)

    def userName(self, text):
        # extract username from template param value
        uNameR = re.compile(r'.*?:(?P<username>.*)')
        if self.opt.testusername:
            pywikibot.output('userName:%s' % text)
        if '[' in text:
            uName = uNameR.match(text)
            if uName:
                return (uName.group('username'))
            else:
                return (None)
        elif not len(text):
            return (None)
        else:
            return (text)

    def getTemplateInfo(self, page, template, lang):
        param = {}
        # author, creationDate = self.getUpdater(page)
        parlist = {'country': [], 'user': None, 'woman': False, 'hrights': False, 'nocountry': False}
        if self.opt.test2:
            pywikibot.output('page:%s' % page.text)
        # return dictionary with template params
        for t in page.templatesWithParams():
            title, params = t
            # print(title)
            # print(params)
            tt = re.sub(r'\[\[.*?:(.*?)\]\]', r'\1', title.title())
            if self.opt.test2:
                pywikibot.output('tml:%s * %s * %s' % (title, tt, template))
            if tt in template:
                paramcount = 1
                countryDef = False  # check if country defintion exists
                parlist['woman'] = False
                parlist['hrights'] = False
                parlist['country'] = []
                parlist['user'] = None
                for p in params:
                    named, name, value = self.templateArg(p)
                    # strip square brackets from value
                    if lang == 'myv' and name.startswith(self.countryp['myv']):
                        value = re.sub(r"\'*\{\{Масторкоцт *\| *([^\}]*)[^\n]*", r'\1', value)
                    else:
                        value = re.sub(r"\'*\[*([^\]\|\']*).*", r'\1', value)
                    if not named:
                        name = str(paramcount)
                    param[name] = value
                    paramcount += 1
                    if self.opt.test2:
                        pywikibot.output('p:%s' % p)
                    # check username in template
                    if lang in self.userp.keys() and name.lower().startswith(self.userp[lang].lower()):
                        if self.opt.test:
                            pywikibot.output('user:%s:%s' % (name, value))
                        # if lang in self.userp.keys() and value.lower().startswith(self.userp[lang].lower()):
                        #    parlist['user'] = value
                        parlist['user'] = self.userName(value)
                        if self.opt.testusername:
                            pywikibot.output('[[%s]] par value:%s' % (page.title(), value))
                            pywikibot.output('[[%s]] username:%s' % (page.title(), parlist['user']))
                    # check article about women
                    if lang in self.topicp.keys() and name.lower().startswith(self.topicp[lang].lower()):
                        if self.opt.test2:
                            pywikibot.output('topic:%s:%s' % (name, value))
                        if lang in self.womenp.keys() and value.lower().startswith(self.womenp[lang].lower()):
                            # self.women[lang] += 1
                            parlist['woman'] = True
                        if value.lower().startswith('human rights'):
                            parlist['hrights'] = True
                    # check article about human rights
                    if lang in self.topicp.keys() and name.lower().startswith(self.topicp[lang].lower()):
                        if self.opt.test2:
                            pywikibot.output('topic:%s:%s' % (name, value))
                        if lang in self.hrightsp.keys() and value.lower().startswith(self.hrightsp[lang].lower()):
                            # self.women[lang] += 1
                            parlist['hrights'] = True
                    # check article about country
                    if lang in self.countryp.keys() and name.lower().startswith(self.countryp[lang].lower()):
                        if self.opt.test2:
                            pywikibot.output('country:%s:%s:%i' % (name, value, len(value)))
                        if len(value) > 0:
                            countryDef = True
                            if lang in countryNames.keys() and value in (countryNames[lang].keys()):
                                countryEN = countryNames[lang][value]
                                if self.opt.test2:
                                    pywikibot.output('countryEN:%s (%s)' % (countryEN, value))
                                if not countryEN in parlist['country']:
                                    if self.opt.test2:
                                        pywikibot.output('appending countryEN:%s' % countryEN)
                                    parlist['country'].append(countryEN)
                                    if lang not in self.pagesCount.keys():
                                        self.pagesCount[lang] = {}
                                    if countryEN in self.pagesCount[lang].keys():
                                        self.pagesCount[lang][countryEN] += 1
                                    else:
                                        self.pagesCount[lang][countryEN] = 1
                            else:
                                if not value in parlist['country']:
                                    if self.opt.test2:
                                        pywikibot.output('appending other country:%s' % value)
                                    parlist['country'].append(value)
                                    if value not in self.otherCountriesList[lang]:
                                        self.otherCountriesList[lang].append(value)
                    if self.opt.test:
                        pywikibot.output(self.pagesCount)
                if self.opt.test3:
                    # pywikibot.output('PARAM:%s' % param)
                    pywikibot.output('PARLIST:%s' % parlist)
                return parlist
        return parlist

    def lang(self, template):
        return (re.sub(r'\[\[(.*?):.*?\]\]', r'\1', template))

    def genInterwiki(self, page):
        # yield interwiki sites generator
        iw = []
        iw.append(page)
        try:
            for s in page.data_item().iterlinks():
                if self.opt.testinterwiki:
                    pywikibot.output('SL iw: %s' % s)
                spage = pywikibot.Page(s)
                if self.opt.testinterwiki:
                    pywikibot.output('SL spage')
                    pywikibot.output('gI Page: %s' % spage.title(force_interwiki=True))
                    pywikibot.output('gI Site:%s Family:%s' % (spage.site, spage.site.family))
                if spage.site.family in allowedFamilies:
                    iw.append(spage)
                print(iw)
        except Exception as e:
            pywikibot.output('genInterwiki EXCEPTION %s' % str(e))
            pass
        # print(iw)
        return (iw)

    def generateOtherCountriesTable(self, res, pagename, header, footer):
        """
        Generates results page from res
        Starting with header, ending with footer
        Output page is pagename
        """
        locpagename = re.sub(r'.*:', '', pagename)

        finalpage = header

        if self.opt.test:
            pywikibot.output('**************************')
            pywikibot.output('generateOtherCountriesTable')
            pywikibot.output('**************************')
            pywikibot.output('OtherCountries:%s' % self.otherCountriesList)

        for c in self.otherCountriesList.keys():
            finalpage += '\n== ' + c + ' =='
            pywikibot.output('== ' + c + ' ==')
            for i in self.otherCountriesList[c]:
                pywikibot.output('c:%s, i:%s' % (c, i))
                finalpage += '\n# <nowiki>' + i + '</nowiki>'

        finalpage += footer
        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        if self.opt.test or self.opt.progress:
            pywikibot.output('OtherCountries:%s' % outpage.title())
        outpage.text = finalpage
        outpage.save(summary=self.opt.summary)
        if self.opt.test or self.opt.progress:
            pywikibot.output('OtherCountries SAVED')

        return

    def generateResultCountryTable(self, res, pagename, header, footer):
        """
        Generates results page from res
        Starting with header, ending with footer
        Output page is pagename
        """
        locpagename = re.sub(r'.*:', '', pagename)

        finalpage = header

        if self.opt.test:
            pywikibot.output('**************************')
            pywikibot.output('generateResultCountryTable')
            pywikibot.output('**************************')

        # total counters
        countryTotals = {}
        for c in countryList:
            countryTotals[c] = 0

        # generate table header
        finalpage += '\n{| class="wikitable sortable" style="text-align: center;"'
        finalpage += '\n|-'
        finalpage += '\n! {{Vert header|stp=1|Wiki / Country}}'
        finalpage += ' !! {{Vert header|stp=1|Total}} '
        for c in countryList:
            finalpage += ' !! {{Vert header|stp=1|%s}}' % c
        finalpage += ' !! {{Vert header|stp=1|Total}} !! {{Vert header|stp=1|Wiki / Country}}'

        # generate table rows
        for wiki in res.keys():
            finalpage += '\n|-'
            finalpage += '\n| [[' + locpagename + '/Article list#' + wiki + '.wikipedia|' + wiki + ']]'
            wikiTotal = 0  # get the row total
            newline = ''  # keep info for the table row
            for c in countryList:
                # newline += ' || '
                if 'Other' in c:
                    if self.opt.test5:
                        pywikibot.output('other:%s' % c)
                        pywikibot.output('res[wiki]:%s' % res[wiki])
                    otherCountry = 0  # count other countries
                    for country in res[wiki]:
                        if country not in countryList and not country == '':
                            if self.opt.test5:
                                pywikibot.output('country:%s ** otherCountry=%i+%i=%i' % \
                                                 (country, otherCountry, res[wiki][country],
                                                  otherCountry + res[wiki][country]))
                            otherCountry += res[wiki][country]
                    newline += ' || ' + str(otherCountry)
                    wikiTotal += otherCountry  # add to wiki total
                    countryTotals[c] += otherCountry
                else:
                    if self.opt.test5:
                        pywikibot.output('c:%s, wiki:%s' % (c, wiki))
                    if c in res[wiki].keys():
                        if self.opt.test5:
                            pywikibot.output('c:%s, wiki:%s, res[wiki][c]:%s' % (c, wiki, res[wiki][c]))
                        if res[wiki][c]:
                            if wiki in languageCountry.keys() and c in languageCountry[wiki]:
                                newline += ' || style="background-color:LightSlateGray" | ' + str(res[wiki][c])
                            else:
                                newline += ' || ' + str(res[wiki][c])
                            if self.opt.test5:
                                pywikibot.output('res[%s][%s]:%s - languageCountry[%s]:%s = %s' % \
                                                 (wiki, c, res[wiki][c], wiki, languageCountry[wiki], c))
                                pywikibot.output('NEWLINE:%s' % newline)
                            wikiTotal += res[wiki][c]  # add to wiki total
                            countryTotals[c] += res[wiki][c]

                    elif wiki in languageCountry.keys():
                        if wiki in languageCountry.keys() and c in languageCountry[wiki]:
                            if self.opt.test5:
                                pywikibot.output('languageCountry[wiki]:%s = %s' % (languageCountry[wiki], c))
                            newline += '|| style="background-color:LightSlateGray" | — '
                        else:
                            if self.opt.test5:
                                pywikibot.output('Empty cell')
                            newline += ' || '
                    else:
                        if self.opt.test5:
                            pywikibot.output('Empty cell')
                        newline += ' || '

            # add row (wiki) total to table
            finalpage += " || '''" + str(wikiTotal) + "'''" + newline + " || '''" + str(wikiTotal) + "'''"
            finalpage += ' || [[' + locpagename + '/Article list#' + wiki + '.wikipedia|' + wiki + ']]'

        finalpage += '\n|-'

        # generate totals
        totalTotal = 0
        lastRow = ''
        for c in countryList:
            lastRow += ' !! ' + str(countryTotals[c])
            totalTotal += countryTotals[c]
        finalpage += "\n! Total: !! '''" + str(totalTotal) + "'''" + lastRow + " || '''" + str(totalTotal) + "'''"
        # generate table footer
        finalpage += '\n|}'

        finalpage += "\n\n'''NOTE:''' the table counts references to respective countries. Article can reference more than 1 country"

        finalpage += footer

        if self.opt.test2:
            pywikibot.output(finalpage)

        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        if self.opt.test:
            pywikibot.output('WomenPage:%s' % outpage.title())
        outpage.text = finalpage
        outpage.save(summary=self.opt.summary)

        return

    def generateAuthorsCountryTable(self, res, pagename, header, footer):
        """
        Generates results page from res
        Starting with header, ending with footer
        Output page is pagename
        """
        locpagename = re.sub(r'.*:', '', pagename)

        finalpage = header

        pywikibot.output('***************************')
        pywikibot.output('generateAuthorsCountryTable')
        pywikibot.output('***************************')

        # total counters
        wikiTotals = {}
        wikiList = list(self.otherCountriesList.keys())
        for a in wikiList:
            wikiTotals[a] = 0

        # generate table header
        finalpage += '\n{| class="wikitable sortable" style="text-align: center;"'
        finalpage += '\n|-'
        finalpage += '\n! author/wiki'
        finalpage += ' !! Total'
        for w in wikiList:
            finalpage += ' !! ' + w
        finalpage += ' !! Total'

        # generate table rows
        for author in res.keys():
            finalpage += '\n|-'
            finalpage += '\n| [[user:%s|%s]]' % (author, author)
            authorTotal = 0  # get the row total
            newline = ''  # keep info for the table row
            for w in wikiList:
                newline += ' || '
                if w in res[author].keys():
                    if res[author][w]:
                        newline += str(res[author][w]['count'])
                        authorTotal += res[author][w]['count']  # add to author total (horizontal)
                        wikiTotals[w] += res[author][w]['count']  # add to wiki total {verical)

            # add row (wiki) total to table
            finalpage += " || '''" + str(authorTotal) + "'''" + newline + " || '''" + str(authorTotal) + "'''"

        finalpage += '\n|-'

        # generate totals
        totalTotal = 0
        finalpage += "\n! Total: !! '''" + str(totalTotal) + "'''"
        for w in wikiList:
            finalpage += ' !! ' + str(wikiTotals[w])
            totalTotal += wikiTotals[w]
        finalpage += " || '''" + str(totalTotal) + "'''"
        # generate table footer
        finalpage += '\n|}'

        finalpage += "\n\n'''NOTE:''' the table counts all articles per author: both new and updated"

        finalpage += footer

        if self.opt.testauthorwiki:
            pywikibot.output(finalpage)

        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        if self.opt.testauthorwiki:
            pywikibot.output('authorListperWiki:%s' % outpage.title())
        outpage.text = finalpage
        outpage.save(summary=self.opt.summary)

        return

    def generateResultWomenPage(self, res, pagename, header, footer):
        """
        Generates results page from res
        Starting with header, ending with footer
        Output page is pagename
        """
        locpagename = re.sub(r'.*:', '', pagename)

        finalpage = header
        itemcount = 0
        artcount = 0
        finalpage += '\n== Articles about women ==\n'

        finalpage += '\n{| class="wikitable sortable" style="text-align: center;"'
        finalpage += '\n!#'
        finalpage += '\n!Wikipedia'
        finalpage += '\n!Articles'

        # ath = sorted(self.authors, reverse=True)
        ath = sorted(res, key=res.__getitem__, reverse=True)
        for a in ath:
            itemcount += 1
            finalpage += '\n|-\n| %i. || %s || %i' % (itemcount, a, res[a])
            artcount += res[a]
        # generate totals
        finalpage += '\n|-\n! !! Total: !! %i' % artcount

        finalpage += '\n|}'

        finalpage += '\n\nTotal number of articles: ' + str(artcount)

        finalpage += "\n\n'''NOTE:''' page counts all articles - new and updated"

        finalpage += footer

        # pywikibot.output(finalpage)

        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        if self.opt.test:
            pywikibot.output('WomenPage:%s' % outpage.title())
        outpage.text = finalpage
        outpage.save(summary=self.opt.summary)
        return

    def generateResultWomenAuthorsTable(self, res, pagename, header, footer):
        """
        Generates results page from res
        Starting with header, ending with footer
        Output page is pagename
        """
        locpagename = re.sub(r'.*:', '', pagename)

        if self.opt.testwomenauthors:
            pywikibot.output(res)

        finalpage = header
        itemcount = 0
        artcount = 0
        finalpage += '\n== Articles about women authors ==\n'

        finalpage += '\n{| class="wikitable sortable" style="text-align: center;"'
        finalpage += '\n!#'
        finalpage += '\n!Author'
        finalpage += '\n!Count'
        finalpage += '\n!Articles'

        # ath = sorted(self.authors, reverse=True)
        ath = sorted(res, key=lambda x: (res[x]['count']), reverse=True)
        # ath = sorted(res, key=res.__getitem__, reverse=True)
        for a in ath:
            if not a or 'UNKNOWN USER' in a or a == '':
                author = "'''unknown'''"
            else:
                author = a
            itemcount += 1
            finalpage += '\n|-\n| %i. || %s || %s || %s' % (
                itemcount, author, res[a]['count'], '[[:' + ']], [[:'.join(res[a]['list']) + ']]')
            artcount += res[a]['count']
        # generate totals
        finalpage += '\n|-\n! !! Total: !! %i !!' % artcount

        finalpage += '\n|}'

        finalpage += '\n\nTotal number of articles: ' + str(artcount)
        finalpage += "\n\n'''NOTE:''' page counts only newly created articles"
        finalpage += footer

        if self.opt.testwomenauthors:
            pywikibot.output(finalpage)

        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        if self.opt.testwomenauthors:
            pywikibot.output('WomenAuthorsPage:%s' % outpage.title())
        outpage.text = finalpage
        outpage.save(summary=self.opt.summary)
        return

    def generateResultHrightsPage(self, res, pagename, header, footer):
        """
        Generates results page from res
        Starting with header, ending with footer
        Output page is pagename
        """
        locpagename = re.sub(r'.*:', '', pagename)

        finalpage = header
        itemcount = 0
        artcount = 0
        finalpage += '\n== Articles about Human Rights ==\n'

        finalpage += '\n{| class="wikitable sortable" style="text-align: center;"'
        finalpage += '\n!#'
        finalpage += '\n!Wikipedia'
        finalpage += '\n!Articles'

        # ath = sorted(self.authors, reverse=True)
        ath = sorted(res, key=res.__getitem__, reverse=True)
        for a in ath:
            itemcount += 1
            finalpage += '\n|-\n| %i. || %s || %i' % (itemcount, a, res[a])
            artcount += res[a]
        # generate totals
        finalpage += '\n|-\n! !! Total: !! %i' % artcount

        finalpage += '\n|}'

        finalpage += '\n\nTotal number of articles: ' + str(artcount)

        finalpage += "\n\n'''NOTE:''' page counts all articles - new and updated"

        finalpage += footer

        # pywikibot.output(finalpage)

        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        if self.opt.test:
            pywikibot.output('HrightsPage:%s' % outpage.title())
        outpage.text = finalpage
        outpage.save(summary=self.opt.summary)
        return

    def generateResultHrightsAuthorsTable(self, res, pagename, header, footer):
        """
        Generates results page from res
        Starting with header, ending with footer
        Output page is pagename
        """
        locpagename = re.sub(r'.*:', '', pagename)

        if self.opt.testwomenauthors:
            pywikibot.output(res)

        finalpage = header
        itemcount = 0
        artcount = 0
        finalpage += '\n== Articles about Human Rights authors ==\n'

        finalpage += '\n{| class="wikitable sortable" style="text-align: center;"'
        finalpage += '\n!#'
        finalpage += '\n!Author'
        finalpage += '\n!Count'
        finalpage += '\n!Articles'

        # ath = sorted(self.authors, reverse=True)
        ath = sorted(res, key=lambda x: (res[x]['count']), reverse=True)
        # ath = sorted(res, key=res.__getitem__, reverse=True)
        for a in ath:
            if not a or 'UNKNOWN USER' in a or a == '':
                author = "'''unknown'''"
            else:
                author = a
            itemcount += 1
            finalpage += '\n|-\n| %i. || %s || %s || %s' % (
                itemcount, author, res[a]['count'], '[[:' + ']], [[:'.join(res[a]['list']) + ']]')
            artcount += res[a]['count']
        # generate totals
        finalpage += '\n|-\n! !! Total: !! %i !!' % artcount

        finalpage += '\n|}'

        finalpage += '\n\nTotal number of articles: ' + str(artcount)
        finalpage += "\n\n'''NOTE:''' page counts only newly created articles"
        finalpage += footer

        if self.opt.testwomenauthors:
            pywikibot.output(finalpage)

        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        if self.opt.testwomenauthors:
            pywikibot.output('WomenAuthorsPage:%s' % outpage.title())
        outpage.text = finalpage
        outpage.save(summary=self.opt.summary)
        return

    def generateResultLengthPage(self, res, pagename, header, footer):
        """
        Generates results page from res
        Starting with header, ending with footer
        Output page is pagename
        """
        locpagename = re.sub(r'.*:', '', pagename)

        csvpage = '<pre>'
        finalpage = header
        itemcount = 0
        finalpage += '\n\nLength of new articles excluding disabled parts in text. Word count approximated.'
        finalpage += '\n== Article length ==\n'
        # ath = sorted(self.authors, reverse=True)
        if self.opt.testlength:
            pywikibot.output('LengthPage:%s' % res)
        # ath = sorted(res, key=res.__getitem__, reverse=True)
        ath = sorted(res, key=lambda x: (res[x]['char']), reverse=True)

        finalpage += '\n{| class="wikitable sortable"'
        finalpage += '\n!#'
        finalpage += '\n!Article'
        finalpage += '\n!Character count'
        finalpage += '\n!Word count'

        for a in ath:
            itemcount += 1
            ccount = res[a]['char']
            wcount = res[a]['word']
            finalpage += '\n|-\n| %i. || [[:%s]] || %i || %i' % (itemcount, a, ccount, wcount)
            csvpage += '\n[[:%s]];%i;%i' % (a, ccount, wcount)
            if self.opt.testlength:
                pywikibot.output('\n|-\n| %i. || [[:%s]] || %i || %i' % (itemcount, a, ccount, wcount))

        finalpage += '\n|}'

        finalpage += '\n\nTotal number of articles: ' + str(itemcount)
        finalpage += footer
        csvpage += '\n</pre>'

        # pywikibot.output(finalpage)

        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        if self.opt.test:
            pywikibot.output('LengthPage:%s' % outpage.title())
        outpage.text = finalpage
        outpage.save(summary=self.opt.summary)

        # save csv version
        outpage = pywikibot.Page(pywikibot.Site(), pagename + '/csv')
        pywikibot.output('CSVLengthPage:%s' % pagename + '/csv')
        # pywikibot.output(csvpage)
        outpage.text = csvpage
        outpage.save(summary=self.opt.summary)

        return

    def generateResultLengthAuthorsPage(self, res, pagename, header, footer):
        """
        Generates results page from res
        Starting with header, ending with footer
        Output page is pagename
        """
        locpagename = re.sub(r'.*:', '', pagename)

        pagecounter = {}
        for p in res.keys():
            auth = res[p]['creator']
            if res[p]['char'] < 2000:
                continue
            if not auth in pagecounter.keys():
                pagecounter[auth] = {'count': 0, 'articles': []}
            pagecounter[auth]['count'] += 1
            pagecounter[auth]['articles'].append(p)

        finalpage = header
        itemcount = 0
        finalpage += '\n\nList of authors of articles longer than 2kB - excluding disabled parts in text.'
        finalpage += '\n== Article count per author ==\n'
        # ath = sorted(self.authors, reverse=True)
        # ath = sorted(pagecounter, key=pagecounter.__getitem__, reverse=True)
        ath = sorted(pagecounter, key=lambda x: (pagecounter[x]['count']), reverse=True)
        if self.opt.testlength:
            pywikibot.output('LengthPage:%s' % ath)

        finalpage += '\n{| class="wikitable sortable" style="text-align: center;"'
        finalpage += '\n!#'
        finalpage += '\n!Author'
        finalpage += '\n!Article count'
        finalpage += '\n!Article list'

        for a in ath:
            itemcount += 1
            ccount = pagecounter[a]['count']
            if len(pagecounter[a]['articles']):
                alist = '[[:' + ']], [[:'.join(pagecounter[a]['articles']) + ']]'
            else:
                alist = ''
            finalpage += '\n|-\n| %i. || [[user:%s|%s]] || %i || %s' % (itemcount, a, a, ccount, alist)
            if self.opt.testlength:
                pywikibot.output('\n|-\n| %i. || [[:%s]] || %i || %s' % (itemcount, a, ccount, alist))

        finalpage += '\n|}'

        finalpage += footer

        # pywikibot.output(finalpage)

        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        if self.opt.test:
            pywikibot.output('AuthorsLengthPage:%s' % outpage.title())
        outpage.text = finalpage
        outpage.save(summary=self.opt.summary)

        return

    def generateResultAuthorsPage(self, res, pagename, header, footer):
        """
        Generates results page from res
        Starting with header, ending with footer
        Output page is pagename
        """
        locpagename = re.sub(r'.*:', '', pagename)

        finalpage = header
        itemcount = 0
        anon = 0
        women = 0
        newbies = 0
        finalpage += '\n== Authors ==\n'
        finalpage += '\n{| class="wikitable sortable" style="text-align: center;"'
        finalpage += '\n!#'
        finalpage += '\n!User'
        finalpage += '\n!Articles'
        finalpage += '\n!New user'
        finalpage += '\n!Female'

        # ath = sorted(self.authors, reverse=True)
        ath = sorted(res, key=res.__getitem__, reverse=True)
        if self.opt.test3:
            pywikibot.output('generateResultAuthorsPage:%s' % ath)
        for a in ath:
            if not a:
                break
            itemcount += 1
            if 'UNKNOWN USER' in a or a == '':
                finalpage += '\n|-\n| %i. || %s || %i || ' % (itemcount, a, res[a])
            else:
                finalpage += '\n|-\n| %i. || [[user:%s|%s]] || %i || ' % (itemcount, a, a, res[a])
            if self.authorsData[a]['newbie']:
                newbies += 1
                finalpage += '[[File:Noto Emoji Oreo 1f476 1f3fb.svg|25px]] || '
            else:
                finalpage += '|| '
            if self.authorsData[a]['gender'] == 'female':
                women += 1
                finalpage += '[[File:Noto Emoji Oreo 2640.svg|25px]]'

            if self.authorsData[a]['anon']:
                anon += 1

        finalpage += '\n|-\n! !! Total: !! !! %i !! %i' % (newbies, women)
        finalpage += '\n|}'

        finalpage += '\n\n== Statistics =='
        finalpage += '\n* Number of authors: ' + str(itemcount)
        finalpage += '\n* Number of not registered authors: ' + str(anon)
        finalpage += '\n* Number of female  authors: ' + str(women)
        finalpage += '\n* Number of new authors: ' + str(newbies)

        finalpage += footer

        # pywikibot.output(finalpage)

        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        if self.opt.test:
            pywikibot.output('AuthorsPage:%s' % outpage.title())
        outpage.text = finalpage
        outpage.save(summary=self.opt.summary)
        return

    def generateResultArticleList(self, res, pagename, header, footer):
        """
        Generates results page from res
        Starting with header, ending with footer
        Output page is pagename
        """
        locpagename = re.sub(r'.*:', '', pagename)

        finalpage = header
        # @@@@@
        itemcount = 0
        newartscount = 0
        updartscount = 0
        # go by language
        for l in res.keys():
            artCount = 0
            newarts = 0
            updarts = 0

            # print('[[:' + i + ':' + self.templatesList[i] +'|' + i + ' wikipedia]]')
            """
            if l in self.templatesList.keys():
                finalpage += '\n== [[:' + l + ':' + self.templatesList[l][0] + '|' + l + '.wikipedia]] =='
            else:
                finalpage += '\n== ' + l + '.wikipedia =='
            """
            finalpage += '\n== ' + l + ' =='
            finalpage += '\n=== ' + l + ' new articles ==='
            finalpage += '\n{| class="wikitable"'
            finalpage += '\n!#'
            finalpage += '\n!Article'
            finalpage += '\n!User'
            finalpage += '\n!Date'
            finalpage += '\n!About'
            updatedArticles = '\n\n=== ' + l + ' updated articles ==='
            updatedArticles += '\n{| class="wikitable"'
            updatedArticles += '\n!#'
            updatedArticles += '\n!Article'
            updatedArticles += '\n!User'
            updatedArticles += '\n!About'
            for i in res[l]:
                if self.opt.test3:
                    pywikibot.output('Generating line from: %s:' % i)
                itemcount += 1
                artCount += 1
                if i['newarticle']:
                    newarts += 1
                    newartscount += 1
                    fam = i['family']
                    artLine = '\n|-\n| %i. || [[:%s:%s]] || %s || %s || ' % (
                        newarts, (fam + ':' if fam != 'wikipedia' else '') + i['lang'], i['title'], i['creator'],
                        i['creationDate'])
                    cList = []
                    for a in i['template']['country']:
                        if a in countryList:
                            cList.append(a)
                        else:
                            cList.append("'''" + a + "'''")
                    finalpage += artLine + ', '.join(cList)
                    if self.opt.test3:
                        pywikibot.output(artLine + ' (NEW)')
                else:
                    # finalpage += " '''(updated)'''"
                    updarts += 1
                    updartscount += 1
                    if i['template']['user']:
                        artLine = '\n|-\n| %i. || [[:%s:%s]] || %s || ' % (
                            updarts, i['lang'], i['title'], i['template']['user'])
                    elif i['creator']:
                        artLine = '\n|-\n| %i. || [[:%s:%s]] || %s || ' % (
                            updarts, i['lang'], i['title'], i['creator'])
                    else:
                        artLine = '\n|-\n| %i. || [[:%s:%s]] || %s || ' % (
                            updarts, i['lang'], i['title'], "'''unknown'''")

                    uList = []
                    for a in i['template']['country']:

                        if a in countryList:
                            uList.append(a)
                        else:
                            uList.append("'''" + a + "'''")
                    updatedArticles += artLine + ', '.join(uList)
                    if self.opt.test3:
                        pywikibot.output(artLine + " '''(updated)'''")

            finalpage += '\n|}'
            finalpage += updatedArticles + '\n|}'
            finalpage += '\nTotal number of articles ' + l + '.wikipedia:' + str(artCount)

        finalpage += '\n\n== Statistics =='
        finalpage += '\n\nNumber of new articles: ' + str(newartscount)
        finalpage += '\n\nNumber of updated articles: ' + str(updartscount)
        finalpage += "\n\n'''Total number of articles: " + str(itemcount) + "'''"
        finalpage += footer

        if self.opt.test2:
            pywikibot.output(finalpage)

        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        if self.opt.test:
            pywikibot.output('ArticlesPage:%s' % outpage.title())
        outpage.text = finalpage
        outpage.save(summary=self.opt.summary)
        return

    def generateResultAuthorsPageDE(self, res, pagename, header, footer):
        """
        Generates results page from res
        Starting with header, ending with footer
        Output page is pagename
        """
        locpagename = re.sub(r'.*:', '', pagename)

        finalpage = header + 'Aktualisiert: ~~~~~\n\n'
        itemcount = 0
        finalpage += '\n\nListe der Teilnehmer mit Artikel länger als 2kB (2000B).'

        # ath = sorted(self.authors, reverse=True)
        # ath = sorted(pagecounter, key=pagecounter.__getitem__, reverse=True)
        ath = sorted(res, key=lambda x: (res[x]['total']), reverse=True)
        if self.opt.testde:
            pywikibot.output('AuthorsDE page:%s' % ath)

        finalpage += '<!-- Results table -->'
        finalpage += '\n{| class="wikitable sortable" style="text-align: center;"'
        finalpage += '\n!#'
        finalpage += '\n!Teilnehmer(in)'
        finalpage += '\n!Neue bzw. veränderte Artikel'
        # finalpage += '\n!Neue Artikel'
        finalpage += '\n!Anzahl Punkte'

        for a in ath:
            itemcount += 1
            alist = []
            for art in res[a]['articles']:
                alist.append('[[%s]] (%i)' % (art['title'], art['points']))
            finalpage += '\n|-\n| %i || [[Benutzer:%s|%s]] || %s || %i' % (
            itemcount, a, a, ', '.join(alist), res[a]['total'])

        finalpage += '\n|}'

        # finalpage += '\n\nNotiz: veränderte Artikel sind im Moment nicht berücksichtigt.'
        finalpage += footer

        # pywikibot.output(finalpage)

        desite = pywikibot.Site('de')
        outpage = pywikibot.Page(desite, pagename)
        if self.opt.testde:
            pywikibot.output('AuthorsLengthPage:%s' % outpage.title())
            pywikibot.output(finalpage)
        outpage.text = finalpage
        outpage.save(summary=self.opt.summary)

        return

    def templateWithNamedParams(self):
        """
        Iterate template as returned by templatesWithNames()

        @return: a generator that yields a tuple for each param of a template
            type: named, int
            name: name of param
            value: value of param
        @rtype: generator
        """

    def templateArg(self, param):
        """
        return name,value for each template param

        input text in form "name = value"
        @return: a tuple for each param of a template
            named: named (True) or int
            name: name of param or None if numbered
            value: value of param
        @rtype: tuple
        """

        paramR = re.compile(r'(?P<name>.*)=(?P<value>.*)')
        if '=' in param:
            match = paramR.search(param)
            named = True
            name = match.group("name").strip()
            value = match.group("value").strip()
        else:
            named = False
            name = None
            value = param
        # test
        if self.opt.testtemplatearg:
            pywikibot.output('name:%s:value:%s' % (name, value))
        return (named, name, value)


def main(*args: Tuple[str, ...]) -> None:
    """
    Process command line arguments and invoke bot.

    If args is an empty list, sys.argv is used.

    @param args: command line arguments
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
