"""
Read/Emit gdml tags from the actual quantities.
"""
import bs4

from copy import copy

###########################################3

class PositionTag(object):

    @staticmethod
    def parse(tag):
        pass

    @staticmethod
    def create(pos, name=None, unit='mm'):
        attrs = dict()
        if name is not None:
            attrs['name'] = name

        attrs['x'] = pos[0]
        attrs['y'] = pos[1]
        attrs['z'] = pos[2]
        attrs['unit'] = unit
        tag = bs4.element.Tag(name='position',\
                              is_xml=True,
                              can_be_empty_element=True,
                              attrs=attrs)
        return tag

##########################################################

class ScaleTag(object):

    @staticmethod
    def parse(tag):
        pass

    @staticmethod
    def create(scale, name=None, unit='mm'):
        attrs = dict()
        if name is not None:
            attrs['name'] = name

        attrs['x'] = scale[0]
        attrs['y'] = scale[1]
        attrs['z'] = scale[2]

        tag = bs4.element.Tag(name='scale',\
                              is_xml=True,
                              can_be_empty_element=True,
                              attrs=attrs)
        return tag

##########################################################

class VolumeTag(object):

    @staticmethod
    def create(name, materialref, solidref):

        v_name = name
        if (name != 'World'):
            v_name += '_v'
        volume = bs4.element.Tag(name='volume', \
                                 is_xml=True, \
                                 attrs={'name': v_name})
        mat = bs4.element.Tag(name='materialref', \
                              is_xml=True, \
                              can_be_empty_element=True, \
                              attrs={'ref': materialref})
        sol = bs4.element.Tag(name='solidref', \
                              is_xml=True, \
                              can_be_empty_element=True,
                              attrs={'ref': solidref})
        volume.append(copy(mat))
        volume.append(copy(sol))
        return copy(volume)

###########################################

class TessellatedTag(object):
    """

    """

    @staticmethod
    def create(tessell_attrs, triangular_attrs, vertex_names):
        """

        Args:
            tessell_attrs:
            triangular_attrs:
            vertex_names: A list of strings which are references to predefined
            vertices in the define section

        Returns:

        """
        tesselltag = bs4.element.Tag(name='tessellated')
        tesselltag.attrs = tessell_attrs
        for k in vertex_names:
            ttag = bs4.element.Tag(name='triangular',\
                                   is_xml=True,\
                                   can_be_empty_element=True)
            ttag.attrs = triangular_attrs
            ttag.attrs['vertex1'] = k[0]
            ttag.attrs['vertex2'] = k[1]
            ttag.attrs['vertex3'] = k[2]
            # not clear why the copy is needed here
            # it might just be a lazy execution thing
            tesselltag.append(copy(ttag))
        return tesselltag

###########################################3

class RotationTag(object):
    @staticmethod
    def create(name, axis='x',value=90):
        rtag = bs4.element.Tag(name='rotation',\
                               is_xml=True,\
                               can_be_empty_element=True)
        attrs = {'name' : name,\
                 axis   : value,\
                 'unit' : "deg"}
        rtag.attrs = attrs
        return rtag
#class DefineTag(object):
#
#    @staticmethod
#    def creat
