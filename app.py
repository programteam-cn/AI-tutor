import streamlit as st
import sys
from pathlib import Path
from agents.student_profile import StudentProfileAgent
from agents.question_picker import QuestionPickerAgent
from agents.mastery_agent import KnowledgeGraphMasteryAgent
from config import config_manager
from storage.tutor_state import TutorState
st.set_page_config(page_title="AI Tutor", page_icon="📚")

##########################################################################
########################### Initializing state ###########################
##########################################################################

if 'tutor_state' not in st.session_state:
    st.session_state.tutor_state = {
        "user_id": None,
        "topic": None,
        "question_difficulty": config_manager.config.default_difficulty,
        "current_question": None,
        "question_count":0,
        "previous_questions": []
    }
if 'session_started' not in st.session_state:
    st.session_state.session_started = False

##########################################################################
########################### Main Application #############################
##########################################################################

# Title
st.title("📚 AI Tutoring System")

# User ID input section
if not st.session_state.session_started:
    st.markdown("### Welcome! Let's get started")
    
    # Create a form for user ID input
    with st.form("user_id_form"):
        user_id = st.text_input("Enter your User ID:", placeholder="e.g., student123")
        topic = "inner join"
        # topic = st.text_input("Enter Subtopic", placeholder="e.g., INNER JOIN, OUTER JOIN, CROSS JOIN, or SELF JOIN")
        submit_button = st.form_submit_button("Start Session")
    # Display welcome message after form submission
    if submit_button:
        if user_id and topic:
            st.session_state.tutor_state['user_id'] = user_id
            st.session_state.tutor_state['topic'] = topic
            st.session_state.session_started = True
            # Initialize agents
            st.session_state.student_agent = StudentProfileAgent(user_id, topic)
            st.session_state.question_agent = QuestionPickerAgent(
                tutor_state=st.session_state.tutor_state,
                student_agent=st.session_state.student_agent
            )
            st.session_state.mastery_agent = KnowledgeGraphMasteryAgent(
                problems_file="problems.json",
                knowledge_graph_file="knowledge_graph.json",
                user_id=user_id
            )
            
            # Generate initial question
            with st.spinner("Generating your first question..."):
                question_data = st.session_state.question_agent.generate_initial_question()
                st.session_state.tutor_state['current_question'] = question_data
            
            st.success(f"Welcome to the AI Tutoring Session, {user_id}! 🎓")
            st.rerun()
        else:
            st.error("Please enter a valid User ID")
