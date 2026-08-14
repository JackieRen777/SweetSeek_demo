import { describe, expect, it } from 'vitest';
import { featureFromPath } from './routing';

describe('feature routing', () => {
  it('supports Proteoglycan and preserves Encapsulation compatibility routes', () => {
    expect(featureFromPath('/proteoglycan')).toBe('proteoglycan');
    expect(featureFromPath('/proteoglycan/')).toBe('proteoglycan');
    expect(featureFromPath('/encapsulation')).toBe('encapsulation');
    expect(featureFromPath('/embedding')).toBe('encapsulation');
  });
});
