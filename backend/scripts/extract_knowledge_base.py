"""
Knowledge Base Extractor
- FDA XML files se adverse reactions extract karta hai
- MedDRA mapping use karta hai
- WHO guidelines se definitions add karta hai

Usage:
    cd backend
    python scripts/extract_knowledge_base.py
"""

import os
import json
import csv
import re
import xml.etree.ElementTree as ET
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
RAW_DATA_DIR = BASE_DIR / "app" / "agents" / "knowledge_base" / "raw_data"
OUTPUT_DIR = BASE_DIR / "app" / "agents" / "knowledge_base"

# WHO Seriousness Criteria (from PDF page 6)
WHO_SERIOUS_CRITERIA = {
    "FATAL": {
        "description": "Any event that results in death",
        "seriousness": "HIGH",
        "regulatory_timeline": "15 days expedited report",
        "keywords": ["death", "fatal", "died", "mortality"]
    },
    "LIFE_THREATENING": {
        "description": "Any event that places the patient at immediate risk of death",
        "seriousness": "HIGH",
        "regulatory_timeline": "15 days expedited report",
        "keywords": ["life-threatening", "cardiac arrest", "respiratory failure", "anaphylactic shock"]
    },
    "HOSPITALIZATION": {
        "description": "Any event that requires or prolongs hospitalization",
        "seriousness": "HIGH",
        "regulatory_timeline": "15 days expedited report",
        "keywords": ["hospitalization", "hospital", "admitted", "ICU"]
    },
    "DISABILITY": {
        "description": "Any event that results in persistent or significant disability/incapacity",
        "seriousness": "HIGH",
        "regulatory_timeline": "15 days expedited report",
        "keywords": ["disability", "incapacity", "permanent", "persistent"]
    },
    "CONGENITAL_ANOMALY": {
        "description": "Any event that causes a congenital anomaly/birth defect",
        "seriousness": "HIGH",
        "regulatory_timeline": "15 days expedited report",
        "keywords": ["congenital", "birth defect", "teratogenic", "fetal"]
    },
    "INTERVENTION_REQUIRED": {
        "description": "Any event requiring medical intervention to prevent permanent damage",
        "seriousness": "HIGH",
        "regulatory_timeline": "15 days expedited report",
        "keywords": ["intervention", "prevent damage", "emergency"]
    }
}

# MedDRA System Organ Class seriousness mapping
SOC_SERIOUSNESS = {
    "Cardiac disorders": "HIGH",
    "Hepatobiliary disorders": "HIGH",
    "Renal disorders": "HIGH",
    "Nervous system disorders": "MEDIUM",
    "Respiratory disorders": "MEDIUM",
    "Immune system disorders": "MEDIUM",
    "Blood disorders": "MEDIUM",
    "Neoplasms": "HIGH",
    "Psychiatric disorders": "MEDIUM",
    "Gastrointestinal disorders": "LOW",
    "Skin disorders": "LOW",
    "Musculoskeletal disorders": "LOW",
    "General disorders": "LOW",
    "Metabolic disorders": "LOW",
    "Ocular disorders": "LOW",
    "Product issues": "LOW"
}


