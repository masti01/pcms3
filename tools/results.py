"""
Class to present results on multiple pages
"""
#
# (C) masti, 2022
#
# Distributed under the terms of the MIT license.
#
import pywikibot
import re


class Results:

    def __init__(self, basepage, header1, header2, footer1, footer2, summary, lpp=1000):
        self.results = []
        self.header1 = header1 or ''  # header for all pages
        self.header2 = header2 or ''  # header for all pages
        self.footer1 = footer1 or ''  # footer for all pages
        self.footer2 = footer2 or ''  # footer for all pages
        self.bpname = basepage.title()  # text version of base Page
        self.lpp = lpp  # lines per page
        self.pagenum = 0  # current page number
        self.summary = summary
        self.currPage = None
        self.test = False  # set to true for test outputs

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    @property
    def pages(self):
        """
        calculate number of required pages: lpp - lines per page

        @rtype: int
        """
        if self.test:
            pywikibot.output("RES pages:{}".format((len(self.results) // self.lpp) + 1)
                             if (len(self.results) % self.lpp) else len(self.results) // self.lpp)
        return (len(self.results) // self.lpp) + 1 if (len(self.results) % self.lpp) else len(self.results) // self.lpp

    def add(self, result: str) -> None:
        """
        add result to list
        @rtype: None
        @param result: str
        @return:
        """
        if self.test:
            pywikibot.output("RESult added:{}".format(result))
        self.results.append(result)

    @staticmethod
    def _savepage(text, pagename, summary):
        # Save page
        # pywikibot.output(finalpage)
        outpage = pywikibot.Page(pywikibot.Site(), pagename)
        outpage.text = text
        outpage.save(summary=summary)

    def _previouspage(self, pagenum):
        return "{} {}".format(self.bpname, pagenum - 1) if pagenum > 1 else (self.bpname if pagenum else None)

    def _nextpage(self, pagenum):
        """
        return next page name
        """
        return "{} {}".format(self.bpname, pagenum + 1)

    def _currentpage(self, pagenum):
        return "{} {}".format(self.bpname, pagenum) if pagenum else self.bpname

    def navbar(self, pagenum):
        """
        generate navbar template for current page
        """
        opis = 'Strona {} z {}'.format(pagenum, self.pages)
        pp = self._previouspage(pagenum)
        np = self._nextpage(pagenum)
        return "{{{{Wikipedysta:MastiBot/Nawigacja|{}|{}|tekst={}|opis={}}}}}".format(pp, np, 'Nawiguj', opis)

    def _pagestart(self, pagenum):
        return "{}\n{}\n{}".format(self.header1, self.navbar(pagenum), self.header2)

    def _pageend(self, pagenum):
        return "{}\n{}\n{}".format(self.footer1, self.navbar(pagenum), self.footer2)

    def _initpage(self, pagenum):
        self.currPage = self._pagestart(pagenum)  # intialize page content

    def _closepage(self, pagenum):
        if self.test:
            pywikibot.output("Saving page #{}".format(pagenum))
        self.currPage += self._pageend(pagenum)  # add footers
        self.currPage = self._przypisy(self.currPage)
        self._savepage(self.currPage, self._currentpage(pagenum), self.summary)  # save page

    @staticmethod
    def _przypisy(text) -> str:
        """
        Searches text for references, adds {{Przypisy}} if found.
        """
        return '\n\n== Przypisy ==\n{{Przypisy}}' if re.search(r'(?i)<ref|{{([ru][ |])', text) else ''

    @property
    def testenable(self):
        self.test = True

    @property
    def testdisable(self):
        self.test = False

    def saveresults(self):
        pagenum = 0
        linenum = 0

        self._initpage(pagenum)
        for r in self.results:
            linenum += 1
            self.currPage += r
            if not linenum % self.lpp:
                self._closepage(pagenum)
                pagenum += 1
                self._initpage(pagenum)

        self._closepage(pagenum)
