import sys, os, shutil, PTN, cStringIO as StringIO
import xmlrpclib, urllib, urlparse, socket, re
from urlparse import uses_netloc
from datetime import datetime
from imdbpie import Imdb

uses_netloc.append('scgi')

enable_disk_check = 'yes'
enable_labels_disk = 'yes'

host = 'scgi://127.0.0.1:5000'
disk = os.statvfs('/')

minimum_filesize = 5
minimum_ratio = 1.2
labels_disk = ['TV', 'Movies']

labels_imdb = {
		     "Hollywood Blockbusters" : [7, 'yes'],
                     "Bollywood Classics" : [8, 'no'],
	      }

class SCGIRequest(object):

	def __init__(self, url):
		self.url=url
		self.resp_headers=[]

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
	def add_required_scgi_headers(data, headers=[]):
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


def imdb(torrent_name, minimum_rating, skip_foreign):
        imdb = Imdb()
        torrent_info = PTN.parse(torrent_name)

        try:
                rating = imdb.get_title_ratings(imdb.search_for_title(str(torrent_info['title']) + ' ' + str(torrent_info['year']))[0]['imdb_id'])['rating']
        except:
                return
        else:
                if rating < minimum_rating:
                        print 'exit'
                        quit()

        if skip_foreign == 'yes':

                try:
                        country = imdb.get_title_versions(imdb.search_for_title(str(torrent_info['title']) + ' ' + str(torrent_info['year']))[0]['imdb_id'])['origins']
                except:
                        return
                else:
                        if 'US' not in country:
                                print 'exit'
                                quit()


def xmlrpc(methodname, hash):
        xmlreq = xmlrpclib.dumps(hash, methodname)
        xmlresp = SCGIRequest(host).send(xmlreq)
        return xmlrpclib.loads(xmlresp)[0][0]

try:
        torrent_name = str(sys.argv[1])
        torrent_label = str(sys.argv[2])
        torrent_size = int(sys.argv[3])
except:
        torrent_size = int(sys.argv[1])
        torrent_name = None
        torrent_label = None

if torrent_label in labels_imdb:
        minimum_rating = labels_imdb[torrent_label][0]
        skip_foreign = labels_imdb[torrent_label][1]
        imdb(torrent_name, minimum_rating, skip_foreign)


if enable_disk_check == 'yes':

        torrent_size = round(torrent_size / (1024 * 1024 * 1024.0), 2)
        available_space = round(float(disk.f_bsize * disk.f_bavail) / 1024 / 1024 / 1024, 2)
        required_space = torrent_size + 5
        torrents = {}

        while available_space < required_space:

                if not torrents:
                        hashes = xmlrpc('download_list', tuple([]))

                        for hash in hashes:
                                date = datetime.utcfromtimestamp(xmlrpc('d.creation_date', tuple([hash]))).strftime('%Y/%m/%d')
                                filesize = round(xmlrpc('d.size_bytes', tuple([hash])) / (1024 * 1024 * 1024.0), 2)
                                base_path = xmlrpc('d.base_path', tuple([hash]))
                                ratio = xmlrpc('d.ratio', tuple([hash])) / 1000.0
                                label = urllib.unquote(xmlrpc('d.custom1', tuple([hash])))
                                torrents[date] = filesize, ratio, label, base_path, hash

                oldest_torrent = min(torrents)
                filesize = torrents[oldest_torrent][0]
                ratio = torrents[oldest_torrent][1]
                label = torrents[oldest_torrent][2]
                base_path = torrents[oldest_torrent][3]
                hash = torrents[oldest_torrent][4]

                if filesize < minimum_filesize or ratio < minimum_ratio or enable_labels_disk == 'yes' and label not in labels_disk:
                        del torrents[oldest_torrent]

                        if not torrents:
                                break

                        continue

                if os.path.isdir(base_path):
                        shutil.rmtree(base_path)
                else:
                        os.remove(base_path)

                xmlrpc('d.erase', tuple([hash]))
                del torrents[oldest_torrent]
                available_space = available_space + filesize

print 'finish'
