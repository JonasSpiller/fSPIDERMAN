# -*- coding: utf-8 -*-
from os.path import expanduser,join
home = expanduser("~")
param_file = join(home,'.fspidermanrc')

class RcParams(object):
	def __init__(self):
		self.dict = {}
		try:
			print('looking for fspidermanrc file at '+param_file)
			for line in open(param_file):
				key = line.split(':')[0].replace(' ','')
				cval = line.split(':')[1].replace(' ','').replace('\n','')
				self.dict[key] = cval
			RcParams.read = True
		except:
			RcParams.read = False
			print('no fspidermanrc file detected')
	def __getitem__(self, key):
	    return self.dict[key]
rcParams = RcParams()

from fspiderman.params import *
from fspiderman.web import *
from fspiderman.plot import *
from fspiderman.test import *
from fspiderman.stellar_grid import *
from fspiderman.read_model import *

__all__ = ["web","params","_web","plot","test","stellar_grid","read_model"]
