#! /usr/bin/env python

# Copyright (c) 2014, Antti Honkela
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# 
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import sys, os, subprocess
import re
import codecs
import pickle
from unidecode import unidecode

PAGESIZES = {'595 x 841 pts': 'a4',
'595 x 842 pts (A4)': 'a4',
'595.22 x 842 pts (A4)': 'a4',
'595.27 x 841.82 pts (A4)': 'a4',
'595.276 x 841.89 pts (A4)': 'a4',
'595.28 x 841.89 pts (A4)': 'a4',
'612 x 792 pts (letter)': 'letter'}

authorre = re.compile(r"""([\-.\w ]+[\-.\w])\*? \([^)]*\)""", re.UNICODE)

################
# BEGIN CONFIG #
################
# Conference year
YEAR = '14'

# Author information file from CMT, assumed to be in UTF-16 encoding (Excel!), format:
# Users And Roles 
#        
# FirstName       LastName
AUTHORFILE = 'cmt_users_2014-03-13.txt'

# Camera ready paper information file from CMT, UTF-16 encoding, format:
# [Track name]
#                                                                        
# ID      Title   Track   Abstract        Name (Org)      Name (Org) <Email>      Email   Files   ...
PAPERFILE = 'Camera_Ready_Papers_2014-03-13.txt'

# Directory with paper pdfs with 'Paper xx' subdirectories for each paper
PAPER_INPUT_DIR = os.path.expanduser('~/myconference/original_papers')

# Directory for LaTeX sources generated by the script
LATEX_SOURCE_DIR = os.path.expanduser('~/myconference/latex_sources')

# Directory for the final proceedings generated by the script
PAPER_OUTPUT_DIR = os.path.expanduser('~/myconference/final_proceedings')

# Title fix file, format:
# biblabel[tab]New title
TITLE_FIX_FILE = 'title_fixes.txt'

# Abstract fix file, format:
# biblabel[tab]New abstract
ABSTRACT_FIX_FILE = 'abstract_fixes.txt'
BIB_FILENAME = os.path.expanduser('~/myconference/final_proceedings/myconference2014.bib')

# Special paper ids, to be placed at the beginning of the proceedings
NOTABLE_PAPER_IDS = [283, 46, 43]

# Bib entry for the proceedings and preface
BIB_PREAMBLE = """@Proceedings{AISTATS-2014,
  booktitle = {Proceedings of the Seventeenth International Conference on Artificial Intelligence and Statistics},
  editor = {Samuel Kaski and Jukka Corander},
  volume = {33},
  year = {2014},
  shortname = {AISTATS}
}

@InProceedings{kaski14,
  title = {Preface},
  author = {Kaski, Samuel and Corander, Jukka},
  pages = {i-iv},
  abstract = {Preface to AISTATS 2014}
}\n\n"""
################
#  END CONFIG  #
################

def read_user_names(authorfile):
    f = codecs.open(authorfile, 'r', 'utf16')
    l = f.next()
    while l[0:5] != "First":
        l = f.next()
    fields = parse_header(l)
    authors = dict()
    for l in f:
        d = parse_line(l, fields)
        authors['%(FirstName)s %(LastName)s' % d] = d
    return authors

def parse_header(header):
    t = header.strip().split('\t')
    return t

def parse_line(line, fields):
    t = line.strip().split('\t')
    return dict(zip(fields, t))

def read_paper_info(fname):
    f = codecs.open(fname, 'r', 'utf16')
    l = f.next()
    while l[0:2] != "ID":
        l = f.next()
    fields = parse_header(l)
    papers = []
    for l in f:
        papers.append(parse_line(l, fields))
    f.close()
    return papers

def read_fixes(fname):
    try:
        f = codecs.open(fname, 'r', 'utf8')
        fixes = dict()
        for l in f:
            t = l.strip().split('\t')
            fixes[t[0].lower()] = t[1]
        return fixes
    except:
        print "Cannot open fix file %s, ignoring." % fname
        return dict()

def apply_fixes(papers, fixes, field):
    for i, p in enumerate(papers):
        if p['bibid'] in fixes:
            papers[i][field] = fixes[p['bibid']]
    return papers

