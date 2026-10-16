import { useState, useMemo, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { eventsApi, aiApi } from '../services/api';
import './CreateEventPage.css';

const CATEGORIES = [
  'Workshop',
  'Hackathon',
  'Seminar',
  'Competition',
  'Conference',
  'Cultural',
  'Sports',
  'Other',
];

export default function CreateEventPage() {
  const { user, token, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const { eventId } = useParams();
  const isEditMode = !!eventId;

  const minDate = useMemo(() => new Date().toISOString().split('T')[0], []);
  const minDateTime = useMemo(() => new Date().toISOString().slice(0, 16), []);

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    category: '',
    organization: '',
    venue: '',
    date: '',
    start_time: '',
    end_time: '',
    tags: '',
    registration_deadline: '',
    registration_link: '',
    eligibility: '',
    capacity: '',
    poster_url: '',
    contact_email: '',
    online_meeting_url: '',
    speaker_info: '',
    additional_instructions: '',
  });

  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [isLoading, setIsLoading] = useState(isEditMode);
  
  // AI extraction state
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractError, setExtractError] = useState('');
  const [extractWarnings, setExtractWarnings] = useState([]);
  const announcementRef = useRef(null);

  // Load event data in edit mode
  useEffect(() => {
    if (isEditMode) {
      const loadEvent = async () => {
        try {
          const event = await eventsApi.getOrganizerEvent(eventId, token);
          // Convert date to YYYY-MM-DD format for date input
          const eventDate = event.date ? event.date.split('T')[0] : '';
          // Convert datetime-local format for registration_deadline
          const regDeadline = event.registration_deadline 
            ? event.registration_deadline.replace('Z', '').replace('+00:00', '')
            : '';
          
          setFormData({
            title: event.title || '',
            description: event.description || '',
            category: event.category || '',
            venue: event.venue || '',
            date: eventDate,
            start_time: event.start_time || '',
            end_time: event.end_time || '',
            tags: Array.isArray(event.tags) ? event.tags.join(', ') : '',
            registration_deadline: regDeadline,
            registration_link: event.registration_link || '',
            eligibility: event.eligibility || '',
            capacity: event.capacity || '',
            poster_url: event.poster_url || '',
            contact_email: event.contact_email || '',
            online_meeting_url: event.online_meeting_url || '',
            speaker_info: event.speaker_info || '',
            additional_instructions: event.additional_instructions || '',
          });
        } catch (err) {
          setSubmitError(err.message || 'Failed to load event. Please try again.');
        } finally {
          setIsLoading(false);
        }
      };
      loadEvent();
    }
  }, [eventId, token, isEditMode]);

  const validateForm = () => {
    const newErrors = {};

    if (!formData.title.trim()) {
      newErrors.title = 'Event title is required';
    }

    if (!formData.category) {
      newErrors.category = 'Category is required';
    }

    if (!formData.venue.trim()) {
      newErrors.venue = 'Venue is required';
    }

    if (!formData.date) {
      newErrors.date = 'Event date is required';
    }

    if (!formData.start_time) {
      newErrors.start_time = 'Start time is required';
    }

    if (!formData.end_time) {
      newErrors.end_time = 'End time is required';
    }

    if (formData.start_time && formData.end_time && formData.end_time <= formData.start_time) {
      newErrors.end_time = 'End time must be after start time';
    }

    if (formData.registration_deadline && formData.date && formData.start_time) {
      const deadline = new Date(formData.registration_deadline);
      const eventStart = new Date(`${formData.date}T${formData.start_time}`);
      if (deadline > eventStart) {
        newErrors.registration_deadline = 'Registration deadline must be before event start time';
      }
    }

    if (formData.registration_link && !isValidUrl(formData.registration_link)) {
      newErrors.registration_link = 'Please enter a valid URL';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const isValidUrl = (string) => {
    try {
      new URL(string);
      return true;
    } catch {
      return false;
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
    if (submitError) {
      setSubmitError('');
    }
  };

  // AI Extraction from announcement text
  const handleExtractFromAnnouncement = async (e) => {
    e.preventDefault();
    
    const announcementText = announcementRef.current?.value?.trim();
    if (!announcementText) {
      setExtractError('Please enter an announcement text to extract event details from.');
      return;
    }

    setIsExtracting(true);
    setExtractError('');
    setExtractWarnings([]);

    try {
      const result = await aiApi.extractEvent(announcementText, token);
      
      if (result.extracted_data) {
        const data = result.extracted_data;
        
        // Map extracted data to form fields
        const updates = {};
        if (data.title) updates.title = data.title;
        if (data.description) updates.description = data.description;
        else if (data.details) updates.description = data.details;
        if (data.category) updates.category = data.category;
        if (data.organization) updates.organization = data.organization;
        if (data.venue) updates.venue = data.venue;
        if (data.date) updates.date = data.date.split('T')[0]; // ISO date to YYYY-MM-DD
        if (data.start_time) updates.start_time = data.start_time;
        if (data.end_time) updates.end_time = data.end_time;
        if (data.tags && data.tags.length > 0) updates.tags = data.tags.join(', ');
        if (data.registration_deadline) {
          // Convert to datetime-local format
          const deadline = new Date(data.registration_deadline);
          updates.registration_deadline = deadline.toISOString().slice(0, 16);
        }
        if (data.registration_link) updates.registration_link = data.registration_link;
        if (data.eligibility) updates.eligibility = data.eligibility;
        if (data.capacity) updates.capacity = data.capacity.toString();
        if (data.contact_email) updates.contact_email = data.contact_email;
        if (data.online_meeting_url) updates.online_meeting_url = data.online_meeting_url;
        if (data.speaker_info) updates.speaker_info = data.speaker_info;
        if (data.additional_instructions) updates.additional_instructions = data.additional_instructions;
        
        setFormData(prev => ({ ...prev, ...updates }));
        
        // Clear errors for filled fields
        const errorKeys = Object.keys(errors);
        const filledKeys = Object.keys(updates);
        if (errorKeys.length > 0 && filledKeys.length > 0) {
          setErrors(prev => {
            const newErrors = { ...prev };
            filledKeys.forEach(key => delete newErrors[key]);
            return newErrors;
          });
        }
        
        // Show warnings if any
        if (result.warnings && result.warnings.length > 0) {
          setExtractWarnings(result.warnings);
        }
        
        // Show confidence
        const confidence = Math.round((result.confidence || 0) * 100);
        if (confidence > 0) {
          setExtractError(`Extracted with ${confidence}% confidence. Please review and edit as needed.`);
        } else {
          setExtractError('Extraction completed. Please review all fields carefully.');
        }
      }
    } catch (err) {
      setExtractError(err.message || 'Failed to extract event data. Please try again.');
    } finally {
      setIsExtracting(false);
    }
  };

  const buildPayload = () => {
    const deadline = formData.registration_deadline;
    let formattedDeadline = undefined;
    if (deadline) {
      // datetime-local input gives YYYY-MM-DDTHH:MM or YYYY-MM-DDTHH:MM:SS
      // Ensure we have seconds but not double seconds
      if (deadline.match(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/)) {
        formattedDeadline = `${deadline}:00`;
      } else if (deadline.match(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/)) {
        formattedDeadline = deadline;
      } else {
        formattedDeadline = deadline;
      }
    }

    return {
      title: formData.title.trim(),
      description: formData.description.trim() || undefined,
      category: formData.category,
      organization: formData.organization?.trim() || undefined,
      venue: formData.venue.trim(),
      date: formData.date,
      start_time: formData.start_time,
      end_time: formData.end_time,
      tags: formData.tags
        ? formData.tags.split(',').map(t => t.trim()).filter(Boolean)
        : [],
      registration_deadline: formattedDeadline,
      registration_link: formData.registration_link.trim() || undefined,
      eligibility: formData.eligibility.trim() || undefined,
      capacity: formData.capacity ? parseInt(formData.capacity, 10) : undefined,
      poster_url: formData.poster_url.trim() || undefined,
      contact_email: formData.contact_email.trim() || undefined,
      online_meeting_url: formData.online_meeting_url.trim() || undefined,
      speaker_info: formData.speaker_info.trim() || undefined,
      additional_instructions: formData.additional_instructions.trim() || undefined,
    };
  };

  const handleSaveDraft = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    setSubmitError('');

    try {
      const payload = buildPayload();

      if (isEditMode) {
        await eventsApi.updateEvent(eventId, payload, token);
        navigate('/organizer', { state: { successMessage: 'Event updated successfully!' } });
      } else {
        await eventsApi.createEvent(payload, token);
        navigate('/organizer', { state: { successMessage: 'Event created successfully!' } });
      }
    } catch (err) {
      setSubmitError(err.message || `Failed to ${isEditMode ? 'update' : 'create'} event. Please try again.`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePublish = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    // In create mode, we need to save first, then publish
    // In edit mode, we can publish directly if it's a draft
    setIsSubmitting(true);
    setSubmitError('');

    try {
      const payload = buildPayload();

      if (isEditMode) {
        // For edit mode, save the draft first, then publish
        await eventsApi.updateEvent(eventId, payload, token);
        await eventsApi.publishEvent(eventId, token);
      } else {
        // For create mode, create the event, then publish
        const response = await eventsApi.createEvent(payload, token);
        await eventsApi.publishEvent(response.id, token);
      }
      navigate('/organizer', { state: { successMessage: 'Event published successfully!' } });
    } catch (err) {
      setSubmitError(err.message || 'Failed to publish event. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isAuthenticated || user?.role !== 'ORGANIZER') {
    return (
      <div className="page-layout">
        <div className="container" style={{ textAlign: 'center', padding: 'var(--space-16) 0' }}>
          <h1 className="font-display text-3xl font-bold" style={{ marginBottom: 'var(--space-4)' }}>
            Access Denied
          </h1>
          <p className="text-secondary">
            You must be logged in as an organizer to create events.
          </p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="page-layout">
        <div className="container" style={{ textAlign: 'center', padding: 'var(--space-16) 0' }}>
          <p className="text-secondary">Loading event...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-layout">
      <div className="container page-content">
        <div className="create-event-header">
          <h1 className="font-display text-2xl font-bold">
            {isEditMode ? 'Edit Event' : 'Create New Event'}
          </h1>
          <p className="text-secondary">
            {isEditMode
              ? 'Update the event details below. Changes are saved as a draft.'
              : 'Fill in the details below to create a new event draft.'}
          </p>
        </div>

        {submitError && (
          <div className="alert alert-error" role="alert">
            {submitError}
          </div>
        )}

        {/* AI Extraction from Announcement */}
        <div className="ai-extraction-section">
          <h3 className="ai-extraction-title">🤖 Extract from Announcement</h3>
          <p className="ai-extraction-description">
            Paste an event announcement, email, or poster text below and let AI fill in the form for you.
          </p>
          <form onSubmit={handleExtractFromAnnouncement} className="ai-extraction-form">
            <textarea
              ref={announcementRef}
              className="ai-extraction-textarea"
              placeholder="Paste event announcement text here...&#10;&#10;Example: Join us for the AI Hackathon on March 15th at 10 AM in the Main Auditorium. Open to all CS students. Register by March 10th at https://example.com/register"
              rows={4}
              disabled={isExtracting}
            />
            <div className="ai-extraction-actions">
              <button
                type="submit"
                className="btn btn-secondary"
                disabled={isExtracting}
              >
                {isExtracting ? 'Extracting...' : 'Extract Event Details'}
              </button>
            </div>
            {extractError && (
              <div className={`ai-extraction-message ${extractError.startsWith('Extracted') || extractError.startsWith('Failed') ? 'warning' : 'error'}`}>
                {extractError}
              </div>
            )}
            {extractWarnings.length > 0 && (
              <div className="ai-extraction-warnings">
                <strong>⚠️ Review needed:</strong>
                <ul>
                  {extractWarnings.map((w, i) => (
                    <li key={i}>{w.field}: {w.message}</li>
                  ))}
                </ul>
              </div>
            )}
          </form>
        </div>

        <form onSubmit={handleSaveDraft} className="create-event-form" noValidate>
          <div className="form-section">
            <h2 className="form-section-title">Basic Information</h2>

            <div className="form-group">
              <label htmlFor="title" className="form-label required">Event Title</label>
              <input
                type="text"
                id="title"
                name="title"
                className={`form-input ${errors.title ? 'error' : ''}`}
                value={formData.title}
                onChange={handleChange}
                placeholder="Enter event title"
                maxLength={255}
                required
                disabled={isSubmitting}
              />
              {errors.title && <span className="form-error">{errors.title}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="description" className="form-label">Description</label>
              <textarea
                id="description"
                name="description"
                className="form-input form-textarea"
                value={formData.description}
                onChange={handleChange}
                placeholder="Describe your event..."
                rows={4}
                maxLength={5000}
                disabled={isSubmitting}
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="category" className="form-label required">Category</label>
                <select
                  id="category"
                  name="category"
                  className={`form-input ${errors.category ? 'error' : ''}`}
                  value={formData.category}
                  onChange={handleChange}
                  required
                  disabled={isSubmitting}
                >
                  <option value="">Select category</option>
                  {CATEGORIES.map(cat => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
                {errors.category && <span className="form-error">{errors.category}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="venue" className="form-label required">Venue / Location</label>
                <input
                  type="text"
                  id="venue"
                  name="venue"
                  className={`form-input ${errors.venue ? 'error' : ''}`}
                  value={formData.venue}
                  onChange={handleChange}
                  placeholder="e.g., Main Auditorium, Block A"
                  maxLength={255}
                  required
                  disabled={isSubmitting}
                />
                {errors.venue && <span className="form-error">{errors.venue}</span>}
              </div>
            </div>
          </div>

          <div className="form-section">
            <h2 className="form-section-title">Date & Time</h2>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="date" className="form-label required">Event Date</label>
                <input
                  type="date"
                  id="date"
                  name="date"
                  className={`form-input ${errors.date ? 'error' : ''}`}
                  value={formData.date}
                  onChange={handleChange}
                  min={minDate}
                  required
                  disabled={isSubmitting}
                />
                {errors.date && <span className="form-error">{errors.date}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="start_time" className="form-label required">Start Time</label>
                <input
                  type="time"
                  id="start_time"
                  name="start_time"
                  className={`form-input ${errors.start_time ? 'error' : ''}`}
                  value={formData.start_time}
                  onChange={handleChange}
                  required
                  disabled={isSubmitting}
                />
                {errors.start_time && <span className="form-error">{errors.start_time}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="end_time" className="form-label required">End Time</label>
                <input
                  type="time"
                  id="end_time"
                  name="end_time"
                  className={`form-input ${errors.end_time ? 'error' : ''}`}
                  value={formData.end_time}
                  onChange={handleChange}
                  required
                  disabled={isSubmitting}
                />
                {errors.end_time && <span className="form-error">{errors.end_time}</span>}
              </div>
            </div>
          </div>

          <div className="form-section">
            <h2 className="form-section-title">Registration Details</h2>

            <div className="form-group">
              <label htmlFor="registration_deadline" className="form-label">Registration Deadline</label>
              <input
                type="datetime-local"
                id="registration_deadline"
                name="registration_deadline"
                className={`form-input ${errors.registration_deadline ? 'error' : ''}`}
                value={formData.registration_deadline}
                onChange={handleChange}
                min={minDateTime}
                disabled={isSubmitting}
              />
              {errors.registration_deadline && <span className="form-error">{errors.registration_deadline}</span>}
              <p className="form-hint">Optional. Must be before event start time.</p>
            </div>

            <div className="form-group">
              <label htmlFor="registration_link" className="form-label">Registration Link</label>
              <input
                type="url"
                id="registration_link"
                name="registration_link"
                className={`form-input ${errors.registration_link ? 'error' : ''}`}
                value={formData.registration_link}
                onChange={handleChange}
                placeholder="https://example.com/register"
                maxLength={500}
                disabled={isSubmitting}
              />
              {errors.registration_link && <span className="form-error">{errors.registration_link}</span>}
              <p className="form-hint">Optional. External registration form URL.</p>
            </div>

            <div className="form-group">
              <label htmlFor="eligibility" className="form-label">Eligibility / Target Audience</label>
              <input
                type="text"
                id="eligibility"
                name="eligibility"
                className="form-input"
                value={formData.eligibility}
                onChange={handleChange}
                placeholder="e.g., All UG and PG students, CS students only, etc."
                maxLength={255}
                disabled={isSubmitting}
              />
              <p className="form-hint">Optional. Who can attend this event?</p>
            </div>

            <div className="form-group">
              <label htmlFor="tags" className="form-label">Tags</label>
              <input
                type="text"
                id="tags"
                name="tags"
                className="form-input"
                value={formData.tags}
                onChange={handleChange}
                placeholder="ai, workshop, hands-on, beginner-friendly"
                maxLength={500}
                disabled={isSubmitting}
              />
              <p className="form-hint">Optional. Comma-separated tags for discoverability.</p>
            </div>
          </div>

          <div className="form-section">
            <h2 className="form-section-title">Additional Details</h2>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="capacity" className="form-label">Capacity</label>
                <input
                  type="number"
                  id="capacity"
                  name="capacity"
                  className="form-input"
                  value={formData.capacity}
                  onChange={handleChange}
                  placeholder="e.g., 100"
                  min="1"
                  max="10000"
                  disabled={isSubmitting}
                />
                <p className="form-hint">Optional. Maximum number of attendees.</p>
              </div>

              <div className="form-group">
                <label htmlFor="contact_email" className="form-label">Contact Email</label>
                <input
                  type="email"
                  id="contact_email"
                  name="contact_email"
                  className="form-input"
                  value={formData.contact_email}
                  onChange={handleChange}
                  placeholder="organizer@example.com"
                  maxLength={255}
                  disabled={isSubmitting}
                />
                <p className="form-hint">Optional. Contact email for inquiries.</p>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="poster_url" className="form-label">Poster Image URL</label>
                <input
                  type="url"
                  id="poster_url"
                  name="poster_url"
                  className="form-input"
                  value={formData.poster_url}
                  onChange={handleChange}
                  placeholder="https://example.com/poster.jpg"
                  maxLength={500}
                  disabled={isSubmitting}
                />
                <p className="form-hint">Optional. URL to event poster image.</p>
              </div>

              <div className="form-group">
                <label htmlFor="online_meeting_url" className="form-label">Online Meeting URL</label>
                <input
                  type="url"
                  id="online_meeting_url"
                  name="online_meeting_url"
                  className="form-input"
                  value={formData.online_meeting_url}
                  onChange={handleChange}
                  placeholder="https://meet.example.com/event"
                  maxLength={500}
                  disabled={isSubmitting}
                />
                <p className="form-hint">Optional. For virtual/hybrid events.</p>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="speaker_info" className="form-label">Speaker Information</label>
              <textarea
                id="speaker_info"
                name="speaker_info"
                className="form-input form-textarea"
                value={formData.speaker_info}
                onChange={handleChange}
                placeholder="Speaker names, bios, topics..."
                rows={3}
                maxLength={2000}
                disabled={isSubmitting}
              />
              <p className="form-hint">Optional. Details about speakers/presenters.</p>
            </div>

            <div className="form-group">
              <label htmlFor="additional_instructions" className="form-label">Additional Instructions</label>
              <textarea
                id="additional_instructions"
                name="additional_instructions"
                className="form-input form-textarea"
                value={formData.additional_instructions}
                onChange={handleChange}
                placeholder="Special instructions for attendees (what to bring, preparation, etc.)"
                rows={3}
                maxLength={2000}
                disabled={isSubmitting}
              />
              <p className="form-hint">Optional. Any additional information for attendees.</p>
            </div>
          </div>

          <div className="form-actions">
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => navigate('/organizer')}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Saving...' : 'Save Draft'}
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handlePublish}
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Publishing...' : 'Publish Event'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}