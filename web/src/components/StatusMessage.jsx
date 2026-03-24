/**
 * StatusMessage Component
 *
 * Displays status messages with different severities (error, warning, info, success).
 * Replaces the generic error-state div with a more flexible component.
 */

export default function StatusMessage({
  type = 'error',
  title,
  message,
  icon,
  actions
}) {
  if (!message && message !== 0) return null;

  const typeClass = `status-message-${type}`;

  // Default icons based on type
  const defaultIcons = {
    error: '⚠️',
    warning: '⚠️',
    info: 'ℹ️',
    success: '✓',
    cancelled: '🚫'
  };

  const displayIcon = icon || defaultIcons[type] || defaultIcons.info;

  return (
    <div className={`status-message ${typeClass}`}>
      <div className="status-message-icon" aria-hidden="true">
        {displayIcon}
      </div>
      <h2 className="status-message-title">
        {title}
      </h2>
      <p className="status-message-text">
        {message}
      </p>
      {actions && (
        <div className="status-message-actions">
          {actions}
        </div>
      )}
    </div>
  );
}
