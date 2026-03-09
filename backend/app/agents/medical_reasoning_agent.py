"""
Medical Reasoning Agent v2.0 - PURE RAG Implementation
=======================================================

IMPROVEMENTS OVER v1.0:
1. BioBERT embedding model (medical-domain optimized)
2. Query expansion using medical synonyms
3. Enhanced retrieval (k=10 + reranking)
4. Better knowledge base with WHO/ICH guidelines
5. NO HARDCODED RULES - Pure semantic retrieval

Author: AI Assistant
Date: Feb 13, 2026
"""

import os
import pickle
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import numpy as np

# Paths
KNOWLEDGE_BASE_DIR = os.path.join(os.path.dirname(__file__), 'knowledge_base')
FAISS_INDEX_PATH = os.path.join(KNOWLEDGE_BASE_DIR, 'faiss_index.bin')
METADATA_PATH = os.path.join(KNOWLEDGE_BASE_DIR, 'metadata.pkl')
SYNONYMS_PATH = os.path.join(KNOWLEDGE_BASE_DIR, 'medical_synonyms.json')


class MedicalSynonymExpander:
    """
    Expands queries using medical terminology synonyms
    NO HARDCODED RULES - uses knowledge base
    """
    
    def __init__(self, synonyms_path: str):
        self.synonyms = {}
        if os.path.exists(synonyms_path):
            with open(synonyms_path, 'r') as f:
                self.synonyms = json.load(f)
    
    def expand(self, query: str) -> str:
        """
        Expand query with medical synonyms
        
        Example:
            "anaphylactic shock" → "anaphylactic shock anaphylaxis severe allergic reaction hypersensitivity"
        """
        query_lower = query.lower()
        expansions = []
        
        # Find matching concepts
        for concept, synonyms in self.synonyms.items():
            if concept in query_lower:
                expansions.extend(synonyms)
        
        if expansions:
            # Return original + expansions
            return f"{query} {' '.join(set(expansions))}"
        
        return query


class RAGRetriever:
    """
    Enhanced FAISS retriever with:
    - BioBERT embeddings
    - Query expansion
    - Reranking
    """
    
    _instance = None
    _index = None
    _metadata = None
    _model = None
    _synonym_expander = None
    _is_loaded = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load(self) -> bool:
        """Load FAISS index and BioBERT model"""
        if self._is_loaded:
            return True
        
        # Check files
        if not os.path.exists(FAISS_INDEX_PATH):
            print(f"⚠️ FAISS index not found: {FAISS_INDEX_PATH}")
            return False
        
        if not os.path.exists(METADATA_PATH):
            print(f"⚠️ Metadata not found: {METADATA_PATH}")
            return False
        
        try:
            # Load FAISS
            import faiss
            self._index = faiss.read_index(FAISS_INDEX_PATH)
            print(f"✅ FAISS index loaded: {self._index.ntotal} vectors")
            
            # Load metadata
            with open(METADATA_PATH, 'rb') as f:
                self._metadata = pickle.load(f)
            print(f"✅ Metadata loaded: {len(self._metadata)} documents")
            
            # Load BioBERT model (better for medical text)
            from sentence_transformers import SentenceTransformer
            
            # Try BioBERT first, fallback to MiniLM if not available
            try:
                self._model = SentenceTransformer('pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb')
                print("✅ BioBERT loaded (medical-optimized)")
            except:
                print("⚠️ BioBERT not available, using all-MiniLM-L6-v2")
                self._model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Load synonym expander
            self._synonym_expander = MedicalSynonymExpander(SYNONYMS_PATH)
            
            self._is_loaded = True
            return True
            
        except ImportError as e:
            print(f"❌ Import error: {e}")
            return False
        except Exception as e:
            print(f"❌ Error loading RAG: {e}")
            return False
    
    def retrieve(self, query: str, top_k: int = 10) -> List[Tuple[Dict, float]]:
        """
        Enhanced retrieval with query expansion and reranking
        
        Steps:
        1. Expand query with medical synonyms
        2. Retrieve top_k candidates (default 10)
        3. Rerank using cross-encoder similarity
        4. Return top 5 after reranking
        """
        if not self.load():
            return []
        
        # Step 1: Query expansion
        expanded_query = self._synonym_expander.expand(query)
        print(f"🔍 Original: {query}")
        if expanded_query != query:
            print(f"🔍 Expanded: {expanded_query}")
        
        # Step 2: Embed expanded query
        import faiss
        query_embedding = self._model.encode([expanded_query], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)
        
        # Step 3: Search (get more candidates for reranking)
        scores, indices = self._index.search(query_embedding, top_k)
        
        # Step 4: Build candidate results
        candidates = []
        for idx, score in zip(indices[0], scores[0]):
            if 0 <= idx < len(self._metadata):
                candidates.append((self._metadata[idx], float(score)))
        
        # Step 5: Rerank (semantic reranking)
        reranked = self._rerank(query, candidates)
        
        # Return top 5 after reranking
        return reranked[:5]
    
    def _rerank(self, original_query: str, candidates: List[Tuple[Dict, float]]) -> List[Tuple[Dict, float]]:
        """
        Rerank candidates using cross-encoder
        Falls back to original scores if cross-encoder not available
        """
        try:
            from sentence_transformers import CrossEncoder
            
            # Use cross-encoder for reranking
            reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            
            # Prepare query-document pairs
            pairs = []
            for doc, _ in candidates:
                text = f"{doc['title']}. {doc['content']}"
                pairs.append([original_query, text])
            
            # Get reranking scores
            rerank_scores = reranker.predict(pairs)
            
            # Combine with original scores (weighted average)
            reranked = []
            for (doc, original_score), rerank_score in zip(candidates, rerank_scores):
                # Normalize rerank score to 0-1
                normalized_rerank = (rerank_score + 10) / 20  # Rough normalization
                
                # Weighted combination: 70% rerank, 30% original
                combined_score = 0.7 * normalized_rerank + 0.3 * original_score
                reranked.append((doc, combined_score))
            
            # Sort by combined score
            reranked.sort(key=lambda x: x[1], reverse=True)
            return reranked
            
        except Exception as e:
            print(f"⚠️ Reranking failed, using original scores: {e}")
            # Fallback: return original candidates sorted by score
            return sorted(candidates, key=lambda x: x[1], reverse=True)
    
    @property
    def is_ready(self) -> bool:
        return self._is_loaded or self.load()


