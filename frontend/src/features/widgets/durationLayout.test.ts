import { describe, expect, it } from 'vitest';

import { durationGridRows, durationPlotHeight } from './durationLayout';

describe('durationPlotHeight', () => {
  it('растёт с числом операций', () => {
    const small = durationPlotHeight('operation_durations_boxplot', 5);
    const big = durationPlotHeight('operation_durations_boxplot', 20);
    expect(big).toBeGreaterThan(small);
  });

  it('минимум 1 операция (не нулевая высота)', () => {
    expect(durationPlotHeight('sojourn_vs_own', 0)).toBe(
      durationPlotHeight('sojourn_vs_own', 1),
    );
  });
});

describe('durationGridRows', () => {
  it('растёт с числом операций', () => {
    const a = durationGridRows('operation_durations_boxplot', 5, 6);
    const b = durationGridRows('operation_durations_boxplot', 20, 6);
    expect(b).toBeGreaterThan(a);
  });

  it('не опускается ниже minRows', () => {
    expect(durationGridRows('operation_durations_boxplot', 1, 8)).toBe(8);
  });

  it('упирается в потолок при многих операциях (>25 → дальше скролл)', () => {
    const at25 = durationGridRows('duration_bottleneck_heatmap', 25, 6);
    const at50 = durationGridRows('duration_bottleneck_heatmap', 50, 6);
    expect(at50).toBe(at25);
  });
});
