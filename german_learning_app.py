import tkinter as tk
from tkinter import StringVar
from tkinter import ttk, messagebox
import random
from PIL import Image, ImageTk
from PIL import Image, ImageDraw
import os
from io import BytesIO
import requests
import sys
from functools import partial
import math
from PIL import ImageFont

class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        # Create a canvas and scrollbar
        self.canvas = tk.Canvas(self, borderwidth=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        # Configure the canvas
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # Bind mouse wheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Create window inside canvas
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Configure canvas to expand with window
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        # Pack the scrollbar and canvas
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
    def _on_canvas_configure(self, event):
        # Update the width of the canvas window when the canvas is resized
        self.canvas.itemconfig(self.canvas_frame, width=event.width)
        
class GermanLearningApp:
    def __init__(self, root):
        self.root = root
        self.root.title("German Learning App")
        self.root.geometry("1200x1000")
        
        # Create main container frame
        main_container = ttk.Frame(root)
        main_container.pack(expand=True, fill='both')
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(pady=10, expand=True, fill='both')
        
        # Create scrollable frames for each tab
        self.alphabet_tab = ScrollableFrame(self.notebook)
        self.greetings_tab = ScrollableFrame(self.notebook)
        self.book_tab = ScrollableFrame(self.notebook)
        self.sit_stand_tab = ScrollableFrame(self.notebook)
        self.matching_tab = ScrollableFrame(self.notebook)
        self.letter_completion_tab = ScrollableFrame(self.notebook)
        self.quiz_tab = ScrollableFrame(self.notebook)
        self.write_tab = ScrollableFrame(self.notebook)
        
        # Add tabs to notebook
        self.notebook.add(self.alphabet_tab, text="Alphabet")
        self.notebook.add(self.greetings_tab, text="Greetings")
        self.notebook.add(self.book_tab, text="Book Commands")
        self.notebook.add(self.sit_stand_tab, text="Sit/Stand")
        self.notebook.add(self.matching_tab, text="Matching Exercise")
        self.notebook.add(self.letter_completion_tab, text="Letter Completion")
        self.notebook.add(self.quiz_tab, text="Quiz")
        self.notebook.add(self.write_tab, text="Write Down")
        
        # Initialize data
        self.init_data()
        self.create_alphabet_images()  # This will create all our images
        
        # Setup all tabs
        self.setup_alphabet_tab()
        self.setup_greetings_tab()
        self.setup_book_tab()
        self.setup_sit_stand_tab()
        self.setup_matching_tab()
        self.setup_letter_completion_tab()
        self.setup_styles()
        self.setup_quiz_tab()
        self.setup_write_tab()

        # Add footer with greeting
        footer_frame = ttk.Frame(main_container)
        footer_frame.pack(fill='x', pady=5)
        
        footer_label = ttk.Label(
            footer_frame, 
            text="To my lovely boy ADAM ❤️", 
            font=('Arial', 10, 'italic')
        )
        footer_label.pack(side='right', padx=10)

    def create_alphabet_images(self):
        """Create simple images for each letter using PIL"""
        self.alphabet_images = {}
        
        # Define some basic colors
        colors = {
            'red': (255, 0, 0),
            'green': (0, 155, 0),
            'blue': (0, 0, 255),
            'brown': (139, 69, 19),
            'gray': (128, 128, 128),
            'yellow': (255, 255, 0),
            'white': (255, 255, 255),
            'black': (0, 0, 0),
            'orange': (255, 165, 0),
            'darkgray': (169, 169, 169),  # Added missing color
            'pink': (255, 192, 203),     # For cake frosting
            'navy': (0, 0, 128),         # For night backgrounds
            'lightgray': (211, 211, 211),# For needle eye
            'silver': (192, 192, 192),   # Metallic colors
            'lightblue': (173, 216, 230),# For water scenes
            'darkblue': (0, 0, 139),      # For deep water
            'purple': (128, 0, 128),
            'gold': (255, 215, 0),
            'lightyellow': (255, 255, 204),
            'beige': (245, 245, 220),
            'skyblue': (135, 206, 235),
            'skyblue': (135, 206, 235),
            'darkgreen': (0, 100, 0),
            'cyan': (0, 255, 255),
            'teal': (0, 128, 128),
            'maroon': (128, 0, 0)
        }
        
        # Helper function for consistent image creation
        def create_image(size=(120, 120), color='white'):
            """Improved base image creation with anti-aliasing support"""
            img = Image.new('RGB', size, color)
            draw = ImageDraw.Draw(img)
            return img, draw


        def draw_spiral(draw, cx, cy, radius, **kwargs):
            """Helper function to draw a spiral"""
            points = []
            steps = 30
            rotations = 2
            for i in range(steps * rotations):
                angle = math.radians(i * 360/steps)
                r = radius * i/(steps * rotations)
                x = cx + r * math.cos(angle)
                y = cy + r * math.sin(angle)
                points.append((x, y))
            for i in range(1, len(points)):
                draw.line([points[i-1], points[i]], **kwargs)

               
        # Create Jaguar
        img, draw = create_image()
        draw.ellipse([20, 40, 80, 80], fill=colors['orange'])        # body
        draw.ellipse([60, 30, 90, 50], fill=colors['orange'])        # head
        for _ in range(20):                                          # spots
            x = random.randint(25, 75)
            y = random.randint(40, 70)
            draw.ellipse([x, y, x+5, y+5], fill=colors['black'])
        self.alphabet_images['Jaguar'] = ImageTk.PhotoImage(img)

         # J: Jacke (jacket)
        img, draw = create_image()
        draw.polygon([30,20, 70,20, 80,80, 20,80], fill=colors['blue'])
        draw.line([50,20, 50,80], fill=colors['black'], width=3)
        draw.rectangle([40,40, 60,60], fill=colors['silver'])  # zipper
        self.alphabet_images['Jacke'] = ImageTk.PhotoImage(img)

        # K: Kirsche (cherry)
        img, draw = create_image()
        draw.ellipse([40,30, 60,50], fill=colors['red'])  # cherry
        draw.line([50,50, 50,70], fill=colors['green'], width=2)  # stem
        self.alphabet_images['Kirsche'] = ImageTk.PhotoImage(img)

        # J: Juwel (jewel)
        img, draw = create_image()
        draw.polygon([50,20, 70,40, 50,60, 30,40], fill=colors['purple'])
        draw.line([50,20, 30,40], fill=colors['gold'], width=2)
        draw.line([50,20, 70,40], fill=colors['gold'], width=2)
        self.alphabet_images['Juwel'] = ImageTk.PhotoImage(img)

        # K: Kamel (camel)
        img, draw = create_image()
        draw.polygon([30,60, 50,40, 70,60], fill=colors['brown'])  # body
        draw.polygon([70,60, 90,50, 85,70], fill=colors['brown'])  # neck
        draw.ellipse([80,40, 100,60], fill=colors['brown'])        # head
        for i in range(2):  # humps
            draw.ellipse([40+i*20, 30, 60+i*20, 50], fill=colors['brown'])
        self.alphabet_images['Kamel'] = ImageTk.PhotoImage(img)

        # L: Lupe (magnifier)
        img, draw = create_image()
        draw.ellipse([30,30, 90,90], outline=colors['black'], width=3)  # lens
        draw.rectangle([70,20, 80,30], fill=colors['brown'])            # handle
        self.alphabet_images['Lupe'] = ImageTk.PhotoImage(img)

        # M: Milch (milk)
        img, draw = create_image()
        draw.rectangle([40,30, 80,80], fill=colors['white'])
        draw.polygon([40,30, 50,20, 80,30], fill=colors['lightyellow'])
        self.alphabet_images['Milch'] = ImageTk.PhotoImage(img)

        # N: Nase (nose)
        img, draw = create_image()
        draw.arc([40,40, 80,80], 180, 360, fill=colors['beige'], width=5)
        draw.line([60,60, 60,70], fill=colors['black'], width=2)  # septum
        self.alphabet_images['Nase'] = ImageTk.PhotoImage(img)

        # O: Ohr (ear)
        img, draw = create_image()
        draw.polygon([30,40, 70,30, 50,80], fill=colors['beige'])
        draw.line([40,50, 60,60], fill=colors['brown'], width=2)  # inner ear
        self.alphabet_images['Ohr'] = ImageTk.PhotoImage(img)

        # P: Papagei (parrot)
        img, draw = create_image()
        draw.polygon([40,40, 60,20, 80,40], fill=colors['green'])  # body
        draw.polygon([60,20, 80,10, 70,30], fill=colors['red'])    # head
        self.alphabet_images['Papagei'] = ImageTk.PhotoImage(img)

        # Q: Quark (curd)
        img, draw = create_image()
        draw.ellipse([30,30, 90,90], fill=colors['white'])
        for _ in range(20):  # curd texture
            x = random.randint(35, 85)
            y = random.randint(35, 85)
            draw.ellipse([x,y, x+3,y+3], fill=colors['lightyellow'])
        self.alphabet_images['Quark'] = ImageTk.PhotoImage(img)

        # R: Robbe (seal)
        img, draw = create_image()
        draw.ellipse([30,40, 90,80], fill=colors['gray'])        # body
        draw.polygon([80,60, 100,50, 90,70], fill=colors['gray'])  # head
        self.alphabet_images['Robbe'] = ImageTk.PhotoImage(img)

        # S: Schuh (shoe)
        img, draw = create_image()
        draw.polygon([30,60, 70,60, 80,80, 20,80], fill=colors['brown'])
        draw.line([50,50, 50,70], fill=colors['black'], width=2)  # lace
        self.alphabet_images['Schuh'] = ImageTk.PhotoImage(img)

        # T: Tisch (table)
        img, draw = create_image()
        draw.rectangle([20,60, 80,70], fill=colors['brown'])  # top
        draw.rectangle([35,70, 45,80], fill=colors['brown'])  # leg
        draw.rectangle([65,70, 75,80], fill=colors['brown'])  # leg
        self.alphabet_images['Tisch'] = ImageTk.PhotoImage(img)

        # U: Universum (universe)
        img, draw = create_image(color='black')
        # Draw stars
        for _ in range(50):
            x = random.randint(10, 110)
            y = random.randint(10, 110)
            draw.ellipse([x, y, x+2, y+2], fill=colors['white'])
        # Draw spiral galaxy using helper function
        draw_spiral(draw, 50, 50, 30, fill=colors['purple'], width=2)
        self.alphabet_images['Universum'] = ImageTk.PhotoImage(img)
    
        # V: Vulkan (volcano)
        img, draw = create_image()
        draw.polygon([30,80, 70,30, 110,80], fill=colors['brown'])
        draw.ellipse([60,20, 80,40], fill=colors['red'])  # lava
        self.alphabet_images['Vulkan'] = ImageTk.PhotoImage(img)

        # W: Wurm (worm)
        img, draw = create_image()
        for i in range(5):  # segmented body
            draw.ellipse([20+i*15,40, 35+i*15,55], fill=colors['pink'])
        self.alphabet_images['Wurm'] = ImageTk.PhotoImage(img)

        # X: Xerox (photocopy)
        img, draw = create_image()
        draw.rectangle([30,30, 90,90], fill=colors['white'])
        draw.text((40,50), "X", fill=colors['black'], 
                font=ImageFont.truetype("Arial", 40))
        self.alphabet_images['Xerox'] = ImageTk.PhotoImage(img)

        # Y: Yoga
        img, draw = create_image()
        draw.ellipse([40,30, 80,70], fill=colors['beige'])  # body
        draw.line([60,50, 60,80], fill=colors['beige'], width=10)  # legs
        draw.line([60,50, 40,30], fill=colors['beige'], width=10)  # arms
        self.alphabet_images['Yoga'] = ImageTk.PhotoImage(img)

        # Z: Zug (train)
        img, draw = create_image()
        draw.rectangle([20,50, 80,60], fill=colors['red'])  # body
        draw.ellipse([25,70, 45,90], fill=colors['black'])  # wheels
        draw.ellipse([65,70, 85,90], fill=colors['black'])
        self.alphabet_images['Zug'] = ImageTk.PhotoImage(img)
            

        # M: Mütze (hat)
        img, draw = create_image()
        draw.ellipse([30,50, 70,70], fill=colors['gray'])  # brim
        draw.rectangle([40,30, 60,50], fill=colors['blue'])  # crown
        self.alphabet_images['Mütze'] = ImageTk.PhotoImage(img)

        # Create Jacket
        img, draw = create_image()
        draw.polygon([30,20, 70,20, 80,80, 20,80], fill=colors['blue'])  # jacket body
        draw.line([50,20, 50,80], fill=colors['black'], width=3)         # zipper
        self.alphabet_images['Jacke'] = ImageTk.PhotoImage(img)

        # Create Katze (cat)
        img, draw = create_image()
        draw.ellipse([30, 40, 70, 80], fill=colors['gray'])          # body
        draw.polygon([45,30, 55,30, 50,15], fill=colors['gray'])     # ears
        draw.line([40,70, 20,80], fill=colors['gray'], width=3)      # tail
        self.alphabet_images['Katze'] = ImageTk.PhotoImage(img)

        # Create Xylophon
        img, draw = create_image()
        for i, c in enumerate(['red','orange','yellow','green']):
            draw.rectangle([20+i*15,40, 30+i*15,80], fill=c)
        self.alphabet_images['Xylophon'] = ImageTk.PhotoImage(img)

        # Create Zebra
        img, draw = create_image()
        draw.ellipse([30, 40, 70, 80], fill=colors['white'])         # body
        for _ in range(15):                                          # stripes
            x = random.randint(30,70)
            y = random.randint(40,80)
            draw.line([x,y, x+10,y+10], fill=colors['black'], width=3)
        self.alphabet_images['Zebra'] = ImageTk.PhotoImage(img)

        # Create Cafe
        img, draw = create_image()
        draw.rectangle([20, 40, 80, 80], fill=colors['brown'])  # building
        draw.rectangle([35, 50, 65, 65], fill=colors['white'])  # window
        draw.ellipse([40, 20, 60, 40], fill=colors['gray'])    # coffee steam
        self.alphabet_images['Café'] = ImageTk.PhotoImage(img)

        # Create Boss (Chef)
        img, draw = create_image()
        draw.ellipse([35, 10, 65, 40], fill=colors['gray'])    # head
        draw.rectangle([40, 40, 60, 80], fill=colors['black'])  # suit
        draw.rectangle([30, 15, 70, 25], fill=colors['black'])  # hat
        self.alphabet_images['Chef'] = ImageTk.PhotoImage(img)

        # Create Duck (Ente)
        img, draw = create_image()
        draw.ellipse([30, 40, 70, 70], fill=colors['yellow'])    # body
        draw.ellipse([60, 30, 80, 50], fill=colors['yellow'])    # head
        draw.polygon([75, 35, 90, 40, 75, 45], fill=colors['orange'])  # beak
        self.alphabet_images['Ente'] = ImageTk.PhotoImage(img)

        # Create Elephant (Elefant)
        img, draw = create_image()
        draw.ellipse([20, 30, 70, 80], fill=colors['gray'])      # body
        draw.polygon([60, 40, 80, 50, 60, 60], fill=colors['gray'])  # trunk
        self.alphabet_images['Elefant'] = ImageTk.PhotoImage(img)

        # Create Fish (Fisch)
        img, draw = create_image()
        draw.polygon([20, 50, 60, 20, 60, 80], fill=colors['blue'])   # body
        draw.polygon([60, 30, 80, 50, 60, 70], fill=colors['blue'])   # tail
        self.alphabet_images['Fisch'] = ImageTk.PhotoImage(img)

        # Create Fork (Gabel)
        img, draw = create_image()
        draw.rectangle([45, 30, 55, 80], fill=colors['gray'])    # handle
        for i in range(4):                                       # prongs
            draw.line([35+i*7, 20, 35+i*7, 40], fill=colors['gray'], width=2)
        self.alphabet_images['Gabel'] = ImageTk.PhotoImage(img)

        # Create Guitar (Gitarre)
        img, draw = create_image()
        draw.polygon([30, 30, 70, 30, 60, 80, 40, 80], fill=colors['brown'])  # body
        draw.rectangle([35, 10, 40, 30], fill=colors['brown'])                # neck
        self.alphabet_images['Gitarre'] = ImageTk.PhotoImage(img)

        # Create Dog (Hund)
        img, draw = create_image()
        draw.ellipse([40, 40, 80, 70], fill=colors['brown'])     # body
        draw.ellipse([70, 30, 90, 50], fill=colors['brown'])     # head
        draw.polygon([85, 35, 95, 40, 85, 45], fill=colors['black'])  # nose
        self.alphabet_images['Hund'] = ImageTk.PhotoImage(img)

        # Create Heart (Herz)
        img, draw = create_image()
        x0, y0 = 50, 50
        draw.polygon([x0, y0+30, x0-30, y0, x0-15, y0-20, x0, y0-10, 
                     x0+15, y0-20, x0+30, y0], fill=colors['red'])
        self.alphabet_images['Herz'] = ImageTk.PhotoImage(img)

        # Enhanced Igel (hedgehog)
        img, draw = create_image()
        draw.ellipse([20, 40, 80, 80], fill=colors['brown'])
        for i in range(40):  # more detailed spikes
            angle = random.randint(0, 360)
            length = random.randint(8, 12)
            x = 50 + 40 * math.cos(math.radians(angle))
            y = 60 + 30 * math.sin(math.radians(angle))
            draw.line([x, y, x+length*math.cos(math.radians(angle)), 
                     y+length*math.sin(math.radians(angle))], 
                     fill=colors['darkgray'], width=3)
        self.alphabet_images['Igel'] = ImageTk.PhotoImage(img)
    
        # Create Island (Insel)
        img, draw = create_image()
        draw.ellipse([20, 50, 80, 90], fill=colors['yellow'])    # sand
        draw.polygon([40, 50, 60, 30, 50, 50], fill=colors['green'])  # palm tree
        draw.rectangle([45, 50, 55, 70], fill=colors['brown'])   # tree trunk
        self.alphabet_images['Insel'] = ImageTk.PhotoImage(img)

         # Enhanced Apfel (apple) with leaf detail
        img, draw = create_image()
        draw.ellipse([20, 20, 80, 80], fill=colors['red'])
        draw.rectangle([45, 10, 55, 20], fill=colors['brown'])
        draw.polygon([55, 15, 70, 5, 65, 20], fill=colors['green'])
        draw.line([65, 20, 60, 25], fill=colors['green'], width=2)  # leaf vein
        self.alphabet_images['Apfel'] = ImageTk.PhotoImage(img)

        # Create Eagle (Adler)
        img, draw = create_image()
        draw.polygon([50, 30, 20, 70, 80, 70], fill=colors['brown'])  # body
        draw.polygon([30, 20, 70, 20, 50, 40], fill=colors['gray'])  # wings
        draw.ellipse([40, 15, 60, 35], fill=colors['white'])  # head
        self.alphabet_images['Adler'] = ImageTk.PhotoImage(img)

        # Enhanced Ampel (traffic light) with pole
        img, draw = create_image()
        draw.rectangle([47, 10, 53, 90], fill=colors['gray'])  # pole
        draw.rectangle([35, 10, 65, 90], fill=colors['darkgray'])  # housing
        draw.ellipse([40, 15, 60, 35], fill=colors['red'])
        draw.ellipse([40, 40, 60, 60], fill=colors['yellow'])
        draw.ellipse([40, 65, 60, 85], fill=colors['green'])
        self.alphabet_images['Ampel'] = ImageTk.PhotoImage(img)
        
        # Create Car (Auto)
        img, draw = create_image()
        draw.rectangle([20, 50, 80, 80], fill=colors['blue'])  # body
        draw.polygon([30, 50, 70, 50, 60, 30, 40, 30], fill=colors['blue'])  # top
        draw.ellipse([25, 70, 45, 90], fill=colors['black'])  # wheel 1
        draw.ellipse([55, 70, 75, 90], fill=colors['black'])  # wheel 2
        self.alphabet_images['Auto'] = ImageTk.PhotoImage(img)

        # Create Pineapple (Ananas)
        img, draw = create_image()
        draw.polygon([40, 30, 60, 30, 65, 80, 35, 80], fill=colors['yellow'])  # body
        for i in range(5):  # texture
            draw.line([40+i*5, 30, 35+i*7, 80], fill=colors['brown'], width=1)
        draw.polygon([30, 20, 70, 20, 50, 35], fill=colors['green'])  # leaves
        self.alphabet_images['Ananas'] = ImageTk.PhotoImage(img)

        # Create Doctor (Arzt)
        img, draw = create_image()
        draw.rectangle([35, 30, 65, 80], fill=colors['white'])  # coat
        draw.ellipse([40, 10, 60, 30], fill=colors['gray'])  # head
        draw.rectangle([45, 40, 55, 50], fill=colors['red'])  # red cross
        self.alphabet_images['Arzt'] = ImageTk.PhotoImage(img)

        # Create Work (Arbeit)
        img, draw = create_image()
        draw.rectangle([30, 40, 70, 70], fill=colors['brown'])  # briefcase
        draw.rectangle([45, 30, 55, 40], fill=colors['brown'])  # handle
        self.alphabet_images['Arbeit'] = ImageTk.PhotoImage(img)

        # Create Eye (Auge)
        img, draw = create_image()
        draw.ellipse([20, 30, 80, 70], fill=colors['white'])  # eye white
        draw.ellipse([40, 40, 60, 60], fill=colors['blue'])   # iris
        draw.ellipse([45, 45, 55, 55], fill=colors['black'])  # pupil
        self.alphabet_images['Auge'] = ImageTk.PhotoImage(img)

        # Create Arm
        img, draw = create_image()
        draw.line([30, 20, 50, 50], fill=colors['gray'], width=15)  # upper arm
        draw.line([50, 50, 70, 80], fill=colors['gray'], width=15)  # lower arm
        self.alphabet_images['Arm'] = ImageTk.PhotoImage(img)

        # Create Ant (Ameise)
        img, draw = create_image()
        draw.ellipse([40, 20, 60, 35], fill=colors['black'])  # head
        draw.ellipse([35, 35, 65, 55], fill=colors['black'])  # thorax
        draw.ellipse([40, 55, 60, 80], fill=colors['black'])  # abdomen
        for y in [35, 45, 55]:  # legs
            draw.line([35, y, 20, y-5], fill=colors['black'], width=2)
            draw.line([65, y, 80, y-5], fill=colors['black'], width=2)
        self.alphabet_images['Ameise'] = ImageTk.PhotoImage(img)

        # Create Bread (Brot)
        img, draw = create_image()
        draw.rectangle([20, 30, 80, 70], fill=colors['brown'])
        draw.ellipse([25, 35, 75, 65], fill=colors['yellow'])
        self.alphabet_images['Brot'] = ImageTk.PhotoImage(img)

         # Enhanced Buch (book)
        img, draw = create_image()
        draw.rounded_rectangle([30, 20, 40, 80], radius=3, fill=colors['brown'])  # spine
        draw.rounded_rectangle([40, 25, 80, 75], radius=5, fill=colors['blue'])   # cover
        draw.line([45, 40, 75, 40], fill=colors['gold'], width=2)  # decoration
        self.alphabet_images['Buch'] = ImageTk.PhotoImage(img)
    
        # Create Ball
        img, draw = create_image()
        draw.ellipse([20, 20, 80, 80], fill=colors['red'])
        draw.arc([20, 20, 80, 80], 0, 180, fill=colors['white'])
        self.alphabet_images['Ball'] = ImageTk.PhotoImage(img)

        # Create Tree (Baum)
        img, draw = create_image()
        draw.rectangle([45, 60, 55, 90], fill=colors['brown'])  # trunk
        draw.polygon([20, 60, 80, 60, 50, 10], fill=colors['green'])  # leaves
        self.alphabet_images['Baum'] = ImageTk.PhotoImage(img)

        # Create Banana (Banane)
        img, draw = create_image()
        draw.arc([20, 20, 80, 60], 0, 180, fill=colors['yellow'])
        self.alphabet_images['Banane'] = ImageTk.PhotoImage(img)

        # Create Letter (Brief)
        img, draw = create_image()
        draw.rectangle([20, 30, 80, 70], fill=colors['white'])
        draw.polygon([20, 30, 50, 50, 80, 30], fill=colors['gray'])
        self.alphabet_images['Brief'] = ImageTk.PhotoImage(img)

        # Create Glasses (Brille)
        img, draw = create_image()
        draw.ellipse([20, 40, 45, 65], outline=colors['black'], width=3)
        draw.ellipse([55, 40, 80, 65], outline=colors['black'], width=3)
        draw.line([45, 50, 55, 50], fill=colors['black'], width=3)
        self.alphabet_images['Brille'] = ImageTk.PhotoImage(img)

        # Create Bed (Bett)
        img, draw = create_image()
        draw.rectangle([20, 50, 80, 80], fill=colors['brown'])  # frame
        draw.rectangle([25, 40, 75, 55], fill=colors['white'])  # pillow
        self.alphabet_images['Bett'] = ImageTk.PhotoImage(img)

        # Create Mountain (Berg)
        img, draw = create_image()
        draw.polygon([10, 80, 50, 20, 90, 80], fill=colors['gray'])
        draw.polygon([40, 30, 50, 20, 60, 30], fill=colors['white'])  # snow cap
        self.alphabet_images['Berg'] = ImageTk.PhotoImage(img)

        # Create Flower (Blume)
        img, draw = create_image()
        for i in range(6):  # petals
            angle = i * 60
            x = 50 + 30 * math.cos(math.radians(angle))
            y = 50 + 30 * math.sin(math.radians(angle))
            draw.ellipse([x-15, y-15, x+15, y+15], fill=colors['red'])
        draw.ellipse([40, 40, 60, 60], fill=colors['yellow'])  # center
        self.alphabet_images['Blume'] = ImageTk.PhotoImage(img)

         # Enhanced Computer with screen details
        img, draw = create_image()
        draw.rounded_rectangle([20, 30, 80, 70], radius=5, fill=colors['gray'])  # monitor
        draw.rectangle([45, 70, 55, 80], fill=colors['gray'])  # stand
        draw.rounded_rectangle([25, 35, 75, 65], radius=3, fill=colors['blue'])  # screen
        # Add screen content
        for y in [40, 45, 50, 55, 60]:
            draw.line([30, y, 70, y], fill=colors['white'], width=1)
        self.alphabet_images['Computer'] = ImageTk.PhotoImage(img)
    
        # Create Dragon (Drache)
        img, draw = create_image()
        draw.polygon([20, 50, 80, 50, 60, 20], fill=colors['green'])  # body
        draw.polygon([60, 20, 80, 10, 70, 30], fill=colors['red'])    # head
        self.alphabet_images['Drache'] = ImageTk.PhotoImage(img)

        # Create Ice Cream (Eis)
        img, draw = create_image()
        draw.polygon([40, 30, 60, 30, 50, 80], fill=colors['brown'])  # cone
        draw.ellipse([35, 15, 65, 45], fill=colors['white'])          # ice cream
        self.alphabet_images['Eis'] = ImageTk.PhotoImage(img)

        # Create Owl (Eule)
        img, draw = create_image()
        draw.ellipse([30, 20, 70, 80], fill=colors['brown'])          # body
        draw.ellipse([35, 30, 50, 45], fill=colors['yellow'])         # left eye
        draw.ellipse([50, 30, 65, 45], fill=colors['yellow'])         # right eye
        self.alphabet_images['Eule'] = ImageTk.PhotoImage(img)

        # Create Window (Fenster)
        img, draw = create_image()
        draw.rectangle([20, 20, 80, 80], outline=colors['brown'], width=3)
        draw.line([50, 20, 50, 80], fill=colors['brown'], width=3)
        draw.line([20, 50, 80, 50], fill=colors['brown'], width=3)
        self.alphabet_images['Fenster'] = ImageTk.PhotoImage(img)

        # Create Bottle (Flasche)
        img, draw = create_image()
        draw.rectangle([40, 20, 60, 30], fill=colors['green'])   # neck
        draw.polygon([30, 30, 70, 30, 65, 80, 35, 80], fill=colors['green'])  # body
        self.alphabet_images['Flasche'] = ImageTk.PhotoImage(img)

        # Create Frog (Frosch)
        img, draw = create_image()
        draw.ellipse([30, 40, 70, 70], fill=colors['green'])     # body
        draw.ellipse([35, 30, 45, 40], fill=colors['yellow'])    # eye 1
        draw.ellipse([55, 30, 65, 40], fill=colors['yellow'])    # eye 2
        self.alphabet_images['Frosch'] = ImageTk.PhotoImage(img)

        # Create Glass (Glas)
        img, draw = create_image()
        draw.polygon([35, 20, 65, 20, 60, 80, 40, 80], fill=colors['blue'])
        self.alphabet_images['Glas'] = ImageTk.PhotoImage(img)

        # Create Garden (Garten)
        img, draw = create_image()
        draw.rectangle([0, 70, 100, 100], fill=colors['brown'])  # soil
        for i in range(3):                                       # flowers
            draw.ellipse([20+i*25, 40, 35+i*25, 55], fill=colors['red'])
            draw.line([27+i*25, 55, 27+i*25, 70], fill=colors['green'], width=2)
        self.alphabet_images['Garten'] = ImageTk.PhotoImage(img)

        # Create Giraffe
        img, draw = create_image()
        draw.rectangle([45, 20, 55, 80], fill=colors['yellow'])              # neck
        draw.ellipse([35, 10, 65, 30], fill=colors['yellow'])               # head
        draw.polygon([35, 80, 65, 80, 60, 90, 40, 90], fill=colors['yellow'])  # body
        self.alphabet_images['Giraffe'] = ImageTk.PhotoImage(img)

        # Create House (Haus)
        img, draw = create_image()
        draw.rectangle([30, 40, 70, 80], fill=colors['red'])          # walls
        draw.polygon([30, 40, 50, 20, 70, 40], fill=colors['brown'])  # roof
        self.alphabet_images['Haus'] = ImageTk.PhotoImage(img)

        # Create Hand
        img, draw = create_image()
        draw.rectangle([40, 30, 60, 70], fill=colors['gray'])    # palm
        for i in range(5):                                       # fingers
            draw.rectangle([30+i*8, 20, 35+i*8, 40], fill=colors['gray'])
        self.alphabet_images['Hand'] = ImageTk.PhotoImage(img)

        # Create Hat (Hut)
        img, draw = create_image()
        draw.ellipse([20, 50, 80, 70], fill=colors['brown'])     # brim
        draw.rectangle([35, 20, 65, 50], fill=colors['brown'])   # top
        self.alphabet_images['Hut'] = ImageTk.PhotoImage(img)

        # Create Insect (Insekt)
        img, draw = create_image()
        draw.ellipse([30, 40, 50, 60], fill=colors['black'])     # body segment 1
        draw.ellipse([50, 40, 70, 60], fill=colors['black'])     # body segment 2
        for i in range(3):                                       # legs
            draw.line([40, 50-i*5, 20, 40-i*5], fill=colors['black'], width=2)
            draw.line([60, 50-i*5, 80, 40-i*5], fill=colors['black'], width=2)
        self.alphabet_images['Insekt'] = ImageTk.PhotoImage(img)

        # Create Instrument
        img, draw = create_image()
        draw.ellipse([30, 40, 70, 80], fill=colors['brown'])     # violin body
        draw.rectangle([45, 10, 55, 40], fill=colors['brown'])   # neck
        draw.line([70, 30, 80, 60], fill=colors['brown'], width=3)  # bow
        self.alphabet_images['Instrument'] = ImageTk.PhotoImage(img)

        # Create Internet
        img, draw = create_image()
        draw.ellipse([30, 30, 70, 70], fill=colors['blue'])      # globe
        for i in range(3):                                       # network lines
            draw.line([20+i*20, 50, 80-i*20, 50], fill=colors['white'], width=2)
            draw.line([50, 20+i*20, 50, 80-i*20], fill=colors['white'], width=2)
        self.alphabet_images['Internet'] = ImageTk.PhotoImage(img)

        # Create Chance
        img, draw = create_image()
        draw.ellipse([20, 20, 80, 80], outline=colors['blue'], width=3)  # circle
        draw.text([35, 35], "?", fill=colors['blue'], font=ImageFont.truetype("Arial", 36))
        self.alphabet_images['Chance'] = ImageTk.PhotoImage(img)

        # Create Cent
        img, draw = create_image()
        draw.ellipse([20, 20, 80, 80], fill=colors['yellow'])  # coin
        draw.text([40, 35], "¢", fill=colors['black'], font=ImageFont.truetype("Arial", 36))
        self.alphabet_images['Cent'] = ImageTk.PhotoImage(img)

        # Create Roof (Dach)
        img, draw = create_image()
        draw.polygon([10, 60, 50, 20, 90, 60], fill=colors['red'])  # roof
        draw.rectangle([20, 60, 80, 80], fill=colors['gray'])       # wall
        self.alphabet_images['Dach'] = ImageTk.PhotoImage(img)

        # Create Printer (Drucker)
        img, draw = create_image()
        draw.rectangle([20, 40, 80, 70], fill=colors['gray'])    # printer body
        draw.rectangle([30, 30, 70, 40], fill=colors['white'])   # paper tray
        draw.rectangle([25, 70, 75, 75], fill=colors['white'])   # paper output
        self.alphabet_images['Drucker'] = ImageTk.PhotoImage(img)

        # Create Can (Dose)
        img, draw = create_image()
        draw.rectangle([30, 20, 70, 80], fill=colors['gray'])
        draw.ellipse([30, 15, 70, 25], fill=colors['gray'])
        draw.ellipse([30, 75, 70, 85], fill=colors['gray'])
        self.alphabet_images['Dose'] = ImageTk.PhotoImage(img)

        # Create Shower (Dusche)
        img, draw = create_image()
        draw.rectangle([40, 10, 60, 30], fill=colors['gray'])    # shower head
        for i in range(5):                                       # water drops
            draw.line([45+i*5, 30, 45+i*5, 60], fill=colors['blue'], width=2)
        self.alphabet_images['Dusche'] = ImageTk.PhotoImage(img)

        # Create Strawberry (Erdbeere)
        img, draw = create_image()
        draw.polygon([30, 80, 50, 30, 70, 80], fill=colors['red'])  # berry
        draw.polygon([40, 20, 50, 30, 60, 20], fill=colors['green'])  # leaves
        for i in range(10):  # seeds
            x = random.randint(35, 65)
            y = random.randint(40, 75)
            draw.ellipse([x, y, x+3, y+3], fill=colors['yellow'])
        self.alphabet_images['Erdbeere'] = ImageTk.PhotoImage(img)

        # Create Bicycle (Fahrrad)
        img, draw = create_image()
        draw.ellipse([20, 50, 40, 70], fill=colors['black'])     # wheel 1
        draw.ellipse([60, 50, 80, 70], fill=colors['black'])     # wheel 2
        draw.line([30, 60, 70, 60], fill=colors['blue'], width=3)  # frame
        draw.line([30, 60, 50, 40], fill=colors['blue'], width=3)  # handlebar support
        draw.line([40, 35, 60, 35], fill=colors['blue'], width=3)  # handlebar
        self.alphabet_images['Fahrrad'] = ImageTk.PhotoImage(img)

        # J: Jaguar
        img, draw = create_image()
        draw.ellipse([30, 40, 70, 80], fill=colors['orange'])  # body
        draw.polygon([65, 30, 85, 40, 65, 50], fill=colors['orange'])  # head
        for _ in range(20):  # spots
            x = random.randint(35, 75)
            y = random.randint(45, 75)
            draw.ellipse([x, y, x+6, y+6], fill=colors['black'])
        self.alphabet_images['Jaguar'] = ImageTk.PhotoImage(img)

        # K: Kuchen (cake)
        img, draw = create_image()
        draw.rectangle([20, 60, 80, 80], fill=colors['brown'])  # base
        draw.rectangle([25, 50, 75, 60], fill=colors['pink'])    # frosting
        for i in range(5):  # candles
            draw.rectangle([30+i*10, 30, 35+i*10, 50], fill=colors['yellow'])
        self.alphabet_images['Kuchen'] = ImageTk.PhotoImage(img)

        # L: Löwe (lion)
        img, draw = create_image()
        draw.ellipse([30, 40, 70, 80], fill=colors['yellow'])  # face
        for angle in [30, 150, 270]:  # mane
            x = 50 + 40 * math.cos(math.radians(angle))
            y = 60 + 40 * math.sin(math.radians(angle))
            draw.ellipse([x-20, y-20, x+20, y+20], fill=colors['orange'])
        self.alphabet_images['Löwe'] = ImageTk.PhotoImage(img)

        # M: Mond (moon)
        img, draw = create_image(color='navy')
        draw.ellipse([30, 30, 70, 70], fill=colors['white'])
        draw.ellipse([40, 35, 60, 55], fill=colors['navy'])  # crater
        self.alphabet_images['Mond'] = ImageTk.PhotoImage(img)

        # N: Nadel (needle)
        img, draw = create_image()
        draw.line([50, 20, 50, 80], fill=colors['gray'], width=3)
        draw.polygon([45, 25, 55, 25, 50, 15], fill=colors['silver'])  # eye
        self.alphabet_images['Nadel'] = ImageTk.PhotoImage(img)

        # O: Ozean (ocean)
        img, draw = create_image()
        draw.rectangle([0, 60, 100, 100], fill=colors['blue'])
        draw.polygon([20, 60, 40, 40, 60, 60], fill=colors['white'])  # wave
        self.alphabet_images['Ozean'] = ImageTk.PhotoImage(img)

        # P: Pferd (horse)
        img, draw = create_image()
        draw.polygon([30,60, 50,30, 70,60], fill=colors['brown'])  # body
        draw.polygon([70,60, 85,40, 70,50], fill=colors['brown'])  # neck/head
        self.alphabet_images['Pferd'] = ImageTk.PhotoImage(img)

        # Q: Qualle (jellyfish)
        img, draw = create_image(color='darkblue')
        draw.ellipse([40, 30, 60, 50], fill=colors['pink'])  # body
        for i in range(5):  # tentacles
            draw.line([45+i*3, 50, 40+i*5, 70], fill=colors['pink'], width=2)
        self.alphabet_images['Qualle'] = ImageTk.PhotoImage(img)

        # R: Regen (rain)
        img, draw = create_image(color='lightgray')
        for i in range(15):  # raindrops
            x = random.randint(10, 90)
            y = random.randint(10, 90)
            draw.line([x, y, x+3, y+10], fill=colors['blue'], width=2)
        self.alphabet_images['Regen'] = ImageTk.PhotoImage(img)

        # S: Sonne (sun)
        img, draw = create_image(color='lightblue')
        draw.ellipse([30, 30, 70, 70], fill=colors['yellow'])
        for angle in range(0, 360, 30):  # rays
            x = 50 + 40 * math.cos(math.radians(angle))
            y = 50 + 40 * math.sin(math.radians(angle))
            draw.line([50,50, x,y], fill=colors['yellow'], width=3)
        self.alphabet_images['Sonne'] = ImageTk.PhotoImage(img)

        # T: Tiger
        img, draw = create_image()
        draw.ellipse([30, 40, 70, 80], fill=colors['orange'])  # body
        for _ in range(20):  # stripes
            x = random.randint(35, 65)
            y = random.randint(45, 75)
            draw.line([x, y, x+10, y+10], fill=colors['black'], width=3)
        self.alphabet_images['Tiger'] = ImageTk.PhotoImage(img)

        # U: Uhr (clock)
        img, draw = create_image()
        draw.ellipse([20, 20, 80, 80], outline=colors['black'], width=3)
        draw.line([50,50, 50,30], fill=colors['black'], width=2)  # hour
        draw.line([50,50, 70,50], fill=colors['black'], width=2)  # minute
        self.alphabet_images['Uhr'] = ImageTk.PhotoImage(img)

        # Enhanced Vogel (bird)
        img, draw = create_image()
        draw.polygon([35,50, 50,30, 65,50], fill=colors['blue'])  # body
        draw.polygon([65,50, 80,40, 75,55], fill=colors['blue'])  # head
        draw.line([50,50, 50,70], fill=colors['orange'], width=3)  # legs
        self.alphabet_images['Vogel'] = ImageTk.PhotoImage(img)

        # W: Wasser (water)
        img, draw = create_image()
        draw.rectangle([0, 70, 100, 100], fill=colors['blue'])
        draw.polygon([20,70, 40,50, 60,70], fill=colors['white'])  # wave
        self.alphabet_images['Wasser'] = ImageTk.PhotoImage(img)

        # X: Xylophon
        img, draw = create_image()
        for i, c in enumerate(['red', 'orange', 'yellow', 'green', 'blue']):
            bar_width = 20 - i*3
            draw.rectangle([20+i*15, 80-(i+1)*10, 20+i*15+bar_width, 80], fill=c)
        self.alphabet_images['Xylophon'] = ImageTk.PhotoImage(img)

        # J: Joghurt
        img, draw = create_image()
        draw.ellipse([40, 30, 80, 70], fill=colors['white'])  # cup
        draw.rectangle([45, 70, 75, 80], fill=colors['brown'])  # base
        for i in range(5):  # fruit pieces
            x = random.randint(45, 75)
            y = random.randint(40, 65)
            draw.ellipse([x, y, x+5, y+5], fill=colors['red'])
        self.alphabet_images['Joghurt'] = ImageTk.PhotoImage(img)

        # X: Xenon (improved)
        img, draw = create_image(color='black')
        draw.ellipse([40, 40, 80, 80], fill=colors['purple'])
        for _ in range(30):  # particles
            x = random.randint(30, 90)
            y = random.randint(30, 90)
            draw.ellipse([x,y, x+2,y+2], fill=colors['white'])
        self.alphabet_images['Xenon'] = ImageTk.PhotoImage(img)

        # Y: Yeti
        img, draw = create_image()
        draw.ellipse([40, 30, 80, 70], fill=colors['white'])  # body
        draw.ellipse([50, 20, 70, 40], fill=colors['white'])  # head
        for _ in range(20):  # fur texture
            x = random.randint(45, 75)
            y = random.randint(35, 65)
            draw.line([x, y, x+3, y+3], fill=colors['gray'], width=2)
        self.alphabet_images['Yeti'] = ImageTk.PhotoImage(img)

        # Q: Quelle (spring)
        img, draw = create_image()
        draw.polygon([40,80, 60,80, 70,60, 30,60], fill=colors['blue'])  # water
        draw.ellipse([45, 30, 55, 40], fill=colors['gray'])  # rock
        for i in range(3):  # water lines
            draw.line([40+i*10, 50, 50+i*10, 70], fill=colors['white'], width=2)
        self.alphabet_images['Quelle'] = ImageTk.PhotoImage(img)

        # Y: Yacht
        img, draw = create_image()
        draw.polygon([20,80, 50,40, 80,80], fill=colors['white'])  # hull
        draw.line([50,40, 50,20], fill=colors['brown'], width=3)   # mast
        draw.polygon([50,20, 70,30, 50,40], fill=colors['white'])  # sail
        self.alphabet_images['Yacht'] = ImageTk.PhotoImage(img)

        # Z: Zebra
        img, draw = create_image()
        draw.ellipse([30, 40, 70, 80], fill=colors['white'])  # body
        for _ in range(15):  # stripes
            x = random.randint(35, 65)
            y = random.randint(45, 75)
            draw.line([x, y, x+random.randint(5,15), y+random.randint(5,15)], 
                     fill=colors['black'], width=3)
        self.alphabet_images['Zebra'] = ImageTk.PhotoImage(img)

        # Enhanced Wolke (cloud)
        img, draw = create_image(color='lightblue')
        draw.ellipse([20, 40, 60, 80], fill=colors['white'])
        draw.ellipse([40, 30, 80, 70], fill=colors['white'])
        draw.ellipse([60, 40, 100, 80], fill=colors['white'])
        self.alphabet_images['Wolke'] = ImageTk.PhotoImage(img)

        # Y: Yen
        img, draw = create_image()
        draw.text((40,40), "¥", fill=colors['black'], 
                font=ImageFont.truetype("Arial", 48))
        self.alphabet_images['Yen'] = ImageTk.PhotoImage(img)

        # Z: Zahn (tooth)
        img, draw = create_image()
        draw.ellipse([40, 30, 80, 70], fill=colors['white'])
        draw.line([60,30, 60,70], fill=colors['gray'], width=3)
        self.alphabet_images['Zahn'] = ImageTk.PhotoImage(img)

        # Enhanced Lemon (Zitrone)
        img, draw = create_image()
        draw.ellipse([30, 30, 90, 90], fill=colors['yellow'])
        for _ in range(15):  # texture
            x = random.randint(35, 85)
            y = random.randint(35, 85)
            draw.line([x, y, x+3, y+3], fill=colors['green'], width=2)
        self.alphabet_images['Zitrone'] = ImageTk.PhotoImage(img)

        # U-Boot (submarine)
        img, draw = create_image()
        draw.ellipse([20, 40, 80, 60], fill=colors['gray'])  # body
        draw.rectangle([45, 30, 55, 40], fill=colors['red'])  # tower
        for i in range(3):  # portholes
            draw.ellipse([30+i*15, 45, 35+i*15, 50], fill=colors['black'])
        self.alphabet_images['U-Boot'] = ImageTk.PhotoImage(img)

        # Xenon improved
        img, draw = create_image(color='black')
        draw.ellipse([40, 40, 80, 80], fill=colors['purple'])
        for _ in range(20):  # particle effect
            x = random.randint(30, 90)
            y = random.randint(30, 90)
            draw.ellipse([x, y, x+2, y+2], fill=colors['white'])
        self.alphabet_images['Xenon'] = ImageTk.PhotoImage(img)

        # Create greeting images
        # Morning greeting
        img, draw = create_image()
        draw.arc([20, -40, 80, 40], 0, 180, fill=colors['yellow'])  # Sun rising
        draw.rectangle([0, 70, 100, 100], fill=colors['green'])      # Ground
        self.alphabet_images['Guten_Morgen'] = ImageTk.PhotoImage(img)

        # Day greeting
        img, draw = create_image()
        draw.ellipse([70, 10, 90, 30], fill=colors['yellow'])       # Sun high in sky
        draw.rectangle([0, 70, 100, 100], fill=colors['green'])     # Ground
        self.alphabet_images['Guten_Tag'] = ImageTk.PhotoImage(img)

        # Evening greeting
        img, draw = create_image()
        draw.arc([20, 60, 80, 140], 180, 360, fill=colors['orange'])  # Sun setting
        draw.rectangle([0, 70, 100, 100], fill=colors['green'])       # Ground
        self.alphabet_images['Guten_Abend'] = ImageTk.PhotoImage(img)

        # Night greeting
        img, draw = create_image(color='navy')
        for i in range(10):  # Stars
            x = random.randint(10, 90)
            y = random.randint(10, 60)
            draw.ellipse([x, y, x+2, y+2], fill=colors['yellow'])
        draw.ellipse([70, 20, 85, 35], fill=colors['yellow'])  # Moon
        self.alphabet_images['Gute_Nacht'] = ImageTk.PhotoImage(img)

        # Create book command images
        # Open book
        img, draw = create_image()
        draw.polygon([20, 50, 50, 20, 80, 50, 50, 80], fill=colors['brown'])  # open book shape
        draw.line([50, 20, 50, 80], fill=colors['gray'], width=2)  # page line
        self.alphabet_images['Buch_auf'] = ImageTk.PhotoImage(img)

        # Closed book
        img, draw = create_image()
        draw.rectangle([30, 20, 70, 80], fill=colors['brown'])  # closed book
        draw.line([35, 25, 65, 25], fill=colors['gray'], width=2)  # decoration
        draw.line([35, 75, 65, 75], fill=colors['gray'], width=2)  # decoration
        self.alphabet_images['Buch_zu'] = ImageTk.PhotoImage(img)

        # Create sit/stand command images
        # Sitting person
        img, draw = create_image()
        # Chair
        draw.rectangle([30, 50, 70, 70], fill=colors['brown'])  # seat
        draw.rectangle([30, 70, 40, 90], fill=colors['brown'])  # left leg
        draw.rectangle([60, 70, 70, 90], fill=colors['brown'])  # right leg
        # Person
        draw.ellipse([40, 30, 60, 50], fill=colors['gray'])    # head
        draw.line([50, 50, 50, 70], fill=colors['gray'], width=3)  # body
        draw.line([35, 60, 65, 60], fill=colors['gray'], width=3)  # arms
        draw.line([50, 70, 65, 80], fill=colors['gray'], width=3)  # legs
        self.alphabet_images['Setz'] = ImageTk.PhotoImage(img)

        # Standing person
        img, draw = create_image()
        draw.ellipse([40, 10, 60, 30], fill=colors['gray'])    # head
        draw.line([50, 30, 50, 70], fill=colors['gray'], width=3)  # body
        draw.line([30, 50, 70, 50], fill=colors['gray'], width=3)  # arms
        draw.line([50, 70, 30, 90], fill=colors['gray'], width=3)  # left leg
        draw.line([50, 70, 70, 90], fill=colors['gray'], width=3)  # right leg
        self.alphabet_images['Steh'] = ImageTk.PhotoImage(img)

    def init_data(self):
        self.alphabet_words = {
            'A': [
                'Apfel (apple)',
                'Adler (eagle)',
                'Ampel (traffic light)',
                'Auto (car)',
                'Ananas (pineapple)',
                'Arzt (doctor)',
                'Arbeit (work)',
                'Auge (eye)',
                'Arm (arm)',
                'Ameise (ant)'
            ],
            'B': [
                'Brot (bread)',
                'Buch (book)',
                'Ball (ball)',
                'Baum (tree)',
                'Banane (banana)',
                'Brief (letter)',
                'Brille (glasses)',
                'Bett (bed)',
                'Berg (mountain)',
                'Blume (flower)'
            ],
            'C': [
                'Computer (computer)',
                'Café (cafe)',
                'Chef (boss)',
                'Chance (chance)',
                'Cent (cent)'
            ],
            'D': [
                'Dach (roof)',
                'Drucker (printer)',
                'Dose (can)',
                'Dusche (shower)',
                'Drache (dragon)'
            ],
            'E': [
                'Eis (ice cream)',
                'Eule (owl)',
                'Ente (duck)',
                'Elefant (elephant)',
                'Erdbeere (strawberry)'
            ],
            'F': [
                'Fisch (fish)',
                'Fenster (window)',
                'Fahrrad (bicycle)',
                'Flasche (bottle)',
                'Frosch (frog)'
            ],
            'G': [
                'Glas (glass)',
                'Gabel (fork)',
                'Garten (garden)',
                'Gitarre (guitar)',
                'Giraffe (giraffe)'
            ],
            'H': [
                'Haus (house)',
                'Hund (dog)',
                'Hand (hand)',
                'Hut (hat)',
                'Herz (heart)'
            ],
            'I': [
                'Igel (hedgehog)',
                'Insel (island)',
                'Insekt (insect)',
                'Instrument (instrument)',
                'Internet (internet)'
            ],
            'J': [
                'Jaguar (jaguar)',
                'Jacke (jacket)',
                'Joghurt (yogurt)',
                'Juwel (jewel)'
            ],
            'K': [
                'Katze (cat)',
                'Kuchen (cake)',
                'Kirsche (cherry)',
                'Kamel (camel)'
            ],
            'L': [
                'Lampe (lamp)',
                'Löwe (lion)',
                'Lupe (magnifier)',
                'Lemon (lemon)'
            ],
            'M': [
                'Mond (moon)',
                'Maus (mouse)',
                'Milch (milk)',
                'Mütze (hat)'
            ],
            'N': [
                'Nase (nose)',
                'Nest (nest)',
                'Nadel (needle)',
                'Nummer (number)'
            ],
            'O': [
                'Orange (orange)',
                'Ohr (ear)',
                'Ozean (ocean)',
                'Oval (oval)'
            ],
            'P': [
                'Pferd (horse)',
                'Papagei (parrot)',
                'Pilz (mushroom)',
                'Paket (package)'
            ],
            'Q': [
                'Qualle (jellyfish)',
                'Quark (curd)',
                'Quelle (spring)',
                'Quiz (quiz)'
            ],
            'R': [
                'Rose (rose)',
                'Rad (wheel)',
                'Regen (rain)',
                'Robbe (seal)'
            ],
            'S': [
                'Sonne (sun)',
                'Stern (star)',
                'Schuh (shoe)',
                'Schaf (sheep)'
            ],
            'T': [
                'Tisch (table)',
                'Tiger (tiger)',
                'Tasche (bag)',
                'Tomate (tomato)'
            ],
            'U': [
                'Uhr (clock)',
                'Unterhose (underwear)',
                'U-Boot (submarine)',
                'Universum (universe)'
            ],
            'V': [
                'Vogel (bird)',
                'Vase (vase)',
                'Violine (violin)',
                'Vulkan (volcano)'
            ],
            'W': [
                'Wasser (water)',
                'Wolf (wolf)',
                'Wolke (cloud)',
                'Wurm (worm)'
            ],
            'X': [
                'Xylophon (xylophone)',
                'Xenon (xenon)',
                'Xerox (photocopy)',
                'Xylit (xylitol)'
            ],
            'Y': [
                'Yoga (yoga)',
                'Yacht (yacht)',
                'Yeti (yeti)',
                'Yen (yen)'
            ],
            'Z': [
                'Zebra (zebra)',
                'Zahn (tooth)',
                'Zug (train)',
                'Zitrone (lemon)'
            ]
            
        }
        
        self.completion_words = self.generate_completion_exercises()
        
        self.greetings = {
            'Guten Morgen': 'Good Morning (until 11:00)',
            'Guten Tag': 'Good Day (11:00-18:00)',
            'Guten Abend': 'Good Evening (after 18:00)',
            'Gute Nacht': 'Good Night'
        }
        
        self.book_commands = {
            'Mach das Buch auf': 'Open the book',
            'Mach das Buch zu': 'Close the book'
        }
        
        self.sit_stand_commands = {
            'Setz dich': 'Sit down',
            'Steh auf': 'Stand up'
        }

    def generate_completion_exercises(self):
        """Generate completion exercises from alphabet words with random missing letters"""
        completion_dict = {}
        
        for letter, words in self.alphabet_words.items():
            exercises = []
            for word in words:
                german_word = word.split(' (')[0]  # Get the German word
                english_word = word.split('(')[1].rstrip(')')  # Get the English translation
                
                # Select a random position in the word
                pos = random.randint(0, len(german_word) - 1)
                # Create incomplete word by replacing random letter with underscore
                incomplete = german_word[:pos] + '_' + german_word[pos+1:]
                missing_letter = german_word[pos]
                
                exercises.append((incomplete, missing_letter, german_word, english_word))
            
            completion_dict[letter] = exercises
        
        return completion_dict

    def setup_alphabet_tab(self):
        frame = ttk.Frame(self.alphabet_tab.scrollable_frame)
        frame.pack(pady=10, expand=True, fill='both')
        
        title_label = ttk.Label(frame, text="German Words by Letter", font=('Arial', 14, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20), padx=10)
        
        current_row = 1
        for letter, words in self.alphabet_words.items():
            # Letter header
            letter_frame = ttk.Frame(frame)
            letter_frame.grid(row=current_row, column=0, columnspan=3, pady=(20, 10), padx=10, sticky='w')
            
            letter_label = ttk.Label(letter_frame, text=f"Letter {letter}", font=('Arial', 12, 'bold'))
            letter_label.pack(side='left', padx=(0, 20))
            
            current_row += 1
            
            # Words list with their corresponding images
            for word in words:
                word_frame = ttk.Frame(frame)
                word_frame.grid(row=current_row, column=0, pady=2, padx=30, sticky='w')
                
                # Extract the German word from the format "Word (translation)"
                german_word = word.split(' (')[0]
                
                word_label = ttk.Label(word_frame, text=word)
                word_label.pack(side='left', padx=(0, 10))
                
                # Add image if available
                if german_word in self.alphabet_images:
                    img_label = ttk.Label(word_frame, image=self.alphabet_images[german_word])
                    img_label.pack(side='left')
                
                current_row += 1
            
            if letter != list(self.alphabet_words.keys())[-1]:
                ttk.Separator(frame, orient='horizontal').grid(
                    row=current_row, column=0, columnspan=3, sticky='ew', pady=10)
                current_row += 1

    def setup_styles(self):
        """Setup ttk styles for the application"""
        style = ttk.Style()
        
        # Configure button style
        style.configure('TButton', padding=6, relief="flat", background="#ccc")
        
        # Configure label style
        style.configure('TLabel', padding=3)
        
        # Configure notebook style
        style.configure('TNotebook', padding=2)
        style.configure('TNotebook.Tab', padding=[10, 2])
        
        # Configure frame style
        style.configure('TFrame', background='white')

    def setup_greetings_tab(self):
        frame = ttk.Frame(self.greetings_tab.scrollable_frame)
        frame.pack(pady=10, expand=True, fill='both')
        
        # Add title
        title_label = ttk.Label(frame, text="German Greetings", font=('Arial', 14, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20), padx=10)
        
        current_row = 1
        for greeting, translation in self.greetings.items():
            # Create frame for each greeting
            greeting_frame = ttk.Frame(frame)
            greeting_frame.grid(row=current_row, column=0, columnspan=3, pady=10, padx=10, sticky='w')
            
            # Add greeting text
            ttk.Label(greeting_frame, 
                     text=f"{greeting}", 
                     font=('Arial', 12, 'bold')).pack(side='left', padx=(0, 20))
            
            # Add translation
            ttk.Label(greeting_frame, 
                     text=f"{translation}").pack(side='left', padx=(0, 20))
            
            # Add image
            img_key = greeting.replace(' ', '_')  # Convert space to underscore to match image keys
            if img_key in self.alphabet_images:
                img_label = ttk.Label(greeting_frame, image=self.alphabet_images[img_key])
                img_label.pack(side='left')
            
            current_row += 1
            
            # Add separator except after last item
            if greeting != list(self.greetings.keys())[-1]:
                ttk.Separator(frame, orient='horizontal').grid(
                    row=current_row, column=0, columnspan=3, sticky='ew', pady=5)
                current_row += 1

    def setup_book_tab(self):
        frame = ttk.Frame(self.book_tab.scrollable_frame)
        frame.pack(pady=10, expand=True, fill='both')
        
        # Add title
        title_label = ttk.Label(frame, text="Book Commands", font=('Arial', 14, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20), padx=10)
        
        current_row = 1
        for command, translation in self.book_commands.items():
            # Create frame for each command
            command_frame = ttk.Frame(frame)
            command_frame.grid(row=current_row, column=0, columnspan=3, pady=10, padx=10, sticky='w')
            
            # Add command text
            ttk.Label(command_frame, 
                     text=f"{command}", 
                     font=('Arial', 12, 'bold')).pack(side='left', padx=(0, 20))
            
            # Add translation
            ttk.Label(command_frame, 
                     text=f"{translation}").pack(side='left', padx=(0, 20))
            
            # Add image
            img_key = 'Buch_auf' if 'auf' in command else 'Buch_zu'
            if img_key in self.alphabet_images:
                img_label = ttk.Label(command_frame, image=self.alphabet_images[img_key])
                img_label.pack(side='left')
            
            current_row += 1
            
            # Add separator except after last item
            if command != list(self.book_commands.keys())[-1]:
                ttk.Separator(frame, orient='horizontal').grid(
                    row=current_row, column=0, columnspan=3, sticky='ew', pady=5)
                current_row += 1

    def setup_sit_stand_tab(self):
        frame = ttk.Frame(self.sit_stand_tab.scrollable_frame)
        frame.pack(pady=10, expand=True, fill='both')
        
        # Add title
        title_label = ttk.Label(frame, text="Sit and Stand Commands", font=('Arial', 14, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20), padx=10)
        
        current_row = 1
        for command, translation in self.sit_stand_commands.items():
            # Create frame for each command
            command_frame = ttk.Frame(frame)
            command_frame.grid(row=current_row, column=0, columnspan=3, pady=10, padx=10, sticky='w')
            
            # Add command text
            ttk.Label(command_frame, 
                     text=f"{command}", 
                     font=('Arial', 12, 'bold')).pack(side='left', padx=(0, 20))
            
            # Add translation
            ttk.Label(command_frame, 
                     text=f"{translation}").pack(side='left', padx=(0, 20))
            
            # Add image
            img_key = 'Setz' if 'Setz' in command else 'Steh'
            if img_key in self.alphabet_images:
                img_label = ttk.Label(command_frame, image=self.alphabet_images[img_key])
                img_label.pack(side='left')
            
            current_row += 1
            
            # Add separator except after last item
            if command != list(self.sit_stand_commands.keys())[-1]:
                ttk.Separator(frame, orient='horizontal').grid(
                    row=current_row, column=0, columnspan=3, sticky='ew', pady=5)
                current_row += 1

    def setup_matching_tab(self):
        frame = ttk.Frame(self.matching_tab.scrollable_frame)
        frame.pack(pady=10, expand=True, fill='both')
        
        self.matching_pairs = {}
        self.matching_pairs.update(self.book_commands)
        self.matching_pairs.update(self.sit_stand_commands)
        
        self.selected_word = None
        self.buttons = []
        
        german_words = list(self.matching_pairs.keys())
        english_words = list(self.matching_pairs.values())
        random.shuffle(german_words)
        random.shuffle(english_words)
        
        for i, word in enumerate(german_words):
            btn = ttk.Button(frame, text=word, width=30,
                           command=lambda w=word: self.match_word(w, 'de'))
            btn.grid(row=i, column=0, pady=5, padx=10, sticky='w')
            self.buttons.append(btn)
        
        for i, word in enumerate(english_words):
            btn = ttk.Button(frame, text=word, width=30,
                           command=lambda w=word: self.match_word(w, 'en'))
            btn.grid(row=i, column=1, pady=5, padx=10, sticky='w')
            self.buttons.append(btn)

    def match_word(self, word, language):
        if self.selected_word is None:
            self.selected_word = (word, language)
            for btn in self.buttons:
                if btn['text'] == word:
                    btn.state(['disabled'])
        else:
            prev_word, prev_lang = self.selected_word
            if language != prev_lang:
                if (language == 'en' and self.matching_pairs[prev_word] == word) or \
                   (language == 'de' and self.matching_pairs[word] == prev_word):
                    messagebox.showinfo("Correct!", "That's right!")
                    for btn in self.buttons:
                        if btn['text'] in [word, prev_word]:
                            btn.state(['disabled'])
                else:
                    messagebox.showinfo("Incorrect", "Try again!")
                    for btn in self.buttons:
                        if btn['text'] == prev_word:
                            btn.state(['!disabled'])
            self.selected_word = None

    def setup_letter_completion_tab(self):
        main_frame = ttk.Frame(self.letter_completion_tab.scrollable_frame)
        main_frame.pack(expand=True, fill='both', padx=20, pady=20)
        
        # Create frame for instructions and random button
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(top_frame, text="Practice completing German words:", 
                 font=('Arial', 12, 'bold')).pack(side='left', pady=5)
        
        random_btn = ttk.Button(top_frame, text="Random Word",
                               command=self.show_random_completion_exercise)
        random_btn.pack(side='right', padx=5)
        
        # Create frame for letter selection
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side='left', padx=10, fill='y')
        
        ttk.Label(left_frame, text="Or select letter:").pack(pady=5)
        
        for letter in self.completion_words.keys():
            ttk.Button(left_frame, text=letter,
                      command=lambda l=letter: self.show_completion_exercises(l)).pack(pady=2)
        
        self.exercise_frame = ttk.Frame(main_frame)
        self.exercise_frame.pack(side='left', expand=True, fill='both', padx=10)

    def show_random_completion_exercise(self):
        """Show a random word completion exercise"""
        # Clear existing exercises
        for widget in self.exercise_frame.winfo_children():
            widget.destroy()
        
        # Select random letter and word
        letter = random.choice(list(self.completion_words.keys()))
        exercise = random.choice(self.completion_words[letter])
        
        ttk.Label(self.exercise_frame, 
                 text="Complete the missing letter in this word:",
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        exercise_frame = ttk.Frame(self.exercise_frame)
        exercise_frame.pack(pady=10)
        
        incomplete, missing_letter, complete, english = exercise
        
        word_frame = ttk.Frame(exercise_frame)
        word_frame.pack(pady=5, fill='x')
        
        ttk.Label(word_frame, text=incomplete, 
                 font=('Arial', 11)).pack(side='left', padx=5)
        
        entry = ttk.Entry(word_frame, width=5)
        entry.pack(side='left', padx=5)
        
        check_btn = ttk.Button(word_frame, 
                             text="Check",
                             command=lambda e=entry, m=missing_letter, c=complete: 
                                 self.check_random_answer(e, m, c))
        check_btn.pack(side='left', padx=5)
        
        ttk.Label(word_frame, 
                 text=f"({english})",
                 font=('Arial', 11)).pack(side='left', padx=5)
        
        # Add a "Try Another" button
        ttk.Button(self.exercise_frame, 
                  text="Try Another Word",
                  command=self.show_random_completion_exercise).pack(pady=10)

    def show_completion_exercises(self, letter):
        for widget in self.exercise_frame.winfo_children():
            widget.destroy()
        
        ttk.Label(self.exercise_frame, 
                 text=f"Complete the missing letters in these words:",
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        exercises_frame = ttk.Frame(self.exercise_frame)
        exercises_frame.pack(pady=10)
        
        for incomplete, missing_letter, complete, english in self.completion_words[letter]:
            exercise_frame = ttk.Frame(exercises_frame)
            exercise_frame.pack(pady=5, fill='x')
            
            ttk.Label(exercise_frame, text=incomplete, 
                     font=('Arial', 11)).pack(side='left', padx=5)
            
            entry = ttk.Entry(exercise_frame, width=5)
            entry.pack(side='left', padx=5)
            
            check_btn = ttk.Button(exercise_frame, 
                                 text="Check",
                                 command=lambda e=entry, m=missing_letter, c=complete: 
                                     self.check_random_answer(e, m, c))
            check_btn.pack(side='left', padx=5)
            
            ttk.Label(exercise_frame, 
                     text=f"({english})",
                     font=('Arial', 11)).pack(side='left', padx=5)

    def check_random_answer(self, entry, missing_letter, complete_word):
        user_answer = entry.get().strip().lower()
        correct_letter = missing_letter.lower()
        
        if user_answer == correct_letter:
            messagebox.showinfo("Correct!", f"Yes! The word is '{complete_word}'")
            entry.config(state='disabled')
        else:
            messagebox.showerror("Incorrect", "Try again!")

    def setup_quiz_tab(self):
        frame = ttk.Frame(self.quiz_tab.scrollable_frame)
        frame.pack(pady=20, padx=20, fill='both', expand=True)

        self.quiz_data = []
        self.current_question = 0
        self.score = 0

        # Quiz header
        self.quiz_header = ttk.Label(frame, text="German Word Quiz", font=('Arial', 16, 'bold'))
        self.quiz_header.pack(pady=10)

        # Question container
        self.question_frame = ttk.Frame(frame)
        self.question_frame.pack(pady=20)

        # Question text
        self.question_label = ttk.Label(self.question_frame, text="", font=('Arial', 14))
        self.question_label.pack()

        # Image display
        self.quiz_image_label = ttk.Label(self.question_frame)
        self.quiz_image_label.pack(pady=10)

        # Answer buttons
        self.answer_buttons = []
        for _ in range(4):
            btn = ttk.Button(self.question_frame, width=30, 
                           command=lambda i=_: self.check_answer(i))
            btn.pack(pady=5)
            self.answer_buttons.append(btn)

        # Score and controls
        self.score_label = ttk.Label(frame, text="Score: 0/0", font=('Arial', 12))
        self.score_label.pack(pady=10)

        self.next_btn = ttk.Button(frame, text="Next Question", 
                                 command=self.next_question, state='disabled')
        self.next_btn.pack(pady=10)

        # Initialize quiz data
        self.prepare_quiz_data()
        self.show_question()

    def prepare_quiz_data(self):
        """Create quiz questions from alphabet words"""
        for letter, words in self.alphabet_words.items():
            for word in words:
                german, english = word.split(' (')
                english = english.rstrip(')')
                self.quiz_data.append({
                    'german': german,
                    'english': english,
                    'image': self.alphabet_images.get(german)
                })

    def show_question(self):
        """Display a new question"""
        if not self.quiz_data:
            messagebox.showinfo("Quiz Complete", f"Final Score: {self.score}/{len(self.quiz_data)}")
            return

        # Get random question
        self.current_q = random.choice(self.quiz_data)
        self.quiz_data.remove(self.current_q)

        # Set question text and image
        self.question_label.config(text=f"What is '{self.current_q['german']}' in English?")
        if self.current_q['image']:
            self.quiz_image_label.config(image=self.current_q['image'])
        else:
            self.quiz_image_label.config(image='')

        # Generate answer options
        correct_answer = self.current_q['english']
        wrong_answers = random.sample(
            [w['english'] for w in self.quiz_data if w['english'] != correct_answer], 3
        )
        options = random.sample([correct_answer] + wrong_answers, 4)

        # Update answer buttons
        for i, btn in enumerate(self.answer_buttons):
            btn.config(text=options[i], state='normal')

        # Update score display
        self.score_label.config(text=f"Score: {self.score}/{self.current_question}")
        self.next_btn.config(state='disabled')

    def check_answer(self, selected_index):
        """Check selected answer"""
        selected_answer = self.answer_buttons[selected_index].cget('text')
        correct = selected_answer == self.current_q['english']

        # Visual feedback
        for i, btn in enumerate(self.answer_buttons):
            if btn.cget('text') == self.current_q['english']:
                btn.config(style='Correct.TButton' if correct else 'TButton')
            else:
                btn.config(state='disabled')

        # Update score
        self.current_question += 1
        if correct:
            self.score += 1
        self.score_label.config(text=f"Score: {self.score}/{self.current_question}")
        self.next_btn.config(state='normal')

    def next_question(self):
        """Load next question"""
        if self.quiz_data:
            self.show_question()
        else:
            messagebox.showinfo("Quiz Complete", f"Final Score: {self.score}/{self.current_question}")

    def setup_styles(self):
        """Setup ttk styles for the application"""
        style = ttk.Style()
        
        # Base styles
        style.configure('TButton', padding=6, relief="flat", background="#ccc")
        style.configure('TLabel', padding=3)
        style.configure('TNotebook', padding=2)
        style.configure('TNotebook.Tab', padding=[10, 2])
        style.configure('TFrame', background='white')
        
        # Quiz-specific styles
        style.configure('Correct.TButton', background='#90EE90', foreground='black')
        style.map('Correct.TButton', 
                background=[('active', '#76C576'), ('disabled', '#90EE90')])
        
    def setup_write_tab(self):
        frame = ttk.Frame(self.write_tab.scrollable_frame)
        frame.pack(pady=20, padx=20, fill='both', expand=True)

        self.write_phrases = {
            'My name is Adam': 'Ich heiße Adam',
            'I am 7 years old': 'Ich bin sieben Jahre alt',
            'I have one brother': 'Ich habe einen Bruder',
            'I go to school by bus': 'Ich fahre mit dem Bus zur Schule',
            'I want to be a soldier': 'Ich möchte Soldat werden',
            'I prefer blue colour': 'Ich mag blaue Farbe',
            'I love my teacher': 'Ich liebe meine Lehrerin',
            'I like to eat Pizza': 'Ich esse gerne Pizza'
        }

        # Instructions
        ttk.Label(frame, 
                text="Enter German translation and select matching English phrase:",
                font=('Arial', 12, 'bold')).pack(pady=10)

        # German input field
        input_frame = ttk.Frame(frame)
        input_frame.pack(pady=10, fill='x')
        
        ttk.Label(input_frame, text="German Phrase:").pack(side='left', padx=5)
        self.german_input = StringVar()
        entry = ttk.Entry(input_frame, textvariable=self.german_input, width=40)
        entry.pack(side='left', padx=5, fill='x', expand=True)

        # English phrase selection
        self.selected_english = StringVar()
        phrases_frame = ttk.Frame(frame)
        phrases_frame.pack(pady=10, fill='x')

        ttk.Label(phrases_frame, text="Select English phrase:").pack(anchor='w')
        
        for english in self.write_phrases.keys():
            rb = ttk.Radiobutton(
                phrases_frame,
                text=english,
                variable=self.selected_english,
                value=english
            )
            rb.pack(anchor='w', pady=2)

        # Control buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Check", 
                 command=self.check_translation).pack(side='left', padx=5)
        
        ttk.Button(btn_frame, text="Clear",
                 command=self.clear_translation).pack(side='left', padx=5)

        # Result display
        self.result_label = ttk.Label(frame, text="", font=('Arial', 12))
        self.result_label.pack(pady=10)

    def check_translation(self):
        entered_german = self.german_input.get().strip()
        selected_english = self.selected_english.get()
        
        if not entered_german:
            self.result_label.config(text="Please enter a German phrase!", foreground='red')
            return
            
        if not selected_english:
            self.result_label.config(text="Please select an English phrase!", foreground='red')
            return

        correct_german = self.write_phrases[selected_english]
        if entered_german == correct_german:
            self.result_label.config(text="✓ Correct! Well done!", foreground='green')
        else:
            self.result_label.config(
                text=f"✗ Incorrect. Correct translation:\n{correct_german}",
                foreground='red'
            )

    def clear_translation(self):
        self.german_input.set("")
        self.selected_english.set("")
        self.result_label.config(text="")

    
def main():
    root = tk.Tk()
    app = GermanLearningApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
