import { describe, expect, it } from 'vitest';
import { money } from './format';

describe('INR formatting', () => {
  it('formats values using Indian digit grouping', () => {
    expect(money(1234567)).toContain('12,34,567');
  });
  it('rounds to whole rupees for dashboard display', () => {
    expect(money(1250.4)).toContain('1,250');
  });
});
