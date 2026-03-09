"""
Production-Ready ML-Based Risk Assessment Agent

Uses multi-feature prediction:
- Text embeddings (adverse_event, suspect_drug)
- Structured features (age, route, reporter_type)
- LogisticRegression trained on FAERS seriousness labels

NO keyword-based rules.
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import joblib
import os
from pathlib import Path
from typing import Dict, List, Tuple
import logging

from app.db.session import SessionLocal
from app.models.case import AECase

logger = logging.getLogger(__name__)


class RiskAssessmentAgent:
    """
    ML-based risk assessment using multi-feature prediction.
    
    Features:
    - adverse_event text → SentenceTransformer (384D)
    - suspect_drug text → SentenceTransformer (384D)
    - patient_age → numeric (scaled)
    - route → one-hot encoding (top 20 + Other)
    - reporter_type (occp_cod) → one-hot encoding (5 categories)
    
    Training:
    - Loads FAERS cases from database with all features
    - Uses is_serious field as ground truth label
    - Trains LogisticRegression on concatenated feature vector
    
    Inference:
    - Extracts and engineers all features
    - Predicts probability of seriousness
    - Maps to HIGH/MEDIUM/LOW categories
    """
    
    # Top 20 most common routes (from data analysis)
    TOP_ROUTES = [
        'Oral', 'Unknown', 'Intravenous (not otherwise specified)',
        'Subcutaneous', 'Intravenous drip', 'Intramuscular',
        'Respiratory (inhalation)', 'Other', 'Transplacental',
        'Topical', 'Intra-uterine', 'Transdermal', 'Ophthalmic',
        'Intraocular', 'Subdermal', 'Vaginal', 'Sublingual',
        'Intraperitoneal', 'Nasal', 'Intravenous bolus'
    ]
    
    # Reporter types (occp_cod)
    REPORTER_TYPES = ['CN', 'HP', 'MD', 'LW', 'PH']
    
    def __init__(self, model_dir: str = "models"):
        """
        Initialize and train the multi-feature risk assessment model.
        
        Args:
            model_dir: Directory to save/load trained models
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        
        # Paths for saved models
        self.classifier_path = self.model_dir / "risk_classifier.pkl"
        self.scaler_path = self.model_dir / "risk_scaler.pkl"
        self.features_path = self.model_dir / "risk_model_features.json"
        
        logger.info("Initializing Multi-Feature RiskAssessmentAgent...")
        
        # Load embedding model
        logger.info("Loading SentenceTransformer (all-MiniLM-L6-v2)...")
        self.encoder = SentenceTransformer("all-MiniLM-L6-v2")
        
        # Load or train classifier and scaler
        if self.classifier_path.exists() and self.scaler_path.exists():
            logger.info("Loading pre-trained multi-feature classifier...")
            self.classifier = joblib.load(self.classifier_path)
            self.scaler = joblib.load(self.scaler_path)
        else:
            logger.info("Training new multi-feature classifier on FAERS data...")
            self._train_classifier()
        
        logger.info("✅ Multi-Feature RiskAssessmentAgent ready")
    
    def _load_training_data(self) -> Tuple[List[Dict], List[int]]:
        """
        Load multi-feature training data from FAERS database.
        
        Returns:
            Tuple of (case_feature_dicts, is_serious_labels)
        """
        logger.info("Loading multi-feature FAERS training data from database...")
        
        db = SessionLocal()
        try:
            # Load all cases with all required features
            cases = db.query(
                AECase.adverse_event,
                AECase.suspect_drug,
                AECase.patient_age,
                AECase.drug_route,
                AECase.reporter_type,
                AECase.is_serious
            ).filter(
                AECase.adverse_event.isnot(None),
                AECase.adverse_event != '',
                AECase.suspect_drug.isnot(None),
                AECase.suspect_drug != ''
            ).all()
            
            # Build feature dictionaries
            case_dicts = []
            labels = []
            
            for case in cases:
                case_dicts.append({
                    'adverse_event': case.adverse_event or '',
                    'suspect_drug': case.suspect_drug or '',
                    'age': case.patient_age,
                    'route': case.drug_route,
                    'occp_cod': case.reporter_type
                })
                labels.append(1 if case.is_serious else 0)
            
            logger.info(f"Loaded {len(case_dicts)} cases with all features")
            logger.info(f"Serious cases: {sum(labels)} ({100*sum(labels)/len(labels):.1f}%)")
            logger.info(f"Non-serious cases: {len(labels)-sum(labels)} ({100*(len(labels)-sum(labels))/len(labels):.1f}%)")
            
            return case_dicts, labels
            
        finally:
            db.close()
    
    def _engineer_features(self, case_dict: Dict) -> np.ndarray:
        """
        Engineer multi-feature vector from case dictionary.
        
        Args:
            case_dict: Dictionary with keys: adverse_event, suspect_drug, age, route, occp_cod
        
        Returns:
            Feature vector (numpy array)
        """
        features = []
        
        # 1. Adverse event embedding (384D)
        adverse_event = case_dict.get('adverse_event', '')
        if adverse_event:
            ae_embedding = self.encoder.encode([adverse_event])[0]
        else:
            ae_embedding = np.zeros(384)
        features.append(ae_embedding)
        
        # 2. Suspect drug embedding (384D)
        suspect_drug = case_dict.get('suspect_drug', '')
        if suspect_drug:
            drug_embedding = self.encoder.encode([suspect_drug])[0]
        else:
            drug_embedding = np.zeros(384)
        features.append(drug_embedding)
        
        # 3. Patient age (1D, will be scaled later)
        age = case_dict.get('age')
        if age is not None and isinstance(age, (int, float)) and not np.isnan(age):
            age_feature = [float(age)]
        else:
            age_feature = [0.0]  # Missing age
        features.append(np.array(age_feature))
        
        # 4. Route one-hot (21D: top 20 + Other)
        route = case_dict.get('route', '') or ''
        route_onehot = np.zeros(len(self.TOP_ROUTES) + 1)  # +1 for "Other"
        if route in self.TOP_ROUTES:
            route_onehot[self.TOP_ROUTES.index(route)] = 1
        else:
            route_onehot[-1] = 1  # Other
        features.append(route_onehot)
        
        # 5. Reporter type one-hot (5D)
        reporter = case_dict.get('occp_cod', '') or ''
        reporter_onehot = np.zeros(len(self.REPORTER_TYPES))
        if reporter in self.REPORTER_TYPES:
            reporter_onehot[self.REPORTER_TYPES.index(reporter)] = 1
        features.append(reporter_onehot)
        
        # Concatenate all features
        return np.concatenate(features)
    
    def _train_classifier(self):
        """
        Train multi-feature LogisticRegression classifier on FAERS data.
        """
        # Load data
        case_dicts, labels = self._load_training_data()
        
        # Generate multi-feature vectors
        logger.info("Engineering multi-feature vectors...")
        logger.info("Features: adverse_event(384D) + suspect_drug(384D) + age(1D) + route(21D) + reporter(5D)")
        
        feature_vectors = []
        for i, case_dict in enumerate(case_dicts):
            if i % 10000 == 0:
                logger.info(f"  Processing {i}/{len(case_dicts)}...")
            feature_vectors.append(self._engineer_features(case_dict))
        
        feature_vectors = np.array(feature_vectors)
        logger.info(f"Feature vector shape: {feature_vectors.shape}")
        
        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            feature_vectors, labels,
            test_size=0.2,
            random_state=42,
            stratify=labels
        )
        
        logger.info(f"Training set: {len(X_train)} samples")
        logger.info(f"Test set: {len(X_test)} samples")
        
        # Scale numeric features (age is at index 768)
        logger.info("Scaling numeric features...")
        self.scaler = StandardScaler()
        X_train[:, 768] = self.scaler.fit_transform(X_train[:, 768].reshape(-1, 1)).ravel()
        X_test[:, 768] = self.scaler.transform(X_test[:, 768].reshape(-1, 1)).ravel()
        
        # Train classifier with class balancing
        logger.info("Training multi-feature LogisticRegression (class_weight='balanced')...")
        self.classifier = LogisticRegression(
            class_weight='balanced',
            max_iter=1000,
            random_state=42,
            n_jobs=-1
        )
        self.classifier.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.classifier.predict(X_test)
        y_proba = self.classifier.predict_proba(X_test)[:, 1]
        
        logger.info("\n" + "="*60)
        logger.info("MULTI-FEATURE CLASSIFICATION REPORT")
        logger.info("="*60)
        logger.info("\n" + classification_report(
            y_test, y_pred,
            target_names=['Non-Serious', 'Serious']
        ))
        
        auc = roc_auc_score(y_test, y_proba)
        logger.info(f"ROC-AUC: {auc:.4f}")
        logger.info("="*60)
        
        # Save models
        logger.info(f"Saving classifier to {self.classifier_path}")
        joblib.dump(self.classifier, self.classifier_path)
        
        logger.info(f"Saving scaler to {self.scaler_path}")
        joblib.dump(self.scaler, self.scaler_path)
        
        # Save feature info
        import json
        feature_info = {
            "total_features": feature_vectors.shape[1],
            "adverse_event_embedding": "0-383 (384D)",
            "suspect_drug_embedding": "384-767 (384D)",
            "age": "768 (1D, scaled)",
            "route_onehot": f"769-{769+len(self.TOP_ROUTES)} ({len(self.TOP_ROUTES)+1}D)",
            "reporter_onehot": f"{770+len(self.TOP_ROUTES)}-{774+len(self.TOP_ROUTES)} (5D)",
            "top_routes": self.TOP_ROUTES,
            "reporter_types": self.REPORTER_TYPES
        }
        with open(self.features_path, 'w') as f:
            json.dump(feature_info, f, indent=2)
        logger.info(f"Saved feature info to {self.features_path}")
    
    async def assess(self, case_data: Dict) -> Dict:
        """
        Assess risk using multi-feature ML classifier.
        
        Args:
            case_data: Dictionary with keys:
                - adverse_event: str
                - age: int/float (optional)
                - suspect_drug: str (optional)
                - route: str (optional)
                - occp_cod: str (optional)
        
        Returns:
            {
                "risk_score": float (0-1),
                "risk_category": "HIGH" | "MEDIUM" | "LOW",
                "confidence_score": float (0-1),
                "reasoning_text": str
            }
        """
        # Extract and validate adverse event
        adverse_event = case_data.get('adverse_event', '')
        
        if not adverse_event:
            return {
                "risk_score": 0.0,
                "risk_category": "LOW",
                "confidence_score": 0.0,
                "reasoning_text": "No adverse event text provided"
            }
        
        # Build complete feature dictionary with defaults
        feature_dict = {
            'adverse_event': adverse_event,
            'suspect_drug': case_data.get('suspect_drug', ''),
            'age': case_data.get('age'),
            'route': case_data.get('route'),
            'occp_cod': case_data.get('occp_cod')
        }
        
        # Engineer features
        feature_vector = self._engineer_features(feature_dict)
        
        # Scale age feature (at index 768)
        feature_vector[768] = self.scaler.transform([[feature_vector[768]]])[0, 0]
        
        # Predict probability
        probability = self.classifier.predict_proba([feature_vector])[0, 1]
        
        # Map to category
        if probability > 0.7:
            category = "HIGH"
        elif probability > 0.3:
            category = "MEDIUM"
        else:
            category = "LOW"
        
        # Build reasoning
        reasoning = "Multi-feature FAERS ML classifier"
        
        return {
            "risk_score": float(probability),
            "risk_category": category,
            "confidence_score": float(probability),
            "reasoning_text": reasoning
        }
