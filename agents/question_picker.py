"""Question Picker Agent."""
""" Picks a question from the knowledge graph and student profile."""

import json
from typing import Dict, Any
import random
from config import config_manager
from storage.tutor_state import TutorState


class QuestionPickerAgent:
    """Agent to pick questions from the knowledge graph based on student profile."""
    
    def __init__(self, knowledge_graph_path: str = "knowledge_graph.json", problems_path: str = "problems.json", tutor_state: TutorState = None, student_agent=None):
        self.knowledge_graph_path = knowledge_graph_path
        self.knowledge_graph = self._load_knowledge_graph()
        self.problems_path = problems_path
        self.problems = self._load_problems()
        self.tutor_state = tutor_state or {}
        self.mastery_threshold = 0.80  # 80% mastery required to move to next subtopic
        self.current_subtopic = None  # Track current subtopic being practiced
        self.asked_problems = set()  # Track problems already asked in current subtopic
        self.student_agent = student_agent  # Reference to student profile agent for mastery reset


    ############ Load Knowledge Graph and Problems ############

    def _load_knowledge_graph(self) -> Dict[str, Any]:
        """Load the knowledge graph from JSON file."""
        with open(self.knowledge_graph_path, 'r') as f:
            return json.load(f)
    
    def _load_problems(self) -> list:
        """Load the problems from JSON file."""
        with open(self.problems_path, 'r') as f:
            return json.load(f)
    
    def _get_problems_for_cluster(self, cluster_id: str) -> list:
        """Get list of problems for a given cluster_id."""
        return [p for p in self.problems if p.get("cluster_id") == cluster_id]
    

    ################## Picking Initial Question ##################

    def generate_initial_question(self) -> Dict[str, Any]:
        """ Generate initial question for a new student."""
        initial_difficulty = config_manager.config.default_difficulty.lower()
        # Map difficulty to complexity level: easy -> 1, medium -> 2, hard -> 3 (adjust as needed)
        difficulty_map = {"easy": 1, "medium": 2, "hard": 4}
        target_complexity = difficulty_map.get(initial_difficulty, 1)  # default to 1
        
        user_topic = self.tutor_state.get("topic", "")
        print('generating initial question for topic:', user_topic)
        if not user_topic:
            return {"message": "No topic specified", "completed": True}
        # Find clusters matching the topic and target complexity
        matching_clusters = []
        for topic_item in self.knowledge_graph.get("topics", []):
            for subtopic in topic_item.get("subtopics", []):
                if subtopic.get("subtopic_name").lower() == user_topic.lower():
                    for cluster in subtopic.get("clusters", []):
                        if cluster.get("complexity_level") == target_complexity:
                            cluster_info = {
                                "cluster_id": cluster.get("cluster_id"),
                                "cluster_name": cluster.get("cluster_name"),
                                "description": cluster.get("description"),
                                "complexity_level": cluster.get("complexity_level"),
                                "learning_objective": cluster.get("learning_objective"),
                                "skills_tested": cluster.get("skills_tested", []),
                                "subtopic_name": subtopic.get("subtopic_name"),
                                "topic_name": topic_item.get("topic_name")
                            }
                            matching_clusters.append(cluster_info)
        
        if not matching_clusters:
            return {"message": f"No clusters found for topic '{user_topic}' at difficulty '{initial_difficulty}'", "completed": True}
        
        # Randomly select a cluster
        selected_cluster = random.choice(matching_clusters)
        
        # Get problems for the selected cluster
        problems = self._get_problems_for_cluster(selected_cluster["cluster_id"])
        if not problems:
            return {"message": f"No problems available for cluster '{selected_cluster['cluster_id']}'", "completed": True}
        
        # Randomly select a problem
        selected_problem = random.choice(problems)
        question = selected_problem.get("description", "No description available")
        
        return {
            "cluster_info": selected_cluster,
            "question": question,
            "problem_id": selected_problem.get("problem_id"),
            "completed": False
        }

    
    def get_next_question(self, student_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pick the next appropriate question based on student profile and mastery scores.
        
        Logic:
        1. Identify weak topics from user's answer history
        2. Pick questions that cover the most concepts for weak topics
        3. Progression is concept-wise (not difficulty-wise)
        4. Check if current subtopic has achieved mastery (>= 0.80)
        5. If not mastered, keep giving questions from same subtopic
        6. If mastered, progress to next subtopic
        """
        user_topic = self.tutor_state.get("topic", "")
        mastery_scores = student_profile.get("mastery_scores", {})
        
        # Get mastery tracking info
        mastery_tracking = mastery_scores if isinstance(mastery_scores, dict) and "subtopics" in mastery_scores else {"subtopics": {}, "overall_mastery": 0.0}
        subtopic_mastery = mastery_tracking.get("subtopics", {})
        
        # Get weak concepts from student profile
        weak_concepts = student_profile.get("weak_concepts", {})
        concept_gaps = student_profile.get("concept_gaps", [])
        priority_concepts = self._extract_priority_concepts(weak_concepts, concept_gaps)
        
        # Initialize current subtopic if not set
        if self.current_subtopic is None:
            self.current_subtopic = user_topic
            self.asked_problems = set()
        
        # Check if current subtopic has achieved mastery (case-insensitive lookup)
        current_subtopic_data = {}
        for subtopic_key, subtopic_value in subtopic_mastery.items():
            if subtopic_key.lower() == self.current_subtopic.lower():
                current_subtopic_data = subtopic_value
                break
        
        current_mastery_score = current_subtopic_data.get("mastery_score", 0.0)
        mastery_achieved = current_subtopic_data.get("mastery_achieved", False)
        attempts = current_subtopic_data.get("attempts", 0)
        
        print(f"\n📊 Mastery Check: {self.current_subtopic}")
        print(f"   Current Score: {current_mastery_score:.1%}")
        print(f"   Attempts: {attempts}")
        print(f"   Threshold: {self.mastery_threshold:.1%}")
        print(f"   Mastery Achieved: {mastery_achieved}")
        
        # If mastery achieved (requires >= 80% score AND >= 3 attempts), try to find next subtopic
        if mastery_achieved and attempts >= 3:
            print(f"   ✅ Mastery achieved! Looking for next subtopic...")
            next_subtopic = self._get_next_subtopic(user_topic, subtopic_mastery)
            
            if next_subtopic:
                # Reset mastery score for the new subtopic
                if self.student_agent:
                    self.student_agent.reset_subtopic_mastery(next_subtopic)
                    print(f"   🔄 Reset mastery score to 0 for: {next_subtopic}")
                
                self.current_subtopic = next_subtopic
                self.asked_problems = set()
                print(f"   📚 Moving to: {next_subtopic}")
            else:
                print(f"   🏆 All subtopics mastered!")
                return {"message": "Congratulations! You've mastered all subtopics! 🎉", "completed": True}
        elif attempts < 3:
            print(f"   ⏳ Continue practicing {self.current_subtopic} (need {3 - attempts} more attempts)")
        else:
            print(f"   ⏳ Continue practicing {self.current_subtopic}")
        
        # Find available clusters for current subtopic
        available_clusters = self._get_clusters_for_subtopic(self.current_subtopic)
        
        if not available_clusters:
            return {"message": f"No clusters found for subtopic '{self.current_subtopic}'", "completed": True}
        
        # Select cluster based on concept coverage for weak areas (concept-wise, not difficulty-wise)
        selected_cluster = self._select_cluster_by_concept_coverage(
            available_clusters, 
            current_mastery_score, 
            priority_concepts
        )
        
        # Get problems for the selected cluster (excluding already asked ones)
        problems = self._get_problems_for_cluster(selected_cluster["cluster_id"])
        available_problems = [p for p in problems if p.get("problem_id") not in self.asked_problems]
        
        # If all problems asked in this cluster, reset and allow repeats
        if not available_problems:
            print(f"   🔄 All problems in cluster used, allowing repeats...")
            available_problems = problems
            # Optionally reset asked_problems for this cluster
        
        if not available_problems:
            return {"message": f"No problems available for cluster '{selected_cluster['cluster_id']}'", "completed": True}
        
        # Select problem that covers the most concepts related to weak areas
        selected_problem = self._select_problem_by_concept_richness(
            available_problems,
            priority_concepts,
            selected_cluster
        )
        self.asked_problems.add(selected_problem.get("problem_id"))
        
        question = selected_problem.get("description", "No description available")
        
        print(f"   📝 Selected: {selected_cluster['cluster_name']} (Complexity: {selected_cluster['complexity_level']})")
        
        return {
            "cluster_info": selected_cluster,
            "question": question,
            "problem_id": selected_problem.get("problem_id"),
            "completed": False
        }
    
    def _get_clusters_for_subtopic(self, subtopic_name: str) -> list:
        """Get all clusters for a given subtopic."""
        clusters = []
        for topic in self.knowledge_graph.get("topics", []):
            for subtopic in topic.get("subtopics", []):
                if subtopic.get("subtopic_name").lower() == subtopic_name.lower():
                    for cluster in subtopic.get("clusters", []):
                        cluster_info = {
                            "cluster_id": cluster.get("cluster_id"),
                            "cluster_name": cluster.get("cluster_name"),
                            "description": cluster.get("description"),
                            "complexity_level": cluster.get("complexity_level"),
                            "learning_objective": cluster.get("learning_objective"),
                            "skills_tested": cluster.get("skills_tested", []),
                            "subtopic_name": subtopic.get("subtopic_name"),
                            "topic_name": topic.get("topic_name")
                        }
                        clusters.append(cluster_info)
        return clusters
    
    def _select_cluster_by_mastery(self, clusters: list, mastery_score: float) -> Dict[str, Any]:
        """
        Select cluster based on mastery score.
        Lower mastery -> start with lower complexity
        Higher mastery -> progress to higher complexity
        """
        if not clusters:
            return None
        
        # Sort clusters by complexity level
        sorted_clusters = sorted(clusters, key=lambda x: x.get("complexity_level", 1))
        
        # Select complexity based on mastery
        if mastery_score < 0.40:
            # Struggling - focus on easiest clusters (complexity 1-2)
            target_clusters = [c for c in sorted_clusters if c.get("complexity_level", 1) <= 2]
        elif mastery_score < 0.60:
            # Developing - medium clusters (complexity 2-3)
            target_clusters = [c for c in sorted_clusters if 2 <= c.get("complexity_level", 1) <= 3]
        elif mastery_score < 0.80:
            # Good progress - medium to hard (complexity 3-4)
            target_clusters = [c for c in sorted_clusters if 3 <= c.get("complexity_level", 1) <= 4]
        else:
            # Almost mastered - hardest clusters (complexity 4-5)
            target_clusters = [c for c in sorted_clusters if c.get("complexity_level", 1) >= 4]
        
        # If no clusters match criteria, use all available
        if not target_clusters:
            target_clusters = sorted_clusters
        
        # Randomly select from appropriate complexity level
        return random.choice(target_clusters)
    
    def _get_next_subtopic(self, current_topic: str, subtopic_mastery: Dict[str, Any]) -> str:
        """
        Find the next subtopic to practice after mastering current one.
        Returns None if all subtopics are mastered.
        """
        # Get all subtopics for the current topic area
        all_subtopics = []
        for topic in self.knowledge_graph.get("topics", []):
            for subtopic in topic.get("subtopics", []):
                # Check if related to current topic area (flexible matching)
                subtopic_name = subtopic.get("subtopic_name", "")
                all_subtopics.append(subtopic_name)
        
        # Find unmastered subtopics
        unmastered = []
        for subtopic_name in all_subtopics:
            subtopic_data = subtopic_mastery.get(subtopic_name, {})
            is_mastered = subtopic_data.get("mastery_achieved", False)
            mastery_score = subtopic_data.get("mastery_score", 0.0)
            
            if not is_mastered and mastery_score < self.mastery_threshold:
                unmastered.append(subtopic_name)
        
        # Return first unmastered subtopic, or None if all mastered
        return unmastered[0] if unmastered else None
    
    def _extract_priority_concepts(self, weak_concepts: Dict[str, Any], concept_gaps: list) -> list:
        """Extract priority concepts from weak concepts and gaps."""
        priority = []
        
        # Add most frequently weak concepts (top 3)
        ranked_weak = sorted(
            weak_concepts.items(),
            key=lambda x: x[1].get("occurrences", 0) if isinstance(x[1], dict) else 0,
            reverse=True
        )
        priority.extend([concept for concept, _ in ranked_weak[:3]])
        
        # Add concept gaps
        priority.extend(concept_gaps[:3])
        
        return list(set(priority))  # Remove duplicates
    
    def _select_cluster_by_concept_coverage(self, clusters: list, mastery_score: float, priority_concepts: list) -> Dict[str, Any]:
        """
        Select cluster based on concept coverage for weak areas.
        Prioritizes clusters that cover the most weak concepts (concept-wise progression).
        Falls back to mastery-based selection if no weak concepts identified.
        """
        if not clusters:
            return None
        
        # If we have priority concepts, select cluster with best coverage
        if priority_concepts:
            cluster_scores = []
            for cluster in clusters:
                skills_tested = cluster.get("skills_tested", [])
                # Count how many weak concepts this cluster addresses
                coverage_score = sum(1 for concept in priority_concepts 
                                   if any(concept.lower() in skill.lower() or skill.lower() in concept.lower() 
                                         for skill in skills_tested))
                cluster_scores.append((cluster, coverage_score, len(skills_tested)))
            
            # Sort by coverage score (descending), then by total concepts (descending)
            cluster_scores.sort(key=lambda x: (x[1], x[2]), reverse=True)
            
            # If best cluster has good coverage, return it
            if cluster_scores[0][1] > 0:
                print(f"   🎯 Selected cluster covering {cluster_scores[0][1]} weak concepts")
                return cluster_scores[0][0]
        
        # Fallback to original mastery-based selection
        return self._select_cluster_by_mastery(clusters, mastery_score)
    
    def _select_problem_by_concept_richness(self, problems: list, priority_concepts: list, cluster: Dict[str, Any]) -> Dict[str, Any]:
        """
        Select problem that covers the most concepts, especially weak concepts.
        Prioritizes concept richness over difficulty.
        """
        if not problems:
            return None
        
        if not priority_concepts:
            # No weak concepts identified, select randomly
            return random.choice(problems)
        
        # Score each problem by concept relevance
        problem_scores = []
        cluster_skills = cluster.get("skills_tested", [])
        
        for problem in problems:
            # Get problem's concept coverage from brief_summary or skills
            brief_summary = problem.get("brief_summary", "").lower()
            
            # Score based on:
            # 1. How many weak concepts are mentioned/tested
            # 2. How comprehensive the problem is
            weak_concept_coverage = sum(1 for concept in priority_concepts 
                                       if concept.lower() in brief_summary)
            cluster_skill_coverage = sum(1 for skill in cluster_skills 
                                        if skill.lower() in brief_summary)
            
            total_score = weak_concept_coverage * 3 + cluster_skill_coverage  # Weight weak concepts higher
            problem_scores.append((problem, total_score))
        
        # Sort by score (descending)
        problem_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Select from top 3 problems randomly to add some variety
        top_problems = [p for p, _ in problem_scores[:3]]
        selected = random.choice(top_problems) if top_problems else problems[0]
        
        print(f"   📚 Selected concept-rich problem covering multiple weak areas")
        return selected

