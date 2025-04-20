# Add version system at the top of the file
__version__ = "1.0.0"

import csv
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, font, simpledialog
from datetime import datetime, timedelta
from Bio import Entrez
from Bio import Medline
from time import sleep  # Add for rate limiting
import threading
import webbrowser
from datetime import datetime, date, timedelta
import re
import time
import json
import urllib.request
import urllib.error
import ssl
import hashlib
import tempfile
import shutil
import subprocess
import logging
from tkinter import filedialog, messagebox
import xlsxwriter
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from Bio import Entrez, Medline
import pandas as pd
from collections import Counter
import urllib3
import calendar

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='ophthopapers.log',
    filemode='a'
)
logger = logging.getLogger(__name__)

try:
    from Bio import Entrez
    import tkinter as tk
    from tkinter import ttk
    import pandas as pd
    import numpy as np
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Please install the required packages using:")
    print("pip install biopython pandas numpy")
    sys.exit(1)

def extract_date_from_pubmed(record):
    """
    Extract and parse publication date from PubMed record
    Returns a tuple of (date_string, datetime_object)
    """
    # Try to get the most accurate date available
    # Priority: Electronic Publication Date > Created Date > Modified Date > Publication Date
    date_str = record.get('DEP', record.get('EDAT', record.get('MHDA', record.get('DP', 'Unknown date'))))
    
    # Handle unknown date
    if date_str == 'Unknown date':
        return date_str, datetime(1900, 1, 1)  # fallback
    
    # Try to extract a valid date for sorting
    date_obj = None
    
    # Try ISO format like 2023-01-01
    if '-' in date_str:
        try:
            parts = date_str.split('-')
            if len(parts) >= 3:
                date_obj = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
            elif len(parts) == 2:
                # Handle YYYY-MM format
                date_obj = datetime(int(parts[0]), int(parts[1]), 1)
        except ValueError:
            pass
    
    # Try format like 2023/01/01
    if not date_obj and '/' in date_str:
        try:
            parts = date_str.split('/')
            if len(parts) >= 3:
                date_obj = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
            elif len(parts) == 2:
                # Handle YYYY/MM format
                date_obj = datetime(int(parts[0]), int(parts[1]), 1)
        except ValueError:
            pass
    
    # Try PubMed format like "2023 Jan 15" or "2023 Jan"
    if not date_obj:
        try:
            # Remove any additional text after the date
            date_parts = date_str.split()
            if len(date_parts) >= 3:
                year = int(date_parts[0])
                month_str = date_parts[1]
                # Convert month name to number
                month_dict = {
                    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                }
                month = month_dict.get(month_str[:3], 1)  # Default to January if month not recognized
                
                # Try to extract day, defaulting to 1 if not available
                day = 1
                if len(date_parts) >= 3:
                    try:
                        day = int(date_parts[2])
                    except ValueError:
                        pass  # Keep day as 1 if not a valid number
                
                date_obj = datetime(year, month, day)
            elif len(date_parts) == 2:
                # Handle "2023 Jan" format
                year = int(date_parts[0])
                month_str = date_parts[1]
                month_dict = {
                    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                }
                month = month_dict.get(month_str[:3], 1)
                date_obj = datetime(year, month, 1)
        except (ValueError, IndexError):
            pass
    
    # Last resort: try to extract basic date components
    if not date_obj:
        try:
            # Try to extract year, month, day from the beginning of the string
            year = int(date_str[:4]) if len(date_str) >= 4 else 1900
            month = int(date_str[5:7]) if len(date_str) >= 7 else 1
            day = int(date_str[8:10]) if len(date_str) >= 10 else 1
            date_obj = datetime(year, month, day)
        except ValueError:
            # If all else fails, use default date
            date_obj = datetime(1900, 1, 1)
    
    return date_str, date_obj

def fetch_recent_ophthalmology_articles(email, api_key=None, days_back=30, max_results=1000, min_impact_factor=0.0, subspecialty=None, today_only=False, month_only=False, search_keyword=None, specific_journal=None, specific_year=None):
    """
    Fetch recent ophthalmology articles from PubMed
    
    Parameters:
    - email: Required for NCBI API
    - api_key: NCBI API key (optional but recommended)
    - days_back: How many days to search back
    - max_results: Maximum number of results to return (default increased to 1000)
    - min_impact_factor: Minimum journal impact factor (0.0 = no filtering)
    - subspecialty: Ophthalmology subspecialty to filter by (None = no filtering)
    - today_only: If True, only fetch articles published today
    - month_only: If True, only fetch articles published this month
    - search_keyword: Specific keyword to search for in PubMed query
    - specific_journal: Specific journal to search for (by name or ISSN)
    - specific_year: Specific year to search for (YYYY format)
    """
    # Set email and API key (required by NCBI)
    Entrez.email = email
    if api_key:
        Entrez.api_key = api_key

    # Define ophthalmology journals list with ISSNs and impact factors
    journals = [
        # High-impact ophthalmology journals
        ('Ophthalmology', '0161-6420', 13.8),
        ('JAMA Ophthalmol', '2168-6165', 9.6),
        ('Prog Retin Eye Res', '1350-9462', 24.4),
        ('Am J Ophthalmol', '0002-9394', 5.8),
        ('Br J Ophthalmol', '0007-1161', 5.3),
        ('Retina', '0275-5408', 4.3),
        ('Invest Ophthalmol Vis Sci', '0146-0404', 5.6),
        ('Acta Ophthalmol', '1755-375X', 4.2),
        ('Cornea', '0277-3740', 3.2),
        ('Eye (Lond)', '0950-222X', 3.0),
        ('Graefes Arch Clin Exp Ophthalmol', '0721-832X', 3.7),
        ('J Cataract Refract Surg', '0886-3350', 5.2),
        ('J Refract Surg', '1081-597X', 3.8),
        ('J Glaucoma', '1057-0829', 2.6),
        ('Exp Eye Res', '0014-4835', 3.5),
        ('Ocul Surf', '1542-0124', 13.4),
        ('Surv Ophthalmol', '0039-6257', 9.1),
        ('Ophthalmol Retina', '2468-6530', 7.5),
        ('Ophthalmol Glaucoma', '2589-4196', 4.7),
        ('Ophthalmol Ther', '2193-8245', 4.9),
        # Additional ophthalmology journals
        ('Curr Eye Res', '0271-3683', 2.8),
        ('J Ophthalmol', '2090-004X', 1.9),
        ('Clin Ophthalmol', '1177-5467', 2.1),
        ('Indian J Ophthalmol', '0301-4738', 2.0),
        ('Can J Ophthalmol', '0008-4182', 2.5),
        ('Ophthalmic Res', '0030-3747', 2.4),
        ('Eur J Ophthalmol', '1120-6721', 2.1),
        ('J Ocul Pharmacol Ther', '1080-7683', 2.3),
        ('Curr Opin Ophthalmol', '1040-8738', 3.1),
        ('Ophthalmic Epidemiol', '0928-6586', 2.2),
        ('Ophthalmic Plast Reconstr Surg', '0740-9303', 1.8),
        ('Ophthalmic Surg Lasers Imaging Retina', '2325-8160', 1.7),
        ('Doc Ophthalmol', '0012-4486', 2.0),
        ('Int Ophthalmol', '0165-5701', 2.4),
        ('Semin Ophthalmol', '0882-0538', 1.5),
        ('Asia Pac J Ophthalmol', '2162-0989', 2.0),
        ('Clin Exp Ophthalmol', '1442-6404', 3.0),
        ('Middle East Afr J Ophthalmol', '0974-9233', 1.0),
        ('Transl Vis Sci Technol', '2164-2591', 2.5),
        ('Ophthalmic Genet', '1381-6810', 1.5),
        ('Mol Vis', '1090-0535', 2.0),
        ('J Vis', '1534-7362', 2.5),
        ('Vision Res', '0042-6989', 2.5),
        ('J Eye Movement Res', '1995-8692', 1.2),
        # Taylor & Francis ophthalmology journals
        ('Orbit', '0167-6830', 1.8),
        ('Current Eye Research', '0271-3683', 2.8),
        ('Current Medical Research and Opinion', '0300-7995', 2.9),
        ('Ophthalmic and Physiological Optics', '0275-5408', 3.0),
        ('Cutaneous and Ocular Toxicology', '1556-9527', 2.0),
        ('Journal of Toxicology: Cutaneous and Ocular Toxicology', '0731-3829', 1.5),
        ('Visual Neuroscience', '0952-5238', 1.7),
        ('Journal of Visual Communication in Medicine', '1745-3054', 1.0),
        ('International Journal of Ophthalmic Practice', '2044-5504', 0.8),
        ('Visual Cognition', '1350-6285', 1.4),
        ('Clinical and Experimental Optometry', '0816-4622', 2.2),
        # Additional Taylor & Francis ophthalmology and vision science journals
        ('Acta Ophthalmologica Scandinavica', '1395-3907', 3.2),
        ('Neuro-Ophthalmology', '0165-8107', 1.3),
        ('Ocular Immunology and Inflammation', '0927-3948', 2.7),
        ('Refractive Surgery', '0883-0444', 2.1),
        ('Strabismus', '0927-3972', 0.9),
        ('Journal of Neuro-Ophthalmology', '1070-8022', 2.3),
        ('Ophthalmic Plastic and Reconstructive Surgery', '0740-9303', 1.8),
        ('Seminars in Ophthalmology', '0882-0538', 1.5),
        ('International Ophthalmology Clinics', '0020-8167', 1.2),
        ('Journal of Pediatric Ophthalmology and Strabismus', '0191-3913', 1.3),
        ('Journal of Vision Impairment & Blindness', '0145-482X', 1.1),
        ('Optometry and Vision Science', '1040-5488', 2.1),
        ('Expert Review of Ophthalmology', '1746-9899', 2.5),
        ('Visual Development and Rehabilitation', '2374-6440', 0.9),
        ('Journal of Ophthalmic Vision Research', '2008-2010', 1.7),
        ('Ophthalmic Research', '0030-3747', 2.4),
        ('British and Irish Orthoptic Journal', '2516-3590', 0.8),
        ('Clinical Optometry', '1179-2752', 1.2),
        ('Advances in Ophthalmology and Visual System', '2374-9695', 1.0),
        ('Eye and Brain', '1179-2744', 1.9),
        ('Open Ophthalmology Journal', '1874-3641', 0.7),
        ('Journal of Optometry', '1888-4296', 2.0),
        ('Journal of Current Ophthalmology', '2452-2325', 1.6),
        # Healio ophthalmology journals
        ('Journal of Pediatric Ophthalmology and Strabismus', '0191-3913', 1.3),
        ('Ocular Surgery News', '8750-3085', 0.8),
        ('Primary Care Optometry News', '1081-6437', 0.7),
        ('Ocular Surgery News Europe/Asia-Pacific Edition', '1085-5629', 0.8),
        ('Ophthalmic Technology Assessment', '0162-0436', 1.0),
        ('International Journal of Eye Banking', '2193-4037', 0.9),
        ('Ophthalmic ASC', '2578-9740', 0.7),
    ]
    
    # List of general journals to exclude from the search
    excluded_journals = [
        'Nature', 'Science', 'NEJM', 'JAMA', 'Lancet', 'Nat Med', 'Cell', 'BMJ',
        '0028-0836', '0036-8075', '0028-4793', '0098-7484', '0140-6736', '1078-8956', '0092-8674', '0959-8138'
    ]
    
    # Create journal query string from our journals list (excluding general journals)
    filtered_journals = [(name, issn, impact) for name, issn, impact in journals 
                         if name not in excluded_journals and issn not in excluded_journals]
    
    # Filter by minimum impact factor if specified
    if min_impact_factor > 0:
        filtered_journals = [(name, issn, impact) for name, issn, impact in filtered_journals 
                            if impact >= min_impact_factor]
    
    # Create the journal query
    if specific_journal:
        # Handle specific journal search
        if specific_journal.lower() == "jama ophthalmology":
            # Special case for JAMA Ophthalmology
            journal_matches = [j for j in filtered_journals if j[0] == "JAMA Ophthalmol" or j[1] == "2168-6165"]
            journal_query = f'"{specific_journal}"[Journal]'
        else:
            # Search by name or ISSN
            journal_matches = [j for j in filtered_journals if specific_journal.lower() in j[0].lower() or specific_journal == j[1]]
            if journal_matches:
                journal_query = ' OR '.join([f'"{j[1]}"[ISSN]' for j in journal_matches])
    else:
        # Use all filtered journals
        journal_query = ' OR '.join([f'"{j[1]}"[ISSN]' for j in filtered_journals])
    
    # Set date range depending on mode
    today = datetime.today()
    
    if today_only:
        # Get today's date in YYYY/MM/DD format
        today_date = today.strftime('%Y/%m/%d')
        # Use the most specific date field for today-only filtering - Date of Publication [DP] + Date - Create [CRDT]
        date_query = f'("{today_date}"[Date - Publication] OR "{today_date}"[CRDT])'
        # Use exact today's date for search
        search_date_range = date_query
    elif month_only:
        # Get first day of current month
        first_day = datetime(today.year, today.month, 1).strftime('%Y/%m/%d')
        # Get current day
        current_day = today.strftime('%Y/%m/%d')
        date_query = f'"{first_day}"[Date - Publication] : "{current_day}"[Date - Publication]'
        search_date_range = f"{today.strftime('%Y/%m')}[PDAT]"  # Use month format
    elif specific_year:
        # If specific year is selected, use that year for the date range
        start_date = datetime(int(specific_year), 1, 1)
        end_date = datetime(int(specific_year), 12, 31)
        date_query = f'"{start_date.strftime("%Y/%m/%d")}"[Date - Publication] : "{end_date.strftime("%Y/%m/%d")}"[Date - Publication]'
        search_date_range = date_query
    else:
        # Calculate date range based on days_back
        end_date = today
        start_date = end_date - timedelta(days=days_back)
        date_query = f'"{start_date.strftime("%Y/%m/%d")}"[Date - Publication] : "{end_date.strftime("%Y/%m/%d")}"[Date - Publication]'
        search_date_range = date_query  # Use the full date range
    
    # Define exclusion terms
    exclusion_terms = {'reply', 'erratum', 'error', 'correction', 'letter', 'comment', 'response', 'correspondence'}
    
    # Enhanced subspecialty filters with MeSH terms and broader keyword coverage
    subspecialty_terms = {
        "cataract": {
            "mesh_terms": ['Cataract', 'Cataract Extraction', 'Phacoemulsification', 'Capsulorhexis', 'Lens, Crystalline', 'Lens Implantation, Intraocular'],
            "keywords": ['cataract', 'phacoemulsification', 'iol', 'intraocular lens', 'capsulorrhexis', 'capsular', 'pseudophakic', 'lens extraction', 'pciol', 'aciol', 'posterior capsule opacification', 'effective lens position']
        },
        "refractive": {
            "mesh_terms": ['Refractive Surgical Procedures', 'Keratomileusis, Laser In Situ', 'Photorefractive Keratectomy', 'Corneal Surgery, Laser', 'Presbyopia', 'Myopia'],
            "keywords": ['refractive', 'lasik', 'prk', 'smile', 'presbyopia', 'keratorefractive', 'wavefront', 'excimer', 'myopia', 'hyperopia', 'astigmatism', 'salk', 'corneal refractive', 'corneal topography', 'intracorneal rings', 'corneal inlays', 'refractive lens exchange', 'phakic iol']
        },
        "glaucoma": {
            "mesh_terms": ['Glaucoma', 'Glaucoma, Open-Angle', 'Glaucoma, Angle-Closure', 'Intraocular Pressure', 'Trabecular Meshwork', 'Filtering Surgery'],
            "keywords": ['glaucoma', 'tonometry', 'trabeculectomy', 'iop', 'intraocular pressure', 'visual field', 'trabecular', 'angle closure', 'open angle', 'ocular hypertension', 'migs', 'selective laser trabeculoplasty', 'slt', 'minimally invasive glaucoma surgery', 'aqueous humor', 'optic disc', 'visual field defect', 'optic nerve head']
        },
        "retina": {
            "mesh_terms": ['Retina', 'Retinal Diseases', 'Macular Degeneration', 'Diabetic Retinopathy', 'Retinal Vein Occlusion', 'Vitreous Body', 'Vitrectomy', 'Retinal Detachment'],
            "keywords": ['retina', 'macula', 'vitreous', 'amd', 'diabetic retinopathy', 'dr', 'vein occlusion', 'epiretinal membrane', 'erm', 'pdr', 'vitrectomy', 'anti-vegf', 'age-related macular degeneration', 'retinal detachment', 'vitreoretinal', 'retinal vein occlusion', 'retinal artery occlusion', 'cystoid macular edema', 'aflibercept', 'ranibizumab', 'bevacizumab', 'retinal ischemia', 'choroidal neovascularization', 'cnv', 'proliferative vitreoretinopathy']
        },
        "oculoplasty": {
            "mesh_terms": ['Eyelids', 'Orbit', 'Orbital Diseases', 'Ptosis', 'Blepharoplasty', 'Dacryocystorhinostomy', 'Entropion', 'Ectropion'],
            "keywords": ['oculoplasty', 'oculoplastic', 'eyelid', 'orbit', 'ptosis', 'blepharoplasty', 'dacryocystorhinostomy', 'dcr', 'entropion', 'ectropion', 'facial', 'orbital reconstruction', 'orbital fracture', 'orbital tumor', 'blepharospasm', 'grave\'s ophthalmopathy', 'thyroid eye disease', 'facial palsy', 'periocular', 'orbital decompression', 'botulinum toxin']
        },
        "uveitis": {
            "mesh_terms": ['Uveitis', 'Uveitis, Anterior', 'Uveitis, Posterior', 'Panuveitis', 'Inflammation', 'Vasculitis', 'Iritis'],
            "keywords": ['uveitis', 'iritis', 'choroiditis', 'panuveitis', 'inflammation', 'immunosuppressive', 'vasculitis', 'vitritis', 'scleritis', 'episcleritis', 'autoimmune', 'immune-mediated', 'immunomodulatory', 'intermediate uveitis', 'viral retinitis', 'posterior uveitis', 'anterior uveitis', 'ocular inflammation', 'sarcoidosis', 'behcet', 'vogt-koyanagi-harada']
        },
        "pediatrics": {
            "mesh_terms": ['Strabismus', 'Amblyopia', 'Retinopathy of Prematurity', 'Esotropia', 'Exotropia', 'Vision Disorders', 'Child'],
            "keywords": ['pediatric', 'amblyopia', 'strabismus', 'retinopathy of prematurity', 'rop', 'esotropia', 'exotropia', 'children', 'juvenile', 'infantile', 'accommodative', 'intermittent', 'binocular vision', 'ocular alignment', 'congenital cataract', 'pediatric glaucoma', 'childhood', 'alternating', 'hypertropia', 'prism']
        },
        "cornea": {
            "mesh_terms": ['Cornea', 'Corneal Diseases', 'Keratitis', 'Keratoconus', 'Corneal Transplantation', 'Descemet Stripping Endothelial Keratoplasty', 'Fuchs\' Endothelial Dystrophy'],
            "keywords": ['cornea', 'keratitis', 'keratoconus', 'corneal transplantation', 'dsek', 'dmek', 'dalk', 'fuchs dystrophy', 'corneal edema', 'corneal ulcer', 'corneal dystrophy', 'corneal cross-linking', 'corneal topography', 'corneal pachymetry', 'corneal endothelium', 'corneal epithelium', 'microbial keratitis', 'penetrating keratoplasty', 'endothelial keratoplasty', 'anterior lamellar keratoplasty']
        },
        "neuro": {
            "mesh_terms": ['Optic Nerve Diseases', 'Optic Neuritis', 'Papilledema', 'Pseudotumor Cerebri', 'Vision Disorders', 'Visual Fields'],
            "keywords": ['neuro-ophthalmology', 'optic neuritis', 'optic neuropathy', 'papilledema', 'pseudotumor cerebri', 'visual field', 'diplopia', 'ocular motility', 'nystagmus', 'cranial nerve', 'multiple sclerosis', 'intracranial hypertension', 'optic disc swelling', 'optic disc edema', 'optic atrophy', 'chiasm', 'pupil', 'visual pathway', 'idiopathic intracranial hypertension']
        }
    }
    
    # Subspecialty filters
    subspecialty_keywords = {
        'cataract': ['cataract', 'phacoemulsification', 'iol', 'intraocular lens', 'capsulorrhexis', 'capsular'],
        'refractive': ['refractive', 'lasik', 'prk', 'smile', 'presbyopia', 'keratorefractive', 'wavefront', 'excimer'],
        'glaucoma': ['glaucoma', 'tonometry', 'trabeculectomy', 'iop', 'intraocular pressure', 'visual field', 'trabecular', 'angle closure'],
        'retina': ['retina', 'macula', 'vitreous', 'amd', 'diabetic retinopathy', 'dr', 'vein occlusion', 'epiretinal membrane', 'erm', 'pdr', 'vitrectomy'],
        'oculoplasty': ['oculoplasty', 'oculoplastic', 'eyelid', 'orbit', 'ptosis', 'blepharoplasty', 'dacryocystorhinostomy', 'dcr', 'entropion', 'ectropion'],
        'uveitis': ['uveitis', 'iritis', 'choroiditis', 'panuveitis', 'inflammation', 'immunosuppressive', 'vasculitis', 'vitritis'],
        'pediatrics': ['pediatric', 'amblyopia', 'strabismus', 'retinopathy of prematurity', 'rop', 'esotropia', 'exotropia', 'children']
    }
    
    # Choose keywords based on subspecialty or use general ophthalmology keywords
    if subspecialty and subspecialty.lower() in subspecialty_terms:
        # If a subspecialty is selected, use both MeSH terms and keywords
        subspecialty_info = subspecialty_terms[subspecialty.lower()]
        
        # Create MeSH terms query with higher priority
        mesh_query = ' OR '.join([f'"{term}"[MeSH Terms]' for term in subspecialty_info["mesh_terms"]])
        
        # Create keywords query for title and abstract
        keyword_query = ' OR '.join([f'"{kw}"[Title/Abstract]' for kw in subspecialty_info["keywords"]])
        
        # Combine with (MeSH OR keyword) for better coverage
        subspecialty_query = f'({mesh_query} OR {keyword_query})'
        
        # Use subspecialty's keywords for relevance scoring
        relevance_keywords = subspecialty_info["keywords"]
    else:
        # Keywords to boost article relevance in general ophthalmology
        relevance_keywords = [
            'retina', 'cornea', 'glaucoma', 'cataract', 'refractive', 'surgery', 
            'macular degeneration', 'diabetic retinopathy', 'inflammation', 'infection', 
            'keratoconus', 'keratitis', 'uveitis', 'amblyopia', 'strabismus', 
            'presbyopia', 'keratoplasty', 'intravitreal', 'myopia'
        ]
        subspecialty_query = None
    
    # Add the search keyword to boost its priority if provided
    if search_keyword:
        specific_keyword_query = f'"{search_keyword}"[Title/Abstract]'
        # Add the keyword to our search to prioritize it in relevance calculation
        if search_keyword.lower() not in [k.lower() for k in relevance_keywords]:
            relevance_keywords.append(search_keyword)
    else:
        specific_keyword_query = None
    
    relevance_boost = ' OR '.join([f'"{kw}"[Title/Abstract]' for kw in relevance_keywords])
    
    # Construct the base query with journals and date range
    base_query = f'({journal_query}) AND ({search_date_range}) AND English[lang] AND ("Journal Article"[Publication Type])'
    
    # Add subspecialty filter if specified
    if subspecialty_query:
        base_query += f' AND ({subspecialty_query})'
    
    # Add the keyword search if provided - with extra priority
    if specific_keyword_query:
        # When searching by keyword, make it a requirement but maintain journal restriction
        search_query = f'({specific_keyword_query}) AND ({base_query})'
    else:
        # Otherwise use our general relevance boosting terms
        search_query = f'{base_query} AND ({relevance_boost})'
    
    # Add exclusion for general journals as a final check
    exclude_terms = ' NOT '.join([f'"{journal}"[Journal]' for journal in excluded_journals])
    search_query += f' NOT ({exclude_terms})'
    
    try:
        # Add error handling for API calls
        handle = Entrez.esearch(
            db='pubmed',
            term=search_query,
            retmax=max_results * 5 if not (today_only or month_only) else max_results * 20,  # Increased fetch size for all queries
            sort='pub_date',  # Sort by publication date, most recent first
            usehistory='y'  # Enable for large result sets
        )
        search_results = Entrez.read(handle)
        handle.close()

        # Get the list of PMIDs
        id_list = search_results["IdList"]
        
        if not id_list:
            logger.info(f"No articles found for query: {search_query}")
            return []
        
        # Batch processing with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                handle = Entrez.efetch(
                    db='pubmed',
                    id=id_list,
                    rettype='medline',
                    retmode='text'
                )
                records = Medline.parse(handle)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                sleep(2 ** attempt)  # Exponential backoff
        
        # Record list for sorting by date
        article_records = []
                
        for record in records:
            # Skip excluded content types
            title = record.get('TI', '').lower()
            if any(term in title for term in exclusion_terms):
                continue
        
            # Skip general journals
            journal_name = record.get('JT', 'Unknown journal')
            if journal_name in excluded_journals:
                continue

            # Enhanced DOI detection
            doi = next((id.split(' [doi]')[0] for id in record.get('AID', []) 
                      if id.endswith('[doi]')), 'N/A')
            
            # Create DOI URL
            doi_url = f'https://doi.org/{doi}' if doi != 'N/A' else ''
            
            # Process abstract
            abstract = record.get('AB', 'No abstract available')
            abstract_preview = abstract[:250] + '...' if len(abstract) > 250 else abstract

            # Add PubMed URL
            pmid = record.get('PMID', 'N/A')
            pubmed_url = f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/' if pmid != 'N/A' else ''
            
            # Get journal info including impact factor
            journal_issn = record.get('IS', 'N/A')
            
            # Get the accurate impact factor from our journal list
            impact_factor = next((j[2] for j in journals if j[1] == journal_issn or j[0] == journal_name), 0.0)
            
            # Double-check that this is from our predefined journal list - especially important for month_only
            if not specific_journal and not any(j[1] == journal_issn or j[0] == journal_name for j in journals):
                continue  # Skip articles not in our predefined journal list
            
            # Special handling for JAMA vs JAMA Ophthalmology
            if specific_journal and specific_journal.lower() == "jama ophthalmology":
                # If searching specifically for JAMA Ophthalmology, skip general JAMA articles
                if journal_name == "JAMA" or journal_issn == "0098-7484":
                    continue
            elif specific_journal and specific_journal.lower() == "jama":
                # If searching specifically for JAMA, skip JAMA Ophthalmology articles
                if journal_name == "JAMA ophthalmology" or journal_issn == "2168-6165":
                    continue
            
            # Check if article has a publication date
            try:
                # Try multiple date formats
                pub_date = record.get('DEP', record.get('EDAT', record.get('MHDA', record.get('DP', 'Unknown date'))))
                # Parse date for sorting
                if pub_date != 'Unknown date':
                    # Try to extract a valid date for sorting
                    if '-' in pub_date:  # ISO format like 2023-01-01
                        parts = pub_date.split('-')
                        if len(parts) >= 3:
                            date_obj = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                        else:
                            date_obj = datetime(1900, 1, 1)  # fallback
                    elif '/' in pub_date:  # Format like 2023/01/01
                        parts = pub_date.split('/')
                        if len(parts) >= 3:
                            date_obj = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                        else:
                            date_obj = datetime(1900, 1, 1)  # fallback
                    else:  # Try to extract year month day
                        year = int(pub_date[:4]) if len(pub_date) >= 4 else 1900
                        month = int(pub_date[5:7]) if len(pub_date) >= 7 else 1
                        day = int(pub_date[8:10]) if len(pub_date) >= 10 else 1
                        date_obj = datetime(year, month, day)
                else:
                    date_obj = datetime(1900, 1, 1)  # fallback
            except:
                date_obj = datetime(1900, 1, 1)  # fallback for parsing errors
            
            # Additional date filtering based on options
            # If today_only is True, check if the article was published today
            if today_only:
                # Super strict today-only check 
                article_date = date_obj.date()
                today_date = today.date()
                
                # If publication date is unknown or not today, skip
                if article_date != today_date:
                    # Double-check all possible date formats in the raw publication date string
                    pub_date_lower = pub_date.lower()
                    today_formats = [
                        today.strftime('%Y-%m-%d'),    # ISO format: 2023-10-25
                        today.strftime('%Y/%m/%d'),    # Slash format: 2023/10/25
                        f"{today.day} {today.strftime('%b')} {today.year}",  # Day Month Year: 25 Oct 2023
                        f"{today.strftime('%b')} {today.day}, {today.year}",  # Month Day, Year: Oct 25, 2023
                        today.strftime('%d.%m.%Y'),    # European format: 25.10.2023
                        today.strftime('%Y%m%d')       # Compact format: 20231025
                    ]
                    
                    # Check if any of today's date formats appear in the pub_date string
                    if not any(date_format in pub_date_lower for date_format in today_formats):
                        continue  # Skip this article as it's not published today
            
            # If month_only is True, check if the article was published this month
            if month_only:
                # More flexible month check: only compare year and month components
                if date_obj.year == today.year and date_obj.month == today.month:
                    pass  # Keep the article
                # Also check if the date string contains this month in various formats
                elif (f"{today.strftime('%Y-%m')}" in pub_date or 
                      f"{today.strftime('%Y/%m')}" in pub_date or
                      f"{today.strftime('%b')} {today.year}" in pub_date):
                    pass  # Keep the article
                else:
                    continue  # Skip this article

            article_data = {
                'title': record.get('TI', 'No title available'),
                'journal': journal_name,
                'impact_factor': impact_factor,
                'pub_date': pub_date,
                'date_obj': date_obj,  # For sorting, will be removed later
                'doi': doi,
                'doi_url': doi_url,
                'abstract_preview': abstract_preview,
                'full_abstract': abstract,
                'pmid': pmid,
                'authors': ', '.join(record.get('AU', [])),
                'pubmed_url': pubmed_url,
                'publication_type': ', '.join(record.get('PT', ['Unknown'])),
                'keywords': ', '.join(record.get('OT', []))
            }
            
            # Add relevance score based on keyword matching
            relevance_score = 0
            for keyword in relevance_keywords:
                if keyword.lower() in title.lower():
                    relevance_score += 3  # Higher weight for title matches
                if keyword.lower() in abstract.lower():
                    relevance_score += 1  # Lower weight for abstract matches
            
            article_data['relevance_score'] = relevance_score
            article_records.append(article_data)

        handle.close()
        
        # Sort by date (newest first) and then by relevance score
        # For month_only or today_only option, prioritize impact factor
        if month_only or today_only:
            # Sort by impact factor (highest first), then by date (newest first), then by relevance
            article_records.sort(key=lambda x: (-x['impact_factor'], -x['date_obj'].timestamp(), -x['relevance_score']))
        else:
            # Regular sorting: date first, then relevance
            article_records.sort(key=lambda x: (-x['date_obj'].timestamp(), -x['relevance_score'], -x['impact_factor']))
        
        # Remove the date_obj used for sorting
        for article in article_records:
            del article['date_obj']
        
        # Limit to max_results
        articles = article_records[:max_results]

        return articles

    except Exception as e:
        logger.error(f"Error fetching articles: {str(e)}")
        print(f"Error: {str(e)}")
        return []

