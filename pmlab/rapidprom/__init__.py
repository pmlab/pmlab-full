#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os, os.path
import subprocess
import contextlib
import csv
from tempfile import mkdtemp
from shutil import rmtree
from pmlab.pn import pn_from_file

if 'MAX_JAVA_MEMORY' not in os.environ:
	os.environ['MAX_JAVA_MEMORY'] = '4096'

if 'JAVA_ADDITIONAL_OPTIONS' not in os.environ:
	os.environ['JAVA_ADDITIONAL_OPTIONS'] = '-Djava.awt.headless=true'

class RapidPromError(EnvironmentError):
	pass

@contextlib.contextmanager
def _maketempdir(delete = False):
    tempdir = mkdtemp()
    yield tempdir
    if delete:
		rmtree(tempdir)

def run_rapidminer_script(script, stdout, defs):
	try:
		rapidminer_home = os.environ['RAPIDMINER_HOME']
	except KeyError:
		raise EnvironmentError, "RAPIDMINER_HOME is not set"
	rapidminer_bin = os.path.abspath(rapidminer_home + "/scripts/rapidminer")
	script = os.path.abspath(os.path.join(os.path.dirname(__file__), script))
	args = [rapidminer_bin, '-f', script]
	for k, v in defs.iteritems():
		args.append("-M%s=%s" % (k, v))
	if stdout is not None:
		out = open(stdout, 'w')
	else:
		out = None

	exitcode = subprocess.call(args, stdout=out, stderr=out, cwd = rapidminer_home, close_fds = True)

	if out is not None:
		out.close()

	if exitcode != 0:
		raise RapidPromError

def _run_miner_script(script, log, verbose=False):
	with _maketempdir() as tmpdir:
		stdout = None if verbose else os.path.join(tmpdir, "output.txt")
		log_file = os.path.join(tmpdir, 'log.xes')
		net_file = os.path.join(tmpdir, 'net.pnml')

		log.save(log_file, format='xes')

		run_rapidminer_script(script, stdout, {
			'log_file': log_file,
			'output_file': net_file
		})

		pn = pn_from_file(net_file, format='pnml')
		pn.mark_as_modified(True) # We're about to delete its temporary file

		return pn

def _parse_csv(filename):
	res = {}
	with open(filename, 'r') as f:
		r = csv.reader(f, delimiter=';')
		for row in r:
			res[row[0]] = row[1]
	return res

def mine_ilp(log, verbose=False):
	return _run_miner_script('mine_ilp.rmp', log, verbose)

def mine_inductive(log, verbose=False):
	pn = _run_miner_script('inductive.rmp', log, verbose)
	# Properly make "tau"s invisible:
	for t in pn.get_transitions(names=False):
		name = pn.vp_elem_name[t]
		if name in ("tau from tree", "tau split") or name.startswith('start tau '):
			pn.vp_transition_dummy[t] = True
	return pn

def mine_alpha(log, verbose=False):
	return _run_miner_script('alpha.rmp', log, verbose)

def measure_fitness(log, pn, states=100,verbose=False):
	with _maketempdir() as tmpdir:
		stdout = None if verbose else os.path.join(tmpdir, "output.txt")
		log_file = os.path.join(tmpdir, 'log.xes')
		net_file = os.path.join(tmpdir, 'net.pnml')
		res_file = os.path.join(tmpdir, 'res.txt')

		log.save(log_file, format='xes')
		pn.save(net_file, format='pnml')
		log.mark_as_modified(True) # We're about to delete its temporary file
		pn.mark_as_modified(True)

		run_rapidminer_script('fitness.rmp', stdout, {
			'log_file': log_file,
			'pnml_file': net_file,
			'output_file': res_file,
			'states': states
		})

		res = _parse_csv(res_file)

		return float(res['Trace Fitness'])

def measure_precision(log, pn, verbose=False):
	with _maketempdir() as tmpdir:
		stdout = None if verbose else os.path.join(tmpdir, "output.txt")
		log_file = os.path.join(tmpdir, 'log.xes')
		net_file = os.path.join(tmpdir, 'net.pnml')
		res_file = os.path.join(tmpdir, 'res.txt')

		log.save(log_file, format='xes')
		pn.save(net_file, format='pnml')
		log.mark_as_modified(True) # We're about to delete its temporary file
		pn.mark_as_modified(True)

		run_rapidminer_script('prec.rmp', stdout, {
			'log_file': log_file,
			'pnml_file': net_file,
			'output_file': res_file
		})

		res = _parse_csv(res_file)

		return {'fitness': float(res['Fitness']), 'precision': float(res['Precision'])}

