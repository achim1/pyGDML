"""
Extract and parser certain entities from a gdml file
"""


import bs4
import vectormath as vm
import tqdm
import numpy as np
import rich
import hjson

import logging
LOG = logging
try:
    import hepbasestack as hep
    from . import __package_loglevel__
    LOG = hep.logger.get_logger(__package_loglevel__)
    del logging
except ImportError:
    pass

from .gdml_solid import GdmlTessellatedSolid

from copy import copy, deepcopy

################################################################

def get_unique_names(tessell_list,
                     metainfo=None,
                     return_solids=False):
    """

    Keyword Args:
        metainfo (str)       : filename for .json file with
                               meta info
        return_solids (bool) : return the actual solids as well


    """
    if metainfo is not None:
        metainfo = hjson.load(open(metainfo))

    names = [k.name for k in tessell_list if k.name != 'NONE']
    names = [k.split('__uid')[0] for k in names]
    # names = [''.join([i for i in s if not i.isdigit()]) for s in names]
    names = set(names)
    names = [k for k in set(names)]
    if metainfo is not None:
        names = metainfo['functional_parts'].keys()
        parts = metainfo['functional_parts']
    print(f'We found {len(names)} unique names!')
    print('[')
    for k in sorted(names):
        print(k)
    print(']')

    all_followers = []
    group = dict()
    for k in names:
        if k in all_followers:
            continue
        print(f'Checking {k}')
        followers = [j.name for j in tessell_list if ((j.name.startswith(k) and (j.name != k)))]
        followers = [j for j in followers if (not j in all_followers)]
        if return_solids:
            followers_solids = [t for t in tessell_list if ((t.name in followers) or (t.name == k))]
            if 'position_sequence' in parts[k]:
                position_sequence = parts[k]['position_sequence']
                print(position_sequence)
                for pos in position_sequence:
                    pos = (float(pos[0]), float(pos[1]), float(pos[2]))
                [t.translate(*pos) for t in followers_solids]
                # materials
            [t.set_material(parts[k]['material']) for t in followers_solids]
        all_followers.extend(followers)
        print(f'-- found {len(followers)} followers...')
        if return_solids:
            if len(followers) > 1:
                group[followers[0]] = (followers[1:], followers_solids)
            elif len(followers) == 1:
                group[followers[0]] = (followers, followers_solids)
            else:
                continue
        else:
            if len(followers) > 1:
                group[followers[0]] = followers[1:]
            elif len(followers) == 1:
                group[followers[0]] = followers
            else:
                continue

    console = rich.get_console()
    for k in group:
        if return_solids:
            console.print(f'{k} x {len(group[k][0]) + 1}:', style='bold underline')
            print(f'--{k} [leader]')
            for j in group[k][0]:
                print(f'-- --{j} [follower]')
        else:
            console.print(f'{k} x {len(group[k]) + 1}:', style='bold underline')
            print(f'--{k} [leader]')
            for j in group[k]:
                print(f'-- --{j} [follower]')

    return group

################################################################


def is_world(name):
    if name.lower() in ['worldbox', 'world']:
        return True

################################################################


def compare_mesh(a, b):
    """
    Quadratic array comparator
    """
    assert (len(a) == len(b))
    vals = [np.sqrt((a[k] - b[k]) ** 2) for k in range(len(a))]
    return sum(vals)

##################################


