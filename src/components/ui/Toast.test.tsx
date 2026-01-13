import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '../../test/utils';
import userEvent from '@testing-library/user-event';
import { Toast } from './Toast';

describe('Toast Component', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  const defaultProps = {
    id: 'toast-1',
    message: 'Test notification',
    onClose: vi.fn(),
  };

  it('renders with message', () => {
    render(<Toast {...defaultProps} />);
    expect(screen.getByText('Test notification')).toBeInTheDocument();
  });

  it('renders with default info variant', () => {
    const { container } = render(<Toast {...defaultProps} />);
    const toast = container.querySelector('.toast-info');
    expect(toast).toBeInTheDocument();
  });

  it('renders with success variant', () => {
    const { container } = render(<Toast {...defaultProps} variant="success" />);
    const toast = container.querySelector('.toast-success');
    expect(toast).toBeInTheDocument();
  });

  it('renders with error variant', () => {
    const { container } = render(<Toast {...defaultProps} variant="error" />);
    const toast = container.querySelector('.toast-error');
    expect(toast).toBeInTheDocument();
  });

  it('renders with warning variant', () => {
    const { container } = render(<Toast {...defaultProps} variant="warning" />);
    const toast = container.querySelector('.toast-warning');
    expect(toast).toBeInTheDocument();
  });

  it('has correct ARIA attributes', () => {
    const { container } = render(<Toast {...defaultProps} />);
    const toast = container.querySelector('[role="alert"]');
    expect(toast).toBeInTheDocument();
    expect(toast).toHaveAttribute('aria-live', 'polite');
  });

  it('calls onClose when close button is clicked', async () => {
    const user = userEvent.setup({ delay: null });
    const onClose = vi.fn();
    render(<Toast {...defaultProps} onClose={onClose} />);

    const closeButton = screen.getByRole('button', { name: /close notification/i });
    await user.click(closeButton);

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledWith('toast-1');
  });

  it('auto-dismisses after default duration (5000ms)', () => {
    const onClose = vi.fn();
    render(<Toast {...defaultProps} onClose={onClose} />);

    expect(onClose).not.toHaveBeenCalled();

    vi.advanceTimersByTime(5000);

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledWith('toast-1');
  });

  it('auto-dismisses after custom duration', () => {
    const onClose = vi.fn();
    render(<Toast {...defaultProps} duration={3000} onClose={onClose} />);

    expect(onClose).not.toHaveBeenCalled();

    vi.advanceTimersByTime(2999);
    expect(onClose).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('does not auto-dismiss when duration is 0', () => {
    const onClose = vi.fn();
    render(<Toast {...defaultProps} duration={0} onClose={onClose} />);

    vi.advanceTimersByTime(10000);

    expect(onClose).not.toHaveBeenCalled();
  });

  it('renders action button when provided', () => {
    const action = {
      label: 'Undo',
      onClick: vi.fn(),
    };
    render(<Toast {...defaultProps} action={action} />);

    expect(screen.getByRole('button', { name: /undo/i })).toBeInTheDocument();
  });

  it('calls action onClick when action button is clicked', async () => {
    const user = userEvent.setup({ delay: null });
    const actionOnClick = vi.fn();
    const action = {
      label: 'Undo',
      onClick: actionOnClick,
    };
    render(<Toast {...defaultProps} action={action} />);

    const actionButton = screen.getByRole('button', { name: /undo/i });
    await user.click(actionButton);

    expect(actionOnClick).toHaveBeenCalledTimes(1);
  });

  it('does not render action button when not provided', () => {
    render(<Toast {...defaultProps} />);

    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(1); // Only close button
    expect(buttons[0]).toHaveAttribute('aria-label', 'Close notification');
  });

  it('renders appropriate icon for each variant', () => {
    const { container, rerender } = render(<Toast {...defaultProps} variant="success" />);
    let icon = container.querySelector('.toast-icon svg');
    expect(icon).toBeInTheDocument();

    rerender(<Toast {...defaultProps} variant="error" />);
    icon = container.querySelector('.toast-icon svg');
    expect(icon).toBeInTheDocument();

    rerender(<Toast {...defaultProps} variant="warning" />);
    icon = container.querySelector('.toast-icon svg');
    expect(icon).toBeInTheDocument();

    rerender(<Toast {...defaultProps} variant="info" />);
    icon = container.querySelector('.toast-icon svg');
    expect(icon).toBeInTheDocument();
  });

  it('cleans up timer on unmount', () => {
    const onClose = vi.fn();
    const { unmount } = render(<Toast {...defaultProps} onClose={onClose} />);

    unmount();
    vi.advanceTimersByTime(5000);

    expect(onClose).not.toHaveBeenCalled();
  });

  it('resets timer when duration changes', () => {
    const onClose = vi.fn();
    const { rerender } = render(<Toast {...defaultProps} duration={5000} onClose={onClose} />);

    vi.advanceTimersByTime(3000);

    rerender(<Toast {...defaultProps} duration={2000} onClose={onClose} />);

    vi.advanceTimersByTime(2000);

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
