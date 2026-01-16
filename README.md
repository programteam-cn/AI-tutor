# 📚 AI Tutor - Adaptive SQL Learning System

An intelligent tutoring system that uses AI to provide personalized SQL learning experiences. The system adapts to each student's learning pace, tracks mastery progress, and delivers targeted questions to strengthen weak areas.

## 🌟 Features

### Adaptive Learning
- **Personalized Question Selection**: Questions are selected based on student performance and weak areas
- **Dynamic Difficulty Adjustment**: System adapts question complexity based on student proficiency
- **Mastery-Based Progression**: Students must achieve 80% mastery (minimum 3 attempts) before advancing to next subtopic

### Intelligent Assessment
- **AI-Powered Evaluation**: Uses GPT-4 for sophisticated answer evaluation and feedback
- **Concept Tracking**: Monitors understanding of specific SQL concepts (JOINs, subqueries, etc.)
- **Weak Area Detection**: Automatically identifies and prioritizes concepts needing improvement

### Student Profiling
- **Learning Pace Classification**: Categorizes students as slow, medium, or fast learners
- **Performance History**: Maintains detailed records of all attempts and progress
- **Mastery Metrics**: Tracks mastery scores per subtopic with independent progression

### Progressive Subtopic Mastery
- **Independent Tracking**: Each subtopic starts fresh with 0% mastery
- **Gradual Progression**: Mastery scores increase gradually over multiple attempts
- **Hard Caps**: Prevents premature high scores (max 30% on first attempt, 50% on second)
- **Clean Transitions**: When mastery is achieved, system resets for next subtopic

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- OpenAI API key
- Streamlit

### Installation

1. **Clone the repository**
   ```bash
   cd "AI TUTOR PHASE1"
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   ```

4. **Verify required files**
   Ensure these files exist:
   - `knowledge_graph.json` - Topic and subtopic structure
   - `problems.json` - Question bank
   - `config.py` - System configuration

### Running the Application

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

## 📖 How to Use

1. **Start Session**
   - Enter your User ID (e.g., `student123`)
   - Enter the subtopic you want to practice (e.g., `INNER JOIN`)
   - Click "Start Session"

2. **Answer Questions**
   - Read the question and learning context
   - Write your SQL query in the answer box
   - Submit your answer

3. **Review Feedback**
   - See your score and correctness
   - Read AI-generated feedback
   - Review identified weak concepts
   - Check your mastery progress

4. **Progress Through Subtopics**
   - Achieve 80%+ mastery with minimum 3 attempts
   - System automatically moves you to the next subtopic
   - Start fresh with new subtopic at 0% mastery

5. **Monitor Progress**
   - Check sidebar for current performance
   - View overall mastery percentage
   - See areas needing improvement

## 📁 Project Structure

```
AI TUTOR PHASE1/
├── app.py                      # Main Streamlit application
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
├── knowledge_graph.json        # Topic/subtopic structure
├── problems.json              # Question bank
├── .env                       # Environment variables (create this)
│
├── agents/
│   ├── student_profile.py     # Student profiling and mastery tracking
│   ├── question_picker.py     # Question selection logic
│   ├── mastery_agent.py       # Mastery assessment agent
│   └── question_generator.py  # Question generation (if applicable)
│
├── prompts/
│   ├── assessment_system.txt  # System prompt for assessment
│   ├── assessment_user.txt    # User prompt template for assessment
│   ├── grading_system.txt     # System prompt for grading
│   └── grading_user.txt       # User prompt template for grading
│
├── storage/
│   ├── tutor_state.py         # Session state management
│   └── user_data/             # Individual user progress files
│       ├── user1.json
│       └── ...
│
└── outputs/                   # Generated output files
```

## 🔧 Configuration

### `config.py`
Configure default settings:
```python
config_manager.config.default_difficulty = "medium"  # easy, medium, hard
```

### Mastery Thresholds
- **Mastery Achievement**: 80% score + minimum 3 attempts
- **First Attempt Cap**: Maximum 30% mastery
- **Second Attempt Cap**: Maximum 50% mastery
- **Third+ Attempts**: Full mastery possible based on performance

## 🛠 Technologies Used

- **Streamlit**: Interactive web interface
- **LangChain**: LLM orchestration and prompting
- **OpenAI GPT-4**: Answer evaluation and mastery assessment
- **Python**: Core programming language
- **JSON**: Data storage for knowledge graph and user progress

## 📊 Data Files

### knowledge_graph.json
Defines the learning structure:
```json
{
  "topics": [
    {
      "topic_name": "SQL Joins",
      "subtopics": [
        {
          "subtopic_id": "inner_join",
          "subtopic_name": "INNER JOIN",
          "clusters": [...]
        }
      ]
    }
  ]
}
```

### problems.json
Contains questions with metadata:
```json
[
  {
    "problem_id": "p001",
    "cluster_id": "c001",
    "description": "Question text...",
    "difficulty": "medium"
  }
]
```

## 🎯 Key Features Explained

### Independent Subtopic Mastery
Each subtopic is tracked independently:
- Starts at 0% mastery
- Tracks only questions from that subtopic
- Clears concept mastery and weak areas
- Requires fresh demonstration of understanding

### AI-Powered Assessment
The system uses GPT-4 to:
- Evaluate SQL query correctness
- Provide detailed feedback
- Identify weak concepts
- Assess mastery probability
- Detect missing concepts

### Adaptive Question Selection
Questions are selected based on:
- Current subtopic mastery level
- Identified weak concepts
- Concept coverage gaps
- Previous question history

## 🔄 Mastery Progression Flow

1. Student starts subtopic → Mastery: 0%
2. First question → Max mastery: 30%
3. Second question → Max mastery: 50%
4. Third+ questions → Can reach 80%+ for mastery
5. Mastery achieved → Reset to 0% for next subtopic
6. Repeat for each subtopic

## 📝 User Data Storage

User progress is saved in `storage/user_data/{user_id}.json`:
- Question history
- Mastery tracking (concepts, subtopics)
- Weak concepts and gaps
- Performance metrics

## 🤝 Contributing

To extend the system:
1. Add new subtopics to `knowledge_graph.json`
2. Add questions to `problems.json`
3. Modify prompts in `prompts/` directory
4. Adjust mastery thresholds in agents

## 📄 License

[Add your license information here]

## 🐛 Troubleshooting

**Issue**: High mastery on first question
- **Solution**: System now caps first attempt at 30%, second at 50%

**Issue**: Questions from previous subtopic appearing
- **Solution**: System now filters history by current subtopic only

**Issue**: OpenAI API errors
- **Solution**: Check your API key in `.env` file and ensure credits

## 📧 Contact

[Add your contact information here]

---

Built with ❤️ for adaptive learning