def convert_authors(paper, users):
    author = paper['Name (Org)']
    a = author.strip('"').split(';')
    aa = [re.match(authorre, au).group(1) for au in a]
    aa = [au.replace("  ", " ") for au in aa]
    a2 = [au.replace("  ", " ") for au in aa]
    # Capitalize first and last word of names
    for k in range(len(aa)):
        an = aa[k].split(' ')
        an[0] = an[0][0].capitalize() + an[0][1:]
        an[-1] = an[-1][0].capitalize() + an[-1][1:]
        aa[k] = ' '.join(an)
        if (len(an) > 2):
            name = ' '.join(an)
            #print "Difficult name:", name
            if name in users:
                a2[k] = "%(LastName)s, %(FirstName)s" % users[name]
            else:
                raise(Exception("Author not in users!"))
            #print "trying:", aa[k]
        else:
            a2[k] = an[-1] + ', ' + ' '.join(an[:-1])
    bibauthor = ' and '.join(a2)
    leadauthor = bibauthor[0:bibauthor.index(',')]
    paper['bibtex_author'] = bibauthor
    paper['leadauthor'] = leadauthor
    paper['linear_author'] = ', '.join(aa)
    return paper

def normalise_name(name):
    try:
        name.encode('ascii')
    except:
        print 'Converting for id:', name, '->', unidecode(name)
        return unidecode(name).lower()
    else:
        return name.lower()

def generate_identifiers(papers):
    leadauthors = [paper['leadauthor'] for paper in papers]
    clashes = {}
    for i, a in enumerate(leadauthors):
        au = normalise_name(a) + YEAR
        # check if there are multiple authors with same name
        if leadauthors.count(a) > 1:
            if au in clashes:
                clashes[au] = chr(ord(clashes[au]) + 1)
            else:
                clashes[au] = 'a'
            papers[i]['bibid'] = (au + clashes[au]).replace(" ", "")
        else:
            papers[i]['bibid'] = au.replace(" ", "")
    return papers

def generate_pages(papers):
    curpage = 0
    for i, p in enumerate(papers):
        thispages = int(p['main_pdf_info']['Pages'])
        papers[i]['pages'] = (curpage+1, curpage+thispages)
        papers[i]['pagestring'] = "%d-%d" % papers[i]['pages']
        curpage += thispages
    return papers

def cleanup_abstract(paper):
    abs = paper['Abstract']
    paper['Abstract'] = abs.strip()
    return paper

def create_bibentry(paper):
    return """@InProceedings{%(bibid)s,
  title = {{%(Title)s}},
  author = {%(bibtex_author)s},
  pages = {%(pagestring)s},
  abstract = {%(Abstract)s}
}""" % paper

def print_bibfile(papers, outfile):
    f = codecs.open(outfile, 'w', 'utf8')
    f.write(BIB_PREAMBLE)
    for p in papers:
        f.write(create_bibentry(p) + '\n\n')
    f.close()

def check_pdfinfo(file):
    info = subprocess.check_output(["pdfinfo", file])
    info = dict([[y.strip() for y in x.split(':', 1)] for x in info.strip().split('\n')])
    if info['Page size'] not in PAGESIZES:
        print 'Unknown page size:', info['Page size']
    else:
        info['Paper size'] = PAGESIZES[info['Page size']]
    return info

def find_papers(paper, dir):
    id = '%(ID)s' % paper
    mydir = dir + '/Paper %s' % id
    ls = os.listdir(mydir)
    if len(ls) == 1:
        paper['main_pdf'] = mydir + '/' +  ls[0]
        paper['supp_file'] = None
    elif len(ls) == 2:
        mainfile = '%s.pdf' % id
        if mainfile in ls:
            paper['main_pdf'] = mydir + '/' +  ls[ls.index(mainfile)]
            paper['supp_file'] = mydir + '/' +  ls[1-ls.index(mainfile)]
        else:
            suppfile = [f for f in ls if "supp" in f]
            if len(suppfile) == 0:
                suppfile = [f for f in ls if "extra" in f]
            if len(suppfile) == 0:
                suppfile = [f for f in ls if "appendix" in f]
            if suppfile[0] in ls:
                paper['main_pdf'] = mydir + '/' +  ls[1-ls.index(suppfile[0])]
                paper['supp_file'] = mydir + '/' +  ls[ls.index(suppfile[0])]
            print "Non-standard file names, using %s for main text, %s for supplement" % (ls[1-ls.index(suppfile[0])], ls[ls.index(suppfile[0])])
    else:
        raise(Exception("Invalid number of files found"))
    paper['main_pdf_info'] = check_pdfinfo(paper['main_pdf'])
    return paper

