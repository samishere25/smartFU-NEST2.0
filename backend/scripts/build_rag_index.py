"""
Enhanced FAISS Index Builder v2.0
==================================

IMPROVEMENTS:
1. BioBERT embedding model (medical-optimized)
2. Larger index (better retrieval)
3. Progress tracking
4. Auto-fallback to MiniLM if BioBERT unavailable

Usage:
    cd backend
    python scripts/build_rag_index.py
"""

import json
import pickle
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
KNOWLEDGE_DIR = BASE_DIR / "app" / "agents" / "knowledge_base"
KNOWLEDGE_PATH = KNOWLEDGE_DIR / "medical_knowledge.json"
INDEX_PATH = KNOWLEDGE_DIR / "faiss_index.bin"
METADATA_PATH = KNOWLEDGE_DIR / "metadata.pkl"
EMBEDDINGS_PATH = KNOWLEDGE_DIR / "embeddings.npy"


def build_index():
    print("=" * 60)
    print("BUILDING ENHANCED FAISS INDEX V2.0")
    print("=" * 60)
    
    # Load knowledge base
    print("\n[1/5] Loading knowledge base...")
    if not KNOWLEDGE_PATH.exists():
        print(f"❌ Knowledge base not found: {KNOWLEDGE_PATH}")
        print("   Run extract_knowledge_base.py first")
        return False
    
    with open(KNOWLEDGE_PATH, 'r') as f:
        kb = json.load(f)
    
    documents = kb['documents']
    print(f"   ✅ Loaded {len(documents)} documents")
    
    # Load BioBERT model (medical-optimized)
    print("\n[2/5] Loading embedding model...")
    try:
        from sentence_transformers import SentenceTransformer
        
        # Try BioBERT first
        try:
            model = SentenceTransformer('pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb')
            print("   ✅ BioBERT loaded (medical-optimized)")
            model_name = "BioBERT"
        except Exception as e:
            print(f"   ⚠️ BioBERT not available: {e}")
            print("   📥 Falling back to all-MiniLM-L6-v2")
            model = SentenceTransformer('all-MiniLM-L6-v2')
            model_name = "MiniLM-L6-v2"
            print("   ✅ MiniLM loaded (general-purpose)")
            
    except ImportError:
        print("❌ Install: pip install sentence-transformers")
        return False
    
    # Create embeddings
    print("\n[3/5] Creating embeddings...")
    texts = []
    metadata = []
    
    for doc in documents:
        # Enhanced text representation for better matching
        # Combine title + category + content
        text = f"{doc['title']}. Category: {doc['category']}. {doc['content']}"
        texts.append(text)
        
        metadata.append({
            'doc_id': doc['doc_id'],
            'source': doc['source'],
            'category': doc['category'],
            'title': doc['title'],
            'content': doc['content'],
            'seriousness': doc['seriousness'],
            'critical_fields': doc['critical_fields'],
            'regulatory_action': doc['regulatory_action'],
            'drug_name': doc.get('drug_name'),
            'generic_name': doc.get('generic_name'),
            'keywords': doc.get('keywords', [])
        })
    
    print(f"   📝 Embedding {len(texts)} documents with {model_name}...")
    embeddings = model.encode(
        texts, 
        show_progress_bar=True, 
        convert_to_numpy=True,
        batch_size=32  # Optimize batch size
    )
    print(f"   ✅ Created {len(embeddings)} embeddings (dim: {embeddings.shape[1]})")
    
    # Build FAISS index
    print("\n[4/5] Building FAISS index...")
    try:
        import faiss
    except ImportError:
        print("❌ Install: pip install faiss-cpu")
        return False
    
    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings)
    
    # Create index (IndexFlatIP for inner product = cosine similarity after normalization)
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    print(f"   ✅ Index created: {index.ntotal} vectors")
    print(f"   📊 Index type: Flat (exact search, cosine similarity)")
    
    # Save everything
    print("\n[5/5] Saving index and metadata...")
    faiss.write_index(index, str(INDEX_PATH))
    print(f"   ✅ {INDEX_PATH}")
    
    with open(METADATA_PATH, 'wb') as f:
        pickle.dump(metadata, f)
    print(f"   ✅ {METADATA_PATH}")
    
    np.save(EMBEDDINGS_PATH, embeddings)
    print(f"   ✅ {EMBEDDINGS_PATH}")
    
    # Summary
    print("\n" + "=" * 60)
    print("INDEX BUILD COMPLETE!")
    print("=" * 60)
    print(f"Model:      {model_name}")
    print(f"Dimension:  {dimension}")
    print(f"Vectors:    {index.ntotal}")
    print(f"Index Type: Flat (exact search)")
    print("\nNext step: Test with python -m app.agents.medical_reasoning_agent")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success = build_index()
    if not success:
        exit(1)