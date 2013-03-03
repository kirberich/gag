import math
import pygame
import cairo
import numpy
import Image
import random
import copy

class Color(object):
    def __init__(self, r = 1, g = 1, b = 1, a = 1):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def replace(self, r = None, g = None, b = None, a = None):
        """ Returns a copy of the color with all supplied values replaced. """
        if not r: r = self.r 
        if not g: g = self.g 
        if not b: b = self.b 
        if not a: a = self.a
        return Color(r,g,b,a)

    def __repr__(self):
        return 'Color object: (%s,%s,%s,%s)' % (self.r, self.g, self.b, self.a)

class Gui(object):
    def __init__(self, width = 640, height = 480, caption = "DisplayTest", textureDirectory = "textures", virtual_width = None, virtual_height = None):
        """ Initialize a pygame window. This is only for early testing, there probably won't be a gui later. """
        pygame.init()
        screen = pygame.display.set_mode((width,height))
        pygame.display.set_caption(caption)
        
        background = pygame.Surface(screen.get_size())
        background.fill((255, 255, 255))
        
        screen.blit(background, (0, 0))
        pygame.display.flip()

        data = numpy.empty(width * height * 4, dtype=numpy.int8)

        self.cairo_surface = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, width, height, width * 4)
        self.cairo_context = cairo.Context(self.cairo_surface)  
        self.cairo_context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
        self.cairo_context.set_line_width(0.01)

        self.screen = screen
        self.textureDirectory = textureDirectory
        self.width = width
        self.height = height
        self.clock = pygame.time.Clock()

        # Set virtual resolution for pixel stuff
        self.virtual_width = width 
        self.virtual_height = height 
        self.pixel_width = 1
        self.pixel_height = 1

        if virtual_width and virtual_width < width:
            self.virtual_width = virtual_width
            self.pixel_width = width / virtual_width
        if virtual_height and virtual_height < height:
            self.virtual_height = virtual_height
            self.pixel_height = height / virtual_height

    def fill(self, color):
        """ Fill the entire surface with one color """
        self.set_color(color)
        self.cairo_context.paint()

    def draw_circle(self, center, radius, fill_color = None, stroke_color = None):
        """ Draw a circle at center, with a given radius and optional fill_color and stroke_color """
        (x, y) = center
        self.cairo_context.arc(x, y, radius, 0, 2 * math.pi)
        self.apply_colors(fill_color, stroke_color)
        self.cairo_context.close_path()

    def draw_rect(self, x, y, width, height, fill_color = None, stroke_color = None):
        """ Draw a rectangle with its upper left corner at x,y, size of width,height and optional fill_color and stroke_color """
        self.cairo_context.rectangle(x, y, width, height)
        self.apply_colors(fill_color, stroke_color)
        self.cairo_context.close_path()

    def draw_pixel(self, x, y, color = None):
        """ Draw a virtual pixel. The size of the pixel is determined by Gui.virtual_width and Gui.virtual_height """
        self.cairo_context.rectangle(x * self.pixel_width, y * self.pixel_height, self.pixel_width, self.pixel_height)        
        if color: self.set_color(color)
        self.cairo_context.fill()
        self.cairo_context.new_path()

    def draw_pixels(self, pixels):
        for pixel in pixels:
            self.draw_pixel(*pixel)

    def draw_polygon(self, coordinates, fill_color = None, stroke_color = None):
        """ Draw an n-sided polygon """
        if len(coordinates) < 3: raise Exception("Polygons need to have at least three points")
        self.cairo_context.move_to( coordinates[0][0], coordinates[0][1] )
        for (x,y) in coordinates[1:]:
            self.cairo_context.line_to(x,y)
        self.apply_colors(fill_color, stroke_color)

    def draw_text(self, x, y, text, fill_color = None, stroke_color = None):
        self.cairo_context.move_to(x,y)
        self.cairo_context.text_path(text)
        self.apply_colors(fill_color, stroke_color)

    def apply_colors(self, fill_color, stroke_color):
        """ Apply fill and stroke colors to the current path """
        if fill_color:
            self.set_color(fill_color)
            self.cairo_context.fill_preserve()
        if stroke_color:
            self.set_color(stroke_color)
            self.cairo_context.stroke()

        self.cairo_context.new_path()

    def set_color(self, color):
        self.cairo_context.set_source_rgba(color.r, color.g, color.b, color.a)

    def rotate(self, angle):
        """ Rotates the transformation matrix, this only has an effect on 
            newly drawn things and is kind of useless.
        """
        self.cairo_context.rotate(angle)

    def reverse_rotate(self, angle):
        self.rotate(-angle)

    def scale(self, amount=1):
        self.cairo_context.scale(amount, amount)

    def reverse_scale(self, amount=1):
        self.scale(1.0 / amount)

    def translate(self, x, y):
        self.cairo_context.translate(x, y)

    def reverse_translate(self, x, y):
        self.translate(-x, -y)

    def transform(self, translate_x = 0, translate_y = 0, scale = 1):
        self.translate(translate_x, translate_y)
        self.scale(scale)

    def reverse_transform(self, translate_x = 0, translate_y = 0, scale = 1):
        self.cairo_context.scale(1.0 / scale, 1.0 / scale)
        self.cairo_context.translate(translate_x * -1, translate_y * -1)

    def from_degrees(self, degrees):
        return degrees * math.pi / 180.0

    def cairo_drawing_test(self):
        """ Just a cairo test """ 
        # Reset background
        self.cairo_context.set_source_rgba(1, 1, 1, 1)
        self.cairo_context.paint()

        self.cairo_context.set_line_width(100)
        self.cairo_context.arc(320, 240, 200, 0, 1.9 * math.pi)
     
        self.cairo_context.set_source_rgba(1, 0, 0, random.random())
        self.cairo_context.fill_preserve()
     
        self.cairo_context.set_source_rgba(0, 1, 0, 0.5)
        self.cairo_context.stroke()

    def _bgra_surf_to_rgba_string(self):
        img = Image.frombuffer(
            'RGBA', (self.cairo_surface.get_width(),
                     self.cairo_surface.get_height()),
            self.cairo_surface.get_data(), 'raw', 'BGRA', 0, 1)
     
        return img.tostring('raw', 'RGBA', 0, 1)

    def update(self):
        data_string = self._bgra_surf_to_rgba_string()
        pygame_surface = pygame.image.frombuffer(data_string, (self.width, self.height), 'RGBA')

        self.screen.blit(pygame_surface, (0,0)) 
        pygame.display.flip()