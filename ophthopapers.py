import csv
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime, timedelta
from Bio import Entrez
from Bio import Medline
from time import sleep  # Add for rate limiting
import threading
import webbrowser  # For opening hyperlinks
import pandas as pd  # For Excel export
import re  # For pattern matching in keyword search

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

def fetch_recent_ophthalmology_articles(email, api_key=None, days_back=30, max_results=1000, min_impact_factor=0.0, subspecialty=None, today_only=False, month_only=False, search_keyword=None, specific_journal=None):
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
    """
    # Set email and API key (required by NCBI)
    Entrez.email = email
    if api_key:
        Entrez.api_key = api_key

    # Calculate date range
    today = datetime.today()
    
    if today_only:
        # Set days_back to 0 to get only today's articles
        past_date = today
        date_str = today.strftime("%Y/%m/%d")
    elif month_only:
        # Set to first day of current month
        past_date = today.replace(day=1)
        date_str = past_date.strftime("%Y/%m/%d")
    else:
        past_date = today - timedelta(days=days_back)
        date_str = past_date.strftime("%Y/%m/%d")

    # Enhanced journal list with ISSNs and 2022/2023 Impact Factors
    # (Impact factors are approximate and for reference only)
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
        
        # General high-impact journals that publish ophthalmology research
        ('Nature', '0028-0836', 69.7),
        ('Science', '0036-8075', 56.9),
        ('NEJM', '0028-4793', 91.2),
        ('JAMA', '0098-7484', 157.3),
        ('Lancet', '0140-6736', 202.7),
        ('Nat Med', '1078-8956', 87.2),
        ('Cell', '0092-8674', 66.8),
        ('BMJ', '0959-8138', 39.8)
    ]

    # For month_only option, remove general journals and keep only ophthalmology-specific ones
    if month_only or today_only:
        # Define general journals to exclude
        general_journals = {'Nature', 'Science', 'NEJM', 'Lancet', 'Nat Med', 'Cell', 'JAMA'}
        journals = [j for j in journals if j[0] not in general_journals]

    # Filter by specific journal if requested
    if specific_journal:
        # Check if it's matching by name or ISSN
        if specific_journal.lower() == "jama ophthalmology" or specific_journal == "2168-6165":
            # Special case for JAMA Ophthalmology to avoid confusion with general JAMA
            journals = [j for j in journals if j[0] == "JAMA Ophthalmol" or j[1] == "2168-6165"]
            journal_query = ' OR '.join([f'"{issn}"[ISSN]' for _, issn, _ in journals])
        else:
            journals = [j for j in journals if specific_journal.lower() in j[0].lower() or specific_journal == j[1]]
            if not journals:
                # If no match in our list, still try to search for it directly in PubMed
                journal_query = f'"{specific_journal}"[Journal]'
            else:
                journal_query = ' OR '.join([f'"{issn}"[ISSN]' for _, issn, _ in journals])
    else:
        # Filter journals by impact factor if requested
        if min_impact_factor > 0:
            journals = [j for j in journals if j[2] >= min_impact_factor]
        # Use all journals in list
        journal_query = ' OR '.join([f'"{issn}"[ISSN]' for _, issn, _ in journals])

    # Improved exclusion terms with partial matches
    exclusion_terms = {'reply', 'erratum', 'error', 'correction', 'letter', 'comment', 'response', 'correspondence'}
    
    # Choose search start date based on filters
    search_date_range = ""
    if today_only:
        # For today's articles, use a broader search but filter more strictly in post-processing
        # Use current month to catch all articles that might be published today but have different date formats
        search_date_range = f"{today.strftime('%Y/%m')}[PDAT]"
    elif month_only:
        # For this month's articles, use the month/year format
        search_date_range = f"{today.strftime('%Y/%m')}[PDAT]"
    else:
        # Use date range for regular searches
        search_date_range = f"{date_str}[PDAT] : {today.strftime('%Y/%m/%d')}[PDAT]"
    
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
    if subspecialty and subspecialty in subspecialty_keywords:
        relevance_keywords = subspecialty_keywords[subspecialty]
    else:
        # Keywords to boost article relevance in ophthalmology
        relevance_keywords = [
            'retina', 'cornea', 'glaucoma', 'cataract', 'refractive', 'surgery', 
            'macular degeneration', 'diabetic retinopathy', 'inflammation', 'infection', 
            'keratoconus', 'keratitis', 'uveitis', 'amblyopia', 'strabismus', 
            'presbyopia', 'keratoplasty', 'intravitreal', 'myopia'
        ]
    
    # Add the search keyword to boost its priority if provided
    if search_keyword:
        specific_keyword_query = f'"{search_keyword}"[Title/Abstract]'
        # Add the keyword to our search to prioritize it in relevance calculation
        if search_keyword.lower() not in [k.lower() for k in relevance_keywords]:
            relevance_keywords.append(search_keyword)
    else:
        specific_keyword_query = None
    
    relevance_boost = ' OR '.join([f'"{kw}"[Title/Abstract]' for kw in relevance_keywords])
    
    # Construct the base query - always use our list of ophthalmology journals
    # Ensure we ONLY search in our predefined ophthalmology journals
    base_query = f'({journal_query}) AND ({search_date_range}) AND English[lang] AND ("Journal Article"[Publication Type])'
    
    # Add the keyword search if provided - with extra priority
    if specific_keyword_query:
        # When searching by keyword, make it a requirement but maintain journal restriction
        search_query = f'({specific_keyword_query}) AND ({base_query})'
    else:
        # Otherwise use our general relevance boosting terms
        search_query = f'{base_query} AND ({relevance_boost})'
    
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

        articles = []
        id_list = search_results.get('IdList', [])

        if id_list:
            # Add rate limiting
            sleep(0.3)  # NCBI recommends ≤3 requests/sec
            
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
                journal_name = record.get('JT', 'Unknown journal')
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
                    # More flexible today check: compare only year, month and day components
                    article_date = date_obj.date()
                    today_date = today.date()
                    
                    # First try exact date match
                    if article_date == today_date:
                        pass  # Keep the article
                    # Also check if the date string contains today's date in various formats
                    elif (f"{today.strftime('%Y-%m-%d')}" in date_str or 
                          f"{today.strftime('%Y/%m/%d')}" in date_str or
                          f"{today.day} {today.strftime('%b')} {today.year}" in date_str or
                          f"{today.strftime('%b')} {today.day}, {today.year}" in date_str):
                        pass  # Keep the article
                    else:
                        continue  # Skip this article
                
                # If month_only is True, check if the article was published this month
                if month_only:
                    # More flexible month check: only compare year and month components
                    if date_obj.year == today.year and date_obj.month == today.month:
                        pass  # Keep the article
                    # Also check if the date string contains this month in various formats
                    elif (f"{today.strftime('%Y-%m')}" in date_str or 
                          f"{today.strftime('%Y/%m')}" in date_str or
                          f"{today.strftime('%b')} {today.year}" in date_str):
                        pass  # Keep the article
                    else:
                        continue  # Skip this article

                article_data = {
                    'title': record.get('TI', 'No title available'),
                    'journal': journal_name,
                    'impact_factor': impact_factor,
                    'pub_date': date_str,
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
        print(f"Error fetching data: {str(e)}")
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
            if (len(phrase) > 6 and phrase not in keywords and 
                (not existing_keywords or phrase not in existing_keywords)):
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

class OphthoPapersApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ophthalmology Papers Fetcher - © Designed by Dr. Mahmoud Sami")
        self.root.geometry("850x650")
        self.root.minsize(750, 550)
        
        # Create a main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
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
        self.keyword_search_var = tk.StringVar()  # For searching existing results
        self.fetch_keyword_var = tk.StringVar()  # For fetching by keyword from PubMed
        self.journal_var = tk.StringVar(value="")  # For fetching by specific journal
        self.current_displayed_articles = []  # For tracking what's currently displayed
        self.selected_article_idx = None  # For tracking selected article
        self.search_history = []  # For tracking search history
        
        # Add a search settings tracker
        self.current_search_settings = {
            "date_filter": "None",
            "days_back": "30",
            "max_results": "1000",
            "subspecialty": "All",
            "keyword": "",
            "journal": ""
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
        
        ttk.Label(self.date_frame, text="Days Back:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        days_back_entry = ttk.Entry(self.date_frame, textvariable=self.days_back_var, width=8)
        days_back_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        create_tooltip(days_back_entry, "Number of days to look back for articles.\nUsed when neither 'Today's Articles' nor 'This Month's Articles' is selected.")
        
        # Today's articles checkbox with improved tooltip
        today_check = ttk.Checkbutton(self.date_frame, text="Today's Articles Only", variable=self.today_only_var, 
                                      command=self.toggle_days_back)
        today_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        create_tooltip(today_check, "When checked, fetches only articles published today.\nOverrides 'Days Back' setting.\nUses an expanded search to maximize results.")
        
        # Month's articles checkbox with improved tooltip
        month_check = ttk.Checkbutton(self.date_frame, text="This Month's Articles Only", variable=self.month_only_var, 
                                      command=self.toggle_month_back)
        month_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        create_tooltip(month_check, "When checked, fetches only articles published in the current month.\nOverrides 'Days Back' setting.\nUses an expanded search to maximize results.")
        
        # Max results - LEFT frame
        max_results_frame = ttk.LabelFrame(left_frame, text="Results Settings")
        max_results_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(max_results_frame, text="Max Results:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        max_results_entry = ttk.Entry(max_results_frame, textvariable=self.max_results_var, width=10)
        max_results_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        create_tooltip(max_results_entry, "Maximum number of articles to retrieve.\nDefault is 1000.\nFor time-based filters (Today/Month), the system will\ntry multiple approaches to get close to this number.")
        
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
            # Healio journals
            ('Journal of Pediatric Ophthalmology and Strabismus', '0191-3913'),
            ('Ocular Surgery News', '8750-3085'),
            ('Primary Care Optometry News', '1081-6437'),
            ('Ocular Surgery News Europe/Asia-Pacific Edition', '1085-5629'),
            ('Ophthalmic Technology Assessment', '0162-0436'),
            ('International Journal of Eye Banking', '2193-4037'),
            ('Ophthalmic ASC', '2578-9740'),
        ]])
        journal_combobox = ttk.Combobox(self.content_frame, textvariable=self.journal_var, width=25, values=journal_names)
        journal_combobox.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        create_tooltip(journal_combobox, "Select a specific journal to filter articles.\nLeave empty to search across all ophthalmology journals.\nJournals are sorted alphabetically.")
        
        # Clear journal button
        clear_journal_btn = ttk.Button(self.content_frame, text="×", width=2, 
                                     command=lambda: self.journal_var.set(""))
        clear_journal_btn.grid(row=1, column=2, padx=(0, 5))
        create_tooltip(clear_journal_btn, "Clear journal selection")
        
        # Subspecialty selection with improved tooltip
        ttk.Label(self.content_frame, text="Subspecialty:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        subspecialty_combobox = ttk.Combobox(self.content_frame, textvariable=self.subspecialty_var, width=25)
        subspecialty_combobox['values'] = ('All', 'Cataract', 'Refractive', 'Glaucoma', 'Retina', 'Oculoplasty', 'Uveitis', 'Pediatrics')
        subspecialty_combobox.current(0)
        subspecialty_combobox.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        create_tooltip(subspecialty_combobox, "Filter articles by ophthalmology subspecialty.\n'All' retrieves articles from all subspecialties.\nApplies additional keywords to the search specific to each subspecialty.")
        
        # Active filter indicators
        self.date_filter_indicator = ttk.Label(self.date_frame, text="", foreground="blue")
        self.date_filter_indicator.grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(5, 2))
        
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
        
        # Progress bar
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress = ttk.Progressbar(action_frame, orient=tk.HORIZONTAL, length=300, mode='determinate', variable=self.progress_var)
        self.progress.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready to fetch articles")
        status_label = ttk.Label(action_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT, padx=5)
        
        # Fetch button - make it larger and more prominent
        self.fetch_button = ttk.Button(action_frame, text="Fetch Articles", 
                                      command=self.fetch_articles, style='Fetch.TButton')
        self.fetch_button.pack(side=tk.RIGHT, padx=5, ipadx=10, ipady=5)
        
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
    
    def toggle_days_back(self):
        """Enable/disable days back entry based on today's articles checkbox"""
        if self.today_only_var.get():
            # If "Today's Articles Only" is checked, disable days back entry and uncheck month option
            self.days_back_var.set("0")
            self.month_only_var.set(False)
        else:
            # If unchecked, enable days back entry with default value (unless month is checked)
            if not self.month_only_var.get():
                self.days_back_var.set("30")
                
        # Update the filter indicators
        self.update_filter_indicators()
    
    def toggle_month_back(self):
        """Enable/disable days back entry based on month's articles checkbox"""
        if self.month_only_var.get():
            # If "This Month's Articles Only" is checked, disable days back entry and uncheck today option
            self.days_back_var.set("0")
            self.today_only_var.set(False)
        else:
            # If unchecked, enable days back entry with default value
            self.days_back_var.set("30")
            
        # Update the filter indicators
        self.update_filter_indicators()
        
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
        else:
            days = self.days_back_var.get()
            if days and int(days) > 0:
                date_filters.append(f"Past {days} Days")
                # Change the date frame style to indicate active filter
                self.date_frame.configure(text=f"Date Settings (ACTIVE: {days} Days)")
            else:
                self.date_frame.configure(text="Date Settings")
                
        self.date_filter_indicator.configure(text=", ".join(date_filters) if date_filters else "")
        
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
            self.content_filter_indicator.configure(text=", ".join(content_filters))
        else:
            self.content_frame.configure(text="Content Filters")
            self.content_filter_indicator.configure(text="")
            
    def handle_text_click(self, event):
        """Handle click events in text widget for hyperlinks and article selection"""
        index = self.results_text.index(f"@{event.x},{event.y}")
        
        # Check if it's a hyperlink click
        for tag in self.results_text.tag_names(index):
            if tag in self.hyperlinks:
                url = self.hyperlinks[tag]
                webbrowser.open_new_tab(url)
                return
        
        # Check if it's an article title click (for selection)
        line = int(index.split('.')[0])
        for i, start_line in enumerate(self.article_line_positions):
            if line >= start_line and line < start_line + 4:  # Approximate article header size
                self.selected_article_idx = i
                self.highlight_selected_article()
                return
    
    def highlight_selected_article(self):
        """Highlight the currently selected article"""
        if self.selected_article_idx is None or not self.article_line_positions:
            return
        
        # Clear previous highlighting
        self.results_text.tag_remove("selected", "1.0", tk.END)
        
        # Add highlighting to selected article
        start_line = self.article_line_positions[self.selected_article_idx]
        
        # Find end of the article (next article start or end of text)
        if self.selected_article_idx < len(self.article_line_positions) - 1:
            end_line = self.article_line_positions[self.selected_article_idx + 1]
        else:
            end_line = int(self.results_text.index(tk.END).split('.')[0])
        
        # Apply selected tag
        self.results_text.tag_add("selected", f"{start_line}.0", f"{end_line}.0")
        self.results_text.tag_configure("selected", background="#f0f0ff")
        
        # Ensure visible
        self.results_text.see(f"{start_line}.0")
    
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
                
                self.results_text.insert(tk.END, article['doi'], link_tag)
                self.results_text.insert(tk.END, "\n")
            else:
                self.results_text.insert(tk.END, f"DOI: {article['doi']}\n")
            
            # Insert divider
            self.results_text.insert(tk.END, f"{'-' * 50}\n")
        
        if len(articles_to_display) > max_display:
            self.results_text.insert(tk.END, f"\n... and {len(articles_to_display) - max_display} more articles\n")
    
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
        related_window.geometry("800x600")
        
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
        def open_hyperlink(event):
            index = result_text.index(f"@{event.x},{event.y}")
            for tag in result_text.tag_names(index):
                if tag in result_hyperlinks:
                    url = result_hyperlinks[tag]
                    webbrowser.open_new_tab(url)
                    break
                    
        result_text.bind("<Button-1>", open_hyperlink)
    
    def browse_directory(self):
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
        """Fetch articles based on inputs"""
        if not self.validate_inputs():
            return
        
        # Update filter indicators before fetching
        self.update_filter_indicators()
        
        # Clear previous results
        self.results_text.delete(1.0, tk.END)
        self.hyperlinks = {}
        
        # Disable UI during fetch
        self.fetch_button.config(state=tk.DISABLED)
        self.status_var.set("Preparing to fetch articles...")
        self.progress_var.set(0)
        self.root.update_idletasks()
        
        # Gather all search parameters
        email = self.email_var.get()
        api_key = self.api_key_var.get()
        
        # Determine the date range strategy based on user selections
        if self.today_only_var.get():
            days_back = 0  # Today only
            date_strategy = "today"
            self.status_var.set("Fetching today's articles...")
            # Save current settings
            self.current_search_settings["date_filter"] = "Today Only"
            self.current_search_settings["days_back"] = "0"
        elif self.month_only_var.get():
            days_back = 30  # This month
            date_strategy = "month"
            self.status_var.set("Fetching this month's articles...")
            # Save current settings
            self.current_search_settings["date_filter"] = "This Month Only"
            self.current_search_settings["days_back"] = "30"
        else:
            days_back = int(self.days_back_var.get())
            date_strategy = f"past {days_back} days"
            self.status_var.set(f"Fetching articles from the past {days_back} days...")
            # Save current settings
            self.current_search_settings["date_filter"] = f"Past {days_back} Days"
            self.current_search_settings["days_back"] = str(days_back)
        
        # Content filtering parameters
        max_results = int(self.max_results_var.get())
        save_dir = self.save_dir_var.get()
        subspecialty = self.subspecialty_var.get().lower()
        export_format = self.export_format_var.get()
        fetch_keyword = self.fetch_keyword_var.get().strip() if self.fetch_keyword_var.get().strip() else None
        journal = self.journal_var.get() if self.journal_var.get() else None
        
        # Update current search settings
        self.current_search_settings["max_results"] = str(max_results)
        self.current_search_settings["subspecialty"] = self.subspecialty_var.get()
        self.current_search_settings["keyword"] = self.fetch_keyword_var.get().strip()
        self.current_search_settings["journal"] = self.journal_var.get()
        
        # Display search summary in status
        search_summary = []
        if date_strategy == "today":
            search_summary.append("Today's articles")
        elif date_strategy == "month":
            search_summary.append("This month's articles")
        else:
            search_summary.append(f"Articles from past {days_back} days")
            
        if subspecialty != "all":
            search_summary.append(f"in {subspecialty}")
            
        if journal:
            search_summary.append(f"from {journal}")
            
        if fetch_keyword:
            search_summary.append(f"matching '{fetch_keyword}'")
            
        search_summary.append(f"(max: {max_results})")
        
        # Update status with more informative message
        search_summary_text = "Fetching " + ", ".join(search_summary) + "..."
        self.status_var.set(search_summary_text)
        self.root.update_idletasks()
        
        # Add to search history
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.search_history.append({
            "timestamp": timestamp,
            "summary": search_summary_text,
            "settings": self.current_search_settings.copy()
        })
        
        # Create and start a thread for fetching
        fetch_thread = threading.Thread(
            target=self.fetch_thread,
            args=(email, api_key, days_back, max_results, save_dir, 
                  subspecialty if subspecialty != "all" else None, 
                  export_format, self.today_only_var.get(), self.month_only_var.get(),
                  fetch_keyword, journal)
        )
        fetch_thread.daemon = True
        fetch_thread.start()
    
    def fetch_thread(self, email, api_key, days_back, max_results, save_dir, subspecialty, export_format, today_only, month_only, fetch_keyword=None, journal=None):
        try:
            # Reset progress
            self.progress_var.set(10)
            self.root.update_idletasks()
            
            # Log search criteria for debugging/feedback
            search_params = {
                "Date filter": "Today only" if today_only else "This month only" if month_only else f"Past {days_back} days",
                "Maximum results": max_results,
                "Subspecialty": subspecialty if subspecialty else "All",
                "Journal": journal if journal else "All journals",
                "Keyword": fetch_keyword if fetch_keyword else "None",
                "Export format": export_format
            }
            
            search_msg = "Search parameters:\n" + "\n".join([f"• {k}: {v}" for k, v in search_params.items()])
            print(search_msg)  # For console debugging
            
            # Use a very high multiplier to ensure we get as many articles as possible
            adjusted_max_results = max_results
            if month_only or today_only:
                # When using month_only or today_only, request significantly more articles to ensure we get close to the requested amount
                adjusted_max_results = max_results * 20  # Significantly increased the multiplier
                self.status_var.set(f"Using expanded search to find {max_results} articles...")
            else:
                self.status_var.set(f"Searching for up to {max_results} articles...")
            self.root.update_idletasks()
            
            # Fetch articles with new parameters
            articles = fetch_recent_ophthalmology_articles(
                email=email,
                api_key=api_key,
                days_back=days_back,
                max_results=adjusted_max_results,
                min_impact_factor=0.0,  # No longer using impact factor filtering in UI
                subspecialty=subspecialty,
                today_only=today_only,
                month_only=month_only,
                search_keyword=fetch_keyword,
                specific_journal=journal
            )
            
            initial_count = len(articles)
            self.status_var.set(f"Initial search found {initial_count} articles. Processing...")
            self.root.update_idletasks()
            
            # Check if we got fewer articles than requested and try to fetch more if needed
            if (today_only or month_only) and len(articles) < max_results:
                # Try multiple passes with increasingly aggressive settings to get enough articles
                self.status_var.set(f"Found {len(articles)} articles, trying expanded search...")
                self.root.update_idletasks()
                
                # First try a more targeted approach with very large fetch size
                more_articles = fetch_recent_ophthalmology_articles(
                    email=email,
                    api_key=api_key,
                    days_back=days_back,
                    max_results=max_results * 100,  # Increased to 100x multiplier for better coverage
                    min_impact_factor=0.0,
                    subspecialty=subspecialty,
                    today_only=today_only,
                    month_only=month_only,
                    search_keyword=fetch_keyword,
                    specific_journal=journal
                )
                
                if len(more_articles) > len(articles):
                    articles = more_articles
                    self.status_var.set(f"Expanded search found {len(articles)} articles...")
                    self.root.update_idletasks()
                
                # If still not enough, try once more with an extreme multiplier and wider date range
                if len(articles) < max_results:
                    self.status_var.set(f"Using advanced techniques to find more articles...")
                    self.root.update_idletasks()
                    
                    # For today_only, try fetching from 3 days instead of just yesterday
                    extended_days_back = 3 if today_only else days_back
                    
                    # For month_only, if we're in the first week of the month, include previous month too
                    if month_only and datetime.today().day <= 7:
                        extended_days_back = 45  # Increased to cover more of previous month
                        self.status_var.set(f"It's early in the month - including articles from last month too...")
                    
                    final_articles = fetch_recent_ophthalmology_articles(
                        email=email,
                        api_key=api_key,
                        days_back=extended_days_back,
                        max_results=max_results * 200,  # Doubled to 200x multiplier for maximum coverage
                        min_impact_factor=0.0,
                        subspecialty=subspecialty,
                        today_only=False,  # Turn off day/month filter to get more results
                        month_only=False,
                        search_keyword=fetch_keyword,
                        specific_journal=journal
                    )
                    
                    # Manually filter the results to match the requested date range
                    today = datetime.today()
                    today_date = today.date()
                    this_month = (today.year, today.month)
                    
                    # Post-process to filter by date
                    filtered_final = []
                    for article in final_articles:
                        # Get the date from the article
                        pub_date = article.get('pub_date', '')
                        
                        # Try to parse the date
                        try:
                            date_parts = pub_date.split()
                            # Handle common PubMed date formats
                            if len(date_parts) >= 3:  # Format like "2023 Jan 15"
                                year = int(date_parts[0])
                                month_dict = {
                                    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                                    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                                }
                                month = month_dict.get(date_parts[1][:3], 1)
                                if today_only:
                                    # For today, check if it's today's date
                                    day = int(date_parts[2])
                                    article_date = date(year, month, day)
                                    if article_date == today_date:
                                        filtered_final.append(article)
                                elif month_only:
                                    # For month, check if it's this month
                                    if (year, month) == this_month:
                                        filtered_final.append(article)
                            elif len(date_parts) == 2:  # Format like "2023 Jan"
                                year = int(date_parts[0])
                                month_dict = {
                                    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                                    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                                }
                                month = month_dict.get(date_parts[1][:3], 1)
                                if month_only and (year, month) == this_month:
                                    filtered_final.append(article)
                        except (ValueError, IndexError):
                            # If date parsing fails, use other methods to check
                            if today_only and today.strftime('%Y-%m-%d') in pub_date:
                                filtered_final.append(article)
                            elif month_only and today.strftime('%Y-%m') in pub_date:
                                filtered_final.append(article)
                    
                    # If we found more articles with the manual filtering, use those
                    if len(filtered_final) > len(articles):
                        pre_filter_count = len(final_articles)
                        post_filter_count = len(filtered_final)
                        self.status_var.set(f"Found {post_filter_count} relevant articles from {pre_filter_count} total results")
                        articles = filtered_final
            
            # Only limit the results if we have more than requested
            if len(articles) > max_results:
                self.status_var.set(f"Found {len(articles)} articles, limiting to requested {max_results}")
                articles = articles[:max_results]
            
            self.articles = articles
            self.progress_var.set(50)
            self.root.update_idletasks()
            
            if not articles:
                message = "No articles found in the specified period"
                if today_only:
                    message = "No articles found published today. This may be because:\n" + \
                             "1. No articles were published today in the selected journals\n" + \
                             "2. The publication date in PubMed might not be updated yet\n\n" + \
                             "Try using 'This Month's Articles' for more recent publications."
                elif month_only:
                    message = "No articles found published this month. This may be because:\n" + \
                              "1. No articles were published this month in the selected journals\n" + \
                              "2. Try adjusting the impact factor or subspecialty filters"
                self.root.after(0, lambda: messagebox.showinfo("Results", message))
                self.root.after(0, self.enable_ui)
                return
            
            # Save files based on selected format
            saved_files = []
            
            if export_format == "csv" or export_format == "all":
                # Save regular CSV
                csv_path = os.path.join(save_dir, "ophthalmology_articles.csv")
                save_to_csv(articles, csv_path)
                saved_files.append(("CSV", csv_path))
            
            if export_format == "txt" or export_format == "all":
                # Save TXT
                txt_path = os.path.join(save_dir, "ophthalmology_articles.txt")
                saved_txt = save_to_txt(articles, txt_path)
                if saved_txt:
                    saved_files.append(("Text", txt_path))
            
            if export_format == "excel" or export_format == "all":
                # Save Excel with hyperlinks
                excel_path = os.path.join(save_dir, "ophthalmology_articles.xlsx")
                saved_excel = save_to_excel(articles, excel_path)
                if saved_excel:
                    saved_files.append(("Excel", excel_path))
            
            # Always save DOI URLs for quick access
            doi_path = os.path.join(save_dir, "doi_urls.csv")
            doi_file, doi_count = save_doi_urls(articles, doi_path)
            saved_files.append(("DOI URLs", doi_file))
            
            self.progress_var.set(100)
            
            # Clear previous display and setup for display
            self.results_text.delete(1.0, tk.END)
            self.hyperlinks = {}
            self.article_line_positions = []
            self.selected_article_idx = None
            
            # Display articles using the new display method
            self.display_articles(articles)
            
            # Show success message
            saved_text = "\n".join([f"{format_type}: {path}" for format_type, path in saved_files])
            self.root.after(0, lambda: messagebox.showinfo("Success", 
                f"Saved {len(articles)} articles to:\n\n{saved_text}"))
            
            self.status_var.set(f"Fetched {len(articles)} articles")
        
        except Exception as e:
            error_message = str(e)
            self.root.after(0, lambda error=error_message: messagebox.showerror("Error", f"An error occurred: {error}"))
            self.status_var.set("Error occurred")
        finally:
            self.root.after(0, self.enable_ui)
    
    def enable_ui(self):
        """Re-enable UI elements after fetch completes"""
        self.fetch_button.config(state=tk.NORMAL)
        self.progress_var.set(0)
        
        # Check if any articles were found
        if self.articles:
            # Update status with a summary of the results and active filters
            date_filter = "Today Only" if self.today_only_var.get() else "This Month Only" if self.month_only_var.get() else f"Past {self.days_back_var.get()} Days"
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
        """Display the search history in a new window"""
        if not self.search_history:
            messagebox.showinfo("Search History", "No search history available")
            return
            
        # Create a new window
        history_window = tk.Toplevel(self.root)
        history_window.title("Search History")
        history_window.geometry("600x400")
        history_window.minsize(500, 300)
        
        # Create a frame for the history
        frame = ttk.Frame(history_window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Add a title
        ttk.Label(frame, text="Search History", font=("Helvetica", 14, "bold")).pack(pady=(0, 10))
        
        # Create a frame for the list
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create listbox for history items
        history_list = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Helvetica", 10), height=15)
        history_list.pack(fill=tk.BOTH, expand=True, pady=5)
        scrollbar.config(command=history_list.yview)
        
        # Add history items
        for i, item in enumerate(reversed(self.search_history), 1):
            # Format the history item
            list_text = f"{i}. [{item['timestamp']}] {item['summary'].replace('Fetching ', '')}"
            history_list.insert(tk.END, list_text)
        
        # Add buttons frame
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # Add "Apply Selected Settings" button
        def apply_selected_settings():
            # Get the selected index
            selection = history_list.curselection()
            if not selection:
                messagebox.showinfo("Selection", "Please select a search history item")
                return
                
            # Get the selected history item (considering the reversed order)
            selected_idx = len(self.search_history) - 1 - selection[0]
            selected_settings = self.search_history[selected_idx]['settings']
            
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
            
            # Update the filter indicators
            self.update_filter_indicators()
            
            # Close the window
            history_window.destroy()
            
            # Show confirmation
            messagebox.showinfo("Settings Applied", "Search settings have been applied. Click 'Fetch Articles' to run the search.")
            
        ttk.Button(button_frame, text="Apply Selected Settings", command=apply_selected_settings).pack(side=tk.LEFT, padx=(0, 5))
        
        # Add "Close" button
        ttk.Button(button_frame, text="Close", command=history_window.destroy).pack(side=tk.RIGHT)

    def display_current_search_settings(self):
        """Display the current search settings in a new window"""
        # Create a new window
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Current Search Settings")
        settings_window.geometry("500x350")
        
        # Create a frame
        frame = ttk.Frame(settings_window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Add a title
        ttk.Label(frame, text="Current Search Settings", font=("Helvetica", 14, "bold")).pack(pady=(0, 10))
        
        # Create a text widget to display settings
        settings_text = tk.Text(frame, height=15, width=60, wrap=tk.WORD)
        settings_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Configure tags for formatting
        settings_text.tag_configure("section", font=("Helvetica", 12, "bold"))
        settings_text.tag_configure("setting", font=("Helvetica", 10))
        settings_text.tag_configure("value", font=("Helvetica", 10, "bold"), foreground="blue")
        
        # Insert settings information
        settings_text.insert(tk.END, "Date Settings\n", "section")
        date_filter = "None"
        if self.today_only_var.get():
            date_filter = "Today Only"
        elif self.month_only_var.get():
            date_filter = "This Month Only"
        else:
            days = self.days_back_var.get()
            if days and int(days) > 0:
                date_filter = f"Past {days} Days"
                
        settings_text.insert(tk.END, "Date Filter: ", "setting")
        settings_text.insert(tk.END, f"{date_filter}\n", "value")
        
        if not self.today_only_var.get() and not self.month_only_var.get():
            settings_text.insert(tk.END, "Days Back: ", "setting")
            settings_text.insert(tk.END, f"{self.days_back_var.get()}\n", "value")
            
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
        settings_text.insert(tk.END, "\nSearch Behavior:\n", "section")
        
        search_behavior = ""
        if self.today_only_var.get():
            search_behavior += "• Articles published today only\n"
            search_behavior += "• Uses expanded search with multiple retries to find articles\n"
        elif self.month_only_var.get():
            search_behavior += "• Articles published in the current month only\n"
            search_behavior += "• If early in the month, may also include previous month\n"
        else:
            search_behavior += f"• Articles published in the past {self.days_back_var.get()} days\n"
            
        if self.fetch_keyword_var.get().strip():
            search_behavior += f"• Results must contain keyword: '{self.fetch_keyword_var.get().strip()}'\n"
            
        if self.journal_var.get():
            search_behavior += f"• Results limited to journal: '{self.journal_var.get()}'\n"
            
        if self.subspecialty_var.get().lower() != "all":
            search_behavior += f"• Results filtered for subspecialty: '{self.subspecialty_var.get()}'\n"
            
        search_behavior += f"• Maximum of {self.max_results_var.get()} articles will be returned\n"
        
        settings_text.insert(tk.END, search_behavior, "setting")
        
        # Make the text widget read-only
        settings_text.config(state=tk.DISABLED)
        
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
        file_menu.add_command(label="Exit", command=self.root.destroy)
        
        # Search menu
        search_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Search", menu=search_menu)
        search_menu.add_command(label="View Current Search Settings", command=self.display_current_search_settings)
        search_menu.add_command(label="Search History", command=self.show_search_history)
        search_menu.add_separator()
        search_menu.add_command(label="Search Articles by Keyword", command=self.search_keywords)
        search_menu.add_command(label="Find Related Articles", command=self.find_related_articles)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Export Results", command=lambda: messagebox.showinfo("Info", "Use the export format settings to save articles when fetching"))
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=lambda: messagebox.showinfo("About", "Ophthalmology Papers Fetcher\n© Designed by Dr. Mahmoud Sami"))

if __name__ == '__main__':
    root = tk.Tk()
    app = OphthoPapersApp(root)
    app.create_menu()  # Add the menu
    root.mainloop()
