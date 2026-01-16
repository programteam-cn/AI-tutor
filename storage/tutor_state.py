from typing import TypedDict, List, Annotated, Literal, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from config import config_manager

class TutorState(TypedDict):
    user_id: Annotated[Optional[str], "Unique identifier for the user"]
    topic: Annotated[Optional[str], "Topic selected by the user"]
    question_difficulty: Annotated[Literal["easy", "medium", "hard"], "Difficulty level of questions"]
    question_count: Annotated[int, "Number of questions asked in the session"]
    previous_questions: Annotated[List[BaseMessage], "List of previously asked questions"]
    history : Annotated[List[BaseMessage], "Conversation history between the tutor and the student"]
    