def save_to_csv(articles, filename='ophthalmology_articles.csv'):
    """Save filtered articles to CSV"""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            # Updated fieldnames to include all fields
            fieldnames = ['title', 'authors', 'journal', 'impact_factor', 'pub_date', 
                         'doi', 'doi_url', 'pmid', 'pubmed_url', 'abstract_preview',
                         'full_abstract', 'keywords', 'publication_type', 'relevance_score']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(articles)
    except IOError as e:
        print(f"File save error: {str(e)}")

def save_to_txt(articles, filename='ophthalmology_articles.txt'):
    """Save filtered articles to a text file"""
    try:
        with open(filename, 'w', encoding='utf-8') as txtfile:
            txtfile.write(f"Ophthalmology Articles Report - Generated on {datetime.today().strftime('%Y-%m-%d')}\n\n")
            
            for idx, article in enumerate(articles, 1):
                txtfile.write(f"Article {idx}:\n")
                txtfile.write(f"Title: {article['title']}\n")
                txtfile.write(f"Authors: {article['authors']}\n")
                txtfile.write(f"Journal: {article['journal']} (Impact Factor: {article['impact_factor']:.1f})\n")
                txtfile.write(f"Publication Date: {article['pub_date']}\n")
                txtfile.write(f"DOI: {article['doi']}\n")
                txtfile.write(f"DOI URL: {article['doi_url']}\n")
                txtfile.write(f"PubMed URL: {article['pubmed_url']}\n")
                txtfile.write(f"Abstract:\n{article['full_abstract']}\n")
                txtfile.write(f"Keywords: {article['keywords']}\n")
                txtfile.write("\n" + "-"*80 + "\n\n")
        
        return filename
    except IOError as e:
        print(f"Text file save error: {str(e)}")
        return None

def save_to_excel(articles, filename='ophthalmology_articles.xlsx'):
    """Save filtered articles to Excel with clickable hyperlinks"""
    try:
        # Convert to pandas DataFrame
        df = pd.DataFrame(articles)
        
        # Create a Pandas Excel writer
        writer = pd.ExcelWriter(filename, engine='xlsxwriter')
        
        # Convert the dataframe to an XlsxWriter Excel object
        df.to_excel(writer, sheet_name='Articles', index=False)
        
        # Get the workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Articles']
        
        # Find the DOI URL column index
        doi_url_col = df.columns.get_loc('doi_url')
        
        # Add a URL format for the DOI links
        url_format = workbook.add_format({
            'font_color': 'blue',
            'underline': 1
        })
        
        # Write DOI URLs as hyperlinks
        for row_num, doi_url in enumerate(df['doi_url']):
            if doi_url and doi_url != '':
                worksheet.write_url(row_num + 1, doi_url_col, doi_url, url_format, string='Open DOI')
        
        # Same for PubMed URLs
        pubmed_url_col = df.columns.get_loc('pubmed_url')
        for row_num, pubmed_url in enumerate(df['pubmed_url']):
            if pubmed_url and pubmed_url != '':
                worksheet.write_url(row_num + 1, pubmed_url_col, pubmed_url, url_format, string='PubMed')
        
        # Auto-adjust column widths
        for col_num, col in enumerate(df.columns):
            column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(col_num, col_num, min(column_width, 50))  # Limit width to 50
        
        # Close the Pandas Excel writer
        writer.close()
        
        return filename
    except Exception as e:
        print(f"Excel file save error: {str(e)}")
        return None

def save_doi_urls(articles, filename='doi_urls.csv'):
    """Save only the DOI URLs to a CSV file with clickable hyperlinks"""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['title', 'doi', 'doi_url', 'hyperlink', 'journal', 'impact_factor']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            # Extract only the relevant fields and add Excel-compatible hyperlink formula
            doi_data = []
            for article in articles:
                if article['doi'] != 'N/A' and article['doi_url']:
                    excel_hyperlink = f'=HYPERLINK("{article["doi_url"]}", "Open DOI")'
                    doi_data.append({
                        'title': article['title'],
                        'doi': article['doi'],
                        'doi_url': article['doi_url'],
                        'hyperlink': excel_hyperlink,
                        'journal': article['journal'],
                        'impact_factor': article['impact_factor']
                    })
                else:
                    doi_data.append({
                        'title': article['title'],
                        'doi': article['doi'],
                        'doi_url': article['doi_url'],
                        'hyperlink': '',
                        'journal': article['journal'],
                        'impact_factor': article['impact_factor']
                    })
            writer.writerows(doi_data)
        return filename, len(doi_data)
    except IOError as e:
        print(f"File save error: {str(e)}")
        return filename, 0