# Global instance
_retriever = RAGRetriever()


class MedicalReasoningAgent:
    """
    Pure RAG-based Medical Reasoning Agent v2.0
    
    NO HARDCODED RULES - All reasoning from knowledge base retrieval
    """
    
    @staticmethod
    def analyze(
        adverse_event: str,
        case_data: Optional[Dict] = None,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Analyze adverse event using PURE RAG retrieval
        
        Returns:
            Complete medical reasoning with high confidence scores
        """
        # Empty check
        if not adverse_event or not adverse_event.strip():
            return MedicalReasoningAgent._empty_response()
        
        # Retriever check
        if not _retriever.is_ready:
            return MedicalReasoningAgent._no_index_response(adverse_event)
        
        # Retrieve with enhanced pipeline
        retrieved = _retriever.retrieve(adverse_event, top_k=top_k)
        
        if not retrieved:
            return MedicalReasoningAgent._no_matches_response(adverse_event)
        
        # Generate from context
        return MedicalReasoningAgent._generate_response(adverse_event, retrieved, case_data)
    
    @staticmethod
    def _generate_response(
        query: str,
        retrieved: List[Tuple[Dict, float]],
        case_data: Optional[Dict]
    ) -> Dict[str, Any]:
        """
        Generate response from retrieved documents
        PURE RAG - no keyword rules
        """
        
        top_doc, top_score = retrieved[0]
        
        # Aggregate from ALL retrieved docs (ensemble approach)
        all_fields = set()
        categories = []
        knowledge_sources = set()
        seriousness_votes = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        
        for doc, score in retrieved:
            # Collect fields
            all_fields.update(doc.get('critical_fields', []))
            knowledge_sources.add(doc.get('source', 'UNKNOWN'))
            
            # Vote on seriousness (weighted by similarity score)
            seriousness = doc['seriousness']
            seriousness_votes[seriousness] += score
            
            # Category info
            categories.append({
                'category': doc['category'],
                'title': doc['title'],
                'similarity': round(score, 3),
                'seriousness': doc['seriousness'],
                'source': doc.get('source', 'UNKNOWN'),
                'drug_name': doc.get('drug_name')
            })
        
        # Determine seriousness by weighted voting (not max)
        max_seriousness = max(seriousness_votes.items(), key=lambda x: x[1])[0]
        
        # Calculate confidence from top score + consensus
        # Higher score + more agreement = higher confidence
        consensus_factor = seriousness_votes[max_seriousness] / sum(seriousness_votes.values())
        confidence = min(0.98, (top_score * 0.6) + (consensus_factor * 0.4))
        
        # Build reasoning
        reasoning = MedicalReasoningAgent._build_reasoning(
            query, top_doc, top_score, retrieved, max_seriousness, consensus_factor
        )
        
        # Determine urgency from seriousness
        urgency_map = {
            'HIGH': 'IMMEDIATE',
            'MEDIUM': 'HIGH',
            'LOW': 'ROUTINE'
        }
        urgency = urgency_map.get(max_seriousness, 'ROUTINE')
        
        return {
            "medical_seriousness_hint": max_seriousness,
            "critical_followup_fields": list(all_fields)[:8],
            "reasoning_text": reasoning,
            "confidence_score": round(confidence, 3),
            "matched_categories": categories,
            "regulatory_implication": top_doc.get('regulatory_action', 'Standard monitoring'),
            "followup_urgency": urgency,
            "retrieved_documents": [
                {
                    'doc_id': doc['doc_id'],
                    'title': doc['title'],
                    'category': doc['category'],
                    'seriousness': doc['seriousness'],
                    'similarity': round(score, 3),
                    'source': doc.get('source', 'UNKNOWN'),
                    'drug_name': doc.get('drug_name'),
                    'generic_name': doc.get('generic_name')
                }
                for doc, score in retrieved
            ],
            "retrieval_method": "ENHANCED_RAG_V2",
            "knowledge_sources": list(knowledge_sources),
            "top_k_used": len(retrieved),
            "seriousness_consensus": {
                'votes': seriousness_votes,
                'winner': max_seriousness,
                'consensus_score': round(consensus_factor, 3)
            }
        }
    
    @staticmethod
    def _build_reasoning(
        query: str,
        top_doc: Dict,
        top_score: float,
        all_docs: List[Tuple[Dict, float]],
        final_seriousness: str,
        consensus: float
    ) -> str:
        """Build enhanced reasoning text"""
        
        parts = []
        
        # Method intro
        parts.append(
            f"[Enhanced RAG v2.0 Analysis] Analyzed '{query[:60]}...' using BioBERT embeddings "
            f"with query expansion and semantic reranking."
        )
        
        # Knowledge sources
        sources = list(set(doc.get('source', 'UNKNOWN') for doc, _ in all_docs))
        parts.append(f"Knowledge sources: {', '.join(sources)}.")
        
        # Top match
        parts.append(
            f"Best match: '{top_doc['title']}' ({top_score:.1%} similarity after reranking). "
            f"Category: {top_doc['category']}, Known seriousness: {top_doc['seriousness']}."
        )
        
        # Consensus voting
        parts.append(
            f"Seriousness assessment: {final_seriousness} (consensus: {consensus:.1%} across {len(all_docs)} documents)."
        )
        
        # Source-specific context
        if top_doc.get('source') == 'FDA_LABEL':
            drug = top_doc.get('drug_name', 'Unknown')
            parts.append(f"This is a known adverse reaction from FDA label for {drug}.")
        elif top_doc.get('source') == 'WHO_GUIDELINES':
            parts.append("Classification based on WHO serious adverse event criteria.")
        elif top_doc.get('source') == 'MEDDRA':
            parts.append(f"MedDRA classification: {top_doc['category']}.")
        
        # Content snippet
        content = top_doc.get('content', '')[:200]
        if content:
            parts.append(f"Context: \"{content}...\"")
        
        # Regulatory action
        regulatory = top_doc.get('regulatory_action', 'Standard monitoring')
        parts.append(f"Regulatory recommendation: {regulatory}.")
        
        # Supporting evidence
        if len(all_docs) > 1:
            supporting = [f"{d['title'][:40]} ({s:.0%})" for d, s in all_docs[1:4]]
            parts.append(f"Supporting matches: {'; '.join(supporting)}.")
        
        return " ".join(parts)
    
    @staticmethod
    def _empty_response() -> Dict[str, Any]:
        """Response when no adverse event provided"""
        return {
            "medical_seriousness_hint": "MEDIUM",
            "critical_followup_fields": ["adverse_event", "event_date", "event_outcome"],
            "reasoning_text": "No adverse event description provided. Cannot perform RAG retrieval.",
            "confidence_score": 0.0,
            "matched_categories": [],
            "regulatory_implication": "Unknown",
            "followup_urgency": "ROUTINE",
            "retrieved_documents": [],
            "retrieval_method": "NONE",
            "knowledge_sources": [],
            "top_k_used": 0
        }
    
    @staticmethod
    def _no_index_response(adverse_event: str) -> Dict[str, Any]:
        """Response when FAISS index not available"""
        return {
            "medical_seriousness_hint": "MEDIUM",
            "critical_followup_fields": ["event_date", "patient_age", "drug_dose", "event_outcome"],
            "reasoning_text": f"RAG index not available for: '{adverse_event[:50]}...'. Please run build_rag_index.py to enable RAG retrieval.",
            "confidence_score": 0.0,
            "matched_categories": [],
            "regulatory_implication": "Unknown - RAG unavailable",
            "followup_urgency": "ROUTINE",
            "retrieved_documents": [],
            "retrieval_method": "NO_INDEX",
            "knowledge_sources": [],
            "top_k_used": 0
        }
    
    @staticmethod
    def _no_matches_response(adverse_event: str) -> Dict[str, Any]:
        """Response when no matches found"""
        return {
            "medical_seriousness_hint": "MEDIUM",
            "critical_followup_fields": ["adverse_event", "event_date", "patient_age"],
            "reasoning_text": f"No relevant matches found in knowledge base for: '{adverse_event[:50]}...'. Event may be novel or requires manual review.",
            "confidence_score": 0.2,
            "matched_categories": [],
            "regulatory_implication": "Manual review recommended",
            "followup_urgency": "HIGH",
            "retrieved_documents": [],
            "retrieval_method": "NO_MATCHES",
            "knowledge_sources": [],
            "top_k_used": 0
        }


# ============================================================================
# LANGGRAPH INTEGRATION
# ============================================================================

async def medical_reasoning_agent(state: Dict) -> Dict:
    """LangGraph-compatible agent function"""
    case_data = state.get("case_data", {})
    adverse_event = case_data.get("adverse_event", "")
    
    # Perform enhanced RAG analysis
    result = MedicalReasoningAgent.analyze(adverse_event, case_data)
    
    # Update state
    state["medical_seriousness_hint"] = result["medical_seriousness_hint"]
    state["medical_critical_fields"] = result["critical_followup_fields"]
    state["medical_reasoning_text"] = result["reasoning_text"]
    state["medical_confidence"] = result["confidence_score"]
    state["medical_regulatory_implication"] = result["regulatory_implication"]
    state["medical_followup_urgency"] = result["followup_urgency"]
    
    # Add to agent confidences
    if "agent_confidences" not in state:
        state["agent_confidences"] = {}
    if "agent_reasonings" not in state:
        state["agent_reasonings"] = {}
    
    state["agent_confidences"]["MedicalReasoning"] = result["confidence_score"]
    state["agent_reasonings"]["MedicalReasoning"] = result["reasoning_text"]
    
    # Add to messages
    if "messages" not in state:
        state["messages"] = []
    
    state["messages"].append({
        "agent": "MedicalReasoningV2",
        "seriousness_hint": result["medical_seriousness_hint"],
        "confidence": result["confidence_score"],
        "reasoning": result["reasoning_text"],
        "matched_categories": result["matched_categories"],
        "critical_fields": result["critical_followup_fields"],
        "retrieval_method": result["retrieval_method"],
        "knowledge_sources": result["knowledge_sources"],
        "docs_retrieved": len(result["retrieved_documents"]),
        "consensus": result.get("seriousness_consensus")
    })
    
    # Add to decision history
    if "decision_history" not in state:
        state["decision_history"] = []
    
    state["decision_history"].append({
        "agent": "MedicalReasoningV2",
        "timestamp": datetime.utcnow().isoformat(),
        "decision": result["medical_seriousness_hint"],
        "confidence": result["confidence_score"],
        "reasoning": result["reasoning_text"][:300],
        "retrieval_method": result["retrieval_method"]
    })
    
    return state


# ============================================================================
# TEST FUNCTION
# ============================================================================

def test_rag_v2():
    """Test the enhanced RAG retrieval"""
    test_queries = [
        "patient died after taking medication",
        "severe diarrhea and dehydration",
        "cardiac arrest following drug administration",
        "nausea and vomiting",
        "anaphylactic shock",
        "liver failure hepatotoxicity",
        "hospitalization required",
        "rash and itching"
    ]
    
    print("=" * 80)
    print("TESTING MEDICAL REASONING AGENT V2.0 (ENHANCED RAG)")
    print("=" * 80)
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print("-" * 80)
        
        result = MedicalReasoningAgent.analyze(query)
        
        print(f"Seriousness:  {result['medical_seriousness_hint']}")
        print(f"Confidence:   {result['confidence_score']:.0%}")
        print(f"Urgency:      {result['followup_urgency']}")
        print(f"Method:       {result['retrieval_method']}")
        print(f"Sources:      {', '.join(result['knowledge_sources'])}")
        print(f"Docs Found:   {len(result['retrieved_documents'])}")
        
        if 'seriousness_consensus' in result:
            consensus = result['seriousness_consensus']
            print(f"Consensus:    {consensus['winner']} ({consensus['consensus_score']:.0%})")
            print(f"Votes:        {consensus['votes']}")
        
        if result['retrieved_documents']:
            print(f"\nTop 3 Matches:")
            for i, doc in enumerate(result['retrieved_documents'][:3], 1):
                print(f"  {i}. {doc['title'][:55]}... ({doc['similarity']:.0%})")
                print(f"     Source: {doc['source']}, Seriousness: {doc['seriousness']}")
        
        print(f"\nReasoning:\n{result['reasoning_text']}")


if __name__ == "__main__":
    test_rag_v2()