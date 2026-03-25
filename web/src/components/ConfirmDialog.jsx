/**
 * ConfirmDialog Component
 *
 * A styled confirmation dialog that matches the app's design system.
 * Replaces the browser's default confirm() with a custom modal.
 */

export default function ConfirmDialog({
  isOpen,
  title,
  message,
  onConfirm,
  onCancel,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  isDanger = false
}) {
  if (!isOpen) return null;

  return (
    <div className="confirm-dialog-backdrop">
      <div role="dialog" aria-modal="true" aria-labelledby="confirm-dialog-title" className="confirm-dialog-content">
        <h3 id="confirm-dialog-title" className="confirm-dialog-title">
          {title}
        </h3>

        <p className="confirm-dialog-message">
          {message}
        </p>

        <div className="confirm-dialog-actions">
          <button
            onClick={onCancel}
            type="button"
            className="confirm-dialog-btn-cancel"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            type="button"
            className={`confirm-dialog-btn-confirm ${
              isDanger
                ? 'confirm-dialog-btn-confirm-danger'
                : 'confirm-dialog-btn-confirm-normal'
            }`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