def load_meddra_mapping():
    """Load MedDRA event to category mapping"""
    mapping = {}
    meddra_path = RAW_DATA_DIR / "meddra_mapping.csv"
    
    if meddra_path.exists():
        with open(meddra_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                event = row['event'].strip()
                category = row['category'].strip()
                mapping[event.lower()] = category
        print(f"✅ Loaded MedDRA mapping: {len(mapping)} terms")
    else:
        print(f"⚠️ MedDRA mapping not found at {meddra_path}")
    
    return mapping


def parse_fda_xml(xml_path):
    """Parse FDA drug label XML and extract adverse reactions"""
    print(f"\n📄 Parsing: {xml_path.name}")
    
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"   ❌ XML parse error: {e}")
        return None
    
    # Namespace
    ns = {'hl7': 'urn:hl7-org:v3'}
    
    # Get drug name
    drug_name = "Unknown"
    title_elem = root.find('.//hl7:title', ns)
    if title_elem is not None:
        # Extract drug name from title
        title_text = ''.join(title_elem.itertext())
        # Look for drug name pattern
        match = re.search(r'([A-Z][A-Za-z]+)(?:\s*®|\s*\()', title_text)
        if match:
            drug_name = match.group(1)
    
    # Get manufacturer
    manufacturer = "Unknown"
    mfr_elem = root.find('.//hl7:representedOrganization/hl7:n', ns)
    if mfr_elem is not None and mfr_elem.text:
        manufacturer = mfr_elem.text
    
    # Get generic name
    generic_name = drug_name.lower()
    generic_elem = root.find('.//hl7:genericMedicine/hl7:n', ns)
    if generic_elem is not None and generic_elem.text:
        generic_name = generic_elem.text.lower()
    
    # Find all sections
    sections = root.findall('.//hl7:section', ns)
    
    drug_info = {
        "drug_name": drug_name,
        "generic_name": generic_name,
        "manufacturer": manufacturer,
        "adverse_reactions": [],
        "warnings": [],
        "contraindications": [],
        "boxed_warning": None
    }
    
    for section in sections:
        code_elem = section.find('hl7:code', ns)
        if code_elem is None:
            continue
        
        section_code = code_elem.get('code', '')
        section_name = code_elem.get('displayName', '')
        
        # Get section text
        text_content = ' '.join(section.itertext())
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        # Boxed Warning
        if 'BOXED WARNING' in section_name.upper():
            drug_info["boxed_warning"] = text_content[:1000]
        
        # Adverse Reactions Section
        elif 'ADVERSE REACTIONS' in section_name.upper():
            # Extract reaction terms
            reactions = extract_adverse_reactions(text_content)
            drug_info["adverse_reactions"].extend(reactions)
        
        # Warnings Section
        elif 'WARNING' in section_name.upper() and 'BOXED' not in section_name.upper():
            drug_info["warnings"].append(text_content[:500])
        
        # Contraindications
        elif 'CONTRAINDICATION' in section_name.upper():
            drug_info["contraindications"].append(text_content[:500])
    
    print(f"   ✅ {drug_name}: {len(drug_info['adverse_reactions'])} reactions found")
    return drug_info


def extract_adverse_reactions(text):
    """Extract adverse reaction terms from text"""
    reactions = []
    
    # Common adverse reaction patterns
    patterns = [
        r'(?:diarrhea|nausea|vomiting|headache|fatigue|pain|rash|pruritus)',
        r'(?:abdominal\s+\w+|chest\s+\w+)',
        r'(?:\w+\s+increased|\w+\s+decreased)',
        r'(?:hypotension|hypertension|tachycardia|bradycardia)',
        r'(?:anaphylaxis|anaphylactic|hypersensitivity)',
        r'(?:hepatotoxicity|nephrotoxicity|cardiotoxicity)',
        r'(?:seizure|convulsion|tremor)',
        r'(?:infection|pneumonia|sepsis)',
        r'(?:hemorrhage|bleeding|haemorrhage)',
    ]
    
    text_lower = text.lower()
    
    # Find reactions
    found = set()
    for pattern in patterns:
        matches = re.findall(pattern, text_lower)
        found.update(matches)
    
    # Also look for common terms
    common_reactions = [
        'diarrhea', 'nausea', 'vomiting', 'headache', 'fatigue', 'pain',
        'abdominal pain', 'abdominal distension', 'flatulence', 'constipation',
        'dizziness', 'rash', 'pruritus', 'dyspnea', 'cough', 'fever',
        'dehydration', 'hypotension', 'hypertension', 'tachycardia',
        'anemia', 'neutropenia', 'thrombocytopenia', 'infection'
    ]
    
    for reaction in common_reactions:
        if reaction in text_lower:
            found.add(reaction)
    
    return list(found)


