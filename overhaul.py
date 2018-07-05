import sys, os, shutil, cStringIO as StringIO
import xmlrpclib, urllib, urlparse, socket, re
from urlparse import uses_netloc
from datetime import datetime

try:
        import PTN
        from imdbpie import Imdb
except:
        pass

yes = 'yes'
no = 'no'

uses_netloc.append('scgi')

enable_disk_check = yes

host = 'scgi://127.0.0.1:5000'
disk = os.statvfs('/')

# General Rules

# Filesize in Gigabytes
minimum_filesize = 5
# Age in Days
minimum_age = 7
minimum_ratio = 1.2

# Fallback Age - Only the age of a torrent must be higher or equal to this number to be deleted - no to disable
fallback_age = no

# Fallback Ratio - Only the ratio of a torrent must be higher or equal to this number to be deleted - no to disable
fallback_ratio = 1.4

# End of General Rules

# Tracker Rules will override General Rules - Fill to enable
# Value Order - 1. Minimum Filesize (GB) 2. Minimum Age 3. Minimum Ratio 4. Fallback Age 5. Fallback Ratio
trackers = {}

# Example
#trackers = {
#                   "redacted.ch" : [1, 7, 1.2, no, no],
#                   "hd-torrents.org" : [3, 5, 1.3, 9, 1.3],
#                   "privatehd.to" : [5, 6, 1.2, 12, no],
#                   "apollo.rip" : [2, 5, 1.4, no, 1.8],
#           }

# Only delete torrents from trackers that have a tracker rule (yes/no)
trackers_only = yes

# Only delete torrents that have labels in this list - Fill to enable
labels_disk = []

# Example
# labels_disk = ['TV', 'Movies', 'Crap']



# IMDB Criteria - Fill to enable
# Value Order - 1. Minimum IMDB Rating 2. Minimum Votes 3. Skip Foreign Movies (yes/no)
labels_imdb = {}

# Example
#labels_imdb = {
#                     "Hollywood Blockbusters" : [7, 80000, yes],
#                     "Bollywood Classics" : [8, 60000, no],
#              }


class SCGIRequest(object):

	def __init__(self, url):
		self.url = url
		self.resp_headers = []

	def __send(self, scgireq):
		scheme, netloc, path, query, frag = urlparse.urlsplit(self.url)
		host, port = urllib.splitport(netloc)

		if netloc:
                        inet6_host = ''

                        if len(inet6_host) > 0:
			        addrinfo = socket.getaddrinfo(inet6_host, port, socket.AF_INET6, socket.SOCK_STREAM)
                        else:
			        addrinfo = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)

			assert len(addrinfo) == 1, "There's more than one? %r" % addrinfo

			sock = socket.socket(*addrinfo[0][:3])
			sock.connect(addrinfo[0][4])
		else:
			sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
			sock.connect(path)

		sock.send(scgireq)
		recvdata = resp = sock.recv(1024)

		while recvdata != '':
			recvdata = sock.recv(1024)
			resp += recvdata
		sock.close()
		return resp

	def send(self, data):
		"Send data over scgi to url and get response"
		scgiresp = self.__send(self.add_required_scgi_headers(data))
		resp, self.resp_headers = self.get_scgi_resp(scgiresp)
		return resp

	@staticmethod
	def encode_netstring(string):
		"Encode string as netstring"
		return '%d:%s,'%(len(string), string)

        @staticmethod
	def make_headers(headers):
		"Make scgi header list"
		return '\x00'.join(['%s\x00%s'%t for t in headers])+'\x00'

	@staticmethod
	def add_required_scgi_headers(data, headers = []):
		"Wrap data in an scgi request,\nsee spec at: http://python.ca/scgi/protocol.txt"
		headers = SCGIRequest.make_headers([('CONTENT_LENGTH', str(len(data))),('SCGI', '1'),] + headers)
		enc_headers = SCGIRequest.encode_netstring(headers)
		return enc_headers+data

	@staticmethod
	def gen_headers(file):
		"Get header lines from scgi response"
		line = file.readline().rstrip()

		while line.strip():
			yield line
			line = file.readline().rstrip()

	@staticmethod
	def get_scgi_resp(resp):
		"Get xmlrpc response from scgi response"
		fresp = StringIO.StringIO(resp)
		headers = []

		for line in SCGIRequest.gen_headers(fresp):
			headers.append(line.split(': ', 1))

		xmlresp = fresp.read()
		return (xmlresp, headers)


