import { useState } from 'react';
import styles from './ObservationsPanel.module.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function ObservationsPanel({ personId, trackingId, onClose, onSaved }) {
  const [formData, setFormData] = useState({
    observation_type: 'note',
    title: '',
    description: '',
    severity: 'info',
    recorded_by: 'operator',
    requires_followup: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.description.trim()) {
      setError('Description is required');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      let url;
      if (personId) {
        url = `${API_BASE_URL}/api/observations/person/${personId}`;
      } else if (trackingId) {
        url = `${API_BASE_URL}/api/observations/tracking/${trackingId}`;
      } else {
        setError('Either person ID or tracking ID is required');
        return;
      }

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save observation');
      }

      const result = await response.json();

      // Reset form
      setFormData({
        observation_type: 'note',
        title: '',
        description: '',
        severity: 'info',
        recorded_by: 'operator',
        requires_followup: false,
      });

      // Notify parent
      if (onSaved) {
        onSaved(result);
      }

      // Show success message
      alert('Observation saved successfully!');

      // Close modal if requested
      if (onClose) {
        onClose();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={styles.modal} onClick={onClose}>
      <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2 className={styles.title}>Add Manual Observation</h2>
          <button onClick={onClose} className={styles.closeButton}>×</button>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          {error && (
            <div className={styles.errorBanner}>{error}</div>
          )}

          <div className={styles.formGroup}>
            <label className={styles.label}>
              Observation Type
              <select
                name="observation_type"
                value={formData.observation_type}
                onChange={handleChange}
                className={styles.select}
                required
              >
                <option value="note">Note</option>
                <option value="issue">Issue</option>
                <option value="feedback">Feedback</option>
                <option value="action_taken">Action Taken</option>
              </select>
            </label>
          </div>

          <div className={styles.formGroup}>
            <label className={styles.label}>
              Title (Optional)
              <input
                type="text"
                name="title"
                value={formData.title}
                onChange={handleChange}
                className={styles.input}
                placeholder="Brief title for the observation"
              />
            </label>
          </div>

          <div className={styles.formGroup}>
            <label className={styles.label}>
              Description *
              <textarea
                name="description"
                value={formData.description}
                onChange={handleChange}
                className={styles.textarea}
                placeholder="Detailed description of your observation..."
                rows={5}
                required
              />
            </label>
          </div>

          <div className={styles.formRow}>
            <div className={styles.formGroup}>
              <label className={styles.label}>
                Severity
                <select
                  name="severity"
                  value={formData.severity}
                  onChange={handleChange}
                  className={styles.select}
                >
                  <option value="info">Info</option>
                  <option value="warning">Warning</option>
                  <option value="critical">Critical</option>
                </select>
              </label>
            </div>

            <div className={styles.formGroup}>
              <label className={styles.label}>
                Recorded By
                <input
                  type="text"
                  name="recorded_by"
                  value={formData.recorded_by}
                  onChange={handleChange}
                  className={styles.input}
                  placeholder="Your name or role"
                />
              </label>
            </div>
          </div>

          <div className={styles.checkboxGroup}>
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                name="requires_followup"
                checked={formData.requires_followup}
                onChange={handleChange}
                className={styles.checkbox}
              />
              Requires Follow-up
            </label>
          </div>

          <div className={styles.infoBox}>
            <strong>Target:</strong>{' '}
            {personId ? `Person ID: ${personId}` : `Tracking ID: ${trackingId}`}
          </div>

          <div className={styles.actions}>
            <button
              type="button"
              onClick={onClose}
              className={styles.cancelButton}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className={styles.submitButton}
              disabled={submitting}
            >
              {submitting ? 'Saving...' : 'Save Observation'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default ObservationsPanel;