def extract_tessellated_solids(cursor, \
                               solid_tags_to_write=[], \
                               tags_to_write=[],
                               tessellsolid_identifier=0):
    """
    Go over a gdml file and extract all tessellated solids
    Keep track of the other tags in the file which are
    NOT tessellated solids (like the world box)

    Args:
        cursor (bs4.element) : The starting point into the gdml file
    Keyword Args:
        solid_tags_to_write (list, MUTABLE) : [it will be used to append tags]
        tags_to_write (list, MUTABLE)       : [it will be used to append tags]
    """
    # tessellsolid_identifier = 0 # mark each tessellated solid
    # with an individual identifier

    nkids = len(cursor.findAll())
    ntess = 0  # how many tesseleated solids
    all_tessell_solids = []
    pbar = tqdm.tqdm(total=nkids)
    while cursor is not None:
        print(cursor.name)
        if cursor.name == 'define':
            # cursor = cursor.findNextSibling()
            # continue
            # if we saw more than one tesselated solid
            # per define section, the whole shebang
            # blows up.
            if ntess > 1:
                raise ValueError(f'Too many tessellated solids per define section! {ntess}')

            ntess = 0
            gt_solid = GdmlTessellatedSolid(identifier=tessellsolid_identifier)
            tessellsolid_identifier += 1
            # FIXME - look up what is our world extent.
            # By derault, when reading the triangles,
            # it seems to be set to 1e-9 in g4,
            # so for now let's try this
            # gt_solid.set_tolerance(1e-09)
            gt_solid.tolerance = 1e-9
            for j, vertex in enumerate(cursor.findChildren()):
                if 'name' in vertex.attrs:
                    if vertex.attrs['name'] == 'center':
                        deftag = bs4.element.Tag(name='define')
                        deftag.append(vertex)
                        solid_tags_to_write.append(deftag)
                        continue

                # print (vertex)
                vtuple = (float(vertex.attrs['x']), \
                          float(vertex.attrs['y']), \
                          float(vertex.attrs['z']))
                gt_solid.unit = vertex.attrs['unit']
                vtuple_vec = vm.Vector3(*vtuple)
                gt_solid.vertices.append(vtuple)
                gt_solid.named_vertices[vertex.attrs['name']] = vtuple_vec
                gt_solid.indizes[vertex.attrs['name']] = j
            cursor = cursor.findNextSibling()
            continue

            # it is absolutely crucical, that for
        # each define section, there is
        # a solids section with exactly one
        # tesselated solid afterwards
        elif cursor.name == 'solids':
            # cursor = cursor.findNextSibling()
            # continue
            # note that the recursive behavior of findChildren
            # can be switched off, in case the structur
            # of our gdml file changes
            for kiddo in cursor.findChildren():
                if 'name' in kiddo.attrs:
                    if kiddo.attrs['name'] == 'worldbox':
                        soltag = bs4.element.Tag(name='solids')
                        soltag.append(kiddo)
                        solid_tags_to_write.append(soltag)
                        continue

                if kiddo.name == 'tessellated':
                    gt_solid.tessell_attrs = kiddo.attrs
                    gt_solid.name = kiddo.attrs['name']
                    ntess += 1
                    continue
                if kiddo.name == 'triangular':
                    gt_solid.triangular_attrs = kiddo.attrs
                    v1 = kiddo.attrs['vertex1']
                    v2 = kiddo.attrs['vertex2']
                    v3 = kiddo.attrs['vertex3']
                    gt_solid.vertex_names.append((v1, v2, v3))
                    gt_solid.triangles.append((gt_solid.named_vertices[v1], \
                                               gt_solid.named_vertices[v2], \
                                               gt_solid.named_vertices[v3]))
                    gt_solid.faces.append([gt_solid.indizes[v1], gt_solid.indizes[v2], gt_solid.indizes[v3]])

            # don't extract corrupt solids
            if not gt_solid.nvertices:
                print(f'WARNING {gt_solid.name} has 0 vertices!')
                cursor = cursor.findNextSibling()
                continue
            all_tessell_solids.append(deepcopy(gt_solid))
            del gt_solid
            cursor = cursor.findNextSibling()
            # break
            continue

        else:
            # we need to keep the other tags
            # e.g. setup and so on

            LOG.debug(f'Register {cursor.name} for copy...')
            tags_to_write.append(copy(cursor))
        # cleaned_file.write(cursor.decode())
        cursor = cursor.findNextSibling()
        pbar.update(1)
    pbar.close()
    return all_tessell_solids


