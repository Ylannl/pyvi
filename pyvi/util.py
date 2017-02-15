import numpy as np
from .gloo import *

class BBox(object):
    def __init__(self, data_array=None):
        self.is_empty = True
        if not data_array is None:
            self.update(data_array)

    def update(self, data_array, reset=False):
        mi = np.nanmin(data_array, axis=0)
        ma = np.nanmax(data_array, axis=0)
        if self.is_empty or reset:
            self.mi = mi
            self.ma = ma
        else:
            self.mi = np.min([self.mi, mi], axis=0)
            self.ma = np.max([self.ma, ma], axis=0)
        self.dim = len(data_array)
        self.width = self.ma - self.mi
        self.center = self.mi + self.width/2
        self.is_empty = False


class Shader(object):
    vertexShaderSource = '''
#version 330
in highp vec3 a_position;
in lowp vec3 a_color;
out lowp vec4 col;
uniform highp mat4 mvp_matrix;
void main() {
    col = vec4(a_color, 1.);
    gl_Position = mvp_matrix * vec4(a_position, 1.);
    gl_PointSize = 10.0;
}
'''

    fragmentShaderSource = '''
#version 330
in lowp vec4 col;
out vec4 color;
void main() {
    color = col;
}
'''

    attribute_definitions = [
        ('a_position', np.float32, 2),
        ('a_color', np.float32, 3)]

class Scene(object):
    def __init__(self):
        self.painters = []
        self._bbox = None
        self.is_initialised = False
        self.is_changed = False

    @property
    def bbox(self):
        return self._bbox

    @bbox.setter
    def bbox(self, value):
        self._bbox=value
        self.is_changed = True

    def initialise(self):
        self._initialise()
        self.is_initialised = True
        
class BasicScene(Scene):
    def __init__(self):
        super(BasicScene, self).__init__()
        self.sources = []
        self.shader = Shader()

    def addSource(self, data, draw_type='points'):
        self.sources.append((draw_type, data))
        self.bbox = BBox(data['a_position'])
    
    def _initialise(self):
        self.m_program = ShaderProgram()
        self.m_program.addShader('vertex',
                self.shader.vertexShaderSource)
        self.m_program.addShader('fragment',
                self.shader.fragmentShaderSource)
        self.m_program.link()

        for draw_type, data in self.sources:
            self.painters.append(Painter(self.m_program, draw_type, Buffer(data)))