def write_paper_latex(paper, outputpath):
    pagesize = paper['main_pdf_info']['Paper size']
    pdfversion = paper['main_pdf_info']['PDF version'].split('.')[1]
    if pdfversion < '4':
        pdfversion = '4'
    if pagesize is None:
        raise "Bad page size!"
    filename = outputpath + '/%s.tex' % paper['bibid']
    f = open(filename, 'w')
    f.write("""\\documentclass{article}
\\usepackage{graphicx}
\\usepackage[%s]{geometry}
\\usepackage{times}
\\usepackage{pdfpages,calc}
\\usepackage[space]{grffile}
\\usepackage[absolute]{textpos}

\\setlength{\\topmargin}{-15mm}
\\setlength{\\textheight}{21cm}
\\setlength{\\oddsidemargin}{0mm}
\\setlength{\\evensidemargin}{0mm}
\\setlength{\\textwidth}{125.2mm}

\\pdfinclusioncopyfonts=1
\\pdfminorversion=%s

\\begin{document}

\\pagestyle{empty}

\\centering\n""" % (pagesize+'paper', pdfversion))
    for k in range(int(paper['main_pdf_info']['Pages'])):
        f.write("""\\includepdf[pages=%d,offset=0 %s,pagecommand={\\begin{textblock*}{0mm}(\\paperwidth/2,268mm)
\\parbox{10mm}{\\centering \\usefont{T1}{ptm}{m}{n} \\small %d}
\\end{textblock*}}]{%s}\n""" % (k+1, '0', paper['pages'][0]+k, paper['main_pdf']))
    f.write("\\end{document}\n")
    f.close()
    paper['tex_file'] = filename
    return paper
    #os.system("pdflatex -interaction nonstopmode -output-directory=%s %s/mlsp2010_paper_%s.tex" % (path, path, paperid))

def compile_and_copy(paper, outputdir):
    cwd = os.getcwd()
    os.chdir(os.path.dirname(paper['tex_file']))
    subprocess.call(['tex2pdf', paper['tex_file']])
    os.chdir(cwd)
    s = os.path.splitext(paper['tex_file'])
    subprocess.call(['cp', s[0] + '.pdf', outputdir])
    if paper['supp_file']:
        s = os.path.splitext(paper['supp_file'])
        subprocess.call(['cp', paper['supp_file'],
                         outputdir + '/' + paper['bibid'] + '-supp' + s[1]])


def print_abstracts(papers, file):
    f = codecs.open(file, 'w', 'utf8')
    f.write("""\\documentclass{article}
\\usepackage[utf8]{inputenc}
\\usepackage{graphicx}
\\usepackage[a4paper]{geometry}
\\usepackage{times}
\\usepackage{pdfpages,calc}
\\usepackage[space]{grffile}
\\usepackage[absolute]{textpos}

\\begin{document}

\\pagestyle{empty}\n\n""")
    for p in papers:
        f.write("""(%(bibid)s) \\textbf{%(Title)s}\\\\
%(linear_author)s\\\\
%(Abstract)s\\\\[1em]\n""" % p)
    f.write("\n\end{document}\n")
    f.close()


def save_database(papers, file):
    pickle.dump(papers, open(file, 'wb'), 1)


users = read_user_names(AUTHORFILE)
papers = read_paper_info(PAPERFILE)
papers = [convert_authors(paper, users) for paper in papers]
papers.sort(key=lambda x: (x['bibtex_author'], x['ID']))
papers = generate_identifiers(papers)
# Move notable paper to the front
inds = [i for i, p in enumerate(papers) if int(p['ID']) in NOTABLE_PAPER_IDS]
for i, ind in enumerate(inds):
    papers.insert(i, papers.pop(ind))
papers = apply_fixes(papers, read_fixes(TITLE_FIX_FILE), 'Title')
papers = apply_fixes(papers, read_fixes(ABSTRACT_FIX_FILE), 'Abstract')

papers = [cleanup_abstract(paper) for paper in papers]

# Find the pdfs and extract info
papers = [find_papers(paper, PAPER_INPUT_DIR) for paper in papers]

# Generate page numbers
papers = generate_pages(papers)

# Write LaTeX wrappers
papers = [write_paper_latex(p, LATEX_SOURCE_DIR) for p in papers]

# Compile LaTeX for all the papers
for p in papers:
    compile_and_copy(p, PAPER_OUTPUT_DIR)

# Print the final bib file
print_bibfile(papers, BIB_FILENAME)
