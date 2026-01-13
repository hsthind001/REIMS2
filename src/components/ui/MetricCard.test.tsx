import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '../../test/utils';
import userEvent from '@testing-library/user-event';
import { MetricCard } from './MetricCard';

describe('MetricCard Component', () => {
  const defaultProps = {
    title: 'Total Revenue',
    value: '$2.5M',
  };

  it('renders title and value', () => {
    render(<MetricCard {...defaultProps} />);
    expect(screen.getByText('Total Revenue')).toBeInTheDocument();
    expect(screen.getByText('$2.5M')).toBeInTheDocument();
  });

  it('renders delta when provided', () => {
    render(<MetricCard {...defaultProps} delta={5.2} />);
    expect(screen.getByText(/5.2%/)).toBeInTheDocument();
  });

  it('renders trend indicator based on trend prop', () => {
    const { container, rerender } = render(<MetricCard {...defaultProps} delta={5.2} trend="up" />);
    let trendElement = container.querySelector('.ui-trend-up');
    expect(trendElement).toBeInTheDocument();

    rerender(<MetricCard {...defaultProps} delta={-3.1} trend="down" />);
    trendElement = container.querySelector('.ui-trend-down');
    expect(trendElement).toBeInTheDocument();

    rerender(<MetricCard {...defaultProps} delta={0} trend="neutral" />);
    trendElement = container.querySelector('.ui-trend-neutral');
    expect(trendElement).toBeInTheDocument();
  });

  it('renders comparison text when provided', () => {
    render(<MetricCard {...defaultProps} delta={5.2} comparison="vs last month" />);
    expect(screen.getByText(/vs last month/i)).toBeInTheDocument();
  });

  it('renders target when target is provided', () => {
    const { container } = render(
      <MetricCard {...defaultProps} target={75} />
    );
    const targetElement = container.querySelector('.ui-metric-target');
    expect(targetElement).toBeInTheDocument();
  });

  it('renders status dot with correct status color', () => {
    const { container, rerender } = render(
      <MetricCard {...defaultProps} status="success" />
    );
    let statusDot = container.querySelector('.ui-status-success');
    expect(statusDot).toBeInTheDocument();

    rerender(<MetricCard {...defaultProps} status="warning" />);
    statusDot = container.querySelector('.ui-status-warning');
    expect(statusDot).toBeInTheDocument();

    rerender(<MetricCard {...defaultProps} status="danger" />);
    statusDot = container.querySelector('.ui-status-danger');
    expect(statusDot).toBeInTheDocument();
  });

  it('calls onClick when clicked', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    const { container } = render(<MetricCard {...defaultProps} onClick={handleClick} />);

    const card = container.querySelector('.ui-metric-card');
    if (card) {
      await user.click(card);
      expect(handleClick).toHaveBeenCalledTimes(1);
    }
  });

  it('shows skeleton loading state', () => {
    const { container } = render(<MetricCard {...defaultProps} loading />);
    const skeletons = container.querySelectorAll('.ui-skeleton');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('displays all elements when all props are provided', () => {
    render(
      <MetricCard
        title="Complete Metric"
        value="2500000"
        delta={5.2}
        trend="up"
        comparison="vs last quarter"
        target={83}
        status="success"
      />
    );

    expect(screen.getByText('Complete Metric')).toBeInTheDocument();
    expect(screen.getByText('2500000')).toBeInTheDocument();
    expect(screen.getByText(/5.2%/)).toBeInTheDocument();
    expect(screen.getByText(/vs last quarter/i)).toBeInTheDocument();
  });
});
