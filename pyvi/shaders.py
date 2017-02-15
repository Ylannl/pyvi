import numpy as np
from .gloo import ShaderProgram

class PointShaderProgram(ShaderProgram):
    def __init__(self, **kwargs):

        self.options = {
            'color_mode': 'fixed', # or texture, color
            'draw_mode': 'oriented_disk', # 'oriented_disk', 'disk', 'simple', 
            'lightning': True,
            'point_size': 3.0,
            'color': [1.,1.,0.,1.]
        }
        super(PointShaderProgram, self).__init__()
        self.setOptions(**kwargs)

    def setOptions(self, **kwargs):
        self.options.update(kwargs)

        self.attribute_names = ['a_position']
        self.uniform_names = ['u_model', 'u_view', 'u_projection', 'u_point_size']
        
        self.s_defines = ""
        for key, value in self.options.items():
            if key == 'draw_mode':
                self.s_defines += "#define {}\n".format(key+'_'+value)
                if value in ['oriented_disk', 'disk']:
                    self.uniform_names += ['u_model_scale']
            elif key == 'color_mode':
                if value == 'fixed':
                    self.uniform_names += ['u_color']
                elif value == 'texture':
                    self.attribute_names += ['a_intensity']
                elif value == 'color':
                    self.attribute_names += ['a_color']
                self.s_defines += "#define {}\n".format(key+'_'+value)
            elif key == 'lightning':
                if value:
                    self.s_defines += "#define {}\n".format(key)

        if self.options['lightning'] or self.options['draw_mode'] == 'oriented_disk':
            self.attribute_names += ['a_normal']

    def initialise(self):
        ShaderProgram.initialise(self)
        self.setUniformValue('u_point_size', self.options['point_size'])
        if self.options['color_mode'] == 'fixed':
            self.setUniformValue('u_color', np.array(self.options['color'], dtype=np.float32))


    def rebuild(self, **kwargs):
        self.delete()
        self.setOptions(**kwargs)

    @property
    def vertexShaderSource(self):
        return 'vertex', """
        #version 330

        {defines}

        // Uniforms
        // ------------------------------------
        uniform highp mat4 u_model;
        uniform highp mat4 u_view;
        uniform highp mat4 u_projection;
        uniform float u_point_size;

        #if defined(draw_mode_oriented_disk) | defined(draw_mode_disk)
        uniform float u_model_scale;
        #endif

        #if defined(color_mode_fixed)
        uniform lowp vec4 u_color;
        #endif

        // Attributes
        // ------------------------------------
        in vec3 a_position;
        #if defined(lightning) | defined(draw_mode_oriented_disk)
        in vec3 a_normal;
        #endif
        #if defined(color_mode_texture)
        in float a_intensity;
        #elif defined(color_mode_color)
        in lowp vec4 a_color;
        #endif

        // Varyings
        // ------------------------------------
        #if defined(color_mode_texture)
        out float v_color_intensity;
        #elif defined(color_mode_fixed) | defined(color_mode_color)
        out vec4 vcolor;
        #endif
        out float v_lightpwr;
        #if defined(draw_mode_oriented_disk)
            out vec4 v_normal;
        #endif

        

        void main (void) {{
            vec4 posEye = u_view * u_model * vec4(a_position, 1.0);    
            gl_Position = u_projection * posEye;

            //# if defined(with_point_radius)
            //    float scale = u_model_scale*a_splat_radius;
            #if defined(draw_mode_oriented_disk) | defined(draw_mode_disk)
                float scale = u_model_scale;
            #endif
            
            #if defined(draw_mode_oriented_disk) | defined(draw_mode_disk)
                vec4 projCorner = u_projection * vec4(scale, scale, posEye.z, posEye.w);
                float s = 2.0 * u_point_size / projCorner.w;
                gl_PointSize = projCorner.x * s;
            #else
                gl_PointSize = u_point_size;
            #endif
            //gl_PointSize = 0.0;
            
            #if defined(color_mode_texture)
                v_color_intensity = a_intensity;
            #endif

            #if defined(lightning) | defined(draw_mode_oriented_disk)
                vec4 n = u_view * u_model * vec4(a_normal, 0);
                n = normalize(n);
            #endif
            #if defined(lightning)
                vec4 lighting_direction_1 = vec4(1,1,1,0);
                vec4 lighting_direction_2 = vec4(0,0.5,1,0);
                float L = dot(n, normalize(lighting_direction_1)) + dot(n, normalize(lighting_direction_2));
                v_lightpwr = clamp(abs(L), 0.3, 1);
            #else
                v_lightpwr = 1.0;
            #endif
            #if defined(color_mode_fixed)
                vcolor = u_color;
            #elif defined(color_mode_color)
                vcolor = a_color;
            #endif
            #if defined(draw_mode_oriented_disk)
                v_normal = n;
            #endif
        }}
        """.format(defines=self.s_defines)

    @property
    def fragmentShaderSource(self):
        return 'fragment', """
        #version 330

        {defines}

        #if defined(color_mode_texture)
        uniform sampler1D u_colormap;
        in float v_color_intensity;
        #endif
        #if defined(color_mode_fixed) | defined(color_mode_color)
        in vec4 vcolor;
        #endif

        in float v_lightpwr;
        #if defined(draw_mode_oriented_disk)
            in vec4 v_normal;
        #endif

        out vec4 color;

        // Main
        // ------------------------------------
        void main()
        {{
            float x = gl_PointCoord.x - 0.5;
            float y = gl_PointCoord.y - 0.5;

            
            #if defined(draw_mode_oriented_disk)
                float dz = -(v_normal.x/v_normal.z)*x + (v_normal.y/v_normal.z)*y;
            #elif defined(draw_mode_disk)
                float dz = 0;
            #endif

            float alpha = 1.;
            #if defined(draw_mode_oriented_disk) | defined(draw_mode_disk)
                float r = length(vec3(x,y,dz));
                if (r > 0.5) {{
                    discard;
                }}
            #endif

            float c = 1.0 - (pow(2*x,2.0) + pow(2*x,2.0));
            //color =  vec4(color_scheme(v_color_intensity), alpha);
            //#else if defined(with_texture)
            #if defined(color_mode_texture)
                color =  vec4(v_lightpwr, v_lightpwr, v_lightpwr, 1.0)*texture(u_colormap, v_color_intensity);
            #else
                color =  vec4(v_lightpwr, v_lightpwr, v_lightpwr, 1.0)*vcolor;
            #endif
            gl_FragDepth = gl_FragCoord.z + 0.002*(1.0-pow(c, 1.0)) * gl_FragCoord.w;
            
        }}
        """.format(defines=self.s_defines)

