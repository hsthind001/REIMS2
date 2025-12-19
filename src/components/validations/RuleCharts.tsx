/**
 * RuleCharts Component
 * 
 * Displays validation rule analytics charts
 */

import React, { useEffect, useRef } from 'react';
import { Card } from '../design-system';
import { Chart, registerables } from 'chart.js';
import type { ValidationAnalyticsResponse } from '../../types/api';

Chart.register(...registerables);

interface RuleChartsProps {
  analytics: ValidationAnalyticsResponse;
}

export const RuleCharts: React.FC<RuleChartsProps> = ({ analytics }) => {
  const passRateChartRef = useRef<HTMLCanvasElement>(null);
  const failureDistributionChartRef = useRef<HTMLCanvasElement>(null);
  const topFailingChartRef = useRef<HTMLCanvasElement>(null);
  const validationVolumeChartRef = useRef<HTMLCanvasElement>(null);
  const chartInstances = useRef<Chart[]>([]);

  useEffect(() => {
    // Destroy existing charts before re-rendering
    chartInstances.current.forEach(chart => chart.destroy());
    chartInstances.current = [];

    if (!analytics) return;

    // Chart 1: Pass Rate Over Time (Line Chart) - 7 days
    if (passRateChartRef.current && analytics.pass_rate_trends['7d']) {
      const trends = analytics.pass_rate_trends['7d'];
      const labels = trends.map(t => new Date(t.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
      const passRates = trends.map(t => t.pass_rate);

      const passRateChart = new Chart(passRateChartRef.current, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: 'Pass Rate (%)',
            data: passRates,
            borderColor: '#4CAF50',
            backgroundColor: 'rgba(76, 175, 80, 0.1)',
            tension: 0.4,
            fill: true
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'top',
            },
            title: {
              display: true,
              text: 'Pass Rate Over Time (Last 7 Days)',
              color: '#E0E0E0'
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              max: 100,
              title: {
                display: true,
                text: 'Pass Rate (%)',
                color: '#E0E0E0'
              },
              ticks: {
                color: '#B0B0B0'
              },
              grid: {
                color: 'rgba(255, 255, 255, 0.1)'
              }
            },
            x: {
              title: {
                display: true,
                text: 'Date',
                color: '#E0E0E0'
              },
              ticks: {
                color: '#B0B0B0'
              },
              grid: {
                color: 'rgba(255, 255, 255, 0.1)'
              }
            }
          }
        },
      });
      chartInstances.current.push(passRateChart);
    }

    // Chart 2: Failure Distribution (Doughnut Chart) - By Severity
    if (failureDistributionChartRef.current && analytics.failure_distribution) {
      const severityFailures = analytics.failure_distribution.filter(f => f.severity);
      const labels = severityFailures.map(f => f.severity || 'Unknown');
      const data = severityFailures.map(f => f.count);
      const colors = ['#F44336', '#FF9800', '#2196F3']; // Red, Orange, Blue

      const failureChart = new Chart(failureDistributionChartRef.current, {
        type: 'doughnut',
        data: {
          labels: labels,
          datasets: [{
            data: data,
            backgroundColor: colors.slice(0, labels.length),
            hoverOffset: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
            },
            title: {
              display: true,
              text: 'Failure Distribution by Severity',
              color: '#E0E0E0'
            }
          }
        },
      });
      chartInstances.current.push(failureChart);
    }

    // Chart 3: Top Failing Rules (Bar Chart)
    if (topFailingChartRef.current && analytics.top_failing_rules) {
      const topRules = analytics.top_failing_rules.slice(0, 5); // Top 5
      const labels = topRules.map(r => r.rule_name.length > 20 ? r.rule_name.substring(0, 20) + '...' : r.rule_name);
      const failureRates = topRules.map(r => r.failure_rate);

      const topFailingChart = new Chart(topFailingChartRef.current, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            label: 'Failure Rate (%)',
            data: failureRates,
            backgroundColor: '#F44336',
            borderColor: '#D32F2F',
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          indexAxis: 'y', // Horizontal bars
          plugins: {
            legend: {
              display: false
            },
            title: {
              display: true,
              text: 'Top Failing Rules (by Failure Rate)',
              color: '#E0E0E0'
            }
          },
          scales: {
            x: {
              beginAtZero: true,
              max: 100,
              title: {
                display: true,
                text: 'Failure Rate (%)',
                color: '#E0E0E0'
              },
              ticks: {
                color: '#B0B0B0'
              },
              grid: {
                color: 'rgba(255, 255, 255, 0.1)'
              }
            },
            y: {
              title: {
                display: true,
                text: 'Rule',
                color: '#E0E0E0'
              },
              ticks: {
                color: '#B0B0B0'
              },
              grid: {
                color: 'rgba(255, 255, 255, 0.1)'
              }
            }
          }
        },
      });
      chartInstances.current.push(topFailingChart);
    }

    // Chart 4: Validation Volume (Area Chart) - Last 7 days
    if (validationVolumeChartRef.current && analytics.pass_rate_trends['7d']) {
      const trends = analytics.pass_rate_trends['7d'];
      const labels = trends.map(t => new Date(t.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
      const volumes = trends.map(t => t.total_tests);

      const volumeChart = new Chart(validationVolumeChartRef.current, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: 'Validation Volume',
            data: volumes,
            borderColor: '#2196F3',
            backgroundColor: 'rgba(33, 150, 243, 0.2)',
            tension: 0.4,
            fill: true
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'top',
            },
            title: {
              display: true,
              text: 'Validation Volume Over Time (Last 7 Days)',
              color: '#E0E0E0'
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              title: {
                display: true,
                text: 'Number of Validations',
                color: '#E0E0E0'
              },
              ticks: {
                color: '#B0B0B0'
              },
              grid: {
                color: 'rgba(255, 255, 255, 0.1)'
              }
            },
            x: {
              title: {
                display: true,
                text: 'Date',
                color: '#E0E0E0'
              },
              ticks: {
                color: '#B0B0B0'
              },
              grid: {
                color: 'rgba(255, 255, 255, 0.1)'
              }
            }
          }
        },
      });
      chartInstances.current.push(volumeChart);
    }

    return () => {
      chartInstances.current.forEach(chart => chart.destroy());
    };
  }, [analytics]);

  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold">Analytics & Performance</h3>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-4 h-80">
          <canvas ref={passRateChartRef}></canvas>
        </Card>
        <Card className="p-4 h-80">
          <canvas ref={failureDistributionChartRef}></canvas>
        </Card>
        <Card className="p-4 h-80">
          <canvas ref={topFailingChartRef}></canvas>
        </Card>
        <Card className="p-4 h-80">
          <canvas ref={validationVolumeChartRef}></canvas>
        </Card>
      </div>
    </div>
  );
};