def imdb(torrent_name, minimum_rating, minimum_votes, skip_foreign):
        imdb = Imdb()
        torrent_info = PTN.parse(torrent_name)

        try:
                search = imdb.get_title_ratings(imdb.search_for_title(str(torrent_info['title']) + ' ' + str(torrent_info['year']))[0]['imdb_id'])
                rating = search['rating']
                votes = search['ratingCount']
        except:
                return
        else:
                if rating < minimum_rating or votes < minimum_votes:
                        print 'exit'
                        quit()

        if skip_foreign == 'yes':
                country = imdb.get_title_versions(imdb.search_for_title(str(torrent_info['title']) + ' ' + str(torrent_info['year']))[0]['imdb_id'])['origins']

                if 'US' not in country:
                        print 'exit'
                        quit()


def xmlrpc(methodname, hash):
        xmlreq = xmlrpclib.dumps(hash, methodname)
        xmlresp = SCGIRequest(host).send(xmlreq)
        return xmlrpclib.loads(xmlresp)[0][0]

torrent_name = str(sys.argv[1])
torrent_label = str(sys.argv[2])
torrent_size = int(sys.argv[3])

if torrent_label in labels_imdb:
        minimum_rating = labels_imdb[torrent_label][0]
        minimum_votes = labels_imdb[torrent_label][1]
        skip_foreign = labels_imdb[torrent_label][2]
        imdb(torrent_name, minimum_rating, minimum_votes, skip_foreign)

if enable_disk_check == 'yes':
        torrent_size = round(torrent_size / (1024 * 1024 * 1024.0), 2)
        available_space = round(float(disk.f_bsize * disk.f_bavail) / 1024 / 1024 / 1024, 2)
        required_space = torrent_size + 5
        torrents = {}
        fallback_torrents = {}
        fallback = 'no'

        while available_space < required_space:

                if not torrents and fallback == 'no' and fallback_torrents:
                        fallback = 'yes'

                if not torrents and fallback == 'no':
                        hashes = xmlrpc('download_list', tuple([]))

                        for hash in hashes:
                                date = datetime.utcfromtimestamp(xmlrpc('d.timestamp.finished', tuple([hash])))
                                tracker = xmlrpc('t.multicall', (hash, '', 't.url='))
                                filesize = round(xmlrpc('d.size_bytes', tuple([hash])) / (1024 * 1024 * 1024.0), 2)
                                ratio = xmlrpc('d.ratio', tuple([hash])) / 1000.0
                                label = urllib.unquote(xmlrpc('d.custom1', tuple([hash])))
                                base_path = xmlrpc('d.base_path', tuple([hash]))
                                torrents[date] = tracker, filesize, ratio, label, base_path, hash

                if fallback == 'no':
                        oldest_torrent = min(torrents)
                        age = (datetime.now() - oldest_torrent).days
                        tracker = torrents[oldest_torrent][0]
                        filesize = torrents[oldest_torrent][1]
                        ratio = torrents[oldest_torrent][2]
                        label = torrents[oldest_torrent][3]
                        base_path = torrents[oldest_torrent][4]
                        hash = torrents[oldest_torrent][5]

                        if trackers:
                                rule = [rule for rule in trackers for url in tracker if rule in url[0]]

                                if rule:
                                        rule = rule[0]
                                        minimum_filesize = trackers[rule][0]
                                        minimum_age = trackers[rule][1]
                                        minimum_ratio = trackers[rule][2]
                                        fallback_age = trackers[rule][3]
                                        fallback_ratio = trackers[rule][4]

                                if not rule and trackers_only == 'yes':
                                        del torrents[oldest_torrent]

                                        if not torrents and not fallback_torrents:
                                                break

                                        continue

                        if age < minimum_age or filesize < minimum_filesize or ratio < minimum_ratio or (labels_disk and label not in labels_disk):

                                if (isinstance(fallback_age, (int, float)) and filesize >= minimum_filesize and age >= fallback_age) and (labels_disk and label in labels_disk or not labels_disk):
                                        fallback_torrents[oldest_torrent] = base_path, hash, filesize
                                elif (isinstance(fallback_ratio, (int, float)) and filesize >= minimum_filesize and ratio >= fallback_ratio) and (labels_disk and label in labels_disk or not labels_disk):
                                        fallback_torrents[oldest_torrent] = base_path, hash, filesize

                                del torrents[oldest_torrent]

                                if not torrents:

                                        if fallback_torrents:
                                                continue

                                        break

                                continue
                else:
                        oldest_torrent = min(fallback_torrents)
                        base_path = fallback_torrents[oldest_torrent][0]
                        hash = fallback_torrents[oldest_torrent][1]
                        filesize = fallback_torrents[oldest_torrent][2]

                if os.path.isdir(base_path):
                        shutil.rmtree(base_path)
                else:
                        os.remove(base_path)

                xmlrpc('d.erase', tuple([hash]))

                if fallback == 'no':
                        del torrents[oldest_torrent]
                else:
                        del fallback_torrents[oldest_torrent]

                available_space = available_space + filesize

                if not torrents and not fallback_torrents:
                        break

print 'finish'
