"""
Response Prediction Service
============================

ML-based response probability prediction using trained Random Forest model.

This service:
1. Loads the trained response_model_rf.pkl
2. Prepares features from case data
3. Predicts response probability
4. Returns prediction with confidence

Used by Feature-2 Engagement Risk Adaptation Module.
"""

import os
import joblib
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Model paths
MODELS_DIR = Path(__file__).parent.parent.parent / "models"
RESPONSE_MODEL_PATH = MODELS_DIR / "response_model_rf.pkl"
RESPONSE_FEATURES_PATH = MODELS_DIR / "response_model_features.pkl"


class ResponsePredictionService:
    """
    ML-based Response Prediction Service
    
    Uses trained Random Forest model to predict reporter response probability.
    Falls back to rule-based prediction if model unavailable.
    """
    
    _instance = None
    _model = None
    _features = None
    _is_loaded = False
    
    # Fallback response rates by reporter type
    FALLBACK_RATES = {
        'MD': 0.70,  # Medical Doctor
        'HP': 0.60,  # Health Professional
        'PH': 0.55,  # Pharmacist
        'CN': 0.35,  # Consumer
        'LW': 0.45,  # Lawyer
        'PT': 0.40,  # Patient
        'OT': 0.40,  # Other
        'UNKNOWN': 0.40
    }
    
    # Reporter type encoding (must match training)
    REPORTER_ENCODING = {
        'MD': 5, 'HP': 4, 'PH': 3, 'CN': 1, 'LW': 2, 'PT': 0, 'OT': 0, 'UNKNOWN': 0
    }
    
    # Sex encoding
    SEX_ENCODING = {'M': 1, 'F': 0, 'UNKNOWN': 0.5}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load_model(self) -> bool:
        """Load the trained model and features"""
        if self._is_loaded:
            return True
        
        try:
            if not RESPONSE_MODEL_PATH.exists():
                logger.warning(f"Response model not found: {RESPONSE_MODEL_PATH}")
                return False
            
            if not RESPONSE_FEATURES_PATH.exists():
                logger.warning(f"Response features not found: {RESPONSE_FEATURES_PATH}")
                return False
            
            self._model = joblib.load(RESPONSE_MODEL_PATH)
            self._features = joblib.load(RESPONSE_FEATURES_PATH)
            self._is_loaded = True
            
            logger.info(f"✅ Response model loaded: {len(self._features)} features")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load response model: {e}")
            return False
    
    def prepare_features(self, case_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Prepare feature dict from case data.
        
        Maps case_data fields to model features.
        """
        reporter_type = str(case_data.get('reporter_type', 'UNKNOWN')).upper()
        
        # Calculate completeness
        required_fields = ['patient_age', 'sex', 'adverse_event', 'suspect_drug', 
                          'event_date', 'reporter_type', 'dose', 'route']
        present = sum(1 for f in required_fields if case_data.get(f))
        completeness_score = present / len(required_fields)
        
        # Missing count
        missing_count = len(required_fields) - present
        
        # Patient age
        patient_age = case_data.get('patient_age') or case_data.get('age', 50)
        try:
            patient_age = float(patient_age)
        except:
            patient_age = 50.0
        
        # Sex encoding
        sex = str(case_data.get('sex', 'UNKNOWN')).upper()
        sex_encoded = self.SEX_ENCODING.get(sex, 0.5)
        
        # Age categories
        is_elderly = 1 if patient_age >= 65 else 0
        is_child = 1 if patient_age < 18 else 0
        
        # Reporter encoding
        reporter_encoded = self.REPORTER_ENCODING.get(reporter_type, 0)
        
        # Reporter intelligence features (use defaults if not available)
        reporter_credibility = case_data.get('reporter_credibility', 0.6)
        reporter_historical_rate = case_data.get('reporter_historical_rate', 0.5)
        reporter_avg_response_time = case_data.get('reporter_avg_response_time', 48)
        reporter_quality_score = case_data.get('reporter_quality_score', 0.7)
        
        # Reporter type frequency (how common this type is)
        reporter_type_freq = {'MD': 0.25, 'HP': 0.20, 'PH': 0.10, 'CN': 0.30, 
                             'LW': 0.05, 'PT': 0.08, 'OT': 0.02}
        reporter_type_frequency = reporter_type_freq.get(reporter_type, 0.1)
        is_frequent_reporter_type = 1 if reporter_type_frequency > 0.15 else 0
        
        # Temporal features
        event_date = case_data.get('event_date') or case_data.get('event_dt')
        if event_date:
            try:
                if isinstance(event_date, str):
                    # Try parsing various formats
                    for fmt in ['%Y-%m-%d', '%Y%m%d', '%d-%m-%Y']:
                        try:
                            event_date = datetime.strptime(event_date[:10], fmt)
                            break
                        except:
                            continue
                if isinstance(event_date, datetime):
                    report_age_days = (datetime.now() - event_date).days
                else:
                    report_age_days = 30  # Default
            except:
                report_age_days = 30
        else:
            report_age_days = 30
        
        is_very_recent = 1 if report_age_days <= 7 else 0
        is_recent = 1 if report_age_days <= 30 else 0
        is_old = 1 if report_age_days > 180 else 0
        
        # Quarter and seasonal features
        now = datetime.now()
        report_quarter = (now.month - 1) // 3 + 1
        is_holiday_season = 1 if now.month in [11, 12, 1] else 0
        is_summer = 1 if now.month in [6, 7, 8] else 0
        is_weekday = 1 if now.weekday() < 5 else 0
        report_day_of_week = now.weekday()
        
        # Geographic features (use defaults)
        country = str(case_data.get('country', 'US')).upper()
        country_response_rate = {'US': 0.65, 'UK': 0.60, 'DE': 0.55, 'FR': 0.50}.get(country, 0.45)
        is_us_reporter = 1 if country == 'US' else 0
        is_eu_reporter = 1 if country in ['UK', 'DE', 'FR', 'IT', 'ES'] else 0
        country_regulation_score = {'US': 0.9, 'UK': 0.85, 'DE': 0.85, 'FR': 0.8}.get(country, 0.6)
        country_encoded = hash(country) % 100 / 100  # Normalize to 0-1
        
        # Risk score (from Feature-1)
        risk_score = case_data.get('risk_score', 0.5)
        
        # Interaction features
        reporter_risk_interaction = reporter_credibility * risk_score
        completeness_risk_interaction = completeness_score * risk_score
        temporal_reporter_interaction = (1 - is_old) * reporter_historical_rate
        geographic_credibility_interaction = country_regulation_score * reporter_credibility
        
        return {
            # Core features (7)
            'reporter_encoded': reporter_encoded,
            'missing_count': missing_count,
            'completeness_score': completeness_score,
            'patient_age': patient_age,
            'sex_encoded': sex_encoded,
            'is_elderly': is_elderly,
            'is_child': is_child,
            
            # Reporter intelligence (6)
            'reporter_credibility': reporter_credibility,
            'reporter_historical_rate': reporter_historical_rate,
            'reporter_avg_response_time': reporter_avg_response_time,
            'reporter_quality_score': reporter_quality_score,
            'reporter_type_frequency': reporter_type_frequency,
            'is_frequent_reporter_type': is_frequent_reporter_type,
            
            # Temporal features (9)
            'report_age_days': report_age_days,
            'is_very_recent': is_very_recent,
            'is_recent': is_recent,
            'is_old': is_old,
            'report_quarter': report_quarter,
            'is_holiday_season': is_holiday_season,
            'is_summer': is_summer,
            'is_weekday': is_weekday,
            'report_day_of_week': report_day_of_week,
            
            # Geographic features (5)
            'country_response_rate': country_response_rate,
            'is_us_reporter': is_us_reporter,
            'is_eu_reporter': is_eu_reporter,
            'country_regulation_score': country_regulation_score,
            'country_encoded': country_encoded,
            
            # Risk context (1)
            'risk_score': risk_score,
            
            # Interactions (4)
            'reporter_risk_interaction': reporter_risk_interaction,
            'completeness_risk_interaction': completeness_risk_interaction,
            'temporal_reporter_interaction': temporal_reporter_interaction,
            'geographic_credibility_interaction': geographic_credibility_interaction
        }
    
    def predict(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict response probability for a case.
        
        Args:
            case_data: Case data dictionary
            
        Returns:
            {
                "response_probability": float (0.0-1.0),
                "prediction_confidence": float (0.0-1.0),
                "prediction_method": "ML_MODEL" | "FALLBACK",
                "model_version": str,
                "features_used": int
            }
        """
        # Try ML model first
        if self.load_model():
            try:
                return self._predict_with_model(case_data)
            except Exception as e:
                logger.warning(f"ML prediction failed, using fallback: {e}")
        
        # Fallback to rule-based
        return self._predict_fallback(case_data)
    
    def _predict_with_model(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict using trained ML model"""
        import numpy as np
        
        # Prepare features
        feature_dict = self.prepare_features(case_data)
        
        # Create feature array in correct order
        feature_array = np.array([[feature_dict.get(f, 0) for f in self._features]])
        
        # Predict probability
        proba = self._model.predict_proba(feature_array)[0]
        response_probability = float(proba[1])  # Probability of positive class (will respond)
        
        # Calculate confidence from probability distribution
        # High confidence when probability is far from 0.5
        prediction_confidence = abs(response_probability - 0.5) * 2
        prediction_confidence = min(0.95, prediction_confidence + 0.3)  # Boost base confidence
        
        return {
            "response_probability": round(response_probability, 3),
            "prediction_confidence": round(prediction_confidence, 3),
            "prediction_method": "ML_MODEL",
            "model_version": "response_model_rf_v1",
            "features_used": len(self._features),
            "feature_values": {k: round(v, 3) if isinstance(v, float) else v 
                             for k, v in feature_dict.items()}
        }
    
    def _predict_fallback(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback rule-based prediction"""
        reporter_type = str(case_data.get('reporter_type', 'UNKNOWN')).upper()
        
        # Base rate from reporter type
        base_prob = self.FALLBACK_RATES.get(reporter_type, 0.40)
        
        # Adjust for missing fields
        required_fields = ['patient_age', 'sex', 'adverse_event', 'suspect_drug']
        missing_count = sum(1 for f in required_fields if not case_data.get(f))
        adjusted_prob = base_prob - (missing_count * 0.03)
        
        # Adjust for risk score
        risk_score = case_data.get('risk_score', 0.5)
        if risk_score > 0.7:
            adjusted_prob *= 1.1  # Higher risk = more motivation
        
        # Clamp
        response_probability = max(0.1, min(0.95, adjusted_prob))
        
        # Lower confidence for fallback
        prediction_confidence = 0.5 if reporter_type in self.FALLBACK_RATES else 0.3
        
        return {
            "response_probability": round(response_probability, 3),
            "prediction_confidence": round(prediction_confidence, 3),
            "prediction_method": "FALLBACK",
            "model_version": "rule_based_v1",
            "features_used": 4,
            "fallback_reason": "ML model unavailable"
        }


# Global service instance
_service = ResponsePredictionService()


def predict_response(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function for response prediction.
    
    Example:
        result = predict_response({
            "reporter_type": "MD",
            "patient_age": 65,
            "sex": "M",
            "adverse_event": "nausea",
            "risk_score": 0.6
        })
        
        print(result["response_probability"])  # 0.72
        print(result["prediction_confidence"])  # 0.75
    """
    return _service.predict(case_data)


# ============================================================================
# TEST
# ============================================================================

def test_response_prediction():
    """Test the response prediction service"""
    print("=" * 70)
    print("TESTING RESPONSE PREDICTION SERVICE")
    print("=" * 70)
    
    test_cases = [
        {
            "name": "Medical Doctor, complete data",
            "case_data": {
                "reporter_type": "MD",
                "patient_age": 45,
                "sex": "F",
                "adverse_event": "hepatotoxicity",
                "suspect_drug": "acetaminophen",
                "risk_score": 0.7
            }
        },
        {
            "name": "Consumer, incomplete data",
            "case_data": {
                "reporter_type": "CN",
                "patient_age": 30,
                "risk_score": 0.4
            }
        },
        {
            "name": "Health Professional, elderly patient",
            "case_data": {
                "reporter_type": "HP",
                "patient_age": 78,
                "sex": "M",
                "adverse_event": "cardiac arrest",
                "suspect_drug": "warfarin",
                "risk_score": 0.9
            }
        },
        {
            "name": "Unknown reporter",
            "case_data": {
                "reporter_type": "UNKNOWN",
                "adverse_event": "rash",
                "risk_score": 0.3
            }
        }
    ]
    
    for tc in test_cases:
        print(f"\n{'='*70}")
        print(f"Test: {tc['name']}")
        print("-" * 70)
        
        result = predict_response(tc["case_data"])
        
        print(f"Input:")
        for k, v in tc["case_data"].items():
            print(f"  {k}: {v}")
        
        print(f"\nOutput:")
        print(f"  Response Probability: {result['response_probability']:.0%}")
        print(f"  Prediction Confidence: {result['prediction_confidence']:.0%}")
        print(f"  Method: {result['prediction_method']}")
        print(f"  Model Version: {result['model_version']}")
        print(f"  Features Used: {result['features_used']}")


if __name__ == "__main__":
    test_response_prediction()