def extract_keywords_from_text(text, existing_keywords=None):
    """
    Extract meaningful keywords from text using simple NLP techniques
    
    Parameters:
    - text: Text to analyze
    - existing_keywords: List of already identified keywords to avoid duplicates
    
    Returns:
    - List of extracted keywords
    """
    if not text:
        return []
        
    # Comprehensive list of ophthalmology-specific terms and abbreviations that should be prioritized
    ophtho_terms = {
        # Diseases and conditions
        'glaucoma', 'cataract', 'retinopathy', 'macular degeneration', 'amd', 'diabetic retinopathy', 'dr',
        'uveitis', 'keratoconus', 'myopia', 'hyperopia', 'astigmatism', 'presbyopia', 'dry eye', 'conjunctivitis',
        'amblyopia', 'strabismus', 'retinal detachment', 'retinitis pigmentosa', 'ocular hypertension',
        'pcv', 'cscr', 'crao', 'crvo', 'pdr', 'npdr', 'poag', 'dmek', 'dsaek', 'dalk', 'pek', 'iol',
        'endophthalmitis', 'scleritis', 'iritis', 'choroiditis', 'blepharitis', 'keratitis', 'maculopathy',
        'neuropathy', 'optic neuritis', 'papilledema', 'pterygium', 'pinguecula', 'chalazion', 'hordeolum',
        'stye', 'entropion', 'ectropion', 'trachoma', 'sjögren', 'graves', 'thyroid eye disease', 'ted',
        'fuchs dystrophy', 'retinoblastoma', 'melanoma', 'basal cell', 'squamous cell', 'lymphoma',
        'central serous', 'csr', 'age-related macular degeneration', 'armd', 'wet amd', 'dry amd', 'geographic atrophy',
        'panuveitis', 'anterior uveitis', 'posterior uveitis', 'intermediate uveitis', 'hla-b27', 'behcet',
        'ankylosing spondylitis', 'sarcoidosis', 'toxoplasmosis', 'toxocariasis', 'onchocerciasis',
        'vkh', 'vogt-koyanagi-harada', 'sympathetic ophthalmia', 'eales disease', 
        'exudative', 'drusen', 'pseudodrusen', 'pigment epithelial detachment', 'ped', 'rpe tear',
        'mactel', 'macular telangiectasia', 'angioid streaks', 'cnv', 'choroidal neovascularization',
        'cme', 'cystoid macular edema', 'dme', 'diabetic macular edema', 'cotton wool spots',
        'subretinal fluid', 'srf', 'intraretinal fluid', 'irf', 'hard exudates', 'hemorrhages',
        'microaneurysms', 'branch retinal vein occlusion', 'brvo', 'central retinal vein occlusion', 'crvo',
        'branch retinal artery occlusion', 'brao', 'central retinal artery occlusion', 'crao',
        'arteritic anterior ischemic optic neuropathy', 'aion', 'naion', 'non-arteritic',
        'papillitis', 'optic atrophy', 'optic neuropathy', 'lhon', 'leber hereditary optic neuropathy',
        'giant cell arteritis', 'temporal arteritis', 'pseudotumor cerebri', 'idiopathic intracranial hypertension',
        'iih', 'chiasmal compression', 'pituitary adenoma', 'meningioma', 'optic glioma', 'optic nerve sheath meningioma',
        'ocular surface disease', 'osd', 'meibomian gland dysfunction', 'mgd', 'blepharoconjunctivitis',
        'megalocornea', 'microcornea', 'cornea plana', 'cornea guttata', 'corneal opacity',
        'corneal scarring', 'corneal ulcer', 'corneal abrasion', 'recurrent corneal erosion', 'rce',
        'band keratopathy', 'acanthamoeba', 'herpes simplex keratitis', 'hsk', 'herpes zoster ophthalmicus', 'hzo',
        'exposure keratopathy', 'filamentary keratitis', 'neurotrophic keratitis', 'bullous keratopathy',
        
        # Anatomical structures
        'cornea', 'retina', 'macula', 'optic nerve', 'vitreous', 'choroid', 'sclera', 'conjunctiva', 'iris',
        'lens', 'anterior chamber', 'posterior chamber', 'fovea', 'limbus', 'trabecular meshwork',
        'ciliary body', 'zonules', 'eyelid', 'orbit', 'extraocular muscles', 'tear film', 'optic disc',
        'lamina cribrosa', 'schlemm canal', 'pupil', 'episclera', 'tenon capsule', 'bruch membrane',
        'bowman layer', 'descemet membrane', 'endothelium', 'epithelium', 'stroma', 'ora serrata',
        'retinal pigment epithelium', 'rpe', 'choriocapillaris', 'ganglion cell layer', 'gcl',
        'nerve fiber layer', 'nfl', 'inner nuclear layer', 'inl', 'outer nuclear layer', 'onl',
        'inner plexiform layer', 'ipl', 'outer plexiform layer', 'opl', 'inner limiting membrane', 'ilm',
        'outer limiting membrane', 'olm', 'ellipsoid zone', 'photoreceptors', 'rods', 'cones',
        'retinal nerve fiber layer', 'rnfl', 'bipolar cells', 'amacrine cells', 'horizontal cells',
        'müller cells', 'lacrimal gland', 'meibomian gland', 'punctum', 'canaliculus', 'nasolacrimal duct',
        'lacrimal sac', 'superior oblique', 'inferior oblique', 'lateral rectus', 'medial rectus',
        'superior rectus', 'inferior rectus', 'levator palpebrae superioris', 'orbital septum',
        'tarsal plate', 'lid margin', 'fornix', 'caruncle', 'plica semilunaris',
        
        # Treatments and procedures
        'phacoemulsification', 'trabeculectomy', 'vitrectomy', 'intravitreal', 'anti-vegf', 'photocoagulation',
        'femtosecond', 'lasik', 'prk', 'smile', 'crosslinking', 'cxl', 'keratoplasty', 'penetrating keratoplasty',
        'corneal transplant', 'dsaek', 'dmek', 'dalk', 'endothelial keratoplasty', 'slt', 'selective laser trabeculoplasty',
        'alt', 'argon laser trabeculoplasty', 'iridotomy', 'iridoplasty', 'cyclophotocoagulation', 'cyclocryotherapy',
        'panretinal photocoagulation', 'prp', 'focal laser', 'pars plana vitrectomy', 'ppv', 'mp', 'micropulse',
        'pneumatic retinopexy', 'scleral buckle', 'migs', 'minimally invasive glaucoma surgery',
        'express shunt', 'ahmed valve', 'baerveldt implant', 'molteno implant', 'gc', 'goniotomy',
        'trabeculotomy', 'canaloplasty', 'viscocanalostomy', 'deep sclerectomy', 'ab interno', 'ab externo',
        'trabectome', 'istent', 'cypass', 'xen gel stent', 'preserflo', 'hydrus', 'gonioscopy-assisted transluminal trabeculotomy', 'gatt',
        'dacryocystorhinostomy', 'dcr', 'conjunctivodacryocystorhinostomy', 'cdcr', 'jones tube',
        'ptosis repair', 'levator resection', 'frontalis sling', 'blepharoplasty', 'entropion repair',
        'ectropion repair', 'tarsorrhaphy', 'enucleation', 'evisceration', 'exenteration',
        'orbitotomy', 'orbital decompression', 'endoscopic', 'bevacizumab', 'avastin', 'ranibizumab',
        'lucentis', 'aflibercept', 'eylea', 'brolucizumab', 'beovu', 'pegaptanib', 'macugen', 'faricimab',
        'vabysmo', 'dexamethasone implant', 'ozurdex', 'fluocinolone implant', 'iluvien', 'yutiq',
        'triamcinolone', 'kenalog', 'triesence', 'photodynamic therapy', 'pdt', 'verteporfin', 'visudyne',
        'radiation therapy', 'brachytherapy', 'proton beam', 'transpupillary thermotherapy', 'ttt',
        'clear lens extraction', 'cle', 'refractive lens exchange', 'rle', 'posterior capsulotomy',
        'yag capsulotomy', 'punctal plug', 'punctal cautery', 'amniotic membrane', 'prokera',
        'autologous serum', 'platelet rich plasma', 'prp drops', 'bandage contact lens', 'scleral lens',
        'collagen crosslinking', 'riboflavin', 'uv-a', 'phototherapeutic keratectomy', 'ptk',
        'relaxing incisions', 'astigmatic keratotomy', 'ak', 'limbal relaxing incisions', 'lri',
        'arcuate keratotomy', 'kpro', 'keratoprosthesis', 'boston kpro', 'osteo-odonto-keratoprosthesis',
        'ookp', 'botulinum toxin', 'botox', 'lateral tarsal strip', 'lts', 'lateral canthal sling',
        'medial spindle', 'quickert sutures', 'everting sutures', 'mullerectomy', 'transconjunctival blepharoplasty',
        'transcutaneous blepharoplasty', 'browpexy', 'browplasty', 'canthoplasty', 'canthopexy',
        'face lift', 'rhytidectomy', 'silicone oil', 'perfluorocarbon liquid', 'pfcl', 'gas tamponade',
        'sf6', 'c3f8', 'air tamponade', 'membrane peel', 'ilm peel', 'internal limiting membrane',
        'epiretinal membrane', 'erm peel', 'macular hole repair', 'pneumatic displacement',
        'drainage retinotomy', 'retinectomy', 'laser demarcation', 'endolaser', 'prophylactic laser',
        'barrier laser', 'sector laser', 'grid laser', 'transscleral cyclophotocoagulation', 'micropulse tcp',
        'endocyclophotocoagulation', 'ecp', 'peripheral iridotomy', 'pi', 'laser peripheral iridotomy', 'lpi',
        'laser iridoplasty', 'plication', 'tucking', 'myectomy', 'faden', 'adjustable suture',
        'symblepharon release', 'pterygium excision', 'amniotic membrane graft', 'conjunctival autograft',
        'mitomycin c', 'mmx', '5-fluorouracil', '5-fu', 'collagen matrix', 'ologen', 'antimetabolite',
        'photorefractive keratectomy', 'small incision lenticule extraction', 'flap creation',
        'surface ablation', 'wavefront-guided', 'wavefront-optimized', 'topography-guided',
        'femtosecond lenticule extraction', 'flex', 'relex flex', 'relex smile',
        'accommodative', 'multifocal', 'toric', 'monofocal', 'extended depth of focus', 'edof',
        'presbyopia correcting', 'pc-iol', 'premium', 'piggyback', 'sulcus', 'bag', 'in-the-bag',
        'iol calculation', 'capsulorhexis', 'capsulorrhexis', 'continuous curvilinear capsulorhexis', 'ccc',
        'anterior vitrectomy', 'hydrodissection', 'hydrodelineation', 'divide and conquer',
        'stop and chop', 'phaco chop', 'horizontal chop', 'vertical chop', 'iris hook',
        'capsular tension ring', 'ctr', 'modified ctr', 'mctr', 'cionni ring', 'ahmed segment',
        
        # Diagnostic techniques
        'oct', 'octa', 'optical coherence tomography', 'angiography', 'fluorescein', 'icg', 'indocyanine green', 'perimetry',
        'visual field', 'topography', 'pachymetry', 'biometry', 'aberrometry', 'a-scan', 'b-scan',
        'ultrasound biomicroscopy', 'ubm', 'specular microscopy', 'confocal microscopy', 'in vivo confocal',
        'anterior segment oct', 'as-oct', 'corneal topography', 'scheimpflug', 'pentacam', 'orbscan',
        'corneal hysteresis', 'ocular response analyzer', 'ora', 'endothelial cell count', 'ecc',
        'humphrey visual field', 'hvf', 'swedish interactive thresholding algorithm', 'sita',
        'standard automated perimetry', 'sap', 'frequency doubling technology', 'fdt',
        'short wavelength automated perimetry', 'swap', 'blue on yellow', 'microperimetry', 'mp',
        'maia', 'goldman visual field', 'confrontation visual field', 'amsler grid', 'color vision',
        'ishihara', 'farnsworth', 'farnsworth-munsell', 'hue', 'color blindness', 'protanopia',
        'deuteranopia', 'tritanopia', 'electrophysiology', 'electroretinogram', 'erg', 'multifocal erg', 'mferg',
        'pattern erg', 'perg', 'visual evoked potential', 'vep', 'electrooculogram', 'eog',
        'dark adaptation', 'microperimetry', 'mp-1', 'fundus autofluorescence', 'faf', 'swaf', 'naf',
        'fluorescein angiography', 'fa', 'fundus fluorescein angiography', 'ffa', 'indocyanine green angiography', 'icga',
        'wide-field', 'ultra-widefield', 'optos', 'clarus', 'fundus photography', 'multicolor imaging',
        'infrared', 'ir', 'red-free', 'stereo', 'stereoscopic', 'adaptive optics', 'ao',
        'scanning laser ophthalmoscopy', 'slo', 'scanning laser polarimetry', 'gdx', 'nerve fiber analyzer',
        'heidelberg retina tomograph', 'hrt', 'retinal nerve fiber layer', 'rnfl analysis',
        'optical coherence tomography angiography', 'oct-a', 'octa', 'split-spectrum amplitude-decorrelation angiography', 'ssada',
        'anterior chamber optical coherence tomography', 'visante', 'pentacam', 'sirius', 'galilei',
        'cornea visualization scheimpflug technology', 'corvis st', 'ocular surface analyzer', 'keratograph',
        'lipiview', 'non-contact meibography', 'tear film break-up time', 'tfbut', 'fluorescein tbut',
        'non-invasive tear break-up time', 'nitbut', 'tear meniscus height', 'tmh', 'schirmer test',
        'phenol red thread test', 'prt', 'tear osmolarity', 'matrix metalloproteinase-9', 'mmp-9', 'inflammadry',
        'rose bengal staining', 'lissamine green', 'vital staining', 'tearlab', 'ocular surface disease index', 'osdi',
        'standard patient evaluation of eye dryness', 'speed', 'dry eye questionnaire', 'deq',
        'impact of dry eye on everyday life', 'ideel', 'national eye institute visual function questionnaire', 'nei-vfq',
        'rsk assessment', 'intraocular pressure', 'iop', 'goldmann applanation tonometry', 'gat',
        'non-contact tonometry', 'nct', 'air-puff tonometry', 'dynamic contour tonometry', 'dct',
        'rebound tonometry', 'icare', 'tono-pen', 'pneumatonometer', 'ocular response analyzer', 'ora',
        'corneal hysteresis', 'ch', 'corneal resistance factor', 'crf', 'pascal dynamic contour tonometry',
        'ocular pulse amplitude', 'opa', 'water drinking test', 'wdt', 'diurnal curve', 'phasing',
        'dark room provocative test', 'prone provocative test', 'gonioscopy', 'spaeth grading',
        'shaffer grading', 'indentation gonioscopy', 'trabecular meshwork', 'angle structures',
        'angle closure', 'synechiae', 'recession', 'sampaolesi line', 'schwalbe line', 'schlemm canal',
        'iris process', 'plateau iris', 'slit lamp biomicroscopy', 'slit lamp examination', 'sle',
        'dilated fundus examination', 'dfe', 'indirect ophthalmoscopy', 'direct ophthalmoscopy',
        '20d', '28d', '90d', '78d', 'contact lens examination', 'three-mirror', 'wide-field lens',
        'fundus contact lens', 'macular contact lens', 'handheld portable', 'binocular indirect ophthalmoscope', 'bio',
        'keratometry', 'wavefront aberrometry', 'refraction', 'manifest refraction', 'cycloplegic refraction',
        'trial frame', 'phoropter', 'autorefractor', 'keratometer', 'lensmeter', 'lensometer',
        'interferometry', 'immersion biometry', 'optical biometry', 'iol master', 'lenstar',
        'argon', 'krypton', 'micropulse', 'pascal', 'quantel', 'diode', 'pattern scanning laser', 'psl',
        'excimer', 'femtosecond', 'photodisruptive', 'alexandrite', 'nd:yag', 'neodymium-doped yttrium aluminum garnet',
        'erbium:yag', 'ktp', 'potassium titanyl phosphate', 'endolaser', 'indirect laser',
        'pan-retinal photocoagulation', 'focal laser', 'grid laser', 'sector laser', 'border laser',
        'barrier laser', 'feeder vessel', 'subthreshold', 'slt', 'alt', 'tlt', 'micropulse laser trabeculoplasty', 'mlt',
        
        # Other important terms
        'refractive', 'intraocular pressure', 'iop', 'visual acuity', 'bcva', 'va', 'best-corrected', 'uncorrected',
        'ucva', 'pinhole', 'ph', 'contrast sensitivity', 'cs', 'halo', 'glare', 'photophobia',
        'photopsia', 'floater', 'flash', 'flashing light', 'flashes', 'floaters', 'metamorphopsia', 'micropsia',
        'macropsia', 'entoptic', 'scotoma', 'blind spot', 'hyperemia', 'redness', 'injection',
        'ciliary injection', 'conjunctival injection', 'episcleritis', 'irritation', 'foreign body sensation', 'fbs',
        'itching', 'burning', 'dryness', 'watering', 'tearing', 'discharge', 'mucus', 'mucopurulent',
        'purulent', 'serous', 'crusting', 'matting', 'swelling', 'edema', 'erythema', 'ecchymosis',
        'hypertropia', 'hypotropia', 'esotropia', 'exotropia', 'tropia', 'phoria', 'hyperphoria',
        'hypophoria', 'esophoria', 'exophoria', 'intermittent', 'alternating', 'comitant', 'incomitant',
        'paralytic', 'restrictive', 'concomitant', 'non-concomitant', 'fusion', 'stereopsis', 'depth perception',
        'diplopia', 'double vision', 'prism', 'diopter', 'base-up', 'base-down', 'base-in', 'base-out',
        'convergence', 'divergence', 'nystagmus', 'jerk', 'pendular', 'gaze-evoked', 'end-gaze',
        'horizontal', 'vertical', 'torsional', 'rotatory', 'downbeat', 'upbeat', 'see-saw',
        'rebound', 'periodic alternating', 'vestibular', 'saccadic', 'pursuit', 'optokinetic',
        'microsaccadic', 'fixation', 'abduction', 'adduction', 'elevation', 'depression',
        'extorsion', 'intorsion', 'cyclorotation', 'incyclotorsion', 'excyclotorsion',
        'pseudomembrane', 'membrane', 'fibrin', 'hypopyon', 'hyphema', 'rubeosis', 'neovascularization',
        'neovascularization of the disc', 'nvd', 'neovascularization elsewhere', 'nve',
        'pre-retinal', 'sub-retinal', 'intra-retinal', 'choroidal', 'vitreomacular traction', 'vmt',
        'vitreomacular adhesion', 'vma', 'posterior vitreous detachment', 'pvd', 'vitreous syneresis',
        'asteroid hyalosis', 'synchysis scintillans', 'amaurosis fugax', 'transient visual obscuration', 'tvo',
        'ischemia', 'ischemic', 'hypoxia', 'hypoxic', 'vasculitis', 'vasculopathy', 'microvasculopathy',
        'microaneurysm', 'telangiectasia', 'macroaneurysm', 'collateral', 'shunt', 'anastomosis',
        'perfusion', 'non-perfusion', 'leakage', 'staining', 'pooling', 'window defect', 'transmission defect',
        'blocking defect', 'arm-retina time', 'arteriovenous transit time', 'laminar flow', 'transit time',
        'watershed zone', 'watershed area'
    }
    
    # List to store found keywords
    keywords = []
    
    # Convert to lowercase for better matching
    text_lower = text.lower()
    
    # Check for ophthalmology-specific terms first
    for term in ophtho_terms:
        if term in text_lower and (not existing_keywords or term not in existing_keywords):
            # Check if multi-word term
            if ' ' in term:
                # For multi-word terms, ensure it's a whole phrase match
                pattern = r'\b' + re.escape(term) + r'\b'
                if re.search(pattern, text_lower):
                    keywords.append(term)
            else:
                # For single word terms, ensure it's a whole word match (not part of another word)
                pattern = r'\b' + re.escape(term) + r'\b'
                if re.search(pattern, text_lower):
                    keywords.append(term)
    
    # If we already have enough ophthalmology terms, return them
    if len(keywords) >= 5:
        return keywords[:10]  # Limit to top 10 keywords
    
    # Split into words and remove common stopwords and other irrelevant terms
    stopwords = {'a', 'an', 'the', 'and', 'or', 'but', 'of', 'with', 'at', 'from', 'to', 'in', 'on', 'for',
                 'by', 'about', 'as', 'into', 'like', 'through', 'after', 'over', 'between', 'out',
                 'study', 'analysis', 'evaluation', 'case', 'report', 'patient', 'patients', 'using',
                 'associated', 'risk', 'effect', 'effects', 'outcome', 'outcomes', 'result', 'results',
                 'method', 'methods', 'compare', 'comparison', 'versus', 'vs', 'cohort', 'group',
                 'clinical', 'significant', 'treatment', 'therapy', 'management', 'approach', 'review',
                 'journal', 'author', 'authors', 'university', 'hospital', 'department', 'institute',
                 'publication', 'research', 'article', 'abstract', 'conclusion', 'background', 'purpose',
                 'objective', 'design', 'setting', 'intervention', 'main', 'measure', 'measures', 'year',
                 'month', 'week', 'day', 'date', 'time', 'period', 'follow', 'followed', 'following'}
    
    # Extract phrases (2-3 word combinations) that might be meaningful
    words = re.findall(r'\b\w+\b', text_lower)
    
    # Create potential 2-3 word phrases and check if they seem meaningful
    for i in range(len(words)-1):
        if words[i] not in stopwords and words[i+1] not in stopwords:
            phrase = words[i] + ' ' + words[i+1]
            # Check for likely medical terms (longer or containing numbers or hyphens)
            if (len(phrase) > 6 and phrase not in keywords 
                and (not existing_keywords or phrase not in existing_keywords)):
                # Check for common medical word patterns
                if (re.search(r'itis|osis|oma|opathy|ectomy|otomy|ectasia|plasia|trophy', phrase) or
                    re.search(r'[0-9]', phrase) or '-' in phrase):
                    keywords.append(phrase)
    
    # Add significant single words that look like medical terms
    single_words = [
        word for word in words 
        if (len(word) > 6 or 
            re.search(r'itis$|osis$|oma$|opathy$|ectomy$|otomy$|ectasia$|plasia$|trophy$', word))
        and word not in stopwords 
        and word not in keywords
        and (not existing_keywords or word not in existing_keywords)
    ]
    
    # Add unique single words to keywords list
    for word in single_words:
        if word not in keywords:
            keywords.append(word)
    
    return keywords[:10]  # Limit to top 10 keywords

# Make sure these functions are defined at the module level, not inside a class
def check_for_updates(current_version=__version__):
    """
    Check if there's a newer version of the script available.
    
    Args:
        current_version: The current version of the script
        
    Returns:
        The latest version if an update is available, None otherwise
    """
    try:
        logger.info("Checking for updates...")
        # Use the correct URL for version information
        version_url = "https://genododi.github.io/Ophthalmology/version.json"
        download_url = "https://genododi.github.io/Ophthalmology/ophthopapers.py"
        
        # Create SSL context for HTTPS connection
        ctx = ssl.create_default_context()
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        
        # Fetch the latest version info
        try:
            with urllib.request.urlopen(version_url, context=ctx) as response:
                if response.status == 404:
                    # If version.json doesn't exist, try to check the script file directly
                    with urllib.request.urlopen(download_url, context=ctx) as script_response:
                        script_content = script_response.read().decode('utf-8')
                        # Try to extract version from the script content
                        version_match = re.search(r'__version__\s*=\s*[\'"]([^\'"]+)[\'"]', script_content)
                        if version_match:
                            latest_version = version_match.group(1)
                            if latest_version > current_version:
                                logger.info(f"Update available: {latest_version}")
                                return {'version': latest_version, 'url': download_url}
                        return None
                else:
                    version_info = json.load(response)
                    latest_version = version_info.get('version')
                    download_url = version_info.get('download_url', download_url)
                    
                    if latest_version and download_url:
                        # Compare versions (simple string comparison works for semantic versioning)
                        if latest_version > current_version:
                            logger.info(f"Update available: {latest_version}")
                            return {'version': latest_version, 'url': download_url}
                        else:
                            logger.info("No updates available")
                            return None
                    else:
                        logger.warning("Invalid version information received")
                        return None
        except urllib.error.URLError as e:
            logger.error(f"Could not connect to update server: {str(e)}")
            return None
    except Exception as e:
        logger.error(f"Error checking for updates: {str(e)}")
        return None

def update_script(update_info):
    """
    Update the script to the latest version.
    
    Args:
        update_info: Dictionary containing version and download URL
        
    Returns:
        True if update successful, False otherwise
    """
    try:
        logger.info(f"Updating to version {update_info['version']}...")
        
        # Create SSL context for HTTPS connection
        ctx = ssl.create_default_context()
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        
        # Download the new version
        temp_dir = tempfile.mkdtemp()
        temp_file = os.path.join(temp_dir, "ophthopapers_new.py")
        
        with urllib.request.urlopen(update_info['url'], context=ctx) as response:
            with open(temp_file, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
        
        # Calculate hash for integrity check
        with open(temp_file, 'rb') as file:
            downloaded_hash = hashlib.sha256(file.read()).hexdigest()
            
        # Get the current script path
        current_script = os.path.abspath(__file__)
        
        # Create backup of current script
        backup_file = current_script + ".bak"
        shutil.copy2(current_script, backup_file)
        
        # Replace current script with new version
        shutil.copy2(temp_file, current_script)
        
        # Clean up
        shutil.rmtree(temp_dir)
        
        logger.info(f"Successfully updated to version {update_info['version']}")
        return True
    except Exception as e:
        logger.error(f"Error updating script: {str(e)}")
        return False

def download_paper_from_scihub(doi, output_path):
    """
    Download a paper from Sci-Hub using its DOI
    
    Args:
        doi (str): The DOI of the paper
        output_path (str): Path where the PDF will be saved
        
    Returns:
        bool: True if download was successful, False otherwise
    """
    # List of Sci-Hub mirrors to try - comprehensive updated list
    scihub_mirrors = [
        "https://sci-hub.se/",
        "https://sci-hub.st/",
        "https://sci-hub.ru/",
        "https://sci-hub.yt/",
        "https://sci-hub.wf/",
        "https://sci-hub.ee/",
        "https://sci-hub.shop/",
        "https://sci-hub.tw/",
        "https://sci-hub.uno/",
        "https://sci-hub.cat/",
        "https://sci-hub.fan/",
        "https://sci-hub.do/",
        "https://sci-hubtw.hkvisa.net/",
        "https://sci.hubg.org/",
        "https://sci-hub.hkvisa.net/",
        "https://sci-hub.wvisa.ru/",
        "https://sci-hub.tech/",
        "https://sci-hub.mksa.top/",
        "https://sci-hub.ren/",
        "https://sci-hub.cc/",
        "https://sci-hub.best/",
        "https://sci.hubtw.fyi/"
    ]
    
    # Configure headers to mimic a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'Referer': 'https://google.com/'
    }
    
    # Disable insecure HTTPS warnings
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Try each mirror
    for mirror in scihub_mirrors:
        try:
            logger.info(f"Trying to download from {mirror} for DOI: {doi}")
            
            # Create URL for the DOI
            url = f"{mirror}{doi}"
            
            # Send request with a timeout, ignore SSL certificate verification
            response = requests.get(url, headers=headers, timeout=30, verify=False)
            
            # Check if the request was successful
            if response.status_code == 200:
                # Parse the HTML response
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for the embedded PDF iframe (multiple selectors to try)
                iframe = soup.find('iframe', id='pdf') or soup.find('iframe', attrs={'name': 'pdf'}) or soup.find('iframe')
                
                # If found iframe with src attribute
                if iframe and iframe.get('src'):
                    pdf_url = iframe['src']
                    
                    # If the URL is relative, make it absolute
                    if pdf_url.startswith('//'):
                        pdf_url = 'https:' + pdf_url
                    elif not pdf_url.startswith(('http://', 'https://')):
                        # Try to determine the base URL from the mirror
                        base_url = '/'.join(mirror.split('/')[:3])
                        pdf_url = base_url + pdf_url if not pdf_url.startswith('/') else base_url + pdf_url
                    
                    logger.info(f"Found PDF URL: {pdf_url}")
                    
                    # Download the PDF with a longer timeout
                    try:
                        pdf_response = requests.get(pdf_url, headers=headers, timeout=60, stream=True, verify=False)
                        
                        # Check if it's a PDF or HTML (sometimes Sci-Hub returns HTML in error cases)
                        content_type = pdf_response.headers.get('Content-Type', '')
                        if pdf_response.status_code == 200 and (content_type.startswith('application/pdf') or pdf_url.lower().endswith('.pdf')):
                            # Save the PDF to the specified path
                            with open(output_path, 'wb') as f:
                                f.write(pdf_response.content)
                            
                            # Verify the file is a PDF (starts with %PDF)
                            with open(output_path, 'rb') as f:
                                header = f.read(4)
                                if header == b'%PDF':
                                    logger.info(f"Successfully downloaded PDF from {mirror}")
                                    return output_path
                                else:
                                    logger.warning(f"Downloaded file is not a valid PDF from {mirror}")
                                    os.remove(output_path)  # Remove invalid file
                    except Exception as e:
                        logger.error(f"Error downloading PDF from {pdf_url}: {str(e)}")
                        continue
                
                # Alternative method: look for direct download button/link
                download_buttons = soup.select('button#save') or soup.select('a.download') or soup.select('a[href*="download"]')
                for button in download_buttons:
                    try:
                        download_url = button.get('href') or button.get('data-href') or button.get('onclick')
                        if download_url:
                            # Extract URL from onclick handler if needed
                            if 'onclick' in str(button):
                                match = re.search(r"location.href='([^']+)'", str(button))
                                if match:
                                    download_url = match.group(1)
                            
                            # Make URL absolute if needed
                            if not download_url.startswith(('http://', 'https://')):
                                download_url = urljoin(mirror, download_url)
                            
                            # Try to download from this URL
                            pdf_response = requests.get(download_url, headers=headers, timeout=60, verify=False)
                            if pdf_response.status_code == 200:
                                with open(output_path, 'wb') as f:
                                    f.write(pdf_response.content)
                                
                                # Verify the file is a PDF
                                with open(output_path, 'rb') as f:
                                    header = f.read(4)
                                    if header == b'%PDF':
                                        logger.info(f"Successfully downloaded PDF from button link")
                                        return output_path
                                    else:
                                        os.remove(output_path)  # Remove invalid file
                    except Exception as e:
                        logger.error(f"Error with download button: {str(e)}")
                        continue
        
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout with mirror {mirror}")
            continue
        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error with mirror {mirror}")
            continue
        except Exception as e:
            logger.error(f"Error with mirror {mirror}: {str(e)}")
            continue
    
    # If all mirrors failed
    logger.error("All Sci-Hub mirrors failed, couldn't download the paper")
    return None

