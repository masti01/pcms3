"""
Class to present results on multiple pages
"""
#
# (C) masti, 2022
#
# Distributed under the terms of the MIT license.
#
import pywikibot


class Results:

    def __init__(self, results, basepage, header1, header2, footer1, footer2, summary, lpp=1000):
        self.results = results or []
        self.header1 = header1 or ''  # header for all pages
        self.header2 = header2 or ''  # header for all pages
        self.footer1 = footer1 or ''  # footer for all pages
        self.footer2 = footer2 or ''  # footer for all pages
        self.bpname = basepage.title()  # text version of base Page
        self.lpp = lpp  # lines per page
        self.pagenum = 0  # current page number
        self.summary = summary
        self.currPage = None

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    @property
    def pages(self):
        """
        calculate number of required pages: lpp - lines per page

        @rtype: int
        """
        return (len(self.results) // self.lpp) + 1 if (len(self.results) % self.lpp) else len(self.results) // self.lpp

    def add(self, result: str) -> None:
        """
        add result to list
        @rtype: None
        @param result: str
        @return:
        """
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
        return "{} {}".format(self.bpname, pagenum)

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
        self.currPage += self._pageend(pagenum)  # add footers
        self._savepage(self.currPage, self._currentpage(pagenum), self.summary)  # save page

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