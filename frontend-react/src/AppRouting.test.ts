import { describe, expect, it } from 'vitest';
import { featureFromPath } from './routing';

describe('feature routing', () => {
  it('keeps research routes while structural tools are disabled', () => {
    expect(featureFromPath('/proteoglycan')).toBe('proteoglycan');
    expect(featureFromPath('/proteoglycan/')).toBe('proteoglycan');
    expect(featureFromPath('/docking')).toBeNull();
    expect(featureFromPath('/amber-md-builder')).toBeNull();
    expect(featureFromPath('/encapsulation')).toBe('encapsulation');
    expect(featureFromPath('/embedding')).toBe('encapsulation');
  });

  it('restores structural routes for a dedicated structure-tools release', () => {
    expect(featureFromPath('/docking', true)).toBe('md-builder');
    expect(featureFromPath('/amber-md-builder', true)).toBe('md-builder');
  });
});