class LineShaderProgram(ShaderProgram):

    def __init__(self, **kwargs):

        self.options = {
            'color_mode': 'fixed', # or texture
            'alternate_vcolor': True,
            'color': [1.,1.,0.,1.]
        }
        super(LineShaderProgram, self).__init__()
        self.setOptions(**kwargs)
        
    def setOptions(self, **kwargs):
        self.options.update(kwargs)

        self.attribute_names = ['a_position']
        self.uniform_names = ['u_model', 'u_view', 'u_projection']
        
        self.s_defines = ""
        for key, value in self.options.items():
            if key == 'color_mode':
                self.s_defines += "#define {}\n".format(key+'_'+value)
                if value == 'fixed':
                    self.uniform_names += ['u_color']
                elif value == 'texture':
                    self.attribute_names += ['a_intensity']
            elif key == 'alternate_vcolor':
                if value:
                    self.s_defines += "#define {}\n".format(key)

    def initialise(self):
        ShaderProgram.initialise(self)
        if self.options['color_mode'] == 'fixed':
            self.setUniformValue('u_color', np.array(self.options['color'], dtype=np.float32))

    def rebuild(self, **kwargs):
        self.delete()
        self.setOptions(**kwargs)

    @property
    def vertexShaderSource(self):
        return 'vertex', """
        #version 330

        {s_defines}

        // Uniforms
        // ------------------------------------
        uniform mat4 u_model;
        uniform mat4 u_view;
        uniform mat4 u_projection;
        
        #if defined(color_mode_fixed)
        uniform vec4 u_color;
        #endif

        // Attributes
        // ------------------------------------
        in vec3 a_position;

        #if defined(color_mode_fixed)
        out vec4 vcolor;
        #endif
        #if defined(color_mode_texture)
        in float a_intensity;
        out float v_intensity;
        #endif

        void main (void) {{
            #if defined(color_mode_fixed)
            vcolor = u_color;
            #if defined(alternate_vcolor)
            if (gl_VertexID%2==0) {{
                vcolor = vec4(1,1,1, 1);
            }}
            #endif
            #endif

            #if defined(color_mode_texture)
            v_intensity = a_intensity;
            #endif
            
            gl_Position = u_projection * u_view * u_model * vec4(a_position, 1.0);    
        }}
        """.format(s_defines=self.s_defines)

    @property
    def fragmentShaderSource(self):
        return 'fragment',"""
        #version 330

        {s_defines}

        #if defined(color_mode_fixed)
        in vec4 vcolor;
        #elif defined(color_mode_texture)
        uniform sampler1D u_colormap;
        in float v_intensity;
        #endif
        out vec4 color;

        void main()
        {{
            #if defined(color_mode_fixed)
            color =  vcolor;
            #endif
            #if defined(color_mode_texture)
            color = texture(u_colormap, v_intensity);
            #endif
        }}
        """.format(s_defines=self.s_defines)