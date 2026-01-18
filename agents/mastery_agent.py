"""
Knowledge Graph-Based Mastery Agent for SQL Learning
Uses LangChain with OpenAI GPT-4o-mini for LLM-based assessment
Supports progressive learning across multiple subtopics
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime
from dotenv import load_dotenv

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage, SystemMessage

# Load environment variables from .env file
load_dotenv()

@dataclass
class QuestionAttempt:
    """Represents a single question attempt with concept coverage"""
    question_id: str
    question_text: str
    difficulty: str
    concepts_tested: List[str]
    user_answer: str
    correct_answer: str
    is_correct: bool
    timestamp: str
    subtopic: str
    explanation: Optional[str] = None

@dataclass
class SubtopicMasteryState:
    """Tracks mastery state for a specific subtopic"""
    subtopic_id: str
    subtopic_name: str
    mastery_probability: float
    total_attempts: int
    correct_attempts: int
    attempts_history: List[QuestionAttempt]
    concepts_encountered: Set[str] = field(default_factory=set)
    concepts_mastered: Set[str] = field(default_factory=set)
    concepts_struggling: Set[str] = field(default_factory=set)
    mastery_achieved: bool = False
    completed_at: Optional[str] = None

class KnowledgeGraphMasteryAgent:
    """
    LLM-powered mastery assessment agent using LangChain and knowledge graph
    Supports progressive learning across multiple subtopics
    """
    
    def __init__(self, 
                 problems_file: str = "problems.json",
                 knowledge_graph_file: str = "knowledge_graph.json",
                 user_id: str = None):
        """Initialize the mastery agent  with LangChain"""
        self.problems_file = problems_file
        self.knowledge_graph_file = knowledge_graph_file
        
        # Generate user ID if not provided
        if user_id is None:
            self.user_id = f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        else:
            self.user_id = user_id
        
        # Create outputs directory if it doesn't exist
        os.makedirs("outputs", exist_ok=True)
        
        # User progress file in outputs folder
        self.user_progress_file = f"outputs/{self.user_id}_progress.json"
        self.problem_assessments = []  # Store assessment per problem
        
        # Initialize LangChain ChatOpenAI model
        self.llm = ChatOpenAI(
            model="gpt-4.1",
            temperature=0.2,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Create a separate LLM for assessment with different temperature
        self.assessment_llm = ChatOpenAI(
            model="gpt-4.1",
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize JSON output parser
        self.json_parser = JsonOutputParser()
        
        # Load data
        self.knowledge_graph = self._load_knowledge_graph()
        self.problems = self._load_problems()
        
        # Extract subtopic progression from knowledge graph
        self.subtopic_sequence = self._extract_subtopic_sequence()
        
        # Initialize mastery states for all subtopics
        self.subtopic_mastery_states: Dict[str, SubtopicMasteryState] = {}
        for subtopic in self.subtopic_sequence:
            self.subtopic_mastery_states[subtopic['subtopic_id']] = SubtopicMasteryState(
                subtopic_id=subtopic['subtopic_id'],
                subtopic_name=subtopic['subtopic_name'],
                mastery_probability=0.0,
                total_attempts=0,
                correct_attempts=0,
                attempts_history=[]
            )
        
        # Track current subtopic
        self.current_subtopic_index = 0
        self.current_subtopic_id = self.subtopic_sequence[0]['subtopic_id'] if self.subtopic_sequence else None
        
        self.mastery_threshold = 0.80
        
        # Load prompts and create LangChain prompt templates
        self._setup_prompt_templates()
    
    def _extract_subtopic_sequence(self) -> List[Dict]:
        """Extract ordered sequence of subtopics from knowledge graph"""
        subtopics = []
        
        if 'topics' in self.knowledge_graph:
            for topic in self.knowledge_graph['topics']:
                if 'subtopics' in topic:
                    for subtopic in topic['subtopics']:
                        subtopics.append({
                            'subtopic_id': subtopic.get('subtopic_id', ''),
                            'subtopic_name': subtopic.get('subtopic_name', ''),
                            'description': subtopic.get('description', ''),
                            'clusters': subtopic.get('clusters', [])
                        })
        
        return subtopics
    
    def _setup_prompt_templates(self):
        """Setup LangChain prompt templates"""
        # Load prompt content
        grading_system = self._load_prompt("grading_system.txt")
        grading_user = self._load_prompt("grading_user.txt")
        assessment_system = self._load_prompt("assessment_system.txt")
        assessment_user = self._load_prompt("assessment_user.txt")
        
        # Create grading prompt template
        self.grading_prompt = ChatPromptTemplate.from_messages([
            ("system", grading_system),
            ("user", grading_user)
        ])
        
        # Create assessment prompt template
        self.assessment_prompt = ChatPromptTemplate.from_messages([
            ("system", assessment_system),
            ("user", assessment_user)
        ])
        
        # Create chains
        self.grading_chain = self.grading_prompt | self.llm | self.json_parser
        self.assessment_chain = self.assessment_prompt | self.assessment_llm | self.json_parser
    
    def _load_prompt(self, filename: str) -> str:
        """Load a prompt from a file in the prompts directory"""
        try:
            with open(os.path.join("prompts", filename), 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            print(f"Warning: prompts/{filename} not found.")
            return ""
    
    def _load_knowledge_graph(self) -> Dict:
        """Load knowledge graph from JSON file"""
        try:
            with open(self.knowledge_graph_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: {self.knowledge_graph_file} not found.")
            return {}
    
    def _load_problems(self) -> List[Dict]:
        """Load problems from JSON file"""
        try:
            with open(self.problems_file, 'r') as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            else:
                return data.get('problems', [])
        except FileNotFoundError:
            print(f"Warning: {self.problems_file} not found.")
            return []
    
    def _get_subtopic_concepts(self, subtopic_id: str) -> List[str]:
        """Extract all concepts for a specific subtopic from knowledge graph"""
        concepts = []
        
        if 'topics' in self.knowledge_graph:
            for topic in self.knowledge_graph['topics']:
                if 'subtopics' in topic:
                    for subtopic in topic['subtopics']:
                        if subtopic.get('subtopic_id', '') == subtopic_id:
                            for cluster in subtopic.get('clusters', []):
                                skills = cluster.get('skills_tested', [])
                                concepts.extend(skills)
        
        return concepts
    
    def get_current_subtopic(self) -> Optional[Dict]:
        """Get the current subtopic being learned"""
        if self.current_subtopic_index < len(self.subtopic_sequence):
            return self.subtopic_sequence[self.current_subtopic_index]
        return None
    
    def get_next_question(self) -> Optional[Dict]:
        """Get the next question for the current subtopic"""
        current_subtopic = self.get_current_subtopic()
        if not current_subtopic:
            return None
        
        # Filter problems for current subtopic
        subtopic_problems = [
            p for p in self.problems 
            if str(p.get('topic_id', '')).lower() == str(current_subtopic['subtopic_id']).lower()
        ]
        
        current_state = self.subtopic_mastery_states[self.current_subtopic_id]
        
        if current_state.total_attempts < len(subtopic_problems):
            return subtopic_problems[current_state.total_attempts]
        return None
    
    def advance_to_next_subtopic(self) -> bool:
        """Move to the next subtopic if current is mastered"""
        current_state = self.subtopic_mastery_states[self.current_subtopic_id]
        
        if current_state.mastery_probability >= self.mastery_threshold:
            current_state.mastery_achieved = True
            current_state.completed_at = datetime.now().isoformat()
            
            self.current_subtopic_index += 1
            
            if self.current_subtopic_index < len(self.subtopic_sequence):
                self.current_subtopic_id = self.subtopic_sequence[self.current_subtopic_index]['subtopic_id']
                print(f"\n🎉 Mastery achieved! Moving to next subtopic: {self.subtopic_sequence[self.current_subtopic_index]['subtopic_name']}")
                return True
            else:
                print(f"\n🏆 CONGRATULATIONS! You've completed all subtopics!")
                return False
        
        return False
    
    def _grade_sql_answer(self, question: Dict, user_answer: str) -> Dict:
        """Use LangChain to grade SQL answer"""
        if not user_answer or user_answer.lower() in ['i dont know', 'idk', 'skip', 'dont know', "i don't know"]:
            return {
                'is_correct': False,
                'score': 0,
                'feedback': 'No valid answer provided.',
                'explanation': 'Please attempt to write a SQL query.',
                'weak_concepts': [],
                'missing_concepts': [],
                'concept_understanding': {}
            }
        
        try:
            # Invoke the grading chain
            result = self.grading_chain.invoke({
                "question_description": question.get('description', ''),
                "user_answer": user_answer
            })
            
            # Ensure all required fields exist with defaults
            if "score" not in result:
                result["score"] = 50 if result.get('is_correct', False) else 0
            if "is_correct" not in result:
                result["is_correct"] = False
            if "feedback" not in result:
                result["feedback"] = "No feedback provided."
            if "explanation" not in result:
                result["explanation"] = "No explanation provided."
            if "weak_concepts" not in result:
                result["weak_concepts"] = []
            if "missing_concepts" not in result:
                result["missing_concepts"] = []
            if "concept_understanding" not in result:
                result["concept_understanding"] = {}
            
            return result
        except Exception as e:
            print(f"Error grading answer: {e}")
            return {
                'is_correct': False,
                'score': 0,
                'feedback': 'Unable to grade automatically.',
                'explanation': str(e),
                'weak_concepts': [],
                'missing_concepts': [],
                'concept_understanding': {}
            }
    
    def record_attempt(self, question: Dict, user_answer: str, correct_answer: str = "", evaluation: Dict = None):
        """Record a learner's attempt for the current subtopic"""
        # Use evaluation result if provided, otherwise compare strings
        if evaluation and 'is_correct' in evaluation:
            is_correct = evaluation.get('is_correct', False)
        elif correct_answer:
            is_correct = user_answer.strip().lower() == correct_answer.strip().lower()
        else:
            is_correct = False
        
        concepts_tested = question.get('concepts', [])
        if not concepts_tested:
            concepts_tested = [question.get('cluster', 'general')]
        
        subtopic_id = question.get('subtopic_id', self.current_subtopic_id)
        
        attempt = QuestionAttempt(
            question_id=str(question.get('problem_id', f"q_{self.subtopic_mastery_states[subtopic_id].total_attempts + 1}")),
            question_text=question.get('description', question.get('problem_name', '')),
            difficulty=question.get('difficulty', 'medium'),
            concepts_tested=concepts_tested,
            user_answer=user_answer,
            correct_answer=correct_answer,
            is_correct=is_correct,
            timestamp=datetime.now().isoformat(),
            subtopic=subtopic_id,
            explanation=question.get('explanation', '')
        )
        
        # Update subtopic-specific state
        current_state = self.subtopic_mastery_states[subtopic_id]
        current_state.attempts_history.append(attempt)
        current_state.total_attempts += 1
        if is_correct:
            current_state.correct_attempts += 1
        
        for concept in concepts_tested:
            current_state.concepts_encountered.add(concept)
    
    def assess_mastery_with_llm(self) -> Dict:
        """
        Use LangChain to assess mastery probability for current subtopic
        """
        current_state = self.subtopic_mastery_states[self.current_subtopic_id]
        
        if not current_state.attempts_history:
            return {
                'mastery_probability': 0.0,
                'feedback': 'No attempts recorded yet. Begin with foundational concepts.',
                'confidence_level': 'low',
                'mastery_achieved': False
            }
        
        try:
            # Prepare comprehensive context
            knowledge_context = self._prepare_knowledge_graph_context(self.current_subtopic_id)
            attempt_history = self._prepare_detailed_attempt_history(current_state)
            concept_coverage = self._analyze_concept_coverage(self.current_subtopic_id, current_state)
        except Exception as e:
            print(f"Error preparing context for LLM: {e}")
            import traceback
            traceback.print_exc()
            
            simple_prob = current_state.correct_attempts / max(current_state.total_attempts, 1) * 0.8
            return {
                'mastery_probability': simple_prob,
                'feedback': f'Error preparing assessment context. Using basic calculation. Continue practicing.',
                'confidence_level': 'low',
                'mastery_achieved': False
            }
        
        try:
            # Invoke the assessment chain using LangChain
            assessment = self.assessment_chain.invoke({
                "topic_name": self.get_current_subtopic().get('subtopic_name', 'SQL'),
                "knowledge_context": knowledge_context,
                "attempt_history": attempt_history,
                "concept_coverage": concept_coverage,
                "total_attempts": current_state.total_attempts,
                "correct_attempts": current_state.correct_attempts,
                "accuracy_pct": (current_state.correct_attempts / current_state.total_attempts * 100)
            })
            
            # Update mastery state based on assessment
            current_state.mastery_probability = assessment['mastery_probability']
            
            assessment['mastery_achieved'] = (
                current_state.mastery_probability >= self.mastery_threshold
            )
            
            # Store per-problem assessment
            if current_state.attempts_history:
                last_attempt = current_state.attempts_history[-1]
                problem_assessment = {
                    'problem_id': last_attempt.question_id,
                    'subtopic_id': self.current_subtopic_id,
                    'subtopic_name': self.get_current_subtopic()['subtopic_name'],
                    'mastery_probability': assessment['mastery_probability'],
                    'feedback': assessment.get('feedback', ''),
                    'confidence_level': assessment.get('confidence_level', 'medium'),
                    'mastery_achieved': assessment['mastery_achieved'],
                    'timestamp': last_attempt.timestamp
                }
                self.problem_assessments.append(problem_assessment)
                self._save_user_progress()
            
            return assessment
            
        except Exception as e:
            print(f"Error in LLM assessment: {e}")
            import traceback
            traceback.print_exc()
            
            simple_prob = current_state.correct_attempts / current_state.total_attempts if current_state.total_attempts > 0 else 0
            return {
                'mastery_probability': simple_prob * 0.8,
                'feedback': 'System assessment temporarily unavailable. Continue practicing.',
                'confidence_level': 'low',
                'mastery_achieved': False
            }
    
    def _prepare_knowledge_graph_context(self, subtopic_id: str) -> str:
        """Prepare knowledge graph context for specific subtopic"""
        lines = []
        
        if 'topics' in self.knowledge_graph:
            for topic in self.knowledge_graph['topics']:
                if 'subtopics' in topic:
                    for subtopic in topic['subtopics']:
                        if subtopic.get('subtopic_id') == subtopic_id:
                            lines.append(f"Subtopic: {subtopic.get('subtopic_name')}")
                            lines.append(f"Description: {subtopic.get('description', 'N/A')}")
                            lines.append("")
                            
                            for cluster in subtopic.get('clusters', []):
                                lines.append(f"  Cluster: {cluster.get('name')}")
                                lines.append(f"  Description: {cluster.get('description', 'N/A')}")
                                lines.append(f"  Concepts:")
                                for concept in cluster.get('concepts', []):
                                    lines.append(f"    - {concept}")
                                lines.append("")
        
        return "\n".join(lines)
    
    def _prepare_detailed_attempt_history(self, state: SubtopicMasteryState) -> str:
        """Prepare detailed attempt history for LLM"""
        lines = []
        
        for i, attempt in enumerate(state.attempts_history, 1):
            result_emoji = "✓" if attempt.is_correct else "✗"
            result_text = "CORRECT" if attempt.is_correct else "INCORRECT"
            
            lines.append(f"Attempt #{i} [{result_emoji} {result_text}]")
            lines.append(f"  Difficulty: {attempt.difficulty}")
            lines.append(f"  Concepts Tested: {', '.join(attempt.concepts_tested)}")
            lines.append(f"  Question: {attempt.question_text}")
            lines.append(f"  Student's Answer: '{attempt.user_answer}'")
            lines.append(f"  Correct Answer: '{attempt.correct_answer}'")
            if attempt.explanation:
                lines.append(f"  Explanation: {attempt.explanation}")
            lines.append(f"  Timestamp: {attempt.timestamp}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _analyze_concept_coverage(self, subtopic_id: str, state: SubtopicMasteryState) -> str:
        """Analyze which concepts have been covered for specific subtopic"""
        all_concepts = set(self._get_subtopic_concepts(subtopic_id))
        covered_concepts = state.concepts_encountered
        uncovered_concepts = all_concepts - covered_concepts
        
        lines = []
        lines.append(f"Total Concepts in Subtopic: {len(all_concepts)}")
        
        if len(all_concepts) > 0:
            coverage_pct = (len(covered_concepts) / len(all_concepts)) * 100
            lines.append(f"Concepts Encountered: {len(covered_concepts)} ({coverage_pct:.1f}% coverage)")
        else:
            lines.append(f"Concepts Encountered: {len(covered_concepts)} (N/A - no concepts in knowledge graph)")
        
        lines.append(f"Concepts Not Yet Encountered: {len(uncovered_concepts)}")
        lines.append("")
        
        if covered_concepts:
            lines.append("Covered Concepts:")
            for concept in sorted(covered_concepts):
                correct = sum(1 for a in state.attempts_history 
                            if concept in a.concepts_tested and a.is_correct)
                total = sum(1 for a in state.attempts_history 
                           if concept in a.concepts_tested)
                
                if total > 0:
                    lines.append(f"  - {concept}: {correct}/{total} correct")
                else:
                    lines.append(f"  - {concept}: No attempts yet")
            lines.append("")
        
        if uncovered_concepts:
            lines.append("Uncovered Concepts:")
            for concept in sorted(uncovered_concepts):
                lines.append(f"  - {concept}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _save_user_progress(self):
        """Save user progress to JSON file"""
        # Convert subtopic states to serializable format
        subtopic_progress = {}
        for subtopic_id, state in self.subtopic_mastery_states.items():
            subtopic_progress[subtopic_id] = {
                'subtopic_name': state.subtopic_name,
                'mastery_probability': state.mastery_probability,
                'mastery_achieved': state.mastery_achieved,
                'total_attempts': state.total_attempts,
                'correct_attempts': state.correct_attempts,
                'completed_at': state.completed_at
            }
        
        progress_data = {
            'user_id': self.user_id,
            'current_subtopic': self.get_current_subtopic()['subtopic_name'] if self.get_current_subtopic() else 'Completed',
            'current_subtopic_id': self.current_subtopic_id,
            'subtopics_completed': sum(1 for s in self.subtopic_mastery_states.values() if s.mastery_achieved),
            'total_subtopics': len(self.subtopic_sequence),
            'overall_progress': (sum(1 for s in self.subtopic_mastery_states.values() if s.mastery_achieved) / len(self.subtopic_sequence) * 100) if self.subtopic_sequence else 0,
            'last_updated': datetime.now().isoformat(),
            'subtopic_progress': subtopic_progress,
            'problem_assessments': self.problem_assessments
        }
        
        with open(self.user_progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
    
    def get_mastery_report(self) -> Dict:
        """Generate comprehensive mastery report"""

        print("INSIDE GET MASTERY REPORT")
        current_subtopic = self.get_current_subtopic()
        
        if not current_subtopic:
            return {
                'status': 'All subtopics completed',
                'subtopic_progress': {
                    subtopic_id: {
                        'subtopic_name': state.subtopic_name,
                        'mastery_probability': state.mastery_probability,
                        'mastery_achieved': state.mastery_achieved,
                        'total_attempts': state.total_attempts,
                        'correct_attempts': state.correct_attempts,
                        'accuracy': state.correct_attempts / state.total_attempts if state.total_attempts > 0 else 0
                    }
                    for subtopic_id, state in self.subtopic_mastery_states.items()
                }
            }
        
        current_state = self.subtopic_mastery_states[self.current_subtopic_id]
        all_concepts = self._get_subtopic_concepts(self.current_subtopic_id)
        
        report = {
            'current_subtopic': current_subtopic['subtopic_name'],
            'current_subtopic_id': self.current_subtopic_id,
            'total_attempts': current_state.total_attempts,
            'correct_attempts': current_state.correct_attempts,
            'accuracy': current_state.correct_attempts / current_state.total_attempts if current_state.total_attempts > 0 else 0,
            'mastery_probability': current_state.mastery_probability,
            'mastery_threshold': self.mastery_threshold,
            'mastery_achieved': current_state.mastery_achieved,
            'concept_coverage': {
                'total_concepts': len(all_concepts),
                'concepts_encountered': len(current_state.concepts_encountered),
                'coverage_percentage': len(current_state.concepts_encountered) / len(all_concepts) * 100 if all_concepts else 0
            },
            'subtopics_completed': sum(1 for s in self.subtopic_mastery_states.values() if s.mastery_achieved),
            'total_subtopics': len(self.subtopic_sequence)
        }
        
        return report
    
    def print_status(self):
        """Print current mastery status"""
        current_subtopic = self.get_current_subtopic()
        
        if not current_subtopic:
            print("\n" + "="*70)
            print("🏆 ALL SUBTOPICS COMPLETED!")
            print("="*70)
            return
        
        current_state = self.subtopic_mastery_states[self.current_subtopic_id]
        all_concepts = self._get_subtopic_concepts(self.current_subtopic_id)
        
        if len(all_concepts) > 0:
            coverage_pct = len(current_state.concepts_encountered) / len(all_concepts) * 100
        else:
            coverage_pct = 0.0
        
        print("\n" + "="*70)
        print("MASTERY STATUS")
        print("="*70)
        print(f"Current Subtopic: {current_subtopic['subtopic_name']}")
        print(f"Progress: Subtopic {self.current_subtopic_index + 1}/{len(self.subtopic_sequence)}")
        print(f"Questions Attempted: {current_state.total_attempts}")
        print(f"Correct Answers: {current_state.correct_attempts}/{current_state.total_attempts}")
        print(f"Accuracy: {(current_state.correct_attempts/current_state.total_attempts*100):.1f}%" if current_state.total_attempts > 0 else "Accuracy: N/A")
        print(f"Concept Coverage: {len(current_state.concepts_encountered)}/{len(all_concepts)} ({coverage_pct:.1f}%)")
        print(f"Mastery Probability: {current_state.mastery_probability:.1%}")
        print(f"Mastery Threshold: {self.mastery_threshold:.1%}")
        print(f"Status: {'✓ MASTERED' if current_state.mastery_probability >= self.mastery_threshold else '⏳ In Progress'}")
        print("="*70 + "\n")








# ============================================================================
# INTERACTIVE LEARNING SESSION
# ============================================================================

def run_learning_session():
    """Run an interactive learning session with progressive subtopic mastery"""
    print("\n🎓 Welcome to the Knowledge Graph-Based SQL Mastery Agent!")
    print("This adaptive system uses your complete learning history to assess mastery.\n")
    print("Powered by LangChain + OpenAI GPT-4o-mini\n")
    
    # Ask for user ID
    user_id = input("Please enter your User ID (or press Enter for auto-generated ID): ").strip()
    
    if not user_id:
        user_id = f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"Generated User ID: {user_id}")
    else:
        print(f"User ID: {user_id}")
    
    print()
    
    # Initialize agent with user ID
    agent = KnowledgeGraphMasteryAgent(user_id=user_id)
    
    if not agent.problems:
        print("⚠️  No problems loaded. Please ensure problems.json exists.")
        return
    
    if not agent.knowledge_graph:
        print("⚠️  No knowledge graph loaded. Please ensure knowledge_graph.json exists.")
        return
    
    if not agent.subtopic_sequence:
        print("⚠️  No subtopics found in knowledge graph.")
        return
    
    print(f"📚 Loaded {len(agent.problems)} questions")
    print(f"🗺️  Knowledge Graph: {len(agent.subtopic_sequence)} subtopics")
    print(f"🎯 Mastery threshold: {agent.mastery_threshold:.0%}\n")
    
    # Display subtopic progression
    print("📖 Subtopic Progression:")
    for i, subtopic in enumerate(agent.subtopic_sequence, 1):
        print(f"   {i}. {subtopic['subtopic_name']}")
    print()
    
    # Learning loop
    while True:
        current_subtopic = agent.get_current_subtopic()
        
        if not current_subtopic:
            print("\n🏆 CONGRATULATIONS! You've completed all subtopics!")
            break
        
        question = agent.get_next_question()
        
        if question is None:
            # No more questions for current subtopic, check mastery
            print(f"\n📝 All questions completed for {current_subtopic['subtopic_name']}")
            assessment = agent.assess_mastery_with_llm()
            
            if assessment.get('mastery_achieved'):
                agent.advance_to_next_subtopic()
            else:
                print(f"\n⚠️  Mastery not yet achieved ({assessment.get('mastery_probability', 0):.1%})")
                print("   You need to review this subtopic or wait for more questions.")
                break
            
            continue
        
        # Display question
        current_state = agent.subtopic_mastery_states[agent.current_subtopic_id]
        print("\n" + "-"*70)
        print(f"Subtopic: {current_subtopic['subtopic_name']} (Question {current_state.total_attempts + 1})")
        print(f"Difficulty: {question.get('difficulty', 'N/A')}")
        print(f"Cluster: {question.get('cluster', 'N/A')}")
        if 'concepts' in question:
            print(f"Concepts: {', '.join(question['concepts'])}")
        print("-"*70)
        desc = question.get('description', 'No question text')\
            .replace('<br>', '\n').replace('<b>', '').replace('</b>', '')\
            .replace('<ul>', '').replace('</ul>', '').replace('<li>', '- ').replace('</li>', '')
        print(f"\n{desc}\n")
        
        # Get user answer
        user_answer = input("Your answer: ").strip()
        
        if user_answer.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Session ended by user.")
            break
        
        # Grade the answer using LangChain
        print("\n🤖 Grading your answer...")
        grading_result = agent._grade_sql_answer(question, user_answer)
        
        # Record attempt with evaluation result
        agent.record_attempt(question, user_answer, "", evaluation=grading_result)
        
        # Provide immediate feedback
        is_correct = grading_result.get('is_correct', False)
        if is_correct:
            print("\n✅ Correct!")
        else:
            print("\n❌ Incorrect")
        
        print(f"📝 Feedback: {grading_result.get('feedback', 'N/A')}")
        print(f"💡 Explanation: {grading_result.get('explanation', 'N/A')}")
        
        if question.get('brief_summary'):
            print(f"\n📊 Concept Summary: {question['brief_summary']}")
        
        # Assess mastery after EVERY question
        print("\n🤖 Calculating mastery probability...")
        assessment = agent.assess_mastery_with_llm()
        
        # Display quick mastery score update
        print(f"\n📈 Current Mastery Probability: {assessment.get('mastery_probability', 0.0):.1%}")
        print(f"   Threshold for Mastery: {agent.mastery_threshold:.0%}")
        print(f"   Status: {'✅ MASTERED' if assessment.get('mastery_achieved', False) else '⏳ In Progress'}")
        
        # Detailed assessment periodically
        should_show_detailed = (
            current_state.total_attempts % 3 == 0 or
            assessment.get('mastery_achieved', False)
        )
        
        if should_show_detailed:
            print("\n" + "="*70)
            print("DETAILED MASTERY ASSESSMENT")
            print("="*70)
            
            agent.print_status()
            
            print("💭 AI Mastery Assessment:")
            print(f"   Confidence: {assessment.get('confidence_level', 'N/A')}")
            print(f"   Feedback: {assessment.get('feedback', 'N/A')}")
            print("="*70)
        
        # Check for mastery achievement and advance
        if assessment.get('mastery_achieved'):
            print(f"\n🎉 CONGRATULATIONS! You've achieved mastery of {current_subtopic['subtopic_name']}!")
            print(f"   Final Probability: {current_state.mastery_probability:.1%}")
            
            has_next = agent.advance_to_next_subtopic()
            
            if not has_next:
                break
            
            # Show next subtopic info
            next_subtopic = agent.get_current_subtopic()
            if next_subtopic:
                print(f"\n📚 Starting: {next_subtopic['subtopic_name']}")
                print(f"   Description: {next_subtopic.get('description', 'N/A')}")
                input("\nPress Enter to continue to next subtopic...")
        
        # Continue prompt
        else:
            continue_input = input("\nPress Enter for next question (or 'q' to quit): ").strip().lower()
            if continue_input == 'q':
                break
    
    # Final comprehensive report
    print("\n" + "="*70)
    print("FINAL MASTERY REPORT")
    print("="*70)
    report = agent.get_mastery_report()
    print(json.dumps(report, indent=2, default=str))
    
    print(f"\n📄 User progress saved to: {agent.user_progress_file}")
    print(f"\n📊 Problem-by-Problem Assessment:")
    print("-" * 70)
    for assessment in agent.problem_assessments:
        print(f"Problem ID: {assessment['problem_id']}")
        print(f"  Subtopic: {assessment['subtopic_name']}")
        print(f"  Mastery Probability: {assessment['mastery_probability']:.1%}")
        print(f"  Confidence: {assessment['confidence_level']}")
        print(f"  Feedback: {assessment['feedback']}")
        print(f"  Mastery Achieved: {'✅' if assessment['mastery_achieved'] else '❌'}")
        print("-" * 70)
    
    # Display subtopic completion summary
    print("\n" + "="*70)
    print("SUBTOPIC COMPLETION SUMMARY")
    print("="*70)
    for subtopic_id, state in agent.subtopic_mastery_states.items():
        status_emoji = "✅" if state.mastery_achieved else "⏳"
        print(f"{status_emoji} {state.subtopic_name}")
        print(f"   Mastery: {state.mastery_probability:.1%}")
        print(f"   Attempts: {state.correct_attempts}/{state.total_attempts}")
        if state.completed_at:
            print(f"   Completed: {state.completed_at}")
        print()
    print("="*70)


if __name__ == "__main__":
    run_learning_session()