import React, { useState } from 'react';
import '../Modal.css';

const CustomInputModal = ({ isOpen, onClose, onSubmit, questionIndex }) => {
  const [customInput, setCustomInput] = useState('');

  if (!isOpen) return null;

  const handleSubmit = () => {
    onSubmit(customInput, questionIndex);
    setCustomInput('');
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-content">
        <h3 className="modal-title">Custom Question Input</h3>
        <div className="modal-body">
          <textarea
            className="modal-textarea"
            value={customInput}
            onChange={(e) => setCustomInput(e.target.value)}
            placeholder="Enter your question or topic, and the AI will refine it..."
          ></textarea>
        </div>
        <div className="modal-footer">
          <button
            onClick={handleSubmit}
            className="button button-primary"
          >
            Generate & Update
          </button>
          <button
            onClick={onClose}
            className="button button-gray"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

export default CustomInputModal;
