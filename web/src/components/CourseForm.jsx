/**
 * CourseForm Component
 *
 * Form for entering course and book information to find resources.
 */

import { useState } from 'react';

export default function CourseForm({ onJobSubmitted, isLoading }) {
  const [searchParamType, setSearchParamType] = useState('');
  const [formData, setFormData] = useState({
    course_url: '',
    book_url: '',
    book_title: '',
    book_author: '',
    isbn: '',
    topics_list: '',
    email: '',
    desired_resource_types: [],
    force_refresh: false
  });

  const [validationError, setValidationError] = useState('');
  const [isDesiredResourcesExpanded, setIsDesiredResourcesExpanded] = useState(false);
  const [isFocusTopicsExpanded, setIsFocusTopicsExpanded] = useState(false);
  // Email section - COMMENTED OUT
  // const [isEmailExpanded, setIsEmailExpanded] = useState(false);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
    // Clear validation error when user types
    if (validationError) {
      setValidationError('');
    }
  };

  const handleResourceTypeChange = (resourceType) => {
    setFormData(prev => {
      const currentTypes = prev.desired_resource_types || [];
      const newTypes = currentTypes.includes(resourceType)
        ? currentTypes.filter(type => type !== resourceType)
        : [...currentTypes, resourceType];
      return {
        ...prev,
        desired_resource_types: newTypes
      };
    });
    // Clear validation error when user changes selection
    if (validationError) {
      setValidationError('');
    }
  };

  const handleSearchParamChange = (e) => {
    const value = e.target.value;
    setSearchParamType(value);
    // Clear validation error when selection changes
    if (validationError) {
      setValidationError('');
    }
    // Clear form data when switching search types
    setFormData({
      course_url: '',
      book_url: '',
      book_title: '',
      book_author: '',
      isbn: '',
      topics_list: formData.topics_list, // Keep topics_list
      email: formData.email, // Keep email
      desired_resource_types: formData.desired_resource_types // Keep desired_resource_types
    });
  };

  const isFormValid = () => {
    if (!searchParamType) {
      return false;
    }

    // Check if required fields are filled based on selected search parameter type
    switch (searchParamType) {
      case 'course_url':
        return formData.course_url.trim() !== '';
      case 'book_url':
        return formData.book_url.trim() !== '';
      case 'book_title_author':
        return formData.book_title.trim() !== '' && formData.book_author.trim() !== '';
      case 'isbn':
        return formData.isbn.trim() !== '';
      default:
        return false;
    }
  };

  const validateForm = () => {
    if (!searchParamType) {
      setValidationError('Please select a search parameter type');
      return false;
    }

    // Validate based on selected search parameter type
    switch (searchParamType) {
      case 'course_url':
        if (formData.course_url.trim() === '') {
          setValidationError('Please provide a Course URL');
          return false;
        }
        break;
      case 'book_url':
        if (formData.book_url.trim() === '') {
          setValidationError('Please provide a Book URL');
          return false;
        }
        break;
      case 'book_title_author':
        if (formData.book_title.trim() === '' || formData.book_author.trim() === '') {
          setValidationError('Please provide both Book Title and Author');
          return false;
        }
        break;
      case 'isbn':
        if (formData.isbn.trim() === '') {
          setValidationError('Please provide a Book ISBN');
          return false;
        }
        break;
      default:
        setValidationError('Please select a valid search parameter type');
        return false;
    }

    return true;
  };

  const handleReset = () => {
    setSearchParamType('');
    setFormData({
      course_url: '',
      book_url: '',
      book_title: '',
      book_author: '',
      isbn: '',
      topics_list: '',
      email: '',
      desired_resource_types: [],
      force_refresh: false
    });
    setValidationError('');
    setIsDesiredResourcesExpanded(false);
    setIsFocusTopicsExpanded(false);
    // Email section - COMMENTED OUT
    // setIsEmailExpanded(false);
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
    <div className="relative bg-gradient-to-br from-white to-purple-50 rounded-xl p-12 shadow-xl border-2 border-gray-200 transition-all overflow-hidden before:content-[''] before:absolute before:-top-1/2 before:-right-1/2 before:w-[200%] before:h-[200%] before:bg-[radial-gradient(circle,rgba(124,58,237,0.05)_0%,transparent_70%)] before:animate-[pulse_4s_ease-in-out_infinite] before:pointer-events-none hover:shadow-xl">
      <h2 className="relative z-10 m-0 mb-6 text-xl font-bold text-gray-800 tracking-tight text-center">Find Study Resources</h2>

      <form onSubmit={handleSubmit} className="relative z-10 flex flex-col gap-4">
        {/* Submit and Reset Buttons - Moved to top */}
        <div className="flex gap-2 flex-shrink-0 mb-2 -order-1 max-md:flex-col">
          <button
            type="submit"
            className="relative overflow-hidden whitespace-nowrap px-6 py-3 bg-gradient-to-r from-primary to-primary-dark text-white border-none rounded-lg text-base font-bold cursor-pointer transition-all shadow-md tracking-wide hover:not(:disabled):-translate-y-0.5 hover:not(:disabled):shadow-lg active:not(:disabled):translate-y-0 active:not(:disabled):shadow-md disabled:bg-gray-100 disabled:text-gray-500 disabled:cursor-not-allowed disabled:shadow-none disabled:transform-none before:content-[''] before:absolute before:top-0 before:-left-full before:w-full before:h-full before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent before:transition-[left_600ms] hover:not(:disabled):before:left-full max-md:w-full"
            disabled={isLoading || !isFormValid()}
          >
            {isLoading ? '🔍 Finding Resources...' : '🔍 Find Resources'}
          </button>
          <button
            type="button"
            className="whitespace-nowrap px-5 py-3 bg-white text-gray-600 border-2 border-gray-200 rounded-lg text-base font-semibold cursor-pointer transition-all hover:not(:disabled):bg-gray-50 hover:not(:disabled):border-primary-light hover:not(:disabled):text-gray-800 hover:not(:disabled):-translate-y-px active:not(:disabled):translate-y-0 disabled:bg-gray-100 disabled:text-gray-500 disabled:cursor-not-allowed disabled:border-gray-100 max-md:w-full"
            onClick={handleReset}
            disabled={isLoading}
          >
            Reset
          </button>
        </div>

        {/* Force Refresh Option */}
        <div className="my-2 px-4 py-2 bg-primary/5 rounded-lg border border-primary/20">
          <label htmlFor="force_refresh" className="flex items-center gap-2 cursor-pointer px-2 py-1 mb-0 select-none">
            <input
              type="checkbox"
              id="force_refresh"
              name="force_refresh"
              checked={formData.force_refresh}
              onChange={handleChange}
              disabled={isLoading}
              className="w-5 h-5 cursor-pointer accent-primary flex-shrink-0 m-0 disabled:cursor-not-allowed disabled:opacity-60"
            />
            <span className="text-base font-medium text-gray-800 flex-1">🔄 Force refresh (bypass cache and get fresh results)</span>
          </label>
          <p className="mt-1 mb-0 text-xs text-gray-600 leading-relaxed">Check this to ignore cached results and search for the latest resources. This may take longer but ensures you get the most up-to-date results.</p>
        </div>

        {/* Search Parameters Section */}
        <div className="flex flex-col gap-0 p-0 bg-gray-50 rounded-lg border border-gray-100 overflow-hidden transition-all hover:border-primary-light">
          <div className="flex items-center justify-between px-4 py-4 cursor-pointer select-none transition-colors hover:bg-gray-100">
            <h3 className="m-0 text-base font-bold text-gray-800 flex items-center gap-2 tracking-tight">📚 Course Details <span className="text-red-600 font-bold">*</span></h3>
          </div>

          <div className="px-4 pb-4 flex flex-col gap-4 animate-[slideDown_0.2s_ease-out]">
              <div className="flex flex-col gap-1">
                <label htmlFor="search_param_type" className="text-sm font-semibold text-gray-800 flex items-center gap-1">Search Parameters <span className="text-red-600 font-bold">*</span></label>
                <select
                  id="search_param_type"
                  name="search_param_type"
                  value={searchParamType}
                  onChange={handleSearchParamChange}
                  disabled={isLoading}
                  className="font-medium px-3.5 py-2.5 border-2 border-gray-200 rounded-lg text-sm transition-all bg-white text-gray-800 cursor-pointer appearance-none bg-[url('data:image/svg+xml,%3Csvg_xmlns=%27http://www.w3.org/2000/svg%27_width=%2712%27_height=%2712%27_viewBox=%270_0_12_12%27%3E%3Cpath_fill=%27%236b7280%27_d=%27M6_9L1_4h10z%27/%3E%3C/svg%3E')] bg-no-repeat bg-[right_16px_center] pr-10 focus:outline-none focus:border-primary focus:shadow-[0_0_0_4px_rgba(99,102,241,0.1)] focus:-translate-y-px hover:not(:disabled):not(:focus):border-primary-light disabled:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  <option value="">-- Select a search type --</option>
                  <option value="course_url">Course URL</option>
                  <option value="book_url">Book URL</option>
                  <option value="book_title_author">Book Title and Author</option>
                  <option value="isbn">Book ISBN</option>
                </select>
              </div>

              {/* Course URL - shown when "Course URL" is selected */}
              {searchParamType === 'course_url' && (
                <div className="flex flex-col gap-1">
                  <label htmlFor="course_url" className="text-sm font-semibold text-gray-800 flex items-center gap-1">Course URL <span className="text-red-600 font-bold">*</span></label>
                  <input
                    type="url"
                    id="course_url"
                    name="course_url"
                    value={formData.course_url}
                    onChange={handleChange}
                    placeholder="https://ocw.mit.edu/courses/..."
                    disabled={isLoading}
                    required
                    className="px-3.5 py-2.5 border-2 border-gray-200 rounded-lg text-sm transition-all bg-white text-gray-800 focus:outline-none focus:border-primary focus:shadow-[0_0_0_4px_rgba(99,102,241,0.1)] focus:-translate-y-px hover:not(:disabled):not(:focus):border-primary-light disabled:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-70"
                  />
                </div>
              )}

              {/* Book URL - shown when "Book URL" is selected */}
              {searchParamType === 'book_url' && (
                <div className="flex flex-col gap-1">
                  <label htmlFor="book_url" className="text-sm font-semibold text-gray-800 flex items-center gap-1">Book URL <span className="text-red-600 font-bold">*</span></label>
                  <input
                    type="url"
                    id="book_url"
                    name="book_url"
                    value={formData.book_url}
                    onChange={handleChange}
                    placeholder="https://..."
                    disabled={isLoading}
                    required
                    className="px-3.5 py-2.5 border-2 border-gray-200 rounded-lg text-sm transition-all bg-white text-gray-800 focus:outline-none focus:border-primary focus:shadow-[0_0_0_4px_rgba(99,102,241,0.1)] focus:-translate-y-px hover:not(:disabled):not(:focus):border-primary-light disabled:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-70"
                  />
                </div>
              )}

              {/* Book Title and Author - shown when "Book Title and Author" is selected */}
              {searchParamType === 'book_title_author' && (
                <>
                  <div className="flex flex-col gap-1">
                    <label htmlFor="book_title" className="text-sm font-semibold text-gray-800 flex items-center gap-1">Book Title <span className="text-red-600 font-bold">*</span></label>
                    <input
                      type="text"
                      id="book_title"
                      name="book_title"
                      value={formData.book_title}
                      onChange={handleChange}
                      placeholder="e.g., Introduction to Algorithms"
                      disabled={isLoading}
                      required
                      className="px-3.5 py-2.5 border-2 border-gray-200 rounded-lg text-sm transition-all bg-white text-gray-800 focus:outline-none focus:border-primary focus:shadow-[0_0_0_4px_rgba(99,102,241,0.1)] focus:-translate-y-px hover:not(:disabled):not(:focus):border-primary-light disabled:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-70"
                    />
                  </div>

                  <div className="flex flex-col gap-1">
                    <label htmlFor="book_author" className="text-sm font-semibold text-gray-800 flex items-center gap-1">Book Author(s) <span className="text-red-600 font-bold">*</span></label>
                    <input
                      type="text"
                      id="book_author"
                      name="book_author"
                      value={formData.book_author}
                      onChange={handleChange}
                      placeholder="e.g., Cormen, Leiserson, Rivest, Stein"
                      disabled={isLoading}
                      required
                      className="px-3.5 py-2.5 border-2 border-gray-200 rounded-lg text-sm transition-all bg-white text-gray-800 focus:outline-none focus:border-primary focus:shadow-[0_0_0_4px_rgba(99,102,241,0.1)] focus:-translate-y-px hover:not(:disabled):not(:focus):border-primary-light disabled:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-70"
                    />
                  </div>
                </>
              )}

              {/* ISBN - shown when "Book ISBN" is selected */}
              {searchParamType === 'isbn' && (
                <div className="flex flex-col gap-1">
                  <label htmlFor="isbn" className="text-sm font-semibold text-gray-800 flex items-center gap-1">Book ISBN <span className="text-red-600 font-bold">*</span></label>
                  <input
                    type="text"
                    id="isbn"
                    name="isbn"
                    value={formData.isbn}
                    onChange={handleChange}
                    placeholder="e.g., 978-0262046305"
                    disabled={isLoading}
                    required
                    className="px-3.5 py-2.5 border-2 border-gray-200 rounded-lg text-sm transition-all bg-white text-gray-800 focus:outline-none focus:border-primary focus:shadow-[0_0_0_4px_rgba(99,102,241,0.1)] focus:-translate-y-px hover:not(:disabled):not(:focus):border-primary-light disabled:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-70"
                  />
                </div>
              )}
            </div>
        </div>

        {/* Desired Resources Section */}
        <div className="flex flex-col gap-0 p-0 bg-gray-50 rounded-lg border border-gray-100 overflow-hidden transition-all hover:border-primary-light">
          <div className="flex items-center justify-between px-4 py-4 cursor-pointer select-none transition-colors hover:bg-gray-100" onClick={() => setIsDesiredResourcesExpanded(!isDesiredResourcesExpanded)}>
            <h3 className="m-0 text-base font-bold text-gray-800 flex items-center gap-2 tracking-tight">🎯 Resource Types <span className="font-normal text-gray-500 text-sm ml-1">(Optional)</span></h3>
            <button type="button" className="w-7 h-7 flex items-center justify-center bg-white border-2 border-gray-200 rounded text-primary text-lg font-bold cursor-pointer transition-all p-0 leading-none hover:bg-primary hover:text-white hover:border-primary hover:scale-110" aria-label="Toggle section">
              {isDesiredResourcesExpanded ? '▼' : '▶'}
            </button>
          </div>

          {isDesiredResourcesExpanded && (
            <div className="px-4 pb-4 flex flex-col gap-4 animate-[slideDown_0.2s_ease-out]">
              <div className="flex flex-col gap-1 mb-0">
                <label className="text-sm font-semibold text-gray-800 flex items-center gap-1 mb-1">Filter by resource type (leave empty to find all types):</label>
                <div className="flex flex-col gap-1 mt-1 mb-0">
                  <label className="flex items-center gap-2 cursor-pointer px-4 py-1 rounded-lg transition-all select-none hover:bg-gray-50 has-[:checked]:bg-primary/10 has-[:checked]:border-l-[3px] has-[:checked]:border-primary">
                    <input
                      type="checkbox"
                      checked={formData.desired_resource_types?.includes('textbooks') || false}
                      onChange={() => handleResourceTypeChange('textbooks')}
                      disabled={isLoading}
                      className="w-5 h-5 cursor-pointer accent-primary flex-shrink-0 m-0 disabled:cursor-not-allowed disabled:opacity-60"
                    />
                    <span className="text-base font-medium text-gray-800 flex-1">📚 Textbooks</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer px-4 py-1 rounded-lg transition-all select-none hover:bg-gray-50 has-[:checked]:bg-primary/10 has-[:checked]:border-l-[3px] has-[:checked]:border-primary">
                    <input
                      type="checkbox"
                      checked={formData.desired_resource_types?.includes('practice_problem_sets') || false}
                      onChange={() => handleResourceTypeChange('practice_problem_sets')}
                      disabled={isLoading}
                      className="w-5 h-5 cursor-pointer accent-primary flex-shrink-0 m-0 disabled:cursor-not-allowed disabled:opacity-60"
                    />
                    <span className="text-base font-medium text-gray-800 flex-1">📐 Practice Problem Sets</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer px-4 py-1 rounded-lg transition-all select-none hover:bg-gray-50 has-[:checked]:bg-primary/10 has-[:checked]:border-l-[3px] has-[:checked]:border-primary">
                    <input
                      type="checkbox"
                      checked={formData.desired_resource_types?.includes('practice_exams_tests') || false}
                      onChange={() => handleResourceTypeChange('practice_exams_tests')}
                      disabled={isLoading}
                      className="w-5 h-5 cursor-pointer accent-primary flex-shrink-0 m-0 disabled:cursor-not-allowed disabled:opacity-60"
                    />
                    <span className="text-base font-medium text-gray-800 flex-1">📋 Practice Exams/Tests</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer px-4 py-1 rounded-lg transition-all select-none hover:bg-gray-50 has-[:checked]:bg-primary/10 has-[:checked]:border-l-[3px] has-[:checked]:border-primary">
                    <input
                      type="checkbox"
                      checked={formData.desired_resource_types?.includes('lecture_videos') || false}
                      onChange={() => handleResourceTypeChange('lecture_videos')}
                      disabled={isLoading}
                      className="w-5 h-5 cursor-pointer accent-primary flex-shrink-0 m-0 disabled:cursor-not-allowed disabled:opacity-60"
                    />
                    <span className="text-base font-medium text-gray-800 flex-1">🎥 Lecture Videos</span>
                  </label>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Focus Topics Section */}
        <div className="flex flex-col gap-0 p-0 bg-gray-50 rounded-lg border border-gray-100 overflow-hidden transition-all hover:border-primary-light">
          <div className="flex items-center justify-between px-4 py-4 cursor-pointer select-none transition-colors hover:bg-gray-100" onClick={() => setIsFocusTopicsExpanded(!isFocusTopicsExpanded)}>
            <h3 className="m-0 text-base font-bold text-gray-800 flex items-center gap-2 tracking-tight">🎯 Focus Topics <span className="font-normal text-gray-500 text-sm ml-1">(Optional)</span></h3>
            <button type="button" className="w-7 h-7 flex items-center justify-center bg-white border-2 border-gray-200 rounded text-primary text-lg font-bold cursor-pointer transition-all p-0 leading-none hover:bg-primary hover:text-white hover:border-primary hover:scale-110" aria-label="Toggle section">
              {isFocusTopicsExpanded ? '▼' : '▶'}
            </button>
          </div>

          {isFocusTopicsExpanded && (
            <div className="px-4 pb-4 flex flex-col gap-4 animate-[slideDown_0.2s_ease-out]">
              {/* Topics List */}
              <div className="flex flex-col gap-1">
                <label htmlFor="topics_list" className="text-sm font-semibold text-gray-800 flex items-center gap-1">Topics List</label>
                <textarea
                  id="topics_list"
                  name="topics_list"
                  value={formData.topics_list}
                  onChange={handleChange}
                  placeholder="e.g., Midterm review, Chapter 4, Dynamic programming, Sorting algorithms"
                  rows="2"
                  disabled={isLoading}
                  className="resize-y min-h-[55px] px-3.5 py-2.5 border-2 border-gray-200 rounded-lg text-sm transition-all bg-white text-gray-800 focus:outline-none focus:border-primary focus:shadow-[0_0_0_4px_rgba(99,102,241,0.1)] focus:-translate-y-px hover:not(:disabled):not(:focus):border-primary-light disabled:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-70"
                />
                <div className="px-2 py-2 bg-gradient-to-r from-amber-100 to-amber-200 border-l-4 border-amber-500 rounded-lg mt-1">
                  <p className="m-0 text-xs text-amber-900 leading-relaxed">
                    <strong className="text-amber-950 font-semibold">💡 Tip:</strong> Add 3–6 topics like 'Midterm review', 'Chapter 4', or 'Dynamic programming' for better matches.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Email Section - COMMENTED OUT */}
        {/* <div className="form-section">
          <div className="section-header" onClick={() => setIsEmailExpanded(!isEmailExpanded)}>
            <h3>📧 Get Results by Email <span className="optional-label">(Optional)</span></h3>
            <button type="button" className="collapse-toggle" aria-label="Toggle section">
              {isEmailExpanded ? '▼' : '▶'}
            </button>
          </div>

          {isEmailExpanded && (
            <div className="section-content">
              <div className="form-group">
                <label htmlFor="email">Email Address</label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="your.email@example.com"
                  disabled={isLoading}
                />
                <p className="field-hint">
                  We'll email you the results when your search completes (usually 1-5 minutes)
                </p>
              </div>
            </div>
          )}
        </div> */}

        {/* Validation Error */}
        {validationError && (
          <div className="px-4 py-4 bg-red-50 border-2 border-red-200 border-l-4 border-l-red-600 rounded-lg text-red-600 text-sm font-medium">
            {validationError}
          </div>
        )}
      </form>
    </div>
  );
}
