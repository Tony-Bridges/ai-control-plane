from typing import List, Dict, Any, Optional
import asyncio
import time
import re
import logging
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_anonymizer import AnonymizerEngine
import spacy

from src.detectors.base import DetectedEntity
from src.detectors.sa_detectors import (
    SAIDDetector, SAPhoneDetector, SACompanyDetector,
    SABankDetector, SARSDetector, MedicalAidDetector
)
from src.api.models import ClassificationResult, RiskLevel
from src.utils.constants import CLASSIFICATION_KEYWORDS, RISK_WEIGHTS
from src.utils.validators import ValidatorChain

logger = logging.getLogger(__name__)

class ClassificationEngine:
    """Main classification engine with SA specialization"""

    def __init__(self):
        # Initialize Presidio
        self.analyzer = AnalyzerEngine()

        # Add SA-specific recognizers
        registry = RecognizerRegistry()
        registry.add_recognizer(SAIDDetector())
        registry.add_recognizer(SAPhoneDetector())
        registry.add_recognizer(SACompanyDetector())
        registry.add_recognizer(SABankDetector())
        registry.add_recognizer(SARSDetector())
        registry.add_recognizer(MedicalAidDetector())

        # Load spaCy model for NLP
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
            self.nlp = spacy.load("en_core_web_sm")

        # Initialize validators
        self.validators = ValidatorChain()

        # Cache for classification results
        self.cache = {}
        self.cache_size = 1000

    async def classify(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ClassificationResult:
        """Classify text and detect entities"""

        start_time = time.time()

        # Check cache
        cache_key = f"{text[:100]}_{context.get('department', '')}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Analyze with Presidio
        presidio_results = self.analyzer.analyze(
            text=text,
            language="en",
            context=context
        )

        # Convert to our entity format
        entities = []
        for result in presidio_results:
            entity = DetectedEntity(
                entity_type=result.entity_type,
                value=text[result.start:result.end],
                start=result.start,
                end=result.end,
                score=result.score,
                confidence=result.score,
                metadata={"context": context}
            )
            # Validate
            if self.validators.validate(entity):
                entities.append(entity)

        # Run additional NLP analysis
        doc = self.nlp(text)

        # Determine classification
        classification = self._determine_classification(text, doc, entities)

        # Calculate risk score
        risk_score = self._calculate_risk_score(entities, classification, context)

        # Determine risk level
        risk_level = self._get_risk_level(risk_score)

        # Check for SA IDs specifically
        contains_sa_id = any(
            e.entity_type == "SA_ID" for e in entities
        )

        # Build result
        result = ClassificationResult(
            classification=classification,
            risk_score=risk_score,
            risk_level=risk_level,
            contains_pii=len(entities) > 0,
            contains_sa_id=contains_sa_id,
            detected_entities=[e.entity_type for e in entities],
            confidence_scores={
                e.entity_type: e.confidence for e in entities
            },
            metadata={
                "entities_count": len(entities),
                "processing_time_ms": (time.time() - start_time) * 1000,
                "text_length": len(text)
            }
        )

        # Cache result
        if len(self.cache) >= self.cache_size:
            # Remove oldest entry
            self.cache.pop(next(iter(self.cache)))
        self.cache[cache_key] = result

        return result

    def _determine_classification(
        self,
        text: str,
        doc,
        entities: List[DetectedEntity]
    ) -> str:
        """Determine text classification"""

        text_lower = text.lower()

        # Score each classification
        scores = {}
        for category, keywords in CLASSIFICATION_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
                # Check if keyword appears as lemma
                for token in doc:
                    if token.lemma_.lower() == keyword:
                        score += 0.5
            scores[category] = score

        # Check entity types
        for entity in entities:
            if entity.entity_type in ["SA_ID", "SA_PHONE"]:
                scores["employee"] = scores.get("employee", 0) + 2
            elif entity.entity_type in ["SA_BANK", "SARS"]:
                scores["financial"] = scores.get("financial", 0) + 2
            elif entity.entity_type in ["MEDICAL_AID"]:
                scores["medical"] = scores.get("medical", 0) + 3

        # Get max score
        if scores:
            max_category = max(scores, key=scores.get)
            if scores[max_category] > 0:
                return max_category

        return "general"

    def _calculate_risk_score(
        self,
        entities: List[DetectedEntity],
        classification: str,
        context: Optional[Dict[str, Any]] = None
    ) -> int:
        """Calculate risk score"""

        score = 0

        # Add weights based on entity types
        for entity in entities:
            weight = RISK_WEIGHTS.get(entity.entity_type, 10)
            score += weight * entity.confidence

        # Increase score for medical/financial classification
        if classification == "medical":
            score += 20
        elif classification == "financial":
            score += 15
        elif classification == "employee":
            score += 10

        # Department adjustments
        if context and context.get("department"):
            dept = context["department"]
            if dept == "hr" and classification == "employee":
                score += 10
            elif dept == "finance" and classification == "financial":
                score += 10
            elif dept == "medical" and classification == "medical":
                score += 15

        # Cap at 100
        return min(100, int(score))

    def _get_risk_level(self, score: int) -> RiskLevel:
        """Determine risk level from score"""
        if score >= 70:
            return RiskLevel.CRITICAL
        elif score >= 50:
            return RiskLevel.HIGH
        elif score >= 30:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