else:
    # Display active session
    st.markdown(f"### Welcome back, **{st.session_state['tutor_state']['user_id']}**! 🎓")
    
    # Sidebar with student profile
    with st.sidebar:
        st.header("📊 Your Profile")
        profile = st.session_state.student_agent.get_profile()
        st.write(f"**User ID:** {profile['user_id']}")
        st.write(f"**Skill Level:** {profile['skill_level']}")
        st.write(f"**Questions Answered:** {st.session_state.tutor_state['question_count']}")
        
        st.markdown("---")
        st.subheader("📈 Current Performance")
        
        # Display category with color coding
        category = profile.get('category', 'medium')
        if category == 'fast':
            st.success(f"**Learning Pace:** 🚀 {category.upper()}")
        elif category == 'slow':
            st.warning(f"**Learning Pace:** 🐢 {category.upper()}")
        else:
            st.info(f"**Learning Pace:** 🚶 {category.upper()}")
        
        # Display reasoning
        reasoning = profile.get('reasoning', 'Initial assessment pending')
        st.write(f"**Assessment:** {reasoning}")
        
        # Display Mastery Information
        st.markdown("---")
        st.subheader("🎯 Mastery Tracking")
        
        # Display current subtopic being practiced
        current_subtopic = st.session_state.question_agent.current_subtopic
        if current_subtopic:
            st.write(f"**Current Subtopic:** {current_subtopic}")
        
        mastery_info = st.session_state.student_agent.get_mastery_info()
        overall_mastery = mastery_info.get("overall_mastery", 0.0)
        
        st.write(f"**Overall Mastery:** {overall_mastery:.1%}")
        st.progress(overall_mastery)
        
        # Show weak topics
        st.markdown("---")
        st.subheader("⚠️ Areas to Improve")
        
        # Show latest weak concepts from most recent answer
        history = st.session_state.student_agent.session_data.get("questions_history", [])
        if history:
            last_eval = history[-1].get("evaluation", {})
            latest_weak = last_eval.get("weak_concepts", [])
            latest_missing = last_eval.get("missing_concepts", [])
            
            if latest_weak or latest_missing:
                with st.expander("🆕 From Your Last Answer", expanded=True):
                    if latest_weak:
                        st.write("**Struggled With:**")
                        for concept in latest_weak[:5]:
                            st.write(f"🔴 {concept}")
                    if latest_missing:
                        st.write("**Should Have Used:**")
                        for concept in latest_missing[:5]:
                            st.write(f"🔵 {concept}")
        
        # Show accumulated weak topics (most frequent)
        weak_topics = st.session_state.student_agent.get_weak_topics()
        
        # Debug: Print what we're getting
        print(f"\n📋 Sidebar - Retrieved Weak Topics:")
        print(f"   Weak concepts count: {len(weak_topics.get('weak_concepts', {}))}")
        print(f"   Concept gaps count: {len(weak_topics.get('concept_gaps', []))}")
        
        weak_concepts = weak_topics.get("weak_concepts", {})
        if weak_concepts:
            st.write("**Most Frequent Weak Concepts:**")
            for concept, data in list(weak_concepts.items())[:5]:
                occurrences = data.get("occurrences", 0)
                st.write(f"🔴 {concept} (struggled {occurrences}x)")
                print(f"   Displaying: {concept} ({occurrences}x)")
        
        concept_gaps = weak_topics.get("concept_gaps", [])
        if concept_gaps:
            st.write("**All Missing Concepts:**")
            for concept in concept_gaps[:5]:
                st.write(f"🔵 {concept}")
                print(f"   Displaying gap: {concept}")
        
        if not weak_concepts and not concept_gaps:
            st.success("No weak areas identified yet!")
            print("   No weak areas to display")
        
        st.markdown("---")
        if st.button("End Session"):
            st.session_state.clear()
            st.rerun()
    
    # Main content area - Display question
    st.markdown("---")
    
    # Display current question
    if st.session_state.tutor_state.get('current_question'):
        question_data = st.session_state.tutor_state['current_question']
        
        if question_data.get("completed"):
            st.warning("⚠️ " + question_data.get("message", "No question available"))
        else:
            cluster_info = question_data.get("cluster_info", {})
            question = question_data.get("question", "")
            
            # Display question details
            st.markdown(f"### 📝 Question")
            
            with st.expander("ℹ️ Learning Context", expanded=False):
                st.write(f"**Topic:** {cluster_info.get('topic_name')}")
                st.write(f"**Subtopic:** {cluster_info.get('subtopic_name')}")
                st.write(f"**Cluster:** {cluster_info.get('cluster_name')}")
                st.write(f"**Complexity:** {cluster_info.get('complexity_level')}/5")
                st.write(f"**Learning Objective:** {cluster_info.get('learning_objective')}")
                st.write(f"**Skills Tested:** {', '.join(cluster_info.get('skills_tested', []))}")
                
                # Show if this question targets weak areas
                weak_topics = st.session_state.student_agent.get_weak_topics()
                priority_concepts = weak_topics.get("priority_concepts", [])
                if priority_concepts:
                    skills = cluster_info.get('skills_tested', [])
                    targeted_weak = [c for c in priority_concepts if any(c.lower() in s.lower() or s.lower() in c.lower() for s in skills)]
                    if targeted_weak:
                        st.success(f"🎯 This question targets your weak areas: {', '.join(targeted_weak)}")
            
            st.markdown("#### Question:")
            st.info(question)
            
            # Answer submission area
            st.markdown("#### Your Answer:")
            user_answer = st.text_area("Write your SQL query here:", height=150, key="answer_input")
            
            if st.button("Submit Answer", type="primary"):
                if user_answer:
                    with st.spinner("Processing your answer and generating next question..."):
                        # Classify student based on th
                        
                        classification = st.session_state.student_agent.classify_student(
                            question=question,
                            response=user_answer
                        )
                        
                        # Evaluate student Answer using mastery agent
                        # Prepare question dict for _grade_sql_answer
                        question_for_grading = {
                            'description': question,
                            'problem_id': question_data.get('problem_id'),
                            'cluster_info': cluster_info
                        }
                        evaluation = st.session_state.mastery_agent._grade_sql_answer(
                            question=question_for_grading,
                            user_answer=user_answer
                        )
                        
                        # Record the attempt in mastery agent
                        question_record = {
                            'problem_id': question_data.get('problem_id'),
                            'description': question,
                            'difficulty': cluster_info.get('complexity_level', 3),
                            'concepts': cluster_info.get('skills_tested', []),
                            'subtopic_id': st.session_state.mastery_agent.current_subtopic_id
                        }
                        
                        # Record attempt and assess mastery using mastery agent
                        st.session_state.mastery_agent.record_attempt(
                            question=question_record,
                            user_answer=user_answer,
                            correct_answer="",
                            evaluation=evaluation  # Pass evaluation result to determine correctness
                        )
                        
                        # Get mastery assessment from mastery agent
                        mastery_assessment = st.session_state.mastery_agent.assess_mastery_with_llm()
                        
                        # Add concept_mastery and subtopic_mastery for compatibility
                        if 'concept_mastery' not in mastery_assessment:
                            skills_tested = cluster_info.get('skills_tested', [])
                            accuracy = evaluation.get('score', 0) / 100.0
                            mastery_assessment['concept_mastery'] = {skill: accuracy for skill in skills_tested}
                        if 'subtopic_mastery' not in mastery_assessment:
                            mastery_assessment['subtopic_mastery'] = mastery_assessment.get('mastery_probability', 0.0)

                        # Save question data to user file with mastery assessment from mastery agent
                        st.session_state.student_agent.save_question_data(
                            question_data=question_data,
                            user_answer=user_answer,
                            classification=classification,
                            evaluation=evaluation,
                            mastery_assessment=mastery_assessment
                        )
                        
                        # Update tutor state
                        st.session_state.tutor_state['question_count'] += 1
                        st.session_state.tutor_state['previous_questions'].append({
                            'question': question_data,
                            'user_answer': user_answer,
                            'classification': classification,
                            'evaluation': evaluation
                        })
                        
                        # Print grading report to terminal for debugging
                        print("\n" + "="*70)
                        print("📊 GRADING REPORT")
                        print("="*70)
                        print(f"Problem ID: {question_data.get('problem_id')}")
                        print(f"Score: {evaluation['score']}/100")
                        print(f"Is Correct: {evaluation['is_correct']}")
                        print(f"\nFeedback: {evaluation['feedback']}")
                        print(f"\nExplanation: {evaluation.get('explanation', 'N/A')}")
                        
                        weak_concepts = evaluation.get('weak_concepts', [])
                        missing_concepts = evaluation.get('missing_concepts', [])
                        concept_understanding = evaluation.get('concept_understanding', {})
                        
                        if weak_concepts:
                            print(f"\nWeak Concepts: {', '.join(weak_concepts)}")
                        if missing_concepts:
                            print(f"Missing Concepts: {', '.join(missing_concepts)}")
                        if concept_understanding:
                            print(f"\nConcept Understanding:")
                            for concept, score in concept_understanding.items():
                                print(f"  - {concept}: {score:.0%}")
                        print("="*70 + "\n")
                        
                        # Display evaluation feedback in UI
                        if evaluation['is_correct']:
                             st.success(f"✅ Correct! Score: {evaluation['score']}/100")
                        else:
                             st.error(f"❌ Incorrect. Score: {evaluation['score']}/100")
                        
                        st.info(f"📝 **Feedback:** {evaluation['feedback']}")
                        
                        # Display detailed grading report
                        with st.expander("📊 Detailed Grading Report", expanded=True):
                            st.markdown(f"**Score:** {evaluation['score']}/100")
                            st.markdown(f"**Correctness:** {'✅ Correct' if evaluation['is_correct'] else '❌ Incorrect'}")
                            st.markdown(f"**Explanation:** {evaluation.get('explanation', 'N/A')}")
                            
                            # Show concept understanding scores
                            if concept_understanding:
                                st.markdown("**Concept Understanding:**")
                                for concept, score in concept_understanding.items():
                                    st.progress(score, text=f"{concept}: {score:.0%}")
                        
                        if weak_concepts or missing_concepts:
                            with st.expander("⚠️ Concepts Needing Work", expanded=True):
                                if weak_concepts:
                                    st.write("**Struggled With:**")
                                    for concept in weak_concepts:
                                        st.write(f"🔴 {concept}")
                                
                                if missing_concepts:
                                    st.write("**Should Have Used:**")
                                    for concept in missing_concepts:
                                        st.write(f"🔵 {concept}")
                                
                                st.info("💡 Your next questions will focus on these concepts!")
                        
                        # Get and display mastery assessment
                        mastery_info = st.session_state.student_agent.get_mastery_info()
                        
                        # Display mastery in an expander
                        with st.expander("🎯 Mastery Assessment", expanded=True):
                            overall_mastery = mastery_info.get("overall_mastery", 0.0)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Overall Mastery", f"{overall_mastery:.1%}")
                            
                            # Get last question's mastery assessment
                            history = st.session_state.student_agent.session_data.get("questions_history", [])
                            if history:
                                last_assessment = history[-1].get("mastery_assessment", {})
                                
                                with col2:
                                    mastery_achieved = last_assessment.get("mastery_achieved", False)
                                    status = "✅ Achieved" if mastery_achieved else "⏳ In Progress"
                                    st.metric("Mastery Status", status)
                                
                                st.write(f"**Confidence Level:** {last_assessment.get('confidence_level', 'N/A').title()}")
                                st.write(f"**AI Feedback:** {last_assessment.get('feedback', 'N/A')}")
                                
                                # Show concept mastery for this question
                                concept_mastery = last_assessment.get("concept_mastery", {})
                                if concept_mastery:
                                    st.write("**Concept Understanding:**")
                                    for concept, score in concept_mastery.items():
                                        st.write(f"• {concept}: {score:.0%}")
                        
                        # Get student profile and generate next question
                        profile = st.session_state.student_agent.get_profile()
                        next_question_data = st.session_state.question_agent.get_next_question(profile)
                        st.session_state.tutor_state['current_question'] = next_question_data
                        
                        st.success("Answer submitted! Moving to next question...")
                    st.rerun()
                else:
                    st.warning("Please write your answer before submitting.")
    else:
        st.info("No question available. Please try restarting the session.")


