if enable_disk_check == 'yes':
        torrent_size = round(torrent_size / (1024 * 1024 * 1024.0), 2)
        available_space = round(float(disk.f_bsize * disk.f_bavail) / 1024 / 1024 / 1024, 2)
        required_space = torrent_size + 5
        torrents = {}
		fallback_list = {}
        fallback = no

        while available_space < required_space:

                if not torrents and fallback == 'no':
                        hashes = xmlrpc('download_list', tuple([]))

                        for hash in hashes:
                                date = datetime.utcfromtimestamp(xmlrpc('d.creation_date', tuple([hash])))
                                filesize = round(xmlrpc('d.size_bytes', tuple([hash])) / (1024 * 1024 * 1024.0), 2)
                                ratio = xmlrpc('d.ratio', tuple([hash])) / 1000.0
                                label = urllib.unquote(xmlrpc('d.custom1', tuple([hash])))
                                base_path = xmlrpc('d.base_path', tuple([hash]))
                                torrents[date] = filesize, ratio, label, base_path, hash
								
				if fallback == 'no':
                        oldest_torrent = min(torrents)
                        age = (datetime.strptime(datetime.today().strftime('%m/%d/%Y'), '%m/%d/%Y') - datetime.strptime(oldest_torrent.strftime('%m/%d/%Y'), '%m/%d/%Y')).days
                        filesize = torrents[oldest_torrent][0]
                        ratio = torrents[oldest_torrent][1]
                        label = torrents[oldest_torrent][2]
                        base_path = torrents[oldest_torrent][3]
                        hash = torrents[oldest_torrent][4]

				else:
				        oldest_torrent = min(fallback_list)
						filesize = fallback_list[oldest_torrent][0]
						base_path = fallback_list[oldest_torrent][1]
                        hash = fallback_list[oldest_torrent][2]

				if fallback == 'no':
                        if age < minimum_age or filesize < minimum_filesize or ratio < minimum_ratio or (enable_labels_disk == 'yes' and label not in labels_disk):

                                if (enable_fallback = yes) and (enable_labels_disk == 'yes' and label in labels_disk) and age > minimum_age or filesize > minimum_filesize:
								        fallback_list[age] = filesize, base_path, hash

                                del torrents[oldest_torrent]

                                if not torrents:
						        
								        if enable_fallback = yes and if fallback_list:
								                fallback = 'yes'
										        continue

                                        break

                                continue

                if os.path.isdir(base_path):
                        shutil.rmtree(base_path)
                else:
                        os.remove(base_path)

                xmlrpc('d.erase', tuple([hash]))
                del torrents[oldest_torrent]
                available_space = available_space + filesize

                if not torrents and if not fallback_list:
                        break

print 'finish'
