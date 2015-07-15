"""High level scripts Module """
import os.path
from collections import defaultdict
import pmlab.cnet
import pmlab.bpmn
import pmlab.log.filters
import re
import os
import csv
#import projectors
#import filters
#import clustering
#import tempfile
#import subprocess
#import pmlab.ts
import numpy as np
import matplotlib.pyplot as plt

def plot_responsibles(log,activity,col_responsible):
	if not('.csv' in log.filename):
		raise ValueError, 'Log is not in .csv format'
	with open(log.filename, 'r') as f:
		reader = csv.reader(f)
		sum = 0
		resp = {}
		for row in reader:
			if re.search("#",row[0]) or activity != row[1]:
				continue
			if row[col_responsible] in resp:
				resp[row[col_responsible]] = resp[row[col_responsible]] + 1
			else:
				resp[row[col_responsible]] = 1
			sum = sum + 1
		N = len(resp)
		Y1=np.arange(N)
		plt.title(activity + ' % responsibility', bbox={'facecolor':'0.8', 'pad':5})
		i = 0
		labs = []
		for responsible in resp.keys():
			Y1[i] = 100*resp[responsible]/sum
			labs.append(responsible)
			i = i +1
		plt.pie(Y1, labels=labs,
				autopct='%1.1f%%', shadow=True)
		plt.show()
	

def plot_statistics(b):
	N = len(b.get_activities())
	# init and end events are not considered
	Y1=np.arange(N-2)
	ind = np.arange(N-2)  # the x locations for the groups
	width = 0.35       # the width of the bars
	
	plt.ylabel('Activity Durations')
#	plt.title('Scores by group and gender')
	acts = map (lambda x: x.name,b.get_activities())
	facts = [s for s in acts if s != 'E' and s != 'S']
	facts.sort()
	plt.xticks(ind+width, facts,rotation=17)	
	
	i = 0
	for name in facts:
		Y1[i] = b.node_info[name]['avg_duration']
		i = i +1
	
	
#	menMeans = (20, 35, 30, 35, 27)
#	menStd =   (2, 3, 4, 1, 2)



	plt.subplot(111)
	rects1 = plt.bar(ind, +Y1, width,
						color='r')#,
						#yerr=menStd,
						#error_kw=dict(elinewidth=6, ecolor='pink'))

#	womenMeans = (25, 32, 34, 20, 25)
#	womenStd =   (3, 5, 2, 3, 3)
	
#	rects2 = plt.bar(ind+width, womenMeans, width,
#						color='y',
#						yerr=womenStd,
#						error_kw=dict(elinewidth=6, ecolor='yellow'))

	# add some


#	plt.legend( (rects1[0], rects2[0]), ('Men', 'Women') )

	def autolabel(rects):
		# attach some text labels
		for rect in rects:
			height = rect.get_height()
			plt.text(rect.get_x()+rect.get_width()/2., 1.05*height, '%d'%int(height),
					ha='center', va='bottom')

	autolabel(rects1)
#	autolabel(rects2)

	plt.show()
	
def draw_bpmn(bp):
	bp.print_dot(bp.name+'.dot')
	os.system('dot -Tps '+ bp.name+'.dot > '+bp.name+'.ps')
	os.system('gv -resize ' +bp.name+'.ps')
#	os.system('ps2pdf ' + bp.name+'.ps')
#	os.system('pdfcrop '+bp.name +'.pdf')
#	os.system('evince '+ bp.name+'.pdf')

def bpmn_discovery(log,log_percentage=None,minimal_case_length=None,add_frequency=None):
	if (minimal_case_length):
		log = pmlab.log.filters.filter_log(log,pmlab.log.filters.CaseLengthFilter(above=minimal_case_length))
	if (log_percentage):
		log = pmlab.log.filters.filter_log(log,pmlab.log.filters.FrequencyFilter(log,log_min_freq=log_percentage))
	clog = pmlab.cnet.condition_log_for_cnet(log)
	skeleton = pmlab.cnet.flexible_heuristic_miner(clog)
	cn,bf = pmlab.cnet.cnet_from_log(clog,skeleton=skeleton)
	bp = pmlab.bpmn.bpmn_from_cnet(cn)
	if (add_frequency):
		bp.add_frequency_info(clog,bf)
	return bp
		
def parallel_cnet_discovery(view,log):
	cases = map(lambda t: list(t),log.get_uniq_cases())
	scat_cases = []
	for l in cases:
		s = reduce(lambda x,y: x+' '+y,l)
		scat_cases.append(s)
	view.scatter('sublog',scat_cases)
        view.execute('from pmlab import log,cnet')
	view.execute('import os')
	view.execute('l = log.log_from_iterable(sublog)')
	view.execute('cl = cnet.condition_log_for_cnet(l)')
	view.execute('cl.filename = str(os.getpid())')
	view.execute('sk = cnet.flexible_heuristic_miner(cl)')
	view.execute('c,b = cnet.cnet_from_log(cl, skeleton=sk)')
	cn = reduce(lambda x,y: x+y, view.gather('c'))
	return cn
	
	
	