def download_paper_from_ekb(doi, output_path, username="genododi@gmail.com", password="pu@pjq8CgYnZAM4"):
    """
    Download a paper from EKB (Egyptian Knowledge Bank) using its DOI
    
    Args:
        doi (str): The DOI of the paper
        output_path (str): Path where the PDF will be saved
        username (str): EKB username
        password (str): EKB password
        
    Returns:
        str: Path to the saved PDF if successful, None otherwise
    """
    logger.info(f"Attempting to download from EKB for DOI: {doi}")
    
    # EKB base URL
    ekb_url = "https://www.ekb.eg/"
    
    # Configure session with headers to mimic a browser
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Referer': ekb_url
    }
    
    session.headers.update(headers)
    
    try:
        # Step 1: Visit the home page to get cookies
        logger.info("Accessing EKB home page")
        home_response = session.get(ekb_url, timeout=30)
        if home_response.status_code != 200:
            logger.error(f"Failed to access EKB home page: {home_response.status_code}")
            return None
        
        # Step 2: Login to EKB
        logger.info("Logging in to EKB")
        login_url = f"{ekb_url}login"
        login_data = {
            'username': username,
            'password': password,
            'remember': 'true'
        }
        
        login_response = session.post(login_url, data=login_data, timeout=30)
        if login_response.status_code != 200 or "login" in login_response.url.lower():
            logger.error("Login failed")
            return None
        
        # Step 3: Search for the article by DOI
        logger.info(f"Searching for article with DOI: {doi}")
        search_url = f"{ekb_url}search"
        search_params = {
            'query': doi,
            'type': 'all'
        }
        
        search_response = session.get(search_url, params=search_params, timeout=30)
        if search_response.status_code != 200:
            logger.error(f"Search failed: {search_response.status_code}")
            return None
        
        # Parse the search results to find the article
        soup = BeautifulSoup(search_response.text, 'html.parser')
        article_links = soup.select('a.article-title')
        
        if not article_links:
            logger.warning("No articles found for this DOI")
            
            # Try an alternative approach - direct URL construction
            direct_url = f"https://doi.org/{doi}"
            logger.info(f"Trying direct DOI access: {direct_url}")
            
            # Follow the DOI redirect to publisher
            doi_response = session.get(direct_url, timeout=30, allow_redirects=True)
            if doi_response.status_code != 200:
                logger.error(f"Failed to access article via DOI: {doi_response.status_code}")
                return None
            
            # Check if we landed on a publisher page that EKB might support
            publisher_url = doi_response.url
            publisher_domain = publisher_url.split('/')[2]
            
            # Try to access the PDF directly through EKB's proxied access
            ekb_publisher_url = f"https://www.ekb.eg/web/guest/resources/-/journal_content/56/55802/proxy?url={publisher_url}"
            logger.info(f"Trying EKB proxy access: {ekb_publisher_url}")
            
            publisher_response = session.get(ekb_publisher_url, timeout=60)
            if publisher_response.status_code != 200:
                logger.error(f"Failed to access through EKB proxy: {publisher_response.status_code}")
                return None
            
            # Look for PDF download links on the publisher page
            pub_soup = BeautifulSoup(publisher_response.text, 'html.parser')
            pdf_links = pub_soup.select('a[href*=".pdf"], a[data-download-type="pdf"], a.pdf-link')
            
            if not pdf_links:
                logger.warning("No PDF links found on publisher page")
                return None
            
            # Try the first PDF link
            pdf_url = pdf_links[0].get('href')
            if not pdf_url.startswith(('http://', 'https://')):
                pdf_url = urljoin(publisher_url, pdf_url)
            
            # Download the PDF
            logger.info(f"Downloading PDF from: {pdf_url}")
            pdf_response = session.get(pdf_url, timeout=60, stream=True)
            
            if pdf_response.status_code == 200 and (pdf_response.headers.get('Content-Type', '').startswith('application/pdf') or pdf_url.lower().endswith('.pdf')):
                with open(output_path, 'wb') as f:
                    f.write(pdf_response.content)
                
                # Verify it's a valid PDF
                with open(output_path, 'rb') as f:
                    header = f.read(4)
                    if header == b'%PDF':
                        logger.info("Successfully downloaded PDF from EKB")
                        return output_path
                    else:
                        logger.warning("Downloaded file is not a valid PDF")
                        os.remove(output_path)
                        return None
        else:
            # Process search results
            for link in article_links:
                article_title = link.text.strip()
                article_url = link.get('href')
                if not article_url.startswith(('http://', 'https://')):
                    article_url = urljoin(ekb_url, article_url)
                
                logger.info(f"Found article: {article_title}")
                
                # Visit the article page
                article_response = session.get(article_url, timeout=30)
                if article_response.status_code != 200:
                    logger.error(f"Failed to access article page: {article_response.status_code}")
                    continue
                
                # Look for PDF download link
                article_soup = BeautifulSoup(article_response.text, 'html.parser')
                pdf_links = article_soup.select('a[href*=".pdf"], a.pdf-download-link, a[data-download-type="pdf"]')
                
                if not pdf_links:
                    logger.warning("No PDF links found on article page")
                    continue
                
                # Try the first PDF link
                pdf_url = pdf_links[0].get('href')
                if not pdf_url.startswith(('http://', 'https://')):
                    pdf_url = urljoin(article_url, pdf_url)
                
                # Download the PDF
                logger.info(f"Downloading PDF from: {pdf_url}")
                pdf_response = session.get(pdf_url, timeout=60, stream=True)
                
                if pdf_response.status_code == 200 and (pdf_response.headers.get('Content-Type', '').startswith('application/pdf') or pdf_url.lower().endswith('.pdf')):
                    with open(output_path, 'wb') as f:
                        f.write(pdf_response.content)
                    
                    # Verify it's a valid PDF
                    with open(output_path, 'rb') as f:
                        header = f.read(4)
                        if header == b'%PDF':
                            logger.info("Successfully downloaded PDF from EKB")
                            return output_path
                        else:
                            logger.warning("Downloaded file is not a valid PDF")
                            os.remove(output_path)
                            continue
                
                # If we reached here, the download failed for this link
                logger.warning(f"Failed to download PDF from: {pdf_url}")
            
            # If we've tried all links and failed
            logger.error("Could not download PDF from any of the article links")
            return None
    
    except Exception as e:
        logger.error(f"Error in EKB download process: {str(e)}")
        return None
    
    return None

