directory="/home/user/rtorrent/downloads"

available_space=$(df /dev/sda3 --block-size=1G | awk 'END {print $4}')
required_space=95

while [ $available_space -lt $required_space ]; do

     oldest_file=$(ls "$directory" -1t | tail -1)
     filesize=$(du "$directory/$oldest_file" -sh --block-size=1G | awk '{print $1}')
     rm -rf "$directory/$oldest_file"
     available_space=$[available_space+filesize]

done
