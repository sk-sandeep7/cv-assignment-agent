import React from 'react';
import '../Modal.css';

const EvaluationModal = ({ isOpen, onClose, rubric, onRegenerate, isRegenerating }) => {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop">
      <div className="modal-content">
        <h3 className="modal-title">Evaluation Rubric</h3>
        <div className="modal-body">
          {isRegenerating ? (
            <div style={{ textAlign: 'center', padding: '20px' }}>
              <div className="spinner"></div>
              <p>Regenerating rubrics...</p>
            </div>
          ) : rubric && rubric.length > 0 ? (
            <table className="rubric-table">
              <thead>
                <tr>
                  <th>Criterion</th>
                  <th>Marks</th>
                </tr>
              </thead>
              <tbody>
                {rubric.map((item, index) => (
                  <tr key={index}>
                    <td>{item.criterion}</td>
                    <td>{item.marks}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>No rubric available.</p>
          )}
        </div>
        <div className="modal-footer">
          <button 
            onClick={onRegenerate} 
            className="button button-secondary"
            disabled={isRegenerating}
            style={{ 
              opacity: isRegenerating ? 0.6 : 1,
              cursor: isRegenerating ? 'not-allowed' : 'pointer'
            }}
          >
            {isRegenerating ? 'Regenerating...' : 'Regenerate'}
          </button>
          <button onClick={onClose} className="button button-primary">
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default EvaluationModal;
