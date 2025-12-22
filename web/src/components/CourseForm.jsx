/**
 * CourseForm Component
 *
 * Form for entering course and book information to find resources.
 */

import { useState } from 'react';
import './CourseForm.css';

export default function CourseForm({ onJobSubmitted, isLoading }) {
  const [formData, setFormData] = useState({
    university_name: '',
    course_name: '',
    course_url: '',
    textbook: '',
    topics_list: '',
    book_title: '',
    book_author: '',
    isbn: '',
    book_pdf_path: '',
    book_url: ''
  });

  const [validationError, setValidationError] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear validation error when user types
    if (validationError) {
      setValidationError('');
    }
  };

  const validateForm = () => {
    // Check if at least one field is filled
    const hasAnyValue = Object.values(formData).some(value => value.trim() !== '');

    if (!hasAnyValue) {
      setValidationError('Please fill in at least one field');
      return false;
    }

    return true;
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    // Call parent callback with form data
    onJobSubmitted(formData);
  };

  return (
    <div className="course-form-card">
      <h2>Course Information</h2>

      <form onSubmit={handleSubmit} className="course-form">
        {/* University Name */}
        <div className="form-group">
          <label htmlFor="university_name">University Name</label>
          <input
            type="text"
            id="university_name"
            name="university_name"
            value={formData.university_name}
            onChange={handleChange}
            placeholder="e.g., MIT, Stanford"
            disabled={isLoading}
          />
        </div>

        {/* Course Name */}
        <div className="form-group">
          <label htmlFor="course_name">Course Name</label>
          <input
            type="text"
            id="course_name"
            name="course_name"
            value={formData.course_name}
            onChange={handleChange}
            placeholder="e.g., Introduction to Algorithms"
            disabled={isLoading}
          />
        </div>

        {/* Course URL */}
        <div className="form-group">
          <label htmlFor="course_url">Course URL <span className="optional">(optional)</span></label>
          <input
            type="url"
            id="course_url"
            name="course_url"
            value={formData.course_url}
            onChange={handleChange}
            placeholder="https://..."
            disabled={isLoading}
          />
        </div>

        {/* Book Title */}
        <div className="form-group">
          <label htmlFor="book_title">Book Title</label>
          <input
            type="text"
            id="book_title"
            name="book_title"
            value={formData.book_title}
            onChange={handleChange}
            placeholder="e.g., Introduction to Algorithms"
            disabled={isLoading}
          />
        </div>

        {/* Book Author */}
        <div className="form-group">
          <label htmlFor="book_author">Book Author(s)</label>
          <input
            type="text"
            id="book_author"
            name="book_author"
            value={formData.book_author}
            onChange={handleChange}
            placeholder="e.g., Cormen, Leiserson, Rivest, Stein"
            disabled={isLoading}
          />
        </div>

        {/* ISBN */}
        <div className="form-group">
          <label htmlFor="isbn">ISBN <span className="optional">(optional)</span></label>
          <input
            type="text"
            id="isbn"
            name="isbn"
            value={formData.isbn}
            onChange={handleChange}
            placeholder="e.g., 978-0262046305"
            disabled={isLoading}
          />
        </div>

        {/* Book URL */}
        <div className="form-group">
          <label htmlFor="book_url">Book URL <span className="optional">(optional)</span></label>
          <input
            type="url"
            id="book_url"
            name="book_url"
            value={formData.book_url}
            onChange={handleChange}
            placeholder="https://..."
            disabled={isLoading}
          />
        </div>

        {/* Topics List */}
        <div className="form-group">
          <label htmlFor="topics_list">Topics List <span className="optional">(optional)</span></label>
          <textarea
            id="topics_list"
            name="topics_list"
            value={formData.topics_list}
            onChange={handleChange}
            placeholder="e.g., Sorting, Graph Algorithms, Dynamic Programming"
            rows="3"
            disabled={isLoading}
          />
        </div>

        {/* Validation Error */}
        {validationError && (
          <div className="validation-error">
            {validationError}
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          className="submit-button"
          disabled={isLoading}
        >
          {isLoading ? 'Finding Resources...' : 'Find Resources'}
        </button>
      </form>
    </div>
  );
}
