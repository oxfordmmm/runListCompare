#!/usr/bin/env python

from subprocess import call
import multiprocessing, os, sys
from optparse import OptionParser

usage = '''
getClusterAlign instructions
Usage: getClusterAlign.py [options] list_of_fasta.txt cluster_file.txt ref.fa output_prefix

list_of_fasta.txt: tab delimited 1) name, 2) fasta path and filename
cluster_file.txt: cluster list generated by clusterCreator.py
ref.fa: reference in fasta format

output_prefix: output folder

Options
-p, --nprocs  number of cores to use, default 1
-m, --mask  optional mask file for mobile elements, 
            tab delimited - start and end coordinates, counting from one, not zero
-v, --varsites  proportion of variable sites to be called for variable site to be retained
				default 0.70
-s, --seq 		proportion of sequence (variable sites) required to be called for a 
				sequence to be retained, default 0.70
-n, --align		length of alignment before start filtering out sequences, default 0

Example:

getClusterAlign.py -m maskfile.txt -p 4 -v 0.70 -s 0.70 -n 0 list_of_fasta.txt cluster_file.txt ref.fa output_prefix

'''


if __name__=='__main__':

	### PROCESS INPUT OPTIONS AND ARGUMENTS ###	
	parser = OptionParser()
	parser.add_option( '-p', '--nprocs', action = 'store', type='int', dest = 'nprocs', default = 1 )
	parser.add_option( '-m', '--mask', action = 'store', type='string', dest = 'maskfile', default = '' )
	parser.add_option( '-s', '--seq', action = 'store', type='float', dest = 'seq_keep', default = 0.70 )
	parser.add_option( '-v', '--varsites', action = 'store', type='float', dest = 'varsite_keep', default = 0.70 )
	parser.add_option( '-n', '--align', action = 'store', type='int', dest = 'align_n', default = 0 )
	opts, args = parser.parse_args()
	
	#check have correct number of arguments
	if len(args) == 4:
		fileloc, clusterfile, refpath, output_stem = args
		nprocs = opts.nprocs
		maskfile = opts.maskfile
		seq_keep = opts.seq_keep
		varsite_keep = opts.varsite_keep
		align_n = opts.align_n
		
	else:
		sys.stdout.write(usage)
		sys.exit(1)
	
	
	#get list of clusters, comids
	f = open(clusterfile, 'r')
	bin = next(f)
	clusterDict = dict()

	for l in f:
		print(l)
		l = l.strip().split()
		if l[0] in list(clusterDict.keys()):
			clusterDict[l[0]].append(l[1])
		else:
			clusterDict[l[0]] = [l[1]]

	f.close()
	
	
	#get list of original file locations
	f = open(fileloc, 'r')
	faDict = dict()
	for l in f:
		l = l.strip().split()
		faDict[l[0]] = l[1]

	f.close()


	#write cluster file lists - preparatory
	# check cluster directory exists
	if not os.path.isdir('%s/cluster'%output_stem):
		os.mkdir('%s/cluster'%output_stem)
	
	print(clusterDict)

	for c in list(clusterDict.keys()):
		clusterListOut = '%s/cluster/cluster_%s.txt'%(output_stem, c)
		if len(clusterDict[c])>2:
			f = open(clusterListOut, 'w')
			for sample in clusterDict[c]:
				fa = faDict[sample]
				f.write('%s\t%s\n'%(sample, fa))
			f.close()
		
	## use parallel loop to generate alignments

	# get and clean alignment
	def getAC(c, output_stem, maskfile, varsite_keep, seq_keep, align_n):
		clusterListOut = '%s/cluster/cluster_%s.txt'%(output_stem, c)
		clusterVar = '%s/cluster/cluster_%s'%(output_stem, c)
		#make alignment
		if maskfile:
			cmd = 'python getAlignment.py -m %s %s %s %s'%(maskfile, clusterListOut, refpath, clusterVar)
		else:
			sys.stdout.write('Proceeding without mask file\n')
			cmd = 'python getAlignment.py %s %s %s'%(clusterListOut, refpath, clusterVar)
		sys.stdout.write('%s\n'%cmd)
		sys.stdout.flush()
		call(cmd.split())
		#clean alignment
		cmd = 'python cleanAlignment.py -v %s -s %s -n %s %s'%(varsite_keep, seq_keep, align_n, clusterVar)
		call(cmd.split())
	
	# do get AC for particular modulus and cluster list
	def runAC(i, cd, nprocs):
		for c in cd[i::nprocs]:
			getAC(c, output_stem, maskfile, varsite_keep, seq_keep, align_n)

	# get list of clusters
	cd = [int(c) for c in list(clusterDict.keys()) if len(clusterDict[c])>2]
	cd.sort(reverse=True)

	procs = []

	for i in range(nprocs):
		p = multiprocessing.Process(
				target=runAC,
				args=(i, cd, nprocs))
		procs.append(p)
		p.start()

	# Wait for all worker processes to finish
	for p in procs:
		p.join()