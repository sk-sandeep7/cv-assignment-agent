import React, { useState, useEffect } from 'react';
import { Routes, Route, useNavigate, useLocation, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import MainContent from './components/MainContent';
import CustomInputModal from './components/CustomInputModal';
import EvaluationModal from './components/EvaluationModal';
import AssignmentModal from './components/AssignmentModal';
import Submissions from './components/Submissions';
import Login from './components/Login';
import API_BASE_URL from './config';

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [currentStep, setCurrentStep] = useState('initial');
  const [assignmentQuestions, setAssignmentQuestions] = useState([]);
  const [selectedQuestion, setSelectedQuestion] = useState('');
  const [evaluationCriteria, setEvaluationCriteria] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEvaluationModalOpen, setIsEvaluationModalOpen] = useState(false);
  const [isAssignmentModalOpen, setIsAssignmentModalOpen] = useState(false);
  const [currentRubric, setCurrentRubric] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [customQuestionIndex, setCustomQuestionIndex] = useState(null);
  const [loadingRubricIndex, setLoadingRubricIndex] = useState(null);
  const [questionsToAssign, setQuestionsToAssign] = useState([]);
  const [assignmentTopic, setAssignmentTopic] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authChecked, setAuthChecked] = useState(false);

  // Check authentication status
  const checkAuthStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/check_auth`, {
        credentials: 'include'
      });
      const data = await response.json();
      console.log('Auth check result:', data); // Debug log
      setIsAuthenticated(data.logged_in);
      setAuthChecked(true);
      
      // Only redirect if not authenticated and on a protected route
      if (!data.logged_in && (location.pathname === '/home' || location.pathname === '/questions' || location.pathname === '/submissions')) {
        console.log('Not authenticated, redirecting to login'); // Debug log
        navigate('/login');
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      setIsAuthenticated(false);
      setAuthChecked(true);
      if (location.pathname !== '/login') {
        navigate('/login');
      }
    }
  };

  // Check auth status on mount and when location changes
  // Add a small delay when coming from OAuth redirect
  useEffect(() => {
    if (location.pathname === '/home' && !authChecked) {
      // Add a small delay for OAuth redirects to allow session to establish
      setTimeout(() => {
        checkAuthStatus();
      }, 500);
    } else {
      checkAuthStatus();
    }
  }, [location.pathname]);

  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE_URL}/api/auth/google/logout`, {
        method: 'POST',
        credentials: 'include'
      });
      // Reset authentication state
      setIsAuthenticated(false);
      // Redirect to login page
      navigate('/login');
    } catch (error) {
      console.error('Logout error:', error);
      // Still reset state and redirect even if logout API fails
      setIsAuthenticated(false);
      navigate('/login');
    }
  };

  useEffect(() => {
    if (location.pathname === '/questions' && assignmentQuestions.length > 0) {
      setCurrentStep('questions_generated');
    } else if (location.pathname === '/home') {
      setCurrentStep('initial');
    }
  }, [location.pathname, assignmentQuestions.length]);

  const handleGenerateAssignments = async (topicsInput, numQuestions) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/generate-questions`, {
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
      const res = await fetch(`${API_BASE_URL}/api/get-evaluation-criteria`, {
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
        const res = await fetch(`${API_BASE_URL}/api/regenerate-question`, {
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
      const res = await fetch(`${API_BASE_URL}/api/generate-evaluation-rubrics`, {
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
      const res = await fetch(`${API_BASE_URL}/api/generate-custom-question`, {
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
    // Check if all questions have rubrics
    const allHaveRubrics = assignmentQuestions.every(q => q.rubrics && q.rubrics.length > 0);
    
    if (!allHaveRubrics) {
      alert('Please generate evaluation metrics for all questions before proceeding.');
      return;
    }

    try {
      // Store questions in database to get IDs
      const response = await fetch(`${API_BASE_URL}/api/store-questions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ questions: assignmentQuestions }),
      });

      if (!response.ok) {
        throw new Error(`Failed to store questions: ${response.status}`);
      }

      const result = await response.json();
      
      if (result.status === 'success' && result.stored_questions) {
        // Update questions with database IDs
        setAssignmentQuestions(result.stored_questions);
        
        // Extract topic from questions for assignment title
        const topicFromQuestions = result.stored_questions[0]?.topic || ['General Assignment'];
        setAssignmentTopic(topicFromQuestions);
        setQuestionsToAssign(result.stored_questions);
        setIsAssignmentModalOpen(true);
      } else {
        throw new Error(result.message || 'Failed to store questions');
      }
    } catch (error) {
      console.error('Error storing questions:', error);
      alert('Failed to save questions. Please try again.');
    }
  };

  // Show loading while checking authentication
  if (!authChecked) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        backgroundColor: '#FFF9F2' 
      }}>
        <div>Checking authentication...</div>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<Login />} />
      <Route path="/home" element={
        isAuthenticated ? (
          <div style={{ padding: '0', display: 'flex', backgroundColor: '#FFF9F2' }}>
            <Sidebar onLogout={handleLogout} />
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
            {isAssignmentModalOpen && (
              <AssignmentModal
                isOpen={isAssignmentModalOpen}
                onClose={() => setIsAssignmentModalOpen(false)}
                questions={questionsToAssign}
                topic={assignmentTopic}
              />
            )}
          </div>
        ) : (
          <Navigate to="/login" replace />
        )
      } />
      <Route path="/questions" element={
        isAuthenticated ? (
          <div style={{ padding: '0', display: 'flex', backgroundColor: '#FFF9F2' }}>
            <Sidebar onLogout={handleLogout} />
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
            {isAssignmentModalOpen && (
              <AssignmentModal
                isOpen={isAssignmentModalOpen}
                onClose={() => setIsAssignmentModalOpen(false)}
                questions={questionsToAssign}
                topic={assignmentTopic}
              />
            )}
          </div>
        ) : (
          <Navigate to="/login" replace />
        )
      } />
      <Route path="/submissions" element={
        isAuthenticated ? (
          <div style={{ padding: '0', display: 'flex', backgroundColor: '#FFF9F2' }}>
            <Sidebar onLogout={handleLogout} />
            <div style={{ marginLeft: '256px', width: '100%' }}>
              <Submissions />
            </div>
          </div>
        ) : (
          <Navigate to="/login" replace />
        )
      } />
    </Routes>
  );
}

export default App;
