from OpenGL import GL as gl
import numpy as np
import ctypes

from .util import BBox

DRAW_TYPES = {'points':gl.GL_POINTS, 'lines':gl.GL_LINES, 'triangles':gl.GL_TRIANGLES, 'line_strip':gl.GL_LINE_STRIP, 'line_loop':gl.GL_LINE_LOOP}
SHADER_TYPES = { 'vertex':gl.GL_VERTEX_SHADER, 'fragment':gl.GL_FRAGMENT_SHADER }

class ShaderProgram(object):
    def __init__(self):
        self.uniform_names = []
        self.attribute_names = []
        # self.shader_sources = []
        self.uniforms = {}
        self.shaders = []
        self.is_bound = False
        self.is_initialised = False
        self.version = 0

    # def addShader(self, shader_type, shader_source):
    #     self.shader_sources.append((shader_type, shader_source))

    def compileShaders(self):
        def compileShader(handle, shader_source):
            gl.glShaderSource(handle, shader_source)
            gl.glCompileShader(handle)
            if not gl.glGetShaderiv(handle, gl.GL_COMPILE_STATUS):
                print(gl.glGetShaderInfoLog(handle))

        for shader_type, shader_source in [self.vertexShaderSource, self.fragmentShaderSource]:
            shader = gl.glCreateShader(SHADER_TYPES[shader_type])
            if shader==0:
                raise Exception('Failed to create shader')
            elif gl.glGetError()==gl.GL_INVALID_ENUM:
                raise Exception('Invalid shader type')
            compileShader(shader, shader_source)
            self.shaders.append(shader)

    def link(self):
        self.program = gl.glCreateProgram()

        for shader in self.shaders:
            gl.glAttachShader(self.program, shader)
        gl.glLinkProgram(self.program)

        if not gl.glGetProgramiv(self.program, gl.GL_LINK_STATUS):
            print(gl.glGetProgramInfoLog(self.program))

        for shader in self.shaders:
            gl.glDetachShader(self.program, shader)
        self.shaders = []

    def initialise(self):
        self.compileShaders()
        self.link()
        for name in self.uniform_names:
            self.uniforms[name] = self.uniformLocation(name)
        self.is_initialised = True

    def attributeLocation(self, attribute_name):
        loc = gl.glGetAttribLocation(self.program, attribute_name)
        if loc==-1: raise NameError("Invalid attribute name '{}'".format(attribute_name))
        return loc

    def uniformLocation(self, uniform_name):
        loc = gl.glGetUniformLocation(self.program, uniform_name)
        if loc==-1: raise NameError("Invalid uniform name '{}'".format(uniform_name))
        return loc

    def setUniformValue(self, uniform_name, value):
        uniform_location = self.uniforms[uniform_name]
        if not self.is_bound:
            gl.glUseProgram(self.program)
        if type(value) in [float, np.float64, np.float32]:
            gl.glUniform1f(uniform_location, np.float32(value))
        elif type(value) == np.ndarray and value.shape == (4,4):
            gl.glUniformMatrix4fv(uniform_location, 1, gl.GL_FALSE, np.float32(value))
        elif type(value) == np.ndarray and value.shape == (4,):
            gl.glUniform4f(uniform_location, np.float32(value[0]), np.float32(value[1]), np.float32(value[2]), np.float32(value[3]))
        else:
            import ipdb; ipdb.set_trace()
            raise NotImplementedError
        if not self.is_bound:
            gl.glUseProgram(0)

    def bind(self):
        gl.glUseProgram(self.program)
        self.is_bound = True

    def release(self):
        gl.glUseProgram(0)
        self.is_bound = False

    def delete(self):
        if self.is_initialised:
            gl.glDeleteProgram(self.program)
        self.uniforms = {}
        self.is_bound = False
        self.is_initialised = False

# class DataShaderProgram(ShaderProgram):
#     def __init__(self):
#         super(DataShaderProgram, self).__init__()
#         self.uniform_names = 

