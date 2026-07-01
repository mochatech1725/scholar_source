import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import AuthInput from './AuthInput';

describe('AuthInput', () => {
  it('renders label and input', () => {
    render(
      <AuthInput id="email" label="Email Address" type="email" icon="✉️"
        value="" onChange={() => {}} />
    );
    expect(screen.getByLabelText('Email Address')).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('associates label with input via id', () => {
    render(
      <AuthInput id="email" label="Email Address" type="email" icon="✉️"
        value="" onChange={() => {}} />
    );
    const input = screen.getByLabelText('Email Address');
    expect(input).toHaveAttribute('id', 'email');
  });

  it('passes type to input', () => {
    render(
      <AuthInput id="pw" label="Password" type="password" icon="🔒"
        value="" onChange={() => {}} />
    );
    expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'password');
  });

  it('calls onChange when user types', () => {
    const onChange = vi.fn();
    render(
      <AuthInput id="email" label="Email" type="email" icon="✉️"
        value="" onChange={onChange} />
    );
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'a@b.com' } });
    expect(onChange).toHaveBeenCalled();
  });

  it('disables input when disabled prop is true', () => {
    render(
      <AuthInput id="email" label="Email" type="email" icon="✉️"
        value="" onChange={() => {}} disabled />
    );
    expect(screen.getByRole('textbox')).toBeDisabled();
  });

  it('renders labelExtra alongside label', () => {
    render(
      <AuthInput id="pw" label="Password" type="password" icon="🔒"
        value="" onChange={() => {}}
        labelExtra={<button type="button">Forgot password?</button>}
      />
    );
    expect(screen.getByRole('button', { name: 'Forgot password?' })).toBeInTheDocument();
  });

  it('renders children below the input', () => {
    render(
      <AuthInput id="pw" label="Password" type="password" icon="🔒"
        value="" onChange={() => {}}>
        <p>Hint text</p>
      </AuthInput>
    );
    expect(screen.getByText('Hint text')).toBeInTheDocument();
  });

  it('toggles password visibility when enabled', () => {
    render(
      <AuthInput id="pw" label="Password" type="password" icon="🔒"
        value="secret" onChange={() => {}} showPasswordToggle />
    );

    const input = screen.getByLabelText('Password');
    expect(input).toHaveAttribute('type', 'password');

    fireEvent.click(screen.getByRole('button', { name: 'Show Password' }));
    expect(input).toHaveAttribute('type', 'text');

    fireEvent.click(screen.getByRole('button', { name: 'Hide Password' }));
    expect(input).toHaveAttribute('type', 'password');
  });
});
