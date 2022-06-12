"""
Base class for gdml solid parsing

"""

from copy import copy
import bs4
import trimesh
import vectormath as vm

from .gdml_tags import PositionTag, ScaleTag, VolumeTag, TessellatedTag

class GDMLAbstractSolid(object):
    """
    Abstract base class
    """
    # does the solid need
    # extra geometrical information (e.g. vertices)
    # for which tags need to be
    # written to a gdml define section?
    has_define_section = False

    def solid_tag(self):
        raise NotImplementedError(f'Not implemented for {type(self)}')

    def volume_tag(self):
        raise NotImplementedError(f'Not implemented for {type(self)}')

    def define_tags(self):
        raise NotImplementedError(f'Not implemented for {type(self)}')

###########################################################
# BOX
##########################################################

class GdmlBox(GDMLAbstractSolid):
    """
    The gdml representation of a G4Box
    """
    def __init__(self, name ,x_half, y_half, z_half):
        """

        Args:
            name:
            x_half:
            y_half:
            z_half:
        """
        self.name = name
        self.dimension = (x_half, y_half, z_half)

    def solid_tag(self):
        attrs = dict()
        attrs['name'] = self.name + '_s'
        attrs['x']    = self.dimension[0]
        attrs['y']    = self.dimension[1]
        attrs['z']    = self.dimension[2]
        tag = bs4.element.Tag(name='box',\
                              is_xml=True,\
                              can_be_empty_element=True,
                              attrs=attrs)
        return tag

    def volume_tag(self, material):
        return VolumeTag.create(self.name, material, self.name + '_s')

##################################################################################3
# TESSELLATED SOLID
###################################################################################

