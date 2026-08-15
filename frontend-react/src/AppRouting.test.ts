import { describe, expect, it } from 'vitest';
import { featureFromPath } from './routing';

describe('feature routing', () => {
  it('supports all research and structural-computation routes', () => {
    expect(featureFromPath('/proteoglycan')).toBe('proteoglycan');
    expect(featureFromPath('/proteoglycan/')).toBe('proteoglycan');
    expect(featureFromPath('/docking')).toBe('docking');
    expect(featureFromPath('/encapsulation')).toBe('encapsulation');
    expect(featureFromPath('/embedding')).toBe('encapsulation');
  });
});