class OphthoPapersApp:
    def __init__(self, root):
        # Set the root window
        self.root = root
        self.root.title(f"Ophthalmology Papers Fetcher v{__version__} - © Designed by Dr. Mahmoud Sami")
        self.root.geometry("1200x1000")
        self.root.minsize(750, 550)
        
        # Initialize search presets
        self.search_presets = []
        
        # Create a main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Set icon if available
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except:
            pass  # Ignore icon loading errors
        
        # Setup variables
        self.email_var = tk.StringVar(value="default_email@example.com")  # Hidden default email
        self.api_key_var = tk.StringVar(value="9bf2be2683f9a133cad29bc4891684364e08")  # Default API key
        self.days_back_var = tk.StringVar(value="30")
        self.max_results_var = tk.StringVar(value="1000")  # Increased default max results
        self.save_dir_var = tk.StringVar(value=os.path.expanduser("~/Desktop"))
        self.export_format_var = tk.StringVar(value="csv")
        self.subspecialty_var = tk.StringVar(value="all")
        self.today_only_var = tk.BooleanVar(value=False)
        self.month_only_var = tk.BooleanVar(value=False)
        self.specific_year_var = tk.BooleanVar(value=False)  # For specific year filter
        self.year_var = tk.StringVar(value=str(datetime.today().year))  # Default to current year
        self.keyword_search_var = tk.StringVar()  # For searching existing results
        self.fetch_keyword_var = tk.StringVar()  # For fetching by keyword from PubMed
        self.journal_var = tk.StringVar(value="")  # For fetching by specific journal
        self.current_displayed_articles = []  # For tracking what's currently displayed
        self.selected_article_idx = None  # For tracking selected article
        self.search_history = []  # For tracking search history
        self.search_presets = []  # For storing search presets
        
        # For progress bar
        self.progress_var = tk.DoubleVar(value=0)
        
        # List to track input widgets for disabling/enabling during fetch
        self.input_widgets = []
        
        # Add a search settings tracker
        self.current_search_settings = {
            "date_filter": "None",
            "days_back": "30",
            "max_results": "1000",
            "subspecialty": "All",
            "keyword": "",
            "journal": "",
            "preset_name": ""
        }
        
        # Create tooltip function
        def create_tooltip(widget, text):
            def enter(event):
                x, y, _, _ = widget.bbox("insert")
                x += widget.winfo_rootx() + 25
                y += widget.winfo_rooty() + 25
                
                # Create a toplevel window
                tooltip = tk.Toplevel(widget)
                tooltip.wm_overrideredirect(True)
                tooltip.wm_geometry(f"+{x}+{y}")
                
                # Add a label
                label = ttk.Label(tooltip, text=text, justify=tk.LEFT,
                                 background="#ffffe0", relief="solid", borderwidth=1,
                                 padding=4)
                label.pack()
                
                widget._tooltip = tooltip
                
            def leave(event):
                if hasattr(widget, "_tooltip"):
                    widget._tooltip.destroy()
                    
            widget.bind("<Enter>", enter)
            widget.bind("<Leave>", leave)
        
        # Create a style to highlight active filters
        style = ttk.Style()
        style.configure('TLabelframe.Label', font=('Helvetica', 10))
        style.configure('Active.TLabelframe.Label', foreground='blue', font=('Helvetica', 10, 'bold'))
        style.configure('Fetch.TButton', font=('Helvetica', 11, 'bold'))
        style.configure('Active.TEntry', background='#e6f2ff')  # Light blue background for active Entry
        
        # Create input frame
        input_frame = ttk.LabelFrame(main_frame, text="Search Settings", padding="10")
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Left and right frames for search settings
        left_frame = ttk.Frame(input_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        
        right_frame = ttk.Frame(input_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, expand=True, padx=(10, 0))
        
        # Date filters - LEFT frame
        self.date_frame = ttk.LabelFrame(left_frame, text="Date Settings")
        self.date_frame.pack(fill=tk.X, pady=5)
        
        # First section - days back
        ttk.Label(self.date_frame, text="Days Back:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        days_back_entry = ttk.Entry(self.date_frame, textvariable=self.days_back_var, width=8)
        days_back_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        create_tooltip(days_back_entry, "Number of days to look back for articles.\n"
                       "When used with 'Specific Year', limits search to\n"
                       "the last X days of that year (0 = entire year).")
        self.input_widgets.append(days_back_entry)
        
        # Time-based filters
        ttk.Label(self.date_frame, text="Time-based Filters:").grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(10,2))
        
        # Today's articles checkbox with improved tooltip
        today_check = ttk.Checkbutton(self.date_frame, text="Today's Articles Only", variable=self.today_only_var, 
                                      command=self.toggle_days_back)
        today_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=15, pady=2)
        create_tooltip(today_check, "When checked, fetches ONLY articles published today (strict filtering).\nOverrides 'Days Back' setting.\nResults will be limited to articles with today's exact publication date.")
        self.input_widgets.append(today_check)
        
        # Month's articles checkbox with improved tooltip
        month_check = ttk.Checkbutton(self.date_frame, text="This Month's Articles Only", variable=self.month_only_var, 
                                      command=self.toggle_month_back)
        month_check.grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=15, pady=2)
        create_tooltip(month_check, "When checked, fetches only articles published in the current month.\nOverrides 'Days Back' setting.\nUses an expanded search to maximize results.")
        self.input_widgets.append(month_check)
        
        # Separator
        ttk.Separator(self.date_frame, orient='horizontal').grid(row=4, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=8)
        
        # Year-based filter section
        ttk.Label(self.date_frame, text="Year-based Filter:").grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(0,2))
        
        # Specific year checkbox and dropdown
        date_frame_inner = ttk.Frame(self.date_frame)
        date_frame_inner.grid(row=6, column=0, columnspan=2, sticky=tk.W, padx=15, pady=2)
        
        year_check = ttk.Checkbutton(date_frame_inner, text="Specific Year:", variable=self.specific_year_var, 
                                    command=self.toggle_specific_year)
        year_check.pack(side=tk.LEFT)
        create_tooltip(year_check, "When checked, fetches articles published in the selected year.\n"
                       "Can be combined with 'Days Back' to limit search to\n"
                       "the last X days of the year (0 = entire year).")
        self.input_widgets.append(year_check)
        
        # Year dropdown with values from 1980 to 2025
        years = [str(year) for year in range(1980, 2026)]
        year_dropdown = ttk.Combobox(date_frame_inner, textvariable=self.year_var, values=years, width=6, state="readonly")
        year_dropdown.pack(side=tk.LEFT, padx=(5, 0))
        create_tooltip(year_dropdown, "Select the specific year to search for articles.\n"
                       "Combined with 'Days Back' to filter articles from a\n"
                       "specific time period within the selected year.")
        self.input_widgets.append(year_dropdown)
        
        # Integration hint
        integration_label = ttk.Label(self.date_frame, text="Note: 'Days Back' can be combined with 'Specific Year'",
                                      font=('Helvetica', 8), foreground='blue')
        integration_label.grid(row=7, column=0, columnspan=2, sticky=tk.W, padx=15, pady=(2, 5))
        
        # Max results - LEFT frame
        max_results_frame = ttk.LabelFrame(left_frame, text="Results Settings")
        max_results_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(max_results_frame, text="Max Results:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        max_results_entry = ttk.Entry(max_results_frame, textvariable=self.max_results_var, width=10)
        max_results_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        create_tooltip(max_results_entry, "Maximum number of articles to retrieve.\nDefault is 1000.\nFor time-based filters (Today/Month), the system will\ntry multiple approaches to get close to this number.")
        self.input_widgets.append(max_results_entry)
        self.input_widgets.append(days_back_entry)
        
        # Fetch keyword & Journal - RIGHT frame
        self.content_frame = ttk.LabelFrame(right_frame, text="Content Filters")
        self.content_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.content_frame, text="Fetch by Keyword:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        keyword_entry = ttk.Entry(self.content_frame, textvariable=self.fetch_keyword_var, width=25)
        keyword_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        create_tooltip(keyword_entry, "Enter keywords to search for in article titles and abstracts.\nExample: 'OCT glaucoma' will find articles containing both terms.\nLeave empty to retrieve all articles without keyword filtering.")
        
        # Clear keyword button
        clear_keyword_btn = ttk.Button(self.content_frame, text="×", width=2, 
                                      command=lambda: self.fetch_keyword_var.set(""))
        clear_keyword_btn.grid(row=0, column=2, padx=(0, 5))
        create_tooltip(clear_keyword_btn, "Clear keyword search")
        
        # Journal selection with improved tooltip
        ttk.Label(self.content_frame, text="Journal:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        # Create a combobox with the list of journals
        journal_names = [''] + sorted([j[0] for j in [
            ('Ophthalmology', '0161-6420'),
            ('JAMA Ophthalmol', '2168-6165'),
            ('Prog Retin Eye Res', '1350-9462'),
            ('Am J Ophthalmol', '0002-9394'),
            ('Br J Ophthalmol', '0007-1161'),
            ('Retina', '0275-5408'),
            ('Invest Ophthalmol Vis Sci', '0146-0404'),
            ('Acta Ophthalmol', '1755-375X'),
            ('Cornea', '0277-3740'),
            ('Eye (Lond)', '0950-222X'),
            ('Graefes Arch Clin Exp Ophthalmol', '0721-832X'),
            ('J Cataract Refract Surg', '0886-3350'),
            ('J Refract Surg', '1081-597X'),
            ('J Glaucoma', '1057-0829'),
            ('Exp Eye Res', '0014-4835'),
            ('Ocul Surf', '1542-0124'),
            ('Surv Ophthalmol', '0039-6257'),
            ('Ophthalmol Retina', '2468-6530'),
            ('Ophthalmol Glaucoma', '2589-4196'),
            ('Ophthalmol Ther', '2193-8245'),
            ('Curr Eye Res', '0271-3683'),
            ('J Ophthalmol', '2090-004X'),
            ('Clin Ophthalmol', '1177-5467'),
            ('Indian J Ophthalmol', '0301-4738'),
            ('Can J Ophthalmol', '0008-4182'),
            ('Ophthalmic Res', '0030-3747'),
            ('Eur J Ophthalmol', '1120-6721'),
            ('J Ocul Pharmacol Ther', '1080-7683'),
            ('Curr Opin Ophthalmol', '1040-8738'),
            ('Ophthalmic Epidemiol', '0928-6586'),
            ('Ophthalmic Plast Reconstr Surg', '0740-9303'),
            ('Ophthalmic Surg Lasers Imaging Retina', '2325-8160'),
            ('Doc Ophthalmol', '0012-4486'),
            ('Int Ophthalmol', '0165-5701'),
            ('Semin Ophthalmol', '0882-0538'),
            ('Asia Pac J Ophthalmol', '2162-0989'),
            ('Clin Exp Ophthalmol', '1442-6404'),
            ('Middle East Afr J Ophthalmol', '0974-9233'),
            ('Transl Vis Sci Technol', '2164-2591'),
            ('Ophthalmic Genet', '1381-6810'),
            ('Mol Vis', '1090-0535'),
            ('J Vis', '1534-7362'),
            ('Vision Res', '0042-6989'),
            ('J Eye Movement Res', '1995-8692'),
            # Taylor & Francis journals
            ('Orbit', '0167-6830'),
            ('Current Eye Research', '0271-3683'),
            ('Current Medical Research and Opinion', '0300-7995'),
            ('Ophthalmic and Physiological Optics', '0275-5408'),
            ('Cutaneous and Ocular Toxicology', '1556-9527'),
            ('Journal of Toxicology: Cutaneous and Ocular Toxicology', '0731-3829'),
            ('Visual Neuroscience', '0952-5238'),
            ('Journal of Visual Communication in Medicine', '1745-3054'),
            ('International Journal of Ophthalmic Practice', '2044-5504'),
            ('Visual Cognition', '1350-6285'),
            ('Clinical and Experimental Optometry', '0816-4622'),
            # Additional Taylor & Francis ophthalmology and vision science journals
            ('Acta Ophthalmologica Scandinavica', '1395-3907'),
            ('Neuro-Ophthalmology', '0165-8107'),
            ('Ocular Immunology and Inflammation', '0927-3948'),
            ('Refractive Surgery', '0883-0444'),
            ('Strabismus', '0927-3972'),
            ('Journal of Neuro-Ophthalmology', '1070-8022'),
            ('Ophthalmic Plastic and Reconstructive Surgery', '0740-9303'),
            ('Seminars in Ophthalmology', '0882-0538'),
            ('International Ophthalmology Clinics', '0020-8167'),
            ('Journal of Pediatric Ophthalmology and Strabismus', '0191-3913'),
            ('Journal of Vision Impairment & Blindness', '0145-482X'),
            ('Optometry and Vision Science', '1040-5488'),
            ('Expert Review of Ophthalmology', '1746-9899'),
            ('Visual Development and Rehabilitation', '2374-6440'),
            ('Journal of Ophthalmic Vision Research', '2008-2010'),
            ('Ophthalmic Research', '0030-3747'),
            ('British and Irish Orthoptic Journal', '2516-3590'),
            ('Clinical Optometry', '1179-2752'),
            ('Advances in Ophthalmology and Visual System', '2374-9695'),
            ('Eye and Brain', '1179-2744'),
            ('Open Ophthalmology Journal', '1874-3641'),
            ('Journal of Optometry', '1888-4296'),
            ('Journal of Current Ophthalmology', '2452-2325'),
            # Healio ophthalmology journals
            ('Journal of Pediatric Ophthalmology and Strabismus', '0191-3913'),
            ('Ocular Surgery News', '8750-3085'),
            ('Primary Care Optometry News', '1081-6437'),
            ('Ocular Surgery News Europe/Asia-Pacific Edition', '1085-5629'),
            ('Ophthalmic Technology Assessment', '0162-0436'),
            ('International Journal of Eye Banking', '2193-4037'),
            ('Ophthalmic ASC', '2578-9740'),
        ]])
        journal_combo = ttk.Combobox(self.content_frame, textvariable=self.journal_var, width=25, values=journal_names)
        journal_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        create_tooltip(journal_combo, "Select a specific journal to search, or leave empty to search all journals.\nFiltering by journal can help find more relevant articles.\nWith 'This Month's Articles Only', filters will be applied to ensure ophthalmology focus.")
        self.input_widgets.append(journal_combo)
        
        # Clear journal button
        clear_journal_btn = ttk.Button(self.content_frame, text="×", width=2, 
                                     command=lambda: self.journal_var.set(""))
        clear_journal_btn.grid(row=1, column=2, padx=(0, 5))
        create_tooltip(clear_journal_btn, "Clear journal selection")
        
        # Subspecialty selection with improved tooltip
        ttk.Label(self.content_frame, text="Subspecialty:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        subspecialty_combobox = ttk.Combobox(self.content_frame, textvariable=self.subspecialty_var, width=25)
        subspecialty_combobox['values'] = ('All', 'Cataract', 'Cornea', 'Refractive', 'Glaucoma', 'Retina', 'Oculoplasty', 'Uveitis', 'Pediatrics')
        subspecialty_combobox.current(0)
        subspecialty_combobox.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        create_tooltip(subspecialty_combobox, "Filter articles by ophthalmology subspecialty.\n'All' retrieves articles from all subspecialties.\nApplies additional keywords to the search specific to each subspecialty.")
        
        # Active filter indicators
        self.date_filter_indicator = ttk.Label(self.date_frame, text="", foreground="blue")
        self.date_filter_indicator.grid(row=8, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(5, 2))
        
        self.content_filter_indicator = ttk.Label(self.content_frame, text="", foreground="blue")
        self.content_filter_indicator.grid(row=3, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(5, 2))
        
        # Export format and directory - RIGHT frame
        export_frame = ttk.LabelFrame(right_frame, text="Export Settings")
        export_frame.pack(fill=tk.X, pady=5)
        
        # Export format selection
        ttk.Label(export_frame, text="Export Format:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        export_format_frame = ttk.Frame(export_frame)
        export_format_frame.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Radiobutton(export_format_frame, text="CSV", variable=self.export_format_var, value="csv").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Radiobutton(export_format_frame, text="Excel", variable=self.export_format_var, value="excel").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Radiobutton(export_format_frame, text="Text", variable=self.export_format_var, value="txt").pack(side=tk.LEFT, padx=(0, 5))
        
        # Save directory selection
        ttk.Label(export_frame, text="Save Directory:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        dir_frame = ttk.Frame(export_frame)
        dir_frame.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(dir_frame, textvariable=self.save_dir_var, width=25).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(dir_frame, text="Browse...", command=self.browse_directory).pack(side=tk.LEFT)
        
        # Action button frame - prominent in the center
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=10)
        self.action_frame = action_frame  # Store as instance variable
        
        # Progress bar
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress = ttk.Progressbar(action_frame, orient=tk.HORIZONTAL, length=300, mode='determinate', variable=self.progress_var)
        self.progress.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready to fetch articles")
        status_label = ttk.Label(action_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT, padx=5)
        
        # Create a stylish fetch button
        fetch_frame = ttk.Frame(input_frame)
        fetch_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        # Add clear results button
        self.clear_button = ttk.Button(
            fetch_frame, 
            text="Clear Results", 
            command=self.clear_results
        )
        self.clear_button.pack(side=tk.RIGHT, padx=5)
        create_tooltip(self.clear_button, "Clear all displayed articles")
        
        self.fetch_button = ttk.Button(
            fetch_frame, 
            text="Fetch Articles", 
            command=self.fetch_articles,
            style="Fetch.TButton"
        )
        self.fetch_button.pack(side=tk.RIGHT, padx=5)
        create_tooltip(self.fetch_button, "Start fetching articles with the current settings")
        
        # Add to input widgets list
        self.input_widgets.append(journal_combo)
        self.input_widgets.append(keyword_entry)
        self.input_widgets.append(subspecialty_combobox)
        
        # Additional widgets should be added to input_widgets as they are created
        
        # Add keyword search frame
        search_frame = ttk.LabelFrame(main_frame, text="Search Results")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Keyword search
        ttk.Label(search_frame, text="Search Keywords:").pack(side=tk.LEFT, padx=5, pady=5)
        keyword_entry = ttk.Entry(search_frame, textvariable=self.keyword_search_var, width=30)
        keyword_entry.pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(search_frame, text="Search", command=self.search_keywords).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(search_frame, text="Clear", command=self.clear_search).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(search_frame, text="Find Related Articles", command=self.find_related_articles).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Results text area with frame
        results_frame = ttk.LabelFrame(main_frame, text="Results", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a frame for the text area and its scrollbar
        text_frame = ttk.Frame(results_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(text_frame)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        x_scrollbar = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create text widget with scrollbars
        self.results_text = tk.Text(text_frame, wrap=tk.NONE, yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure scrollbars
        y_scrollbar.config(command=self.results_text.yview)
        x_scrollbar.config(command=self.results_text.xview)
        
        # Configure text widget for hyperlinks and article selection
        self.results_text.tag_configure("hyperlink", foreground="blue", underline=1)
        self.results_text.tag_configure("article_title", foreground="dark green", font=("Helvetica", 10, "bold"))
        self.results_text.bind("<Button-1>", self.handle_text_click)
        
        # Initialize articles list and hyperlinks dictionary
        self.articles = []
        self.hyperlinks = {}
        
        # Load saved settings after UI is set up
        self.load_search_settings()
        
        # Create progress bar
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, orient="horizontal", mode="determinate")
        # It will be placed in the UI only when needed
    
    def toggle_days_back(self):
        """Enable/disable days back entry based on today's articles checkbox"""
        if self.today_only_var.get():
            # If "Today's Articles Only" is checked, disable days back entry and uncheck month option
            self.days_back_var.set("0")
            self.month_only_var.set(False)
            self.specific_year_var.set(False)  # Also uncheck specific year
        else:
            # If unchecked, enable days back entry with default value (unless month is checked)
            if not self.month_only_var.get() and not self.specific_year_var.get():
                self.days_back_var.set("30")
                
        # Update the filter indicators
        self.update_filter_indicators()
    
    def toggle_month_back(self):
        """Enable/disable days back entry based on month's articles checkbox"""
        if self.month_only_var.get():
            # If "This Month's Articles Only" is checked, disable days back entry and uncheck today option
            self.days_back_var.set("0")
            self.today_only_var.set(False)
            self.specific_year_var.set(False)  # Also uncheck specific year
        else:
            # If unchecked, enable days back entry with default value
                self.days_back_var.set("30")
            
        # Update the filter indicators
        self.update_filter_indicators()
    
    def toggle_specific_year(self):
        """Enable/disable days back entry based on specific year checkbox"""
        # Find the days back field to highlight it
        days_back_label = None
        days_back_entry = None
        
        for child in self.date_frame.winfo_children():
            if isinstance(child, ttk.Entry) and child.winfo_name().endswith("entry"):
                if child.grid_info()["row"] == 0:  # It's in the first row
                    days_back_entry = child
            elif isinstance(child, ttk.Label) and "Days Back" in child.cget("text"):
                days_back_label = child
        
        if self.specific_year_var.get():
            # If "Specific Year" is checked, disable today and month options
            self.today_only_var.set(False)
            self.month_only_var.set(False)
            # We don't disable days_back anymore - it can be used to limit results within the year
            
            # Highlight the days back field to show it's active with specific year
            if days_back_label:
                days_back_label.configure(foreground="blue", font=("Helvetica", 10, "bold"))
            
            # Highlight the integration between days back and specific year
            self.update_integration_note(True)
        else:
            # If unchecked, reset days back entry to default value if it was zero
            if self.days_back_var.get() == "0":
                self.days_back_var.set("30")
            
            # Reset the days back label appearance
            if days_back_label:
                days_back_label.configure(foreground="black", font=("Helvetica", 10))
            
            # Reset the integration note
            self.update_integration_note(False)
        
        # Update the filter indicators
        self.update_filter_indicators()
    
    def update_integration_note(self, is_active=False):
        """Update the integration note to reflect the current state of date filters"""
        # Find the integration note by text content (the note we added in the UI)
        integration_label = None
        for child in self.date_frame.winfo_children():
            if isinstance(child, ttk.Label) and "can be combined" in child.cget("text"):
                integration_label = child
                break
        
        if integration_label:
            if is_active and self.specific_year_var.get() and self.days_back_var.get() != "0":
                # When both specific year and days back are being used together
                days = self.days_back_var.get()
                year = self.year_var.get()
                integration_label.configure(
                    text=f"Active: Last {days} days of year {year}",
                    foreground="blue", 
                    font=('Helvetica', 9, 'bold')
                )
            else:
                # Default state - just show the hint
                integration_label.configure(
                    text="Note: 'Days Back' can be combined with 'Specific Year'",
                    foreground="blue",
                    font=('Helvetica', 8)
                )
    
    def search_keywords(self):
        """Search within fetched articles using keywords"""
        if not self.articles:
            messagebox.showinfo("Info", "No articles to search. Please fetch articles first.")
            return
            
        search_term = self.keyword_search_var.get().strip().lower()
        if not search_term:
            messagebox.showinfo("Info", "Please enter a search term")
            return
        
        # Find articles matching the search term
        matched_articles = []
        for article in self.articles:
            # Search in title, abstract, authors, keywords and journal
            searchable_text = (
                article['title'].lower() + ' ' + 
                article['full_abstract'].lower() + ' ' + 
                article['authors'].lower() + ' ' + 
                article['keywords'].lower() + ' ' + 
                article['journal'].lower()
            )
            
            if search_term in searchable_text:
                matched_articles.append(article)
        
        if not matched_articles:
            messagebox.showinfo("Search Results", f"No articles found containing '{search_term}'")
            return
        
        # Display the search results
        self.current_displayed_articles = matched_articles
        self.selected_article_idx = None
        
        # Update the status bar with search info
        self.status_var.set(f"Found {len(matched_articles)} articles containing '{search_term}' (from {len(self.articles)} total)")
        
        # Clear the results text
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, f"Search Results for: '{search_term}'\n\n", "heading")
        self.results_text.tag_configure("heading", font=("Helvetica", 12, "bold"))
        
        # Display the matched articles
        self.display_articles(matched_articles)
        
        # Highlight the search term in the results
        self.highlight_search_term(search_term)
    
    def highlight_search_term(self, term):
        """Highlight the search term in the results text"""
        # Configure a tag for highlighting
        self.results_text.tag_configure("search_highlight", background="yellow")
        
        # Find all occurrences of the term
        start_pos = "1.0"
        while True:
            # Find the next occurrence
            start_pos = self.results_text.search(term, start_pos, tk.END, nocase=1)
            if not start_pos:
                break
                
            # Calculate end position
            end_pos = f"{start_pos}+{len(term)}c"
            
            # Apply the highlight tag
            self.results_text.tag_add("search_highlight", start_pos, end_pos)
            
            # Move to the next position
            start_pos = end_pos
    
    def clear_search(self):
        """Clear search and display all articles"""
        if not self.articles:
            return
            
        self.keyword_search_var.set("")
        self.results_text.delete(1.0, tk.END)
        self.hyperlinks = {}
        self.article_line_positions = []
        self.selected_article_idx = None
        
        # Display all articles (limited to first 10 for display)
        self.display_articles(self.articles)
        self.status_var.set(f"Displaying all {len(self.articles)} articles")
    
    def display_articles(self, articles_to_display, max_display=10):
        """Display articles in the results text widget"""
        self.current_displayed_articles = articles_to_display
        self.article_line_positions = []
        
        # Only show up to max_display articles for performance
        display_count = min(len(articles_to_display), max_display)
        
        for idx, article in enumerate(articles_to_display[:display_count], 1):
            # Record the line position where this article starts
            line_pos = int(self.results_text.index(tk.END).split('.')[0])
            self.article_line_positions.append(line_pos)
            
            # Insert article title with a tag for selection
            self.results_text.insert(tk.END, f"\nArticle {idx}:\n", "article_number")
            self.results_text.insert(tk.END, f"Title: {article['title']}\n", "article_title")
            
            # Insert rest of article info
            journal_text = f"Journal: {article['journal']} (IF: {article['impact_factor']:.1f})\n"
            date_text = f"Pub Date: {article['pub_date']}\n"
            self.results_text.insert(tk.END, journal_text + date_text)
            
            # Insert DOI with hyperlink if available
            if article['doi'] != 'N/A' and article['doi_url']:
                self.results_text.insert(tk.END, "DOI: ")
                
                # Create unique tag for this hyperlink
                link_tag = f"link_{idx}"
                self.hyperlinks[link_tag] = article['doi_url']
                
                # Insert the DOI with the hyperlink tag
                self.results_text.insert(tk.END, article['doi'], link_tag)
                self.results_text.insert(tk.END, "\n")
                
                # Add a "Download Full Paper" link if DOI is available
                download_tag = f"download_{idx}"
                self.results_text.insert(tk.END, "Full Paper: ")
                self.results_text.insert(tk.END, "[Download via Sci-Hub]", download_tag)
                self.results_text.insert(tk.END, "\n")
                self.results_text.tag_configure(download_tag, foreground="green", underline=1)
                self.hyperlinks[download_tag] = f"download_doi:{article['doi']}"
            else:
                self.results_text.insert(tk.END, "DOI: N/A\n")
            
            # Insert abstract
            if article['full_abstract'] and article['full_abstract'] != 'N/A':
                self.results_text.insert(tk.END, f"Abstract: {article['full_abstract']}\n")
            else:
                self.results_text.insert(tk.END, "Abstract: Not available\n")
            
            # Insert authors and keywords
            self.results_text.insert(tk.END, f"Authors: {article['authors']}\n")
            if article['keywords'] and article['keywords'] != 'N/A':
                self.results_text.insert(tk.END, f"Keywords: {article['keywords']}\n")
            
            # Insert separator
            self.results_text.insert(tk.END, "\n" + "-"*80 + "\n")
        
        # Show message if there are more articles than displayed
        if len(articles_to_display) > display_count:
            self.results_text.insert(tk.END, f"\nNote: {len(articles_to_display) - display_count} more articles not shown. Export to file to see all articles.\n")
        
        # Update tags for hyperlinks
        self.results_text.tag_configure("hyperlink", foreground="blue", underline=1)
        self.results_text.tag_configure("article_number", font=("Helvetica", 10, "bold"))
    
    def handle_text_click(self, event):
        """Handle clicks in the results text widget to select articles and activate hyperlinks"""
        index = self.results_text.index(f"@{event.x},{event.y}")
        
        # Check if the click is on a hyperlink
        for tag in self.results_text.tag_names(index):
            if tag in self.hyperlinks:
                url = self.hyperlinks[tag]
                
                # Handle Sci-Hub download requests
                if url.startswith("download_doi:"):
                    doi = url.replace("download_doi:", "")
                    
                    # Ask user where to save the file
                    save_dir = self.save_dir_var.get() or os.path.expanduser("~/Desktop")
                    filename = doi.replace("/", "_").replace(".", "_") + ".pdf"
                    output_path = os.path.join(save_dir, filename)
                    
                    # Update status
                    self.status_var.set(f"Attempting to download paper with DOI: {doi}...")
                    self.root.update_idletasks()
                    
                    # Create a progress window
                    progress_window = tk.Toplevel(self.root)
                    progress_window.title("Downloading Paper")
                    progress_window.geometry("400x150")
                    progress_window.transient(self.root)
                    progress_window.grab_set()
                    
                    # Add message
                    ttk.Label(progress_window, text=f"Downloading paper with DOI:\n{doi}", 
                             wraplength=380, justify=tk.CENTER).pack(pady=10)
                    
                    # Add progress bar
                    progress = ttk.Progressbar(progress_window, mode='indeterminate', length=350)
                    progress.pack(pady=10)
                    progress.start()
                    
                    # Run download in a thread to keep UI responsive
                    def download_thread():
                        result = download_paper_from_scihub(doi, output_path)
                        self.root.after(0, lambda: complete_download(result))
                    
                    def complete_download(result):
                        progress.stop()
                        progress_window.destroy()
                        
                        if result:
                            self.status_var.set(f"Downloaded paper to {result}")
                            messagebox.showinfo("Download Complete", 
                                               f"Paper was successfully downloaded to:\n{result}")
                            
                            # Ask if user wants to open the PDF
                            if messagebox.askyesno("Open PDF", "Would you like to open the PDF now?"):
                                if sys.platform == 'darwin':  # macOS
                                    os.system(f"open '{result}'")
                                elif sys.platform == 'win32':  # Windows
                                    os.startfile(result)
                                else:  # Linux
                                    os.system(f"xdg-open '{result}'")
                        else:
                            self.status_var.set("Failed to download paper from Sci-Hub")
                            messagebox.showerror("Download Failed", 
                                                "Could not download the paper from Sci-Hub.\n"
                                                "Try again later or try a different source.")
                    
                    # Start download thread
                    threading.Thread(target=download_thread).start()
                else:
                    # Regular URL - open in browser
                    webbrowser.open_new_tab(url)
                return
        
        # Check if the click is on an article to select it
        if self.article_line_positions and self.current_displayed_articles:
            # Get the current line number
            line_number = int(index.split('.')[0])
            
            # Find which article was clicked on by its position in the text widget
            for i, start_line in enumerate(self.article_line_positions):
                if start_line <= line_number <= start_line + 20:  # Approximate article size in lines
                    # Select this article
                    self.selected_article_idx = i
                    
                    # Remove previous selection highlight
                    self.results_text.tag_remove("selected_article", "1.0", tk.END)
                    
                    # Highlight the selected article - estimate 20 lines per article
                    start_pos = f"{start_line}.0"
                    end_pos = f"{start_line + 20}.0"
                    self.results_text.tag_add("selected_article", start_pos, end_pos)
                    self.results_text.tag_configure("selected_article", background="#e6f2ff")  # Light blue background
                    
                    # Update status to show the article is selected
                    self.status_var.set(f"Selected: {self.current_displayed_articles[i]['title']}")
                    
                    # Enable any buttons that work with selected articles
                    if hasattr(self, 'related_button'):
                        self.related_button.config(state=tk.NORMAL)
                    
                    break
    
    def perform_related_search(self, terms_window, key_terms, author_last_names, selected_article):
        """Perform the actual search after confirming terms"""
        # Close the terms window if it exists
        if terms_window:
            terms_window.destroy()
        
        # Find articles with matching terms
        related_articles = []
        
        # Update status
        self.status_var.set(f"Analyzing {len(self.articles)} articles for matches...")
        self.root.update_idletasks()
        
        for article in self.articles:
            if article == selected_article:  # Skip the selected article itself
                continue
                
            # Calculate a relevance score
            relevance = 0
            matched_terms = set()
            
            # Check for term matches in title (highest weight)
            title_lower = article['title'].lower()
            for term in key_terms:
                if term.lower() in title_lower:
                    relevance += 10  # Highest weight for title matches
                    matched_terms.add(term)
            
            # Check for term matches in abstract
            abstract_lower = article['full_abstract'].lower()
            for term in key_terms:
                if term.lower() in abstract_lower:
                    relevance += 5  # Medium weight for abstract matches
                    matched_terms.add(term)
            
            # Check for term matches in keywords
            keywords_lower = article['keywords'].lower()
            for term in key_terms:
                if term.lower() in keywords_lower:
                    relevance += 8  # High weight for keyword matches
                    matched_terms.add(term)
            
            # Check for same authors (much lower weight than before)
            author_matches = []
            for author in author_last_names:
                if author.lower() in article['authors'].lower():
                    relevance += 1  # Very low weight for same author - primarily using medical content now
                    author_matches.append(author)
            
            # Journal-based matching - if from the same journal, give a small boost
            if article['journal'] == selected_article['journal']:
                relevance += 2  # Small boost for same journal
            
            # Add to related if it has some relevance from medical terms
            if relevance > 0 and len(matched_terms) > 0:  # Must have at least one medical term match
                article_copy = article.copy()
                article_copy['relevance'] = relevance
                article_copy['matched_terms'] = list(matched_terms)
                article_copy['matched_authors'] = author_matches
                article_copy['same_journal'] = (article['journal'] == selected_article['journal'])
                related_articles.append(article_copy)
        
        # Sort by relevance
        related_articles.sort(key=lambda x: x['relevance'], reverse=True)
        
        # Update status
        self.status_var.set(f"Found {len(related_articles)} related articles")
        self.root.update_idletasks()
        
        if not related_articles:
            messagebox.showinfo("Related Articles", "No articles with related medical terms found")
            return
        
        # Create a new window to show related articles
        related_window = tk.Toplevel(self.root)
        related_window.title("Related Articles by Medical Terms")
        related_window.geometry("800x800")
        
        # Add content to the window
        frame = ttk.Frame(related_window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Add title
        ttk.Label(frame, text=f"Articles with related medical terms to: {selected_article['title']}", 
                 font=("Helvetica", 12, "bold"), wraplength=750).pack(pady=10)
        
        # Create scrollable text widget for results
        text_frame = ttk.Frame(frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        result_text = tk.Text(text_frame, yscrollcommand=scrollbar.set, wrap=tk.WORD)
        result_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=result_text.yview)
        
        # Configure tags for formatting
        result_text.tag_configure("hyperlink", foreground="blue", underline=1)
        result_text.tag_configure("title", font=("Helvetica", 10, "bold"), foreground="dark green")
        result_text.tag_configure("matched_term", background="#FFFF99")  # Highlight matched terms
        result_text.tag_configure("heading", font=("Helvetica", 9, "bold"))
        result_text.tag_configure("same_journal", foreground="purple")
        result_hyperlinks = {}
        
        # Display number of related articles found
        result_text.insert(tk.END, f"Found {len(related_articles)} related articles based on {len(key_terms)} medical terms\n\n", "heading")
        
        # Add related articles
        for idx, article in enumerate(related_articles[:30], 1):  # Show up to 30 articles
            # Insert article info
            result_text.insert(tk.END, f"{idx}. ", "heading")
            result_text.insert(tk.END, f"{article['title']}\n", "title")
            
            # Mark if it's the same journal
            if article.get('same_journal'):
                result_text.insert(tk.END, f"    Journal: {article['journal']} (IF: {article['impact_factor']:.1f})\n", "same_journal")
            else:
                result_text.insert(tk.END, f"    Journal: {article['journal']} (IF: {article['impact_factor']:.1f})\n")
                
            result_text.insert(tk.END, f"    Publication Date: {article['pub_date']}\n")
            
            # Insert DOI with hyperlink
            if article['doi'] != 'N/A' and article['doi_url']:
                result_text.insert(tk.END, "    DOI: ")
                
                # Create unique tag for this hyperlink
                link_tag = f"rel_link_{idx}"
                result_hyperlinks[link_tag] = article['doi_url']
                
                result_text.insert(tk.END, article['doi'], link_tag)
                result_text.insert(tk.END, "\n")
            else:
                result_text.insert(tk.END, f"    DOI: {article['doi']}\n")
            
            # Show matched terms with higher prominence
            if article['matched_terms']:
                result_text.insert(tk.END, "    Matched Medical Terms: ", "heading")
                result_text.insert(tk.END, ", ".join(article['matched_terms']) + "\n")
            
            # Show authors as secondary information (de-emphasized)
            if article['matched_authors']:
                result_text.insert(tk.END, "    Matched Authors: ")
                result_text.insert(tk.END, ", ".join(article['matched_authors']) + "\n")
            
            # Show relevance metrics
            result_text.insert(tk.END, f"    Relevance Score: {article['relevance']}\n")
            
            # Insert divider
            result_text.insert(tk.END, f"\n{'-' * 80}\n\n")
        
        # Add hyperlink click handling
        # Add hyperlink click handling
        def open_hyperlink(event):
            index = result_text.index(f"@{event.x},{event.y}")
            for tag in result_text.tag_names(index):
                if tag in result_hyperlinks:
                    url = result_hyperlinks[tag]
                    webbrowser.open_new_tab(url)
                    break
                    
        result_text.bind("<Button-1>", open_hyperlink)
    def browse_directory(self):
        """Browse for a directory to save the exported files"""
        directory = filedialog.askdirectory(initialdir=self.save_dir_var.get())
        if directory:
            self.save_dir_var.set(directory)
    
    def validate_inputs(self):
        """Validate the input fields"""
        # Check days back
        try:
            if not self.today_only_var.get() and not self.month_only_var.get():
                days_back = int(self.days_back_var.get())
                if days_back < 0:
                    messagebox.showerror("Input Error", "Days back must be a positive number")
                    return False
        except ValueError:
            messagebox.showerror("Input Error", "Days back must be a number")
            return False
        
        # Check max results
        try:
            max_results = int(self.max_results_var.get())
            if max_results <= 0:
                messagebox.showerror("Input Error", "Maximum results must be a positive number")
                return False
            if max_results > 5000:  # Set a reasonable upper limit
                response = messagebox.askokcancel("Large Request", 
                    "Requesting a very large number of results (>5000) may take a long time and could be unstable. Continue anyway?")
                if not response:
                    return False
        except ValueError:
            messagebox.showerror("Input Error", "Maximum results must be a number")
            return False
        
        # Check save directory
        save_dir = self.save_dir_var.get()
        if not os.path.isdir(save_dir):
            messagebox.showerror("Input Error", f"Save directory does not exist: {save_dir}")
            return False
        
        return True
    
    def fetch_articles(self):
        """Fetch articles based on current settings and display them in the UI."""
        # Validate inputs
        try:
            max_results = int(self.max_results_var.get())
            if max_results <= 0:
                raise ValueError("Maximum results must be positive")
        except ValueError as e:
            messagebox.showerror("Input Error", f"Invalid maximum results: {e}")
            return
        
        # Days back validation only needed if not using today_only or month_only
        if not self.today_only_var.get() and not self.month_only_var.get():
            try:
                days_back = int(self.days_back_var.get())
                if days_back < 0:
                    raise ValueError("Days back must be non-negative")
            except ValueError as e:
                messagebox.showerror("Input Error", f"Invalid days back: {e}")
                return

        # Specific year validation if selected
        if self.specific_year_var.get():
            try:
                year = int(self.year_var.get())
                if year < 1980 or year > 2025:
                    raise ValueError("Year must be between 1980 and 2025")
            except ValueError as e:
                messagebox.showerror("Input Error", f"Invalid year: {e}")
                return

        # Disable UI elements during fetch
        self.fetch_button.config(state=tk.DISABLED)
        self.clear_button.config(state=tk.DISABLED)
        
        # Display the progress bar - using pack instead of grid
        self.progress_bar.pack(in_=self.action_frame, side=tk.TOP, fill=tk.X, pady=5)
        self.progress_bar.start(10)
        self.status_var.set("Fetching articles...")
        
        # Prepare search parameters based on current settings
        keyword = self.fetch_keyword_var.get().strip()
        subspecialty = self.subspecialty_var.get()
        journal = self.journal_var.get() if self.journal_var.get() != "All Journals" else ""
        
        if self.today_only_var.get():
            date_filter = "Today Only"
        elif self.month_only_var.get():
            date_filter = "This Month Only"
        elif self.specific_year_var.get():
            days_back_val = int(self.days_back_var.get()) if self.days_back_var.get() else 0
            if days_back_val > 0:
                date_filter = f"Year {self.year_var.get()} (Last {days_back_val} days)"
            else:
                date_filter = f"Year {self.year_var.get()}"
        else:
            date_filter = "Past Days"
            
        days_back = int(self.days_back_var.get()) if self.days_back_var.get() else 0
        max_results = int(self.max_results_var.get())
        
        # Create a summary of the search
        summary_parts = []
        if self.specific_year_var.get():
            days_back_val = int(self.days_back_var.get()) if self.days_back_var.get() else 0
            if days_back_val > 0:
                summary_parts.append(f"Fetching articles published in the last {days_back_val} days of {self.year_var.get()}")
            else:
                summary_parts.append(f"Fetching articles published in {self.year_var.get()}")
        else:
            summary_parts.append(f"Fetching {'today' if self.today_only_var.get() else 'this month' if self.month_only_var.get() else f'last {days_back} days'}'s articles")
        
        if keyword:
            summary_parts.append(f"with keyword '{keyword}'")
        if subspecialty != "All Subspecialties" and subspecialty.lower() != "all":
            summary_parts.append(f"in {subspecialty}")
        if journal:
            summary_parts.append(f"from {journal}")
        
        summary = " ".join(summary_parts)
        
        # Save current search settings
        search_settings = {
            "date_filter": date_filter,
            "days_back": days_back,
            "specific_year": self.year_var.get() if self.specific_year_var.get() else "",
            "max_results": max_results,
            "subspecialty": subspecialty,
            "keyword": keyword,
            "journal": journal,
            "export_format": self.export_format_var.get(),
            "save_dir": self.save_dir_var.get()
        }
        
        # Update current settings
        self.current_search_settings = search_settings
        
        # Log search parameters
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        search_entry = {
            "timestamp": timestamp,
            "summary": summary,
            "settings": search_settings
        }
        
        # Add to search history with limit to last 50 entries
        self.search_history.append(search_entry)
        if len(self.search_history) > 50:
            self.search_history = self.search_history[-50:]
        
        # Save settings before starting search
        self.save_search_settings()
        
        # Start a thread to prevent UI freezing
        threading.Thread(target=self.fetch_thread, args=(
            keyword, 
            subspecialty, 
            journal,
            self.today_only_var.get(),
            self.month_only_var.get(),
            days_back,
            max_results,
            search_entry,  # Pass the search_entry to update with results count
            self.specific_year_var.get(),  # Pass specific year flag
            self.year_var.get() if self.specific_year_var.get() else ""  # Pass the year if specific year is checked
        )).start()
    
    def find_related_articles(self):
        """Find articles related to the currently selected article"""
        if self.selected_article_idx is None or not self.current_displayed_articles:
            messagebox.showinfo("Info", "Please select an article first by clicking its title")
            return
        
        # Show a loading indicator in the status bar
        self.status_var.set("Finding related articles...")
        self.root.update_idletasks()
        
        selected_article = self.current_displayed_articles[self.selected_article_idx]
        
        # Extract key terms from the selected article
        key_terms = []
        
        # 1. First check for existing keywords in the article metadata
        if selected_article['keywords']:
            keywords = [k.strip().lower() for k in selected_article['keywords'].split(',')]
            key_terms.extend(keywords)
        
        # 2. Extract keywords from title
        title_keywords = extract_keywords_from_text(selected_article['title'], key_terms)
        key_terms.extend(title_keywords)
        
        # 3. Extract keywords from abstract
        abstract_keywords = extract_keywords_from_text(selected_article['full_abstract'], key_terms)
        key_terms.extend(abstract_keywords)
        
        # Remove duplicates while preserving order
        unique_key_terms = []
        for term in key_terms:
            if term not in unique_key_terms:
                unique_key_terms.append(term)
        
        key_terms = unique_key_terms
        
        # We'll de-emphasize author matching and focus on medical content relationships
        # But still collect authors for informational purposes
        author_last_names = []
        for author in selected_article['authors'].split(', '):
            if author and len(author.split()) > 0:
                author_last_names.append(author.split()[0])  # Get first element (last name)
        
        if not key_terms:
            messagebox.showinfo("Info", "Unable to extract medical terms for finding related articles")
            return
        
        # Skip showing the extracted terms window and directly perform the search
        self.perform_related_search(None, key_terms, author_last_names, selected_article)

    def get_date_range(self):
        """
        Get the appropriate date range based on user settings
        Returns a tuple of (start_date, end_date, description)
        """
        today = datetime.today()
        end_date = today
        
        if self.today_only_var.get():
            # For today's articles, use only today's date for strict filtering
            start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)  # Beginning of today
            description = "today's"
            
        elif self.month_only_var.get():
            # For this month's articles
            if today.day <= 7:
                # If we're in the first week of the month, include the last month as well
                # to ensure we capture recent publications that might have been published at the end of last month
                last_month = today.replace(day=1) - timedelta(days=1)
                start_date = last_month.replace(day=1)  # First day of last month
                description = f"{last_month.strftime('%B')} and {today.strftime('%B')}"
            else:
                # Otherwise just use current month
                start_date = today.replace(day=1)  # First day of current month
                description = f"this month's ({today.strftime('%B')})"
        
        elif self.specific_year_var.get():
            # For specific year articles
            try:
                year = int(self.year_var.get())
                days_back = int(self.days_back_var.get()) if self.days_back_var.get() else 0
                
                if days_back > 0:
                    # Use the year's end date and subtract days_back
                    end_date = datetime(year, 12, 31, 23, 59, 59)  # December 31st, 23:59:59 of selected year
                    start_date = end_date - timedelta(days=days_back)
                    
                    # Ensure start_date doesn't go before the beginning of the year
                    year_start = datetime(year, 1, 1)
                    if start_date < year_start:
                        start_date = year_start
                        
                    description = f"published in {year} (last {days_back} days of the year)"
                else:
                    # Use the entire year
                    start_date = datetime(year, 1, 1)  # January 1st of selected year
                    end_date = datetime(year, 12, 31, 23, 59, 59)  # December 31st, 23:59:59 of selected year
                    description = f"published in {year}"
            except ValueError:
                # Default to current year if invalid input
                year = today.year
                start_date = datetime(year, 1, 1)
                end_date = datetime(year, 12, 31, 23, 59, 59)
                description = f"published in {year}"
                
        else:
            # Use the specified number of days back
            try:
                days_back = int(self.days_back_var.get())
                start_date = today - timedelta(days=days_back)
                description = f"the past {days_back} days'"
            except ValueError:
                # Default to 30 days if invalid input
                start_date = today - timedelta(days=30)
                description = "the past 30 days'"
                
        return (start_date, end_date, description)
        
    def filter_articles(self, articles, date_range=None, content_filters=None, max_results=None):
        """
        Comprehensive filtering function that combines date and content filtering
        
        Parameters:
        - articles: List of articles to filter
        - date_range: Optional tuple of (start_date, end_date, description) from get_date_range()
        - content_filters: Optional dict of content filters from get_content_filters()
        - max_results: Optional maximum number of results to return
        
        Returns:
        - filtered_articles: List of filtered articles
        - filter_stats: Dict with statistics about the filtering process
        """
        if not articles:
            return [], {"original": 0, "date_filtered": 0, "content_filtered": 0, "final": 0}
            
        filter_stats = {"original": len(articles)}
        filtered_articles = articles.copy()
        
        # Apply date filtering if specified
        if date_range:
            start_date, end_date, _ = date_range
            date_filtered = []
            
            # Check if we're using today-only mode for extra-strict filtering
            today_only = self.today_only_var.get() if hasattr(self, 'today_only_var') else 0
            today_date = datetime.now().date()
            
            for article in filtered_articles:
                # Get the publication date from the article
                pub_date_str = article.get('pub_date', 'Unknown date')
                pub_date = self.parse_article_date(pub_date_str)
                
                # Extra strict today-only mode
                if today_only and pub_date:
                    if pub_date.date() != today_date:
                        # Explicitly skip this article, even if it somehow passes other filters
                        continue
                    else:
                        date_filtered.append(article)
                # Regular date range filtering for non-today-only mode
                elif pub_date and start_date <= pub_date <= end_date:
                    date_filtered.append(article)
                elif not pub_date and not today_only:
                    # If we couldn't parse the date and we're not in today-only mode,
                    # include it (err on the side of inclusion)
                    date_filtered.append(article)
                    
            filtered_articles = date_filtered
            filter_stats["date_filtered"] = len(filtered_articles)
            
        # Apply content filtering if specified
        if content_filters:
            # Apply keyword filtering if specified
            if content_filters.get("keyword"):
                keyword = content_filters["keyword"].lower()
                keyword_filtered = []
                
                for article in filtered_articles:
                    # Search in title, abstract, keywords, journal name, and author names
                    searchable_text = (
                        article.get('title', '').lower() + ' ' +
                        article.get('full_abstract', '').lower() + ' ' +
                        article.get('keywords', '').lower() + ' ' +
                        article.get('journal', '').lower() + ' ' +
                        article.get('authors', '').lower()
                    )
                    
                    if keyword in searchable_text:
                        keyword_filtered.append(article)
                        
                filtered_articles = keyword_filtered
                
            # Apply subspecialty filtering if specified
            if content_filters.get("subspecialty"):
                subspecialty = content_filters["subspecialty"].lower()
                subspecialty_filtered = []
                
                # Define subspecialty keywords for each category
                subspecialty_terms = {
                    "retina": ["retina", "macula", "vitreous", "amd", "diabetic retinopathy", "retinal detachment", 
                               "epiretinal", "subretinal", "intraretinal", "photoreceptor", "choroidal"],
                    "glaucoma": ["glaucoma", "intraocular pressure", "iop", "trabeculectomy", "angle-closure", 
                                 "open-angle", "trabecular meshwork", "optic nerve", "visual field", "ocular hypertension"],
                    "cornea": ["cornea", "keratoconus", "corneal transplant", "keratoplasty", "dry eye", 
                               "descemet", "epithelium", "endothelium", "keratitis", "corneal edema", "fuchs"],
                    "cataract": ["cataract", "phacoemulsification", "iol", "intraocular lens", "phaco", 
                                 "capsular", "pseudophakia", "toric", "multifocal", "presbyopia-correcting"],
                    "refractive": ["lasik", "refractive surgery", "prk", "myopia", "hyperopia", "presbyopia", 
                                   "astigmatism", "keratorefractive", "small incision lenticule extraction", "smile"],
                    "pediatric": ["pediatric", "strabismus", "amblyopia", "rop", "retinopathy of prematurity", 
                                  "esotropia", "exotropia", "hypertropia", "pediatric cataract", "congenital"],
                    "oculoplastics": ["oculoplastic", "eyelid", "orbit", "lacrimal", "blepharoplasty", 
                                     "ptosis", "enophthalmos", "exophthalmos", "thyroid eye disease", "orbital"],
                    "uveitis": ["uveitis", "inflammatory", "ocular inflammation", "choroiditis", 
                               "scleritis", "iritis", "vitritis", "anterior uveitis", "posterior uveitis"],
                    "neuro-ophthalmology": ["neuro-ophthalmology", "optic nerve", "visual field", "papilledema", 
                                           "optic neuritis", "cranial nerve", "nystagmus", "diplopia", "chiasm"]
                }
                
                # Get the relevant terms for the selected subspecialty
                relevant_terms = subspecialty_terms.get(subspecialty.lower(), [])
                
                # If we have terms for this subspecialty, use them for filtering
                if relevant_terms:
                    for article in filtered_articles:
                        article_text = (
                            article.get('title', '').lower() + ' ' +
                            article.get('full_abstract', '').lower() + ' ' +
                            article.get('keywords', '').lower()
                        )
                        
                        # Check if any of the subspecialty terms are in the article
                        if any(term in article_text for term in relevant_terms):
                            subspecialty_filtered.append(article)
                            
                    filtered_articles = subspecialty_filtered
                
            # Apply journal filtering if specified
            if content_filters.get("journal"):
                journal_name = content_filters["journal"].lower()
                journal_filtered = []
                
                for article in filtered_articles:
                    if journal_name in article.get('journal', '').lower():
                        journal_filtered.append(article)
                        
                filtered_articles = journal_filtered
                
            # Apply impact factor filtering if specified
            if content_filters.get("impact_factor_min") > 0:
                min_if = content_filters["impact_factor_min"]
                if_filtered = []
                
                for article in filtered_articles:
                    try:
                        if_value = float(article.get('impact_factor', 0))
                        if if_value >= min_if:
                            if_filtered.append(article)
                    except (ValueError, TypeError):
                        # If impact factor can't be parsed, skip this filter
                        pass
                        
                filtered_articles = if_filtered
            
            filter_stats["content_filtered"] = len(filtered_articles)
                
        # Sort by publication date (newest first) and then by impact factor (highest first)
        filtered_articles.sort(key=lambda a: (self.parse_article_date(a.get('pub_date', '')) or datetime(1900, 1, 1), 
                                              float(a.get('impact_factor', 0) or 0)), 
                              reverse=True)
        
        # Limit results if specified
        if max_results and len(filtered_articles) > max_results:
            filtered_articles = filtered_articles[:max_results]
            
        filter_stats["final"] = len(filtered_articles)
        return filtered_articles, filter_stats
    
    def parse_article_date(self, date_string):
        """
        Parse publication date from various formats
        
        Parameters:
        - date_string: The date string to parse
        
        Returns:
        - datetime object or None if parsing failed
        """
        if not date_string or date_string == 'Unknown date':
            return None
            
        # Try to parse the date
        date_obj = None
        
        # Try various date formats - extended for better date detection
        date_formats = [
            '%Y-%m-%d', '%Y/%m/%d', '%d %b %Y', '%b %d, %Y',
            '%Y-%m', '%Y/%m', '%b %Y', '%Y %b',
            '%d.%m.%Y', '%m/%d/%Y', '%Y%m%d'
        ]
        
        # First try to directly parse with standard formats
        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(date_string, fmt)
                return date_obj
            except ValueError:
                continue
        
        # If standard formats fail, try more flexible parsing
        # Look for patterns that might indicate a date component
        try:
            # Try to extract year, month, day from the string
            year_pattern = r'(?:^|\D)(\d{4})(?:\D|$)'  # 4-digit year
            year_match = re.search(year_pattern, date_string)
            
            if year_match:
                year = int(year_match.group(1))
                
                # Look for month (numeric or text)
                month_pattern = r'(?:^|\D)(\d{1,2})(?:\D|$)'  # 1 or 2 digit month
                month_text_pattern = r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b'
                
                month = None
                month_match = re.search(month_pattern, date_string)
                month_text_match = re.search(month_text_pattern, date_string, re.IGNORECASE)
                
                if month_text_match:
                    month_abbr = month_text_match.group(1).capitalize()
                    # Convert month abbreviation to number (Jan=1, Feb=2, etc.)
                    for i, m in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], 1):
                        if month_abbr.startswith(m):
                            month = i
                            break
                elif month_match:
                    potential_month = int(month_match.group(1))
                    if 1 <= potential_month <= 12:
                        month = potential_month
                
                # Look for day
                day_pattern = r'\b(\d{1,2})\b'
                potential_days = re.findall(day_pattern, date_string)
                
                day = 1  # Default to 1st of the month if no day found
                
                # Check if there's a number that could be a day
                for potential_day in potential_days:
                    potential_day = int(potential_day)
                    if 1 <= potential_day <= 31 and potential_day != year and potential_day != month:
                        day = potential_day
                        break
                
                # Create datetime object with extracted components
                if month:
                    try:
                        return datetime(year, month, day)
                    except ValueError:
                        # If day is invalid for this month, use last day of month
                        if day > 28:
                            try:
                                last_day = calendar.monthrange(year, month)[1]
                                return datetime(year, month, last_day)
                            except ValueError:
                                pass
                        
                        # Fallback to just year and month
                        return datetime(year, month, 1)
                else:
                    # If we only have year, use January 1st
                    return datetime(year, 1, 1)
        
        except (ValueError, TypeError, AttributeError) as e:
            pass
            
        # If all parsing attempts fail, return None
        return None

    def get_content_filters(self):
        """
        Get content filter settings from user input
        Returns a dictionary of content filter parameters
        """
        filters = {
            "keyword": None,
            "subspecialty": None,
            "journal": None,
            "impact_factor_min": 0.0
        }
        
        # Get keyword filter
        keyword = self.fetch_keyword_var.get().strip() if hasattr(self, 'fetch_keyword_var') else ""
        if keyword:
            filters["keyword"] = keyword
            
        # Get subspecialty filter
        subspecialty = self.subspecialty_var.get() if hasattr(self, 'subspecialty_var') else "All"
        if subspecialty and subspecialty != "All":
            filters["subspecialty"] = subspecialty
            
        # Get journal filter
        journal = self.journal_var.get() if hasattr(self, 'journal_var') else ""
        if journal:
            filters["journal"] = journal
            
        # Get impact factor filter if available
        try:
            if hasattr(self, 'impact_factor_var'):
                impact_min = float(self.impact_factor_var.get())
                if impact_min > 0:
                    filters["impact_factor_min"] = impact_min
        except (ValueError, AttributeError):
            pass
            
        return filters
        
    def apply_advanced_filtering(self, articles, content_filters, max_results=None):
        """
        Apply advanced content filtering to the articles
        
        Parameters:
        - articles: List of articles to filter
        - content_filters: Dictionary of filter criteria from get_content_filters()
        - max_results: Optional maximum number of results to return
        
        Returns:
        - Filtered list of articles
        """
        if not articles:
            return []
            
        filtered_articles = articles.copy()
        
        # Apply keyword filtering if specified
        if content_filters.get("keyword"):
            keyword = content_filters["keyword"].lower()
            keyword_filtered = []
            
            for article in filtered_articles:
                # Search in title, abstract, keywords, journal name, and author names
                searchable_text = (
                    article.get('title', '').lower() + ' ' +
                    article.get('full_abstract', '').lower() + ' ' +
                    article.get('keywords', '').lower() + ' ' +
                    article.get('journal', '').lower() + ' ' +
                    article.get('authors', '').lower()
                )
                
                if keyword in searchable_text:
                    keyword_filtered.append(article)
                    
            filtered_articles = keyword_filtered
            
        # Apply subspecialty filtering if specified
        if content_filters.get("subspecialty"):
            subspecialty = content_filters["subspecialty"].lower()
            subspecialty_filtered = []
            
            # Define subspecialty keywords for each category
            subspecialty_terms = {
                "retina": ["retina", "macula", "vitreous", "amd", "diabetic retinopathy", "retinal detachment"],
                "glaucoma": ["glaucoma", "intraocular pressure", "trabeculectomy", "angle-closure"],
                "cornea": ["cornea", "keratoconus", "corneal transplant", "keratoplasty", "dry eye"],
                "cataract": ["cataract", "phacoemulsification", "iol", "intraocular lens"],
                "refractive": ["lasik", "refractive surgery", "prk", "myopia", "hyperopia", "presbyopia"],
                "pediatric": ["pediatric", "strabismus", "amblyopia", "rop", "retinopathy of prematurity"],
                "oculoplastics": ["oculoplastic", "eyelid", "orbit", "lacrimal", "blepharoplasty"],
                "uveitis": ["uveitis", "inflammatory", "ocular inflammation", "choroiditis"],
                "neuro-ophthalmology": ["neuro-ophthalmology", "optic nerve", "visual field", "papilledema"]
            }
            
            # Get the relevant terms for the selected subspecialty
            relevant_terms = subspecialty_terms.get(subspecialty.lower(), [])
            
            # If we have terms for this subspecialty, use them for filtering
            if relevant_terms:
                for article in filtered_articles:
                    article_text = (
                        article.get('title', '').lower() + ' ' +
                        article.get('full_abstract', '').lower() + ' ' +
                        article.get('keywords', '').lower()
                    )
                    
                    # Check if any of the subspecialty terms are in the article
                    if any(term in article_text for term in relevant_terms):
                        subspecialty_filtered.append(article)
                        
                filtered_articles = subspecialty_filtered
            
        # Apply journal filtering if specified
        if content_filters.get("journal"):
            journal_name = content_filters["journal"].lower()
            journal_filtered = []
            
            for article in filtered_articles:
                if journal_name in article.get('journal', '').lower():
                    journal_filtered.append(article)
                    
            filtered_articles = journal_filtered
            
        # Apply impact factor filtering if specified
        if content_filters.get("impact_factor_min") > 0:
            min_if = content_filters["impact_factor_min"]
            if_filtered = []
            
            for article in filtered_articles:
                try:
                    if_value = float(article.get('impact_factor', 0))
                    if if_value >= min_if:
                        if_filtered.append(article)
                except (ValueError, TypeError):
                    # If impact factor can't be parsed, skip this filter
                    pass
                    
            filtered_articles = if_filtered
            
        # Sort by impact factor (highest first)
        filtered_articles.sort(key=lambda a: float(a.get('impact_factor', 0) or 0), reverse=True)
        
        # Limit results if specified
        if max_results and len(filtered_articles) > max_results:
            filtered_articles = filtered_articles[:max_results]
            
        return filtered_articles

    def fetch_thread(self, keyword, subspecialty, journal, today_only, month_only, days_back, max_results, search_entry, specific_year=False, year=""):
        """Thread function to fetch articles"""
        try:
            self.root.after(0, lambda: self.progress_var.set(10))
            
            # Get the export format if set
            export_format = self.export_format_var.get().lower() if hasattr(self, 'export_format_var') else None
            save_dir = self.save_dir_var.get() if hasattr(self, 'save_dir_var') else os.path.expanduser("~/Desktop")
            
            # Get date range for more detailed logging and user feedback
            date_range = self.get_date_range()
            start_date, end_date, date_description = date_range
            
            # Get content filters
            content_filters = self.get_content_filters()
            
            # Log the search parameters for debugging
            search_params = {
                "Keyword": keyword if keyword else "None",
                "Subspecialty": subspecialty if subspecialty != "All" else "All",
                "Journal": journal if journal else "All",
                "Date Range": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({date_description})",
                "Maximum Results": max_results,
                "Content Filters": content_filters,
                "Specific Year": year if specific_year else "None",
                "Days Back": days_back
            }
            logger.info(f"Search parameters: {search_params}")
            
            # Get default API_KEY and email
            api_key = self.api_key_var.get() if hasattr(self, 'api_key_var') else None
            email = self.email_var.get() if hasattr(self, 'email_var') else "user@example.com"
            
            # Set up progress tracking
            self.root.after(0, lambda: self.status_var.set(f"Fetching {date_description} articles..."))
            self.root.after(0, lambda: self.progress_var.set(20))
            
            # First attempt with adjusted settings to get more results
            adjusted_max_results = max_results * 20  # Setting higher initial multiplier to fetch more results
            self.root.after(0, lambda: self.status_var.set(f"Searching PubMed for {date_description} ophthalmology articles..."))
            
            # For specific year searches, use a wider range and filter later
            search_days_back = days_back
            if specific_year:
                # If days_back is specified with specific_year, we'll still use a wider search window
                # but will apply precise filtering afterward
                search_days_back = 365  # Use full year for initial search
                today_only = False
                month_only = False
                
            # Fetch articles
            articles = fetch_recent_ophthalmology_articles(
                email=email,
                api_key=api_key,
                days_back=search_days_back,
                max_results=adjusted_max_results,
                min_impact_factor=content_filters.get("impact_factor_min", 0.0),
                subspecialty=subspecialty if subspecialty != "All" else None,
                today_only=today_only,
                month_only=month_only,
                search_keyword=keyword,
                specific_journal=journal
            )
            
            self.root.after(0, lambda: self.progress_var.set(40))
            
            # If we don't get enough articles, try expanding the search
            if len(articles) < max_results and (today_only or month_only or specific_year):
                self.root.after(0, lambda: self.status_var.set(f"First attempt found {len(articles)} articles. Expanding search..."))
                
                # Aggressive second attempt with larger expansion factor
                expanded_max = max_results * 100  # Much larger multiplier for second attempt
                
                # For today's articles, expand to past 5 days
                if today_only:
                    expanded_days_back = 5
                    today_expanded = False
                    month_expanded = False
                    year_expanded = False
                # For month's articles, if we're early in the month, expand to include more of last month
                elif month_only and datetime.today().day <= 10:
                    expanded_days_back = 45  # Including more of last month
                    today_expanded = False
                    month_expanded = True
                    year_expanded = False
                # For specific year, expand search range
                elif specific_year:
                    expanded_days_back = 730  # Two years worth
                    today_expanded = False
                    month_expanded = False
                    year_expanded = True
                else:
                    expanded_days_back = 30
                    today_expanded = False
                    month_expanded = True
                    year_expanded = False
                
                self.root.after(0, lambda: self.status_var.set(f"Expanding search to past {expanded_days_back} days..."))
                
                second_attempt = fetch_recent_ophthalmology_articles(
                    email=email,
                    api_key=api_key,
                    days_back=expanded_days_back,
                    max_results=expanded_max,
                    min_impact_factor=content_filters.get("impact_factor_min", 0.0),
                    subspecialty=subspecialty if subspecialty != "All" else None,
                    today_only=today_expanded,
                    month_only=month_expanded,
                    search_keyword=keyword,
                    specific_journal=journal
                )
                
                # If we still don't have enough, make one final attempt with even larger factors
                if len(second_attempt) < max_results:
                    self.root.after(0, lambda: self.status_var.set(f"Second attempt found {len(second_attempt)} articles. Final expansion..."))
                    self.root.after(0, lambda: self.progress_var.set(50))
                    
                    # Ultimate attempt with extreme parameters
                    final_max = max_results * 200  # Extreme multiplier for final attempt
                    final_days_back = 60  # Go back two months
                    # For specific year, use even wider search
                    if specific_year:
                        final_days_back = 1095  # Three years worth
                    
                    self.root.after(0, lambda: self.status_var.set(f"Making final comprehensive search attempt..."))
                    
                    
                    final_attempt = fetch_recent_ophthalmology_articles(
                        email=email,
                        api_key=api_key,
                        days_back=final_days_back,
                        max_results=final_max,
                        min_impact_factor=content_filters.get("impact_factor_min", 0.0),
                        subspecialty=subspecialty if subspecialty != "All" else None,
                        today_only=False,
                        month_only=False,
                        search_keyword=keyword,
                        specific_journal=journal
                    )
                    
                    # Now use our comprehensive filtering method
                    if len(final_attempt) > 0:
                        self.root.after(0, lambda: self.status_var.set(f"Post-processing {len(final_attempt)} articles with unified filtering..."))
                        filtered_results, filter_stats = self.filter_articles(
                            final_attempt, 
                            date_range=date_range if today_only or month_only or specific_year else None,
                            content_filters=content_filters,
                            max_results=max_results
                        )
                        
                        self.root.after(0, lambda: self.status_var.set(
                            f"Filtering reduced {filter_stats['original']} articles to {filter_stats['final']} relevant articles"))
                        
                        articles = filtered_results
                    else:
                        articles = final_attempt
                else:
                    # Use our unified filtering on the second attempt
                    filtered_results, filter_stats = self.filter_articles(
                        second_attempt,
                        date_range=date_range if today_only or month_only or specific_year else None,
                        content_filters=content_filters,
                        max_results=max_results
                    )
                    
                    self.root.after(0, lambda: self.status_var.set(
                        f"Filtering reduced {filter_stats['original']} articles to {filter_stats['final']} relevant articles"))
                    
                    articles = filtered_results
            else:
                # Apply our unified filtering approach to the first results
                if len(articles) > 0:
                    self.root.after(0, lambda: self.status_var.set(f"Applying unified filtering to {len(articles)} articles..."))
                    self.root.after(0, lambda: self.progress_var.set(70))
                    
                    filtered_results, filter_stats = self.filter_articles(
                        articles,
                        content_filters=content_filters,
                        date_range=date_range if today_only or month_only or specific_year else None,
                        max_results=max_results
                    )
                    
                    if filter_stats['final'] < filter_stats['original']:
                        self.root.after(0, lambda: self.status_var.set(
                            f"Filtering refined {filter_stats['original']} articles to {filter_stats['final']} most relevant articles"))
                    
                    articles = filtered_results
            
            # Update search history entry with results count
            search_entry['results_count'] = len(articles)
            
            # Store the articles for display
            self.articles = articles
            self.root.after(0, lambda: self.progress_var.set(80))
            
            # Handle no results case
            if not articles:
                message = "No articles found matching your criteria."
                if today_only:
                    message = "No articles found published today. Try using 'This Month's Articles' for more recent publications."
                elif month_only:
                    message = "No articles found published this month. Try adjusting your filters or date range."
                elif specific_year:
                    message = f"No articles found published in {year}. Try adjusting your filters or selecting a different year."
                
                self.root.after(0, lambda: messagebox.showinfo("Results", message))
                self.root.after(0, lambda: self.reset_ui())
                return
            
            # Export results if needed
            if export_format:
                self.root.after(0, lambda: self.status_var.set(f"Preparing to export {len(articles)} articles..."))
            
            # Save files based on selected format
            saved_files = []
            
            if export_format == "csv" or export_format == "all":
                csv_path = os.path.join(save_dir, "ophthalmology_articles.csv")
                save_to_csv(articles, csv_path)
                saved_files.append(("CSV", csv_path))
            
            if export_format == "txt" or export_format == "all":
                txt_path = os.path.join(save_dir, "ophthalmology_articles.txt")
                saved_txt = save_to_txt(articles, txt_path)
                if saved_txt:
                    saved_files.append(("Text", txt_path))
            
            if export_format == "excel" or export_format == "all":
                excel_path = os.path.join(save_dir, "ophthalmology_articles.xlsx")
                saved_excel = save_to_excel(articles, excel_path)
                if saved_excel:
                    saved_files.append(("Excel", excel_path))
            
                # Also save DOI URLs if available
                if any('doi' in article for article in articles):
                    doi_path = os.path.join(save_dir, "doi_urls.csv")
                    save_doi_urls(articles, doi_path)
                    saved_files.append(("DOI URLs", doi_path))
                
                # Show export summary if files were saved
                if saved_files:
                    files_info = "\n".join([f"• {f_type}: {os.path.basename(f_path)}" for f_type, f_path in saved_files])
                    self.root.after(0, lambda: messagebox.showinfo("Export Complete", 
                                                 f"Exported {len(articles)} articles to:\n{files_info}\n\nLocation: {save_dir}"))
            
            # Update progress to 100%
            self.root.after(0, lambda: self.progress_var.set(100))
            
            # Display articles in the UI
            self.root.after(0, lambda: self.display_articles(articles))
            self.root.after(0, lambda: self.status_var.set(f"Found {len(articles)} articles. Display complete."))
            
            # Reset UI when done
            self.root.after(0, lambda: self.reset_ui())
        
        except Exception as e:
            # Handle errors
            error_message = str(e)
            self.root.after(0, lambda: messagebox.showerror("Error", f"An error occurred: {error_message}"))
            self.root.after(0, lambda: self.reset_ui())
            import traceback
            traceback.print_exc()
    
    def reset_ui(self):
        """Re-enable UI elements after fetch completes"""
        # Stop progress bar
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        
        # Reset progress
        self.progress_var.set(0)
        
        # Re-enable input widgets
        for widget in self.input_widgets:
            widget.configure(state="normal")
        
        # Re-enable fetch button
        self.fetch_button.configure(state="normal")
        
        # Enable clear button if we have articles
        if hasattr(self, 'articles') and self.articles:
            self.clear_button.configure(state="normal")

    def enable_ui(self):
        """Re-enable UI elements after fetch completes"""
        self.fetch_button.config(state=tk.NORMAL)
        self.progress_var.set(0)
        
        # Check if any articles were found
        if self.articles:
            # Update status with a summary of the results and active filters
            if self.today_only_var.get():
                date_filter = "Today Only"
            elif self.month_only_var.get():
                date_filter = "This Month Only"
            elif self.specific_year_var.get():
                date_filter = f"Year {self.year_var.get()}"
            else:
                date_filter = f"Past {self.days_back_var.get()} Days"
                
            content_filters = []
            
            if self.fetch_keyword_var.get().strip():
                content_filters.append(f"Keyword: {self.fetch_keyword_var.get().strip()}")
                
            if self.journal_var.get():
                content_filters.append(f"Journal: {self.journal_var.get()}")
                
            if self.subspecialty_var.get().lower() != "all":
                content_filters.append(f"Subspecialty: {self.subspecialty_var.get()}")
                
            filter_text = f" | Date: {date_filter}"
            if content_filters:
                filter_text += f" | {', '.join(content_filters)}"
                
            self.status_var.set(f"Found {len(self.articles)} articles{filter_text}")
        else:
            self.status_var.set("No articles found matching your criteria")

    def show_search_history(self):
        """Display the search history in a new window with improved visualization"""
        if not self.search_history:
            messagebox.showinfo("Search History", "No search history available")
            return
            
        # Create a new window
        history_window = tk.Toplevel(self.root)
        history_window.title("Search History")
        history_window.geometry("700x500")
        history_window.minsize(600, 400)
        
        # Create a frame for the history
        frame = ttk.Frame(history_window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Add a title
        ttk.Label(frame, text="Search History", font=("Helvetica", 14, "bold")).pack(pady=(0, 10))
        
        # Create a frame for the list and details
        main_frame = ttk.Frame(frame)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a PanedWindow for the list on the left and details on the right
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left frame for the history list
        list_frame = ttk.Frame(paned_window)
        paned_window.add(list_frame, weight=1)
        
        # Right frame for details
        details_frame = ttk.Frame(paned_window)
        paned_window.add(details_frame, weight=2)
        
        # Add scrollbar for list
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create listbox for history items
        history_list = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Helvetica", 10), height=15)
        history_list.pack(fill=tk.BOTH, expand=True, pady=5)
        scrollbar.config(command=history_list.yview)
        
        # Create text widget for details
        details_text = tk.Text(details_frame, wrap=tk.WORD, width=50, height=20)
        details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        details_text.config(state=tk.DISABLED)
        
        # Configure tags for formatting
        details_text.tag_configure("heading", font=("Helvetica", 12, "bold"))
        details_text.tag_configure("subheading", font=("Helvetica", 11, "bold"))
        details_text.tag_configure("normal", font=("Helvetica", 10))
        details_text.tag_configure("value", font=("Helvetica", 10, "bold"), foreground="blue")
        
        # Add history items
        reversed_history = list(reversed(self.search_history))
        for i, item in enumerate(reversed_history, 1):
            # Format the history item
            timestamp = item['timestamp']
            summary = item['summary'].replace('Fetching ', '')
            list_text = f"{i}. [{timestamp}] {summary}"
            history_list.insert(tk.END, list_text)
        
        # Function to show details when an item is selected
        def show_details(event):
            selection = history_list.curselection()
            if not selection:
                return
                
            # Get the selected history item (considering the reversed order)
            selected_idx = selection[0]
            selected_item = reversed_history[selected_idx]
            
            # Clear and enable text widget
            details_text.config(state=tk.NORMAL)
            details_text.delete(1.0, tk.END)
            
            # Add search summary
            details_text.insert(tk.END, "Search Summary\n", "heading")
            details_text.insert(tk.END, f"{selected_item['summary']}\n\n", "normal")
            
            # Add timestamp
            details_text.insert(tk.END, f"Time: {selected_item['timestamp']}\n\n", "normal")
            
            # Add settings details
            details_text.insert(tk.END, "Search Settings\n", "heading")
            settings = selected_item['settings']
            
            # Date settings
            details_text.insert(tk.END, "\nDate Settings:\n", "subheading")
            details_text.insert(tk.END, f"Date Filter: ", "normal")
            details_text.insert(tk.END, f"{settings['date_filter']}\n", "value")
            
            if settings['date_filter'] == "Past Days":
                details_text.insert(tk.END, f"Days Back: ", "normal")
                details_text.insert(tk.END, f"{settings['days_back']}\n", "value")
            
            # Content filters
            details_text.insert(tk.END, "\nContent Filters:\n", "subheading")
            details_text.insert(tk.END, f"Keyword: ", "normal")
            details_text.insert(tk.END, f"{settings['keyword'] if settings['keyword'] else 'None'}\n", "value")
            
            details_text.insert(tk.END, f"Journal: ", "normal")
            details_text.insert(tk.END, f"{settings['journal'] if settings['journal'] else 'All Journals'}\n", "value")
            
            details_text.insert(tk.END, f"Subspecialty: ", "normal")
            details_text.insert(tk.END, f"{settings['subspecialty']}\n", "value")
            
            # Results settings
            details_text.insert(tk.END, "\nResults Settings:\n", "subheading")
            details_text.insert(tk.END, f"Maximum Results: ", "normal")
            details_text.insert(tk.END, f"{settings['max_results']}\n", "value")
            
            # Results info if available
            if 'results_count' in selected_item:
                details_text.insert(tk.END, "\nResults:\n", "subheading")
                details_text.insert(tk.END, f"Articles Found: ", "normal")
                details_text.insert(tk.END, f"{selected_item['results_count']}\n", "value")
            
            # Make the text widget read-only again
            details_text.config(state=tk.DISABLED)
        
        # Bind selection event
        history_list.bind('<<ListboxSelect>>', show_details)
        
        # Add buttons frame
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # Add "Apply Selected Settings" button
        def apply_selected_settings():
            """Apply search settings from history and save them as current settings"""
            # Get the selected index
            selection = history_list.curselection()
            if not selection:
                messagebox.showinfo("Selection", "Please select a search history item")
                return
                
            # Get the selected history item
            selected_idx = selection[0]
            selected_settings = reversed_history[selected_idx]['settings']
            
            # Apply the settings
            if selected_settings["date_filter"] == "Today Only":
                self.today_only_var.set(True)
                self.month_only_var.set(False)
            elif selected_settings["date_filter"] == "This Month Only":
                self.month_only_var.set(True)
                self.today_only_var.set(False)
            else:
                self.today_only_var.set(False)
                self.month_only_var.set(False)
                self.days_back_var.set(selected_settings["days_back"])
                
            self.max_results_var.set(selected_settings["max_results"])
            self.subspecialty_var.set(selected_settings["subspecialty"])
            self.fetch_keyword_var.set(selected_settings["keyword"])
            self.journal_var.set(selected_settings["journal"])
            
            # Save current settings to ensure consistency
            self.current_search_settings = selected_settings.copy()
            
            # Update the filter indicators
            self.update_filter_indicators()
            
            # Save settings to persistent storage
            self.save_search_settings()
            
            # Close the window
            history_window.destroy()
            
            # Show confirmation with option to run search immediately
            response = messagebox.askyesno(
                "Settings Applied", 
                "Search settings have been applied. Would you like to run the search now?",
                icon="question"
            )
            
            # If user selects Yes, run the search
            if response:
                self.fetch_articles()
            
        ttk.Button(button_frame, text="Apply Selected Settings", command=apply_selected_settings).pack(side=tk.LEFT, padx=(0, 5))
        
        # Add "Apply & Search" button - directly applies settings and runs search
        def apply_and_search():
            # Apply settings first
            selection = history_list.curselection()
            if not selection:
                messagebox.showinfo("Selection", "Please select a search history item")
                return
                
            # Get the selected history item
            selected_idx = selection[0]
            selected_settings = reversed_history[selected_idx]['settings']
            
            # Apply the settings
            if selected_settings["date_filter"] == "Today Only":
                self.today_only_var.set(True)
                self.month_only_var.set(False)
            elif selected_settings["date_filter"] == "This Month Only":
                self.month_only_var.set(True)
                self.today_only_var.set(False)
            else:
                self.today_only_var.set(False)
                self.month_only_var.set(False)
                self.days_back_var.set(selected_settings["days_back"])
                
            self.max_results_var.set(selected_settings["max_results"])
            self.subspecialty_var.set(selected_settings["subspecialty"])
            self.fetch_keyword_var.set(selected_settings["keyword"])
            self.journal_var.set(selected_settings["journal"])
            
            # Save current settings to ensure consistency
            self.current_search_settings = selected_settings.copy()
            
            # Update the filter indicators
            self.update_filter_indicators()
            
            # Save settings to persistent storage 
            self.save_search_settings()
            
            # Close the window
            history_window.destroy()
            
            # Run the search immediately
            self.fetch_articles()
        
        ttk.Button(button_frame, text="Apply & Search", command=apply_and_search).pack(side=tk.LEFT, padx=5)
        
        # Add "Close" button
        ttk.Button(button_frame, text="Close", command=history_window.destroy).pack(side=tk.RIGHT)

    def display_current_search_settings(self):
        """Display the current search settings in a new window"""
        # Create a new window
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Current Search Settings")
        settings_window.geometry("600x500")
        
        # Create a frame
        frame = ttk.Frame(settings_window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Add a title
        ttk.Label(frame, text="Current Search Settings", font=("Helvetica", 14, "bold")).pack(pady=(0, 10))
        
        # Create a text widget to display settings
        settings_text = tk.Text(frame, height=18, width=60, wrap=tk.WORD)
        settings_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Configure tags for formatting
        settings_text.tag_configure("section", font=("Helvetica", 12, "bold"))
        settings_text.tag_configure("subsection", font=("Helvetica", 11, "bold"), foreground="#444444")
        settings_text.tag_configure("setting", font=("Helvetica", 10))
        settings_text.tag_configure("value", font=("Helvetica", 10, "bold"), foreground="blue")
        settings_text.tag_configure("note", font=("Helvetica", 9, "italic"), foreground="#666666")
        
        # Insert settings information
        settings_text.insert(tk.END, "Date Settings\n", "section")
        
        # Determine date filter type
        if self.today_only_var.get():
            date_filter = "Today Only"
            settings_text.insert(tk.END, "Date Filter: ", "setting")
            settings_text.insert(tk.END, f"{date_filter}\n", "value")
            settings_text.insert(tk.END, "• All results will be from today's date only\n", "note")
            
        elif self.month_only_var.get():
            date_filter = "This Month Only"
            settings_text.insert(tk.END, "Date Filter: ", "setting")
            settings_text.insert(tk.END, f"{date_filter}\n", "value")
            settings_text.insert(tk.END, "• Results limited to the current month\n", "note")
            
        elif self.specific_year_var.get():
            year = self.year_var.get()
            days = self.days_back_var.get()
            
            settings_text.insert(tk.END, "Year Filter: ", "setting")
            settings_text.insert(tk.END, f"Year {year}\n", "value")
            
            if days and int(days) > 0:
                settings_text.insert(tk.END, "Days Back: ", "setting")
                settings_text.insert(tk.END, f"{days}\n", "value")
                settings_text.insert(tk.END, f"• Results limited to the last {days} days of {year}\n", "note")
            else:
                settings_text.insert(tk.END, "• Results include the entire year {year}\n", "note")
                
        else:
            days = self.days_back_var.get()
            if days and int(days) > 0:
                date_filter = f"Past {days} Days"
                settings_text.insert(tk.END, "Date Filter: ", "setting")
                settings_text.insert(tk.END, f"{date_filter}\n", "value")
                settings_text.insert(tk.END, f"• Results from the last {days} days from today\n", "note")
            else:
                settings_text.insert(tk.END, "Date Filter: ", "setting")
                settings_text.insert(tk.END, "None (Default 30 days)\n", "value")
            
        settings_text.insert(tk.END, "\nContent Filters\n", "section")
        
        keyword = self.fetch_keyword_var.get().strip()
        settings_text.insert(tk.END, "Keyword: ", "setting")
        settings_text.insert(tk.END, f"{keyword if keyword else 'None'}\n", "value")
        
        journal = self.journal_var.get()
        settings_text.insert(tk.END, "Journal: ", "setting")
        settings_text.insert(tk.END, f"{journal if journal else 'All Journals'}\n", "value")
        
        subspecialty = self.subspecialty_var.get()
        settings_text.insert(tk.END, "Subspecialty: ", "setting")
        settings_text.insert(tk.END, f"{subspecialty}\n", "value")
        
        settings_text.insert(tk.END, "\nResults Settings\n", "section")
        settings_text.insert(tk.END, "Maximum Results: ", "setting")
        settings_text.insert(tk.END, f"{self.max_results_var.get()}\n", "value")
        
        # Add a description of how these settings affect the search
        settings_text.insert(tk.END, "\nSearch Behavior\n", "section")
        
        search_behavior = ""
        if self.today_only_var.get():
            search_behavior += "• Articles published today only\n"
            search_behavior += "• Uses expanded search with multiple retries to find articles\n"
        elif self.month_only_var.get():
            search_behavior += "• Articles published in the current month only\n"
            search_behavior += "• If early in the month, may also include previous month\n"
        elif self.specific_year_var.get():
            year = self.year_var.get()
            days = self.days_back_var.get()
            
            if days and int(days) > 0:
                search_behavior += f"• Articles published in the last {days} days of year {year}\n"
                search_behavior += "• First searches full year, then applies date filtering\n"
            else:
                search_behavior += f"• Articles published throughout the entire year {year}\n"
                search_behavior += "• Uses broader search to find all articles from this year\n"
        else:
            days = self.days_back_var.get() or "30"
            search_behavior += f"• Articles published in the past {days} days\n"
            
        if self.fetch_keyword_var.get().strip():
            search_behavior += f"• Results must contain keyword: '{self.fetch_keyword_var.get().strip()}'\n"
            
        if self.journal_var.get():
            search_behavior += f"• Results limited to journal: '{self.journal_var.get()}'\n"
            
        if self.subspecialty_var.get().lower() != "all":
            search_behavior += f"• Results filtered for subspecialty: '{self.subspecialty_var.get()}'\n"
            
        search_behavior += f"• Maximum of {self.max_results_var.get()} articles will be returned\n"
        
        settings_text.insert(tk.END, search_behavior, "setting")
        
        # Add information about date settings integration
        settings_text.insert(tk.END, "\nDate Settings Integration\n", "subsection")
        integration_notes = (
            "• 'Days Back' can be used alone to search recent articles\n"
            "• 'Specific Year' can be used to search an entire year\n"
            "• Combining both limits search to last X days of selected year\n"
            "• Enter 0 days with 'Specific Year' to search the entire year\n"
        )
        settings_text.insert(tk.END, integration_notes, "note")
        
        # Make the text widget read-only
        settings_text.config(state=tk.DISABLED)
        
        # Add a scrollbar
        scrollbar = ttk.Scrollbar(frame, command=settings_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        settings_text.config(yscrollcommand=scrollbar.set)
        
        # Add close button
        ttk.Button(frame, text="Close", command=settings_window.destroy).pack(pady=10)

    def create_menu(self):
        """Create application menu"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Fetch Articles", command=self.fetch_articles)
        file_menu.add_separator()
        file_menu.add_command(label="Save Search Settings", command=self.save_search_settings)
        file_menu.add_command(label="Load Default Settings", command=self.reset_to_defaults)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)
        
        # Search menu
        search_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Search", menu=search_menu)
        search_menu.add_command(label="View Current Search Settings", command=self.display_current_search_settings)
        search_menu.add_command(label="Search History", command=self.show_search_history)
        search_menu.add_separator()
        search_menu.add_command(label="Search Articles by Keyword", command=self.search_keywords)
        search_menu.add_command(label="Find Related Articles", command=self.find_related_articles)
        search_menu.add_separator()
        search_menu.add_command(label="Save Search as Preset", command=self.save_search_preset)
        search_menu.add_command(label="Manage Search Presets", command=self.manage_search_presets)
        
        # Export menu
        export_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Export", menu=export_menu)
        export_menu.add_command(label="Export as CSV", command=lambda: self.export_current_results("csv"))
        export_menu.add_command(label="Export as Excel", command=lambda: self.export_current_results("excel"))
        export_menu.add_command(label="Export as Text", command=lambda: self.export_current_results("txt"))
        export_menu.add_command(label="Export DOI URLs", command=lambda: self.export_current_results("doi"))
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Check for Updates", command=self.check_for_updates_ui)
    
    def reset_to_defaults(self):
        """Reset search settings to default values"""
        # Confirm with user
        confirm = messagebox.askyesno("Reset Settings", 
                                      "Are you sure you want to reset all search settings to defaults?")
        if not confirm:
            return
            
        # Reset to defaults
        self.days_back_var.set("30")
        self.max_results_var.set("1000")
        self.subspecialty_var.set("all")
        self.today_only_var.set(False)
        self.month_only_var.set(False)
        self.specific_year_var.set(False)
        self.year_var.set(str(datetime.today().year))
        self.fetch_keyword_var.set("")
        self.journal_var.set("")
        self.export_format_var.set("csv")
        self.save_dir_var.set(os.path.expanduser("~/Desktop"))
        
        # Update UI
        self.update_filter_indicators()
        
        # Save the defaults
        self.save_search_settings()
        
        messagebox.showinfo("Reset Complete", "Search settings have been reset to defaults")
    
    def export_current_results(self, format_type):
        """Export currently displayed articles to the specified format"""
        if not self.current_displayed_articles:
            messagebox.showinfo("Export", "No articles to export. Please fetch or search for articles first.")
            return
        
        # Get save directory
        save_dir = self.save_dir_var.get()
        if not os.path.isdir(save_dir):
            save_dir = os.path.expanduser("~/Desktop")
        
        # Generate filename based on current search settings
        filename_parts = []
        if self.today_only_var.get():
            filename_parts.append("today")
        elif self.month_only_var.get():
            filename_parts.append("thismonth")
        else:
            filename_parts.append(f"past{self.days_back_var.get()}days")
            
        if self.fetch_keyword_var.get():
            filename_parts.append(self.fetch_keyword_var.get().replace(" ", "_"))
            
        if self.journal_var.get():
            journal_short = self.journal_var.get().split()[0]
            filename_parts.append(journal_short)
            
        if self.subspecialty_var.get().lower() != "all":
            filename_parts.append(self.subspecialty_var.get().lower())
        
        # Create a timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Build the filename
        if filename_parts:
            base_filename = f"ophthalmology_articles_{'-'.join(filename_parts)}_{timestamp}"
        else:
            base_filename = f"ophthalmology_articles_{timestamp}"
        
        try:
            if format_type == "csv":
                filename = os.path.join(save_dir, f"{base_filename}.csv")
                save_to_csv(self.current_displayed_articles, filename)
            elif format_type == "excel":
                filename = os.path.join(save_dir, f"{base_filename}.xlsx")
                save_to_excel(self.current_displayed_articles, filename)
            elif format_type == "txt":
                filename = os.path.join(save_dir, f"{base_filename}.txt")
                save_to_txt(self.current_displayed_articles, filename)
            elif format_type == "doi":
                filename = os.path.join(save_dir, f"{base_filename}_doi_urls.csv")
                save_doi_urls(self.current_displayed_articles, filename)
            
            # Show success message with option to open the directory
            result = messagebox.askyesno("Export Complete", 
                                        f"Articles exported to {filename}.\n\nWould you like to open the containing folder?")
            if result:
                if sys.platform == 'darwin':  # macOS
                    subprocess.call(['open', save_dir])
                elif sys.platform == 'win32':  # Windows
                    os.startfile(save_dir)
                else:  # Linux
                    subprocess.call(['xdg-open', save_dir])
        
        except Exception as e:
            messagebox.showerror("Export Error", f"Error exporting articles: {str(e)}")
            logger.error(f"Export error: {str(e)}")

    def load_search_settings(self):
        """Load saved search settings from config file"""
        try:
            # Initialize search presets
            self.load_all_presets()
            
            # Load last search settings
            config_dir = os.path.join(os.path.expanduser("~"), ".ophthopapers")
            settings_file = os.path.join(config_dir, "search_settings.json")
            
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                
                # Apply loaded settings
                if settings.get("date_filter") == "Today Only":
                    self.today_only_var.set(True)
                    self.month_only_var.set(False)
                    self.specific_year_var.set(False)
                elif settings.get("date_filter") == "This Month Only":
                    self.today_only_var.set(False)
                    self.month_only_var.set(True)
                    self.specific_year_var.set(False)
                elif settings.get("date_filter", "").startswith("Year "):
                    self.today_only_var.set(False)
                    self.month_only_var.set(False)
                    self.specific_year_var.set(True)
                    # Extract year from "Year YYYY" format
                    year_str = settings.get("date_filter").replace("Year ", "")
                    try:
                        year = int(year_str)
                        if 1980 <= year <= 2025:
                            self.year_var.set(str(year))
                    except ValueError:
                        # Use current year if value is invalid
                        self.year_var.set(str(datetime.today().year))
                else:
                    self.today_only_var.set(False)
                    self.month_only_var.set(False)
                    self.specific_year_var.set(False)
                    self.days_back_var.set(settings.get("days_back", 30))
                
                self.max_results_var.set(settings.get("max_results", 1000))
                self.subspecialty_var.set(settings.get("subspecialty", ""))
                self.fetch_keyword_var.set(settings.get("keyword", ""))
                self.journal_var.set(settings.get("journal", ""))
                self.export_format_var.set(settings.get("export_format", "CSV"))
                self.save_dir_var.set(settings.get("save_dir", ""))
                
                # Apply export settings if available
                if 'export_format' in settings:
                    self.export_format_var.set(settings.get('export_format', 'csv'))
                if 'save_dir' in settings:
                    save_dir = settings.get('save_dir', os.path.expanduser("~/Desktop"))
                    if os.path.exists(save_dir):
                        self.save_dir_var.set(save_dir)
                
                # Update filter indicators
                self.update_filter_indicators()
                
                # Log the loaded preset name if applicable
                if settings.get('preset_name'):
                    preset_name = settings.get('preset_name')
                    self.status_var.set(f"Loaded search preset: {preset_name}")
                else:
                    self.status_var.set("Loaded last used search settings")
        except Exception as e:
            print(f"Error loading settings: {e}")
            # Use defaults if loading fails
            self.today_only_var.set(False)
            self.month_only_var.set(False)
            self.specific_year_var.set(False)
            self.days_back_var.set('30')
            self.max_results_var.set('1000')
            self.subspecialty_var.set('All')
    
    def save_search_settings(self):
        """Save current search settings for future use"""
        try:
            # Create settings directory if it doesn't exist
            config_dir = os.path.join(os.path.expanduser("~"), ".ophthopapers")
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            # Determine date filter
            if self.today_only_var.get():
                date_filter = "Today Only"
            elif self.month_only_var.get():
                date_filter = "This Month Only"
            elif self.specific_year_var.get():
                date_filter = f"Year {self.year_var.get()}"
            else:
                date_filter = "Past Days"
            
            # Collect settings to save
            settings = {
                "date_filter": date_filter,
                "days_back": self.days_back_var.get(),
                "max_results": self.max_results_var.get(),
                "subspecialty": self.subspecialty_var.get(),
                "keyword": self.fetch_keyword_var.get(),
                "journal": self.journal_var.get(),
                "export_format": self.export_format_var.get(),
                "save_dir": self.save_dir_var.get(),
                "preset_name": self.current_search_settings.get("preset_name", "")
            }
            
            # Save to file
            settings_file = os.path.join(config_dir, "search_settings.json")
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
                
            self.status_var.set("Search settings saved")
        except Exception as e:
            print(f"Error saving settings: {e}")
            self.status_var.set("Error saving settings")
    
    def show_about(self):
        """Show about dialog with version information"""
        about_message = f"Ophthalmology Papers Fetcher\nVersion {__version__}\n\n© Designed by Dr. Mahmoud Sami"
        messagebox.showinfo("About", about_message)
    
    def check_for_updates_ui(self):
        """Check for updates with UI feedback"""
        self.status_var.set("Checking for updates...")
        self.root.update_idletasks()
        
        update_info = check_for_updates()  # Call the global function
        
        if update_info:
            response = messagebox.askyesno(
                "Update Available", 
                f"A new version ({update_info['version']}) is available!\n\n" +
                f"You are currently running version {__version__}.\n\n" +
                "Would you like to update now?"
            )
            
            if response:
                self.status_var.set("Downloading update...")
                self.root.update_idletasks()
                
                if update_script(update_info):  # Call the global function
                    restart = messagebox.askyesno(
                        "Update Complete", 
                        "Update successful! You need to restart the application to use the new version.\n\n" +
                        "Would you like to restart now?"
                    )
                    
                    if restart:
                        # Restart the application
                        python = sys.executable
                        os.execl(python, python, *sys.argv)
                else:
                    messagebox.showerror(
                        "Update Failed", 
                        "Unable to update the application. Please try again later or download the update manually."
                    )
        else:
            messagebox.showinfo(
                "No Updates", 
                f"You are running the latest version ({__version__})."
            )
        
        self.status_var.set("Ready")
        self.root.update_idletasks()

    def load_all_presets(self):
        """Load all presets from file"""
        try:
            config_dir = os.path.join(os.path.expanduser("~"), ".ophthopapers")
            presets_file = os.path.join(config_dir, "search_presets.json")
            
            if os.path.exists(presets_file):
                with open(presets_file, 'r') as f:
                    self.search_presets = json.load(f)
            else:
                self.search_presets = []
        except Exception as e:
            print(f"Error loading presets: {e}")
            self.search_presets = []
    
    def save_all_presets(self):
        """Save all presets to file"""
        try:
            config_dir = os.path.join(os.path.expanduser("~"), ".ophthopapers")
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
                
            presets_file = os.path.join(config_dir, "search_presets.json")
            with open(presets_file, 'w') as f:
                json.dump(self.search_presets, f, indent=2)
        except Exception as e:
            print(f"Error saving presets: {e}")
    
    def save_search_preset(self):
        """Save current search settings as a named preset"""
        if not self.articles:
            messagebox.showinfo("Info", "Please fetch articles first before saving a preset.")
            return
            
        # Create a dialog to get the preset name
        preset_name = simpledialog.askstring("Save Search Preset", "Enter a name for this preset:")
        if not preset_name:
            return
            
        # Get current search settings
        if self.today_only_var.get():
            date_filter = "Today Only"
        elif self.month_only_var.get():
            date_filter = "This Month Only"
        elif self.specific_year_var.get():
            date_filter = f"Year {self.year_var.get()}"
        else:
            date_filter = "Past Days"
            
        settings = {
            "name": preset_name,
            "date_filter": date_filter,
            "days_back": self.days_back_var.get(),
            "max_results": self.max_results_var.get(),
            "subspecialty": self.subspecialty_var.get(),
            "keyword": self.fetch_keyword_var.get(),
            "journal": self.journal_var.get(),
            "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "results_count": len(self.articles)
        }
        
        # Check if the name already exists
        for i, preset in enumerate(self.search_presets):
            if preset["name"] == preset_name:
                overwrite = messagebox.askyesno("Confirm", 
                                               f"A preset named '{preset_name}' already exists. Overwrite?")
                if overwrite:
                    self.search_presets[i] = settings
                    self.save_all_presets()
                    messagebox.showinfo("Success", f"Search preset '{preset_name}' has been updated.")
                return
        
        # Add new preset
        self.search_presets.append(settings)
        self.save_all_presets()
        messagebox.showinfo("Success", f"Search preset '{preset_name}' has been saved.")
    
    def manage_search_presets(self):
        """Show a window to manage saved search presets"""
        # Load presets if they exist
        self.load_all_presets()
        
        if not self.search_presets:
            messagebox.showinfo("No Presets", "You don't have any saved search presets.")
            return
            
        # Create a window to display and manage presets
        preset_window = tk.Toplevel(self.root)
        preset_window.title("Manage Search Presets")
        preset_window.geometry("700x500")
        preset_window.transient(self.root)
        
        # Add a title
        ttk.Label(preset_window, text="Saved Search Presets", 
                 font=("Helvetica", 14, "bold")).pack(pady=(10, 5))
        
        # Create main frame
        main_frame = ttk.Frame(preset_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create a paned window for list and details
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Left frame for list
        list_frame = ttk.Frame(paned)
        paned.add(list_frame, weight=1)
        
        # Right frame for details
        details_frame = ttk.Frame(paned)
        paned.add(details_frame, weight=2)
        
        # Create listbox for presets
        ttk.Label(list_frame, text="Saved Presets").pack(pady=(0, 5))
        listbox_frame = ttk.Frame(list_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        
        preset_listbox = tk.Listbox(listbox_frame, exportselection=0)
        preset_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=preset_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        preset_listbox.config(yscrollcommand=scrollbar.set)
        
        # Populate listbox
        for preset in self.search_presets:
            preset_listbox.insert(tk.END, preset["name"])
        
        # Create text widget for details
        ttk.Label(details_frame, text="Preset Details").pack(pady=(0, 5))
        details_text = tk.Text(details_frame, wrap=tk.WORD, height=15)
        details_text.pack(fill=tk.BOTH, expand=True)
        details_text.config(state=tk.DISABLED)
        
        # Configure tags
        details_text.tag_configure("heading", font=("Helvetica", 12, "bold"))
        details_text.tag_configure("normal", font=("Helvetica", 10))
        details_text.tag_configure("value", foreground="blue", font=("Helvetica", 10, "bold"))
        
        # Function to show preset details
        def show_preset_details(event):
            selected = preset_listbox.curselection()
            if not selected:
                return
                
            idx = selected[0]
            preset = self.search_presets[idx]
            
            details_text.config(state=tk.NORMAL)
            details_text.delete(1.0, tk.END)
            
            details_text.insert(tk.END, f"{preset['name']}\n", "heading")
            details_text.insert(tk.END, f"Created: {preset['created_date']}\n\n", "normal")
            
            details_text.insert(tk.END, "Search Settings\n", "heading")
            details_text.insert(tk.END, "Date Filter: ", "normal")
            details_text.insert(tk.END, f"{preset['date_filter']}\n", "value")
            
            if preset['date_filter'] == "Past Days":
                details_text.insert(tk.END, "Days Back: ", "normal")
                details_text.insert(tk.END, f"{preset['days_back']}\n", "value")
                
            details_text.insert(tk.END, "Maximum Results: ", "normal")
            details_text.insert(tk.END, f"{preset['max_results']}\n", "value")
            
            details_text.insert(tk.END, "Subspecialty: ", "normal")
            details_text.insert(tk.END, f"{preset['subspecialty']}\n", "value")
            
            if preset['keyword']:
                details_text.insert(tk.END, "Keyword: ", "normal")
                details_text.insert(tk.END, f"{preset['keyword']}\n", "value")
                
            if preset['journal']:
                details_text.insert(tk.END, "Journal: ", "normal")
                details_text.insert(tk.END, f"{preset['journal']}\n", "value")
                
            if 'results_count' in preset:
                details_text.insert(tk.END, "\nLast Results Count: ", "normal")
                details_text.insert(tk.END, f"{preset['results_count']} articles\n", "value")
                
            details_text.config(state=tk.DISABLED)
        
        # Bind selection event
        preset_listbox.bind('<<ListboxSelect>>', show_preset_details)
        
        # Function to load a preset
        def load_preset():
            selected = preset_listbox.curselection()
            if not selected:
                messagebox.showinfo("Selection", "Please select a preset to load")
                return
                
            idx = selected[0]
            preset = self.search_presets[idx]
            
            # Apply the settings
            if preset["date_filter"] == "Today Only":
                self.today_only_var.set(True)
                self.month_only_var.set(False)
            elif preset["date_filter"] == "This Month Only":
                self.month_only_var.set(True)
                self.today_only_var.set(False)
            else:
                self.today_only_var.set(False)
                self.month_only_var.set(False)
                self.days_back_var.set(preset["days_back"])
                
            self.max_results_var.set(preset["max_results"])
            self.subspecialty_var.set(preset["subspecialty"])
            self.fetch_keyword_var.set(preset["keyword"])
            self.journal_var.set(preset["journal"])
            
            # Update filter indicators
            self.update_filter_indicators()
            
            # Create a complete settings object
            complete_settings = {
                "date_filter": preset["date_filter"],
                "days_back": preset["days_back"],
                "max_results": preset["max_results"],
                "subspecialty": preset["subspecialty"],
                "keyword": preset["keyword"],
                "journal": preset["journal"],
                "preset_name": preset["name"],
                "export_format": self.export_format_var.get(),
                "save_dir": self.save_dir_var.get()
            }
            
            # Save current settings with preset name
            self.current_search_settings = complete_settings
            
            # Save to persistent storage
            self.save_search_settings()
            
            # Close the window
            preset_window.destroy()
            
            # Ask if user wants to run the search
            response = messagebox.askyesno("Load Preset", 
                                           f"Preset '{preset['name']}' has been loaded. Run the search now?")
            if response:
                self.fetch_articles()
        
        # Function to delete a preset
        def delete_preset():
            selected = preset_listbox.curselection()
            if not selected:
                messagebox.showinfo("Selection", "Please select a preset to delete")
                return
                
            idx = selected[0]
            preset_name = self.search_presets[idx]["name"]
            
            confirm = messagebox.askyesno("Confirm Delete", 
                                          f"Are you sure you want to delete the preset '{preset_name}'?")
            if not confirm:
                return
                
            # Remove the preset
            del self.search_presets[idx]
            self.save_all_presets()
            
            # Update the listbox
            preset_listbox.delete(idx)
            details_text.config(state=tk.NORMAL)
            details_text.delete(1.0, tk.END)
            details_text.config(state=tk.DISABLED)
            
            messagebox.showinfo("Deleted", f"Preset '{preset_name}' has been deleted")
        
        # Add buttons
        button_frame = ttk.Frame(preset_window)
        button_frame.pack(pady=10, fill=tk.X)
        
        ttk.Button(button_frame, text="Load Preset", command=load_preset).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Delete Preset", command=delete_preset).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Close", command=preset_window.destroy).pack(side=tk.RIGHT, padx=10)

    def on_close(self):
        """Save settings and confirm before closing"""
        try:
            # Save current settings before closing
            self.save_search_settings()
            
            # Save any presets
            self.save_all_presets()
            
            # Close the application
            self.root.destroy()
        except Exception as e:
            # If there's an error saving, log it but still allow closing
            print(f"Error saving settings on exit: {e}")
            self.root.destroy()

    def clear_results(self):
        """Clear all displayed articles and reset the UI"""
        if not hasattr(self, 'articles') or not self.articles:
            messagebox.showinfo("Info", "No articles to clear")
            return
            
        # Confirm with user
        confirm = messagebox.askyesno("Confirm", "Are you sure you want to clear all displayed articles?")
        if not confirm:
            return
            
        # Clear articles list and reset UI
        self.articles = []
        self.current_displayed_articles = []
        self.results_text.delete(1.0, tk.END)
        self.hyperlinks = {}
        self.article_line_positions = []
        self.selected_article_idx = None
        
        # Update status
        self.status_var.set("Results cleared. Ready to fetch new articles.")

    def update_filter_indicators(self):
        """Update the visual indicators for active filters"""
        # Update date filter indicator
        date_filters = []
        if self.today_only_var.get():
            date_filters.append("Today Only")
            # Change the date frame style to indicate active filter
            self.date_frame.configure(text="Date Settings (ACTIVE: Today)")
        elif self.month_only_var.get():
            date_filters.append("This Month Only")
            # Change the date frame style to indicate active filter
            self.date_frame.configure(text="Date Settings (ACTIVE: Month)")
        elif self.specific_year_var.get():
            year = self.year_var.get()
            days = self.days_back_var.get()
            
            if days and int(days) > 0:
                date_filters.append(f"Year {year} (Last {days} days)")
                # Change the date frame style to indicate active filter with combined settings
                self.date_frame.configure(text=f"Date Settings (ACTIVE: Year {year} + Last {days} days)")
            else:
                date_filters.append(f"Year {year}")
                # Change the date frame style to indicate active filter
                self.date_frame.configure(text=f"Date Settings (ACTIVE: Year {year})")
        else:
            days = self.days_back_var.get()
            if days and int(days) > 0:
                date_filters.append(f"Past {days} Days")
                # Change the date frame style to indicate active filter
                self.date_frame.configure(text=f"Date Settings (ACTIVE: {days} Days)")
            else:
                self.date_frame.configure(text="Date Settings")
                
        # Create a more descriptive date filter indicator
        date_filter_text = ", ".join(date_filters) if date_filters else "No date filters active"
        self.date_filter_indicator.configure(text=f"Active: {date_filter_text}")
        
        # Update content filter indicator
        content_filters = []
        if self.fetch_keyword_var.get().strip():
            content_filters.append(f"Keyword: {self.fetch_keyword_var.get().strip()}")
            
        if self.journal_var.get():
            content_filters.append(f"Journal: {self.journal_var.get()}")
            
        if self.subspecialty_var.get() != "All":
            content_filters.append(f"Subspecialty: {self.subspecialty_var.get()}")
            
        if content_filters:
            self.content_frame.configure(text="Content Filters (ACTIVE)")
            content_filter_text = ", ".join(content_filters)
            self.content_filter_indicator.configure(text=f"Active: {content_filter_text}")
        else:
            self.content_frame.configure(text="Content Filters")
            self.content_filter_indicator.configure(text="No content filters active")
            
        # Update appearance when both specific year and days back are active together
        if self.specific_year_var.get() and self.days_back_var.get() and int(self.days_back_var.get()) > 0:
            # Find integration label and add a colored border around it
            for child in self.date_frame.winfo_children():
                if isinstance(child, ttk.Label) and "Active:" in child.cget("text"):
                    child.configure(borderwidth=1, relief="solid")
                    break
        else:
            # Remove border when not active
            for child in self.date_frame.winfo_children():
                if isinstance(child, ttk.Label) and "can be combined" in child.cget("text"):
                    child.configure(borderwidth=0, relief="flat")
                    break

if __name__ == '__main__':
    def main():
        try:
            # Check for updates at startup
            update_info = check_for_updates()
            if update_info:
                # GUI update dialog
                update_dialog = tk.Tk()
                update_dialog.title("Update Available")
                update_dialog.geometry("400x200")
                update_dialog.resizable(False, False)
                
                frame = ttk.Frame(update_dialog, padding=20)
                frame.pack(fill=tk.BOTH, expand=True)
                
                ttk.Label(
                    frame, 
                    text=f"A new version ({update_info['version']}) is available!", 
                    font=("Helvetica", 12, "bold")
                ).pack(pady=(0, 10))
                
                ttk.Label(
                    frame, 
                    text=f"You are currently running version {__version__}.\nWould you like to update now?",
                    justify=tk.CENTER
                ).pack(pady=(0, 20))
                
                btn_frame = ttk.Frame(frame)
                btn_frame.pack(fill=tk.X, pady=10)
                
                def do_update():
                    result_label.config(text="Updating, please wait...")
                    update_dialog.update_idletasks()
                    if update_script(update_info):
                        result_label.config(text="Update successful! Restart the application to use the new version.")
                        restart_btn.pack(pady=10)
                    else:
                        result_label.config(text="Update failed. Please try again or download manually.")
                
                def restart_app():
                    update_dialog.destroy()
                    # Restart the app
                    python = sys.executable
                    os.execl(python, python, *sys.argv)
                
                ttk.Button(btn_frame, text="Update Now", command=do_update).pack(side=tk.LEFT, padx=10)
                ttk.Button(btn_frame, text="Skip", command=update_dialog.destroy).pack(side=tk.RIGHT, padx=10)
                
                result_label = ttk.Label(frame, text="")
                result_label.pack(pady=10)
                
                restart_btn = ttk.Button(frame, text="Restart Now", command=restart_app)
                
                # Center the dialog
                update_dialog.update_idletasks()
                width = update_dialog.winfo_width()
                height = update_dialog.winfo_height()
                x = (update_dialog.winfo_screenwidth() // 2) - (width // 2)
                y = (update_dialog.winfo_screenheight() // 2) - (height // 2)
                update_dialog.geometry(f"{width}x{height}+{x}+{y}")
                
                update_dialog.mainloop()
        except Exception as e:
            # Log the error but continue with the application
            logger.error(f"Error during update check: {str(e)}")
            print(f"Update check failed: {str(e)}")
        
        # Start the main application
        root = tk.Tk()
        app = OphthoPapersApp(root)
        app.create_menu()
        root.mainloop()
    
    # Call the main function
    main()