class ColorMap(object):
    def __init__(self):
        self.image = None
        self.width = 256
        self.is_initialised = False
        # if not scheme is None:
        #     self.setScheme(scheme)
        

    def bind(self):
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_1D, self.texture)

    def initialise(self):
        self.texture = gl.glGenTextures(1)
        self.bind()
        gl.glTexParameteri(gl.GL_TEXTURE_1D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)

        gl.glTexParameterf(gl.GL_TEXTURE_1D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameterf(gl.GL_TEXTURE_1D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        
        self.create()

        self.is_initialised = True

    def setWrapMode(self, mode):
        self.bind()
        if mode == 'repeat':
            gl.glTexParameteri(gl.GL_TEXTURE_1D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)
        elif mode == 'clamp_to_edge':
            gl.glTexParameteri(gl.GL_TEXTURE_1D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)

    # def setScheme(self, scheme):        
    #     if scheme == 'random':
    #         image = np.random.rand(self.width,3).astype(np.float32)
    #         image[0,:] = 1.
    #         # gl.glTexParameteri(gl.GL_TEXTURE_1D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT);
    #         # gl.glTexParameterf(gl.GL_TEXTURE_1D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
    #         # gl.glTexParameterf(gl.GL_TEXTURE_1D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST);
    #     elif scheme == 'validation':
    #         image = np.ones((self.width,3), dtype=np.float32)
    #         image[:128,:] = [1.,0.,0.]
    #         image[128:,:] = [0.,1.,0.]
    #     else:
    #         cmap = cm.get_cmap(scheme)
    #         image = cmap(np.arange(self.width))[:,:3].astype(np.float32)
    #     self.setImage((image*255).astype(np.ubyte))

    def setImage(self, image):
        """image should be a self.width x 3 sized color array"""
        # assert(image.dtype is np.ubyte)
        self.image = image#.astype(np.ubyte)
        if self.is_initialised:
            self.update()

    def create(self):
        self.bind()
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        gl.glTexImage1D(gl.GL_TEXTURE_1D, 0, gl.GL_RGB, self.width, 0, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, self.image)
        gl.glBindTexture(gl.GL_TEXTURE_1D, 0)

    def update(self):
        self.bind()
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        gl.glTexSubImage1D(gl.GL_TEXTURE_1D, 0, 0, self.width, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, self.image)
        gl.glBindTexture(gl.GL_TEXTURE_1D, 0)

    def delete(self):
        if self.is_initialised:
            gl.glDeleteTextures(1, gl.GLuint(self.texture))

class Buffer(object):
    def __init__(self, struct_array=None):
        self.data = struct_array
        self.len = None
        self.vertex_buffer = None

        self.is_initialised = False
        self.version = 0

    def initialise(self):
        if self.data is None:
            raise Exception("Can't initialise buffer without data'")
        self.vertex_buffer = gl.glGenBuffers(1)
        if gl.glGetError()==gl.GL_INVALID_ENUM:
            raise Exception('Failed to create buffer')
        self.create()
        self.is_initialised = True

    def setAttribute(self, key, value):
        self.data[key] = value
        self.update()

    def setData(self, struct_array):
        self.data = struct_array
        if self.is_initialised:
            self.create()
            self.version += 1

    def create(self):
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vertex_buffer)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, self.data.nbytes, self.data, gl.GL_DYNAMIC_DRAW)        
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        self.len = len(self.data)
        self.setDrawRange(0, self.len)

    def update(self):
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vertex_buffer)
        gl.glBufferSubData(gl.GL_ARRAY_BUFFER, 0, self.len, self.data)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)

    def setDrawRange(self, start, end):
        self.start = start
        self.end = end
    
    def update(self):
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vertex_buffer)
        gl.glBufferSubData(gl.GL_ARRAY_BUFFER, 0, self.data.nbytes, self.data)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)

    def delete(self):
        if self.is_initialised:
            gl.glDeleteBuffers(1, gl.GLuint(self.vertex_buffer))


