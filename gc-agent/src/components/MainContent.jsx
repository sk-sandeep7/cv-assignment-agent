import React, { useState } from 'react';
import '../App.css';

const MainContent = ({
  currentStep,
  assignmentQuestions,
  onGenerate,
  onGenerateAgain,
  onCustomInput,
  onGenerateRubrics,
  onViewRubrics,
  isLoading,
  loadingRubricIndex,
}) => {
  const [topicsInput, setTopicsInput] = useState('');
  const [numQuestions, setNumQuestions] = useState(3);

  const handleGenerateClick = () => {
    onGenerate(topicsInput, numQuestions);
  };

  return (
    <div className="main-content">
      {isLoading && currentStep === 'initial' ? (
        <div className="loader-container">
          <div className="loader"></div>
        </div>
      ) : (
        <>
          {currentStep === 'initial' && (
            <div className="initial-view">
              <div className="input-options">
                <input
                  type="text"
                  placeholder="Enter topics, separated by commas"
                  value={topicsInput}
                  onChange={(e) => setTopicsInput(e.target.value)}
                  className="topic-input"
                />
                <select value={numQuestions} onChange={(e) => setNumQuestions(Number(e.target.value))} className="num-questions-select">
                  {[...Array(10).keys()].map(i => (
                    <option key={i + 1} value={i + 1}>{i + 1}</option>
                  ))}
                </select>
              </div>
              <button onClick={handleGenerateClick} className="button button-primary">
                Generate Assignments
              </button>
            </div>
          )}

          {currentStep === 'questions_generated' && (
            <div className="questions-container">
              <h2 className="questions-header">Generated Questions</h2>
              <table className="questions-table">
                <thead>
                  <tr>
                    <th>Question</th>
                    <th>Marks</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {assignmentQuestions.map((q, i) => (
                    <tr key={i}>
                      <td>{q.loading ? <div className="loader-small"></div> : q.question}</td>
                      <td>{q.loading ? '' : q.marks}</td>
                      <td>
                        <div className="action-buttons">
                          <button onClick={() => onGenerateAgain(topicsInput, i)} className="button button-gray" disabled={q.loading}>
                            Generate Again
                          </button>
                          <button onClick={() => onCustomInput(i)} className="button button-secondary" disabled={q.loading}>
                            Custom Input
                          </button>
                          <button 
                            onClick={() => onGenerateRubrics(i)} 
                            className="button button-blue" 
                            disabled={q.loading || loadingRubricIndex === i || q.rubrics}
                          >
                            {loadingRubricIndex === i ? <div className="loader-small"></div> : 'Evaluation Metrics'}
                          </button>
                          {q.rubrics && (
                            <button onClick={() => onViewRubrics(q.rubrics)} className="button-icon" aria-label="View Rubrics">
                              👁️
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <button onClick={() => onGenerateAgain(topicsInput, undefined, numQuestions)} className="button button-primary" style={{ marginTop: '1.5rem' }}>
                Generate All Again
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default MainContent;
