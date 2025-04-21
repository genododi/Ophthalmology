import os
import textwrap
from datetime import datetime, date, timedelta
import subprocess
import sys
import site
import time
import qrcode
from PIL import Image
import re
import socket
import json
import threading
import tempfile
import calendar
import webbrowser
from tkinter import font as tkfont
import sqlite3


# Add PyPDF2 for PDF merging
try:
    from PyPDF2 import PdfReader, PdfWriter
except ImportError:
    print("PyPDF2 not available. PDF export may have limited functionality.")
    print("Install with: pip install PyPDF2")

# Third-party imports
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext  # Add scrolledtext here
import sqlite3

# ReportLab imports
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics import renderPDF
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
# Add these new imports
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT  # Add TA_RIGHT and TA_LEFT
from reportlab.platypus.tables import Table, TableStyle
from reportlab.lib import colors

# Arabic text handling
ARABIC_SUPPORT = True

def setup_arabic_support():
    """Setup Arabic support by ensuring required packages are installed"""
    try:
        # Try to import required packages
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            print("Arabic support packages already installed")
            return True
        except ImportError:
            print("Arabic support packages not found, attempting to install...")
            
            # Check if pip is available
            try:
                import pip
            except ImportError:
                print("pip not available, cannot install required packages")
                return False
                
            # Install required packages
            import subprocess
            import sys
            
            # Use the same Python executable that's running this script
            python_executable = sys.executable
            
            # Install packages
            packages = ["python-bidi", "arabic-reshaper"]
            for package in packages:
                print(f"Installing {package}...")
                try:
                    subprocess.check_call([python_executable, "-m", "pip", "install", package])
                except subprocess.CalledProcessError as e:
                    print(f"Failed to install {package}: {e}")
                    return False
                    
            # Verify installation
            try:
                import arabic_reshaper
                from bidi.algorithm import get_display
                print("Arabic support packages successfully installed")
                return True
            except ImportError:
                print("Failed to import packages after installation")
                return False
                
    except Exception as e:
        print(f"Error setting up Arabic support: {e}")
        return False

# Try to setup Arabic support
ARABIC_SUPPORT = setup_arabic_support()

def process_arabic_text(text, is_pdf=False):
    """Process text with Arabic support, handling mixed LTR/RTL content with enhanced rendering"""
    if not text or not ARABIC_SUPPORT:
        return text
        
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        
        # Create a configured reshaper instance instead of passing configuration directly
        # This is the correct way to use arabic_reshaper with configuration
        try:
            # Use ArabicReshaper class with configuration
            from arabic_reshaper import ArabicReshaper
            
            # Define enhanced configuration
            config = {
                'delete_harakat': False,      # Keep diacritics
                'support_ligatures': True,    # Support Arabic ligatures
                'use_unshaped_instead_of_isolated': True,  # Better handling of isolated characters
                'delete_tatweel': False,      # Keep tatweel character
                'shift_harakat_position': False, # Don't shift harakat positions
                'support_zwj': True,          # Support Zero Width Joiner
            }
            
            # Create a reshaper with our configuration
            reshaper = ArabicReshaper(config)
            
            # Improved Arabic character detection including full range
            def is_arabic_char(char):
                # Basic Arabic (0600-06FF)
                # Arabic Supplement (0750-077F)
                # Arabic Extended-A (08A0-08FF)
                # Arabic Presentation Forms-A (FB50-FDFF)
                # Arabic Presentation Forms-B (FE70-FEFF)
                # Thaana (0780-07BF) - for embedded Arabic in other scripts
                return (
                    ('\u0600' <= char <= '\u06FF') or  # Basic Arabic
                    ('\u0750' <= char <= '\u077F') or  # Arabic Supplement
                    ('\u0780' <= char <= '\u07BF') or  # Thaana (sometimes contains Arabic)
                    ('\u08A0' <= char <= '\u08FF') or  # Arabic Extended-A
                    ('\uFB50' <= char <= '\uFDFF') or  # Arabic Presentation Forms-A
                    ('\uFE70' <= char <= '\uFEFF')     # Arabic Presentation Forms-B
                )
            
            # Check if text has Arabic content
            has_arabic = any(is_arabic_char(c) for c in text)
            
            if not has_arabic:
                return text
                
            # Always reshape Arabic text to ensure proper character forms
            reshaped = reshaper.reshape(text)
            
            # For PDF contexts, we need to apply bidirectional algorithm
            if is_pdf:
                # For mixed content, set a lower threshold to favor RTL display
                # This ensures Arabic-containing text is properly aligned from right to left
                return get_display(reshaped)
            else:
                # For non-PDF contexts, just return the reshaped text
                # This will be displayed based on the context's natural text direction
                return reshaped
                
        except ImportError:
            # Fall back to simple reshaping if ArabicReshaper class is not available
            print("Using simplified Arabic reshaping (ArabicReshaper class not available)")
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped) if is_pdf else reshaped
            
    except Exception as e:
        print(f"Arabic processing error: {e}")
        import traceback
        traceback.print_exc()
        return text

def setup_arabic_font():
    """Setup Arabic font with enhanced configuration and fallback options"""
    try:
        # Try to find Arabic fonts in common locations, prioritizing Amiri but with more options
        font_options = [
            # Amiri font options (preferred)
            {'name': 'Amiri', 'paths': [
                os.path.join(os.path.dirname(__file__), 'Amiri-Regular.ttf'),  # Local directory first
                '/Library/Fonts/Amiri-Regular.ttf',  # macOS
                'C:/Windows/Fonts/Amiri-Regular.ttf',  # Windows
                '/usr/share/fonts/truetype/amiri/amiri-regular.ttf',  # Linux
            ]},
            # Scheherazade font options (first fallback)
            {'name': 'Scheherazade', 'paths': [
                os.path.join(os.path.dirname(__file__), 'ScheherazadeNew-Regular.ttf'),
                '/Library/Fonts/ScheherazadeNew-Regular.ttf',
                'C:/Windows/Fonts/ScheherazadeNew-Regular.ttf',
                '/usr/share/fonts/truetype/sil/ScheherazadeNew-Regular.ttf',
            ]},
            # Noto Naskh Arabic (second fallback)
            {'name': 'NotoNaskhArabic', 'paths': [
                os.path.join(os.path.dirname(__file__), 'NotoNaskhArabic-Regular.ttf'),
                '/Library/Fonts/NotoNaskhArabic-Regular.ttf',
                'C:/Windows/Fonts/NotoNaskhArabic-Regular.ttf',
                '/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf',
            ]},
            # Dubai font (third fallback)
            {'name': 'Dubai', 'paths': [
                os.path.join(os.path.dirname(__file__), 'Dubai-Regular.ttf'),
                '/Library/Fonts/Dubai-Regular.ttf',
                'C:/Windows/Fonts/Dubai-Regular.ttf',
                '/usr/share/fonts/truetype/dubai/Dubai-Regular.ttf',
            ]},
            # IBM Plex Sans Arabic (fourth fallback)
            {'name': 'IBMPlexSansArabic', 'paths': [
                os.path.join(os.path.dirname(__file__), 'IBMPlexSansArabic-Regular.ttf'),
                '/Library/Fonts/IBMPlexSansArabic-Regular.ttf',
                'C:/Windows/Fonts/IBMPlexSansArabic-Regular.ttf',
                '/usr/share/fonts/truetype/ibm-plex/IBMPlexSansArabic-Regular.ttf',
            ]},
            # Any system Arabic font (last resort)
            {'name': 'ArabicSystem', 'paths': [
                '/System/Library/Fonts/ArabicUIDisplay.ttc',  # macOS system Arabic
                '/System/Library/Fonts/ArabicUIText.ttc',     # macOS system Arabic
                '/Library/Fonts/Arial Unicode.ttf',           # Common Unicode font with Arabic
            ]},
        ]
        
        # Try each font option
        for font_option in font_options:
            for font_path in font_option['paths']:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont('Arabic', font_path))
                    print(f"Found and registered Arabic font: {font_path}")
                    return 'Arabic', font_path
        
        # If no font found, download Amiri font
        print("Downloading Amiri font...")
        import urllib.request
        import tempfile
        import zipfile
        
        # Use a more reliable direct download link
        font_url = "https://github.com/alif-type/amiri/releases/download/1.0.0/Amiri-1.0.0.zip"
        local_font_path = os.path.join(os.path.dirname(__file__), 'Amiri-Regular.ttf')
        
        # Create a temporary directory for download
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "amiri.zip")
            
            # Download the font
            urllib.request.urlretrieve(font_url, zip_path)
            
            # Extract the font
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Find the regular font file
                for file in zip_ref.namelist():
                    if file.endswith('Amiri-Regular.ttf'):
                        # Extract to temp directory first
                        zip_ref.extract(file, temp_dir)
                        extracted_path = os.path.join(temp_dir, file)
                        
                        # Copy to final destination
                        import shutil
                        shutil.copy2(extracted_path, local_font_path)
                        break
                else:
                    # If Amiri not found in zip, try direct download of the TTF
                    direct_url = "https://github.com/alif-type/amiri/raw/master/fonts/ttf/Amiri-Regular.ttf"
                    urllib.request.urlretrieve(direct_url, local_font_path)
        
        # Register the downloaded font
        if os.path.exists(local_font_path):
            pdfmetrics.registerFont(TTFont('Arabic', local_font_path))
            print("Downloaded and registered Amiri font")
            return 'Arabic', local_font_path
        
        raise FileNotFoundError("Could not find or download any Arabic font")
        
    except Exception as e:
        print(f"Error setting up Arabic font: {e}")
        print("Using fallback font 'Helvetica'")
        # Ensure Helvetica is registered as a fallback
        return 'Helvetica', None

def arabic_text(text):
    """Handle Arabic text with proper reshaping and bidirectional support"""
    if not text or not ARABIC_SUPPORT:
        return text
    try:
        # Import here to avoid startup issues
        import arabic_reshaper
        from bidi.algorithm import get_display
        
        # Enhanced configuration for better letter joining and ligatures
        configuration = {
            'delete_harakat': False,      # Keep diacritics
            'support_ligatures': True,    # Support Arabic ligatures
            'COMPAT_DECOMPOSITION': False, # Don't decompose characters
            'use_unshaped_instead_of_isolated': True,  # Better handling of isolated characters
            'delete_tatweel': False,      # Keep tatweel character
            'shift_harakat_position': False, # Don't shift harakat positions
        }
        
        # Improved Arabic character detection
        def is_arabic_char(char):
            return (
                ('\u0600' <= char <= '\u06FF') or  # Basic Arabic
                ('\u0750' <= char <= '\u077F') or  # Arabic Supplement
                ('\u08A0' <= char <= '\u08FF') or  # Arabic Extended-A
                ('\uFB50' <= char <= '\uFDFF') or  # Arabic Presentation Forms-A
                ('\uFE70' <= char <= '\uFEFF')     # Arabic Presentation Forms-B
            )
        
        # Check if text is primarily Arabic
        arabic_char_count = sum(1 for c in text if is_arabic_char(c))
        is_primarily_arabic = arabic_char_count > len(text) * 0.3  # If more than 30% is Arabic
        
        # Reshape with enhanced configuration
        reshaped_text = arabic_reshaper.reshape(text, configuration)
        
        # Apply bidirectional algorithm if primarily Arabic
        if is_primarily_arabic:
            return get_display(reshaped_text)
        else:
            return reshaped_text
            
    except Exception as e:
        print(f"Error processing Arabic text '{text}': {e}")
        return text

# Initialize Arabic font with path
arabic_font, arabic_font_path = setup_arabic_font()

# Setup virtual environment
def setup_venv():
    """Setup virtual environment and required packages"""
    try:
        # Get the directory containing the script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Construct virtual environment paths
        venv_dir = os.path.join(base_dir, 'venv')
        if os.name == 'nt':  # Windows
            site_packages = os.path.join(venv_dir, 'Lib', 'site-packages')
            activate_script = os.path.join(venv_dir, 'Scripts', 'activate_this.py')
        else:  # macOS/Linux
            python_version = f'python{sys.version_info.major}.{sys.version_info.minor}'
            site_packages = os.path.join(venv_dir, 'lib', python_version, 'site-packages')
            activate_script = os.path.join(venv_dir, 'bin', 'activate_this.py')

        if not os.path.exists(venv_dir):
            print("\nVirtual environment not found!")
            print("Please run these commands in Terminal:")
            print(f"cd {base_dir}")
            print("python3 -m venv venv")
            print("source venv/bin/activate")
            print("pip install reportlab arabic-reshaper python-bidi\n")
            return False

        # Add site-packages to Python path
        if os.path.exists(site_packages):
            site.addsitedir(site_packages)
            print(f"Added virtual environment site-packages: {site_packages}")
            
            # Verify required packages
            try:
                import arabic_reshaper
                from bidi.algorithm import get_display
                print("Successfully imported Arabic support packages")
                return True
            except ImportError:
                print("\nRequired packages not found in virtual environment!")
                print("Please run these commands in Terminal:")
                print(f"cd {base_dir}")
                print("source venv/bin/activate")
                print("pip install reportlab arabic-reshaper python-bidi\n")
                return False
            
    except Exception as e:
        print(f"Virtual environment setup error: {e}")
    return False

# Try to setup virtual environment
if not setup_venv():
    print("\nPlease set up the virtual environment using these commands:")
    print("cd /Users/mahmoudsami/Desktop")
    print("python3 -m venv venv")
    print("source venv/bin/activate")
    print("pip install arabic-reshaper python-bidi reportlab\n")

# Now try importing Arabic support
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SUPPORT = True
    print("Arabic text support enabled")
except ImportError as e:
    print(f"\nArabic support import error: {e}")
    print("Please make sure you've activated the virtual environment and installed packages")
    ARABIC_SUPPORT = False

# Add virtual environment site-packages to Python path
venv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'venv')
if os.path.exists(venv_path):
    site_packages = os.path.join(
        venv_path,
        'lib',
        f'python{sys.version_info.major}.{sys.version_info.minor}',
        'site-packages'
    )
    sys.path.insert(0, site_packages)

def adapt_date(val):
    """Convert date to ISO format string for storage"""
    if isinstance(val, str):
        try:
            # Try to parse various date formats
            for fmt in ['%d %B %Y', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                try:
                    return datetime.strptime(val, fmt).date().isoformat()
                except ValueError:
                    continue
            raise ValueError(f"Unable to parse date: {val}")
        except ValueError:
            return None
    return val.isoformat() if val else None

def convert_date(val):
    """Convert date from SQLite format to Python date object"""
    if val is None:
        return None
    try:
        # Try ISO format first
        return date.fromisoformat(val.decode())
    except:
        try:
            # Try other common formats
            formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']
            for fmt in formats:
                try:
                    return datetime.strptime(val.decode(), fmt).date()
                except:
                    continue
            # If all fails, return the raw value
            return val
        except:
            return val
    
# Update SQLite configuration with explicit converters
sqlite3.register_adapter(date, adapt_date)
sqlite3.register_converter("DATE", convert_date)

def apply_theme(self):
    """Apply a modern theme to the application with RTL support"""
    # Set application style
    style = ttk.Style()
    
    # Try to use a modern theme if available
    try:
        if sys.platform.startswith('win'):
            style.theme_use('vista')
        elif sys.platform.startswith('darwin'):  # macOS
            style.theme_use('clam')
        else:  # Linux and others
            style.theme_use('clam')
    except:
        # Fallback to default
        pass
    
    # Configure common styles
    style.configure('TFrame', background='#f5f5f5')
    style.configure('TLabel', background='#f5f5f5', font=('Arial', 10))
    style.configure('TButton', font=('Arial', 10))
    style.configure('TNotebook', background='#f5f5f5', tabposition='n')
    style.configure('TNotebook.Tab', padding=[10, 5], font=('Arial', 10))
    
    # Configure treeview
    style.configure('Treeview',
                    background='#ffffff',
                    fieldbackground='#ffffff',
                    font=('Arial', 10))
    style.configure('Treeview.Heading', font=('Arial', 10, 'bold'))
    
    # Configure entry fields
    style.configure('TEntry', font=('Arial', 10))
    style.map('TEntry', fieldbackground=[('readonly', '#f0f0f0')])
    
    # Configure special buttons
    style.configure('Primary.TButton',
                   background='#4285f4',
                   foreground='white',
                   font=('Arial', 10, 'bold'))
    
    # Create RTL-specific styles
    style.configure('RTL.TLabel', anchor=tk.E, justify=tk.RIGHT)
    style.configure('RTL.TEntry', justify=tk.RIGHT)
    style.configure('RTL.TCombobox', justify=tk.RIGHT)
    
    # Apply colors to the main window
    self.parent.configure(background='#f5f5f5')
    
    # Create custom fonts with better Arabic support
    self.header_font = tkfont.Font(family="Arial", size=14, weight="bold")
    self.subheader_font = tkfont.Font(family="Arial", size=12, weight="bold")
    self.normal_font = tkfont.Font(family="Arial", size=10)
    self.small_font = tkfont.Font(family="Arial", size=9)
    
    # Try to load an Arabic-friendly font if available on the system
    try:
        # Check for common Arabic fonts
        arabic_fonts = ["Arial", "Tahoma", "Segoe UI", "Dubai", "Times New Roman"]
        for font_name in arabic_fonts:
            try:
                self.arabic_font = tkfont.Font(family=font_name, size=10)
                print(f"Using {font_name} for Arabic text display")
                break
            except:
                continue
    except Exception as e:
        print(f"Could not set Arabic font: {e}")

def setup_rtl_support(self):
    """Configure RTL support for Arabic text with enhanced rendering"""
    # Configure all text widgets to support RTL
    
    # Find all text widgets
    text_widgets = self.find_all_widgets(self.parent, tk.Text)
    for widget in text_widgets:
        # Enable bidirectional text support
        widget.configure(wrap=tk.WORD)
        
        # Configure RTL text tag with full styling
        widget.tag_configure("rtl", 
                            justify=tk.RIGHT,
                            lmargin1=20,  # Add margin for better readability
                            lmargin2=20,
                            rmargin=10)
        
        # Bind key events to detect Arabic input
        widget.bind("<KeyRelease>", lambda event, w=widget: self.detect_text_direction(event, w))
    
    # Find and configure all Entry widgets
    entry_widgets = self.find_all_widgets(self.parent, ttk.Entry) + self.find_all_widgets(self.parent, tk.Entry)
    for widget in entry_widgets:
        # Bind events to handle RTL input in entry widgets
        widget.bind("<KeyRelease>", lambda event, w=widget: self.handle_entry_rtl(event, w))
    
    # Configure comboboxes for RTL content
    combo_widgets = self.find_all_widgets(self.parent, ttk.Combobox)
    for widget in combo_widgets:
        # Add binding for RTL handling in comboboxes
        widget.bind("<KeyRelease>", lambda event, w=widget: self.handle_entry_rtl(event, w))

def handle_entry_rtl(self, event, widget):
    """Handle RTL text direction for Entry widgets"""
    text = widget.get()
    
    # Check if entry contains Arabic text
    def is_arabic(char):
        return '\u0600' <= char <= '\u06FF' or '\uFB50' <= char <= '\uFDFF' or '\uFE70' <= char <= '\uFEFF'
    
    contains_arabic = any(is_arabic(c) for c in text)
    
    if contains_arabic:
        # Configure for RTL
        widget.configure(justify=tk.RIGHT)
    else:
        # Configure for LTR
        widget.configure(justify=tk.LEFT)

def process_arabic_text(self, text, is_pdf=False):
    """Process text with Arabic support for better rendering in UI and PDF"""
    if not text or not hasattr(self, 'arabic_support') or not self.arabic_support:
        return text
        
    try:
        # Enhanced reshaping parameters for better connected letters
        configuration = {
            'delete_harakat': False,      # Keep diacritics
            'support_ligatures': True,    # Support Arabic ligatures
            'COMPAT_DECOMPOSITION': False, # Don't decompose characters
            'use_unshaped_instead_of_isolated': True,  # Better handling of isolated characters
            'delete_tatweel': False,      # Keep tatweel character
            'shift_harakat_position': False, # Don't shift harakat positions
        }
        
        # For PDF output we need full bidirectional processing
        if is_pdf:
            reshaped_text = self.arabic_reshaper.reshape(text, configuration)
            return self.get_display(reshaped_text)
        else:
            # For UI text, sometimes just reshaping is better for editable fields
            return self.arabic_reshaper.reshape(text, configuration)
            
    except Exception as e:
        print(f"Error processing Arabic text: {e}")
        import traceback
        traceback.print_exc()
        return text

def create_enhanced_arabic_field(self, parent, label_text, variable=None, width=20, readonly=False):
    """Create an entry field with enhanced RTL support"""
    frame = ttk.Frame(parent)
    
    # Create a label with RTL support
    label = ttk.Label(frame, text=label_text, anchor=tk.E)
    label.pack(side=tk.RIGHT, padx=(5, 0))
    
    # Create an entry with RTL support
    if variable:
        entry = ttk.Entry(frame, textvariable=variable, width=width)
    else:
        entry = ttk.Entry(frame, width=width)
        
    if readonly:
        entry.configure(state="readonly")
        
    entry.pack(side=tk.RIGHT)
    
    # Bind RTL detection
    entry.bind("<KeyRelease>", lambda event: self.handle_entry_rtl(event, entry))
    
    # Initially check if we need RTL
    if variable and variable.get():
        text = variable.get()
        def is_arabic(char):
            return '\u0600' <= char <= '\u06FF' or '\uFB50' <= char <= '\uFDFF' or '\uFE70' <= char <= '\uFEFF'
        
        if any(is_arabic(c) for c in text):
            entry.configure(justify=tk.RIGHT)
    
    return frame, entry

def find_all_widgets(self, parent, widget_type):
    """Find all widgets of a specific type"""
    result = []
    for widget in parent.winfo_children():
        if isinstance(widget, widget_type):
            result.append(widget)
        result.extend(self.find_all_widgets(widget, widget_type))
    return result

def detect_text_direction(self, event, widget):
    """Detect if text is Arabic to apply RTL styling with improved accuracy"""
    text = widget.get("1.0", tk.END)
    
    # Improved Arabic character detection including full Unicode ranges
    def is_arabic_char(char):
        # Basic Arabic (0600-06FF)
        # Arabic Supplement (0750-077F)
        # Arabic Extended-A (08A0-08FF)
        # Arabic Presentation Forms-A (FB50-FDFF)
        # Arabic Presentation Forms-B (FE70-FEFF)
        return (
            ('\u0600' <= char <= '\u06FF') or  # Basic Arabic
            ('\u0750' <= char <= '\u077F') or  # Arabic Supplement
            ('\u08A0' <= char <= '\u08FF') or  # Arabic Extended-A
            ('\uFB50' <= char <= '\uFDFF') or  # Arabic Presentation Forms-A
            ('\uFE70' <= char <= '\uFEFF')     # Arabic Presentation Forms-B
        )
    
    # Calculate percentage of Arabic characters
    arabic_chars = sum(is_arabic_char(c) for c in text)
    total_chars = len(text.strip())
    
    # Apply RTL if more than 20% of text is Arabic (better threshold for mixed content)
    if total_chars > 0 and (arabic_chars / total_chars) > 0.2:
        widget.tag_add("rtl", "1.0", tk.END)
        # Configure text alignment for RTL
        widget.tag_configure("rtl", justify=tk.RIGHT)
    else:
        widget.tag_remove("rtl", "1.0", tk.END)

def create_rounded_button(self, parent, text, command, width=10, bg="#4285f4", fg="white"):
    """Create a custom rounded button"""
    # Create a frame to hold the button
    frame = ttk.Frame(parent)
    
    # Create the button with a styled background
    button = tk.Button(
        frame,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        font=('Arial', 10, 'bold'),
        bd=0,
        width=width,
        padx=10,
        pady=5,
        cursor="hand2"
    )
    button.pack(padx=2, pady=2)
    
    # Add hover effect
    button.bind("<Enter>", lambda e: button.config(bg=self.adjust_color(bg, -20)))
    button.bind("<Leave>", lambda e: button.config(bg=bg))
    
    return frame

def adjust_color(self, hex_color, amount):
    """Adjust a hex color by the given amount (-255 to 255)"""
    r = max(0, min(255, int(hex_color[1:3], 16) + amount))
    g = max(0, min(255, int(hex_color[3:5], 16) + amount))
    b = max(0, min(255, int(hex_color[5:7], 16) + amount))
    return f"#{r:02x}{g:02x}{b:02x}"

class MainApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("Clinic Management System")
        
        # Set window size (80% of screen size)
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        
        # Position window in center of screen
        x_position = (screen_width - window_width) // 2
        y_position = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        
        # Initialize database connection
        self.db_path = self.get_database_path()
        self.conn = self.initialize_database()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create secretary module tab
        self.secretary_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.secretary_frame, text="Appointments | المواعيد")
        
        # Initialize secretary module
        self.secretary_module = SecretaryModule(self.secretary_frame, self)
        
        # Add status bar
        self.status_bar = ttk.Label(
            root,
            text="Ready | جاهز",
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Add menu
        self.create_menu()
        
        # Add this method to your __init__ to apply the improvements
        def init_ui_improvements(self):
            """Initialize UI improvements"""
            # Apply theme styling
            self.apply_theme()
            
            # Setup RTL support
            self.setup_rtl_support()
            
            # Make status bar more visible
            if hasattr(self, 'status_bar'):
                self.status_bar.configure(relief=tk.GROOVE, bd=1, background='#e0e0e0')
            
            # Apply some subtle animations (for button clicks)
            def animate_click(widget):
                orig_bg = widget["background"]
                widget.configure(background="#d0d0d0")
                widget.after(150, lambda: widget.configure(background=orig_bg))
            
            # Apply to all buttons
            for button in self.find_all_widgets(self.parent, tk.Button):
                button.bind("<Button-1>", lambda e: animate_click(e.widget))
            
            # Make the application responsive
            self.make_responsive()

        def make_responsive(self):
            """Make the main application window responsive"""
            # Configure main frame to expand
            for child in self.parent.winfo_children():
                if isinstance(child, ttk.Frame) or isinstance(child, tk.Frame):
                    child.pack(fill=tk.BOTH, expand=True)
            
            # Configure grid weights in main frames
            for frame in self.find_all_widgets(self.parent, ttk.Frame):
                rows, cols = frame.grid_size()
                for i in range(rows):
                    frame.rowconfigure(i, weight=1)
                for i in range(cols):
                    frame.columnconfigure(i, weight=1)
        
    def get_database_path(self):
        """Get the path to the database file"""
        # Use the same directory as this script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, "clinic_database.db")
    
    def initialize_database(self):
        """Initialize database connection"""
        try:
            # Connect to database with foreign key support
            conn = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Create patients table if it doesn't exist (required for appointments)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS patients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    date_of_birth DATE,
                    gender TEXT,
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    medical_history TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            
            print(f"Database initialized at {self.db_path}")
            return conn
        except Exception as e:
            messagebox.showerror(
                "Database Error",
                f"Failed to initialize database: {e}"
            )
            sys.exit(1)
    
    def create_menu(self):
        """Create application menu bar"""
        menu_bar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="📄 طباعة الجدول | Print Schedule",
                             command=self.secretary_module.print_schedule)
        file_menu.add_separator()
        file_menu.add_command(label="🚪 خروج | Exit", command=self.root.quit)
        menu_bar.add_cascade(label="📁 ملف | File", menu=file_menu)
        
        # Edit menu
        edit_menu = tk.Menu(menu_bar, tearoff=0)
        edit_menu.add_command(label="➕ إضافة موعد | Add Appointment",
                             command=self.secretary_module.add_appointment)
        edit_menu.add_command(label="✏️ تعديل موعد | Edit Appointment",
                             command=self.secretary_module.edit_appointment)
        edit_menu.add_command(label="❌ إلغاء موعد | Cancel Appointment",
                             command=self.secretary_module.cancel_appointment)
        menu_bar.add_cascade(label="📝 تحرير | Edit", menu=edit_menu)
        
        # View menu
        view_menu = tk.Menu(menu_bar, tearoff=0)
        view_menu.add_command(label="📅 اليوم | Today",
                             command=self.secretary_module.go_to_today)
        view_menu.add_command(label="🔄 تحديث | Refresh",
                             command=self.secretary_module.update_appointments)
        menu_bar.add_cascade(label="👁️ عرض | View", menu=view_menu)
        
        # Help menu
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="ℹ️ حول | About", command=self.show_about)
        menu_bar.add_cascade(label="❓ مساعدة | Help", menu=help_menu)
        
        self.root.config(menu=menu_bar)
    
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo(
            "About | حول",
            "Clinic Management System\nVersion 1.0\n\n"
            "© 2023 Your Clinic"
        )
    
    def on_closing(self):
        """Handle window closing event"""
        if messagebox.askokcancel("Quit | خروج", "Are you sure you want to quit? | هل أنت متأكد من الخروج؟"):
            # Close database connection
            if self.conn:
                self.conn.close()
            self.root.destroy()
            
