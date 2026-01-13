import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '../../test/utils';
import userEvent from '@testing-library/user-event';
import { Card } from './Card';

describe('Card Component', () => {
  it('renders with children', () => {
    render(
      <Card>
        <p>Card content</p>
      </Card>
    );
    expect(screen.getByText(/card content/i)).toBeInTheDocument();
  });

  it('applies default variant class', () => {
    const { container } = render(<Card>Content</Card>);
    const card = container.firstChild as HTMLElement;
    expect(card).toHaveClass('ui-card', 'ui-card-default');
  });

  it('applies correct variant classes', () => {
    const { container, rerender } = render(<Card variant="elevated">Elevated</Card>);
    let card = container.firstChild as HTMLElement;
    expect(card).toHaveClass('ui-card-elevated');

    rerender(<Card variant="glass">Glass</Card>);
    card = container.firstChild as HTMLElement;
    expect(card).toHaveClass('ui-card-glass');

    rerender(<Card variant="outlined">Outlined</Card>);
    card = container.firstChild as HTMLElement;
    expect(card).toHaveClass('ui-card-outlined');
  });

  it('applies hoverable class when hoverable prop is true', () => {
    const { container } = render(<Card hoverable>Hoverable</Card>);
    const card = container.firstChild as HTMLElement;
    expect(card).toHaveClass('ui-card-hover');
  });

  it('applies interactive class when interactive prop is true', () => {
    const { container } = render(<Card interactive>Interactive</Card>);
    const card = container.firstChild as HTMLElement;
    expect(card).toHaveClass('ui-card-interactive');
  });

  it('calls onClick when clicked if interactive', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    const { container } = render(
      <Card interactive onClick={handleClick}>
        Click me
      </Card>
    );

    const card = container.firstChild as HTMLElement;
    await user.click(card);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('applies custom className', () => {
    const { container } = render(<Card className="custom-class">Content</Card>);
    const card = container.firstChild as HTMLElement;
    expect(card).toHaveClass('ui-card', 'custom-class');
  });

  it('does not apply interactive class when not interactive', () => {
    const { container } = render(<Card>Non-interactive</Card>);
    const card = container.firstChild as HTMLElement;
    expect(card).not.toHaveClass('ui-card-interactive');
  });

  it('combines multiple props correctly', () => {
    const { container } = render(
      <Card variant="elevated" hoverable interactive className="custom">
        Combined
      </Card>
    );
    const card = container.firstChild as HTMLElement;
    expect(card).toHaveClass('ui-card', 'ui-card-elevated', 'ui-card-hover', 'ui-card-interactive', 'custom');
  });
});
