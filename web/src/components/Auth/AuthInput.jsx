/**
 * AuthInput Component
 *
 * Labelled, icon-prefixed text/email/password input used in auth forms.
 * Keeps the shared structure (label, icon slot, input) in one place.
 */

export default function AuthInput({
  id,
  label,
  type = 'text',
  icon,
  value,
  onChange,
  placeholder,
  disabled = false,
  required = false,
  labelExtra,    // optional node rendered to the right of the label (e.g. "Forgot password?")
  children,      // optional content rendered below the input (e.g. password strength bar)
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label
          htmlFor={id}
          className="block text-xs font-semibold text-slate-500 uppercase tracking-wider"
        >
          {label}
        </label>
        {labelExtra}
      </div>
      <div className="relative">
        <span className="absolute inset-y-0 left-3 flex items-center text-slate-400 pointer-events-none">
          {icon}
        </span>
        <input
          id={id}
          type={type}
          required={required}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          disabled={disabled}
          className="w-full pl-10 pr-4 py-3 border border-slate-200 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-60 transition"
        />
      </div>
      {children}
    </div>
  );
}
