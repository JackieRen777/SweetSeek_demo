import { describe, expect, it } from 'vitest';
import { isNearBottom } from '../scrollUtils';

describe('isNearBottom', () => {
  it('detects whether the conversation is close enough to resume auto-follow', () => {
    expect(isNearBottom({ scrollHeight: 1000, scrollTop: 598, clientHeight: 400 })).toBe(true);
    expect(isNearBottom({ scrollHeight: 1000, scrollTop: 590, clientHeight: 400 })).toBe(false);
  });
});