class SecretaryModule:
    def __init__(self, parent, main_app):
        """Initialize the secretary module for appointment booking"""
        self.parent = parent
        self.main_app = main_app
        
        # Set up SQLite connection with proper row factory for dictionary access
        if hasattr(main_app, 'conn'):
            self.conn = main_app.conn
            # Set row_factory for dictionary-like access
            self.conn.row_factory = sqlite3.Row
        else:
            # Create a new connection
            # sqlite3 is now imported at the top of the file
            
            # Register adapters and converters
            sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
            sqlite3.register_adapter(date, lambda d: d.isoformat())
            
            # Connect to database with row_factory set for dictionary access
            self.conn = sqlite3.connect('clinic_database.db',
                                       detect_types=sqlite3.PARSE_DECLTYPES,
                                       check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
        
        self.selected_date = datetime.now().date()
        self.selected_appointment_id = None
        self.arabic_font = None  # Will be set if Arabic support is enabled
        
        # Check for Arabic support - REVERT TO ORIGINAL APPROACH
        self.arabic_support = False
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            self.arabic_reshaper = arabic_reshaper
            self.get_display = get_display
            self.arabic_support = True
            # Try to register Arabic font for PDF
            try:
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont
                # Try common Arabic font locations
                for font_path in [
                    "/usr/share/fonts/truetype/arabic/arabeyes-fonts/ae_Arab.ttf",
                    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                    "/Library/Fonts/Arial.ttf",  # macOS
                    "/Library/Fonts/ArialUnicode.ttf",
                    "/System/Library/Fonts/Arial Unicode.ttf",
                    "C:\\Windows\\Fonts\\arial.ttf",  # Windows
                    "C:\\Windows\\Fonts\\arialuni.ttf",
                ]:
                    if os.path.exists(font_path):
                        pdfmetrics.registerFont(TTFont('Arabic', font_path))
                        self.arabic_font = 'Arabic'
                        break
            except:
                pass
        except ImportError:
            pass
        
        # Initialize database tables
        self.initialize_database()
        
        # Initialize time slots (every 15 minutes from 9 AM to 5 PM)
        self.time_slots = []
        for hour in range(9, 18):
            for minute in [0, 15, 30, 45]:
                self.time_slots.append(f"{hour:02d}:{minute:02d}")
        
        # Common appointment durations in minutes
        self.durations = [15, 30, 45, 60, 90, 120]
        
        # Common reasons for visits with emojis
        self.common_reasons = [
            "🔍 كشف | Examination",
            "🔄 متابعة | Follow-up",
            "💬 استشارة | Consultation",
            "⚕️ إجراء | Procedure",
            "🧪 تحاليل | Lab Tests",
            "📷 أشعة | Radiology",
            "📝 تقرير طبي | Medical Report",
            "📌 أخرى | Other"
        ]
        
       # Status types with color codes and emojis
        self.status_types = {
            "⏳ قيد الانتظار | Pending": "#fff9c4",     # Light yellow
            "✅ مؤكد | Confirmed": "#e3f2fd",          # Light blue
            "🚶 تم الحضور | Arrived": "#e8f5e9",       # Light green
            "👨‍⚕️ قيد الكشف | In Progress": "#e1f5fe",   # Sky blue
            "✓ تم الكشف | Completed": "#f1f8e9",      # Lime green
            "❓ لم يحضر | No-show": "#fce4ec",         # Pink
            "❌ ملغي | Cancelled": "#ffebee"           # Light red
        }
        
        # Setup UI
        self.setup_ui()
        
        # Initialize tooltips
        self.setup_tooltips()
        
        # Setup keyboard shortcuts
        self.setup_shortcuts()
        
        # Check for appointments today and show summary
        self.show_daily_summary()

    def setup_ui(self):
        """Setup the user interface for the secretary module with improved layout"""
        # Create main frame with padding
        self.main_frame = ttk.Frame(self.parent, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add dashboard at the top
        self.setup_dashboard()
        
        # Create paned window for resizable sections
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Create left and right panes
        self.left_pane = ttk.Frame(self.paned_window)
        self.right_pane = ttk.Frame(self.paned_window)
        
        # Add panes to paned window
        self.paned_window.add(self.left_pane, weight=1)
        self.paned_window.add(self.right_pane, weight=1)
        
        # Setup calendar view directly in left pane
        self.setup_calendar()
        
        # Setup appointments view
        self.setup_appointments_view()
        
        # Setup appointment form
        self.setup_appointment_form()
        
        # Setup search results
        self.setup_search_results()
        
        # Setup waiting list
        self.setup_waiting_list()
        
        # Setup status bar
        self.setup_status_bar()
        
        # Update the calendar and appointments
        self.update_calendar()
        self.update_appointments()
        
    def setup_dashboard(self):
        """Add a dashboard with quick statistics and actions"""
        dashboard = ttk.LabelFrame(self.main_frame, text="📊 لوحة المعلومات | Dashboard")
        dashboard.pack(fill=tk.X, pady=(0, 10))
        
        # Create grid layout for dashboard
        dashboard_grid = ttk.Frame(dashboard)
        dashboard_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Today's date display
        date_frame = ttk.Frame(dashboard_grid)
        date_frame.grid(row=0, column=0, padx=10, sticky="w")
        
        today = datetime.now().date()
        day_name = today.strftime("%A")
        date_str = today.strftime("%Y-%m-%d")
        
        ttk.Label(
            date_frame,
            text=f"📅 اليوم | Today: {day_name}",
            font=("Arial", 12, "bold")
        ).pack(anchor="w")
        ttk.Label(
            date_frame,
            text=date_str,
            font=("Arial", 10)
        ).pack(anchor="w")
        
        # Today's appointments counter
        self.today_count_var = tk.StringVar(value="0")
        counter_frame = ttk.Frame(dashboard_grid)
        counter_frame.grid(row=0, column=1, padx=10)
        
        ttk.Label(
            counter_frame,
            text="🗓️ عدد المواعيد | Appointments:",
            font=("Arial", 10)
        ).pack(side=tk.LEFT)
        ttk.Label(
            counter_frame,
            textvariable=self.today_count_var,
            font=("Arial", 12, "bold"),
            foreground="blue"
        ).pack(side=tk.LEFT, padx=5)
        
        # Waiting patients counter
        self.waiting_count_var = tk.StringVar(value="0")
        waiting_frame = ttk.Frame(dashboard_grid)
        waiting_frame.grid(row=0, column=2, padx=10)
        
        ttk.Label(
            waiting_frame,
            text="⏱️ في الانتظار | Waiting:",
            font=("Arial", 10)
        ).pack(side=tk.LEFT)
        ttk.Label(
            waiting_frame,
            textvariable=self.waiting_count_var,
            font=("Arial", 12, "bold"),
            foreground="green"
        ).pack(side=tk.LEFT, padx=5)
        
        # Quick actions frame
        actions_frame = ttk.Frame(dashboard_grid)
        actions_frame.grid(row=0, column=3, padx=10, sticky="e")
        
        ttk.Button(
            actions_frame,
            text="✚ موعد جديد | New Appointment",
            style="Accent.TButton",
            command=self.add_appointment
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            actions_frame,
            text="🔍 بحث متقدم | Advanced Search",
            command=self.advanced_search
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            actions_frame,
            text="⏱️ وصول مريض | Check-in",
            command=self.patient_checkin
        ).pack(side=tk.LEFT, padx=5)
        
        # Set column weights
        for i in range(4):
            dashboard_grid.columnconfigure(i, weight=1)

    def parse_date(self, date_str):
        """Safely parse a date string into a date object"""
        if not date_str:
            return None
            
        try:
            # First try direct ISO format
            return date.fromisoformat(date_str)
        except ValueError:
            # Then try with datetime strptime
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                try:
                    # Try other common formats
                    for fmt in ['%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y']:
                        try:
                            return datetime.strptime(date_str, fmt).date()
                        except ValueError:
                            continue
                            
                    # If we get here, no format worked
                    print(f"Date parsing error: could not parse '{date_str}' as a date")
                    return None
                except Exception as e:
                    print(f"Date parsing error: {e} for value: {date_str}")
                    return None
    
    def setup_calendar(self):
        """Setup calendar panel"""
        # Create calendar frame if it doesn't exist
        self.cal_frame = ttk.Frame(self.main_frame)
        self.cal_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Set current date
        today = datetime.now().date()
        self.cal_year = today.year
        self.cal_month = today.month
        self.selected_date = today
        
        # Calendar header frame
        header_frame = ttk.Frame(self.cal_frame)
        header_frame.pack(fill=tk.X)
        
        # Previous year button
        prev_year_btn = ttk.Button(
            header_frame,
            text="◀◀",
            width=4,
            command=self.prev_year
        )
        prev_year_btn.pack(side=tk.LEFT, padx=2)
        
        # Previous month button
        prev_month_btn = ttk.Button(
            header_frame,
            text="◀",
            width=4,
            command=self.prev_month
        )
        prev_month_btn.pack(side=tk.LEFT, padx=2)
        
        # Month/Year display
        self.calendar_title = ttk.Label(
            header_frame,
            text="",
            font=("Arial", 12, "bold"),
            anchor=tk.CENTER
        )
        self.calendar_title.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        # Next month button
        next_month_btn = ttk.Button(
            header_frame,
            text="▶",
            width=4,
            command=self.next_month
        )
        next_month_btn.pack(side=tk.LEFT, padx=2)
        
        # Next year button
        next_year_btn = ttk.Button(
            header_frame,
            text="▶▶",
            width=4,
            command=self.next_year
        )
        next_year_btn.pack(side=tk.LEFT, padx=2)
        
        # Days of week header
        days_frame = ttk.Frame(self.cal_frame)
        days_frame.pack(fill=tk.X, pady=(10, 5))
        
        days = ["S", "M", "T", "W", "T", "F", "S"]
        for i, day in enumerate(days):
            label = ttk.Label(
                days_frame,
                text=day,
                anchor=tk.CENTER,
                width=4,
                font=("Arial", 10, "bold")
            )
            label.grid(row=0, column=i, padx=1)
        
        # Calendar days
        self.cal_days_frame = ttk.Frame(self.cal_frame)
        self.cal_days_frame.pack(fill=tk.BOTH)
        
        # Create day buttons
        self.day_buttons = []
        for row in range(6):  # 6 weeks max in a month view
            for col in range(7):  # 7 days in a week
                btn = ttk.Button(
                    self.cal_days_frame,
                    text="",
                    width=4,
                    style="Calendar.TButton"
                )
                btn.grid(row=row, column=col, padx=1, pady=1)
                self.day_buttons.append(btn)
        
        # Update calendar to current month/year
        self.update_calendar()

    def update_end_time(self):
        """Update end time based on selected start time and duration"""
        try:
            # Get selected start time
            start_time = self.start_time_var.get()
            if not start_time:
                return
                
            # Get selected duration
            duration = self.duration_var.get() if hasattr(self, 'duration_var') else 30
            try:
                duration_minutes = int(duration)
            except ValueError:
                duration_minutes = 30  # Default to 30 minutes
                
            # Calculate end time
            start_hour, start_minute = map(int, start_time.split(':'))
            total_minutes = start_hour * 60 + start_minute + duration_minutes
            end_hour = total_minutes // 60
            end_minute = total_minutes % 60
            
            # Format end time
            end_time = f"{end_hour:02d}:{end_minute:02d}"
            
            # Update end time field
            if hasattr(self, 'end_time_var'):
                self.end_time_var.set(end_time)
                
        except Exception as e:
            print(f"Error updating end time: {e}")
    
    
    def update_calendar(self):
        """Update the calendar display for the current month/year"""
        # Update month/year labels
        month_names = [
            "📅 يناير | January", "📅 فبراير | February", "📅 مارس | March",
            "📅 أبريل | April", "📅 مايو | May", "📅 يونيو | June",
            "📅 يوليو | July", "📅 أغسطس | August", "📅 سبتمبر | September",
            "📅 أكتوبر | October", "📅 نوفمبر | November", "📅 ديسمبر | December"
        ]
        
        # Update title
        if hasattr(self, 'calendar_title'):
            self.calendar_title.config(text=f"{month_names[self.cal_month-1]} {self.cal_year}")
        
        # Update month and year variables if applicable
        if hasattr(self, 'month_var'):
            self.month_var.set(month_names[self.cal_month-1])
        if hasattr(self, 'year_var'):
            self.year_var.set(str(self.cal_year))
        
        # Get the calendar for this month
        cal = calendar.monthcalendar(self.cal_year, self.cal_month)
        
        # Get dates with appointments
        dates_with_appointments = self.get_dates_with_appointments(self.cal_year, self.cal_month)
        
        # Get today's date
        today = datetime.now().date()
        
        # Check if we have day buttons
        if not hasattr(self, 'day_buttons') or not self.day_buttons:
            print("No day buttons found, recreating calendar")
            self.setup_calendar()
            return
        
        # Update day buttons
        for btn_idx, btn in enumerate(self.day_buttons):
            # Reset button style
            btn.configure(
                text="",
                state=tk.DISABLED,
                style="Calendar.TButton"
            )
            
        # Fill in dates
        for week_idx, week in enumerate(cal):
            for day_idx, day in enumerate(week):
                if day != 0:
                    button_idx = week_idx * 7 + day_idx
                    
                    # Skip if button index out of range
                    if button_idx >= len(self.day_buttons):
                        continue
                    
                    # Enable button
                    self.day_buttons[button_idx].configure(
                        text=str(day),
                        state=tk.NORMAL
                    )
                    
                    # Bind click event
                    current_date = date(self.cal_year, self.cal_month, day)
                    self.day_buttons[button_idx].configure(
                        command=lambda d=current_date: self.select_date(d)
                    )
                    
                    # Check if this is today
                    if today.year == self.cal_year and today.month == self.cal_month and today.day == day:
                        self.day_buttons[button_idx].configure(style="Today.TButton")
                    
                    # Check if this is the selected date
                    if (hasattr(self, 'selected_date') and
                        self.selected_date.year == self.cal_year and
                        self.selected_date.month == self.cal_month and
                        self.selected_date.day == day):
                        self.day_buttons[button_idx].configure(style="Selected.TButton")
                    
                    # Check if this date has appointments
                    if day in dates_with_appointments:
                        # Apply special style or indicator
                        if (hasattr(self, 'selected_date') and
                            self.selected_date.year == self.cal_year and
                            self.selected_date.month == self.cal_month and
                            self.selected_date.day == day):
                            # This is the selected date with appointments
                            self.day_buttons[button_idx].configure(style="SelectedWithAppt.TButton")
                        elif today.year == self.cal_year and today.month == self.cal_month and today.day == day:
                            # This is today with appointments
                            self.day_buttons[button_idx].configure(style="TodayWithAppt.TButton")
                        else:
                            # Regular day with appointments
                            self.day_buttons[button_idx].configure(style="WithAppt.TButton")
    
    def prev_year(self):
        """Move to previous year in calendar"""
        self.cal_year -= 1
        self.update_calendar()
        self.set_status(f"📅 عرض تقويم {self.cal_year} | Viewing calendar for {self.cal_year}")

    def next_year(self):
        """Move to next year in calendar"""
        self.cal_year += 1
        self.update_calendar()
        self.set_status(f"📅 عرض تقويم {self.cal_year} | Viewing calendar for {self.cal_year}")

    def prev_month(self):
        """Move to previous month in calendar"""
        self.cal_month -= 1
        if self.cal_month < 1:
            self.cal_month = 12
            self.cal_year -= 1
        self.update_calendar()
        
        # Get month name for status
        month_names = [
            "يناير | January", "فبراير | February", "مارس | March",
            "أبريل | April", "مايو | May", "يونيو | June",
            "يوليو | July", "أغسطس | August", "سبتمبر | September",
            "أكتوبر | October", "نوفمبر | November", "ديسمبر | December"
        ]
        self.set_status(f"📅 عرض تقويم {month_names[self.cal_month-1]} {self.cal_year} | Viewing calendar for {month_names[self.cal_month-1]} {self.cal_year}")

    def next_month(self):
        """Move to next month in calendar"""
        self.cal_month += 1
        if self.cal_month > 12:
            self.cal_month = 1
            self.cal_year += 1
        self.update_calendar()
        
        # Get month name for status
        month_names = [
            "يناير | January", "فبراير | February", "مارس | March",
            "أبريل | April", "مايو | May", "يونيو | June",
            "يوليو | July", "أغسطس | August", "سبتمبر | September",
            "أكتوبر | October", "نوفمبر | November", "ديسمبر | December"
        ]
        self.set_status(f"📅 عرض تقويم {month_names[self.cal_month-1]} {self.cal_year} | Viewing calendar for {month_names[self.cal_month-1]} {self.cal_year}")

    def select_date(self, selected_date):
        """Handle date selection in calendar"""
        # Update selected date
        self.selected_date = selected_date
        
        # Update date display in appointment form
        if hasattr(self, 'date_var'):
            self.date_var.set(selected_date.strftime('%Y-%m-%d'))
        
        # Update calendar visual selection
        self.update_calendar()
        
        # Update appointments list for this date
        self.filter_appointments_by_date(selected_date)
        
        # Update status
        date_str = selected_date.strftime('%Y-%m-%d')
        self.set_status(f"📆 تم اختيار التاريخ: {date_str} | Selected date: {date_str}")

    def filter_appointments_by_date(self, filter_date):
        """Filter the appointments treeview to show only appointments for the selected date"""
        try:
            # Clear current appointments
            for item in self.appointments_tree.get_children():
                self.appointments_tree.delete(item)
            
            # Format date for query
            date_str = filter_date.strftime('%Y-%m-%d')
            
            # Query appointments for this date
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT a.id, a.patient_id, p.name, a.appointment_date, 
                       a.start_time, a.end_time, a.reason, a.status
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                WHERE a.appointment_date = ?
                ORDER BY a.start_time
            ''', (date_str,))
            
            # Insert appointments into treeview
            for appt in cursor.fetchall():
                appt_id, patient_id, name, appt_date, start_time, end_time, reason, status = appt
                
                # Process Arabic text if needed
                name = self.process_arabic_text(name) if name else ""
                reason = self.process_arabic_text(reason) if reason else ""
                status = self.process_arabic_text(status) if status else ""
                
                # Format time
                time_str = f"{start_time} - {end_time}" if start_time and end_time else ""
                
                # Add to treeview
                self.appointments_tree.insert(
                    "", "end", appt_id,
                    values=(patient_id, name, appt_date, time_str, reason, status)
                )
            
            # Update appointment count
            count = len(self.appointments_tree.get_children())
            if hasattr(self, 'appointments_count_var'):
                self.appointments_count_var.set(f"🗓️ المواعيد: {count} | Appointments: {count}")
            
        except Exception as e:
            print(f"Error filtering appointments: {e}")
            import traceback
            traceback.print_exc()
    
    
    def go_to_today(self):
        """Set the calendar to today's date"""
        # Get current date
        today = datetime.now().date()
        
        # Update calendar
        self.cal_year = today.year
        self.cal_month = today.month
        
        # Select today
        self.select_date(today)
        
        # Update calendar display
        self.update_calendar()

    def select_date(self, date_obj):
        """Select a date in the calendar"""
        # Update selected date
        self.selected_date = date_obj
        
        # Update appointments list for selected date
        self.update_appointments()
        
        # Update calendar (to refresh highlighting)
        self.update_calendar()
    
    def show_info(self, title, message):
        """Display information in a message box"""
        try:
            # Create a custom messagebox for better formatting
            info_window = tk.Toplevel(self.parent)
            info_window.title(title)
            info_window.geometry("500x400")
            info_window.resizable(True, True)
            
            # Add icon if running on Windows
            try:
                info_window.iconbitmap("icons/info.ico")
            except:
                pass  # Icon not crucial
                
            # Main frame with padding
            main_frame = ttk.Frame(info_window, padding=20)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Message area with scrollbar (text widget)
            text_frame = ttk.Frame(main_frame)
            text_frame.pack(fill=tk.BOTH, expand=True)
            
            # Scrollbar
            scrollbar = ttk.Scrollbar(text_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Text widget
            text_widget = tk.Text(
                text_frame,
                wrap=tk.WORD,
                padx=10,
                pady=10,
                font=("Arial", 11),
                yscrollcommand=scrollbar.set
            )
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=text_widget.yview)
            
            # Insert the message
            text_widget.insert(tk.END, message)
            text_widget.config(state=tk.DISABLED)  # Make read-only
            
            # Close button at the bottom
            ttk.Button(
                main_frame,
                text="✓ موافق | OK",
                command=info_window.destroy
            ).pack(pady=(15, 0))
            
            # Center the window
            info_window.update_idletasks()
            width = info_window.winfo_width()
            height = info_window.winfo_height()
            x = (info_window.winfo_screenwidth() // 2) - (width // 2)
            y = (info_window.winfo_screenheight() // 2) - (height // 2)
            info_window.geometry(f'{width}x{height}+{x}+{y}')
            
            # Make window modal
            info_window.transient(self.parent)
            info_window.grab_set()
            self.parent.wait_window(info_window)
            
        except Exception as e:
            # Fallback to standard messagebox if custom one fails
            print(f"Error showing custom info dialog: {e}, falling back to standard dialog")
            messagebox.showinfo(title, message)
    
    def set_duration(self, minutes):
        """Set appointment duration and calculate end time based on start time"""
        try:
            # Get current start time
            start_time = self.start_time_var.get()
            if not start_time:
                messagebox.showinfo(
                    "معلومات | Info",
                    "الرجاء اختيار وقت البدء أولاً | Please select start time first"
                )
                return
                
            # Parse start time (expecting HH:MM format)
            hours, mins = map(int, start_time.split(':'))
            
            # Create a datetime object for calculation
            # Use today's date as a base (the actual date doesn't matter for time calculation)
            start_dt = datetime.now().replace(hour=hours, minute=mins, second=0, microsecond=0)
            
            # Add duration
            end_dt = start_dt + timedelta(minutes=minutes)
            
            # Format end time as HH:MM
            end_time = end_dt.strftime("%H:%M")
            
            # Update end time field
            self.end_time_var.set(end_time)
            
            # Update duration variable
            self.duration_var.set(str(minutes))
            
        except Exception as e:
            messagebox.showerror(
                "خطأ | Error",
                f"خطأ في تعيين المدة: {e} | Error setting duration: {e}"
            )

    def setup_appointments_view(self):
        """Setup the appointments list view"""
        # Create a frame for appointments directly in the left pane
        appointments_frame = ttk.LabelFrame(self.left_pane, text="🗓️ مواعيد اليوم | Today's Appointments")
        appointments_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add toolbar for appointments
        toolbar = ttk.Frame(appointments_frame)
        toolbar.pack(fill=tk.X, pady=5)
        
        ttk.Button(toolbar, text="✚ إضافة موعد | Add",
                   command=self.add_appointment).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="✏️ تعديل | Edit",
                   command=self.edit_appointment).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="❌ إلغاء | Cancel",
                   command=self.cancel_appointment).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="👥 عرض المرضى | View Patients",
                   command=self.view_patients_by_date).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🔄 تحديث القائمة | Refresh",
                   command=self.update_appointments).pack(side=tk.RIGHT, padx=5)
        
        # Add appointment list
        tree_frame = ttk.Frame(appointments_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create treeview for appointments
        self.appointments_tree = ttk.Treeview(
            tree_frame,
            columns=("Time", "Patient", "Reason", "Status"),
            show="headings",
            selectmode="browse",
            yscrollcommand=scrollbar.set
        )
        self.appointments_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.appointments_tree.yview)
        
        # Configure columns
        self.appointments_tree.heading("Time", text="الوقت | Time")
        self.appointments_tree.heading("Patient", text="المريض | Patient")
        self.appointments_tree.heading("Reason", text="السبب | Reason")
        self.appointments_tree.heading("Status", text="الحالة | Status")
        
        # Set column widths
        self.appointments_tree.column("Time", width=100)
        self.appointments_tree.column("Patient", width=150)
        self.appointments_tree.column("Reason", width=150)
        self.appointments_tree.column("Status", width=100)
        
        # Create tags for status colors
        self.appointments_tree.tag_configure("normal", background="#ffffff")
        self.appointments_tree.tag_configure("confirmed", background="#e3f2fd")
        self.appointments_tree.tag_configure("arrived", background="#e8f5e9")
        self.appointments_tree.tag_configure("completed", background="#f1f8e9")
        self.appointments_tree.tag_configure("cancelled", background="#ffebee")
        self.appointments_tree.tag_configure("noshow", background="#fce4ec")
        
        # Bind events
        self.appointments_tree.bind("<Double-1>", self.edit_appointment)
        self.appointments_tree.bind("<Return>", self.edit_appointment)

    def setup_appointment_form(self):
        """Setup the appointment form for adding/editing appointments"""
        # Create appointment form in the right pane if it doesn't exist already
        if hasattr(self, 'appointment_form'):
            # Form already exists
            return
            
        self.appointment_form = ttk.LabelFrame(self.right_pane, text="📝 تفاصيل الموعد | Appointment Details")
        self.appointment_form.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create form fields
        form_frame = ttk.Frame(self.appointment_form)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Patient selection
        ttk.Label(form_frame, text="👤 المريض | Patient:").grid(row=0, column=0, sticky="w", pady=5)
        self.patient_var = tk.StringVar()
        self.patient_combo = ttk.Combobox(form_frame, textvariable=self.patient_var, width=30)
        self.patient_combo.grid(row=0, column=1, sticky="ew", pady=5)
        
        # Add patient button
        ttk.Button(form_frame, text="➕ مريض جديد | New Patient",
                  command=self.add_new_patient).grid(row=0, column=2, padx=5, pady=5)
        
        # Date selection
        ttk.Label(form_frame, text="📅 التاريخ | Date:").grid(row=1, column=0, sticky="w", pady=5)
        self.date_var = tk.StringVar(value=self.selected_date.strftime('%Y-%m-%d'))
        date_entry = ttk.Entry(form_frame, textvariable=self.date_var, width=15)
        date_entry.grid(row=1, column=1, sticky="w", pady=5)
        ttk.Button(form_frame, text="🗓️", width=3,
                  command=self.show_date_picker).grid(row=1, column=2, sticky="w", pady=5)
        
        # Day of week selection
        ttk.Label(form_frame, text="🗓️ يوم الأسبوع | Day:").grid(row=2, column=0, sticky="w", pady=5)
        day_frame = ttk.Frame(form_frame)
        day_frame.grid(row=2, column=1, columnspan=2, sticky="w", pady=5)
        
        self.day_vars = {}
        days = [
            ("S", "الأحد | Sunday"),
            ("M", "الإثنين | Monday"),
            ("T", "الثلاثاء | Tuesday"),
            ("W", "الأربعاء | Wednesday"),
            ("T", "الخميس | Thursday"),
            ("F", "الجمعة | Friday"),
            ("S", "السبت | Saturday")
        ]
        
        for i, (day_letter, day_name) in enumerate(days):
            self.day_vars[i] = tk.BooleanVar(value=False)
            day_btn = ttk.Checkbutton(
                day_frame,
                text=day_letter,
                variable=self.day_vars[i],
                command=lambda d=i: self.day_selected(d)
            )
            day_btn.pack(side=tk.LEFT, padx=2)
            # Add tooltip
            self.create_tooltip(day_btn, day_name)
        
        # Preselect current day of week based on selected date
        if hasattr(self, 'selected_date'):
            weekday = self.selected_date.weekday()
            # Convert from Monday=0 to Sunday=0 format
            sunday_based_weekday = (weekday + 1) % 7
            if sunday_based_weekday in self.day_vars:
                self.day_vars[sunday_based_weekday].set(True)
        
        # Time selection
        ttk.Label(form_frame, text="🕒 الوقت | Time:").grid(row=3, column=0, sticky="w", pady=5)
        time_frame = ttk.Frame(form_frame)
        time_frame.grid(row=3, column=1, columnspan=2, sticky="w", pady=5)
        
        # Start time
        ttk.Label(time_frame, text="من | From:").pack(side=tk.LEFT, padx=2)
        self.start_time_var = tk.StringVar()
        self.start_time_combo = ttk.Combobox(time_frame, textvariable=self.start_time_var, width=8)
        self.start_time_combo.pack(side=tk.LEFT, padx=2)
        self.start_time_combo['values'] = self.time_slots
        self.start_time_combo.bind("<<ComboboxSelected>>", lambda e: self.update_end_time())
        
        # End time
        ttk.Label(time_frame, text="إلى | To:").pack(side=tk.LEFT, padx=(10, 2))
        self.end_time_var = tk.StringVar()
        self.end_time_combo = ttk.Combobox(time_frame, textvariable=self.end_time_var, width=8)
        self.end_time_combo.pack(side=tk.LEFT, padx=2)
        self.end_time_combo['values'] = self.time_slots
        
        # Duration shortcuts
        ttk.Label(form_frame, text="⏱️ المدة | Duration:").grid(row=4, column=0, sticky="w", pady=5)
        duration_frame = ttk.Frame(form_frame)
        duration_frame.grid(row=4, column=1, columnspan=2, sticky="w", pady=5)
        
        self.duration_var = tk.StringVar()
        for duration in self.durations:
            btn = ttk.Button(
                duration_frame,
                text=f"{duration} min",
                width=6,
                command=lambda d=duration: self.set_duration(d)
            )
            btn.pack(side=tk.LEFT, padx=2)
        
        # Reason for visit
        ttk.Label(form_frame, text="🔍 سبب الزيارة | Reason:").grid(row=5, column=0, sticky="w", pady=5)
        self.reason_var = tk.StringVar()
        self.reason_combo = ttk.Combobox(form_frame, textvariable=self.reason_var, width=30)
        self.reason_combo.grid(row=5, column=1, columnspan=2, sticky="ew", pady=5)
        self.reason_combo['values'] = self.common_reasons
        
        # Notes
        ttk.Label(form_frame, text="📝 ملاحظات | Notes:").grid(row=6, column=0, sticky="nw", pady=5)
        self.notes_text = tk.Text(form_frame, width=30, height=4)
        self.notes_text.grid(row=6, column=1, columnspan=2, sticky="ew", pady=5)
        
        # Add scrollbar for notes
        notes_scroll = ttk.Scrollbar(form_frame, orient="vertical", command=self.notes_text.yview)
        notes_scroll.grid(row=6, column=3, sticky="ns", pady=5)
        self.notes_text.configure(yscrollcommand=notes_scroll.set)
        
        # Status
        ttk.Label(form_frame, text="📊 الحالة | Status:").grid(row=7, column=0, sticky="w", pady=5)
        self.status_var = tk.StringVar()
        self.status_combo = ttk.Combobox(form_frame, textvariable=self.status_var, width=30)
        self.status_combo.grid(row=7, column=1, columnspan=2, sticky="ew", pady=5)
        self.status_combo['values'] = list(self.status_types.keys())
        
        # Buttons
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=8, column=0, columnspan=3, pady=15)
        
        # Save button
        self.save_btn = ttk.Button(
            button_frame,
            text="💾 حفظ | Save",
            style="Accent.TButton",
            command=self.save_appointment
        )
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        # Cancel button
        self.cancel_btn = ttk.Button(
            button_frame,
            text="❌ إلغاء | Cancel",
            command=self.clear_form
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Delete button (hidden initially)
        self.delete_btn = ttk.Button(
            button_frame,
            text="🗑️ حذف | Delete",
            style="Danger.TButton",
            command=self.delete_appointment
        )
        
        # Add appointment ID field (hidden)
        self.appointment_id_var = tk.StringVar()
        
        # Configure form grid
        for i in range(9):
            form_frame.rowconfigure(i, weight=1)
        form_frame.columnconfigure(1, weight=1)
        
        # Load patients into combo
        self.load_patients()

    def load_patients(self):
        """Load patients into the patient selection combobox"""
        try:
            # Check if the patients combobox exists
            if not hasattr(self, 'patient_combo'):
                print("Patient combobox not found")
                return
                
            # Query all patients from database
            cursor = self.conn.cursor()
            
            # Check if patients table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='patients'")
            if not cursor.fetchone():
                print("Patients table does not exist yet")
                self.patient_combo['values'] = []
                return
                
            # Get patients
            cursor.execute("SELECT id, name FROM patients ORDER BY name")
            patients = cursor.fetchall()
            
            # Format for combobox (ID - Name)
            patient_values = []
            for patient_id, name in patients:
                # Format name with ID
                formatted_name = f"{patient_id} - {name}"
                
                # Process Arabic text if applicable
                if self.arabic_support and name:
                    if hasattr(self, 'get_display') and hasattr(self, 'arabic_reshaper'):
                        try:
                            reshaped = self.arabic_reshaper.reshape(name)
                            display_name = self.get_display(reshaped)
                            formatted_name = f"{patient_id} - {display_name}"
                        except:
                            pass
                            
                patient_values.append(formatted_name)
            
            # Update combobox values
            self.patient_combo['values'] = patient_values
            
            # Set status
            self.set_status(f"👥 تم تحميل {len(patients)} مريض | Loaded {len(patients)} patients")
            
        except Exception as e:
            print(f"Error loading patients: {e}")
            import traceback
            traceback.print_exc()
            
            # Set empty values as fallback
            if hasattr(self, 'patient_combo'):
                self.patient_combo['values'] = []
    
    def day_selected(self, day_index):
        """Handle day of week selection"""
        selected_day = day_index
        
        # Update the date field to the next occurrence of this day of week
        today = datetime.now().date()
        current_day = today.weekday()
        
        # Convert from Sunday=0 to Monday=0 format for calculation
        if selected_day == 0:  # Sunday
            selected_day_monday_based = 6
        else:
            selected_day_monday_based = selected_day - 1
        
        # Calculate days to add
        days_ahead = selected_day_monday_based - current_day
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        # Calculate the next occurrence
        next_occurrence = today + timedelta(days=days_ahead)
        
        # Update date field
        self.date_var.set(next_occurrence.strftime('%Y-%m-%d'))
        
        # Also update the selected date and calendar
        self.selected_date = next_occurrence
        self.update_calendar()
        
        # Show available slots for this day
        self.show_available_slots(next_occurrence)

    def show_available_slots(self, for_date):
        """Show available time slots for the selected date"""
        try:
            # Clear current values
            self.start_time_combo['values'] = []
            
            # Get all slots
            all_slots = self.time_slots.copy()
            
            # Query booked slots for this date
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT start_time, end_time 
                FROM appointments 
                WHERE appointment_date = ? 
                AND status NOT LIKE '%Cancelled%' AND status NOT LIKE '%ملغي%'
            ''', (for_date.strftime('%Y-%m-%d'),))
            
            # Get booked slots
            booked_slots = []
            for start, end in cursor.fetchall():
                # Find all slots between start and end
                start_idx = self.time_slots.index(start) if start in self.time_slots else -1
                end_idx = self.time_slots.index(end) if end in self.time_slots else -1
                
                if start_idx >= 0 and end_idx >= 0:
                    for i in range(start_idx, end_idx):
                        booked_slots.append(self.time_slots[i])
            
            # Remove booked slots from available slots
            available_slots = [slot for slot in all_slots if slot not in booked_slots]
            
            # Update combo values
            self.start_time_combo['values'] = available_slots
            
            # Update status
            weekday_names = ["الأحد | Sunday", "الإثنين | Monday", "الثلاثاء | Tuesday",
                             "الأربعاء | Wednesday", "الخميس | Thursday", "الجمعة | Friday", "السبت | Saturday"]
            weekday = for_date.weekday()
            # Convert to Sunday=0 format
            sunday_based_weekday = (weekday + 1) % 7
            weekday_name = weekday_names[sunday_based_weekday]
            
            slots_count = len(available_slots)
            self.set_status(f"🕒 {slots_count} مواعيد متاحة في {weekday_name}, {for_date.strftime('%Y-%m-%d')} | {slots_count} available slots on {weekday_name}, {for_date.strftime('%Y-%m-%d')}")
            
        except Exception as e:
            print(f"Error showing available slots: {e}")
            import traceback
            traceback.print_exc()

    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        def enter(event):
            # Create a toplevel window
            x, y, cx, cy = widget.bbox("insert")
            x = x + widget.winfo_rootx() + 25
            y = y + widget.winfo_rooty() + 25
            
            # Create a tooltip window
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            
            # Add a label with tooltip text
            tooltip_label = ttk.Label(
                self.tooltip,
                text=text,
                justify=tk.LEFT,
                background="#ffffd0",
                relief=tk.SOLID,
                borderwidth=1,
                padding=(5, 3)
            )
            tooltip_label.pack()
            
        def leave(event):
            # Destroy the tooltip window when mouse leaves
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
                delattr(self, 'tooltip')
        
        # Bind events to widget
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def setup_tooltips(self):
        """Set up tooltips for main UI elements"""
        # Calendar tooltips
        if hasattr(self, 'calendar_title'):
            self.create_tooltip(self.calendar_title, "التقويم الشهري | Monthly Calendar")
            
        # Buttons tooltips
        if hasattr(self, 'save_btn'):
            self.create_tooltip(self.save_btn, "حفظ تفاصيل الموعد | Save appointment details")
        if hasattr(self, 'cancel_btn'):
            self.create_tooltip(self.cancel_btn, "مسح النموذج | Clear the form")
        if hasattr(self, 'delete_btn'):
            self.create_tooltip(self.delete_btn, "حذف الموعد | Delete this appointment")
            
        # Calendar navigation tooltips
        for btn in getattr(self, 'day_buttons', []):
            if btn.cget("text"):
                # Only add tooltip for buttons with days
                self.create_tooltip(btn, "انقر لاختيار هذا اليوم | Click to select this day")
    
    def setup_search_results(self):
        """Setup enhanced search results panel"""
        self.search_results_frame = ttk.LabelFrame(self.right_pane, text="نتائج البحث | Search Results")
        self.search_results_frame.pack(fill=tk.BOTH, expand=False, pady=10)
        
        # Add toolbar for search results
        toolbar = ttk.Frame(self.search_results_frame)
        toolbar.pack(fill=tk.X, pady=5)
        
        # Add search field
        ttk.Label(toolbar, text="بحث سريع | Quick Search:").pack(side=tk.LEFT, padx=5)
        self.quick_search_var = tk.StringVar()
        quick_search = ttk.Entry(toolbar, textvariable=self.quick_search_var, width=20)
        quick_search.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        quick_search.bind('<KeyRelease>', self.filter_search_results)
        
        ttk.Button(
            toolbar,
            text="تحديث | Refresh",
            command=self.refresh_search_results
        ).pack(side=tk.RIGHT, padx=5)
        
        # Create treeview frame with scrollbar
        tree_frame = ttk.Frame(self.search_results_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar for search results
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create enhanced treeview for search results
        self.search_results_tree = ttk.Treeview(
            tree_frame,
            columns=("ID", "Name", "Phone", "Gender", "DOB"),
            show="headings",
            selectmode="browse",
            height=5,
            yscrollcommand=scrollbar.set
        )
        self.search_results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.search_results_tree.yview)
        
        # Configure columns
        self.search_results_tree.heading("ID", text="الرقم | ID")
        self.search_results_tree.heading("Name", text="الاسم | Name")
        self.search_results_tree.heading("Phone", text="الهاتف | Phone")
        self.search_results_tree.heading("Gender", text="الجنس | Gender")
        self.search_results_tree.heading("DOB", text="تاريخ الميلاد | DOB")
        
        # Set column widths
        self.search_results_tree.column("ID", width=50, anchor=tk.CENTER)
        self.search_results_tree.column("Name", width=150)
        self.search_results_tree.column("Phone", width=100)
        self.search_results_tree.column("Gender", width=80, anchor=tk.CENTER)
        self.search_results_tree.column("DOB", width=100, anchor=tk.CENTER)
        
        # Bind select event for search results
        self.search_results_tree.bind("<Double-1>", self.select_search_result)
        self.search_results_tree.bind("<Return>", self.select_search_result)

    def setup_waiting_list(self):
        """Setup waiting list view"""
        waiting_frame = ttk.LabelFrame(self.right_pane, text="⏱️ قائمة الانتظار | Waiting List")
        waiting_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Add toolbar for waiting list
        toolbar = ttk.Frame(waiting_frame)
        toolbar.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            toolbar,
            text="➕ إضافة مريض للانتظار | Add to Waiting",
            command=self.add_to_waiting_list
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            toolbar,
            text="▶️ بدء الكشف | Start Exam",
            command=self.start_examination
        ).pack(side=tk.LEFT, padx=5)
        
        # Create waiting list treeview
        tree_frame = ttk.Frame(waiting_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Waiting list treeview
        self.waiting_tree = ttk.Treeview(
            tree_frame,
            columns=("Position", "Name", "Time", "Reason", "Status"),
            show="headings",
            selectmode="browse",
            height=5,
            yscrollcommand=scrollbar.set
        )
        self.waiting_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.waiting_tree.yview)
        
        # Configure columns
        self.waiting_tree.heading("Position", text="الرقم | #")
        self.waiting_tree.heading("Name", text="الاسم | Name")
        self.waiting_tree.heading("Time", text="وقت الوصول | Arrival")
        self.waiting_tree.heading("Reason", text="السبب | Reason")
        self.waiting_tree.heading("Status", text="الحالة | Status")
        
        # Set column widths
        self.waiting_tree.column("Position", width=40, anchor=tk.CENTER)
        self.waiting_tree.column("Name", width=150)
        self.waiting_tree.column("Time", width=80, anchor=tk.CENTER)
        self.waiting_tree.column("Reason", width=120)
        self.waiting_tree.column("Status", width=100)
        
        # Color configurations
        self.waiting_tree.tag_configure("waiting", background="#fff9c4")    # Light yellow
        self.waiting_tree.tag_configure("urgent", background="#ffccbc")     # Light orange
        self.waiting_tree.tag_configure("in_progress", background="#e8f5e9") # Light green
        
        # Bind events
        self.waiting_tree.bind("<Double-1>", self.edit_waiting_patient)
        self.waiting_tree.bind("<Button-3>", self.show_waiting_menu)  # Right-click

    def setup_status_bar(self):
        """Setup status bar at the bottom of the application"""
        status_frame = ttk.Frame(self.parent)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Current user display
        self.user_label = ttk.Label(
            status_frame,
            text="👤 المستخدم: سكرتير | User: Secretary",
            border=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2)
        )
        self.user_label.pack(side=tk.LEFT, fill=tk.Y)
        
        # Database connection status
        conn_status = "🟢 متصل | Connected" if self.conn else "🔴 غير متصل | Disconnected"
        self.connection_label = ttk.Label(
            status_frame,
            text=f"قاعدة البيانات: {conn_status} | Database: {conn_status}",
            border=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2)
        )
        self.connection_label.pack(side=tk.LEFT, fill=tk.Y)
        
        # Status message
        self.status_label = ttk.Label(
            status_frame,
            text="✅ جاهز | Ready",
            border=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2)
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Date and time
        self.datetime_label = ttk.Label(
            status_frame,
            text="",
            border=1,
            relief=tk.SUNKEN,
            anchor=tk.E,
            padding=(5, 2)
        )
        self.datetime_label.pack(side=tk.RIGHT, fill=tk.Y)
        self.update_datetime()

    def update_datetime(self):
        """Update date and time in status bar"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.datetime_label.config(text=f"🕒 {current_time}")
        # Update every second
        self.parent.after(1000, self.update_datetime)
    
    def get_today_appointment_count(self):
        """Get the count of appointments for today"""
        try:
            cursor = self.conn.cursor()
            today = datetime.now().date().isoformat()
            
            cursor.execute('''
                SELECT COUNT(*) FROM appointments
                WHERE appointment_date = ?
                AND status NOT LIKE '%ملغي%' AND status NOT LIKE '%Cancelled%'
            ''', (today,))
            
            count = cursor.fetchone()[0]
            return count
        except Exception as e:
            print(f"Error getting today's appointment count: {e}")
            return 0
    
    def get_waiting_patients_count(self):
        """Get the count of patients currently waiting"""
        try:
            cursor = self.conn.cursor()
            today = datetime.now().date().isoformat()
            
            # Get patients who have arrived but haven't been seen
            cursor.execute('''
                SELECT COUNT(*) FROM appointments
                WHERE appointment_date = ?
                AND (status LIKE '%تم الحضور%' OR status LIKE '%Arrived%')
                AND status NOT LIKE '%تم الكشف%' AND status NOT LIKE '%Completed%'
                AND status NOT LIKE '%قيد الكشف%' AND status NOT LIKE '%In Progress%'
            ''', (today,))
            
            count = cursor.fetchone()[0]
            return count
        except Exception as e:
            print(f"Error getting waiting patients count: {e}")
            return 0
    
    def setup_tooltips(self):
        """Setup tooltips for better usability"""
        # We'll need to implement a tooltip class or use an existing one
        # For now, we'll just define what tooltips would be useful
        tooltips = {
            "add_button": "إضافة موعد جديد | Add a new appointment",
            "edit_button": "تعديل الموعد المحدد | Edit selected appointment",
            "cancel_button": "إلغاء الموعد المحدد | Cancel selected appointment",
            "search_button": "البحث عن مريض | Search for a patient",
            "calendar": "انقر على تاريخ لعرض المواعيد | Click on a date to view appointments",
            "waiting_list": "قائمة المرضى في الانتظار | List of waiting patients",
            "patient_name": "اسم المريض | Patient name",
            "appointment_time": "وقت الموعد | Appointment time",
            "appointment_duration": "مدة الموعد | Appointment duration",
            "save_button": "حفظ الموعد | Save appointment",
            "clear_button": "مسح النموذج | Clear form",
            "print_button": "طباعة بطاقة الموعد | Print appointment card"
        }
        
        # In real implementation, we would create tooltip objects here

    def setup_shortcuts(self):
        """Setup keyboard shortcuts for common operations"""
        # This would bind keyboard shortcuts to the main window
        # For example:
        # self.parent.bind("<Control-n>", lambda e: self.add_appointment())
        # self.parent.bind("<Control-s>", lambda e: self.save_appointment())
        # self.parent.bind("<Control-f>", lambda e: self.search_patient())
        # self.parent.bind("<Control-p>", lambda e: self.print_schedule())
        # self.parent.bind("<F5>", lambda e: self.update_appointments())
        pass  # We'll implement this later or as needed

    def show_daily_summary(self):
        """Show daily appointments summary"""
        # Update count with emoji
        today_count = self.get_today_appointment_count()
        self.today_count_var.set(f"{today_count}")
        
        # Update waiting count
        waiting_count = self.get_waiting_patients_count()
        self.waiting_count_var.set(f"{waiting_count}")
        
        # Only show message if we have appointments
        if today_count > 0:
            message = f"🗓️ لديك {today_count} مواعيد اليوم | You have {today_count} appointments today"
            if waiting_count > 0:
                message += f"\n⏱️ {waiting_count} مرضى في الانتظار | {waiting_count} patients waiting"
            self.show_info("ملخص اليوم | Daily Summary", message)
            
        try:
            # Count today's appointments
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM appointments 
                WHERE appointment_date = ?
            ''', (datetime.now().date().isoformat(),))
            count = cursor.fetchone()[0]
            
            # Update dashboard
            self.today_count_var.set(str(count))
            
            # Set waiting count to 0 (will be updated later)
            self.waiting_count_var.set("0")
            
            # Display helpful message in status bar
            if count > 0:
                self.set_status(f"اليوم لديك {count} مواعيد | You have {count} appointments today")
            else:
                self.set_status("لا يوجد مواعيد لليوم | No appointments for today")
                
        except Exception as e:
            print(f"Error showing daily summary: {e}")

    def set_status(self, message):
        """Set status bar message with emoji"""
        if hasattr(self, 'status_var'):
            self.status_var.set(message)
        else:
            # Fallback if status bar not available
            print(message)

    # New helper methods for improved functionality

    def add_to_waiting_list(self):
        """Add a patient to the waiting list"""
        try:
            # Check if a patient is selected
            if not self.patient_var.get():
                messagebox.showwarning(
                    "No Patient Selected | لم يتم اختيار مريض",
                    "Please select a patient to add to the waiting list | الرجاء اختيار مريض لإضافته إلى قائمة الانتظار"
                )
                return
                
            # Extract patient ID and name
            patient_info = self.patient_var.get()
            patient_id = None
            patient_name = patient_info
            
            # Try to parse ID - Name format
            if " - " in patient_info:
                parts = patient_info.split(" - ", 1)
                try:
                    patient_id = int(parts[0])
                    patient_name = parts[1]
                except ValueError:
                    pass
                    
            if not patient_id:
                # Try to get ID from database if needed
                patient_id = self.get_patient_id(patient_info)
                
            if not patient_id:
                messagebox.showwarning(
                    "Invalid Patient | مريض غير صالح",
                    "Could not determine patient ID. Please select a valid patient. | تعذر تحديد معرف المريض. الرجاء اختيار مريض صالح."
                )
                return
            
            # Create waiting list dialog
            waiting_window = tk.Toplevel(self.parent)
            waiting_window.title("إضافة إلى قائمة الانتظار | Add to Waiting List")
            waiting_window.geometry("400x300")
            
            # Create form
            form_frame = ttk.Frame(waiting_window, padding=20)
            form_frame.pack(fill=tk.BOTH, expand=True)
            
            # Patient info (read-only)
            ttk.Label(form_frame, text="👤 المريض | Patient:").grid(row=0, column=0, sticky="w", pady=10)
            ttk.Label(form_frame, text=f"{patient_name}").grid(row=0, column=1, sticky="w", pady=10)
            
            # Reason selection
            ttk.Label(form_frame, text="🔍 سبب الزيارة | Reason:").grid(row=1, column=0, sticky="w", pady=10)
            reason_var = tk.StringVar(value=self.common_reasons[0] if self.common_reasons else "")
            reason_combo = ttk.Combobox(form_frame, textvariable=reason_var, values=self.common_reasons)
            reason_combo.grid(row=1, column=1, sticky="ew", pady=10)
            
            # Notes
            ttk.Label(form_frame, text="📝 ملاحظات | Notes:").grid(row=2, column=0, sticky="nw", pady=10)
            notes_text = tk.Text(form_frame, width=30, height=4)
            notes_text.grid(row=2, column=1, sticky="ew", pady=10)
            
            # Priority
            ttk.Label(form_frame, text="🔴 أولوية | Priority:").grid(row=3, column=0, sticky="w", pady=10)
            priority_var = tk.StringVar(value="عادي | Normal")
            priority_frame = ttk.Frame(form_frame)
            priority_frame.grid(row=3, column=1, sticky="w", pady=10)
            
            ttk.Radiobutton(priority_frame, text="عادي | Normal", variable=priority_var,
                          value="عادي | Normal").pack(side=tk.LEFT, padx=5)
            ttk.Radiobutton(priority_frame, text="عاجل | Urgent", variable=priority_var,
                          value="عاجل | Urgent").pack(side=tk.LEFT, padx=5)
            
            # Button frame
            button_frame = ttk.Frame(form_frame)
            button_frame.grid(row=4, column=0, columnspan=2, pady=20)
            
            # Save function
            def save_waiting():
                # Get reason and notes
                reason = reason_var.get()
                notes = notes_text.get(1.0, tk.END).strip()
                priority = priority_var.get()
                
                # Get current time
                current_time = datetime.now().strftime("%H:%M")
                
                # Status based on priority
                status = "🔴 عاجل | Urgent" if "عاجل" in priority else "⏳ في الانتظار | Waiting"
                
                # Add to waiting list
                if hasattr(self, 'waiting_tree'):
                    item_id = self.waiting_tree.insert(
                        "", 0,  # Insert at the top
                        values=(patient_id, patient_name, current_time, reason, status, notes)
                    )
                    
                    # Select and see the new item
                    self.waiting_tree.selection_set(item_id)
                    self.waiting_tree.see(item_id)
                    
                # Update waiting count
                self.update_waiting_count()
                
                # Close window
                waiting_window.destroy()
                
                # Show success message
                self.set_status(f"👥 تمت إضافة {patient_name} إلى قائمة الانتظار | Added {patient_name} to waiting list")
                
            # Buttons
            ttk.Button(
                button_frame,
                text="💾 حفظ | Save",
                style="Accent.TButton",
                command=save_waiting
            ).pack(side=tk.LEFT, padx=10)
            
            ttk.Button(
                button_frame,
                text="❌ إلغاء | Cancel",
                command=waiting_window.destroy
            ).pack(side=tk.LEFT, padx=10)
            
            # Make the grid expandable
            form_frame.columnconfigure(1, weight=1)
            
            # Center the window on screen
            waiting_window.update_idletasks()
            width = waiting_window.winfo_width()
            height = waiting_window.winfo_height()
            x = (waiting_window.winfo_screenwidth() // 2) - (width // 2)
            y = (waiting_window.winfo_screenheight() // 2) - (height // 2)
            waiting_window.geometry(f'{width}x{height}+{x}+{y}')
            
            # Make window modal
            waiting_window.transient(self.parent)
            waiting_window.grab_set()
            self.parent.wait_window(waiting_window)
                
        except Exception as e:
            messagebox.showerror(
                "Error | خطأ",
                f"Failed to add to waiting list: {e} | فشل في الإضافة إلى قائمة الانتظار: {e}"
            )
            print(f"Error adding to waiting list: {e}")
            import traceback
            traceback.print_exc()

    def update_waiting_count(self):
        """Update the waiting count in the dashboard"""
        if hasattr(self, 'waiting_tree') and hasattr(self, 'waiting_count_var'):
            count = len(self.waiting_tree.get_children())
            self.waiting_count_var.set(str(count))
    
    def start_examination(self):
        """Mark selected waiting patient as being examined"""
        selected_id = self.waiting_tree.selection()
        if not selected_id:
            messagebox.showinfo(
                "تنبيه | Info",
                "الرجاء تحديد مريض من قائمة الانتظار | Please select a patient from the waiting list"
            )
            return
            
        # Update status in waiting list
        self.waiting_tree.item(
            selected_id,
            values=(
                self.waiting_tree.item(selected_id)['values'][0],
                self.waiting_tree.item(selected_id)['values'][1],
                self.waiting_tree.item(selected_id)['values'][2],
                self.waiting_tree.item(selected_id)['values'][3],
                "قيد الكشف | In Progress"
            ),
            tags=("in_progress",)
        )
        
        # Show success message
        self.set_status(f"تم بدء الكشف للمريض | Examination started for the patient")

    def edit_waiting_patient(self, event=None):
        """Edit details of waiting patient"""
        selected_id = self.waiting_tree.selection()
        if not selected_id:
            return
            
        # Get patient data
        values = self.waiting_tree.item(selected_id)['values']
        
        # Create dialog for editing
        edit_dialog = tk.Toplevel(self.parent)
        edit_dialog.title("تعديل بيانات الانتظار | Edit Waiting Details")
        edit_dialog.geometry("400x300")
        edit_dialog.transient(self.parent)
        edit_dialog.grab_set()
        
        # Create form
        form_frame = ttk.Frame(edit_dialog, padding=10)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Patient info display
        ttk.Label(form_frame, text="المريض | Patient:").grid(row=0, column=0, sticky=tk.E, padx=5, pady=5)
        ttk.Label(form_frame, text=values[1], font=("Arial", 10, "bold")).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Status
        ttk.Label(form_frame, text="الحالة | Status:").grid(row=1, column=0, sticky=tk.E, padx=5, pady=5)
        status_var = tk.StringVar(value=values[4])
        statuses = ["في الانتظار | Waiting", "قيد الكشف | In Progress", "تم الكشف | Completed", "غادر | Left"]
        status_combo = ttk.Combobox(form_frame, textvariable=status_var, values=statuses, state="readonly")
        status_combo.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # Priority
        ttk.Label(form_frame, text="الأولوية | Priority:").grid(row=2, column=0, sticky=tk.E, padx=5, pady=5)
        priority_var = tk.StringVar(value="عادي | Normal")
        if "urgent" in self.waiting_tree.item(selected_id)['tags']:
            priority_var.set("عاجل | Urgent")
            
        priority_frame = ttk.Frame(form_frame)
        priority_frame.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Radiobutton(priority_frame, text="عادي | Normal", variable=priority_var, value="عادي | Normal").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(priority_frame, text="عاجل | Urgent", variable=priority_var, value="عاجل | Urgent").pack(side=tk.LEFT, padx=5)
        
        # Notes
        ttk.Label(form_frame, text="ملاحظات | Notes:").grid(row=3, column=0, sticky=tk.NE, padx=5, pady=5)
        notes_text = tk.Text(form_frame, height=4, width=30)
        notes_text.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # Buttons
        buttons_frame = ttk.Frame(form_frame)
        buttons_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        def update_waiting():
            """Update waiting patient details"""
            try:
                # Determine tag based on priority and status
                tag = "waiting"
                if "عاجل" in priority_var.get():
                    tag = "urgent"
                if "قيد الكشف" in status_var.get():
                    tag = "in_progress"
                if "تم الكشف" in status_var.get() or "غادر" in status_var.get():
                    # Remove from waiting list
                    self.waiting_tree.delete(selected_id)
                    edit_dialog.destroy()
                    
                    # Update waiting count
                    waiting_count = len(self.waiting_tree.get_children())
                    self.waiting_count_var.set(str(waiting_count))
                    
                    self.set_status("تم تحديث حالة المريض | Patient status updated")
                    return
                
                # Update in treeview
                self.waiting_tree.item(
                    selected_id,
                    values=(
                        values[0],
                        values[1],
                        values[2],
                        values[3],
                        status_var.get()
                    ),
                    tags=(tag,)
                )
                
                # Show success message
                self.set_status("تم تحديث بيانات الانتظار | Waiting details updated")
                
                # Close dialog
                edit_dialog.destroy()
                
            except Exception as e:
                messagebox.showerror(
                    "خطأ | Error",
                    f"فشل في تحديث بيانات الانتظار: {e} | Failed to update waiting details: {e}"
                )
        
        ttk.Button(buttons_frame, text="تحديث | Update", command=update_waiting).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="إلغاء | Cancel", command=edit_dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Make dialog responsive
        form_frame.columnconfigure(1, weight=1)

    def show_waiting_menu(self, event):
        """Show context menu for waiting list items"""
        # Check if clicked on an item
        item = self.waiting_tree.identify_row(event.y)
        if not item:
            return
            
        # Select the item
        self.waiting_tree.selection_set(item)
        
        # Create popup menu
        popup = tk.Menu(self.waiting_tree, tearoff=0)
        popup.add_command(label="بدء الكشف | Start Examination", command=self.start_examination)
        popup.add_command(label="تعديل | Edit", command=self.edit_waiting_patient)
        popup.add_separator()
        popup.add_command(label="إزالة من القائمة | Remove", command=lambda: self.remove_from_waiting(item))
        
        # Display popup menu
        popup.tk_popup(event.x_root, event.y_root)

    def remove_from_waiting(self, item_id):
        """Remove patient from waiting list"""
        if messagebox.askyesno(
            "تأكيد | Confirm",
            "هل أنت متأكد من إزالة المريض من قائمة الانتظار؟ | Are you sure you want to remove this patient from the waiting list?"
        ):
            self.waiting_tree.delete(item_id)
            
            # Update waiting count
            waiting_count = len(self.waiting_tree.get_children())
            self.waiting_count_var.set(str(waiting_count))
            
            self.set_status("تمت إزالة المريض من قائمة الانتظار | Patient removed from waiting list")

    def patient_checkin(self):
        """Handle patient check-in for an appointment"""
        # Find appointment for check-in
        checkin_dialog = tk.Toplevel(self.parent)
        checkin_dialog.title("تسجيل وصول مريض | Patient Check-in")
        checkin_dialog.geometry("500x400")
        checkin_dialog.transient(self.parent)
        checkin_dialog.grab_set()
        
        # Create form
        form_frame = ttk.Frame(checkin_dialog, padding=10)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Search options
        ttk.Label(form_frame, text="بحث عن موعد | Search Appointment:", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        # Search by patient name
        name_frame = ttk.Frame(form_frame)
        name_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(name_frame, text="اسم المريض | Patient Name:").pack(side=tk.LEFT, padx=5)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(name_frame, textvariable=name_var, width=30)
        name_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Today's appointments
        ttk.Label(form_frame, text="مواعيد اليوم | Today's Appointments:", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(15, 10))
        
        # Create treeview for appointments
        tree_frame = ttk.Frame(form_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Appointments treeview
        appointments_tree = ttk.Treeview(
            tree_frame,
            columns=("Time", "Name", "Status"),
            show="headings",
            selectmode="browse",
            height=5,
            yscrollcommand=scrollbar.set
        )
        appointments_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=appointments_tree.yview)
        
        # Configure columns
        appointments_tree.heading("Time", text="الوقت | Time")
        appointments_tree.heading("Name", text="المريض | Patient")
        appointments_tree.heading("Status", text="الحالة | Status")
        
        appointments_tree.column("Time", width=80)
        appointments_tree.column("Name", width=150)
        appointments_tree.column("Status", width=100)
        
        # Load today's appointments
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT a.id, a.start_time, a.end_time, p.name, a.status
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                WHERE a.appointment_date = ?
                ORDER BY a.start_time
            ''', (datetime.now().date().isoformat(),))
            
            for row in cursor.fetchall():
                appt_id, start_time, end_time, name, status = row
                
                # Process Arabic text
                name = self.process_arabic_text(name)
                status = self.process_arabic_text(status)
                
                # Format time
                time_str = f"{start_time} - {end_time}"
                
                # Add to treeview
                appointments_tree.insert("", "end", iid=appt_id, values=(time_str, name, status))
        except Exception as e:
            print(f"Error loading appointments for check-in: {e}")
        
        # Filter function for name search
        def filter_appointments(event=None):
            search_term = name_var.get().lower()
            for item in appointments_tree.get_children():
                item_values = appointments_tree.item(item)['values']
                if search_term in item_values[1].lower():
                    appointments_tree.selection_set(item)
                    appointments_tree.see(item)
                    break
        
        # Bind search
        name_entry.bind("<Return>", filter_appointments)
        
        # Function to mark patient as arrived
        def mark_as_arrived():
            selected_id = appointments_tree.selection()
            if not selected_id:
                messagebox.showinfo(
                    "تنبيه | Info",
                    "الرجاء تحديد موعد | Please select an appointment"
                )
                return
                
            try:
                # Update status in database
                cursor = self.conn.cursor()
                cursor.execute('''
                    UPDATE appointments
                    SET status = ?
                    WHERE id = ?
                ''', ("تم الحضور | Arrived", selected_id[0]))
                self.conn.commit()
                
                # Update in treeview
                appointments_tree.item(
                    selected_id,
                    values=(
                        appointments_tree.item(selected_id)['values'][0],
                        appointments_tree.item(selected_id)['values'][1],
                        "تم الحضور | Arrived"
                    )
                )
                
                # Also update in main appointments view if same day
                if self.selected_date == datetime.now().date():
                    self.update_appointments()
                
                # Show success message
                self.set_status(f"تم تسجيل وصول المريض | Patient marked as arrived")
                
                # Add to waiting list option
                if messagebox.askyesno(
                    "إضافة للانتظار | Add to Waiting",
                    "هل تريد إضافة المريض لقائمة الانتظار؟ | Do you want to add the patient to the waiting list?"
                ):
                    # Get patient details
                    cursor.execute('''
                        SELECT p.id, p.name, a.reason
                        FROM appointments a
                        JOIN patients p ON a.patient_id = p.id
                        WHERE a.id = ?
                    ''', (selected_id[0],))
                    
                    patient_data = cursor.fetchone()
                    if patient_data:
                        patient_id, patient_name, reason = patient_data
                        
                        # Set patient in form
                        self.patient_id_var.set(patient_id)
                        self.patient_name_var.set(patient_name)
                        self.reason_var.set(reason if reason else self.common_reasons[0])
                        
                        # Close check-in dialog
                        checkin_dialog.destroy()
                        
                        # Open waiting list dialog
                        self.add_to_waiting_list()
                        return
                
            except Exception as e:
                messagebox.showerror(
                    "خطأ | Error",
                    f"فشل في تسجيل وصول المريض: {e} | Failed to mark patient as arrived: {e}"
                )
        
        # Buttons
        buttons_frame = ttk.Frame(form_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            buttons_frame,
            text="تسجيل الوصول | Check-in",
            command=mark_as_arrived
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            buttons_frame,
            text="إلغاء | Cancel",
            command=checkin_dialog.destroy
        ).pack(side=tk.RIGHT, padx=5)
        
        # Set focus to name entry
        name_entry.focus_set()

    def insert_quick_note(self, note):
        """Insert a quick note into the notes text area"""
        self.notes_text.insert(tk.END, note + "\n")

    def filter_search_results(self, event=None):
        """Filter search results based on quick search field"""
        search_term = self.quick_search_var.get().lower()
        
        for item in self.search_results_tree.get_children():
            item_values = self.search_results_tree.item(item)['values']
            # Convert all values to string and check if search term is in any column
            item_text = " ".join([str(value).lower() for value in item_values])
            
            if search_term in item_text:
                # Show this item
                self.search_results_tree.item(item, tags=())
            else:
                # Hide this item (we could set a tag to make it gray or less visible)
                self.search_results_tree.item(item, tags=("hidden",))
                
        # Configure the hidden tag
        self.search_results_tree.tag_configure("hidden", foreground="light gray")

    def advanced_search(self):
        """Open advanced search dialog"""
        try:
            # Create search window
            search_window = tk.Toplevel(self.parent)
            search_window.title("بحث متقدم | Advanced Search")
            search_window.geometry("800x600")
            
            # Main frame
            main_frame = ttk.Frame(search_window, padding=20)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Create search form
            form_frame = ttk.LabelFrame(main_frame, text="معايير البحث | Search Criteria")
            form_frame.pack(fill=tk.X, padx=10, pady=10)
            
            # Use grid for consistent layout in the form frame
            # Patient name
            ttk.Label(form_frame, text="👤 اسم المريض | Patient Name:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
            patient_name_var = tk.StringVar()
            ttk.Entry(form_frame, textvariable=patient_name_var, width=25).grid(row=0, column=1, sticky="ew", padx=10, pady=10)
            
            # Date range
            ttk.Label(form_frame, text="📅 من تاريخ | From Date:").grid(row=1, column=0, sticky="w", padx=10, pady=10)
            from_date_var = tk.StringVar()
            ttk.Entry(form_frame, textvariable=from_date_var, width=15).grid(row=1, column=1, sticky="w", padx=10, pady=10)
            
            ttk.Label(form_frame, text="📅 إلى تاريخ | To Date:").grid(row=1, column=2, sticky="w", padx=10, pady=10)
            to_date_var = tk.StringVar()
            ttk.Entry(form_frame, textvariable=to_date_var, width=15).grid(row=1, column=3, sticky="w", padx=10, pady=10)
            
            # Status
            ttk.Label(form_frame, text="🔍 الحالة | Status:").grid(row=2, column=0, sticky="w", padx=10, pady=10)
            status_var = tk.StringVar()
            status_combo = ttk.Combobox(form_frame, textvariable=status_var, width=25)
            status_combo['values'] = [""] + list(self.status_types.keys())
            status_combo.grid(row=2, column=1, sticky="ew", padx=10, pady=10)
            
            # Reason
            ttk.Label(form_frame, text="🔍 سبب الزيارة | Reason:").grid(row=2, column=2, sticky="w", padx=10, pady=10)
            reason_var = tk.StringVar()
            reason_combo = ttk.Combobox(form_frame, textvariable=reason_var, width=25)
            reason_combo['values'] = [""] + self.common_reasons
            reason_combo.grid(row=2, column=3, sticky="ew", padx=10, pady=10)
            
            # Results frame - use grid instead of pack
            results_frame = ttk.LabelFrame(main_frame, text="نتائج البحث | Search Results")
            results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Results tree
            columns = [
                "id", "patient_name", "date", "time", "status", "reason"
            ]
            
            results_tree = ttk.Treeview(results_frame, columns=columns, show="headings")
            
            # Define column headings
            results_tree.heading("id", text="#")
            results_tree.heading("patient_name", text="👤 اسم المريض | Patient")
            results_tree.heading("date", text="📅 التاريخ | Date")
            results_tree.heading("time", text="🕒 الوقت | Time")
            results_tree.heading("status", text="🔍 الحالة | Status")
            results_tree.heading("reason", text="🔍 سبب الزيارة | Reason")
            
            # Define column widths
            results_tree.column("id", width=50)
            results_tree.column("patient_name", width=200)
            results_tree.column("date", width=100)
            results_tree.column("time", width=100)
            results_tree.column("status", width=150)
            results_tree.column("reason", width=150)
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=results_tree.yview)
            results_tree.configure(yscrollcommand=scrollbar.set)
            
            # Pack tree and scrollbar - use grid instead of pack
            results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Define the perform_search function BEFORE referencing it in a lambda
            def perform_search():
                """Perform the search based on criteria"""
                # Clear current results
                for item in results_tree.get_children():
                    results_tree.delete(item)
                    
                # Get search criteria
                patient = patient_name_var.get().strip()
                from_date = from_date_var.get().strip()
                to_date = to_date_var.get().strip()
                status = status_var.get()
                reason = reason_var.get().strip()
                
                # Build query
                query = '''
                    SELECT a.id, p.name as patient_name, a.appointment_date, 
                           a.start_time, a.end_time, a.status, a.reason
                    FROM appointments a
                    JOIN patients p ON a.patient_id = p.id
                    WHERE 1=1
                '''
                
                params = []
                
                # Add conditions
                if patient:
                    query += " AND p.name LIKE ?"
                    params.append(f"%{patient}%")
                    
                if from_date:
                    try:
                        date_obj = self.parse_date(from_date)
                        if date_obj:
                            query += " AND a.appointment_date >= ?"
                            params.append(date_obj.isoformat())
                    except:
                        pass
                        
                if to_date:
                    try:
                        date_obj = self.parse_date(to_date)
                        if date_obj:
                            query += " AND a.appointment_date <= ?"
                            params.append(date_obj.isoformat())
                    except:
                        pass
                        
                if status:
                    query += " AND a.status = ?"
                    params.append(status)
                    
                if reason:
                    query += " AND a.reason LIKE ?"
                    params.append(f"%{reason}%")
                    
                # Order by date and time
                query += " ORDER BY a.appointment_date DESC, a.start_time"
                
                try:
                    # Execute query
                    cursor = self.conn.cursor()
                    cursor.execute(query, params)
                    
                    # Process results
                    for row in cursor.fetchall():
                        # Access by column index rather than dictionary key
                        appt_id = row[0]  # id
                        patient = row[1]  # patient_name
                        appt_date = row[2]  # appointment_date
                        
                        # Format the date
                        if isinstance(appt_date, (date, datetime)):
                            appt_date = appt_date.strftime('%Y-%m-%d')
                            
                        time_slot = f"{row[3]} - {row[4]}"  # start_time - end_time
                        status = row[5]  # status
                        reason = row[6] or ""  # reason
                        
                        # Insert into tree
                        results_tree.insert(
                            "", tk.END, iid=str(appt_id),
                            values=(appt_id, patient, appt_date, time_slot, status, reason)
                        )
                        
                    # Update status
                    result_count = len(results_tree.get_children())
                    search_window.title(f"بحث متقدم | Advanced Search - {result_count} نتائج | results")
                    
                except Exception as e:
                    print(f"Error searching appointments: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Add double-click event to open appointment
            def on_result_double_click(event):
                selected_item = results_tree.focus()
                if selected_item:
                    appt_id = results_tree.item(selected_item)['values'][0]
                    
                    # Close search window
                    search_window.destroy()
                    
                    # Load appointment
                    self.load_appointment(appt_id)
                    
            results_tree.bind("<Double-1>", on_result_double_click)
            
            # Button frame
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, padx=10, pady=10)
            
            # Search button
            search_btn = ttk.Button(
                button_frame,
                text="🔍 بحث | Search",
                command=perform_search  # Now this references the defined function
            )
            search_btn.pack(side=tk.LEFT, padx=5)
            
            # Clear button
            def clear_form():
                patient_name_var.set("")
                from_date_var.set("")
                to_date_var.set("")
                status_var.set("")
                reason_var.set("")
                
                # Clear results
                for item in results_tree.get_children():
                    results_tree.delete(item)
                    
            clear_btn = ttk.Button(
                button_frame,
                text="❌ مسح | Clear",
                command=clear_form
            )
            clear_btn.pack(side=tk.LEFT, padx=5)
            
            # Close button
            ttk.Button(
                button_frame,
                text="🚪 إغلاق | Close",
                command=search_window.destroy
            ).pack(side=tk.RIGHT, padx=5)
            
            # Make window modal
            search_window.transient(self.parent)
            search_window.grab_set()
            
            # Center the window
            search_window.update_idletasks()
            width = search_window.winfo_width()
            height = search_window.winfo_height()
            x = (search_window.winfo_screenwidth() // 2) - (width // 2)
            y = (search_window.winfo_screenheight() // 2) - (height // 2)
            search_window.geometry(f'{width}x{height}+{x}+{y}')
            
            # Set focus on search entry
            patient_name_var.set("")
            search_window.focus_set()
            
        except Exception as e:
            print(f"Error opening advanced search: {e}")
            import traceback
            traceback.print_exc()

    def insert_quick_note(self, note):
        """Insert a quick note into the notes field"""
        if note:
            current_text = self.notes_text.get("1.0", tk.END).strip()
            if current_text:
                # Add new line if there's already content
                self.notes_text.insert(tk.END, f"\n{note}")
            else:
                # Just add the note if empty
                self.notes_text.insert("1.0", note)

    def send_reminder(self):
        """Send appointment reminder to patient"""
        if not self.patient_id_var.get():
            messagebox.showwarning(
                "تحذير | Warning",
                "يرجى تحديد مريض أولاً | Please select a patient first"
            )
            return
            
        # Get patient contact info
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT phone, email FROM patients WHERE id = ?",
                (self.patient_id_var.get(),)
            )
            row = cursor.fetchone()
            
            if not row:
                messagebox.showwarning(
                    "تحذير | Warning",
                    "لم يتم العثور على معلومات المريض | Patient information not found"
                )
                return
                
            phone, email = row
            
            # Ask user which contact method to use
            contact_methods = []
            if phone:
                contact_methods.append(f"SMS: {phone}")
            if email:
                contact_methods.append(f"Email: {email}")
                
            if not contact_methods:
                messagebox.showwarning(
                    "تحذير | Warning",
                    "لا توجد معلومات اتصال للمريض | No contact information available for patient"
                )
                return
                
            # Create dialog for reminder
            reminder_dialog = tk.Toplevel(self.parent)
            reminder_dialog.title("إرسال تذكير | Send Reminder")
            reminder_dialog.geometry("500x350")
            reminder_dialog.transient(self.parent)
            reminder_dialog.grab_set()
            
            # Create form
            form_frame = ttk.Frame(reminder_dialog, padding=10)
            form_frame.pack(fill=tk.BOTH, expand=True)
            
            # Patient info
            ttk.Label(
                form_frame,
                text=f"إرسال تذكير للمريض | Send reminder to: {self.patient_name_var.get()}",
                font=("Arial", 11, "bold")
            ).pack(anchor=tk.W, pady=(0, 10))
            
            # Contact method
            ttk.Label(form_frame, text="طريقة الاتصال | Contact Method:").pack(anchor=tk.W)
            
            contact_var = tk.StringVar(value=contact_methods[0] if contact_methods else "")
            contact_combo = ttk.Combobox(form_frame, textvariable=contact_var, values=contact_methods, state="readonly")
            contact_combo.pack(fill=tk.X, pady=5)
            
            # Appointment details
            appointment_date = self.date_var.get()
            appointment_time = self.start_time_var.get()
            
            # Message template
            ttk.Label(form_frame, text="نص الرسالة | Message:").pack(anchor=tk.W, pady=(10, 5))
            
            message_text = tk.Text(form_frame, height=10)
            message_text.pack(fill=tk.BOTH, expand=True)
            
            # Default message template
            template = f"""تذكير بموعدك في العيادة
