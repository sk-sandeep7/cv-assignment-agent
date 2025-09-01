import React, { useState, useEffect } from 'react';
import API_BASE_URL from '../config';

const Submissions = () => {
  const [courses, setCourses] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState('');
  const [selectedAssignment, setSelectedAssignment] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchCourses();
  }, []);

  useEffect(() => {
    if (selectedCourse) {
      fetchAssignments(selectedCourse);
      setSelectedAssignment('');
      setSubmissions([]);
    }
  }, [selectedCourse]);

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

  const fetchAssignments = async (courseId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/classroom/assignments/${courseId}`, {
        credentials: 'include'
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setAssignments(data);
    } catch (error) {
      console.error('Error fetching assignments:', error);
      setError('Failed to load assignments. Please try again.');
    }
  };

  const fetchSubmissions = async () => {
    if (!selectedCourse || !selectedAssignment) {
      setError('Please select both a course and an assignment.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      console.log(`Fetching submissions for course: ${selectedCourse}, assignment: ${selectedAssignment}`);
      const response = await fetch(
        `${API_BASE_URL}/api/classroom/submissions/${selectedCourse}/${selectedAssignment}`,
        {
          credentials: 'include'
        }
      );
      
      console.log('Response status:', response.status);
      
      if (response.status === 401) {
        setError('Authentication expired. Please log out and log in again.');
        return;
      }
      
      if (!response.ok) {
        // Try to get more detailed error information
        try {
          const errorData = await response.json();
          console.error('Error response:', errorData);
          setError(`Failed to load submissions: ${errorData.detail || `HTTP ${response.status}`}`);
        } catch {
          setError(`Failed to load submissions: HTTP ${response.status}`);
        }
        return;
      }
      
      const data = await response.json();
      console.log('Submissions data:', data);
      setSubmissions(data);
    } catch (error) {
      console.error('Error fetching submissions:', error);
      setError(`Failed to load submissions: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  const getStateColor = (state) => {
    switch (state) {
      case 'CREATED': return '#6b7280';
      case 'TURNED_IN': return '#059669';
      case 'RETURNED': return '#dc2626';
      case 'RECLAIMED_BY_STUDENT': return '#d97706';
      default: return '#374151';
    }
  };

  const getGradeColor = (grade) => {
    switch (grade) {
      case 'A': return '#059669'; // Green
      case 'B': return '#0891b2'; // Blue
      case 'C': return '#d97706'; // Orange
      case 'D': return '#dc2626'; // Red
      case 'F': return '#7c2d12'; // Dark red
      default: return '#6b7280'; // Gray
    }
  };

  const handleDownloadFile = async (fileId, fileName) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/download/drive-file/${fileId}`, {
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error(`Failed to download file: ${response.status}`);
      }

      // Create blob from response
      const blob = await response.blob();
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName || 'download.pdf';
      
      // Trigger download
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);
      
    } catch (error) {
      console.error('Error downloading file:', error);
      setError(`Failed to download file: ${error.message}`);
    }
  };

  const handleGradeSubmissions = async () => {
    if (!selectedCourse || !selectedAssignment) {
      setError('Please select both course and assignment');
      return;
    }

    if (!assignments.length) {
      setError('No assignment data available for grading');
      return;
    }

    try {
      setLoading(true);
      setError('');

      // Find the selected assignment to get its title
      const selectedAssignmentData = assignments.find(a => a.id === selectedAssignment);
      if (!selectedAssignmentData) {
        throw new Error('Selected assignment not found');
      }

      console.log('Fetching questions for assignment:', selectedAssignmentData.title);

      // Extract question IDs from assignment description
      const questionIds = [];
      if (selectedAssignmentData.description) {
        // Match pattern {id: xxxx} in the description
        const idMatches = selectedAssignmentData.description.match(/\{id:\s*([^}]+)\}/g);
        if (idMatches) {
          idMatches.forEach(match => {
            const id = match.match(/\{id:\s*([^}]+)\}/)[1].trim();
            questionIds.push(id);
          });
        }
      }

      console.log('Extracted question IDs from description:', questionIds);

      // Get questions with evaluation criteria using question IDs
      let questionsData;
      if (questionIds.length > 0) {
        // Use question IDs for direct lookup
        const questionsResponse = await fetch(
          `${API_BASE_URL}/api/get-questions-by-ids`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ question_ids: questionIds })
          }
        );

        if (!questionsResponse.ok) {
          throw new Error('Failed to fetch assignment questions by IDs');
        }

        questionsData = await questionsResponse.json();
      } else {
        // Fallback to title-based search
        const questionsResponse = await fetch(
          `${API_BASE_URL}/api/get-assignment-questions/${encodeURIComponent(selectedAssignmentData.title)}`,
          {
            credentials: 'include'
          }
        );

        if (!questionsResponse.ok) {
          throw new Error('Failed to fetch assignment questions');
        }

        questionsData = await questionsResponse.json();
      }
      
      if (questionsData.status !== 'success' || !questionsData.questions || questionsData.questions.length === 0) {
        throw new Error('No questions found for this assignment. Make sure the assignment was created through this system.');
      }

      console.log('Found questions:', questionsData.questions);

      // Start grading process
      console.log('Starting grading process...');
      const gradeData = {
        course_id: selectedCourse,
        assignment_id: selectedAssignment,
        questions: questionsData.questions
      };

      const gradeResponse = await fetch(`${API_BASE_URL}/api/classroom/grade-submissions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(gradeData)
      });

      if (!gradeResponse.ok) {
        const errorData = await gradeResponse.json();
        throw new Error(errorData.detail || 'Failed to grade submissions');
      }

      const result = await gradeResponse.json();
      
      console.log('Grading completed:', result);

      // Update submissions with grades
      setSubmissions(prevSubmissions => {
        return prevSubmissions.map(submission => {
          const gradeResult = result.results.find(r => r.submission_id === submission.id);
          if (gradeResult) {
            return {
              ...submission,
              aiGrade: gradeResult.grading_result,
              isGraded: true
            };
          }
          return submission;
        });
      });

      alert(`Grading completed!\n\nTotal submissions: ${result.total_submissions}\nSuccessfully graded: ${result.graded_count}\nGrades assigned to Classroom: ${result.grades_assigned_to_classroom}`);
      
    } catch (error) {
      console.error('Error grading submissions:', error);
      setError(`Failed to grade submissions: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '2rem', backgroundColor: '#FFF9F2', minHeight: '100vh' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        <h1 style={{ color: '#C54B42', fontSize: '2rem', fontWeight: 'bold', marginBottom: '2rem' }}>
          Student Submissions
        </h1>

        {error && (
          <div style={{
            backgroundColor: '#fee2e2',
            border: '1px solid #fecaca',
            color: '#dc2626',
            padding: '12px',
            borderRadius: '8px',
            marginBottom: '20px'
          }}>
            {error}
          </div>
        )}

        {/* Dropdowns */}
        <div style={{ 
          display: 'flex', 
          gap: '1rem', 
          marginBottom: '2rem',
          alignItems: 'flex-end',
          flexWrap: 'wrap'
        }}>
          <div style={{ minWidth: '250px' }}>
            <label style={{ 
              display: 'block', 
              marginBottom: '8px', 
              fontWeight: '600', 
              color: '#333' 
            }}>
              Select Course:
            </label>
            <select
              value={selectedCourse}
              onChange={(e) => setSelectedCourse(e.target.value)}
              style={{
                width: '100%',
                padding: '12px',
                border: '2px solid #e5e7eb',
                borderRadius: '8px',
                fontSize: '14px',
                backgroundColor: 'white'
              }}
            >
              <option value="">-- Select a course --</option>
              {courses.map((course) => (
                <option key={course.id} value={course.id}>
                  {course.name}
                </option>
              ))}
            </select>
          </div>

          <div style={{ minWidth: '250px' }}>
            <label style={{ 
              display: 'block', 
              marginBottom: '8px', 
              fontWeight: '600', 
              color: '#333' 
            }}>
              Select Assignment:
            </label>
            <select
              value={selectedAssignment}
              onChange={(e) => setSelectedAssignment(e.target.value)}
              disabled={!selectedCourse}
              style={{
                width: '100%',
                padding: '12px',
                border: '2px solid #e5e7eb',
                borderRadius: '8px',
                fontSize: '14px',
                backgroundColor: selectedCourse ? 'white' : '#f9fafb',
                cursor: selectedCourse ? 'pointer' : 'not-allowed'
              }}
            >
              <option value="">-- Select an assignment --</option>
              {assignments.map((assignment) => (
                <option key={assignment.id} value={assignment.id}>
                  {assignment.title}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={fetchSubmissions}
            disabled={!selectedCourse || !selectedAssignment || loading}
            style={{
              padding: '12px 24px',
              backgroundColor: (!selectedCourse || !selectedAssignment || loading) ? '#e5e7eb' : '#C54B42',
              color: (!selectedCourse || !selectedAssignment || loading) ? '#9ca3af' : 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '14px',
              fontWeight: '600',
              cursor: (!selectedCourse || !selectedAssignment || loading) ? 'not-allowed' : 'pointer',
              minWidth: '150px'
            }}
          >
            {loading ? 'Loading...' : 'Get Submissions'}
          </button>

          {/* Grade Submissions Button */}
          <button
            onClick={handleGradeSubmissions}
            disabled={!selectedCourse || !selectedAssignment || loading || submissions.length === 0}
            style={{
              padding: '12px 24px',
              backgroundColor: (!selectedCourse || !selectedAssignment || loading || submissions.length === 0) ? '#e5e7eb' : '#10b981',
              color: (!selectedCourse || !selectedAssignment || loading || submissions.length === 0) ? '#9ca3af' : 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '14px',
              fontWeight: '600',
              cursor: (!selectedCourse || !selectedAssignment || loading || submissions.length === 0) ? 'not-allowed' : 'pointer',
              minWidth: '180px',
              marginLeft: '12px'
            }}
          >
            {loading ? 'Grading...' : '🤖 Grade Submissions'}
          </button>
        </div>

        {/* Submissions Table */}
        {submissions.length > 0 && (
          <div style={{
            backgroundColor: 'white',
            borderRadius: '8px',
            boxShadow: '0 2px 10px rgba(0, 0, 0, 0.1)',
            overflow: 'hidden'
          }}>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ backgroundColor: '#f8f9fa' }}>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #e5e7eb', fontWeight: '600' }}>
                      Student Name
                    </th>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #e5e7eb', fontWeight: '600' }}>
                      Student ID
                    </th>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #e5e7eb', fontWeight: '600' }}>
                      Status
                    </th>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #e5e7eb', fontWeight: '600' }}>
                      Attachments
                    </th>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #e5e7eb', fontWeight: '600' }}>
                      AI Grade
                    </th>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #e5e7eb', fontWeight: '600' }}>
                      Submitted
                    </th>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #e5e7eb', fontWeight: '600' }}>
                      Last Updated
                    </th>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #e5e7eb', fontWeight: '600' }}>
                      Grade
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {submissions.map((submission, index) => (
                    <tr key={submission.id} style={{ 
                      backgroundColor: index % 2 === 0 ? 'white' : '#f9fafb',
                      borderBottom: '1px solid #e5e7eb'
                    }}>
                      <td style={{ padding: '12px' }}>
                        {submission.studentName}
                      </td>
                      <td style={{ padding: '12px', fontSize: '14px', color: '#6b7280' }}>
                        {submission.studentId || 'N/A'}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <span style={{
                          padding: '4px 8px',
                          borderRadius: '4px',
                          fontSize: '12px',
                          fontWeight: '600',
                          backgroundColor: `${getStateColor(submission.state)}20`,
                          color: getStateColor(submission.state)
                        }}>
                          {submission.state.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td style={{ padding: '12px' }}>
                        {submission.attachments && submission.attachments.length > 0 ? (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                            {submission.attachments.map((attachment, attachIndex) => (
                              <div key={attachIndex} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                {attachment.type === 'drive_file' && (
                                  <>
                                    {attachment.downloadUrl ? (
                                      <a
                                        href={attachment.downloadUrl}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        style={{
                                          padding: '4px 8px',
                                          backgroundColor: '#3b82f6',
                                          color: 'white',
                                          textDecoration: 'none',
                                          borderRadius: '4px',
                                          fontSize: '12px',
                                          cursor: 'pointer'
                                        }}
                                        onMouseOver={(e) => e.target.style.backgroundColor = '#2563eb'}
                                        onMouseOut={(e) => e.target.style.backgroundColor = '#3b82f6'}
                                      >
                                        📄 {attachment.title}
                                      </a>
                                    ) : (
                                      <button
                                        onClick={() => handleDownloadFile(attachment.id, attachment.title)}
                                        style={{
                                          padding: '4px 8px',
                                          backgroundColor: '#3b82f6',
                                          color: 'white',
                                          border: 'none',
                                          borderRadius: '4px',
                                          fontSize: '12px',
                                          cursor: 'pointer',
                                          textDecoration: 'none'
                                        }}
                                        onMouseOver={(e) => e.target.style.backgroundColor = '#2563eb'}
                                        onMouseOut={(e) => e.target.style.backgroundColor = '#3b82f6'}
                                      >
                                        📄 {attachment.title}
                                      </button>
                                    )}
                                  </>
                                )}
                                {attachment.type === 'link' && (
                                  <a
                                    href={attachment.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{
                                      padding: '4px 8px',
                                      backgroundColor: '#10b981',
                                      color: 'white',
                                      textDecoration: 'none',
                                      borderRadius: '4px',
                                      fontSize: '12px'
                                    }}
                                  >
                                    🔗 {attachment.title}
                                  </a>
                                )}
                                {attachment.type === 'youtube_video' && (
                                  <a
                                    href={attachment.alternateLink}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{
                                      padding: '4px 8px',
                                      backgroundColor: '#ef4444',
                                      color: 'white',
                                      textDecoration: 'none',
                                      borderRadius: '4px',
                                      fontSize: '12px'
                                    }}
                                  >
                                    🎥 {attachment.title}
                                  </a>
                                )}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <span style={{ color: '#6b7280', fontSize: '14px' }}>No attachments</span>
                        )}
                      </td>
                      <td style={{ padding: '12px' }}>
                        {submission.isGraded && submission.aiGrade ? (
                          <div style={{ textAlign: 'center' }}>
                            <div style={{ 
                              fontWeight: 'bold', 
                              fontSize: '16px', 
                              color: '#2c5530',
                              marginBottom: '4px'
                            }}>
                              {submission.aiGrade.total_marks}/{submission.aiGrade.max_total_marks}
                            </div>
                            <div style={{
                              padding: '2px 8px',
                              backgroundColor: getGradeColor(submission.aiGrade.letter_grade),
                              color: 'white',
                              borderRadius: '4px',
                              fontSize: '12px',
                              fontWeight: 'bold',
                              display: 'inline-block'
                            }}>
                              {submission.aiGrade.letter_grade}
                            </div>
                          </div>
                        ) : (
                          <span style={{ color: '#6b7280', fontSize: '14px', fontStyle: 'italic' }}>
                            Not graded
                          </span>
                        )}
                      </td>
                      <td style={{ padding: '12px', fontSize: '14px' }}>
                        {formatDate(submission.creationTime)}
                      </td>
                      <td style={{ padding: '12px', fontSize: '14px' }}>
                        {formatDate(submission.updateTime)}
                      </td>
                      <td style={{ padding: '12px', fontSize: '14px', fontWeight: '600' }}>
                        {submission.assignedGrade || submission.draftGrade || 'Not graded'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {submissions.length === 0 && selectedCourse && selectedAssignment && !loading && (
          <div style={{
            textAlign: 'center',
            padding: '3rem',
            backgroundColor: 'white',
            borderRadius: '8px',
            boxShadow: '0 2px 10px rgba(0, 0, 0, 0.1)'
          }}>
            <p style={{ color: '#6b7280', fontSize: '16px' }}>
              No submissions found for this assignment.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Submissions;
