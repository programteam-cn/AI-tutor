"""Question Picker Agent."""
""" Picks a question from the knowledge graph and student profile."""

import json
from typing import Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from config import llm, config_manager
import random
from storage.tutor_state import TutorState
load_dotenv()

llm = ChatOpenAI(
    model_name=llm["model_name"],
    temperature=llm["temperature"],
    max_tokens=llm["max_tokens"],
)


class QuestionPickerAgent:
    """Agent to pick questions from the knowledge graph based on student profile."""
    
    def __init__(self, knowledge_graph_path: str = "knowledge_graph.json", tutor_state: TutorState = None):
        self.llm = llm
        self.knowledge_graph_path = knowledge_graph_path
        self.knowledge_graph = self._load_knowledge_graph()
        self.tutor_state = tutor_state or {}

    def _load_knowledge_graph(self) -> Dict[str, Any]:
        """Load the knowledge graph from JSON file."""
        with open(self.knowledge_graph_path, 'r') as f:
            return json.load(f)
    
    def generate_initial_question(self) -> Dict[str, Any]:
        """ Generate initial question for a new student."""
        initial_difficulty = config_manager.config.default_difficulty
        user_topic = self.tutor_state.get("topic", "")
        print('generating initial question for topic:', user_topic)
        if not user_topic:
            return {"message": "No topic specified", "completed": True}
        
        # Search through all topics and subtopics
        for topic_item in self.knowledge_graph.get("topics", []):
            for subtopic in topic_item.get("subtopics", []):
                # Match user input with subtopic name
                if subtopic.get("subtopic_name").lower() == user_topic.lower():
                    clusters = subtopic.get("clusters", [])
                    if clusters:
                        cluster = random.choice(clusters)
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
                        
                        prompt = f"""Based on the following learning objective, generate a SQL question:
        
                        Topic: {cluster_info['topic_name']}
                        Subtopic: {cluster_info['subtopic_name']}
                        Cluster: {cluster_info['cluster_name']}
                        Complexity Level: {cluster_info['complexity_level']}/5

                        Learning Objective: {cluster_info['learning_objective']}

                        Description: {cluster_info['description']}

                        Skills to test: {', '.join(cluster_info['skills_tested'])}

                        Generate a clear, practical SQL question that tests these skills. Make it concrete with example table names."""
        
                        question = self.llm.invoke(prompt).content
                        return {
                                "cluster_info": cluster_info,
                                "question": question,
                                "completed": False
                                }
        
        # If no matching subtopic found
        available_subtopics = []
        for topic_item in self.knowledge_graph.get("topics", []):
            for subtopic in topic_item.get("subtopics", []):
                available_subtopics.append(subtopic.get("subtopic_name"))
        
        return {
            "message": f"Subtopic '{user_topic}' not found. Available subtopics: {', '.join(available_subtopics)}", 
            "completed": True
        }


    def get_next_question(self, student_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Pick the next appropriate question based on student profile."""
        # completed_clusters = student_profile.get("completed_clusters", [])
        current_cluster = student_profile.get("current_cluster")
        user_topic = self.tutor_state.get("topic", "")

        # Find available clusters from the knowledge graph
        available_clusters = []
        for topic in self.knowledge_graph.get("topics", []):
            for subtopic in topic.get("subtopics", []):
                if subtopic.get("subtopic_name").lower() == user_topic.lower():
                    clusters = subtopic.get("clusters", [])
                    for cluster in subtopic.get("clusters", []):
                        cluster_id = cluster.get("cluster_id")
                        # if cluster_id not in completed_clusters:
                        cluster = random.choice(subtopic.get("clusters", []))
                        cluster_info = {
                            "cluster_id": cluster_id,
                            "cluster_name": cluster.get("cluster_name"),
                            "description": cluster.get("description"),
                            "complexity_level": cluster.get("complexity_level"),
                            "learning_objective": cluster.get("learning_objective"),
                            "skills_tested": cluster.get("skills_tested", []),
                            "subtopic_name": subtopic.get("subtopic_name"),
                            "topic_name": topic.get("topic_name")
                        }
                        available_clusters.append(cluster_info)
            
        if not available_clusters:
            return {"message": "All clusters completed! Great job!", "completed": True}
        
        # Select the next cluster (starting with lowest complexity)
        next_cluster = min(available_clusters, key=lambda x: x["complexity_level"])
        
        # Generate a question using LLM
        question = self._generate_question(next_cluster)
        
        return {
            "cluster_info": next_cluster,
            "question": question,
            "completed": False
        }
    
    def _generate_question(self, cluster_info: Dict[str, Any]) -> str:
        """Generate a question using LLM based on cluster information."""
        prompt = f"""Based on the following learning objective, generate a SQL question:
        
Topic: {cluster_info['topic_name']}
Subtopic: {cluster_info['subtopic_name']}
Cluster: {cluster_info['cluster_name']}
Complexity Level: {cluster_info['complexity_level']}/5

Learning Objective: {cluster_info['learning_objective']}

Description: {cluster_info['description']}

Skills to test: {', '.join(cluster_info['skills_tested'])}

Generate a clear, practical SQL question that tests these skills. Make it concrete with example table names."""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            # Fallback to a simple question if LLM fails
            return f"Write a SQL query to demonstrate: {cluster_info['learning_objective']}"


