sub _sendRtorrent {
        my $self = shift;
        my @script = split $/, `python /home/user/scripts/check.py '$self->{ti}{torrentName}' '$self->{uploadMethod}{rtLabel}' '$self->{ti}{torrentSizeInBytes}'`;

        if ($script[0] eq "exit") {
                return;
        }

	eval {
		my $rtAddress = _getRtAddress();
		if ($rtAddress eq "") {
			$self->_messageFail(0, "Can't send torrent file to rtorrent. You have not initialized rt-address (SCGI address).");
			return;
		}

		my $filename = $self->_writeTempFile($self->{torrentFileData});
		my $macroReplacer = $self->_getMacroReplacer($filename);
		my $rtDir = getAbsPath($self->{uploadMethod}{rtDir});
		my $rtCommands = $macroReplacer->replace($self->{uploadMethod}{rtCommands});
		my $rtLabel = toUrlEncode($macroReplacer->replace($self->{uploadMethod}{rtLabel}));
		my $rtRatioGroup = $self->{uploadMethod}{rtRatioGroup};
		my $rtChannel = $self->{uploadMethod}{rtChannel};
		my $rtPriority = $self->{uploadMethod}{rtPriority};
		my $rtIgnoreScheduler = $self->{uploadMethod}{rtIgnoreScheduler};

		my @dirs = File::Spec->splitdir($rtDir);
		for my $name (@dirs) {
			$name = convertToValidPathName($macroReplacer->replace($name));
		}
		$rtDir = File::Spec->catdir(@dirs);
		dmessage 5, "Dest dir: '$rtDir'";

		my $rt = new AutodlIrssi::RtorrentCommands();
		if ($rtDir ne "") {
			if ($self->{uploadMethod}{rtDontAddName}) {
				$rt->func('d.directory_base.set', $rtDir);
			}
			else {
				$rt->func('d.directory.set', $rtDir);
			}
		}
		$rt->func('d.custom1.set', $rtLabel) if $rtLabel ne "";
		$rt->func('d.views.push_back_unique', $rtRatioGroup)->func('view.set_visible', $rtRatioGroup) if $rtRatioGroup ne "";
		$rt->func('d.throttle_name.set', $rtChannel) if $rtChannel ne "";
		$rt->func('d.priority.set', $rtPriority) if $rtPriority ne "";
		$rt->func('d.throttle_name.set', 'NULL')->func('d.custom.set', 'sch_ignore', '1') if $rtIgnoreScheduler;
		$rt->func('d.tied_to_file.set');
		my $cmds = $rt->get();
		$cmds .= ";$rtCommands" if $rtCommands ne "";
		dmessage 5, "rtorrent commands: '$cmds'";

		# Make sure destination base dir exists
		createDirectories($rtDir) if $rtDir ne "";

		# Set REMOTE_ADDR since there could be user commands
		my $scgi = new AutodlIrssi::Scgi($rtAddress, {REMOTE_ADDR => "127.0.0.1"});
		my $xmlrpc = new AutodlIrssi::XmlRpcSimpleCall($scgi);
		$xmlrpc->method($rtPriority eq '0' ? 'load.normal' : 'load.start');
		$xmlrpc->string($filename);
		$xmlrpc->string($cmds) if $cmds ne "";
		$xmlrpc->methodEnd();
		$xmlrpc->send(sub { $self->_onRtorrentUploadComplete(@_) });
	};
	if ($@) {
		$self->_messageFail(0, "Could not send rtorrent commands, torrent '$self->{ti}{torrentName}', error: " . formatException($@));
	}
}
