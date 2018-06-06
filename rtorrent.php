class rTorrent
{
	const RTORRENT_PACKET_LIMIT = 1572864;
	static public function sendTorrent($fname, $isStart, $isAddPath, $directory, $label, $saveTorrent, $isFast, $isNew = true, $addition = null)
	{
		$hash = false;
		$torrent = is_object($fname) ? $fname : new Torrent($fname);
#   exec("python /home/user/scripts/diskcheck.py");
		if(!$torrent->errors())
		{
			if($isFast && ($resume = self::fastResume($torrent, $directory, $isAddPath)))
				$torrent = $resume;
			else
				if($isNew)
				{
					if(isset($torrent->{'libtorrent_resume'}))
						unset($torrent->{'libtorrent_resume'});
				}			
			if($isNew)
