from app.lib.provider.yarr.base import nzbBase
from urllib import urlencode
from urllib2 import URLError
import logging
import time
import urllib2

log = logging.getLogger(__name__)

class nzbs(nzbBase):
    """Api for nzbs"""

    name = 'NZBs.org'
    downloadUrl = 'http://nzbs.org/index.php?action=getnzb&nzbid=%s%s'
    nfoUrl = 'http://nzbs.org/index.php?action=view&nzbid=%s&nfo=1'
    detailUrl = 'http://nzbs.org/index.php?action=view&nzbid=%s'
    apiUrl = 'http://nzbs.org/rss.php'

    catIds = {
        4: ['720p', '1080p'],
        2: ['cam', 'ts', 'dvdrip', 'tc', 'brrip', 'r5', 'scr'],
        9: ['dvdr']
    }
    catBackupId = 't2'

    def __init__(self, config):
        log.info('Using NZBs.org provider')

        self.config = config

    def conf(self, option):
        return self.config.get('NZBsorg', option)

    def enabled(self):
        return self.config.get('NZB', 'enabled') and self.conf('id') and self.conf('key')

    def find(self, movie, quality, type, retry = False):

        results = []
        if not self.enabled() or not self.isAvailable(self.apiUrl):
            return results

        arguments = urlencode({
            'action':'search',
            'q': self.toSearchString(movie.name + ' ' + quality),
            'catid':self.getCatId(type),
            'i':self.conf('id'),
            'h':self.conf('key'),
            'age': self.config.get('NZB', 'retention')
        })
        url = "%s?%s" % (self.apiUrl, arguments)

        log.info('Searching: %s', url)

        try:
            data = urllib2.urlopen(url, timeout = self.timeout)
        except (IOError, URLError):
            log.error('Failed to open %s.' % url)
            return results

        if data:
            log.debug('Parsing NZBs.org RSS.')
            try:
                try:
                    xml = self.getItems(data)
                except:
                    if retry == False:
                        log.error('No valid xml, to many requests? Try again in 15sec.')
                        time.sleep(15)
                        return self.find(movie, quality, type, retry = True)
                    else:
                        log.error('Failed again.. disable %s for 15min.' % self.name)
                        self.available = False
                        return results

                for nzb in xml:

                    id = int(self.gettextelement(nzb, "link").partition('nzbid=')[2])

                    size = self.gettextelement(nzb, "description").split('</a><br />')[1].split('">')[1]

                    new = self.feedItem()
                    new.id = id
                    new.type = 'nzb'
                    new.name = self.gettextelement(nzb, "title")
                    new.date = time.mktime(time.strptime(str(self.gettextelement(nzb, "pubDate")), '%a, %d %b %Y %H:%M:%S +0000'))
                    new.size = self.parseSize(size)
                    new.url = self.downloadLink(id)
                    new.detailUrl = self.detailLink(id)
                    new.content = self.gettextelement(nzb, "description")
                    new.score = self.calcScore(new, movie)

                    if self.isCorrectMovie(new, movie, type):
                        results.append(new)
                        log.info('Found: %s', new.name)

                return results
            except SyntaxError:
                log.error('Failed to parse XML response from NZBs.org')
                return False


    def getApiExt(self):
        return '&i=%s&h=%s' % (self.conf('id'), self.conf('key'))
