import sys, os, subprocess, shutil, PTN, cStringIO as StringIO
import xmlrpclib, urllib, urlparse, socket, re
from urlparse import uses_netloc
from math import expm1
from imdbpie import Imdb

uses_netloc.append('scgi')

minimum_rating = 6

host = "scgi://127.0.0.1:5000"
directory = "/home/user/rtorrent/downloads"
torrent_directory = "/home/user/rtorrent/.session"
disk = os.statvfs("/")

def erase(hash):
        xmlreq = xmlrpclib.dumps(tuple([hash]), "d.erase")
        xmlresp = SCGIRequest(host).send(xmlreq)
        return xmlrpclib.loads(xmlresp)[0][0]

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


imdb = Imdb()
torrent_info = PTN.parse(sys.argv[1])
country = imdb.get_title_versions(imdb.search_for_title(str(torrent_info['title']) + " " + str(torrent_info['year']))[0]['imdb_id'])['origins']
rating = imdb.get_title_ratings(imdb.search_for_title(str(torrent_info['title']) + " " + str(torrent_info['year']))[0]['imdb_id'])['rating']

if str(country) != "[u'US']" or rating < minimum_rating:
        print "exit"
        quit()

torrent_size = round(int(sys.argv[2]) / (1024 * 1024 * 1024.0), 2)
available_space = round(float(disk.f_bsize * disk.f_bavail) / 1024 / 1024 / 1024, 2)
required_space = torrent_size + 5

while available_space < required_space:
        os.chdir(directory)
        files = sorted(os.listdir(os.getcwd()), key=os.path.getmtime)
        oldest_file = files[0]
        full_path = os.path.join(directory, oldest_file)

        if os.path.isdir(full_path):
                filesize = sum(os.path.getsize(os.path.join(dirpath, filename)) for dirpath, dirnames, filenames in os.walk(full_path) for filename in filenames)
                filesize = round(filesize * expm1(1e-9), 2)
                shutil.rmtree(full_path)
        else:
                filesize = os.path.getsize(full_path)
                filesize = round(filesize * expm1(1e-9), 2)
                os.remove(full_path)

        torrents = []
        files = os.listdir(torrent_directory)

	for file in files:
                if file.endswith(".torrent"):
                        torrents.append(os.path.join(torrent_directory, file))

        for torrent in torrents:
                match = subprocess.call(['/bin/grep', oldest_file, torrent])
                if match == 0:
                        hash = os.path.splitext(os.path.basename(torrent))[0]
                        erase(hash)
                        available_space = available_space + filesize

print "success"