class GdmlTessellatedSolid(GDMLAbstractSolid):
    """

    pass
    A tesselated solid, which can be serialized/deserialized to gdml with
    a <define> and <solid> section.
    """

    def __init__(self, identifier=0):
        self.has_define_section = True
        self.name = "NONE"
        self.named_vertices = {}
        self.vertices = []
        self.vertex_pts = []
        self.triangles = []
        self.faces = []
        self.areas = []
        self.indizes = {}  # position name ->index
        self.faces = []
        self.vertex_names = []
        self.unit = None
        self.triangular_attrs = {}
        self.tessell_attrs = {}
        self.tolerance = 0
        self.ntriangles = 0
        self.ninvalidtri = 0
        self._identifier = identifier
        # the center of gravity
        self.center_mass = None
        self.trafo_to_write = None

        # this can hold a name for
        # a material as well
        self.material = None

        # in case we have moved it,
        # record the new position
        self.position = None

        self.rotation = None

        # in case we have scaled it,
        # record the scalefactors
        self.scalefactors = None

        # usually, the volume reference is
        # inferred, however, it can be changed
        # so that we can use the solid for
        # a different phys volume
        self.volume_ref = None

    @property
    def identifier(self):
        #return self.name + str(self._identifier)
        return self._identifier

    def set_material(self, material):
        self.material = material

    def set_tolerance(self, worldextent):
        """
        Worldextent is needed to define tolerances.
        Worldextent in mm
        """
        self.tolerance = 1e-11 * worldextent

    @property
    def nvertices(self):
        return len(self.vertices)

    def __repr__(self):
        return f'<GdmlTessellatedSolid with {self.nvertices} vertices>'

    def get_auxiliary_info(self):
        """
        Create the corresponding mesh with trimesh,
        calculate the center of gravity and write it
        to the axiliary file.
        """
        mesh = trimesh.Trimesh(vertices=self.vertices, faces=self.faces)
        self.trafo_to_write = 'NONE'
        try:
            center_mass = mesh.center_mass
        except Exception as e:
            print(f'Calculating center_mass of {self.name} caused exception {e}')
            return self.trafo_to_write
        self.trafo_to_write = (f'{self.name} -- {center_mass}\n')
        self.center_mass = center_mass
        return self.trafo_to_write

    def scale(self, x, y, z):
        """
        """
        # make sure the scale is not applied multiple time
        # this means, whenever we scale something
        # rescale it to 1 first
        if self.scalefactors is not None:
            print (self.scalefactors)
            raise
            x_0, y_0, z_0 = self.scalefactors
            self.vertices = [((k[0] * 1/x_0),
                             (k[1] * 1/y_0),
                             (k[2] * 1/z_0)) for k in self.vertices]

        shifted_vertices = [(k[0] * x,\
                             k[1] * y,\
                             k[2] * z) for k in self.vertices]
        self.vertices = shifted_vertices
        self.scalefactors = (x, y, z)
        # fixes the self.named_vertices and
        # makes sure nothing got messed up
        # during the scaling
        self.remove_invalid_triangles()

    def translate(self, x, y, z):
        """
        Translate to arbitrary position
        """
        shifted_vertices = [(k[0] + x,\
                             k[1] + y,\
                             k[2] + z) for k in self.vertices]
        self.vertices = shifted_vertices
        self._update_vertices()
        self.position = (x, y, z)

    def translate_to_center_mass(self):
        """
        Translate the whole solid to its center of mass
        """
        if self.center_mass is None:
            self.get_auxiliary_info()
        conv = 1e-5
        conv = 0.05
        conv = 1
        shifted_vertices = [(k[0] - self.center_mass[0] * conv,\
                             k[1] - self.center_mass[1] * conv,\
                             k[2] - self.center_mass[2] * conv) for k in self.vertices]

        self.vertices = shifted_vertices
        self._update_vertices()
        self.position = self.center_mass #* 0.1


    def calculate_triangle_areas(self):
        """
        Calculate all triangle areas
        Returns:
            None
        """
        def area(x,y,z):
            """
            args are 3 vectormath.Vector3 vectors
            """
            a = y - x
            b = z - x
            return 0.5 * a.cross(b).length

        self.areas = [area(*k) for k in self.triangles]

    def check_triangle_g4valid(self, face):
        """
        A face has 3 vertices. This code is ported from
        geant4's G4TriangularFacet
        """
        self.ntriangles += 1
        delta = self.tolerance
        v0, v1, v2 = face
        v0 = vm.Vector3(self.named_vertices[f'v{self.identifier}_{v0}'])
        v1 = vm.Vector3(self.named_vertices[f'v{self.identifier}_{v1}'])
        v2 = vm.Vector3(self.named_vertices[f'v{self.identifier}_{v2}'])
        # FIXME - it seems all the vertices are always absolut
        # however, as it is with always, nothing is ever "always"
        # so FIXME - watch out
        e1 = v1 - v0
        e2 = v2 - v0
        e1xe2 = e1.cross(e2)
        area = 0.5 * e1xe2.length
        # checks
        leng1 = e1.length
        leng2 = (e2 - e1).length
        leng3 = e1.length
        # print (f'{leng1, leng2, leng3, 2*area/max(max(leng1, leng2, leng3)), delta}')
        if (leng1 <= delta or leng2 <= delta or leng3 <= delta):
            # print (f'Invalid triangle {leng1, leng2, leng3} , delta {delta}')
            self.ninvalidtri += 1
            return False
        if (2. * area / max(max(leng1, leng2), leng3) <= delta):
            # print (f'Invalid triangle {2.*area/max(max(leng1,leng2),leng3)} , {delta}')
            self.ninvalidtri += 1
            return False
        return True

    def is_similar(self, other):
        """
        Check if this solid seams to be similar to
        another one.
        If the value is really small, it it pretty likely they are similar.
        """
        other_name = other.name
        mesh = trimesh.Trimesh(self.vertices, self.faces)
        other = trimesh.Trimesh(other.vertices, other.faces)
        try:
            a = trimesh.comparison.identifier_simple(mesh)
            b = trimesh.comparison.identifier_simple(other)
        except Exception as e:
            print(f'Can not compare {self.name} and {other_name}')
            return np.inf
        return compare_mesh(a, b)

    def _update_vertices(self):
        """

        Args:
            mesh:

        Returns:

        """

        for k, v in enumerate(self.vertices):
            # keep the name valid, but short to reduce gdml file size
            self.named_vertices[f'v{self.identifier}_{k}'] = v


    def remove_invalid_triangles(self):
        """
        Create a trimesh.Trimesh. During the processing of the
        Trimesh, invalid triangles will be automatically removed,
        so the only thing is we have to convert it back and forth.
        Obviously, our inital naming conventions will be lost, but
        we can take care of that by just setting up a new one, as
        long as we keep everything in sync.
        """
        mesh = trimesh.Trimesh(vertices=self.vertices, faces=self.faces, validate=True)
        # clear out the old values
        self.vertex_names.clear()
        self.named_vertices.clear()
        for k, v in enumerate(mesh.vertices):
            # keep the name valid, but short to reduce gdml file size
            self.named_vertices[f'v{self.identifier}_{k}'] = v
        # check tthat the triangles are valid first, before appending them
        # if there are "stale" vertices, we have to remove them at the very end
        # TODO
        for k in mesh.faces:
            if not self.check_triangle_g4valid(k):
                continue  # don't use that triangle then

            self.vertex_names.append((f'v{self.identifier}_{k[0]}', \
                                      f'v{self.identifier}_{k[1]}', \
                                      f'v{self.identifier}_{k[2]}'))

    @property
    def vpoints(self):
        if self.vertex_pts:
            return self.vertex_pts
        else:
            self.vertex_pts = [np.array([[k[0].x, k[0].y, k[0].z], \
                                         [k[1].x, k[1].y, k[1].z], \
                                         [k[2].x, k[2].y, k[2].z]]) \
                               for k in self.triangles]
            self.vertex_pts.flatten()
            return self.vertex_pts

    def create_define_tag(self):
        deftag = bs4.element.Tag(name='define', is_xml=True)
        for vtag in self.define_tags():
            #vtag = PositionTag.create(self.named_vertices[k][0], \
            #                          self.named_vertices[k][1], \
            #                          self.named_vertices[k][2], \
            #                          name=k, unit=self.unit)
            # vtag = bs4.element.Tag(name='position', is_xml=True, can_be_empty_element=True)
            # vtag.attrs['name'] = k
            # vtag.attrs['x'] = self.named_vertices[k][0]
            # vtag.attrs['y'] = self.named_vertices[k][1]
            # vtag.attrs['z'] = self.named_vertices[k][2]
            # vtag.attrs['unit'] = self.unit
            deftag.append(vtag)
        return deftag

    def define_tags(self):
        for k in self.named_vertices:
            dtag = PositionTag.create(self.named_vertices[k],\
                                      name=k, unit=self.unit)
            yield dtag

    def volume_tag(self, material, fix_solid_reference=True):
        name = self.name
        if fix_solid_reference:
            name += '_s'
        vtag = VolumeTag.create(self.name,material,name)
        return vtag

    def solid_tag(self, use_name=None):
        attrs = self.tessell_attrs
        # follow new convetion - everything in the solid
        # section ends with _s
        attrs['name'] = attrs['name'] + '_s'
        if use_name is not None:
            attrs['name'] = use_name
        tesselltag = TessellatedTag.create(attrs, self.triangular_attrs,\
                                           self.vertex_names)
        #tesselltag = bs4.element.Tag(name='tessellated',is_xml=True)
        #tesselltag.attrs = self.tessell_attrs
        #for k in self.vertex_names:
        #    ttag = bs4.element.Tag(name='triangular', can_be_empty_element=True)
        #    ttag.attrs = self.triangular_attrs
        #    ttag.attrs['vertex1'] = k[0]
        #    ttag.attrs['vertex2'] = k[1]
        #    ttag.attrs['vertex3'] = k[2]
        #    # not clear why the copy is needed here
        #    # it might just be a lazy execution thing
        #    tesselltag.append(copy(ttag))
        return tesselltag

    def create_solid_tag(self, no_name_change=False):
        """
        Prepare the tag defining the facets of the tessellated solid
        This creates a tag of the following kind
        <solids>
          <tessellated name= ...>
            <triangular vertex1=.../>
        """
        solidtag = bs4.element.Tag(name='solids')
        tesselltag = self.solid_tag()
        if no_name_change:
            tesselltag.attrs['name'] = self.name
        solidtag.append(tesselltag)
        return solidtag
