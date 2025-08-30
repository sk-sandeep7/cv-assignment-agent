import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import MainContent from './components/MainContent';
import CustomInputModal from './components/CustomInputModal';
import EvaluationModal from './components/EvaluationModal';

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [currentStep, setCurrentStep] = useState('initial');
  const [assignmentQuestions, setAssignmentQuestions] = useState([]);
  const [selectedQuestion, setSelectedQuestion] = useState('');
  const [evaluationCriteria, setEvaluationCriteria] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEvaluationModalOpen, setIsEvaluationModalOpen] = useState(false);
  const [currentRubric, setCurrentRubric] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [customQuestionIndex, setCustomQuestionIndex] = useState(null);
  const [loadingRubricIndex, setLoadingRubricIndex] = useState(null);

  useEffect(() => {
    if (location.pathname === '/questions' && assignmentQuestions.length > 0) {
      setCurrentStep('questions_generated');
    } else {
      setCurrentStep('initial');
      // Optional: Clear questions if navigating back to home
      // setAssignmentQuestions([]); 
    }
  }, [location.pathname, assignmentQuestions.length]);

  const handleGenerateAssignments = async (topicsInput, numQuestions) => {
    setIsLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/generate-questions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          topic: topicsInput.split(',').map(topic => topic.trim()),
          num_questions: numQuestions 
        }),
      });
      const data = await res.json();
      const questionsWithLoading = data.questions ? data.questions.map(q => ({ ...q, loading: false, rubrics: null })) : [];
      setAssignmentQuestions(questionsWithLoading);
      setCurrentStep('questions_generated');
      navigate('/questions');
    } catch (err) {
      setAssignmentQuestions([]);
      alert('Failed to fetch questions');
    }
    setIsLoading(false);
  };

  const handleQuestionSelect = async (question) => {
    setSelectedQuestion(question);
    setIsLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/get-evaluation-criteria', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      setEvaluationCriteria(data.criteria || []);
      setCurrentStep('criteria_displayed');
    } catch (err) {
      setEvaluationCriteria([]);
      alert('Failed to fetch criteria');
    }
    setIsLoading(false);
  };

  const handleGenerateAgain = async (topicsInput, index, numQuestions) => {
    if (index !== undefined) {
      const newQuestions = [...assignmentQuestions];
      newQuestions[index].loading = true;
      setAssignmentQuestions(newQuestions);

      try {
        const res = await fetch('http://localhost:8000/api/regenerate-question', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ topic: topicsInput.split(',').map(topic => topic.trim()) }),
        });
        const newQuestion = await res.json();
        const updatedQuestions = [...assignmentQuestions];
        updatedQuestions[index] = { ...newQuestion, loading: false };
        setAssignmentQuestions(updatedQuestions);
      } catch (err) {
        alert('Failed to regenerate question');
        const updatedQuestions = [...assignmentQuestions];
        updatedQuestions[index].loading = false;
        setAssignmentQuestions(updatedQuestions);
      }
    } else {
      await handleGenerateAssignments(topicsInput, numQuestions);
    }
  };

  const handleGenerateRubrics = async (index) => {
    setLoadingRubricIndex(index);
    const question = assignmentQuestions[index];

    try {
      const res = await fetch('http://localhost:8000/api/generate-evaluation-rubrics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question.question, marks: question.marks }),
      });
      const data = await res.json();
      const updatedQuestions = [...assignmentQuestions];
      updatedQuestions[index] = { ...question, rubrics: data.rubric };
      setAssignmentQuestions(updatedQuestions);
    } catch (err) {
      alert('Failed to generate evaluation rubrics.');
    } finally {
      setLoadingRubricIndex(null);
    }
  };

  const handleViewRubrics = (rubric) => {
    setCurrentRubric(rubric);
    setIsEvaluationModalOpen(true);
  };

  const handleCustomInput = (index) => {
    setCustomQuestionIndex(index);
    setIsModalOpen(true);
  };

  const handleCustomQuestionSubmit = async (customInput, index) => {
    setIsModalOpen(false);
    
    // Set loading state for the specific question
    const newQuestions = [...assignmentQuestions];
    newQuestions[index].loading = true;
    setAssignmentQuestions(newQuestions);

    try {
      const res = await fetch('http://localhost:8000/api/generate-custom-question', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_input: customInput, index: index }),
      });
      const newQuestionData = await res.json();
      if (newQuestionData && newQuestionData.question) {
        console.log(newQuestionData)
        const updatedQuestions = [...assignmentQuestions];
        console.log(updatedQuestions)
        updatedQuestions[index] = { ...newQuestionData, loading: false };
        setAssignmentQuestions(updatedQuestions);
      } else {
        throw new Error("Invalid response from server");
      }
    } catch (err) {
      alert('Failed to update question with custom input.');
      console.error(err);
      // Reset loading state on error
      const updatedQuestions = [...assignmentQuestions];
      updatedQuestions[index].loading = false;
      setAssignmentQuestions(updatedQuestions);
    }
  };

  const handleProceed = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/execute-task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: selectedQuestion, criteria: evaluationCriteria }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        setCurrentStep('task_successful');
      } else {
        alert('Task failed');
      }
    } catch (err) {
      alert('Failed to execute task');
    }
    setIsLoading(false);
  };

  return (
    <div style={{ padding: '0', display: 'flex', backgroundColor: '#FFF9F2' }}>
      <Sidebar />
      <div style={{ marginLeft: '256px', width: '100%' }}>
        <MainContent
          currentStep={currentStep}
          onGenerate={handleGenerateAssignments}
          onQuestionSelect={handleQuestionSelect}
          assignmentQuestions={assignmentQuestions}
          evaluationCriteria={evaluationCriteria}
          onGenerateAgain={handleGenerateAgain}
          onCustomInput={handleCustomInput}
          onGenerateRubrics={handleGenerateRubrics}
          onViewRubrics={handleViewRubrics}
          isLoading={isLoading}
          loadingRubricIndex={loadingRubricIndex}
          onProceed={handleProceed}
        />
      </div>
      {isModalOpen && (
        <CustomInputModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onSubmit={handleCustomQuestionSubmit}
          questionIndex={customQuestionIndex}
        />
      )}
      {isEvaluationModalOpen && (
        <EvaluationModal
          isOpen={isEvaluationModalOpen}
          onClose={() => setIsEvaluationModalOpen(false)}
          rubric={currentRubric}
        />
      )}
    </div>
  );
}

export default App;
