import { describe, expect, it } from 'vitest';
import { featureFromPath } from './routing';

describe('feature routing', () => {
  it('keeps research routes while MD Builder is disabled', () => {
    expect(featureFromPath('/proteoglycan')).toBe('proteoglycan');
    expect(featureFromPath('/proteoglycan/')).toBe('proteoglycan');
    expect(featureFromPath('/docking', false)).toBeNull();
    expect(featureFromPath('/amber-md-builder', false)).toBeNull();
    expect(featureFromPath('/encapsulation')).toBe('encapsulation');
    expect(featureFromPath('/embedding')).toBe('encapsulation');
  });

  it('routes both MD Builder addresses when MD Builder is enabled', () => {
    expect(featureFromPath('/docking', true)).toBe('md-builder');
    expect(featureFromPath('/amber-md-builder', true)).toBe('md-builder');
  });
});
