"""
Gdml representation of geant4's physical volume
"""

import bs4

from .gdml_tags import PositionTag, ScaleTag, RotationTag
from .gdml_file import GdmlFileMinimal

#class Rotation(object):


class GdmlPhysVol(object):
    """
    A gdml representation of a physical volume. This is the minimal implementation
    which means that it needs a position, a scale and a rotation as
    well as references to those as well as a reference to a solid
    and a volume.
    """

    def __init__(self,
                 name,\
                 position,\
                 solid=None,\
                 material=None,\
                 rotation={'x': 0,'y': 0, 'z' : 0},\
                 scale=[1,1,1],
                 metadata=None,
                 counter=None):
        """

        """
        self.name             = name
        self.volume_ref       = None
        self._update_names()
        self.position         = position
        self.rotation         = rotation
        self.scale            = scale
        self.solid            = solid
        self.material         = material
        self.metadata         = metadata
        self.counter          = counter
        #self.volume          = volume

        if self.metadata is None:
            self.metadata = dict()
            self.metadata['generalized_name'] = self.name
            self.metadata['unique'] = True

    ###############################################################

    @property
    def is_unique_part(self):
        print (self.metadata)
        return bool(self.metadata['unique'])

    ###############################################################

    @property
    def generalized_name(self):
        return self.metadata['generalized_name']

    ###############################################################

    @property
    def physvol_name(self):
        if self.counter is not None:
            return self.name + f'__pid{self.counter}' + '_p'
        else:
            return self.name + '_p'

    ###############################################################

    def _update_names(self):
        self.volume_ref       = self.name + '_v'
        #self.physvol_name     = self.name + '_p'

    ###############################################################

    @property
    def physvol_tag(self):
        """
        We agree on writing a tag of the form
        <physvol name="foo_p">
        <volumeref ref="foo_vref"/>
         <position x="1" y="1" z="1"/>
         <scale x="1" y="1" z="1"/>
        </physvol>

        Args:
            solidtype:

        Returns:
            bs4.element.Tag
        """

        physvol_t = bs4.element.Tag(name='physvol',\
                                    is_xml=True,\
                                    attrs={'name': self.physvol_name})
        vol_ref = bs4.element.Tag(name='volumeref',\
                                  is_xml=True, \
                                  can_be_empty_element=True, \
                                  attrs={'ref': self.volume_ref})
        physvol_t.append(vol_ref)
        pos_tag = PositionTag.create(self.position, name=self.physvol_name + '_pos')
        physvol_t.append(pos_tag)
        if (self.scale != [1,1,1]) and (self.scale is not None):
            #print(self.scale)
            scale_tag = ScaleTag.create(self.scale, name=self.physvol_name + '_sca')
            physvol_t.append(scale_tag)
        if self.rotation is not None:
            for axis in self.rotation:
                if self.rotation[axis] != 0:
                    rotation_tag = RotationTag.create(self.physvol_name + '_rot',\
                                                      axis=axis,\
                                                      value=self.rotation[axis])

                    physvol_t.append(rotation_tag)
        return physvol_t

    ###############################################################

    def add_rotation(self, axis, value):
        # rotation in degree
        self.rotation[axis] += float(value)

    ###############################################################

    def register_myself(self, gdml_file):
        """
        Write the necessary tags to the gdml file

        Args:
            gdml_file:

        Returns:
            None
        """
        if not isinstance(gdml_file,GdmlFileMinimal):
            raise ValueError(f'Can add myself only to {GdmlFileMinimal.__str__()}')

        # we rename the solid, in case this part is not unique
        # the registry will take care that it gets registered
        # at least once
        use_name = None
        if not self.is_unique_part:
            self.solid.name = self.generalized_name
            self.volume_ref = self.generalized_name + '_v'
            use_name        = self.generalized_name + '_s'

        # the solid might need additional infomartion
        # to be written to the file
        if self.solid.has_define_section:
            for tag in self.solid.define_tags():
                gdml_file.add_define_tag(tag,\
                                         generalized_part_name=self.generalized_name)

        gdml_file.add_solid_tag(self.solid.solid_tag(use_name=use_name),\
                                generalized_part_name=self.generalized_name)
        gdml_file.add_physvol_tag(self.physvol_tag)
        gdml_file.add_volume_tag(self.solid.volume_tag(self.material),\
                                 generalized_part_name=self.generalized_name)

