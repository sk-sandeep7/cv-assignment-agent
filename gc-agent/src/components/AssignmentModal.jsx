import React, { useState, useEffect } from 'react';
import '../Modal.css';
import API_BASE_URL from '../config';

const AssignmentModal = ({ isOpen, onClose, questions, topic }) => {
  const [courses, setCourses] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState('');
  const [deadline, setDeadline] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen) {
      fetchCourses();
    }
  }, [isOpen]);

  const fetchCourses = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/classroom/courses`, {
        credentials: 'include'
      });
      
      if (response.status === 401) {
        setError('Authentication expired. Please log out and log in again.');
        return;
      }
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setCourses(data);
    } catch (error) {
      console.error('Error fetching courses:', error);
      setError('Failed to load courses. Please try again.');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedCourse) {
      setError('Please select a course');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const topicString = Array.isArray(topic) ? topic.join(', ') : topic;
      const assignmentData = {
        title: `Assignment-${topicString}`,
        description: null, // Let backend handle description generation with question IDs
        deadline: deadline || null,
        course_id: selectedCourse,
        questions: questions
      };

      const response = await fetch(`${API_BASE_URL}/api/classroom/create-assignment`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(assignmentData)
      });

      if (!response.ok) {
        throw new Error(`Failed to create assignment: ${response.status}`);
      }

      const result = await response.json();
      alert('Assignment created successfully!');
      onClose();
    } catch (error) {
      console.error('Error creating assignment:', error);
      setError('Failed to create assignment. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content assignment-modal">
        <div className="modal-header">
          <h2>Create Assignment in Google Classroom</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          {error && <div className="error-message">{error}</div>}
          
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="course">Select Course:</label>
              <select
                id="course"
                value={selectedCourse}
                onChange={(e) => setSelectedCourse(e.target.value)}
                required
              >
                <option value="">-- Select a course --</option>
                {courses.map((course) => (
                  <option key={course.id} value={course.id}>
                    {course.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="deadline">Deadline (optional):</label>
              <input
                type="datetime-local"
                id="deadline"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label>Assignment Preview:</label>
              <div className="assignment-preview">
                <h4>Title: Assignment-{Array.isArray(topic) ? topic.join(', ') : topic}</h4>
                <div className="total-marks" style={{ 
                  backgroundColor: '#e8f5e8', 
                  padding: '8px', 
                  borderRadius: '4px', 
                  margin: '8px 0',
                  fontWeight: 'bold',
                  color: '#2c5530'
                }}>
                  Total Marks: {questions.reduce((sum, q) => sum + (q.marks || 0), 0)} points
                  <br />
                  <small style={{ fontWeight: 'normal', color: '#666' }}>
                    This assignment will be created as a graded assignment in Google Classroom
                  </small>
                </div>
                <div className="questions-preview">
                  {questions.map((q, index) => (
                    <div key={index} className="question-preview">
                      <strong>Question {index + 1}:</strong> {q.question}
                      <br />
                      <strong>Marks:</strong> {q.marks}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="modal-actions">
              <button type="button" onClick={onClose} className="cancel-button">
                Cancel
              </button>
              <button type="submit" disabled={loading} className="submit-button">
                {loading ? 'Creating...' : 'Create Assignment'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default AssignmentModal;
