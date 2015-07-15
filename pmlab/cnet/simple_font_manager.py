import pygame
from pygame.locals import *
 
class cFontManager:
    '''
    A simple class used to manage Font objects and provide a simple way to use
    them to draw text on any surface.
 
    Directly import this file to use the class, or run this file from the
    command line to see a trivial sample.
 
    Written by Scott O. Nelson  
    '''
    def __init__(self, listOfFontNamesAndSizesAsTuple):
        '''
        Pass in a tuple of 2-item tuples.  Each 2-item tuple is a fontname / 
        size pair. To use the default font, pass in a None for the font name.
        Font objects are created for each of the pairs and can then be used
        to draw text with the Draw() method below.
        
        Ex: fontMgr = cFontManager(((None, 24), ('arial', 18), ('arial', 24),
            ('courier', 12), ('papyrus', 50)))
 
        TODO: add support for bold & italics
        '''
        self._fontDict = {}
        for pair in listOfFontNamesAndSizesAsTuple:
            assert len(pair) == 2, \
                "Pair must be composed of a font name and a size - ('arial', 24)"
            if pair[0]:
                fontFullFileName = pygame.font.match_font(pair[0])
                assert fontFullFileName, \
                    'Font: %s Size: %d is not available.' % pair
            else:
                fontFullFileName = None # use default font
            self._fontDict[pair] = pygame.font.Font(fontFullFileName, pair[1])
 
    def Draw(self, surface, fontName, size, text, rectOrPosToDrawTo, color,
            alignHoriz='left', alignVert='top', antialias=False):
        '''
        Draw text with the given parameters on the given surface.
        
        surface - Surface to draw the text onto.
        
        fontName - Font name that identifies what font to use to draw the text.
        This font name must have been specified in the cFontManager 
        
        rectOrPosToDrawTo - Where to render the text at.  This can be a 2
        item tuple or a Rect.  If a position tuple is used, the align
        arguments will be ignored.
        
        color - Color to draw the text with.
        
        alignHoriz - Specifies horizontal alignment of the text in the
        rectOrPosToDrawTo Rect.  If rectOrPosToDrawTo is not a Rect, the
        alignment is ignored.
        
        alignVert - Specifies vertical alignment of the text in the
        rectOrPosToDrawTo Rect.  If rectOrPosToDrawTo is not a Rect, the
        alignment is ignored.
 
        antialias - Whether to draw the text anti-aliased or not.
        '''
        pair = (fontName, size)
        assert pair in self._fontDict, \
            'Font: %s Size: %d is not available in cFontManager.' % pair
        fontSurface = self._fontDict[(fontName, size)].render(text,
            antialias, color)
        if isinstance(rectOrPosToDrawTo, tuple):
            surface.blit(fontSurface, rectOrPosToDrawTo)
        elif isinstance(rectOrPosToDrawTo, pygame.Rect):
            fontRect = fontSurface.get_rect()
            # align horiz
            if alignHoriz == 'center':
                fontRect.centerx = rectOrPosToDrawTo.centerx
            elif alignHoriz == 'right':
                fontRect.right = rectOrPosToDrawTo.right
            else:
                fontRect.x = rectOrPosToDrawTo.x  # left
            # align vert
            if alignVert == 'center':
                fontRect.centery = rectOrPosToDrawTo.centery
            elif alignVert == 'bottom':
                fontRect.bottom = rectOrPosToDrawTo.bottom
            else:
                fontRect.y = rectOrPosToDrawTo.y  # top
                
            surface.blit(fontSurface, fontRect)
 
def RunDemo():
    '''A simple demo of the use of the cFontManager class'''
    pygame.init()     
    pygame.display.set_mode((640, 480))
    screen = pygame.display.get_surface()
    clock = pygame.time.Clock()
 
    # a font of None means to use the default font
    fontMgr = cFontManager(((None, 24), (None, 48), ('arial', 24)))
    
    doQuit = False
    while not doQuit:
        clock.tick(60) # run at 60 fps
        screen.fill((0, 0, 0))
 
        white = (255, 255, 255)
        gray = (64, 64, 64)
        fontMgr.Draw(screen, None, 48, 'Default font, 48', (0, 50), white)
        fontMgr.Draw(screen, None, 24, 'Default font, 24', (0, 0), white)
 
        rect = pygame.Rect(0, 100, 640, 60)
        pygame.draw.rect(screen, gray, rect)        
        fontMgr.Draw(screen, 'arial', 24, 'Arial 24 top left', rect, white,
            'left', 'top')
        rect.top += 75
        
        pygame.draw.rect(screen, gray, rect)        
        fontMgr.Draw(screen, 'arial', 24, 'Arial 24 centered', rect, white,
            'center', 'center')
        rect.top += 75
 
        pygame.draw.rect(screen, gray, rect)        
        fontMgr.Draw(screen, 'arial', 24, 'Arial 24 bottom right', rect,
            white, 'right', 'bottom')
        rect.top += 75
 
        pygame.draw.rect(screen, gray, rect)        
        fontMgr.Draw(screen, 'arial', 24, 'Arial 24 left center, anti-aliased',
            rect, white, 'left', 'center', True)
        rect.top += 75
        
        pygame.display.update()
        if QUIT in [event.type for event in pygame.event.get()]:
            doQuit = True
    pygame.quit()
 
if __name__ == '__main__':
    # Execute the demo code if this file is run directly from the command line.
    # Do not run demo if file is imported.
    RunDemo()
