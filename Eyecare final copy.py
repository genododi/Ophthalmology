
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

# Import DateEntry if tkcalendar is installed (pip install tkcalendar)
try:
    from tkcalendar import DateEntry
    HAS_TKCALENDAR = True
except ImportError:
    HAS_TKCALENDAR = False
    print("Warning: tkcalendar not found. Using simple Entry for dates.")
    print("Install using: pip install tkcalendar")

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
    """Convert stored ISO format string back to date object"""
    if not val:
        return None
    try:
        if isinstance(val, bytes):
            val = val.decode()
        # Handle both ISO format and other common formats
        try:
            return datetime.fromisoformat(val)
        except ValueError:
            for fmt in ['%d %B %Y', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                try:
                    return datetime.strptime(val, fmt).date()
                except ValueError:
                    continue
            raise ValueError(f"Unable to parse date: {val}")
    except Exception as e:
        print(f"Error converting date {val}: {e}")
        return None

# Update SQLite configuration with explicit converters
sqlite3.register_adapter(date, adapt_date)
sqlite3.register_converter("DATE", convert_date)

# Add this class definition before OphthalmologyEMR class
class MedicalReportTab:
    def __init__(self, tabs, parent):
        self.frame = ttk.Frame(tabs)
        # Add your medical report tab implementation here

class OphthalmologyEMR:
    def __init__(self, root):
        """Initialize the application"""
        self.root = root
        self.root.title("Ophthalmology EMR System")
        self.root.geometry("1200x800")
        
        # Initialize database connection
        self.conn = sqlite3.connect('ophthalmology_emr.db', 
                                  detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES,
                                  isolation_level=None)
        
        # Initialize autorefractor connection variables
        self.autorefractor_ip = None
        self.autorefractor_port = 8080  # Default port, can be configured
        self.autorefractor_connected = False
        self.autorefractor_socket = None
        self.connection_type = "lan"  # Default connection type: "lan" or "rs232"
        self.serial_connection = None  # For RS232 connection
        self.serial_port = None  # COM port for serial connection
        self.serial_baudrate = 9600  # Default baud rate for Topcon RM-800
        
        # Keep track of the currently selected patient/appointment in the secretary tab
        self.secretary_selected_patient_id = None
        self.secretary_selected_appointment_id = None
        # Keep track of selected investigation ID
        self.selected_investigation_id = None
        
        # Initialize database
        self.initialize_database()
        
        # Setup GUI
        self.setup_gui()
        
        # Start periodic connection check
        self.schedule_connection_check()
        
    def schedule_connection_check(self):
        """Schedule periodic check of autorefractor connection"""
        # Check connection status every 30 seconds
        self.check_autorefractor_connection()
        self.root.after(30000, self.schedule_connection_check)

    def initialize_database(self):
        """Initialize database tables"""
        try:
            cursor = self.conn.cursor()
            
            # Drop existing tables if they exist
            cursor.execute("DROP TABLE IF EXISTS medications")
            cursor.execute("DROP TABLE IF EXISTS investigations")
            
            # Create medications table
            cursor.execute('''
                CREATE TABLE medications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER,
                    type TEXT,
                    name TEXT,
                    dosage TEXT,
                    frequency TEXT,
                    duration TEXT,
                    tapering TEXT,
                    instructions TEXT,
                    notes TEXT,
                    date_prescribed TEXT,
                    FOREIGN KEY (patient_id) REFERENCES patients(id)
                )
            ''')
            
            # Create investigations table with all required columns
            cursor.execute('''
                CREATE TABLE investigations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER,
                    date DATE,
                    type TEXT,
                    details TEXT,
                    results TEXT,
                    recommendations TEXT,
                    FOREIGN KEY (patient_id) REFERENCES patients(id)
                )
            ''')
            
            # Create visits table to track patient visits
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER,
                    visit_date DATE,
                    reason TEXT,
                    notes TEXT,
                    FOREIGN KEY (patient_id) REFERENCES patients(id)
                )
            ''')
                
            self.conn.commit()
            print("Database initialized successfully")
            
        except Exception as e:
            print(f"Error initializing database: {e}")
            self.conn.rollback()

    def setup_gui(self):
        # Initialize main window
        self.root.title("Dr Mahmoud Sami Ophthalmologist    د محمود سامي طب و جراحة العيون")
        self.root.geometry("1500x1200")

        # Create menu bar
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)
        
        # File menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Help menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about_dialog)
        
        # Devices menu
        self.devices_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Devices", menu=self.devices_menu)
        
        # Autorefractor submenu
        autorefractor_menu = tk.Menu(self.devices_menu, tearoff=0)
        self.devices_menu.add_cascade(label="Autorefractor", menu=autorefractor_menu)
        autorefractor_menu.add_command(label="Connect to RM-800", command=self.connect_to_autorefractor)
        autorefractor_menu.add_command(label="Disconnect", command=self.disconnect_from_autorefractor)
        autorefractor_menu.add_separator()
        autorefractor_menu.add_command(label="Start Simulator", command=self.simulate_autorefractor_server)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both')

        # Create tabs
        self.patient_tab = ttk.Frame(self.notebook)
        self.exam_tab = ttk.Frame(self.notebook)
        self.prescription_tab = ttk.Frame(self.notebook)
        self.investigation_tab = ttk.Frame(self.notebook)
        self.treatment_tab = ttk.Frame(self.notebook)
        self.medical_report_frame = ttk.Frame(self.notebook)
        self.medications_tab = ttk.Frame(self.notebook)  # Add new medications tab
        self.secretary_tab = ttk.Frame(self.notebook)  # Add this line
        
        # Add tabs to notebook
        self.notebook.add(self.patient_tab, text='Patient Management')
        self.notebook.add(self.exam_tab, text='Eye Examination')
        self.notebook.add(self.prescription_tab, text='Prescription')
        self.notebook.add(self.investigation_tab, text="Investigation")
        self.notebook.add(self.treatment_tab, text='Treatment')
        self.notebook.add(self.medical_report_frame, text='Medical Reports')
        self.notebook.add(self.medications_tab, text='Medications')  # Add medications tab
        self.notebook.add(self.secretary_tab, text='السكرتارية | Secretary')  # Add this line
        
        # Add copyright status bar at the bottom
        self.status_bar = ttk.Frame(self.root, relief=tk.SUNKEN, borderwidth=1)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Copyright label with a professional font and styling
        copyright_text = "Designed & Coded by Ophthalmologist Dr Mahmoud Sami © 2025"
        self.copyright_label = ttk.Label(
            self.status_bar, 
            text=copyright_text,
            font=('Arial', 10, 'bold'),
            foreground='#333333',  # Darker gray for better visibility
            padding=(5, 3)  # Add some padding for better appearance
        )
        self.copyright_label.pack(side=tk.RIGHT, padx=10, pady=2)

        # Setup individual tabs
        self.setup_patient_tab()
        self.setup_exam_tab()
        self.setup_prescription_tab()
        self.setup_investigation_tab()
        self.setup_treatment_tab()
        self.setup_medical_report_tab()
        self.setup_medications_tab()
        self.setup_secretary_tab()

    def position_qr_code(self, c, patient_id, patient_name):
        """Position QR code in the top right corner of the PDF"""
        try:
            # Generate QR code
            qr_file = self.create_qr_code(
                patient_id=patient_id,
                patient_name=patient_name,
                date=datetime.now().strftime('%Y-%m-%d')
            )
            
            if qr_file and os.path.exists(qr_file):
    
                try:
                    # Position QR code in the top right corner with proper margins
                    c.drawImage(qr_file, 
                            letter[0] - 2.0*inch,  # X position (right side with margin)
                            letter[1] - 1.5*inch,  # Y position (top with margin)
                            width=1*inch, 
                            height=1*inch, 
                            preserveAspectRatio=True)
                finally:
                    # Clean up temporary QR code file
                    try:
                        os.remove(qr_file)
                    except:
                        pass
        except Exception as e:
            print(f"Error positioning QR code: {e}")
    
    def setup_patient_tab(self):
        """Setup enhanced patient management interface"""
        # Create main container with padding
        main_frame = ttk.Frame(self.patient_tab, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title with better styling
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(title_frame, text="Patient Management", 
                  font=('Arial', 16, 'bold')).pack(side=tk.LEFT)

        # Create left and right frames for better organization
        left_frame = ttk.LabelFrame(main_frame, text="Patient Information", padding="5")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        right_frame = ttk.LabelFrame(main_frame, text="Patient List", padding="5")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # Patient Information Form (Left Frame)
        form_frame = ttk.Frame(left_frame)
        form_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Input fields with better layout
        fields = [
            ("Name:", "name_entry"),
            ("Date of Birth:", "dob_entry"),
            ("Contact:", "contact_entry")
        ]

        for i, (label_text, entry_name) in enumerate(fields):
            field_frame = ttk.Frame(form_frame)
            field_frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(field_frame, text=label_text, width=15).pack(side=tk.LEFT)
            entry = ttk.Entry(field_frame)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
            setattr(self, entry_name, entry)

        # Medical History with label above
        history_frame = ttk.Frame(form_frame)
        history_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        ttk.Label(history_frame, text="Medical History:").pack(anchor=tk.W)
        history_container, self.history_text = self.create_bilingual_text_widget(history_frame, height=5)
        history_container.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # Buttons frame
        buttons_frame = ttk.Frame(left_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(buttons_frame, text="Add Patient", 
                   command=self.add_patient).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Save Changes", 
                   command=self.save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Clear Form", 
                   command=self.clear_patient_form).pack(side=tk.LEFT, padx=5)

        # Search Frame (Right Frame)
        search_frame = ttk.Frame(right_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))

        # Search fields with icons (you'll need to add icon files)
        ttk.Label(search_frame, text="ID:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_id_entry = ttk.Entry(search_frame, width=10)
        self.search_id_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(search_frame, text="Name:").pack(side=tk.LEFT, padx=(10, 5))
        self.search_name_entry = ttk.Entry(search_frame, width=20)
        self.search_name_entry.pack(side=tk.LEFT, padx=5)

        # Search buttons
        ttk.Button(search_frame, text="Search", 
                   command=self.search_patient).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Show All", 
                   command=self.refresh_patient_list).pack(side=tk.LEFT, padx=5)

        # Enhanced Patient List
        list_frame = ttk.Frame(right_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        # Create Treeview with scrollbars
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Vertical scrollbar
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Horizontal scrollbar
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        # Enhanced Treeview
        self.patient_tree = ttk.Treeview(tree_frame, columns=(
            'ID', 'Name', 'DOB', 'Contact', 'Last Visit'
        ), show='headings', selectmode='browse')
        
        # Configure scrollbars
        self.patient_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.configure(command=self.patient_tree.yview)
        hsb.configure(command=self.patient_tree.xview)

        # Configure columns
        self.patient_tree.heading('ID', text='ID', anchor=tk.W)
        self.patient_tree.heading('Name', text='Name', anchor=tk.W)
        self.patient_tree.heading('DOB', text='Date of Birth', anchor=tk.W)
        self.patient_tree.heading('Contact', text='Contact', anchor=tk.W)
        self.patient_tree.heading('Last Visit', text='Last Visit', anchor=tk.W)

        # Column widths
        self.patient_tree.column('ID', width=50, minwidth=50)
        self.patient_tree.column('Name', width=150, minwidth=100)
        self.patient_tree.column('DOB', width=100, minwidth=100)
        self.patient_tree.column('Contact', width=120, minwidth=100)
        self.patient_tree.column('Last Visit', width=100, minwidth=100)

        self.patient_tree.pack(fill=tk.BOTH, expand=True)

        # Bind select event
        self.patient_tree.bind('<<TreeviewSelect>>', self.on_patient_select)
        self.patient_tree.bind('<Double-1>', lambda e: self.edit_patient())

        # Action buttons below tree
        action_frame = ttk.Frame(right_frame)
        action_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(action_frame, text="Edit Patient", 
                   command=self.edit_patient).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Delete Patient", 
                   command=self.delete_patient).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="View History", 
                   command=self.show_visit_history).pack(side=tk.LEFT, padx=5)

        # Add alternating row colors
        self.patient_tree.tag_configure('oddrow', background='#f0f0f0')
        self.patient_tree.tag_configure('evenrow', background='#ffffff')

        # Refresh the patient list
        self.refresh_patient_list()

    def setup_exam_tab(self):
        # Examination Form
        ttk.Label(self.exam_tab, text="Eye Examination", font=('Arial', 14, 'bold')).grid(row=0, column=0, pady=10, padx=5)
        
        # Patient Selection
        ttk.Label(self.exam_tab, text="Patient ID:").grid(row=1, column=0, pady=5, padx=5)
        self.exam_patient_id = ttk.Entry(self.exam_tab)
        self.exam_patient_id.grid(row=1, column=1, pady=5, padx=5)
        
        # Autorefractor status indicator
        self.autorefractor_status = ttk.Label(self.exam_tab, text="Autorefractor: Not Connected", foreground="red")
        self.autorefractor_status.grid(row=1, column=2, pady=5, padx=5)
        
        # Unaided Visual Acuity
        ttk.Label(self.exam_tab, text="Unaided Visual Acuity:", font=('Arial', 11, 'bold')).grid(row=2, column=0, columnspan=2, pady=5, padx=5)
        ttk.Label(self.exam_tab, text="Right Eye:").grid(row=3, column=0, pady=5, padx=5)
        self.unaided_va_right = ttk.Entry(self.exam_tab, width=10)
        self.unaided_va_right.grid(row=3, column=1, pady=5, padx=5, sticky='w')
        ttk.Label(self.exam_tab, text="Left Eye:").grid(row=4, column=0, pady=5, padx=5)
        self.unaided_va_left = ttk.Entry(self.exam_tab, width=10)
        self.unaided_va_left.grid(row=4, column=1, pady=5, padx=5, sticky='w')
        
        # Old Glasses
        ttk.Label(self.exam_tab, text="Old Glasses:", font=('Arial', 11, 'bold')).grid(row=5, column=0, columnspan=2, pady=5, padx=5)
        ttk.Label(self.exam_tab, text="Right Eye (SPH/CYL/AXIS):").grid(row=6, column=0, pady=5, padx=5)
        self.old_sph_right = ttk.Entry(self.exam_tab, width=10)
        self.old_sph_right.grid(row=6, column=1, pady=5, padx=5, sticky='w')
        self.old_cyl_right = ttk.Entry(self.exam_tab, width=10)
        self.old_cyl_right.grid(row=6, column=1, pady=5, padx=(160, 5))
        self.old_axis_right = ttk.Entry(self.exam_tab, width=10)
        self.old_axis_right.grid(row=6, column=1, pady=5, padx=(320, 5))
        
        ttk.Label(self.exam_tab, text="Left Eye (SPH/CYL/AXIS):").grid(row=7, column=0, pady=5, padx=5)
        self.old_sph_left = ttk.Entry(self.exam_tab, width=10)
        self.old_sph_left.grid(row=7, column=1, pady=5, padx=5, sticky='w')
        self.old_cyl_left = ttk.Entry(self.exam_tab, width=10)
        self.old_cyl_left.grid(row=7, column=1, pady=5, padx=(160, 5))
        self.old_axis_left = ttk.Entry(self.exam_tab, width=10)
        self.old_axis_left.grid(row=7, column=1, pady=5, padx=(320, 5))
        
        # Autorefraction
        ttk.Label(self.exam_tab, text="Autorefraction:", font=('Arial', 11, 'bold')).grid(row=8, column=0, columnspan=2, pady=5, padx=5)
        
        # Add Import button for autorefractor data
        ttk.Button(self.exam_tab, text="Import from RM-800", command=self.import_autorefractor_data).grid(row=8, column=2, pady=5, padx=5)
        
        ttk.Label(self.exam_tab, text="Right Eye (SPH/CYL/AXIS):").grid(row=9, column=0, pady=5, padx=5)
        self.auto_sph_right = ttk.Entry(self.exam_tab, width=10)
        self.auto_sph_right.grid(row=9, column=1, pady=5, padx=5, sticky='w')
        self.auto_cyl_right = ttk.Entry(self.exam_tab, width=10)
        self.auto_cyl_right.grid(row=9, column=1, pady=5, padx=(160, 5))
        self.auto_axis_right = ttk.Entry(self.exam_tab, width=10)
        self.auto_axis_right.grid(row=9, column=1, pady=5, padx=(320, 5))
        ttk.Label(self.exam_tab, text="BCVA:").grid(row=9, column=2, pady=5, padx=5)
        self.auto_bcva_right = ttk.Entry(self.exam_tab, width=10)
        self.auto_bcva_right.grid(row=9, column=3, pady=5, padx=5)
        
        ttk.Label(self.exam_tab, text="Left Eye (SPH/CYL/AXIS):").grid(row=10, column=0, pady=5, padx=5)
        self.auto_sph_left = ttk.Entry(self.exam_tab, width=10)
        self.auto_sph_left.grid(row=10, column=1, pady=5, padx=5, sticky='w')
        self.auto_cyl_left = ttk.Entry(self.exam_tab, width=10)
        self.auto_cyl_left.grid(row=10, column=1, pady=5, padx=(160, 5))
        self.auto_axis_left = ttk.Entry(self.exam_tab, width=10)
        self.auto_axis_left.grid(row=10, column=1, pady=5, padx=(320, 5))
        ttk.Label(self.exam_tab, text="BCVA:").grid(row=10, column=2, pady=5, padx=5)
        self.auto_bcva_left = ttk.Entry(self.exam_tab, width=10)
        self.auto_bcva_left.grid(row=10, column=3, pady=5, padx=5)
        
        # Subjective Refraction
        ttk.Label(self.exam_tab, text="Subjective Refraction:", font=('Arial', 11, 'bold')).grid(row=11, column=0, columnspan=2, pady=5, padx=5)
        ttk.Label(self.exam_tab, text="Right Eye (SPH/CYL/AXIS):").grid(row=12, column=0, pady=5, padx=5)
        self.subj_sph_right = ttk.Entry(self.exam_tab, width=10)
        self.subj_sph_right.grid(row=12, column=1, pady=5, padx=5, sticky='w')
        self.subj_cyl_right = ttk.Entry(self.exam_tab, width=10)
        self.subj_cyl_right.grid(row=12, column=1, pady=5, padx=(160, 5))
        self.subj_axis_right = ttk.Entry(self.exam_tab, width=10)
        self.subj_axis_right.grid(row=12, column=1, pady=5, padx=(320, 5))
        ttk.Label(self.exam_tab, text="VA:").grid(row=12, column=2, pady=5, padx=5)
        self.subj_va_right = ttk.Entry(self.exam_tab, width=10)
        self.subj_va_right.grid(row=12, column=3, pady=5, padx=5)
        
        ttk.Label(self.exam_tab, text="Left Eye (SPH/CYL/AXIS):").grid(row=13, column=0, pady=5, padx=5)
        self.subj_sph_left = ttk.Entry(self.exam_tab, width=10)
        self.subj_sph_left.grid(row=13, column=1, pady=5, padx=5, sticky='w')
        self.subj_cyl_left = ttk.Entry(self.exam_tab, width=10)
        self.subj_cyl_left.grid(row=13, column=1, pady=5, padx=(160, 5))
        self.subj_axis_left = ttk.Entry(self.exam_tab, width=10)
        self.subj_axis_left.grid(row=13, column=1, pady=5, padx=(320, 5))
        ttk.Label(self.exam_tab, text="VA:").grid(row=13, column=2, pady=5, padx=5)
        self.subj_va_left = ttk.Entry(self.exam_tab, width=10)
        self.subj_va_left.grid(row=13, column=3, pady=5, padx=5)
        
        # IOP
        ttk.Label(self.exam_tab, text="IOP (Right):").grid(row=14, column=0, pady=5, padx=5)
        self.iop_right = ttk.Entry(self.exam_tab)
        self.iop_right.grid(row=14, column=1, pady=5, padx=5)
        ttk.Label(self.exam_tab, text="IOP (Left):").grid(row=15, column=0, pady=5, padx=5)
        self.iop_left = ttk.Entry(self.exam_tab)
        self.iop_left.grid(row=15, column=1, pady=5, padx=5)
        
        # Anterior and Posterior Segment
        ttk.Label(self.exam_tab, text="Anterior Segment:").grid(row=16, column=0, pady=5, padx=5)
        self.anterior_text = tk.Text(self.exam_tab, height=3, width=40)
        self.anterior_text.grid(row=16, column=1, columnspan=3, pady=5, padx=5)
        ttk.Label(self.exam_tab, text="Posterior Segment:").grid(row=17, column=0, pady=5, padx=5)
        self.posterior_text = tk.Text(self.exam_tab, height=3, width=40)
        self.posterior_text.grid(row=17, column=1, columnspan=3, pady=5, padx=5)
        
        # Diagnosis
        ttk.Label(self.exam_tab, text="Diagnosis:").grid(row=18, column=0, pady=5, padx=5)
        self.diagnosis_text = tk.Text(self.exam_tab, height=3, width=40)
        self.diagnosis_text.grid(row=18, column=1, columnspan=3, pady=5, padx=5)
        
        # Save Button
        ttk.Button(self.exam_tab, text="Save Examination", command=self.save_examination).grid(row=19, column=0, columnspan=4, pady=10)

    def save_examination(self):
            exam_data = {
                'patient_id': self.exam_patient_id.get(),
                'unaided_va': {
                    'right': self.unaided_va_right.get(),
                    'left': self.unaided_va_left.get()
                },
                'old_glasses': {
                    'right': {
                        'sph': self.old_sph_right.get(),
                        'cyl': self.old_cyl_right.get(),
                        'axis': self.old_axis_right.get()
                    },
                    'left': {
                        'sph': self.old_sph_left.get(),
                        'cyl': self.old_cyl_left.get(),
                        'axis': self.old_axis_left.get()
                    }
                },
                'autorefraction': {
                    'right': {
                        'sph': self.auto_sph_right.get(),
                        'cyl': self.auto_cyl_right.get(),
                        'axis': self.auto_axis_right.get(),
                        'bcva': self.auto_bcva_right.get()
                    },
                    'left': {
                        'sph': self.auto_sph_left.get(),
                        'cyl': self.auto_cyl_left.get(),
                        'axis': self.auto_axis_left.get(),
                        'bcva': self.auto_bcva_left.get()
                    }
                },
                'subjective_refraction': {
                    'right': {
                        'sph': self.subj_sph_right.get(),
                        'cyl': self.subj_cyl_right.get(),
                        'axis': self.subj_axis_right.get(),
                        'va': self.subj_va_right.get()
                    },
                    'left': {
                        'sph': self.subj_sph_left.get(),
                        'cyl': self.subj_cyl_left.get(),
                        'axis': self.subj_axis_left.get(),
                        'va': self.subj_va_left.get()
                    }
                },
                'iop_right': self.iop_right.get(),
                'iop_left': self.iop_left.get(),
                'anterior_segment': self.anterior_text.get("1.0", tk.END).strip(),
                'posterior_segment': self.posterior_text.get("1.0", tk.END).strip(),
                'diagnosis': self.diagnosis_text.get("1.0", tk.END).strip()
            }
            
            # Here you would add code to save the exam_data to your database
            # For example:
            # self.db.save_examination(exam_data)
            
            # Clear the form after saving
            self.clear_examination_form()
            
            messagebox.showinfo("Success", "Examination data saved successfully!")

    def clear_examination_form(self):
            # Clear all entry fields
            self.exam_patient_id.delete(0, tk.END)
            
            # Clear unaided VA fields
            self.unaided_va_right.delete(0, tk.END)
            self.unaided_va_left.delete(0, tk.END)
            
            # Clear old glasses fields
            for field in [self.old_sph_right, self.old_cyl_right, self.old_axis_right,
                         self.old_sph_left, self.old_cyl_left, self.old_axis_left]:
                field.delete(0, tk.END)
            
            # Clear autorefraction fields
            for field in [self.auto_sph_right, self.auto_cyl_right, self.auto_axis_right,
                         self.auto_sph_left, self.auto_cyl_left, self.auto_axis_left]:
                field.delete(0, tk.END)
                
            # Clear subjective refraction fields
            for field in [self.subj_sph_right, self.subj_cyl_right, self.subj_axis_right,
                         self.subj_sph_left, self.subj_cyl_left, self.subj_axis_left]:
                field.delete(0, tk.END)
                
            # Clear other fields
            self.va_right.delete(0, tk.END)
            self.va_left.delete(0, tk.END)
            self.iop_right.delete(0, tk.END)
            self.iop_left.delete(0, tk.END)
            
            # Clear text areas
            self.anterior_text.delete("1.0", tk.END)
            self.posterior_text.delete("1.0", tk.END)
            self.diagnosis_text.delete("1.0", tk.END)
                
    def setup_investigation_tab(self):
        """Setup the investigations tab interface"""
        # Create main frame
        main_frame = ttk.Frame(self.investigation_tab)
        main_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Create left and right frames inside main frame
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill='both', expand=True, padx=5, pady=5)
        
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill='both', expand=True, padx=5, pady=5)

        # Patient Selection Frame (Left Side)
        patient_frame = ttk.LabelFrame(left_frame, text="Patient Selection")
        patient_frame.pack(fill='x', padx=5, pady=5)
        
        # Search frame
        search_frame = ttk.Frame(patient_frame)
        search_frame.pack(fill='x', padx=5, pady=2)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.inv_search_entry = ttk.Entry(search_frame)
        self.inv_search_entry.pack(side=tk.LEFT, fill='x', expand=True, padx=5)
        ttk.Button(search_frame, text="Search", 
                   command=self.search_patient_for_investigation).pack(side=tk.LEFT, padx=5)
        
        # Add the search results treeview
        self.inv_search_tree = ttk.Treeview(patient_frame, 
                                           columns=('ID', 'Name', 'DOB'), 
                                           show='headings',
                                           height=3)
        self.inv_search_tree.heading('ID', text='ID')
        self.inv_search_tree.heading('Name', text='Name')
        self.inv_search_tree.heading('DOB', text='Date of Birth')
        self.inv_search_tree.column('ID', width=50)
        self.inv_search_tree.column('Name', width=150)
        self.inv_search_tree.column('DOB', width=100)
        self.inv_search_tree.pack(fill='x', padx=5, pady=2)

        # Selected patient info
        info_frame = ttk.Frame(patient_frame)
        info_frame.pack(fill='x', padx=5, pady=2)
        
        ttk.Label(info_frame, text="Patient ID:").pack(side=tk.LEFT, padx=5)
        self.inv_patient_id = tk.StringVar()
        ttk.Entry(info_frame, textvariable=self.inv_patient_id, 
                  state='readonly', width=10).pack(side=tk.LEFT, padx=5)

        # Investigation details frame
        details_frame = ttk.LabelFrame(right_frame, text="Investigation Details")
        details_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Investigation type
        ttk.Label(details_frame, text="Type:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.inv_type = ttk.Combobox(details_frame, values=[
            "OCT", "Visual Field", "Fundus Photo", "Topography", "Other"
        ])
        self.inv_type.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        
        # Details
        ttk.Label(details_frame, text="Details:").grid(row=1, column=0, padx=5, pady=5, sticky='ne')
        self.inv_details = tk.Text(details_frame, height=4, width=40)
        self.inv_details.grid(row=1, column=1, sticky='ew', padx=5, pady=5)
        
        # Results
        ttk.Label(details_frame, text="Results:").grid(row=2, column=0, padx=5, pady=5, sticky='ne')
        self.inv_results = tk.Text(details_frame, height=4, width=40)
        self.inv_results.grid(row=2, column=1, sticky='ew', padx=5, pady=5)
        
        # Recommendations
        ttk.Label(details_frame, text="Recommendations:").grid(row=3, column=0, padx=5, pady=5, sticky='ne')
        self.inv_recommendations = tk.Text(details_frame, height=4, width=40)
        self.inv_recommendations.grid(row=3, column=1, sticky='ew', padx=5, pady=5)
        
        # Configure grid weights
        details_frame.grid_columnconfigure(1, weight=1)
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=10)
        
        ttk.Button(button_frame, text="Save Investigation", 
                   command=self.save_investigation).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Print Investigation", 
                   command=self.print_investigation).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear Form", 
                   command=self.clear_investigation_form).pack(side=tk.LEFT, padx=5)
    
    def setup_treatment_tab(self):
        # Treatment Form
        ttk.Label(self.treatment_tab, text="Treatment Plan", font=('Arial', 14, 'bold')).grid(row=0, column=0, pady=10, padx=5, columnspan=2)

        # Patient Selection
        ttk.Label(self.treatment_tab, text="Patient ID:").grid(row=1, column=0, pady=5, padx=5)
        self.treatment_patient_id = ttk.Entry(self.treatment_tab)
        self.treatment_patient_id.grid(row=1, column=1, pady=5, padx=5)

        # Medical Treatment
        ttk.Label(self.treatment_tab, text="Medical Treatment:").grid(row=2, column=0, pady=5, padx=5)
        self.medical_treatment_text = tk.Text(self.treatment_tab, height=4, width=40)
        self.medical_treatment_text.grid(row=2, column=1, pady=5, padx=5)

        # Surgical Treatment
        ttk.Label(self.treatment_tab, text="Surgical Treatment:").grid(row=3, column=0, pady=5, padx=5)
        self.surgical_treatment_text = tk.Text(self.treatment_tab, height=4, width=40)
        self.surgical_treatment_text.grid(row=3, column=1, pady=5, padx=5)

        # Investigations
        ttk.Label(self.treatment_tab, text="Investigations Required:").grid(row=4, column=0, pady=5, padx=5)
        self.investigations_text = tk.Text(self.treatment_tab, height=4, width=40)
        self.investigations_text.grid(row=4, column=1, pady=5, padx=5)

        # Follow-up Date
        ttk.Label(self.treatment_tab, text="Follow-up Date:").grid(row=5, column=0, pady=5, padx=5)
        self.followup_date = ttk.Entry(self.treatment_tab)
        self.followup_date.grid(row=5, column=1, pady=5, padx=5)

        # Notes
        ttk.Label(self.treatment_tab, text="Additional Notes:").grid(row=6, column=0, pady=5, padx=5)
        self.treatment_notes = tk.Text(self.treatment_tab, height=4, width=40)
        self.treatment_notes.grid(row=6, column=1, pady=5, padx=5)

        # Button Frame
        button_frame = ttk.Frame(self.treatment_tab)
        button_frame.grid(row=7, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Save Treatment Plan", command=self.save_treatment).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Print Treatment Plan", command=self.print_treatment).pack(side=tk.LEFT, padx=5)

    def setup_medical_report_tab(self):
        """Setup the medical reports tab"""
        # Create frames for organization
        search_frame = ttk.LabelFrame(self.medical_report_frame, text="Patient Selection")
        search_frame.pack(fill='x', padx=5, pady=5)

        report_options_frame = ttk.LabelFrame(self.medical_report_frame, text="Report Options")
        report_options_frame.pack(fill='x', padx=5, pady=5)

        buttons_frame = ttk.Frame(self.medical_report_frame)
        buttons_frame.pack(fill='x', padx=5, pady=5)

        # Patient selection elements
        ttk.Label(search_frame, text="Patient ID:").grid(row=0, column=0, padx=5, pady=5)
        self.report_patient_id = ttk.Entry(search_frame, width=20)
        self.report_patient_id.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(search_frame, text="Patient Name:").grid(row=0, column=2, padx=5, pady=5)
        self.report_patient_name = ttk.Entry(search_frame, width=30)
        self.report_patient_name.grid(row=0, column=3, padx=5, pady=5)

        ttk.Button(search_frame, text="Search", command=self.search_patient_for_report).grid(row=0, column=4, padx=5, pady=5)

        # Report options
        ttk.Label(report_options_frame, text="Report Type:").grid(row=0, column=0, padx=5, pady=5)
        self.report_type = ttk.Combobox(report_options_frame, values=[
            "Complete Medical Report",
            "Examination Summary",
            "Treatment Summary",
            "Prescription History",
            "Investigation Results"
        ])
        self.report_type.grid(row=0, column=1, padx=5, pady=5)
        self.report_type.set("Complete Medical Report")

        ttk.Label(report_options_frame, text="Date Range:").grid(row=1, column=0, padx=5, pady=5)
        date_range_frame = ttk.Frame(report_options_frame)
        date_range_frame.grid(row=1, column=1, padx=5, pady=5)

        self.start_date = ttk.Entry(date_range_frame, width=12)
        self.start_date.pack(side=tk.LEFT, padx=2)
        ttk.Label(date_range_frame, text="to").pack(side=tk.LEFT, padx=2)
        self.end_date = ttk.Entry(date_range_frame, width=12)
        self.end_date.pack(side=tk.LEFT, padx=2)

        # Buttons
        ttk.Button(buttons_frame, text="Generate Report", command=self.generate_medical_report).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="View Report History", command=self.view_report_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Export Report", command=self.export_report).pack(side=tk.LEFT, padx=5)

        # Report preview area
        preview_frame = ttk.LabelFrame(self.medical_report_frame, text="Report Preview")
        preview_frame.pack(fill='both', expand=True, padx=5, pady=5)

        self.report_preview = tk.Text(preview_frame, wrap=tk.WORD, height=20)
        self.report_preview.pack(fill='both', expand=True, padx=5, pady=5)

    def add_medical_reports_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS medical_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            date DATE,
            report_type TEXT,
            report_content TEXT,
            generated_by TEXT,
            creation_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (id)
        )
        ''')
        self.conn.commit()
    
    
    def search_patient_for_report(self):
        """Search for a patient to generate report"""
        patient_id = self.report_patient_id.get()
        patient_name = self.report_patient_name.get()
        
        if not patient_id and not patient_name:
            messagebox.showerror("Error", "Please enter either Patient ID or Name")
            return
        
        try:
            cursor = self.conn.cursor()
            if patient_id:
                cursor.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
            else:
                messagebox.showwarning("Warning", "Please enter either Patient ID or Name")
                return
            
            results = cursor.fetchall()
            
            if not results:
                messagebox.showinfo("Info", "No patients found")
                return
            
            # If multiple results, show selection dialog
            if len(results) > 1:
                selection_window = tk.Toplevel(self.root)
                selection_window.title("Select Patient")
                selection_window.geometry("400x300")
                
                # Create treeview for patient selection
                tree = ttk.Treeview(selection_window, columns=('ID', 'Name', 'DOB', 'Last Visit'), show='headings')
                tree.heading('ID', text='ID')
                tree.heading('Name', text='Name')
                tree.heading('DOB', text='Date of Birth')
                tree.heading('Last Visit', text='Last Visit')
                
                for patient in results:
                    tree.insert('', 'end', values=patient)
                
                tree.pack(pady=10, padx=10, fill='both', expand=True)
                
            patient = cursor.fetchone()
            if patient:
                self.report_patient_id.delete(0, tk.END)
                self.report_patient_id.insert(0, str(patient[0]))
                self.report_patient_name.delete(0, tk.END)
                self.report_patient_name.insert(0, patient[1])
            else:
                # Single result - populate fields directly
                patient = results[0]
                self.report_patient_id.delete(0, tk.END)
                self.report_patient_id.insert(0, str(patient[0]))
                self.report_patient_name.delete(0, tk.END)
                self.report_patient_name.insert(0, patient[1])
                
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Database error: {str(e)}")

    def generate_medical_report(self):
        """Generate a medical report based on selected options"""
        try:
            patient_id = self.report_patient_id.get()
            if not patient_id:
                messagebox.showerror("Error", "Please select a patient first")
                return
            
            # Get report parameters
            report_type = self.report_type.get()
            if not report_type:
                messagebox.showerror("Error", "Please select a report type")
                return
                
            # Get date range with defaults
            start_date = self.start_date.get() or '1900-01-01'
            end_date = self.end_date.get() or datetime.now().strftime('%Y-%m-%d')
            
            # Clear preview
            self.report_preview.delete(1.0, tk.END)
            
            # Get patient info
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
            patient = cursor.fetchone()
            
            if not patient:
                messagebox.showerror("Error", "Patient not found")
                return
                
            # Generate report header
            report_text = f"Medical Report\n\nPatient Information:\n"
            report_text += f"Name: {patient[1]}\n"
            report_text += f"ID: {patient[0]}\n"
            report_text += f"Date of Birth: {patient[2]}\n"
            report_text += f"Contact: {patient[3]}\n\n"
            
            # Add content based on report type
            if report_type == "Complete Medical Report":
                # Add examination data
                cursor.execute("""
                    SELECT date, va_right, va_left, iop_right, iop_left, diagnosis 
                    FROM examinations 
                    WHERE patient_id = ? AND date BETWEEN ? AND ?
                    ORDER BY date DESC""", (patient_id, start_date, end_date))
                exams = cursor.fetchall()
                
                report_text += "\nEXAMINATION HISTORY\n"
                for exam in exams:
                    report_text += f"\nDate: {exam[0]}"
                    report_text += f"\nVisual Acuity: R {exam[1]} / L {exam[2]}"
                    report_text += f"\nIOP: R {exam[3]} / L {exam[4]}"
                    report_text += f"\nDiagnosis: {exam[5]}\n"
                
                # Add treatment data
                cursor.execute("""
                    SELECT date, medical_treatment, surgical_treatment, notes 
                    FROM treatments 
                    WHERE patient_id = ? AND date BETWEEN ? AND ?
                    ORDER BY date DESC""", (patient_id, start_date, end_date))
                treatments = cursor.fetchall()
                
                report_text += "\nTREATMENT HISTORY\n"
                for treatment in treatments:
                    report_text += f"\nDate: {treatment[0]}"
                    if treatment[1]: report_text += f"\nMedical Treatment: {treatment[1]}"
                    if treatment[2]: report_text += f"\nSurgical Treatment: {treatment[2]}"
                    if treatment[3]: report_text += f"\nNotes: {treatment[3]}\n"
                
            elif report_type == "Examination Summary":
                cursor.execute("""
                    SELECT date, va_right, va_left, iop_right, iop_left, diagnosis 
                    FROM examinations 
                    WHERE patient_id = ? AND date BETWEEN ? AND ?
                    ORDER BY date DESC LIMIT 5""", (patient_id, start_date, end_date))
                exams = cursor.fetchall()
                
                report_text += "\nRECENT EXAMINATIONS\n"
                for exam in exams:
                    report_text += f"\nDate: {exam[0]}"
                    report_text += f"\nVisual Acuity: R {exam[1]} / L {exam[2]}"
                    report_text += f"\nIOP: R {exam[3]} / L {exam[4]}"
                    report_text += f"\nDiagnosis: {exam[5]}\n"
                
            elif report_type == "Treatment Summary":
                cursor.execute("""
                    SELECT date, medical_treatment, surgical_treatment, notes 
                    FROM treatments 
                    WHERE patient_id = ? AND date BETWEEN ? AND ?
                    ORDER BY date DESC""", (patient_id, start_date, end_date))
                treatments = cursor.fetchall()
                
                report_text += "\nTREATMENT SUMMARY\n"
                for treatment in treatments:
                    report_text += f"\nDate: {treatment[0]}"
                    if treatment[1]: report_text += f"\nMedical Treatment: {treatment[1]}"
                    if treatment[2]: report_text += f"\nSurgical Treatment: {treatment[2]}"
                    if treatment[3]: report_text += f"\nNotes: {treatment[3]}\n"
                
            elif report_type == "Prescription History":
                cursor.execute("""
                    SELECT date, sph_right, cyl_right, axis_right, 
                           sph_left, cyl_left, axis_left, add_power, notes
                    FROM prescriptions 
                    WHERE patient_id = ? AND date BETWEEN ? AND ?
                    ORDER BY date DESC""", (patient_id, start_date, end_date))
                prescriptions = cursor.fetchall()
                
                report_text += "\nPRESCRIPTION HISTORY\n"
                for rx in prescriptions:
                    report_text += f"\nDate: {rx[0]}"
                    report_text += f"\nRight Eye: {rx[1]} / {rx[2]} x {rx[3]}"
                    report_text += f"\nLeft Eye: {rx[4]} / {rx[5]} x {rx[6]}"
                    if rx[7]: report_text += f"\nAdd Power: {rx[7]}"
                    if rx[8]: report_text += f"\nNotes: {rx[8]}\n"
                
            # Display in preview
            self.report_preview.insert(1.0, report_text)
            
            # Save to database
            cursor.execute("""
                INSERT INTO medical_reports (patient_id, date, report_type, report_content, generated_by)
                VALUES (?, ?, ?, ?, ?)
            """, (patient_id, datetime.now().strftime('%Y-%m-%d'), report_type, report_text, "System"))
            self.conn.commit()
            
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Database error: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def view_report_history(self):
        """View history of generated reports for the selected patient"""
        try:
            patient_id = self.report_patient_id.get().strip()
            if not patient_id:
                messagebox.showwarning("Warning", "Please select a patient first")
                return
                
            # Create history window
            history_window = tk.Toplevel(self.root)
            history_window.title("Report History")
            history_window.geometry("800x600")
            
            # Create treeview for reports
            tree = ttk.Treeview(history_window, 
                               columns=('Date', 'Type', 'Generated By'),
                               show='headings')
            tree.heading('Date', text='Date')
            tree.heading('Type', text='Report Type')
            tree.heading('Generated By', text='Generated By')
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(history_window, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            # Pack elements
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Fetch and display reports
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT date, report_type, report_content, generated_by 
                FROM medical_reports 
                WHERE patient_id = ?
                ORDER BY date DESC""", (patient_id,))
            reports = cursor.fetchall()
            
            for report in reports:
                tree.insert('', 'end', values=(report[0], report[1], report[3]))
                
            def view_report(event):
                selected = tree.selection()
                if selected:
                    item = tree.item(selected[0])
                    date = item['values'][0]
                    r_type = item['values'][1]
                    
                    cursor.execute("""
                        SELECT report_content 
                        FROM medical_reports 
                        WHERE patient_id = ? AND date = ? AND report_type = ?""",
                        (patient_id, date, r_type))
                    content = cursor.fetchone()[0]
                    
                    self.report_preview.delete(1.0, tk.END)
                    self.report_preview.insert(1.0, content)
                    
            tree.bind('<<TreeviewSelect>>', view_report)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load report history: {str(e)}")
        
    def export_report(self):
        """Export the current report to a file"""
        try:
            report_content = self.report_preview.get(1.0, tk.END).strip()
            if not report_content:
                messagebox.showwarning("Warning", "No report to export")
                return

            # Get patient info for filename
            patient_id = self.report_patient_id.get().strip()
            patient_name = self.report_patient_name.get().strip()
            date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_filename = f"medical_report_{patient_id}_{patient_name}_{date_str}"

            # Get file name for saving
            file_path = filedialog.asksaveasfilename(
                initialfile=default_filename,
                defaultextension=".pdf",
                filetypes=[
                    ("PDF files", "*.pdf"),
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ]
            )

            if not file_path:
                return

            # Show a loading cursor during export
            self.root.config(cursor="wait")
            self.root.update()

            try:
                if file_path.endswith('.pdf'):
                    # Export as PDF
                    self.export_as_pdf(file_path, report_content, patient_id, patient_name)
                else:
                    # Export as text file with proper encoding
                    self.export_as_text(file_path, report_content)

                messagebox.showinfo("Success", "Report exported successfully")
                
                # Try to open the exported file
                try:
                    if os.name == 'nt':  # Windows
                        os.startfile(file_path)
                    else:  # macOS/Linux
                        subprocess.run(['open', file_path], check=True)
                except Exception as e:
                    print(f"Could not open exported file: {e}")
            finally:
                # Restore cursor
                self.root.config(cursor="")

        except Exception as e:
            # Restore cursor in case of error
            self.root.config(cursor="")
            messagebox.showerror("Error", f"Export failed: {str(e)}")
            import traceback
            traceback.print_exc()  # Print detailed error for debugging

    def export_as_pdf(self, file_path, content, patient_id, patient_name):
        """Export report as a well-formatted PDF document with enhanced Arabic support"""
        try:
            # Setup Arabic font with fallback options (ensure we get the most suitable font)
            arabic_font = self.setup_pdf_arabic_font()
            
            # Create a PDF directly without the decorative elements
            doc = SimpleDocTemplate(
                file_path,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )

            # Create custom styles for Arabic and bilingual text
            custom_styles = self.create_arabic_styles(arabic_font)

            # Preprocess the entire content to determine overall document direction
            has_arabic = any('\u0600' <= c <= '\u06FF' for c in content)
            arabic_char_count = sum(1 for c in content if '\u0600' <= c <= '\u06FF')
            total_char_count = len([c for c in content if c.strip()])
            is_rtl_document = has_arabic and arabic_char_count > total_char_count * 0.4

            # Build document content
            story = []
            
            # Add title with Arabic support - always bilingual
            title_text = f"Medical Report - التقرير الطبي"
            # Use the fixed process_arabic_text function
            title = process_arabic_text(title_text, is_pdf=True)
            story.append(Paragraph(title, custom_styles['BilingualHeading']))
            
            # Add header information with bilingual support
            header_info = [
                f"Patient ID: {patient_id} - رقم المريض",
                f"Patient Name: {patient_name} - اسم المريض",
                f"Date Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - تاريخ التقرير",
                "\n"
            ]
            
            for info in header_info:
                # Process each header line with proper Arabic handling
                processed_info = process_arabic_text(info, is_pdf=True)
                story.append(Paragraph(processed_info, custom_styles['Bilingual']))
            
            story.append(Spacer(1, 20))

            # Process content sections with improved language detection
            sections = content.split('\n\n')
            for section in sections:
                if not section.strip():
                    story.append(Spacer(1, 12))
                    continue
                
                # Analyze section language content
                section_has_arabic = any('\u0600' <= c <= '\u06FF' for c in section)
                
                # Process section with PDF-specific Arabic handling
                processed_section = process_arabic_text(section, is_pdf=True)
                
                # Replace line breaks with HTML breaks for proper rendering
                formatted_section = processed_section.replace('\n', '<br/>')
                
                # Determine the appropriate style based on content
                if section.strip().isupper():
                    # Headers (all uppercase) - use heading style
                    style = custom_styles['BilingualHeading']
                elif section_has_arabic:
                    if is_rtl_document:
                        # For Arabic-dominant documents, use RTL paragraph alignment
                        style = custom_styles['ArabicRTL']
                    else:
                        # For mixed documents, use standard Arabic style
                        style = custom_styles['Arabic']
                else:
                    # For English/non-Arabic text
                    style = custom_styles['English']
                
                # Add the formatted section to the story
                story.append(Paragraph(formatted_section, style))
                story.append(Spacer(1, 12))

            # Add QR code to the story if needed
            if patient_id and patient_name:
                try:
                    qr_img = self.create_qr_code(patient_id, patient_name, datetime.now().strftime('%Y-%m-%d'), size=80)
                    story.append(Image(qr_img, width=80, height=80, hAlign='RIGHT'))
                except Exception as e:
                    print(f"QR code generation error: {e}")
            
            # Build the final PDF with content
            doc.build(story)
            
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export PDF: {str(e)}")
            import traceback
            traceback.print_exc()  # Print detailed error for debugging
            return False

    def setup_pdf_arabic_font(self):
        """Setup Arabic font for PDF with enhanced support for Arabic rendering"""
        try:
            # Try to find Arabic fonts in common locations
            font_options = [
                # Amiri font options (preferred)
                {'name': 'Amiri', 'paths': [
                    os.path.join(os.path.dirname(__file__), 'Amiri-Regular.ttf'),
                    '/Library/Fonts/Amiri-Regular.ttf',
                    'C:/Windows/Fonts/Amiri-Regular.ttf',
                    '/usr/share/fonts/truetype/amiri/amiri-regular.ttf',
                ]},
                # Scheherazade font options
                {'name': 'Scheherazade', 'paths': [
                    os.path.join(os.path.dirname(__file__), 'ScheherazadeNew-Regular.ttf'),
                    '/Library/Fonts/ScheherazadeNew-Regular.ttf',
                    'C:/Windows/Fonts/ScheherazadeNew-Regular.ttf',
                    '/usr/share/fonts/truetype/sil/ScheherazadeNew-Regular.ttf',
                ]},
                # Noto Naskh Arabic
                {'name': 'NotoNaskhArabic', 'paths': [
                    os.path.join(os.path.dirname(__file__), 'NotoNaskhArabic-Regular.ttf'),
                    '/Library/Fonts/NotoNaskhArabic-Regular.ttf',
                    'C:/Windows/Fonts/NotoNaskhArabic-Regular.ttf',
                    '/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf',
                ]},
                # Dubai font
                {'name': 'Dubai', 'paths': [
                    os.path.join(os.path.dirname(__file__), 'Dubai-Regular.ttf'),
                    '/Library/Fonts/Dubai-Regular.ttf',
                    'C:/Windows/Fonts/Dubai-Regular.ttf',
                    '/usr/share/fonts/truetype/dubai/Dubai-Regular.ttf',
                ]},
                # IBM Plex Sans Arabic (excellent modern Arabic font)
                {'name': 'IBMPlexSansArabic', 'paths': [
                    os.path.join(os.path.dirname(__file__), 'IBMPlexSansArabic-Regular.ttf'),
                    '/Library/Fonts/IBMPlexSansArabic-Regular.ttf',
                    'C:/Windows/Fonts/IBMPlexSansArabic-Regular.ttf',
                    '/usr/share/fonts/truetype/ibm-plex/IBMPlexSansArabic-Regular.ttf',
                ]},
                # Tahoma (widely available on Windows with good Arabic support)
                {'name': 'Tahoma', 'paths': [
                    'C:/Windows/Fonts/tahoma.ttf',
                    '/Library/Fonts/Tahoma.ttf',
                ]},
                # System Arabic fonts
                {'name': 'SystemArabic', 'paths': [
                    '/System/Library/Fonts/ArabicUIDisplay.ttc',
                    '/System/Library/Fonts/ArabicUIText.ttc',
                    '/System/Library/Fonts/GeezaPro.ttc',  # macOS Arabic font
                    '/Library/Fonts/Arial Unicode.ttf',
                ]},
            ]
            
            # Store registered fonts to avoid duplicates
            registered_fonts = []
            
            # Try each font option
            for font_option in font_options:
                font_name = font_option['name']
                if font_name in registered_fonts:
                    continue
                    
                for font_path in font_option['paths']:
                    if os.path.exists(font_path):
                        try:
                            # For TTC (TrueType Collection) files, try to extract the font
                            if font_path.lower().endswith('.ttc'):
                                # Try to register font from TTC file with index 0
                                pdfmetrics.registerFont(TTFont(font_name, font_path, subfontIndex=0))
                            else:
                                # Register standard TTF font
                                pdfmetrics.registerFont(TTFont(font_name, font_path))
                                
                            registered_fonts.append(font_name)
                            print(f"Found and registered {font_name} font: {font_path}")
                            return font_name
                        except Exception as e:
                            print(f"Error registering font {font_name} from {font_path}: {e}")
                            continue
            
            # Download Amiri if not found
            print("Downloading Amiri font...")
            import urllib.request
            import tempfile
            import zipfile
            
            # Try direct download first
            local_path = os.path.join(os.path.dirname(__file__), 'Amiri-Regular.ttf')
            try:
                direct_url = "https://github.com/alif-type/amiri/raw/master/fonts/ttf/Amiri-Regular.ttf"
                urllib.request.urlretrieve(direct_url, local_path)
            except Exception as direct_err:
                print(f"Direct download failed: {direct_err}")
                # If direct download fails, try zip download
                try:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        zip_path = os.path.join(temp_dir, "amiri.zip")
                        zip_url = "https://github.com/alif-type/amiri/releases/download/1.0.0/Amiri-1.0.0.zip"
                        
                        urllib.request.urlretrieve(zip_url, zip_path)
                        
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            for file in zip_ref.namelist():
                                if file.endswith('Amiri-Regular.ttf'):
                                    zip_ref.extract(file, temp_dir)
                                    extracted_path = os.path.join(temp_dir, file)
                                    
                                    import shutil
                                    shutil.copy2(extracted_path, local_path)
                                    break
                except Exception as zip_err:
                    print(f"Zip download failed: {zip_err}")
                    # Last resort: try the Noto Naskh Arabic font
                    try:
                        noto_url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoNaskhArabic/NotoNaskhArabic-Regular.ttf"
                        noto_path = os.path.join(os.path.dirname(__file__), 'NotoNaskhArabic-Regular.ttf')
                        urllib.request.urlretrieve(noto_url, noto_path)
                        pdfmetrics.registerFont(TTFont('NotoNaskhArabic', noto_path))
                        return 'NotoNaskhArabic'
                    except Exception as noto_err:
                        print(f"Noto download failed: {noto_err}")
            
            if os.path.exists(local_path):
                try:
                    pdfmetrics.registerFont(TTFont('Amiri', local_path))
                    return 'Amiri'
                except Exception as e:
                    print(f"Failed to register downloaded Amiri font: {e}")
                
        except Exception as e:
            print(f"Error setting up Arabic font for PDF: {e}")
        
        # Register Helvetica as fallback if available
        try:
            # Make sure Helvetica is available
            pdfmetrics.getFont('Helvetica')
            return 'Helvetica'
        except:
            # Absolute last resort - use whatever font is available
            print("Warning: No suitable Arabic font found. Text rendering may be poor.")
            return None

    def export_as_text(self, file_path, content):
        """Export report as a text file with proper encoding for Arabic"""
        try:
            # Ensure content has proper line endings
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            # Enhanced Arabic character detection with wider Unicode range
            def is_arabic_text(text):
                # Check for Arabic character ranges
                for c in text:
                    if (('\u0600' <= c <= '\u06FF') or  # Basic Arabic
                        ('\u0750' <= c <= '\u077F') or  # Arabic Supplement
                        ('\u0780' <= c <= '\u07BF') or  # Thaana (sometimes used with Arabic)
                        ('\u08A0' <= c <= '\u08FF') or  # Arabic Extended-A
                        ('\uFB50' <= c <= '\uFDFF') or  # Arabic Presentation Forms-A
                        ('\uFE70' <= c <= '\uFEFF')):   # Arabic Presentation Forms-B
                        return True
                return False
            
            # Process content line by line for better RTL handling
            processed_lines = []
            rtl_mark = '\u200F'  # Right-to-Left Mark (RLM)
            ltr_mark = '\u200E'  # Left-to-Right Mark (LRM)
            
            # Process each line with proper RTL/LTR marks
            for line in content.split('\n'):
                if not line.strip():
                    processed_lines.append(line)
                    continue
                
                # Analyze line to determine if it contains Arabic
                has_arabic = is_arabic_text(line)
                
                # Count Arabic characters for determining dominant direction
                arabic_count = sum(1 for c in line if '\u0600' <= c <= '\u06FF' or 
                                              '\uFB50' <= c <= '\uFDFF' or
                                              '\uFE70' <= c <= '\uFEFF')
                total_chars = len([c for c in line if c.strip()])
                
                # Determine if line is primarily Arabic (>30% Arabic characters)
                is_primarily_arabic = total_chars > 0 and arabic_count / total_chars > 0.3
                
                if has_arabic:
                    if is_primarily_arabic:
                        # For primarily Arabic lines, add RTL mark at beginning
                        processed_lines.append(rtl_mark + line)
                    else:
                        # For mixed content with some Arabic, use both marks
                        # Add RTL mark at start and LTR mark at end for better bidirectional handling
                        processed_lines.append(rtl_mark + line + ltr_mark)
                else:
                    # For non-Arabic lines, ensure LTR direction
                    processed_lines.append(ltr_mark + line)
            
            # Join processed lines and add BOM for better UTF-8 compatibility in various text editors
            final_content = '\n'.join(processed_lines)
            
            # Write with UTF-8-BOM encoding for better compatibility with all text editors
            with open(file_path, 'wb') as file:
                file.write('\ufeff'.encode('utf-8'))  # UTF-8 BOM
                file.write(final_content.encode('utf-8'))
                
            return True
        except Exception as e:
            print(f"Error exporting text file: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to write text file: {str(e)}")
            return False

    
    def save_investigation(self):
        """Save investigation details to database"""
        patient_id = self.inv_patient_id.get()
        if not patient_id:
            messagebox.showerror("Error", "Patient ID is required")
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO investigations (
                    patient_id, date, type, details,
                    results, recommendations
                )
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                patient_id,
                datetime.now().date().isoformat(),
                self.inv_type.get(),
                self.inv_details.get("1.0", tk.END).strip(),
                self.inv_results.get("1.0", tk.END).strip(),
                self.inv_recommendations.get("1.0", tk.END).strip()
            ))
            self.conn.commit()
            messagebox.showinfo("Success", "Investigation data saved successfully")
            self.clear_investigation_form()
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Database error: {str(e)}")

    def save_treatment(self):
        patient_id = self.treatment_patient_id.get()
        if not patient_id:
            messagebox.showerror("Error", "Patient ID is required")
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO treatments (
                    patient_id, date, medical_treatment, surgical_treatment,
                    investigations, followup_date, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                patient_id,
                datetime.now().date(),
                self.medical_treatment_text.get("1.0", tk.END).strip(),
                self.surgical_treatment_text.get("1.0", tk.END).strip(),
                self.investigations_text.get("1.0", tk.END).strip(),
                self.followup_date.get(),
                self.treatment_notes.get("1.0", tk.END).strip()
            ))
            self.conn.commit()
            messagebox.showinfo("Success", "Treatment plan saved successfully")
            self.clear_treatment_form()
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Database error: {str(e)}")

    def clear_treatment_form(self):
        self.treatment_patient_id.delete(0, tk.END)
        self.medical_treatment_text.delete("1.0", tk.END)
        self.surgical_treatment_text.delete("1.0", tk.END)
        self.investigations_text.delete("1.0", tk.END)
        self.followup_date.delete(0, tk.END)
        self.treatment_notes.delete("1.0", tk.END)

    def print_treatment(self):
        patient_id = self.treatment_patient_id.get()
        if not patient_id:
            messagebox.showerror("Error", "Patient ID is required")
            return

        # Get patient information
        cursor = self.conn.cursor()
        cursor.execute('SELECT name, dob FROM patients WHERE id = ?', (patient_id,))
        patient_data = cursor.fetchone()
        
        if not patient_data:
            messagebox.showerror("Error", "Patient not found")
            return

        # Create PDF
        filename = f"treatment_plan_{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        c = canvas.Canvas(filename, pagesize=letter)
        
        # Add QR code with consistent positioning
        # Removed duplicate QR code call
        
        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(1*inch, 10*inch, "Treatment Plan")
        
        # Patient Information
        c.setFont("Helvetica", 12)
        c.drawString(1*inch, 9.5*inch, f"Patient Name: {patient_data[0]}")
        c.drawString(1*inch, 9*inch, f"Patient ID: {patient_id}")
        c.drawString(1*inch, 8.5*inch, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
        
        # Treatment Details
        def draw_section(title, content, y_position):
            c.setFont("Helvetica-Bold", 12)
            c.drawString(1*inch, y_position, title)
            c.setFont("Helvetica", 12)
            
            # Split content into lines that fit within the page width
            words = content.split()
            lines = []
            current_line = []
            
            for word in words:
                current_line.append(word)
                if len(' '.join(current_line)) > 60:  # Adjust based on page width
                    lines.append(' '.join(current_line[:-1]))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))
            
            # Draw lines with proper spacing
            for i, line in enumerate(lines):
                c.drawString(1*inch, y_position - 0.25*inch - (i * 0.25*inch), line)
            
            return y_position - (len(lines) + 2) * 0.25*inch

        y_pos = 8*inch
        y_pos = draw_section("Medical Treatment:", 
                            self.medical_treatment_text.get("1.0", tk.END).strip(), y_pos)
        y_pos = draw_section("Surgical Treatment:", 
                            self.surgical_treatment_text.get("1.0", tk.END).strip(), y_pos)
        y_pos = draw_section("Investigations Required:", 
                            self.investigations_text.get("1.0", tk.END).strip(), y_pos)
        
        # Follow-up Date
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1*inch, y_pos, "Follow-up Date:")
        c.setFont("Helvetica", 12)
        c.drawString(2.5*inch, y_pos, self.followup_date.get())
        
        # Notes
        y_pos -= 0.5*inch
        draw_section("Additional Notes:", 
                    self.treatment_notes.get("1.0", tk.END).strip(), y_pos)
        
        # Footer
        c.setFont("Helvetica", 10)
        c.drawString(1*inch, 1*inch, "Please follow the treatment plan as prescribed and return for follow-up as scheduled.")
        
        c.save()
        
        # Open the PDF
        try:
            if os.name == 'nt':  # Windows
                os.startfile(filename)
            else:  # macOS and Linux
                os.system(f'open {filename}')
        except:
            messagebox.showinfo("Success", f"Treatment plan saved as {filename}")

    def setup_prescription_tab(self):
        """Setup the prescription tab with proper entry widgets"""
        # Patient selection frame
        patient_frame = ttk.LabelFrame(self.prescription_tab, text="Patient Selection")
        patient_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(patient_frame, text="Patient ID:").grid(row=0, column=0, padx=5, pady=5)
        self.rx_patient_id = ttk.Entry(patient_frame)
        self.rx_patient_id.grid(row=0, column=1, padx=5, pady=5)

        # Prescription details frame
        rx_frame = ttk.LabelFrame(self.prescription_tab, text="Prescription Details")
        rx_frame.pack(fill='x', padx=5, pady=5)

        # Right eye
        ttk.Label(rx_frame, text="Right Eye (OD)").grid(row=0, column=0, columnspan=3, pady=5)
        
        # Initialize StringVar for each entry to better track changes
        self.sph_right_var = tk.StringVar()
        self.cyl_right_var = tk.StringVar()
        self.axis_right_var = tk.StringVar()
        self.sph_left_var = tk.StringVar()
        self.cyl_left_var = tk.StringVar()
        self.axis_left_var = tk.StringVar()
        
        ttk.Label(rx_frame, text="Sphere:").grid(row=1, column=0, padx=5)
        self.sph_right = ttk.Entry(rx_frame, width=10, textvariable=self.sph_right_var)
        self.sph_right.grid(row=1, column=1, padx=5)
        
        ttk.Label(rx_frame, text="Cylinder:").grid(row=1, column=2, padx=5)
        self.cyl_right = ttk.Entry(rx_frame, width=10, textvariable=self.cyl_right_var)
        self.cyl_right.grid(row=1, column=3, padx=5)
        
        ttk.Label(rx_frame, text="Axis:").grid(row=1, column=4, padx=5)
        self.axis_right = ttk.Entry(rx_frame, width=10, textvariable=self.axis_right_var)
        self.axis_right.grid(row=1, column=5, padx=5)

        # Left eye
        ttk.Label(rx_frame, text="Left Eye (OS)").grid(row=2, column=0, columnspan=3, pady=5)
        
        ttk.Label(rx_frame, text="Sphere:").grid(row=3, column=0, padx=5)
        self.sph_left = ttk.Entry(rx_frame, width=10, textvariable=self.sph_left_var)
        self.sph_left.grid(row=3, column=1, padx=5)
        
        ttk.Label(rx_frame, text="Cylinder:").grid(row=3, column=2, padx=5)
        self.cyl_left = ttk.Entry(rx_frame, width=10, textvariable=self.cyl_left_var)
        self.cyl_left.grid(row=3, column=3, padx=5)
        
        ttk.Label(rx_frame, text="Axis:").grid(row=3, column=4, padx=5)
        self.axis_left = ttk.Entry(rx_frame, width=10, textvariable=self.axis_left_var)
        self.axis_left.grid(row=3, column=5, padx=5)

        # Add power
        ttk.Label(rx_frame, text="Add Power:").grid(row=4, column=0, padx=5, pady=10)
        self.add_power = ttk.Entry(rx_frame, width=10)
        self.add_power.grid(row=4, column=1, padx=5, pady=10)

        # Notes
        ttk.Label(rx_frame, text="Notes:").grid(row=5, column=0, padx=5)
        self.rx_notes = tk.Text(rx_frame, height=4, width=50)
        self.rx_notes.grid(row=5, column=1, columnspan=5, padx=5, pady=5)

        # Buttons
        button_frame = ttk.Frame(self.prescription_tab)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Save Prescription", 
                   command=self.save_prescription).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Print Prescription", 
                   command=self.print_prescription).pack(side=tk.LEFT, padx=5)

    def add_patient(self):
        """Add a new patient to the database."""
        try:
            name = self.name_entry.get().strip()
            dob = self.dob_entry.get().strip()
            contact = self.contact_entry.get().strip()
            history = self.history_text.get("1.0", tk.END).strip()

            if not name:
                messagebox.showerror("Error", "Name is required")
                return

            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute('''
                    INSERT INTO patients (name, dob, contact, medical_history)
                    VALUES (?, ?, ?, ?)
                ''', (name, dob, contact, history))
                
                messagebox.showinfo("Success", "Patient added successfully")
                self.clear_patient_form()
                self.refresh_patient_list()
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Database error: {str(e)}")
            logging.error(f"Error adding patient: {str(e)}")

    def edit_patient(self):
        """Edit selected patient's information in a new window."""
        try:
            selected_items = self.patient_tree.selection()
            if not selected_items:
                messagebox.showwarning("Warning", "Please select a patient to edit")
                return
                
            item = selected_items[0]
            patient_values = self.patient_tree.item(item)['values']
            if not patient_values:
                return
                
            # Create edit window
            edit_window = tk.Toplevel(self.root)
            edit_window.title("Edit Patient")
            edit_window.geometry("400x500")
            
            # Add padding around the window
            main_frame = ttk.Frame(edit_window, padding="10")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Create form fields
            ttk.Label(main_frame, text="Name:").pack(anchor=tk.W, pady=(0, 5))
            name_entry = ttk.Entry(main_frame, width=40)
            name_entry.pack(fill=tk.X, pady=(0, 10))
            name_entry.insert(0, patient_values[1] if patient_values[1] else '')
            
            ttk.Label(main_frame, text="Date of Birth:").pack(anchor=tk.W, pady=(0, 5))
            dob_entry = ttk.Entry(main_frame, width=40)
            dob_entry.pack(fill=tk.X, pady=(0, 10))
            dob_entry.insert(0, patient_values[2] if patient_values[2] else '')
            
            ttk.Label(main_frame, text="Contact:").pack(anchor=tk.W, pady=(0, 5))
            contact_entry = ttk.Entry(main_frame, width=40)
            contact_entry.pack(fill=tk.X, pady=(0, 10))
            contact_entry.insert(0, patient_values[3] if patient_values[3] else '')
            
            ttk.Label(main_frame, text="Medical History:").pack(anchor=tk.W, pady=(0, 5))
            history_text = tk.Text(main_frame, height=10, width=40)
            history_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            # Get medical history from database
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute('SELECT medical_history FROM patients WHERE id = ?', (patient_values[0],))
                result = cursor.fetchone()
                if result and result[0]:
                    history_text.insert("1.0", result[0])
            
            def save_changes():
                try:
                    name = name_entry.get().strip()
                    if not name:
                        messagebox.showerror("Error", "Name is required")
                        return
                        
                    with self.conn:
                        cursor = self.conn.cursor()
                        
                        # First, ensure the updated_at column exists
                        cursor.execute("PRAGMA table_info(patients)")
                        columns = [col[1] for col in cursor.fetchall()]
                        
                        if 'updated_at' not in columns:
                            cursor.execute('ALTER TABLE patients ADD COLUMN updated_at TIMESTAMP')
                        
                        # Now perform the update with the correct columns
                        cursor.execute('''
                            UPDATE patients 
                            SET name=?, 
                                date_of_birth=?, 
                                contact_info=?, 
                                medical_history=?,
                                updated_at=CURRENT_TIMESTAMP
                            WHERE id=?
                        ''', (
                            name,
                            dob_entry.get().strip(),
                            contact_entry.get().strip(),
                            history_text.get("1.0", tk.END).strip(),
                            patient_values[0]
                        ))
                        
                    messagebox.showinfo("Success", "Patient information updated")
                    edit_window.destroy()
                    self.refresh_patient_list()
                    
                except sqlite3.Error as e:
                    messagebox.showerror("Error", f"Database error: {str(e)}")
                    logging.error(f"Error updating patient: {str(e)}")
            
            # Button frame
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(10, 0))
            
            ttk.Button(button_frame, text="Save Changes", command=save_changes).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Cancel", command=edit_window.destroy).pack(side=tk.LEFT)
            
            # Make the window modal
            edit_window.transient(self.root)
            edit_window.grab_set()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open edit window: {str(e)}")
            logging.error(f"Error in edit_patient: {str(e)}")
            
    def search_patient(self):
        """Search for patients by ID or name."""
        try:
            search_id = self.search_id_entry.get().strip()
            search_name = self.search_name_entry.get().strip()
            
            if not search_id and not search_name:
                messagebox.showerror("Error", "Please enter an ID or name to search")
                return

            with self.conn:
                cursor = self.conn.cursor()
                if search_id:
                    cursor.execute('SELECT * FROM patients WHERE id = ?', (search_id,))
                else:
                    cursor.execute('SELECT * FROM patients WHERE name LIKE ?', (f'%{search_name}%',))
                
                results = cursor.fetchall()
                if not results:
                    messagebox.showinfo("Search Results", "No matching patients found")
                self.update_patient_tree(results)
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Database error: {str(e)}")
            logging.error(f"Error searching patient: {str(e)}")

    def save_examination(self):
        patient_id = self.exam_patient_id.get()
        if not patient_id:
            messagebox.showerror("Error", "Patient ID is required")
            return

        
        cursor = self.conn.cursor()
        cursor.execute('SELECT id FROM patients WHERE id = ?', (patient_id,))
        if not cursor.fetchone():
            messagebox.showerror("Error", "Patient not found")
            return

        try:
            # Validate IOP values
            iop_right = self.iop_right.get().strip()
            iop_left = self.iop_left.get().strip()
            
            if iop_right and not re.match(r'^\d*\.?\d*$', iop_right):
                raise ValueError("Invalid right IOP value")
            if iop_left and not re.match(r'^\d*\.?\d*$', iop_left):
                raise ValueError("Invalid left IOP value")

            cursor.execute('''
                INSERT INTO examinations (
                    patient_id, date, va_right, va_left, 
                    iop_right, iop_left, anterior_segment, 
                    posterior_segment, diagnosis
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                patient_id,
                datetime.now().date(),
                self.unaided_va_right.get().strip(),
                self.unaided_va_left.get().strip(),
                float(iop_right) if iop_right else 0,
                float(iop_left) if iop_left else 0,
                self.anterior_text.get("1.0", tk.END).strip(),
                self.posterior_text.get("1.0", tk.END).strip(),
                self.diagnosis_text.get("1.0", tk.END).strip()
            ))
            self.conn.commit()
            
            if messagebox.askyesno("Success", "Examination saved successfully. Would you like to print the examination report?"):
                self.print_examination(patient_id)
                
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Database error: {str(e)}")
        except ValueError as e:
            messagebox.showerror("Error", "Please enter valid numbers for IOP values")


    def save_prescription(self):
        patient_id = self.rx_patient_id.get()
        if not patient_id:
            messagebox.showerror("Error", "Patient ID is required")
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO prescriptions (
                    patient_id, date, sph_right, cyl_right, axis_right,
                    sph_left, cyl_left, axis_left, add_power, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                patient_id,
                datetime.now().date(),
                float(self.sph_right.get() or 0),
                float(self.cyl_right.get() or 0),
                int(self.axis_right.get() or 0),
                float(self.sph_left.get() or 0),
                float(self.cyl_left.get() or 0),
                int(self.axis_left.get() or 0),
                float(self.add_power.get() or 0),
                self.rx_notes.get("1.0", tk.END).strip()
            ))
            self.conn.commit()
            messagebox.showinfo("Success", "Prescription saved successfully")
            
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Database error: {str(e)}")
        except ValueError as e:
            messagebox.showerror("Error", "Please enter valid numbers for prescription values")

    def refresh_patient_list(self):
        """Refresh the patient list with alternating row colors"""
        try:
            # Clear existing items
            for item in self.patient_tree.get_children():
                self.patient_tree.delete(item)
            
            cursor = self.conn.cursor()
            cursor.execute('SELECT id, name, dob, contact, last_visit FROM patients ORDER BY name')
            
            for i, row in enumerate(cursor.fetchall()):
                # Handle potential None values and date formatting
                patient_id = row[0] or ''
                name = row[1] or ''
                dob = row[2].strftime('%d %B %Y') if row[2] else ''
                contact = row[3] or ''
                last_visit = row[4].strftime('%d %B %Y') if row[4] else ''
                
                # Add row with alternating color
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                self.patient_tree.insert('', 'end', 
                                       values=(patient_id, name, dob, contact, last_visit),
                                       tags=(tag,))
                
        except Exception as e:
            print(f"Error refreshing patient list: {e}")
            messagebox.showerror("Error", "Failed to refresh patient list")

    def update_patient_tree(self, results):
        """Update the patient treeview with the given results."""
        try:
            # Clear existing items
            for item in self.patient_tree.get_children():
                self.patient_tree.delete(item)
            
            # Use a single cursor for all operations
            with self.conn:
                cursor = self.conn.cursor()
                for row in results:
                    # More efficient query using COALESCE and single query
                    cursor.execute('''
                        SELECT COALESCE(
                            (SELECT MAX(date) FROM (
                                SELECT date FROM examinations WHERE patient_id = ?
                                UNION ALL
                                SELECT date FROM prescriptions WHERE patient_id = ?
                            )), 'No visits'
                        ) as last_visit
                    ''', (row[0], row[0]))
                    
                    last_visit = cursor.fetchone()[0]
                    
                    # Convert row to list if it's a tuple
                    values = list(row) + [last_visit]
                    self.patient_tree.insert('', 'end', values=values)
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update patient list: {str(e)}")
            logging.error(f"Error updating patient tree: {str(e)}")

    def on_patient_select(self, event):
        """Handle patient selection in the treeview."""
        try:
            selected_items = self.patient_tree.selection()
            if not selected_items:
                return
                
            item = selected_items[0]
            values = self.patient_tree.item(item)['values']
            if not values:
                return
                
            patient_id = values[0]
            self.load_patient_data(patient_id)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to select patient: {str(e)}")
            logging.error(f"Error in patient selection: {str(e)}")

    def load_patient_data(self, patient_id):
        """Load patient data into the form fields."""
        try:
            self.clear_patient_form()  # Clear form before loading new data
            
            with self.conn:
                cursor = self.conn.cursor()
                
                # First, verify the table structure
                cursor.execute("PRAGMA table_info(patients)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Check if required columns exist
                required_columns = {'id', 'name', 'date_of_birth', 'contact_info', 'medical_history'}
                missing_columns = required_columns - set(columns)
                
                if missing_columns:
                    # Add missing columns if necessary
                    for column in missing_columns:
                        if column == 'date_of_birth':
                            cursor.execute('ALTER TABLE patients ADD COLUMN date_of_birth DATE')
                        elif column == 'medical_history':
                            cursor.execute('ALTER TABLE patients ADD COLUMN medical_history TEXT')
                        elif column == 'contact_info':
                            cursor.execute('ALTER TABLE patients ADD COLUMN contact_info TEXT')
                
                # Now proceed with the select query
                cursor.execute('''
                    SELECT id, name, date_of_birth, contact_info, medical_history 
                    FROM patients 
                    WHERE id = ?
                ''', (patient_id,))
                
                patient = cursor.fetchone()
                if not patient:
                    messagebox.showwarning("Warning", "Patient not found")
                    return
                
                # Safely insert values with proper null handling
                self.name_entry.insert(0, patient[1] if patient[1] else '')
                self.dob_entry.insert(0, patient[2] if patient[2] else '')
                self.contact_entry.insert(0, patient[3] if patient[3] else '')
                self.history_text.insert("1.0", patient[4] if patient[4] else '')
                
                # Store current patient ID for later use
                self.current_patient_id = patient_id
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load patient data: {str(e)}")
            logging.error(f"Error loading patient data: {str(e)}")

    def clear_patient_form(self):
        """Clear all form fields."""
        self.name_entry.delete(0, tk.END)
        self.dob_entry.delete(0, tk.END)
        self.contact_entry.delete(0, tk.END)
        self.history_text.delete("1.0", tk.END)
        self.current_patient_id = None
            
    def save_changes(self):
        """Save changes to patient information."""
        try:
            if not hasattr(self, 'current_patient_id') or not self.current_patient_id:
                messagebox.showerror("Error", "No patient selected")
                return
                
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute('''
                    UPDATE patients 
                    SET name=?, dob=?, contact=?, medical_history=?
                    WHERE id=?
                ''', (
                    self.name_entry.get().strip(),
                    self.dob_entry.get().strip(),
                    self.contact_entry.get().strip(),
                    self.history_text.get("1.0", tk.END).strip(),
                    self.current_patient_id
                ))
                
                messagebox.showinfo("Success", "Patient information updated")
                self.refresh_patient_list()
                
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Database error: {str(e)}")
            logging.error(f"Error updating patient: {str(e)}")

    def delete_patient(self):
        """Delete a patient and all associated records."""
        try:
            selected_items = self.patient_tree.selection()
            if not selected_items:
                messagebox.showwarning("Warning", "Please select a patient to delete")
                return
                
            item = selected_items[0]
            patient_id = self.patient_tree.item(item)['values'][0]
            patient_name = self.patient_tree.item(item)['values'][1]
            
            if not messagebox.askyesno("Confirm Delete", 
                f"Are you sure you want to delete patient {patient_name}?\n"
                "This will also delete all associated records."):
                return
                
            with self.conn:
                cursor = self.conn.cursor()
                # Delete related records first
                cursor.execute('DELETE FROM examinations WHERE patient_id = ?', (patient_id,))
                cursor.execute('DELETE FROM prescriptions WHERE patient_id = ?', (patient_id,))
                # Delete patient record
                cursor.execute('DELETE FROM patients WHERE id = ?', (patient_id,))
                
                messagebox.showinfo("Success", "Patient and associated records deleted")
                self.refresh_patient_list()
                
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Database error: {str(e)}")
            logging.error(f"Error deleting patient: {str(e)}")
    
    def show_visit_history(self):
        selected_items = self.patient_tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select a patient to view history")
            return
            
        item = selected_items[0]
        patient_id = self.patient_tree.item(item)['values'][0]
        patient_name = self.patient_tree.item(item)['values'][1]
        
        # Create history window
        history_window = tk.Toplevel(self.root)
        history_window.title(f"Visit History - {patient_name}")
        history_window.geometry("800x600")
        
        # Create notebook for different types of visits
        notebook = ttk.Notebook(history_window)
        notebook.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Examinations tab
        exam_frame = ttk.Frame(notebook)
        notebook.add(exam_frame, text='Examinations')
        
        exam_tree = ttk.Treeview(exam_frame, columns=('Date', 'VA_R', 'VA_L', 'IOP_R', 'IOP_L', 'Diagnosis'), show='headings')
        exam_tree.pack(expand=True, fill='both')
        
        exam_tree.heading('Date', text='Date')
        exam_tree.heading('VA_R', text='VA Right')
        exam_tree.heading('VA_L', text='VA Left')
        exam_tree.heading('IOP_R', text='IOP Right')
        exam_tree.heading('IOP_L', text='IOP Left')
        exam_tree.heading('Diagnosis', text='Diagnosis')
        
        # Prescriptions tab
        rx_frame = ttk.Frame(notebook)
        notebook.add(rx_frame, text='Prescriptions')
        
        rx_tree = ttk.Treeview(rx_frame, columns=('Date', 'SPH_R', 'CYL_R', 'AXIS_R', 'SPH_L', 'CYL_L', 'AXIS_L', 'ADD'), show='headings')
        rx_tree.pack(expand=True, fill='both')
        
        rx_tree.heading('Date', text='Date')
        rx_tree.heading('SPH_R', text='SPH Right')
        rx_tree.heading('CYL_R', text='CYL Right')
        rx_tree.heading('AXIS_R', text='AXIS Right')
        rx_tree.heading('SPH_L', text='SPH Left')
        rx_tree.heading('CYL_L', text='CYL Left')
        rx_tree.heading('AXIS_L', text='AXIS Left')
        rx_tree.heading('ADD', text='ADD')
        
        # Load examination history
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT date, va_right, va_left, iop_right, iop_left, diagnosis 
            FROM examinations 
            WHERE patient_id = ? 
            ORDER BY date DESC
        ''', (patient_id,))
        
        for row in cursor.fetchall():
            exam_tree.insert('', 'end', values=row)
        
        # Load prescription history
        cursor.execute('''
            SELECT date, sph_right, cyl_right, axis_right, sph_left, cyl_left, axis_left, add_power 
            FROM prescriptions 
            WHERE patient_id = ? 
            ORDER BY date DESC
        ''', (patient_id,))
        
        for row in cursor.fetchall():
            rx_tree.insert('', 'end', values=row)

    def create_prescription_table(self, c, y_position):
        """Creates a bilingual prescription table"""
        table_width = 7 * inch
        col_widths = [1.5*inch, 1.8*inch, 1.8*inch, 1.9*inch]
        row_height = 0.6 * inch
        x_start = (letter[0] - table_width) / 2
        
        def draw_cell(x, y, width, height, text, ar_text=None, is_header=False, is_title=False):
            # Cell background (white for all cells)
            c.setFillColorRGB(1, 1, 1)
            c.rect(x, y - height, width, height, fill=1, stroke=0)
            
            # Cell border
            c.setLineWidth(0.5)
            c.setStrokeColorRGB(0.7, 0.7, 0.7)  # Light gray borders
            c.rect(x, y - height, width, height, fill=0, stroke=1)
            
            # Text color
            if is_header:
                c.setFillColorRGB(0.2, 0.2, 0.2)  # Dark gray for headers
            elif is_title:
                c.setFillColorRGB(0.3, 0.3, 0.3)  # Medium gray for titles
            else:
                c.setFillColorRGB(0, 0, 0)  # Black for values
            
            # Draw text
            text = str(text).strip()
            if is_header or is_title:
                c.setFont("Helvetica-Bold", 11)
            else:
                c.setFont("Helvetica", 11)
                
            text_width = c.stringWidth(text, c._fontname, c._fontsize)
            text_x = x + (width - text_width) / 2
            text_y = y - height/2 + c._fontsize/2
            c.drawString(text_x, text_y, text)
            
            # Draw Arabic text
            if ar_text and ARABIC_SUPPORT:
                try:
                    c.setFont("Arabic", 11)
                    # Process Arabic text with proper configuration
                    processed_text = process_arabic_text(ar_text, is_pdf=True)
                    if processed_text:
                        # Calculate width and position
                        arabic_width = c.stringWidth(processed_text, "Arabic", 11)
                        arabic_x = x + (width - arabic_width) / 2
                        # Draw with adjusted baseline
                        c.drawString(arabic_x, text_y - 13, processed_text)
                except Exception as e:
                    print(f"Error drawing Arabic text '{ar_text}': {e}")

        # Draw headers - removing Arabic keywords as requested
        headers = [
            ("Eye", ""),
            ("Sphere (SPH)", ""),
            ("Cylinder (CYL)", ""),
            ("Axis", "")
        ]
        
        y = y_position
        x = x_start
        for i, (eng, ar) in enumerate(headers):
            draw_cell(x, y, col_widths[i], row_height, eng, ar_text=ar, is_header=True)
            x += col_widths[i]

        # Add debug prints to check values
        print("\nDebug: Prescription Values")
        print(f"Right Eye - Sphere: {self.sph_right.get()}")
        print(f"Right Eye - Cylinder: {self.cyl_right.get()}")
        print(f"Right Eye - Axis: {self.axis_right.get()}")
        print(f"Left Eye - Sphere: {self.sph_left.get()}")
        print(f"Left Eye - Cylinder: {self.cyl_left.get()}")
        print(f"Left Eye - Axis: {self.axis_left.get()}")

        # Get prescription values with better error handling
        def get_value(entry, default="0.00"):
            """Safely get value from entry widget"""
            try:
                value = entry.get().strip()
                if not value:
                    print(f"Debug: Empty value for {entry}, using default: {default}")
                    return default
                print(f"Debug: Got value: {value}")
                return value
            except Exception as e:
                print(f"Debug: Error getting value: {e}")
                return default

        # Format values with proper signs and units
        def format_power(value):
            """Format power values with sign and unit"""
            try:
                num = float(value)
                result = f"{num:+.2f} D" if num != 0 else "0.00 D"
                print(f"Debug: Formatted power {value} to {result}")
                return result
            except ValueError as e:
                print(f"Debug: Error formatting power {value}: {e}")
                return "0.00 D"

        def format_axis(value):
            """Format axis values with degree symbol"""
            try:
                num = int(float(value))
                result = f"{num}°"
                print(f"Debug: Formatted axis {value} to {result}")
                return result
            except ValueError as e:
                print(f"Debug: Error formatting axis {value}: {e}")
                return "0°"

        # Get and format values
        sph_right = format_power(get_value(self.sph_right))
        cyl_right = format_power(get_value(self.cyl_right))
        axis_right = format_axis(get_value(self.axis_right, "0"))
        
        sph_left = format_power(get_value(self.sph_left))
        cyl_left = format_power(get_value(self.cyl_left))
        axis_left = format_axis(get_value(self.axis_left, "0"))

        # Data rows with formatted values
        data = [
            [("OD (Right Eye)", ""), sph_right, cyl_right, axis_right],
            [("OS (Left Eye)", ""), sph_left, cyl_left, axis_left]
        ]

        print("\nDebug: Formatted Data")
        print(f"Right Eye: {sph_right}, {cyl_right}, {axis_right}")
        print(f"Left Eye: {sph_left}, {cyl_left}, {axis_left}")

        # Draw data rows
        y -= row_height
        for row in data:
            x = x_start
            for col_idx, value in enumerate(row):
                if col_idx == 0:  # Eye label
                    draw_cell(x, y, col_widths[col_idx], row_height, value[0], 
                             ar_text=value[1], is_title=True)
                else:  # Values
                    draw_cell(x, y, col_widths[col_idx], row_height, value)
                x += col_widths[col_idx]
            y -= row_height

        return y

    def run(self):
        self.refresh_patient_list()
        self.root.mainloop()

    # Add this method to the OphthalmologyEMR class
    def create_bilingual_text_widget(self, parent, height=4, width=40):
        """Create a text widget with enhanced Arabic input support"""
        # Create a frame to hold the text widget and toolbar
        frame = ttk.Frame(parent)
        
        # Create toolbar with language toggle and formatting buttons
        toolbar = ttk.Frame(frame)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        # Language indicator and toggle
        self.text_direction = tk.StringVar(value="LTR")
        direction_label = ttk.Label(toolbar, text="Direction:")
        direction_label.pack(side=tk.LEFT, padx=2)
        
        # Radio buttons for text direction
        ttk.Radiobutton(toolbar, text="LTR", variable=self.text_direction, value="LTR").pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(toolbar, text="RTL", variable=self.text_direction, value="RTL").pack(side=tk.LEFT, padx=2)
        
        # Create the text widget with enhanced features
        text_widget = tk.Text(frame, height=height, width=width, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(frame, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)
        
        # Configure tags for different text directions
        text_widget.tag_configure("RTL", justify=tk.RIGHT)
        text_widget.tag_configure("LTR", justify=tk.LEFT)
        
        # Bind events for automatic language detection and formatting
        def process_input(event):
            # Get current line
            current_line = text_widget.get("insert linestart", "insert lineend")
            
            # Check if line contains Arabic text
            has_arabic = any('\u0600' <= c <= '\u06FF' for c in current_line)
            
            # Apply appropriate tag based on content or user selection
            if has_arabic or self.text_direction.get() == "RTL":
                text_widget.tag_add("RTL", "insert linestart", "insert lineend")
                text_widget.tag_remove("LTR", "insert linestart", "insert lineend")
            else:
                text_widget.tag_add("LTR", "insert linestart", "insert lineend")
                text_widget.tag_remove("RTL", "insert linestart", "insert lineend")
                
        # Bind to key release for real-time formatting
        text_widget.bind("<KeyRelease>", process_input)
        
        # Bind to direction change
        def on_direction_change(*args):
            # Apply direction to current line
            line_start = text_widget.index("insert linestart")
            line_end = text_widget.index("insert lineend")
            
            if self.text_direction.get() == "RTL":
                text_widget.tag_add("RTL", line_start, line_end)
                text_widget.tag_remove("LTR", line_start, line_end)
            else:
                text_widget.tag_add("LTR", line_start, line_end)
                text_widget.tag_remove("RTL", line_start, line_end)
                
        self.text_direction.trace_add("write", on_direction_change)
        
        return frame, text_widget

    def setup_medications_tab(self):
        """Setup the medications tab interface with improved layout and functionality"""
        # Create main frame with horizontal panes
        medications_paned = ttk.PanedWindow(self.medications_tab, orient=tk.HORIZONTAL)
        medications_paned.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Left and right frames
        left_frame = ttk.Frame(medications_paned)
        right_frame = ttk.Frame(medications_paned)
        
        medications_paned.add(left_frame, weight=40)  # 40% of width
        medications_paned.add(right_frame, weight=60)  # 60% of width
        
        # ===== PATIENT SELECTION SECTION (LEFT SIDE) =====
        patient_frame = ttk.LabelFrame(left_frame, text="Patient Selection")
        patient_frame.pack(fill='x', padx=5, pady=5)
        
        # Quick access tabs for patient selection
        patient_notebook = ttk.Notebook(patient_frame)
        patient_notebook.pack(fill='x', padx=5, pady=5)
        
        # Search tab
        search_tab = ttk.Frame(patient_notebook)
        recent_tab = ttk.Frame(patient_notebook)
        
        patient_notebook.add(search_tab, text="Search Patient")
        patient_notebook.add(recent_tab, text="Recent Patients")
        
        # Search tab content
        search_options_frame = ttk.Frame(search_tab)
        search_options_frame.pack(fill='x', padx=5, pady=5)
        
        # Search type selector
        ttk.Label(search_options_frame, text="Search by:").pack(side=tk.LEFT, padx=5)
        self.med_search_type = ttk.Combobox(search_options_frame, values=["Name", "ID", "Phone"], width=10)
        self.med_search_type.current(0)  # Default to Name
        self.med_search_type.pack(side=tk.LEFT, padx=5)
        
        # Search entry with icon
        search_entry_frame = ttk.Frame(search_tab)
        search_entry_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(search_entry_frame, text="🔍").pack(side=tk.LEFT)
        self.med_search_entry = ttk.Entry(search_entry_frame)
        self.med_search_entry.pack(side=tk.LEFT, fill='x', expand=True, padx=5)
        
        # Make Enter key trigger search
        self.med_search_entry.bind("<Return>", lambda event: self.search_patient_for_medication())
        
        # Search results with column headers
        self.med_search_tree = ttk.Treeview(search_tab, columns=('ID', 'Name', 'DOB'), show='headings', height=5)
        self.med_search_tree.heading('ID', text='ID')
        self.med_search_tree.heading('Name', text='Name')
        self.med_search_tree.heading('DOB', text='Date of Birth')
        
        # Adjust column widths
        self.med_search_tree.column('ID', width=50)
        self.med_search_tree.column('Name', width=150)
        self.med_search_tree.column('DOB', width=80)
        
        # Add scrollbar to search results
        search_scroll = ttk.Scrollbar(search_tab, orient="vertical", command=self.med_search_tree.yview)
        self.med_search_tree.configure(yscrollcommand=search_scroll.set)
        
        self.med_search_tree.pack(side=tk.LEFT, fill='both', expand=True, padx=5, pady=5)
        search_scroll.pack(side=tk.RIGHT, fill='y', pady=5)
        
        # Bind selection event
        self.med_search_tree.bind('<<TreeviewSelect>>', self.on_medication_patient_selected)
        
        # Recent patients tab content
        self.recent_patients_tree = ttk.Treeview(recent_tab, columns=('ID', 'Name', 'Last Visit'), show='headings', height=5)
        self.recent_patients_tree.heading('ID', text='ID')
        self.recent_patients_tree.heading('Name', text='Name')
        self.recent_patients_tree.heading('Last Visit', text='Last Visit')
        
        # Adjust column widths
        self.recent_patients_tree.column('ID', width=50)
        self.recent_patients_tree.column('Name', width=150)
        self.recent_patients_tree.column('Last Visit', width=80)
        
        # Add scrollbar to recent patients
        recent_scroll = ttk.Scrollbar(recent_tab, orient="vertical", command=self.recent_patients_tree.yview)
        self.recent_patients_tree.configure(yscrollcommand=recent_scroll.set)
        
        self.recent_patients_tree.pack(side=tk.LEFT, fill='both', expand=True, padx=5, pady=5)
        recent_scroll.pack(side=tk.RIGHT, fill='y', pady=5)
        
        # Bind selection event for recent patients
        self.recent_patients_tree.bind('<<TreeviewSelect>>', self.on_recent_patient_selected)
        
        # Add "Refresh" button for recent patients
        ttk.Button(recent_tab, text="Refresh Recent", 
                   command=self.load_recent_patients).pack(padx=5, pady=5, anchor='se')
        
        # Selected patient information card
        selected_patient_frame = ttk.LabelFrame(left_frame, text="Selected Patient")
        selected_patient_frame.pack(fill='x', padx=5, pady=5)
        
        # Style the patient card to make it more visible
        patient_card = ttk.Frame(selected_patient_frame, style="Card.TFrame")
        patient_card.pack(fill='x', padx=10, pady=10)
        
        # Patient details with grid layout
        ttk.Label(patient_card, text="Patient ID:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.med_patient_id = ttk.Entry(patient_card, width=10, state='readonly')
        self.med_patient_id.grid(row=0, column=1, sticky='w', padx=5, pady=2)
        
        ttk.Label(patient_card, text="Name:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.med_patient_name = ttk.Entry(patient_card, width=25, state='readonly')
        self.med_patient_name.grid(row=1, column=1, sticky='w', padx=5, pady=2)
        
        ttk.Label(patient_card, text="Age:").grid(row=2, column=0, sticky='w', padx=5, pady=2)
        self.med_patient_age = ttk.Entry(patient_card, width=5, state='readonly')
        self.med_patient_age.grid(row=2, column=1, sticky='w', padx=5, pady=2)
        
        # Clear selected patient button
        ttk.Button(selected_patient_frame, text="Clear Selection", 
                   command=self.clear_medication_patient).pack(pady=5, anchor='e', padx=10)
        
        # ===== MEDICATIONS LIST SECTION (LEFT SIDE) =====
        medications_list_frame = ttk.LabelFrame(left_frame, text="Current Prescription Items")
        medications_list_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Toolbar for medication list operations
        meds_toolbar = ttk.Frame(medications_list_frame)
        meds_toolbar.pack(fill='x', padx=5, pady=2)
        
        ttk.Button(meds_toolbar, text="Edit Selected", 
                   command=self.edit_selected_medication).pack(side=tk.LEFT, padx=2)
        ttk.Button(meds_toolbar, text="Remove", 
                   command=self.remove_selected_medication).pack(side=tk.LEFT, padx=2)
        ttk.Button(meds_toolbar, text="Clear All", 
                   command=self.clear_all_medications).pack(side=tk.LEFT, padx=2)
        
        # Create medications treeview with improved columns
        columns = ('Type', 'Name', 'Dosage', 'Frequency', 'Duration', 'Tapering')
        self.medications_tree = ttk.Treeview(medications_list_frame, columns=columns, show='headings', height=8)
        
        # Configure columns with better sizing
        self.medications_tree.heading('Type', text='Type')
        self.medications_tree.heading('Name', text='Medication Name')
        self.medications_tree.heading('Dosage', text='Dosage')
        self.medications_tree.heading('Frequency', text='Frequency')
        self.medications_tree.heading('Duration', text='Duration')
        self.medications_tree.heading('Tapering', text='Tapering Schedule')
        
        self.medications_tree.column('Type', width=80)
        self.medications_tree.column('Name', width=150)
        self.medications_tree.column('Dosage', width=70)
        self.medications_tree.column('Frequency', width=100)
        self.medications_tree.column('Duration', width=80)
        self.medications_tree.column('Tapering', width=150)
        
        # Add scrollbars
        meds_y_scroll = ttk.Scrollbar(medications_list_frame, orient=tk.VERTICAL, command=self.medications_tree.yview)
        meds_x_scroll = ttk.Scrollbar(medications_list_frame, orient=tk.HORIZONTAL, command=self.medications_tree.xview)
        self.medications_tree.configure(yscrollcommand=meds_y_scroll.set, xscrollcommand=meds_x_scroll.set)
        
        # Pack widgets
        self.medications_tree.pack(side=tk.TOP, fill='both', expand=True, padx=5, pady=5)
        meds_x_scroll.pack(side=tk.BOTTOM, fill='x')
        meds_y_scroll.pack(side=tk.RIGHT, fill='y')
        
        # Add double-click to edit functionality
        self.medications_tree.bind("<Double-1>", lambda event: self.edit_selected_medication())
        
        # Action buttons for the prescription
        action_frame = ttk.Frame(left_frame)
        action_frame.pack(fill='x', padx=5, pady=10)
        
        prescription_buttons = ttk.Frame(action_frame)
        prescription_buttons.pack(side=tk.RIGHT)
        
        ttk.Button(prescription_buttons, text="Save Prescription", 
                   command=self.save_medication).pack(side=tk.LEFT, padx=5)
        ttk.Button(prescription_buttons, text="Print Prescription", 
                   command=self.print_medication).pack(side=tk.LEFT, padx=5)
        
        # ===== MEDICATION ENTRY FORM (RIGHT SIDE) =====
        medication_entry_frame = ttk.LabelFrame(right_frame, text="Add New Medication")
        medication_entry_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create a scrollable canvas for the form
        canvas = tk.Canvas(medication_entry_frame)
        scrollbar = ttk.Scrollbar(medication_entry_frame, orient="vertical", command=canvas.yview)
        
        # Create a frame inside the canvas to hold the form
        form_frame = ttk.Frame(canvas)
        form_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Add the form frame to the canvas
        canvas.create_window((0, 0), window=form_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack the canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Medication Type (as dropdown)
        type_frame = ttk.Frame(form_frame)
        type_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(type_frame, text="Type:").pack(side=tk.LEFT, padx=5)
        
        # Define medication types for the dropdown
        med_types = [
            "Eye Drops", 
            "Eye Ointment", 
            "Oral Medication", 
            "Tablet", 
            "Capsule", 
            "Injection"
        ]
        self.med_type = ttk.Combobox(type_frame, values=med_types, width=20)
        self.med_type.pack(side=tk.LEFT, padx=5, fill='x', expand=True)
        
        # Name with improved layout
        name_frame = ttk.Frame(form_frame)
        name_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(name_frame, text="Name:").pack(side=tk.LEFT, padx=5)
        self.med_name = ttk.Entry(name_frame, width=30)
        self.med_name.pack(side=tk.LEFT, padx=5, fill='x', expand=True)
        
        # Common medication names dropdown for quick selection
        common_names = [
            "Prednisolone Acetate", 
            "Moxifloxacin", 
            "Timolol", 
            "Tobramycin", 
            "Dexamethasone", 
            "Cyclopentolate",
            "Latanoprost",
            "Brimonidine",
            "Artificial Tears",
            "Atropine"
        ]
        self.med_name_list = ttk.Combobox(name_frame, values=common_names, width=20)
        self.med_name_list.pack(side=tk.LEFT, padx=5)
        
        # When a name is selected from the dropdown, update the entry
        def update_name(event):
            selected = self.med_name_list.get()
            if selected:
                self.med_name.delete(0, tk.END)
                self.med_name.insert(0, selected)
        
        self.med_name_list.bind("<<ComboboxSelected>>", update_name)
        
        # Dosage with common options
        dosage_frame = ttk.Frame(form_frame)
        dosage_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(dosage_frame, text="Dosage:").pack(side=tk.LEFT, padx=5)
        self.med_dosage = ttk.Entry(dosage_frame, width=20)
        self.med_dosage.pack(side=tk.LEFT, padx=5, fill='x', expand=True)
        
        # Common dosages
        common_dosages = [
            "1%", "0.5%", "0.1%", "0.3%", 
            "1 drop", "2 drops", 
            "5mg", "10mg", "20mg", "25mg", "50mg", "100mg",
            "125mg", "250mg", "500mg", "1g"
        ]
        self.dosage_list = ttk.Combobox(dosage_frame, values=common_dosages, width=15)
        self.dosage_list.pack(side=tk.LEFT, padx=5)
        
        def update_dosage(event):
            selected = self.dosage_list.get()
            if selected:
                self.med_dosage.delete(0, tk.END)
                self.med_dosage.insert(0, selected)
        
        self.dosage_list.bind("<<ComboboxSelected>>", update_dosage)
        
        # Frequency with common options
        freq_frame = ttk.Frame(form_frame)
        freq_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(freq_frame, text="Frequency:").pack(side=tk.LEFT, padx=5)
        self.med_frequency = ttk.Entry(freq_frame, width=20)
        self.med_frequency.pack(side=tk.LEFT, padx=5, fill='x', expand=True)
        
        # Common frequencies
        common_frequencies = [
            "QID (4 times daily)", 
            "TID (3 times daily)", 
            "BID (2 times daily)", 
            "Daily", 
            "Every 2 hours", 
            "Every 4 hours",
            "Every 6 hours",
            "Hourly",
            "At bedtime",
            "Once weekly",
            "Twice weekly"
        ]
        self.frequency_list = ttk.Combobox(freq_frame, values=common_frequencies, width=20)
        self.frequency_list.pack(side=tk.LEFT, padx=5)
        
        def update_frequency(event):
            selected = self.frequency_list.get()
            if selected:
                self.med_frequency.delete(0, tk.END)
                self.med_frequency.insert(0, selected)
        
        self.frequency_list.bind("<<ComboboxSelected>>", update_frequency)
        
        # Duration with common options
        duration_frame = ttk.Frame(form_frame)
        duration_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(duration_frame, text="Duration:").pack(side=tk.LEFT, padx=5)
        self.med_duration = ttk.Entry(duration_frame, width=20)
        self.med_duration.pack(side=tk.LEFT, padx=5, fill='x', expand=True)
        
        # Common durations
        common_durations = [
            "1 week", "2 weeks", "3 weeks", "4 weeks", 
            "1 month", "2 months", "3 months", 
            "5 days", "7 days", "10 days", "14 days",
            "Until finished"
        ]
        self.duration_list = ttk.Combobox(duration_frame, values=common_durations, width=15)
        self.duration_list.pack(side=tk.LEFT, padx=5)
        
        def update_duration(event):
            selected = self.duration_list.get()
            if selected:
                self.med_duration.delete(0, tk.END)
                self.med_duration.insert(0, selected)
        
        self.duration_list.bind("<<ComboboxSelected>>", update_duration)
        
        # Steroid checkbox for tapering schedule
        steroid_frame = ttk.Frame(form_frame)
        steroid_frame.pack(fill='x', padx=5, pady=5)
        
        self.is_steroid = tk.BooleanVar(value=False)
        steroid_check = ttk.Checkbutton(steroid_frame, text="Is Steroid (Enable Tapering Schedule)", 
                                       variable=self.is_steroid, 
                                       command=self.toggle_tapering_schedule)
        steroid_check.pack(side=tk.LEFT, padx=5)
        
        # Tapering Schedule Configuration
        self.tapering_config_frame = ttk.LabelFrame(form_frame, text="Tapering Schedule")
        
        # Create add/remove buttons for tapering steps
        buttons_frame = ttk.Frame(self.tapering_config_frame)
        buttons_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(buttons_frame, text="Add Step", command=self.add_tapering_step).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Remove Step", command=self.remove_tapering_step).pack(side=tk.LEFT, padx=5)
        
        # Add initial tapering step
        self.tapering_steps_frame = ttk.Frame(self.tapering_config_frame)
        self.tapering_steps_frame.pack(fill='x', padx=5, pady=5)
        
        self.tapering_entries = []
        self.add_tapering_step()
        
        # Additional Information
        info_frame = ttk.LabelFrame(form_frame, text="Additional Information")
        info_frame.pack(fill='x', padx=5, pady=5)
        
        # Instructions with common options
        ttk.Label(info_frame, text="Instructions:").pack(anchor='w', padx=5, pady=2)
        self.med_instructions = tk.Text(info_frame, height=3, width=40)
        self.med_instructions.pack(fill='x', padx=5, pady=2)
        
        # Add common instructions dropdown
        common_instructions = [
            "Apply to affected eye",
            "Apply to both eyes",
            "Apply to right eye only",
            "Apply to left eye only",
            "Take with food",
            "Take on empty stomach",
            "Shake well before using",
            "Do not touch tip to eye",
            "Wait 5 minutes between eye drops",
            "Store in refrigerator"
        ]
        
        instructions_dropdown_frame = ttk.Frame(info_frame)
        instructions_dropdown_frame.pack(fill='x', padx=5, pady=2)
        
        ttk.Label(instructions_dropdown_frame, text="Common Instructions:").pack(side=tk.LEFT, padx=5)
        self.instructions_list = ttk.Combobox(instructions_dropdown_frame, values=common_instructions, width=30)
        self.instructions_list.pack(side=tk.LEFT, padx=5, fill='x', expand=True)
        
        def add_instruction(event):
            selected = self.instructions_list.get()
            if selected:
                current = self.med_instructions.get("1.0", tk.END).strip()
                if current:
                    self.med_instructions.insert(tk.END, f"\n{selected}")
                else:
                    self.med_instructions.insert(tk.END, selected)
        
        self.instructions_list.bind("<<ComboboxSelected>>", add_instruction)
        
        # Notes
        ttk.Label(info_frame, text="Notes:").pack(anchor='w', padx=5, pady=2)
        self.med_notes = tk.Text(info_frame, height=3, width=40)
        self.med_notes.pack(fill='x', padx=5, pady=2)
        
        # Submit button for medication
        buttons_frame = ttk.Frame(form_frame)
        buttons_frame.pack(fill='x', padx=5, pady=10)
        
        ttk.Button(buttons_frame, text="Add to Prescription", 
                   command=self.add_to_medication_list,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Clear Fields", 
                   command=self.clear_medication_fields).pack(side=tk.LEFT, padx=5)
               
        # Initialize tapering options as hidden
        self.toggle_tapering_schedule()
        
        # Load recent patients initially
        self.load_recent_patients()

    def toggle_tapering_schedule(self):
        """Toggle visibility of tapering options based on checkbox state"""
        if self.is_steroid.get():
            self.tapering_config_frame.pack(fill='x', pady=5)
        else:
            self.tapering_config_frame.pack_forget()

    def add_to_medication_list(self):
        """Add medication to the list for this patient"""
        try:
            # Check if a patient is selected
            patient_id = self.med_patient_id.get()
            if not patient_id:
                messagebox.showerror("Error", "Please select a patient first")
                return
            
            # Get medication details
            med_type = self.med_type.get().strip()
            med_name = self.med_name.get().strip()
            med_dosage = self.med_dosage.get().strip()
            med_frequency = self.med_frequency.get().strip()
            med_duration = self.med_duration.get().strip()
            
            # Validate data
            if not (med_type and med_name):
                messagebox.showerror("Error", "Type and Name are required")
                return
                
            # Check if this is a steroid with tapering schedule
            tapering_schedule = ""
            if self.is_steroid.get():
                # Process tapering steps
                steps = []
                for freq, duration in self.tapering_entries:
                    step_freq = freq.get().strip()
                    step_duration = duration.get().strip()
                    
                    if step_freq and step_duration:
                        steps.append(f"{step_freq} for {step_duration}")
                
                if steps:
                    tapering_schedule = " → ".join(steps)
            
            # Add to treeview
            self.medications_tree.insert('', 'end', values=(
                med_type, med_name, med_dosage, med_frequency, med_duration, tapering_schedule
            ))
            
            # Provide feedback
            messagebox.showinfo("Success", "Medication added to list")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error adding medication: {str(e)}")

    def remove_selected_medication(self):
        """Remove selected medication from the list"""
        try:
            selected = self.medications_tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a medication to remove")
                return
                
            for item in selected:
                self.medications_tree.delete(item)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error removing medication: {str(e)}")

    def clear_medication_fields(self):
        """Clear only medication fields, keeping patient info"""
        try:
            self.med_type.set('')
            self.med_name.delete(0, tk.END)
            self.med_dosage.delete(0, tk.END)
            self.med_frequency.delete(0, tk.END)
            self.med_duration.delete(0, tk.END)
            self.med_instructions.delete("1.0", tk.END)
            self.med_notes.delete("1.0", tk.END)
            
            # Reset tapering schedule
            self.is_steroid.set(False)
            self.toggle_tapering_schedule()
            for freq, duration in self.tapering_entries:
                freq.delete(0, tk.END)
                freq.insert(0, "Frequency")
                duration.delete(0, tk.END)
                duration.insert(0, "Duration")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error clearing fields: {str(e)}")

    def set_medication_patient(self, patient):
        """Set the selected patient's information in the medication form"""
        try:
            # Clear any existing data
            self.med_patient_id.delete(0, tk.END)
            self.med_patient_name.delete(0, tk.END)
            
            # Set patient ID and name
            self.med_patient_id.insert(0, str(patient[0]))  # ID
            self.med_patient_name.insert(0, patient[1])     # Name
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set patient information: {str(e)}")

    def translate_medical_term(self, text):
        """Translate medical terms to Arabic with fallback to Google Translate"""
        if not text:
            return ""
            
        translations = {
            # Extended medication types
            "Eye Drops": "قطرة عين",
            "Eye Ointment": "مرهم عين",
            "Oral Medication": "دواء فموي",
            "Injection": "حقنة",
            "Capsule": "كبسولة",
            "Tablet": "قرص",
            
            # Dosage forms
            "mg": "ملغ",
            "ml": "مل",
            "drops": "قطرات",
            
            # Medication details
            "Dosage": "الجرعة",
            "Frequency": "التكرار",
            "Duration": "المدة",
            
            # Instructions
            "apply to affected eye": "ضع على العين المصابة",
            "both eyes": "كلتا العينين",
            "right eye": "العين اليمنى",
            "left eye": "العين اليسرى",
            
            # Add more terms as needed
        }
        
        text = text.strip().lower()
        if text in translations:
            return translations[text]
            
        # Handle numbers and units
        parts = re.split(r'(\d+)', text)
        translated_parts = []
        for part in parts:
            if part.isdigit():
                translated_parts.append(''.join(translations.get(d, d) for d in part))
            elif part in translations:
                translated_parts.append(translations[part])
            else:
                # Fallback to Google Translate
                try:
                    # Use our more reliable translate_text method instead of googletrans directly
                    translated = self.translate_text(part, 'ar')
                    translated_parts.append(translated)
                except Exception as e:
                    print(f"Translation error in medical term: {e}")
                    translated_parts.append(part)
                    
        return ' '.join(translated_parts)

    def show_patient_selection_dialog(self, patients):
        """Show dialog for selecting from multiple matching patients"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Patient")
        dialog.geometry("400x300")
        
        # Make dialog modal
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create and pack a label
        ttk.Label(dialog, text="Multiple patients found. Please select one:").pack(pady=10)
        
        # Create treeview for patients
        tree = ttk.Treeview(dialog, columns=('ID', 'Name', 'DOB'), show='headings')
        tree.heading('ID', text='ID')
        tree.heading('Name', text='Name')
        tree.heading('DOB', text='Date of Birth')
        tree.pack(pady=10, padx=10, fill='both', expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(dialog, orient='vertical', command=tree.yview)
        scrollbar.pack(side='right', fill='y')
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Insert patients into treeview
        for patient in patients:
            tree.insert('', 'end', values=(patient[0], patient[1], patient[2]))
        
        def on_select():
            selected = tree.selection()
            if selected:
                item = tree.item(selected[0])
                patient_id = item['values'][0]
                # Get full patient data
                cursor = self.conn.cursor()
                cursor.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
                patient = cursor.fetchone()
                if patient:
                    self.set_medication_patient(patient)
                dialog.destroy()
        
        # Add select button
        ttk.Button(dialog, text="Select", command=on_select).pack(pady=10)
        
        # Center the dialog on the screen
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'{width}x{height}+{x}+{y}')

    def create_qr_code(self, patient_id, patient_name, date, size=100):
        """Create QR code for prescription"""
        temp_dir = "temp"  # Define temp_dir at the start
        try:
            # Ensure the temp directory exists
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            
            # Create QR code data
            qr_data = f"ID: {patient_id}\nName: {patient_name}\nDate: {date}"
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Create PIL image
            qr_image = qr.make_image(fill_color="black", back_color="white")
            
            # Resize to specified size
            qr_image = qr_image.resize((size, size), Image.Resampling.LANCZOS)
            
            # Create a temporary file path with timestamp
            temp_file = os.path.join(temp_dir, f"qr_{patient_id}_{int(time.time())}.png")
            
            # Save the image
            qr_image.save(temp_file, format='PNG')
            
            return temp_file
            
        except Exception as e:
            print(f"Error creating QR code: {e}")
            return None
        
        finally:
            # Clean up old temporary files
            try:
                if os.path.exists(temp_dir):
                    current_time = time.time()
                    for f in os.listdir(temp_dir):
                        file_path = os.path.join(temp_dir, f)
                        if os.path.isfile(file_path) and current_time - os.path.getmtime(file_path) > 3600:
                            os.remove(file_path)
            except Exception as e:
                print(f"Error cleaning up temporary files: {e}")
    def save_medication(self):
        """Save medication to database"""
        try:
            patient_id = self.med_patient_id.get().strip()
            if not patient_id:
                messagebox.showerror("Error", "Please select a patient first")
                return
            
            # Get all medications from the tree
            medications = []
            for item in self.medications_tree.get_children():
                values = self.medications_tree.item(item)['values']
                medications.append({
                    'type': values[0],
                    'name': values[1],
                    'dosage': values[2],
                    'frequency': values[3],
                    'duration': values[4],
                    'tapering': values[5] if len(values) > 5 else None,
                })
            
            if not medications:
                messagebox.showwarning("Warning", "No medications to save")
                return
            
            # Save to database
            cursor = self.conn.cursor()
            
            try:
                # Create medications table if it doesn't exist
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS medications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        patient_id INTEGER,
                        type TEXT,
                        name TEXT,
                        dosage TEXT,
                        frequency TEXT,
                        duration TEXT,
                        tapering TEXT,
                        instructions TEXT,
                        notes TEXT,
                        date_prescribed TEXT,
                        FOREIGN KEY (patient_id) REFERENCES patients(id)
                    )
                ''')
                
                current_date = datetime.now().strftime('%Y-%m-%d')
                
                # First, delete existing medications for this visit
                cursor.execute('''
                    DELETE FROM medications 
                    WHERE patient_id = ? AND date(date_prescribed) = ?
                ''', (patient_id, current_date))
                
                # Then insert new medications
                for med in medications:
                    cursor.execute('''
                        INSERT INTO medications 
                        (patient_id, type, name, dosage, frequency, duration, tapering, 
                         instructions, notes, date_prescribed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        patient_id,
                        med['type'],
                        med['name'],
                        med['dosage'],
                        med['frequency'],
                        med['duration'],
                        med['tapering'],
                        self.med_instructions.get("1.0", tk.END).strip(),
                        self.med_notes.get("1.0", tk.END).strip(),
                        current_date
                    ))
                
                self.conn.commit()
                messagebox.showinfo("Success", "Medications saved successfully")
                
            except sqlite3.Error as e:
                self.conn.rollback()
                raise Exception(f"Database error: {str(e)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save medications: {str(e)}")

    def clear_medication_form(self):
        """Clear all fields in the medication form"""
        try:
            # Clear patient information
            self.med_patient_id.delete(0, tk.END)
            self.med_patient_name.delete(0, tk.END)
            
            # Clear medication details
            self.med_type.set('')
            self.med_name.delete(0, tk.END)
            self.med_dosage.delete(0, tk.END)
            self.med_frequency.delete(0, tk.END)
            self.med_duration.delete(0, tk.END)
            
            # Clear text areas
            self.med_instructions.delete("1.0", tk.END)
            self.med_notes.delete("1.0", tk.END)
            
            # Clear medications list
            for item in self.medications_tree.get_children():
                self.medications_tree.delete(item)
                
            # Reset tapering schedule
            self.is_steroid.set(False)
            self.toggle_tapering_schedule()
            for freq, duration in self.tapering_entries:
                freq.delete(0, tk.END)
                freq.insert(0, "Frequency")
                duration.delete(0, tk.END)
                duration.insert(0, "Duration")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error clearing form: {str(e)}")

    def draw_corner_decorations(self, c, margin):
        """Draw decorative corners on the prescription"""
        def draw_corner(x, y, rotate=0):
            """Draw a single corner decoration"""
            c.saveState()
            c.translate(x, y)
            c.rotate(rotate)
            c.setLineWidth(0.5)
            c.line(0, 0, 0.3*inch, 0)
            c.line(0, 0, 0, 0.3*inch)
            c.restoreState()
        
        # Calculate corner positions
        corner_margin = margin + 0.04*inch
        
        # Draw all four corners
        draw_corner(corner_margin, corner_margin)  # Bottom left
        draw_corner(letter[0]-corner_margin, corner_margin, 90)  # Bottom right
        draw_corner(letter[0]-corner_margin, letter[1]-corner_margin, 180)  # Top right
        draw_corner(corner_margin, letter[1]-corner_margin, 270)  # Top left

    def draw_patient_info(self, c, patient_data, patient_id, y_pos):
        """Draw patient information section on the prescription"""
        import arabic_reshaper
        from bidi.algorithm import get_display
        
        # Patient Information header
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1*inch, y_pos, "Patient Information:")
        
        # Arabic translation
        try:
            c.setFont(arabic_font, 12)
            info_ar = arabic_reshaper.reshape("معلومات المريض:")
            info_ar = get_display(info_ar)
            c.drawRightString(7.5*inch, y_pos, info_ar)
        except Exception as e:
            print(f"Error rendering Arabic patient info header: {e}")
        
        # Name
        y_pos -= 0.4*inch
        c.setFont("Helvetica", 11)
        c.drawString(1*inch, y_pos, f"Name: {patient_data[0]}")
        
        try:
            c.setFont(arabic_font, 11)
            name_ar = arabic_reshaper.reshape(f"الاسم: {patient_data[0]}")
            name_ar = get_display(name_ar)
            c.drawRightString(7.5*inch, y_pos, name_ar)
        except Exception as e:
            print(f"Error rendering Arabic patient name: {e}")
        
        # ID
        y_pos -= 0.3*inch
        c.setFont("Helvetica", 11)
        c.drawString(1*inch, y_pos, f"ID: {patient_id}")
        
        try:
            c.setFont(arabic_font, 11)
            # Convert patient_id to Arabic numerals with vertical adjustment
            arabic_patient_id, v_offset = self.convert_to_arabic_numerals_pdf(str(patient_id))
            id_ar = arabic_reshaper.reshape(f"رقم الملف: {arabic_patient_id}")
            id_ar = get_display(id_ar)
            # Apply vertical offset only to Arabic numeral text
            c.drawRightString(7.5*inch, y_pos + v_offset, id_ar)
        except Exception as e:
            print(f"Error rendering Arabic patient ID: {e}")
        
        # Date
        y_pos -= 0.3*inch
        date_str = datetime.now().strftime('%Y-%m-%d')
        c.setFont("Helvetica", 11)
        c.drawString(1*inch, y_pos, f"Date: {date_str}")
        
        try:
            c.setFont(arabic_font, 11)
            # Convert date to Arabic numerals with vertical adjustment
            arabic_date_str, v_offset = self.convert_to_arabic_numerals_pdf(date_str)
            date_ar = arabic_reshaper.reshape(f"التاريخ: {arabic_date_str}")
            date_ar = get_display(date_ar)
            # Apply vertical offset only to Arabic numeral text
            c.drawRightString(7.5*inch, y_pos + v_offset, date_ar)
        except Exception as e:
            print(f"Error rendering Arabic date: {e}")
        
        y_pos -= 0.3*inch
        c.setLineWidth(0.5)
        c.line(1*inch, y_pos, 7.5*inch, y_pos)

        return y_pos

    def print_medication(self):
        """Print medication prescription as PDF with Arabic support and improved formatting"""
        global arabic_font, ARABIC_SUPPORT
        
        try:
            # Initialize ARABIC_SUPPORT if not defined
            if 'ARABIC_SUPPORT' not in globals():
                ARABIC_SUPPORT = True
                
            # Import Arabic text processing libraries at the beginning of the function
            arabic_reshaper = None
            get_display = None
            if ARABIC_SUPPORT:
                try:
                    import arabic_reshaper
                    from bidi.algorithm import get_display
                except ImportError:
                    print("Arabic support libraries not found")
                    ARABIC_SUPPORT = False
                    
            # Ensure the Arabic font is properly set up
            if not arabic_font or arabic_font == "Helvetica":
                arabic_font = self.setup_pdf_arabic_font()
                    
            # Reset the page footer tracking
            self._current_page_footer_drawn = {}
            
            patient_id = self.med_patient_id.get().strip()
            if not patient_id:
                messagebox.showerror("Error", "Please select a patient first")
                return

            # Get patient information
            cursor = self.conn.cursor()
            cursor.execute('SELECT name, dob FROM patients WHERE id = ?', (patient_id,))
            patient_data = cursor.fetchone()
            
            if not patient_data:
                messagebox.showerror("Error", "Patient not found")
                return

            if not self.medications_tree.get_children():
                messagebox.showwarning("Warning", "No medications added to the list")
                return

            # Save medications first
            self.save_medication()

            # Generate PDF filename
            filename = f"medication_prescription_{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            c = canvas.Canvas(filename, pagesize=letter)
            
            # Apply initial border and footer setup for the first page
            # Use _add_page_border to ensure consistent border and footer on all pages
            self._add_page_border(c)
            
            # Constants for layout
            LEFT_MARGIN = 0.75 * inch  # Reduced from 1 inch
            RIGHT_MARGIN = letter[0] - 0.75 * inch  # Reduced from 1 inch
            TOP_MARGIN = letter[1] - 0.5 * inch  # Elevated from 0.75 inch to be closer to top
            SECTION_GAP = 0.4 * inch  # Slightly reduced from 0.5 inch
            LINE_GAP = 0.3 * inch  # Slightly reduced from 0.35 inch
            SMALL_GAP = 0.2 * inch  # Slightly reduced from 0.25 inch
            MEDICATION_SPACING = 0.5 * inch  # Added increased spacing between medications and instructions
            
            # Note: We don't need to add an additional border here since it's handled by _add_page_border
            # Add QR code to the right top corner
            qr_file = self.create_qr_code(patient_id=patient_id, patient_name=patient_data[0], date=datetime.now().strftime('%Y-%m-%d'))
            if qr_file and os.path.exists(qr_file):
                try:
                    # Position QR code in the top right corner with proper margins
                    c.drawImage(qr_file,
                            letter[0] - 1.25*inch,  # X position (right side with reduced margin)
                            letter[1] - 1.0*inch,  # Y position (top with reduced margin)
                            width=0.9*inch,  # Slightly smaller QR code
                            height=0.9*inch)
                finally:
                    # Clean up temporary QR code file
                    try:
                        os.remove(qr_file)
                    except:
                        pass
            
            # Header
            y_pos = TOP_MARGIN  # Elevated position (removed 0.1*inch subtraction)
            c.setFont(arabic_font, 24)  # Use global arabic_font
            header_ar = arabic_reshaper.reshape("د / محمود سامى أبوزيد")
            header_ar = get_display(header_ar)
            c.drawCentredString(letter[0]/2, y_pos, header_ar)  # Add missing text parameter
            
            y_pos -= LINE_GAP
            if ARABIC_SUPPORT:
                try:
                    # No need to import again since we already imported at the beginning
                    c.setFont(arabic_font, 12)  # Use global arabic_font
                    header_ar = arabic_reshaper.reshape("   أخصائي جراحات المياه البيضاء وتصحيح الابصار   ")
                    header_ar = get_display(header_ar)
                    c.drawCentredString(letter[0]/2, y_pos, header_ar)
                except Exception as e:
                    print(f"Error rendering Arabic header: {e}")
                 

            y_pos -= LINE_GAP
            if ARABIC_SUPPORT:
                try:
                    # No need to import again since we already imported at the beginning
                    c.setFont(arabic_font, 12)
                    address_ar = arabic_reshaper.reshape("عضو الكلية الملكية لطب وجراحة العيون بانجلترا")
                    address_ar = get_display(address_ar)
                    c.drawCentredString(letter[0]/2, y_pos, address_ar)  # Fixed: Use address_ar instead of header_ar
                except Exception as e:
                    print(f"Error rendering Arabic address: {e}")
            
            y_pos -= LINE_GAP
            if ARABIC_SUPPORT:
                try:
                    c.setFont(arabic_font, 12)  # Use global arabic_font
                    address_ar = arabic_reshaper.reshape("جراحات تجميل الجفون و الجهاز الدمعي بمعهد الرمد بالجيزة")
                    address_ar = get_display(address_ar)
                    c.drawCentredString(letter[0]/2, y_pos, address_ar)
                except Exception as e:
                    print(f"Error rendering Arabic address: {e}")

            # Patient Information
            y_pos -= SECTION_GAP * 2
            y_pos = self.draw_patient_info(c, patient_data, patient_id, y_pos)
            
            # Medications List Header
            y_pos -= SECTION_GAP * 1.5
            c.setFont("Helvetica-Bold", 12)
            c.drawString(LEFT_MARGIN, y_pos, "Prescribed Medications")
            if ARABIC_SUPPORT:
                try:
                    c.setFont(arabic_font, 12)  # Use global arabic_font
                    med_header_ar = arabic_reshaper.reshape("الأدوية الموصوفة")
                    med_header_ar = get_display(med_header_ar)
                    c.drawRightString(RIGHT_MARGIN, y_pos, med_header_ar)
                except Exception as e:
                    print(f"Error rendering Arabic medications header: {e}")
            
            y_pos -= LINE_GAP * 1.5
            
            # Draw medications
            for item in self.medications_tree.get_children():
                if y_pos < 2*inch:
                    c.showPage()
                    self._add_page_border(c)
                    y_pos = TOP_MARGIN - 2*inch

                values = self.medications_tree.item(item)['values']
                c.setFont("Helvetica-Bold", 11)
                med_name = f"{values[0] or ''}: {values[1] or ''}"
                c.drawString(LEFT_MARGIN, y_pos, med_name)
                
                if ARABIC_SUPPORT:
                    try:
                        c.setFont(arabic_font, 11)  # Ensure Arabic font is set
                        med_type = str(values[0]) if values[0] else ""
                        type_translated = self.translate_medical_term(med_type)
                        med_name_ar = f"{type_translated}: {values[1] or ''}"
                        # Convert any numbers in the medication name to Arabic numerals
                        med_name_ar = self.convert_to_arabic_numerals(med_name_ar)
                        med_name_ar = arabic_reshaper.reshape(med_name_ar)
                        med_name_ar = get_display(med_name_ar)
                        c.drawRightString(RIGHT_MARGIN, y_pos, med_name_ar)
                    except Exception as e:
                        print(f"Error rendering Arabic medication name: {e}")
                
                y_pos -= LINE_GAP
                
                # Details
                details = [
                    ("Dosage:", str(values[2]) if values[2] else ""),
                    ("Frequency:", str(values[3]) if values[3] else ""),
                    ("Duration:", str(values[4]) if values[4] else "")
                ]
                
                for label, value in details:
                    c.setFont("Helvetica", 11)
                    c.drawString(LEFT_MARGIN + 0.3*inch, y_pos, f"{label} {value}")
                    if ARABIC_SUPPORT:
                        try:
                            c.setFont(arabic_font, 11)  # Ensure the Arabic font is set
                            # Translate the label itself (removing the colon for translation)
                            label_without_colon = label.rstrip(':')
                            label_ar = self.translate_medical_term(label_without_colon)
                            label_ar = f"{label_ar}:"  # Add back the colon
                            
                            # Convert any numbers in the value to Arabic numerals
                            value_ar = self.translate_medical_term(value)
                            value_ar = self.convert_to_arabic_numerals(value_ar)
                            
                            # Reshape and display the Arabic text
                            text_ar = f"{label_ar} {value_ar}"
                            text_ar = arabic_reshaper.reshape(text_ar)
                            text_ar = get_display(text_ar)
                            c.drawRightString(RIGHT_MARGIN, y_pos, text_ar)
                        except Exception as e:
                            print(f"Error rendering Arabic detail: {e}")
                    y_pos -= SMALL_GAP
                
                # Tapering schedule
                if len(values) > 5 and values[5]:
                    y_pos -= SMALL_GAP * 1.5  # Increased spacing before schedule section
                    
                    # Add a visual separator line before tapering schedule
                    c.setLineWidth(0.5)
                    c.setStrokeColorRGB(0.8, 0.8, 0.8)  # Light gray line
                    c.line(LEFT_MARGIN, y_pos + 0.1*inch, RIGHT_MARGIN, y_pos + 0.1*inch)
                    
                    # Tapering schedule header with clear separation
                    y_pos -= SMALL_GAP
                    c.setFont("Helvetica-Bold", 11)
                    c.drawString(LEFT_MARGIN, y_pos, "Tapering Schedule:")
                    
                    if ARABIC_SUPPORT:
                        try:
                            c.setFont(arabic_font, 11)
                            taper_ar = arabic_reshaper.reshape("جدول التناقص:")
                            taper_ar = get_display(taper_ar)
                            # Align with other Arabic right-aligned text
                            c.drawRightString(RIGHT_MARGIN, y_pos, taper_ar)
                        except Exception as e:
                            print(f"Error rendering Arabic tapering header: {e}")
                    
                    # Define layout columns to prevent overlap
                    english_left = LEFT_MARGIN + 0.3*inch
                    english_right = letter[0]/2 - 0.5*inch  # English text stays in left half
                    arabic_left = letter[0]/2 + 0.5*inch    # Arabic text starts in right half
                    arabic_right = RIGHT_MARGIN - 0.1*inch
                    
                    # Split the tapering steps
                    schedule_steps = values[5].split(" → ")
                    
                    # Add a subheader row with columns
                    y_pos -= SMALL_GAP * 1.2
                    c.setFont("Helvetica-Oblique", 10)
                    c.drawString(english_left, y_pos, "Step")
                    c.drawString(english_left + 0.6*inch, y_pos, "Instructions")
                    
                    if ARABIC_SUPPORT:
                        try:
                            c.setFont(arabic_font, 10)
                            step_header_ar = arabic_reshaper.reshape("الخطوة")
                            step_header_ar = get_display(step_header_ar)
                            instr_header_ar = arabic_reshaper.reshape("التعليمات")
                            instr_header_ar = get_display(instr_header_ar)
                            # Put the "الخطوة" header to the right (first in RTL reading)
                            c.drawRightString(arabic_right, y_pos, step_header_ar)
                            # Position "التعليمات" header to the left of "الخطوة"
                            c.drawRightString(arabic_right - 1.2*inch, y_pos, instr_header_ar)
                        except Exception as e:
                            print(f"Error rendering Arabic column headers: {e}")
                    
                    # Draw a light separator under headers
                    y_pos -= 0.1*inch
                    c.setLineWidth(0.3)
                    c.line(LEFT_MARGIN + 0.2*inch, y_pos, RIGHT_MARGIN - 0.2*inch, y_pos)
                    
                    # Display each step with better formatting
                    for i, step in enumerate(schedule_steps):
                        step_y_pos = y_pos - SMALL_GAP * 1.5  # Starting position for this step
                        
                        # Display step number in a consistent position
                        c.setFont("Helvetica-Bold", 10)
                        c.drawString(english_left, step_y_pos, f"{i+1}.")
                        
                        # Clean up the step text - remove "Then " prefix if present
                        step_text = step.replace("Then ", "").strip()
                        
                        # Prepare English lines with wrapping
                        c.setFont("Helvetica", 10)
                        english_lines = textwrap.wrap(step_text, width=40)
                        
                        # Prepare Arabic lines (if supported)
                        arabic_lines = []
                        if ARABIC_SUPPORT:
                            try:
                                # Translate the step text
                                ar_text = self.translate_medical_term(step_text)
                                # Use the improved method for vertical alignment
                                ar_text_converted, v_offset = self.convert_to_arabic_numerals_pdf(ar_text)
                                ar_text = arabic_reshaper.reshape(ar_text_converted)
                                ar_text = get_display(ar_text)
                                arabic_lines = textwrap.wrap(ar_text, width=40)
                            except Exception as e:
                                print(f"Error preparing Arabic lines: {e}")
                        
                        # Draw English and Arabic text line by line
                        # Determine the maximum number of lines needed
                        max_lines = max(len(english_lines), len(arabic_lines))
                        
                        for j in range(max_lines):
                            line_y = step_y_pos - (j * 0.2*inch)
                            
                            # Draw English line if available
                            if j < len(english_lines):
                                c.setFont("Helvetica", 10)
                                c.drawString(english_left + 0.6*inch, line_y, english_lines[j])
                            
                            # Draw Arabic line if available
                            if j < len(arabic_lines) and ARABIC_SUPPORT:
                                c.setFont(arabic_font, 10)
                                # Use the vertical offset when Arabic numerals are present
                                has_arabic_numerals = any(char in '٠١٢٣٤٥٦٧٨٩' for char in arabic_lines[j])
                                y_offset = v_offset if has_arabic_numerals else 0
                                # Align Arabic text with the instructions header (which is now to the left of "الخطوة")
                                c.drawRightString(arabic_right - 1.2*inch, line_y + y_offset, arabic_lines[j])
                                
                            # If this is the first line, also draw the step number in Arabic
                            if j == 0 and ARABIC_SUPPORT:
                                try:
                                    c.setFont(arabic_font, 10)
                                    # Use the improved method for vertical alignment
                                    step_num_ar_converted, v_offset = self.convert_to_arabic_numerals_pdf(str(i+1), vertical_offset=-2)
                                    step_num_ar = arabic_reshaper.reshape(step_num_ar_converted + ".")
                                    step_num_ar = get_display(step_num_ar)
                                    # Align with the الخطوة header (which is now at the right)
                                    c.drawRightString(arabic_right, line_y + v_offset, step_num_ar)
                                except Exception as e:
                                    print(f"Error rendering Arabic step number: {e}")
                        
                        # Update y_pos based on the content of this step
                        y_pos = step_y_pos - (max_lines * 0.2*inch) - 0.1*inch  # Extra space between steps
                    
                    # Add extra spacing after the entire schedule
                    y_pos -= SMALL_GAP
                    
                    # Add a visual separator line after tapering schedule
                    c.setLineWidth(0.5)
                    c.setStrokeColorRGB(0.8, 0.8, 0.8)  # Light gray line
                    c.line(LEFT_MARGIN, y_pos, RIGHT_MARGIN, y_pos)
                
                # Add extra spacing after the entire schedule
                y_pos -= SMALL_GAP * 1.5
                
                # Add a visual separator line after tapering schedule
                c.setLineWidth(0.5)
                c.setStrokeColorRGB(0.8, 0.8, 0.8)  # Light gray line
                c.line(LEFT_MARGIN, y_pos, RIGHT_MARGIN, y_pos)
            
            # Instructions
            instructions = self.med_instructions.get("1.0", tk.END).strip()
            if instructions:
                if y_pos < 3*inch:
                    c.showPage()
                    self._add_page_border(c)
                    y_pos = TOP_MARGIN - 2*inch
                
                c.setFont("Helvetica-Bold", 11)
                c.drawString(LEFT_MARGIN, y_pos, "Instructions:")
                if ARABIC_SUPPORT:
                    try:
                        c.setFont(arabic_font, 11)  # Use global arabic_font
                        inst_ar = arabic_reshaper.reshape("التعليمات:")
                        inst_ar = get_display(inst_ar)
                        c.drawRightString(RIGHT_MARGIN, y_pos, inst_ar)
                    except Exception as e:
                        print(f"Error rendering Arabic instructions header: {e}")
                
                y_pos -= LINE_GAP
                for line in textwrap.wrap(instructions, width=50):
                    if ARABIC_SUPPORT:
                        try:
                            c.setFont(arabic_font, 11)  # Use global arabic_font
                            
                            # More comprehensive check for Arabic characters
                            def is_arabic_char(char):
                                return (
                                    ('\u0600' <= char <= '\u06FF') or  # Basic Arabic
                                    ('\u0750' <= char <= '\u077F') or  # Arabic Supplement
                                    ('\u0780' <= char <= '\u07BF') or  # Thaana (sometimes contains Arabic)
                                    ('\u08A0' <= char <= '\u08FF') or  # Arabic Extended-A
                                    ('\uFB50' <= char <= '\uFDFF') or  # Arabic Presentation Forms-A
                                    ('\uFE70' <= char <= '\uFEFF')     # Arabic Presentation Forms-B
                                )
                            
                            # Check if the line contains Arabic characters
                            has_arabic = any(is_arabic_char(c) for c in line)
                            
                            # If it has Arabic, reshape and display at right position, otherwise draw English at left
                            if has_arabic:
                                line_ar = arabic_reshaper.reshape(line)
                                line_ar = get_display(line_ar)
                                # Check for Arabic numerals and adjust vertical alignment
                                has_numerals = any(char in '٠١٢٣٤٥٦٧٨٩' for char in line_ar)
                                if has_numerals:
                                    c.drawRightString(RIGHT_MARGIN - 0.3*inch, y_pos - 1.5, line_ar)
                                else:
                                    c.drawRightString(RIGHT_MARGIN - 0.3*inch, y_pos, line_ar)
                            else:
                                c.setFont("Helvetica", 11)
                                c.drawString(LEFT_MARGIN + 0.3*inch, y_pos, line)
                                
                                # Translate English to Arabic
                                c.setFont(arabic_font, 11)  # Set Arabic font again for translated text
                                line_ar = self.translate_text(line, 'ar')
                                # Convert any numbers to Arabic numerals with vertical alignment adjustment
                                line_ar_converted, v_offset = self.convert_to_arabic_numerals_pdf(line_ar)
                                line_ar = arabic_reshaper.reshape(line_ar_converted)
                                line_ar = get_display(line_ar)
                                c.drawRightString(RIGHT_MARGIN - 0.3*inch, y_pos + v_offset, line_ar)
                        except Exception as e:
                            print(f"Error rendering Arabic instruction line: {e}")
                            # Fallback to English only on exception
                            c.setFont("Helvetica", 11)
                            c.drawString(LEFT_MARGIN + 0.3*inch, y_pos, line)
                    else:
                        c.setFont("Helvetica", 11)
                        c.drawString(LEFT_MARGIN + 0.3*inch, y_pos, line)
                        
                    y_pos -= LINE_GAP
                    if y_pos < 2*inch:
                        c.showPage()
                        self._add_page_border(c)
                        y_pos = TOP_MARGIN - 2*inch

                # Notes
                notes = self.med_notes.get("1.0", tk.END).strip()
                if notes:
                    if y_pos < 3*inch:
                        c.showPage()
                        self._add_page_border(c)
                        y_pos = TOP_MARGIN - 2*inch
                    
                    c.setFont("Helvetica-Bold", 11)
                    c.drawString(LEFT_MARGIN, y_pos, "Notes:")
                    if ARABIC_SUPPORT:
                        try:
                            c.setFont(arabic_font, 11)  # Use global arabic_font
                            notes_ar = arabic_reshaper.reshape("ملاحظات:")
                            notes_ar = get_display(notes_ar)
                            c.drawRightString(RIGHT_MARGIN, y_pos, notes_ar)
                        except Exception as e:
                            print(f"Error rendering Arabic notes header: {e}")
                    
                    y_pos -= LINE_GAP
                    for line in textwrap.wrap(notes, width=50):
                        if ARABIC_SUPPORT:
                            try:
                                c.setFont(arabic_font, 11)  # Use global arabic_font
                                
                                # More comprehensive check for Arabic characters
                                def is_arabic_char(char):
                                    return (
                                        ('\u0600' <= char <= '\u06FF') or  # Basic Arabic
                                        ('\u0750' <= char <= '\u077F') or  # Arabic Supplement
                                        ('\u0780' <= char <= '\u07BF') or  # Thaana (sometimes contains Arabic)
                                        ('\u08A0' <= char <= '\u08FF') or  # Arabic Extended-A
                                        ('\uFB50' <= char <= '\uFDFF') or  # Arabic Presentation Forms-A
                                        ('\uFE70' <= char <= '\uFEFF')     # Arabic Presentation Forms-B
                                    )
                                
                                # Check if the line contains Arabic characters
                                has_arabic = any(is_arabic_char(c) for c in line)
                                
                                # If it has Arabic, reshape and display at right position, otherwise draw English at left
                                if has_arabic:
                                    line_ar = arabic_reshaper.reshape(line)
                                    line_ar = get_display(line_ar)
                                    # Check for Arabic numerals and adjust vertical alignment
                                    has_numerals = any(char in '٠١٢٣٤٥٦٧٨٩' for char in line_ar)
                                    if has_numerals:
                                        c.drawRightString(RIGHT_MARGIN - 0.3*inch, y_pos - 1.5, line_ar)
                                    else:
                                        c.drawRightString(RIGHT_MARGIN - 0.3*inch, y_pos, line_ar)
                                else:
                                    c.setFont("Helvetica", 11)
                                    c.drawString(LEFT_MARGIN + 0.3*inch, y_pos, line)
                                    # Translate English to Arabic
                                    translated_text = self.translate_text(line, 'ar')
                                    line_ar = arabic_reshaper.reshape(translated_text)
                                    line_ar = get_display(line_ar)
                                    c.setFont(arabic_font, 11)
                                    c.drawRightString(RIGHT_MARGIN - 0.3*inch, y_pos, line_ar)
                            except Exception as e:
                                print(f"Error rendering Arabic note line: {e}")
                                # Fallback to English only on exception
                                c.setFont("Helvetica", 11)
                                c.drawString(LEFT_MARGIN + 0.3*inch, y_pos, line)
                        else:
                            c.setFont("Helvetica", 11)
                            c.drawString(LEFT_MARGIN + 0.3*inch, y_pos, line)
                        
                        y_pos -= LINE_GAP
                        if y_pos < 2*inch:
                            c.showPage()
                            self._add_page_border(c)
                            y_pos = TOP_MARGIN - 2*inch

            # Skip adding footer here as it's already handled by _add_page_border
            c.save()

            # Open the PDF
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(filename)
                else:  # macOS and Linux
                    os.system(f'open {filename}')
            except Exception as e:
                messagebox.showinfo("Success", f"Prescription saved as {filename}: {str(e)}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate PDF: {str(e)}")

    def _add_page_border(self, c):
        """Add a consistent border to the PDF page"""
        try:
            # Draw borders first (this includes the decorative corners)
            self.draw_prescription_border(c)
            
            # Then explicitly add the footer with proper positioning within the border
            # This ensures consistent footer appearance on all pages
            self.draw_prescription_footer(c)
            
        except Exception as e:
            print(f"Error adding page border: {e}")
            import traceback
            traceback.print_exc()

    def search_patient_for_medication(self):
        """Search for patients and update the medication search tree"""
        try:
            # Get search query
            query = self.med_search_entry.get().strip()
            
            # Clear current results
            for item in self.med_search_tree.get_children():
                self.med_search_tree.delete(item)
            
            if not query:
                return
                
            # Search database
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, name 
                FROM patients 
                WHERE name LIKE ? OR id LIKE ?
            ''', (f'%{query}%', f'%{query}%'))
            
            # Add results to tree
            results = cursor.fetchall()
            for row in results:
                self.med_search_tree.insert('', 'end', values=row)
                
            # Bind selection event
            def on_select(event):
                selected = self.med_search_tree.selection()
                if not selected:
                    return
                    
                # Get selected patient data
                item = self.med_search_tree.item(selected[0])
                patient_id, patient_name = item['values']
                
                # Update patient info fields
                self.med_patient_id.delete(0, tk.END)
                self.med_patient_id.insert(0, str(patient_id))
                
                self.med_patient_name.delete(0, tk.END)
                self.med_patient_name.insert(0, patient_name)
            
            self.med_search_tree.bind('<<TreeviewSelect>>', on_select)
            
            if not results:
                messagebox.showinfo("Search Results", "No matching patients found")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error searching for patients: {str(e)}")

    def set_medication_patient(self, patient):
        """Set patient information in medication form"""
        try:
            self.med_patient_id.delete(0, tk.END)
            self.med_patient_id.insert(0, str(patient[0]))  # ID
            
            self.med_patient_name.delete(0, tk.END)
            self.med_patient_name.insert(0, patient[1])  # Name
            
        except Exception as e:
            messagebox.showerror("Error", f"Error setting patient information: {str(e)}")

    def draw_prescription_border(self, c):
        """Draw a decorative border for Arabic PDFs"""
        try:
            # Get page dimensions
            width, height = letter
            
            # Set border color (dark blue)
            c.setStrokeColorRGB(0, 0.2, 0.4)
            c.setLineWidth(2)
            
            # Draw outer border only with minimized margin
            # Reduce margin from 20 to 10 to maximize space for content
            margin = 10
            c.rect(margin, margin, width - 2*margin, height - 2*margin)
            
            # Draw decorative corners
            self.draw_corner_decorations(c, margin)
            
            # Don't add footer content here - it will be handled by draw_prescription_footer
            
        except Exception as e:
            print(f"Error drawing prescription border: {e}")
            import traceback
            traceback.print_exc()

    def draw_corner_decorations(self, c, margin):
        """Draw decorative Islamic-style corners for the PDF"""
        try:
            width, height = letter
            corner_size = 20
            
            # Define a function to draw a corner decoration
            def draw_corner(x, y, rotate=0):
                c.saveState()
                c.translate(x, y)
                c.rotate(rotate)
                
                # Set color for decoration
                c.setStrokeColorRGB(0, 0.2, 0.4)
                c.setFillColorRGB(0, 0.2, 0.4)
                c.setLineWidth(1)
                
                # Draw Islamic-style corner decoration
                # Outer arc
                c.arc(0, 0, corner_size, 0, 90)
                
                # Inner details
                c.arc(5, 5, corner_size-5, 0, 90)
                
                # Small circle in corner
                c.circle(corner_size/2, corner_size/2, 3, fill=1)
                
                # Decorative lines
                c.line(0, corner_size/2, corner_size/2, corner_size/2)
                c.line(corner_size/2, 0, corner_size/2, corner_size/2)
                
                c.restoreState()
            
            # Draw the four corners
            draw_corner(margin, margin, 0)  # Bottom left
            draw_corner(width-margin, margin, 270)  # Bottom right
            draw_corner(margin, height-margin, 90)  # Top left
            draw_corner(width-margin, height-margin, 180)  # Top right
            
        except Exception as e:
            print(f"Error drawing corner decorations: {e}")

    def draw_prescription_footer(self, c):
        """Draw additional footer information on prescription if needed"""
        # Use a static variable to track if we've drawn the footer on the current page
        if not hasattr(self, '_current_page_footer_drawn'):
            self._current_page_footer_drawn = {}
        
        # Get the current page number
        current_page = c.getPageNumber()
        
        # If footer is already drawn for this page, skip
        if self._current_page_footer_drawn.get(current_page):
            return
            
        # Mark this page as having a footer
        self._current_page_footer_drawn[current_page] = True
        
        try:
            # Get page dimensions
            width, height = letter
            
            # Use consistent margin settings to match the outer border
            # The outer border is now drawn at margin = 10
            margin = 10
            
            # Calculate footer position to fit within the border with adequate spacing
            # Add slightly more space from bottom border
            footer_base_margin = margin + 20  # Increased from 10 to 20 to elevate the footer
            
            # Draw line above footer at an appropriate height
            c.setStrokeColorRGB(0.8, 0.8, 0.8)
            c.setLineWidth(0.5)
            # Position footer line to be at least 30 points from the border
            c.line(margin + 30, footer_base_margin + 30, width - margin - 30, footer_base_margin + 30)  # Increased from 25 to 30
            
            # Position clinic name with proper spacing from the border
            c.setFont('Helvetica-Bold', 10)
            c.setFillColorRGB(0, 0.2, 0.4)
            c.drawCentredString(width/2, footer_base_margin + 20, "Dr. Mahmoud Sami Ophthalmology Clinic")  # Increased from 15 to 20
            # Footer text with improved positioning
            if ARABIC_SUPPORT:
                try:
                    import arabic_reshaper
                    from bidi.algorithm import get_display
                    # Use proper font configuration
                    arabic_font_name = self.setup_pdf_arabic_font()
                    c.setFont(arabic_font_name, 9)
                    
                    # Arabic clinic name with adjusted positioning
                    clinic_ar = arabic_reshaper.reshape("١ برج الكوثر - الدور الرابع - العمرانية الهرم")
                    clinic_ar = get_display(clinic_ar)
                    c.drawCentredString(width/2, footer_base_margin + 5, clinic_ar)
                    
                    # Contact information with adjusted positioning
                    c.setFont('Helvetica', 8)
                    c.drawCentredString(width/2, footer_base_margin - 15, "Phone: 01005602267 | Email: ophthalmology@drmahmoudsami.com")
                    
                except Exception as e:
                    print(f"Error rendering Arabic footer: {e}")
                    c.setFont("Helvetica", 9)
                    c.drawCentredString(width/2, footer_base_margin, "Phone: 01005602267 | Email: ophthalmology@drmahmoudsami.com")
            else:
                # English-only version with adjusted positioning
                c.setFont("Helvetica", 8)
                c.drawCentredString(width/2, footer_base_margin - 15, "Phone: 01005602267 | Email: ophthalmology@drmahmoudsami.com")
        
        except Exception as e:
            print(f"Error drawing footer: {e}")
            import traceback
            traceback.print_exc()

    def initialize_database(self):
        """Initialize database tables"""
        try:
            cursor = self.conn.cursor()
            
            # Drop existing tables if they exist
            cursor.execute("DROP TABLE IF EXISTS medications")
            cursor.execute("DROP TABLE IF EXISTS investigations")
            
            # Create medications table
            cursor.execute('''
                CREATE TABLE medications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER,
                    type TEXT,
                    name TEXT,
                    dosage TEXT,
                    frequency TEXT,
                    duration TEXT,
                    tapering TEXT,
                    instructions TEXT,
                    notes TEXT,
                    date_prescribed TEXT,
                    FOREIGN KEY (patient_id) REFERENCES patients(id)
                )
            ''')
            
            # Create investigations table with all required columns
            cursor.execute('''
                CREATE TABLE investigations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER,
                    date DATE,
                    type TEXT,
                    details TEXT,
                    results TEXT,
                    recommendations TEXT,
                    FOREIGN KEY (patient_id) REFERENCES patients(id)
                )
            ''')
                
            # Create visits table to track patient visits
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER,
                    visit_date DATE,
                    reason TEXT,
                    notes TEXT,
                    FOREIGN KEY (patient_id) REFERENCES patients(id)
                )
            ''')
                
            self.conn.commit()
            print("Database initialized successfully")
            
        except Exception as e:
            print(f"Error initializing database: {e}")
            self.conn.rollback()

    def save_medication(self):
        """Save medication to database"""
        try:
            patient_id = self.med_patient_id.get().strip()
            if not patient_id:
                messagebox.showerror("Error", "Please select a patient first")
                return
            
            # Get all medications from the tree
            medications = []
            for item in self.medications_tree.get_children():
                values = self.medications_tree.item(item)['values']
                medications.append({
                    'type': values[0],
                    'name': values[1],
                    'dosage': values[2],
                    'frequency': values[3],
                    'duration': values[4],
                    'tapering': values[5] if len(values) > 5 else None,
                })
            
            if not medications:
                messagebox.showwarning("Warning", "No medications to save")
                return
            
            # Save to database
            cursor = self.conn.cursor()
            
            try:
                # Create medications table if it doesn't exist
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS medications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        patient_id INTEGER,
                        type TEXT,
                        name TEXT,
                        dosage TEXT,
                        frequency TEXT,
                        duration TEXT,
                        tapering TEXT,
                        instructions TEXT,
                        notes TEXT,
                        date_prescribed TEXT,
                        FOREIGN KEY (patient_id) REFERENCES patients(id)
                    )
                ''')
                
                current_date = datetime.now().strftime('%Y-%m-%d')
                
                # First, delete existing medications for this visit
                cursor.execute('''
                    DELETE FROM medications 
                    WHERE patient_id = ? AND date(date_prescribed) = ?
                ''', (patient_id, current_date))
                
                # Then insert new medications
                for med in medications:
                    cursor.execute('''
                        INSERT INTO medications 
                        (patient_id, type, name, dosage, frequency, duration, tapering, 
                         instructions, notes, date_prescribed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        patient_id,
                        med['type'],
                        med['name'],
                        med['dosage'],
                        med['frequency'],
                        med['duration'],
                        med['tapering'],
                        self.med_instructions.get("1.0", tk.END).strip(),
                        self.med_notes.get("1.0", tk.END).strip(),
                        current_date
                    ))
                
                self.conn.commit()
                messagebox.showinfo("Success", "Medications saved successfully")
                
            except sqlite3.Error as e:
                self.conn.rollback()
                raise Exception(f"Database error: {str(e)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save medications: {str(e)}")

    def create_qr_code(self, patient_id, patient_name, date, size=100):
        """Create QR code for prescription"""
        temp_dir = "temp"  # Define temp_dir at the start
        try:
            # Create QR code data
            qr_data = f"ID: {patient_id}\nName: {patient_name}\nDate: {date}"
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Create PIL image
            qr_image = qr.make_image(fill_color="black", back_color="white")
            
            # Resize to specified size
            qr_image = qr_image.resize((size, size), Image.Resampling.LANCZOS)
            
            # Create a temporary file path
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
                
            temp_file = os.path.join(temp_dir, f"qr_{patient_id}_{int(time.time())}.png")
            
            # Save the image
            qr_image.save(temp_file, format='PNG')
            
            return temp_file
            
        except Exception as e:
            print(f"Error creating QR code: {e}")
            return None
        
        finally:
            # Clean up old temporary files
            try:
                if os.path.exists(temp_dir):
                    current_time = time.time()
                    for f in os.listdir(temp_dir):
                        file_path = os.path.join(temp_dir, f)
                        if os.path.isfile(file_path) and current_time - os.path.getmtime(file_path) > 3600:
                            os.remove(file_path)
            except Exception as e:
                print(f"Error cleaning up temporary files: {e}")

    

    def print_prescription(self):
        """Print prescription details as PDF"""
        try:
            patient_id = self.rx_patient_id.get()
            if not patient_id:
                messagebox.showerror("Error", "Patient ID is required")
                return
                
            cursor = self.conn.cursor()
            cursor.execute('SELECT name, dob FROM patients WHERE id = ?', (patient_id,))
            patient_data = cursor.fetchone()
            
            if not patient_data:
                messagebox.showerror("Error", "Patient not found")
                return
        
            def process_arabic(text):
                """Handle Arabic text with proper reshaping and bidirectional support"""
                if not text or not ARABIC_SUPPORT:
                    return text
                try:
                    # Properly reshape and handle bidirectional text
                    reshaped_text = arabic_reshaper.reshape(text)
                    bidi_text = get_display(reshaped_text)
                    return bidi_text
                except Exception as e:
                    print(f"Arabic text processing error: {e}")
                    return text

            # Setup Arabic font
            try:
                # Try to find and register Amiri font
                font_paths = [
                    'Amiri-Regular.ttf',
                    '/Library/Fonts/Amiri-Regular.ttf',
                    '/usr/share/fonts/truetype/amiri/amiri-regular.ttf',
                    'C:/Windows/Fonts/Amiri-Regular.ttf'
                ]
                
                font_found = False
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        pdfmetrics.registerFont(TTFont('Arabic', font_path))
                        font_found = True
                        break
                            
                if not font_found:
                    # Download Amiri font if not found
                    import urllib.request
                    print("Downloading Amiri font...")
                    font_url = "https://github.com/alif-type/amiri/raw/master/fonts/ttf/Amiri-Regular.ttf"
                    urllib.request.urlretrieve(font_url, "Amiri-Regular.ttf")
                    pdfmetrics.registerFont(TTFont('Arabic', 'Amiri-Regular.ttf'))
                
                arabic_font = 'Arabic'
                print("Arabic font loaded successfully")
                
            except Exception as e:
                print(f"Font setup error: {e}")
                arabic_font = 'Helvetica'
                print("Using fallback font: Helvetica")

            # Create PDF
            filename = f"prescription_{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            c = canvas.Canvas(filename, pagesize=letter)
            
            # Add elegant border with maximum width
            c.setStrokeColorRGB(0.4, 0.4, 0.4)  # Dark gray
            c.setLineWidth(0.75)  # Slightly thicker outer border
            
            # Minimal margins to extend to page edges
            margin = 0.15*inch  # Reduced to minimum (was 0.3*inch)
            
            # Draw outer border
            c.rect(margin, margin, letter[0]-2*margin, letter[1]-2*margin)
            
            # Draw inner decorative border with minimal gap
            inner_margin = margin + 0.08*inch  # Minimal gap between borders
            c.setLineWidth(0.5)
            c.rect(inner_margin, inner_margin,
                   letter[0]-2*inner_margin, letter[1]-2*inner_margin)
            
            # Add corner decorations with adjusted size
            def draw_corner(x, y, rotate=0):
                c.saveState()
                c.translate(x, y)
                c.rotate(rotate)
                c.setLineWidth(0.5)
                c.line(0, 0, 0.3*inch, 0)  # Larger corner decorations
                c.line(0, 0, 0, 0.3*inch)
                c.restoreState()
            
            # Draw corners with minimal margin
            corner_margin = margin + 0.04*inch  # Minimal corner position
            draw_corner(corner_margin, corner_margin)  # Bottom left
            draw_corner(letter[0]-corner_margin, corner_margin, 90)  # Bottom right
            draw_corner(letter[0]-corner_margin, letter[1]-corner_margin, 180)  # Top right
            draw_corner(corner_margin, letter[1]-corner_margin, 270)  # Top left

            # Add QR code with consistent positioning
            # Removed duplicate QR code call
            
            # Adjust content margins for proper padding
            content_margin = inner_margin + 0.5*inch  # Increased content padding for better spacing  # Increased content padding

            # Header with proper Arabic text (adjusted positions)
            c.setFont(arabic_font, 24)
            c.setFillColorRGB(0.2, 0.2, 0.2)  # Dark gray text
            c.drawCentredString(letter[0]/2, 10.5*inch, "Dr Mahmoud Sami Clinic")
            header_arabic = process_arabic("عيادة د. محمود سامي")
            c.drawCentredString(letter[0]/2, 10.1*inch, header_arabic)
            
            # Remove the separator line
            # c.setLineWidth(0.5)
            # c.setStrokeColorRGB(0.7, 0.7, 0.7)
            # c.line(content_margin, 9.8*inch, letter[0]-content_margin, 9.8*inch)
            
            # Adjust spacing for address
            c.setFont(arabic_font, 14)
            c.setFillColorRGB(0.3, 0.3, 0.3)  # Medium gray text
            c.drawCentredString(letter[0]/2, 9.7*inch, "1 Alkawthar Tower - 4th floor, Omraneya Alharam")
            address_arabic = process_arabic("١ برج الكوثر - الدور الرابع - العمرانية الهرم")
            c.drawCentredString(letter[0]/2, 9.4*inch, address_arabic)
            
            # QR Code with website URL
            current_date = datetime.now().strftime('%Y-%m-%d')
            qr_code_path = self.create_qr_code(
                patient_id=patient_id,
                patient_name=patient_data[0], 
                date=current_date
            )

            # Add QR code image if file was created successfully
            if qr_code_path and os.path.exists(qr_code_path):
                try:
                    # Place QR code image on PDF - right top corner
                    qr_size = 1.0 * inch
                    right_margin = 0.75 * inch
                    top_margin = 0.75 * inch
                    c.drawImage(qr_code_path, 
                               letter[0] - qr_size - right_margin,  # X position from right
                               letter[1] - qr_size - top_margin,    # Y position from top
                               width=qr_size, 
                               height=qr_size)
                finally:
                    # Clean up temporary QR code file
                    try:
                        os.remove(qr_code_path)
                    except:
                        pass
            
            # Patient Information with improved styling
            c.setFillColorRGB(0.2, 0.2, 0.2)  # Dark gray text
            c.setFont("Helvetica-Bold", 12)
            c.drawString(1*inch, 8.9*inch, "Patient Information")
            c.setFont(arabic_font, 12)
            c.drawRightString(7*inch, 8.9*inch, process_arabic("معلومات المريض"))
            
            # Patient details with improved bilingual layout
            c.setFont("Helvetica", 11)
            details_y = 8.5*inch
            
            # Calculate the right alignment position for Arabic text (aligned under معلومات المريض)
            arabic_headline_width = c.stringWidth(process_arabic("معلومات المريض"), arabic_font, 12)
            arabic_right_position = 7*inch  # Same as the headline position
            
            # Adjust the position for patient data to avoid overlap
            patient_data_position = 3.0*inch  # Moved further right to avoid overlap with Arabic text
            
            # Name with fixed Arabic text
            c.drawString(1*inch, details_y, "Name:")
            c.setFont(arabic_font, 11)
            name_arabic = process_arabic("الاسم")
            c.drawRightString(arabic_right_position, details_y, name_arabic)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(patient_data_position, details_y, f"{patient_data[0]}")
            # ID
            c.setFont("Helvetica", 11)
            c.drawString(1*inch, details_y-0.3*inch, "ID:")
            c.setFont(arabic_font, 11)
            c.drawRightString(arabic_right_position, details_y-0.3*inch, process_arabic("رقم الملف"))
            c.setFont("Helvetica-Bold", 11)
            c.drawString(patient_data_position, details_y-0.3*inch, f"{patient_id}")
            
            # Date
            c.setFont("Helvetica", 11)
            c.drawString(1*inch, details_y-0.6*inch, "Date:")
            c.setFont(arabic_font, 11)
            c.drawRightString(arabic_right_position, details_y-0.6*inch, process_arabic("التاريخ"))
            c.setFont("Helvetica-Bold", 11)
            c.drawString(patient_data_position, details_y-0.6*inch, f"{datetime.now().strftime('%Y-%m-%d')}")
            # Add a separator line
            c.setLineWidth(0.5)
            c.setStrokeColorRGB(0.8, 0.8, 0.8)  # Light gray
            c.line(1*inch, details_y-0.8*inch, 7*inch, details_y-0.8*inch)
            
            # Prescription table
            y_pos = self.create_prescription_table(c, 7.0*inch)
            
            # Add Power with fixed Arabic text
            if self.add_power.get():
                c.setFont("Helvetica", 12)
                c.drawString(1*inch, y_pos - 0.7*inch, "Add Power:")
                c.setFont(arabic_font, 12)
                add_power_arabic = process_arabic("قوة الإضافة")
                c.drawRightString(arabic_right_position, y_pos - 0.7*inch, add_power_arabic)
                c.setFont("Helvetica-Bold", 12)
                c.drawString(patient_data_position, y_pos - 0.7*inch, f"{self.add_power.get()} D")
            
            # Notes
            notes = self.rx_notes.get("1.0", tk.END).strip()
            if notes:
                # Notes header
                c.setFont("Helvetica", 12)
                c.drawString(1*inch, y_pos - 1.5*inch, "Notes:")
                c.setFont(arabic_font, 12)
                notes_arabic = process_arabic("ملاحظات")
                c.drawRightString(arabic_right_position, y_pos - 1.5*inch, notes_arabic)
                
                # Notes content
                if any('\u0600' <= c <= '\u06FF' for c in notes):  # Check if contains Arabic
                    # Handle Arabic notes
                    c.setFont(arabic_font, 11)
                    notes_lines = textwrap.wrap(notes, width=50)
                    current_y = y_pos - 1.9*inch
                    for line in notes_lines:
                        processed_line = process_arabic(line)
                        c.drawRightString(6.5*inch, current_y, processed_line)
                        current_y -= 0.3*inch
                else:
                    # Handle non-Arabic notes
                    c.setFont("Helvetica", 11)
                    text = c.beginText(1.2*inch, y_pos - 1.9*inch)
                    for line in textwrap.fill(notes, width=70).split('\n'):
                        text.textLine(line)
                    c.drawText(text)
            
            # Footer
            c.setFont("Helvetica", 10)
            c.drawString(1*inch, 0.85*inch, "This prescription is valid for one year from the date of issue.")
            c.setFont(arabic_font, 10)
            c.drawRightString(arabic_right_position, 0.65*inch, process_arabic("هذه الوصفة صالحة لمدة عام من تاريخ الإصدار"))
            
            c.save()
            
            # Open PDF
            try:
                if os.name == 'nt':
                    os.startfile(filename)
                else:
                    os.system(f'open {filename}')
            except Exception as e:
                print(f"Error opening PDF: {e}")
                messagebox.showinfo("Success", f"Prescription saved as {filename}")
            
        except Exception as e:
            print(f"Error in print_prescription: {e}")
            messagebox.showerror("Error", f"An error occurred while printing prescription: {str(e)}")

    def print_investigation(self):
        """Print investigation report as PDF with Arabic support"""
        try:
            patient_id = self.inv_patient_id.get()
            if not patient_id:
                messagebox.showerror("Error", "Please select a patient first")
                return
                
            # Get patient information
            cursor = self.conn.cursor()
            cursor.execute('SELECT name, dob FROM patients WHERE id = ?', (patient_id,))
            patient_data = cursor.fetchone()
            
            if not patient_data:
                messagebox.showerror("Error", "Patient not found")
                return
                
            # Generate filename
            filename = f"investigation_{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            # Create PDF
            c = canvas.Canvas(filename, pagesize=letter)
            
            # Add content to PDF
            self.draw_prescription_border(c)
            
            # Add header
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(letter[0]/2, 10*inch, "Investigation Report")
            
            # Add patient info
            y_pos = self.draw_patient_info(c, patient_data, patient_id, 9*inch)
            
            # Add investigation details
            c.setFont("Helvetica-Bold", 12)
            c.drawString(1*inch, y_pos - 0.5*inch, "Investigation Type:")
            c.setFont("Helvetica", 11)
            c.drawString(1*inch, y_pos - 0.8*inch, self.inv_type.get())
            
            # Add details, results, and recommendations
            y_pos -= 1.2*inch
            
            def add_section(title, content, y):
                c.setFont("Helvetica-Bold", 12)
                c.drawString(1*inch, y, title)
                c.setFont("Helvetica", 11)
                wrapped = textwrap.wrap(content, width=80)
                for line in wrapped:
                    y -= 0.2*inch
                    c.drawString(1*inch, y, line)
                return y - 0.3*inch
            
            y_pos = add_section("Details:", self.inv_details.get("1.0", tk.END).strip(), y_pos)
            y_pos = add_section("Results:", self.inv_results.get("1.0", tk.END).strip(), y_pos)
            y_pos = add_section("Recommendations:", self.inv_recommendations.get("1.0", tk.END).strip(), y_pos)
            
            # Add QR code
            # Removed duplicate QR code call
            
            # Save and show PDF
            c.save()

            # Open the PDF
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(filename)
                else:  # macOS and Linux
                    os.system(f'open {filename}')
            except Exception as e:
                messagebox.showinfo("Success", f"Investigation report saved as {filename}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate investigation report: {str(e)}")

    def print_examination(self, patient_id):
        """Print examination details as PDF"""
        try:
            # Get patient information
            cursor = self.conn.cursor()
            cursor.execute('SELECT name, dob FROM patients WHERE id = ?', (patient_id,))
            patient_data = cursor.fetchone()
            
            if not patient_data:
                messagebox.showerror("Error", "Patient not found")
                return

            # Generate PDF filename
            filename = f"examination_{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            # Create PDF
            c = canvas.Canvas(filename, pagesize=letter)
            
            # Add QR code with consistent positioning
            # Removed duplicate QR code call
            
            # Constants for layout
            LEFT_MARGIN = 0.25 * inch
            RIGHT_MARGIN = letter[0] - (0.25 * inch)
            TOP_MARGIN = letter[1] - (0.25 * inch)
            LINE_GAP = 0.35 * inch
            
            # Add border
            c.setStrokeColorRGB(0.4, 0.4, 0.4)
            c.setLineWidth(0.75)
            border_margin = 0.125 * inch
            c.rect(border_margin, border_margin, 
                   letter[0] - 2*border_margin, 
                   letter[1] - 2*border_margin)
            
            # Header
            y_pos = TOP_MARGIN - inch
            c.setFont("Helvetica-Bold", 24)
            c.drawCentredString(letter[0]/2, y_pos, "Dr Mahmoud Sami Clinic")
            
            y_pos -= LINE_GAP
            c.setFont("Arabic", 24)
            header_ar = arabic_reshaper.reshape("عيادة د. محمود سامي")
            header_ar = get_display(header_ar)
            c.drawCentredString(letter[0]/2, y_pos, header_ar)
            
            # Patient Information
            y_pos -= LINE_GAP * 2
            c.setFont("Helvetica-Bold", 12)
            c.drawString(LEFT_MARGIN + 0.5*inch, y_pos, f"Patient: {patient_data[0]}")
            c.drawString(RIGHT_MARGIN - 2.5*inch, y_pos, f"ID: {patient_id}")
            
            # Get examination data
            cursor.execute('''
                SELECT * FROM examinations 
                WHERE patient_id = ? 
                ORDER BY date DESC LIMIT 1
            ''', (patient_id,))
            exam_data = cursor.fetchone()
            
            if exam_data:
                # Add examination details
                y_pos -= LINE_GAP * 2
                c.setFont("Helvetica-Bold", 14)
                c.drawString(LEFT_MARGIN + 0.5*inch, y_pos, "Examination Details")
                
                # Add your examination fields here
                # Example:
                y_pos -= LINE_GAP
                c.setFont("Helvetica", 12)
                c.drawString(LEFT_MARGIN + 0.5*inch, y_pos, f"Date: {exam_data[2]}")
                
                # Add more examination details as needed
                
            c.save()
            
            # Try to open the PDF
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(filename)
                else:  # macOS and Linux
                    subprocess.run(['open', filename], check=True)
            except:
                messagebox.showinfo("Success", f"Examination report saved as {filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate examination report: {str(e)}")

    def clear_investigation_form(self):
        """Clear all investigation form fields"""
        self.inv_type.set('')
        self.inv_details.delete("1.0", tk.END)
        self.inv_results.delete("1.0", tk.END)
        self.inv_recommendations.delete("1.0", tk.END)

    def translate_arabic_to_english(self, text):
        """Translate Arabic medical terms to English"""
        try:
            # Define the translation dictionary directly
            arabic_to_english = {
                'قطرة': 'Drop',
                'مرهم': 'Ointment',
                'حبوب': 'Tablets',
                'حقن': 'Injection',
                'كبسول': 'Capsule',
                'شراب': 'Syrup',
                # Add more translations as needed
                'مرات': 'times',
                'يوميا': 'daily',
                'اسبوع': 'week',
                'اسبوعين': '2 weeks',
                'شهر': 'month',
                'شهرين': '2 months',
                'ثلاث': 'three',
                'اربع': 'four',
                'خمس': 'five',
                'ست': 'six',
                'كل': 'every',
                'ساعات': 'hours',
                'مستمر': 'continuous',
                'عند': 'when',
                'الحاجة': 'needed',
                'قبل': 'before',
                'بعد': 'after',
                'الاكل': 'meals',
                'النوم': 'sleep',
                'صباحا': 'morning',
                'مساء': 'evening',
                'ليلا': 'night',
                'يمين': 'right',
                'يسار': 'left',
                'عين': 'eye',
                'عينين': 'eyes'
            }
            
            # If text is None or empty, return empty string
            if not text:
                return ""
                
            # Convert text to string if it isn't already
            text = str(text).strip()
            
            # If text is empty after stripping, return empty string
            if not text:
                return ""
                
            # Return translation if exists, otherwise return original text
            return arabic_to_english.get(text, text)
            
        except Exception as e:
            print(f"Translation error: {e}")
            return text  # Return original text if translation fails

    def search_patient_for_investigation(self):
        """Search for patients and update the investigation search tree"""
        try:
            # Get search query
            query = self.inv_search_entry.get().strip()
            
            # Clear current results
            for item in self.inv_search_tree.get_children():
                self.inv_search_tree.delete(item)
            
            if not query:
                return
                
            # Search database
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, name, dob 
                FROM patients 
                WHERE name LIKE ? OR id LIKE ?
            ''', (f'%{query}%', f'%{query}%'))
            
            # Add results to tree
            results = cursor.fetchall()
            for row in results:
                self.inv_search_tree.insert('', 'end', values=row)
                
            # Bind selection event
            def on_select(event):
                selected = self.inv_search_tree.selection()
                if not selected:
                    return
                    
                # Get selected patient data
                item = self.inv_search_tree.item(selected[0])
                patient_id, patient_name, patient_dob = item['values']
                
                # Update patient info fields
                self.inv_patient_id.set(str(patient_id))
                
            self.inv_search_tree.bind('<<TreeviewSelect>>', on_select)
            
            if not results:
                messagebox.showinfo("Search Results", "No matching patients found")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error searching for patients: {str(e)}")
    
    def translate_text(self, text, target_lang):
        """Translate text to target language using Google Translate API"""
        try:
            # Skip translation for empty text
            if not text or text.strip() == "":
                return text
                
            # Use a different translation method - the googletrans library has issues with async
            try:
                # First try with the deep_translator library which is more reliable
                from deep_translator import GoogleTranslator
                translator = GoogleTranslator(source='auto', target=target_lang)
                return translator.translate(text)
            except ImportError:
                # Fall back to TextBlob which is more reliable than googletrans
                try:
                    from textblob import TextBlob
                    blob = TextBlob(text)
                    # Some versions of TextBlob may not have translate method
                    # Check if translate method exists
                    if hasattr(blob, 'translate'):
                        return str(blob.translate(to=target_lang))
                    else:
                        # Use googletrans as a fallback if both deep_translator and TextBlob.translate are unavailable
                        try:
                            from googletrans import Translator
                            translator = Translator()
                            
                            # Fix for "coroutine 'Translator.translate' was never awaited" warning
                            # Check if the method returns a coroutine (newer versions of googletrans)
                            import asyncio
                            import inspect
                            
                            result = translator.translate(text, dest=target_lang)
                            if inspect.iscoroutine(result):
                                # If it's a coroutine, use asyncio to get the result
                                try:
                                    # Create a new event loop for this thread if needed
                                    try:
                                        loop = asyncio.get_event_loop()
                                    except RuntimeError:
                                        loop = asyncio.new_event_loop()
                                        asyncio.set_event_loop(loop)
                                    
                                    # Run the coroutine and get the result
                                    if loop.is_running():
                                        # If loop is already running, use run_coroutine_threadsafe
                                        future = asyncio.run_coroutine_threadsafe(result, loop)
                                        result = future.result(timeout=5)  # 5 seconds timeout
                                    else:
                                        # If loop is not running, use run_until_complete
                                        result = loop.run_until_complete(result)
                                except Exception as e:
                                    print(f"Async translation error: {e}")
                                    return text  # Return original on error
                            
                            # Extract text property if available
                            return result.text if hasattr(result, 'text') else str(result)
                        except Exception as e:
                            print(f"Googletrans error: {e}")
                            return text  # Return original if all translation methods fail
                except Exception as e:
                    print(f"TextBlob translation error: {e}")
                    return text  # Return original text if TextBlob fails
        except Exception as e:
            print(f"Translation error: {e}")
            return text  # Return original text if translation fails

    def connect_to_autorefractor(self, ip_address=None, port=None):
        """Connect to the Topcon RM-800 autorefractor over LAN"""
        if ip_address:
            self.autorefractor_ip = ip_address
        if port:
            self.autorefractor_port = port
            
        if not self.autorefractor_ip:
            # Show dialog to enter IP address if not provided
            self.show_autorefractor_connection_dialog()
            return
            
        try:
            # Create a socket connection to the autorefractor
            self.autorefractor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.autorefractor_socket.settimeout(5)  # 5 second timeout
            self.autorefractor_socket.connect((self.autorefractor_ip, self.autorefractor_port))
            self.autorefractor_connected = True
            
            # Update status indicator
            self.autorefractor_status.config(text=f"Autorefractor: Connected to {self.autorefractor_ip}", foreground="green")
            
            messagebox.showinfo("Connection Successful", f"Connected to autorefractor at {self.autorefractor_ip}:{self.autorefractor_port}")
        except Exception as e:
            self.autorefractor_connected = False
            
            # Update status indicator
            self.autorefractor_status.config(text="Autorefractor: Not Connected", foreground="red")
            
            messagebox.showerror("Connection Error", f"Failed to connect to autorefractor: {str(e)}")
            
    def disconnect_from_autorefractor(self):
        """Disconnect from the autorefractor device"""
        if self.autorefractor_socket:
            try:
                self.autorefractor_socket.close()
            except:
                pass
            finally:
                self.autorefractor_socket = None
                self.autorefractor_connected = False
                
                # Update status indicator
                self.autorefractor_status.config(text="Autorefractor: Not Connected", foreground="red")
                
                messagebox.showinfo("Disconnected", "Disconnected from autorefractor")
    def show_autorefractor_connection_dialog(self):
        """Show dialog to enter autorefractor IP address and port"""
        connection_dialog = tk.Toplevel(self.root)
        connection_dialog.title("Connect to Autorefractor")
        connection_dialog.geometry("300x150")
        connection_dialog.transient(self.root)
        connection_dialog.grab_set()
        
        ttk.Label(connection_dialog, text="IP Address:").grid(row=0, column=0, padx=5, pady=5)
        ip_entry = ttk.Entry(connection_dialog, width=15)
        ip_entry.grid(row=0, column=1, padx=5, pady=5)
        ip_entry.insert(0, self.autorefractor_ip or "192.168.1.100")  # Default IP
        
        ttk.Label(connection_dialog, text="Port:").grid(row=1, column=0, padx=5, pady=5)
        port_entry = ttk.Entry(connection_dialog, width=15)
        port_entry.grid(row=1, column=1, padx=5, pady=5)
        port_entry.insert(0, str(self.autorefractor_port))
        
        def on_connect():
            ip = ip_entry.get().strip()
            try:
                port = int(port_entry.get().strip())
                connection_dialog.destroy()
                self.connect_to_autorefractor(ip, port)
            except ValueError:
                messagebox.showerror("Invalid Port", "Please enter a valid port number")
                
        ttk.Button(connection_dialog, text="Connect", command=on_connect).grid(row=2, column=0, columnspan=2, pady=10)
        
    def import_autorefractor_data(self, patient_id=None):
        """Import autorefractor data for the selected patient"""
        if not patient_id:
            patient_id = self.exam_patient_id.get()
            
        if not patient_id:
            messagebox.showerror("Error", "Please select a patient first")
            return
            
        if not self.autorefractor_connected:
            # Try to connect if not already connected
            self.connect_to_autorefractor()
            if not self.autorefractor_connected:
                return
                
        try:
            # Show a loading message
            self.root.config(cursor="wait")
            self.root.update()
            
            if hasattr(self, 'connection_type') and self.connection_type == "rs232":
                # RS232 Serial connection
                try:
                    import serial
                    import time
                    
                    # Clear any pending data
                    self.serial_connection.reset_input_buffer()
                    
                    # Send request command for data (adjust based on Topcon RM-800 protocol)
                    command = f"GET,DATA,{patient_id}\r\n"
                    self.serial_connection.write(command.encode())
                    
                    # Read response with timeout
                    response = b""
                    start_time = time.time()
                    timeout = 10  # 10 seconds timeout
                    
                    while True:
                        if self.serial_connection.in_waiting > 0:
                            chunk = self.serial_connection.read(self.serial_connection.in_waiting)
                            response += chunk
                            
                            # Check if response is complete (adjust based on protocol)
                            if b'\r\n' in response:
                                break
                                
                        # Check timeout
                        if time.time() - start_time > timeout:
                            raise Exception("Timeout waiting for device response")
                            
                        # Small delay to prevent CPU hogging
                        time.sleep(0.1)
                    
                    # Parse response
                    lines = response.decode('ascii', errors='ignore').strip().split('\r\n')
                    data = {
                        "right_eye": {},
                        "left_eye": {}
                    }
                    
                    for line in lines:
                        if not line.strip():
                            continue
                        
                        fields = line.split(',')
                        
                        # Example parsing - adjust based on actual Topcon RM-800 output format
                        if len(fields) >= 5 and fields[0] == "R":  # Right eye data
                            data["right_eye"]["sph"] = fields[1].strip()
                            data["right_eye"]["cyl"] = fields[2].strip()
                            data["right_eye"]["axis"] = fields[3].strip()
                            data["right_eye"]["bcva"] = fields[4].strip()
                        elif len(fields) >= 5 and fields[0] == "L":  # Left eye data
                            data["left_eye"]["sph"] = fields[1].strip()
                            data["left_eye"]["cyl"] = fields[2].strip()
                            data["left_eye"]["axis"] = fields[3].strip()
                            data["left_eye"]["bcva"] = fields[4].strip()
                    
                    # Fill in the autorefraction fields
                    self.fill_autorefraction_data(data)
                    messagebox.showinfo("Success", "Autorefractor data imported successfully via RS232")
                
                except Exception as rs232_error:
                    raise Exception(f"RS232 error: {str(rs232_error)}")
            else:
                # LAN connection (default)
                # Send request for patient data
                request = {
                    "command": "get_patient_data",
                    "patient_id": patient_id
                }
                self.autorefractor_socket.sendall(json.dumps(request).encode())
                
                # Receive response
                response = b""
                while True:
                    chunk = self.autorefractor_socket.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    if len(chunk) < 4096:  # End of message
                        break
                        
                # Parse the response
                data = json.loads(response.decode())
                
                if data.get("status") == "success":
                    # Fill in the autorefraction fields
                    self.fill_autorefraction_data(data.get("data", {}))
                    messagebox.showinfo("Success", "Autorefractor data imported successfully via LAN")
                else:
                    messagebox.showerror("Error", f"Failed to import data: {data.get('message', 'Unknown error')}")
                    
        except Exception as e:
            messagebox.showerror("Error", f"Error importing autorefractor data: {str(e)}")
            self.autorefractor_connected = False
        finally:
            # Reset cursor
            self.root.config(cursor="")
            
    def check_autorefractor_connection(self):
        """Check if the autorefractor is still connected"""
        if not self.autorefractor_socket:
            self.autorefractor_connected = False
            return False
            
        try:
            # Try to send a ping to check connection
            self.autorefractor_socket.settimeout(2)
            request = {"command": "ping"}
            self.autorefractor_socket.sendall(json.dumps(request).encode())
            response = self.autorefractor_socket.recv(1024)
            
            if response:
                self.autorefractor_connected = True
                return True
            else:
                self.autorefractor_connected = False
                return False
        except:
            self.autorefractor_connected = False
            return False

    def fill_autorefraction_data(self, data):
        """Fill the autorefraction fields with the imported data"""
        try:
            # Right eye data
            right_eye = data.get("right_eye", {})
            self.auto_sph_right.delete(0, tk.END)
            self.auto_sph_right.insert(0, right_eye.get("sph", ""))
            
            self.auto_cyl_right.delete(0, tk.END)
            self.auto_cyl_right.insert(0, right_eye.get("cyl", ""))
            
            self.auto_axis_right.delete(0, tk.END)
            self.auto_axis_right.insert(0, right_eye.get("axis", ""))
            
            self.auto_bcva_right.delete(0, tk.END)
            self.auto_bcva_right.insert(0, right_eye.get("bcva", ""))
            
            # Left eye data
            left_eye = data.get("left_eye", {})
            self.auto_sph_left.delete(0, tk.END)
            self.auto_sph_left.insert(0, left_eye.get("sph", ""))
            
            self.auto_cyl_left.delete(0, tk.END)
            self.auto_cyl_left.insert(0, left_eye.get("cyl", ""))
            
            self.auto_axis_left.delete(0, tk.END)
            self.auto_axis_left.insert(0, left_eye.get("axis", ""))
            
            self.auto_bcva_left.delete(0, tk.END)
            self.auto_bcva_left.insert(0, left_eye.get("bcva", ""))
            
        except Exception as e:
            messagebox.showerror("Error", f"Error filling autorefraction data: {str(e)}")
        
    def simulate_autorefractor_server(self):
        """
        Simulate a Topcon RM-800 autorefractor server for testing purposes.
        This function starts a server in a separate thread that listens for connections
        and responds with simulated autorefractor data.
        """
        def server_thread():
            try:
                # Create a server socket
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(('localhost', 8080))
                server.listen(5)
                print("Simulated autorefractor server started on localhost:8080")
                
                while True:
                    # Accept client connections
                    client, addr = server.accept()
                    print(f"Connection from {addr}")
                    
                    # Receive data from client
                    data = client.recv(1024).decode()
                    request = json.loads(data)
                    
                    # Generate simulated response
                    if request.get("command") == "get_patient_data":
                        patient_id = request.get("patient_id")
                        
                        # Simulate random autorefractor data
                        import random
                        
                        # Generate realistic values
                        right_sph = round(random.uniform(-6.0, 2.0), 2)
                        right_cyl = round(random.uniform(-2.0, 0.0), 2)
                        right_axis = random.randint(1, 180)
                        right_bcva = random.choice(["20/20", "20/25", "20/30", "20/40"])
                        
                        left_sph = round(random.uniform(-6.0, 2.0), 2)
                        left_cyl = round(random.uniform(-2.0, 0.0), 2)
                        left_axis = random.randint(1, 180)
                        left_bcva = random.choice(["20/20", "20/25", "20/30", "20/40"])
                        
                        response = {
                            "status": "success",
                            "data": {
                                "patient_id": patient_id,
                                "timestamp": datetime.now().isoformat(),
                                "device": "Topcon RM-800",
                                "right_eye": {
                                    "sph": f"{right_sph:+.2f}",
                                    "cyl": f"{right_cyl:.2f}",
                                    "axis": f"{right_axis}",
                                    "bcva": right_bcva
                                },
                                "left_eye": {
                                    "sph": f"{left_sph:+.2f}",
                                    "cyl": f"{left_cyl:.2f}",
                                    "axis": f"{left_axis}",
                                    "bcva": left_bcva
                                }
                            }
                        }
                    elif request.get("command") == "ping":
                        # Respond to ping requests
                        response = {
                            "status": "success",
                            "message": "pong"
                        }
                    else:
                        response = {
                            "status": "error",
                            "message": "Unknown command"
                        }
                    
                    # Send response back to client
                    client.sendall(json.dumps(response).encode())
                    client.close()
                    
            except Exception as e:
                print(f"Simulated server error: {str(e)}")
            finally:
                if 'server' in locals():
                    server.close()
                    
        # Start the server in a separate thread
        threading.Thread(target=server_thread, daemon=True).start()
        messagebox.showinfo("Simulator", "Autorefractor simulator started on localhost:8080")
        
        # Auto-connect to the simulator
        self.connect_to_autorefractor("localhost", 8080)

    def create_arabic_styles(self, base_font_name):
        """Create enhanced paragraph styles for Arabic and mixed-language content"""
        try:
            styles = getSampleStyleSheet()
            
            # Set fallback font if none provided
            if not base_font_name:
                base_font_name = 'Helvetica'
            
            # Register the fallback font if it's not already registered
            try:
                pdfmetrics.getFont(base_font_name)
            except:
                try:
                    pdfmetrics.getFont('Helvetica')
                    base_font_name = 'Helvetica'
                except:
                    # Last resort - use the default font
                    base_font_name = styles['Normal'].fontName
                    
            # Create Arabic style - with strong right-to-left alignment
            arabic_style = ParagraphStyle(
                'Arabic',
                parent=styles['Normal'],
                fontName=base_font_name,
                fontSize=12,
                leading=14,
                firstLineIndent=0,
                alignment=TA_RIGHT,  # Right alignment for Arabic
                rightIndent=0,
                leftIndent=0,
                spaceAfter=10,
                spaceBefore=10,
                wordWrap='RTL',  # Explicitly set RTL word wrapping for all Arabic text
                borderWidth=0,
                textColor=colors.black,
            )
            
            # Create Arabic RTL style - strongly right-to-left for Arabic-dominant text
            arabic_rtl_style = ParagraphStyle(
                'ArabicRTL',
                parent=arabic_style,
                alignment=TA_RIGHT,
                rightIndent=0,
                leftIndent=0,  # No left indent to give more space for RTL text
                bulletIndent=10,
                wordWrap='RTL',  # Explicitly set RTL word wrapping
            )
            
            # Create English style
            english_style = ParagraphStyle(
                'English',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=12,
                leading=14,
                alignment=TA_LEFT,
                spaceAfter=10,
                spaceBefore=10,
            )
            
            # Create bilingual style for mixed content with better RTL support
            bilingual_style = ParagraphStyle(
                'Bilingual',
                parent=styles['Normal'],
                fontName=base_font_name,
                fontSize=12,
                leading=16,
                firstLineIndent=0,
                alignment=TA_RIGHT,  # Changed to right alignment for better mixed content display
                bulletFontName=base_font_name,
                wordWrap='RTL',  # Better wrapping for mixed scripts with RTL preference
                spaceAfter=5,
                spaceBefore=5,
            )
            
            # Create bilingual heading style
            bilingual_heading_style = ParagraphStyle(
                'BilingualHeading',
                parent=bilingual_style,
                fontSize=16,
                leading=20,
                alignment=TA_CENTER,  # Center alignment for headings
                fontName=base_font_name,
                textColor=colors.black,
                spaceAfter=15,
                spaceBefore=15,
                borderWidth=0,
                borderColor=colors.black,
                borderPadding=5,
                borderRadius=2,
            )
            
            # Create compact Arabic style for tables
            arabic_table_style = ParagraphStyle(
                'ArabicTable',
                parent=arabic_style,
                fontSize=10,
                leading=12,
                spaceAfter=2,
                spaceBefore=2,
                wordWrap='RTL',  # Ensure RTL wrapping in tables
            )
            
            # Create compact English style for tables
            english_table_style = ParagraphStyle(
                'EnglishTable',
                parent=english_style,
                fontSize=10,
                leading=12,
                spaceAfter=2,
                spaceBefore=2,
            )
            
            # Return the collection of styles
            return {
                'Arabic': arabic_style,
                'ArabicRTL': arabic_rtl_style,
                'English': english_style,
                'Bilingual': bilingual_style,
                'BilingualHeading': bilingual_heading_style,
                'ArabicTable': arabic_table_style,
                'EnglishTable': english_table_style,
            }
        
        except Exception as e:
            print(f"Error creating Arabic styles: {e}")
            # Return basic styles as fallback
            styles = getSampleStyleSheet()
            return {
                'Arabic': styles['Normal'],
                'ArabicRTL': styles['Normal'],
                'English': styles['Normal'],
                'Bilingual': styles['Normal'],
                'BilingualHeading': styles['Heading1'],
                'ArabicTable': styles['Normal'],
                'EnglishTable': styles['Normal'],
            }

    def show_about_dialog(self):
        """Display application information and copyright"""
        about_window = tk.Toplevel(self.root)
        about_window.title("About Ophthalmology EMR")
        about_window.geometry("450x300")
        about_window.resizable(False, False)
        about_window.transient(self.root)
        about_window.grab_set()
        
        # Center the window
        about_window.update_idletasks()
        width = about_window.winfo_width()
        height = about_window.winfo_height()
        x = (about_window.winfo_screenwidth() // 2) - (width // 2)
        y = (about_window.winfo_screenheight() // 2) - (height // 2)
        about_window.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
        # Frame for content
        content_frame = ttk.Frame(about_window, padding=20)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # App name
        ttk.Label(
            content_frame, 
            text="Ophthalmology EMR System",
            font=('Arial', 16, 'bold')
        ).pack(pady=(0, 10))
        
        # Version
        ttk.Label(
            content_frame,
            text="Version 1.0",
            font=('Arial', 10)
        ).pack(pady=(0, 20))
        
        # Copyright info
        ttk.Label(
            content_frame,
            text=f"© {datetime.now().year} Designed by Dr Mahmoud Sami",
            font=('Arial', 10)
        ).pack(pady=(0, 5))
        
        ttk.Label(
            content_frame,
            text="All Rights Reserved",
            font=('Arial', 10)
        ).pack(pady=(0, 20))
        
        # Description
        description_text = "Advanced Electronic Medical Record System for Ophthalmology Practice"
        ttk.Label(
            content_frame,
            text=description_text,
            font=('Arial', 9),
            foreground='#555555',
            wraplength=400,
            justify=tk.CENTER
        ).pack(pady=(0, 20))
        
        # Close button
        ttk.Button(
            content_frame,
            text="Close",
            command=about_window.destroy
        ).pack(pady=(10, 0))

    def convert_to_arabic_numerals(self, text):
        """Convert English digits in a string to Arabic digits"""
        # Dictionary mapping English digits to Arabic digits
        digit_map = {
            '0': '٠',
            '1': '١',
            '2': '٢',
            '3': '٣',
            '4': '٤',
            '5': '٥',
            '6': '٦',
            '7': '٧',
            '8': '٨',
            '9': '٩'
        }
        
        # Replace each English digit with its Arabic counterpart
        for english, arabic in digit_map.items():
            text = text.replace(english, arabic)
        
        return text
        
    def convert_to_arabic_numerals_pdf(self, text, vertical_offset=-1):
        """Convert English digits in a string to Arabic digits with vertical alignment adjustment for PDF rendering
        
        Args:
            text (str): The text containing digits to convert
            vertical_offset (int): Vertical pixel adjustment for better alignment, default is -1
                                  (negative values move text up, positive move down)
        """
        # Dictionary mapping English digits to Arabic digits
        digit_map = {
            '0': '٠',
            '1': '١',
            '2': '٢',
            '3': '٣',
            '4': '٤',
            '5': '٥',
            '6': '٦',
            '7': '٧',
            '8': '٨',
            '9': '٩'
        }
        
        result = ""
        has_arabic_digits = False
        
        # Process each character, marking if we encounter Arabic digits
        for char in text:
            if char in digit_map:
                result += digit_map[char]
                has_arabic_digits = True
            else:
                result += char
        
        # Always return a tuple with text and vertical offset
        return (result, vertical_offset)
        
        
    def generate_tapering_schedule(self):
        """Generate a steroid tapering schedule based on user inputs"""
        try:
            # Clear existing items in the schedule tree
            for item in self.schedule_tree.get_children():
                self.schedule_tree.delete(item)
            
            # Get values from form
            try:
                initial_dose = float(self.initial_dose.get())
                num_steps = int(self.tapering_steps.get())
                days_per_step = int(self.step_interval.get())
                reduction_method = self.reduction_method.get()
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers for initial dose, steps, and interval")
                return
            
            # Get current date as starting point
            start_date = datetime.now().date()
            
            # Create schedule based on reduction method
            schedule = []
            current_date = start_date
            
            # Add initial dose (day 0)
            schedule.append({
                'day': 0,
                'date': current_date.strftime('%Y-%m-%d'),
                'dose': f"{initial_dose:.1f}",
                'frequency': self.med_frequency.get(),
                'instructions': "Starting dose"
            })
            
            # Add to tree view
            self.schedule_tree.insert('', 'end', values=(
                f"Day 0",
                current_date.strftime('%Y-%m-%d'),
                f"{initial_dose:.1f}",
                self.med_frequency.get(),
                "Starting dose"
            ))
            
            # Calculate doses for each step
            for step in range(1, num_steps + 1):
                # Update date for this step
                current_date = start_date + timedelta(days=step * days_per_step)
                
                # Calculate dose based on reduction method
                if reduction_method == "Linear Reduction":
                    # Simple linear taper
                    reduction_per_step = initial_dose / (num_steps + 1)
                    dose = max(0, initial_dose - (step * reduction_per_step))
                elif reduction_method == "Percentage Reduction":
                    # Reduce by 25% each step
                    dose = initial_dose * (0.75 ** step)
                else:  # "Fixed Step Reduction"
                    # Reduce by fixed amounts based on initial dose
                    if initial_dose > 60:
                        fixed_step = 10  # Reduce by 10 units each step
                    elif initial_dose > 30:
                        fixed_step = 5   # Reduce by 5 units each step
                    else:
                        fixed_step = 2.5 # Reduce by 2.5 units each step
                    dose = max(0, initial_dose - (step * fixed_step))
                
                # Round to 1 decimal place for readability
                dose = round(dose, 1)
                
                # Create instructions
                if dose <= 0:
                    instructions = "Discontinue medication"
                    dose = 0
                else:
                    instructions = f"Reduced dose (Step {step})"
                
                # Add to schedule
                day_num = step * days_per_step
                schedule.append({
                    'day': day_num,
                    'date': current_date.strftime('%Y-%m-%d'),
                    'dose': f"{dose:.1f}",
                    'frequency': self.med_frequency.get(),
                    'instructions': instructions
                })
                
                # Add to tree view
                self.schedule_tree.insert('', 'end', values=(
                    f"Day {day_num}",
                    current_date.strftime('%Y-%m-%d'),
                    f"{dose:.1f}",
                    self.med_frequency.get(),
                    instructions
                ))
            
            # Store schedule for later use in prescription
            self.tapering_schedule = schedule
            
            # Update instructions field with summarized schedule
            instructions_text = "TAPERING SCHEDULE:\n"
            for item in schedule:
                instructions_text += f"• {item['date']}: {item['dose']} {self.med_frequency.get()}\n"
            
            # Update the instructions text field
            self.med_instructions.delete("1.0", tk.END)
            self.med_instructions.insert("1.0", instructions_text)
            
            messagebox.showinfo("Success", "Tapering schedule generated successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate schedule: {str(e)}")
            import traceback
            traceback.print_exc()

    def add_tapering_step(self):
        """Add a new tapering step to the form"""
        step_frame = ttk.Frame(self.tapering_steps_frame)
        step_frame.pack(fill='x', pady=2)
        
        # Common frequencies for tapering
        common_frequencies = [
            "TID (3 times daily)", 
            "BID (2 times daily)", 
            "Daily", 
            "Every other day",
            "Twice weekly",
            "Once weekly"
        ]
        
        # Common durations for tapering
        common_durations = [
            "1 week", "2 weeks", "3 days", "5 days", "7 days"
        ]
        
        freq = ttk.Combobox(step_frame, values=common_frequencies, width=20)
        freq.insert(0, "Frequency")
        freq.pack(side=tk.LEFT, padx=5)
        
        duration = ttk.Combobox(step_frame, values=common_durations, width=20)
        duration.insert(0, "Duration")
        duration.pack(side=tk.LEFT, padx=5)
        
        # Add to list of entries
        self.tapering_entries.append((freq, duration))

    def remove_tapering_step(self):
        """Remove the last tapering step from the form"""
        if len(self.tapering_entries) > 1:  # Keep at least one step
            # Get the last entry pair
            freq, duration = self.tapering_entries.pop()
            # Destroy the parent frame containing both widgets
            freq.master.destroy()

    def load_recent_patients(self):
        """Load recent patients into the recent patients tab"""
        try:
            # Clear existing entries
            for item in self.recent_patients_tree.get_children():
                self.recent_patients_tree.delete(item)
            
            # Query for recent patients (last 10 visits)
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT p.id, p.name, MAX(v.visit_date) as last_visit 
                FROM patients p
                LEFT JOIN visits v ON p.id = v.patient_id
                GROUP BY p.id
                ORDER BY last_visit DESC
                LIMIT 10
            ''')
            
            patients = cursor.fetchall()
            
            # Add to treeview
            for patient in patients:
                self.recent_patients_tree.insert('', 'end', values=patient)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load recent patients: {str(e)}")

    def on_recent_patient_selected(self, event):
        """Handle selection from recent patients list"""
        try:
            selected = self.recent_patients_tree.selection()
            if not selected:
                return
                
            # Get patient data
            values = self.recent_patients_tree.item(selected[0])['values']
            patient_id = values[0]
            patient_name = values[1]
            
            # Set patient info
            self.med_patient_id.configure(state='normal')
            self.med_patient_id.delete(0, tk.END)
            self.med_patient_id.insert(0, patient_id)
            self.med_patient_id.configure(state='readonly')
            
            self.med_patient_name.configure(state='normal')
            self.med_patient_name.delete(0, tk.END)
            self.med_patient_name.insert(0, patient_name)
            self.med_patient_name.configure(state='readonly')
            
            # Calculate and set age
            cursor = self.conn.cursor()
            cursor.execute('SELECT date_of_birth FROM patients WHERE id = ?', (patient_id,))
            dob_result = cursor.fetchone()
            
            if dob_result and dob_result[0]:
                try:
                    dob = datetime.strptime(dob_result[0], '%Y-%m-%d')
                    today = datetime.today()
                    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                    
                    self.med_patient_age.configure(state='normal')
                    self.med_patient_age.delete(0, tk.END)
                    self.med_patient_age.insert(0, str(age))
                    self.med_patient_age.configure(state='readonly')
                except:
                    self.med_patient_age.configure(state='normal')
                    self.med_patient_age.delete(0, tk.END)
                    self.med_patient_age.configure(state='readonly')
            
        except Exception as e:
            messagebox.showerror("Error", f"Error selecting recent patient: {str(e)}")

    def on_medication_patient_selected(self, event):
        """Handle patient selection from search results"""
        try:
            selected = self.med_search_tree.selection()
            if not selected:
                return
                
            # Get patient data from the selected item
            item = self.med_search_tree.item(selected[0])
            values = item['values']
            
            if not values:
                return
                
            patient_id = values[0]
            patient_name = values[1]
            
            # Update patient info fields
            self.med_patient_id.configure(state='normal')
            self.med_patient_id.delete(0, tk.END)
            self.med_patient_id.insert(0, patient_id)
            self.med_patient_id.configure(state='readonly')
            
            self.med_patient_name.configure(state='normal')
            self.med_patient_name.delete(0, tk.END)
            self.med_patient_name.insert(0, patient_name)
            self.med_patient_name.configure(state='readonly')
            
            # Calculate and set age
            cursor = self.conn.cursor()
            cursor.execute('SELECT date_of_birth FROM patients WHERE id = ?', (patient_id,))
            dob_result = cursor.fetchone()
            
            if dob_result and dob_result[0]:
                try:
                    dob = datetime.strptime(dob_result[0], '%Y-%m-%d')
                    today = datetime.today()
                    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                    
                    self.med_patient_age.configure(state='normal')
                    self.med_patient_age.delete(0, tk.END)
                    self.med_patient_age.insert(0, str(age))
                    self.med_patient_age.configure(state='readonly')
                except:
                    self.med_patient_age.configure(state='normal')
                    self.med_patient_age.delete(0, tk.END)
                    self.med_patient_age.configure(state='readonly')
            
        except Exception as e:
            messagebox.showerror("Error", f"Error selecting patient: {str(e)}")

    def clear_medication_patient(self):
        """Clear the selected patient"""
        self.med_patient_id.configure(state='normal')
        self.med_patient_id.delete(0, tk.END)
        self.med_patient_id.configure(state='readonly')
        
        self.med_patient_name.configure(state='normal')
        self.med_patient_name.delete(0, tk.END)
        self.med_patient_name.configure(state='readonly')
        
        self.med_patient_age.configure(state='normal')
        self.med_patient_age.delete(0, tk.END)
        self.med_patient_age.configure(state='readonly')

    def edit_selected_medication(self):
        """Load selected medication for editing"""
        try:
            selected = self.medications_tree.selection()
            if not selected:
                messagebox.showinfo("Info", "Please select a medication to edit")
                return
                
            # Get selected medication data
            values = self.medications_tree.item(selected[0])['values']
            
            # Clear current fields
            self.clear_medication_fields()
            
            # Fill form with selected medication data
            self.med_type.set(values[0])
            self.med_name.insert(0, values[1])
            self.med_dosage.insert(0, values[2])
            self.med_frequency.insert(0, values[3])
            self.med_duration.insert(0, values[4])
            
            # Handle tapering schedule if present
            if len(values) > 5 and values[5]:
                self.is_steroid.set(True)
                self.toggle_tapering_schedule()
                
                # Parse tapering steps and fill the fields
                steps = values[5].split(" → ")
                
                # Clear existing steps except the first one
                while len(self.tapering_entries) > 1:
                    self.remove_tapering_step()
                    
                # Add steps as needed
                while len(self.tapering_entries) < len(steps):
                    self.add_tapering_step()
                    
                # Fill in the step data
                for i, step in enumerate(steps):
                    if i < len(self.tapering_entries):
                        freq, duration = self.tapering_entries[i]
                        
                        # Parse the step text "Frequency for Duration"
                        parts = step.split(" for ")
                        if len(parts) == 2:
                            freq_text, duration_text = parts
                            
                            freq.delete(0, tk.END)
                            freq.insert(0, freq_text)
                            
                            duration.delete(0, tk.END)
                            duration.insert(0, duration_text)
        
            # Remove the selected item (will be added back when user clicks Add Medication)
            self.medications_tree.delete(selected)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error editing medication: {str(e)}")

    def clear_all_medications(self):
        """Clear all medications from the list"""
        if messagebox.askyesno("Confirm", "Are you sure you want to clear all medications?"):
            for item in self.medications_tree.get_children():
                self.medications_tree.delete(item)

    def search_patient_for_medication(self):
        """Enhanced search for a patient to assign medication"""
        try:
            # Get search query and type
            search_term = self.med_search_entry.get().strip()
            search_type = self.med_search_type.get()
            
            if not search_term:
                messagebox.showinfo("Search", "Please enter a search term")
                return
                
            # Clear current results
            for item in self.med_search_tree.get_children():
                self.med_search_tree.delete(item)
            
            # Build query based on search type
            cursor = self.conn.cursor()
            
            if search_type == "Name":
                cursor.execute('''
                    SELECT id, name, date_of_birth FROM patients 
                    WHERE name LIKE ?
                    ORDER BY name
                ''', (f'%{search_term}%',))
            elif search_type == "ID":
                cursor.execute('''
                    SELECT id, name, date_of_birth FROM patients 
                    WHERE id LIKE ?
                    ORDER BY id
                ''', (f'%{search_term}%',))
            elif search_type == "Phone":
                cursor.execute('''
                    SELECT id, name, date_of_birth FROM patients 
                    WHERE phone LIKE ?
                    ORDER BY name
                ''', (f'%{search_term}%',))
            else:
                # Default to searching all fields
                cursor.execute('''
                    SELECT id, name, date_of_birth FROM patients 
                    WHERE name LIKE ? OR id LIKE ? OR phone LIKE ?
                    ORDER BY name
                ''', (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
            
            results = cursor.fetchall()
            
            # Populate treeview with results
            for row in results:
                # Format date of birth if it exists
                dob = row[2] if len(row) > 2 and row[2] else "N/A"
                self.med_search_tree.insert('', 'end', values=(row[0], row[1], dob))
            
            if not results:
                messagebox.showinfo("Search Results", "No matching patients found")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error searching for patients: {str(e)}")

    def setup_secretary_tab(self):
        """Sets up the Secretary/Appointments tab interface."""
        # Main container frame for the secretary tab
        main_frame = ttk.Frame(self.secretary_tab, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Configure main layout columns/rows ---
        # Column 0: Patient selection, Date, Appointments List (weight 1)
        # Column 1: Appointment Details Form, Buttons (weight 1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        # Row 0: Patient Sel (L), Details Form (R)
        # Row 1: Date Sel (L), Buttons (R)
        # Row 2: Appt List (L, expands), Empty (R)
        main_frame.grid_rowconfigure(0, weight=0) # Patient/Details row
        main_frame.grid_rowconfigure(1, weight=0) # Date/Buttons row
        main_frame.grid_rowconfigure(2, weight=1) # Appt List row (allow vertical expansion)

        # --- Left Column Frame ---
        # This frame will hold Patient Selection, Date, and Appointment List
        left_frame = ttk.Frame(main_frame)
        # Place left_frame in grid, spanning relevant rows
        left_frame.grid(row=0, column=0, rowspan=3, sticky='nsew', padx=(0, 10))
        # Configure rows within left_frame
        left_frame.grid_rowconfigure(0, weight=0) # Patient selection
        left_frame.grid_rowconfigure(1, weight=0) # Date selection
        left_frame.grid_rowconfigure(2, weight=1) # Appointment list (expand)
        left_frame.grid_columnconfigure(0, weight=1) # Allow content to fill width

        # 1. Patient Selection Frame (inside left_frame)
        sec_patient_frame = ttk.LabelFrame(left_frame, text="Select Patient", padding="5")
        sec_patient_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        sec_patient_frame.grid_columnconfigure(1, weight=1) # Allow search entry to expand

        # Search widgets
        ttk.Label(sec_patient_frame, text="Search:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.sec_search_entry = ttk.Entry(sec_patient_frame)
        self.sec_search_entry.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.sec_search_entry.bind("<Return>", self.search_patient_for_secretary) # Bind Enter
        ttk.Button(sec_patient_frame, text="Search",
                   command=self.search_patient_for_secretary).grid(row=0, column=2, padx=5, pady=5)

        # Import Button <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< NEW
        ttk.Button(sec_patient_frame, text="Import Patients...",
                   command=self.import_external_patients).grid(row=0, column=3, padx=10, pady=5)

        # Selected patient info (Readonly)
        ttk.Label(sec_patient_frame, text="Selected ID:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.sec_patient_id_var = tk.StringVar()
        sec_id_entry = ttk.Entry(sec_patient_frame, textvariable=self.sec_patient_id_var,
                                 state='readonly', width=10)
        sec_id_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        ttk.Label(sec_patient_frame, text="Name:").grid(row=1, column=2, padx=(10, 5), pady=5, sticky='w')
        self.sec_patient_name_var = tk.StringVar()
        sec_name_entry = ttk.Entry(sec_patient_frame, textvariable=self.sec_patient_name_var,
                                   state='readonly', width=25)
        # Span name entry across columns 3 and 4 if needed, or adjust import button position
        sec_name_entry.grid(row=1, column=3, columnspan=1, padx=5, pady=5, sticky='ew') # Adjusted columnspan
        sec_patient_frame.grid_columnconfigure(3, weight=1) # Allow name field to expand


        # 2. Date Selection Frame (inside left_frame)
        date_frame = ttk.Frame(left_frame)
        date_frame.grid(row=1, column=0, sticky='ew', pady=(0, 10)) # Row 1 in left_frame
        ttk.Label(date_frame, text="Appointment Date:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 5))

        if HAS_TKCALENDAR:
            self.sec_date_entry = DateEntry(date_frame, width=12, date_pattern='yyyy-mm-dd',
                                            command=self.load_appointments) # Load on date change
            self.sec_date_entry.pack(side=tk.LEFT, padx=5)
            self.sec_date_entry.set_date(datetime.now().date())
        else:
            self.sec_date_entry = ttk.Entry(date_frame, width=15)
            self.sec_date_entry.pack(side=tk.LEFT, padx=5)
            self.sec_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
            ttk.Button(date_frame, text="Load Date", command=self.load_appointments).pack(side=tk.LEFT, padx=5)


        # 3. Appointments List Frame (inside left_frame)
        appt_list_frame = ttk.LabelFrame(left_frame, text="Appointments for Selected Date", padding="5")
        appt_list_frame.grid(row=2, column=0, sticky='nsew') # Row 2 in left_frame, expands
        appt_list_frame.grid_rowconfigure(0, weight=1)
        appt_list_frame.grid_columnconfigure(0, weight=1)

        # Treeview for Appointments (inside appt_list_frame)
        sec_tree_frame = ttk.Frame(appt_list_frame)
        sec_tree_frame.grid(row=0, column=0, sticky='nsew')
        sec_tree_frame.grid_rowconfigure(0, weight=1)
        sec_tree_frame.grid_columnconfigure(0, weight=1)

        sec_vsb = ttk.Scrollbar(sec_tree_frame, orient="vertical")
        sec_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        sec_hsb = ttk.Scrollbar(sec_tree_frame, orient="horizontal")
        sec_hsb.pack(side=tk.BOTTOM, fill=tk.X)

        self.sec_appointment_tree = ttk.Treeview(sec_tree_frame, columns=(
            'Appt ID', 'Time', 'Patient Name', 'Reason', 'Status'
        ), show='headings', selectmode='browse',
            yscrollcommand=sec_vsb.set, xscrollcommand=sec_hsb.set)

        sec_vsb.config(command=self.sec_appointment_tree.yview)
        sec_hsb.config(command=self.sec_appointment_tree.xview)

        # Define headings and columns (no change here)
        self.sec_appointment_tree.heading('Appt ID', text='ID')
        self.sec_appointment_tree.heading('Time', text='Time')
        self.sec_appointment_tree.heading('Patient Name', text='Patient Name')
        self.sec_appointment_tree.heading('Reason', text='Reason')
        self.sec_appointment_tree.heading('Status', text='Status')
        self.sec_appointment_tree.column('Appt ID', width=40, minwidth=30, anchor=tk.W)
        self.sec_appointment_tree.column('Time', width=60, minwidth=50, anchor=tk.W)
        self.sec_appointment_tree.column('Patient Name', width=150, minwidth=120, anchor=tk.W)
        self.sec_appointment_tree.column('Reason', width=150, minwidth=100, anchor=tk.W)
        self.sec_appointment_tree.column('Status', width=80, minwidth=70, anchor=tk.W)

        self.sec_appointment_tree.pack(fill='both', expand=True)
        self.sec_appointment_tree.bind('<<TreeviewSelect>>', self.on_appointment_select)
        self.sec_appointment_tree.tag_configure('oddrow', background='#f0f0f0')
        self.sec_appointment_tree.tag_configure('evenrow', background='#ffffff')


        # --- Right Column Frames ---
        # Frame for Appointment Details Form (inside main_frame)
        details_frame = ttk.LabelFrame(main_frame, text="Appointment Details", padding="10")
        details_frame.grid(row=0, column=1, sticky='nsew', pady=(0,5)) # Top right, row 0
        details_frame.grid_columnconfigure(1, weight=1) # Allow widgets to expand horizontally

        # Frame for Buttons (inside main_frame)
        sec_button_frame = ttk.Frame(main_frame)
        sec_button_frame.grid(row=1, column=1, sticky='ew', padx=5, pady=5) # Row 1, below details

        # --- Widgets inside Appointment Details Form (details_frame) ---
        ttk.Label(details_frame, text="Time (HH:MM):").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.sec_time_entry = ttk.Entry(details_frame, width=10)
        self.sec_time_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')

        ttk.Label(details_frame, text="Reason:").grid(row=1, column=0, padx=5, pady=5, sticky='ne')
        self.sec_reason_text = tk.Text(details_frame, height=3, width=40, wrap=tk.WORD)
        self.sec_reason_text.grid(row=1, column=1, columnspan=2, sticky='ew', padx=5, pady=5)
        sec_reason_scroll = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.sec_reason_text.yview)
        sec_reason_scroll.grid(row=1, column=3, sticky='ns')
        self.sec_reason_text['yscrollcommand'] = sec_reason_scroll.set

        ttk.Label(details_frame, text="Status:").grid(row=2, column=0, padx=5, pady=5, sticky='e')
        self.sec_status_var = tk.StringVar()
        self.sec_status_combo = ttk.Combobox(details_frame, textvariable=self.sec_status_var,
                                             values=['Scheduled', 'Checked-in', 'Completed', 'Cancelled', 'No Show'],
                                             state='readonly', width=15)
        self.sec_status_combo.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        self.sec_status_combo.set('Scheduled')

        ttk.Label(details_frame, text="Notes:").grid(row=3, column=0, padx=5, pady=5, sticky='ne')
        self.sec_notes_text = tk.Text(details_frame, height=4, width=40, wrap=tk.WORD)
        self.sec_notes_text.grid(row=3, column=1, columnspan=2, sticky='ew', padx=5, pady=5)
        sec_notes_scroll = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.sec_notes_text.yview)
        sec_notes_scroll.grid(row=3, column=3, sticky='ns')
        self.sec_notes_text['yscrollcommand'] = sec_notes_scroll.set

        # --- Widgets inside Buttons Frame (sec_button_frame) ---
        ttk.Button(sec_button_frame, text="Add/Update",
                   command=self.save_appointment).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(sec_button_frame, text="Clear Form",
                   command=self.clear_appointment_form).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(sec_button_frame, text="Delete Selected",
                   command=self.delete_appointment).pack(side=tk.LEFT, padx=5, pady=5)

        # --- Initial data load ---
        self.load_appointments()
        
    # --- Secretary Tab Helper Methods ---

    def search_patient_for_secretary(self, event=None):
        """Searches patients for the secretary tab context."""
        search_term = self.sec_search_entry.get().strip()
        if not search_term:
            messagebox.showinfo("Search", "Please enter a name or ID to search.")
            return

        # Use the same logic as investigation search, but update secretary fields
        query = "SELECT id, name, dob FROM patients WHERE id LIKE ? OR name LIKE ?"
        params = (f"%{search_term}%", f"%{search_term}%")

        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            patients = cursor.fetchall()

            if not patients:
                messagebox.showinfo("Search Results", "No patients found matching your search.")
                self.clear_secretary_patient_selection()
            elif len(patients) == 1:
                patient_id, patient_name, _ = patients[0]
                self.secretary_selected_patient_id = patient_id
                self.sec_patient_id_var.set(patient_id)
                self.sec_patient_name_var.set(patient_name)
                self.clear_appointment_form(clear_patient=False) # Clear form but keep patient
                # Optional: Reload appointments if date is today?
                # self.load_appointments()
            else:
                # Handle multiple results - show selection dialog or first match
                patient_id, patient_name, _ = patients[0]
                self.secretary_selected_patient_id = patient_id
                self.sec_patient_id_var.set(patient_id)
                self.sec_patient_name_var.set(patient_name)
                self.clear_appointment_form(clear_patient=False)
                messagebox.showinfo("Search Results", f"Multiple patients found. Selecting first match: {patient_name} (ID: {patient_id}).")

        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to search patients: {e}")
            self.clear_secretary_patient_selection()
        # finally:
        #     if cursor: cursor.close()


    def load_appointments(self):
        """Loads appointments for the selected date into the treeview."""
        selected_date = self.sec_date_entry.get()
        if not selected_date:
            return # Don't load if date is empty

        # Validate date format if using simple Entry
        if not HAS_TKCALENDAR:
            try:
                datetime.strptime(selected_date, '%Y-%m-%d')
            except ValueError:
                messagebox.showerror("Error", "Invalid date format. Please use YYYY-MM-DD.")
                # Clear tree if date is invalid
                for item in self.sec_appointment_tree.get_children():
                    self.sec_appointment_tree.delete(item)
                return

        # Clear existing appointments
        for item in self.sec_appointment_tree.get_children():
            self.sec_appointment_tree.delete(item)

        try:
            cursor = self.conn.cursor()
            # Join with patients table to get the name
            cursor.execute("""
                SELECT a.id, a.appointment_time, p.name, a.reason, a.status, a.patient_id
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                WHERE a.appointment_date = ?
                ORDER BY a.appointment_time ASC
            """, (selected_date,))
            appointments = cursor.fetchall()

            for i, appt in enumerate(appointments):
                # appt contains: id, time, name, reason, status, patient_id
                display_appt = [str(a) if a is not None else "" for a in appt[:5]] # Only display first 5 columns
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                 # Store patient_id with the item but don't display it directly
                self.sec_appointment_tree.insert('', tk.END, iid=appt[0], values=display_appt, tags=(tag,)) # Use appt ID as iid

        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to load appointments: {e}")
        # finally:
        #     if cursor: cursor.close()


    def on_appointment_select(self, event=None):
        """Handles selection of an appointment in the treeview."""
        selected_item_iid = self.sec_appointment_tree.focus() # Get the item ID (appt ID)
        if not selected_item_iid:
            self.secretary_selected_appointment_id = None
            return

        self.secretary_selected_appointment_id = selected_item_iid

        # Fetch full details for the selected appointment
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT a.patient_id, p.name, a.appointment_time, a.reason, a.status, a.notes
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                WHERE a.id = ?
            """, (self.secretary_selected_appointment_id,))
            details = cursor.fetchone()

            if details:
                patient_id, patient_name, time, reason, status, notes = details

                # Update patient selection fields
                self.secretary_selected_patient_id = patient_id
                self.sec_patient_id_var.set(patient_id)
                self.sec_patient_name_var.set(patient_name)

                # Populate the form
                self.sec_time_entry.delete(0, tk.END)
                self.sec_time_entry.insert(0, time if time else "")
                self.sec_reason_text.delete("1.0", tk.END)
                self.sec_reason_text.insert("1.0", reason if reason else "")
                self.sec_status_var.set(status if status else "Scheduled")
                self.sec_notes_text.delete("1.0", tk.END)
                self.sec_notes_text.insert("1.0", notes if notes else "")
            else:
                messagebox.showerror("Error", "Could not retrieve appointment details.")
                self.clear_appointment_form() # Clear form if details not found


        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to load appointment details: {e}")
            self.secretary_selected_appointment_id = None
        # finally:
        #     if cursor: cursor.close()


    def save_appointment(self):
        """Saves a new appointment or updates the selected one."""
        patient_id = self.secretary_selected_patient_id # Use the stored ID
        if not patient_id:
            messagebox.showerror("Error", "No patient selected. Please search and select a patient first.")
            return

        appt_date = self.sec_date_entry.get()
        appt_time = self.sec_time_entry.get().strip()
        appt_reason = self.sec_reason_text.get("1.0", tk.END).strip()
        appt_status = self.sec_status_var.get()
        appt_notes = self.sec_notes_text.get("1.0", tk.END).strip()

        if not appt_date or not appt_time:
            messagebox.showerror("Error", "Appointment Date and Time are required.")
            return

        # Basic time format validation (HH:MM) - enhance if needed
        try:
            datetime.strptime(appt_time, '%H:%M')
        except ValueError:
             try:
                 # Try HH:MM:SS
                 datetime.strptime(appt_time, '%H:%M:%S')
             except ValueError:
                 messagebox.showerror("Error", "Invalid Time format. Please use HH:MM or HH:MM:SS.")
                 return


        # Validate date format if using simple Entry
        if not HAS_TKCALENDAR:
            try:
                datetime.strptime(appt_date, '%Y-%m-%d')
            except ValueError:
                messagebox.showerror("Error", "Invalid date format. Please use YYYY-MM-DD.")
                return


        try:
            cursor = self.conn.cursor()
            # Check if we are updating (an appointment was selected from the list)
            if self.secretary_selected_appointment_id:
                cursor.execute("""
                    UPDATE appointments
                    SET patient_id = ?, appointment_date = ?, appointment_time = ?,
                        reason = ?, status = ?, notes = ?
                    WHERE id = ?
                """, (patient_id, appt_date, appt_time, appt_reason, appt_status, appt_notes,
                      self.secretary_selected_appointment_id))
                action = "updated"
            else:
                # Insert new appointment
                cursor.execute("""
                    INSERT INTO appointments (patient_id, appointment_date, appointment_time, reason, status, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (patient_id, appt_date, appt_time, appt_reason, appt_status, appt_notes))
                action = "added"

            self.conn.commit()
            messagebox.showinfo("Success", f"Appointment {action} successfully.")
            self.load_appointments() # Refresh list for the current date
            self.clear_appointment_form() # Clear form after successful save

        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to save appointment: {e}")
            self.conn.rollback()
        # finally:
        #     if cursor: cursor.close()


    def delete_appointment(self):
        """Deletes the appointment selected in the appointment list."""
        selected_item_iid = self.sec_appointment_tree.focus()
        if not selected_item_iid:
            messagebox.showerror("Error", "No appointment selected to delete.")
            return

        appt_id = selected_item_iid
        # Get details for confirmation message
        try:
             appt_time = self.sec_appointment_tree.item(appt_id)['values'][1]
             pat_name = self.sec_appointment_tree.item(appt_id)['values'][2]
        except IndexError:
             appt_time = "N/A"
             pat_name = "N/A"


        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the appointment for '{pat_name}' at {appt_time} (ID: {appt_id})?"):
            try:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM appointments WHERE id = ?", (appt_id,))
                self.conn.commit()

                if cursor.rowcount > 0:
                    messagebox.showinfo("Success", "Appointment deleted successfully.")
                    self.load_appointments() # Refresh list
                    # Check if the deleted appointment was loaded in the form
                    if self.secretary_selected_appointment_id == appt_id:
                        self.clear_appointment_form() # Clear form
                else:
                    messagebox.showerror("Error", "Appointment not found or already deleted.")

            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Failed to delete appointment: {e}")
                self.conn.rollback()
            # finally:
            #     if cursor: cursor.close()


    def clear_appointment_form(self, clear_patient=True):
        """Clears the appointment details form."""
        if clear_patient:
            self.clear_secretary_patient_selection()

        self.sec_time_entry.delete(0, tk.END)
        self.sec_reason_text.delete("1.0", tk.END)
        self.sec_status_var.set("Scheduled") # Reset status
        self.sec_notes_text.delete("1.0", tk.END)

        # Reset selected appointment ID
        self.secretary_selected_appointment_id = None
        # Deselect item in appointment tree
        if self.sec_appointment_tree.selection():
            self.sec_appointment_tree.selection_remove(self.sec_appointment_tree.selection()[0])


    def clear_secretary_patient_selection(self):
        """Clears the patient selection fields in the secretary tab."""
        self.sec_search_entry.delete(0, tk.END)
        self.secretary_selected_patient_id = None
        self.sec_patient_id_var.set("")
        self.sec_patient_name_var.set("")
        
    def get_external_table_columns(self, cursor, table_name):
        """Gets column names from a table in the external database."""
        try:
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = [info[1] for info in cursor.fetchall()] # Column name is the second element
            return columns
        except sqlite3.Error as e:
            print(f"Error getting table info for '{table_name}': {e}")
            return None

    def find_column_mapping(self, external_columns):
        """
        Tries to map expected internal column names to actual external column names.
        Returns a dictionary mapping internal_name -> external_name or None if not found.
        """
        # Define the columns needed for the internal database and potential aliases
        target_schema = {
            'name': ['name', 'patient_name', 'full_name'],
            'dob': ['dob', 'date_of_birth', 'birthdate', 'birth_date'],
            'contact': ['contact', 'phone', 'telephone', 'contact_number', 'phone_number'],
            'medical_history': ['medical_history', 'history', 'notes', 'medical_notes', 'chart']
        }
        # Store the mapping: internal_name -> actual_external_name
        mapping = {}
        # Store the actual external names found for the SELECT query
        select_columns = []

        external_columns_lower = {col.lower(): col for col in external_columns} # For case-insensitive matching

        for internal_name, aliases in target_schema.items():
            found_external_name = None
            for alias in aliases:
                if alias.lower() in external_columns_lower:
                    found_external_name = external_columns_lower[alias.lower()]
                    break # Found the best match for this internal name

            if found_external_name:
                mapping[internal_name] = found_external_name
                select_columns.append(f'"{found_external_name}"') # Quote names in case they have spaces/special chars
            else:
                # Column not found in external DB, map internal name to None
                mapping[internal_name] = None
                select_columns.append("NULL") # Select NULL if the column doesn't exist externally
                print(f"Warning: Could not find a matching column for '{internal_name}' in the external database.")

        # --- Crucial Check: Ensure 'name' column was found ---
        if mapping.get('name') is None:
            messagebox.showerror("Import Error",
                                 "Could not find a required 'name' column (or similar alias) "
                                 "in the 'patients' table of the selected database.")
            return None, None # Indicate failure

        return mapping, select_columns


    def import_external_patients(self):
        """Imports patient data from an external SQLite database file with schema detection."""
        filepath = filedialog.askopenfilename(
            title="Select External Clinic Database",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
        )

        if not filepath:
            messagebox.showinfo("Import Cancelled", "Patient import operation cancelled.")
            return

        print(f"Attempting to import from: {filepath}")
        external_conn = None
        imported_count = 0
        skipped_count = 0
        total_patients = 0

        try:
            # Connect to the external database
            external_conn = sqlite3.connect(filepath)
            external_cursor = external_conn.cursor()

            # 1. Check if 'patients' table exists
            external_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='patients';")
            if not external_cursor.fetchone():
                 messagebox.showerror("Import Error",
                                     f"The selected database '{os.path.basename(filepath)}' "
                                     "does not contain a 'patients' table.")
                 return

            # 2. Get actual column names from the external 'patients' table
            external_columns = self.get_external_table_columns(external_cursor, 'patients')
            if not external_columns:
                 messagebox.showerror("Import Error",
                                     f"Could not read column information from the 'patients' table "
                                     f"in '{os.path.basename(filepath)}'.")
                 return
            print(f"Found columns in external 'patients' table: {external_columns}")

            # 3. Find mapping between internal needs and external columns
            column_mapping, select_columns = self.find_column_mapping(external_columns)
            if column_mapping is None: # Required column ('name') was missing
                return # Error message already shown in find_column_mapping

            # 4. Construct and execute the dynamic SELECT query
            select_query = f"SELECT {', '.join(select_columns)} FROM patients;"
            print(f"Executing query: {select_query}")
            try:
                external_cursor.execute(select_query)
            except sqlite3.Error as e:
                 messagebox.showerror("Import Error",
                                     f"Error executing query on external database:\n{e}\n\n"
                                     f"Query: {select_query}")
                 return

            external_patients = external_cursor.fetchall()
            total_patients = len(external_patients)
            print(f"Found {total_patients} potential patient records in external database.")

            if total_patients == 0:
                messagebox.showinfo("Import Info", "No patient records found in the 'patients' table of the selected file.")
                return

            # Get cursor for the internal database
            internal_cursor = self.conn.cursor()

            # 5. Iterate, extract data using mapping, clean, and insert
            for i, patient_data in enumerate(external_patients):
                # Extract data using the index corresponding to select_columns order
                # Remember select_columns was built in the order of target_schema keys
                internal_data = {}
                target_keys = list(column_mapping.keys()) # ['name', 'dob', 'contact', 'medical_history']

                for idx, key in enumerate(target_keys):
                    internal_data[key] = patient_data[idx] # Data corresponds to the order in select_columns

                # --- Data Cleaning and Formatting ---
                name = str(internal_data['name']).strip() if internal_data.get('name') else None
                dob_raw = internal_data.get('dob')
                contact = str(internal_data['contact']).strip() if internal_data.get('contact') else None
                history = str(internal_data['medical_history']).strip() if internal_data.get('medical_history') else None

                # Basic check for essential data
                if not name:
                    print(f"Skipping record {i+1} due to missing name: {patient_data}")
                    skipped_count += 1
                    continue

                # --- Date of Birth Parsing (Keep your existing robust logic) ---
                dob_str = None
                if dob_raw:
                    try:
                        if isinstance(dob_raw, (datetime, date)):
                            dob_str = dob_raw.strftime('%Y-%m-%d')
                        else:
                            parsed_date = None
                            # Try parsing common formats (add more if needed)
                            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y%m%d',
                                        '%Y-%m-%d %H:%M:%S', '%d-%b-%Y', '%m-%d-%Y'):
                                try:
                                    # Convert to string first for consistent parsing
                                    parsed_date = datetime.strptime(str(dob_raw).strip(), fmt)
                                    break
                                except (ValueError, TypeError):
                                    continue
                            if parsed_date:
                                dob_str = parsed_date.strftime('%Y-%m-%d')
                            else:
                                print(f"Warning: Could not parse DOB '{dob_raw}' for patient '{name}'. Storing as is or skipping.")
                                # Optionally store the raw value if your internal DB allows text for DOB
                                # dob_str = str(dob_raw).strip() # Uncomment if you want to store unparsed DOB
                    except Exception as date_err:
                         print(f"Warning: Error processing DOB '{dob_raw}' for patient '{name}': {date_err}. Skipping DOB.")
                # --- End Date Parsing ---

                # --- Insertion into Internal DB ---
                try:
                    internal_cursor.execute('''
                        INSERT INTO patients (name, dob, contact, medical_history)
                        VALUES (?, ?, ?, ?)
                    ''', (name, dob_str, contact, history))
                    imported_count += 1
                except sqlite3.IntegrityError:
                    # Patient with same unique key (e.g., name, dob) likely exists
                    print(f"Skipping duplicate patient: Name='{name}', DOB='{dob_str}'")
                    skipped_count += 1
                except sqlite3.Error as insert_err:
                    print(f"Error inserting patient '{name}': {insert_err}")
                    skipped_count += 1
                    # Decide if you want to rollback all on first error or just skip
                    # self.conn.rollback() # Rollback the entire import on ANY insert error
                    # break # Stop import on first error

            # Commit all successful inserts
            self.conn.commit()

            messagebox.showinfo("Import Complete",
                                f"Patient import finished.\n\n"
                                f"Total records found: {total_patients}\n"
                                f"Successfully imported: {imported_count}\n"
                                f"Skipped (duplicates or errors): {skipped_count}")

            # Refresh the main patient list view
            self.refresh_patient_list()

        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"An error occurred connecting to or reading the external database: {e}")
            if self.conn: self.conn.rollback() # Rollback any partial internal transaction
        except Exception as e:
            messagebox.showerror("Import Error", f"An unexpected error occurred during import: {e}")
            if self.conn: self.conn.rollback()
        finally:
            # Ensure external connection is closed
            if external_conn:
                external_conn.close()
                print("External database connection closed.")


import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime, date, timedelta
from tkcalendar import Calendar # Ensure tkcalendar is installed: pip install tkcalendar
import os
from typing import Optional, List, Tuple, Dict, Any # For type hinting

# --- Constants ---
# Consider making DB_PATH configurable via settings or environment variable
# Use a placeholder path if the original is user-specific
DB_PATH = "clinic_database.db" # Use a relative path or ensure the absolute path exists

# Statuses (Using constants for clarity and easier modification)
STATUS_CONFIRMED = "مؤكد | Confirmed"
STATUS_PENDING = "قيد الانتظار | Pending"
STATUS_ARRIVED = "تم الحضور | Arrived"
STATUS_COMPLETED = "تم الكشف | Completed"
STATUS_NOSHOW = "لم يحضر | No-show"
STATUS_CANCELLED = "ملغي | Cancelled"

APPOINTMENT_STATUSES = [
    STATUS_CONFIRMED, STATUS_PENDING, STATUS_ARRIVED,
    STATUS_COMPLETED, STATUS_NOSHOW, STATUS_CANCELLED
]

# Reasons
REASON_EXAMINATION = "كشف | Examination"
REASON_FOLLOWUP = "متابعة | Follow-up"
REASON_PROCEDURE = "إجراء | Procedure"
REASON_CONSULTATION = "استشارة | Consultation"
REASON_OTHER = "أخرى | Other"

APPOINTMENT_REASONS = [
    REASON_EXAMINATION, REASON_FOLLOWUP, REASON_PROCEDURE,
    REASON_CONSULTATION, REASON_OTHER
]

# --- Helper Functions ---
def generate_time_slots(start_hour: int = 9, end_hour: int = 17, interval: int = 15) -> List[str]:
    """Generates time slots in HH:MM format within the specified range."""
    slots = []
    try:
        current_time = datetime.strptime(f"{start_hour:02d}:00", "%H:%M")
        # End time limit is exclusive, so aim for the start of the hour *after* the end_hour
        end_time_limit = datetime.strptime(f"{end_hour:02d}:59", "%H:%M") # Allow slots up to end_hour:XX
    except ValueError:
        print("Error: Invalid start or end hour for time slot generation.")
        return [] # Return empty list on error

    while current_time <= end_time_limit:
        slots.append(current_time.strftime("%H:%M"))
        current_time += timedelta(minutes=interval)

    return slots

# --- Main Class ---
class SecretaryModule:
    """
    Manages the Secretary tab UI for patient appointment scheduling.
    Handles patient search, appointment viewing, creation, editing, and cancellation.
    """

    def __init__(self, parent: tk.Widget, main_app: Any):
        """Initialize the secretary module."""
        self.parent = parent
        self.main_app = main_app # Keep reference if needed elsewhere
        self.conn: Optional[sqlite3.Connection] = None
        self.selected_patient_id: Optional[int] = None
        self.selected_appointment_id: Optional[int] = None # Store the DB ID of the appointment in the form
        self.date_picker_window: Optional[tk.Toplevel] = None # Track date picker window

        # --- UI Variables ---
        self.status_message = tk.StringVar()
        self.patient_search_var = tk.StringVar()
        self.patient_id_var = tk.StringVar()
        self.patient_name_var = tk.StringVar()
        self.date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self.start_time_var = tk.StringVar()
        self.end_time_var = tk.StringVar()
        self.reason_var = tk.StringVar()
        self.status_var = tk.StringVar(value=STATUS_CONFIRMED) # Default status

        # --- UI Widgets (initialized in setup methods) ---
        self.patient_search_entry: Optional[ttk.Entry] = None
        self.appointments_tree: Optional[ttk.Treeview] = None
        self.start_time_combo: Optional[ttk.Combobox] = None
        self.end_time_combo: Optional[ttk.Combobox] = None
        self.reason_combo: Optional[ttk.Combobox] = None
        self.status_combo: Optional[ttk.Combobox] = None
        self.notes_text: Optional[tk.Text] = None
        self.date_entry: Optional[ttk.Entry] = None

        # --- Data ---
        self.time_slots = generate_time_slots() # Generate time slots once

        # --- Initialization Steps ---
        if self._connect_database(DB_PATH):
            self._initialize_database_schema() # Ensure schema is checked/created
            self._setup_ui()
            self.show_status("Ready. Please search for a patient or select a date.")
        else:
            # Display error in the parent frame if DB connection fails
            error_label = ttk.Label(self.parent, text="Database connection failed. Cannot load module.", foreground="red", font=('Arial', 12))
            error_label.pack(pady=20, padx=10, anchor=tk.CENTER)

    # --------------------------------------------------------------------------
    # Database Initialization and Connection
    # --------------------------------------------------------------------------

    def _connect_database(self, db_path: str) -> bool:
        """Establish connection to the SQLite database."""
        try:
            # Ensure the directory exists if specified
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                try:
                    os.makedirs(db_dir)
                    print(f"Created database directory: {db_dir}")
                except OSError as e:
                    messagebox.showerror("Database Error", f"Could not create database directory: {db_dir}\n{e}", parent=self.parent)
                    return False

            self.conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
            self.conn.row_factory = sqlite3.Row # Access columns by name
            print(f"Database connection established: {db_path}")
            return True
        except sqlite3.Error as e:
            self.log_error(f"Database connection error to {db_path}: {e}", show_popup=True)
            self.conn = None
            return False
        except Exception as e: # Catch other potential errors like permissions
            self.log_error(f"Failed to connect to database {db_path}: {e}", show_popup=True)
            self.conn = None
            return False

    def _initialize_database_schema(self):
        """Create necessary tables and indices if they don't exist."""
        if not self.conn:
            self.log_error("Database connection not available for schema initialization.", show_popup=True)
            return

        schema_sql = [
            # Patients table (ensure it matches your main application's needs)
            # Added common fields, adjust as necessary
            '''CREATE TABLE IF NOT EXISTS patients (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   name TEXT NOT NULL,
                   dob TEXT, -- Date of Birth (YYYY-MM-DD)
                   phone TEXT,
                   address TEXT,
                   national_id TEXT UNIQUE, -- Optional: Ensure uniqueness
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
               )''',
            # Appointments table
            '''CREATE TABLE IF NOT EXISTS appointments (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   patient_id INTEGER NOT NULL,
                   appointment_date DATE NOT NULL,
                   start_time TEXT NOT NULL,
                   end_time TEXT,
                   reason TEXT,
                   status TEXT NOT NULL,
                   notes TEXT,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
               )''',
            # Trigger to update 'updated_at' timestamp on appointment update
            '''CREATE TRIGGER IF NOT EXISTS update_appointments_updated_at
               AFTER UPDATE ON appointments FOR EACH ROW
               WHEN OLD.updated_at = NEW.updated_at OR OLD.updated_at IS NULL -- Avoid recursion if updated_at is explicitly set
               BEGIN
                   UPDATE appointments SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
               END;''',
            # Indices for faster lookups
            '''CREATE INDEX IF NOT EXISTS idx_appointments_patient_date ON appointments(patient_id, appointment_date)''',
            '''CREATE INDEX IF NOT EXISTS idx_appointments_date_time ON appointments(appointment_date, start_time)''', # Useful for calendar views
            '''CREATE INDEX IF NOT EXISTS idx_patients_name ON patients(name)''',
            '''CREATE INDEX IF NOT EXISTS idx_patients_phone ON patients(phone)''', # If searching by phone
            '''CREATE INDEX IF NOT EXISTS idx_patients_national_id ON patients(national_id)''' # If searching by National ID
        ]

        try:
            cursor = self.conn.cursor()
            for sql in schema_sql:
                cursor.execute(sql)
            self.conn.commit()
            print("Database schema checked/initialized successfully.")
            # Optional: Add ALTER TABLE statements here if needed for upgrades
            # self._check_and_add_columns() # Example for handling schema changes
        except sqlite3.Error as e:
            self.log_error(f"Database schema initialization error: {e}", show_popup=True)
            try:
                self.conn.rollback() # Rollback any partial changes on error
            except sqlite3.Error as rb_e:
                print(f"Rollback failed: {rb_e}")

    # Optional: Helper to add columns if they don't exist (for schema evolution)
    # def _check_and_add_columns(self):
    #     """Checks for missing columns and adds them."""
    #     if not self.conn: return
    #     cursor = self.conn.cursor()
    #     try:
    #         # Check for 'dob' in 'patients'
    #         cursor.execute("PRAGMA table_info(patients)")
    #         columns = [info[1] for info in cursor.fetchall()]
    #         if 'dob' not in columns:
    #             print("Adding 'dob' column to 'patients' table.")
    #             cursor.execute("ALTER TABLE patients ADD COLUMN dob TEXT")
    #         # Add checks for other columns if necessary
    #         self.conn.commit()
    #     except sqlite3.Error as e:
    #         print(f"Error checking/adding columns: {e}")
    #         self.conn.rollback()

    def close_connection(self):
        """Close the database connection when the module/app is closed."""
        if self.date_picker_window: # Close date picker if open
            try:
                self.date_picker_window.destroy()
            except tk.TclError:
                pass # Window might already be closed
        if self.conn:
            try:
                self.conn.close()
                print("Database connection closed.")
                self.conn = None
            except sqlite3.Error as e:
                print(f"Error closing database connection: {e}") # Log quietly

    # --------------------------------------------------------------------------
    # UI Setup - Main Structure and Helpers
    # --------------------------------------------------------------------------

    def _setup_ui(self):
        """Setup the main user interface layout and widgets."""
        # --- Main frame ---
        main_frame = ttk.Frame(self.parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.rowconfigure(1, weight=1) # Make paned window row expandable
        main_frame.columnconfigure(0, weight=1) # Make paned window column expandable

        # --- Title ---
        title_frame = ttk.Frame(main_frame)
        # Use grid for title frame placement
        title_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        ttk.Label(title_frame, text="إدارة مواعيد المرضى | Patient Appointment Management",
                  font=('Arial', 16, 'bold')).pack(side=tk.LEFT) # Pack within its frame

        # --- Status Bar (at the bottom) ---
        status_bar = ttk.Label(main_frame, textvariable=self.status_message,
                               relief=tk.SUNKEN, anchor=tk.W, padding=(5, 2))
        # Use grid for status bar placement
        status_bar.grid(row=2, column=0, sticky="ew", pady=(5, 0))

        # --- Paned Window for resizable panes (above status bar) ---
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        # Use grid for paned window placement, make it expand
        paned_window.grid(row=1, column=0, sticky="nsew")

        # --- Left Pane (Appointments List) ---
        left_pane = ttk.Frame(paned_window, padding=5)
        paned_window.add(left_pane, weight=2) # Adjust weight as needed
        left_pane.rowconfigure(1, weight=1) # Make treeview frame expandable
        left_pane.columnconfigure(0, weight=1) # Make treeview frame expandable

        # --- Right Pane (Search + Form) ---
        right_pane = ttk.Frame(paned_window, padding=5)
        paned_window.add(right_pane, weight=3) # Adjust weight as needed
        right_pane.rowconfigure(2, weight=1) # Make form frame expandable
        right_pane.columnconfigure(0, weight=1) # Make form frame expandable

        # --- Populate Panes ---
        # Use grid within the right pane for better control
        self._setup_patient_search_ui(right_pane) # Row 0
        self._setup_appointment_form_ui(right_pane) # Row 1 (patient info) + Row 2 (rest of form)

        # Use grid within the left pane
        self._setup_appointments_view_ui(left_pane) # Row 0 (toolbar) + Row 1 (treeview)


    def _setup_patient_search_ui(self, parent_pane: tk.Widget):
        """Sets up the patient search input and buttons."""
        search_frame_outer = ttk.LabelFrame(parent_pane, text="بحث عن مريض | Find Patient", padding=10)
        # Place using grid in the parent (right_pane)
        search_frame_outer.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        search_frame_outer.columnconfigure(1, weight=1) # Make entry expand

        ttk.Label(search_frame_outer, text="الاسم أو الرقم | Name or ID:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)

        self.patient_search_entry = ttk.Entry(search_frame_outer, width=30, textvariable=self.patient_search_var)
        self.patient_search_entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 5))
        # Bindings
        self.patient_search_entry.bind("<Return>", lambda e: self.search_patient())
        self.patient_search_entry.bind("<KeyRelease>", self._incremental_patient_search) # Optional incremental search feedback

        search_button = ttk.Button(search_frame_outer, text="بحث | Search", command=self.search_patient)
        search_button.grid(row=0, column=2, padx=(0, 5))

        clear_button = ttk.Button(search_frame_outer, text="مسح | Clear", command=self.clear_patient_selection)
        clear_button.grid(row=0, column=3)

    def _setup_appointments_view_ui(self, parent_pane: tk.Widget):
        """Sets up the appointments list view (Treeview)."""
        # This frame will contain the toolbar and the treeview frame
        view_container = ttk.Frame(parent_pane)
        view_container.grid(row=0, column=0, sticky="nsew") # Place container in parent (left_pane)
        view_container.rowconfigure(1, weight=1) # Make treeview row expandable
        view_container.columnconfigure(0, weight=1)

        self._create_appointments_toolbar(view_container) # Row 0 of view_container
        self._create_appointment_treeview(view_container) # Row 1 of view_container

    def _create_appointments_toolbar(self, parent_frame: tk.Widget):
        """Creates the toolbar with Add, Edit, Cancel, Refresh buttons."""
        toolbar = ttk.Frame(parent_frame, padding=(5, 5, 5, 0)) # Padding around toolbar
        toolbar.grid(row=0, column=0, sticky="ew") # Place toolbar at the top

        ttk.Button(toolbar, text="إضافة | Add", command=self.add_new_appointment_for_patient).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(toolbar, text="تعديل | Edit", command=self.edit_selected_appointment).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(toolbar, text="إلغاء | Cancel", command=self.cancel_selected_appointment).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(toolbar, text="تحديث | Refresh", command=self.update_appointments_list).pack(side=tk.RIGHT) # Align right

    def _create_appointment_treeview(self, parent_frame: tk.Widget):
        """Creates the Treeview widget for displaying appointments."""
        # Frame to hold treeview and scrollbars
        tree_frame = ttk.LabelFrame(parent_frame, text="مواعيد المريض | Patient Appointments", padding=5)
        tree_frame.grid(row=1, column=0, sticky="nsew") # Place below toolbar, make it expand
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # Scrollbars
        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        # Treeview Definition
        columns = ("appt_id", "Date", "Time", "Reason", "Status") # Add hidden ID column
        self.appointments_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            displaycolumns=("Date", "Time", "Reason", "Status"), # Columns to actually show
            show="headings",
            selectmode="browse", # Only allow single selection
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )
        self.appointments_tree.grid(row=0, column=0, sticky="nsew") # Make tree expand
        scrollbar_y.config(command=self.appointments_tree.yview)
        scrollbar_x.config(command=self.appointments_tree.xview)

        # Column Configuration
        col_configs = {
            # "appt_id": {"text": "ID", "width": 0, "anchor": tk.W, "stretch": tk.NO}, # Hidden ID column
            "Date": {"text": "التاريخ | Date", "width": 100, "anchor": tk.W},
            "Time": {"text": "الوقت | Time", "width": 110, "anchor": tk.W},
            "Reason": {"text": "السبب | Reason", "width": 150, "anchor": tk.W},
            "Status": {"text": "الحالة | Status", "width": 120, "anchor": tk.W}
        }
        # Configure display columns
        for col in self.appointments_tree['displaycolumns']:
             config = col_configs[col]
             self.appointments_tree.heading(col, text=config["text"], anchor=config.get("anchor", tk.CENTER))
             self.appointments_tree.column(col, width=config["width"], anchor=config.get("anchor", tk.W), stretch=tk.YES)

        # Configure hidden ID column
        self.appointments_tree.column("appt_id", width=0, stretch=tk.NO)


        # Tag Styles for status visualization
        self.appointments_tree.tag_configure("completed", background="#DCEDC8") # Light green
        self.appointments_tree.tag_configure("cancelled", background="#FFCDD2", foreground="#B71C1C") # Light red, dark text
        self.appointments_tree.tag_configure("noshow", background="#FFECB3", foreground="#E65100") # Light amber, dark text
        self.appointments_tree.tag_configure("arrived", background="#C5CAE9") # Light indigo
        self.appointments_tree.tag_configure("confirmed", background="#E3F2FD") # Light blue
        self.appointments_tree.tag_configure("pending", background="#F5F5F5") # Greyish

        # Event Bindings
        self.appointments_tree.bind("<<TreeviewSelect>>", self._on_appointment_select)
        self.appointments_tree.bind("<Double-1>", lambda e: self.edit_selected_appointment()) # Double-click to edit

    def _setup_appointment_form_ui(self, parent_pane: tk.Widget):
        """Sets up the appointment details form."""
        # Main container for the form elements in the right pane
        form_container = ttk.Frame(parent_pane)
        form_container.grid(row=1, column=0, rowspan=2, sticky="nsew") # Span rows if needed, make it expand
        form_container.columnconfigure(0, weight=1) # Make content expand horizontally
        form_container.rowconfigure(4, weight=1) # Make notes section expand vertically

        # --- Patient Info Display (Read-only) ---
        self._create_patient_info_display(form_container) # Grid row 0

        # --- Form Fields Frame ---
        # Use a LabelFrame for the editable part of the form
        form_fields_frame = ttk.LabelFrame(form_container, text="تفاصيل الموعد | Appointment Details", padding=10)
        form_fields_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0)) # Place below patient info
        form_fields_frame.columnconfigure(1, weight=1) # Allow widgets in col 1 to expand
        form_fields_frame.columnconfigure(3, weight=1) # Allow widgets in col 3 to expand

        self._create_datetime_widgets(form_fields_frame)     # Grid row 0 of form_fields_frame
        self._create_reason_status_widgets(form_fields_frame) # Grid row 1 & 2 of form_fields_frame
        self._create_notes_widget(form_fields_frame)          # Grid row 3 of form_fields_frame
        self._create_form_buttons(form_fields_frame)          # Grid row 4 of form_fields_frame

    def _create_patient_info_display(self, parent_frame: tk.Widget):
        """Creates the read-only display for selected patient ID and Name."""
        # Use a simple frame, place it using grid in the form_container
        frame = ttk.Frame(parent_frame, padding=(0, 0, 0, 5)) # Bottom padding
        frame.grid(row=0, column=0, sticky="ew")
        frame.columnconfigure(1, weight=1) # Let name entry expand

        ttk.Label(frame, text="المريض المحدد | Selected Patient:", font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 5))

        ttk.Label(frame, text="رقم المريض | ID:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Entry(frame, textvariable=self.patient_id_var, state="readonly", width=10).grid(row=1, column=1, sticky=tk.W, padx=(0, 10)) # Align left

        ttk.Label(frame, text="الاسم | Name:").grid(row=1, column=2, sticky=tk.W, padx=(0, 5))
        ttk.Entry(frame, textvariable=self.patient_name_var, state="readonly", width=35).grid(row=1, column=3, sticky=tk.EW) # Expand name field

    def _create_datetime_widgets(self, parent_frame: tk.Widget):
        """Creates Date entry, picker, and Time comboboxes within the form_fields_frame."""
        # Use grid layout within the parent_frame (form_fields_frame)
        row_num = 0

        # Date
        ttk.Label(parent_frame, text="التاريخ | Date:").grid(row=row_num, column=0, sticky=tk.W, padx=(0, 5), pady=5)
        self.date_entry = ttk.Entry(parent_frame, textvariable=self.date_var, width=12)
        self.date_entry.grid(row=row_num, column=1, sticky=tk.W, padx=(0, 2), pady=5)
        self.date_entry.bind("<FocusOut>", self._validate_date_format) # Validate on losing focus
        date_picker_button = ttk.Button(parent_frame, text="📅", width=3, command=self._show_date_picker)
        date_picker_button.grid(row=row_num, column=2, sticky=tk.W, padx=(0, 15), pady=5)

        # Start Time
        ttk.Label(parent_frame, text="من | From:").grid(row=row_num, column=3, sticky=tk.E, padx=(10, 5), pady=5) # Align label right
        self.start_time_combo = ttk.Combobox(parent_frame, textvariable=self.start_time_var, values=self.time_slots, width=8, state="readonly")
        self.start_time_combo.grid(row=row_num, column=4, sticky=tk.W, padx=(0, 10), pady=5)
        self.start_time_combo.bind("<<ComboboxSelected>>", self._update_end_time_from_start)

        # End Time
        ttk.Label(parent_frame, text="إلى | To:").grid(row=row_num, column=5, sticky=tk.E, padx=(0, 5), pady=5) # Align label right
        self.end_time_combo = ttk.Combobox(parent_frame, textvariable=self.end_time_var, values=self.time_slots, width=8, state="readonly")
        self.end_time_combo.grid(row=row_num, column=6, sticky=tk.W, pady=5)

    def _create_reason_status_widgets(self, parent_frame: tk.Widget):
        """Creates Reason and Status comboboxes within the form_fields_frame."""
        row_num = 1 # Start from next row

        # Reason
        ttk.Label(parent_frame, text="سبب الزيارة | Reason:").grid(row=row_num, column=0, sticky=tk.W, padx=(0, 5), pady=5)
        self.reason_combo = ttk.Combobox(parent_frame, textvariable=self.reason_var, values=APPOINTMENT_REASONS, width=30)
        self.reason_combo.grid(row=row_num, column=1, columnspan=6, sticky=tk.EW, pady=5) # Span across columns

        row_num += 1

        # Status
        ttk.Label(parent_frame, text="الحالة | Status:").grid(row=row_num, column=0, sticky=tk.W, padx=(0, 5), pady=5)
        self.status_combo = ttk.Combobox(parent_frame, textvariable=self.status_var, values=APPOINTMENT_STATUSES, state="readonly", width=30)
        self.status_combo.grid(row=row_num, column=1, columnspan=6, sticky=tk.EW, pady=5) # Span across columns

    def _create_notes_widget(self, parent_frame: tk.Widget):
        """Creates the Notes Text widget with scrollbar within the form_fields_frame."""
        row_num = 3 # Start from next row
        parent_frame.rowconfigure(row_num, weight=1) # Allow notes row to expand vertically

        notes_frame = ttk.LabelFrame(parent_frame, text="ملاحظات | Notes", padding=(5, 5, 5, 5))
        notes_frame.grid(row=row_num, column=0, columnspan=7, sticky="nsew", pady=5) # Span all columns, expand
        notes_frame.rowconfigure(0, weight=1)
        notes_frame.columnconfigure(0, weight=1)

        notes_scroll = ttk.Scrollbar(notes_frame)
        notes_scroll.grid(row=0, column=1, sticky="ns")

        self.notes_text = tk.Text(notes_frame, height=4, yscrollcommand=notes_scroll.set, wrap=tk.WORD, undo=True, relief=tk.SOLID, borderwidth=1)
        self.notes_text.grid(row=0, column=0, sticky="nsew")
        notes_scroll.config(command=self.notes_text.yview)

    def _create_form_buttons(self, parent_frame: tk.Widget):
        """Creates the Save and New buttons within the form_fields_frame."""
        row_num = 4 # Start from next row

        buttons_frame = ttk.Frame(parent_frame)
        # Place at bottom right using grid properties
        buttons_frame.grid(row=row_num, column=0, columnspan=7, sticky=tk.E, pady=(10, 0))

        ttk.Button(buttons_frame, text="حفظ | Save", command=self.save_appointment_details, width=10).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(buttons_frame, text="جديد | New", command=self.clear_form_for_new_appointment, width=10).pack(side=tk.RIGHT)

    # --------------------------------------------------------------------------
    # Date Picker Logic
    # --------------------------------------------------------------------------

    def _show_date_picker(self):
        """Displays a Toplevel window with a Calendar widget."""
        if self.date_picker_window and self.date_picker_window.winfo_exists():
            self.date_picker_window.lift()
            return

        # Create Toplevel window relative to the date entry
        picker_win = tk.Toplevel(self.parent)
        picker_win.title("Select Date")
        picker_win.transient(self.parent) # Keep on top of parent
        picker_win.grab_set() # Modal behavior
        picker_win.resizable(False, False)
        self.date_picker_window = picker_win # Store reference

        # Get current date from entry or default to today
        try:
            current_date = datetime.strptime(self.date_var.get(), '%Y-%m-%d').date()
        except ValueError:
            current_date = date.today()

        # Create Calendar widget
        cal = Calendar(picker_win, selectmode='day',
                       year=current_date.year, month=current_date.month, day=current_date.day,
                       date_pattern='yyyy-mm-dd') # Match our format
        cal.pack(pady=10, padx=10)

        def on_date_select():
            """Update the date variable and close the picker."""
            selected_date = cal.get_date()
            self.date_var.set(selected_date)
            picker_win.destroy()
            self.date_picker_window = None # Clear reference

        def on_picker_close():
            """Handle closing the picker window directly."""
            self.date_picker_window = None # Clear reference
            picker_win.destroy()

        picker_win.protocol("WM_DELETE_WINDOW", on_picker_close) # Handle window close button

        # Select Button
        select_button = ttk.Button(picker_win, text="Select", command=on_date_select)
        select_button.pack(pady=(0, 10))

        # Position the window near the date entry
        picker_win.update_idletasks() # Ensure widgets are drawn to get geometry
        if self.date_entry:
            entry_x = self.date_entry.winfo_rootx()
            entry_y = self.date_entry.winfo_rooty()
            entry_h = self.date_entry.winfo_height()
            win_w = picker_win.winfo_width()
            win_h = picker_win.winfo_height()

            # Position below and slightly to the right of the entry
            picker_win.geometry(f"+{entry_x}+{entry_y + entry_h + 5}")
        else:
            # Fallback positioning if entry doesn't exist
            parent_x = self.parent.winfo_rootx()
            parent_y = self.parent.winfo_rooty()
            parent_w = self.parent.winfo_width()
            parent_h = self.parent.winfo_height()
            x = parent_x + (parent_w // 2) - (win_w // 2)
            y = parent_y + (parent_h // 3) - (win_h // 2) # Position higher up
            picker_win.geometry(f"+{x}+{y}")

        picker_win.focus_set() # Focus the picker window

    def _validate_date_format(self, event: Optional[Any] = None):
        """Validate the date entry format when focus is lost."""
        date_str = self.date_var.get()
        try:
            # Attempt to parse the date
            datetime.strptime(date_str, '%Y-%m-%d')
            # Optional: Add range validation if needed
        except ValueError:
            # If format is wrong, reset to today's date or show error
            today_str = datetime.now().strftime('%Y-%m-%d')
            self.show_error(f"Invalid date format: '{date_str}'. Please use YYYY-MM-DD.", clear_after=5000)
            self.date_var.set(today_str) # Reset to today
            if self.date_entry: self.date_entry.focus_set() # Refocus entry


    # --------------------------------------------------------------------------
    # Event Handlers
    # --------------------------------------------------------------------------

    def _on_appointment_select(self, event: Optional[Any] = None):
        """Handles selection change in the appointments Treeview."""
        if not self.appointments_tree: return

        selected_items = self.appointments_tree.selection()
        if selected_items:
            item_iid = selected_items[0] # The iid is the database ID we set
            try:
                # Retrieve the hidden 'appt_id' value from the selected row
                item_data = self.appointments_tree.item(item_iid)
                self.selected_appointment_id = int(item_data['values'][0]) # Get ID from hidden column value
                print(f"Selected appointment ID from tree: {self.selected_appointment_id}") # Debug print
                self._load_appointment_details_to_form()
            except (ValueError, IndexError, KeyError) as e:
                 self.log_error(f"Error retrieving appointment ID from tree selection: {e}")
                 self.selected_appointment_id = None
                 self.clear_form_for_new_appointment(clear_patient=False) # Clear form but keep patient
        else:
            self.selected_appointment_id = None
            # Decide whether to clear the form or keep the last loaded appointment
            # self.clear_form_for_new_appointment(clear_patient=False) # Option: Clear form on deselection

    def _incremental_patient_search(self, event: Optional[Any] = None):
        """Provides simple feedback during incremental search."""
        if not self.patient_search_entry: return
        search_text = self.patient_search_var.get().strip()
        if len(search_text) < 2: # Only search if 2+ characters are entered
            # Optionally clear previous suggestions or status message
            # self.show_status("")
            return

        # This version just updates the status bar, no dropdown
        try:
            # Limit results for performance in incremental search
            results = self._fetch_patient_matches(search_text, limit=5)
            if results:
                self.show_status(f"Found {len(results)} potential match(es) for '{search_text}'. Press Enter or Search.", clear_after=5000)
            else:
                self.show_status(f"No matches found for '{search_text}'.", clear_after=5000)
        except Exception as e:
            # Log quietly, don't disrupt typing with popups
            print(f"Incremental search error: {e}")

    def _update_end_time_from_start(self, event: Optional[Any] = None):
        """Auto-updates the end time based on the selected start time (e.g., +30 mins)."""
        start_time_str = self.start_time_var.get()
        if not start_time_str or not self.time_slots: # Check if slots are available
            self.end_time_var.set("")
            return

        try:
            start_dt = datetime.strptime(start_time_str, '%H:%M')
            # Default duration (e.g., 30 minutes). Make this configurable if needed.
            duration = timedelta(minutes=30)
            end_dt = start_dt + duration
            calculated_end_time_str = end_dt.strftime('%H:%M')

            # Find the best matching slot in the available time slots
            best_slot = ""
            try:
                start_index = self.time_slots.index(start_time_str)
            except ValueError:
                start_index = -1 # Start time not found in list (shouldn't happen with combobox)

            if start_index != -1:
                # Look for the calculated end time or the next available slot after it
                found_exact = False
                for i in range(start_index + 1, len(self.time_slots)):
                    slot_dt = datetime.strptime(self.time_slots[i], '%H:%M')
                    if slot_dt == end_dt: # Exact match found
                        best_slot = self.time_slots[i]
                        found_exact = True
                        break
                    elif slot_dt > end_dt: # First slot after the calculated end time
                        best_slot = self.time_slots[i]
                        break # Stop searching
                # If no later slot found, maybe default to the last slot? Or the calculated time?
                # Current logic: if exact match not found, uses the next slot > end_dt
                # If end_dt is beyond the last slot, best_slot remains "" unless handled
                if not best_slot and not found_exact:
                    # Handle case where calculated time is beyond the last slot
                    # Option 1: Set to the last slot
                    # best_slot = self.time_slots[-1]
                    # Option 2: Allow the calculated time even if not a slot (requires end_time entry?)
                    # best_slot = calculated_end_time_str # Requires end_time_combo to be editable or use an Entry
                    # Option 3: Clear end time (safest if only slots are allowed)
                    best_slot = ""
                    self.show_status("Calculated end time is beyond available slots.", clear_after=4000)


            # If start time wasn't found or no suitable end slot, clear end time
            if not best_slot:
                 # Check if the calculated time itself is a valid slot (might be the last one)
                 if calculated_end_time_str in self.time_slots:
                     best_slot = calculated_end_time_str
                 else:
                     best_slot = "" # Clear if no valid slot found

            self.end_time_var.set(best_slot)

        except (ValueError, IndexError) as e:
            print(f"Error updating end time: {e}") # Log error
            self.end_time_var.set("") # Clear on error

    # --------------------------------------------------------------------------
    # Patient Search and Selection Logic
    # --------------------------------------------------------------------------

    def search_patient(self):
        """Handles the main patient search action (triggered by button or Enter)."""
        search_text = self.patient_search_var.get().strip()
        if not search_text:
            self.show_error("Please enter a name, ID, phone, or National ID to search.")
            return

        try:
            # Fetch more results for explicit search
            results = self._fetch_patient_matches(search_text, limit=20)

            if not results:
                self.show_status(f"No patient found matching '{search_text}'")
                # Optional: Ask if user wants to add a new patient
                # if messagebox.askyesno("Patient Not Found", f"No patient found matching '{search_text}'.\nWould you like to add a new patient record?", parent=self.parent):
                #     # Call a function (potentially in main_app) to switch to patient registration tab/form
                #     # self.main_app.navigate_to_patient_registration(search_text) # Example
                #     pass
                self.clear_patient_selection() # Clear selection if none found
            elif len(results) == 1:
                self._select_patient(results[0]) # Auto-select if only one match
            else:
                # Show dialog to choose from multiple matches
                self._show_patient_selection_dialog(results)

        except sqlite3.Error as e:
            # Check for specific "no such column" error related to 'dob'
            if "no such column: dob" in str(e):
                 self.log_error(f"Database Error: The 'patients' table is missing the 'dob' column. Please check the database schema.\nQuery failed: {e}", show_popup=True)
                 # Attempt search without dob
                 try:
                     results = self._fetch_patient_matches(search_text, limit=20, include_dob=False)
                     if not results:
                         self.show_status(f"No patient found matching '{search_text}' (searched without DOB).")
                         self.clear_patient_selection()
                     elif len(results) == 1:
                         self._select_patient(results[0])
                     else:
                         self._show_patient_selection_dialog(results)
                 except Exception as e_no_dob:
                     self.log_error(f"Patient search failed even without DOB: {e_no_dob}", show_popup=True)

            else:
                self.log_error(f"Patient search database error: {e}", show_popup=True)
        except Exception as e:
            self.log_error(f"An unexpected error occurred during patient search: {e}", show_popup=True)

    def _fetch_patient_matches(self, search_text: str, limit: int = 10, include_dob: bool = True) -> List[sqlite3.Row]:
        """
        Fetches patient records matching the search text (name, ID, phone, national_id).
        Returns a list of sqlite3.Row objects.
        Handles potential missing 'dob' column.
        """
        if not self.conn: return []

        cursor = self.conn.cursor()
        results = []

        # Determine columns to select based on include_dob flag and table structure
        select_columns = "id, name"
        if include_dob:
            try:
                # Check if dob column exists before including it
                cursor.execute("PRAGMA table_info(patients)")
                columns_info = cursor.fetchall()
                column_names = [info['name'] for info in columns_info]
                if 'dob' in column_names:
                    select_columns += ", dob"
                else:
                    print("Warning: 'dob' column not found in 'patients' table. Excluding from search results.")
                    include_dob = False # Ensure dob is not accessed later if missing
            except sqlite3.Error as e:
                print(f"Warning: Could not check for 'dob' column: {e}. Excluding from search results.")
                include_dob = False # Assume missing on error

        # Add other potential columns if they exist (optional, adjust as needed)
        # if 'phone' in column_names: select_columns += ", phone"
        # if 'national_id' in column_names: select_columns += ", national_id"

        base_query = f"SELECT {select_columns} FROM patients WHERE "
        params = []

        # Try searching by ID if input is purely numeric
        try:
            search_id = int(search_text)
            query = base_query + "id = ? OR name LIKE ? OR phone LIKE ? OR national_id LIKE ? LIMIT ?"
            params = [search_id, f'%{search_text}%', f'%{search_text}%', f'%{search_text}%', limit]
        except ValueError:
            # If not numeric, search by name, phone, or national_id
            query = base_query + "name LIKE ? OR phone LIKE ? OR national_id LIKE ? LIMIT ?"
            params = [f'%{search_text}%', f'%{search_text}%', f'%{search_text}%', limit]

        try:
            print(f"Executing patient search query: {query} with params: {params}") # Debug print
            cursor.execute(query, params)
            results = cursor.fetchall() # Returns list of Row objects
            print(f"Found {len(results)} matches.") # Debug print
        except sqlite3.Error as e:
            # Handle specific errors if needed, otherwise re-raise or log
            self.log_error(f"Database error during patient fetch: {e}\nQuery: {query}", show_popup=False) # Log without popup first
            # Re-raise to be caught by the calling function for user feedback
            raise e

        return results


    def _select_patient(self, patient_data: sqlite3.Row):
        """Updates UI and state when a patient is chosen from search results."""
        try:
            patient_id = patient_data['id']
            name = patient_data['name']
            # dob = patient_data['dob'] if 'dob' in patient_data.keys() else None # Safely access dob

            self.patient_id_var.set(str(patient_id))
            self.patient_name_var.set(name or "N/A") # Handle potential null name
            self.selected_patient_id = patient_id

            self.update_appointments_list() # Refresh appointments for the selected patient
            self.clear_form_for_new_appointment(clear_patient=False) # Clear form for new/edit
            self.show_status(f"Selected Patient: {name} (ID: {patient_id})")
            self.patient_search_var.set("") # Clear search entry after selection
            if self.appointments_tree:
                self.appointments_tree.focus_set() # Focus the appointments list

        except KeyError as e:
            self.log_error(f"Error accessing patient data key: {e}. Data received: {dict(patient_data)}", show_popup=True)
            self.clear_patient_selection()
        except Exception as e:
            self.log_error(f"Unexpected error selecting patient: {e}", show_popup=True)
            self.clear_patient_selection()


    def clear_patient_selection(self):
        """Clears patient info fields, the appointments list, and the form."""
        self.patient_id_var.set("")
        self.patient_name_var.set("")
        self.selected_patient_id = None
        self.patient_search_var.set("")
        self.selected_appointment_id = None # Also clear selected appointment

        # Clear appointments tree
        if self.appointments_tree:
            try:
                for item in self.appointments_tree.get_children():
                    self.appointments_tree.delete(item)
            except tk.TclError as e:
                 print(f"Error clearing treeview: {e}") # Handle if tree doesn't exist

        self.clear_form_for_new_appointment(clear_patient=True) # Clear form completely
        self.show_status("Patient selection cleared. Search for a patient.")
        if self.patient_search_entry:
            self.patient_search_entry.focus_set() # Focus back on search

    def _show_patient_selection_dialog(self, results: List[sqlite3.Row]):
        """Shows a modal dialog to select from multiple patient results."""
        dialog = tk.Toplevel(self.parent)
        dialog.title("Select Patient")
        dialog.geometry("450x300") # Wider and taller for more info
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.resizable(False, False)

        ttk.Label(dialog, text="Multiple patients found. Please select one:", font=('Arial', 10)).pack(pady=(10, 5))

        listbox_frame = ttk.Frame(dialog)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        listbox_frame.rowconfigure(0, weight=1)
        listbox_frame.columnconfigure(0, weight=1)

        listbox = tk.Listbox(listbox_frame, width=60, height=10, font=('Courier', 10)) # Monospaced font for alignment
        list_scroll = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=listbox.yview)
        listbox.config(yscrollcommand=list_scroll.set)

        list_scroll.grid(row=0, column=1, sticky="ns")
        listbox.grid(row=0, column=0, sticky="nsew")

        patient_map: Dict[int, sqlite3.Row] = {} # Map listbox index to patient data row
        for i, patient in enumerate(results):
            patient_id = patient['id']
            name = patient['name']
            dob = patient['dob'] if 'dob' in patient.keys() else "N/A"
            phone = patient['phone'] if 'phone' in patient.keys() else "N/A" # Example: include phone if available

            # Format display string for better alignment
            display_text = f"ID: {str(patient_id):<6} Name: {name:<25}"
            if dob != "N/A": display_text += f" DOB: {dob:<12}"
            # if phone != "N/A": display_text += f" Phone: {phone}" # Add phone if needed

            listbox.insert(tk.END, display_text)
            patient_map[i] = patient

        selected_patient_data: Optional[sqlite3.Row] = None

        def on_select():
            nonlocal selected_patient_data
            selected_indices = listbox.curselection()
            if selected_indices:
                try:
                    selected_patient_data = patient_map[selected_indices[0]]
                    self._select_patient(selected_patient_data) # Select the patient in main UI
                    dialog.destroy()
                except KeyError:
                     messagebox.showerror("Error", "Could not retrieve selected patient data.", parent=dialog)
                except Exception as e:
                     messagebox.showerror("Error", f"An error occurred: {e}", parent=dialog)
            else:
                messagebox.showwarning("Selection Required", "Please select a patient from the list.", parent=dialog)

        listbox.bind("<Double-Button-1>", lambda e: on_select()) # Double-click selects

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=(5, 10))
        ttk.Button(button_frame, text="Select", command=on_select, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)

        # Center dialog relative to parent
        dialog.update_idletasks()
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()
        dialog_w = dialog.winfo_width()
        dialog_h = dialog.winfo_height()
        x = parent_x + (parent_w // 2) - (dialog_w // 2)
        y = parent_y + (parent_h // 2) - (dialog_h // 2)
        dialog.geometry(f"+{x}+{y}")

        dialog.focus_set()
        listbox.focus_set() # Focus listbox initially
        if results: listbox.selection_set(0) # Pre-select first item

    # --------------------------------------------------------------------------
    # Appointment Data Loading and List Update
    # --------------------------------------------------------------------------

    def update_appointments_list(self):
        """Fetches and displays appointments for the selected patient in the Treeview."""
        if not self.appointments_tree:
            print("Error: Appointments treeview not initialized.")
            return
        if not self.conn:
            self.show_error("Database connection is not available.")
            return

        # Clear existing items
        try:
            for item in self.appointments_tree.get_children():
                self.appointments_tree.delete(item)
        except tk.TclError as e:
            print(f"Error clearing treeview before update: {e}")
            return # Avoid proceeding if tree is broken

        if self.selected_patient_id is None:
            # self.show_status("Select a patient to view appointments.") # Optional message
            return # No patient selected, do nothing further

        try:
            cursor = self.conn.cursor()
            # Fetch appointments ordered by date and time
            query = """
                SELECT id, appointment_date, start_time, end_time, reason, status, notes
                FROM appointments
                WHERE patient_id = ?
                ORDER BY appointment_date DESC, start_time ASC
            """
            cursor.execute(query, (self.selected_patient_id,))
            appointments = cursor.fetchall()

            if not appointments:
                self.show_status("No appointments found for this patient.")
                return

            # Populate the treeview
            for appt in appointments:
                appt_id = appt['id']
                appt_date = appt['appointment_date']
                # Format date if it's a date object, otherwise use as string
                date_str = appt_date.strftime('%Y-%m-%d') if isinstance(appt_date, date) else str(appt_date)

                start_time = appt['start_time'] or "N/A"
                end_time = appt['end_time'] or ""
                time_str = f"{start_time}" + (f" - {end_time}" if end_time else "") # Combine start/end time

                reason = appt['reason'] or "N/A"
                status = appt['status'] or "N/A"
                notes = appt['notes'] or "" # Keep notes for potential tooltips or details view

                # Determine tag based on status for styling
                tag = ""
                if status == STATUS_COMPLETED: tag = "completed"
                elif status == STATUS_CANCELLED: tag = "cancelled"
                elif status == STATUS_NOSHOW: tag = "noshow"
                elif status == STATUS_ARRIVED: tag = "arrived"
                elif status == STATUS_CONFIRMED: tag = "confirmed"
                elif status == STATUS_PENDING: tag = "pending"

                # Insert item using appointment ID as the iid for easy lookup
                # Store the DB ID in the first (hidden) column's value as well
                values = (appt_id, date_str, time_str, reason, status)
                self.appointments_tree.insert("", tk.END, iid=appt_id, values=values, tags=(tag,))

            self.show_status(f"Displayed {len(appointments)} appointment(s).")

        except sqlite3.Error as e:
            self.log_error(f"Database error fetching appointments: {e}", show_popup=True)
        except Exception as e:
            self.log_error(f"Unexpected error updating appointments list: {e}", show_popup=True)


    def _load_appointment_details_to_form(self) -> bool:
        """Fetches details of the selected appointment ID and populates the form."""
        if self.selected_appointment_id is None:
            print("No appointment selected to load.") # Debug print
            # self.clear_form_for_new_appointment(clear_patient=False) # Optionally clear form
            return False
        if not self.conn:
            self.show_error("Database connection not available.")
            return False

        try:
            cursor = self.conn.cursor()
            query = """
                SELECT appointment_date, start_time, end_time, reason, status, notes
                FROM appointments
                WHERE id = ?
            """
            cursor.execute(query, (self.selected_appointment_id,))
            appt_data = cursor.fetchone() # Use fetchone as ID is primary key

            if not appt_data:
                self.show_error(f"Appointment ID {self.selected_appointment_id} not found.")
                self.selected_appointment_id = None # Reset ID if not found
                return False

            # Populate form fields
            appt_date = appt_data['appointment_date']
            date_str = appt_date.strftime('%Y-%m-%d') if isinstance(appt_date, date) else str(appt_date)
            self.date_var.set(date_str)
            self.start_time_var.set(appt_data['start_time'] or "")
            self.end_time_var.set(appt_data['end_time'] or "")
            self.reason_var.set(appt_data['reason'] or "")
            self.status_var.set(appt_data['status'] or STATUS_PENDING) # Default if status is somehow null

            if self.notes_text:
                self.notes_text.delete("1.0", tk.END)
                self.notes_text.insert("1.0", appt_data['notes'] or "")
                self.notes_text.edit_reset() # Clear undo stack after loading

            self.show_status(f"Loaded details for appointment ID: {self.selected_appointment_id}")
            return True

        except sqlite3.Error as e:
            self.log_error(f"Database error loading appointment {self.selected_appointment_id}: {e}", show_popup=True)
            return False
        except Exception as e:
            self.log_error(f"Unexpected error loading appointment details: {e}", show_popup=True)
            return False

    # --------------------------------------------------------------------------
    # Appointment Actions (Triggered by UI)
    # --------------------------------------------------------------------------

    def add_new_appointment_for_patient(self):
        """Clears the form to add a new appointment for the CURRENTLY selected patient."""
        if self.selected_patient_id is None:
            self.show_error("Please select a patient before adding an appointment.")
            return
        # Patient is selected, just clear the form fields for a new entry
        self.clear_form_for_new_appointment(clear_patient=False) # Keep patient info
        self.show_status(f"Enter details for new appointment for {self.patient_name_var.get()}.")
        if self.date_entry: self.date_entry.focus_set() # Focus date field

    def edit_selected_appointment(self):
        """Loads the selected appointment from the list into the form for editing."""
        if not self.appointments_tree: return

        selected_items = self.appointments_tree.selection()
        if not selected_items:
            self.show_error("Please select an appointment from the list to edit.")
            return

        item_iid = selected_items[0]
        try:
            # Retrieve the hidden 'appt_id' value
            item_data = self.appointments_tree.item(item_iid)
            self.selected_appointment_id = int(item_data['values'][0]) # Get ID from hidden column
            print(f"Editing appointment ID from tree: {self.selected_appointment_id}") # Debug

            if not self._load_appointment_details_to_form():
                # If loading fails (e.g., appointment deleted elsewhere), reset state
                self.selected_appointment_id = None
                self.update_appointments_list() # Refresh list
                return

            self.show_status(f"Editing appointment ID: {self.selected_appointment_id} for {self.patient_name_var.get()}")
            if self.reason_combo: self.reason_combo.focus_set() # Focus a form field

        except (ValueError, IndexError, KeyError) as e:
             self.log_error(f"Error retrieving appointment ID for editing: {e}")
             self.selected_appointment_id = None
             self.clear_form_for_new_appointment(clear_patient=False)


    def cancel_selected_appointment(self):
        """Marks the selected appointment in the list as 'Cancelled' in the DB."""
        if not self.appointments_tree: return

        selected_items = self.appointments_tree.selection()
        if not selected_items:
            self.show_error("Please select an appointment from the list to cancel.")
            return

        appointment_id_to_cancel: Optional[int] = None
        item_values = None
        try:
            item_iid = selected_items[0]
            item_data = self.appointments_tree.item(item_iid)
            appointment_id_to_cancel = int(item_data['values'][0]) # Get ID from hidden column
            item_values = item_data['values'] # Get visible values for confirmation
            print(f"Attempting to cancel appointment ID: {appointment_id_to_cancel}") # Debug
        except (ValueError, IndexError, KeyError) as e:
            self.log_error(f"Error retrieving appointment ID for cancellation: {e}")
            self.show_error("Could not get appointment details to cancel.")
            return

        if appointment_id_to_cancel is None: return # Should not happen if selection exists

        confirm_msg = f"Are you sure you want to cancel this appointment?\n\n"
        if item_values and len(item_values) > 4: # Check if we got the expected values
            confirm_msg += f"Patient: {self.patient_name_var.get()}\n"
            confirm_msg += f"Date: {item_values[1]}\nTime: {item_values[2]}\nReason: {item_values[3]}"
        else:
             confirm_msg += f"Appointment ID: {appointment_id_to_cancel}"


        if messagebox.askyesno("Confirm Cancellation", confirm_msg, icon='warning', parent=self.parent):
            if self._update_appointment_status(appointment_id_to_cancel, STATUS_CANCELLED):
                self.show_status(f"Appointment ID: {appointment_id_to_cancel} has been cancelled.")
                self.update_appointments_list() # Refresh list to show cancelled status

                # If the cancelled appointment was the one currently loaded in the form, clear the form
                if self.selected_appointment_id == appointment_id_to_cancel:
                    self.clear_form_for_new_appointment(clear_patient=False) # Keep patient info
            else:
                # Error message shown by _update_appointment_status
                pass

    def _update_appointment_status(self, appointment_id: int, new_status: str) -> bool:
        """Updates the status of a specific appointment in the database."""
        if not self.conn:
            self.show_error("Database connection is not available.")
            return False
        if not appointment_id:
            self.show_error("Invalid Appointment ID provided for status update.")
            return False
        if new_status not in APPOINTMENT_STATUSES:
            self.show_error(f"Invalid status provided: {new_status}")
            return False

        try:
            cursor = self.conn.cursor()
            query = "UPDATE appointments SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            cursor.execute(query, (new_status, appointment_id))
            self.conn.commit()

            if cursor.rowcount == 0:
                self.show_error(f"Appointment ID {appointment_id} not found for status update.")
                return False
            else:
                print(f"Successfully updated status for appointment {appointment_id} to {new_status}")
                return True

        except sqlite3.Error as e:
            self.log_error(f"Database error updating appointment status for ID {appointment_id}: {e}", show_popup=True)
            self.conn.rollback()
            return False
        except Exception as e:
            self.log_error(f"Unexpected error updating appointment status: {e}", show_popup=True)
            self.conn.rollback()
            return False

    def save_appointment_details(self):
        """Validates form data and saves (inserts new or updates existing) appointment to the DB."""
        if not self._validate_form_data():
            return # Stop if validation fails

        # Retrieve validated data
        try:
            patient_id = int(self.patient_id_var.get()) # Already validated by selection
        except ValueError:
            self.show_error("Invalid Patient ID. Please re-select the patient.")
            return

        appt_date_str = self.date_var.get()
        start_time = self.start_time_var.get()
        end_time = self.end_time_var.get() or None # Store None if empty
        reason = self.reason_var.get().strip() or None # Store None if empty
        status = self.status_var.get()
        notes = self.notes_text.get("1.0", tk.END).strip() if self.notes_text else ""

        # Convert date string to ensure correct format for DB
        try:
            appt_date_obj = datetime.strptime(appt_date_str, '%Y-%m-%d').date()
        except ValueError:
            self.show_error("Invalid date format. Please use YYYY-MM-DD.")
            return

        appointment_data = {
            "patient_id": patient_id,
            "appointment_date": appt_date_obj, # Use date object
            "start_time": start_time,
            "end_time": end_time,
            "reason": reason,
            "status": status,
            "notes": notes
        }

        if not self.conn:
            self.show_error("Database connection is not available.")
            return

        try:
            cursor = self.conn.cursor()
            if self.selected_appointment_id is not None:
                # --- UPDATE existing appointment ---
                print(f"Updating appointment ID: {self.selected_appointment_id}") # Debug
                query = """
                    UPDATE appointments
                    SET patient_id = :patient_id,
                        appointment_date = :appointment_date,
                        start_time = :start_time,
                        end_time = :end_time,
                        reason = :reason,
                        status = :status,
                        notes = :notes
                        -- updated_at is handled by trigger
                    WHERE id = :id
                """
                appointment_data['id'] = self.selected_appointment_id
                cursor.execute(query, appointment_data)
                self.conn.commit()

                if cursor.rowcount > 0:
                    self.show_status(f"Appointment ID {self.selected_appointment_id} updated successfully.")
                    # Keep form populated, update list
                    self.update_appointments_list()
                    # Reselect the updated item in the tree? Optional.
                    if self.appointments_tree:
                         try:
                             self.appointments_tree.selection_set(str(self.selected_appointment_id))
                             self.appointments_tree.focus(str(self.selected_appointment_id))
                             self.appointments_tree.see(str(self.selected_appointment_id))
                         except tk.TclError:
                             print(f"Could not re-select item {self.selected_appointment_id} after update.")
                else:
                    # This case might happen if the ID was valid but deleted just before update
                    self.show_error(f"Failed to update. Appointment ID {self.selected_appointment_id} might no longer exist.")
                    self.selected_appointment_id = None # Clear ID as it's invalid now
                    self.update_appointments_list() # Refresh list

            else:
                # --- INSERT new appointment ---
                print("Inserting new appointment.") # Debug
                query = """
                    INSERT INTO appointments (patient_id, appointment_date, start_time, end_time, reason, status, notes)
                    VALUES (:patient_id, :appointment_date, :start_time, :end_time, :reason, :status, :notes)
                """
                cursor.execute(query, appointment_data)
                new_appointment_id = cursor.lastrowid # Get the ID of the newly inserted row
                self.conn.commit()

                if new_appointment_id:
                    self.show_status(f"New appointment (ID: {new_appointment_id}) saved successfully.")
                    self.update_appointments_list() # Refresh list to show the new appointment
                    self.clear_form_for_new_appointment(clear_patient=False) # Clear form for next entry
                     # Optionally select the newly added item
                    if self.appointments_tree:
                         try:
                             self.appointments_tree.selection_set(str(new_appointment_id))
                             self.appointments_tree.focus(str(new_appointment_id))
                             self.appointments_tree.see(str(new_appointment_id))
                             # Load the newly created appointment back into the form?
                             # self.selected_appointment_id = new_appointment_id
                             # self._load_appointment_details_to_form()
                         except tk.TclError:
                             print(f"Could not select newly added item {new_appointment_id}.")

                else:
                    self.show_error("Failed to save the new appointment. No ID returned.")

        except sqlite3.IntegrityError as e:
            # Handle potential constraint violations (e.g., foreign key if patient_id is invalid)
            self.log_error(f"Database Integrity Error saving appointment: {e}", show_popup=True)
            self.conn.rollback()
        except sqlite3.Error as e:
            self.log_error(f"Database error saving appointment: {e}", show_popup=True)
            self.conn.rollback()
        except Exception as e:
            self.log_error(f"Unexpected error saving appointment: {e}", show_popup=True)
            if self.conn: self.conn.rollback() # Ensure rollback on any exception


    def _validate_form_data(self) -> bool:
        """Performs basic validation on the appointment form fields."""
        # 1. Patient Selected?
        if self.selected_patient_id is None:
            self.show_error("No patient selected. Please search and select a patient first.")
            return False
        try:
            int(self.patient_id_var.get()) # Check if ID is still valid integer
        except ValueError:
             self.show_error("Invalid Patient ID in form. Please re-select the patient.")
             return False

        # 2. Date Valid?
        date_str = self.date_var.get()
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            self.show_error("Invalid Date format. Please use YYYY-MM-DD or the date picker.")
            if self.date_entry: self.date_entry.focus_set()
            return False

        # 3. Start Time Selected?
        if not self.start_time_var.get():
            self.show_error("Please select a Start Time for the appointment.")
            if self.start_time_combo: self.start_time_combo.focus_set()
            return False

        # 4. Status Selected? (Should always have a value due to default and readonly)
        if not self.status_var.get():
            self.show_error("Please select a Status for the appointment.")
            if self.status_combo: self.status_combo.focus_set()
            return False # Should not happen

        # 5. Optional: Reason Selected? (Depends on requirements)
        # if not self.reason_var.get():
        #     if messagebox.askyesno("Missing Reason", "No reason for the appointment is selected. Continue anyway?", parent=self.parent):
        #         pass # Allow saving without reason
        #     else:
        #         if self.reason_combo: self.reason_combo.focus_set()
        #         return False # Stop saving

        # 6. Optional: End Time validation (e.g., ensure end > start if end is provided)
        start_time_str = self.start_time_var.get()
        end_time_str = self.end_time_var.get()
        if start_time_str and end_time_str:
            try:
                start_dt = datetime.strptime(start_time_str, '%H:%M')
                end_dt = datetime.strptime(end_time_str, '%H:%M')
                if end_dt <= start_dt:
                    self.show_error("End Time must be after Start Time.")
                    if self.end_time_combo: self.end_time_combo.focus_set()
                    return False
            except ValueError:
                self.show_error("Invalid Start or End Time format.") # Should not happen with combobox
                return False

        # Add more specific validations as needed (e.g., check for overlapping appointments)

        return True # All checks passed

    def clear_form_for_new_appointment(self, clear_patient: bool = True):
        """Clears the appointment form fields, optionally keeping patient info."""
        self.selected_appointment_id = None # Always clear appointment ID when clearing form

        # Clear appointment-specific fields
        self.date_var.set(datetime.now().strftime('%Y-%m-%d')) # Reset date to today
        self.start_time_var.set("")
        self.end_time_var.set("")
        self.reason_var.set("")
        self.status_var.set(STATUS_CONFIRMED) # Reset status to default

        if self.notes_text:
            self.notes_text.delete("1.0", tk.END)
            self.notes_text.edit_reset() # Clear undo stack

        # Clear patient fields only if requested
        if clear_patient:
            self.patient_id_var.set("")
            self.patient_name_var.set("")
            self.selected_patient_id = None

        # Optionally set focus to the first editable field (e.g., date or reason)
        # if self.date_entry: self.date_entry.focus_set()
        self.show_status("Form cleared. Ready for new appointment entry.")


    # --------------------------------------------------------------------------
    # Utility and Logging Methods
    # --------------------------------------------------------------------------

    def show_status(self, message: str, clear_after: Optional[int] = None):
        """Displays a message in the status bar."""
        self.status_message.set(message)
        print(f"Status: {message}") # Also print to console for logging
        if clear_after:
            # Schedule clearing the status bar after 'clear_after' milliseconds
            self.parent.after(clear_after, lambda: self.status_message.set("") if self.status_message.get() == message else None)

    def show_error(self, message: str, clear_after: Optional[int] = None):
        """Displays an error message in the status bar and logs it."""
        full_message = f"Error: {message}"
        self.status_message.set(full_message)
        print(f"ERROR: {message}") # Log error to console
        # Optionally show a messagebox for critical errors, but status bar is less intrusive
        # messagebox.showerror("Error", message, parent=self.parent)
        if clear_after:
            self.parent.after(clear_after, lambda: self.status_message.set("") if self.status_message.get() == full_message else None)


    def log_error(self, message: str, show_popup: bool = False):
        """Logs an error message and optionally shows a popup."""
        print(f"ERROR: {message}") # Always print to console
        self.status_message.set(f"Error: {message.splitlines()[0]}") # Show first line in status
        if show_popup:
            messagebox.showerror("Error", message, parent=self.parent)

if __name__ == "__main__":
    root = tk.Tk()
    app = OphthalmologyEMR(root)
    root.mainloop()






