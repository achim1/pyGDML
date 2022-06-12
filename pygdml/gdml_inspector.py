#! /usr/bin/env python

"""
Show properties of a gdml file, list volumes and
number of facets
"""

import bs4
#import re

from tessellatedsolid import extract_tessellated_solids, get_unique_names

from collections import defaultdict

if __name__ == '__main__':
    
    import argparse

    parser = argparse.ArgumentParser(description='Inspect a gdml file. Show a list of parts and materials')
    parser.add_argument('infile', metavar='infile', type=str,
                        help='Input .gdml file')
    parser.add_argument('--show-relations', dest='show_relations', action='store_true',
                        default=False,
                        help='Go through all the volumes and show those which are similar to it')
    parser.add_argument('--show-unique-names', dest='show_unique_names', action='store_true',
                        default=False,
                        help='Go through all the volumes and show identify which names are (sort of) unique. Do this by comparing the names without the nubmers')
    args = parser.parse_args()

    gdml = bs4.BeautifulSoup(open(args.infile), features="lxml-xml")
    
    # assume we have materials
    cursor = gdml.gdml.materials
    if cursor is None:
        cursor = bs.gdml.define
    all_tessell_solids = extract_tessellated_solids(cursor) 

    allchildren = gdml.gdml.findChildren(recursive=False)
    for k in allchildren:
        if k.name == 'solids':
            for j in k.findChildren(recursive=False):
                print (f'-- -- SOLID: {j.name}/{j.attrs["name"]} - nelements : {len([n for n in j.children])}')
            continue
        if k.name == 'structure':
            print ('-- STRUCTURE:')
            for j in k.findChildren(recursive=False):
                if j.name == 'volume':
                    volumename = j.attrs['name']
                    material = 'NONE'
                    solidref = 'NONE'
                    for n in j.findChildren(recursive=False):
                        if n.name == 'materialref':
                            materialref = n.attrs['ref']
                        if n.name == 'solidref':
                            solidref = n.attrs['ref']
                    print (f'-- -- {volumename}/{solidref}/{materialref}')
                    continue
                #print (f'-- -- STRUCTURE: {j.name}/{j.attrs["name"]} - nelements : {len([n for n in j.children])}')
            continue
        # children without a name
        try:
            print (f'-- {k.name}/{k.attrs["name"]} - nelements : {len([j for j in k.children])}')
        except:
            print (f'-- {k.name}/NONE - nelements : {len([j for j in k.children])}')

    if args.show_relations:
        print ('Checking for similarities...')
        threshold = 1e-9
        stop = False
        sisters = defaultdict(list)
        for k in all_tessell_solids:
            for j in all_tessell_solids:
                if k.name == j.name:
                    continue
                result = k.is_similar(j)
                if result < threshold:
                    j.result = result
                    sisters[k].append(j)

        print ("Related parts")
        for k in sisters:
            print (f'-- {k.name}:') 
            for j in sisters[k]:
                print (f'-- -- {j.name}/{j.result}')
            print ('====================\n\n')
    if args.show_unique_names:
        get_unique_names(all_tessell_solids)
    