التاريخ: {appointment_date}
الوقت: {appointment_time}
المريض: {self.patient_name_var.get()}

Reminder for your clinic appointment
Date: {appointment_date}
Time: {appointment_time}
Patient: {self.patient_name_var.get()}
"""
            message_text.insert("1.0", template)
            
            # Buttons
            buttons_frame = ttk.Frame(form_frame)
            buttons_frame.pack(fill=tk.X, pady=10)
            
            def send_message():
                # Here you would integrate with an SMS or email service
                # For now, we'll just show a success message
                messagebox.showinfo(
                    "نجاح | Success",
                    "تم إرسال التذكير بنجاح | Reminder sent successfully"
                )
                reminder_dialog.destroy()
            
            ttk.Button(
                buttons_frame,
                text="إرسال | Send",
                command=send_message
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                buttons_frame,
                text="إلغاء | Cancel",
                command=reminder_dialog.destroy
            ).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            messagebox.showerror(
                "خطأ | Error",
                f"فشل في إرسال التذكير: {e} | Failed to send reminder: {e}"
            )

    def print_appointment_card(self):
        """Print appointment card with enhanced RTL support for Arabic text"""
        if not self.patient_id_var.get() or not self.date_var.get() or not self.start_time_var.get():
            messagebox.showwarning(
                "بيانات غير مكتملة | Incomplete Data",
                "الرجاء تحديد المريض والتاريخ والوقت | Please select patient, date and time"
            )
            return
            
        try:
            # Get appointment details
            patient_name = self.patient_name_var.get()
            patient_id = self.patient_id_var.get()
            appt_date = self.date_var.get()
            appt_time = self.start_time_var.get()
            doctor_name = "Dr. Example"  # This would be replaced with actual doctor name
            
            # Create a PDF buffer
            pdf_buffer = self.generate_appointment_card_pdf(
                patient_name, patient_id, appt_date, appt_time, doctor_name
            )
            
            # Save PDF to temp file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(pdf_buffer.getvalue())
                tmp_file_path = tmp_file.name
                
            # Open PDF in default viewer
            webbrowser.open(f'file://{tmp_file_path}')
            
            self.set_status("تم إنشاء بطاقة الموعد | Appointment card created")
            
        except Exception as e:
            messagebox.showerror(
                "خطأ | Error",
                f"فشل في طباعة بطاقة الموعد: {e} | Failed to print appointment card: {e}"
            )

    def generate_appointment_card_pdf(self, patient_name, patient_id, appt_date, appt_time, doctor_name):
        """Generate a PDF appointment card with proper RTL support"""
        import io
        from reportlab.lib.pagesizes import A6
        from reportlab.lib import colors
        
        # Setup buffer to hold PDF data
        buffer = io.BytesIO()
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A6,
            rightMargin=10,
            leftMargin=10,
            topMargin=10,
            bottomMargin=10
        )
        
        # Create styles with RTL support
        styles = getSampleStyleSheet()
        
        # Create custom RTL paragraph style
        rtl_style = ParagraphStyle(
            'RTL',
            parent=styles['Normal'],
            alignment=TA_RIGHT,
            fontName=arabic_font if self.arabic_support else 'Helvetica',
            fontSize=10
        )
        
        # Create title style
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Title'],
            alignment=TA_CENTER,
            fontName=arabic_font if self.arabic_support else 'Helvetica-Bold',
            fontSize=14
        )
        
        # Process text for Arabic rendering
        clinic_name = self.process_arabic_text("عيادة الطبيب | Doctor's Clinic", is_pdf=True)
        patient_name_rtl = self.process_arabic_text(patient_name, is_pdf=True)
        patient_id_text = self.process_arabic_text(f"رقم المريض | Patient ID: {patient_id}", is_pdf=True)
        appt_date_text = self.process_arabic_text(f"تاريخ الموعد | Date: {appt_date}", is_pdf=True)
        appt_time_text = self.process_arabic_text(f"وقت الموعد | Time: {appt_time}", is_pdf=True)
        doctor_text = self.process_arabic_text(f"الطبيب | Doctor: {doctor_name}", is_pdf=True)
        clinic_address = self.process_arabic_text("العنوان: شارع المثال، المدينة | Address: Example St, City", is_pdf=True)
        
        # Create story for the document
        story = []
        
        # Add logo or clinic name
        story.append(Paragraph(clinic_name, title_style))
        story.append(Spacer(1, 10))
        
        # Add appointment details header
        story.append(Paragraph(
            self.process_arabic_text("بطاقة الموعد | Appointment Card", is_pdf=True),
            title_style
        ))
        story.append(Spacer(1, 15))
        
        # Add patient details
        story.append(Paragraph(patient_name_rtl, rtl_style))
        story.append(Paragraph(patient_id_text, rtl_style))
        story.append(Spacer(1, 10))
        
        # Add appointment details
        story.append(Paragraph(appt_date_text, rtl_style))
        story.append(Paragraph(appt_time_text, rtl_style))
        story.append(Paragraph(doctor_text, rtl_style))
        story.append(Spacer(1, 15))
        
        # Add clinic address
        story.append(Paragraph(clinic_address, rtl_style))
        story.append(Spacer(1, 10))
        
        # Add QR code with appointment info
        qr_data = f"Patient: {patient_name}, ID: {patient_id}, Date: {appt_date}, Time: {appt_time}"
        qr = QrCodeWidget(qr_data)
        qr.barWidth = 50
        qr.barHeight = 50
        qr_drawing = Drawing(70, 70, transform=[0.7, 0, 0, 0.7, 0, 0])
        qr_drawing.add(qr)
        
        # Add QR code
        story.append(qr_drawing)
        
        # Build the PDF
        doc.build(story)
        
        # Return the buffer
        buffer.seek(0)
        return buffer
    
    def filter_search_results(self, event=None):
        """Filter search results based on quick search text"""
        search_text = self.quick_search_var.get().lower()
        
        if not search_text:
            # If search is empty, refresh to show all
            self.refresh_search_results()
            return
            
        # Filter displayed items
        for item in self.search_results_tree.get_children():
            values = self.search_results_tree.item(item)['values']
            # Check if search text exists in name or phone
            name = str(values[1]).lower()
            phone = str(values[2]).lower() if values[2] else ""
            
            if search_text in name or search_text in phone:
                # Keep visible
                pass
            else:
                # Hide the item
                self.search_results_tree.detach(item)
                
    def refresh_search_results(self):
        """Refresh the search results with recent patients"""
        # Clear existing items
        for item in self.search_results_tree.get_children():
            self.search_results_tree.delete(item)
            
        try:
            # Query for recent patients
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT p.id, p.name, p.phone, p.gender, p.date_of_birth
                FROM patients p
                LEFT JOIN appointments a ON p.id = a.patient_id
                GROUP BY p.id
                ORDER BY MAX(a.appointment_date) DESC, p.id DESC
                LIMIT 20
            ''')
            
            for row in cursor.fetchall():
                patient_id, name, phone, gender, dob = row
                
                # Process Arabic text
                name = self.process_arabic_text(name) if name else ""
                gender = self.process_arabic_text(gender) if gender else ""
                
                # Format date of birth
                dob_str = dob.strftime('%Y-%m-%d') if dob else ""
                
                # Add to treeview
                self.search_results_tree.insert(
                    "", "end",
                    values=(patient_id, name, phone, gender, dob_str)
                )
                
            # Update frame title with count
            count = len(self.search_results_tree.get_children())
            self.search_results_frame.configure(text=f"نتائج البحث ({count}) | Search Results")
            
        except Exception as e:
            print(f"Error refreshing search results: {e}")

    def select_search_result(self, event=None):
        """Handle selection of a search result"""
        try:
            # Check which search tree is being used
            search_tree = None
            
            # Check if we're in patient search (most common)
            if hasattr(self, 'patient_search_tree') and self.patient_search_tree.winfo_exists():
                search_tree = self.patient_search_tree
            # Check if we're in advanced search results
            elif hasattr(self, 'search_results_tree') and self.search_results_tree.winfo_exists():
                search_tree = self.search_results_tree
            # Check for any other search trees
            elif hasattr(self, 'search_tree') and self.search_tree.winfo_exists():
                search_tree = self.search_tree
                
            # If no search tree found or it's not a valid widget, return
            if not search_tree:
                print("No active search tree found")
                return
                
            # Get selected item
            selected_item = search_tree.focus()
            if not selected_item:
                print("No item selected in search tree")
                return
                
            # Get values
            values = search_tree.item(selected_item)['values']
            if not values or len(values) < 2:
                print(f"Invalid values in selected item: {values}")
                return
                
            patient_id = values[0]  # First column is patient ID
            patient_name = values[1]  # Second column is patient name
            
            # Format as "ID - Name"
            patient_text = f"{patient_id} - {patient_name}"
            
            # Set patient in appointment form
            if hasattr(self, 'patient_var'):
                self.patient_var.set(patient_text)
                
            # Close search window if it exists
            for window_name in ['search_window', 'patient_search_window', 'advanced_search_window']:
                if hasattr(self, window_name) and getattr(self, window_name).winfo_exists():
                    getattr(self, window_name).destroy()
                    break
                    
            print(f"Selected patient: {patient_text}")
                
        except Exception as e:
            print(f"Error selecting search result: {e}")
            import traceback
            traceback.print_exc()

    def edit_waiting_patient(self, event=None):
        """Edit a patient in the waiting list"""
        selected = self.waiting_tree.selection()
        if not selected:
            return
            
        # Get waiting record ID
        waiting_id = selected[0]
        
        # Get details from treeview
        values = self.waiting_tree.item(waiting_id)['values']
        position, name, arrival_time, reason, status = values
        
        # Create edit dialog
        waiting_dialog = tk.Toplevel(self.parent)
        waiting_dialog.title("تعديل حالة الانتظار | Edit Waiting Status")
        waiting_dialog.geometry("400x300")
        waiting_dialog.transient(self.parent)
        waiting_dialog.grab_set()
        
        # Create form
        form_frame = ttk.Frame(waiting_dialog, padding=10)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Patient info
        ttk.Label(form_frame, text="المريض | Patient:").grid(row=0, column=0, sticky=tk.E, padx=5, pady=5)
        ttk.Label(form_frame, text=name, font=("Arial", 10, "bold")).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Arrival time
        ttk.Label(form_frame, text="وقت الوصول | Arrival Time:").grid(row=1, column=0, sticky=tk.E, padx=5, pady=5)
        arrival_var = tk.StringVar(value=arrival_time)
        ttk.Entry(form_frame, textvariable=arrival_var).grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # Reason
        ttk.Label(form_frame, text="سبب الزيارة | Reason:").grid(row=2, column=0, sticky=tk.E, padx=5, pady=5)
        reason_var = tk.StringVar(value=reason)
        reason_combo = ttk.Combobox(form_frame, textvariable=reason_var, values=self.common_reasons)
        reason_combo.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # Status
        ttk.Label(form_frame, text="الحالة | Status:").grid(row=3, column=0, sticky=tk.E, padx=5, pady=5)
        status_var = tk.StringVar(value=status)
        status_combo = ttk.Combobox(form_frame, textvariable=status_var)
        status_combo['values'] = [
            "في الانتظار | Waiting",
            "قيد الفحص | In Progress",
            "عاجل | Urgent",
            "تم الكشف | Completed",
            "مغادر | Left"
        ]
        status_combo.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # Notes
        ttk.Label(form_frame, text="ملاحظات | Notes:").grid(row=4, column=0, sticky=tk.NE, padx=5, pady=5)
        notes_text = tk.Text(form_frame, height=4, width=25)
        notes_text.grid(row=4, column=1, sticky=tk.EW, padx=5, pady=5)
        notes_text.insert("1.0", "")  # We'd fill this from database if we stored notes
        
        # Buttons
        buttons_frame = ttk.Frame(form_frame)
        buttons_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        def update_waiting():
            # Update the waiting list entry
            self.waiting_tree.item(
                waiting_id,
                values=(position, name, arrival_var.get(), reason_var.get(), status_var.get()),
                tags=(status_var.get().split(" | ")[0].lower(),)
            )
            
            # If completed, remove from waiting list
            if "تم الكشف" in status_var.get() or "Completed" in status_var.get() or "مغادر" in status_var.get() or "Left" in status_var.get():
                self.waiting_tree.delete(waiting_id)
                
                # Update waiting count
                count = len(self.waiting_tree.get_children())
                self.waiting_count_var.set(str(count))
                
            waiting_dialog.destroy()
        
        ttk.Button(buttons_frame, text="تحديث | Update", command=update_waiting).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="إلغاء | Cancel", command=waiting_dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
    def show_waiting_menu(self, event):
        """Show context menu for waiting list on right-click"""
        # Select row under mouse
        iid = self.waiting_tree.identify_row(event.y)
        if iid:
            # Select this row
            self.waiting_tree.selection_set(iid)
            
            # Create popup menu
            menu = tk.Menu(self.parent, tearoff=0)
            menu.add_command(label="تعديل | Edit", command=self.edit_waiting_patient)
            menu.add_command(label="بدء الكشف | Start Exam", command=self.start_examination)
            menu.add_separator()
            menu.add_command(label="حذف | Delete", command=lambda: self.remove_from_waiting())
            
            # Display popup menu
            menu.tk_popup(event.x_root, event.y_root)
            
    def remove_from_waiting(self):
        """Remove a patient from the waiting list"""
        selected = self.waiting_tree.selection()
        if not selected:
            return
            
        # Confirm deletion
        result = messagebox.askyesno(
            "تأكيد | Confirm",
            "هل أنت متأكد من حذف هذا المريض من قائمة الانتظار؟ | Are you sure you want to remove this patient from the waiting list?"
        )
        
        if result:
            # Delete selected item
            self.waiting_tree.delete(selected[0])
            
            # Update waiting count
            count = len(self.waiting_tree.get_children())
            self.waiting_count_var.set(str(count))

    def initialize_database(self):
        """Initialize database tables if they don't exist and upgrade schema if needed"""
        try:
            cursor = self.conn.cursor()
            
            # Check if patients table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='patients'")
            if not cursor.fetchone():
                # Create patients table
                cursor.execute('''
                    CREATE TABLE patients (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        phone TEXT,
                        email TEXT,
                        date_of_birth TEXT,
                        gender TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                print("Created patients table")
            else:
                # Check if notes column exists
                cursor.execute("PRAGMA table_info(patients)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Add notes column if it doesn't exist
                if 'notes' not in columns:
                    try:
                        cursor.execute("ALTER TABLE patients ADD COLUMN notes TEXT")
                        print("Added notes column to patients table")
                    except:
                        print("Failed to add notes column, may already exist or other error")
            
            # Check if appointments table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='appointments'")
            if not cursor.fetchone():
                # Create appointments table
                cursor.execute('''
                    CREATE TABLE appointments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        patient_id INTEGER NOT NULL,
                        appointment_date TEXT NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT NOT NULL,
                        reason TEXT,
                        status TEXT DEFAULT '⏳ قيد الانتظار | Pending',
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (patient_id) REFERENCES patients (id)
                    )
                ''')
                print("Created appointments table")
            
            self.conn.commit()
            print("Database initialized successfully")
            
        except Exception as e:
            print(f"Error initializing database: {e}")
            import traceback
            traceback.print_exc()

    def add_appointment(self):
        """Create a new appointment"""
        # Clear form
        self.clear_form()
        
        # Set default date to selected date
        self.date_var.set(self.selected_date.isoformat())
        
        # Set default status
        self.status_var.set("قيد الانتظار | Pending")
        
        # Set default start and end times (next available slot)
        current_time = datetime.now()
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        # Round to next 15 minutes
        if current_minute < 15:
            next_minute = 15
        elif current_minute < 30:
            next_minute = 30
        elif current_minute < 45:
            next_minute = 45
        else:
            next_minute = 0
            current_hour += 1
        
        # Make sure we're within business hours
        if current_hour < 9:
            current_hour = 9
            next_minute = 0
        elif current_hour >= 18:
            current_hour = 9  # Next day first slot
            next_minute = 0
        
        # Format times
        start_time = f"{current_hour:02d}:{next_minute:02d}"
        
        # Calculate end time (default 30 min appointment)
        end_minute = next_minute + 30
        end_hour = current_hour
        if end_minute >= 60:
            end_minute -= 60
            end_hour += 1
        
        end_time = f"{end_hour:02d}:{end_minute:02d}"
        
        # Set times in form
        self.start_time_var.set(start_time)
        self.end_time_var.set(end_time)
        
        # Focus on patient search to begin
        if hasattr(self, 'patient_search'):
            self.patient_search.focus_set()
        
        # Update status
        self.set_status("جاهز لإضافة موعد جديد | Ready to add new appointment")

    def edit_appointment(self, event=None):
        """Edit the selected appointment"""
        selected = self.appointments_tree.selection()
        if not selected:
            messagebox.showwarning(
                "تحذير | Warning",
                "يرجى تحديد موعد للتعديل | Please select an appointment to edit"
            )
            return
        
        # Get appointment ID
        appointment_id = selected[0]
        
        # Load appointment details
        self.load_appointment(appointment_id)
        
        # Set selected appointment ID
        self.selected_appointment_id = appointment_id
        
        # Update status
        self.set_status("تعديل الموعد | Editing appointment")

    def cancel_appointment(self):
        """Cancel the selected appointment"""
        selected = self.appointments_tree.selection()
        if not selected:
            messagebox.showwarning(
                "تحذير | Warning",
                "يرجى تحديد موعد للإلغاء | Please select an appointment to cancel"
            )
            return
        
        # Get appointment ID
        appointment_id = selected[0]
        
        # Confirm cancellation
        result = messagebox.askyesno(
            "تأكيد | Confirm",
            "هل أنت متأكد من إلغاء هذا الموعد؟ | Are you sure you want to cancel this appointment?"
        )
        
        if result:
            try:
                # Update appointment status in database
                cursor = self.conn.cursor()
                cursor.execute(
                    "UPDATE appointments SET status = ? WHERE id = ?",
                    ("ملغي | Cancelled", appointment_id)
                )
                
                # Log the change
                cursor.execute(
                    """
                    INSERT INTO appointments_history 
                    (appointment_id, action, old_status, new_status)
                    VALUES (?, ?, ?, ?)
                    """,
                    (appointment_id, "cancel", 
                     self.appointments_tree.item(appointment_id)['values'][3], 
                     "ملغي | Cancelled")
                )
                
                self.conn.commit()
                
                # Update the appointment in the treeview
                values = list(self.appointments_tree.item(appointment_id)['values'])
                values[3] = "ملغي | Cancelled"  # Update status
                
                # Update item with new values and tag
                self.appointments_tree.item(
                    appointment_id,
                    values=tuple(values),
                    tags=("cancelled",)
                )
                
                # Update status
                self.set_status("تم إلغاء الموعد | Appointment cancelled")
                
            except Exception as e:
                messagebox.showerror(
                    "خطأ | Error",
                    f"فشل في إلغاء الموعد: {e} | Failed to cancel appointment: {e}"
                )

    def view_patients_by_date(self):
        """View all patients with appointments on the selected date"""
        try:
            # Get all patients with appointments on the selected date
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT p.id, p.name, p.phone, p.gender, 
                       a.start_time, a.end_time, a.reason, a.status
                FROM patients p
                JOIN appointments a ON p.id = a.patient_id
                WHERE a.appointment_date = ?
                ORDER BY a.start_time
            ''', (self.selected_date.isoformat(),))
            
            patients = cursor.fetchall()
            
            if not patients:
                messagebox.showinfo(
                    "قائمة المرضى | Patient List",
                    "لا يوجد مرضى مسجلين في هذا اليوم | No patients registered for this date"
                )
                return
                
            # Create dialog to show patients
            patients_dialog = tk.Toplevel(self.parent)
            patients_dialog.title(f"قائمة المرضى ليوم {self.selected_date.isoformat()} | Patients for {self.selected_date.isoformat()}")
            patients_dialog.geometry("800x500")
            patients_dialog.transient(self.parent)
            
            # Main frame
            main_frame = ttk.Frame(patients_dialog, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Date info
            ttk.Label(
                main_frame,
                text=f"قائمة المرضى ليوم: {self.selected_date.isoformat()} | Patients List for: {self.selected_date.isoformat()}",
                font=("Arial", 12, "bold")
            ).pack(fill=tk.X, pady=(0, 10))
            
            # Create treeview for patients
            tree_frame = ttk.Frame(main_frame)
            tree_frame.pack(fill=tk.BOTH, expand=True)
            
            # Scrollbars
            y_scrollbar = ttk.Scrollbar(tree_frame)
            y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            x_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
            x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            
            # Create treeview
            patients_tree = ttk.Treeview(
                tree_frame,
                columns=("ID", "Name", "Phone", "Time", "Duration", "Reason", "Status"),
                show="headings",
                yscrollcommand=y_scrollbar.set,
                xscrollcommand=x_scrollbar.set
            )
            patients_tree.pack(fill=tk.BOTH, expand=True)
            
            # Configure scrollbars
            y_scrollbar.config(command=patients_tree.yview)
            x_scrollbar.config(command=patients_tree.xview)
            
            # Configure columns
            patients_tree.heading("ID", text="الرقم | ID")
            patients_tree.heading("Name", text="الاسم | Name")
            patients_tree.heading("Phone", text="الهاتف | Phone")
            patients_tree.heading("Time", text="الوقت | Time")
            patients_tree.heading("Duration", text="المدة | Duration")
            patients_tree.heading("Reason", text="السبب | Reason")
            patients_tree.heading("Status", text="الحالة | Status")
            
            patients_tree.column("ID", width=50, anchor=tk.CENTER)
            patients_tree.column("Name", width=150)
            patients_tree.column("Phone", width=100)
            patients_tree.column("Time", width=100, anchor=tk.CENTER)
            patients_tree.column("Duration", width=70, anchor=tk.CENTER)
            patients_tree.column("Reason", width=150)
            patients_tree.column("Status", width=100)
            
            # Create tags for status colors (same as appointments)
            patients_tree.tag_configure("normal", background="#ffffff")
            patients_tree.tag_configure("confirmed", background="#e3f2fd")
            patients_tree.tag_configure("arrived", background="#e8f5e9")
            patients_tree.tag_configure("completed", background="#f1f8e9")
            patients_tree.tag_configure("cancelled", background="#ffebee")
            patients_tree.tag_configure("noshow", background="#fce4ec")
            
            # Populate data
            for patient in patients:
                patient_id, name, phone, gender, start_time, end_time, reason, status = patient
                
                # Process Arabic text
                name = self.process_arabic_text(name) if name else ""
                reason = self.process_arabic_text(reason) if reason else ""
                status = self.process_arabic_text(status) if status else ""
                
                # Calculate duration
                duration = "N/A"
                if start_time and end_time:
                    try:
                        start_hour, start_min = map(int, start_time.split(':'))
                        end_hour, end_min = map(int, end_time.split(':'))
                        
                        total_start_mins = start_hour * 60 + start_min
                        total_end_mins = end_hour * 60 + end_min
                        
                        duration_mins = total_end_mins - total_start_mins
                        if duration_mins < 0:  # Handle appointments past midnight
                            duration_mins += 24 * 60
                            
                        duration = f"{duration_mins} min"
                    except:
                        pass
                
                # Determine tag based on status
                tag = "normal"
                if status.startswith("مؤكد") or "Confirmed" in status:
                    tag = "confirmed"
                elif status.startswith("تم الحضور") or "Arrived" in status:
                    tag = "arrived"
                elif status.startswith("تم الكشف") or "Completed" in status:
                    tag = "completed"
                elif status.startswith("ملغي") or "Cancelled" in status:
                    tag = "cancelled"
                elif status.startswith("لم يحضر") or "No-show" in status:
                    tag = "noshow"
                
                # Add to treeview
                patients_tree.insert(
                    "", "end",
                    values=(patient_id, name, phone, f"{start_time} - {end_time}", 
                            duration, reason, status),
                    tags=(tag,)
                )
                    
            # Add buttons at bottom
            buttons_frame = ttk.Frame(main_frame)
            buttons_frame.pack(fill=tk.X, pady=10)
            
            ttk.Button(
                buttons_frame,
                text="تصدير إلى PDF | Export to PDF",
                command=lambda: self.print_patients_list(patients)
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                buttons_frame,
                text="تصدير إلى إكسل | Export to Excel",
                command=lambda: self.export_patients_to_excel(patients)
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                buttons_frame,
                text="إغلاق | Close",
                command=patients_dialog.destroy
            ).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            messagebox.showerror(
                "خطأ | Error",
                f"فشل في عرض قائمة المرضى: {e} | Failed to view patients list: {e}"
            )

    def previous_month(self):
        """Navigate to the previous month in the calendar"""
        self.cal_month -= 1
        if self.cal_month < 1:
            self.cal_month = 12
            self.cal_year -= 1
        self.update_calendar()
        
    def next_month(self):
        """Navigate to the next month in the calendar"""
        self.cal_month += 1
        if self.cal_month > 12:
            self.cal_month = 1
            self.cal_year += 1
        self.update_calendar()
        
    def go_to_today(self):
        """Reset calendar to today's date"""
        today = datetime.now().date()
        self.cal_year = today.year
        self.cal_month = today.month
        self.selected_date = today
        self.update_calendar()
        self.update_appointments()
        
    def update_from_year_month(self, event=None):
        """Update calendar when year or month is changed from dropdown"""
        try:
            # Get year from spinbox
            year = int(self.year_var.get())
            
            # Get month from combobox (format: "1 - يناير | Jan")
            month_str = self.month_var.get()
            month = int(month_str.split()[0])
            
            # Update calendar variables
            self.cal_year = year
            self.cal_month = month
            
            # Update calendar display
            self.update_calendar()
        except ValueError:
            pass  # Invalid input, ignore

    def select_date(self, selected_date):
        """Handle date selection in calendar"""
        self.selected_date = selected_date
        
        # Update date display in appointment form
        self.date_var.set(selected_date.isoformat())
        
        # Update appointments list for selected date
        self.update_appointments()
        
        # Update calendar (to refresh highlighting)
        self.update_calendar()

    def show_date_picker(self):
        """Show a date picker dialog for appointment date"""
        # Create a top-level window
        picker = tk.Toplevel(self.parent)
        picker.title("اختيار التاريخ | Date Picker")
        picker.transient(self.parent)
        picker.grab_set()
        
        # Create a month calendar
        cal_frame = ttk.Frame(picker, padding=10)
        cal_frame.pack(fill=tk.BOTH, expand=True)
        
        # Navigation
        nav_frame = ttk.Frame(cal_frame)
        nav_frame.pack(fill=tk.X, pady=5)
        
        # Year selector
        year_frame = ttk.Frame(nav_frame)
        year_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(year_frame, text="السنة | Year:").pack(side=tk.LEFT)
        year_var = tk.StringVar(value=str(datetime.now().year))
        year_spin = ttk.Spinbox(
            year_frame, from_=2000, to=2050, textvariable=year_var, width=5
        )
        year_spin.pack(side=tk.LEFT, padx=5)
        
        # Month selector
        month_frame = ttk.Frame(nav_frame)
        month_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(month_frame, text="الشهر | Month:").pack(side=tk.LEFT)
        month_names = [
            "يناير | January", "فبراير | February", "مارس | March",
            "أبريل | April", "مايو | May", "يونيو | June",
            "يوليو | July", "أغسطس | August", "سبتمبر | September",
            "أكتوبر | October", "نوفمبر | November", "ديسمبر | December"
        ]
        month_var = tk.StringVar(value=month_names[datetime.now().month-1])
        month_combo = ttk.Combobox(month_frame, textvariable=month_var, values=month_names, width=15, state="readonly")
        month_combo.pack(side=tk.LEFT, padx=5)
        
        # Calendar grid
        cal_grid = ttk.Frame(cal_frame)
        cal_grid.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Weekday headers
        weekdays = ["Sun | أحد", "Mon | اثنين", "Tue | ثلاثاء", "Wed | أربعاء", "Thu | خميس", "Fri | جمعة", "Sat | سبت"]
        for i, day in enumerate(weekdays):
            ttk.Label(cal_grid, text=day, anchor=tk.CENTER, padding=5).grid(row=0, column=i, sticky="nsew")
        
        # Day buttons - will be populated by update function
        day_buttons = []
        for row in range(1, 7):  # Up to 6 weeks
            for col in range(7):  # 7 days per week
                btn = ttk.Button(cal_grid, text="", width=4)
                btn.grid(row=row, column=col, padx=1, pady=1, sticky="nsew")
                day_buttons.append(btn)
        
        # Make grid cells expandable
        for i in range(7):
            cal_grid.columnconfigure(i, weight=1)
        for i in range(7):
            cal_grid.rowconfigure(i, weight=1)
        
        # Update calendar function
        def update_picker_calendar():
            # Get year and month from widgets
            try:
                year = int(year_var.get())
                month = month_names.index(month_var.get()) + 1
                
                # Get calendar for this month
                cal = calendar.monthcalendar(year, month)
                
                # Clear all buttons
                for btn in day_buttons:
                    btn.configure(text="", state="disabled")
                
                # Fill in day buttons
                btn_idx = 0
                for week in cal:
                    for day in week:
                        if day == 0:
                            # Day outside month
                            day_buttons[btn_idx].configure(text="", state="disabled")
                        else:
                            # Configure day button
                            day_buttons[btn_idx].configure(
                                text=str(day), 
                                state="normal",
                                command=lambda y=year, m=month, d=day: select_and_close(y, m, d)
                            )
                        btn_idx += 1
            except:
                # Handle any errors
                pass
        
        # Function to select date and close picker
        def select_and_close(year, month, day):
            selected_date = date(year, month, day)
            self.date_var.set(selected_date.isoformat())
            picker.destroy()
        
        # Update when month or year changes
        month_combo.bind("<<ComboboxSelected>>", lambda e: update_picker_calendar())
        year_spin.bind("<KeyRelease>", lambda e: update_picker_calendar())
        
        # Today button
        today_btn = ttk.Button(
            cal_frame, 
            text="اليوم | Today",
            command=lambda: select_and_close(datetime.now().year, datetime.now().month, datetime.now().day)
        )
        today_btn.pack(side=tk.LEFT, pady=10)
        
        # Close button
        close_btn = ttk.Button(
            cal_frame,
            text="إغلاق | Close",
            command=picker.destroy
        )
        close_btn.pack(side=tk.RIGHT, pady=10)
        
        # Initialize calendar display
        update_picker_calendar()
        
        # Position near the date entry
        # TODO: Improve positioning

    def update_appointments(self):
        """Update the appointments list for the selected date"""
        # Clear current appointments
        for item in self.appointments_tree.get_children():
            self.appointments_tree.delete(item)
        
        try:
            if not self.selected_date:
                return
                
            # Safely format date for query
            selected_date_str = self.selected_date.isoformat()
            
            # Get appointments for selected date
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT a.id, a.start_time, a.end_time, p.name, a.reason, a.status, a.appointment_date
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                WHERE a.appointment_date = ? OR a.appointment_date = ?
                ORDER BY a.start_time
            ''', (selected_date_str, selected_date_str + " 00:00:00"))
            
            appointments = cursor.fetchall()
            
            # Display appointments
            for appointment in appointments:
                appt_id, start_time, end_time, patient_name, reason, status, appt_date = appointment
                
                # Debug output for the problematic date
                print(f"Appointment date from DB: {appt_date} (type: {type(appt_date)})")
                
                # Format time display
                time_display = f"{start_time} - {end_time}"
                
                # Process Arabic text
                patient_name = self.process_arabic_text(patient_name) if patient_name else ""
                reason = self.process_arabic_text(reason) if reason else ""
                status = self.process_arabic_text(status) if status else ""
                
                # Determine tag based on status
                tag = "normal"
                if status.startswith("مؤكد") or "Confirmed" in status:
                    tag = "confirmed"
                elif status.startswith("تم الحضور") or "Arrived" in status:
                    tag = "arrived"
                elif status.startswith("تم الكشف") or "Completed" in status:
                    tag = "completed"
                elif status.startswith("ملغي") or "Cancelled" in status:
                    tag = "cancelled"
                elif status.startswith("لم يحضر") or "No-show" in status:
                    tag = "noshow"
                
                # Insert into treeview
                self.appointments_tree.insert(
                    "", "end",
                    iid=appt_id,
                    values=(time_display, patient_name, reason, status),
                    tags=(tag,)
                )
                
            # Update status
            self.set_status(f"تم تحميل {len(appointments)} مواعيد | Loaded {len(appointments)} appointments")
            
        except Exception as e:
            print(f"Error updating appointments: {e}")
            import traceback
            traceback.print_exc()
            self.set_status(f"خطأ في تحميل المواعيد: {e} | Error loading appointments: {e}")

    def process_arabic_text(self, text):
        """Process Arabic text for proper display"""
        if not text:
            return ""
            
        if self.arabic_support:
            try:
                # Reshape Arabic text for proper display
                reshaped_text = self.arabic_reshaper.reshape(text)
                # Apply bidirectional algorithm
                bidi_text = self.get_display(reshaped_text)
                return bidi_text
            except Exception as e:
                print(f"Error processing Arabic text: {e}")
                return text
        return text

    def load_appointment(self, appointment_id):
        """Load an appointment's details into the form for editing"""
        try:
            # Query appointment details
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT a.*, p.name as patient_name
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                WHERE a.id = ?
            ''', (appointment_id,))
            
            appointment = cursor.fetchone()
            if not appointment:
                print(f"Appointment with ID {appointment_id} not found")
                return
                
            # Extract appointment data using indices instead of keys
            # The order matches the SELECT query fields
            patient_id = appointment[1]  # patient_id is the second column
            appt_date = appointment[2]  # appointment_date is the third column
            start_time = appointment[3]  # start_time is the fourth column
            end_time = appointment[4]  # end_time is the fifth column
            reason = appointment[5]  # reason is the sixth column
            status = appointment[6]  # status is the seventh column
            notes = appointment[7] if len(appointment) > 7 else None  # notes if available
            
            # Get patient name from last column of our query
            patient_name = appointment[-1]  # patient_name is the last column
            
            # Print debug info
            print(f"Appointment date from DB: {appt_date} (type: {type(appt_date)})")
            
            # Convert appt_date to string if it's a date object
            if isinstance(appt_date, (date, datetime)):
                appt_date = appt_date.strftime('%Y-%m-%d')
                
            # Set form values
            # Set appointment ID (hidden field)
            if hasattr(self, 'appointment_id_var'):
                self.appointment_id_var.set(appointment_id)
                
            # Set patient (format as "ID - Name")
            if hasattr(self, 'patient_var'):  # Use patient_var, not patient_id_var
                patient_text = f"{patient_id} - {patient_name}"
                self.patient_var.set(patient_text)
                
            # Set appointment date
            if hasattr(self, 'date_var'):
                self.date_var.set(appt_date)
                
            # Update selected date in calendar if needed
            if hasattr(self, 'selected_date') and isinstance(appt_date, str):
                try:
                    parsed_date = self.parse_date(appt_date)
                    if parsed_date:
                        self.selected_date = parsed_date
                        self.cal_year = parsed_date.year
                        self.cal_month = parsed_date.month
                        self.update_calendar()
                except Exception as e:
                    print(f"Error updating calendar: {e}")
                    
            # Set times
            if hasattr(self, 'start_time_var'):
                self.start_time_var.set(start_time)
            if hasattr(self, 'end_time_var'):
                self.end_time_var.set(end_time)
                
            # Calculate duration
            if hasattr(self, 'duration_var') and hasattr(self, 'durations'):
                try:
                    start_hour, start_minute = map(int, start_time.split(':'))
                    end_hour, end_minute = map(int, end_time.split(':'))
                    
                    start_total_minutes = start_hour * 60 + start_minute
                    end_total_minutes = end_hour * 60 + end_minute
                    
                    duration = end_total_minutes - start_total_minutes
                    
                    # Find closest standard duration
                    closest_duration = min(self.durations, key=lambda x: abs(x - duration))
                    
                    self.duration_var.set(str(closest_duration))
                except Exception as e:
                    print(f"Error calculating duration: {e}")
                    # Set default duration
                    self.duration_var.set("30")
                    
            # Set reason
            if hasattr(self, 'reason_var'):
                self.reason_var.set(reason if reason else "")
                
            # Set status
            if hasattr(self, 'status_var'):
                self.status_var.set(status if status else "⏳ قيد الانتظار | Pending")
                
            # Set notes
            if hasattr(self, 'notes_text') and notes:
                self.notes_text.delete(1.0, tk.END)
                self.notes_text.insert(tk.END, notes)
                
            # Enable edit/delete buttons if they exist
            if hasattr(self, 'edit_mode_var'):
                self.edit_mode_var.set(True)
                
            if hasattr(self, 'delete_btn'):
                self.delete_btn.config(state=tk.NORMAL)
                
            # Set focus on date field
            if hasattr(self, 'date_entry'):
                self.date_entry.focus()
                
            # Show success message
            self.set_status(f"📝 تم تحميل تفاصيل الموعد | Appointment details loaded")
            
        except Exception as e:
            print(f"Error loading appointment: {e}")
            import traceback
            traceback.print_exc()

    def search_patient(self):
        """Open dialog to search for a patient"""
        # Create a top-level window
        search_dialog = tk.Toplevel(self.parent)
        search_dialog.title("بحث عن مريض | Patient Search")
        search_dialog.transient(self.parent)
        search_dialog.grab_set()
        search_dialog.minsize(600, 400)
        
        # Main frame
        main_frame = ttk.Frame(search_dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Search criteria frame
        search_frame = ttk.LabelFrame(main_frame, text="معايير البحث | Search Criteria")
        search_frame.pack(fill=tk.X, pady=10)
        
        # Create search fields
        fields_frame = ttk.Frame(search_frame)
        fields_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Patient ID
        ttk.Label(fields_frame, text="رقم المريض | Patient ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        id_var = tk.StringVar()
        ttk.Entry(fields_frame, textvariable=id_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Patient name
        ttk.Label(fields_frame, text="اسم المريض | Patient Name:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(fields_frame, textvariable=name_var, width=20)
        name_entry.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        # Phone number
        ttk.Label(fields_frame, text="رقم الهاتف | Phone:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        phone_var = tk.StringVar()
        ttk.Entry(fields_frame, textvariable=phone_var, width=15).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Gender
        ttk.Label(fields_frame, text="الجنس | Gender:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        gender_var = tk.StringVar()
        gender_combo = ttk.Combobox(fields_frame, textvariable=gender_var, width=15)
        gender_combo['values'] = ["", "ذكر | Male", "أنثى | Female"]
        gender_combo.grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)
        gender_combo.current(0)
        
        # Search button
        button_frame = ttk.Frame(search_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(
            button_frame, 
            text="بحث | Search",
            command=lambda: perform_search()
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="إعادة ضبط | Reset",
            command=lambda: [id_var.set(""), name_var.set(""), phone_var.set(""), gender_var.set("")]
        ).pack(side=tk.LEFT, padx=5)
        
        # Results frame
        results_frame = ttk.LabelFrame(main_frame, text="نتائج البحث | Search Results (0)")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create treeview for results
        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Results treeview
        results_tree = ttk.Treeview(
            tree_frame,
            columns=("ID", "Name", "Phone", "Gender", "DOB", "Last Visit"),
            show="headings",
            selectmode="browse",
            yscrollcommand=scrollbar.set
        )
        results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=results_tree.yview)
        
        # Configure columns
        results_tree.heading("ID", text="الرقم | ID")
        results_tree.heading("Name", text="الاسم | Name")
        results_tree.heading("Phone", text="الهاتف | Phone")
        results_tree.heading("Gender", text="الجنس | Gender")
        results_tree.heading("DOB", text="تاريخ الميلاد | DOB")
        results_tree.heading("Last Visit", text="آخر زيارة | Last Visit")
        
        # Set column widths
        results_tree.column("ID", width=50, anchor=tk.CENTER)
        results_tree.column("Name", width=150)
        results_tree.column("Phone", width=100)
        results_tree.column("Gender", width=80, anchor=tk.CENTER)
        results_tree.column("DOB", width=100, anchor=tk.CENTER)
        results_tree.column("Last Visit", width=100, anchor=tk.CENTER)
        
        # Search function
        def perform_search():
            # Clear previous results
            for item in results_tree.get_children():
                results_tree.delete(item)
        
            try:
                # Build query
                query = '''
                    SELECT p.id, p.name, p.phone, p.gender, p.date_of_birth,
                           MAX(a.appointment_date) as last_visit
                    FROM patients p
                    LEFT JOIN appointments a ON p.id = a.patient_id
                    WHERE 1=1
                '''
                params = []
                
                # Add ID filter
                if id_var.get():
                    query += " AND p.id = ?"
                    params.append(id_var.get())
                
                # Add name filter
                if name_var.get():
                    query += " AND p.name LIKE ?"
                    params.append(f"%{name_var.get()}%")
                
                # Add phone filter
                if phone_var.get():
                    query += " AND p.phone LIKE ?"
                    params.append(f"%{phone_var.get()}%")
                
                # Add gender filter
                if gender_var.get():
                    query += " AND p.gender = ?"
                    params.append(gender_var.get())
                
                # Group by patient
                query += " GROUP BY p.id"
                
                # Execute query
                cursor = self.conn.cursor()
                cursor.execute(query, params)
                
                # Process results
                for row in cursor.fetchall():
                    patient_id, name, phone, gender, dob, last_visit = row
                    
                    # Process Arabic text
                    name = self.process_arabic_text(name) if name else ""
                    gender = self.process_arabic_text(gender) if gender else ""
                    
                    # Format dates
                    dob_str = dob if dob else ""
                    last_visit_str = last_visit if last_visit else ""
                    
                    # Add to results
                    results_tree.insert(
                        "", "end",
                        values=(patient_id, name, phone, gender, dob_str, last_visit_str)
                    )
                
                # Show count
                count = len(results_tree.get_children())
                results_frame.configure(text=f"نتائج البحث | Search Results ({count})")
                
            except Exception as e:
                messagebox.showerror(
                    "خطأ | Error",
                    f"فشل في البحث: {e} | Search failed: {e}"
                )
        
        # Function to select patient and create appointment
        def select_and_return():
            selected = results_tree.selection()
            if not selected:
                messagebox.showwarning(
                    "تحذير | Warning",
                    "يرجى تحديد مريض | Please select a patient"
                )
                return
                
            # Get selected patient ID and name
            patient_id = results_tree.item(selected[0])['values'][0]
            patient_name = results_tree.item(selected[0])['values'][1]
            
            # Set in appointment form
            self.patient_id_var.set(patient_id)
            self.patient_name_var.set(patient_name)
            
            # Close the dialog
            search_dialog.destroy()
        
        # Double-click to select
        results_tree.bind("<Double-1>", lambda e: select_and_return())
        
        # Buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            buttons_frame,
            text="تحديد المريض | Select Patient",
            command=select_and_return
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            buttons_frame,
            text="إغلاق | Close",
            command=search_dialog.destroy
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            buttons_frame,
            text="مريض جديد | New Patient",
            command=lambda: [search_dialog.destroy(), self.add_new_patient()]
        ).pack(side=tk.RIGHT, padx=5)
        
        # Focus on name field
        name_entry.focus_set()

    def show_date_picker_for_field(self, variable):
        """Show date picker dialog and set result to the given variable"""
        # Create a top-level window
        picker = tk.Toplevel(self.parent)
        picker.title("اختيار التاريخ | Date Picker")
        picker.transient(self.parent)
        picker.grab_set()
        
        # Create a calendar widget
        cal_frame = ttk.Frame(picker, padding=10)
        cal_frame.pack(fill=tk.BOTH, expand=True)
        
        current_date = datetime.now()
        
        # Year selector
        year_frame = ttk.Frame(cal_frame)
        year_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(year_frame, text="السنة | Year:").pack(side=tk.LEFT)
        year_var = tk.StringVar(value=str(current_date.year))
        year_spin = ttk.Spinbox(year_frame, from_=1900, to=2100, textvariable=year_var, width=5)
        year_spin.pack(side=tk.LEFT, padx=5)
        
        # Month selector
        month_names = [
            "يناير | January", "فبراير | February", "مارس | March",
            "أبريل | April", "مايو | May", "يونيو | June",
            "يوليو | July", "أغسطس | August", "سبتمبر | September",
            "أكتوبر | October", "نوفمبر | November", "ديسمبر | December"
        ]
        
        ttk.Label(year_frame, text="الشهر | Month:").pack(side=tk.LEFT, padx=(10, 0))
        month_var = tk.StringVar(value=month_names[current_date.month-1])
        month_combo = ttk.Combobox(year_frame, textvariable=month_var, values=month_names, width=15, state="readonly")
        month_combo.pack(side=tk.LEFT, padx=5)
        
        # Create calendar grid
        cal_grid = ttk.Frame(cal_frame)
        cal_grid.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Day labels
        days = ["أحد | Sun", "اثنين | Mon", "ثلاثاء | Tue", "أربعاء | Wed", "خميس | Thu", "جمعة | Fri", "سبت | Sat"]
        for i, day in enumerate(days):
            ttk.Label(cal_grid, text=day, anchor=tk.CENTER, padding=5).grid(row=0, column=i, sticky="nsew")
        
        # Day buttons
        day_buttons = []
        for week in range(6):
            for day in range(7):
                btn = ttk.Button(cal_grid, text="", width=3)
                btn.grid(row=week+1, column=day, padx=1, pady=1, sticky="nsew")
                day_buttons.append(btn)
        
        def update_calendar():
            # Get current year and month
            year = int(year_var.get())
            month = month_names.index(month_var.get()) + 1
            
            # Get calendar for this month
            cal = calendar.monthcalendar(year, month)
            
            # Update buttons
            for i, btn in enumerate(day_buttons):
                btn.configure(text="", state=tk.DISABLED)
            
            for week_idx, week in enumerate(cal):
                for day_idx, day in enumerate(week):
                    if day != 0:
                        button_idx = week_idx * 7 + day_idx
                        if button_idx < len(day_buttons):
                            day_buttons[button_idx].configure(
                                text=str(day),
                                state=tk.NORMAL,
                                command=lambda y=year, m=month, d=day: select_date(y, m, d)
                            )
        
        def select_date(year, month, day):
            # Format date as ISO
            selected_date = date(year, month, day)
            variable.set(selected_date.isoformat())
            picker.destroy()
        
        # Update calendar when year/month changes
        month_combo.bind("<<ComboboxSelected>>", lambda e: update_calendar())
        year_spin.bind("<KeyRelease>", lambda e: update_calendar())
        
        # Today button
        buttons_frame = ttk.Frame(cal_frame)
        buttons_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            buttons_frame,
            text="اليوم | Today",
            command=lambda: select_date(current_date.year, current_date.month, current_date.day)
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            buttons_frame,
            text="إغلاق | Close",
            command=picker.destroy
        ).pack(side=tk.RIGHT)
        
        # Initialize calendar
        update_calendar()

    def view_patient_history(self, patient_id=None):
        """View the appointment history for a patient"""
        # If no patient ID provided, get from current selection
        if patient_id is None:
            # Try to get from form if available
            if hasattr(self, 'patient_id_var') and self.patient_id_var.get():
                patient_id = self.patient_id_var.get()
            else:
                # No patient ID available
                messagebox.showwarning(
                    "تحذير | Warning",
                    "يرجى تحديد مريض أولاً | Please select a patient first"
                )
                return
        
        try:
            # Get patient info
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, name, phone, gender, date_of_birth FROM patients WHERE id = ?", (patient_id,))
            patient = cursor.fetchone()
            
            if not patient:
                messagebox.showerror(
                    "خطأ | Error",
                    "لم يتم العثور على المريض | Patient not found"
                )
                return
            
            patient_id, name, phone, gender, dob = patient
            
            # Create a top-level window
            history_dialog = tk.Toplevel(self.parent)
            history_dialog.title(f"سجل المواعيد | Appointment History: {self.process_arabic_text(name)}")
            history_dialog.transient(self.parent)
            history_dialog.grab_set()
            history_dialog.minsize(700, 500)
            
            # Main frame
            main_frame = ttk.Frame(history_dialog, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Patient info frame
            info_frame = ttk.LabelFrame(main_frame, text="بيانات المريض | Patient Information")
            info_frame.pack(fill=tk.X, pady=10)
            
            # Create grid for patient info
            grid = ttk.Frame(info_frame)
            grid.pack(fill=tk.X, padx=10, pady=10)
            
            # Row 1: ID and Name
            ttk.Label(grid, text="رقم المريض | ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
            ttk.Label(grid, text=str(patient_id)).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
            
            ttk.Label(grid, text="الاسم | Name:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
            ttk.Label(grid, text=self.process_arabic_text(name)).grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
            
            # Row 2: Phone and Gender
            ttk.Label(grid, text="الهاتف | Phone:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
            ttk.Label(grid, text=phone if phone else "").grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
            
            ttk.Label(grid, text="الجنس | Gender:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
            ttk.Label(grid, text=self.process_arabic_text(gender) if gender else "").grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
            
            # Row 3: DOB and Visit Count
            ttk.Label(grid, text="تاريخ الميلاد | DOB:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
            ttk.Label(grid, text=dob if dob else "").grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
            
            # Get visit count
            cursor.execute("SELECT COUNT(*) FROM appointments WHERE patient_id = ?", (patient_id,))
            visit_count = cursor.fetchone()[0]
            
            ttk.Label(grid, text="عدد الزيارات | Visit Count:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
            ttk.Label(grid, text=str(visit_count)).grid(row=2, column=3, sticky=tk.W, padx=5, pady=2)
            
            # Appointment history
            history_frame = ttk.LabelFrame(main_frame, text="سجل المواعيد | Appointment History")
            history_frame.pack(fill=tk.BOTH, expand=True, pady=10)
            
            # Filter controls
            filter_frame = ttk.Frame(history_frame)
            filter_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Date range filter
            ttk.Label(filter_frame, text="من | From:").pack(side=tk.LEFT, padx=5)
            from_date_var = tk.StringVar()
            from_date_entry = ttk.Entry(filter_frame, textvariable=from_date_var, width=10)
            from_date_entry.pack(side=tk.LEFT, padx=2)
            
            ttk.Button(
                filter_frame, 
                text="📅", 
                width=2,
                command=lambda: self.show_date_picker_for_field(from_date_var)
            ).pack(side=tk.LEFT, padx=2)
            
            ttk.Label(filter_frame, text="إلى | To:").pack(side=tk.LEFT, padx=5)
            to_date_var = tk.StringVar()
            to_date_entry = ttk.Entry(filter_frame, textvariable=to_date_var, width=10)
            to_date_entry.pack(side=tk.LEFT, padx=2)
            
            ttk.Button(
                filter_frame, 
                text="📅", 
                width=2,
                command=lambda: self.show_date_picker_for_field(to_date_var)
            ).pack(side=tk.LEFT, padx=2)
            
            # Status filter
            ttk.Label(filter_frame, text="الحالة | Status:").pack(side=tk.LEFT, padx=5)
            status_var = tk.StringVar()
            status_combo = ttk.Combobox(filter_frame, textvariable=status_var, width=15)
            status_combo['values'] = ["", "قيد الانتظار | Pending", "مؤكد | Confirmed", 
                                    "تم الحضور | Arrived", "تم الكشف | Completed", 
                                    "لم يحضر | No-show", "ملغي | Cancelled"]
            status_combo.pack(side=tk.LEFT, padx=5)
            status_combo.current(0)
            
            # Apply filter button
            ttk.Button(
                filter_frame, 
                text="تطبيق | Apply", 
                command=lambda: load_history()
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                filter_frame, 
                text="إعادة ضبط | Reset", 
                command=lambda: [from_date_var.set(""), to_date_var.set(""), status_var.set(""), load_history()]
            ).pack(side=tk.LEFT, padx=5)
            
            # Create treeview for history
            tree_frame = ttk.Frame(history_frame)
            tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            # Scrollbar
            scrollbar = ttk.Scrollbar(tree_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Results treeview
            history_tree = ttk.Treeview(
                tree_frame,
                columns=("Date", "Time", "Reason", "Status", "Notes"),
                show="headings",
                selectmode="browse",
                yscrollcommand=scrollbar.set
            )
            history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=history_tree.yview)
            
            # Configure columns
            history_tree.heading("Date", text="التاريخ | Date")
            history_tree.heading("Time", text="الوقت | Time")
            history_tree.heading("Reason", text="السبب | Reason")
            history_tree.heading("Status", text="الحالة | Status")
            history_tree.heading("Notes", text="ملاحظات | Notes")
            
            # Set column widths
            history_tree.column("Date", width=100, anchor=tk.CENTER)
            history_tree.column("Time", width=100, anchor=tk.CENTER)
            history_tree.column("Reason", width=150)
            history_tree.column("Status", width=100)
            history_tree.column("Notes", width=200)
            
            # Create tags for status colors (same as appointments)
            history_tree.tag_configure("normal", background="#ffffff")
            history_tree.tag_configure("confirmed", background="#e3f2fd")
            history_tree.tag_configure("arrived", background="#e8f5e9")
            history_tree.tag_configure("completed", background="#f1f8e9")
            history_tree.tag_configure("cancelled", background="#ffebee")
            history_tree.tag_configure("noshow", background="#fce4ec")
            
            def load_history():
                # Clear previous results
                for item in history_tree.get_children():
                    history_tree.delete(item)
                
                try:
                    # Build query
                    query = '''
                        SELECT id, appointment_date, start_time, end_time, reason, status, notes
                        FROM appointments 
                        WHERE patient_id = ?
                    '''
                    params = [patient_id]
                    
                    # Add date filters if specified
                    if from_date_var.get():
                        query += " AND appointment_date >= ?"
                        params.append(from_date_var.get())
                    
                    if to_date_var.get():
                        query += " AND appointment_date <= ?"
                        params.append(to_date_var.get())
                    
                    # Add status filter if specified
                    if status_var.get():
                        query += " AND status = ?"
                        params.append(status_var.get())
                    
                    # Order by date (most recent first)
                    query += " ORDER BY appointment_date DESC, start_time DESC"
                    
                    # Execute query
                    cursor.execute(query, params)
                    
                    # Process results
                    for row in cursor.fetchall():
                        appt_id, appt_date, start_time, end_time, reason, status, notes = row
                        
                        # Process Arabic text
                        reason = self.process_arabic_text(reason) if reason else ""
                        status = self.process_arabic_text(status) if status else ""
                        
                        # Format time display
                        time_display = f"{start_time} - {end_time}" if start_time and end_time else ""
                        
                        # Truncate notes if too long
                        notes_display = notes[:50] + "..." if notes and len(notes) > 50 else (notes or "")
                        
                        # Determine tag based on status
                        tag = "normal"
                        if status.startswith("مؤكد") or "Confirmed" in status:
                            tag = "confirmed"
                        elif status.startswith("تم الحضور") or "Arrived" in status:
                            tag = "arrived"
                        elif status.startswith("تم الكشف") or "Completed" in status:
                            tag = "completed"
                        elif status.startswith("ملغي") or "Cancelled" in status:
                            tag = "cancelled"
                        elif status.startswith("لم يحضر") or "No-show" in status:
                            tag = "noshow"
                        
                        # Add to treeview
                        history_tree.insert(
                            "", "end",
                            iid=appt_id,
                            values=(appt_date, time_display, reason, status, notes_display),
                            tags=(tag,)
                        )
                    
                    # Update count in frame label
                    count = len(history_tree.get_children())
                    history_frame.configure(text=f"سجل المواعيد | Appointment History ({count})")
                    
                except Exception as e:
                    messagebox.showerror(
                        "خطأ | Error",
                        f"فشل في تحميل سجل المواعيد: {e} | Failed to load appointment history: {e}"
                    )
            
            # Function to view detailed appointment
            def view_appointment_details():
                selected = history_tree.selection()
                if not selected:
                    messagebox.showwarning(
                        "تحذير | Warning",
                        "يرجى تحديد موعد | Please select an appointment"
                    )
                    return
                
                # Get appointment ID
                appointment_id = selected[0]
                
                # Get appointment details
                cursor.execute('''
                    SELECT a.appointment_date, a.start_time, a.end_time,
                           a.reason, a.status, a.notes, a.created_at
                    FROM appointments a
                    WHERE a.id = ?
                ''', (appointment_id,))
                
                appt = cursor.fetchone()
                if not appt:
                    messagebox.showerror(
                        "خطأ | Error",
                        "لم يتم العثور على الموعد | Appointment not found"
                    )
                    return
                
                appt_date, start_time, end_time, reason, status, notes, created_at = appt
                
                # Create details dialog
                details_dialog = tk.Toplevel(history_dialog)
                details_dialog.title(f"تفاصيل الموعد | Appointment Details: {appt_date}")
                details_dialog.transient(history_dialog)
                details_dialog.grab_set()
                details_dialog.minsize(500, 400)
                
                # Details frame
                details_frame = ttk.Frame(details_dialog, padding=10)
                details_frame.pack(fill=tk.BOTH, expand=True)
                
                # Basic appointment info
                info_grid = ttk.Frame(details_frame)
                info_grid.pack(fill=tk.X, pady=10)
                
                # Row 1: Date and Time
                ttk.Label(info_grid, text="التاريخ | Date:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
                ttk.Label(info_grid, text=appt_date).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
                
                ttk.Label(info_grid, text="الوقت | Time:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
                ttk.Label(info_grid, text=f"{start_time} - {end_time}").grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
                
                # Row 2: Reason and Status
                ttk.Label(info_grid, text="السبب | Reason:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
                ttk.Label(info_grid, text=self.process_arabic_text(reason) if reason else "").grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
                
                ttk.Label(info_grid, text="الحالة | Status:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
                ttk.Label(info_grid, text=self.process_arabic_text(status) if status else "").grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)
                
                # Row 3: Created Date
                ttk.Label(info_grid, text="تاريخ الإنشاء | Created:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
                ttk.Label(info_grid, text=created_at if created_at else "").grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
                
                # Notes section
                notes_frame = ttk.LabelFrame(details_frame, text="ملاحظات | Notes")
                notes_frame.pack(fill=tk.BOTH, expand=True, pady=10)
                
                notes_text = tk.Text(notes_frame, wrap=tk.WORD, height=10)
                notes_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                
                # Insert notes
                if notes:
                    notes_text.insert("1.0", notes)
                
                notes_text.config(state=tk.DISABLED)  # Make read-only
                
                # Bottom buttons
                buttons_frame = ttk.Frame(details_dialog)
                buttons_frame.pack(fill=tk.X, pady=10)
                
                ttk.Button(
                    buttons_frame,
                    text="طباعة | Print",
                    command=lambda: self.print_appointment_details(appointment_id)
                ).pack(side=tk.LEFT, padx=5)
                
                ttk.Button(
                    buttons_frame,
                    text="إغلاق | Close",
                    command=details_dialog.destroy
                ).pack(side=tk.RIGHT, padx=5)
            
            # Bind double-click event
            history_tree.bind("<Double-1>", lambda e: view_appointment_details())
            
            # Buttons
            buttons_frame = ttk.Frame(main_frame)
            buttons_frame.pack(fill=tk.X, pady=10)
            
            ttk.Button(
                buttons_frame,
                text="عرض التفاصيل | View Details",
                command=view_appointment_details
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                buttons_frame,
                text="موعد جديد | New Appointment",
                command=lambda: [history_dialog.destroy(), self.add_appointment_for_patient(patient_id)]
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                buttons_frame,
                text="تقرير | Report",
                command=lambda: self.print_patient_history(patient_id)
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                buttons_frame,
                text="تعديل بيانات المريض | Edit Patient",
                command=lambda: [history_dialog.destroy(), self.edit_patient(patient_id)]
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                buttons_frame,
                text="إغلاق | Close",
                command=history_dialog.destroy
            ).pack(side=tk.RIGHT, padx=5)
            
            # Load initial history
            load_history()
            
        except Exception as e:
            messagebox.showerror(
                "خطأ | Error",
                f"فشل في عرض سجل المريض: {e} | Failed to view patient history: {e}"
            )
            print(f"Error viewing patient history: {e}")
            import traceback
            traceback.print_exc()

    def add_appointment_for_patient(self, patient_id):
        """Add a new appointment for a specific patient"""
        try:
            # Get patient details
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, name FROM patients WHERE id = ?", (patient_id,))
            patient = cursor.fetchone()
            
            if not patient:
                messagebox.showerror(
                    "خطأ | Error",
                    "لم يتم العثور على المريض | Patient not found"
                )
                return
            
            # Clear form and set patient details
            self.clear_form()
            self.patient_id_var.set(patient[0])
            self.patient_name_var.set(patient[1])
            
            # Set default date to today
            self.date_var.set(datetime.now().date().isoformat())
            
            # Set default status
            self.status_var.set("قيد الانتظار | Pending")
            
            # Show form
            self.show_appointment_form()
            
        except Exception as e:
            messagebox.showerror(
                "خطأ | Error",
                f"فشل في إنشاء موعد جديد: {e} | Failed to create new appointment: {e}"
            )

    def save_appointment(self):
        """Save the appointment (add new or update existing)"""
        try:
            # Validate required fields
            if not self.patient_var.get():
                messagebox.showwarning(
                    "Missing Information | معلومات ناقصة",
                    "Please select a patient | الرجاء اختيار مريض"
                )
                return
                
            if not self.date_var.get():
                messagebox.showwarning(
                    "Missing Information | معلومات ناقصة",
                    "Please enter a date | الرجاء إدخال تاريخ"
                )
                return
                
            if not self.start_time_var.get():
                messagebox.showwarning(
                    "Missing Information | معلومات ناقصة",
                    "Please select a start time | الرجاء اختيار وقت البدء"
                )
                return
                
            if not self.end_time_var.get():
                messagebox.showwarning(
                    "Missing Information | معلومات ناقصة",
                    "Please select an end time | الرجاء اختيار وقت الانتهاء"
                )
                return
            
            # Get form data
            patient_name = self.patient_var.get()
            appt_date = self.date_var.get()
            start_time = self.start_time_var.get()
            end_time = self.end_time_var.get()
            reason = self.reason_var.get()
            status = self.status_var.get()
            notes = self.notes_text.get(1.0, tk.END).strip()
            
            # Get patient ID from name
            patient_id = self.get_patient_id(patient_name)
            
            if not patient_id:
                messagebox.showwarning(
                    "Invalid Patient | مريض غير صالح",
                    "Selected patient not found. Please select a valid patient. | المريض المحدد غير موجود. الرجاء اختيار مريض صالح."
                )
                return
            
            # Check if this is a new appointment or an update
            appointment_id = self.appointment_id_var.get()
            
            cursor = self.conn.cursor()
            
            if appointment_id:  # Update existing
                cursor.execute('''
                    UPDATE appointments
                    SET patient_id = ?, appointment_date = ?, start_time = ?,
                        end_time = ?, reason = ?, status = ?, notes = ?
                    WHERE id = ?
                ''', (patient_id, appt_date, start_time, end_time, reason, status, notes, appointment_id))
                
                success_message = "✅ تم تحديث الموعد بنجاح | Appointment updated successfully"
            else:  # Add new
                cursor.execute('''
                    INSERT INTO appointments
                    (patient_id, appointment_date, start_time, end_time, reason, status, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (patient_id, appt_date, start_time, end_time, reason, status, notes))
                
                # Get the ID of the new appointment
                appointment_id = cursor.lastrowid
                success_message = "✅ تم إضافة الموعد بنجاح | Appointment added successfully"
            
            self.conn.commit()
            
            # Update UI
            self.clear_form()
            self.filter_appointments_by_date(datetime.strptime(appt_date, '%Y-%m-%d').date())
            
            # Show success message
            self.set_status(success_message)
            messagebox.showinfo(
                "Success | نجاح",
                success_message
            )
            
        except Exception as e:
            messagebox.showerror(
                "Error | خطأ",
                f"Failed to save appointment: {e} | فشل في حفظ الموعد: {e}"
            )
            print(f"Error saving appointment: {e}")
            import traceback
            traceback.print_exc()
        
    def get_patient_id(self, patient_name):
        """Get patient ID from name"""
        try:
            # Extract patient ID if name is in format "ID - Name"
            if " - " in patient_name:
                parts = patient_name.split(" - ", 1)
                try:
                    return int(parts[0].strip())
                except ValueError:
                    pass
            
            # Otherwise query database
            cursor = self.conn.cursor()
            cursor.execute("SELECT id FROM patients WHERE name = ?", (patient_name,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            return None
            
        except Exception as e:
            print(f"Error getting patient ID: {e}")
            return None
    
    def delete_appointment(self):
        """Delete the currently selected appointment"""
        # Check if an appointment is selected
        if not self.appointment_id_var.get():
            messagebox.showwarning(
                "No Selection | لا يوجد اختيار",
                "Please select an appointment to delete | الرجاء اختيار موعد للحذف"
            )
            return
        
        # Ask for confirmation
        if not messagebox.askyesno(
            "Confirm Deletion | تأكيد الحذف",
            "Are you sure you want to delete this appointment? This cannot be undone. | "
            "هل أنت متأكد من حذف هذا الموعد؟ لا يمكن التراجع عن هذا الإجراء."
        ):
            return
        
        try:
            # Get appointment ID
            appointment_id = self.appointment_id_var.get()
            
            # Delete appointment from database
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
            self.conn.commit()
            
            # Remove from treeview
            if hasattr(self, 'appointments_tree'):
                try:
                    self.appointments_tree.delete(appointment_id)
                except:
                    # Item might not be in the current view
                    pass
            
            # Update view
            self.clear_form()
            self.update_appointments()
            
            # Show success message
            self.set_status("✅ تم حذف الموعد بنجاح | Appointment deleted successfully")
            messagebox.showinfo(
                "Success | نجاح",
                "Appointment has been deleted | تم حذف الموعد"
            )
        
        except Exception as e:
            # Show error message
            messagebox.showerror(
                "Error | خطأ",
                f"Failed to delete appointment: {e} | فشل في حذف الموعد: {e}"
            )
            print(f"Error deleting appointment: {e}")
            import traceback
            traceback.print_exc()
    
    def clear_form(self):
        """Clear the appointment form"""
        # Reset form fields
        if hasattr(self, 'patient_var'):
            self.patient_var.set("")
        if hasattr(self, 'date_var'):
            self.date_var.set(datetime.now().date().strftime('%Y-%m-%d'))
        if hasattr(self, 'start_time_var'):
            self.start_time_var.set("")
        if hasattr(self, 'end_time_var'):
            self.end_time_var.set("")
        if hasattr(self, 'reason_var'):
            self.reason_var.set("")
        if hasattr(self, 'status_var'):
            self.status_var.set("⏳ قيد الانتظار | Pending")
        if hasattr(self, 'notes_text'):
            self.notes_text.delete(1.0, tk.END)
        
        # Reset day selections
        if hasattr(self, 'day_vars'):
            for day_var in self.day_vars.values():
                day_var.set(False)
        
        # Clear appointment ID
        self.appointment_id_var.set("")
        
        # Hide delete button
        if hasattr(self, 'delete_btn') and self.delete_btn.winfo_ismapped():
            self.delete_btn.pack_forget()
        
        # Update save button text
        if hasattr(self, 'save_btn'):
            self.save_btn.configure(text="💾 حفظ | Save")
        
        # Reset selection
        self.selected_appointment_id = None
        
        # Update status
        self.set_status("🆕 نموذج موعد جديد | New appointment form")

    def show_appointment_form(self):
        """Show the appointment form in a dialog"""
        # Create a top-level window
        self.appointment_dialog = tk.Toplevel(self.parent)
        self.appointment_dialog.title("إضافة/تعديل موعد | Add/Edit Appointment")
        self.appointment_dialog.transient(self.parent)
        self.appointment_dialog.grab_set()
        self.appointment_dialog.minsize(500, 400)
        
        # Main frame
        main_frame = ttk.Frame(self.appointment_dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create form
        form_frame = ttk.LabelFrame(main_frame, text="بيانات الموعد | Appointment Details")
        form_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Patient section
        patient_frame = ttk.Frame(form_frame, padding=10)
        patient_frame.pack(fill=tk.X)
        
        # Patient ID and Name (hidden ID)
        ttk.Label(patient_frame, text="المريض | Patient:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        # Patient selection panel
        patient_panel = ttk.Frame(patient_frame)
        patient_panel.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5, columnspan=3)
        
        # Patient name display
        name_entry = ttk.Entry(patient_panel, textvariable=self.patient_name_var, width=30, state="readonly")
        name_entry.pack(side=tk.LEFT, padx=2)
        
        # Hidden patient ID
        id_entry = ttk.Entry(patient_panel, textvariable=self.patient_id_var, width=5)
        id_entry.pack(side=tk.LEFT, padx=2)
        id_entry.pack_forget()  # Hide it
        
        # Patient search button
        ttk.Button(
            patient_panel,
            text="بحث | Search",
            command=self.search_patient
        ).pack(side=tk.LEFT, padx=2)
        
        # New patient button
        ttk.Button(
            patient_panel,
            text="مريض جديد | New",
            command=self.add_new_patient
        ).pack(side=tk.LEFT, padx=2)
        
        # Date section
        date_frame = ttk.Frame(form_frame, padding=10)
        date_frame.pack(fill=tk.X)
        
        # Date
        ttk.Label(date_frame, text="تاريخ الموعد | Date:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        date_panel = ttk.Frame(date_frame)
        date_panel.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        date_entry = ttk.Entry(date_panel, textvariable=self.date_var, width=12)
        date_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            date_panel,
            text="📅",
            width=2,
            command=lambda: self.show_date_picker()
        ).pack(side=tk.LEFT, padx=2)
        
        # Time section
        time_frame = ttk.Frame(form_frame, padding=10)
        time_frame.pack(fill=tk.X)
        
        # Start time
        ttk.Label(time_frame, text="وقت البدء | Start Time:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        start_combo = ttk.Combobox(time_frame, textvariable=self.start_time_var, values=self.time_slots, width=10)
        start_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # End time
        ttk.Label(time_frame, text="وقت الانتهاء | End Time:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        
        end_combo = ttk.Combobox(time_frame, textvariable=self.end_time_var, values=self.time_slots, width=10)
        end_combo.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        # Duration shortcuts
        ttk.Label(time_frame, text="المدة | Duration:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        duration_frame = ttk.Frame(time_frame)
        duration_frame.grid(row=1, column=1, columnspan=3, sticky=tk.W, padx=5, pady=5)
        
        for duration in self.durations:
            ttk.Button(
                duration_frame,
                text=f"{duration} دقيقة | min",
                width=8,
                command=lambda d=duration: self.set_end_time_from_duration(d)
            ).pack(side=tk.LEFT, padx=2)
        
        # Reason and status
        details_frame = ttk.Frame(form_frame, padding=10)
        details_frame.pack(fill=tk.X)
        
        # Reason
        ttk.Label(details_frame, text="سبب الزيارة | Reason:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        reason_combo = ttk.Combobox(details_frame, textvariable=self.reason_var, values=self.common_reasons, width=30)
        reason_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Status
        ttk.Label(details_frame, text="الحالة | Status:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        status_combo = ttk.Combobox(
            details_frame, 
            textvariable=self.status_var, 
            values=list(self.status_types.keys()), 
            width=30,
            state="readonly"
        )
        status_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Notes section
        notes_frame = ttk.LabelFrame(form_frame, text="ملاحظات | Notes")
        notes_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.notes_text = tk.Text(notes_frame, wrap=tk.WORD, height=5)
        self.notes_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            button_frame,
            text="حفظ | Save",
            command=self.save_appointment
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="إلغاء | Cancel",
            command=self.appointment_dialog.destroy
        ).pack(side=tk.RIGHT, padx=5)
        
        # If we have a selected appointment, load its data
        if self.selected_appointment_id:
            self.load_appointment(self.selected_appointment_id)

    def set_end_time_from_duration(self, duration):
        """Calculate end time based on start time and duration in minutes"""
        try:
            start_time = self.start_time_var.get()
            if not start_time:
                messagebox.showwarning(
                    "تحذير | Warning",
                    "يرجى تحديد وقت البدء أولاً | Please select start time first"
                )
                return
                
            # Parse start time
            start_hour, start_min = map(int, start_time.split(':'))
            
            # Calculate end time
            total_minutes = start_hour * 60 + start_min + duration
            end_hour = total_minutes // 60
            end_min = total_minutes % 60
            
            # Format end time
            end_time = f"{end_hour:02d}:{end_min:02d}"
            
            # Set end time
            self.end_time_var.set(end_time)
            
        except Exception as e:
            print(f"Error calculating end time: {e}")

    def print_schedule(self, date=None):
        """Generate and print a schedule for the selected date"""
        if date is None:
            date = self.selected_date
        
        try:
            # Get appointments for the selected date
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT a.id, a.start_time, a.end_time, p.name, p.phone, 
                       a.reason, a.status, a.notes
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                WHERE a.appointment_date = ?
                ORDER BY a.start_time
            ''', (date.isoformat(),))
            
            appointments = cursor.fetchall()
            
            if not appointments:
                messagebox.showinfo(
                    "معلومات | Information",
                    f"لا توجد مواعيد في {date.isoformat()} | No appointments on {date.isoformat()}"
                )
                return
            
            # Create report directory if it doesn't exist
            report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
            if not os.path.exists(report_dir):
                os.makedirs(report_dir)
            
            # Generate PDF filename
            filename = os.path.join(report_dir, f"schedule_{date.isoformat()}.pdf")
            
            # Try to import PDF generation libraries
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.lib import colors
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont
                
                # Register Arabic font if available
                if self.arabic_font:
                    pdfmetrics.registerFont(TTFont('Arabic', self.arabic_font))
                    arabic_style = ParagraphStyle(
                        'Arabic',
                        fontName='Arabic',
                        fontSize=12,
                        leading=14,
                        alignment=1  # Center aligned
                    )
                else:
                    arabic_style = ParagraphStyle(
                        'DefaultArabic',
                        fontSize=12,
                        leading=14,
                        alignment=1  # Center aligned
                    )
                
                # Create document
                doc = SimpleDocTemplate(filename, pagesize=A4)
                elements = []
                
                # Add styles
                styles = getSampleStyleSheet()
                title_style = styles['Title']
                normal_style = styles['Normal']
                
                # Add title
                weekday = date.strftime("%A")
                weekday_ar = {
                    "Monday": "الاثنين",
                    "Tuesday": "الثلاثاء",
                    "Wednesday": "الأربعاء",
                    "Thursday": "الخميس",
                    "Friday": "الجمعة",
                    "Saturday": "السبت",
                    "Sunday": "الأحد"
                }.get(weekday, weekday)
                
                # Add clinic title
                if self.arabic_font:
                    elements.append(Paragraph(f"جدول المواعيد | Appointment Schedule", arabic_style))
                else:
                    elements.append(Paragraph("Appointment Schedule | جدول المواعيد", title_style))
                
                # Add date
                elements.append(Paragraph(f"{date.isoformat()} - {weekday_ar} | {weekday}", normal_style))
                elements.append(Spacer(1, 20))
                
                # Build table data
                headers = ["الوقت | Time", "المريض | Patient", "الهاتف | Phone", 
                          "السبب | Reason", "الحالة | Status"]
                
                data = [headers]
                
                for appointment in appointments:
                    appt_id, start_time, end_time, name, phone, reason, status, notes = appointment
                    
                    # Process Arabic text
                    name = self.process_arabic_text(name) if name else ""
                    reason = self.process_arabic_text(reason) if reason else ""
                    status = self.process_arabic_text(status) if status else ""
                    
                    # Format time
                    time_str = f"{start_time} - {end_time}"
                    
                    # Add to table
                    data.append([time_str, name, phone, reason, status])
                
                # Create table
                table = Table(data)
                
                # Style the table
                style = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ])
                
                # Add alternating row colors
                for i in range(1, len(data)):
                    if i % 2 == 0:
                        style.add('BACKGROUND', (0, i), (-1, i), colors.lightgrey)
                
                table.setStyle(style)
                elements.append(table)
                
                # Add summary
                elements.append(Spacer(1, 20))
                elements.append(Paragraph(f"إجمالي المواعيد | Total appointments: {len(appointments)}", normal_style))
                
                # Add time of printing
                now = datetime.now()
                elements.append(Paragraph(f"تم الطباعة | Printed: {now.strftime('%Y-%m-%d %H:%M')}", normal_style))
                
                # Build PDF
                doc.build(elements)
                
                # Open the generated PDF
                if sys.platform == 'win32':
                    os.startfile(filename)
                elif sys.platform == 'darwin':  # macOS
                    subprocess.Popen(['open', filename])
                else:  # Linux
                    subprocess.Popen(['xdg-open', filename])
                    
                # Update status
                self.set_status(f"تم إنشاء جدول المواعيد | Schedule created: {filename}")
                
            except ImportError:
                # If ReportLab is not available, fall back to simple text output
                messagebox.showinfo(
                    "معلومات | Information",
                    "مكتبة ReportLab غير متوفرة، سيتم إنشاء ملف نصي | ReportLab not available, creating text file"
                )
                
                # Create text file
                filename = os.path.join(report_dir, f"schedule_{date.isoformat()}.txt")
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"جدول المواعيد | Appointment Schedule\n")
                    f.write(f"{date.isoformat()} - {weekday_ar} | {weekday}\n")
                    f.write("="*50 + "\n\n")
                    
                    f.write(f"{'الوقت | Time':<15}{'المريض | Patient':<25}{'الهاتف | Phone':<15}")
                    f.write(f"{'السبب | Reason':<25}{'الحالة | Status':<15}\n")
                    f.write("-"*100 + "\n")
                    
                    for appointment in appointments:
                        appt_id, start_time, end_time, name, phone, reason, status, notes = appointment
                        time_str = f"{start_time} - {end_time}"
                        
                        # Process Arabic text
                        name = self.process_arabic_text(name) if name else ""
                        reason = self.process_arabic_text(reason) if reason else ""
                        status = self.process_arabic_text(status) if status else ""
                        
                        f.write(f"{time_str:<15}{name:<25}{phone:<15}{reason:<25}{status:<15}\n")
                    
                    f.write("\n" + "="*50 + "\n")
                    f.write(f"إجمالي المواعيد | Total appointments: {len(appointments)}\n")
                    now = datetime.now()
                    f.write(f"تم الطباعة | Printed: {now.strftime('%Y-%m-%d %H:%M')}\n")
                
                # Open the text file
                if sys.platform == 'win32':
                    os.startfile(filename)
                elif sys.platform == 'darwin':  # macOS
                    subprocess.Popen(['open', filename])
                else:  # Linux
                    subprocess.Popen(['xdg-open', filename])
                    
                # Update status
                self.set_status(f"تم إنشاء جدول المواعيد كملف نصي | Schedule created as text file: {filename}")
        
        except Exception as e:
            messagebox.showerror(
                "خطأ | Error",
                f"فشل في إنشاء جدول المواعيد: {e} | Failed to create schedule: {e}"
            )
            print(f"Error creating schedule: {e}")
            import traceback
            traceback.print_exc()
        
    def print_patient_history(self, patient_id):
        """Generate and print a patient appointment history report"""
        try:
            # Get patient info
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, name, phone, gender, date_of_birth FROM patients WHERE id = ?", (patient_id,))
            patient = cursor.fetchone()
            
            if not patient:
                messagebox.showerror(
                    "خطأ | Error",
                    "لم يتم العثور على المريض | Patient not found"
                )
                return
            
            patient_id, name, phone, gender, dob = patient
            
            # Get appointment history
            cursor.execute('''
                SELECT a.id, a.appointment_date, a.start_time, a.end_time, 
                       a.reason, a.status, a.notes
                FROM appointments a
                WHERE a.patient_id = ?
                ORDER BY a.appointment_date DESC, a.start_time DESC
            ''', (patient_id,))
            
            appointments = cursor.fetchall()
            
            if not appointments:
                messagebox.showinfo(
                    "معلومات | Information",
                    f"لا يوجد سجل مواعيد للمريض {self.process_arabic_text(name)} | No appointment history for patient {name}"
                )
                return
            
            # Create report directory if it doesn't exist
            report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
            if not os.path.exists(report_dir):
                os.makedirs(report_dir)
            
            # Generate PDF filename
            filename = os.path.join(report_dir, f"patient_{patient_id}_history.pdf")
            
            # Try to import PDF generation libraries
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.lib import colors
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont
                
                # Register Arabic font if available
                if self.arabic_font:
                    pdfmetrics.registerFont(TTFont('Arabic', self.arabic_font))
                    arabic_style = ParagraphStyle(
                        'Arabic',
                        fontName='Arabic',
                        fontSize=12,
                        leading=14,
                        alignment=1  # Center aligned
                    )
                else:
                    arabic_style = ParagraphStyle(
                        'DefaultArabic',
                        fontSize=12,
                        leading=14,
                        alignment=1  # Center aligned
                    )
                
                # Create document
                doc = SimpleDocTemplate(filename, pagesize=A4)
                elements = []
                
                # Add styles
                styles = getSampleStyleSheet()
                title_style = styles['Title']
                heading_style = styles['Heading1']
                normal_style = styles['Normal']
                
                # Add title
                elements.append(Paragraph("سجل مواعيد المريض | Patient Appointment History", title_style))
                elements.append(Spacer(1, 20))
                
                # Add patient info table
                patient_data = [
                    ["رقم المريض | Patient ID:", str(patient_id)],
                    ["الاسم | Name:", self.process_arabic_text(name)],
                    ["الهاتف | Phone:", phone if phone else ""],
                    ["الجنس | Gender:", self.process_arabic_text(gender) if gender else ""],
                    ["تاريخ الميلاد | DOB:", dob if dob else ""]
                ]
                
                patient_table = Table(patient_data, colWidths=[150, 350])
                patient_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('PADDING', (0, 0), (-1, -1), 6),
                ]))
                
                elements.append(patient_table)
                elements.append(Spacer(1, 20))
                
                # Add appointments heading
                elements.append(Paragraph("المواعيد | Appointments", heading_style))
                elements.append(Spacer(1, 10))
                
                # Build appointments table
                headers = ["التاريخ | Date", "الوقت | Time", "السبب | Reason", "الحالة | Status"]
                
                data = [headers]
                
                for appointment in appointments:
                    appt_id, appt_date, start_time, end_time, reason, status, notes = appointment
                    
                    # Process Arabic text
                    reason = self.process_arabic_text(reason) if reason else ""
                    status = self.process_arabic_text(status) if status else ""
                    
                    # Format time
                    time_str = f"{start_time} - {end_time}"
                    
                    # Add to table
                    data.append([appt_date, time_str, reason, status])
                
                # Create table
                table = Table(data)
                
                # Style the table
                style = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ])
                
                # Add alternating row colors
                for i in range(1, len(data)):
                    if i % 2 == 0:
                        style.add('BACKGROUND', (0, i), (-1, i), colors.lightgrey)
                
                table.setStyle(style)
                elements.append(table)
                
                # Add summary
                elements.append(Spacer(1, 20))
                elements.append(Paragraph(f"إجمالي المواعيد | Total appointments: {len(appointments)}", normal_style))
                
                # Add time of printing
                now = datetime.now()
                elements.append(Paragraph(f"تم الطباعة | Printed: {now.strftime('%Y-%m-%d %H:%M')}", normal_style))
                
                # Build PDF
                doc.build(elements)
                
                # Open the generated PDF
                if sys.platform == 'win32':
                    os.startfile(filename)
                elif sys.platform == 'darwin':  # macOS
                    subprocess.Popen(['open', filename])
                else:  # Linux
                    subprocess.Popen(['xdg-open', filename])
                    
                # Update status
                self.set_status(f"تم إنشاء سجل المريض | Patient history created: {filename}")
                
            except ImportError:
                # If ReportLab is not available, fall back to simple text output
                messagebox.showinfo(
                    "معلومات | Information",
                    "مكتبة ReportLab غير متوفرة، سيتم إنشاء ملف نصي | ReportLab not available, creating text file"
                )
                
                # Create text file
                filename = os.path.join(report_dir, f"patient_{patient_id}_history.txt")
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"سجل مواعيد المريض | Patient Appointment History\n")
                    f.write("="*50 + "\n\n")
                    
                    f.write(f"رقم المريض | Patient ID: {patient_id}\n")
                    f.write(f"الاسم | Name: {self.process_arabic_text(name)}\n")
                    f.write(f"الهاتف | Phone: {phone if phone else ''}\n")
                    f.write(f"الجنس | Gender: {self.process_arabic_text(gender) if gender else ''}\n")
                    f.write(f"تاريخ الميلاد | DOB: {dob if dob else ''}\n\n")
                    
                    f.write("المواعيد | Appointments\n")
                    f.write("-"*50 + "\n")
                    
                    f.write(f"{'التاريخ | Date':<15}{'الوقت | Time':<15}")
                    f.write(f"{'السبب | Reason':<25}{'الحالة | Status':<15}\n")
                    f.write("-"*70 + "\n")
                    
                    for appointment in appointments:
                        appt_id, appt_date, start_time, end_time, reason, status, notes = appointment
                        time_str = f"{start_time} - {end_time}"
                        
                        # Process Arabic text
                        reason = self.process_arabic_text(reason) if reason else ""
                        status = self.process_arabic_text(status) if status else ""
                        
                        f.write(f"{appt_date:<15}{time_str:<15}{reason:<25}{status:<15}\n")
                    
                    f.write("\n" + "="*50 + "\n")
                    f.write(f"إجمالي المواعيد | Total appointments: {len(appointments)}\n")
                    now = datetime.now()
                    f.write(f"تم الطباعة | Printed: {now.strftime('%Y-%m-%d %H:%M')}\n")
                
                # Open the text file
                if sys.platform == 'win32':
                    os.startfile(filename)
                elif sys.platform == 'darwin':  # macOS
                    subprocess.Popen(['open', filename])
                else:  # Linux
                    subprocess.Popen(['xdg-open', filename])
                    
                # Update status
                self.set_status(f"تم إنشاء سجل المريض كملف نصي | Patient history created as text file: {filename}")
        
        except Exception as e:
            messagebox.showerror(
                "خطأ | Error",
                f"فشل في إنشاء سجل المريض: {e} | Failed to create patient history: {e}"
            )
            print(f"Error creating patient history: {e}")
            import traceback
            traceback.print_exc()

    def get_dates_with_appointments(self, year=None, month=None):
        """Get a list of dates in the specified month that have appointments"""
        if year is None:
            year = self.cal_year
        if month is None:
            month = self.cal_month
        
        # Format dates for the query
        first_day = f"{year:04d}-{month:02d}-01"
        
        # Calculate last day of month
        if month == 12:
            last_day = f"{year+1:04d}-01-01"
        else:
            last_day = f"{year:04d}-{month+1:02d}-01"
        
        dates_with_appointments = []
        
        try:
            # Create a completely new connection and cursor
            import sqlite3
            db_path = getattr(self, 'db_path', 'clinic.db')
            
            # Hard-coded SQL query that returns just the days of month
            sql = f"""
            SELECT DISTINCT CAST(strftime('%d', appointment_date) AS INTEGER) as day
            FROM appointments
            WHERE appointment_date >= '{first_day}' 
            AND appointment_date < '{last_day}'
            """
            
            # Execute the query directly to get day numbers
            try:
                # Try with existing connection first
                self.conn.execute("SELECT 1")  # Test if connection is alive
                
                # Manual approach without using fetchall/fetchone
                days = []
                for row in self.conn.execute(sql):
                    if row and row[0]:
                        days.append(int(row[0]))
                
                return days
                
            except Exception as conn_error:
                print(f"Error with existing connection: {conn_error}")
                
                # Fallback to a new connection
                with sqlite3.connect(db_path) as new_conn:
                    days = []
                    for row in new_conn.execute(sql):
                        if row and row[0]:
                            days.append(int(row[0]))
                    
                    return days
        
        except Exception as e:
            print(f"Error getting dates with appointments: {e}")
            import traceback
            traceback.print_exc()
            return []

        return dates_with_appointments

    

    def call_patient(self):
        """Notify that the patient is being called for their appointment"""
        # Get selected appointment
        selected = self.appointments_tree.selection()
        if not selected:
            messagebox.showwarning(
                "تحذير | Warning",
                "يرجى تحديد موعد | Please select an appointment"
            )
            return
        
        # Get appointment ID
        appointment_id = selected[0]
        
        try:
            # Get appointment details
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT a.status, p.name, a.start_time
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                WHERE a.id = ?
            ''', (appointment_id,))
            
            status, patient_name, start_time = cursor.fetchone()
            
            # Create confirmation dialog
            confirm = messagebox.askyesno(
                "تأكيد | Confirmation",
                f"هل تريد نداء المريض {self.process_arabic_text(patient_name)}؟\nDo you want to call patient {patient_name}?"
            )
            
            if not confirm:
                return
            
            # Update appointment status
            new_status = "تم الحضور | Arrived"
            cursor.execute(
                "UPDATE appointments SET status = ? WHERE id = ?",
                (new_status, appointment_id)
            )
            
            # Log the status change
            cursor.execute('''
                INSERT INTO appointments_history
                (appointment_id, action, old_status, new_status, timestamp, user)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                appointment_id,
                "STATUS_CHANGE",
                status,
                new_status,
                datetime.now().isoformat(),
                "current_user"  # TODO: Use actual logged-in user
            ))
            
            self.conn.commit()
            
            # Update display
            self.update_appointments()
            
            # Show success message
            self.set_status(f"تم نداء المريض: {self.process_arabic_text(patient_name)} | Called patient: {patient_name}")
            
            # Optional: Play sound or visual effect
            self.play_notification_sound()
            
            # Show notification window
            self.show_patient_notification(patient_name, start_time)
            
        except Exception as e:
            messagebox.showerror(
                "خطأ | Error",
                f"فشل في نداء المريض: {e} | Failed to call patient: {e}"
            )
            print(f"Error calling patient: {e}")

    def show_patient_notification(self, patient_name, appointment_time):
        """Show a popup notification when calling a patient"""
        notification = tk.Toplevel(self.parent)
        notification.title("نداء المريض | Patient Call")
        notification.attributes('-topmost', True)  # Keep on top
        
        # Set size and position
        notification.geometry("400x200+50+50")
        
        # Main frame - use tk.Frame instead of ttk.Frame for background color changes
        frame = tk.Frame(notification, padx=20, pady=20)  # Changed to tk.Frame
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header = ttk.Label(
            frame, 
            text="نداء المريض | Patient Call",
            font=("Arial", 16, "bold")
        )
        header.pack(pady=(0, 20))
        
        # Patient name
        name_label = ttk.Label(
            frame,
            text=f"{self.process_arabic_text(patient_name)}",
            font=("Arial", 20, "bold")
        )
        name_label.pack(pady=10)
        
        # Appointment time
        time_label = ttk.Label(
            frame,
            text=f"الموعد | Appointment: {appointment_time}",
            font=("Arial", 12)
        )
        time_label.pack(pady=5)
        
        # Auto-close after 10 seconds
        notification.after(10000, notification.destroy)
        
        # Close button
        close_btn = ttk.Button(
            frame,
            text="إغلاق | Close",
            command=notification.destroy
        )
        close_btn.pack(pady=10)
        
        # Flash effect to draw attention
        def flash():
            if not notification.winfo_exists():
                return
                
            # Use configure for tk.Frame (works with background)
            current_bg = frame["background"]
            new_bg = "yellow" if current_bg != "yellow" else "systemWindowBody"
            frame.configure(background=new_bg)
            
            # Continue flashing if window exists
            if notification.winfo_exists():
                notification.after(500, flash)
        
        # Start flashing
        notification.after(100, flash)

    def play_notification_sound(self):
        """Play a notification sound when calling a patient"""
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except:
            # Not on Windows or winsound not available
            pass

    def add_new_patient(self):
        """Add a new patient to the database"""
        # Create a new window for patient information
        patient_window = tk.Toplevel(self.parent)
        patient_window.title("إضافة مريض جديد | Add New Patient")
        patient_window.geometry("450x400")
        patient_window.resizable(False, False)
        
        # Create a frame for the form
        form_frame = ttk.Frame(patient_window, padding=20)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Name field
        ttk.Label(form_frame, text="👤 الاسم | Name:").grid(row=0, column=0, sticky="w", pady=10)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(form_frame, width=30, textvariable=name_var)
        name_entry.grid(row=0, column=1, sticky="ew", pady=10)
        name_entry.focus()  # Set focus on name field
        
        # Phone field
        ttk.Label(form_frame, text="📞 رقم الهاتف | Phone:").grid(row=1, column=0, sticky="w", pady=10)
        phone_var = tk.StringVar()
        phone_entry = ttk.Entry(form_frame, width=30, textvariable=phone_var)
        phone_entry.grid(row=1, column=1, sticky="ew", pady=10)
        
        # Email field
        ttk.Label(form_frame, text="✉️ البريد الإلكتروني | Email:").grid(row=2, column=0, sticky="w", pady=10)
        email_var = tk.StringVar()
        email_entry = ttk.Entry(form_frame, width=30, textvariable=email_var)
        email_entry.grid(row=2, column=1, sticky="ew", pady=10)
        
        # Date of birth field
        ttk.Label(form_frame, text="🎂 تاريخ الميلاد | DOB:").grid(row=3, column=0, sticky="w", pady=10)
        dob_var = tk.StringVar()
        dob_entry = ttk.Entry(form_frame, width=30, textvariable=dob_var)
        dob_entry.grid(row=3, column=1, sticky="w", pady=10)
        dob_entry.insert(0, "YYYY-MM-DD")
        
        # Gender field
        ttk.Label(form_frame, text="⚧️ الجنس | Gender:").grid(row=4, column=0, sticky="w", pady=10)
        gender_var = tk.StringVar()
        gender_frame = ttk.Frame(form_frame)
        gender_frame.grid(row=4, column=1, sticky="w", pady=10)
        
        ttk.Radiobutton(gender_frame, text="ذكر | Male", variable=gender_var, value="Male").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(gender_frame, text="أنثى | Female", variable=gender_var, value="Female").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(gender_frame, text="آخر | Other", variable=gender_var, value="Other").pack(side=tk.LEFT, padx=5)
        
        # Add notes field (will be shown but not saved if column doesn't exist)
        ttk.Label(form_frame, text="📝 ملاحظات | Notes:").grid(row=5, column=0, sticky="nw", pady=10)
        notes_text = tk.Text(form_frame, width=30, height=4)
        notes_text.grid(row=5, column=1, sticky="ew", pady=10)
        
        # Button frame
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=20)
        
        # Save function
        def save_patient():
            # Validate required fields
            if not name_var.get().strip():
                messagebox.showwarning(
                    "Required Field | حقل مطلوب",
                    "Name is required | الاسم مطلوب"
                )
                name_entry.focus()
                return
                
            try:
                # Get form data
                name = name_var.get().strip()
                phone = phone_var.get().strip()
                email = email_var.get().strip()
                dob = dob_var.get().strip()
                gender = gender_var.get()
                
                # Validate DOB format if provided
                if dob and dob != "YYYY-MM-DD":
                    try:
                        datetime.strptime(dob, '%Y-%m-%d')
                    except ValueError:
                        messagebox.showwarning(
                            "Invalid Date | تاريخ غير صالح",
                            "Date of birth must be in YYYY-MM-DD format | يجب أن يكون تاريخ الميلاد بتنسيق YYYY-MM-DD"
                        )
                        return
                else:
                    dob = None
                    
                # Check table structure
                cursor = self.conn.cursor()
                cursor.execute("PRAGMA table_info(patients)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Adjust SQL based on available columns
                if 'notes' in columns:
                    # If notes column exists, include it
                    notes = notes_text.get(1.0, tk.END).strip()
                    cursor.execute('''
                        INSERT INTO patients
                        (name, phone, email, date_of_birth, gender, notes, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (name, phone, email, dob, gender, notes))
                else:
                    # If notes column doesn't exist, exclude it
                    if 'created_at' in columns:
                        cursor.execute('''
                            INSERT INTO patients
                            (name, phone, email, date_of_birth, gender, created_at)
                            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        ''', (name, phone, email, dob, gender))
                    else:
                        cursor.execute('''
                            INSERT INTO patients
                            (name, phone, email, date_of_birth, gender)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (name, phone, email, dob, gender))
                
                self.conn.commit()
                
                # Get new patient ID
                patient_id = cursor.lastrowid
                
                # Close window
                patient_window.destroy()
                
                # Reload patients in combobox
                self.load_patients()
                
                # Set the new patient as selected
                formatted_name = f"{patient_id} - {name}"
                self.patient_var.set(formatted_name)
                
                # Show success message
                self.set_status(f"✅ تم إضافة المريض بنجاح: {name} | Patient added successfully: {name}")
                messagebox.showinfo(
                    "Success | نجاح",
                    f"Patient added successfully | تم إضافة المريض بنجاح"
                )
                
            except Exception as e:
                messagebox.showerror(
                    "Error | خطأ",
                    f"Failed to add patient: {e} | فشل في إضافة المريض: {e}"
                )
                print(f"Error adding patient: {e}")
                import traceback
                traceback.print_exc()
        
        # Save button
        ttk.Button(
            button_frame,
            text="💾 حفظ | Save",
            style="Accent.TButton",
            command=save_patient
        ).pack(side=tk.LEFT, padx=10)
        
        # Cancel button
        ttk.Button(
            button_frame,
            text="❌ إلغاء | Cancel",
            command=patient_window.destroy
        ).pack(side=tk.LEFT, padx=10)
        
        # Make the grid expandable
        form_frame.columnconfigure(1, weight=1)
        
        # Center the window on screen
        patient_window.update_idletasks()
        width = patient_window.winfo_width()
        height = patient_window.winfo_height()
        x = (patient_window.winfo_screenwidth() // 2) - (width // 2)
        y = (patient_window.winfo_screenheight() // 2) - (height // 2)
        patient_window.geometry(f'{width}x{height}+{x}+{y}')
        
        # Make window modal
        patient_window.transient(self.parent)
        patient_window.grab_set()
        self.parent.wait_window(patient_window)
                
    def convert_timestamp(val):
        """Convert timestamp from SQLite format to Python datetime object"""
        if val is None:
            return None
        try:
            # Try ISO format first
            return datetime.fromisoformat(val.decode())
        except:
            try:
                # Try other common formats
                formats = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']
                for fmt in formats:
                    try:
                        return datetime.strptime(val.decode(), fmt)
                    except:
                        continue
                # If all fails, return the raw value
                return val
            except:
                return val

        def convert_date(val):
            """Convert date from SQLite format to Python date object"""
            if val is None:
                return None
            try:
                # Try ISO format first
                return date.fromisoformat(val.decode())
            except:
                try:
                    # Try other common formats
                    formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']
                    for fmt in formats:
                        try:
                            return datetime.strptime(val.decode(), fmt).date()
                        except:
                            continue
                    # If all fails, return the raw value
                    return val
                except:
                    return val
    
    def safe_parse_date(self, date_str):
        """Safely parse any date string, specifically handling '2025-03-09 00:00:00' format"""
        if not date_str:
            return None
                
        # If it's already a date object
        if isinstance(date_str, date) and not isinstance(date_str, datetime):
            return date_str
                
        # If it's a datetime object
        if isinstance(date_str, datetime):
            return date_str.date()
        
        # Convert bytes to string if needed
        if isinstance(date_str, bytes):
            date_str = date_str.decode()
                
        # Handle the specific format causing the error: "2025-03-09 00:00:00"
        if isinstance(date_str, str):
            # First handle the datetime format
            if ' ' in date_str and ':' in date_str:
                try:
                    # This specifically handles the format causing the error
                    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').date()
                except ValueError:
                    # If that fails, try just extracting the date part
                    date_part = date_str.split(' ')[0]
                    try:
                        return date.fromisoformat(date_part)
                    except ValueError:
                        print(f"Failed to parse datetime string: {date_str}")
            
            # Handle ISO format date string
            try:
                return date.fromisoformat(date_str)
            except ValueError:
                # Try other common formats
                for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y']:
                    try:
                        return datetime.strptime(date_str, fmt).date()
                    except ValueError:
                        continue
        
        # If we get here, we couldn't parse the date
        print(f"Unrecognized date format: {date_str}")
        return None

    def send_sms(self):
        """Send SMS notification to patient"""
        try:
            # Get selected appointment
            selected = self.appointments_tree.selection()
            if not selected:
                messagebox.showwarning(
                    "تحذير | Warning",
                    "يرجى تحديد موعد | Please select an appointment"
                )
                return
            
            # Get patient phone number
            appointment_id = selected[0]
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT p.phone, p.name, a.appointment_date, a.start_time
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                WHERE a.id = ?
            ''', (appointment_id,))
            
            result = cursor.fetchone()
            if not result:
                messagebox.showerror(
                    "خطأ | Error",
                    "لم يتم العثور على معلومات المريض | Patient information not found"
                )
                return
                
            phone, name, appt_date, appt_time = result
            
            if not phone:
                messagebox.showwarning(
                    "تحذير | Warning",
                    "لا يوجد رقم هاتف للمريض | No phone number for patient"
                )
                return
            
            # Show SMS dialog
            sms_dialog = tk.Toplevel(self.parent)
            sms_dialog.title("إرسال رسالة قصيرة | Send SMS")
            sms_dialog.geometry("500x400")
            sms_dialog.transient(self.parent)
            sms_dialog.grab_set()
            
            # Create form
            form_frame = ttk.Frame(sms_dialog, padding=10)
            form_frame.pack(fill=tk.BOTH, expand=True)
            
            # Display patient info
            ttk.Label(form_frame, text="المريض | Patient:").grid(row=0, column=0, sticky=tk.E, padx=5, pady=5)
            ttk.Label(form_frame, text=name).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
            
            ttk.Label(form_frame, text="الهاتف | Phone:").grid(row=1, column=0, sticky=tk.E, padx=5, pady=5)
            ttk.Label(form_frame, text=phone).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
            
            ttk.Label(form_frame, text="الموعد | Appointment:").grid(row=2, column=0, sticky=tk.E, padx=5, pady=5)
            ttk.Label(form_frame, text=f"{appt_date} {appt_time}").grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
            
            # SMS templates
            ttk.Label(form_frame, text="قالب | Template:").grid(row=3, column=0, sticky=tk.E, padx=5, pady=5)
            templates = [
                "تذكير بالموعد | Appointment reminder",
                "تأكيد موعد | Appointment confirmation",
                "إلغاء موعد | Appointment cancellation",
                "تغيير موعد | Appointment rescheduling",
                "رسالة مخصصة | Custom message"
            ]
            template_var = tk.StringVar()
            template_combo = ttk.Combobox(form_frame, textvariable=template_var, values=templates, state="readonly", width=30)
            template_combo.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
            template_combo.current(0)
            
            # Message text
            ttk.Label(form_frame, text="الرسالة | Message:").grid(row=4, column=0, sticky=tk.NE, padx=5, pady=5)
            message_text = tk.Text(form_frame, height=8, width=40)
            message_text.grid(row=4, column=1, sticky=tk.EW, padx=5, pady=5)
            
            # Populate message text based on template
            def populate_message(*args):
                template = template_var.get()
                message = ""
                
                if "تذكير" in template or "reminder" in template.lower():
                    message = f"تذكير: لديك موعد في {appt_date} الساعة {appt_time}."
                    message += f"\nReminder: You have an appointment on {appt_date} at {appt_time}."
                elif "تأكيد" in template or "confirmation" in template.lower():
                    message = f"تم تأكيد موعدك في {appt_date} الساعة {appt_time}."
                    message += f"\nYour appointment on {appt_date} at {appt_time} is confirmed."
                elif "إلغاء" in template or "cancellation" in template.lower():
                    message = f"تم إلغاء موعدك في {appt_date} الساعة {appt_time}."
                    message += f"\nYour appointment on {appt_date} at {appt_time} has been cancelled."
                elif "تغيير" in template or "rescheduling" in template.lower():
                    message = f"تم تغيير موعدك من {appt_date} الساعة {appt_time}."
                    message += f"\nYour appointment on {appt_date} at {appt_time} has been rescheduled."
                
                message_text.delete(1.0, tk.END)
                message_text.insert(tk.END, message)
            
            template_var.trace("w", populate_message)
            populate_message()  # Populate initial message
            
            # Buttons
            buttons_frame = ttk.Frame(form_frame)
            buttons_frame.grid(row=5, column=0, columnspan=2, pady=15)
            
            def send_message():
                """Send SMS message (not actually implemented)"""
                messagebox.showinfo(
                    "معلومات | Information",
                    "هذه ميزة تجريبية. لم يتم إرسال الرسالة فعليًا.\nThis is a demo feature. No actual SMS was sent."
                )
                self.set_status(f"تم محاكاة إرسال رسالة إلى {name} | Simulated sending SMS to {name}")
                sms_dialog.destroy()
            
            ttk.Button(buttons_frame, text="إرسال | Send", command=send_message).pack(side=tk.LEFT, padx=5)
            ttk.Button(buttons_frame, text="إلغاء | Cancel", command=sms_dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        except Exception as e:
            messagebox.showerror(
                "خطأ | Error",
                f"خطأ في إرسال الرسالة: {e} | Error sending SMS: {e}"
            )

    def export_patients_to_excel(self, patients):
        """Export patients data to Excel file"""
        try:
            # Try to import required modules
            try:
                import pandas as pd
            except ImportError:
                if messagebox.askyesno(
                    "مكتبة مطلوبة | Required Library",
                    "يتطلب تصدير البيانات إلى Excel تثبيت مكتبة pandas.\n"
                    "لتثبيت المكتبة، قم بتنفيذ الأمر التالي في Terminal:\n\n"
                    "pip install pandas openpyxl\n\n"
                    "هل ترغب في نسخ الأمر؟\n\n"
                    "Exporting to Excel requires the pandas library.\n"
                    "To install, run this command in Terminal:\n\n"
                    "pip install pandas openpyxl\n\n"
                    "Would you like to copy the command?"
                ):
                    # Copy command to clipboard
                    self.parent.clipboard_clear()
                    self.parent.clipboard_append("pip install pandas openpyxl")
                    messagebox.showinfo(
                        "تم النسخ | Copied",
                        "تم نسخ الأمر إلى الحافظة. الصقه في Terminal وقم بتنفيذه.\n"
                        "The command has been copied. Paste it in Terminal and run it."
                    )
                return
                
            # Check for openpyxl (included in the same pip command above)
            try:
                import openpyxl
            except ImportError:
                if messagebox.askyesno(
                    "مكتبة مطلوبة | Required Library",
                    "يتطلب تصدير البيانات إلى Excel تثبيت مكتبة openpyxl.\n"
                    "لتثبيت المكتبة، قم بتنفيذ الأمر التالي في Terminal:\n\n"
                    "pip install openpyxl\n\n"
                    "هل ترغب في نسخ الأمر؟\n\n"
                    "Exporting to Excel requires the openpyxl library.\n"
                    "To install, run this command in Terminal:\n\n"
                    "pip install openpyxl\n\n"
                    "Would you like to copy the command?"
                ):
                    # Copy command to clipboard
                    self.parent.clipboard_clear()
                    self.parent.clipboard_append("pip install openpyxl")
                    messagebox.showinfo(
                        "تم النسخ | Copied",
                        "تم نسخ الأمر إلى الحافظة. الصقه في Terminal وقم بتنفيذه.\n"
                        "The command has been copied. Paste it in Terminal and run it."
                    )
                return
                
            from tkinter import filedialog
            import platform
            import subprocess
            import os
            
            # Create a list to hold patient data
            data = []
            
            # Process each patient record
            for patient in patients:
                # Create a dictionary for this patient
                patient_data = {"ID": patient[0], "Name": patient[1]}
                
                # Add phone if available (index 2)
                if len(patient) > 2:
                    patient_data["Phone"] = patient[2]
                else:
                    patient_data["Phone"] = ""
                    
                # Add gender if available (index 3)
                if len(patient) > 3:
                    patient_data["Gender"] = patient[3]
                else:
                    patient_data["Gender"] = ""
                    
                # Add date of birth if available (index 4)
                dob = None
                if len(patient) > 4:
                    dob = patient[4]
                    
                # Process date - FIX FOR DATETIME FORMATS WITH TIME
                if dob:
                    try:
                        # If it's a string, try different date formats
                        if isinstance(dob, str):
                            # Try to parse date with time
                            if " " in dob:  # Contains space, like "2025-03-09 00:00:00"
                                dob = datetime.strptime(dob, "%Y-%m-%d %H:%M:%S").date().strftime("%Y-%m-%d")
                            else:  # Just date like "2025-03-09"
                                dob = datetime.strptime(dob, "%Y-%m-%d").date().strftime("%Y-%m-%d")
                        # If it's a datetime object, extract just the date part
                        elif isinstance(dob, datetime):
                            dob = dob.date().strftime("%Y-%m-%d")
                        # If it's already a date, just format it
                        else:
                            dob = dob.strftime("%Y-%m-%d")
                    except Exception as e:
                        # If parsing fails, just use as string but log the error
                        print(f"Date parsing error: {str(e)} for value: {dob}")
                        dob = str(dob)
                
                patient_data["Date of Birth"] = dob if dob else ""
                
                # Add any additional fields with generic column names
                for i in range(5, len(patient)):
                    patient_data[f"Field {i}"] = patient[i]
                    
                data.append(patient_data)
                
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Ask user for save location - using try/except to handle macOS warning
            try:
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".xlsx",
                    filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                    title="Save Patient List As"
                )
            except Exception as e:
                # Log the error but proceed
                print(f"Warning with file dialog: {e}")
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".xlsx",
                    filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                    title="Save Patient List As"
                )
            
            if not file_path:
                return  # User canceled
                
            # Export to Excel
            df.to_excel(file_path, index=False)
            
            # Show success message
            messagebox.showinfo(
                "نجاح | Success",
                f"تم تصدير {len(patients)} مريض بنجاح | Successfully exported {len(patients)} patients"
            )
            
            # Open the file
            if messagebox.askyesno(
                "فتح الملف | Open File",
                "هل تريد فتح الملف الآن؟ | Do you want to open the file now?"
            ):
                if platform.system() == 'Darwin':  # macOS
                    subprocess.call(('open', file_path))
                elif platform.system() == 'Windows':
                    os.startfile(file_path)
                else:  # Linux
                    subprocess.call(('xdg-open', file_path))
                    
        except Exception as e:
            messagebox.showerror(
                "خطأ | Error",
                f"فشل تصدير البيانات: {e} | Failed to export data: {e}"
            )

    def print_patients_list(self, patients):
        """Print a list of patients"""
        try:
            # Create a printable report
            report = tk.Toplevel(self.parent)
            report.title("طباعة قائمة المرضى | Print Patients List")
            report.geometry("800x600")
            report.transient(self.parent)
            report.grab_set()
            
            # Create report content
            report_frame = ttk.Frame(report, padding=20)
            report_frame.pack(fill=tk.BOTH, expand=True)
            
            # Header
            header = ttk.Label(
                report_frame,
                text="قائمة المرضى | Patients List",
                font=("Arial", 18, "bold")
            )
            header.pack(pady=(0, 20))
            
            # Date
            current_date = datetime.now().strftime("%Y-%m-%d")
            date_label = ttk.Label(
                report_frame,
                text=f"التاريخ | Date: {current_date}",
                font=("Arial", 10)
            )
            date_label.pack(anchor=tk.W, pady=(0, 10))
            
            # Create patients table
            table_frame = ttk.Frame(report_frame)
            table_frame.pack(fill=tk.BOTH, expand=True, pady=10)
            
            # Scrollbar
            scrollbar = ttk.Scrollbar(table_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Patients list
            columns = ("ID", "Name", "Phone", "Gender", "DOB")
            tree = ttk.Treeview(
                table_frame,
                columns=columns,
                show="headings",
                yscrollcommand=scrollbar.set
            )
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=tree.yview)
            
            # Configure columns
            tree.heading("ID", text="الرقم | ID")
            tree.heading("Name", text="الاسم | Name")
            tree.heading("Phone", text="الهاتف | Phone")
            tree.heading("Gender", text="الجنس | Gender")
            tree.heading("DOB", text="تاريخ الميلاد | DOB")
            
            tree.column("ID", width=50, anchor=tk.CENTER)
            tree.column("Name", width=200)
            tree.column("Phone", width=120)
            tree.column("Gender", width=100, anchor=tk.CENTER)
            tree.column("DOB", width=100, anchor=tk.CENTER)
            
            # Add patients
            for patient in patients:
                # Handle variable number of fields
                values = []
                # Add the fields we have
                for i in range(min(len(patient), len(columns))):
                    # Handle date formatting for DOB
                    if i == 4 and patient[i]:  # DOB column
                        try:
                            if isinstance(patient[i], str):
                                values.append(patient[i])
                            else:
                                values.append(patient[i].strftime("%Y-%m-%d"))
                        except:
                            values.append(str(patient[i]))
                    else:
                        values.append(patient[i])
                        
                # Add empty values for missing fields
                while len(values) < len(columns):
                    values.append("")
                    
                tree.insert("", tk.END, values=tuple(values))
                
            # Summary
            summary_label = ttk.Label(
                report_frame,
                text=f"إجمالي المرضى | Total patients: {len(patients)}",
                font=("Arial", 12, "bold")
            )
            summary_label.pack(anchor=tk.W, pady=(10, 20))
            
            # Print button
            def print_report():
                # Hide buttons for printing
                buttons_frame.pack_forget()
                
                # Print the window content
                try:
                    import tempfile
                    import os
                    
                    try:
                        from PIL import ImageGrab, Image
                    except ImportError:
                        if messagebox.askyesno(
                            "مكتبة مطلوبة | Required Library",
                            "تتطلب طباعة التقرير تثبيت مكتبة PIL/Pillow.\n"
                            "هل ترغب في فتح صفحة التثبيت؟\n\n"
                            "Printing reports requires the PIL/Pillow library.\n"
                            "Would you like to open installation instructions?"
                        ):
                            import webbrowser
                            webbrowser.open("https://pillow.readthedocs.io/en/stable/installation.html")
                        buttons_frame.pack(pady=10)
                        return
                    
                    # Make report window active for screenshot
                    report.focus_force()
                    report.update()
                    
                    # Slight delay to ensure window is active
                    report.after(500, lambda: capture_and_print())
                    
                    def capture_and_print():
                        try:
                            # Get window position and size
                            x = report.winfo_rootx()
                            y = report.winfo_rooty()
                            width = report.winfo_width()
                            height = report.winfo_height()
                            
                            # Capture screenshot
                            screenshot = ImageGrab.grab(bbox=(x, y, x+width, y+height))
                            
                            # Save to temp file
                            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                            screenshot.save(temp_file.name)
                            temp_file.close()
                            
                            # Open for printing
                            import platform
                            import subprocess
                            
                            if platform.system() == 'Darwin':  # macOS
                                subprocess.call(('open', '-a', 'Preview', temp_file.name))
                                messagebox.showinfo(
                                    "طباعة | Print",
                                    "تم فتح الصورة في برنامج معاينة. يرجى استخدام خيار الطباعة من القائمة.\n"
                                    "Image opened in Preview. Please use print option from the menu."
                                )
                            elif platform.system() == 'Windows':
                                os.startfile(temp_file.name, 'print')
                            else:  # Linux
                                subprocess.call(('xdg-open', temp_file.name))
                                messagebox.showinfo(
                                    "طباعة | Print",
                                    "تم فتح الصورة. يرجى استخدام خيار الطباعة من برنامج العرض.\n"
                                    "Image opened. Please use print option from your image viewer."
                                )
                            
                            # Show buttons again
                            buttons_frame.pack(pady=10)
                            
                        except Exception as e:
                            messagebox.showerror(
                                "خطأ | Error",
                                f"فشل في الطباعة: {e} | Failed to print: {e}"
                            )
                            buttons_frame.pack(pady=10)
                
                except Exception as e:
                    messagebox.showerror(
                        "خطأ | Error",
                        f"فشل في الطباعة: {e} | Failed to print: {e}"
                    )
                    buttons_frame.pack(pady=10)
            
            # Use standard buttons instead of create_rounded_button
            buttons_frame = ttk.Frame(report_frame)
            buttons_frame.pack(pady=10)
            
            ttk.Button(
                buttons_frame,
                text="طباعة | Print",
                command=print_report
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                buttons_frame,
                text="إغلاق | Close",
                command=report.destroy
            ).pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            messagebox.showerror(
                "خطأ | Error",
                f"فشل في إنشاء تقرير الطباعة: {e} | Failed to create print report: {e}"
            )

# Main application entry point
def main():
    root = tk.Tk()
    app = MainApplication(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
