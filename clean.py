#!/usr/bin/env python3

import os
from datetime import datetime

DAY_LIMIT = 90
DEBUG = True

def clean_folder(path):
	if not os.path.isdir(path):
		print("can't find dir "+str(path))
		return False

	# get files list
	f_tab = []
	for (dirpath, dirnames, filenames) in os.walk(path):
	    f_tab.extend(filenames)
	    break

	nb_free_space = 0
	# for each file
	for elem in f_tab:
		# call clean_file(file_path)
		res = clean_file(path+"/"+elem)
		if res:
			nb_free_space+=res[6]

	if DEBUG:
		print("Nb of free spaces : "+str(int((nb_free_space/1000)*100)/100)+" ko\n\n")

def clean_file(path):

	# get data

	if DEBUG:
		print("[Test] "+path)

	(mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(path)

	dt_now = datetime.now()
	dt_ctime = datetime.fromtimestamp(ctime)

	t_now = datetime.timestamp(dt_now)
	t_day_limit = DAY_LIMIT*24*60*60

	res_t_dif = t_now - ctime

	if DEBUG:
		print("\t- created : "+str(int((res_t_dif/24/60/60)*100)/100)+" days ago")
		print("\t- expired ? "+str(res_t_dif>t_day_limit))

	# if now - create time > 90
	if res_t_dif>t_day_limit:
		# delete the file
		if DEBUG:
			print("[Deleting] "+path+"\n---\n")
		os.remove(path)

		# return file data
		return mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime
	else:
		return False

# clean archive
clean_folder("./reports")

# clean new mail
clean_folder("./mails/INBOX/new")

# clean mail
clean_folder("./mails/INBOX/cur")