def classify_seriousness(event, meddra_mapping):
    """Classify event seriousness using WHO criteria and MedDRA"""
    event_lower = event.lower()
    
    # Check WHO serious criteria keywords
    for category, info in WHO_SERIOUS_CRITERIA.items():
        for keyword in info['keywords']:
            if keyword in event_lower:
                return {
                    "seriousness": info['seriousness'],
                    "category": category,
                    "regulatory": info['regulatory_timeline'],
                    "source": "WHO_CRITERIA"
                }
    
    # Check MedDRA mapping
    if event_lower in meddra_mapping:
        soc = meddra_mapping[event_lower]
        seriousness = SOC_SERIOUSNESS.get(soc, "MEDIUM")
        return {
            "seriousness": seriousness,
            "category": soc,
            "regulatory": "Standard reporting" if seriousness != "HIGH" else "Expedited reporting",
            "source": "MEDDRA"
        }
    
    # Default
    return {
        "seriousness": "MEDIUM",
        "category": "UNKNOWN",
        "regulatory": "Standard monitoring",
        "source": "DEFAULT"
    }


def get_critical_fields(seriousness, category):
    """Get critical follow-up fields based on seriousness"""
    base_fields = ["event_date", "patient_age", "drug_dose", "event_outcome"]
    
    if seriousness == "HIGH":
        base_fields.extend(["hospitalization_dates", "concomitant_meds", "medical_history"])
    
    category_fields = {
        "Cardiac disorders": ["ecg_results", "cardiac_biomarkers"],
        "Hepatobiliary disorders": ["liver_function_tests", "bilirubin"],
        "Renal disorders": ["creatinine", "gfr", "urine_output"],
        "Nervous system disorders": ["neurological_exam", "imaging"],
        "FATAL": ["cause_of_death", "autopsy_results"],
        "LIFE_THREATENING": ["intervention_required", "icu_admission"],
    }
    
    if category in category_fields:
        base_fields.extend(category_fields[category])
    
    return list(set(base_fields))[:10]


