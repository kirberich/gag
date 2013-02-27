import math
import pygame
import cairo
import numpy
import Image
import random
import copy

class Gui(object):
    def __init__(self, width = 640, height = 480, caption = "DisplayTest", textureDirectory = "textures"):
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
        self.screen = screen
        self.textureDirectory = textureDirectory
        self.width = width
        self.height = height
        self.clock = pygame.time.Clock()

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