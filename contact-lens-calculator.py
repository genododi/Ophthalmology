import tkinter as tk
from tkinter import ttk, messagebox
import math
from datetime import datetime
import sqlite3
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

class ContactLensCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("Dr Mahmoud Sami Contact Lens Prescription Calculator")
        self.root.geometry("850x750")
        
        # Initialize database
        self.init_database()
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Patient Information
        ttk.Label(main_frame, text="Patient Information", font=('Arial', 12, 'bold')).grid(row=0, column=0, columnspan=4, pady=10)
        ttk.Label(main_frame, text="Patient Name:").grid(row=1, column=0, sticky=tk.W)
        self.patient_name = ttk.Entry(main_frame, width=30)
        self.patient_name.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        # Search Button
        ttk.Button(main_frame, text="Search History",
                  command=self.search_history).grid(row=1, column=3, padx=5)
        
        # Right Eye (OD) Frame
        od_frame = ttk.LabelFrame(main_frame, text="Right Eye (OD)", padding="10")
        od_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=10, sticky=tk.W)
        
        ttk.Label(od_frame, text="Sphere:").grid(row=0, column=0)
        self.od_sphere = ttk.Entry(od_frame, width=10)
        self.od_sphere.grid(row=0, column=1)
        
        ttk.Label(od_frame, text="Cylinder:").grid(row=1, column=0)
        self.od_cylinder = ttk.Entry(od_frame, width=10)
        self.od_cylinder.grid(row=1, column=1)
        
        ttk.Label(od_frame, text="Axis:").grid(row=2, column=0)
        self.od_axis = ttk.Entry(od_frame, width=10)
        self.od_axis.grid(row=2, column=1)
        
        self.od_spherical_equiv = tk.BooleanVar()
        ttk.Checkbutton(od_frame, text="Use Spherical Equivalent",
                       variable=self.od_spherical_equiv).grid(row=3, column=0, columnspan=2, pady=5, sticky=tk.W)
        
        # Left Eye (OS) Frame
        os_frame = ttk.LabelFrame(main_frame, text="Left Eye (OS)", padding="10")
        os_frame.grid(row=2, column=2, columnspan=2, padx=5, pady=10, sticky=tk.W)
        
        ttk.Label(os_frame, text="Sphere:").grid(row=0, column=0)
        self.os_sphere = ttk.Entry(os_frame, width=10)
        self.os_sphere.grid(row=0, column=1)
        
        ttk.Label(os_frame, text="Cylinder:").grid(row=1, column=0)
        self.os_cylinder = ttk.Entry(os_frame, width=10)
        self.os_cylinder.grid(row=1, column=1)
        
        ttk.Label(os_frame, text="Axis:").grid(row=2, column=0)
        self.os_axis = ttk.Entry(os_frame, width=10)
        self.os_axis.grid(row=2, column=1)
        
        self.os_spherical_equiv = tk.BooleanVar()
        ttk.Checkbutton(os_frame, text="Use Spherical Equivalent",
                       variable=self.os_spherical_equiv).grid(row=3, column=0, columnspan=2, pady=5, sticky=tk.W)
        
        # Buttons Frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=3, column=0, columnspan=4, pady=20)
        
        ttk.Button(buttons_frame, text="Calculate", 
                  command=self.calculate).grid(row=0, column=0, padx=5)
        ttk.Button(buttons_frame, text="Save Prescription",
                  command=self.save_prescription).grid(row=0, column=1, padx=5)
        ttk.Button(buttons_frame, text="Export to PDF",
                  command=self.export_to_pdf).grid(row=0, column=2, padx=5)
        
        # Results Frame
        results_frame = ttk.LabelFrame(main_frame, text="Contact Lens Prescription", padding="10")
        results_frame.grid(row=4, column=0, columnspan=4, pady=10, sticky=(tk.W, tk.E))
        
        self.result_text = tk.Text(results_frame, height=8, width=50)
        self.result_text.grid(row=0, column=0, padx=5, pady=5)
        
        # History Frame
        history_frame = ttk.LabelFrame(main_frame, text="Prescription History", padding="10")
        history_frame.grid(row=5, column=0, columnspan=4, pady=10, sticky=(tk.W, tk.E))
        
        # Create Treeview for history
        self.history_tree = ttk.Treeview(history_frame, columns=("Date", "OD Sphere", "OD Cylinder", "OD Axis", 
                                                               "OS Sphere", "OS Cylinder", "OS Axis"), 
                                       show="headings", height=6)
        
        # Set column headings
        self.history_tree.heading("Date", text="Date")
        self.history_tree.heading("OD Sphere", text="OD Sphere")
        self.history_tree.heading("OD Cylinder", text="OD Cylinder")
        self.history_tree.heading("OD Axis", text="OD Axis")
        self.history_tree.heading("OS Sphere", text="OS Sphere")
        self.history_tree.heading("OS Cylinder", text="OS Cylinder")
        self.history_tree.heading("OS Axis", text="OS Axis")
        
        # Set column widths
        for col in self.history_tree["columns"]:
            self.history_tree.column(col, width=100)
        
        self.history_tree.grid(row=0, column=0, sticky="nsew")
        
        # Add scrollbar for history
        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.history_tree.configure(yscrollcommand=scrollbar.set)

    def search_history(self):
        """Search and display prescription history for the current patient"""
        name = self.patient_name.get()
        if not name:
            messagebox.showerror("Error", "Please enter patient name")
            return
            
        # Clear current history display
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
            
        try:
            # Get all prescriptions for this patient, ordered by date
            self.cursor.execute('''
                SELECT date, od_sphere, od_cylinder, od_axis, 
                       os_sphere, os_cylinder, os_axis 
                FROM prescriptions 
                WHERE patient_name = ? 
                ORDER BY date DESC
            ''', (name,))
            
            prescriptions = self.cursor.fetchall()
            
            if not prescriptions:
                messagebox.showinfo("Info", "No prescription history found for this patient")
                return
                
            # Add prescriptions to treeview
            for prescription in prescriptions:
                self.history_tree.insert("", "end", values=prescription)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to retrieve prescription history: {str(e)}")
            
    def init_database(self):
        """Initialize SQLite database"""
        self.conn = sqlite3.connect('prescriptions.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS prescriptions (
                id INTEGER PRIMARY KEY,
                patient_name TEXT,
                date TEXT,
                od_sphere REAL,
                od_cylinder REAL,
                od_axis INTEGER,
                os_sphere REAL,
                os_cylinder REAL,
                os_axis INTEGER
            )
        ''')
        self.conn.commit()

    def save_prescription(self):
        """Save prescription to database"""
        try:
            name = self.patient_name.get()
            if not name:
                messagebox.showerror("Error", "Please enter patient name")
                return
                
            od_sphere = float(self.od_sphere.get() or 0)
            od_cylinder = float(self.od_cylinder.get() or 0)
            od_axis = int(self.od_axis.get() or 0)
            os_sphere = float(self.os_sphere.get() or 0)
            os_cylinder = float(self.os_cylinder.get() or 0)
            os_axis = int(self.os_axis.get() or 0)
            
            self.cursor.execute('''
                INSERT INTO prescriptions 
                (patient_name, date, od_sphere, od_cylinder, od_axis, os_sphere, os_cylinder, os_axis)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, datetime.now().strftime('%Y-%m-%d'), 
                 od_sphere, od_cylinder, od_axis, 
                 os_sphere, os_cylinder, os_axis))
            self.conn.commit()
            messagebox.showinfo("Success", "Prescription saved successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save prescription: {str(e)}")

    def export_to_pdf(self):
        """Export prescription to PDF with proper identification of Toric lenses"""
        try:
            name = self.patient_name.get()
            if not name:
                messagebox.showerror("Error", "Please enter patient name")
                return
            
            # Calculate contact lens prescription
            od_sphere_input = float(self.od_sphere.get() or 0)
            od_cylinder_input = float(self.od_cylinder.get() or 0)
            od_axis_input = self.od_axis.get() or '0'
            
            os_sphere_input = float(self.os_sphere.get() or 0)
            os_cylinder_input = float(self.os_cylinder.get() or 0)
            os_axis_input = self.os_axis.get() or '0'
            
            # Calculate contact lens values
            od_sphere_cl, od_cylinder_cl = self.calculate_contact_lens_power(
                od_sphere_input, 
                od_cylinder_input,
                self.od_spherical_equiv.get()
            )
            
            os_sphere_cl, os_cylinder_cl = self.calculate_contact_lens_power(
                os_sphere_input,
                os_cylinder_input,
                self.os_spherical_equiv.get()
            )
                
            filename = f"prescription_{name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
            c = canvas.Canvas(filename, pagesize=letter)
            
            # Header
            c.setFont("Times-Bold", 16)
            c.drawString(1*inch, 10*inch, "Dr Mahmoud Sami Ophthalmology clinic")
            
            # Date
            c.setFont("Times-Roman", 12)
            c.drawString(1*inch, 9.5*inch, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
            
            # Patient Info
            c.drawString(1*inch, 9*inch, f"Patient Name: {name}")
            
            # Glasses Prescription
            c.setFont("Times-Bold", 12)
            c.drawString(1*inch, 8.5*inch, "Glasses Prescription:")
            
            c.setFont("Times-Roman", 12)
            # Right Eye Glasses
            c.drawString(1*inch, 8*inch, "Right Eye (OD):")
            c.drawString(1.5*inch, 7.7*inch, f"Sphere: {od_sphere_input:+.2f}")
            c.drawString(1.5*inch, 7.4*inch, f"Cylinder: {od_cylinder_input:+.2f}")
            c.drawString(1.5*inch, 7.1*inch, f"Axis: {od_axis_input}")
            
            # Left Eye Glasses
            c.drawString(1*inch, 6.7*inch, "Left Eye (OS):")
            c.drawString(1.5*inch, 6.4*inch, f"Sphere: {os_sphere_input:+.2f}")
            c.drawString(1.5*inch, 6.1*inch, f"Cylinder: {os_cylinder_input:+.2f}")
            c.drawString(1.5*inch, 5.8*inch, f"Axis: {os_axis_input}")
            
            # Contact Lens Prescription - Moved up to create more space
            c.setFont("Times-Bold", 12)
            c.drawString(1*inch, 5.3*inch, "Contact Lens Prescription:")
            
            c.setFont("Times-Roman", 12)
            # Right Eye Contact Lens
            c.drawString(1*inch, 4.8*inch, "Right Eye (OD):")
            if self.od_spherical_equiv.get() or (od_cylinder_cl == 0):
                c.drawString(1.5*inch, 4.5*inch, "Spherical Contact Lens")
                c.drawString(1.5*inch, 4.2*inch, f"Power: {od_sphere_cl:+.2f}")
            else:
                c.drawString(1.5*inch, 4.5*inch, "Toric Contact Lens")
                c.drawString(1.5*inch, 4.2*inch, f"Sphere: {od_sphere_cl:+.2f}")
                c.drawString(1.5*inch, 3.9*inch, f"Cylinder: {od_cylinder_cl:+.2f}")
                c.drawString(1.5*inch, 3.6*inch, f"Axis: {od_axis_input}")
            
            # Left Eye Contact Lens
            c.drawString(1*inch, 3.2*inch, "Left Eye (OS):")
            if self.os_spherical_equiv.get() or (os_cylinder_cl == 0):
                c.drawString(1.5*inch, 2.9*inch, "Spherical Contact Lens")
                c.drawString(1.5*inch, 2.6*inch, f"Power: {os_sphere_cl:+.2f}")
            else:
                c.drawString(1.5*inch, 2.9*inch, "Toric Contact Lens")
                c.drawString(1.5*inch, 2.6*inch, f"Sphere: {os_sphere_cl:+.2f}")
                c.drawString(1.5*inch, 2.3*inch, f"Cylinder: {os_cylinder_cl:+.2f}")
                c.drawString(1.5*inch, 2.0*inch, f"Axis: {os_axis_input}")
            
            # Notes - Increased spacing from Contact Lens Prescription
            c.setFont("Times-Bold", 12)
            c.drawString(1*inch, 1.5*inch, "Notes:")  # Moved down from 1.8 inch to create more space
            c.setFont("Times-Roman", 10)
            
            # Add notes about high prescription and lens types
            notes_y = 1.3  # Moved down from 1.6 to maintain spacing with Notes header
            if abs(od_sphere_cl) > 5.0 or abs(os_sphere_cl) > 5.0:
                c.drawString(1*inch, notes_y*inch, "• High prescription detected. Please consult with eye care professional.")
                notes_y -= 0.2
            
            if not self.od_spherical_equiv.get() and od_cylinder_cl != 0:
                c.drawString(1*inch, notes_y*inch, "• Right eye requires Toric contact lens for astigmatism correction.")
                notes_y -= 0.2
            
            if not self.os_spherical_equiv.get() and os_cylinder_cl != 0:
                c.drawString(1*inch, notes_y*inch, "• Left eye requires Toric contact lens for astigmatism correction.")
                notes_y -= 0.2
            
            # Footer
            c.setFont("Times-Roman", 10)
            c.drawString(1*inch, 0.75*inch, "This contact lens prescription is valid for one year, for inquires contact Dr Mahmoud")
            
            c.save()
            messagebox.showinfo("Success", f"PDF exported successfully as {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export PDF: {str(e)}")
        
    def calculate_contact_lens_power(self, sphere, cylinder, use_spherical_equiv=False):
        """
        Convert glasses prescription to contact lens prescription
        High myopia (< -5.00) and high hyperopia (> +5.00) require special consideration
        """
        try:
            sphere = float(sphere) if sphere else 0
            cylinder = float(cylinder) if cylinder else 0
            
            # Vertex distance compensation for high prescriptions
            if abs(sphere) >= 4.0:
                # Vertex distance formula for power > ±4.00D
                vertex_power = sphere / (1 - (0.012 * sphere))
                sphere = self.round_to_quarter(vertex_power)
            
            # For astigmatism, we typically reduce cylinder power by 10-20%
            if cylinder != 0:
                cylinder = self.round_to_quarter(cylinder * 0.9)  # 10% reduction
            
            # Calculate spherical equivalent if requested
            if use_spherical_equiv and cylinder != 0:
                sphere = self.calculate_spherical_equivalent(sphere, cylinder)
                cylinder = 0
            # Otherwise, only convert to spherical equivalent for low astigmatism
            elif abs(cylinder) <= 0.75:
                sphere = self.calculate_spherical_equivalent(sphere, cylinder)
                cylinder = 0
                
            return sphere, cylinder
            
        except ValueError:
            return None, None
        
    def round_to_quarter(self, number):
        """Round to the nearest 0.25"""
        quarters = int(number * 4)
        return quarters / 4.0

    def calculate_spherical_equivalent(self, sphere, cylinder):
        """Calculate spherical equivalent"""
        if sphere is not None and cylinder is not None:
            return self.round_to_quarter(sphere + (cylinder / 2))
        return sphere

    def calculate(self):
        """Calculate and display contact lens prescription"""
        try:
            # Get values from input fields
            name = self.patient_name.get()
            
            # Calculate OD (Right Eye)
            od_sphere, od_cylinder = self.calculate_contact_lens_power(
                self.od_sphere.get(), 
                self.od_cylinder.get(),
                self.od_spherical_equiv.get()
            )
            
            # Calculate OS (Left Eye)
            os_sphere, os_cylinder = self.calculate_contact_lens_power(
                self.os_sphere.get(), 
                self.os_cylinder.get(),
                self.os_spherical_equiv.get()
            )
            
            # Clear previous results
            self.result_text.delete('1.0', tk.END)
            
            # Display results
            result = f"Patient: {name}\n\n"
            result += "Right Eye (OD):\n"
            if od_sphere is not None:
                result += f"Sphere: {od_sphere:+.2f} "
                if od_cylinder and od_cylinder != 0:
                    result += f"Cylinder: {od_cylinder:+.2f} Axis: {self.od_axis.get()}"
                if self.od_spherical_equiv.get():
                    result += " (Spherical Equivalent)"
                result += "\n"
            
            result += "\nLeft Eye (OS):\n"
            if os_sphere is not None:
                result += f"Sphere: {os_sphere:+.2f} "
                if os_cylinder and os_cylinder != 0:
                    result += f"Cylinder: {os_cylinder:+.2f} Axis: {self.os_axis.get()}"
                if self.os_spherical_equiv.get():
                    result += " (Spherical Equivalent)"
                result += "\n"
            
            # Add warnings for high prescriptions
            if any(abs(x) > 5.0 for x in [od_sphere, os_sphere] if x is not None):
                result += "\nNote: High prescription detected. Recommend consultation with eye care professional."
            
            self.result_text.insert('1.0', result)
            
        except ValueError as e:
            messagebox.showerror("Error", "Please enter valid numbers for prescription values.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ContactLensCalculator(root)
    root.mainloop()
