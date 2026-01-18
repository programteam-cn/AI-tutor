####################### Student profiling agent ##########################
####################### Categorize the student and results a json ###########

import json
import os
from typing import Dict, Any
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from config import llm

load_dotenv()

model = ChatOpenAI(
    model_name=llm["model_name"],
    temperature=llm["temperature"],
    max_tokens=llm["max_tokens"],
)


class StudentProfileAgent:
    """Agent to update a student profile based on their responses."""
    
    def __init__(self, user_id: str, topic: str = None):
        self.user_id = user_id
        self.topic = topic
        self.model = model
        self.user_data_path = f"storage/user_data/{user_id}.json"
        self.profile = {
            "user_id": user_id,
            "skill_level": "beginner",
            "completed_clusters": [],
            "current_cluster": None,
            "mastery_scores": {},
            "category": "medium",
            "reasoning": "Initial assessment pending"
        }
        self.session_data = {
            "user_id": user_id,
            "topic": topic,
            "questions_history": [],
            "mastery_tracking": {
                "concepts": {},
                "subtopics": {},
                "overall_mastery": 0.0
            },
            "weak_concepts": {},
            "concept_gaps": []
        }
        self.mastery_threshold = 0.80
        self._load_or_create_user_data()
    
    def _load_or_create_user_data(self):
        """Load existing user data or create new file."""
        os.makedirs("storage/user_data", exist_ok=True)
        
        if os.path.exists(self.user_data_path):
            try:
                with open(self.user_data_path, 'r') as f:
                    self.session_data = json.load(f)
            except Exception as e:
                print(f"Error loading user data: {e}")
        else:
            self._save_user_data()
    
    def _save_user_data(self):
        """Save user data to JSON file."""
        try:
            with open(self.user_data_path, 'w') as f:
                json.dump(self.session_data, f, indent=2)
        except Exception as e:
            print(f"Error saving user data: {e}")
    
    def save_question_data(self, question_data: Dict[str, Any], user_answer: str, classification: Dict[str, Any], evaluation: Dict[str, Any] = None, mastery_assessment: Dict[str, Any] = None):
        """Save question, answer, classification, evaluation, and mastery assessment to user data."""
        # Use provided mastery assessment or create a default one
        if mastery_assessment is None:
            mastery_assessment = {
                "mastery_probability": 0.0,
                "concept_mastery": {},
                "subtopic_mastery": 0.0,
                "confidence_level": "low",
                "feedback": "No mastery assessment provided",
                "mastery_achieved": False
            }
        
        question_record = {
            "timestamp": datetime.now().isoformat(),
            "question": question_data.get("question"),
            "problem_id": question_data.get("problem_id"),
            "cluster_info": question_data.get("cluster_info"),
            "user_answer": user_answer,
            "profiling_score": {
                "category": classification.get("category"),
                "reasoning": classification.get("reasoning")
            },
            "mastery_assessment": mastery_assessment
        }
        
        if evaluation:
            question_record["evaluation"] = evaluation
            # Track weak concepts from evaluation
            self._track_weak_concepts(evaluation)
        
        self.session_data["questions_history"].append(question_record)
        
        # Update mastery tracking
        self._update_mastery_tracking(question_data, evaluation, mastery_assessment)
        
        self._save_user_data()
    
    def get_profile(self) -> Dict[str, Any]:
        """Get the current student profile."""
        return self.profile
    
    def update_profile(self, classification: Dict[str, Any]):
        """Update the profile with classification results."""
        self.profile["category"] = classification.get("category", self.profile["category"])
        self.profile["reasoning"] = classification.get("reasoning", self.profile["reasoning"])
    
    def classify_student(self, question: str, response: str) -> Dict[str, Any]:
        """Classify the student based on their response."""
        prompt = f"""Based on the student's response to the question, classify their learning pace and understanding.

Question: {question}

Student's Answer: {response}

Analyze the student's answer and return a JSON object with:
- "category": "slow" (struggling/needs more help), "medium" (progressing normally), or "fast" (advanced/excelling)
- "reasoning": a brief explanation (1-2 sentences) for why you classified them this way

Return ONLY the JSON object, nothing else."""
        
        try:
            ai_message = self.model.invoke(prompt)
            # Extract content from AIMessage
            content = ai_message.content if hasattr(ai_message, 'content') else str(ai_message)
            
            # Try to extract JSON from the response
            # Remove markdown code blocks if present
            content = content.strip()
            if content.startswith('```'):
                lines = content.split('\n')
                content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content
                content = content.replace('```json', '').replace('```', '').strip()
            
            classification = json.loads(content)
            
            # Update the profile with the new classification
            self.update_profile(classification)
            
            return classification
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Response content: {content}")
            return {
                "category": "medium",
                "reasoning": "Unable to analyze response"
            }
        except Exception as e:
            print(f"Error classifying student: {e}")
            return {
                "category": "medium",
                "reasoning": "Error during classification"
            }
    
    def get_subtopic_history(self, subtopic: str) -> list:
        """Get question history for a specific subtopic."""
        all_history = self.session_data.get("questions_history", [])
        history = [
            q for q in all_history 
            if q.get("cluster_info", {}).get("subtopic_name", "") == subtopic
        ]
        return history
    
    def _format_history_for_mastery(self, history: list) -> str:
        """Format recent question history for mastery assessment."""
        if not history:
            return "No previous attempts"
        
        lines = []
        for i, record in enumerate(history, 1):
            eval_data = record.get("evaluation", {})
            cluster_info = record.get("cluster_info", {})
            
            result = "✓ CORRECT" if eval_data.get("is_correct", False) else "✗ INCORRECT"
            score = eval_data.get("score", 0)
            subtopic = cluster_info.get("subtopic_name", "Unknown")
            
            lines.append(f"Attempt {i}: {result} (Score: {score}/100) - {subtopic}")
        
        return "\n".join(lines)
    
    def _update_mastery_tracking(self, question_data: Dict[str, Any], evaluation: Dict[str, Any], mastery_assessment: Dict[str, Any]):
        """Update the mastery tracking in session data."""
        if "mastery_tracking" not in self.session_data:
            self.session_data["mastery_tracking"] = {
                "concepts": {},
                "subtopics": {},
                "overall_mastery": 0.0
            }
        
        cluster_info = question_data.get("cluster_info", {})
        subtopic = cluster_info.get("subtopic_name", "Unknown")
        skills = cluster_info.get("skills_tested", [])
        
        # Update concept mastery
        concept_mastery = mastery_assessment.get("concept_mastery", {})
        for skill, score in concept_mastery.items():
            if skill not in self.session_data["mastery_tracking"]["concepts"]:
                self.session_data["mastery_tracking"]["concepts"][skill] = {
                    "mastery_score": score,
                    "attempts": 1,
                    "last_updated": datetime.now().isoformat()
                }
            else:
                # Average with previous score
                prev_score = self.session_data["mastery_tracking"]["concepts"][skill]["mastery_score"]
                prev_attempts = self.session_data["mastery_tracking"]["concepts"][skill]["attempts"]
                new_score = (prev_score * prev_attempts + score) / (prev_attempts + 1)
                
                self.session_data["mastery_tracking"]["concepts"][skill] = {
                    "mastery_score": new_score,
                    "attempts": prev_attempts + 1,
                    "last_updated": datetime.now().isoformat()
                }
        
        # Update subtopic mastery
        subtopic_mastery = mastery_assessment.get("subtopic_mastery", 0.0)
        if subtopic not in self.session_data["mastery_tracking"]["subtopics"]:
            # First attempt - never mark as mastery achieved
            self.session_data["mastery_tracking"]["subtopics"][subtopic] = {
                "mastery_score": subtopic_mastery,
                "attempts": 1,
                "mastery_achieved": False,  # Never on first attempt
                "last_updated": datetime.now().isoformat()
            }
        else:
            prev_score = self.session_data["mastery_tracking"]["subtopics"][subtopic]["mastery_score"]
            prev_attempts = self.session_data["mastery_tracking"]["subtopics"][subtopic]["attempts"]
            new_score = (prev_score * prev_attempts + subtopic_mastery) / (prev_attempts + 1)
            new_attempts = prev_attempts + 1
            
            # Only allow mastery_achieved if at least 3 attempts
            mastery_achieved = mastery_assessment.get("mastery_achieved", False) and new_attempts >= 3
            
            self.session_data["mastery_tracking"]["subtopics"][subtopic] = {
                "mastery_score": new_score,
                "attempts": new_attempts,
                "mastery_achieved": mastery_achieved,
                "last_updated": datetime.now().isoformat()
            }
        
        # Update overall mastery to reflect ONLY current subtopic's mastery score
        # This ensures each subtopic starts fresh at 0 and tracks independently
        current_subtopic_score = self.session_data["mastery_tracking"]["subtopics"][subtopic]["mastery_score"]
        self.session_data["mastery_tracking"]["overall_mastery"] = current_subtopic_score
        
        # Update profile mastery scores
        self.profile["mastery_scores"] = self.session_data["mastery_tracking"]
    
    def get_mastery_info(self) -> Dict[str, Any]:
        """Get current mastery information."""
        if "mastery_tracking" not in self.session_data:
            return {
                "overall_mastery": 0.0,
                "concepts": {},
                "subtopics": {}
            }
        
        return self.session_data["mastery_tracking"]
    
    def _track_weak_concepts(self, evaluation: Dict[str, Any]):
        """Track weak concepts identified from user's answer evaluation."""
        if "weak_concepts" not in self.session_data:
            self.session_data["weak_concepts"] = {}
        if "concept_gaps" not in self.session_data:
            self.session_data["concept_gaps"] = []
        
        # Track weak concepts from evaluation
        weak_concepts = evaluation.get("weak_concepts", [])
        for concept in weak_concepts:
            if concept not in self.session_data["weak_concepts"]:
                self.session_data["weak_concepts"][concept] = {
                    "occurrences": 1,
                    "first_seen": datetime.now().isoformat(),
                    "last_seen": datetime.now().isoformat(),
                    "severity": "high"
                }
            else:
                self.session_data["weak_concepts"][concept]["occurrences"] += 1
                self.session_data["weak_concepts"][concept]["last_seen"] = datetime.now().isoformat()
        
        # Track missing concepts (concept gaps)
        missing_concepts = evaluation.get("missing_concepts", [])
        for concept in missing_concepts:
            if concept not in self.session_data["concept_gaps"]:
                self.session_data["concept_gaps"].append(concept)
    
    def get_weak_topics(self) -> Dict[str, Any]:
        """Get identified weak topics and concepts from user's performance."""
        weak_concepts = self.session_data.get("weak_concepts", {})
        concept_gaps = self.session_data.get("concept_gaps", [])
        
        # Rank weak concepts by severity (occurrences)
        ranked_weak_concepts = sorted(
            weak_concepts.items(),
            key=lambda x: x[1]["occurrences"],
            reverse=True
        )
        
        return {
            "weak_concepts": dict(ranked_weak_concepts),
            "concept_gaps": concept_gaps,
            "priority_concepts": [concept for concept, _ in ranked_weak_concepts[:3]]  # Top 3 weak concepts
        }
    
    def reset_subtopic_mastery(self, subtopic: str):
        """Reset mastery score for a specific subtopic to 0 when starting it."""
        if "mastery_tracking" not in self.session_data:
            self.session_data["mastery_tracking"] = {
                "concepts": {},
                "subtopics": {},
                "overall_mastery": 0.0
            }
        
        # Clear all concept mastery scores to start fresh for the new subtopic
        self.session_data["mastery_tracking"]["concepts"] = {}
        
        # Initialize or reset the subtopic with 0 mastery
        self.session_data["mastery_tracking"]["subtopics"][subtopic] = {
            "mastery_score": 0.0,
            "attempts": 0,
            "mastery_achieved": False,
            "last_updated": datetime.now().isoformat()
        }
        
        # Update overall mastery to 0 since we're starting a new subtopic
        self.session_data["mastery_tracking"]["overall_mastery"] = 0.0
        
        # Clear weak concepts and concept gaps for fresh start
        self.session_data["weak_concepts"] = {}
        self.session_data["concept_gaps"] = []
        
        # Save the changes
        self._save_user_data()
        
        print(f"✅ Reset mastery score to 0 for subtopic: {subtopic}")
        print(f"   - Cleared all concept mastery scores")
        print(f"   - Cleared weak concepts and gaps")
        print(f"   - Starting fresh mastery tracking")