def build_knowledge_base():
    """Main function to build knowledge base"""
    print("=" * 60)
    print("BUILDING RAG KNOWLEDGE BASE")
    print("=" * 60)
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load MedDRA mapping
    meddra_mapping = load_meddra_mapping()
    
    # Parse all XML files
    print("\n[1/4] Parsing FDA Drug Labels...")
    drug_data = []
    
    if RAW_DATA_DIR.exists():
        xml_files = list(RAW_DATA_DIR.glob("*.xml"))
        print(f"   Found {len(xml_files)} XML files")
        
        for xml_path in xml_files:
            info = parse_fda_xml(xml_path)
            if info:
                drug_data.append(info)
    else:
        print(f"   ⚠️ Raw data directory not found: {RAW_DATA_DIR}")
        print(f"   Creating directory...")
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Build knowledge documents
    print("\n[2/4] Building knowledge documents...")
    documents = []
    doc_id = 0
    
    # Add WHO seriousness criteria documents
    for category, info in WHO_SERIOUS_CRITERIA.items():
        doc = {
            "doc_id": f"who_{doc_id:04d}",
            "source": "WHO_GUIDELINES",
            "category": category,
            "title": f"WHO Serious Adverse Event Criteria: {category.replace('_', ' ').title()}",
            "content": f"{info['description']}. Events in this category are classified as {info['seriousness']} seriousness and require {info['regulatory_timeline']}. Key indicators include: {', '.join(info['keywords'])}.",
            "seriousness": info['seriousness'],
            "critical_fields": get_critical_fields(info['seriousness'], category),
            "regulatory_action": info['regulatory_timeline'],
            "keywords": info['keywords']
        }
        documents.append(doc)
        doc_id += 1
    
    # Add drug-specific documents
    for drug in drug_data:
        # Boxed warning document
        if drug.get("boxed_warning"):
            doc = {
                "doc_id": f"fda_{doc_id:04d}",
                "source": "FDA_LABEL",
                "drug_name": drug["drug_name"],
                "generic_name": drug["generic_name"],
                "category": "BOXED_WARNING",
                "title": f"{drug['drug_name']} Boxed Warning",
                "content": drug["boxed_warning"][:800],
                "seriousness": "HIGH",
                "critical_fields": ["event_date", "patient_age", "drug_dose", "event_outcome"],
                "regulatory_action": "Expedited reporting required"
            }
            documents.append(doc)
            doc_id += 1
        
        # Adverse reaction documents
        for reaction in drug.get("adverse_reactions", []):
            classification = classify_seriousness(reaction, meddra_mapping)
            
            doc = {
                "doc_id": f"fda_{doc_id:04d}",
                "source": "FDA_LABEL",
                "drug_name": drug["drug_name"],
                "generic_name": drug["generic_name"],
                "category": classification["category"],
                "title": f"{reaction.title()} - {drug['drug_name']}",
                "content": f"{reaction.title()} is a known adverse reaction associated with {drug['drug_name']} ({drug['generic_name']}). This event is classified as {classification['seriousness']} seriousness under {classification['category']}. {classification['regulatory']}. Manufactured by {drug['manufacturer']}.",
                "seriousness": classification["seriousness"],
                "critical_fields": get_critical_fields(classification["seriousness"], classification["category"]),
                "regulatory_action": classification["regulatory"]
            }
            documents.append(doc)
            doc_id += 1
    
    # Add MedDRA category documents
    print("\n[3/4] Adding MedDRA category knowledge...")
    for event, category in meddra_mapping.items():
        seriousness = SOC_SERIOUSNESS.get(category, "MEDIUM")
        doc = {
            "doc_id": f"meddra_{doc_id:04d}",
            "source": "MEDDRA",
            "category": category,
            "title": f"{event.title()} - {category}",
            "content": f"{event.title()} is classified under MedDRA System Organ Class: {category}. This type of adverse event typically has {seriousness} seriousness level. Standard pharmacovigilance reporting guidelines apply.",
            "seriousness": seriousness,
            "critical_fields": get_critical_fields(seriousness, category),
            "regulatory_action": "Standard reporting" if seriousness != "HIGH" else "Expedited reporting"
        }
        documents.append(doc)
        doc_id += 1
    
    # Save knowledge base
    print("\n[4/4] Saving knowledge base...")
    
    knowledge_base = {
        "metadata": {
            "total_documents": len(documents),
            "sources": {
                "who_guidelines": len([d for d in documents if d["source"] == "WHO_GUIDELINES"]),
                "fda_labels": len([d for d in documents if d["source"] == "FDA_LABEL"]),
                "meddra": len([d for d in documents if d["source"] == "MEDDRA"])
            },
            "drugs_processed": [d["drug_name"] for d in drug_data],
            "seriousness_distribution": {
                "HIGH": len([d for d in documents if d["seriousness"] == "HIGH"]),
                "MEDIUM": len([d for d in documents if d["seriousness"] == "MEDIUM"]),
                "LOW": len([d for d in documents if d["seriousness"] == "LOW"])
            }
        },
        "documents": documents
    }
    
    output_path = OUTPUT_DIR / "medical_knowledge.json"
    with open(output_path, 'w') as f:
        json.dump(knowledge_base, f, indent=2)
    
    print(f"\n✅ Saved: {output_path}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("KNOWLEDGE BASE COMPLETE!")
    print("=" * 60)
    print(f"\nTotal documents: {len(documents)}")
    print(f"  - WHO Guidelines: {knowledge_base['metadata']['sources']['who_guidelines']}")
    print(f"  - FDA Labels: {knowledge_base['metadata']['sources']['fda_labels']}")
    print(f"  - MedDRA Terms: {knowledge_base['metadata']['sources']['meddra']}")
    print(f"\nSeriousness Distribution:")
    print(f"  - HIGH: {knowledge_base['metadata']['seriousness_distribution']['HIGH']}")
    print(f"  - MEDIUM: {knowledge_base['metadata']['seriousness_distribution']['MEDIUM']}")
    print(f"  - LOW: {knowledge_base['metadata']['seriousness_distribution']['LOW']}")
    print(f"\nNext step: Run build_rag_index.py")


if __name__ == "__main__":
    build_knowledge_base()