class Painter(object):
    def __init__(self, shader_program, draw_type, buffer, colormap=None, is_visible=False):
        self.program = shader_program
        self.buffer = buffer
        self.buffer_version = None
        self.draw_type = draw_type
        self.draw_polywire = False
        self.colormap = colormap
        self.is_visible = is_visible
        self.is_initialised = False

    def initialise(self):
        self.vertex_array = gl.glGenVertexArrays(1)
        if gl.glGetError()==gl.GL_INVALID_ENUM:
            raise Exception('Failed to create vertex array')
        self.is_initialised = True

    def delete(self):
        if self.is_initialised:
            gl.glDeleteVertexArrays(1, gl.GLuint(self.vertex_array))

    def toggleVisibility(self):
        self.is_visible = not self.is_visible

    def setBuffer(self, buffer):
        self.buffer = buffer

    def setProgram(self, program):
        self.program = program

    def setColorMap(self, colormap):
        self.colormap = colormap

    def getBBox(self):
        return BBox(self.buffer.data['a_position'])

    def setAttribPointers(self):
        gl.glBindVertexArray(self.vertex_array)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffer.vertex_buffer)
        
        offset = 0
        for i, name in enumerate(self.buffer.data.dtype.names):
            stride = self.buffer.data[name].strides[0]
            if self.buffer.data[name].ndim == 1:
                size = 1
            else:
                size = self.buffer.data[name].shape[1]
            # import ipdb;ipdb.set_trace()
            if name in self.program.attribute_names:
                loc = self.program.attributeLocation(name)
                gl.glVertexAttribPointer(loc, size, gl.GL_FLOAT, False, stride, ctypes.c_void_p(offset))
                gl.glEnableVertexAttribArray(loc)
            offset += self.buffer.data.dtype[name].itemsize
        
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        gl.glBindVertexArray(0)
        self.buffer_version = self.buffer.version

    def render(self, view=None):
        if self.buffer:
            if not self.is_initialised:
                self.initialise()
            # Ensure program is properly initialised
            if not self.program.is_initialised:
                self.program.initialise()
            # Ensure buffer is properly initialised
            if not self.buffer.is_initialised:
                self.buffer.initialise()
            # see if buffer has been reset (eg it has a different size), if so we need to reset the AttribPointers
            if self.buffer_version!=self.buffer.version: # should prob also check for program version here, in case the program was rebuilt
                self.setAttribPointers()

            # Ensure colormap is properly initialised
            if self.colormap:
                if not self.colormap.is_initialised:
                    self.colormap.initialise()
                # self.colormap.bind()

            self.program.bind()

            if self.colormap:
                self.colormap.bind()

            if not view is None:
                self.program.setUniformValue('u_model', view.mat_model)
                self.program.setUniformValue('u_view', view.mat_view)
                self.program.setUniformValue('u_projection', view.mat_projection)
                if 'u_model_scale' in self.program.uniform_names:
                    self.program.setUniformValue('u_model_scale', view.v_scale)

            # assert(gl.glGetError() == gl.GL_NO_ERROR)
            gl.glBindVertexArray(self.vertex_array)
            # assert(gl.glGetError() == gl.GL_NO_ERROR)
            if self.draw_polywire:
                gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE)
            gl.glDrawArrays(DRAW_TYPES[self.draw_type], self.buffer.start, self.buffer.end)
            # assert(gl.glGetError() == gl.GL_NO_ERROR)
            if self.draw_polywire:
                gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)
            gl.glBindVertexArray(0)
            # assert(gl.glGetError() == gl.GL_NO_ERROR)
            self.program.release()
    
    def __repr__(self):
        return "Painter[{}] {}, {}, {}".format(id(self), self.buffer, self.program, self.colormap)

class Layer(object):
    def __init__(self):
        self.is_visible=True
        self.painters = []

    def setPainter(self, painter):
        if type(painter) is Painter:
            if not painter in self.painters:
                self.painters.append(painter)

    def unsetPainter(self, painter):
        if type(painter) is Painter:
            if painter in self.painters:
                self.painters.remove(painter)